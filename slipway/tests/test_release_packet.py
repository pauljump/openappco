import json
from pathlib import Path
import plistlib
import sys
import time
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import release_packet as release
from flow import evidence, private_write
import test_slipway


class ReleaseTest(unittest.TestCase):
    def setUp(self):
        self.fixture = test_slipway.SlipwayTest()
        self.fixture.setUp()
        self.root = self.fixture.app_dir
        self.app = json.loads((self.root / 'app.json').read_text())
        self.ident = release.identity(self.app)
        self.binary = self.root / 'app.ipa'
        with zipfile.ZipFile(self.binary, 'w') as z:
            z.writestr('Payload/Counter.app/Info.plist', plistlib.dumps(dict(zip(
                ('CFBundleIdentifier', 'CFBundleShortVersionString', 'CFBundleVersion'), self.ident.values()))))
        self.proof = self.root / 'binary.json'
        private_write(self.proof, {'identity': self.ident, 'sha256': evidence(self.binary)['sha256']})
        self.store = self.root / 'store-evidence.json'
        receipt = self.root / 'observed.json'; private_write(receipt, {'source': 'synthetic fixture observation', 'identity': self.ident})
        self.manifest = {'identity': self.ident, 'binary': str(self.binary), 'binaryIdentity': str(self.proof), 'checks': {}}
        for gate in release.STORE_GATES:
            normalized = self.root / (gate + '-receipt.json')
            private_write(normalized, {'identity': self.ident, 'gate': gate, 'result': 'pass', 'source': 'synthetic observation', 'artifacts': [evidence(receipt)]})
            self.manifest['checks'][gate] = {'passed': True, 'observedAt': time.time(), 'expiresAt': time.time()+3600, 'receipt': str(normalized), 'sha256': evidence(normalized)['sha256']}
        private_write(self.store, self.manifest)
        self.destinations = [{'scope': 'apple:submit', 'destination': 'App Store Connect / example release', 'action': 'Submit build 3'},
                             {'scope': 'github:publish', 'destination': 'https://github.com/example/studio', 'action': 'Publish catalog/assets'}]

    def tearDown(self): self.fixture.tearDown()

    def seal(self):
        p = release.packet(self.root, self.store, self.destinations)
        path = self.root / 'packet.json'; private_write(path, p)
        return path, p

    def receipt(self, packet, limits=None):
        path = self.root / 'approval.json'
        private_write(path, {'packetDigest': packet['digest'], 'statement': 'Approved for Apple with named limits',
                             'source': 'synthetic user reply', 'approvedAt': time.time(), 'scopes': ['apple:submit'],
                             'acceptedTestingLimits': limits or []})
        return path

    def test_ready_requires_all_scopes_and_real_artifacts(self):
        path, p = self.seal()
        self.assertEqual(p['blockers'], [])
        self.assertEqual(p['status'], 'ready')
        a = self.receipt(p)
        release.verify_approval(path, a, 'apple:submit')
        with self.assertRaises(ValueError): release.verify_approval(path, a, 'github:publish')
        self.binary.write_bytes(b'changed build')
        with self.assertRaises(ValueError): release.verify_approval(path, a, 'apple:submit')

    def test_testing_limits_are_never_converted_into_passes(self):
        dc = self.root / self.app['files']['deviceCheck']
        data = json.loads(dc.read_text()); data['checks']['voiceOverCoreFlow'] = 'not_checked'; private_write(dc, data)
        path, p = self.seal()
        self.assertEqual(p['status'], 'review-with-limits')
        self.assertEqual(p['testingLimits'], ['voiceOverCoreFlow'])
        with self.assertRaises(ValueError): release.approve(path, self.receipt(p))
        release.approve(path, self.receipt(p, ['voiceOverCoreFlow']))
        self.assertEqual(json.loads(dc.read_text())['checks']['voiceOverCoreFlow'], 'not_checked')

    def test_missing_recording_or_apple_processing_is_not_waivable(self):
        self.manifest['checks']['processing']['passed'] = False
        private_write(self.store, self.manifest)
        path, p = self.seal()
        self.assertEqual(p['status'], 'blocked')
        with self.assertRaises(ValueError): release.approve(path, self.receipt(p, ['processing']))

    def test_expired_receipt_and_wrong_embedded_build_block(self):
        self.manifest['checks']['privacy']['expiresAt'] = time.time()-1
        private_write(self.store, self.manifest)
        with zipfile.ZipFile(self.binary, 'w') as z:
            z.writestr('Payload/Counter.app/Info.plist', plistlib.dumps({'CFBundleVersion': '99'}))
        _, p = self.seal()
        self.assertTrue(any('expired' in x for x in p['blockers']))
        self.assertTrue(any('identity mismatch' in x for x in p['blockers']))

    def test_metadata_change_invalidates_approval(self):
        path, p = self.seal(); a = self.receipt(p)
        notes = self.root / self.app['files']['reviewNotes']; notes.write_text(notes.read_text() + '\nchanged')
        with self.assertRaises(ValueError): release.verify_approval(path, a, 'apple:submit')

    def test_new_source_file_invalidates_packet(self):
        path, p = self.seal(); a = self.receipt(p)
        (self.root / 'Sources/New.swift').write_text('let changed = true')
        with self.assertRaises(ValueError): release.verify_approval(path, a, 'apple:submit')

    def test_wrong_raw_receipt_cannot_be_marked_ready(self):
        raw = self.root / 'processing-receipt.json'
        data = json.loads(raw.read_text()); data['identity']['build'] = '99'; private_write(raw, data)
        self.manifest['checks']['processing']['sha256'] = evidence(raw)['sha256']; private_write(self.store, self.manifest)
        _, p = self.seal()
        self.assertTrue(any('bind gate, build' in x for x in p['blockers']))

    def test_actual_failed_phone_check_is_not_a_waivable_limit(self):
        dc = self.root / self.app['files']['deviceCheck']
        data = json.loads(dc.read_text()); data['checks']['coreFlow'] = 'fail'; private_write(dc, data)
        _, p = self.seal()
        self.assertEqual(p['status'], 'blocked')
        self.assertNotIn('coreFlow', p['testingLimits'])

    def test_runner_requires_packet_approval_for_each_destination(self):
        from flow import Ledger, digest
        path, p = self.seal(); a = self.receipt(p)
        marker = self.root / 'published'
        job = {'id': 'publish', 'kind': 'external', 'effect': 'publication', 'action': 'Publish exact assets',
               'packet': str(path), 'scope': 'github:publish', 'identity': self.ident,
               'command': [sys.executable, '-c', f'from pathlib import Path; Path({str(marker)!r}).write_text("published")'],
               'reconcile': [sys.executable, '-c', f'print({json.dumps({"state":"absent", "identity":self.ident})!r})']}
        plan = {'jobs': [job]}; ledger = Ledger(self.root / 'ledger'); ledger.init(plan)
        auth = {'planDigest': digest(plan), 'scopes': ['github:publish'], 'statement': 'see actual approved scope',
                'source': 'synthetic test', 'releaseApproval': str(a)}
        ledger.run(auth)
        self.assertFalse(marker.exists())
        self.assertEqual(ledger.read()['jobs']['publish']['attempts'], 0)
        self.assertTrue(ledger.read()['authorizations'])

    def test_job_identity_must_equal_approved_packet(self):
        path, p = self.seal(); a = self.receipt(p)
        with self.assertRaises(ValueError):
            release.verify_approval(path, a, 'apple:submit', {**self.ident, 'build': '99'})

    def test_late_readback_can_reconcile_without_repeating_write_or_renewing_approval(self):
        from flow import Ledger, digest
        path, p = self.seal(); a = self.receipt(p)
        job = {'id': 'submit', 'kind': 'external', 'effect': 'submission', 'action': 'Submit reviewed build',
               'packet': str(path), 'scope': 'apple:submit', 'identity': self.ident,
               'command': [sys.executable, '-c', 'raise Exception("must never write again")'],
               'reconcile': [sys.executable, '-c', f'print({json.dumps({"state":"complete", "identity":self.ident})!r})']}
        plan = {'jobs':[job]}; ledger = Ledger(self.root / 'ledger'); ledger.init(plan)
        ledger.change({'syntheticInterruptedIntent': True}, lambda s: s['jobs']['submit'].update(intent=True, state='blocked'))
        # Evidence changed after the remote action. It cannot authorize a new write,
        # but must not stop a read-only reconciliation of the previous intent.
        self.binary.write_bytes(b'local build no longer available')
        ledger.run({'planDigest':digest(plan), 'scopes':['apple:submit'], 'statement':'check earlier action',
                    'source':'synthetic test', 'releaseApproval':str(a)})
        self.assertEqual(ledger.read()['jobs']['submit']['state'], 'complete')
        self.assertEqual(ledger.read()['jobs']['submit']['attempts'], 0)
