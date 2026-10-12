# 2. Build it

The agent builds. I stay out of the way until there's something to hold. A small app should go
from brief to a working build in an hour or two — if it's taking days, it's the wrong app.

## The brief comes first, and it's one page

Use [the template](../templates/app/brief.md). Every question in it is one that otherwise shows up
on ship day, at 8pm, with the agent waiting on me.

- **How long.** A day to build, a day to polish. If it won't fit, cut scope.
- **The job and the first ten seconds.** What can someone do the moment they open it, with no
  setup?
- **What's in, what's out.** Every feature is required, recommended, omit or forbidden. Ads,
  tracking, analytics, accounts, purchases and network calls are forbidden unless you write down
  why — including calls made by shared code you didn't write for this app.
- **Store decisions, now.** Privacy answer, network use, sign-in (none), payments or links to pay
  anywhere (none), content rights (who made every sound, font and image), age rating, release
  type, support and privacy URLs, category, orientation, permissions.
- **Support and Privacy links inside the app,** and the two pages themselves, drafted from
  [the templates](../templates/app/web/). Every app needs them. We kept adding them at the last
  minute.
- **Screenshot states.** Which screens show the app doing its job, and the launch argument that
  puts the app in each state. Without these the store screenshots show an empty app.
- **Acceptance tests** you can check on a phone. Always: it opens straight to the job; data
  survives a force-quit; the core flow works with VoiceOver; the main screen works at the largest
  text size.

Copy the store decisions into `app.json` → `decisions`.

## Show me a picture first (if the look is new)

If this app needs a new look — new icon, new main screen — show one picture before writing much
code: the main screen and the icon, next to your other apps. Five minutes into one build I stopped
it: "this green yellow is ugly." That cost five minutes. After the build it would have cost the
afternoon.

Share type, spacing and controls across your apps. Don't share the icon style, the main screen
layout or the colors. Those are what make each app its own, and they're what Apple compares.

Record `look.motif` and `look.palette` either way. Set `look.new: false` if you're reusing an
existing look; it then doesn't need approval.

## Build

- **Start from a project that already has the keys that bit us.** See
  [Info.plist keys](../templates/ios/info-plist-keys.md): `CFBundlePackageType = APPL`, an explicit
  Home Screen name, version wiring, `ITSAppUsesNonExemptEncryption`. Add the
  [privacy manifest](../templates/ios/PrivacyInfo.xcprivacy).
- **Test the brief.** Unit tests for the logic, UI tests for the core flow, relaunch, and the
  largest text size. Write a failing test before each fix.
- **Demo states come from launch arguments or environment variables only**, never from data a real
  user could see.
- **List the source folders in `files.source`**, including shared packages. The checker reads them
  for network calls, payment code, links out and competitor names, and holds them against your
  decisions.
- **Archive into a numbered folder** — `build/<build-number>/` — not `/tmp`. If Apple asks
  questions you'll need that exact archive. Never reuse a build number.

  ```bash
  xcodebuild archive -project App.xcodeproj -scheme App -configuration Release \
    -destination 'generic/platform=iOS' -archivePath build/3/App.xcarchive \
    -allowProvisioningUpdates -authenticationKeyPath "$ASC_PRIVATE_KEY_PATH" \
    -authenticationKeyID "$ASC_KEY_ID" -authenticationKeyIssuerID "$ASC_ISSUER_ID"
  xcodebuild -exportArchive -archivePath build/3/App.xcarchive -exportPath build/3/export \
    -exportOptionsPlist ExportOptions.plist -allowProvisioningUpdates \
    -authenticationKeyPath "$ASC_PRIVATE_KEY_PATH" -authenticationKeyID "$ASC_KEY_ID" \
    -authenticationKeyIssuerID "$ASC_ISSUER_ID"
  shasum -a 256 build/3/export/*.ipa
  ```

  [ExportOptions.plist](../templates/ios/ExportOptions.plist) needs your Team ID (see
  [setup](setup.md#4-tools-on-the-mac)).
- **Check the archived Info.plist**, not the source one. Point `files.infoPlist` at it; the checker
  compares bundle ID, version, build number and Home Screen name against `app.json`.

Leave the store screenshots for phase 4. They should come from the build you ship.

## Bringing in an app you already built

Most of our apps were prototypes before this process existed. To bring one in:

1. `slipway.py new` a folder for it and fill in `idea.md` from whatever evidence you had.
2. **Audit the code against the forbidden list** — every network call, link out, payment path and
   competitor name, including in shared packages. Set `files.source` and let the checker help.
   Then fill in `decisions` with what's actually there, not the template's "none". Our dry run found
   a shared component, in an app nobody had looked at for weeks, that fetched from a server, named a
   competitor and linked to a payment page.
3. Point `files.brief` at the old brief only if its tests match what was actually built. Old briefs
   describe features that never got made. Otherwise write a short one now.
4. Confirm the bundle ID. It can never change after the first upload.
5. Record the look's motif and palette. Set `look.new: false` only if someone has actually looked at
   it and is happy; otherwise get it approved like a new one.
6. Throw away old screenshots. They'll be redone from the build you ship.
7. Archive it fresh and run the checker. Fix what it finds **in the real source**, not just the
   archive. The first old prototype we ran it on was missing two Info.plist keys that would have
   failed the upload.

When `check` says READY, set `phase` to `phone`.
