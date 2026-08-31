# BENCHMARKS

**Rules for this file.** Only numbers produced by a run that was actually executed and whose output was
pasted in. No estimates, no projections, no "approximately". Every entry records the environment, the
method, the sample count, how many warm-up requests were discarded, and the exact commands to reproduce.
Never report a mean; report p50/p95/p99 with n.

## Status

**NOT YET MEASURED.** No benchmarks exist. No code exists.

## Entry template

```
### <what was measured>
Date:         YYYY-MM-DD
Environment:  OS, kernel, CPU, RAM, Python version, container or host, WSL2 RAM cap if applicable
Method:       what was run, against what, how many requests, concurrency, seed
Warm-up:      N requests discarded, and why that N
Sample count: n = ...
Results:      p50 / p95 / p99, error rate
Raw output:   pasted, verbatim
Reproduce:    exact commands
Caveats:      anything that would make a reader distrust the number
```
