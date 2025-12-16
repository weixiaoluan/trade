"""
vn.py Regime-based Quant Strategy

A CtaTemplate-style strategy that mimics the logic of QuantRegimeStrategy:
- Uses a simple quant score (0-100) and market regime (trending / ranging / unknown)
- In trending regime: follow trend
- In ranging regime: mean-reversion between Bollinger Bands

This file is designed to be copied into a vn.py project (cta_strategy app).
"""

from typing import List

from vnpy.app.cta_strategy import (  # type: ignore
    CtaTemplate,
    BarData,
    ArrayManager,
)


class RegimeCtaStrategy(CtaTemplate):
    """Regime-based quantitative strategy in vn.py CtaTemplate style."""

    author = "AI-Trade"

    # Strategy parameters
    fast_window = 12
    slow_window = 26
    signal_window = 9
    rsi_window = 14
    bb_window = 20
    bb_dev = 2.0

    score_long = 60.0       # Minimum score to open long
    score_short = 60.0      # Minimum score to open short
    score_exit = 40.0       # Exit threshold when score deteriorates

    fixed_size = 1          # Fixed order size per trade

    # vn.py parameter/variable declarations
    parameters: List[str] = [
        "fast_window",
        "slow_window",
        "signal_window",
        "rsi_window",
        "bb_window",
        "bb_dev",
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

        self.am = ArrayManager()

        self.quant_score: float = 0.0
        self.market_regime: str = "unknown"

    # ----------------------------------------------------------------------
    def on_init(self) -> None:
        """Callback when strategy is inited."""
        self.write_log("RegimeCtaStrategy initialized")
        self.load_bar(10)

    # ----------------------------------------------------------------------
    def on_start(self) -> None:
        """Callback when strategy is started."""
        self.write_log("RegimeCtaStrategy started")

    # ----------------------------------------------------------------------
    def on_stop(self) -> None:
        """Callback when strategy is stopped."""
        self.write_log("RegimeCtaStrategy stopped")

    # ----------------------------------------------------------------------
    def on_bar(self, bar: BarData) -> None:  # type: ignore[override]
        """Callback of new bar data."""
        self.am.update_bar(bar)
        if not self.am.inited:
            return

        am = self.am

        close_array = am.close
        high_array = am.high
        low_array = am.low

        close = close_array[-1]

        # === 1. Calculate indicators ===
        macd, signal, hist = am.macd(
            self.fast_window,
            self.slow_window,
            self.signal_window,
        )
        rsi = am.rsi(self.rsi_window)
        upper, middle, lower = am.boll(self.bb_window, self.bb_dev)

        macd_hist = hist[-1]
        rsi_val = rsi[-1]
        upper_val = upper[-1]
        middle_val = middle[-1]
        lower_val = lower[-1]

        # Determine Bollinger position
        if close >= upper_val:
            bb_status = "near_upper"
        elif close <= lower_val:
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

        # Simple MA trend
        ma_fast = am.sma(self.fast_window)[-1]
        ma_slow = am.sma(self.slow_window)[-1]

        if ma_fast > ma_slow and close > ma_fast:
            trend = "bullish"
        elif ma_fast < ma_slow and close < ma_fast:
            trend = "bearish"
        else:
            trend = "neutral"

        # === 2. Quant score and regime estimation ===
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
        band_width = upper_val - lower_val
        if band_width > 0:
            pos_in_band = (close - lower_val) / band_width
        else:
            pos_in_band = 0.5

        if bb_status == "near_upper":
            score -= 5.0
        elif bb_status == "near_lower":
            score += 5.0

        # Clamp score
        score = max(0.0, min(100.0, score))

        # Regime via MACD histogram magnitude + band width
        hist_abs = abs(macd_hist)
        if hist_abs > 0.5 and band_width / middle_val > 0.01:
            regime = "trending"
        elif hist_abs < 0.2 and band_width / middle_val < 0.02:
            regime = "ranging"
        else:
            regime = "unknown"

        self.quant_score = score
        self.market_regime = regime

        # === 3. Trading logic ===
        # Entry logic
        if self.pos == 0:
            if regime == "trending" and trend == "bullish" and score >= self.score_long:
                self.buy(bar.close_price, self.fixed_size)
            elif (
                regime == "trending"
                and trend == "bearish"
                and score >= self.score_short
                and self.fixed_size > 0
            ):
                self.short(bar.close_price, self.fixed_size)
            elif regime == "ranging":
                if bb_status == "near_lower" and rsi_status == "oversold" and score >= 40.0:
                    self.buy(bar.close_price, self.fixed_size)
                elif (
                    bb_status == "near_upper"
                    and rsi_status == "overbought"
                    and score <= 60.0
                    and self.fixed_size > 0
                ):
                    self.short(bar.close_price, self.fixed_size)

        # Exit logic
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

    # ----------------------------------------------------------------------
    def on_tick(self, tick) -> None:  # type: ignore[override]
        """Not used in this bar-based strategy."""
        pass

    # ----------------------------------------------------------------------
    def on_order(self, order) -> None:  # type: ignore[override]
        pass

    # ----------------------------------------------------------------------
    def on_trade(self, trade) -> None:  # type: ignore[override]
        self.put_event()

    # ----------------------------------------------------------------------
    def on_stop_order(self, stop_order) -> None:  # type: ignore[override]
        pass
