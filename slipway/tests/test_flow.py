import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from flow import Ledger, digest, evidence, private_write
from connections import inventory, handoff, load_profile, REQUIRED

WORKER = Path(__file__).resolve().parents[1] / 'tools/flow.py'
IDENT = {'bundleId': 'com.example.counter', 'version': '1.0', 'build': '7'}


class FlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ledger = Ledger(self.root / 'state')
        self.remote = self.root / 'remote.json'
        private_write(self.remote, {'state': 'absent', 'writes': 0, 'identity': IDENT})
        self.script = self.root / 'provider.py'
        self.script.write_text('''import json,sys,time
from pathlib import Path
p=Path(sys.argv[1]); d=json.loads(p.read_text())
if sys.argv[2]=='read': print(json.dumps(d))
else:
 d['writes']+=1; d['state']=sys.argv[2]; p.write_text(json.dumps(d))
 if len(sys.argv)>3: time.sleep(float(sys.argv[3]))
 if d['state']=='unknown': print('connection dropped'); sys.exit(1)
''')

    def tearDown(self):
        self.tmp.cleanup()

    def local(self, name='assets', code=None):
        output = self.root / (name + '.txt')
        return {'id': name, 'kind': 'local', 'action': 'Prepare assets', 'artifacts': [str(output)],
                'command': [sys.executable, '-c', code or f'from pathlib import Path; Path({str(output)!r}).write_text("done")']}

    def external(self, state='complete', delay=None):
        return {'id': 'submit', 'kind': 'external', 'effect': 'preparation', 'action': 'Submit exact release', 'scope': 'apple:exact-build',
                'identity': IDENT, 'command': [sys.executable, str(self.script), str(self.remote), state] + ([str(delay)] if delay else []),
                'reconcile': [sys.executable, str(self.script), str(self.remote), 'read']}

    def start(self, jobs):
        plan = {'jobs': jobs, 'identity': IDENT}
        self.ledger.init(plan)
        return {'planDigest': digest(plan), 'statement': 'Explicit test authorization', 'source': 'synthetic fixture', 'scopes': ['apple:exact-build']}

    def remote_state(self, state):
        d = json.loads(self.remote.read_text()); d['state'] = state; private_write(self.remote, d)

    def test_human_wait_does_not_stall_independent_work_and_answers_survive(self):
        human = {'id': 'phone', 'kind': 'human', 'action': 'Unlock and test phone'}
        depends = self.local('after-phone'); depends['deps'] = ['phone']
        self.start([human, depends, self.local()])
        self.ledger.run()
        s = self.ledger.read()['jobs']
        self.assertEqual(s['assets']['state'], 'complete')
        self.assertEqual(s['phone']['state'], 'waiting')
        self.assertEqual(s['after-phone']['attempts'], 0)
        receipt = self.root / 'answer.json'; private_write(receipt, {'result': 'pass', 'source': 'test human'})
        self.ledger.answer('phone', receipt)
        Ledger(self.ledger.root).run()
        self.ledger.answer('phone', receipt)
        self.assertEqual(self.ledger.read()['jobs']['assets']['attempts'], 1)
        self.assertEqual(self.ledger.read()['jobs']['after-phone']['state'], 'complete')
        self.assertIsNone(self.ledger.status()['worker'])

    def test_expired_login_and_missing_recording_permission_do_not_stall_assets(self):
        for name in ('expired-login', 'recording-permission'):
            job = self.local(name, 'raise SystemExit(1)')
            if name == 'expired-login': jobs = [job]
            else: jobs.append(job)
        self.start(jobs + [self.local()]); self.ledger.run()
        states = self.ledger.read()['jobs']
        self.assertEqual(states['assets']['state'], 'complete')
        self.assertEqual(states['expired-login']['state'], 'blocked')
        self.assertEqual(states['recording-permission']['state'], 'blocked')
        self.ledger.run()
        self.assertEqual(self.ledger.read()['jobs']['recording-permission']['attempts'], 1)

    def test_signing_failure_retry_needs_changed_condition_and_preserves_completed_work(self):
        sentinel = self.root / 'unlocked'
        output = self.root / 'sign.txt'
        code = f'from pathlib import Path; import sys; sys.exit(65) if not Path({str(sentinel)!r}).exists() else Path({str(output)!r}).write_text("signed")'
        self.start([self.local('sign', code), self.local()]); self.ledger.run()
        self.assertEqual(self.ledger.read()['jobs']['sign']['state'], 'blocked')
        self.ledger.run(); self.assertEqual(self.ledger.read()['jobs']['sign']['attempts'], 1)
        sentinel.write_text('disposable signing probe now succeeds')
        self.ledger.retry('sign', sentinel); self.ledger.run()
        self.assertEqual(self.ledger.read()['jobs']['sign']['state'], 'complete')
        self.assertEqual(self.ledger.read()['jobs']['assets']['attempts'], 1)

    def test_delayed_processing_polls_without_second_upload(self):
        auth = self.start([self.external('pending'), self.local()])
        self.ledger.run(auth); self.ledger.run(auth)
        self.assertEqual(self.ledger.read()['jobs']['submit']['state'], 'waiting')
        self.assertEqual(json.loads(self.remote.read_text())['writes'], 1)
        self.remote_state('complete'); self.ledger.run(auth)
        self.assertEqual(self.ledger.read()['jobs']['submit']['state'], 'complete')
        self.assertEqual(json.loads(self.remote.read_text())['writes'], 1)

    def test_ambiguous_response_never_repeats_create_even_if_next_read_says_absent(self):
        auth = self.start([self.external('unknown')]); self.ledger.run(auth)
        self.remote_state('absent'); self.ledger.run(auth)
        self.assertEqual(self.ledger.read()['jobs']['submit']['state'], 'blocked')
        self.assertEqual(json.loads(self.remote.read_text())['writes'], 1)
        with self.assertRaises(ValueError): self.ledger.retry('submit', self.remote)
        self.remote_state('complete'); self.ledger.run(auth)
        self.assertEqual(self.ledger.read()['jobs']['submit']['state'], 'complete')

    def test_killed_worker_recovers_by_readback_without_duplicate_external_action(self):
        auth = self.start([self.external('complete', 0.8)])
        a = self.root / 'auth.json'; private_write(a, auth)
        p = subprocess.Popen([sys.executable, str(WORKER), '--state', str(self.ledger.root), 'run', '--authorization', str(a)], stdout=subprocess.DEVNULL)
        try:
            deadline = time.time() + 5
            while json.loads(self.remote.read_text())['writes'] == 0 and time.time() < deadline: time.sleep(0.02)
            self.assertEqual(json.loads(self.remote.read_text())['writes'], 1)
            self.assertTrue(self.ledger.status()['running'])
            p.kill(); p.wait()
            self.assertFalse(self.ledger.status()['running'])
            self.assertEqual(self.ledger.status()['jobs'][0]['state'], 'blocked')
            self.ledger.run(auth)
            self.assertEqual(self.ledger.read()['jobs']['submit']['state'], 'complete')
            self.assertEqual(json.loads(self.remote.read_text())['writes'], 1)
        finally:
            if p.poll() is None: p.kill(); p.wait()
            time.sleep(0.85)  # let the intentionally orphaned synthetic command exit

    def test_partial_approval_does_not_authorize_publication(self):
        public = self.external(); public['id'] = 'public'; public['scope'] = 'github:example/repo'
        auth = self.start([self.external(), public, self.local()]); self.ledger.run(auth)
        self.assertEqual(self.ledger.read()['jobs']['submit']['state'], 'complete')
        self.assertEqual(self.ledger.read()['jobs']['public']['state'], 'waiting')
        self.assertEqual(self.ledger.read()['jobs']['public']['attempts'], 0)
        self.assertEqual(self.ledger.read()['jobs']['assets']['state'], 'complete')

    def test_wrong_build_readback_and_changed_plan_fail_closed(self):
        auth = self.start([self.external()])
        d = json.loads(self.remote.read_text()); d['identity']['build'] = '6'; private_write(self.remote, d)
        self.ledger.run(auth)
        self.assertEqual(json.loads(self.remote.read_text())['writes'], 0)
        with self.assertRaises(ValueError): self.ledger.init({'jobs': [self.local()]})

    def test_evidence_tamper_blocks_dependents_and_no_session_secret_inheritance(self):
        os.environ['SLIPWAY_TEST_SECRET'] = 'never-forward'
        output = self.root / 'safe.txt'
        job = self.local('safe', f'import os; from pathlib import Path; assert "SLIPWAY_TEST_SECRET" not in os.environ; Path({str(output)!r}).write_text("safe")')
        self.start([job]); self.ledger.run()
        self.assertEqual(self.ledger.read()['jobs']['safe']['state'], 'complete')
        output.write_text('tampered')
        self.assertEqual(self.ledger.status()['jobs'][0]['state'], 'blocked')
        self.ledger.run(); self.assertEqual(self.ledger.read()['jobs']['safe']['attempts'], 1)
        self.assertEqual(self.ledger.db.stat().st_mode & 0o077, 0)

    def test_two_workers_cannot_own_same_release(self):
        self.start([self.local()])
        with self.ledger.lock():
            with self.assertRaises(ValueError): Ledger(self.ledger.root).run()


class OnboardingTest(unittest.TestCase):
    def test_fresh_profile_lists_every_connection_and_preserves_scoped_answers(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); p = root / 'profile.json'
            profile = {'mac': 'Build Mac', 'phone': 'Test iPhone', 'connections': {}}
            private_write(p, profile)
            inv = inventory(load_profile(p))
            self.assertEqual(set(inv['connections']), set(REQUIRED))
            text = handoff(inv)
            self.assertIn('Reachability is unverified', text)
            self.assertNotIn('No cable request', text)
            profile['connections']['phone'] = {'probe': [sys.executable, '-c', 'print(\'{"state":"verified","reachable":true,"paired":true,"transport":"network"}\')']}
            inv = inventory(profile)
            proof = root / 'answer'; proof.write_text('observed pass')
            app = {'app': IDENT}
            answers = {'coreFlow': {'identity': IDENT, 'result': 'pass', 'evidence': [evidence(proof)]}}
            text = handoff(inv, app, answers)
            self.assertIn('No cable request', text)
            self.assertIn('[x] coreFlow: recorded; do not repeat', text)
            answers['coreFlow']['identity'] = {**IDENT, 'build': '8'}
            self.assertIn('[ ] coreFlow', handoff(inv, app, answers))

    def test_expired_session_permission_scope_and_network_authorization(self):
        with tempfile.TemporaryDirectory() as d:
            receipt = Path(d) / 'session.json'
            profile = {'mac': 'Build Mac', 'phone': 'Test iPhone', 'connections': {'webSession': {'receipt': str(receipt)}}}
            item = profile['connections']['webSession']
            fp = digest({'mac': profile['mac'], 'phone': profile['phone'], 'config': item})
            doc = {'fingerprint': fp, 'state': 'verified', 'source': 'observed user session', 'observedAt': time.time(), 'expiresAt': time.time()+300}
            private_write(receipt, doc)
            self.assertEqual(inventory(profile)['connections']['webSession']['state'], 'verified')
            doc['expiresAt'] = time.time()-1; private_write(receipt, doc)
            self.assertEqual(inventory(profile)['connections']['webSession']['state'], 'waiting')
            profile['connections']['api'] = {'network': True, 'probe': [sys.executable, '-c', 'raise Exception("must not run")']}
            inv = inventory(profile)
            self.assertIn('authorization', inv['connections']['api']['action'])
            self.assertEqual(inv['connections']['capturePermission']['state'], 'unknown')
            inv['connections']['capture']['details'] = {'route': 'quicktime-usb'}
            self.assertIn('Test iPhone directly to Build Mac', handoff(inv))

class AdditionalRecoveryTest(unittest.TestCase):
    setUp = FlowTest.setUp
    tearDown = FlowTest.tearDown
    local = FlowTest.local
    start = FlowTest.start
    external = FlowTest.external
    remote_state = FlowTest.remote_state
    def test_failed_prerequisite_is_blocked_not_a_human_wait(self):
        prerequisite = self.local('sign', 'raise SystemExit(65)')
        dependent = self.local('archive'); dependent['deps'] = ['sign']
        self.start([dependent, prerequisite]); self.ledger.run()
        states = {j['id']: j['state'] for j in self.ledger.status()['jobs']}
        self.assertEqual(states['archive'], 'blocked')
        self.assertEqual(self.ledger.read()['jobs']['archive']['attempts'], 0)

    def test_changed_source_invalidates_completed_job(self):
        source = self.root / 'source'; source.write_text('old')
        job = self.local(); job['inputs'] = [str(source)]
        self.start([job]); self.ledger.run()
        source.write_text('new')
        self.assertEqual(self.ledger.status()['jobs'][0]['state'], 'blocked')
        self.ledger.run()
        self.assertEqual(self.ledger.read()['jobs']['assets']['attempts'], 1)

    def test_answer_can_arrive_while_worker_runs(self):
        human = {'id': 'phone', 'kind': 'human', 'action': 'Test phone'}
        output = self.root / 'assets.txt'
        self.start([human, self.local(code=f'import time; from pathlib import Path; time.sleep(0.4); Path({str(output)!r}).write_text("done")')])
        p = subprocess.Popen([sys.executable, str(WORKER), '--state', str(self.ledger.root), 'run'], stdout=subprocess.DEVNULL)
        try:
            deadline = time.time()+5
            while not self.ledger.status()['running'] and time.time()<deadline: time.sleep(0.01)
            receipt = self.root / 'human'; receipt.write_text('human result')
            self.ledger.answer('phone', receipt)
            self.assertEqual(p.wait(timeout=5), 0)
            self.assertEqual(self.ledger.read()['jobs']['phone']['state'], 'complete')
        finally:
            if p.poll() is None: p.kill(); p.wait()


    def test_expired_remote_login_recovers_without_duplicate_or_stalling_assets(self):
        auth = self.start([self.external(), self.local()])
        self.remote_state('blocked')  # adapter cannot verify remote state until login is refreshed
        self.ledger.run(auth)
        self.assertEqual(json.loads(self.remote.read_text())['writes'], 0)
        self.assertEqual(self.ledger.read()['jobs']['assets']['state'], 'complete')
        self.remote_state('absent')  # explicit synthetic refreshed-session readback
        self.ledger.run(auth)
        self.assertEqual(json.loads(self.remote.read_text())['writes'], 1)
        self.assertEqual(self.ledger.read()['jobs']['assets']['attempts'], 1)

class ProfileInitializationTest(unittest.TestCase):
    def test_initialization_seeds_only_local_probes_and_preserves_existing_configuration(self):
        from connections import initialize
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'profile.json'
            initialize(path, 'Build Mac', 'Test iPhone')
            profile = load_profile(path)
            self.assertEqual(set(k for k,v in profile['connections'].items() if v.get('probe')), {'toolchain','phone','capture'})
            with self.assertRaises(ValueError): initialize(path, 'Another Mac', 'Another phone')
            self.assertEqual(load_profile(path)['mac'], 'Build Mac')
