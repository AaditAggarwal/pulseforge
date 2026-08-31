# SECURITY

PulseForge records live API traffic. That makes it higher-risk than most tools of its size, and the
sanitizer is a security boundary rather than a feature.

## Threat model

| Threat | Vector | Mitigation | Status |
|---|---|---|---|
| Credentials leak into corpus | `Authorization`, `Cookie`, custom auth headers | header allowlist, deny by default | designed, Phase 02 |
| PII leaks into corpus | request/response bodies | JSON-path redaction, plus pattern detection as second layer | designed, Phase 02 |
| Raw traffic reaches disk unsanitized | any write-then-clean design | sanitize inside the write path; no code path writes unsanitized bytes | designed, Phase 02 |
| Secrets committed to repo | fixtures, `.env`, docs | gitleaks in pre-commit and CI; synthetic fixtures only | Phase 00 |
| Vulnerable dependency | transitive deps | `pip-audit` in CI, Dependabot, committed lockfile | Phase 00 / 10 |
| Replay hits production by misconfiguration | a wrong base URL | allowlist of replay targets; refuse unknown hosts | not yet designed |
| Prompt injection via captured traffic | attacker-controlled bodies reaching the planner prompt | output schema-validated; planner can only reweight a plan, never widen it (R6) | Phase 07 |

## Sanitization design (Phase 02)

**Deny by default.** An allowlist of headers that may be retained, not a blocklist of headers to strip.
Blocklists fail on the header nobody thought of, and that is the one carrying the token.

Layers, in order:

1. Header allowlist. Everything not on it is dropped. `Authorization`, `Cookie` and `Set-Cookie` are
   never on it, including on redirect responses.
2. Body redaction by JSON path against a declared schema.
3. Pattern-based PII and secret detection as a *second* layer, never the only one.

Sanitization happens before the first byte reaches a filesystem. Writing raw traffic and cleaning it
afterwards is not a weaker design, it is an incident.

## Proving it

- Property-based tests via `hypothesis` on the sanitizer specifically. Example-based tests will not
  find the miss; that is why the sanitizer gets property tests and other components do not.
- A test feeding known secret values through capture, asserting they appear nowhere in the artifact.
- A CI job scanning stored fixtures for high-entropy strings.
- gitleaks in pre-commit and in CI.

## Secret handling

No secrets, credentials, tokens, PII, or real captured traffic in this repository, ever. `.env` is
gitignored; `.env.example` carries names and empty values only. No secrets in container image layers.

## Dependency policy

All dependencies pinned via `uv.lock`, committed. `pip-audit` in CI. Dependabot enabled. Base images
pinned by digest, not tag. Containers run as non-root with a read-only filesystem where possible.
