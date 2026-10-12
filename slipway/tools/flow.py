#!/usr/bin/env python3
"""Durable local work queue. No daemon, shell interpolation, credentials, or implicit retries."""
from __future__ import annotations
import argparse
import concurrent.futures
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def evidence(path):
    p = Path(path).resolve()
    if not p.is_file() or not p.stat().st_size:
        raise ValueError(f'missing or empty evidence: {p}')
    return {'path': str(p), 'sha256': file_hash(p)}


def current_inputs(spec):
    return [evidence(p) for p in spec.get('inputs', [])]


def inputs_intact(spec, value):
    try:
        return value.get('inputs', []) == current_inputs(spec)
    except (ValueError, OSError):
        return False


def intact(items):
    return all(Path(x['path']).is_file() and file_hash(x['path']) == x['sha256'] for x in items)


def private_write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as f:
        os.fchmod(f.fileno(), 0o600)
        json.dump(value, f, indent=2)
        f.write('\n')


def validate(plan):
    jobs = plan['jobs']
    ids = [j['id'] for j in jobs]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError('job IDs must be unique and nonempty')
    for j in jobs:
        if j['kind'] not in ('human', 'local', 'read', 'external'):
            raise ValueError('invalid job kind')
        if not j['id'].replace('-', '').replace('_', '').isalnum():
            raise ValueError('unsafe job ID')
        if not j.get('action'):
            raise ValueError('each job needs an actionable next step')
        if j['kind'] != 'human' and not j.get('command'):
            raise ValueError('agent job needs an argv command')
        for key in ('command', 'reconcile'):
            if key in j and (not isinstance(j[key], list) or not all(isinstance(x, str) for x in j[key])):
                raise ValueError('commands must be argv arrays; use a reviewed wrapper for credentials')
        if j['kind'] == 'external' and j.get('effect') not in ('preparation', 'submission', 'publication'):
            raise ValueError('external job must classify its effect')
        if j.get('effect') in ('submission', 'publication') and not j.get('packet'):
            raise ValueError('submission/publication job needs a sealed release packet')
        if j['kind'] == 'external' and not all(j.get(k) for k in ('scope', 'reconcile', 'identity')):
            raise ValueError('external job needs exact scope, identity, and readback command')
        if j.get('network') and not j.get('scope'):
            raise ValueError('network read needs explicit scoped authorization too')
        if set(j.get('deps', [])) - set(ids):
            raise ValueError('unknown dependency')
    seen = set()
    while len(seen) < len(ids):
        add = {j['id'] for j in jobs if set(j.get('deps', [])) <= seen} - seen
        if not add:
            raise ValueError('dependency cycle')
        seen |= add


@contextlib.contextmanager
def connection(*args, **kwargs):
    c = sqlite3.connect(*args, **kwargs)
    try:
        with c:
            yield c
    finally:
        c.close()


class Ledger:
    def __init__(self, directory):
        self.root = Path(directory).resolve()
        self.db = self.root / 'state.sqlite3'

    def init(self, plan):
        validate(plan)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        with connection(self.db) as c:
            c.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, body TEXT NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, at REAL, body TEXT)')
            old = c.execute('SELECT body FROM state WHERE id=1').fetchone()
            if old:
                if json.loads(old[0])['planDigest'] != digest(plan):
                    raise ValueError('plan is immutable; use a new release directory')
                return
            s = {'plan': plan, 'planDigest': digest(plan), 'worker': None, 'jobs': {}}
            for j in plan['jobs']:
                s['jobs'][j['id']] = {'state': 'waiting' if j['kind'] == 'human' else 'queued',
                                      'attempts': 0, 'evidence': [], 'intent': False, 'reason': j['action']}
            c.execute('INSERT INTO state VALUES (1, ?)', (json.dumps(s),))
        os.chmod(self.db, 0o600)

    def read(self):
        # mode=ro: status never creates or mutates state.
        with connection(f'{self.db.as_uri()}?mode=ro', uri=True) as c:
            return json.loads(c.execute('SELECT body FROM state WHERE id=1').fetchone()[0])

    def change(self, event, fn):
        with connection(self.db, timeout=30) as c:
            c.execute('BEGIN IMMEDIATE')
            s = json.loads(c.execute('SELECT body FROM state WHERE id=1').fetchone()[0])
            fn(s)
            c.execute('UPDATE state SET body=? WHERE id=1', (json.dumps(s),))
            c.execute('INSERT INTO events(at,body) VALUES (?,?)', (time.time(), json.dumps(event)))

    @contextlib.contextmanager
    def lock(self):
        with (self.root / 'worker.lock').open('a') as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError('a worker already owns this release')
            try:
                yield
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def worker_alive(self):
        p = self.root / 'worker.lock'
        if not p.exists():
            return False
        with p.open('r') as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(f, fcntl.LOCK_UN)
                return False
            except BlockingIOError:
                return True

    def status(self):
        s = self.read()
        alive = self.worker_alive()
        rows = []
        for j in s['plan']['jobs']:
            v = dict(s['jobs'][j['id']])
            if v['state'] == 'running' and not alive:
                v.update(state='blocked', reason='worker stopped; run to reconcile, never assume success')
            if v['state'] == 'complete' and (not intact(v['evidence']) or not inputs_intact(j, v)):
                v.update(state='blocked', reason='completed evidence changed or disappeared')
            if v['state'] == 'queued':
                deps = [d for d in j.get('deps', []) if s['jobs'][d]['state'] != 'complete']
                v.update(state='waiting', reason='dependencies: ' + ', '.join(deps) if deps else 'eligible for running worker' if alive else 'no worker; run to continue')
            rows.append({'id': j['id'], 'owner': 'human' if j['kind'] == 'human' else 'agent', **v})
        by_id = {row['id']: row for row in rows}
        for _ in rows:  # propagate failed prerequisites even when the plan is not topologically ordered
            for spec in s['plan']['jobs']:
                row = by_id[spec['id']]
                failed = [d for d in spec.get('deps', []) if by_id[d]['state'] == 'blocked']
                if failed and row['state'] in ('waiting', 'complete'):
                    row.update(state='blocked', reason='blocked prerequisites: ' + ', '.join(failed))
        return {'worker': s['worker'] if alive else None, 'running': alive, 'jobs': rows,
                'planDigest': s['planDigest']}

    def answer(self, job, receipt):
        proof = evidence(receipt)
        def update(s):
            spec = next(j for j in s['plan']['jobs'] if j['id'] == job)
            if spec['kind'] != 'human':
                raise ValueError('answer is only for human tasks')
            v = s['jobs'][job]
            if v['state'] == 'complete':
                if v['evidence'] == [proof]:
                    return
                raise ValueError('answer already recorded; create new release for changed answers')
            v.update(state='complete', evidence=[proof], reason='answer recorded; see receipt')
        self.change({'answer': job, 'receipt': proof}, update)

    def retry(self, job, changed):
        proof = evidence(changed)
        with self.lock():
            def update(s):
                v = s['jobs'][job]
                spec = next(j for j in s['plan']['jobs'] if j['id'] == job)
                if spec['kind'] in ('external', 'human') or v['state'] != 'blocked':
                    raise ValueError('only failed local/read jobs can retry; external intent must reconcile')
                if v.get('childPid'):
                    try:
                        os.kill(v['childPid'], 0)
                    except ProcessLookupError:
                        pass
                    else:
                        raise ValueError('previous child process still exists; inspect it before retry')
                if proof['sha256'] in v.get('retryEvidence', []):
                    raise ValueError('same diagnostic already retried; need changed conditions')
                v.setdefault('retryEvidence', []).append(proof['sha256'])
                v.update(state='queued', reason='changed conditions recorded', changed=proof)
            self.change({'retry': job, 'changed': proof}, update)

    def authorized(self, spec, authorization, mutation=False):
        if spec['kind'] != 'external' and not spec.get('network'):
            return True
        s = self.read()
        a = authorization or {}
        if not (a.get('planDigest') == s['planDigest'] and a.get('statement') and a.get('source')
                and spec['scope'] in a.get('scopes', [])):
            return False
        if spec.get('packet') and mutation:
            from release_packet import verify_approval
            verify_approval(Path(spec['packet']), Path(a['releaseApproval']), spec['scope'], spec['identity'])
        return True

    def command(self, argv, job, label, timeout):
        # Never inherit provider credentials from an agent session. Wrappers load a vault themselves.
        env = {k: v for k, v in os.environ.items() if k in ('PATH', 'HOME', 'USER', 'LOGNAME', 'TMPDIR', 'LANG', 'LC_ALL', 'DEVELOPER_DIR')}
        with self.lock_file(job, label) as log:
            try:
                p = subprocess.Popen(argv, cwd=self.read()['plan'].get('cwd'), env=env,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                                     close_fds=True)
                self.change({'child': job, 'pid': p.pid}, lambda s: s['jobs'][job].update(childPid=p.pid))
                try:
                    code = p.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    import signal
                    os.killpg(p.pid, signal.SIGTERM)
                    try:
                        p.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(p.pid, signal.SIGKILL)
                        p.wait()
                    code = 124
                self.change({'childExited': job}, lambda s: s['jobs'][job].update(childPid=None))
            except OSError:
                code = 127
        return code, self.root / f'{job}.{label}.log'

    @contextlib.contextmanager
    def lock_file(self, job, label):
        # IDs are never used as arbitrary paths.
        if not job.replace('-', '').replace('_', '').isalnum():
            raise ValueError('job ID must be alphanumeric, dash or underscore')
        with os.fdopen(os.open(self.root / f'{job}.{label}.log', os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as f:
            yield f

    def probe(self, spec):
        code, path = self.command(spec['reconcile'], spec['id'], 'readback', spec.get('timeout', 120))
        try:
            data = json.loads(path.read_text()) if code == 0 else {}
            if data.get('identity') != spec['identity']:
                return 'unknown', [evidence(path)] if path.stat().st_size else []
            state = data.get('state', 'unknown')
            if state not in ('absent', 'pending', 'complete', 'blocked'):
                state = 'unknown'
            # Receipt is copied to an immutable attempt path before the next probe overwrites output.
            dest = self.root / f"{spec['id']}.receipt-{time.time_ns()}.json"
            private_write(dest, data)
            return state, [evidence(dest)]
        except (ValueError, OSError):
            return 'unknown', []

    def execute(self, spec, authorization):
        job = spec['id']
        def mark(state, reason, proofs=None):
            def update(s):
                s['jobs'][job].update(state=state, reason=reason)
                if proofs is not None:
                    s['jobs'][job]['evidence'] = proofs
                if state == 'complete':
                    s['jobs'][job]['inputs'] = current_inputs(spec)
            self.change({'job': job, 'state': state, 'reason': reason}, update)
        try:
            mark('running', 'checking authorization and readback')
            starting_inputs = current_inputs(spec)
            if not self.authorized(spec, authorization):
                mark('waiting', 'missing exact scope authorization: ' + spec.get('scope', ''))
                return
            old = self.read()['jobs'][job]
            if spec['kind'] == 'external':
                state, proofs = self.probe(spec)
                if state == 'complete':
                    mark('complete', 'remote state reconciled', proofs)
                    return
                if state == 'pending':
                    self.change({'observedPending': job}, lambda s: s['jobs'][job].update(intent=True))
                    mark('waiting', 'remote processing; next run reads back only', proofs)
                    return
                if old['intent'] or state != 'absent':
                    mark('blocked', 'uncertain external outcome; reconcile only, no repeat write', proofs)
                    return
            if not self.authorized(spec, authorization, mutation=True):
                mark('waiting', 'authorization no longer valid')
                return
            def start(s):
                s['jobs'][job].update(state='running', reason='worker executing', attempts=old['attempts'] + 1,
                                      intent=spec['kind'] == 'external')
            self.change({'job': job, 'intent': spec['kind'] == 'external'}, start)
            code, log = self.command(spec['command'], job, 'attempt-' + str(old['attempts'] + 1), spec.get('timeout', 120))
            if spec['kind'] == 'external':
                state, proofs = self.probe(spec)
                mark('complete' if state == 'complete' else 'waiting' if state == 'pending' else 'blocked',
                     'remote state reconciled' if state == 'complete' else 'remote pending or ambiguous; readback only', proofs)
            elif code == 0:
                if current_inputs(spec) != starting_inputs:
                    raise ValueError('inputs changed during execution; outputs need re-verification')
                paths = spec.get('artifacts', [])
                if not paths:
                    raise ValueError('successful command needs at least one artifact')
                mark('complete', 'command and artifacts verified', [evidence(p) for p in paths])
            else:
                mark('blocked', f'command exit {code}; inspect private log; retry requires changed-condition receipt')
        except Exception as e:
            mark('blocked', f'{type(e).__name__}: {e}')

    def run(self, authorization=None, workers=2):
        with self.lock():
            def recover(s):
                s['worker'] = {'pid': os.getpid(), 'startedAt': time.time()}
                if authorization:
                    s.setdefault('authorizations', {})[digest(authorization)] = authorization
                for spec in s['plan']['jobs']:
                    v = s['jobs'][spec['id']]
                    if v['state'] == 'running':
                        # Orphan local processes might still exist: do not automatically rerun them either.
                        v.update(state='blocked', reason='interrupted attempt; inspect artifacts/process before explicit retry')
                    if v['state'] == 'complete' and (not intact(v['evidence']) or not inputs_intact(spec, v)):
                        v.update(state='blocked', reason='evidence changed; explicit repair required')
            self.change({'worker': 'start'}, recover)
            attempted = set()
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                    active = {}
                    while True:
                        s = self.read()
                        for j in s['plan']['jobs']:
                            v = s['jobs'][j['id']]
                            if j['id'] in attempted or j['kind'] == 'human' or v['state'] == 'complete':
                                continue
                            if v['state'] == 'blocked' and j['kind'] != 'external':
                                continue
                            if any(s['jobs'][d]['state'] != 'complete' for d in j.get('deps', [])):
                                continue
                            if len(active) >= workers:
                                break
                            attempted.add(j['id'])
                            active[pool.submit(self.execute, j, authorization)] = j['id']
                        if not active:
                            break
                        done, _ = concurrent.futures.wait(active, return_when=concurrent.futures.FIRST_COMPLETED)
                        for f in done:
                            f.result()
                            del active[f]
            finally:
                self.change({'worker': 'stop'}, lambda s: s.update(worker=None))
        return self.status()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state', type=Path, required=True, help='private directory, outside source')
    sub = p.add_subparsers(dest='cmd', required=True)
    q = sub.add_parser('init'); q.add_argument('plan', type=Path)
    sub.add_parser('status')
    q = sub.add_parser('run'); q.add_argument('--authorization', type=Path); q.add_argument('--workers', type=int, choices=range(1, 5), default=2)
    q = sub.add_parser('answer'); q.add_argument('job'); q.add_argument('receipt', type=Path)
    q = sub.add_parser('retry'); q.add_argument('job'); q.add_argument('--changed', type=Path, required=True)
    a = p.parse_args(argv)
    ledger = Ledger(a.state)
    try:
        if a.cmd == 'init': ledger.init(json.loads(a.plan.read_text()))
        elif a.cmd == 'run': ledger.run(json.loads(a.authorization.read_text()) if a.authorization else None, a.workers)
        elif a.cmd == 'answer': ledger.answer(a.job, a.receipt)
        elif a.cmd == 'retry': ledger.retry(a.job, a.changed)
        status = ledger.status()
        print(json.dumps(status, indent=2))
        if a.cmd == 'run':
            return 1 if any(j['state'] == 'blocked' for j in status['jobs']) else 2 if any(j['state'] != 'complete' for j in status['jobs']) else 0
        return 0
    except (ValueError, OSError, sqlite3.Error, KeyError) as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
