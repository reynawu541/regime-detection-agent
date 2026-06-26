from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import yfinance as yf

from .storage import load_parquet_or_empty, save_parquet

logger = logging.getLogger(__name__)


def _incremental_start(cached: pd.DataFrame, default_start: str) -> str:
    """Start date for the next fetch: refetch from `default_start` if the cache
    doesn't reach back that far (e.g. config start_date moved earlier), otherwise
    continue from just after the last cached row."""
    if cached.empty:
        return default_start
    cached_min = pd.Timestamp(cached.index.min())
    if cached_min > pd.Timestamp(default_start):
        return default_start
    last = cached.index.max()
    return (pd.Timestamp(last) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")


def _already_current(start: str) -> bool:
    """True if the incremental start date is beyond today (cache has no gap to fill)."""
    return pd.Timestamp(start) > pd.Timestamp.now().normalize()


def _download_ohlcv(tickers: list[str], start: str) -> dict[str, pd.DataFrame]:
    """Batch-download OHLCV for tickers from `start` to latest available.

    Returns {field: wide_df} where field in {Open, High, Low, Close, Volume}
    and wide_df has a Date index and one column per ticker.
    """
    raw = yf.download(
        tickers, start=start, progress=False, auto_adjust=True, group_by="ticker"
    )
    if raw.empty:
        return {f: pd.DataFrame() for f in ("Open", "High", "Low", "Close", "Volume")}

    fields = {}
    for field in ("Open", "High", "Low", "Close", "Volume"):
        fields[field] = raw.xs(field, axis=1, level=1).copy()
    return fields


def _merge_incremental(cached: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    if new.empty:
        return cached
    combined = pd.concat([cached, new]) if not cached.empty else new
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    return combined


def fetch_universe(config: dict) -> dict:
    """Fetch (incrementally) daily OHLCV for the benchmark + sector ETFs, VIX,
    and macro proxy series. Caches everything to Parquet under raw_data_dir.

    Returns a dict with keys: close, volume, vix, macro, errors.
    """
    errors: list[str] = []
    raw_dir = Path(config["paths"]["raw_data_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    default_start = config["history"]["start_date"]

    tickers = [config["universe"]["benchmark"], *config["universe"]["sector_etfs"]]

    cached_close = load_parquet_or_empty(raw_dir / "close_prices.parquet")
    cached_volume = load_parquet_or_empty(raw_dir / "volumes.parquet")
    start = _incremental_start(cached_close, default_start)

    if _already_current(start):
        close, volume = cached_close, cached_volume
    else:
        try:
            fields = _download_ohlcv(tickers, start)
            close = _merge_incremental(cached_close, fields["Close"])
            volume = _merge_incremental(cached_volume, fields["Volume"])
        except Exception as exc:  # network/Yahoo outage shouldn't crash the whole run
            logger.warning("Equity universe download failed: %s", exc)
            errors.append(f"equity_download_failed: {exc}")
            close, volume = cached_close, cached_volume

    missing = [t for t in tickers if t not in close.columns]
    if missing:
        errors.append(f"missing_tickers: {missing}")

    save_parquet(close, raw_dir / "close_prices.parquet")
    save_parquet(volume, raw_dir / "volumes.parquet")

    vix = _fetch_vix(config, raw_dir, errors)
    macro = _fetch_macro(config, raw_dir, errors)

    return {"close": close, "volume": volume, "vix": vix, "macro": macro, "errors": errors}


def _fetch_vix(config: dict, raw_dir: Path, errors: list[str]) -> pd.Series:
    cached = load_parquet_or_empty(raw_dir / "vix.parquet")
    cached_series = cached["VIX"] if "VIX" in cached.columns else pd.Series(dtype=float)
    start = _incremental_start(cached, config["history"]["start_date"])
    if _already_current(start):
        merged = cached_series
    else:
        try:
            fields = _download_ohlcv([config["universe"]["vix_ticker"]], start)
            new = fields["Close"]
            new_series = new.iloc[:, 0].rename("VIX") if not new.empty else pd.Series(dtype=float)
            merged = _merge_incremental(cached_series.to_frame("VIX"), new_series.to_frame("VIX"))["VIX"]
        except Exception as exc:
            logger.warning("VIX download failed: %s", exc)
            errors.append(f"vix_download_failed: {exc}")
            merged = cached_series
    save_parquet(merged.to_frame("VIX"), raw_dir / "vix.parquet")
    return merged


def _fetch_macro(config: dict, raw_dir: Path, errors: list[str]) -> pd.DataFrame:
    macro_cfg = config.get("macro", {})
    series_map: dict[str, str] = macro_cfg.get("fred_series", {})
    cache_path = raw_dir / "macro.parquet"
    cached = load_parquet_or_empty(cache_path)
    if not series_map:
        return cached

    start = _incremental_start(cached, config["history"]["start_date"])
    if _already_current(start):
        merged = cached
    else:
        try:
            import pandas_datareader.data as web

            new_cols = {}
            for fred_code, friendly_name in series_map.items():
                try:
                    s = web.DataReader(fred_code, "fred", start=start)
                    new_cols[friendly_name] = s[fred_code]
                except Exception as exc:
                    logger.warning("FRED series %s failed: %s", fred_code, exc)
                    errors.append(f"fred_{fred_code}_failed: {exc}")
            new_df = pd.DataFrame(new_cols) if new_cols else pd.DataFrame()
            merged = _merge_incremental(cached, new_df)
        except Exception as exc:
            logger.warning("Macro data fetch failed entirely: %s", exc)
            if not macro_cfg.get("fail_silently", True):
                errors.append(f"macro_fetch_failed: {exc}")
            merged = cached

    save_parquet(merged, cache_path)
    return merged
