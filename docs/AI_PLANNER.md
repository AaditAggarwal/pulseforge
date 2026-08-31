# AI_PLANNER

Prompt versions, output schema, determinism strategy, evaluation results, measured cost per call.

## Status

Not built. Phase 07. Provider: OpenRouter, roughly $4 credit available as of 2026-08-30.

## Non-negotiable constraints (R6)

The planner shapes the workload; it never makes the gate decision. If model output is missing, invalid,
or malformed, the system falls back to full-corpus replay and logs that it did. A third-party API
outage must never be a pipeline failure.

## To be recorded here as it is built

- Prompt text, versioned. Every change bumps the version.
- Output JSON schema and the Pydantic model validating it.
- Determinism strategy: how the same diff yields the same plan ID across runs.
- Fallback behaviour, and the test proving the fallback path works.
- Phase 08 evaluation: does it beat random sampling at equal request budget?
- Cost per call, measured, never estimated.
