# Workflow 2: App Review response and resubmission

Start from Apple's complete message and the current remote state. The word
`REJECTED` alone does not prove that the binary needs to change.

## 1. Classify the notice

- **Information request:** Apple asks for context, access, evidence, or answers
  but identifies no binary or metadata defect.
- **Binary or metadata defect:** Apple identifies a reproducible bug, missing
  behavior, misleading listing, invalid package, or other concrete correction.
- **Policy issue:** Apple cites a rule that may require product, rights,
  business-model, entitlement, or distribution changes.

Do not use the information-only lane when Apple identified a substantive defect.

## 2. Information-only lane

For a Guideline 2.1 “Information Needed — New App Submission” request or an
equivalent limited-history request:

1. Prepare a direct Resolution Center reply using the six numbered answers in
   [the response template](templates/reviewer-response.txt).
2. Attach the exact final-build physical-device recording to the message again,
   even if it already appears as a processed App Review attachment.
3. Send only with current authorization to communicate externally.
4. Read the sent thread back. Verify the sender and timestamp, the complete
   reply, the attachment filename, and that the attachment can be downloaded.
   An upload indicator or populated composer is not proof that Apple received it.
5. Save a private receipt without publishing personal contact details or Apple's
   private message.

Open Noise received this request even though its six-part Notes and processed
review attachment were already present. Pre-submission evidence reduces response
time; it does not guarantee Apple will skip the request.

## 3. Decide whether the build changes

Keep the exact validated build when Apple requested only information and no code
or metadata correction is required. Run current review diagnostics and a
submission dry-run if your tool supports them. A disabled web resubmit button is
not by itself proof that a replacement build is needed; reconcile the API and
web states before rebuilding.

Build and test a new release candidate only when the notice or investigation
establishes a defect that the prior build cannot satisfy. Record what changed
and replace the packet's build identity everywhere.

## 4. Resubmit deliberately

Sending the reply and resubmitting are separate external actions unless the
current instruction explicitly authorizes both. Immediately before resubmitting,
verify the version and exact build again and obtain any needed current approval.

## 5. Read back and retain evidence

Require `WAITING_FOR_REVIEW` or another active review state after resubmission.
Retain the response text, attachment metadata/hash, sent-message evidence,
exact build ID, resubmission receipt, and final state privately. A click without
read-back is not a completed workflow.

For a binary, metadata, or policy issue, document the cited issue, reproduction
or interpretation, correction, verification, and new build identity before
returning to [the initial submission workflow](SUBMIT.md).
