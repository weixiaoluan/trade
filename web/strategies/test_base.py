"""
============================================
策略基类单元测试
Unit Tests for Strategy Base Classes
============================================

测试 Signal 数据类和 StrategyRegistry 注册表
Requirements: 1.1
"""

import unittest
from datetime import datetime
from typing import Dict, List, Tuple

from web.strategies.base import Signal, BaseStrategy
from web.strategies.registry import (
    StrategyCategory,
    RiskLevel,
    StrategyDefinition,
    StrategyRegistry
)


class TestSignalDataClass(unittest.TestCase):
    """测试 Signal 数据类"""
    
    def test_signal_creation_with_required_fields(self):
        """测试使用必填字段创建信号"""
        signal = Signal(
            symbol="510300",
            signal_type="buy",
            strength=4,
            confidence=85.0,
            reason="RSI超卖反弹"
        )
        
        self.assertEqual(signal.symbol, "510300")
        self.assertEqual(signal.signal_type, "buy")
        self.assertEqual(signal.strength, 4)
        self.assertEqual(signal.confidence, 85.0)
        self.assertEqual(signal.reason, "RSI超卖反弹")
        self.assertIsNone(signal.target_price)
        self.assertIsNone(signal.stop_loss)
        self.assertIsNone(signal.strategy_id)
        self.assertIsNone(signal.allocated_capital)
        self.assertIsInstance(signal.created_at, datetime)
    
    def test_signal_creation_with_all_fields(self):
        """测试使用所有字段创建信号"""
        signal = Signal(
            symbol="159915",
            signal_type="sell",
            strength=5,
            confidence=90.0,
            reason="触及止盈位",
            target_price=3.50,
            stop_loss=3.20,
            strategy_id="rsi_reversal",
            allocated_capital=50000.0
        )
        
        self.assertEqual(signal.symbol, "159915")
        self.assertEqual(signal.signal_type, "sell")
        self.assertEqual(signal.strength, 5)
        self.assertEqual(signal.confidence, 90.0)
        self.assertEqual(signal.target_price, 3.50)
        self.assertEqual(signal.stop_loss, 3.20)
        self.assertEqual(signal.strategy_id, "rsi_reversal")
        self.assertEqual(signal.allocated_capital, 50000.0)
    
    def test_signal_valid_signal_types(self):
        """测试有效的信号类型"""
        for signal_type in ['buy', 'sell', 'hold']:
            signal = Signal(
                symbol="510300",
                signal_type=signal_type,
                strength=3,
                confidence=70.0,
                reason="测试"
            )
            self.assertEqual(signal.signal_type, signal_type)
    
    def test_signal_invalid_signal_type_raises_error(self):
        """测试无效信号类型抛出异常"""
        with self.assertRaises(ValueError) as context:
            Signal(
                symbol="510300",
                signal_type="invalid",
                strength=3,
                confidence=70.0,
                reason="测试"
            )
        self.assertIn("Invalid signal_type", str(context.exception))
    
    def test_signal_strength_boundary_values(self):
        """测试信号强度边界值"""
        # 有效边界值
        for strength in [1, 5]:
            signal = Signal(
                symbol="510300",
                signal_type="buy",
                strength=strength,
                confidence=70.0,
                reason="测试"
            )
            self.assertEqual(signal.strength, strength)
    
    def test_signal_invalid_strength_raises_error(self):
        """测试无效信号强度抛出异常"""
        for invalid_strength in [0, 6, -1, 10]:
            with self.assertRaises(ValueError) as context:
                Signal(
                    symbol="510300",
                    signal_type="buy",
                    strength=invalid_strength,
                    confidence=70.0,
                    reason="测试"
                )
            self.assertIn("Signal strength must be 1-5", str(context.exception))
    
    def test_signal_confidence_boundary_values(self):
        """测试置信度边界值"""
        # 有效边界值
        for confidence in [0, 100, 50.5]:
            signal = Signal(
                symbol="510300",
                signal_type="buy",
                strength=3,
                confidence=confidence,
                reason="测试"
            )
            self.assertEqual(signal.confidence, confidence)
    
    def test_signal_invalid_confidence_raises_error(self):
        """测试无效置信度抛出异常"""
        for invalid_confidence in [-1, 101, -50, 150]:
            with self.assertRaises(ValueError) as context:
                Signal(
                    symbol="510300",
                    signal_type="buy",
                    strength=3,
                    confidence=invalid_confidence,
                    reason="测试"
                )
            self.assertIn("Confidence must be 0-100", str(context.exception))


class TestStrategyRegistry(unittest.TestCase):
    """测试 StrategyRegistry 注册表"""
    
    def setUp(self):
        """每个测试前清空注册表"""
        StrategyRegistry.clear()
    
    def tearDown(self):
        """每个测试后清空注册表"""
        StrategyRegistry.clear()
    
    def _create_test_strategy(self, strategy_id: str, category: StrategyCategory = StrategyCategory.SHORT_TERM,
                               risk_level: RiskLevel = RiskLevel.MEDIUM) -> StrategyDefinition:
        """创建测试用策略定义"""
        return StrategyDefinition(
            id=strategy_id,
            name=f"测试策略_{strategy_id}",
            category=category,
            description=f"这是{strategy_id}的描述",
            risk_level=risk_level,
            applicable_types=["ETF", "股票"],
            entry_logic="当RSI<30时买入",
            exit_logic="当RSI>70时卖出",
            default_params={"rsi_period": 14},
            min_capital=10000.0
        )
    
    def test_register_strategy(self):
        """测试注册策略"""
        strategy = self._create_test_strategy("test_strategy_1")
        StrategyRegistry.register(strategy)
        
        self.assertEqual(StrategyRegistry.count(), 1)
        retrieved = StrategyRegistry.get_by_id("test_strategy_1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, "test_strategy_1")
    
    def test_register_multiple_strategies(self):
        """测试注册多个策略"""
        for i in range(3):
            strategy = self._create_test_strategy(f"strategy_{i}")
            StrategyRegistry.register(strategy)
        
        self.assertEqual(StrategyRegistry.count(), 3)
    
    def test_get_all_strategies(self):
        """测试获取所有策略"""
        strategies = [
            self._create_test_strategy("s1"),
            self._create_test_strategy("s2"),
            self._create_test_strategy("s3")
        ]
        for s in strategies:
            StrategyRegistry.register(s)
        
        all_strategies = StrategyRegistry.get_all()
        self.assertEqual(len(all_strategies), 3)
        ids = [s.id for s in all_strategies]
        self.assertIn("s1", ids)
        self.assertIn("s2", ids)
        self.assertIn("s3", ids)
    
    def test_get_by_id_existing(self):
        """测试根据ID获取存在的策略"""
        strategy = self._create_test_strategy("existing_strategy")
        StrategyRegistry.register(strategy)
        
        retrieved = StrategyRegistry.get_by_id("existing_strategy")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "测试策略_existing_strategy")
    
    def test_get_by_id_non_existing(self):
        """测试根据ID获取不存在的策略"""
        retrieved = StrategyRegistry.get_by_id("non_existing")
        self.assertIsNone(retrieved)
    
    def test_get_by_category(self):
        """测试根据类别获取策略"""
        # 注册不同类别的策略
        StrategyRegistry.register(self._create_test_strategy("short1", StrategyCategory.SHORT_TERM))
        StrategyRegistry.register(self._create_test_strategy("short2", StrategyCategory.SHORT_TERM))
        StrategyRegistry.register(self._create_test_strategy("swing1", StrategyCategory.SWING))
        StrategyRegistry.register(self._create_test_strategy("long1", StrategyCategory.LONG_TERM))
        
        short_term = StrategyRegistry.get_by_category(StrategyCategory.SHORT_TERM)
        self.assertEqual(len(short_term), 2)
        
        swing = StrategyRegistry.get_by_category(StrategyCategory.SWING)
        self.assertEqual(len(swing), 1)
        
        long_term = StrategyRegistry.get_by_category(StrategyCategory.LONG_TERM)
        self.assertEqual(len(long_term), 1)
    
    def test_get_by_risk_level(self):
        """测试根据风险等级获取策略"""
        StrategyRegistry.register(self._create_test_strategy("low1", risk_level=RiskLevel.LOW))
        StrategyRegistry.register(self._create_test_strategy("med1", risk_level=RiskLevel.MEDIUM))
        StrategyRegistry.register(self._create_test_strategy("med2", risk_level=RiskLevel.MEDIUM))
        StrategyRegistry.register(self._create_test_strategy("high1", risk_level=RiskLevel.HIGH))
        
        low_risk = StrategyRegistry.get_by_risk_level(RiskLevel.LOW)
        self.assertEqual(len(low_risk), 1)
        
        medium_risk = StrategyRegistry.get_by_risk_level(RiskLevel.MEDIUM)
        self.assertEqual(len(medium_risk), 2)
        
        high_risk = StrategyRegistry.get_by_risk_level(RiskLevel.HIGH)
        self.assertEqual(len(high_risk), 1)
    
    def test_unregister_existing_strategy(self):
        """测试取消注册存在的策略"""
        strategy = self._create_test_strategy("to_remove")
        StrategyRegistry.register(strategy)
        self.assertEqual(StrategyRegistry.count(), 1)
        
        result = StrategyRegistry.unregister("to_remove")
        self.assertTrue(result)
        self.assertEqual(StrategyRegistry.count(), 0)
        self.assertIsNone(StrategyRegistry.get_by_id("to_remove"))
    
    def test_unregister_non_existing_strategy(self):
        """测试取消注册不存在的策略"""
        result = StrategyRegistry.unregister("non_existing")
        self.assertFalse(result)
    
    def test_clear_registry(self):
        """测试清空注册表"""
        for i in range(5):
            StrategyRegistry.register(self._create_test_strategy(f"s{i}"))
        
        self.assertEqual(StrategyRegistry.count(), 5)
        StrategyRegistry.clear()
        self.assertEqual(StrategyRegistry.count(), 0)
    
    def test_register_overwrites_existing(self):
        """测试注册相同ID的策略会覆盖"""
        strategy1 = self._create_test_strategy("same_id")
        strategy1_name = strategy1.name
        StrategyRegistry.register(strategy1)
        
        # 创建同ID但不同内容的策略
        strategy2 = StrategyDefinition(
            id="same_id",
            name="新名称",
            category=StrategyCategory.LONG_TERM,
            description="新描述",
            risk_level=RiskLevel.HIGH,
            applicable_types=["期货"],
            entry_logic="新入场逻辑",
            exit_logic="新出场逻辑"
        )
        StrategyRegistry.register(strategy2)
        
        self.assertEqual(StrategyRegistry.count(), 1)
        retrieved = StrategyRegistry.get_by_id("same_id")
        self.assertEqual(retrieved.name, "新名称")


class TestStrategyDefinition(unittest.TestCase):
    """测试 StrategyDefinition 数据类"""
    
    def test_strategy_definition_required_fields(self):
        """测试策略定义必填字段"""
        strategy = StrategyDefinition(
            id="test_id",
            name="测试策略",
            category=StrategyCategory.SHORT_TERM,
            description="策略描述",
            risk_level=RiskLevel.MEDIUM,
            applicable_types=["ETF"],
            entry_logic="入场逻辑",
            exit_logic="出场逻辑"
        )
        
        self.assertEqual(strategy.id, "test_id")
        self.assertEqual(strategy.name, "测试策略")
        self.assertEqual(strategy.category, StrategyCategory.SHORT_TERM)
        self.assertEqual(strategy.risk_level, RiskLevel.MEDIUM)
        self.assertEqual(strategy.min_capital, 10000.0)  # 默认值
        self.assertEqual(strategy.default_params, {})  # 默认值
    
    def test_strategy_definition_with_backtest_data(self):
        """测试带回测数据的策略定义"""
        strategy = StrategyDefinition(
            id="backtest_strategy",
            name="回测策略",
            category=StrategyCategory.SWING,
            description="带回测数据",
            risk_level=RiskLevel.LOW,
            applicable_types=["ETF", "股票"],
            entry_logic="入场",
            exit_logic="出场",
            backtest_return=0.25,
            backtest_sharpe=1.5,
            backtest_max_drawdown=0.10
        )
        
        self.assertEqual(strategy.backtest_return, 0.25)
        self.assertEqual(strategy.backtest_sharpe, 1.5)
        self.assertEqual(strategy.backtest_max_drawdown, 0.10)


class TestStrategyEnums(unittest.TestCase):
    """测试策略相关枚举"""
    
    def test_strategy_category_values(self):
        """测试策略类别枚举值"""
        self.assertEqual(StrategyCategory.SHORT_TERM.value, "short")
        self.assertEqual(StrategyCategory.SWING.value, "swing")
        self.assertEqual(StrategyCategory.LONG_TERM.value, "long")
    
    def test_risk_level_values(self):
        """测试风险等级枚举值"""
        self.assertEqual(RiskLevel.LOW.value, "low")
        self.assertEqual(RiskLevel.MEDIUM.value, "medium")
        self.assertEqual(RiskLevel.HIGH.value, "high")


if __name__ == "__main__":
    unittest.main()
