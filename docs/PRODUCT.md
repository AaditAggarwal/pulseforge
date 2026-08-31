# PRODUCT

## Problem

Tests verify correctness, not behaviour under realistic load. A change passes CI and doubles p95
latency, introduces an N+1 query, or exhausts a connection pool. The team finds out in production.

## Who would care

Teams with a Python API service, meaningful traffic, and an existing CI habit. The buyer is whoever
gets paged when latency regresses.

## Why existing tools do not cover this

Load testing tools (k6, Locust, Artillery) replay a workload someone wrote by hand, which drifts from
reality and is not aware of what changed. APM tools (Datadog, New Relic) detect regressions after
deployment. The gap is a pre-merge, change-aware comparison against real recorded traffic.

## Differentiator

Blast-radius-weighted workloads. A 200ms regression in checkout is not diluted across 9,000 unrelated
`/health` requests. **Not yet built** — Phases 03, 07, 08.

## Deliberately not written yet

Pricing, marketing copy, competitive claims, and resume bullets. None of these get written before the
corresponding feature exists and has measured numbers behind it. There is currently no intent to sell
(ADR-003).

## Onboarding time

Time from `git clone` to first verdict is a tracked metric. Over fifteen minutes is a defect.
**NOT YET MEASURED.**
