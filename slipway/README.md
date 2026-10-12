# Slipway

How we take a small iPhone app from idea to live in the App Store — over and over, with coding
agents doing most of the work.

It started with a piano. We wanted a simple piano app for a kid, and every one we tried stopped the
music for an ad. So we built one. Then we went looking and found the same thing everywhere: tiny
apps that do one job, buried under ads, paywalls and fake limits. That became
[Open AppCo](https://openappco.com) — free apps, no ads, no account, one at a time.

Building each app took an hour or two. Getting it through Apple took days, and we kept paying for
the same mistakes. This repo turns those mistakes into checks and a durable local release runner.

## If an agent sent you here

Tell your agent:

> Clone https://github.com/pauljump/openappco, take its `slipway` folder, install
> `skills/slipway/SKILL.md` from it as a skill, and walk me through `docs/setup.md`.

Setup is a one-time job: an Apple developer account, an API key, and pairing your phone. The agent
runs `python3 tools/slipway.py doctor` to show what's still missing. After that, build an app however
you like and say **"ship the app."** Your agent inventories the full user checklist, prepares the release, and brings one final review
packet. Your approval authorizes submission of that exact build. Existing sessions and permissions
are reused; authentication or new access can still require you.

> **Status:** October 2026. Apple changes its rules a few times a year. Anything Apple-specific has
> a date and a link next to it — check those before you trust them.

## The five phases

When we actually ship an app it goes like this:

1. **[Pick](docs/1-pick.md)** — choose the app, make sure it's actually better, check the name.
2. **[Build it](docs/2-build-it.md)** — a one-page brief, then the build. If the look is new, one
   picture first.
3. **[On my phone](docs/3-on-my-phone.md)** — use it, say what's off, new build, repeat. This is
   where my time goes. It should.
4. **[Get it submitted](docs/4-get-it-submitted.md)** — prepare the packet, approve the exact release, submit.
5. **[Apple's answer](docs/5-apples-answer.md)** — answer the question they'll ask, resubmit, go
   live.

I first wrote this as nine stages. It never felt like nine when we actually shipped one. It felt
like these five. The nine are still in here, as checklists inside them.

## Start here

Start with [durable work](docs/durable-work.md): run the offline onboarding rehearsal, configure a
private connection inventory, and keep each release in one durable ledger. No account is contacted
by the rehearsal.

1. **[Before your first app](docs/setup.md)** — the Apple account, the API key, the tools, being
   signed in, pairing your phone and recording its screen. Do it once. Then run:

   ```bash
   python3 tools/slipway.py doctor
   ```

2. **Read the two pages that save the most time:**
   - [Apple's rules for a stream of small apps](docs/review-rules.md) — guideline 4.3 decides
     whether this works at all.
   - [What Apple sent back, and how to never get it again](docs/prevent-round-trips.md).
3. **Start an app:**

   ```bash
   python3 tools/slipway.py new ~/apps/my-counter    # one folder per app
   python3 tools/slipway.py check ~/apps/my-counter  # what's left in this phase
   python3 tools/slipway.py status ~/apps            # every app and where it stands
   ```

   Keep a `catalog.csv` ([template](templates/catalog.csv)) at the top of your apps folder. It's
   how you see your own apps side by side before Apple does.

4. **Working with an agent?** Read [working with agents](docs/working-with-agents.md), then point it
   at [AGENTS.md](AGENTS.md) or install [the skill](skills/slipway/SKILL.md). It knows when to stop
   and ask you.

Already have a built app? Start at [Bringing in an app you already built](docs/2-build-it.md#bringing-in-an-app-you-already-built).

## What's in here

```text
docs/        setup, the five phases, Apple's rules, what went wrong, agents, making it yours
templates/   app/ (copied by `new`), catalog.csv, ios/ (Info.plist keys, privacy manifest,
             export options)
tools/       checker, connection inventory, durable worker, release packet and offline rehearsal
             Python 3.10+, standard library only
skills/      the agent skill
```

## What it won't do

The checker is offline by default. The runner executes your reviewed adapters only within recorded
authorization; submission and publication require the exact-build packet. It won't
get you approved either: new accounts get asked questions no matter what (our first four apps all
were, as of October 2026).
And it won't make your fifth timer safe. Read the [rules](docs/review-rules.md) first.

## License

MIT. Not affiliated with Apple. App Store, App Store Connect, iPhone and Xcode are Apple's
trademarks.
