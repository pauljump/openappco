# 4. Get it submitted

The app is done. Now hand Apple everything it could ask for, up front, so it has no reason to
bounce it.

Use the [release handoff](release-handoff.md) to identify the complete user checklist before
starting. Reuse an existing App Store Connect session; ask for sign-in only if it is actually needed.

“Ship the app” starts preparation of the [release scope](../templates/app/get-it-submitted.md).
I get asked twice at most: once up front (sign-in, only if it's needed, plus anything Apple will
make me confirm myself), and once at the end, for the exact build. In between, "ship it" covers
creating the app record, reusing the saved review contact, publishing the privacy answer when it's
Data Not Collected and matches the code, and registering the bundle ID and the profile for my phone.
On one app the agent asked me about the record, then the contact and privacy, then the packet, as
three separate approvals. That's what this rule stops.

The agent completes a reviewable packet, including processing and attachment readbacks, then asks
for approval of the exact version/build. Include public tracker/site changes in that same decision
with their destinations and assets named. Approval authorizes the listed actions; new legal or
security prompts still follow the host's confirmation rules.

## The packet (before you even ask)

All of this is local, and the agent should have it ready by the time the phone checks are done.
`check --only submit` validates only the submission packet, not physical-device QA. Run both
`check <app> --only phone` and `check <app> --only submit --online` before final review.
List any incomplete checks and any explicit user-accepted exceptions; never turn exceptions into passes.

- **Listing** in `store/metadata/` (the folder layout `asc` reads):
  - Name: 2–30 characters, same as `app.storeName`.
  - Subtitle: 30 characters at most.
  - Description: what it does in the first line; the plain facts at the end ("No ads. No account.
    No subscription.").
  - Keywords: 100 *bytes* at most. No words from the name or subtitle, never another app's name.
- **Screenshots** come from the end of [phase 3](3-on-my-phone.md#store-screenshots).
- **Support and privacy pages**, from the templates in `web/`, ready to publish at the URLs in
  `decisions`. They need real contact information.
- **Review notes** (`store/review-notes.txt`): six numbered answers in Apple's order, plain text (App
  Store Connect shows Markdown asterisks literally), under 4,000 bytes:
  1. The phone and iOS version you tested on, and what the recording shows.
  2. What it is, who it's for, and how it makes money (or that it doesn't).
  3. How to reach the core feature: no login, no setup, or exactly what's needed.
  4. Every external service, or "none".
  5. Regional differences, or "the same everywhere".
  6. Regulated activity, and the license for every sound, font or image you didn't make.
- **The reply** (`store/review-reply.txt`): the same six answers with a greeting and a sign-off.

Then the agent goes down [what Apple sent back last time](prevent-round-trips.md) and shows me every
line checked off. It also checks the notes against every message App Review has ever sent us, and
lists which files it read. That only works if each message is saved word for word in that app's
release folder when it arrives. A summary isn't enough: ours were summaries, and the originals had to
be dug out of old chats. Last, `check --online` loads the support and privacy pages; a 404 there is a
rejection waiting to happen.

## The Apple part

Run independent preparation steps while human checks are pending; a missing video need not block
a verified binary upload. Processing and authentication can vary, so estimate from actual state. Commands use
[`asc`](https://github.com/rorkai/App-Store-Connect-CLI) 5.9+ through your wrapper; check `--help` on
your version. Read the state before every change and read it back after. Never repeat a "create"
because the response looked odd — look first.

**1. Business → Agreements** shows nothing waiting. (Browser.)

**2. Publish the support and privacy pages**, then `python3 tools/slipway.py check <app> --online`.
They can go up now, with the other setup steps, or as the first action of the final approval. That's
how one of ours went: approval published the pages, and submitting waited until both returned
HTTP 200. Either way, nothing gets submitted while either one is a 404.

**3. Create the app record.** Once per app. This is where the name check becomes real.

```bash
asc bundle-ids list --identifier com.example.app     # automatic signing usually registered it already
asc web auth login --apple-id you@example.com        # asc's own web session; see setup §5
asc web apps create --name "Example App" --bundle-id com.example.app --sku example-app \
  --version 1.0.0 --auto-rename=false --if-exists skip
asc apps list --bundle-id com.example.app            # read back; the numeric id is apple.appId
```

Or create it by hand in the browser: Apps → **+** → New App. Either way, pass the version and turn
off auto-rename. The defaults are `1.0` (won't match a `1.0.0` binary) and quietly renaming your app
if the name's taken. If the name *is* taken, use the fallback from phase 1.

In the browser, check every field before you press Create: the form re-lays out after you pick the
bundle ID. Press Create once, then read it back with `asc apps list --bundle-id`. The browser gave us
version `1.0`; fix it with
`asc versions update --version-id <version-id> --version 1.0.0 --release-type AFTER_APPROVAL`.

**4. EU trader status for this app:** App Information → App Store Regulations and Permits. (Browser;
the page only exists once the record does.)

**5. Listing, screenshots and settings:**

```bash
asc metadata validate --dir store/metadata --check-urls
asc metadata apply --app <app-id> --version 1.0.0 --platform IOS --dir store/metadata
asc screenshots upload --app <app-id> --version 1.0.0 --locale en-US \
  --path store/screenshots/01.jpg --device-type IPHONE_69      # then 02, 03, … one at a time
asc apps content-rights edit --app <app-id> --uses-third-party-content=false
asc age-rating edit --app <app-id> --all-none
```

Upload screenshots one file at a time, in order. A whole-folder upload timed out on one file and
rolled back the others. Read back the count, the order and COMPLETE.

The last two lines are the defaults for an offline app that ships only its own content. An app that
opens arbitrary web pages declares Unrestricted Web Access (`--unrestricted-web-access true`), which
Apple rates 16+ ([Apple](https://developer.apple.com/help/app-store-connect/reference/app-information/age-ratings-values-and-definitions),
checked October 2026 **[dated]**). An app that shows publishers' content sets
`--uses-third-party-content=true`. Our feed reader did both.

Price (Free), availability and release type are in the browser under Pricing and Availability and
the version page, if your CLI version doesn't cover them.

**6. App Review information.** Find the version's review detail, then set the contact, sign-in
off, and the notes, and attach the recording:

```bash
asc versions list --app <app-id> --version 1.0.0        # gives the version id
asc review details-for-version --version-id <version-id> # gives the review detail id
asc review details-update --id <detail-id> --demo-account-required=false \
  --notes "$(cat store/review-notes.txt)"
asc review attachments-upload --review-detail <detail-id> --file store/device-demo.mov
asc review attachments-list --review-detail <detail-id>  # wait for COMPLETE
```

The contact (name, phone, email) is saved once with `details-create`/`details-update`, or in the
browser. Only Apple sees it.

**7. App Privacy:** answer and **Publish**, in the browser (the app's Privacy page → Get Started →
answer → Save → Publish). Saved isn't published, and the API can't tell the difference. Screenshot
the published state. An API key can't do this step, or create the app record; both need a signed-in
web session.

**8. Upload the build:**

```bash
asc publish appstore --app <app-id> --ipa build/<n>/export/App.ipa --version 1.0.0 --wait
asc builds list --app <app-id> --build-number <n>        # the build id; wait for VALID
```

**9. Final approval, then submit:**

Present the exact-build packet and named publication scope. Obtain final approval unless the user
has already explicitly approved that exact release and scope. Do not submit based only on a local
checker passing.

```bash
asc validate --app <app-id> --version 1.0.0 --strict
asc review doctor --app <app-id>
asc review submit --app <app-id> --version 1.0.0 --build-id <build-id> --dry-run
asc review submit --app <app-id> --version 1.0.0 --build-id <build-id> --confirm
asc review status --app <app-id>
```

Don't call it submitted until Apple says `WAITING_FOR_REVIEW` for that build.

**10. Write it down.** In `app.json`, set `phase: review`, `apple.appId`, `apple.state` and
`apple.checkedAt`. Mark it submitted in the catalog. Update your tracker now — we forgot once, and a
submitted app was missing from our own site until someone noticed.

Switch on App Store Connect's Analytics Reports for the app today. None of ours were on, so when
Tally went live I couldn't see its numbers. The first report takes a day or two
([Apple](https://developer.apple.com/documentation/appstoreconnectapi/downloading-analytics-reports),
checked October 2026 **[dated]**).

When `check` says READY at `review`, you're waiting on Apple.
