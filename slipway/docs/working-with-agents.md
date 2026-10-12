# Working with agents

I want apps submitted end to end with as little help from me as possible. Agents can do nearly all
of it — research, briefs, code, tests, screenshots, metadata, uploads. Two things make that work:
knowing exactly when the agent needs me, and turning every rule into something `check` can fail.

I pick the app, approve a new look, complete the human-only phone checks in one handoff, and approve
the final release packet. The agent records the phone when supported; I record only if it cannot.
Sign-in is needed only when the existing session is unavailable. If Apple cites a rule, that comes back to me too, because it's a product
question again. So does anything that costs money, goes public, or installs on my phone for the
first time.

Everything else is the agent's: reading and researching, writing the brief and the code and the
notes, building and testing, reading App Store Connect with the API key whenever it wants, watching
review status, and release preparation. External submission/publication follows the approved scope in the
[get-it-submitted template](../templates/app/get-it-submitted.md).

Automatic signing (`-allowProvisioningUpdates`) registers bundle IDs and creates profiles in your
account. Decide up front whether that's on the agent's side of the line. We put it there.

## Rules as checks

An agent follows a check more reliably than a page of instructions.

- **Check the full scope.** A submission-only pass is not a phone-QA pass. Record explicitly
  accepted exceptions without changing failed or unrun results; always record Apple's real state.
- **One complete human checklist.** Use [release handoff](release-handoff.md) before phone testing.
- **One writer to App Store Connect.** One CLI, one key, one wrapper that loads the key from your
  secrets store. The agent never sees the `.p8` contents.
- **Read before writing, read back after.** Never repeat a create because the response looked
  strange.
- **Read back exact strings before acting on feedback about them.** Names, spacing, capitalization.
- **A failing test before every fix.**
- **Hooks or CI for the mechanical stuff:** competitor names, placeholders, Markdown in review text,
  byte limits.

## Picking up where it left off

Every new session starts from zero, so the state lives in files:

- `app.json` → `phase`, `next`, `history`, and `apple.state` as last read.
- Receipts (IDs, timestamps, read-backs) in a git-ignored folder next to the app.
- First command of every session: `slipway.py status <apps-folder>`.

## Several apps at once

- One agent per app folder, and nothing outside it.
- Shared code, the catalog and anything public stay with one lead.
- Workers never upload, submit or publish.

Building in parallel is fine. Submitting a batch of similar apps at once is how accounts get
flagged; see [pacing](review-rules.md#how-fast-to-go).

The agent skill is [skills/slipway/SKILL.md](../skills/slipway/SKILL.md). Copy it into your agent's
skills folder and set `SLIPWAY` to where you cloned this repo.
