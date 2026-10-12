---
name: slipway
description: Take a small iOS app from idea to live in the App Store with the Slipway workflow (Pick → Build it → On my phone → Get it submitted → Apple's answer). Use when the user says "ship the app" or "ship it" about an app they built (prepare the release for final review, then submit after approval), or when asked to pick, build, put on the phone, submit, or answer App Review for an app that has (or should have) a Slipway app.json, when setting up a Mac or iPhone for shipping, or when asked where an app stands.
---

# Slipway

Five phases from idea to the App Store. The repo has the docs, templates and a checker. Set
`SLIPWAY` to where it lives.

## Start every session the same way

```bash
python3 $SLIPWAY/tools/slipway.py status <apps-folder>   # every app and its phase
python3 $SLIPWAY/tools/slipway.py check <app-folder>     # what's left in this phase
python3 $SLIPWAY/tools/slipway.py doctor                 # is the Mac and phone ready
```

Read the app's `app.json` (`phase`, `next`, `history`) and the phase page in `$SLIPWAY/docs/`.
Trust the files, not memory. For an initialized release, first read
`flow.py --state <private-release-dir> status`. Follow `docs/durable-work.md` for the executable
connection inventory, job recovery and sealed packet. Resume the same ledger; never repeat a create
from a fresh state directory. `run` is foreground; after it returns, no worker is implied.

## Route the request

| They say | Phase page | You're done when |
|---|---|---|
| "what's next", "give me options" | 1-pick | A short list, each with evidence, a differentiation sentence, a `kind` and a name check. **They pick** |
| "build it" | 2-build-it | Brief, decisions, build and archive all pass `check`. If the look is new, **they approve one picture** first |
| "put it on my phone" | 3-on-my-phone | Installed. Then loop on their feedback. When they say it's good: the checks and the recording |
| "ship the app", "get it submitted" | from wherever the app is, through 4-get-it-submitted | Complete final review packet; after explicit approval, Apple reads back `WAITING_FOR_REVIEW` for the exact build |
| "Apple replied", "got denied" | 5-apples-answer | Sorted into question / problem / rule; answered; state read back |
| "is it live" | 5-apples-answer | The public lookup shows it |
| "set up my Mac/phone" | setup | `doctor` is clean apart from understood warnings |

## Rules

- Follow the preparation and final approval boundary in `templates/app/get-it-submitted.md`.
  The current user's explicit scope takes precedence; do not infer external publication from a
  vague phrase or repeat approval already given for the exact action.
- Before phone work, read `docs/release-handoff.md` and fill `user-handoff.md` for this release.
  Batch all known user work, reuse existing authentication, and keep independent agent work moving.
- Read before every write; read back after. Never retry a create blindly.
- Before acting on feedback about exact text (names, spacing), repeat the exact string back.
- A scoped `check --only submit` result covers only the packet. Run phone and submit checks before
  final review. Keep failures visible; record explicitly accepted testing exceptions separately from
  test results. After submission, record Apple's actual state even if an accepted QA limit remains.
- Competitor names never appear in metadata, review notes or in the app. They live in
  `incumbents`.
- No personal contact details, key material, team IDs or device IDs in a public repo.
- After a 4.3 spam rejection, stop and bring it to them. Don't resubmit unchanged.

## End of turn

Tell them: the app, the phase before and after, what changed, the check result, what's blocked and
on whom, and the one next step. Write the next step into `app.json` → `next`.
