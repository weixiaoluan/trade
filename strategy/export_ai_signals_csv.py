"""Export AI-style quant signals (score/regime) to CSV for vn.py strategy.

This script:
1. Uses get_stock_data to fetch OHLCV.
2. Uses simple indicator-based logic (MACD/RSI/Boll/MA) to compute:
   - score (0-100)
   - market_regime (trending/ranging/unknown)
   - trend (bullish/bearish/neutral)
   - bb_status (near_upper/near_lower/middle)
   - rsi_status (overbought/oversold/neutral)
3. Writes a CSV compatible with RegimeCsvCtaStrategy.

Usage (from project root):

    python -m strategy.export_ai_signals_csv --ticker AAPL --period 1y --interval 1d \
        --output ./signals/AAPL_signals.csv

"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from tools.data_fetcher import get_stock_data
from tools import technical_analysis as ta_mod


PROJECT_ROOT = Path(__file__).parent.parent


def _build_dataframe_from_ohlcv(data_json: str) -> pd.DataFrame:
    data = json.loads(data_json)
    if data.get("status") != "success":
        raise RuntimeError(f"get_stock_data error: {data.get('message')}")

    ohlcv = data.get("ohlcv", [])
    if not ohlcv:
        raise RuntimeError("No OHLCV data returned")

    df = pd.DataFrame(ohlcv)

    # Normalize column names
    cols = [c.title() if c not in ("Date", "Datetime") else c for c in df.columns]
    df.columns = cols

    # Determine datetime column
    if "Datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["Datetime"])
    elif "Date" in df.columns:
        df["datetime"] = pd.to_datetime(df["Date"])
    else:
        raise RuntimeError("No Date/Datetime column in OHLCV data")

    # Ensure numeric
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Close"]).reset_index(drop=True)
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


def compute_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Compute score/regime/trend/bb/rsi for each bar using simple rules.

    This mirrors the logic in RegimeCtaStrategy for consistency.
    """
    close = df["Close"].astype(float)

    # Use helper functions from technical_analysis
    macd_line, signal_line, hist = ta_mod._calculate_macd(close)  # type: ignore[attr-defined]
    rsi_series = ta_mod._calculate_rsi(close, 14)  # type: ignore[attr-defined]
    bb_upper, bb_middle, bb_lower = ta_mod._calculate_bollinger_bands(close, 20, 2)  # type: ignore[attr-defined]

    ma_fast = ta_mod._calculate_sma(close, 12)  # type: ignore[attr-defined]
    ma_slow = ta_mod._calculate_sma(close, 26)  # type: ignore[attr-defined]

    # Prepare containers
    scores = []
    regimes = []
    trends = []
    bb_status_list = []
    rsi_status_list = []

    for i in range(len(df)):
        c = close.iloc[i]
        macd_hist = hist.iloc[i]
        rsi_val = rsi_series.iloc[i]
        u = bb_upper.iloc[i]
        m = bb_middle.iloc[i]
        l = bb_lower.iloc[i]
        ma_f = ma_fast.iloc[i]
        ma_s = ma_slow.iloc[i]

        # Skip until we have all indicators
        if np.isnan([macd_hist, rsi_val, u, m, l, ma_f, ma_s]).any():
            scores.append(np.nan)
            regimes.append("unknown")
            trends.append("neutral")
            bb_status_list.append("middle")
            rsi_status_list.append("neutral")
            continue

        # Bollinger status
        if c >= u:
            bb_status = "near_upper"
        elif c <= l:
            bb_status = "near_lower"
        else:
            bb_status = "middle"

        # RSI status
        if rsi_val > 70:
            rsi_status = "overbought"
        elif rsi_val < 30:
            rsi_status = "oversold"
        else:
            rsi_status = "neutral"

        # Trend by MA
        if ma_f > ma_s and c > ma_f:
            trend = "bullish"
        elif ma_f < ma_s and c < ma_f:
            trend = "bearish"
        else:
            trend = "neutral"

        # Score
        score = 50.0

        # Trend component
        if trend == "bullish":
            score += 10.0
        elif trend == "bearish":
            score -= 10.0

        # MACD momentum
        if macd_hist > 0:
            score += 10.0
        else:
            score -= 10.0

        # RSI extremes
        if rsi_status == "overbought":
            score -= 5.0
        elif rsi_status == "oversold":
            score += 5.0

        # Bollinger position
        band_width = u - l
        if band_width > 0:
            # position in band; may be used later if needed
            _pos_in_band = (c - l) / band_width
        else:
            _pos_in_band = 0.5

        if bb_status == "near_upper":
            score -= 5.0
        elif bb_status == "near_lower":
            score += 5.0

        # Clamp
        score = max(0.0, min(100.0, score))

        # Regime estimation (similar to vn.py template)
        hist_abs = abs(macd_hist)
        regime = "unknown"
        if band_width > 0 and m > 0:
            if hist_abs > 0.5 and band_width / m > 0.01:
                regime = "trending"
            elif hist_abs < 0.2 and band_width / m < 0.02:
                regime = "ranging"
        
        scores.append(score)
        regimes.append(regime)
        trends.append(trend)
        bb_status_list.append(bb_status)
        rsi_status_list.append(rsi_status)

    signals = pd.DataFrame({
        "datetime": df["datetime"],
        "score": scores,
        "market_regime": regimes,
        "trend": trends,
        "bb_status": bb_status_list,
        "rsi_status": rsi_status_list,
    })

    # Drop rows where score is NaN (warm-up period)
    signals = signals.dropna(subset=["score"]).reset_index(drop=True)
    # Convert datetime to string for CSV (no timezone)
    signals["datetime"] = signals["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return signals


def export_signals_to_csv(ticker: str, period: str, interval: str, output: Path) -> None:
    raw = get_stock_data(ticker, period, interval)
    df = _build_dataframe_from_ohlcv(raw)
    signals = compute_signals(df)

    output.parent.mkdir(parents=True, exist_ok=True)
    signals.to_csv(output, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export AI-style quant signals to CSV")
    parser.add_argument("--ticker", required=True, help="Ticker symbol, e.g. AAPL or 600519.SS")
    parser.add_argument("--period", default="1y", help="Data period for yfinance/EastMoney (default: 1y)")
    parser.add_argument("--interval", default="1d", help="Data interval (default: 1d)")
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Output CSV path (default: ./signals/<ticker>_signals.csv)",
    )

    args = parser.parse_args()

    ticker = args.ticker
    period = args.period
    interval = args.interval

    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = PROJECT_ROOT / "signals"
        output_path = output_dir / f"{ticker}_signals.csv"

    export_signals_to_csv(ticker, period, interval, output_path)
    print(f"Signals exported to: {output_path}")


if __name__ == "__main__":
    main()
