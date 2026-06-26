from __future__ import annotations

import numpy as np
import pandas as pd


def compute_returns(close: pd.DataFrame) -> pd.DataFrame:
    return close.pct_change()


def realized_vol(returns: pd.Series, window: int, annualize: bool = True) -> pd.Series:
    vol = returns.rolling(window).std()
    return vol * np.sqrt(252) if annualize else vol


def cross_sectional_dispersion(returns: pd.DataFrame, window: int) -> pd.Series:
    daily_dispersion = returns.std(axis=1)
    return daily_dispersion.rolling(window).mean()


def rolling_avg_correlation(returns: pd.DataFrame, window: int) -> pd.Series:
    """Average pairwise correlation across columns within each rolling window."""
    values = returns.values
    n_assets = values.shape[1]
    mask_offdiag = ~np.eye(n_assets, dtype=bool)
    out = np.full(len(returns), np.nan)
    for i in range(window, len(returns) + 1):
        window_data = values[i - window : i]
        if np.isnan(window_data).any():
            continue
        corr = np.corrcoef(window_data, rowvar=False)
        out[i - 1] = np.nanmean(corr[mask_offdiag])
    return pd.Series(out, index=returns.index)


def rolling_pca_explained_variance(returns: pd.DataFrame, window: int) -> pd.Series:
    """Share of cross-sectional variance explained by the first principal component.

    High values mean assets are moving together (one dominant systemic factor);
    a drop signals a correlation breakdown into more idiosyncratic moves.
    """
    values = returns.values
    out = np.full(len(returns), np.nan)
    for i in range(window, len(returns) + 1):
        window_data = values[i - window : i]
        if np.isnan(window_data).any():
            continue
        std = window_data.std(axis=0)
        std[std == 0] = 1.0
        z = (window_data - window_data.mean(axis=0)) / std
        cov = np.cov(z, rowvar=False)
        eigvals = np.sort(np.linalg.eigvalsh(cov))[::-1]
        out[i - 1] = eigvals[0] / eigvals.sum()
    return pd.Series(out, index=returns.index)


def amihud_illiquidity(close: pd.DataFrame, volume: pd.DataFrame, window: int) -> pd.Series:
    """Cross-sectional average Amihud illiquidity: |return| per dollar traded."""
    abs_returns = close.pct_change().abs()
    dollar_volume = (close * volume).replace(0, np.nan)
    illiq = (abs_returns / dollar_volume).replace([np.inf, -np.inf], np.nan)
    illiq_avg = illiq.mean(axis=1)
    return illiq_avg.rolling(window).mean()


def volume_zscore(volume: pd.DataFrame, window: int) -> pd.Series:
    total_vol = volume.sum(axis=1)
    roll_mean = total_vol.rolling(window).mean()
    roll_std = total_vol.rolling(window).std()
    return (total_vol - roll_mean) / roll_std


def build_feature_matrix(universe: dict, config: dict) -> pd.DataFrame:
    """Combine all regime features into a single date-indexed DataFrame.

    `universe` is the dict returned by ingestion.fetch_universe: close, volume,
    vix, macro wide frames/series.
    """
    fcfg = config["features"]
    benchmark = config["universe"]["benchmark"]
    sector_etfs = config["universe"]["sector_etfs"]

    close = universe["close"]
    volume = universe["volume"]
    returns = compute_returns(close)
    sector_returns = returns[sector_etfs].dropna(how="any")

    feats = pd.DataFrame(index=close.index)

    for window in fcfg["vol_windows"]:
        feats[f"vol_{window}"] = realized_vol(returns[benchmark], window)

    feats["dispersion"] = cross_sectional_dispersion(sector_returns, fcfg["dispersion_window"]).reindex(
        feats.index
    )
    feats["avg_correlation"] = rolling_avg_correlation(sector_returns, fcfg["correlation_window"]).reindex(
        feats.index
    )
    feats["pca_explained_var"] = rolling_pca_explained_variance(
        sector_returns, fcfg["correlation_pca_window"]
    ).reindex(feats.index)

    feats["amihud_illiquidity"] = amihud_illiquidity(
        close[[benchmark, *sector_etfs]], volume[[benchmark, *sector_etfs]], fcfg["liquidity_window"]
    )
    feats["volume_zscore"] = volume_zscore(volume[[benchmark, *sector_etfs]], fcfg["liquidity_window"])

    vix = universe["vix"].reindex(feats.index, method="ffill")
    feats["vix_level"] = vix
    feats["vix_change_5d"] = vix.diff(5)

    macro = universe["macro"]
    if not macro.empty:
        macro_aligned = macro.reindex(feats.index, method="ffill")
        if {"us_10y_yield", "us_2y_yield"}.issubset(macro_aligned.columns):
            feats["yield_curve_slope"] = macro_aligned["us_10y_yield"] - macro_aligned["us_2y_yield"]
        if "high_yield_spread" in macro_aligned.columns:
            feats["high_yield_spread"] = macro_aligned["high_yield_spread"]

    return feats


MODEL_FEATURE_COLUMNS = [
    "vol_21",
    "dispersion",
    "pca_explained_var",
    "amihud_illiquidity",
    "vix_level",
]


def select_model_features(feats: pd.DataFrame) -> pd.DataFrame:
    """Canonical, low-dimensional subset fed into clustering/HMM, one per

    required feature category: volatility, dispersion, correlation breakdown,
    liquidity, macro proxy. Drops the rolling-window burn-in period.
    """
    cols = [c for c in MODEL_FEATURE_COLUMNS if c in feats.columns]
    return feats[cols].dropna(how="any")
