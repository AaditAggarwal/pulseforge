# Thin wrapper over `uv run`. Optional: every target is a single uv command you
# can run directly. `make` is deliberately not installed on the Windows host;
# this exists for Linux/WSL2 and CI. See ADR-005, ADR-006.

.PHONY: install lint fmt type test cov check clean seed run

install:
	uv sync

lint:
	uv run ruff check .

fmt:
	uv run ruff format .

type:
	uv run mypy --strict app/

test:
	uv run pytest

cov:
	uv run pytest --cov=app --cov-report=term-missing

seed:
	uv run python -m app.target.seed

# --factory so settings are read at startup, not at import. Reload is off on
# purpose: a reloading process is not the process you measured.
run:
	uv run uvicorn app.target.app:create_app --factory --host 127.0.0.1 --port 8000

check: lint type test

clean:
	rm -rf .mypy_cache .ruff_cache .pytest_cache .hypothesis htmlcov .coverage
