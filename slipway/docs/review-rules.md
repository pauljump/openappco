# Apple's rules for a stream of small apps

Building the apps turned out to be the easy part. The real limit is App Review, and one guideline
in particular decides whether shipping lots of small apps works at all. These are the rules that
matter most, quoted word for word from
[Apple's App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) as of
**October 10, 2026**. Apple changed them in November 2025 and again in June 2026, so read the live
text before you lean on this.

## 4.3 Spam: the one that matters

> **(a)** Don't create multiple Bundle IDs of the same app (for example, submitting a separate map
> app for every city in the world instead of a single worldwide map that allows users to search any
> city). […]
>
> **(b)** Don't submit apps that are indistinguishable from what's already widely available.
> Opportunistically creating variants of existing app categories or popular apps degrades App Store
> discovery, reduces overall app quality, and harms both users and developers. Certain kinds of
> apps, such as dating, flashlight, sound effects, wallpaper, simple timers, and fortune telling,
> are well established on the App Store and we will not accept new submissions unless they offer a
> meaningfully different or improved experience. We may remove these apps from the App Store going
> forward if they are not updated, improved, or do not attract customers. […] **Repeated
> submissions of this kind may lead to removal from the Apple Developer Program.**

How we read it:

- **The apps worth rebuilding are exactly the ones Apple calls crowded.** Timers, metronomes, noise
  machines, counters — that's the list. Apple doesn't say no. It says *meaningfully different or
  improved*.
- **"No ads" isn't enough by itself.** We couldn't find a single case of a reviewer accepting
  privacy or no-ads alone as the difference. Pair it with something better about the job itself.
  That's why [Pick](1-pick.md) starts with one sentence.
- **Apple looks at your whole account.** In forum reports going back to 2017, developers were told
  their *own* apps were too alike and to merge them. Keep a catalog and compare before you submit.
- **Your account is what's at risk.** One spam rejection is information. Resubmitting the same app
  after a second one is how you lose the account. Merge it, rethink it, or drop it.
- **Live apps can be pulled later** if they're "not updated, improved, or do not attract
  customers." Update the ones you keep at least once a year.

### How fast to go

We wanted one app a day. We couldn't find anyone who has shipped crowded-category apps from one
account at that pace — the best-known serial shipper,
[12 startups in 12 months](https://levels.io/12-startups-12-months/), did one a month. Our take: **build
fast, submit slower.** Queue finished apps. Never send two of the same kind back to back. Where
apps are near-twins — three kinds of timer — ship one app with modes. 4.3(a) suggests exactly
that.

## 4.1 Copycats and 2.3.7 metadata

> **4.1 (a)** Come up with your own ideas. […] Don't simply copy the latest popular app on the App
> Store, or make some minor changes to another app's name or UI and pass it off as your own.
>
> **4.1 (c)** You cannot use another developer's icon, brand, or product name in your app's icon or
> name, without approval from the developer.
>
> **2.3.7** Choose a unique app name, assign keywords that accurately describe your app, and don't
> try to pack any of your metadata with trademarked terms, popular app names, pricing information,
> or other irrelevant phrases just to game the system. App names must be limited to 30 characters.

We find ideas by reading competitors' reviews, so their names are everywhere in our notes. They
must never appear in anything Apple sees: name, subtitle, keywords, description, screenshots,
review notes — or inside the app. List them in `app.json` → `incumbents` and the checker flags
them.

Keep prices out of the name, subtitle and screenshots too ("Free!"). "No ads. No account." at the
end of the description is fine.

## 4.2 Minimum functionality

> Your app should include features, content, and UI that elevate it beyond a repackaged website.
> If your app is not particularly useful, unique, or "app-like," it doesn't belong on the App
> Store.

A one-button app can pass. Its one job just has to be done well: data that survives, VoiceOver,
big text, sensible empty states. The brief's acceptance tests are where you prove it.

## 2.1 App completeness, and the question new accounts get

> Submissions to App Review […] should be final versions with all necessary metadata and fully
> functional URLs included […] Make sure your app has been tested on-device for bugs and stability
> before you submit it, and include demo account info […] if your app includes a login.

Separately, new accounts get a "2.1 Information Needed" question on their first apps. It isn't in
the guidelines; it's what happens. [Apple's answer](5-apples-answer.md) has how to handle it, and
Apple's own list of what to include up front is
[here](https://developer.apple.com/help/app-review/before-submitting-for-review/complete-review).

## 3.1.1 Payments

If an app asks for money in any way — even a link to a page where people can chip in — read
[3.1.1](https://developer.apple.com/app-store/review/guidelines/#in-app-purchase) before
submitting. In-app purchases have their own rules. Linking out to pay is restricted. A free app with
no payment anywhere avoids the question entirely. Record it in `decisions.payments`.

## 5.2.1 Intellectual property

> Don't use protected third-party material such as trademarks, copyrighted works, or patented ideas
> in your app without permission […]

Write down the license of every sound, font, sample and generated asset you didn't make. App Store
Connect asks a "content rights" question for every app; decide the answer in the brief.

## How long review takes

Apple: "typically reviewing at least 50% of submissions in less than 24 hours and 90% in less than
48 hours." ([App Review](https://developer.apple.com/distribute/app-review/)) Our first approval took
just over two days from submission, including one question. Others were still waiting after four days.
Plan for days.
