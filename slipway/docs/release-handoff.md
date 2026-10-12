# One complete release handoff

Before asking someone to pick up their phone, identify everything they will need to do. The agent
owns builds, uploads, metadata, screenshots, evidence inspection and tracker preparation. The user
owns product decisions, authentication the agent cannot complete, physical perception checks and
final release approval. Recording belongs to the agent when its authorized tools support it:
iPhone Mirroring first, a cable only as a fallback, and the user's own phone recorder only when the
app's sound is the point or every agent route has failed after a real state change.

Execution and receipt formats live in [durable work](durable-work.md). Generate the inventory
and checklist with `connections.py`; record jobs with `flow.py`; seal the final review with
`release_packet.py`. This page explains ownership; it does not add a second state record.

## Inventory first

Run `doctor`, `check <app> --only phone`, and `check <app> --only submit`. Failures define the work;
they are not a reason to ask one question at a time. Fill
[user-handoff.md](../templates/app/user-handoff.md) with owners, actions, expected results and
receipts. Ask for all remaining human results in one numbered reply.

Include pairing/transport, signing, capture route and permissions, existing account sessions,
core flow, force-quit persistence, VoiceOver, largest text, sound/haptics, lock behavior,
call/alarm interruption and denied app permissions where applicable. Detailed checks are in
[phase 3](3-on-my-phone.md). Complete remotely verifiable work before handing it to the user.
Save original accessibility settings and restore them after testing.

## Permissions without surprises

Inspect existing grants and sessions. Identify the actual responsible recording process, access
scope and destination. Do not assume a terminal application's grant covers a remote command.
Do not grant remote-shell recording access silently. Broader access needs explanation and consent.

Put every foreseeable request in the first handoff, in the same numbered reply as the phone checks:
sign-in (only after checking the live session), and every confirmation Apple will ask the user for
at action time. Don't hold them back until the moment you need them; on one app that turned into
three separate approval requests mid-release. Existing exact-action approvals persist; new security
scope, legal confirmations or authentication can still require a separate prompt. Explain
predictable exceptions upfront. Never promise zero human interaction or bypass a denial.
Retry a failed route only after relevant state changes or a bounded diagnostic finds a supported fix.

## Continue independent work

Prepare and upload the verified binary while human checks or video are pending; do not submit yet.
Use clean demo data. Do not export personal history without specific consent. Inspect the actual
movie, duration and audio, then verify attachment completion. A path or upload commitment is not
proof of usable evidence. Preserve exact build identity throughout.

Record completed user answers. Carry forward unaffected checks only with an explanation. If a new
failure requires follow-up, explain what changed rather than restarting the checklist. Do not imply
background progress unless a job is actually running.

## Final review covers the whole release

Run phone and submit checks, remote validation and account checks outside API coverage. Scoped
READY covers only that scope. Distinguish internal QA limits from store submission blockers.
Record explicit acceptance of named testing limits separately; do not manufacture passing results
or routinely ask for waivers to save work.

Use [get-it-submitted.md](../templates/app/get-it-submitted.md) for one concrete approval: exact
build, evidence, release behavior, public destinations/assets and known limits. Current user scope
governs; the template grants no permission. Approval for one destination does not imply another.
After approval, submit and verify remote state. If one action is blocked, finish the rest.
