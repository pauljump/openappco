# Release scope: [APP NAME] [VERSION] build [BUILD]

“Ship the app” starts preparation for final review. Fill this scope before requesting approval;
the template is not permission. Current explicit user instructions take precedence.
Reuse existing sessions. See `user-handoff.md` for all human tasks and known prompts.

## Prepare the complete packet

- Store name [STORE NAME], fallback [FALLBACK], bundle [BUNDLE ID], version/build above
- App record and signing profiles; archive, upload, process and attach the exact build
- Listing, keywords, screenshots, saved private review contact and published privacy answer [ANSWER]
- Content rights [RIGHTS], age rating [RATING], price [PRICE], territories [TERRITORIES]
- Release behavior [AFTER_APPROVAL / MANUAL]
- Inspected real-phone recording, COMPLETE attachment readback and final reviewer answers
- Phone and submission checks, remote validation, and any named unverified limits

By default, “Ship the app” also covers these setup actions without a separate approval (change
this line if your rules differ): create the App Store
Connect record, reuse the saved review contact, publish the privacy answer when it is Data Not
Collected and matches the code, and register the bundle ID and the phone install profile.
Ask once, up front, only for what that doesn't cover: sign-in if the existing session is gone, a
different or changed privacy answer, new legal agreements, new access. Then the next request is the
final approval below.

Publish required support/privacy pages at [SUPPORT URL] and [PRIVACY URL] under explicit user
publication scope: either earlier with the setup actions, or as the first action of the final
approval. Submission waits until both return HTTP 200.

## Final approval: actions and destinations

- Submit this exact version/build to Apple for review
- Update public tracker [REPOSITORY / ISSUE], catalog [PATH] and site [URL]
- Public assets [ICON / SCREENSHOTS / NAMED FILES]; private reviewer video is excluded
- Accepted testing limits, if explicitly agreed: [NONE / EXACT CHECKS]
- Optional follow-up scope: [APPROVED / NOT APPROVED] to answer information-only review questions
  with prepared answers and privately reattach the recording, then resubmit the same build

Approval received: [EXACT WORDING, DATE, SCOPE]. Once approved, perform those actions and read back
results without another general approval request. Host-required action-time confirmations remain
separate. If a destination is not approved, finish approved work and name the gap.

New builds after submission, material packet changes, reviewer defects/rule problems, withdrawal,
new charges and new access scopes are not silently covered by this approval.
