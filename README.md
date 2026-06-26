# Regime detection agent

An autonomous research pipeline that ingests daily S&P 500 sector-ETF data, engineers
volatility / dispersion / correlation-breakdown / liquidity / macro features, segments
market history into regimes with a Gaussian HMM (cross-checked against GMM and KMeans),
evaluates and characterizes those regimes, and auto-writes a dated research note --
end to end, designed to re-run daily with no manual intervention.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design walkthrough: agent roles,
reasoning flow, methodology, limitations, and future work. That document is the
"architecture walkthrough" deliverable for this project.

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python scripts/run_daily.py
```

This fetches/updates the cached price and macro data under `data/`, then writes
`reports/<date>_daily_note.md`, a regime-shaded price chart, and a JSON metadata
sidecar, and appends a row to `reports/regime_history.csv`.

### Optional: Claude-generated narrative

Without an API key, the analyst/report-writing step uses a deterministic template --
the pipeline is fully functional with zero secrets. To get Claude tool-calling
narrative generation instead:

```bash
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY=sk-...
```

### Running the tests

```bash
pytest tests/ -v
```

The suite runs entirely on synthetic, in-memory data (including the LLM tool-calling
path, via mocks) -- no network access or API key required.

### Daily automation

[`.github/workflows/daily_run.yml`](.github/workflows/daily_run.yml) runs the pipeline
on a weekday cron schedule (and via manual `workflow_dispatch`), then commits the
updated data cache and report back to the repo. Set an `ANTHROPIC_API_KEY` repository
secret to enable the Claude narrative in CI; otherwise it runs in deterministic mode.

## Project layout

```
src/regime_agent/
  ingestion.py     data ingestion agent (Yahoo Finance + FRED)
  features.py      feature engineering agent
  regimes.py       regime detection agent (HMM primary, GMM/KMeans baselines)
  evaluation.py    evaluation agent (regime characterization + data-quality flags)
  llm.py           analyst agent (Claude tool-calling, or deterministic fallback)
  report.py        report-writer agent (markdown + chart + JSON + history log)
  orchestrator.py  LangGraph state machine wiring all of the above together
config/config.yaml   universe, feature windows, regime candidates, known events
templates/            Jinja2 daily note template
scripts/run_daily.py  CLI entrypoint
tests/                pytest suite (synthetic data, no network)
data/                 cached raw + processed Parquet (committed; see ARCHITECTURE.md)
reports/              generated daily notes, charts, metadata, history log
```
