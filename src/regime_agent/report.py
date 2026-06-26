from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from jinja2 import Environment, FileSystemLoader

from .evaluation import RegimeCharacterization
from .llm import AnalystOutput
from .storage import append_history_log

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def plot_regime_timeline(labels: pd.Series, benchmark_close: pd.Series, out_path: Path) -> None:
    aligned_close = benchmark_close.reindex(labels.index).ffill()
    n_states = int(labels.nunique())
    cmap = matplotlib.colormaps["RdYlGn_r"].resampled(n_states)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(aligned_close.index, aligned_close.values, color="black", linewidth=0.9, zorder=3)

    state_arr = labels.values
    dates = labels.index
    start_idx = 0
    for i in range(1, len(state_arr) + 1):
        if i == len(state_arr) or state_arr[i] != state_arr[start_idx]:
            ax.axvspan(dates[start_idx], dates[i - 1], color=cmap(state_arr[start_idx]), alpha=0.3, lw=0)
            start_idx = i

    ax.set_ylabel("Benchmark price")
    ax.set_title("Benchmark price shaded by detected regime (green = calm, red = crisis-like)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=cmap(s), alpha=0.4) for s in range(n_states)]
    ax.legend(handles, [f"regime {s}" for s in range(n_states)], loc="upper left", fontsize=8, ncol=n_states)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    plt.close(fig)


def _stats_table_markdown(stats: pd.DataFrame) -> str:
    pretty = stats.copy()
    pct_cols = ["share_of_days", "ann_return", "ann_vol", "max_drawdown"]
    for col in pct_cols:
        if col in pretty.columns:
            pretty[col] = pretty[col].map(lambda v: f"{v:.1%}")
    for col in ("sharpe", "skew", "kurtosis"):
        if col in pretty.columns:
            pretty[col] = pretty[col].map(lambda v: f"{v:.2f}")
    pretty.index.name = "regime"
    return pretty.to_markdown()


def render_daily_note(
    run_date: str,
    universe: dict,
    regime_detection: dict,
    evaluation: RegimeCharacterization,
    analyst: AnalystOutput,
    config: dict,
    rerun_note: str = "",
) -> dict:
    reports_dir = Path(config["paths"]["reports_dir"])
    reports_dir.mkdir(parents=True, exist_ok=True)

    benchmark = config["universe"]["benchmark"]
    n_states = regime_detection["chosen_n_states"]
    labels = regime_detection["hmm"].labels

    chart_filename = f"{run_date}_regime_timeline.png"
    plot_regime_timeline(labels, universe["close"][benchmark], reports_dir / chart_filename)

    env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), trim_blocks=True, lstrip_blocks=True)
    template = env.get_template("daily_note.md.j2")

    rendered = template.render(
        run_date=run_date,
        headline=analyst.headline,
        current_regime=evaluation.current_regime,
        n_states=n_states,
        candidate_n_states=config["regimes"]["candidate_n_states"],
        analyst_source=analyst.source,
        rerun_note=rerun_note,
        regime_summary=analyst.regime_summary,
        stats_table=_stats_table_markdown(evaluation.stats),
        chart_filename=chart_filename,
        per_regime_notes=analyst.per_regime_notes,
        hmm_vs_gmm=evaluation.method_agreement["hmm_vs_gmm"],
        hmm_vs_kmeans=evaluation.method_agreement["hmm_vs_kmeans"],
        event_check=evaluation.event_check,
        caveats=analyst.caveats,
        outlook=analyst.outlook,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        benchmark=benchmark,
        sector_etfs=", ".join(config["universe"]["sector_etfs"]),
    )

    md_path = reports_dir / f"{run_date}_daily_note.md"
    md_path.write_text(rendered)

    metadata = {
        "run_date": run_date,
        "current_regime": evaluation.current_regime,
        "n_states": n_states,
        "regime_stats": evaluation.stats.to_dict(orient="index"),
        "separation_pvalue": evaluation.separation_pvalue,
        "flags": evaluation.flags,
        "method_agreement": evaluation.method_agreement,
        "event_check": evaluation.event_check,
        "analyst_source": analyst.source,
        "errors": universe.get("errors", []),
    }
    json_path = reports_dir / f"{run_date}_metadata.json"
    json_path.write_text(json.dumps(metadata, indent=2, default=str))

    append_history_log(
        {
            "run_date": run_date,
            "current_regime": evaluation.current_regime,
            "n_states": n_states,
            "ann_vol": evaluation.stats.loc[evaluation.current_regime, "ann_vol"],
            "separation_pvalue": evaluation.separation_pvalue,
            "hmm_vs_gmm_agreement": evaluation.method_agreement["hmm_vs_gmm"],
        },
        config["paths"]["history_log"],
    )

    return {"markdown_path": str(md_path), "chart_path": str(reports_dir / chart_filename), "json_path": str(json_path)}
