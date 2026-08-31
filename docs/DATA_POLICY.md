# DATA_POLICY

What PulseForge captures, what it strips, how long it keeps it, and the legal obligations that follow.
This file exists from Phase 00 because a product recording user traffic cannot have its data policy
written retroactively.

## Status

Design intent only. Nothing implemented; capture is Phase 02.

## What is captured

Per request: method, route template, path, query parameters, allowlisted headers, request body,
response status, response body, timing. Plus the Phase 03 coverage record.

## What is stripped, always

Every header not on the allowlist, unconditionally including `Authorization`, `Cookie` and `Set-Cookie`
on all responses including redirects. Body fields matching configured redaction paths. Values matching
PII and secret patterns, as a second layer. Mechanism in `SECURITY.md`.

## Retention

Default retention must be short and configurable, and deletion must be automatic rather than a
documented manual procedure. **NOT YET DECIDED** — set in Phase 02 and recorded here.

## Storage location

Local filesystem in V0 (ADR-002). Phase 11 moves this to S3, at which point the geographic region
becomes a compliance-relevant choice and is recorded here.

## Legal obligations if this is ever distributed

Recording end-user API traffic implicates GDPR and CCPA. Before any external use this file must state:
the lawful basis for processing, the retention period and its automatic enforcement, the geographic
storage location, sub-processors involved, and how a data subject deletion request is honoured.
Encryption at rest and in transit is required, not optional.

There is currently no intent to distribute or sell (ADR-003). If that changes, this section becomes
blocking engineering work, not paperwork.
