# Thin wrapper over `uv run`. Optional: every target is a single uv command you
# can run directly. `make` is deliberately not installed on the Windows host;
# this exists for Linux/WSL2 and CI. See ADR-005, ADR-006.

.PHONY: install lint fmt type test cov check clean

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

check: lint type test

clean:
	rm -rf .mypy_cache .ruff_cache .pytest_cache .hypothesis htmlcov .coverage
