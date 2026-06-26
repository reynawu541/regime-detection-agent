from __future__ import annotations

import numpy as np
import pandas as pd

from regime_agent.features import (
    MODEL_FEATURE_COLUMNS,
    amihud_illiquidity,
    build_feature_matrix,
    cross_sectional_dispersion,
    realized_vol,
    rolling_avg_correlation,
    rolling_pca_explained_variance,
    select_model_features,
)


def _bdates(n, start="2021-01-01"):
    return pd.bdate_range(start, periods=n)


def test_realized_vol_matches_manual_calc():
    dates = _bdates(30)
    returns = pd.Series(np.full(30, 0.01), index=dates)
    vol = realized_vol(returns, window=5, annualize=False)
    assert np.isclose(vol.iloc[-1], 0.0, atol=1e-9)  # constant returns -> zero std


def test_cross_sectional_dispersion_zero_when_identical():
    dates = _bdates(40)
    returns = pd.DataFrame({"A": 0.01, "B": 0.01, "C": 0.01}, index=dates)
    dispersion = cross_sectional_dispersion(returns, window=10)
    assert np.isclose(dispersion.iloc[-1], 0.0, atol=1e-9)


def test_no_lookahead_realized_vol():
    rng = np.random.default_rng(0)
    dates = _bdates(100)
    returns = pd.Series(rng.normal(0, 0.01, 100), index=dates)
    vol_before = realized_vol(returns, window=21)

    shocked = returns.copy()
    shocked.iloc[80:] = 5.0  # huge shock far in the future
    vol_after = realized_vol(shocked, window=21)

    pd.testing.assert_series_equal(vol_before.iloc[:79], vol_after.iloc[:79])


def test_no_lookahead_pca_explained_variance():
    rng = np.random.default_rng(1)
    dates = _bdates(150)
    returns = pd.DataFrame(rng.normal(0, 0.01, size=(150, 5)), index=dates, columns=list("ABCDE"))
    before = rolling_pca_explained_variance(returns, window=63)

    shocked = returns.copy()
    shocked.iloc[120:, :] = 5.0
    after = rolling_pca_explained_variance(shocked, window=63)

    pd.testing.assert_series_equal(before.iloc[:119], after.iloc[:119])


def test_no_lookahead_avg_correlation():
    rng = np.random.default_rng(2)
    dates = _bdates(150)
    returns = pd.DataFrame(rng.normal(0, 0.01, size=(150, 5)), index=dates, columns=list("ABCDE"))
    before = rolling_avg_correlation(returns, window=63)

    shocked = returns.copy()
    shocked.iloc[120:, :] = 5.0
    after = rolling_avg_correlation(shocked, window=63)

    pd.testing.assert_series_equal(before.iloc[:119], after.iloc[:119])


def test_amihud_illiquidity_higher_for_thinner_volume():
    dates = _bdates(40)
    close = pd.DataFrame({"A": np.linspace(100, 110, 40), "B": np.linspace(100, 110, 40)}, index=dates)
    volume_thick = pd.DataFrame({"A": 1_000_000.0, "B": 1_000_000.0}, index=dates)
    volume_thin = pd.DataFrame({"A": 1_000.0, "B": 1_000.0}, index=dates)

    illiq_thick = amihud_illiquidity(close, volume_thick, window=10).iloc[-1]
    illiq_thin = amihud_illiquidity(close, volume_thin, window=10).iloc[-1]
    assert illiq_thin > illiq_thick


def test_build_feature_matrix_and_select_model_features(synthetic_universe, test_config):
    feats = build_feature_matrix(synthetic_universe, test_config)
    expected_cols = {
        "vol_5", "vol_21", "vol_63", "dispersion", "avg_correlation", "pca_explained_var",
        "amihud_illiquidity", "volume_zscore", "vix_level", "vix_change_5d",
        "yield_curve_slope", "high_yield_spread",
    }
    assert expected_cols.issubset(set(feats.columns))

    model_feats = select_model_features(feats)
    assert list(model_feats.columns) == [c for c in MODEL_FEATURE_COLUMNS if c in feats.columns]
    assert not model_feats.isna().any().any()
    assert len(model_feats) > 0
