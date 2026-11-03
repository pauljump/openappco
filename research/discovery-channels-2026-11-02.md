# Discovery channels an agent can work alone (2026-11-02)

Read-only research. Nothing was posted, submitted, signed up for or called. Scope: free, no human
posting, no human accounts, no paid ads, no paid APIs. Already planned and not re-researched: store
link fixes, Smart App Banner, sitemap/robots, SoftwareApplication JSON-LD, titles, Google Search
Console. In-store keyword rules (name/subtitle/keyword field, secondary category, rating prompt
timing) are already in `_factory/open-suite/docs/discovery-2026-10-25.md` and WORKFLOW → Discovery;
this file only adds what that one lacks.

Baseline that shapes the ranking: search is 69 to 97% of impressions per app (10-25 baseline), and
total downloads are in the tens. At that volume, levers that touch App Store search relevance or a
handful of high-intent referrals beat broad awareness. Every lever is weighed against 4.3(a)/(b)
and 2.3.7 risk on an account that already has a removal warning.

Marks: **AGENT NOW** = doable with credentials already on the Mini (ASC API key, signed-in ASC tab,
`gh`, site repo). **OWNER ONCE** = needs Paul to log in or approve once. **NOT RECOMMENDED** = why given.
"Approval gate" means the existing rule: anything submitted to Apple waits for Paul's "approved".

## Ranked list

### 1. Accessibility Nutrition Labels, filled honestly on every live app (AGENT NOW, approval gate)
Apple: "Users can include Accessibility Nutrition Label features as part of their search query ...
in searches like 'VoiceOver note taking apps' ... apps that have indicated support for those
features in their labels will be considered more relevant in search results." Labels show in an
Accessibility section of the product page, and will become mandatory later. This is the one
in-store lever that matches what Open AppCo actually is (VoiceOver, Larger Text, Reduce Motion,
Differentiate Without Color, Sufficient Contrast). Open Piano's per-note color plus shape is a real
"Differentiate Without Color" claim. Only claim a feature if every common task works with it;
App Review can make you correct misleading labels. Low 4.3 risk: it is accurate metadata, not
volume. Check whether the labels are set via API or only the ASC UI; the signed-in ASC tab works
either way.
Sources: [ASC Help: Accessibility Nutrition Labels](https://developer.apple.com/help/app-store-connect/manage-app-accessibility/overview-of-accessibility-nutrition-labels), [Apple Support 123073](https://support.apple.com/123073)

### 2. Featuring Nomination for Open Piano (AGENT NOW via ASC, approval gate)
Free, in ASC since WWDC 2024, with API read endpoints (`GET /v1/nominations`, API 3.8). A
nomination is a note to the editorial team, not a public listing, so it carries no spam signal.
Piano's story (built for a neurodivergent son, color+shape notes, VoiceOver) is the kind of
accessibility story Apple editorial runs. One nomination per meaningful update; never bulk-nominate
the catalog (that would itself look like the 4.3 pattern). Low probability, very high payoff.
Sources: [ASC Help: Nominate your app](https://developer.apple.com/help/app-store-connect/manage-featuring-nominations/nominate-your-app-for-featuring), [API: GET nominations](https://developer.apple.com/documentation/appstoreconnectapi/get-v1-nominations)

### 3. Cross-localization keyword fields (AGENT NOW to stage; ships with a version, approval gate)
The US storefront reportedly also indexes es-MX, ru, zh-Hans, ar, fr, pt-BR, zh-Hant, vi, ko (vendor
tests, not Apple-documented; one 2026 source claims only en-US + es-MX). Each adds another
30+30+100 of US-indexed text; words don't combine across locales. Start with es-MX only, written
as real Spanish (users in Mexico see it). Reader's traffic is already half outside the US (India,
UK), so en-GB/en-IN localizations with their own keyword sets also help those storefronts directly.
Risk: keyword-stuffed or irrelevant localized text can draw 2.3.7; keep it truthful.
Sources: [AppTweak cross-localization](https://www.apptweak.com/aso-blog/how-to-benefit-from-cross-localization-on-the-app-store), [aso.dev](https://aso.dev/metadata/cross-localization/), [MobileAction](https://www.mobileaction.co/blog/app-store-cross-localization/)

### 4. Keyword-assigned Custom Product Pages, one or two per app max (AGENT NOW via API, approval gate)
CPPs are reviewed but need no binary; promo text on a CPP localization can change anytime. With
keyword assignment, a CPP replaces the default page in organic search for those terms. For Piano,
an intent page for "piano for autistic kids / color notes" with screenshots that show exactly that
is the obvious test. Keep it to 1-2 real intents per app: dozens of near-identical CPPs across a
nine-app catalog is the kind of pattern a 4.3-sensitive reviewer could read as mass production.
The existing workflow says wait for steady search traffic; Reader and Flashcards qualify first.
Sources: [API: POST appCustomProductPages](https://developer.apple.com/documentation/appstoreconnectapi/post-v1-appcustomproductpages), [CPP localizations](https://developer.apple.com/documentation/appstoreconnectapi/appcustomproductpagelocalization)

### 5. IndexNow on openappco.com, plus Bing Webmaster Tools (IndexNow AGENT NOW; BWT OWNER ONCE)
IndexNow: host `<key>.txt` at the site root, POST changed URLs to `api.indexnow.org` (shared with
participating engines: Bing, Yandex, Seznam, Naver; Google does not participate). Up to 10,000 URLs
per POST. Already done this way on filing.win. Hook it into the site deploy so only changed URLs are
sent. Why it ranks this high for an app site: ChatGPT search and Copilot draw heavily on Bing's
index, so Bing coverage is the cheapest route into AI answers. Bing Webmaster Tools needs one
Microsoft or Google sign-in (it can import the site from Search Console once GSC is set up);
it then shows IndexNow receipts and Bing queries. Note the key file in a public repo is visible;
that is harmless (it only lets someone ping you), but it can also be generated at deploy time.
Sources: [indexnow.org documentation](https://www.indexnow.org/documentation), [indexnow-action](https://github.com/bojieyang/indexnow-action), [BWT import from GSC](https://www.seroundtable.com/bing-webmaster-tools-verify-google-search-console-28139.html)

### 6. Let the AI search crawlers in, and write answer-shaped app pages (AGENT NOW)
robots.txt should explicitly allow `OAI-SearchBot` (ChatGPT search; OpenAI says opted-out sites
won't appear in ChatGPT search answers), `Claude-SearchBot`, `PerplexityBot`, and `Applebot`
(Apple says Applebot data powers Spotlight, Siri and Safari suggestions; `noindex` removes you).
Training bots (`GPTBot`, `ClaudeBot`, `Google-Extended`, `Applebot-Extended`) are a separate
choice. Then make each app page answer the question an assistant gets: who it is for, what it
does, what it does not do, device/iOS requirements, privacy, and the App Store link, in plain
text near the top (one large study found 44% of ChatGPT citations come from the first third of a
page). One honest page per live app plus one page about the Piano's design for neurodivergent kids
is enough. Do NOT generate many keyword landing pages per app: that is a doorway-page pattern for
search engines and looks like the mass production Apple is watching for.
Sources: [Applebot](https://support.apple.com/HT204683), [AI crawler tokens summary](https://www.therankmasters.com/insights/service-playbooks/ai-crawlers-robots-txt-claudebot-gptbot-perplexitybot), [How ChatGPT chooses sources](https://dev.to/searchless_ai/how-chatgpt-chooses-sources-388k) (vendor; treat numbers as rough)

### 7. App Store campaign links on every outbound link (AGENT NOW; provider token OWNER ONCE if not known)
Add `?pt=<provider>&ct=<page>&mt=8` to every App Store link on openappco.com, the GitHub README and
any Smart App Banner (`app-argument`/tokens). Free, no review. It turns "App referrer / Web
referrer" into per-source numbers in ASC Analytics (shown after 5+ first-time downloads per
campaign). Without it we can't tell which of the off-store levers below did anything. The provider
token comes from generating one campaign link in ASC → Analytics → Acquisition → Campaigns.
Sources: [ASC Analytics: campaign links](https://developer.apple.com/help/app-store-connect-analytics/acquisition/campaign-links/)

### 8. Share previews: per-app Open Graph and Twitter card images (AGENT NOW)
When a parent, teacher or OT pastes an openappco.com link into Messages, Slack or a forum, the
preview is the ad. Each app page should have its own `og:title`, `og:description`, `og:image`
(1200x630, the real app screen) and `twitter:card=summary_large_image`. Pages already have some
`og:` tags (Piano has 4); check that each one has its own image and description, not the site's.
Linking directly to `apps.apple.com` already gets Apple's own rich preview in Messages.

### 9. GitHub repo as a discovery surface (AGENT NOW via `gh`)
pauljump/openappco is public. Add repo topics (`ios`, `iphone-app`, `accessibility`, `autism`,
`voiceover`, `free-apps`), App Store links (with campaign tokens) per app in the README, and a
short "who each app is for" table. GitHub pages rank well in Google and are heavily represented in
AI training and retrieval. Free, no external posting.

### 10. llms.txt (AGENT NOW, low value)
Costs minutes. Evidence it helps is weak: an Ahrefs log study (as reported) found 97% of llms.txt
files got zero AI requests in May 2026, no major vendor has committed to reading it, and Google says
it ignores such files. Fine to add as a plain index of the app pages; don't expect traffic.
Sources: [PPC Land on Ahrefs data](https://ppc.land/llms-txt-adoption-rises-8-8x-but-97-of-files-get-zero-ai-requests/)

### 11. QR codes and a printable one-pager for the Piano (AGENT NOW to make; owner distributes)
A one-page PDF for teachers, OTs and parent groups with a campaign-tagged QR to the App Store. The
agent can make it; handing it out is a human act. This is the highest-intent channel for a niche
ND app, but it only works through people.

### 12. In-App Events (AGENT NOW via API, approval gate; use rarely)
Events appear in search and on the product page, reviewed without a binary. Guideline 2.3.13
requires a real, time-boxed event inside the app; utility apps get rejected for general promos.
Only do it when there is a real one (e.g. a Reader "classic novels" collection added). A rejected
event is a review mark on the account, so don't experiment.
Sources: [Phiture: getting events approved](https://phiture.com/mobilegrowthstack/in-app-events-how-to-get-approved/), [Gummicube: rejected events](https://www.gummicube.com/blog/what-to-do-if-your-in-app-event-gets-rejected)

### 13. Open-sourcing app code, which unlocks open-source app lists (OWNER DECISION, then PR by agent)
dkhamsing/open-source-ios-apps (1,734 projects, one of the most-linked iOS lists) adds apps via a PR
to `contents.json` with `source` and `itunes` fields; it is a list of open-source apps, so the app
code would have to be public. The app sources are currently private (only the tracker repo is
public). If Paul ever publishes code, this and similar lists become one PR each from his GitHub.
That PR is a public submission under his account, so it needs his approval each time.
Sources: [CONTRIBUTING](https://github.com/dkhamsing/open-source-ios-apps/blob/master/.github/CONTRIBUTING.md)

### 14. Universal links and App Clips (NOT NOW)
Universal links (AASA at `/.well-known/apple-app-site-association`, needs `.nojekyll` on GitHub
Pages and an entitlement in each binary) help people who already have the app, not discovery. A
default App Clip experience can be invoked from Safari, Messages and QR codes without server work
and would let someone try Piano instantly, but it means a new App Clip target per app, more review
surface and more size. Revisit only for Piano if the QR channel (11) shows real use.
Sources: [ASC: default App Clip experience](https://developer.apple.com/help/app-store-connect/offer-app-clip-experiences/offer-a-default-app-clip-experience)

### 15. Directories that need a human account (OWNER ONCE each; flagged)
- **AppleVis** app directory (blind/low-vision iOS users; the best fit for VoiceOver apps): entries
  are posted by community members; developers are pointed to the contact form. Needs Paul to post
  or write. The help page blocked automated fetch. Best of this group for Piano and Reader.
- **AlternativeTo**: FAQ says sign up and add the app yourself; verified email required; moderated.
- **Product Hunt, Hacker News, Reddit**: human accounts, and Product Hunt bans automated outreach
  and repeated submissions. One launch per app at most, posted by Paul. Not for an agent.
- **Autism/special-needs app roundups** (educatorstechnology, eLearning Industry, specialneeds.com,
  NAS UK services directory): editorial, reached by an email from Paul; no submission form found.
Sources: [AppleVis developers](https://applevis.com/developers), [AlternativeTo FAQ](https://alternativeto.net/faq), [NAS directory example](https://www.autism.org.uk/autism-services-directory/aidova-free-aac-communication-app)

## Not recommended

- **Wikidata/Wikipedia entries for our own apps**: conflict of interest and notability rules; a
  2026 account of 109 self-made software items deleted and the account blocked as promotion-only.
- **Copying App Store ratings into JSON-LD to get Google rich results**: Google requires
  `aggregateRating` or `review` for SoftwareApplication rich results, and spammy markup can draw a
  manual action. Ship JSON-LD without ratings (no rich stars, still a clean entity) until the site
  has first-party reviews, which it shouldn't collect.
- **Many CPPs, events or localizations per app**, keyword-stuffed names ("Open X: A & B & C"), or
  near-identical pages per app: each is individually allowed, but across a 9-app catalog under a 4.3
  warning the aggregate reads as volume. Note the 10-25 names already use the `Open X: term` form;
  2.3.7 rejections cite "keywords or descriptors" in the name, so watch the pending reviews.
- **Any posting, commenting, voting or account creation by an agent** on forums, social sites or
  directories: impersonation of Paul, against most sites' terms, and a spam signal tied to the brand.
- **Apple Ads**: paid. New accounts get a one-time $100 credit (Apple's promo-credit page) if the
  developer has an app on sale; the account is the developer's. If Paul ever wants a free test,
  $100 on Piano's exact long-tail terms would show which terms convert, but it is his call and
  spends past the credit if left on. Separate $150 Apple Maps credit is irrelevant.
  Source: [Apple Ads promo credit](https://searchads.apple.com/help/basic/0041-apple-search-ads-promo-credit/)
- **Ratings prompts beyond what exists**: already implemented with success-moment triggers; Piano
  and Dice keep no prompt by policy.

## Context worth knowing

- Since Nov 2025 apps.apple.com is a full web store with search and browsing (no installs). App pages
  are indexable and our site linking to them helps search engines find them; Apple's domain usually
  outranks a developer site for the app name, so our pages should target "who it's for" queries.
- Backlinks do not affect App Store ranking (Google Play only, per vendors). Off-store work pays only
  through the direct downloads it sends, which in turn feed App Store download-velocity signals.
- Promotional text and description are not indexed by App Store search; write them for people.
