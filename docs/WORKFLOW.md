# Progress workflow

Each selected app has one open GitHub issue labelled `app` and exactly one of `status:building`, `status:in-review`, or `status:live`. Issue labels are the source of truth. Keep Live issues open for maintenance.

Use the app name as the title. Include a `Next: ` line, scope, evidence date, remaining checklist, and a verified download link when live. Detailed test records remain with source code.

After updating issues, run `node scripts/sync-apps.mjs` with authenticated GitHub CLI, review the README diff, and commit it. This generates the directory from issues; there is no separate status database or scheduled automation.

Discuss suggestions in Discussions. Keep unselected research internal. Never publish private review contacts, raw reviews, or credentials.
