from dataclasses import dataclass
from typing import List, Dict, Optional

import numpy as np
import pandas as pd


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    direction: str
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    return_pct: float


class QuantRegimeStrategy:
    def __init__(
        self,
        initial_capital: float = 100000.0,
        risk_per_trade: float = 0.01,
        allow_short: bool = False,
    ) -> None:
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.allow_short = allow_short
        self.reset()

    def reset(self) -> None:
        self.position: int = 0
        self.position_size: float = 0.0
        self.entry_price: Optional[float] = None
        self.entry_time: Optional[pd.Timestamp] = None
        self.equity: float = self.initial_capital
        self.equity_curve: List[float] = []
        self.timestamps: List[pd.Timestamp] = []
        self.trades: List[Trade] = []

    def on_bar(self, ts: pd.Timestamp, close: float, context: Dict) -> None:
        score = float(context.get("score", 50.0))
        regime = str(context.get("market_regime", "unknown"))
        trend = str(context.get("trend", "neutral"))
        trend_dir = str(context.get("trend_direction", trend))
        bb_status = str(context.get("bb_status", "middle"))
        rsi_status = str(context.get("rsi_status", "neutral"))

        signal = 0

        if self.position == 0:
            if regime == "trending" and score >= 60.0:
                if trend_dir == "bullish":
                    signal = 1
                elif trend_dir == "bearish" and self.allow_short:
                    signal = -1
            elif regime == "ranging":
                if bb_status == "near_lower" and rsi_status == "oversold" and score >= 40.0:
                    signal = 1
                elif (
                    bb_status == "near_upper"
                    and rsi_status == "overbought"
                    and score <= 60.0
                    and self.allow_short
                ):
                    signal = -1

            if signal != 0:
                risk_amount = self.equity * self.risk_per_trade
                if risk_amount > 0.0:
                    stop_distance = close * 0.02
                    if stop_distance > 0.0:
                        size = risk_amount / stop_distance
                        self.position = signal
                        self.position_size = size
                        self.entry_price = close
                        self.entry_time = ts
        else:
            exit_flag = False

            if score <= 40.0:
                exit_flag = True

            if regime == "ranging":
                if self.position == 1 and bb_status == "near_upper":
                    exit_flag = True
                if self.position == -1 and bb_status == "near_lower":
                    exit_flag = True

            if regime == "trending":
                if self.position == 1 and trend_dir == "bearish":
                    exit_flag = True
                if self.position == -1 and trend_dir == "bullish":
                    exit_flag = True

            if exit_flag:
                self._close_trade(ts, close)

        self._update_equity(ts, close)

    def _update_equity(self, ts: pd.Timestamp, close: float) -> None:
        if self.position == 0 or self.entry_price is None:
            equity = self.initial_capital + sum(t.pnl for t in self.trades)
        else:
            direction = self.position
            open_pnl = (close - self.entry_price) * direction * self.position_size
            equity = self.initial_capital + sum(t.pnl for t in self.trades) + open_pnl

        self.equity = equity
        self.timestamps.append(ts)
        self.equity_curve.append(equity)

    def _close_trade(self, ts: pd.Timestamp, close: float) -> None:
        if self.position == 0 or self.entry_price is None or self.entry_time is None:
            return

        direction = self.position
        pnl = (close - self.entry_price) * direction * self.position_size
        notional = self.entry_price * abs(self.position_size)
        return_pct = pnl / notional if notional != 0.0 else 0.0

        trade = Trade(
            entry_time=self.entry_time,
            exit_time=ts,
            direction="long" if direction == 1 else "short",
            entry_price=self.entry_price,
            exit_price=close,
            size=self.position_size,
            pnl=pnl,
            return_pct=return_pct,
        )
        self.trades.append(trade)

        self.position = 0
        self.position_size = 0.0
        self.entry_price = None
        self.entry_time = None

    def get_equity_series(self) -> pd.Series:
        if not self.timestamps:
            return pd.Series(dtype=float)
        return pd.Series(self.equity_curve, index=pd.to_datetime(self.timestamps))

    def get_trades_frame(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame(
                columns=[
                    "entry_time",
                    "exit_time",
                    "direction",
                    "entry_price",
                    "exit_price",
                    "size",
                    "pnl",
                    "return_pct",
                ]
            )
        return pd.DataFrame([t.__dict__ for t in self.trades])


def compute_performance_metrics(
    equity: pd.Series,
    trades: pd.DataFrame,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> Dict[str, float]:
    metrics: Dict[str, float] = {}

    if equity is None or len(equity) < 2:
        return metrics

    equity = equity.sort_index()
    returns = equity.pct_change().dropna()

    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    metrics["total_return"] = total_return

    if not returns.empty:
        avg_return = float(returns.mean())
        vol = float(returns.std(ddof=1))
        metrics["volatility"] = vol
        if vol > 0.0:
            sharpe = (avg_return - risk_free_rate / periods_per_year) / vol * np.sqrt(periods_per_year)
        else:
            sharpe = 0.0
        metrics["sharpe_ratio"] = float(sharpe)

        downside = returns[returns < 0.0]
        downside_std = float(downside.std(ddof=1)) if not downside.empty else 0.0
        if downside_std > 0.0:
            sortino = (avg_return - risk_free_rate / periods_per_year) / downside_std * np.sqrt(periods_per_year)
        else:
            sortino = 0.0
        metrics["sortino_ratio"] = float(sortino)

    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    max_drawdown = float(drawdown.min()) if len(drawdown) > 0 else 0.0
    metrics["max_drawdown"] = max_drawdown

    if len(drawdown) > 0:
        dd_periods = 0
        max_dd_periods = 0
        for v in drawdown:
            if v < 0:
                dd_periods += 1
                if dd_periods > max_dd_periods:
                    max_dd_periods = dd_periods
            else:
                dd_periods = 0
        metrics["max_drawdown_duration"] = float(max_dd_periods)

    if trades is None or trades.empty:
        return metrics

    wins = trades[trades["pnl"] > 0.0]
    losses = trades[trades["pnl"] < 0.0]

    num_trades = len(trades)
    num_wins = len(wins)
    num_losses = len(losses)
    metrics["num_trades"] = float(num_trades)
    metrics["win_rate"] = float(num_wins / num_trades) if num_trades > 0 else 0.0

    avg_win = float(wins["pnl"].mean()) if num_wins > 0 else 0.0
    avg_loss = float(losses["pnl"].mean()) if num_losses > 0 else 0.0
    metrics["avg_win"] = avg_win
    metrics["avg_loss"] = avg_loss

    if avg_loss < 0.0:
        payoff_ratio = avg_win / abs(avg_loss) if abs(avg_loss) > 0.0 else 0.0
    else:
        payoff_ratio = 0.0
    metrics["payoff_ratio"] = float(payoff_ratio)

    win_rate = metrics["win_rate"]
    expectancy = win_rate * avg_win - (1.0 - win_rate) * abs(avg_loss)
    metrics["expectancy"] = float(expectancy)

    gross_profit = float(wins["pnl"].sum()) if num_wins > 0 else 0.0
    gross_loss = float(losses["pnl"].sum()) if num_losses > 0 else 0.0
    if gross_loss < 0.0:
        profit_factor = gross_profit / abs(gross_loss) if abs(gross_loss) > 0.0 else 0.0
    else:
        profit_factor = 0.0
    metrics["profit_factor"] = float(profit_factor)

    return metrics
