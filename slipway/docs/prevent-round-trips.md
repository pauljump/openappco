# What Apple sent back, and how to never get it again

Every line here cost us a rejected upload, a round trip with Apple, or a stalled evening. Each is
cheap in the phase listed and expensive on ship day. Before I say "get it submitted," the agent goes
down this list and shows me every line checked off.

| Settle it in | What | What happened when we didn't |
|---|---|---|
| 1 Pick | The store name is free, and there's a fallback | Couldn't create the app record on ship day; the icon and screenshots already said the name |
| 1 Pick | The one sentence on what's better, and the catalog check | Risk of a spam rejection, and account standing, in crowded categories |
| 2 Build it | Home Screen name set explicitly, and read back after every change | A build came back with the space missing from the name. It took two corrections |
| 2 Build it | One host for support and privacy pages | Four apps ended up on three different URL patterns, one of them on a machine that could go offline during review |
| 2 Build it | Privacy answer, content rights, release type, sign-in off, Support/Privacy links in the app | Unpublished privacy blocked a submission for days; content rights never set; one app on manual release would have sat unreleased; links added at the last minute |
| 2 Build it | Every network call, including from shared code; no payment links, no competitor names in the app | A dry run caught a shared component in an unsubmitted app that did all three. Nobody had looked, because nobody wrote it for that app |
| 2 Build it | Every claim in the listing, pages and notes matches the code: made on the phone, bundled, or made with AI during development | Noise's copy said its sound was "generated locally." I asked whether that was even true. The privacy page and review notes were rewritten twice |
| 2 Build it | Look approved before building, when it's new | The colors got rejected after the build, so visuals, icon and screenshots were redone |
| 2 Build it | `CFBundlePackageType = APPL` | Upload failed processing (ITMS-90183) and cost a build number. An older prototype had the same gap |
| 2 Build it | Archive in a numbered folder; check the archived Info.plist | The release folder held an older build than the one uploaded |
| Setup | Headless signing works | `errSecInternalComponent` on three different apps |
| Before phone handoff | One complete user checklist, including capture permissions and all device QA | Permission and accessibility requests arrived one at a time after the app seemed ready |
| 3 On my phone | The checks and the recording, right when it feels done | The recording happened on ship day through a 25-minute detour, and came out silent for an audio app |
| 3 On my phone | The agent records through iPhone Mirroring first | On Metronome it fought a cable for 25 minutes while Mirroring, which had already worked for Noise, sat unused |
| 3 On my phone | Record from the exact build you submit, or say in the notes that you didn't | On Feeds the video came from the build before the one we sent. The notes had to drop every build claim |
| 3 On my phone | Audio tested on hardware | A setting that worked in the simulator threw an error on real phones |
| 4 Get it submitted | Reuse sign-in; one up-front ask, then one final packet that names submission, publication and follow-up scope | Expired sessions stalled almost every submission. Asking step by step cost a round trip each: one app got three separate approval requests, and one reply went out without the resubmit |
| 4 Get it submitted | Notes are plain text, six numbered answers, under 4,000 bytes | Asterisks showed up literally; unnumbered notes didn't match what Apple asked for |
| 4 Get it submitted | Keywords don't repeat the name; subtitle 30 characters at most | Validator failures on upload day |
| 4 Get it submitted | Screenshots at 6.9", no alpha, right orientation | Landscape screenshots went up sideways |
| 4 Get it submitted | App record version matches the binary | The record said `1.0`, the binary said `1.0.0` |
| 4 Get it submitted | "Sign-in required" (the demo account) is off, read back | It defaulted to on, and validation demanded a demo username and password for an app with no login |
| 4 Get it submitted | An app that opens web pages declares Unrestricted Web Access; one that shows publishers' content declares third-party content | Our feed reader needed both; the offline defaults would have under-declared it |
| 4 Get it submitted | Screenshots uploaded one at a time, then read back | A folder upload timed out on one file and rolled back the others |
| 4 Get it submitted | Public tracker destination/assets included in final approval | Publication was blocked after Apple submission because only Apple submission had been approved |
| 4 Get it submitted | Tracker updated when you submit | A submitted app was missing from our public page until somebody noticed |
| 5 Apple's answer | Resubmit the *original* submission after a question | A high-level submit command made an empty draft and failed |

## What you can't prevent

The new-account question — "Guideline 2.1 – Information Needed – New App Submission." We answered
everything up front, recording included, and still got it every time, once just hours after
another app was approved. You can't avoid it. You can answer it in fifteen minutes:

1. The notes already have the six answers.
2. The reply is ready to paste.
3. The recording is ready to attach.
4. The final approval explicitly covered reply-and-resubmit.
5. Someone looks twice a day while an app is with Apple.
