from __future__ import annotations

import numpy as np
import pandas as pd

from regime_agent.features import build_feature_matrix, select_model_features
from regime_agent.regimes import _canonical_order, _relabel, run_regime_detection


def test_canonical_order_and_relabel():
    # state 1 has the lowest value on the reference column -> should become state 0
    means_scaled = np.array([[1.0, 0.0], [-1.0, 0.0], [0.5, 0.0]])
    order = _canonical_order(means_scaled, sort_col=0)
    assert list(order) == [1, 2, 0]

    labels = np.array([0, 1, 2, 0, 1])
    relabeled = _relabel(labels, order)
    # old label 1 (smallest) -> new label 0; old label 2 -> new label 1; old label 0 -> new label 2
    assert list(relabeled) == [2, 0, 1, 2, 0]


def test_run_regime_detection_recovers_two_clear_clusters():
    dates = pd.bdate_range("2021-01-01", periods=200)
    low = np.tile([0.05, 0.005, 0.5, 1e-11, 12.0], (100, 1))
    high = np.tile([0.30, 0.015, 0.5, 1e-11, 30.0], (100, 1))
    rng = np.random.default_rng(0)
    data = np.vstack([low, high]) + rng.normal(0, 0.001, size=(200, 5))
    model_feats = pd.DataFrame(
        data, index=dates, columns=["vol_21", "dispersion", "pca_explained_var", "amihud_illiquidity", "vix_level"]
    )

    config = {"regimes": {"candidate_n_states": [2, 3], "random_state": 42}}
    result = run_regime_detection(model_feats, config, n_states=2)

    labels = result["hmm"].labels
    assert labels.iloc[:100].mode()[0] == 0  # calm half -> state 0 (lowest vol)
    assert labels.iloc[100:].mode()[0] == 1  # turbulent half -> state 1


def test_run_regime_detection_deterministic(synthetic_universe, test_config):
    feats = build_feature_matrix(synthetic_universe, test_config)
    model_feats = select_model_features(feats)

    result_a = run_regime_detection(model_feats, test_config)
    result_b = run_regime_detection(model_feats, test_config)

    assert result_a["chosen_n_states"] == result_b["chosen_n_states"]
    pd.testing.assert_series_equal(result_a["hmm"].labels, result_b["hmm"].labels)
