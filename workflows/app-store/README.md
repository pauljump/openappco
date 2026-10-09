# Open X App Store submission kit

This is Open AppCo's reusable, public-safe workflow for submitting an Open X
app to Apple and responding when App Review asks for more information.

Open AppCo is the project. Open X is the app family: Open Piano, Open Noise,
Open Tally, and future `Open <Noun>` apps.

The kit was distilled from real first-version submissions. It is not official
Apple guidance and cannot guarantee acceptance or prevent an information
request. Apple's current documentation remains authoritative.

## Included workflows

- [Initial submission](SUBMIT.md): freeze a release candidate, prepare the
  review packet, validate it, submit it deliberately, and verify the remote
  state.
- [Review response and resubmission](RESPOND.md): classify Apple's message,
  reply with evidence, avoid unnecessary rebuilds, and verify resubmission.
- [Review-packet template](templates/review-packet.md)
- [Review Notes template](templates/review-notes.txt)
- [Reviewer-response template](templates/reviewer-response.txt)
- [Submission manifest example](templates/submission.example.json)
- [Physical-device test summary example](templates/physical-device-tests.example.json)
- [Offline packet validator](tools/validate_packet.py)

## Quick start

Copy the templates into an app-owned release directory, then replace every
placeholder with facts from the exact build being submitted:

```bash
mkdir -p MyApp/release
cp workflows/app-store/templates/review-packet.md MyApp/release/
cp workflows/app-store/templates/review-notes.txt MyApp/release/
cp workflows/app-store/templates/reviewer-response.txt MyApp/release/
cp workflows/app-store/templates/submission.example.json MyApp/release/submission.json
cp workflows/app-store/templates/physical-device-tests.example.json MyApp/release/physical-device-tests.json
```

Add the physical-device recording named in `submission.json`, calculate its
hash with `shasum -a 256 <video>`, and validate locally:

```bash
python3 workflows/app-store/tools/validate_packet.py MyApp/release/submission.json
```

The validator uses only Python's standard library. It reads local files and
prints a JSON report; it never connects to Apple, uploads a build, sends a
message, or submits an app.

Run its tests with:

```bash
python3 -m unittest discover -s workflows/app-store/tests -v
```

## Public/private boundary

Safe to keep in a public repository:

- generic workflow documentation and templates;
- public support and privacy URLs;
- non-sensitive asset provenance and licenses;
- an example manifest containing placeholders.

Keep private or ignored:

- App Store Connect API keys and session files;
- reviewer contact name, email, and phone;
- demo-account credentials;
- signed archives and provisioning material;
- Apple messages or receipts containing private details;
- physical-device recordings that reveal personal notifications or accounts.

The repository currently has no explicit software license. Choose and add a
license before representing this kit as reusable open-source software.

## Official references

- [Submit an app](https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/submit-an-app/)
- [App Review information fields](https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information/)
- [Provide information for a complete review](https://developer.apple.com/help/app-review/before-submitting-for-review/complete-review)
- [Manage app privacy](https://developer.apple.com/help/app-store-connect/manage-app-information/manage-app-privacy)
- [App Store review attachments API](https://developer.apple.com/documentation/appstoreconnectapi/app-store-review-attachments)
