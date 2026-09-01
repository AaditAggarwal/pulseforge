# CHANGELOG

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: semver once there is
something to version. Updated when a phase completes, not on every commit.

## [Unreleased]

### Added
- Documentation system: `docs/` tree, 14 phase documents, ADR-001 through ADR-006
- Repository hygiene: `.gitignore`, `.env.example`, `LICENSE` (BSL 1.1), `CONTRIBUTING.md`
- Core: exception hierarchy, structured JSON logging with correlation IDs (Phase 00)
- Target service (`app/target`): five FastAPI endpoints over SQLite with deliberately different
  cost profiles, deterministic seed data, and a connection pool (Phase 01)
- Four runtime regression switches — `SLOW_PRICING_MS`, `N_PLUS_ONE`, `ERROR_RATE`, `TIMEOUT_RATE` —
  read once at startup, with measured evidence that each changes behaviour (Phase 01)
- `scripts/phase01_evidence.py`, reproducing the `BENCHMARKS.md` numbers

### Changed
- `SLOW_PRICING` is now `SLOW_PRICING_MS`, an integer millisecond magnitude rather than a boolean

### Fixed
- FM-001: the target service emitted no structured logs under uvicorn, because uvicorn leaves the
  root logger bare. `create_app` now installs the JSON handler itself.

Phases 00 and 01 are complete. PulseForge itself — capture, replay, comparison, the gate — is not
built; only the service it will be tested against.
