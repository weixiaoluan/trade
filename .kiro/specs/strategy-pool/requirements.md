# Requirements Document

## Introduction

模拟交易系统策略池功能，允许用户从预设策略中选择多个策略同时运行，配置不同策略的买入金额，并对比各策略的收益表现。系统将实现短线、波段、长线三大类共6种经典量化策略。

## Glossary

- **Strategy_Pool**: 策略池，包含所有可用策略的集合
- **Strategy**: 单个交易策略，包含入场逻辑、出场逻辑和风控规则
- **User_Strategy_Config**: 用户策略配置，记录用户选择的策略及其分配金额
- **Strategy_Performance**: 策略表现，记录策略的收益、胜率等统计数据
- **RSI**: 相对强弱指标 (Relative Strength Index)
- **MA**: 移动平均线 (Moving Average)
- **BIAS**: 乖离率，价格偏离均线的程度
- **Momentum**: 动量，价格变化的速度和方向
- **Risk_Parity**: 风险平价，按波动率倒数分配资金

## Requirements

### Requirement 1: 策略池管理

**User Story:** As a user, I want to view all available strategies in the strategy pool, so that I can understand each strategy's logic and select suitable ones.

#### Acceptance Criteria

1. THE Strategy_Pool SHALL display all preset strategies with name, category, description, and risk level
2. WHEN a user views a strategy THEN the System SHALL show the strategy's entry logic, exit logic, and applicable ETF types
3. THE System SHALL categorize strategies into three types: short-term (1-5 days), swing (1-4 weeks), and long-term (1+ month)
4. WHEN displaying strategy list THEN the System SHALL show each strategy's historical backtest performance metrics

### Requirement 2: 用户策略配置

**User Story:** As a user, I want to select multiple strategies and configure buy amounts for each, so that I can diversify my trading approach.

#### Acceptance Criteria

1. WHEN a user selects a strategy THEN the System SHALL allow configuring the buy amount for that strategy
2. THE User_Strategy_Config SHALL support enabling/disabling individual strategies without deleting configuration
3. WHEN a user configures multiple strategies THEN the System SHALL validate total allocated amount does not exceed available capital
4. THE System SHALL persist user strategy configurations across sessions
5. WHEN a strategy is enabled THEN the System SHALL start monitoring and auto-trading based on that strategy's rules

### Requirement 3: 多策略并行执行

**User Story:** As a user, I want multiple strategies to run simultaneously, so that I can capture different market opportunities.

#### Acceptance Criteria

1. WHEN auto-trading is enabled THEN the System SHALL execute all enabled strategies in parallel
2. WHEN multiple strategies generate signals for the same ETF THEN the System SHALL handle conflicts based on priority rules
3. THE System SHALL track positions separately by strategy for accurate performance attribution
4. WHEN a strategy generates a buy signal THEN the System SHALL use only that strategy's allocated capital
5. IF a strategy's allocated capital is insufficient THEN the System SHALL skip the trade and log the event

### Requirement 4: 策略表现统计与对比

**User Story:** As a user, I want to compare performance across all my strategies, so that I can identify the most effective ones.

#### Acceptance Criteria

1. THE Strategy_Performance SHALL track: total return, win rate, max drawdown, Sharpe ratio, and trade count for each strategy
2. WHEN viewing performance THEN the System SHALL display a comparison table of all enabled strategies
3. THE System SHALL calculate and display cumulative returns chart for each strategy
4. WHEN a trade is completed THEN the System SHALL update the corresponding strategy's performance metrics immediately
5. THE System SHALL provide daily/weekly/monthly performance breakdown for each strategy

### Requirement 5: RSI极限反转策略 (短线)

**User Story:** As a user, I want to use the RSI extreme reversal strategy, so that I can capture short-term oversold rebounds.

#### Acceptance Criteria

1. THE RSI_Strategy SHALL calculate 2-day RSI and 200-day moving average
2. WHEN price is above 200-day MA AND 2-day RSI < 10 THEN the Strategy SHALL generate a buy signal
3. WHEN price closes above 5-day MA THEN the Strategy SHALL generate a sell signal
4. THE Strategy SHALL only apply to high-liquidity broad-based ETFs (e.g., 创业板ETF, 沪深300ETF)
5. THE Strategy SHALL set stop-loss at 3% below entry price

### Requirement 6: 隔夜效应策略 (短线)

**User Story:** As a user, I want to use the overnight effect strategy, so that I can profit from overnight price movements.

#### Acceptance Criteria

1. THE Overnight_Strategy SHALL generate buy signals near market close (14:50-14:57)
2. THE Overnight_Strategy SHALL generate sell signals at market open (9:30-9:35)
3. WHEN selecting targets THEN the Strategy SHALL prefer ETFs with positive overnight return history
4. THE Strategy SHALL skip trading on Fridays to avoid weekend risk
5. THE Strategy SHALL set maximum holding period to 1 trading day

### Requirement 7: 动量轮动策略 (波段)

**User Story:** As a user, I want to use the momentum rotation strategy, so that I can ride sector rotation trends.

#### Acceptance Criteria

1. THE Momentum_Strategy SHALL maintain a pool of 10-15 sector ETFs (半导体、医药、军工、证券、消费等)
2. THE Strategy SHALL calculate 20-day momentum score: (P_t - P_{t-20}) / P_{t-20}
3. WHEN rebalancing THEN the Strategy SHALL buy top 2-3 ETFs by momentum score
4. THE Strategy SHALL rebalance every 5 trading days (weekly)
5. WHEN an ETF drops out of top rankings THEN the Strategy SHALL sell and rotate to higher-ranked ETFs

### Requirement 8: 乖离率回归策略 (波段)

**User Story:** As a user, I want to use the BIAS reversion strategy, so that I can trade mean reversion opportunities.

#### Acceptance Criteria

1. THE BIAS_Strategy SHALL calculate BIAS = (Close - MA20) / MA20
2. THE Strategy SHALL calculate Bollinger Bands with 20-day period and 2 standard deviations
3. WHEN price touches lower Bollinger Band AND volume decreases THEN the Strategy SHALL generate a buy signal
4. WHEN price reaches middle band or upper band THEN the Strategy SHALL generate a sell signal
5. THE Strategy SHALL set stop-loss at 5% below entry price

### Requirement 9: 风险平价策略 (长线)

**User Story:** As a user, I want to use the risk parity strategy, so that I can achieve balanced risk exposure across asset classes.

#### Acceptance Criteria

1. THE RiskParity_Strategy SHALL allocate across stock ETFs, bond ETFs, and gold ETFs
2. THE Strategy SHALL calculate 60-day rolling volatility for each asset
3. THE Strategy SHALL allocate weights inversely proportional to volatility: Weight_i = (1/σ_i) / Σ(1/σ_j)
4. THE Strategy SHALL rebalance monthly when allocation drifts more than 5% from target
5. THE Strategy SHALL maintain minimum 10% allocation to each asset class

### Requirement 10: 自适应均线择时策略 (长线)

**User Story:** As a user, I want to use the adaptive MA timing strategy, so that I can avoid major market downturns.

#### Acceptance Criteria

1. THE AdaptiveMA_Strategy SHALL monitor the benchmark index (沪深300) against its N-day moving average
2. WHEN index price < N-day MA THEN the Strategy SHALL signal to exit equity positions and hold cash/bond ETFs
3. WHEN index price > N-day MA THEN the Strategy SHALL signal to hold equity ETF positions
4. THE Strategy SHALL support configurable MA periods (20, 60, 120 days)
5. THE Strategy SHALL implement a buffer zone (e.g., 1%) to avoid whipsaws near the MA line

### Requirement 11: 策略交易记录

**User Story:** As a user, I want to see detailed trade records for each strategy, so that I can analyze strategy behavior.

#### Acceptance Criteria

1. WHEN a trade is executed THEN the System SHALL record the strategy that generated the signal
2. THE trade record SHALL include: strategy name, entry/exit prices, holding period, profit/loss, and signal reason
3. WHEN viewing trade history THEN the System SHALL allow filtering by strategy
4. THE System SHALL export trade records to CSV format for external analysis
5. THE System SHALL display strategy attribution for each position in the portfolio

### Requirement 12: 策略风控

**User Story:** As a user, I want each strategy to have independent risk controls, so that one strategy's losses don't affect others.

#### Acceptance Criteria

1. THE System SHALL enforce per-strategy position limits (max % of strategy capital per trade)
2. WHEN a strategy's drawdown exceeds threshold THEN the System SHALL pause that strategy and notify user
3. THE System SHALL track daily loss limits per strategy
4. IF a strategy hits daily loss limit THEN the System SHALL stop trading for that strategy until next day
5. THE System SHALL allow user to configure risk parameters for each strategy independently
