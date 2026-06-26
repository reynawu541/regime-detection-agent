from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.stats import f_oneway
from sklearn.preprocessing import StandardScaler


@dataclass
class RegimeCharacterization:
    stats: pd.DataFrame
    separation_pvalue: float
    flags: list[str]
    method_agreement: dict[str, float]
    event_check: list[dict]
    current_regime: int


def _episode_durations(labels: pd.Series, state: int) -> list[int]:
    is_state = (labels == state).astype(int).values
    durations: list[int] = []
    run = 0
    for v in is_state:
        if v == 1:
            run += 1
        else:
            if run > 0:
                durations.append(run)
            run = 0
    if run > 0:
        durations.append(run)
    return durations


def _max_drawdown(cum_returns: pd.Series) -> float:
    if cum_returns.empty:
        return np.nan
    running_max = cum_returns.cummax()
    drawdown = cum_returns / running_max - 1
    return float(drawdown.min())


def _regime_stats(returns: pd.Series, labels: pd.Series) -> pd.DataFrame:
    rows = []
    for state in sorted(labels.unique()):
        mask = labels == state
        r = returns[mask].dropna()
        cum = (1 + r).cumprod()
        durations = _episode_durations(labels, state)
        rows.append(
            {
                "state": state,
                "n_days": int(mask.sum()),
                "share_of_days": float(mask.mean()),
                "ann_return": float(r.mean() * 252) if len(r) else np.nan,
                "ann_vol": float(r.std() * np.sqrt(252)) if len(r) else np.nan,
                "sharpe": float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else np.nan,
                "max_drawdown": _max_drawdown(cum),
                "skew": float(r.skew()) if len(r) > 2 else np.nan,
                "kurtosis": float(r.kurtosis()) if len(r) > 2 else np.nan,
                "n_episodes": len(durations),
                "avg_episode_days": float(np.mean(durations)) if durations else np.nan,
            }
        )
    return pd.DataFrame(rows).set_index("state")


def _separation_pvalue(returns: pd.Series, labels: pd.Series) -> float:
    groups = [returns[labels == s].dropna().values for s in sorted(labels.unique())]
    groups = [g for g in groups if len(g) > 1]
    if len(groups) < 2:
        return float("nan")
    _, pvalue = f_oneway(*groups)
    return float(pvalue)


def _degeneracy_flags(
    stats_df: pd.DataFrame, means_df: pd.DataFrame, scaler: StandardScaler, config: dict
) -> list[str]:
    flags = []
    rcfg = config["regimes"]
    small = stats_df[stats_df["share_of_days"] < rcfg["min_regime_share"]]
    for state, row in small.iterrows():
        flags.append(
            f"regime {state} covers only {row['share_of_days']:.1%} of days "
            f"(below {rcfg['min_regime_share']:.0%} threshold)"
        )

    z = scaler.transform(means_df.values)
    for i in range(len(z)):
        for j in range(i + 1, len(z)):
            dist = float(np.linalg.norm(z[i] - z[j]))
            if dist < rcfg["min_state_distinctness"]:
                flags.append(
                    f"regimes {i} and {j} are weakly distinguishable "
                    f"(standardized centroid distance {dist:.2f} < {rcfg['min_state_distinctness']})"
                )
    return flags


def _agreement(a: pd.Series, b: pd.Series) -> float:
    common = a.index.intersection(b.index)
    if len(common) == 0:
        return float("nan")
    return float((a.loc[common].values == b.loc[common].values).mean())


def _event_check(labels: pd.Series, config: dict) -> list[dict]:
    out = []
    for event in config.get("evaluation", {}).get("known_events", []):
        date = pd.Timestamp(event["date"])
        prior_dates = labels.index[labels.index <= date]
        if len(prior_dates) == 0:
            continue
        nearest = prior_dates.max()
        out.append(
            {
                "event_date": event["date"],
                "event_label": event["label"],
                "nearest_trading_day": str(nearest.date()),
                "regime": int(labels.loc[nearest]),
            }
        )
    return out


def characterize_regimes(benchmark_returns: pd.Series, regime_detection: dict, config: dict) -> RegimeCharacterization:
    hmm_result = regime_detection["hmm"]
    labels = hmm_result.labels
    aligned_returns = benchmark_returns.reindex(labels.index)

    stats_df = _regime_stats(aligned_returns, labels)
    pvalue = _separation_pvalue(aligned_returns, labels)
    flags = _degeneracy_flags(stats_df, hmm_result.means, regime_detection["scaler"], config)
    agreement = {
        "hmm_vs_gmm": _agreement(labels, regime_detection["gmm"].labels),
        "hmm_vs_kmeans": _agreement(labels, regime_detection["kmeans"].labels),
    }
    events = _event_check(labels, config)

    return RegimeCharacterization(
        stats=stats_df,
        separation_pvalue=pvalue,
        flags=flags,
        method_agreement=agreement,
        event_check=events,
        current_regime=int(labels.iloc[-1]),
    )
