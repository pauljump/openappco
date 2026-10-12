# Field notes

The weird stuff, written down so nobody has to find it twice. Seen with Xcode 26–27, App Store
Connect API 4.x and `asc` 5.9, September–October 2026.

## App Store Connect

**Rejected, but no bug named.** That's the new-account question (2.1 Information Needed), not your
app. Answer it and resubmit — see [Apple's answer](5-apples-answer.md#the-question-youll-get-it).

**Replying doesn't resubmit.** The state stays `UNRESOLVED_ISSUES` after you reply. Resubmit
yourself and read back `WAITING_FOR_REVIEW`.

**Resubmitting leaves an empty draft.** A high-level "submit" refuses the existing submission and
creates a new, empty one, because the version stays tied to the original. Resolve the rejected item
and resubmit the original instead (`review items update --resolved true`, then
`review submissions-submit`). Leave the empty draft alone.

**The website's Resubmit button is greyed out.** Don't trust it. On one app it only unlocked after
the rejected item was added back to the submission. Use the API's dry run and read-back.

**Creating the app record says it failed, but it worked.** The web flow showed an "access" error on
success. Look the app up by bundle ID before trying again. Never repeat a create blindly.

**The New App form moves under you.** It re-lays out after you pick the bundle ID, and typing meant
for the SKU field missed. Check every field (a screenshot, if an agent is filling it) before Create.

**One screenshot timed out and took the others with it.** The upload command waited on Apple for one
file, gave up, and rolled back the rest. Upload one file at a time, in order, and read back the
count, the order and COMPLETE.

**Version `1.0` vs `1.0.0`.** A CLI's create command defaulted to `1.0`. Pass the version yourself and
compare it with the binary's `CFBundleShortVersionString`.

**The name's taken.** Some CLIs quietly add a suffix by default. Turn that off and use the fallback
you picked in phase 1.

**"Sign-in required" is on.** Validation then demanded a demo username and password for an app with
no login. Turn it off and read it back.

**Privacy saved but not published.** That blocks the submission, and the API can't tell the
difference. Publish it in the browser and take a screenshot.

**Regulations aren't in the CLI's doctor.** EU trader status and device declarations live only in
the browser, under App Information → App Store Regulations and Permits. Look before submitting.

**The reply button won't enable.** The attachment is still uploading. Wait for the filename to
appear, send, then read the thread back.

**Nothing works and there's no error.** Check Business → Agreements. A new license agreement blocks
app creation until the account holder accepts it.

## Build, signing and upload

**ITMS-90183 after upload.** `CFBundlePackageType` is missing. A generated project left it out, and
the archive and phone install worked anyway — only Apple's processing caught it. Add `APPL`, bump the
build number, upload again.

**`errSecInternalComponent` while signing.** The keychain is locked because the build isn't running
in the desktop session (SSH, background agents). Run it there, or unlock a dedicated signing
keychain in the script.

**Manual signing plus an Xcode-managed profile fails.** Don't mix them. At a desk, automatic signing
all the way through is simplest. An agent building headless can't use that: it needs a dedicated
keychain it unlocks itself, and manual signing with an App Store profile made for that app, for both
archive and export. A brand-new bundle ID needs a profile with your phone in it before you can
install.

**A build exported "for internal TestFlight only"** can never go to the App Store. Check
`ExportOptions.plist` for `testFlightInternalTestingOnly`.

**Xcode changed the build number.** `manageAppVersionAndBuildNumber` defaults to on. Turn it off.

**"No build attached" during validation** just means the build is still processing. Wait for
`VALID`.

**Tests that only fail in Release.** `@testable import` needs `ENABLE_TESTABILITY=YES` in the
configuration you test. Some project generators also drop UI tests from the scheme without saying
so.

**TestFlight disappears.** Twice in one month every TestFlight build on our account expired at once,
and new builds showed as unavailable. That was Apple's side. Installing straight to the phone and
submitting to the App Store kept us moving. Don't make TestFlight a required step.

## Phone and recording

**Locked phone.** Launching fails with `Locked` inside a `10002` error, though the install usually
worked. Unlock and launch again.

**UI tests behave differently on a real phone.** A tap lands in the middle of a wide toggle row and
the switch never flips — tap the switch itself. New controls can be missing from the accessibility
tree for a moment. "Done" can be ambiguous inside nested sheets.

**UI tests that fail at random.** Taps were landing mid-animation after a navigation transition.
Wait for the element to be hittable before tapping (an `isHittable == true` expectation), not just
for it to exist.

**Audio that only breaks on hardware.** An audio session setup the simulator accepted threw
`OSStatus -50` on a phone. Test sound on the device.

**Recording from the Mac is fragile.** Here's what went wrong:
- mirroring tools that don't pass taps through;
- cable capture that didn't see the phone;
- a recorder that saved nothing after being interrupted;
- clips that ran too long;
- iPhone Mirroring saying "iPhone in Use" because I was reading the agent's messages on that phone;
- swipes through Mirroring arriving as taps (one opened Music);
- Home Screen search showing my email in the middle of a take.

iPhone Mirroring is still the one an agent can drive alone: lock the phone, wait a few seconds,
**Try Again** (twice if it says "Connection Interrupted"), go Home with ⌘1, open the app from Search,
and blur anything private before using the take. The phone's own recorder is the only route with
the app's sound.

## Process

**Old names leak.** Our previous project name kept showing up in screenshots, share images and
copy. Keep one naming line in your own README and search public files for old names before
publishing.

**State in five places.** Batch notes, issue labels, a website, a manifest and Apple's real state
all drifted apart. Slipway keeps one `app.json` per app, updated from Apple's read-back, and
everything else should come from that.
