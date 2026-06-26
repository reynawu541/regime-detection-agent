from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

SECTOR_ETFS = ["XLY", "XLP", "XLE", "XLF", "XLV", "XLI", "XLB", "XLK", "XLU"]
ALL_TICKERS = ["SPY", *SECTOR_ETFS]


@pytest.fixture
def synthetic_universe():
    """Two-regime synthetic market: first half calm, second half turbulent,
    with a shared common factor so cross-sectional correlation behaves realistically."""
    rng = np.random.default_rng(42)
    n = 600
    dates = pd.bdate_range("2020-01-01", periods=n)

    vol = np.where(np.arange(n) < n // 2, 0.005, 0.02)
    idio = rng.normal(0.0, 1.0, size=(n, len(ALL_TICKERS))) * vol[:, None]
    common = rng.normal(0.0, 1.0, size=n) * vol
    returns = 0.5 * idio + 0.5 * common[:, None]

    prices = 100 * np.exp(np.cumsum(returns, axis=0))
    close = pd.DataFrame(prices, index=dates, columns=ALL_TICKERS)
    volume = pd.DataFrame(
        rng.integers(1_000_000, 5_000_000, size=(n, len(ALL_TICKERS))), index=dates, columns=ALL_TICKERS
    )
    vix = pd.Series(
        np.where(np.arange(n) < n // 2, 14.0, 28.0) + rng.normal(0, 1, n), index=dates, name="VIX"
    )
    macro = pd.DataFrame(
        {
            "us_10y_yield": 3.5 + rng.normal(0, 0.02, n).cumsum(),
            "us_2y_yield": 3.0 + rng.normal(0, 0.02, n).cumsum(),
            "high_yield_spread": 3.0 + rng.normal(0, 0.02, n).cumsum(),
        },
        index=dates,
    )
    return {"close": close, "volume": volume, "vix": vix, "macro": macro, "errors": []}


@pytest.fixture
def test_config(tmp_path):
    reports_dir = tmp_path / "reports"
    return {
        "universe": {"benchmark": "SPY", "sector_etfs": SECTOR_ETFS, "vix_ticker": "^VIX"},
        "history": {"start_date": "2020-01-01"},
        "macro": {
            "fred_series": {
                "DGS10": "us_10y_yield",
                "DGS2": "us_2y_yield",
                "BAMLH0A0HYM2": "high_yield_spread",
            },
            "fail_silently": True,
        },
        "features": {
            "vol_windows": [5, 21, 63],
            "dispersion_window": 21,
            "correlation_window": 63,
            "correlation_pca_window": 63,
            "liquidity_window": 21,
        },
        "regimes": {
            "candidate_n_states": [2, 3],
            "min_regime_share": 0.05,
            "min_state_distinctness": 0.5,
            "random_state": 42,
        },
        "evaluation": {"known_events": []},
        "llm": {
            "provider": "anthropic",
            "model_env_var": "ANTHROPIC_MODEL",
            "default_model": "claude-haiku-4-5-20251001",
            "max_rerun_attempts": 1,
        },
        "paths": {
            "raw_data_dir": str(tmp_path / "raw"),
            "processed_data_dir": str(tmp_path / "processed"),
            "reports_dir": str(reports_dir),
            "history_log": str(reports_dir / "regime_history.csv"),
        },
    }
