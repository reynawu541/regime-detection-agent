from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from regime_agent import orchestrator
from regime_agent.llm import AnalystOutput


def test_pipeline_runs_end_to_end(synthetic_universe, test_config):
    with patch("regime_agent.orchestrator.fetch_universe", return_value=synthetic_universe):
        final_state = orchestrator.run_pipeline(test_config)

    assert final_state["status"] == "ok"
    assert final_state["rerun_count"] == 0
    md_path = final_state["report_paths"]["markdown_path"]
    assert md_path.endswith("_daily_note.md")
    with open(md_path) as f:
        content = f.read()
    assert "Daily market regime research note" in content


def test_pipeline_handles_insufficient_data(test_config):
    tiny_dates = pd.bdate_range("2024-01-01", periods=2)
    tiny_universe = {
        "close": pd.DataFrame({"SPY": [100.0, 101.0]}, index=tiny_dates),
        "volume": pd.DataFrame({"SPY": [1000, 1000]}, index=tiny_dates),
        "vix": pd.Series([15.0, 15.0], index=tiny_dates),
        "macro": pd.DataFrame(),
        "errors": [],
    }
    with patch("regime_agent.orchestrator.fetch_universe", return_value=tiny_universe):
        final_state = orchestrator.run_pipeline(test_config)

    assert final_state["status"] == "data_error"
    with open(final_state["report_paths"]["markdown_path"]) as f:
        content = f.read()
    assert "Pipeline aborted" in content


def test_pipeline_rerun_loop_is_bounded(synthetic_universe, test_config):
    """Force the analyst to always request a rerun; confirm the graph still
    terminates after exactly one retry (bounded by max_rerun_attempts=1)."""
    call_count = {"n": 0}

    def fake_run_analyst(evaluation, regime_detection, config, allow_rerun=True, note=""):
        call_count["n"] += 1
        if allow_rerun:
            return AnalystOutput(
                headline="",
                regime_summary="",
                per_regime_notes={},
                caveats="",
                outlook="",
                rerun_requested=2,
                rerun_reason="forced for test",
                source="test",
            )
        return AnalystOutput(
            headline="final", regime_summary="s", per_regime_notes={}, caveats="c", outlook="o", source="test"
        )

    with patch("regime_agent.orchestrator.fetch_universe", return_value=synthetic_universe), patch(
        "regime_agent.orchestrator.run_analyst", side_effect=fake_run_analyst
    ):
        final_state = orchestrator.run_pipeline(test_config)

    assert call_count["n"] == 2  # one rerun-requesting call, one forced-finalize call
    assert final_state["rerun_count"] == 1
    assert final_state["analyst"].headline == "final"
