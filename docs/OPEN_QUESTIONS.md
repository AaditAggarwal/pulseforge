# OPEN_QUESTIONS

Unresolved design questions, with the options and the current lean. A question leaves this file only
by becoming an ADR or by being answered and deleted with a note in `DEVELOPMENT_LOG.md`.

## ~~Q1 — Development environment~~ RESOLVED 2026-08-30
WSL2 on the Linux filesystem, at `~/projects/pulseforge`. See ADR-005, now Accepted.

## Q2 — Corpus request-body storage
Store bodies inline in JSONL, or content-address them separately and reference by hash.
Inline is simpler; separate deduplicates identical bodies and keeps manifests small enough to read.
**Lean:** inline until a measured reason exists to split.
**Resolve by:** Phase 02.

## Q3 — What "baseline" means in practice
The currently-deployed commit, the merge-base of the PR, or a pinned tag.
Merge-base is the most correct comparison; deployed is the most operationally meaningful.
**Lean:** merge-base, configurable.
**Resolve by:** Phase 06.

## Q4 — Statefulness of replay
Captured traffic includes writes. Replaying a POST twice against a shared database changes results.
Options: reset database between runs, replay reads only, or accept the divergence and document it.
This is the single hardest correctness problem in the project.
**Lean:** unknown. Needs real thought in Phase 04, not a guess now.
**Resolve by:** Phase 04.

## Q5 — OpenRouter model choice and cost ceiling
Budget is roughly $4. Planner calls must be cheap enough to run per-PR.
**Lean:** cheapest model that reliably emits valid JSON against the schema; measure in Phase 08.
**Resolve by:** Phase 07.

## Q6 — AWS credit balance and expiry
Account created ~2026-08-28, upgraded to Paid Plan. Actual credit balance and expiry NOT YET VERIFIED.
**Resolve by:** before any Phase 11 work. Check Billing console, paste the numbers.
