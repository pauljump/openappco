#!/usr/bin/env python3
"""Freeze checked artifacts for one exact-build approval; never submit from this tool."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import plistlib
import zipfile
import sys
import time

import slipway
from flow import digest, evidence, intact, private_write

# Local policy gates, not a claim that Apple exposes all these through its API.
STORE_GATES = ('signing', 'processing', 'attachedBuild', 'screenshots', 'privacy', 'agreements',
               'urls', 'reviewVideo', 'reviewNotes', 'inspection')


def identity(app):
    return {k: str(app['app'][k]) for k in ('bundleId', 'version', 'build')}


def packet(app_dir, store_evidence, destinations):
    app_dir = Path(app_dir).resolve()
    app = json.loads((app_dir / 'app.json').read_text())
    ident = identity(app)
    hard, limits, reports = [], [], {}
    directories = {}
    expiry = time.time() + 86400
    refs = [app_dir / 'app.json', Path(store_evidence).resolve()]
    for phase in ('build', 'phone', 'submit'):
        report = slipway.check(app_dir, None, phase)
        reports[phase] = report
        for failure in report['failures']:
            m = re.match(r"device check '([^']+)' is .*needs 'pass'", failure)
            if phase == 'phone' and m and ("is 'not_checked'" in failure or 'is None' in failure):
                limits.append(m.group(1))
            else:
                hard.append(f'{phase}: {failure}')
    # Freeze every reviewed source/metadata/media input; substitutions invalidate approval.
    for key, value in app['files'].items():
        for rel in value if isinstance(value, list) else [value]:
            if not isinstance(rel, str):
                continue
            p = app_dir / rel
            if p.is_file(): refs.append(p.resolve())
            elif p.is_dir():
                members = sorted(str(x.resolve()) for x in p.rglob('*') if x.is_file() and x.name not in ('.gitkeep', '.DS_Store'))
                directories[str(p.resolve())] = members
                refs += [Path(x) for x in members]
    dc_path = app_dir / app['files']['deviceCheck']
    if dc_path.is_file():
        dc = json.loads(dc_path.read_text())
        if dc.get('video', {}).get('file'):
            refs.append((dc_path.parent / dc['video']['file']).resolve())
    store = json.loads(Path(store_evidence).read_text())
    if store.get('identity') != ident:
        hard.append('store evidence is for a different build')
    for gate in STORE_GATES:
        item = store.get('checks', {}).get(gate, {})
        if item.get('passed') is not True or not item.get('observedAt'):
            hard.append(f'store: {gate} unverified')
        if not (isinstance(item.get('expiresAt'), (int, float)) and time.time() < item['expiresAt'] <= time.time() + 86400):
            hard.append(f'store: {gate} receipt expired or has no bounded expiry')
        else:
            expiry = min(expiry, item['expiresAt'])
        receipt = item.get('receipt')
        try:
            p = (Path(store_evidence).parent / receipt).resolve() if receipt else None
            if not p or not p.is_file() or not p.stat().st_size:
                raise ValueError('missing receipt')
            if item.get('sha256') != slipway.sha256(p):
                raise ValueError('receipt hash mismatch')
            receipt_doc = json.loads(p.read_text())
            if not (receipt_doc.get('identity') == ident and receipt_doc.get('gate') == gate
                    and receipt_doc.get('result') == 'pass' and receipt_doc.get('source')
                    and receipt_doc.get('artifacts') and intact(receipt_doc['artifacts'])):
                raise ValueError('receipt must bind gate, build, observer/source and intact raw evidence')
            refs.append(p)
            refs.extend(Path(x['path']) for x in receipt_doc['artifacts'])
        except (ValueError, OSError) as e:
            hard.append(f'store: {gate}: {e}')
    # The signed binary, plus its identity readback, must exist. A plist alone is insufficient.
    for key in ('binary', 'binaryIdentity'):
        p = Path(store_evidence).parent / store.get(key, '__missing__')
        if not p.is_file() or not p.stat().st_size:
            hard.append(f'store: missing {key}')
        else:
            refs.append(p.resolve())
            if key == 'binaryIdentity':
                binary_proof = json.loads(p.read_text())
                binary = Path(store_evidence).parent / store.get('binary', '__missing__')
                if binary_proof.get('identity') != ident or not binary.is_file() or binary_proof.get('sha256') != slipway.sha256(binary):
                    hard.append('signed binary identity/hash mismatch')
    try:
        binary = Path(store_evidence).parent / store.get('binary', '__missing__')
        with zipfile.ZipFile(binary) as z:
            names = [n for n in z.namelist() if re.fullmatch(r'Payload/[^/]+\.app/Info.plist', n)]
            if len(names) != 1: raise ValueError('IPA needs one root app plist')
            info = plistlib.loads(z.read(names[0]))
            actual = dict(zip(('bundleId', 'version', 'build'), (str(info.get(k, '')) for k in ('CFBundleIdentifier', 'CFBundleShortVersionString', 'CFBundleVersion'))))
            if actual != ident: raise ValueError('IPA embedded identity mismatch')
    except (OSError, ValueError, zipfile.BadZipFile) as e:
        hard.append(f'binary: {e}')
    if not isinstance(destinations, list) or not destinations or len(set(x['scope'] for x in destinations)) != len(destinations):
        raise ValueError('provide distinct exact destinations and scopes')
    for dest in destinations:
        if not all(dest.get(k) for k in ('scope', 'destination', 'action')):
            raise ValueError('destination needs scope, destination, action')
        for path in dest.get('artifacts', []):
            refs.append(Path(path).resolve())
    proofs = []
    for p in sorted(set(refs)):
        try: proofs.append(evidence(p))
        except (ValueError, OSError): hard.append(f'missing/empty artifact: {p}')
    result = {'schema': 1, 'identity': ident, 'createdAt': time.time(), 'appDir': str(app_dir),
              'expiresAt': expiry, 'status': 'blocked' if hard else 'review-with-limits' if limits else 'ready',
              'blockers': hard, 'testingLimits': sorted(set(limits)), 'reports': reports,
              'destinations': destinations, 'artifacts': proofs, 'directories': directories,
              'releaseBehavior': app.get('decisions', {}).get('releaseType')}
    result['digest'] = digest(result)
    return result


def verify_packet(path):
    p = json.loads(Path(path).read_text())
    h = p.pop('digest')
    if digest(p) != h:
        raise ValueError('packet changed after sealing')
    p['digest'] = h
    if p.get('expiresAt', 0) <= time.time():
        raise ValueError('packet store evidence expired; refresh before acting')
    for folder, members in p.get('directories', {}).items():
        actual = sorted(str(x.resolve()) for x in Path(folder).rglob('*') if x.is_file() and x.name not in ('.gitkeep', '.DS_Store'))
        if actual != members:
            raise ValueError('reviewed directory contents changed; make a new packet')
    if not intact(p['artifacts']):
        raise ValueError('reviewed artifact changed or disappeared; make a new packet')
    if p['blockers']:
        raise ValueError('packet has hard blockers')
    return p


def approve(packet_path, receipt_path, expected_identity=None):
    p = verify_packet(packet_path)
    if expected_identity is not None and p['identity'] != expected_identity:
        raise ValueError('job identity differs from approved packet')
    a = json.loads(Path(receipt_path).read_text())
    if not (a.get('packetDigest') == p['digest'] and a.get('statement') and a.get('source') and a.get('approvedAt')):
        raise ValueError('approval needs exact packet digest, actual statement, source, approvedAt')
    allowed = {d['scope'] for d in p['destinations']}
    if not a.get('scopes') or not set(a['scopes']) <= allowed:
        raise ValueError('approval scopes must be explicit packet destinations')
    if not set(p['testingLimits']) <= set(a.get('acceptedTestingLimits', [])):
        raise ValueError('approval does not accept all named testing limits')
    return a


def verify_approval(packet_path, receipt_path, scope, expected_identity=None):
    a = approve(packet_path, receipt_path, expected_identity)
    if scope not in a['scopes']:
        raise ValueError('this destination was not approved')
    return a


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    q = sub.add_parser('prepare'); q.add_argument('app', type=Path)
    q.add_argument('--store-evidence', type=Path, required=True)
    q.add_argument('--destinations', type=Path, required=True)
    q.add_argument('--out', type=Path, required=True)
    q = sub.add_parser('verify'); q.add_argument('packet', type=Path)
    q = sub.add_parser('approval'); q.add_argument('packet', type=Path); q.add_argument('receipt', type=Path)
    a = p.parse_args(argv)
    try:
        if a.cmd == 'prepare':
            result = packet(a.app, a.store_evidence, json.loads(a.destinations.read_text()))
            private_write(a.out, result)
            print(json.dumps({'status': result['status'], 'digest': result['digest'],
                              'blockers': result['blockers'], 'testingLimits': result['testingLimits']}, indent=2))
            return int(bool(result['blockers']))
        result = approve(a.packet, a.receipt) if a.cmd == 'approval' else verify_packet(a.packet)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, KeyError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
