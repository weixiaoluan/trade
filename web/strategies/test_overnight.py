"""
============================================
隔夜效应策略单元测试
Unit Tests for Overnight Effect Strategy
============================================

测试时段判断逻辑和周五跳过逻辑
Requirements: 6.1, 6.4
"""

import unittest
from datetime import datetime, time
from unittest.mock import patch
import pytz

from web.strategies.overnight import (
    OvernightStrategy,
    parse_time,
    is_time_in_range,
    OVERNIGHT_DEFINITION
)
from web.strategies.base import Signal


class TestTimeParsingFunctions(unittest.TestCase):
    """测试时间解析辅助函数"""
    
    def test_parse_time_valid_format(self):
        """测试有效时间格式解析"""
        result = parse_time('14:50')
        self.assertEqual(result, time(14, 50))
        
        result = parse_time('09:30')
        self.assertEqual(result, time(9, 30))
        
        result = parse_time('00:00')
        self.assertEqual(result, time(0, 0))
        
        result = parse_time('23:59')
        self.assertEqual(result, time(23, 59))
    
    def test_is_time_in_range_within_range(self):
        """测试时间在范围内"""
        start = time(14, 50)
        end = time(14, 57)
        
        # 在范围内
        self.assertTrue(is_time_in_range(time(14, 50), start, end))
        self.assertTrue(is_time_in_range(time(14, 53), start, end))
        self.assertTrue(is_time_in_range(time(14, 57), start, end))
    
    def test_is_time_in_range_outside_range(self):
        """测试时间在范围外"""
        start = time(14, 50)
        end = time(14, 57)
        
        # 在范围外
        self.assertFalse(is_time_in_range(time(14, 49), start, end))
        self.assertFalse(is_time_in_range(time(14, 58), start, end))
        self.assertFalse(is_time_in_range(time(9, 30), start, end))


class TestOvernightStrategyBuyTimePeriod(unittest.TestCase):
    """测试买入时段判断逻辑 - Requirements 6.1"""
    
    def setUp(self):
        """设置测试环境"""
        self.strategy = OvernightStrategy()
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
    
    def test_is_buy_time_within_default_range(self):
        """测试默认买入时段内的时间判断"""
        # 14:50 - 买入开始时间
        self.assertTrue(self.strategy._is_buy_time(time(14, 50)))
        # 14:53 - 买入时段中间
        self.assertTrue(self.strategy._is_buy_time(time(14, 53)))
        # 14:57 - 买入结束时间
        self.assertTrue(self.strategy._is_buy_time(time(14, 57)))
    
    def test_is_buy_time_outside_default_range(self):
        """测试默认买入时段外的时间判断"""
        # 14:49 - 买入开始前
        self.assertFalse(self.strategy._is_buy_time(time(14, 49)))
        # 14:58 - 买入结束后
        self.assertFalse(self.strategy._is_buy_time(time(14, 58)))
        # 9:30 - 开盘时间
        self.assertFalse(self.strategy._is_buy_time(time(9, 30)))
        # 15:00 - 收盘时间
        self.assertFalse(self.strategy._is_buy_time(time(15, 0)))
    
    def test_is_buy_time_with_custom_params(self):
        """测试自定义买入时段参数"""
        custom_strategy = OvernightStrategy(params={
            'buy_time_start': '14:45',
            'buy_time_end': '14:55'
        })
        
        # 在自定义范围内
        self.assertTrue(custom_strategy._is_buy_time(time(14, 45)))
        self.assertTrue(custom_strategy._is_buy_time(time(14, 50)))
        self.assertTrue(custom_strategy._is_buy_time(time(14, 55)))
        
        # 在自定义范围外
        self.assertFalse(custom_strategy._is_buy_time(time(14, 44)))
        self.assertFalse(custom_strategy._is_buy_time(time(14, 56)))


class TestOvernightStrategySellTimePeriod(unittest.TestCase):
    """测试卖出时段判断逻辑 - Requirements 6.2"""
    
    def setUp(self):
        """设置测试环境"""
        self.strategy = OvernightStrategy()
    
    def test_is_sell_time_within_default_range(self):
        """测试默认卖出时段内的时间判断"""
        # 9:30 - 卖出开始时间
        self.assertTrue(self.strategy._is_sell_time(time(9, 30)))
        # 9:32 - 卖出时段中间
        self.assertTrue(self.strategy._is_sell_time(time(9, 32)))
        # 9:35 - 卖出结束时间
        self.assertTrue(self.strategy._is_sell_time(time(9, 35)))
    
    def test_is_sell_time_outside_default_range(self):
        """测试默认卖出时段外的时间判断"""
        # 9:29 - 卖出开始前
        self.assertFalse(self.strategy._is_sell_time(time(9, 29)))
        # 9:36 - 卖出结束后
        self.assertFalse(self.strategy._is_sell_time(time(9, 36)))
        # 14:50 - 买入时段
        self.assertFalse(self.strategy._is_sell_time(time(14, 50)))
    
    def test_is_sell_time_with_custom_params(self):
        """测试自定义卖出时段参数"""
        custom_strategy = OvernightStrategy(params={
            'sell_time_start': '09:31',
            'sell_time_end': '09:40'
        })
        
        # 在自定义范围内
        self.assertTrue(custom_strategy._is_sell_time(time(9, 31)))
        self.assertTrue(custom_strategy._is_sell_time(time(9, 35)))
        self.assertTrue(custom_strategy._is_sell_time(time(9, 40)))
        
        # 在自定义范围外
        self.assertFalse(custom_strategy._is_sell_time(time(9, 30)))
        self.assertFalse(custom_strategy._is_sell_time(time(9, 41)))


class TestOvernightStrategyFridaySkip(unittest.TestCase):
    """测试周五跳过逻辑 - Requirements 6.4"""
    
    def setUp(self):
        """设置测试环境"""
        self.strategy = OvernightStrategy()
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
    
    def test_is_friday_detection(self):
        """测试周五检测"""
        # 周五 (weekday = 4)
        friday = datetime(2024, 1, 5, 14, 50, tzinfo=self.beijing_tz)  # 2024-01-05 是周五
        self.assertTrue(self.strategy._is_friday(friday))
        
        # 周一 (weekday = 0)
        monday = datetime(2024, 1, 1, 14, 50, tzinfo=self.beijing_tz)  # 2024-01-01 是周一
        self.assertFalse(self.strategy._is_friday(monday))
        
        # 周三 (weekday = 2)
        wednesday = datetime(2024, 1, 3, 14, 50, tzinfo=self.beijing_tz)  # 2024-01-03 是周三
        self.assertFalse(self.strategy._is_friday(wednesday))
    
    def test_should_skip_trading_on_friday_default(self):
        """测试默认配置下周五跳过交易"""
        friday = datetime(2024, 1, 5, 14, 50, tzinfo=self.beijing_tz)
        self.assertTrue(self.strategy._should_skip_trading(friday))
    
    def test_should_not_skip_trading_on_other_days(self):
        """测试非周五不跳过交易"""
        # 周一到周四都不应该跳过
        for day in [1, 2, 3, 4]:  # 2024-01-01 是周一
            dt = datetime(2024, 1, day, 14, 50, tzinfo=self.beijing_tz)
            self.assertFalse(self.strategy._should_skip_trading(dt))
    
    def test_skip_friday_disabled(self):
        """测试禁用周五跳过功能"""
        strategy_no_skip = OvernightStrategy(params={'skip_friday': False})
        friday = datetime(2024, 1, 5, 14, 50, tzinfo=self.beijing_tz)
        
        # 禁用后周五不应该跳过
        self.assertFalse(strategy_no_skip._should_skip_trading(friday))


class TestOvernightStrategySignalGeneration(unittest.TestCase):
    """测试信号生成逻辑"""
    
    def setUp(self):
        """设置测试环境"""
        self.strategy = OvernightStrategy()
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
        self.applicable_symbol = '510300'
    
    def test_buy_signal_generated_in_buy_time(self):
        """测试买入时段生成买入信号"""
        # 周三 14:53 (买入时段)
        buy_time = datetime(2024, 1, 3, 14, 53, tzinfo=self.beijing_tz)
        
        market_data = {
            self.applicable_symbol: {
                'close': 3.5,
                'avg_overnight_return': 0.002  # 0.2% > 0.1% 阈值
            }
        }
        
        signals = self.strategy.generate_signals(
            [self.applicable_symbol], 
            market_data, 
            current_datetime=buy_time
        )
        
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].signal_type, 'buy')
        self.assertEqual(signals[0].symbol, self.applicable_symbol)
    
    def test_no_signal_outside_trading_time(self):
        """测试非交易时段不生成信号"""
        # 周三 10:00 (非买入/卖出时段)
        non_trading_time = datetime(2024, 1, 3, 10, 0, tzinfo=self.beijing_tz)
        
        market_data = {
            self.applicable_symbol: {
                'close': 3.5,
                'avg_overnight_return': 0.002
            }
        }
        
        signals = self.strategy.generate_signals(
            [self.applicable_symbol], 
            market_data, 
            current_datetime=non_trading_time
        )
        
        self.assertEqual(len(signals), 0)
    
    def test_no_signal_on_friday(self):
        """测试周五不生成买入信号"""
        # 周五 14:53 (买入时段但是周五)
        friday_buy_time = datetime(2024, 1, 5, 14, 53, tzinfo=self.beijing_tz)
        
        market_data = {
            self.applicable_symbol: {
                'close': 3.5,
                'avg_overnight_return': 0.002
            }
        }
        
        signals = self.strategy.generate_signals(
            [self.applicable_symbol], 
            market_data, 
            current_datetime=friday_buy_time
        )
        
        self.assertEqual(len(signals), 0)
    
    def test_no_signal_for_low_overnight_return(self):
        """测试隔夜收益率低于阈值不生成信号"""
        # 周三 14:53 (买入时段)
        buy_time = datetime(2024, 1, 3, 14, 53, tzinfo=self.beijing_tz)
        
        market_data = {
            self.applicable_symbol: {
                'close': 3.5,
                'avg_overnight_return': 0.0005  # 0.05% < 0.1% 阈值
            }
        }
        
        signals = self.strategy.generate_signals(
            [self.applicable_symbol], 
            market_data, 
            current_datetime=buy_time
        )
        
        self.assertEqual(len(signals), 0)
    
    def test_sell_signal_generated_in_sell_time(self):
        """测试卖出时段生成卖出信号"""
        # 周三 9:32 (卖出时段)
        sell_time = datetime(2024, 1, 3, 9, 32, tzinfo=self.beijing_tz)
        
        market_data = {
            self.applicable_symbol: {
                'close': 3.6,
                'has_position': True  # 有持仓
            }
        }
        
        signals = self.strategy.generate_signals(
            [self.applicable_symbol], 
            market_data, 
            current_datetime=sell_time
        )
        
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].signal_type, 'sell')
        self.assertEqual(signals[0].symbol, self.applicable_symbol)
    
    def test_no_sell_signal_without_position(self):
        """测试无持仓时不生成卖出信号"""
        # 周三 9:32 (卖出时段)
        sell_time = datetime(2024, 1, 3, 9, 32, tzinfo=self.beijing_tz)
        
        market_data = {
            self.applicable_symbol: {
                'close': 3.6,
                'has_position': False  # 无持仓
            }
        }
        
        signals = self.strategy.generate_signals(
            [self.applicable_symbol], 
            market_data, 
            current_datetime=sell_time
        )
        
        self.assertEqual(len(signals), 0)


class TestOvernightStrategyDefinition(unittest.TestCase):
    """测试策略定义"""
    
    def test_strategy_definition_registered(self):
        """测试策略定义已注册"""
        self.assertEqual(OVERNIGHT_DEFINITION.id, "overnight")
        self.assertEqual(OVERNIGHT_DEFINITION.name, "隔夜效应策略")
    
    def test_strategy_default_params(self):
        """测试默认参数"""
        params = OvernightStrategy.get_default_params()
        
        self.assertEqual(params['buy_time_start'], '14:50')
        self.assertEqual(params['buy_time_end'], '14:57')
        self.assertEqual(params['sell_time_start'], '09:30')
        self.assertEqual(params['sell_time_end'], '09:35')
        self.assertTrue(params['skip_friday'])
        self.assertEqual(params['max_holding_days'], 1)


class TestOvernightStrategyParamValidation(unittest.TestCase):
    """测试参数验证"""
    
    def test_valid_params(self):
        """测试有效参数验证通过"""
        strategy = OvernightStrategy()
        is_valid, msg = strategy.validate_params()
        self.assertTrue(is_valid)
        self.assertEqual(msg, "")
    
    def test_invalid_buy_time_range(self):
        """测试无效买入时间范围"""
        strategy = OvernightStrategy(params={
            'buy_time_start': '14:57',
            'buy_time_end': '14:50'  # 结束时间早于开始时间
        })
        is_valid, msg = strategy.validate_params()
        self.assertFalse(is_valid)
        self.assertIn("买入开始时间必须早于结束时间", msg)
    
    def test_invalid_sell_time_range(self):
        """测试无效卖出时间范围"""
        strategy = OvernightStrategy(params={
            'sell_time_start': '09:35',
            'sell_time_end': '09:30'  # 结束时间早于开始时间
        })
        is_valid, msg = strategy.validate_params()
        self.assertFalse(is_valid)
        self.assertIn("卖出开始时间必须早于结束时间", msg)


if __name__ == "__main__":
    unittest.main()
