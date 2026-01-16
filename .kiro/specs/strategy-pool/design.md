# Design Document: Strategy Pool

## Overview

策略池功能为模拟交易系统提供多策略并行执行能力。用户可以从预设的6种经典量化策略中选择，配置各策略的资金分配，系统将同时监控并执行多个策略，并提供策略间的收益对比分析。

## Architecture

```mermaid
graph TB
    subgraph Frontend
        SP[Strategy Pool Page]
        SC[Strategy Config Panel]
        PC[Performance Comparison]
    end
    
    subgraph Backend API
        API[/api/strategies/*]
        SAPI[/api/sim-trade/strategies/*]
    end
    
    subgraph Strategy Engine
        SE[Strategy Executor]
        RSI[RSI Strategy]
        ON[Overnight Strategy]
        MOM[Momentum Strategy]
        BIAS[BIAS Strategy]
        RP[Risk Parity Strategy]
        AMA[Adaptive MA Strategy]
    end
    
    subgraph Data Layer
        DB[(SQLite Database)]
        CACHE[Price Cache]
    end
    
    SP --> API
    SC --> SAPI
    PC --> SAPI
    API --> SE
    SAPI --> SE
    SE --> RSI
    SE --> ON
    SE --> MOM
    SE --> BIAS
    SE --> RP
    SE --> AMA
    SE --> DB
    SE --> CACHE
```

## Components and Interfaces

### 1. Strategy Registry (策略注册表)

```python
# web/strategies/registry.py

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Callable

class StrategyCategory(Enum):
    SHORT_TERM = "short"      # 短线 1-5天
    SWING = "swing"           # 波段 1-4周
    LONG_TERM = "long"        # 长线 1月+

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class StrategyDefinition:
    id: str                           # 策略唯一标识
    name: str                         # 策略名称
    category: StrategyCategory        # 策略类别
    description: str                  # 策略描述
    risk_level: RiskLevel             # 风险等级
    applicable_types: List[str]       # 适用标的类型
    entry_logic: str                  # 入场逻辑描述
    exit_logic: str                   # 出场逻辑描述
    default_params: Dict              # 默认参数
    min_capital: float                # 最小资金要求
    
class StrategyRegistry:
    """策略注册表 - 管理所有预设策略"""
    _strategies: Dict[str, StrategyDefinition] = {}
    
    @classmethod
    def register(cls, strategy: StrategyDefinition):
        cls._strategies[strategy.id] = strategy
    
    @classmethod
    def get_all(cls) -> List[StrategyDefinition]:
        return list(cls._strategies.values())
    
    @classmethod
    def get_by_id(cls, strategy_id: str) -> StrategyDefinition:
        return cls._strategies.get(strategy_id)
    
    @classmethod
    def get_by_category(cls, category: StrategyCategory) -> List[StrategyDefinition]:
        return [s for s in cls._strategies.values() if s.category == category]
```

### 2. Strategy Base Class (策略基类)

```python
# web/strategies/base.py

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Signal:
    symbol: str
    signal_type: str          # 'buy', 'sell', 'hold'
    strength: int             # 1-5
    confidence: float         # 0-100
    reason: str
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None

class BaseStrategy(ABC):
    """策略基类 - 所有策略必须继承此类"""
    
    def __init__(self, params: Dict = None):
        self.params = params or {}
    
    @abstractmethod
    def generate_signals(self, symbols: List[str], market_data: Dict) -> List[Signal]:
        """生成交易信号"""
        pass
    
    @abstractmethod
    def calculate_position_size(self, signal: Signal, capital: float) -> int:
        """计算建议仓位"""
        pass
    
    @abstractmethod
    def check_exit_conditions(self, position: Dict, market_data: Dict) -> Tuple[bool, str]:
        """检查出场条件"""
        pass
```

### 3. Preset Strategies (预设策略实现)

#### 3.1 RSI极限反转策略 (短线)

```python
# web/strategies/rsi_reversal.py

class RSIReversalStrategy(BaseStrategy):
    """RSI极限反转策略 - Connors RSI"""
    
    DEFAULT_PARAMS = {
        'rsi_period': 2,
        'rsi_oversold': 10,
        'ma_long_period': 200,
        'ma_exit_period': 5,
        'stop_loss_pct': 0.03,
        'applicable_etfs': ['159915', '510300', '510500', '159919']
    }
    
    def generate_signals(self, symbols: List[str], market_data: Dict) -> List[Signal]:
        signals = []
        for symbol in symbols:
            if symbol not in self.params.get('applicable_etfs', []):
                continue
            
            data = market_data.get(symbol)
            if not data:
                continue
            
            close = data['close']
            ma200 = data['ma200']
            rsi2 = data['rsi2']
            
            # 买入条件：价格在200日均线上方 且 2日RSI<10
            if close > ma200 and rsi2 < self.params['rsi_oversold']:
                signals.append(Signal(
                    symbol=symbol,
                    signal_type='buy',
                    strength=5,
                    confidence=85,
                    reason=f'RSI极度超卖({rsi2:.1f}),价格在MA200上方',
                    stop_loss=close * (1 - self.params['stop_loss_pct'])
                ))
        return signals
    
    def check_exit_conditions(self, position: Dict, market_data: Dict) -> Tuple[bool, str]:
        data = market_data.get(position['symbol'])
        if not data:
            return False, ''
        
        # 出场条件：收盘价高于5日均线
        if data['close'] > data['ma5']:
            return True, '价格突破5日均线,止盈出场'
        
        # 止损
        if data['close'] < position['cost_price'] * (1 - self.params['stop_loss_pct']):
            return True, '触发止损'
        
        return False, ''
```

#### 3.2 隔夜效应策略 (短线)

```python
# web/strategies/overnight.py

class OvernightStrategy(BaseStrategy):
    """隔夜效应策略 - 收盘买入开盘卖出"""
    
    DEFAULT_PARAMS = {
        'buy_time_start': '14:50',
        'buy_time_end': '14:57',
        'sell_time_start': '09:30',
        'sell_time_end': '09:35',
        'min_overnight_return': 0.001,  # 历史隔夜收益率阈值
        'skip_friday': True
    }
    
    def generate_signals(self, symbols: List[str], market_data: Dict) -> List[Signal]:
        now = get_beijing_now()
        
        # 周五不交易
        if self.params['skip_friday'] and now.weekday() == 4:
            return []
        
        current_time = now.strftime('%H:%M')
        signals = []
        
        # 买入时段
        if self.params['buy_time_start'] <= current_time <= self.params['buy_time_end']:
            for symbol in symbols:
                data = market_data.get(symbol)
                if data and data.get('avg_overnight_return', 0) > self.params['min_overnight_return']:
                    signals.append(Signal(
                        symbol=symbol,
                        signal_type='buy',
                        strength=3,
                        confidence=70,
                        reason=f'隔夜效应买入,历史隔夜收益{data["avg_overnight_return"]*100:.2f}%'
                    ))
        
        return signals
```

#### 3.3 动量轮动策略 (波段)

```python
# web/strategies/momentum_rotation.py

class MomentumRotationStrategy(BaseStrategy):
    """动量轮动策略 - 行业ETF轮动"""
    
    DEFAULT_PARAMS = {
        'momentum_period': 20,
        'top_n': 3,
        'rebalance_days': 5,
        'sector_etfs': [
            '512480',  # 半导体ETF
            '512010',  # 医药ETF
            '512660',  # 军工ETF
            '512880',  # 证券ETF
            '159928',  # 消费ETF
            '512200',  # 房地产ETF
            '512800',  # 银行ETF
            '515030',  # 新能源车ETF
            '159941',  # 纳指ETF
            '513050',  # 中概互联ETF
        ]
    }
    
    def calculate_momentum_score(self, data: Dict) -> float:
        """计算动量得分: (P_t - P_{t-20}) / P_{t-20}"""
        if not data or 'close' not in data or 'close_20d_ago' not in data:
            return -999
        return (data['close'] - data['close_20d_ago']) / data['close_20d_ago']
    
    def generate_signals(self, symbols: List[str], market_data: Dict) -> List[Signal]:
        # 计算所有ETF的动量得分
        scores = []
        for symbol in self.params['sector_etfs']:
            data = market_data.get(symbol)
            score = self.calculate_momentum_score(data)
            if score > -999:
                scores.append((symbol, score, data))
        
        # 按得分排序
        scores.sort(key=lambda x: x[1], reverse=True)
        
        signals = []
        # 买入前N名
        for symbol, score, data in scores[:self.params['top_n']]:
            signals.append(Signal(
                symbol=symbol,
                signal_type='buy',
                strength=4,
                confidence=75,
                reason=f'动量排名前{self.params["top_n"]},得分{score*100:.2f}%'
            ))
        
        return signals
```

#### 3.4 乖离率回归策略 (波段)

```python
# web/strategies/bias_reversion.py

class BiasReversionStrategy(BaseStrategy):
    """乖离率回归策略 - 布林带+乖离率"""
    
    DEFAULT_PARAMS = {
        'ma_period': 20,
        'bb_std': 2,
        'volume_decrease_pct': 0.8,
        'stop_loss_pct': 0.05
    }
    
    def calculate_bias(self, close: float, ma20: float) -> float:
        """计算乖离率: BIAS = (Close - MA20) / MA20"""
        return (close - ma20) / ma20 if ma20 > 0 else 0
    
    def generate_signals(self, symbols: List[str], market_data: Dict) -> List[Signal]:
        signals = []
        for symbol in symbols:
            data = market_data.get(symbol)
            if not data:
                continue
            
            close = data['close']
            bb_lower = data['bb_lower']
            bb_middle = data['bb_middle']
            volume = data['volume']
            volume_ma = data['volume_ma']
            
            # 买入条件：触及下轨 且 缩量
            if close <= bb_lower and volume < volume_ma * self.params['volume_decrease_pct']:
                signals.append(Signal(
                    symbol=symbol,
                    signal_type='buy',
                    strength=4,
                    confidence=80,
                    reason=f'触及布林下轨,缩量{volume/volume_ma*100:.0f}%',
                    stop_loss=close * (1 - self.params['stop_loss_pct'])
                ))
        
        return signals
```

#### 3.5 风险平价策略 (长线)

```python
# web/strategies/risk_parity.py

class RiskParityStrategy(BaseStrategy):
    """风险平价策略 - 按波动率倒数分配"""
    
    DEFAULT_PARAMS = {
        'volatility_period': 60,
        'rebalance_threshold': 0.05,
        'min_allocation': 0.10,
        'asset_classes': {
            'stock': ['510300', '159915'],   # 股票ETF
            'bond': ['511010', '511260'],     # 债券ETF
            'gold': ['518880']                # 黄金ETF
        }
    }
    
    def calculate_weights(self, market_data: Dict) -> Dict[str, float]:
        """计算风险平价权重: Weight_i = (1/σ_i) / Σ(1/σ_j)"""
        volatilities = {}
        for asset_class, symbols in self.params['asset_classes'].items():
            vols = []
            for symbol in symbols:
                data = market_data.get(symbol)
                if data and 'volatility_60d' in data:
                    vols.append(data['volatility_60d'])
            if vols:
                volatilities[asset_class] = sum(vols) / len(vols)
        
        # 计算权重
        inv_vols = {k: 1/v for k, v in volatilities.items() if v > 0}
        total_inv_vol = sum(inv_vols.values())
        
        weights = {}
        for asset_class in volatilities:
            raw_weight = inv_vols.get(asset_class, 0) / total_inv_vol if total_inv_vol > 0 else 0
            weights[asset_class] = max(raw_weight, self.params['min_allocation'])
        
        # 归一化
        total = sum(weights.values())
        return {k: v/total for k, v in weights.items()}
    
    def generate_signals(self, symbols: List[str], market_data: Dict) -> List[Signal]:
        target_weights = self.calculate_weights(market_data)
        signals = []
        
        for asset_class, weight in target_weights.items():
            for symbol in self.params['asset_classes'].get(asset_class, []):
                signals.append(Signal(
                    symbol=symbol,
                    signal_type='buy',
                    strength=3,
                    confidence=70,
                    reason=f'风险平价配置,{asset_class}目标权重{weight*100:.1f}%'
                ))
        
        return signals
```

#### 3.6 自适应均线择时策略 (长线)

```python
# web/strategies/adaptive_ma.py

class AdaptiveMAStrategy(BaseStrategy):
    """自适应均线择时策略 - 均线择时"""
    
    DEFAULT_PARAMS = {
        'ma_period': 60,
        'buffer_zone': 0.01,
        'benchmark': '000300',  # 沪深300指数
        'equity_etfs': ['510300', '159915', '510500'],
        'safe_etfs': ['511010', '511880']  # 货币/债券ETF
    }
    
    def generate_signals(self, symbols: List[str], market_data: Dict) -> List[Signal]:
        benchmark_data = market_data.get(self.params['benchmark'])
        if not benchmark_data:
            return []
        
        close = benchmark_data['close']
        ma = benchmark_data[f'ma{self.params["ma_period"]}']
        buffer = ma * self.params['buffer_zone']
        
        signals = []
        
        if close > ma + buffer:
            # 牛市：持有股票ETF
            for symbol in self.params['equity_etfs']:
                signals.append(Signal(
                    symbol=symbol,
                    signal_type='buy',
                    strength=4,
                    confidence=80,
                    reason=f'指数在{self.params["ma_period"]}日均线上方,持有股票'
                ))
        elif close < ma - buffer:
            # 熊市：切换到安全资产
            for symbol in self.params['safe_etfs']:
                signals.append(Signal(
                    symbol=symbol,
                    signal_type='buy',
                    strength=4,
                    confidence=80,
                    reason=f'指数跌破{self.params["ma_period"]}日均线,切换安全资产'
                ))
            # 卖出股票ETF
            for symbol in self.params['equity_etfs']:
                signals.append(Signal(
                    symbol=symbol,
                    signal_type='sell',
                    strength=5,
                    confidence=90,
                    reason=f'指数跌破均线,清仓股票ETF'
                ))
        
        return signals
```

### 4. Strategy Executor (策略执行器)

```python
# web/strategies/executor.py

class StrategyExecutor:
    """策略执行器 - 并行执行多个策略"""
    
    def __init__(self, username: str):
        self.username = username
        self.strategies: Dict[str, BaseStrategy] = {}
    
    def load_user_strategies(self):
        """加载用户启用的策略"""
        configs = db_get_user_strategy_configs(self.username)
        for config in configs:
            if config['enabled']:
                strategy_class = get_strategy_class(config['strategy_id'])
                self.strategies[config['strategy_id']] = strategy_class(config['params'])
    
    def execute_all(self, market_data: Dict) -> List[Dict]:
        """执行所有启用的策略"""
        all_signals = []
        
        for strategy_id, strategy in self.strategies.items():
            config = db_get_user_strategy_config(self.username, strategy_id)
            symbols = self._get_strategy_symbols(strategy_id)
            
            signals = strategy.generate_signals(symbols, market_data)
            
            for signal in signals:
                signal.strategy_id = strategy_id
                signal.allocated_capital = config['allocated_capital']
                all_signals.append(signal)
        
        # 处理冲突
        resolved_signals = self._resolve_conflicts(all_signals)
        
        # 执行交易
        results = []
        for signal in resolved_signals:
            result = self._execute_signal(signal)
            if result:
                results.append(result)
        
        return results
    
    def _resolve_conflicts(self, signals: List[Signal]) -> List[Signal]:
        """解决同一标的的信号冲突"""
        by_symbol = {}
        for signal in signals:
            if signal.symbol not in by_symbol:
                by_symbol[signal.symbol] = []
            by_symbol[signal.symbol].append(signal)
        
        resolved = []
        for symbol, symbol_signals in by_symbol.items():
            if len(symbol_signals) == 1:
                resolved.append(symbol_signals[0])
            else:
                # 优先级：卖出 > 买入，强度高 > 强度低
                sell_signals = [s for s in symbol_signals if s.signal_type == 'sell']
                if sell_signals:
                    resolved.append(max(sell_signals, key=lambda x: x.strength))
                else:
                    resolved.append(max(symbol_signals, key=lambda x: x.strength))
        
        return resolved
```

## Data Models

### Database Schema

```sql
-- 策略配置表
CREATE TABLE IF NOT EXISTS strategy_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    allocated_capital REAL DEFAULT 100000,
    params TEXT,  -- JSON格式的策略参数
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(username, strategy_id)
);

-- 策略表现统计表
CREATE TABLE IF NOT EXISTS strategy_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    date TEXT NOT NULL,
    total_return REAL DEFAULT 0,
    daily_return REAL DEFAULT 0,
    win_count INTEGER DEFAULT 0,
    loss_count INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0,
    max_drawdown REAL DEFAULT 0,
    sharpe_ratio REAL DEFAULT 0,
    trade_count INTEGER DEFAULT 0,
    position_value REAL DEFAULT 0,
    UNIQUE(username, strategy_id, date)
);

-- 修改持仓表，添加策略字段
ALTER TABLE sim_positions ADD COLUMN strategy_id TEXT;

-- 修改交易记录表，添加策略字段
ALTER TABLE sim_trade_records ADD COLUMN strategy_id TEXT;
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Strategy Metadata Completeness
*For any* strategy in the strategy pool, the strategy definition SHALL contain all required fields: id, name, category, description, risk_level, entry_logic, exit_logic, and applicable_types.
**Validates: Requirements 1.1, 1.2, 1.3**

### Property 2: Strategy Configuration Persistence
*For any* user strategy configuration, saving and then loading the configuration SHALL produce an equivalent configuration object.
**Validates: Requirements 2.1, 2.2, 2.4**

### Property 3: Capital Allocation Validation
*For any* set of strategy configurations for a user, the sum of allocated_capital across all enabled strategies SHALL NOT exceed the user's available capital.
**Validates: Requirements 2.3**

### Property 4: Strategy Position Isolation
*For any* trade executed by a strategy, the trade amount SHALL NOT exceed that strategy's allocated_capital, and the position SHALL be tagged with the strategy_id.
**Validates: Requirements 3.3, 3.4, 3.5**

### Property 5: Signal Conflict Resolution
*For any* set of signals for the same symbol from different strategies, the conflict resolution SHALL produce exactly one signal, prioritizing sell signals over buy signals.
**Validates: Requirements 3.2**

### Property 6: Performance Metrics Completeness
*For any* strategy with at least one completed trade, the performance record SHALL contain: total_return, win_rate, max_drawdown, sharpe_ratio, and trade_count.
**Validates: Requirements 4.1, 4.2, 4.3**

### Property 7: RSI Strategy Signal Generation
*For any* ETF with price above 200-day MA and 2-day RSI below 10, the RSI strategy SHALL generate a buy signal with strength >= 4.
**Validates: Requirements 5.1, 5.2, 5.3**

### Property 8: Momentum Score Calculation
*For any* ETF with valid price history, the momentum score SHALL equal (P_t - P_{t-20}) / P_{t-20}, and the top N ETFs by score SHALL receive buy signals.
**Validates: Requirements 7.2, 7.3**

### Property 9: Risk Parity Weight Calculation
*For any* set of assets with positive volatility, the risk parity weights SHALL be inversely proportional to volatility, and each asset class SHALL have at least 10% allocation.
**Validates: Requirements 9.3, 9.5**

### Property 10: Adaptive MA Signal Generation
*For any* benchmark index price below N-day MA minus buffer, the strategy SHALL generate sell signals for equity ETFs and buy signals for safe assets.
**Validates: Requirements 10.2, 10.3, 10.5**

### Property 11: Trade Record Strategy Attribution
*For any* trade executed by the system, the trade record SHALL contain the strategy_id that generated the signal.
**Validates: Requirements 11.1, 11.2**

### Property 12: Risk Control Enforcement
*For any* strategy with drawdown exceeding the configured threshold, the strategy SHALL be paused and no new buy signals SHALL be generated.
**Validates: Requirements 12.1, 12.2, 12.4**

## Error Handling

1. **策略加载失败**: 记录错误日志，跳过该策略，继续执行其他策略
2. **市场数据缺失**: 对缺失数据的标的跳过信号生成，不影响其他标的
3. **资金不足**: 记录日志，跳过交易，不影响其他策略
4. **数据库错误**: 回滚事务，返回错误信息给用户
5. **策略参数无效**: 使用默认参数，记录警告日志

## Testing Strategy

### Unit Tests
- 测试每个策略的信号生成逻辑
- 测试技术指标计算（RSI、MA、BIAS、布林带等）
- 测试资金分配验证
- 测试冲突解决逻辑

### Property-Based Tests
- 使用 Hypothesis 库生成随机市场数据
- 验证策略信号生成的一致性
- 验证资金分配约束
- 验证性能指标计算

### Integration Tests
- 测试多策略并行执行
- 测试策略配置持久化
- 测试性能统计更新

**Property-Based Testing Configuration**:
- Library: Hypothesis (Python)
- Minimum iterations: 100 per property
- Tag format: **Feature: strategy-pool, Property {number}: {property_text}**
