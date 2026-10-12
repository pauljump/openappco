# Before your first app

Start with the [executable connection inventory and offline rehearsal](durable-work.md#first-clone).
The sections below explain the human setup steps; a discovered tool is not a verified connection.

Do this once. Most of it happens in a browser or on the phone, and some of it waits on Apple. When
you're done, `python3 tools/slipway.py doctor` should come back clean.

Checked against Apple's docs in **October 2026**, with Xcode 27 and iOS 27. Dated items are marked
**[dated]**.

- [1. The Apple Developer account](#1-the-apple-developer-account)
- [2. Agreements and the EU trader question](#2-agreements-and-the-eu-trader-question)
- [3. The API key](#3-the-api-key)
- [4. Tools on the Mac](#4-tools-on-the-mac)
- [5. Being signed in](#5-being-signed-in)
- [6. Signing without anyone at the screen](#6-signing-without-anyone-at-the-screen)
- [7. Your phone](#7-your-phone)
- [8. Recording the phone's screen](#8-recording-the-phones-screen)
- [9. Support and privacy pages](#9-support-and-privacy-pages)
- [10. Run the doctor](#10-run-the-doctor)

---

## 1. The Apple Developer account

$99 a year. Decide one thing first: **individual or organization.**

- **Individual:** your legal name is the seller on every app you ship. Quick to set up.
- **Organization:** your company's name is the seller. You need a real legal entity (an LLC is
  fine; a DBA isn't), a D-U-N-S number (free, up to about a week), a website and an email on its
  domain.

Apple doesn't publish how long approval takes. Start now.
([Enroll](https://developer.apple.com/programs/enroll/), [D-U-N-S](https://developer.apple.com/support/D-U-N-S/))

**Your developer name, shown under every app, is set when you create your first app record, and
you can't edit it later.** An individual's is their legal name; an organization can use a registered
trade name or DBA. So decide individual vs organization, and the name, before that first record. We
didn't think about it until it was already set.
([Apple](https://developer.apple.com/help/app-store-connect/create-an-app-record/set-your-developer-name),
checked October 2026 **[dated]**)

## 2. Agreements and the EU trader question

**Free apps need no tax or banking setup.** They ship under the agreement you accept when you
enroll. Tax forms and banking come with the Paid Apps Agreement, which you only need to sell
something.

**When Apple updates its agreement, everything quietly stops.** You can't create apps (and often
can't submit) until the account holder accepts it in App Store Connect → Business. If something
fails for no visible reason, look there first.

**Every account has to declare EU trader status**, even if you never sell in the EU. Since
**February 17, 2025 [dated]**, apps without it are pulled from EU storefronts.
([Apple](https://developer.apple.com/help/app-store-connect/manage-compliance-information/manage-european-union-digital-services-act-trader-requirements/))

- **Trader:** your address, phone and email are shown on every EU product page. A P.O. box is
  allowed for individuals.
- **Non-trader:** nothing is shown. Apple's own examples suggest a hobbyist with no plan to make
  money may not be a trader. It's your call, not Apple's, and this isn't legal advice.
- Don't want your home address public? Declare non-trader if that's honestly true, use a P.O. box
  and a separate phone and email, or leave the EU out of your availability.

Where: Business → Agreements → Compliance → Digital Services Act. Browser only.

## 3. The API key

The API key is how the command line — and your agent — works with App Store Connect without
anyone signing in: versions, metadata, screenshots, uploads, submissions.

1. **Request access** (account holder, once): Users and Access → Integrations → Request Access.
2. **Make a team key** (account holder or admin): Integrations → Team Keys → **+**.
   - Role: **App Manager**. It can do everything here. The Developer role can't create apps or
     submit. Only use Admin if the key also has to manage users or signing certificates.
   - Use a *team* key. Individual keys can't do provisioning, so automatic signing fails.
3. **Download the `.p8` file. You only get one chance.** Apple keeps no copy. Lose it and you revoke
   and start over.
4. Write down the **Issuer ID** (top of the Integrations page) and the **Key ID** (next to the key).
5. **Keep it out of every repository.** Put the `.p8` in a secrets folder with `chmod 600`, or in your
   password manager. Tools get the path and the IDs from environment variables, nothing more.

([Apple: API keys](https://developer.apple.com/documentation/appstoreconnectapi/creating-api-keys-for-app-store-connect-api))

## 4. Tools on the Mac

- **Xcode 26 or newer** (uploads require it since **April 28, 2026 [dated]**). After installing, run
  `sudo xcode-select -s /Applications/Xcode.app` and open Xcode once to finish setup.
- **An App Store Connect command line.** We use [`asc`](https://github.com/rorkai/App-Store-Connect-CLI)
  (unofficial, MIT, `brew install asc`). [fastlane](https://docs.fastlane.tools/) works too. Pick
  one and let only that one write to App Store Connect.
- **Python 3.10+** for `tools/slipway.py`. Nothing to install.

**Your Team ID** (ExportOptions.plist needs it): [developer.apple.com/account](https://developer.apple.com/account)
→ Membership details. It's ten characters.

Put the key somewhere safe and wire it into `asc` with a small wrapper, so no credentials end up in
config files. Using the macOS Keychain:

```sh
mkdir -p ~/.secrets && chmod 700 ~/.secrets
mv ~/Downloads/AuthKey_XXXXXXXXXX.p8 ~/.secrets/ && chmod 600 ~/.secrets/AuthKey_*.p8
security add-generic-password -s asc-key-id -a "$USER" -w XXXXXXXXXX
security add-generic-password -s asc-issuer-id -a "$USER" -w 00000000-0000-0000-0000-000000000000
mkdir -p ~/bin   # and make sure ~/bin is on your PATH
```

```sh
#!/bin/sh
# ~/bin/asc-env (chmod 700)
export ASC_KEY_ID="$(security find-generic-password -s asc-key-id -w)"
export ASC_ISSUER_ID="$(security find-generic-password -s asc-issuer-id -w)"
export ASC_PRIVATE_KEY_PATH="$(ls ~/.secrets/AuthKey_*.p8 | head -1)"
export ASC_KEY_TYPE=team
export ASC_STRICT_AUTH=1                         # refuse credentials mixed from several places
export ASC_TELEMETRY_DISABLED=1 DO_NOT_TRACK=1   # asc sends usage data by default
export ASC_WEB_DONT_STORE_PASSWORD=1
exec asc "$@"
```

Then `asc-env auth doctor` should report no errors, and `asc-env apps list --limit 1` should print
your apps (or an empty list) instead of an authentication error. `xcodebuild` takes
the same three values as `-authenticationKeyPath`, `-authenticationKeyID` and
`-authenticationKeyIssuerID`.

## 5. Being signed in

There are four different kinds of "signed in", and none of them signs in the others.

| What | Used for | How long it lasts |
|---|---|---|
| **The API key** | Almost everything: metadata, uploads, submitting, signing builds | Until you revoke it |
| **App Store Connect in a browser** (Apple Account + two-factor) | The steps the API can't do: creating the app record, publishing the privacy label, replying to App Review, agreements, EU trader status | Apple doesn't say. Plan on it expiring |
| **`asc`'s own web session** (`asc web auth login --apple-id you@…`, password + two-factor) | Doing the browser-only steps from the command line, like `asc web apps create`. It uses private Apple endpoints that can change | Cached by `asc`; expect to log in again |
| **Xcode → Settings → Apple Accounts** | Only if you sign in Xcode instead of using the key | Not needed if you pass the key to `xcodebuild` |

- **Keep everything you can on the API key.** It never expires on you mid-run.
- **Check the existing App Store Connect session before asking for sign-in.** Only authenticate if
  it has expired, in the browser on the Mac the agent actually uses. Record the observation and scope
  in the private connection inventory.
- **Group the browser-only steps** so they happen in one short window while you're around.

## 6. Signing without anyone at the screen

Agents usually run builds over SSH or in the background. There, `codesign` often fails with
`errSecInternalComponent` because the login keychain is locked outside the desktop session. Fix
it now, not on ship day:

- Run builds inside the logged-in desktop session, **or**
- Keep a dedicated signing keychain, and unlock it at the start of the build script from your
  secrets store (`security unlock-keychain -p "$PW" ~/Library/Keychains/signing.keychain-db`).
  Never put that password in a repository.

Reuse the existing signing identity/profile first and verify a disposable signing probe.
If provisioning changes are authorized, use **automatic signing** with `-allowProvisioningUpdates` and the API key flags. Xcode creates the
bundle ID, profiles and certificates as needed. That *does* write to your developer account —
decide whether your agent may do it on its own.

For a brand-new bundle ID, a development profile that includes your phone has to exist before
you can install on it. Use `-allowProvisioningDeviceRegistration` only when registering that
phone is explicitly authorized.

## 7. Your phone

You need one real iPhone, on a current iOS, that the Mac can install to. This is the part people
skip and then lose an afternoon to.

**Pair it (once):**

1. Plug the phone into the Mac with a cable and unlock it.
2. Tap **Trust This Computer** and enter the passcode.
3. In Xcode 27: **Xcode → Open Developer Tool → Device Hub**, pick the phone, click **Pair** if it's
   there. (Xcode 26 and earlier: **Window → Devices and Simulators**, and tick **Connect via
   network** so you can unplug later.)
4. After pairing once by cable, the phone can install and run apps over Wi-Fi on the same network.
   Pairing with no cable at all needs iOS 27. Updating iOS means pairing again.

**Turn on Developer Mode:** on the phone, **Settings → Privacy & Security → Developer Mode** (near
the bottom), on, **Restart**, then confirm with your passcode after it reboots. The switch only
shows up after the phone has been paired to a Mac.
([Apple](https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device))

**Keep it ready while testing:**

- **Settings → Display & Brightness → Auto-Lock** to the longest option.
- Keep it charging, and **Low Power Mode off** (it forces Auto-Lock to 30 seconds).
- **Unlocking is the one thing that stays manual.** Installs work on a locked phone; launching,
  recording and UI tests don't.

**Check it from the Mac:**

```bash
xcrun devicectl list devices        # the Identifier column is the <UDID> later commands need
python3 tools/slipway.py doctor     # paired? Developer Mode? reachable right now?
```

**When it fails:**

| Error | Means | Do |
|---|---|---|
| `CoreDeviceError 4016` "usage assertion requirements" | The Mac can't reach the phone | Plug in the cable, wake and unlock the phone |
| `CoreDeviceError 10002` with `Locked` inside | The phone is locked. The install probably worked | Unlock, run only the launch again |
| `10002` with `Bad executable` inside | A signing or profile problem, not the lock | Check the phone is in the profile, and the build is development-signed |
| `CoreDeviceError 12040`, "Developer Mode is disabled" | Developer Mode is off | Turn it on (above) |
| "must be paired", or the phone isn't listed | Not trusted, or iOS was updated | Cable, Trust, Pair again |
| `CoreDeviceError 4000` "disconnected immediately" | Flaky Wi-Fi tunnel | Retry, or use the cable |
| Install fails and the Mac lists the phone as "unavailable" | Usually just locked | Check the lock state first and say "unlock it", before calling the phone offline |
| Cable plugged in, but the Mac sees no USB device | iOS is blocking wired accessories | On the phone: Settings → Privacy & Security → Wired Accessories → **Always Allow**. Replug with the phone unlocked, tap Trust, pair again |

## 8. Recording the phone's screen

New accounts get asked for a screen recording from a real phone, starting on the Home Screen. Know
how you'll make one before you need it. The agent makes it. In the order we try them:

1. **iPhone Mirroring + window capture.** Wireless, and the agent can drive it end to end: open
   Mirroring, choose **Try Again** after you unlock or reconnect, go to the Home Screen, do the demo,
   record only the Mirroring window. It needs
   ([Apple](https://support.apple.com/en-us/120421), checked October 2026 **[dated]**):
   - the phone locked, near the Mac and untouched;
   - the same Apple Account on both, with two-factor, and Wi-Fi and Bluetooth on;
   - the Mac not using AirPlay, Sidecar or Internet Sharing;
   - not the EU, where Apple doesn't offer it.

   Apple's list doesn't mention them, but we also keep Handoff on and Personal Hotspot off.

   To record, find the Mirroring window's ID and run
   `screencapture -x -v -V 45 -l <window-id> demo.mov`. Let the timer finish: interrupting it
   threw the movie away. It has no app sound, and swipes arrive as taps, so go Home with ⌘1 and open
   the app from Search.
2. **`devicectl` from the command line (Xcode 27+).**

   ```bash
   xcrun devicectl device capture screen-record --device <UDID> --destination demo.mp4 --duration 45
   ```

   Start it on the Home Screen, then launch the app. No sound, and someone (or a UI test) still has
   to drive the app. Not every phone supports it: ours reports it unsupported. Check once, then move
   on.
3. **The phone's own Screen Recording.** The only route with the app's sound. I use it when the sound
   is the point, or when every agent route has failed after something actually changed.
   - Add it once: Control Center → **+** → **Add a Control** → **Screen Recording**.
   - To record:
     1. Turn on Do Not Disturb.
     2. Go to the Home Screen.
     3. Touch and hold **Screen Recording** in Control Center and turn the **Microphone** on if the
        app makes sound.
     4. Start, use the app, stop from the red indicator.
   - It lands in Photos. Move it to the Mac with AirDrop, or plug in and use **Image Capture**.
4. **QuickTime Player, phone plugged in by cable.** The fallback.
   1. Choose **File → New Movie Recording**.
   2. Click the arrow next to Record and set **Camera: your iPhone** and **Microphone: your
      iPhone** (that captures the phone's sound).
   3. Record, then **File → Save**.

   This needs the cable — it doesn't work over Wi-Fi — and an unlocked, trusted phone.

For apps that work with *hardware*, Apple wants "a video (not a screen recording)" of the phone and
the device together. Film it with another camera.

Keep the finished file under three minutes, check that it opens, and check that it starts on the
Home Screen.

## 9. Support and privacy pages

Every app needs a Support URL that "must lead to actual contact information" and a Privacy Policy
URL. A static site is enough (GitHub Pages, Cloudflare Pages, Netlify).

- **One host and one pattern for every app**, decided before the first submission:
  `https://yourstudio.com/<app>/support/` and `/privacy/`. Moving them later means redirects
  forever.
- **Not on a machine that can go offline** while Apple is reviewing.
- **A contact address you're happy to have public**, such as a support alias, not your personal
  inbox.
- If the site has analytics, say so in one sentence and use the same sentence on every page.
- **On GitHub Pages, if HTTPS hasn't issued after an hour,** remove the custom domain and add it back.
  Ours issued about 30 seconds later. GitHub records that as two commits to your `CNAME` file, so
  pull before you push again.

Templates: [support.html](../templates/app/web/support.html), [privacy.html](../templates/app/web/privacy.html).

## 10. Run the doctor

```bash
python3 tools/slipway.py doctor          # local checks
python3 tools/slipway.py doctor --api    # plus one read-only App Store Connect call
```

For the key checks, run it in a shell where your wrapper's variables are set.

It checks:
- Xcode and the selected toolchain;
- `asc` and the key variables, without printing them;
- that the `.p8` isn't readable by others;
- signing identity inventory and keychain information (a signing probe is still required);
- your phone: discovery, pairing and Developer Mode (a device operation verifies reachability);
- which recording routes are advertised (device support and permission need separate verification).

Warnings mean setup is incomplete; they do not establish release readiness. "Phone not reachable" just means it isn't plugged in at the
moment.

## The whole list

- [ ] Individual or organization decided, and the developer name, before the first app record; enrolled
- [ ] Business → Agreements has nothing waiting
- [ ] **EU trader status declared**
- [ ] Team API key (App Manager), `.p8` stored safely, IDs in your secrets store
- [ ] Xcode ≥ 26, `asc` (or fastlane) with a wrapper; `auth doctor` passes
- [ ] A sample app archives headlessly with the key (the keychain problem is solved)
- [ ] Phone paired, Developer Mode on, Auto-Lock long
- [ ] You know which way you'll record the screen, and you've done it once
- [ ] Support and privacy hosting decided, one URL pattern, a public-safe contact address
- [ ] Review contact decided — Apple needs a name, phone and email (only Apple sees them)
- [ ] Vendor number recorded (App Store Connect → Payments and Financial Reports, top left); Sales
      reports need it
- [ ] `slipway.py doctor` clean apart from warnings you understand
