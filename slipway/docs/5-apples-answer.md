# 5. Apple's answer

Apple says most submissions are reviewed within a day or two. On a new account, expect the first
answer to be a question.

Use the follow-up scope recorded in the approved release packet. Information-only replies and
same-build resubmission can be included there; if omitted, ask before sending. Defects and rule
problems return to the user. Monitoring runs only when a session or authorized scheduled job does.

## Watch for it

Check the review state twice a day while an app is with Apple:

```bash
asc review status --app <app-id>
```

The state alone doesn't tell you what Apple said. When it changes, read the message itself in App
Store Connect (App Review, in the browser). Also check your email; Apple sends notices there too.
Save the message word for word in the app's release folder the day it arrives. The next
submission's notes get checked against all of them.

## Read it, then sort it

| What Apple sent | What it looks like | What to do |
|---|---|---|
| **A question** | "Guideline 2.1 – Information Needed." They want answers or a recording; they don't name a bug | Reply and resubmit the same build. Fifteen minutes |
| **A problem** | They describe a crash, a broken feature, a misleading listing, a privacy mismatch | Fix it, with a failing test first. New build number, back through phases 3 and 4 |
| **A rule** | They cite 4.3 spam, 4.2 minimum functionality, 5.2 intellectual property | Stop. That's a product question for you, not a fix |

"Rejected" on its own doesn't mean the build is bad.

## The question (you'll get it)

New accounts get "Guideline 2.1 – Information Needed – New App Submission" on their first apps.
Our first four apps all got it (as of October 12, 2026), including ones whose notes already answered
every question, and once a few hours after a sibling app was approved. It isn't about your app. Answer it fast:

1. **Reply in App Store Connect** (App Review → the message → Reply). Paste
   `store/review-reply.txt` as plain text, and **attach the recording to the reply itself** —
   even though it's already on the submission. Wait for the attachment to finish uploading before
   sending.
2. **Read it back.** Your message, its time, and the attachment are all in the thread. A filled-in
   reply box isn't a sent message.
3. **Resubmit. Replying doesn't resubmit.** The first time, the agent sent the reply and stopped,
   and I had to ask, "Are we supposed to resubmit it?" That is why final approval includes optional reply-and-resubmit scope.
   The version stays tied to the original submission, so mark the rejected item resolved and
   resubmit *that* submission:

   ```bash
   asc review items list --submission <original-submission-id>
   asc review items update --id <rejected-item-id> --resolved true
   asc review submissions-submit --id <original-submission-id> --confirm
   asc review status --app <app-id>       # must read WAITING_FOR_REVIEW
   ```

   Some high-level submit commands try to make a new submission here, fail, and leave an empty
   draft. Leave the draft alone. A greyed-out Resubmit button on the website isn't the final word
   either — trust the read-back.

Our first approval came about a day and a half after resubmitting, with no more questions.

## When Apple cites a rule

Ask one clear question in the reply if the reason isn't clear. If you think they're wrong, the
[App Review Board](https://developer.apple.com/contact/app-store/?topic=appeal) is the place to say
so, with the differentiation spelled out.

What you don't do is resubmit the same app again and again. Apple's spam guideline says
"repeated submissions … may lead to removal from the Apple Developer Program." After a second spam
rejection, fold the app into a sibling, rethink what makes it different, or drop it. Write down
why in the catalog. It's the first thing to read next time you pick.

## Live

With `AFTER_APPROVAL` the app goes live when it's approved. With `MANUAL` somebody has to press
Release, so set a reminder.

- **Check it's really out.** `https://itunes.apple.com/lookup?bundleId=com.example.app` returns the
  listing once it's public. Install it from the store on a phone.
- **Update your records:** `phase: live`, the catalog, your tracker.
- **Fix any temporary URLs** with permanent redirects. Never break a link a shipped app uses.
- **Set two check-in dates** in `app.json` → `next`, 30 and 90 days out. App Store Connect's own
  numbers (impressions → page views → downloads) are enough, with no analytics in the app, but only
  once Analytics Reports are switched on for that app. Do it on submission day; ours weren't on, and
  Tally's first numbers weren't there when I went looking. Keep your vendor number handy too: Sales
  reports need it.
- **Write the kill rule now**, while you're not attached: "under N downloads a month at 90 days →
  fold into a sibling or retire."
- **Update every app you keep at least once a year.** Apple may remove apps in crowded categories
  "if they are not updated, improved, or do not attract customers."

To retire an app: remove it from sale in App Store Connect, keep its support and privacy pages up
for people who have it, set `phase: retired`, and say why in the catalog.
