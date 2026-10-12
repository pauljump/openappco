# Brief: [APP NAME]

Appetite: [APPETITE]. If it doesn't fit, cut scope. Don't stretch the clock.

## The job
- What someone opens it to do:
- What they can do in the first ten seconds, with no setup:
- The harm we're fixing (from idea.md):

## What's in, what's out
| Feature | required / recommended / omit / forbidden | Why |
|---|---|---|
| Support and Privacy links in the app | required | Every app needs them |
| | | |

Forbidden unless there's a written reason here: ads, tracking, analytics, accounts, purchases,
links to pay anywhere, network calls. That includes network calls made by shared code you didn't
write for this app. Competitor names never appear in the app.

## Screens and states
Each screen, plus empty, error, interrupted (a call, the lock button, backgrounding) and first
launch.

Plays audio in the background? Then pause on the lock screen and in Control Center must stop it. I
couldn't stop our metronome from the lock screen.

## Screenshot states
| Screenshot | What it shows | Launch argument that sets it up |
|---|---|---|
| 1 | The job being done (this one sells it) | |
| 2 | | |
| 3 | | |

## Data
What's saved, where (on the phone), how it survives restarts and updates, and how someone resets or
exports it.

## Accessibility
VoiceOver labels on every control. Usable at the largest text size. Reduce Motion respected. Tap
targets at least 44 pt.

## Store decisions (copy into app.json → decisions)
- App Privacy answer:
- Network calls (every one, and what happens offline):
- Sign-in: none
- Payments or links to pay: none
- Content rights (every sound, font, image or sample you didn't make, and its license):
- Age rating:
- Release: AFTER_APPROVAL
- Category, and `kind`:
- Support and privacy URLs:
- Orientation:
- Permissions, and the one-line reason for each:

## Acceptance tests
Each one is something you can check on a phone. Every required feature has at least one.

- [ ] Tapping the icon lands on the job, with no prompt.
- [ ] (the core job, end to end)
- [ ] Data survives a force-quit and reopen.
- [ ] The core job works with VoiceOver.
- [ ] The main screen works at the largest text size.

## Not in v1

## Open questions

## Phone rounds
One line per round of feedback: build number, what was off, what changed.
