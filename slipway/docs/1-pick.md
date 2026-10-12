# 1. Pick

Pick something people are already angry about. Then ask whether you can make it better — not just
free.

I ask the agent for five options and pick one. It takes a couple of minutes. It's still the most
important call in the whole process.

## Start from what people complain about

The best ideas come from one-star reviews. Not "I wish it did more" — real harm:

- an ad covering the thing you opened the app to do
- the basic feature behind a $9.99/week trial
- an account wall on a calculator
- lost data after an update
- the tuner that told you to keep tightening until the string snapped

Keep each piece of evidence with a link, a date, and a short exact quote. A paraphrase isn't
evidence.

Rank by how bad the harm is, not by how big the market is. We score every complaint the same way
so the ranking can be rerun:

| Harm | Points |
|---|---|
| Lost data, surprise charges, privacy, inappropriate ads, physical harm | 8 |
| The core job is behind a paywall or a sign-up | 4 |
| Ads and nags | 2 |
| Any other bug | 1 |

An idea's score is the total across its complaints. We rank by harm and not market size because
the people a $9.99/week trial hits hardest are the ones least able to dodge it — kids,
grandparents, someone logging blood pressure for a doctor.

The score is keyword rules, not a reader. When I checked ours, almost two thirds of all complaints
landed in "any other bug." Read the top quotes for an idea before you trust its rank.

Write `idea.md` from [the template](../templates/app/idea.md). And pick the one you can finish: I
passed on a tide-chart app once because it needed live data, and none of our apps had brought in
data yet.

## Go deep on the one you picked

The sample that found the idea is for finding ideas. It isn't enough to write a brief from. Before
the brief, pull every page Apple's public review feed exposes for each competitor: several
storefronts, both sort orders (most recent and most helpful), deduped. Write down how many reviews
you got, which pulls failed, and which apps hit the feed's cap. In October 2026 **[dated]** each
feed stopped at page 10 of 50 reviews, so a full page 10 means older reviews you can't see
(`https://itunes.apple.com/us/rss/customerreviews/page=1/id=<APP_ID>/sortby=mostrecent/json`). On Feeds this took the evidence from 4 apps to 12 and moved the whole angle, from paywalls
to read-state you can trust.

Requirements that show up across several apps become acceptance criteria in the brief. One-off
requests get written down and deliberately kept or cut. And say "every review Apple's feed
exposed," never "all reviews." The feed isn't all of them.

## Write the one sentence

Apple won't take new apps in crowded categories "unless they offer a meaningfully different or
improved experience" ([why that matters](review-rules.md)). So before anything gets built, write
one sentence saying what's better — about the job itself, not the price.

- Weak: *"A metronome with no ads."*
- Better: *"A metronome whose beat never drifts or stops when the screen locks, with a one-handed
  tempo dial."*

None of our apps have ads. That alone isn't a reason for Apple to take another metronome.

## Check it against your own apps

Give the app a `kind` — what sort of app it is in Apple's eyes: timer, sound, counter, tuner,
calculator. "Utilities" is too broad to mean anything.

Then look at your catalog. Already have one of that kind live or in review? Two questions:

- Could this be a mode of the app you already have?
- If not, can it wait until the first one is approved?

Apple looks at your account as a whole. Three timers in a week reads as spam even if each one is
good.

## Check the name today

Search the store for your name and anything close to it. If you're the account owner, you can also
type it into App Store Connect's New App form — that's the only real answer, but it's yours to do,
not the agent's. Either way, pick a fallback store name **now**, before icons and screenshots spell
it out. The store name can carry a suffix ("Example Metronome:
Tempo & Beats") while the Home Screen name stays short.

Record what you did in `app.json` → `app.nameCheck`:

```json
"nameCheck": { "method": "public-search", "at": "2026-10-09", "result": "free", "fallback": "Example Metronome: Tempo & Beats" }
```

`method` is `public-search` or `app-store-connect`. A public search only lowers the risk;
App Store Connect confirms it when you create the record in phase 4.

List the competitor apps in `incumbents` while you're here. Their names must never show up in
anything Apple sees, and the checker uses the list to catch them.

When `python3 tools/slipway.py check <app>` says CHECKS PASS for this phase, set `phase` to `build`.
