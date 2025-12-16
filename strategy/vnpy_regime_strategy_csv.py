"""
RegimeCsvCtaStrategy

vn.py CtaTemplate-style strategy that reads precomputed AI signals
from a CSV file (score, market_regime, etc.) to drive trading.

Usage (in vn.py project):
- Copy this file into: vnpy/app/cta_strategy/strategies/
- Ensure pandas is installed in vn.py environment
- CSV schema (required columns):
    datetime, score, market_regime
  Optional columns:
    trend, bb_status, rsi_status

  where
    - datetime: bar time, e.g. "2024-01-02 09:35:00"
    - score: float, 0-100 quant score from AI system
    - market_regime: "trending" / "ranging" / "squeeze" / "unknown"
    - trend: "bullish" / "bearish" / "neutral" (if missing, will be inferred as neutral)
    - bb_status: "near_upper" / "near_lower" / "middle"
    - rsi_status: "overbought" / "oversold" / "neutral"

Strategy behaviour:
- On each bar, find the latest signal row with datetime <= bar.datetime
- Use CSV-provided score/regime (and optionally trend/bb/rsi) for entry/exit.
- Does NOT compute indicators itself; it fully relies on CSV.
"""

from typing import List, Optional

import pandas as pd

from vnpy.app.cta_strategy import (  # type: ignore
    CtaTemplate,
    BarData,
)


class RegimeCsvCtaStrategy(CtaTemplate):
    """Regime-based AI-driven strategy using external CSV signals."""

    author = "AI-Trade"

    # Strategy parameters
    csv_path: str = ""   # Absolute or relative path to signal CSV

    score_long: float = 60.0   # Min score to open long
    score_short: float = 60.0  # Min score to open short
    score_exit: float = 40.0   # Exit threshold when score deteriorates

    fixed_size: int = 1        # Fixed order size per trade

    parameters: List[str] = [
        "csv_path",
        "score_long",
        "score_short",
        "score_exit",
        "fixed_size",
    ]

    variables: List[str] = [
        "pos",
        "quant_score",
        "market_regime",
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):  # type: ignore[no-untyped-def]
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.signal_df: Optional[pd.DataFrame] = None

        self.quant_score: float = 0.0
        self.market_regime: str = "unknown"

    # ------------------------------------------------------------------
    def on_init(self) -> None:
        """Callback when strategy is inited."""
        self.write_log("RegimeCsvCtaStrategy initialized")
        self.load_signals_from_csv()
        # In a live vn.py environment you might also call self.load_bar(N)

    # ------------------------------------------------------------------
    def on_start(self) -> None:
        """Callback when strategy is started."""
        self.write_log("RegimeCsvCtaStrategy started")

    # ------------------------------------------------------------------
    def on_stop(self) -> None:
        """Callback when strategy is stopped."""
        self.write_log("RegimeCsvCtaStrategy stopped")

    # ------------------------------------------------------------------
    def load_signals_from_csv(self) -> None:
        """Load precomputed signals from a CSV file into a DataFrame."""
        if not self.csv_path:
            self.write_log("csv_path is empty; cannot load signals")
            return

        try:
            df = pd.read_csv(self.csv_path)
        except Exception as e:  # pragma: no cover - runtime environment issue
            self.write_log(f"Failed to read CSV: {e}")
            return

        required_cols = {"datetime", "score", "market_regime"}
        missing = required_cols.difference(df.columns)
        if missing:
            self.write_log(f"CSV missing required columns: {missing}")
            return

        try:
            df["datetime"] = pd.to_datetime(df["datetime"])
        except Exception as e:
            self.write_log(f"Failed to parse datetime column: {e}")
            return

        df = df.set_index("datetime").sort_index()
        self.signal_df = df
        self.write_log(f"Loaded {len(df)} signal rows from {self.csv_path}")

    # ------------------------------------------------------------------
    def _lookup_signal_row(self, dt) -> Optional[pd.Series]:  # type: ignore[no-untyped-def]
        """Find the latest signal row with index <= dt.

        dt: bar.datetime, may be timezone-aware in vn.py; timezone is stripped
        for matching with naive CSV datetimes.
        """
        if self.signal_df is None or self.signal_df.empty:
            return None

        # Normalize datetime to naive for comparison
        if getattr(dt, "tzinfo", None) is not None:
            dt = dt.replace(tzinfo=None)

        df = self.signal_df
        # All signals up to current bar time
        df_sub = df[df.index <= dt]
        if df_sub.empty:
            return None
        return df_sub.iloc[-1]

    # ------------------------------------------------------------------
    def on_bar(self, bar: BarData) -> None:  # type: ignore[override]
        """Main bar callback: read signal from CSV, then trade."""
        if self.signal_df is None:
            # Try lazy load if not loaded yet
            self.load_signals_from_csv()
            if self.signal_df is None:
                return

        row = self._lookup_signal_row(bar.datetime)
        if row is None:
            # No signal yet for this time
            return

        # Extract signal fields (with safe defaults)
        score = float(row.get("score", 50.0))
        regime = str(row.get("market_regime", "unknown"))
        trend = str(row.get("trend", "neutral"))
        bb_status = str(row.get("bb_status", "middle"))
        rsi_status = str(row.get("rsi_status", "neutral"))

        self.quant_score = score
        self.market_regime = regime

        # === Trading logic ===
        # Entry logic when flat
        if self.pos == 0:
            if regime == "trending" and trend == "bullish" and score >= self.score_long:
                self.buy(bar.close_price, self.fixed_size)

            elif regime == "trending" and trend == "bearish" and score >= self.score_short:
                self.short(bar.close_price, self.fixed_size)

            elif regime == "ranging":
                if bb_status == "near_lower" and rsi_status == "oversold" and score >= 40.0:
                    self.buy(bar.close_price, self.fixed_size)
                elif bb_status == "near_upper" and rsi_status == "overbought" and score <= 60.0:
                    self.short(bar.close_price, self.fixed_size)

        # Exit logic when holding long
        elif self.pos > 0:
            exit_flag = False

            if score <= self.score_exit:
                exit_flag = True
            if regime == "ranging" and bb_status == "near_upper":
                exit_flag = True
            if regime == "trending" and trend == "bearish":
                exit_flag = True

            if exit_flag:
                self.sell(bar.close_price, abs(self.pos))

        # Exit logic when holding short
        elif self.pos < 0:
            exit_flag = False

            if score <= self.score_exit:
                exit_flag = True
            if regime == "ranging" and bb_status == "near_lower":
                exit_flag = True
            if regime == "trending" and trend == "bullish":
                exit_flag = True

            if exit_flag:
                self.cover(bar.close_price, abs(self.pos))

        self.put_event()

    # ------------------------------------------------------------------
    def on_tick(self, tick) -> None:  # type: ignore[override]
        """Not used in this bar-based strategy."""
        pass

    # ------------------------------------------------------------------
    def on_order(self, order) -> None:  # type: ignore[override]
        pass

    # ------------------------------------------------------------------
    def on_trade(self, trade) -> None:  # type: ignore[override]
        self.put_event()

    # ------------------------------------------------------------------
    def on_stop_order(self, stop_order) -> None:  # type: ignore[override]
        pass
