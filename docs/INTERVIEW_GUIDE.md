# INTERVIEW_GUIDE

Questions and answers grounded in what was actually built. A question is added when the code that
answers it exists, not before. An answer citing a number must cite a number from `BENCHMARKS.md`.

## Status

No implemented code yet. Questions below are the ones Phase 00 decisions must survive.

## Phase 00

**Why in-process middleware instead of a proxy?**
See ADR-001. Short answer: the product differentiator depends on knowing which code paths a request
executed. A proxy sees paths, not route templates or handler identity, and would need a second
instrumentation mechanism plus cross-process correlation to recover what middleware gets for free.
The cost is that only Python ASGI services are supported.

**Why not just threshold p95 at 10%?**
See ADR-004. A threshold below the environment noise floor produces false blocks, and a gate that
produces false blocks gets switched off. The floor has to be measured rather than assumed, which costs
an extra baseline-vs-baseline replay per run.

**Why BSL rather than MIT?**
See ADR-003. Relicensing is impossible once outside contributors hold copyright. BSL costs nothing now
and preserves the option; the permissive direction stays available at any time, the reverse does not.

**Why build the gate before the AI planner, when the planner is the differentiator?**
The planner shapes which requests get replayed. Evaluating a planner requires a trustworthy comparison
engine to evaluate it against. Building it first would mean tuning an input to a system whose output
cannot yet be believed.

**How do you guarantee baseline and candidate get identical workloads?**
R7. The plan is generated once, content-hashed, frozen to disk, and read by both runs. The replay
engine receives a base URL and a plan and has no knowledge that baseline and candidate differ, so there
is no branch that could produce divergence. There is a test asserting plan-ID stability.
