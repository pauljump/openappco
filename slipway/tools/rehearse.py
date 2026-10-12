#!/usr/bin/env python3
"""Offline onboarding and recovery rehearsal. All accounts/devices/provider results are synthetic."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from connections import inventory, load_profile, handoff, REQUIRED
from flow import private_write, Ledger


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    repo = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='slipway-onboarding-') as tmp:
        root = Path(tmp)
        profile = json.loads((repo / 'examples/connections.json').read_text())
        profile.update(mac='Rehearsal Mac', phone='Rehearsal iPhone')
        private_write(root / 'connections.json', profile)
        inv = inventory(load_profile(root / 'connections.json'))
        assert len(inv['connections']) == len(REQUIRED)
        assert all(v['state'] != 'verified' for v in inv['connections'].values())
        new = subprocess.run([sys.executable, str(repo / 'tools/slipway.py'), 'new', str(root / 'app')], capture_output=True, text=True)
        assert new.returncode == 0
        check = subprocess.run([sys.executable, str(repo / 'tools/slipway.py'), 'check', str(root / 'app'), '--json'], capture_output=True, text=True)
        assert check.returncode == 1
        output = root / 'independent.txt'
        plan = {'jobs': [
            {'id': 'phone', 'kind': 'human', 'action': 'Provide one complete phone checklist'},
            {'id': 'assets', 'kind': 'local', 'action': 'Prepare independent assets',
             'command': [sys.executable, '-c', f'from pathlib import Path; Path({str(output)!r}).write_text("prepared")'], 'artifacts': [str(output)]}]}
        ledger = Ledger(root / 'state'); ledger.init(plan); ledger.run()
        Ledger(root / 'state').run()
        assert ledger.read()['jobs']['assets']['attempts'] == 1
        assert ledger.read()['jobs']['phone']['state'] == 'waiting'
        assert not ledger.status()['running']
        suite = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=repo, capture_output=True, text=True)
        report = {'scope': 'offline; synthetic accounts, phone and provider, actual local processes/SQLite/files',
                  'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
                  'freshProfileConnections': len(REQUIRED), 'freshAppBlocks': True,
                  'independentJobAttemptsAcrossRestart': 1, 'humanStillWaiting': True,
                  'workerRunningAfterReturn': False, 'testExit': suite.returncode,
                  'tests': suite.stdout + suite.stderr, 'handoff': handoff(inv),
                  'networkCalls': 0, 'newAccessGrants': 0, 'publications': 0}
        private_write(a.out, report)
        print(json.dumps({k: v for k, v in report.items() if k not in ('tests', 'handoff')}, indent=2))
        return suite.returncode


if __name__ == '__main__': sys.exit(main())
