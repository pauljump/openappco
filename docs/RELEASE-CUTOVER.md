# Open Piano support-page cutover

User decision, October 6, 2026: prepare and publish GitHub Pages help/privacy pages, but retain the current App Store submission and existing support/privacy URLs until Apple approves Open Piano. Do not withdraw or resubmit it for this move.

Target hosting: `main:/docs`, with `.nojekyll`, at https://pauljump.github.io/openappco/.

After approval is verified:

1. Verify both new pages return 200 and contact/navigation links work.
2. Redirect only `/apps/open-piano/support` and `/apps/open-piano/privacy` (including trailing-slash forms) to the matching `/openappco/open-piano/support/` and `/openappco/open-piano/privacy/` GitHub Pages URLs.
3. Keep `/api/apps/open-piano/wishlist` and Wishlist/Bench routes working. Do not redirect JSON requests to HTML. The submitted binary still uses that feed.
4. Verify redirects and the unchanged feed externally, then update the app tracking issue with evidence.

Redirects should eventually execute at the existing hostname’s edge to remove the Mini dependency for these pages. A Node-only redirect still depends on the Mini. This change does not migrate the Wishlist API.

No automatic approval monitor or redirect job is configured. Approval must be checked before cutover.

## Publication verified October 6, 2026

GitHub Pages is enabled on main:/docs with HTTPS. Support and privacy return 200, and browser navigation between them works. A real operator support-page visit appeared in PostHog with pulse_host=pauljump.github.io, pulse_source=native_browser, pulse_is_operator=true, and no query string in the recorded URL. Replay is disabled by the currently deployed shared loader for these pages.

The original support/privacy endpoints and Wishlist JSON feed still return 200 without redirects. App Store metadata was not edited. Redirect cutover remains pending Apple approval.
