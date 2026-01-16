"""
============================================
乖离率回归策略单元测试
Unit Tests for BIAS Reversion Strategy
============================================

测试BIAS计算和布林带计算
Requirements: 8.1, 8.2
"""

import unittest
import math

from web.strategies.bias_reversion import (
    BiasReversionStrategy,
    calculate_bias,
    calculate_sma,
    calculate_std,
    calculate_bollinger_bands,
    BIAS_REVERSION_DEFINITION
)
from web.strategies.base import Signal


class TestBiasCalculation(unittest.TestCase):
    """测试BIAS乖离率计算 - Requirements 8.1"""
    
    def test_bias_positive_deviation(self):
        """测试正乖离率计算（价格高于均线）"""
        close = 110.0
        ma = 100.0
        bias = calculate_bias(close, ma)
        
        # BIAS = (110 - 100) / 100 = 0.10 (10%)
        self.assertAlmostEqual(bias, 0.10, places=6)
    
    def test_bias_negative_deviation(self):
        """测试负乖离率计算（价格低于均线）"""
        close = 90.0
        ma = 100.0
        bias = calculate_bias(close, ma)
        
        # BIAS = (90 - 100) / 100 = -0.10 (-10%)
        self.assertAlmostEqual(bias, -0.10, places=6)
    
    def test_bias_zero_deviation(self):
        """测试零乖离率（价格等于均线）"""
        close = 100.0
        ma = 100.0
        bias = calculate_bias(close, ma)
        
        # BIAS = (100 - 100) / 100 = 0
        self.assertAlmostEqual(bias, 0.0, places=6)
    
    def test_bias_with_zero_ma(self):
        """测试均线为零时返回0"""
        close = 100.0
        ma = 0.0
        bias = calculate_bias(close, ma)
        
        self.assertEqual(bias, 0.0)
    
    def test_bias_with_negative_ma(self):
        """测试均线为负数时返回0"""
        close = 100.0
        ma = -10.0
        bias = calculate_bias(close, ma)
        
        self.assertEqual(bias, 0.0)
    
    def test_bias_small_values(self):
        """测试小数值的乖离率计算"""
        close = 3.55
        ma = 3.50
        bias = calculate_bias(close, ma)
        
        # BIAS = (3.55 - 3.50) / 3.50 ≈ 0.0143
        expected = (3.55 - 3.50) / 3.50
        self.assertAlmostEqual(bias, expected, places=6)
    
    def test_bias_large_negative_deviation(self):
        """测试大幅负乖离率"""
        close = 80.0
        ma = 100.0
        bias = calculate_bias(close, ma)
        
        # BIAS = (80 - 100) / 100 = -0.20 (-20%)
        self.assertAlmostEqual(bias, -0.20, places=6)


class TestSMACalculation(unittest.TestCase):
    """测试简单移动平均线计算"""
    
    def test_sma_basic_calculation(self):
        """测试基本SMA计算"""
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]
        period = 5
        sma = calculate_sma(prices, period)
        
        # SMA = (10 + 20 + 30 + 40 + 50) / 5 = 30
        self.assertAlmostEqual(sma, 30.0, places=6)
    
    def test_sma_with_longer_history(self):
        """测试历史数据长于周期的SMA计算"""
        prices = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0]
        period = 5
        sma = calculate_sma(prices, period)
        
        # 只取最后5个: (15 + 20 + 25 + 30 + 35) / 5 = 25
        self.assertAlmostEqual(sma, 25.0, places=6)
    
    def test_sma_insufficient_data(self):
        """测试数据不足时返回最后一个价格"""
        prices = [10.0, 20.0, 30.0]
        period = 5
        sma = calculate_sma(prices, period)
        
        # 数据不足，返回最后一个价格
        self.assertAlmostEqual(sma, 30.0, places=6)
    
    def test_sma_empty_prices(self):
        """测试空价格列表"""
        prices = []
        period = 5
        sma = calculate_sma(prices, period)
        
        self.assertEqual(sma, 0.0)
    
    def test_sma_single_price(self):
        """测试单个价格"""
        prices = [100.0]
        period = 20
        sma = calculate_sma(prices, period)
        
        self.assertAlmostEqual(sma, 100.0, places=6)


class TestStdCalculation(unittest.TestCase):
    """测试标准差计算"""
    
    def test_std_basic_calculation(self):
        """测试基本标准差计算"""
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]
        period = 5
        std = calculate_std(prices, period)
        
        # 均值 = 30, 方差 = ((10-30)^2 + (20-30)^2 + (30-30)^2 + (40-30)^2 + (50-30)^2) / 5
        # 方差 = (400 + 100 + 0 + 100 + 400) / 5 = 200
        # 标准差 = sqrt(200) ≈ 14.142
        expected_std = math.sqrt(200)
        self.assertAlmostEqual(std, expected_std, places=4)
    
    def test_std_constant_prices(self):
        """测试常数价格的标准差为0"""
        prices = [100.0, 100.0, 100.0, 100.0, 100.0]
        period = 5
        std = calculate_std(prices, period)
        
        self.assertAlmostEqual(std, 0.0, places=6)
    
    def test_std_insufficient_data(self):
        """测试数据不足时返回0"""
        prices = [10.0, 20.0]
        period = 5
        std = calculate_std(prices, period)
        
        self.assertEqual(std, 0.0)
    
    def test_std_empty_prices(self):
        """测试空价格列表"""
        prices = []
        period = 5
        std = calculate_std(prices, period)
        
        self.assertEqual(std, 0.0)


class TestBollingerBandsCalculation(unittest.TestCase):
    """测试布林带计算 - Requirements 8.2"""
    
    def test_bollinger_bands_basic(self):
        """测试基本布林带计算"""
        # 创建一个简单的价格序列
        prices = [100.0] * 20  # 20个相同的价格
        upper, middle, lower = calculate_bollinger_bands(prices, period=20, num_std=2.0)
        
        # 均值 = 100, 标准差 = 0
        # 上轨 = 100 + 2*0 = 100
        # 中轨 = 100
        # 下轨 = 100 - 2*0 = 100
        self.assertAlmostEqual(middle, 100.0, places=6)
        self.assertAlmostEqual(upper, 100.0, places=6)
        self.assertAlmostEqual(lower, 100.0, places=6)
    
    def test_bollinger_bands_with_volatility(self):
        """测试有波动的布林带计算"""
        # 创建有波动的价格序列
        prices = [95.0, 100.0, 105.0, 100.0, 95.0] * 4  # 20个价格
        upper, middle, lower = calculate_bollinger_bands(prices, period=20, num_std=2.0)
        
        # 验证中轨是均值
        expected_middle = sum(prices) / len(prices)
        self.assertAlmostEqual(middle, expected_middle, places=4)
        
        # 验证上轨 > 中轨 > 下轨
        self.assertGreater(upper, middle)
        self.assertGreater(middle, lower)
        
        # 验证上下轨对称
        self.assertAlmostEqual(upper - middle, middle - lower, places=4)
    
    def test_bollinger_bands_different_std_multiplier(self):
        """测试不同标准差倍数的布林带"""
        prices = [90.0, 95.0, 100.0, 105.0, 110.0] * 4  # 20个价格
        
        # 2倍标准差
        upper_2, middle_2, lower_2 = calculate_bollinger_bands(prices, period=20, num_std=2.0)
        
        # 1倍标准差
        upper_1, middle_1, lower_1 = calculate_bollinger_bands(prices, period=20, num_std=1.0)
        
        # 中轨应该相同
        self.assertAlmostEqual(middle_2, middle_1, places=6)
        
        # 2倍标准差的带宽应该是1倍的2倍
        bandwidth_2 = upper_2 - lower_2
        bandwidth_1 = upper_1 - lower_1
        self.assertAlmostEqual(bandwidth_2, bandwidth_1 * 2, places=4)
    
    def test_bollinger_bands_insufficient_data(self):
        """测试数据不足时返回最后价格"""
        prices = [100.0, 105.0, 110.0]  # 只有3个价格
        upper, middle, lower = calculate_bollinger_bands(prices, period=20, num_std=2.0)
        
        # 数据不足，返回最后一个价格
        self.assertAlmostEqual(upper, 110.0, places=6)
        self.assertAlmostEqual(middle, 110.0, places=6)
        self.assertAlmostEqual(lower, 110.0, places=6)
    
    def test_bollinger_bands_empty_prices(self):
        """测试空价格列表"""
        prices = []
        upper, middle, lower = calculate_bollinger_bands(prices, period=20, num_std=2.0)
        
        self.assertEqual(upper, 0.0)
        self.assertEqual(middle, 0.0)
        self.assertEqual(lower, 0.0)
    
    def test_bollinger_bands_exact_period_data(self):
        """测试刚好等于周期的数据"""
        prices = list(range(1, 21))  # [1, 2, 3, ..., 20]
        upper, middle, lower = calculate_bollinger_bands(prices, period=20, num_std=2.0)
        
        # 均值 = (1+2+...+20) / 20 = 210 / 20 = 10.5
        expected_middle = 10.5
        self.assertAlmostEqual(middle, expected_middle, places=4)
        
        # 验证上轨 > 中轨 > 下轨
        self.assertGreater(upper, middle)
        self.assertGreater(middle, lower)


class TestBiasReversionStrategyIndicators(unittest.TestCase):
    """测试策略指标计算方法"""
    
    def setUp(self):
        """设置测试环境"""
        self.strategy = BiasReversionStrategy()
    
    def test_calculate_indicators_with_full_data(self):
        """测试完整数据的指标计算"""
        # 创建测试数据
        close_history = [100.0] * 20
        close_history[-1] = 95.0  # 最后一个价格低于均线
        
        data = {
            'close': 95.0,
            'close_history': close_history,
            'volume': 1000000,
            'volume_history': [1500000] * 20  # 均量150万
        }
        
        indicators = self.strategy.calculate_indicators(data)
        
        # 验证MA20计算
        self.assertIsNotNone(indicators['ma20'])
        
        # 验证BIAS计算
        self.assertIsNotNone(indicators['bias'])
        self.assertLess(indicators['bias'], 0)  # 负乖离
        
        # 验证布林带计算
        self.assertIsNotNone(indicators['bb_upper'])
        self.assertIsNotNone(indicators['bb_middle'])
        self.assertIsNotNone(indicators['bb_lower'])
        
        # 验证成交量比率
        self.assertIsNotNone(indicators['volume_ratio'])
        self.assertLess(indicators['volume_ratio'], 1.0)  # 缩量
    
    def test_calculate_indicators_with_precomputed_values(self):
        """测试使用预计算值的指标计算"""
        data = {
            'close': 95.0,
            'close_history': [],
            'ma20': 100.0,
            'bb_upper': 110.0,
            'bb_middle': 100.0,
            'bb_lower': 90.0,
            'volume': 1000000,
            'volume_ma': 1500000
        }
        
        indicators = self.strategy.calculate_indicators(data)
        
        # 验证使用预计算的MA20
        self.assertEqual(indicators['ma20'], 100.0)
        
        # 验证BIAS计算
        expected_bias = (95.0 - 100.0) / 100.0
        self.assertAlmostEqual(indicators['bias'], expected_bias, places=6)
        
        # 验证使用预计算的布林带
        self.assertEqual(indicators['bb_upper'], 110.0)
        self.assertEqual(indicators['bb_middle'], 100.0)
        self.assertEqual(indicators['bb_lower'], 90.0)


class TestBiasReversionStrategySignalGeneration(unittest.TestCase):
    """测试信号生成逻辑"""
    
    def setUp(self):
        """设置测试环境"""
        self.strategy = BiasReversionStrategy()
        self.applicable_symbol = '510300'
    
    def test_buy_signal_at_lower_band_with_low_volume(self):
        """测试触及下轨且缩量时生成买入信号"""
        market_data = {
            self.applicable_symbol: {
                'close': 3.40,
                'close_history': [3.50] * 20,
                'bb_lower': 3.45,
                'bb_middle': 3.50,
                'bb_upper': 3.55,
                'volume': 800000,
                'volume_ma': 1500000  # 缩量到53%
            }
        }
        
        signals = self.strategy.generate_signals([self.applicable_symbol], market_data)
        
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].signal_type, 'buy')
        self.assertEqual(signals[0].symbol, self.applicable_symbol)
        self.assertIsNotNone(signals[0].stop_loss)
    
    def test_no_signal_above_lower_band(self):
        """测试价格高于下轨时不生成信号"""
        market_data = {
            self.applicable_symbol: {
                'close': 3.50,  # 高于下轨
                'close_history': [3.50] * 20,
                'bb_lower': 3.45,
                'bb_middle': 3.50,
                'bb_upper': 3.55,
                'volume': 800000,
                'volume_ma': 1500000
            }
        }
        
        signals = self.strategy.generate_signals([self.applicable_symbol], market_data)
        
        self.assertEqual(len(signals), 0)
    
    def test_no_signal_with_high_volume(self):
        """测试成交量未萎缩时不生成信号"""
        market_data = {
            self.applicable_symbol: {
                'close': 3.40,  # 低于下轨
                'close_history': [3.50] * 20,
                'bb_lower': 3.45,
                'bb_middle': 3.50,
                'bb_upper': 3.55,
                'volume': 1600000,  # 高于均量
                'volume_ma': 1500000
            }
        }
        
        signals = self.strategy.generate_signals([self.applicable_symbol], market_data)
        
        self.assertEqual(len(signals), 0)
    
    def test_no_signal_for_non_applicable_etf(self):
        """测试非适用ETF不生成信号"""
        non_applicable_symbol = '999999'
        
        market_data = {
            non_applicable_symbol: {
                'close': 3.40,
                'close_history': [3.50] * 20,
                'bb_lower': 3.45,
                'bb_middle': 3.50,
                'bb_upper': 3.55,
                'volume': 800000,
                'volume_ma': 1500000
            }
        }
        
        signals = self.strategy.generate_signals([non_applicable_symbol], market_data)
        
        self.assertEqual(len(signals), 0)


class TestBiasReversionStrategyExitConditions(unittest.TestCase):
    """测试出场条件检查"""
    
    def setUp(self):
        """设置测试环境"""
        self.strategy = BiasReversionStrategy()
    
    def test_exit_at_middle_band(self):
        """测试价格回到中轨时出场"""
        position = {
            'symbol': '510300',
            'cost_price': 3.40
        }
        
        market_data = {
            '510300': {
                'close': 3.50,  # 等于中轨
                'close_history': [3.50] * 20,
                'bb_middle': 3.50,
                'bb_upper': 3.55
            }
        }
        
        should_exit, reason = self.strategy.check_exit_conditions(position, market_data)
        
        self.assertTrue(should_exit)
        self.assertIn('中轨', reason)
    
    def test_exit_at_upper_band(self):
        """测试价格触及上轨时出场（禁用中轨出场）"""
        # 禁用中轨出场，只在上轨出场
        strategy = BiasReversionStrategy(params={'exit_at_middle': False})
        
        position = {
            'symbol': '510300',
            'cost_price': 3.40
        }
        
        market_data = {
            '510300': {
                'close': 3.56,  # 高于上轨
                'close_history': [3.50] * 20,
                'bb_middle': 3.50,
                'bb_upper': 3.55
            }
        }
        
        should_exit, reason = strategy.check_exit_conditions(position, market_data)
        
        self.assertTrue(should_exit)
        self.assertIn('上轨', reason)
    
    def test_exit_at_stop_loss(self):
        """测试触发止损时出场"""
        position = {
            'symbol': '510300',
            'cost_price': 3.50
        }
        
        # 止损价 = 3.50 * (1 - 0.05) = 3.325
        market_data = {
            '510300': {
                'close': 3.30,  # 低于止损价
                'close_history': [3.50] * 20,
                'bb_middle': 3.50,
                'bb_upper': 3.55
            }
        }
        
        should_exit, reason = self.strategy.check_exit_conditions(position, market_data)
        
        self.assertTrue(should_exit)
        self.assertIn('止损', reason)
    
    def test_no_exit_in_normal_range(self):
        """测试正常范围内不出场"""
        position = {
            'symbol': '510300',
            'cost_price': 3.40
        }
        
        market_data = {
            '510300': {
                'close': 3.45,  # 在中轨和下轨之间
                'close_history': [3.50] * 20,
                'bb_middle': 3.50,
                'bb_lower': 3.40,
                'bb_upper': 3.60
            }
        }
        
        should_exit, reason = self.strategy.check_exit_conditions(position, market_data)
        
        self.assertFalse(should_exit)
        self.assertEqual(reason, '')


class TestBiasReversionStrategyParamValidation(unittest.TestCase):
    """测试参数验证"""
    
    def test_valid_default_params(self):
        """测试默认参数验证通过"""
        strategy = BiasReversionStrategy()
        is_valid, msg = strategy.validate_params()
        
        self.assertTrue(is_valid)
        self.assertEqual(msg, "")
    
    def test_invalid_ma_period_too_low(self):
        """测试均线周期过低"""
        strategy = BiasReversionStrategy(params={'ma_period': 5})
        is_valid, msg = strategy.validate_params()
        
        self.assertFalse(is_valid)
        self.assertIn("均线周期", msg)
    
    def test_invalid_ma_period_too_high(self):
        """测试均线周期过高"""
        strategy = BiasReversionStrategy(params={'ma_period': 100})
        is_valid, msg = strategy.validate_params()
        
        self.assertFalse(is_valid)
        self.assertIn("均线周期", msg)
    
    def test_invalid_bb_std_too_low(self):
        """测试布林带标准差倍数过低"""
        strategy = BiasReversionStrategy(params={'bb_std': 0.5})
        is_valid, msg = strategy.validate_params()
        
        self.assertFalse(is_valid)
        self.assertIn("标准差倍数", msg)
    
    def test_invalid_stop_loss_pct(self):
        """测试止损百分比无效"""
        strategy = BiasReversionStrategy(params={'stop_loss_pct': 0.15})
        is_valid, msg = strategy.validate_params()
        
        self.assertFalse(is_valid)
        self.assertIn("止损百分比", msg)


class TestBiasReversionStrategyDefinition(unittest.TestCase):
    """测试策略定义"""
    
    def test_strategy_definition_registered(self):
        """测试策略定义已注册"""
        self.assertEqual(BIAS_REVERSION_DEFINITION.id, "bias_reversion")
        self.assertEqual(BIAS_REVERSION_DEFINITION.name, "乖离率回归策略")
    
    def test_strategy_default_params(self):
        """测试默认参数"""
        params = BiasReversionStrategy.get_default_params()
        
        self.assertEqual(params['ma_period'], 20)
        self.assertEqual(params['bb_std'], 2.0)
        self.assertEqual(params['volume_decrease_pct'], 0.8)
        self.assertEqual(params['stop_loss_pct'], 0.05)


if __name__ == "__main__":
    unittest.main()
