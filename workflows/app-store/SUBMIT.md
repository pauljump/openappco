# Workflow 1: initial App Store submission

This workflow ends only when the exact intended build and its review packet are
read back from App Store Connect in `WAITING_FOR_REVIEW` or another active review
state. Uploading a build is not submission, and submitting is not approval.

## 1. Freeze the release candidate

Record the app name, bundle ID, platform, version, build number, signed archive,
and build identifier. Run the app's release tests and smoke-test the same build
on a supported physical device. Never choose “the newest build” without checking
its identity.

## 2. Prepare the customer-facing listing

Complete the description, subtitle, keywords, category, price, territories,
support URL, privacy-policy URL, screenshots, icon, age-rating answers, content
rights, export-compliance answers, and release method. Verify links and inspect
the final screenshots at their submitted dimensions.

## 3. Reconcile privacy and dependencies

Review the final source, entitlements, privacy manifest, runtime SDKs, network
behavior, analytics, advertising, accounts, and data flows. App Store privacy
answers must include relevant third-party behavior and must match the submitted
binary. Do not copy declarations from another app merely because both are from
Open AppCo.

## 4. Create the App Review packet

Fill [the packet template](templates/review-packet.md) and the six numbered
[Review Notes answers](templates/review-notes.txt):

1. physical-device testing and what the recording demonstrates;
2. purpose, target audience, value, and business model;
3. setup and access instructions;
4. runtime external services and material build-time content tools;
5. regional differences; and
6. regulated activity and protected or third-party material rights.

Apple documents a 4,000-byte limit for the Notes field. Keep the reply-ready
copy within the same limit so it can be reused without contradicting the
submission.

## 5. Capture first-submission evidence

Open AppCo's first-version practice is to capture a short video of the exact
final build on a current physical device. Begin on the Home Screen, launch the
app, and show the ordinary core flow. Include login, account deletion,
user-generated-content controls, or paid access only when the app has them.

Record the device, OS, duration, demonstrated path, filename, and SHA-256. Check
that the recording contains no personal notifications or account information.
This is a risk-reduction practice learned from limited-review-history requests;
it is not a claim that every ordinary app is required to submit a video.

## 6. Validate locally

Run:

```bash
python3 workflows/app-store/tools/validate_packet.py path/to/release/submission.json
```

Resolve every failure. Review warnings manually. A green local result proves
only that the source-side packet is internally complete; it does not inspect
Apple's remote state or authorize an external action.

## 7. Upload and read back

Upload the exact build and wait for processing to complete. Attach the build to
the intended version. Save the App Review contact privately, add the six Notes
answers, upload the physical-device video as a review attachment, and read the
fields back. Require the attachment to finish processing before submission.

Complete App Privacy separately and verify its published state. A saved privacy
URL is not the same thing as a published privacy declaration.

## 8. Submit deliberately

Review diagnostics and the full submission one last time. Submission is an
external, representational action: obtain current authorization immediately
before sending it unless the user's current instruction already explicitly
covers submission.

## 9. Verify the remote result

Read the version, build, submission ID, timestamp, and review status back from
App Store Connect. Store a private receipt. Only a confirmed waiting or active
review state counts as submitted. Approval and public release are later states.

If Apple asks for more information or requests changes, continue with
[Workflow 2](RESPOND.md).
