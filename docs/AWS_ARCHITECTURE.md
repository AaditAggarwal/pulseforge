# AWS_ARCHITECTURE

Every AWS resource: purpose, cost, security posture, teardown command, teardown verification.

## Status

**No AWS resources exist.** Phase 11. Nothing may be created before the billing alarm exists.

## Account facts

- Account created ~2026-08-28, upgraded to Paid Plan to use Textract
- Free-tier credit balance and expiry: **NOT YET VERIFIED** (`OPEN_QUESTIONS.md` Q6)
- Billing alarm: **not configured**

## Resource table (empty)

| Resource | Purpose | Hourly cost | Free tier? | Surprise-bill risk | Teardown | Verified gone |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

## Rules

- Least-privilege IAM from the start. Never `*` on actions or resources, not even temporarily.
- Every resource is created by Terraform. Nothing is created by hand in the console.
- Before any resource is created, its hourly cost, free-tier status, teardown command, and teardown
  verification are recorded in the table above.
