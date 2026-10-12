# Progress workflow

Each selected app has one open GitHub issue labelled `app` and exactly one of `status:building`, `status:in-review`, or `status:live`. Issue labels are the source of truth. Keep Live issues open for maintenance.

Use the app name as the title. Include a `Next: ` line, scope, evidence date, remaining checklist, and a verified download link when live. Detailed test records remain with source code.

## Status pipeline (openappco.com)

1. **App Store Connect → issues.** `scripts/asc-status.py --apply` (run on the Mini with `/Users/mini-home/projects/asc-venv/bin/python`) reads each app's newest App Store version, read-only, and when it changed rewrites the issue's status label, `App Store: <STATE> · checked <date>` line, and `Next:` line. Apps match by the `ascId` and issue number in `apps.config.json`, with exact-name matching only as a fallback. This survives App Store subtitle-style names such as “Open Breath: Breathing Timer.” Unsubmitted versions are skipped.
2. **Issues → site.** `.github/workflows/status.yml` runs `node scripts/sync-apps.mjs --promote` on every issue change and hourly. It writes `docs/apps.json` and the README table, checks the public iTunes lookup (no credentials) and flips an app to `status:live` once Apple lists it, then commits and asks Pages to rebuild.
3. **Site.** `docs/site.js` renders `apps.json` and refreshes 👍 counts and labels live from the GitHub API. Repo stars are the site-wide "likes"; a 👍 on an app's issue is that app's like.

Each numbered app also has a generated living page. `app-pages.config.json` owns its immutable
number, post description, public media and verified complaint/fix rows. Run:

```bash
node scripts/render-app-pages.mjs
node scripts/validate-launch-system.mjs
node scripts/render-app-pages.mjs --post <slug>
```

The hourly status workflow runs the first two commands after refreshing `docs/apps.json`, so every
page gets a current static fallback while `docs/app-page.js` also refreshes status in the browser.
The `--post` form prints the ready-to-paste daily X copy and always links to the app page.

## What ships next

Nothing upcoming is published. The site and README list an app only once it is submitted to Apple (`status:in-review`) or live. The goal is one new app a day, chosen day-of: run `node open-suite/scripts/today.mjs` in the factory repo for a private shortlist ranked by severity of one-star reviews (`scripts/severity.mjs`: 8 harm, 4 blocked, 2 ads/nags, 1 other), with built prototypes listed first because they ship fastest.

Site stages: Submitted (WAITING_FOR_REVIEW) → In review (IN_REVIEW, or approved and releasing) → Live. Rejections show as "Changes requested". Presentation copy, icons and quotes live in `apps.config.json` and `docs/assets/apps/<slug>/`.

Discuss suggestions in Discussions. Keep unselected research internal. Never publish private review contacts, raw reviews, or credentials.

## Daily app post

Once App Store Connect confirms that Apple's review queue accepted the exact approved version and
build (`WAITING_FOR_REVIEW`), the app receives the next permanent Open AppCo launch number. The
number is recorded explicitly and never inferred from issue numbers, build numbers, configuration
order, or the site's current card count. Its public source of truth is the app's `launchNumber` in
`apps.config.json`.

Each kit has three pieces: a short X post naming the launch number, recording that the app was sent
to Apple for review that day, and describing the app's job in one sentence; a 1200×630 share image
styled like a compact iOS App Store listing; and an app-specific living status page. The image shows
the app icon, name, description,
CHECK IT OUT action, Free · iPhone, one real screenshot and `APP #<number>`. It deliberately omits
Apple’s changing review status and does not restate the launch number as an ordinal, so the same
image remains accurate after approval.

The post links to `/<slug>/`, not the homepage or an App Store URL that is not live yet. The page
leads with the current Apple status, then shows three clean screenshots, the inspected
physical-device demo, and every manually verified complaint category the app claims to address with
the corresponding feature delivered free. Quotes are short, source-linked, and stripped of
reviewer identity. The page also states the audit's storefront, sort-order, date and Apple feed-cap
boundary; it never claims access to every lifetime or worldwide review. The status pipeline keeps
the page current. Only after the public App Store lookup succeeds does the page's main action become
the verified download link; that later transition does not create a second launch number.
Approval also does not create a second numbered post or card. A short unnumbered reply to the
original post can announce that the app is live, while the next day's main post stays focused on the
next app.

## How an app gets from idea to the App Store

Open AppCo follows [Slipway](https://github.com/pauljump/slipway), a general five-phase workflow
for shipping small iOS apps: pick, build it, on my phone, get it submitted, Apple's answer. Slipway holds the procedure, templates and an offline checker, and anyone can use it
for their own apps. Open AppCo adds its own defaults on top: no ads, no account, no tracking,
nothing to unlock, support and privacy pages on openappco.com, and this repository's status
pipeline.

Between pick and brief, Open AppCo adds a selected-candidate review audit. The broad mining pass is
for finding promising jobs; the audit then revisits every source app behind the chosen job, requests
every public Apple feed page in the recorded storefronts and sort orders, deduplicates the results,
and records feed caps or failures. Only manually checked receipts can drive requirements. The exact
coverage boundary is published with the methodology because Apple's public feed is not a complete
lifetime or worldwide archive.

App source, signed builds, reviewer contact details, Apple messages and credentials stay private.

Device review is performed on a real iPhone. When available, the release walkthrough is captured
wirelessly with Apple's iPhone Mirroring: the agent retries the connection after an unlock or
reconnect, launches from the Home Screen, uses clean demo content, and inspects the finished video.
USB is a fallback, not a default requirement. Private phone content is kept out of release evidence.
