# 3. On my phone

This is where the app gets good. Put it on your phone, use it like you would, say what's off, get a
new build, repeat.

Our metronome took five builds in one evening. None of the fixes came from a test. The beat counter
stuck on 2. I couldn't stop it from the lock screen. The tempo marks were too small to hit. I found
those by using it.

If your phone isn't set up for this yet, do [the phone part of setup](setup.md#7-your-phone) first.

Before the first phone handoff, follow [the complete release handoff](release-handoff.md).
Identify every user-owned check and missing setup step together.

## The loop

1. **Install.** Unlock the phone first — installs work while it's locked, launches don't.

   ```bash
   xcodebuild -project App.xcodeproj -scheme App -configuration Release \
     -destination 'generic/platform=iOS' -allowProvisioningUpdates \
     -authenticationKeyPath ... -authenticationKeyID ... -authenticationKeyIssuerID ... \
     -derivedDataPath build/device build
   xcrun devicectl device install app --device <UDID> build/device/Build/Products/Release-iphoneos/App.app
   xcrun devicectl device process launch --device <UDID> --terminate-existing com.example.app
   ```

   You can't install an App Store export on a phone. "The same build" means the same code and the
   same build number, signed for development.

2. **Use it.** Not a checklist — just use it. Then say what's wrong in plain words.
3. **Fix with a failing test first**, bump the build number, reinstall.
4. **Repeat** until you'd hand it to someone. Write one line per round in the brief's notes.

**When the agent changes anything you named, it should repeat the exact text back before building.**
I told an agent there needed to be a space between Open and Metronome. The next build took out the
space that was already there.

## Before you put the phone down

When it feels right, do the checks and the recording right then. Don't let them wait for ship day.

| Check | How |
|---|---|
| Opens from the Home Screen | Tap the icon. You're in the app, doing the job, no prompt |
| The core job | Do it end to end |
| The brief's acceptance tests | Every one, on the phone, before the recording. Include typing: text typed through Mirroring once vanished on autosave |
| Survives a restart | Force-quit, reopen. Everything's still there |
| VoiceOver | Settings → Accessibility → VoiceOver. Do the core job without looking |
| Biggest text | Settings → Accessibility → Display & Text Size → Larger Text, all the way up. Still usable |
| Sound through the speaker* | Right volume, no clicks |
| Sound with the screen locked* | Keeps going or stops cleanly, the way the brief says |
| Interruptions* | Take a call or set off an alarm mid-use. The app recovers |
| Permission denied** | Say no to the mic or camera. The app explains and keeps working |

\* Apps that play sound (`app.audio: true`); the interruption check also applies to apps that use the
microphone or camera. Some audio bugs only exist on real phones.
\** For each permission in `app.permissions`.

Write the results in `store/device-check.json`, including `observedBy` — some of these need a
person.

### The recording

Apple asks new accounts for a screen recording from a real phone, starting on the Home Screen and
showing the app's normal use. You'll attach it to the submission and again to your reply if they
ask. Make it now.

**The agent makes it.** On our metronome the agent spent 25 minutes fighting a cable while iPhone
Mirroring, which had already worked for Noise, sat right there. I had to remind it. Now Mirroring
comes first:

1. The agent opens iPhone Mirroring on the Mac. If it says the phone is in use, I lock the phone and
   leave it by the Mac. After I unlock or reconnect anything, the agent chooses **Try Again**.
2. It starts from the Home Screen, opens the app and does the core job, and records only the
   Mirroring window.
3. It cuts it to Home Screen → the job → stop. Past about a minute, it speeds it up 2× (3× was too
   fast to read) and says so in the review notes. Apple's cap is three minutes.
4. It watches the whole thing before using it. On Feeds, Home Screen search showed one of my
   emails for a few seconds; the agent blurred it and said so.

Two things Mirroring won't do. It carries no app sound, and swipes come through as taps (so it goes
Home with ⌘1 and opens the app from Search). I record on the phone myself only when the app's sound
is the point, or when every agent route has failed after something actually changed:

1. Turn on **Do Not Disturb** (Control Center → Focus) so nothing pops up.
2. Go to the Home Screen.
3. Control Center → touch and hold **Screen Recording** → turn the **Microphone** on if the app
   makes sound → **Start Recording**.
4. Open the app. Do the core job. Twenty to sixty seconds is plenty; keep it under three minutes.
5. Stop from the red indicator. It's in **Photos**.
6. AirDrop it to the Mac, or plug in and use Image Capture.

If the app *listens* (a tuner, a recorder), leave the recorder's microphone off so it doesn't
compete with the app, and play the sound anyway — the screen shows the app reacting. Try it once
before the real take.

Every route, in order: [setup → recording the phone](setup.md#8-recording-the-phones-screen).

**Record the build you're shipping.** Watch the recording before the final build. If it shows
something to fix, fix it and record again. If you keep the earlier recording anyway (I did on Feeds),
the notes describe only what the video shows, say nothing about which build, and `app.json` says why.

Put the file next to `device-check.json` and fill in `video.file` and `video.sha256`
(`shasum -a 256 <file>`). The checker reads the duration from the file itself.

## Store screenshots

Take them now, from the build you just approved, so they show what Apple will review.

1. Boot a 6.9" simulator (an iPhone "Pro Max"), install the Release build, and launch it into each
   screenshot state from the brief:

   Launch it fresh each time, not from another app. One of our shots had a "◀ Open Feeds" back-link
   in the corner.

   ```bash
   xcrun simctl status_bar booted override --time 9:41 --batteryLevel 100
   xcrun simctl install booted build/sim/Build/Products/Release-iphonesimulator/App.app
   xcrun simctl launch booted com.example.app -demoState counting      # or SIMCTL_CHILD_DEMO=1 for env vars
   xcrun simctl io booted screenshot store/screenshots/01-raw.png
   ```

2. Simulator screenshots have an alpha channel, and Apple rejects that:
   `sips -s format jpeg store/screenshots/01-raw.png --out store/screenshots/01.jpg`
3. The first one shows the job being done. Three to five is plenty.

You need a 6.9" set (1320×2868). A 6.5" set alone is still accepted. Add 13" iPad if the app runs on
iPad. The checker reads the real image sizes.

## Changed something small after the checks?

If a later build only changed text or links, you don't have to redo everything. Add:

```json
"carryForward": { "toBuild": "7", "why": "only the store name and support links changed" }
```

The checker will accept it with a warning. Do at least open the new build and run the core job once.

When `check` says READY, set `phase` to `submit`.
