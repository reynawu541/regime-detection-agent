from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler


@dataclass
class RegimeFitResult:
    method: str
    n_states: int
    labels: pd.Series
    means: pd.DataFrame  # n_states x feature, in original (unscaled) units
    bic: float
    transition_matrix: np.ndarray | None = None
    probabilities: np.ndarray | None = None


def _canonical_order(means_scaled: np.ndarray, sort_col: int = 0) -> np.ndarray:
    """Order states ascending by their mean on the reference feature (vol_21),
    so state 0 is always the calmest regime regardless of fit-to-fit label drift."""
    return np.argsort(means_scaled[:, sort_col])


def _relabel(labels: np.ndarray, order: np.ndarray) -> np.ndarray:
    mapping = np.zeros(len(order), dtype=int)
    for new_idx, old_idx in enumerate(order):
        mapping[old_idx] = new_idx
    return mapping[labels]


def _hmm_bic(model: GaussianHMM, X: np.ndarray) -> float:
    n_states, n_features = model.n_components, X.shape[1]
    n_params = (
        n_states * (n_states - 1)
        + (n_states - 1)
        + n_states * n_features
        + n_states * n_features
    )
    log_likelihood = model.score(X)
    return -2 * log_likelihood + n_params * np.log(len(X))


def fit_hmm(X: np.ndarray, n_states: int, random_state: int) -> tuple[GaussianHMM, float]:
    model = GaussianHMM(
        n_components=n_states, covariance_type="diag", n_iter=200, random_state=random_state
    )
    model.fit(X)
    return model, _hmm_bic(model, X)


def fit_gmm(X: np.ndarray, n_states: int, random_state: int) -> tuple[GaussianMixture, float]:
    model = GaussianMixture(n_components=n_states, covariance_type="diag", random_state=random_state)
    model.fit(X)
    return model, model.bic(X)


def fit_kmeans(X: np.ndarray, n_states: int, random_state: int) -> KMeans:
    model = KMeans(n_clusters=n_states, n_init=10, random_state=random_state)
    model.fit(X)
    return model


def select_n_states(X: np.ndarray, candidates: list[int], random_state: int) -> tuple[int, dict]:
    """Pick n_states minimizing HMM BIC; also record the GMM BIC curve for the report."""
    curve: dict[int, dict] = {}
    best_k, best_bic = candidates[0], np.inf
    for k in candidates:
        _, hmm_bic = fit_hmm(X, k, random_state)
        _, gmm_bic = fit_gmm(X, k, random_state)
        curve[k] = {"hmm_bic": hmm_bic, "gmm_bic": gmm_bic}
        if hmm_bic < best_bic:
            best_bic, best_k = hmm_bic, k
    return best_k, curve


def _build_result(
    method: str,
    n_states: int,
    labels: np.ndarray,
    means_scaled: np.ndarray,
    scaler: StandardScaler,
    feature_cols: list[str],
    bic: float,
    dates: pd.Index,
    transition_matrix: np.ndarray | None = None,
    probabilities: np.ndarray | None = None,
) -> RegimeFitResult:
    order = _canonical_order(means_scaled)
    labels = _relabel(labels, order)
    means_scaled = means_scaled[order]
    means_original = scaler.inverse_transform(means_scaled)
    means_df = pd.DataFrame(means_original, columns=feature_cols)
    if transition_matrix is not None:
        transition_matrix = transition_matrix[order][:, order]
    if probabilities is not None:
        probabilities = probabilities[:, order]
    return RegimeFitResult(
        method=method,
        n_states=n_states,
        labels=pd.Series(labels, index=dates, name=f"{method}_regime"),
        means=means_df,
        bic=bic,
        transition_matrix=transition_matrix,
        probabilities=probabilities,
    )


def run_regime_detection(model_features: pd.DataFrame, config: dict, n_states: int | None = None) -> dict:
    """Fit HMM (primary), GMM and KMeans (baselines) on the standardized feature matrix.

    If `n_states` is not given, it is chosen by minimizing HMM BIC over
    config["regimes"]["candidate_n_states"]; passing it explicitly lets the
    analyst agent request a re-run with a different state count.
    """
    rcfg = config["regimes"]
    scaler = StandardScaler()
    X = scaler.fit_transform(model_features.values)
    feature_cols = list(model_features.columns)
    dates = model_features.index

    bic_curve: dict = {}
    if n_states is None:
        n_states, bic_curve = select_n_states(X, rcfg["candidate_n_states"], rcfg["random_state"])

    hmm_model, hmm_bic = fit_hmm(X, n_states, rcfg["random_state"])
    hmm_result = _build_result(
        "hmm",
        n_states,
        hmm_model.predict(X),
        hmm_model.means_,
        scaler,
        feature_cols,
        hmm_bic,
        dates,
        transition_matrix=hmm_model.transmat_,
        probabilities=hmm_model.predict_proba(X),
    )

    gmm_model, gmm_bic = fit_gmm(X, n_states, rcfg["random_state"])
    gmm_result = _build_result(
        "gmm",
        n_states,
        gmm_model.predict(X),
        gmm_model.means_,
        scaler,
        feature_cols,
        gmm_bic,
        dates,
        probabilities=gmm_model.predict_proba(X),
    )

    kmeans_model = fit_kmeans(X, n_states, rcfg["random_state"])
    kmeans_result = _build_result(
        "kmeans",
        n_states,
        kmeans_model.labels_,
        kmeans_model.cluster_centers_,
        scaler,
        feature_cols,
        np.nan,
        dates,
    )

    return {
        "scaler": scaler,
        "feature_columns": feature_cols,
        "chosen_n_states": n_states,
        "bic_curve": bic_curve,
        "hmm": hmm_result,
        "gmm": gmm_result,
        "kmeans": kmeans_result,
    }
