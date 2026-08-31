"""Run the target service locally: ``python -m app.target``.

Switches are read from the environment (see ``.env.example``). Example:

    SLOW_PRICING=1 python -m app.target
"""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run(
        "app.target.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
    )


if __name__ == "__main__":
    main()
