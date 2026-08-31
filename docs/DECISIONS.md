# DECISIONS

Numbered architecture decision records. **Append-only.** Supersede, never delete or edit a decision's
substance. Typo fixes are fine; changes of mind get a new ADR that names the one it replaces.

| ADR | Title | Status | Phase |
|---|---|---|---|
| 001 | Capture traffic via in-process ASGI middleware | Accepted | 00 |
| 002 | Content-addressed files on local filesystem for artifacts | Accepted | 00 |
| 003 | Business Source License 1.1 | Accepted | 00 |
| 004 | Regression defined as delta against a measured noise floor | Accepted | 00 |
| 005 | Develop inside WSL2 on the Linux filesystem | Accepted | 00 |
| 006 | Python 3.12 + uv + ruff + mypy --strict | Accepted | 00 |

---

## ADR-001: Capture traffic via in-process ASGI middleware
Status: Accepted
Date: 2026-08-30
Phase: 00

**Context:** PulseForge cannot replay traffic it has not recorded. The recording mechanism determines
the install story, whether sanitization can be a true security boundary, and — critically — whether
Phase 03 can attribute a request to the code paths it executed.

**Options:**

- *ASGI middleware inside the target application.* Requires a code change in the customer application
  and restricts PulseForge to Python/ASGI services. In exchange: exact route and handler attribution
  for free, sanitization before the bytes ever leave the process, and coverage instrumentation running
  in the same process as the request being recorded.
- *Reverse-proxy sidecar (Envoy, nginx, mitmproxy).* Language-agnostic, no application change, a
  materially better install story. But a proxy sees a URL path, not a route template or a handler
  function. `/orders/12345` and `/orders/99` look like unrelated endpoints, and the proxy cannot know
  which functions ran. Phase 03 would need a second, separate instrumentation mechanism, and
  correlating the two across process boundaries becomes its own distributed-systems problem.
- *Kernel-level capture (eBPF, tcpdump).* No application change at all, but TLS puts the interesting
  bytes out of reach, sanitization would necessarily happen after capture (violating the rule that the
  raw write is the incident), and route attribution is strictly worse than the proxy option.

**Decision:** In-process ASGI middleware.

**Reasoning:** The differentiator of this product is change-aware workload weighting, which depends
entirely on knowing which requests exercised which code paths. Options 2 and 3 are blind to exactly
that. Choosing either means building the easy 80% of a commodity load-testing tool and being unable to
build the part that makes it worth anything. The sanitization argument is independent and points the
same way: middleware can redact before the first byte reaches a disk.

**Tradeoffs:** PulseForge supports only Python ASGI applications (FastAPI, Starlette, Django ASGI).
Users must add a middleware line and redeploy before capturing. Capture adds per-request overhead
inside the hot path, which must be measured in Phase 02 and must be disableable.

**Consequences:** Makes easy — route templates, handler identity, coverage instrumentation,
sanitization-before-write. Makes hard — supporting Go/Node/Java services, which would need a second
capture implementation writing the same corpus format. The corpus format must therefore avoid encoding
Python-specific concepts, so a future non-Python capturer can produce identical artifacts.

**Revisit if:** A non-Python service becomes a requirement, or measured capture overhead exceeds a few
percent of request latency.

---

## ADR-002: Content-addressed files on local filesystem for artifacts
Status: Accepted
Date: 2026-08-30
Phase: 00

**Context:** Corpora, workload plans, replay results, and verdicts must be persisted. R7 requires
baseline and candidate to read a byte-identical plan, and the engineering standards require every
artifact to be content-addressed by hash. Phase 11 moves storage to S3.

**Options:**

- *Content-addressed files plus JSONL manifests on the local filesystem.* No query capability; any
  analysis means loading records into memory. Produces many small files.
- *SQLite.* Real queries, transactions, one file to move around. But a binary artifact is not diffable
  and not greppable, and it does not map onto object storage without an export step. Concurrent writers
  from Phase 09 workers become a locking problem.
- *Parquet.* Strong compression and columnar analytics for replay results. Poor fit for the corpus,
  whose request bodies are heterogeneous; requires pyarrow; unreadable without tooling.

**Decision:** Content-addressed files with JSONL manifests on the local filesystem, behind an
`app/storage` seam.

**Reasoning:** Hashing is already mandatory, so content addressing costs nothing extra. A file path
maps one-to-one onto an S3 key, making Phase 11 a swap rather than a migration. Every artifact stays
greppable and diffable by a human at 3am, which is the operational property that matters most in a tool
whose entire output is a judgement somebody will dispute.

**Tradeoffs:** No ad-hoc querying — analytics across runs means writing code, not SQL. Thousands of
small files stress filesystems that handle them badly, which is directly relevant to ADR-005.

**Consequences:** Makes easy — S3 migration, reproducibility, human inspection, immutability. Makes
hard — cross-run trend analysis and any dashboard needing aggregate queries. If Phase 12 wants trend
charts, results will need exporting to something queryable; that is a new ADR, not a reversal of this one.

**Revisit if:** Cross-run analytics becomes a product requirement, or artifact counts make directory
listing a bottleneck.

---

## ADR-003: Business Source License 1.1
Status: Accepted
Date: 2026-08-30
Phase: 00

**Context:** The license must be chosen before contributors exist. Once third parties hold copyright in
the codebase, relicensing requires their consent, which in practice means it cannot be done. There is
no near-term intent to sell PulseForge, but the option should be preserved rather than foreclosed by an
early default.

**Options:**

- *MIT / Apache 2.0.* Maximum adoption and contribution. Permits anyone, including a well-funded
  competitor, to run PulseForge as a commercial hosted service. Irreversible once contributors exist.
- *Business Source License 1.1.* Source-visible, free for non-production and internal use, forbids
  offering it as a competing hosted service, converts automatically to Apache 2.0 on a fixed Change
  Date. Not OSI-approved, which costs some goodwill and some contributors.
- *Elastic License 2.0.* Similar protection, shorter text, but no automatic conversion and less
  familiar to legal reviewers.
- *Open core (Apache core, proprietary planner).* Most commercially defensible, but forces a source-tree
  split and a dual build now, for an outcome that is speculative.

**Decision:** BSL 1.1. Change Date 2030-08-30, Change License Apache 2.0, Additional Use Grant
permitting all non-production use.

**Reasoning:** Costs nothing today and preserves every option. The realistic failure mode for a solo
project is picking MIT by reflex and discovering three years later that the choice cannot be undone.
Open core is the right answer only once there is a business, and there is not one yet. The copyright
holder can always grant more permissive terms later; the reverse is not true.

**Tradeoffs:** Fewer stars, fewer drive-by contributors, and some engineers decline non-OSI licenses on
principle. Corporate legal review is slower than for Apache 2.0.

**Consequences:** Makes easy — commercializing later, or relicensing to Apache 2.0 at any time. Makes
hard — attracting outside contributors, and inclusion anywhere that requires OSI approval.

**Revisit if:** The project is deliberately opened to outside contributors, or a specific commercial
model is chosen — then supersede with an open-core ADR.

---

## ADR-004: Regression defined as delta against a measured noise floor
Status: Accepted
Date: 2026-08-30
Phase: 00

**Context:** The gate's entire value is the verdict. The arithmetic producing PASS/BLOCK determines the
verdict artifact schema, what Phase 05 must compute, and whether users trust the tool enough to leave
it switched on.

**Options:**

- *Fixed percentage threshold on p95* — block if candidate p95 exceeds baseline p95 by more than 10%.
  Trivial to implement and to explain. Fails silently when run-to-run variance in the environment
  exceeds the threshold: the gate blocks on noise, developers learn to ignore it, and it is disabled
  within a week.
- *Bootstrap confidence interval on the difference of distributions.* Statistically principled, gives a
  real significance statement, needs no environment calibration. But it is expensive to compute, much
  harder to explain to the developer whose PR was just blocked, and a statistically significant 2ms
  regression is not a business-relevant one.
- *Delta thresholded against a measured noise floor.* Run baseline against itself first to measure the
  environment's own variance, then require a candidate delta to exceed both a configured threshold and
  that floor.

**Decision:** Option 3. A regression is a delta exceeding both the configured threshold and the
measured noise floor.

**Reasoning:** A threshold set below the noise floor is a gate that gets switched off, and the only way
to avoid that is to measure the floor rather than assume it. It also produces the honest failure mode:
when the environment is too noisy to judge, the gate reports INCONCLUSIVE instead of guessing. That
property is what keeps a gate switched on.

**Tradeoffs:** Every gate run costs an extra baseline-vs-baseline replay, roughly 50% more wall-clock
time. The noise floor is itself an estimate from a finite sample and carries its own uncertainty.

**Consequences:** Makes easy — defending a BLOCK to a skeptical developer, and detecting a degraded CI
runner. Makes hard — running the gate cheaply; a fast mode skipping floor measurement would have to
carry an explicit confidence caveat inside the verdict artifact.

**Revisit if:** Noise-floor measurements prove stable enough across runs to cache, or a bootstrap CI
turns out to be affordable and can be reported alongside the threshold rule rather than instead of it.

---

## ADR-005: Develop inside WSL2 on the Linux filesystem
Status: Accepted
Date: 2026-08-30 (proposed), 2026-08-30 (accepted)
Phase: 00

**Context:** Development is currently on Windows 11 native at `D:\Projects\pulseforge`. WSL2 is
available with RAM capped at half the host. From Phase 04 onward the project measures latency; from
Phase 10 it runs in Linux CI, and later on Linux in AWS.

**Options:**

- *Windows native.* Zero disruption now. But `uvloop` does not exist on Windows, asyncio runs a
  different event loop implementation, and timing characteristics differ from CI and production. Every
  benchmark recorded before a later migration becomes unusable.
- *WSL2 with the repo on `/mnt/d/`.* Correct Linux runtime with no repo move, but filesystem I/O
  crosses the 9p bridge at roughly a tenth of native speed. A test suite writing thousands of small
  content-addressed artifacts (ADR-002) pays that tax on every run.
- *WSL2 with the repo on the Linux filesystem.* Correct runtime, native I/O speed, environment matching
  CI and AWS. Requires re-cloning into `~/projects/pulseforge` and running Claude Code inside WSL.

**Decision:** Option 3.

**Reasoning:** The migration costs minutes today — two commits and two files exist — and roughly half a
day at Phase 04, at precisely the moment when attention should be on the replay engine. ADR-002's
many-small-files layout turns option 2's I/O penalty into a recurring tax rather than a one-time cost.

**Tradeoffs:** Windows-native tooling reaches the repo only through `\\wsl.localhost\`. The WSL2 RAM
cap bounds replay concurrency during local testing and must be recorded alongside every benchmark.

**Consequences:** Makes easy — trustworthy benchmarks, `uvloop`, parity with CI and AWS, Docker without
Windows path translation. Makes hard — nothing material, once the move is done.

**Execution:** Repository re-cloned to `~/projects/pulseforge` inside WSL2 Ubuntu on 2026-08-30.
Windows working copy at `D:\Projects\pulseforge` is abandoned, not synced. Editing happens through
VS Code's WSL remote extension, never through the `\wsl.localhost\` UNC path, which would reintroduce
the 9p penalty this ADR exists to avoid.

**Revisit if:** WSL2's RAM cap becomes the binding constraint on replay concurrency, at which point the
choice is between raising the cap in `.wslconfig` and moving replay to containers.

---

## ADR-006: Python 3.12 + uv + ruff + mypy --strict
Status: Accepted
Date: 2026-08-30
Phase: 00

**Context:** The toolchain must be fixed before the first line of code. Python 3.12.10 and 3.14.3 are
both installed, and the `py` launcher defaults to 3.14.

**Options:** 3.12 (broadest library support, stable typing ecosystem, matches AWS Lambda runtimes),
3.13 (free-threading experiments, some libraries lagging), 3.14 (newest, least library support, mypy
and plugin ecosystem still catching up).

**Decision:** Pin `requires-python = ">=3.12,<3.13"`. `uv` manages the interpreter, so the system `py`
default is irrelevant. `ruff` for both lint and format — one tool, one config, no black/isort/flake8
disagreements. `mypy --strict` on `app/` only; tests are typed but not strict.

**Reasoning:** A performance tool must never itself be the reason a dependency is unavailable or a wheel
has to be built from source. 3.12 has the fewest surprises across FastAPI, httpx, pydantic, and the AWS
ecosystem. Locking the interpreter through `uv` removes an entire class of works-on-my-machine failure.

**Tradeoffs:** No 3.13+ language features. `mypy --strict` slows early development and occasionally
demands casts; those get a comment justifying them rather than a bare `Any`.

**Consequences:** Makes easy — reproducible environments, parity with Lambda and container runtimes.
Makes hard — adopting a library requiring 3.13+, which would need this ADR superseded.

**Revisit if:** A required dependency drops 3.12 support, or free-threading becomes relevant to the
replay engine's concurrency model.
