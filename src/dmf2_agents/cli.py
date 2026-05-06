from __future__ import annotations

import argparse

from .bootstrap import build_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the staged multi-agent orchestrator.")
    parser.add_argument("prompt", help="User request")
    args = parser.parse_args()
    app = build_app()
    session_id = app.run(args.prompt)
    print(session_id)
