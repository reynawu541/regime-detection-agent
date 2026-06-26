from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from regime_agent.evaluation import (
    _degeneracy_flags,
    _episode_durations,
    _event_check,
    _regime_stats,
    _separation_pvalue,
    characterize_regimes,
)
from regime_agent.features import build_feature_matrix, select_model_features
from regime_agent.regimes import run_regime_detection


def test_episode_durations():
    labels = pd.Series([0, 0, 0, 1, 1, 0, 0, 1])
    assert _episode_durations(labels, 0) == [3, 2]
    assert _episode_durations(labels, 1) == [2, 1]


def test_regime_stats_basic():
    dates = pd.bdate_range("2021-01-01", periods=10)
    returns = pd.Series([0.01] * 5 + [-0.01] * 5, index=dates)
    labels = pd.Series([0] * 5 + [1] * 5, index=dates)
    stats = _regime_stats(returns, labels)
    assert stats.loc[0, "n_days"] == 5
    assert stats.loc[0, "ann_return"] > 0
    assert stats.loc[1, "ann_return"] < 0


def test_separation_pvalue_significant_for_clearly_different_groups():
    dates = pd.bdate_range("2021-01-01", periods=200)
    returns = pd.Series([0.05] * 100 + [-0.05] * 100, index=dates)
    labels = pd.Series([0] * 100 + [1] * 100, index=dates)
    pvalue = _separation_pvalue(returns, labels)
    assert pvalue < 0.01


def test_degeneracy_flags_fires_on_small_share_and_close_centroids():
    stats = pd.DataFrame({"share_of_days": [0.5, 0.49, 0.01]}, index=[0, 1, 2])
    means = pd.DataFrame({"f1": [0.0, 0.01, 5.0], "f2": [0.0, 0.01, 5.0]}, index=[0, 1, 2])
    scaler = StandardScaler().fit(np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]]))
    config = {"regimes": {"min_regime_share": 0.05, "min_state_distinctness": 0.5}}

    flags = _degeneracy_flags(stats, means, scaler, config)
    assert any("regime 2 covers only" in f for f in flags)
    assert any("0 and 1" in f for f in flags)


def test_event_check_finds_nearest_trading_day():
    dates = pd.bdate_range("2021-01-04", periods=10)
    labels = pd.Series(range(10), index=dates)
    config = {"evaluation": {"known_events": [{"date": "2021-01-09", "label": "weekend event"}]}}
    result = _event_check(labels, config)
    assert result[0]["nearest_trading_day"] == "2021-01-08"


def test_characterize_regimes_end_to_end(synthetic_universe, test_config):
    feats = build_feature_matrix(synthetic_universe, test_config)
    model_feats = select_model_features(feats)
    regime_detection = run_regime_detection(model_feats, test_config)
    benchmark_returns = synthetic_universe["close"]["SPY"].pct_change()

    char = characterize_regimes(benchmark_returns, regime_detection, test_config)

    assert set(char.stats.index) == set(range(regime_detection["chosen_n_states"]))
    assert 0.0 <= char.method_agreement["hmm_vs_gmm"] <= 1.0
    assert char.current_regime in char.stats.index
