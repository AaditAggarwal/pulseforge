# GLOSSARY

Terms as this project uses them. Not textbook definitions. Add an entry the moment a term is first
used in anger, not before.

**Baseline** — the version of the target service the candidate is being compared against. Which commit
that is remains open; see `OPEN_QUESTIONS.md` Q1... Q3.

**Blast radius** — the set of endpoints and code paths a given diff can plausibly affect. The planner's
job is to estimate it and weight the workload toward it.

**Candidate** — the proposed version of the target service. The thing being judged.

**Corpus** — the stored set of sanitized captured requests available for replay.

**Coverage map** — the recorded association between a captured request and the code paths its handling
executed. Phase 03. This is what makes the planner possible.

**Gate** — the deterministic component that turns a comparison into PASS / BLOCK / INCONCLUSIVE and an
exit code. Never an LLM (R6).

**Noise floor** — the run-to-run variation observed when replaying baseline against itself. A candidate
delta smaller than this is not evidence of anything. See ADR-004.

**Plan / workload plan** — the frozen, hashed, ordered list of requests to replay, with seed and
concurrency. Generated once, read identically by both sides (R7).

**Plan ID** — the content hash of a workload plan. Two runs with identical inputs must produce the same
plan ID; there is a test asserting this.

**Target service** — the application under test. In this repo, the Phase 01 service. In a real
deployment, the customer's API.

**Verdict** — the machine-readable artifact carrying the decision, the rule that fired, the numbers
behind it, and the hashes of every input.
