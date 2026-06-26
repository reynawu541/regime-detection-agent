#!/usr/bin/env python
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
os.chdir(ROOT)  # so relative paths in config.yaml resolve regardless of invocation cwd

from regime_agent.orchestrator import run_pipeline  # noqa: E402


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()

    config = yaml.safe_load((ROOT / "config" / "config.yaml").read_text())
    final_state = run_pipeline(config)

    report_path = final_state["report_paths"]["markdown_path"]
    print(report_path)

    if final_state.get("status") == "data_error":
        logging.error("Pipeline aborted before regime detection: %s", final_state.get("errors"))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
