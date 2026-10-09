# Progress workflow

Each selected app has one open GitHub issue labelled `app` and exactly one of `status:queued`, `status:building`, `status:in-review`, or `status:live`. Issue labels are the source of truth. Keep Live issues open for maintenance.

Use the app name as the title. Include a `Next: ` line, scope, evidence date, remaining checklist, and a verified download link when live. Detailed test records remain with source code.

## Status pipeline (openappco.com)

1. **App Store Connect → issues.** `scripts/asc-status.py --apply` (run on the Mini with `/Users/mini-home/projects/asc-venv/bin/python`) reads each app's newest App Store version, read-only, and when it changed rewrites the issue's status label, `App Store: <STATE> · checked <date>` line, and `Next:` line. Apps match by App Store Connect name = issue title. Unsubmitted versions are skipped.
2. **Issues → site.** `.github/workflows/status.yml` runs `node scripts/sync-apps.mjs --promote` on every issue change and hourly. It writes `docs/apps.json` and the README table, checks the public iTunes lookup (no credentials) and flips an app to `status:live` once Apple lists it, then commits and asks Pages to rebuild.
3. **Site.** `docs/site.js` renders `apps.json` and refreshes 👍 counts and labels live from the GitHub API. Repo stars are the site-wide "likes"; a 👍 on an app's issue is that app's like.

## Lineup (slots 1–10)

The release order is ranked by **severity of one-star reviews**, not market size. `scripts/severity.mjs` scores every verified complaint excerpt with a fixed rubric: 8 harm (lost data, surprise charges, privacy, unsafe ads), 4 blocked (core job paywalled or behind signup), 2 ads/nags, 1 other. An idea's severity is the sum. Apps already at Apple or live hold the first slots; every other slot goes to the highest severity, built or not.

1. **Weekly re-rank.** PM2 scheduled job `openappco-lineup` (Mondays 9:00) runs `scripts/weekly-lineup.sh`: fresh miner export to `~/.local/share/openappco/`, then `lineup.mjs propose --publish`. If the order differs from the approved lineup it opens or refreshes one `lineup-review` issue with the table; if not, it closes any open review.
2. **Approve.** The owner comments `approve` on that issue. `.github/workflows/lineup.yml` runs `lineup.mjs approve`, which writes `lineup` into `apps.config.json`, opens a `status:queued` tracking issue for each new app, closes the review, re-renders, and republishes.
3. **Changes.** To reorder by hand, edit `lineup` in `apps.config.json` (or ask Claude), then run `node scripts/sync-apps.mjs`. Ideas without a short name show "needs a name" in the review; add them to `names`.

Site stages: Queued → Building → Submitted (WAITING_FOR_REVIEW) → In review (IN_REVIEW, or approved and releasing) → Live. Rejections show as "Changes requested". Presentation copy, icons, quotes and teasers live in `apps.config.json` and `docs/assets/apps/<slug>/`.

Discuss suggestions in Discussions. Keep unselected research internal. Never publish private review contacts, raw reviews, or credentials.

## App release workflows

The reusable, public-safe App Store process lives in the
[App Store submission kit](../workflows/app-store/). It separates two workflows:

1. preparing and submitting an exact release candidate; and
2. responding to App Review and resubmitting after an information request or
   resolved issue.

The kit contains templates and a local validator, but no Apple credentials and
no automatic submit action. App source, signed archives, reviewer contact
details, private messages, and credentialed receipts remain in their canonical
private locations.
