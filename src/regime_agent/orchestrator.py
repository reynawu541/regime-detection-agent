from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from .evaluation import characterize_regimes
from .features import build_feature_matrix, select_model_features
from .ingestion import fetch_universe
from .llm import run_analyst
from .regimes import run_regime_detection
from .report import render_daily_note
from .storage import save_parquet

MIN_ROWS_REQUIRED = 252  # ~1 trading year; below this, regime detection is not meaningful


class PipelineState(TypedDict, total=False):
    config: dict
    run_date: str
    universe: dict
    status: str
    features: Any
    model_features: Any
    requested_n_states: int | None
    regime_detection: dict
    evaluation: Any
    analyst: Any
    rerun_count: int
    rerun_reason: str | None
    rerun_note: str
    report_paths: dict
    errors: list[str]


def ingest_node(state: PipelineState) -> dict:
    config = state["config"]
    universe = fetch_universe(config)
    if not universe["close"].empty:
        run_date = universe["close"].index.max().strftime("%Y-%m-%d")
    else:
        run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return {"universe": universe, "run_date": run_date, "errors": list(universe.get("errors", []))}


def validate_node(state: PipelineState) -> dict:
    universe = state["universe"]
    close = universe["close"]
    benchmark = state["config"]["universe"]["benchmark"]
    problems = []
    if close.empty:
        problems.append("no price data fetched")
    elif benchmark not in close.columns:
        problems.append(f"benchmark {benchmark} missing from fetched data")
    elif len(close) < MIN_ROWS_REQUIRED:
        problems.append(f"only {len(close)} rows fetched, need at least {MIN_ROWS_REQUIRED}")
    status = "data_error" if problems else "ok"
    return {"status": status, "errors": state.get("errors", []) + problems}


def feature_node(state: PipelineState) -> dict:
    config = state["config"]
    feats = build_feature_matrix(state["universe"], config)
    save_parquet(feats, Path(config["paths"]["processed_data_dir"]) / "features.parquet")
    return {"features": feats, "model_features": select_model_features(feats)}


def regime_node(state: PipelineState) -> dict:
    regime_detection = run_regime_detection(
        state["model_features"], state["config"], n_states=state.get("requested_n_states")
    )
    return {"regime_detection": regime_detection}


def evaluate_node(state: PipelineState) -> dict:
    config = state["config"]
    benchmark = config["universe"]["benchmark"]
    benchmark_returns = state["universe"]["close"][benchmark].pct_change()
    evaluation = characterize_regimes(benchmark_returns, state["regime_detection"], config)
    return {"evaluation": evaluation}


def analyst_node(state: PipelineState) -> dict:
    config = state["config"]
    rerun_count = state.get("rerun_count", 0)
    allow_rerun = rerun_count < config["llm"]["max_rerun_attempts"]
    note = ""
    if rerun_count > 0:
        note = (
            f"This is a re-fit (attempt {rerun_count + 1}) requested because: "
            f"{state.get('rerun_reason', 'a data-quality concern')}."
        )
    analyst = run_analyst(
        state["evaluation"], state["regime_detection"], config, allow_rerun=allow_rerun, note=note
    )

    updates: dict = {"analyst": analyst}
    if analyst.rerun_requested is not None and allow_rerun:
        updates["requested_n_states"] = analyst.rerun_requested
        updates["rerun_count"] = rerun_count + 1
        updates["rerun_reason"] = analyst.rerun_reason
        updates["rerun_note"] = (
            f"Re-fit with {analyst.rerun_requested} states "
            f"(was {state['regime_detection']['chosen_n_states']}) because: {analyst.rerun_reason}"
        )
    return updates


def report_node(state: PipelineState) -> dict:
    paths = render_daily_note(
        state["run_date"],
        state["universe"],
        state["regime_detection"],
        state["evaluation"],
        state["analyst"],
        state["config"],
        rerun_note=state.get("rerun_note", ""),
    )
    return {"report_paths": paths}


def error_report_node(state: PipelineState) -> dict:
    config = state["config"]
    reports_dir = Path(config["paths"]["reports_dir"])
    reports_dir.mkdir(parents=True, exist_ok=True)
    run_date = state.get("run_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    path = reports_dir / f"{run_date}_daily_note.md"
    issues = "\n".join(f"- {e}" for e in state.get("errors", []))
    path.write_text(
        f"# Daily market regime research note — {run_date}\n\n"
        f"**Pipeline aborted before regime detection: data validation failed.**\n\n"
        f"Issues:\n{issues}\n"
    )
    return {"report_paths": {"markdown_path": str(path)}}


def _route_after_validate(state: PipelineState) -> str:
    return "ok" if state.get("status") == "ok" else "data_error"


def _route_after_analyst(state: PipelineState) -> str:
    # analyst_node only ever sets rerun_requested when it passed allow_rerun=True,
    # so checking the flag here is sufficient -- no need to re-check rerun_count.
    return "rerun" if state["analyst"].rerun_requested is not None else "finalize"


def build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("ingest", ingest_node)
    graph.add_node("validate", validate_node)
    graph.add_node("features", feature_node)
    graph.add_node("regimes", regime_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("report", report_node)
    graph.add_node("error_report", error_report_node)

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "validate")
    graph.add_conditional_edges(
        "validate", _route_after_validate, {"ok": "features", "data_error": "error_report"}
    )
    graph.add_edge("features", "regimes")
    graph.add_edge("regimes", "evaluate")
    graph.add_edge("evaluate", "analyst")
    graph.add_conditional_edges("analyst", _route_after_analyst, {"rerun": "regimes", "finalize": "report"})
    graph.add_edge("report", END)
    graph.add_edge("error_report", END)
    return graph.compile()


def run_pipeline(config: dict) -> PipelineState:
    app = build_graph()
    initial_state: PipelineState = {"config": config, "rerun_count": 0, "errors": []}
    return app.invoke(initial_state, {"recursion_limit": 25})
