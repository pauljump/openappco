# Research and mining

The existing App Store review-mining operation continues under Open AppCo. Its evidence and internal backlog are preserved; moving the tracker does not restart collection.

1. Collect bounded discovery batches of public App Store listings and reviews, preserving source URLs, IDs, capture dates, and run provenance.
2. Verify evidence, group recurring friction, and merge candidates solving the same job.
3. Separate observations from interpretation. Evidence scores inform research; they do not promise a release.
4. Once an app is selected, run a deeper coverage audit across every source app behind that candidate. Record each storefront, sort order and public feed page requested; deduplicate review IDs; disclose failures and feed caps; and manually verify the receipts that change product scope.
5. Reconcile the audit into a brief covering scope, explicit exclusions, privacy, accessibility, acceptance criteria, and release risks. Discovery themes that do not survive the deeper pass do not become product claims.
6. Create a tracking issue when work is selected. Verify on real devices before release.

Apple's public review feed is bounded: it exposes at most ten pages for a storefront and sort order, and does not establish a complete lifetime or worldwide corpus. When we say a selected candidate received a coverage audit, we mean every entry Apple returned from the exact feeds listed in that audit, not reviews Apple does not expose. That boundary is part of the result, not a footnote.

Selected jobs include a straightforward piano, an offline fraction calculator, and a blood-pressure log with export. Their tracking issues describe progress; these examples do not imply all complaints have been solved.

## Public and internal records

Raw databases, full review bodies, reviewer identities, private run logs, and unselected candidates stay internal. Public findings require provenance review and should use only short verified excerpts when necessary, with source links and capture dates.

The September 1, 2026 board export contained 697 candidate entries. Those are research leads, not 697 promised releases. Suggestions belong in Discussions until selected for work.

The existing scripts and database remain in their canonical source location. This repo owns public methodology and selected-app progress. Reusable mining code needs a reviewed extraction before publication; no raw database or credential-bearing configuration is copied here. Updating the tracker does not start collection or paid model jobs.
