# Run a release without losing your place

Use Python 3.10+ and the standard library. The tools work locally; they do not install a daemon,
create credentials, grant permissions, or authorize actions. The existing five phases and design
choices stay in `app.json`. A private SQLite ledger records execution, evidence and recovery.

## First clone

Run the offline rehearsal before connecting an account:

```bash
python3 tools/rehearse.py --out /tmp/slipway-rehearsal.json
```

It creates a fresh app and connection profile, proves that an incomplete app blocks, runs an actual
worker through a human wait and restart, then runs the failure tests. Provider/device responses in
the tests are synthetic; this does not prove access to your Apple account or phone.

Create your private profile with the intended devices (this only writes a mode-600 local file):

```bash
python3 tools/connections.py /private/path/connections.json --init --mac "Build Mac" --phone "Test iPhone"
```

This seeds read-only toolchain, device-discovery and recording-feature probes. It refuses to replace
an existing profile. Put credentials in your existing secret store, never in this file. For each connection,
configure a reviewed `probe` argv array or a `receipt` path. A probe runs without a shell and must
print a small JSON object with `state` (`verified`, `waiting`, `blocked`, `unsupported`, `unknown`).
Optional details: `paired`, `developerMode`, `reachable`, `transport`, `route`, `process`, `scope`,
`destination`. Never output tokens or provider error bodies. Network probes require `network: true`;
run them only with current authorization and `--online-authorized`.

```bash
python3 tools/connections.py /private/path/connections.json \
  --out /private/path/inventory.json --app /apps/counter/app.json \
  --answers /private/path/phone-answers.json > /private/path/user-handoff.md
```

Omit `--answers` initially. The output inventories toolchain, API, browser session, signing, phone,
capture, capture-process permission, agreements, hosting, review contact and publication. Missing
configuration stays unknown; the checklist names the next action. A CLI feature or discovered
transport is not a verified device operation. `doctor` is a diagnostic, not release readiness.

A manually observed connection receipt has `fingerprint` (from the first inventory), `state`,
`source`, `observedAt`, and `expiresAt` (Unix seconds). Scope changes or expiration invalidate it.
Use short expiration for sessions and reachability. A receipt records an observation, not permission
for new access. Existing consent is preserved at its original source; check the current capability
separately. Configure capture process/scope/destination in the profile before asking for new access.

Phone answers are keyed by check name, with `identity: {bundleId, version, build}`, `result: "pass"`,
and `evidence: [{path, sha256}]`. The generated checklist carries forward only intact, same-build
answers. It identifies both devices and the reason when a chosen route actually requires USB.
For detailed test steps, use [the phone phase](3-on-my-phone.md).

## Execute independent work

A plan is an immutable JSON object with `cwd`, optional `identity`, and `jobs`. Each job has `id`,
`kind`, `action`, optional `deps`, and an argv `command` for agent work. `local` and `read` jobs
require nonempty output `artifacts`; declare source `inputs` so edited inputs invalidate completion.
Use existing build wrappers and simulator leases. A `human` job needs no command and waits for a
receipt. Make dependencies reflect actual requirements: archive/upload does not depend on a video;
submission does. A local build may depend on an approved idea/design decision.

```json
{"jobs": [
  {"id":"phone", "kind":"human", "action":"Complete the remaining phone checklist"},
  {"id":"assets", "kind":"local", "action":"Prepare store assets",
   "command":["python3","/apps/counter/scripts/assets.py"],
   "inputs":["/apps/counter/app.json"], "artifacts":["/private/path/assets-report.json"]}
]}
```

```bash
python3 tools/flow.py --state /private/path/release init /private/path/plan.json
python3 tools/flow.py --state /private/path/release run
python3 tools/flow.py --state /private/path/release status
python3 tools/flow.py --state /private/path/release answer phone /private/path/answer.json
python3 tools/flow.py --state /private/path/release run
```

`run` is a foreground worker with up to two independent commands at once (`--workers 1..4`). It
returns when nothing else can run (exit 0: all complete, 1: blocked work, 2: waiting work). No background work remains implied. A held OS lock establishes
worker liveness; a saved PID alone does not. `status` is read-only. Restarting preserves completed
jobs and human answers. Logs, timestamps, attempts and events stay in the mode-700 state directory.
Use the same directory for the same release; creating another ledger defeats duplicate protection.

Failed local work blocks until changed conditions are recorded:

```bash
python3 tools/flow.py --state /private/path/release retry signing --changed /private/path/probe.json
```

A still-existing child process prevents retry. The same changed-condition receipt cannot be reused.
An interrupted local command is not automatically repeated. Inspect artifacts/processes first.

## External actions and uncertainty

An `external` job additionally needs an exact `scope`, `identity`, read-only `reconcile` argv, and
`effect` (`preparation`, `submission`, or `publication`). Submission/publication effects require a sealed packet.
The adapter emits `{state, identity}`; states are `absent`, `pending`, `complete`, `blocked`, or
`unknown`. `complete` must mean the actual resulting remote state for that exact identity. A queued
upload with no known result is `pending`, not complete. Adapter correctness is a separate test duty.

The runner reads before writing, commits intent before the command, then reads back. Only an
unambiguous `absent` before any intent permits a write. Once intent exists, all subsequent runs
only reconcile. Even a later `absent` does not automatically repeat an uncertain create. Diagnose
and resolve the provider state; do not create a second ledger to retry. Polling is once per run.

All external jobs and `network: true` reads require a private authorization receipt supplied with
`run --authorization PATH`. It contains `planDigest` (from init/status), `scopes`, the actual user
`statement`, and its `source`. This is an audit record of permission already obtained, not a way to
create permission. Paid quota, access and publication boundaries remain with the operator/agent.
Commands and adapters are trusted local code, not sandboxed plugins. Do not load unreviewed plans.
Commands must load secrets through a vault wrapper; ambient provider variables are not forwarded.

## One exact-build final decision

```bash
python3 tools/release_packet.py prepare /apps/counter \
  --store-evidence /private/path/store-evidence.json \
  --destinations /private/path/destinations.json --out /private/path/packet.json
```

This runs build, phone and submission checks, reads the IPA's embedded identity, and hashes sources,
metadata, screenshots, movie, binary and raw receipts. The store manifest has `identity`, `binary`,
`binaryIdentity` (a JSON receipt with `identity` and binary `sha256`), and `checks` for `signing`,
`processing`, `attachedBuild`, `screenshots`, `privacy`, `agreements`, `urls`, `reviewVideo`,
`reviewNotes`, `inspection`. Each check needs `passed: true`, `observedAt`, bounded `expiresAt` (at
most 24 hours ahead), `receipt`, and its `sha256`. Each receipt binds `identity`, `gate`,
`result: "pass"`, observer/tool `source`, and `artifacts: [{path, sha256}]` pointing to the actual
raw evidence. Human/browser inspection must be an honest attestation; file hashing cannot see a UI.

Destinations are an array of `{scope, destination, action, artifacts?}`. Include Apple and every
public site/repository operation. Public assets are hashed too. Nothing publishes while preparing.
Only unperformed named phone checks can be disclosed as testing limits; actual failures, missing
video/binary, stale receipts and store blockers cannot be waived by this tool. Output is `blocked`,
`review-with-limits`, or `ready`. Scoped `slipway.py check` success is only `CHECKS PASS`.

An approval receipt contains `packetDigest`, actual `statement`, `source`, `approvedAt`, `scopes`,
and `acceptedTestingLimits`. Keep the user wording and original message reference. Verify it with:

```bash
python3 tools/release_packet.py approval /private/path/packet.json /private/path/approval.json
```

Submission/publication jobs name their sealed `packet` path. Their run authorization additionally
names `releaseApproval`. The runner checks it before a write. Authorized readback can still reconcile an earlier action
after packet evidence expires; expiration never permits another write. Partial approval runs only covered
scopes; other destinations remain waiting. Artifact changes, added source files, expiration or
new build identity invalidate approval. Testing limits remain unverified in the original evidence.
The private adapter must verify Apple's resulting state and exact attached build. A successful
command exit is insufficient.
