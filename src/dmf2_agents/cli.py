from __future__ import annotations

import asyncio
import argparse
from pathlib import Path

from .bootstrap import build_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the staged multi-agent orchestrator.")
    parser.add_argument("prompt", help="User request")
    parser.add_argument("--workflow", type=Path, help="Path to the workflow configuration file")
    args = parser.parse_args()
    app = build_app(workflow_path=args.workflow)
    session_id = asyncio.run(app.run(args.prompt))
    print(session_id)
