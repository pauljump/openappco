#!/usr/bin/env python3
"""One complete, private connection and phone handoff inventory. Offline unless explicitly enabled."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from flow import digest, evidence, intact, private_write

REQUIRED = {
    'toolchain': 'Verify selected Xcode and local build tools.',
    'api': 'Verify API access through a vault wrapper; never paste a key here.',
    'webSession': 'Check the existing browser session on the build Mac; sign in only if expired.',
    'signing': 'Run a disposable signing probe using the existing identity and keychain.',
    'phone': 'Identify the intended phone, pairing, Developer Mode and current reachability.',
    'capture': 'Test a supported recording route and inspect a short capture.',
    'capturePermission': 'Verify permission for the actual capture process, scope and destination.',
    'agreements': 'Check current account agreements and required declarations.',
    'hosting': 'Confirm exact support/privacy destinations and public contact.',
    'reviewContact': 'Verify the private reviewer contact is available through the vault.',
    'publication': 'Identify Apple and every intended public repository/site destination.',
}
PHONE_ACTIONS = {
    'launchFromHomeScreen': 'Launch from the Home Screen and confirm a usable start screen.',
    'coreFlow': 'Perform the main job described in the brief and check the expected output.',
    'relaunchKeepsData': 'Create disposable test data, force-quit, reopen, and verify the saved state.',
    'voiceOverCoreFlow': 'Settings > Accessibility > VoiceOver: test the main flow, then restore the original setting.',
    'largestTextSize': 'Settings > Accessibility > Display & Text Size > Larger Text: test the largest accessibility size and restore the original setting.',
    'soundHaptics': 'Physically confirm speaker output and vibration where the app promises them.',
    'lockResume': 'Lock/unlock and confirm the intended pause/resume behavior.',
    'interruptionRecovers': 'Trigger a test alarm or call and confirm safe interruption and recovery.',
    'permissionDenied': 'Deny each requested app permission and confirm the documented fallback.',
    'recording': 'Using clean demo data, record Home Screen launch and the main flow; inspect video/audio, keep under three minutes, and transfer to the private release evidence folder.'}

PHONE_CHECKS = ['launchFromHomeScreen', 'coreFlow', 'relaunchKeepsData', 'voiceOverCoreFlow',
                'largestTextSize', 'soundHaptics', 'lockResume', 'interruptionRecovers', 'permissionDenied', 'recording']


def local_probe(name):
    import slipway
    if name == 'toolchain':
        code, out = slipway.run_cmd(['xcodebuild', '-version'])
        return {'state': 'verified' if code == 0 and 'Xcode' in out else 'blocked'}
    if name == 'phone':
        phones = slipway.list_phones()
        if not phones or len(phones) != 1:
            return {'state': 'unknown'}
        phone = phones[0]
        return {'state': 'unknown', 'paired': phone['paired'], 'developerMode': phone['devMode'],
                'transport': phone['transport'], 'reachable': None}
    if name == 'capture':
        code, out = slipway.run_cmd(['xcrun', 'devicectl', 'device', 'capture', '--help'])
        return {'state': 'unknown' if code == 0 and 'screen-record' in out else 'unsupported',
                'route': 'devicectl' if code == 0 and 'screen-record' in out else 'on-phone'}
    raise ValueError('unknown local probe')


def initialize(path, mac, phone):
    if Path(path).exists(): raise ValueError('profile already exists; preserving existing configuration')
    if not mac or not phone: raise ValueError('name the intended Mac and phone with --mac and --phone')
    template = Path(__file__).resolve().parents[1] / 'examples/connections.json'
    profile = json.loads(template.read_text())
    profile.update(mac=mac, phone=phone)
    for name in ('toolchain', 'phone', 'capture'):
        profile['connections'][name] = {'probe': [sys.executable, str(Path(__file__).resolve()), '--probe', name]}
    private_write(path, profile)
    return profile


def load_profile(path):
    path = Path(path).resolve()
    if path.stat().st_mode & 0o077:
        raise ValueError('private profile must be mode 600; do not put credentials in it')
    profile = json.loads(path.read_text())
    if not profile.get('mac') or not profile.get('phone') or any('[' in profile[k] for k in ('mac', 'phone')):
        raise ValueError('name the intended Mac and phone in the private profile')
    return profile


def inventory(profile, previous=None, online=False):
    previous = previous or {}
    result = {'schema': 1, 'checkedAt': time.time(), 'mac': profile['mac'], 'phone': profile['phone'], 'connections': {}}
    for name, action in REQUIRED.items():
        item = profile.get('connections', {}).get(name, {})
        fingerprint = digest({'mac': profile['mac'], 'phone': profile['phone'], 'config': item})
        old = previous.get('connections', {}).get(name, {})
        row = {'state': 'unknown', 'owner': 'agent', 'action': action, 'fingerprint': fingerprint,
               'details': {k: item[k] for k in ('process', 'scope', 'destination', 'route', 'priorConsentSource') if k in item}}
        receipt = item.get('receipt')
        if receipt:
            try:
                doc = json.loads(Path(receipt).read_text())
                proof = evidence(receipt)
                if doc.get('fingerprint') != fingerprint or doc.get('expiresAt', 0) <= time.time():
                    row.update(state='waiting', owner='human', action='Receipt expired or scope changed. ' + action)
                elif doc.get('state') == 'verified' and doc.get('observedAt') and doc.get('source'):
                    row.update(state='verified', evidence=[proof], observedAt=doc['observedAt'], expiresAt=doc['expiresAt'])
                    row['details'] = {k: item[k] for k in ('process', 'scope', 'destination', 'route') if k in item}
            except (OSError, ValueError):
                row['action'] = 'Receipt unavailable. ' + action
        elif (old.get('state') == 'verified' and old.get('fingerprint') == fingerprint
              and old.get('expiresAt', 0) > time.time() and intact(old.get('evidence', [])) and old.get('evidence')):
            row = old
        if item.get('probe'):
            if item.get('network') and not online:
                row.update(state='waiting', action='Network probe requires current authorization. ' + action)
            else:
                # Probe must emit ONLY the normalized nonsecret protocol, not raw provider output.
                try:
                    env = {k: v for k, v in os.environ.items() if k in ('PATH', 'HOME', 'USER', 'TMPDIR', 'LANG', 'DEVELOPER_DIR')}
                    p = subprocess.run(item['probe'], capture_output=True, text=True, timeout=20, env=env)
                    doc = json.loads(p.stdout) if p.returncode == 0 else {}
                    state = doc.get('state')
                    if state not in ('verified', 'waiting', 'blocked', 'unsupported'):
                        state = 'unknown'
                    row.update(state=state, owner='human' if state == 'waiting' else 'agent')
                    # Whitelist protocol fields; never copy provider error output or tokens.
                    row['details'] = {k: doc[k] for k in ('transport', 'reachable', 'paired', 'developerMode', 'route', 'process', 'scope', 'destination') if k in doc}
                    if state == 'verified':
                        row['expiresAt'] = time.time() + min(item.get('ttlSeconds', 300), 86400)
                except (OSError, ValueError, subprocess.TimeoutExpired):
                    row.update(state='unknown', action='Probe failed; inspect locally without exposing credentials. ' + action)
        result['connections'][name] = row
    return result


def handoff(inv, app=None, answers=None):
    app, answers = app or {}, answers or {}
    lines = [f"# Release handoff — {inv['phone']} / {inv['mac']}", '',
             'Complete inventory; unknown means unverified. No permission is inferred from this checklist.', '']
    ident = app.get('app', {})
    submitted = app.get('apple', {}).get('state') in ('WAITING_FOR_REVIEW', 'IN_REVIEW')
    if ident:
        lines += [f"Exact release: {ident.get('bundleId')} {ident.get('version')} build {ident.get('build')}.", '']
    if submitted:
        lines += ['Already submitted according to saved release state. This is an evidence inventory, not a new submission or approval request.', '']
    for name, row in inv['connections'].items():
        mark = 'x' if row['state'] == 'verified' else ' '
        lines.append(f"- [{mark}] {name} ({row['state']}; {row['owner']}): {row['action']}")
        if row.get('details'):
            lines.append('  ' + '; '.join(f'{k}: {v}' for k, v in row['details'].items()))
    phone = inv['connections']['phone'].get('details', {})
    capture = inv['connections']['capture'].get('details', {})
    lines += ['', '## Connection decision', '']
    if phone.get('reachable') is True and phone.get('paired') is True:
        lines.append(f"Use the verified {phone.get('transport', 'existing')} connection to {inv['phone']}. No cable request for installation.")
    elif phone.get('paired') is False:
        lines.append(f"Pair {inv['phone']} with {inv['mac']}; if the detected pairing route needs USB, connect a data cable directly between those two devices for trust/pairing.")
    else:
        lines.append('Reachability is unverified. Run device discovery and a supported connection probe before choosing a cable route.')
    if capture.get('route') == 'quicktime-usb':
        lines.append(f"Recording route requires USB: connect {inv['phone']} directly to {inv['mac']} with a data cable for QuickTime video input; a charger or another Mac does not provide this input.")
    lines += ['', '## Phone session — report all remaining results together', '']
    for check in PHONE_CHECKS:
        if check == 'permissionDenied' and not ident.get('permissions'): continue
        if check == 'soundHaptics' and not (ident.get('audio') or ident.get('haptics')): continue
        answer = answers.get(check, {})
        same = answer.get('identity') == {k: str(ident.get(k, '')) for k in ('bundleId', 'version', 'build')}
        valid = same and answer.get('result') == 'pass' and answer.get('evidence') and intact(answer['evidence'])
        result = 'recorded; do not repeat' if valid else 'accepted testing limit; still unverified' if check in answers.get('acceptedTestingLimits', []) else 'pending; record observed result and receipt'
        lines.append(f"- [{'x' if valid else ' '}] {check}: {result}")
        if not valid and check not in answers.get('acceptedTestingLimits', []):
            lines.append('  ' + PHONE_ACTIONS[check])
    lines += ['', 'Preserve the existing Apple submission and approval. Only uncovered publication scope remains pending.' if submitted else 'Final decision comes after the exact-build packet: named testing limits, Apple submission, and each public destination.']
    return '\n'.join(lines) + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('profile', type=Path, nargs='?'); p.add_argument('--out', type=Path)
    p.add_argument('--init', action='store_true'); p.add_argument('--mac'); p.add_argument('--phone')
    p.add_argument('--probe', choices=['toolchain', 'phone', 'capture'])
    p.add_argument('--app', type=Path); p.add_argument('--answers', type=Path)
    p.add_argument('--online-authorized', action='store_true', help='only with current permission for these network probes')
    a = p.parse_args(argv)
    try:
        if a.probe:
            print(json.dumps(local_probe(a.probe))); return 0
        if not a.profile: raise ValueError('private profile path is required')
        if a.init:
            initialize(a.profile, a.mac, a.phone)
            print('Private profile created. Run the inventory to see all remaining connections.'); return 0
        if not a.out: raise ValueError('--out is required for an inventory')
        profile = load_profile(a.profile)
        previous = json.loads(a.out.read_text()) if a.out.exists() else None
        inv = inventory(profile, previous, a.online_authorized)
        private_write(a.out, inv)
        app = json.loads(a.app.read_text()) if a.app else None
        answers = json.loads(a.answers.read_text()) if a.answers else None
        print(handoff(inv, app, answers))
        return 0
    except (OSError, ValueError) as e:
        print(str(e), file=sys.stderr); return 1


if __name__ == '__main__':
    sys.exit(main())
