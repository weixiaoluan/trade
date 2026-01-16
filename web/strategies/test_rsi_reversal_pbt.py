"""
============================================
RSI极限反转策略属性测试
Property-Based Tests for RSI Reversal Strategy
============================================

Feature: strategy-pool, Property 7: RSI Strategy Signal Generation
Validates: Requirements 5.1, 5.2, 5.3

Property 7: RSI Strategy Signal Generation
*For any* ETF with price above 200-day MA and 2-day RSI below 10, 
the RSI strategy SHALL generate a buy signal with strength >= 4.
"""

import unittest
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, List

from web.strategies.rsi_reversal import RSIReversalStrategy, calculate_rsi, calculate_sma
from web.strategies.base import Signal


# Custom strategies for generating valid market data
@st.composite
def market_data_with_buy_conditions(draw):
    """
    Generate market data that satisfies RSI buy conditions:
    - Price above 200-day MA
    - 2-day RSI < 10
    
    This strategy generates data where buy signals SHOULD be generated.
    """
    # Generate a base price (reasonable ETF price range)
    base_price = draw(st.floats(min_value=0.5, max_value=10.0, allow_nan=False, allow_infinity=False))
    
    # MA200 should be below current price (price > MA200)
    ma200_ratio = draw(st.floats(min_value=0.80, max_value=0.99, allow_nan=False, allow_infinity=False))
    ma200 = base_price * ma200_ratio
    
    # RSI2 should be below 10 (oversold condition)
    rsi2 = draw(st.floats(min_value=0.1, max_value=9.9, allow_nan=False, allow_infinity=False))
    
    # Generate close history that would produce low RSI
    # For RSI < 10, we need consecutive down days
    history_length = draw(st.integers(min_value=201, max_value=250))
    
    # Start with a higher price and create declining prices for recent days
    start_price = base_price * 1.1
    close_history = []
    
    # Generate stable prices for most of history
    for i in range(history_length - 5):
        variation = draw(st.floats(min_value=-0.02, max_value=0.02, allow_nan=False, allow_infinity=False))
        price = start_price * (1 + variation)
        close_history.append(max(0.1, price))
    
    # Generate declining prices for last 5 days to create low RSI
    current = close_history[-1] if close_history else start_price
    for i in range(5):
        decline = draw(st.floats(min_value=0.01, max_value=0.03, allow_nan=False, allow_infinity=False))
        current = current * (1 - decline)
        close_history.append(max(0.1, current))
    
    # Set the final close price
    close_history[-1] = base_price
    
    return {
        'close': base_price,
        'ma200': ma200,
        'rsi2': rsi2,
        'close_history': close_history
    }


@st.composite
def market_data_without_buy_conditions(draw):
    """
    Generate market data that does NOT satisfy RSI buy conditions.
    Either price <= MA200 OR RSI2 >= 10
    """
    base_price = draw(st.floats(min_value=0.5, max_value=10.0, allow_nan=False, allow_infinity=False))
    
    # Randomly choose which condition to violate
    violate_ma = draw(st.booleans())
    
    if violate_ma:
        # Price below or equal to MA200
        ma200_ratio = draw(st.floats(min_value=1.0, max_value=1.2, allow_nan=False, allow_infinity=False))
        ma200 = base_price * ma200_ratio
        rsi2 = draw(st.floats(min_value=0.1, max_value=50.0, allow_nan=False, allow_infinity=False))
    else:
        # RSI >= 10 (not oversold)
        ma200_ratio = draw(st.floats(min_value=0.80, max_value=0.99, allow_nan=False, allow_infinity=False))
        ma200 = base_price * ma200_ratio
        rsi2 = draw(st.floats(min_value=10.0, max_value=90.0, allow_nan=False, allow_infinity=False))
    
    return {
        'close': base_price,
        'ma200': ma200,
        'rsi2': rsi2,
        'close_history': [base_price] * 201
    }


class TestRSIStrategySignalGenerationProperty(unittest.TestCase):
    """
    Property-Based Tests for RSI Strategy Signal Generation
    
    Feature: strategy-pool, Property 7: RSI Strategy Signal Generation
    Validates: Requirements 5.1, 5.2, 5.3
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.strategy = RSIReversalStrategy()
        self.applicable_symbol = '510300'  # An applicable ETF
    
    @given(market_data=market_data_with_buy_conditions())
    @settings(max_examples=100, deadline=None)
    def test_buy_signal_generated_when_conditions_met(self, market_data: Dict):
        """
        Property 7: RSI Strategy Signal Generation
        
        *For any* ETF with price above 200-day MA and 2-day RSI below 10,
        the RSI strategy SHALL generate a buy signal with strength >= 4.
        
        Feature: strategy-pool, Property 7: RSI Strategy Signal Generation
        Validates: Requirements 5.1, 5.2, 5.3
        """
        # Arrange
        symbol = self.applicable_symbol
        symbols = [symbol]
        data = {symbol: market_data}
        
        # Verify preconditions
        assume(market_data['close'] > market_data['ma200'])
        assume(market_data['rsi2'] < 10)
        
        # Act
        signals = self.strategy.generate_signals(symbols, data)
        
        # Assert
        # Should generate exactly one buy signal
        self.assertEqual(len(signals), 1, 
            f"Expected 1 signal, got {len(signals)}. "
            f"close={market_data['close']}, ma200={market_data['ma200']}, rsi2={market_data['rsi2']}")
        
        signal = signals[0]
        
        # Signal should be a buy signal
        self.assertEqual(signal.signal_type, 'buy',
            f"Expected 'buy' signal, got '{signal.signal_type}'")
        
        # Signal strength should be >= 4 (as per design)
        self.assertGreaterEqual(signal.strength, 4,
            f"Expected strength >= 4, got {signal.strength}")
        
        # Signal should have correct symbol
        self.assertEqual(signal.symbol, symbol)
        
        # Signal should have stop_loss set
        self.assertIsNotNone(signal.stop_loss,
            "Buy signal should have stop_loss set")
        
        # Stop loss should be 3% below entry price
        expected_stop_loss = market_data['close'] * (1 - 0.03)
        self.assertAlmostEqual(signal.stop_loss, expected_stop_loss, places=4,
            msg=f"Stop loss should be 3% below entry. Expected {expected_stop_loss}, got {signal.stop_loss}")
    
    @given(market_data=market_data_without_buy_conditions())
    @settings(max_examples=100, deadline=None)
    def test_no_buy_signal_when_conditions_not_met(self, market_data: Dict):
        """
        Inverse property: When conditions are NOT met, no buy signal should be generated.
        
        Feature: strategy-pool, Property 7: RSI Strategy Signal Generation (inverse)
        Validates: Requirements 5.1, 5.2
        """
        # Arrange
        symbol = self.applicable_symbol
        symbols = [symbol]
        data = {symbol: market_data}
        
        # Verify at least one condition is violated
        price_below_ma = market_data['close'] <= market_data['ma200']
        rsi_not_oversold = market_data['rsi2'] >= 10
        assume(price_below_ma or rsi_not_oversold)
        
        # Act
        signals = self.strategy.generate_signals(symbols, data)
        
        # Assert - no buy signals should be generated
        buy_signals = [s for s in signals if s.signal_type == 'buy']
        self.assertEqual(len(buy_signals), 0,
            f"Expected no buy signals when conditions not met. "
            f"close={market_data['close']}, ma200={market_data['ma200']}, rsi2={market_data['rsi2']}")
    
    @given(
        rsi_value=st.floats(min_value=0.1, max_value=9.9, allow_nan=False, allow_infinity=False),
        price_ratio=st.floats(min_value=1.01, max_value=1.5, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, deadline=None)
    def test_signal_strength_based_on_rsi_level(self, rsi_value: float, price_ratio: float):
        """
        Property: Signal strength should be higher for more extreme RSI values.
        
        Feature: strategy-pool, Property 7: RSI Strategy Signal Generation
        Validates: Requirements 5.2
        """
        # Arrange
        base_price = 3.0
        ma200 = base_price / price_ratio  # Ensure price > ma200
        
        market_data = {
            'close': base_price,
            'ma200': ma200,
            'rsi2': rsi_value,
            'close_history': [base_price] * 201
        }
        
        symbol = self.applicable_symbol
        data = {symbol: market_data}
        
        # Act
        signals = self.strategy.generate_signals([symbol], data)
        
        # Assert
        self.assertEqual(len(signals), 1)
        signal = signals[0]
        
        # Verify strength is appropriate for RSI level
        if rsi_value < 5:
            self.assertEqual(signal.strength, 5,
                f"RSI < 5 should give strength 5, got {signal.strength}")
        elif rsi_value < 8:
            self.assertEqual(signal.strength, 4,
                f"RSI 5-8 should give strength 4, got {signal.strength}")
        else:
            self.assertGreaterEqual(signal.strength, 4,
                f"RSI 8-10 should give strength >= 4, got {signal.strength}")
    
    @given(symbol=st.sampled_from(['000001', '600000', '399001', 'INVALID']))
    @settings(max_examples=50, deadline=None)
    def test_non_applicable_etf_no_signal(self, symbol: str):
        """
        Property: Non-applicable ETFs should not generate signals regardless of conditions.
        
        Feature: strategy-pool, Property 7: RSI Strategy Signal Generation
        Validates: Requirements 5.4
        """
        # Arrange - create perfect buy conditions
        market_data = {
            'close': 3.0,
            'ma200': 2.5,  # price > ma200
            'rsi2': 5.0,   # RSI < 10
            'close_history': [3.0] * 201
        }
        
        data = {symbol: market_data}
        
        # Act
        signals = self.strategy.generate_signals([symbol], data)
        
        # Assert - no signals for non-applicable symbols
        self.assertEqual(len(signals), 0,
            f"Non-applicable symbol {symbol} should not generate signals")


class TestRSICalculationProperty(unittest.TestCase):
    """
    Property-Based Tests for RSI Calculation
    
    Feature: strategy-pool, Property 7: RSI Strategy Signal Generation
    Validates: Requirements 5.1
    """
    
    @given(
        prices=st.lists(
            st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
            min_size=10,
            max_size=50
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_rsi_bounded_0_to_100(self, prices: List[float]):
        """
        Property: RSI value should always be between 0 and 100.
        
        Feature: strategy-pool, Property 7: RSI Strategy Signal Generation
        Validates: Requirements 5.1
        """
        # Act
        rsi = calculate_rsi(prices, period=2)
        
        # Assert
        self.assertGreaterEqual(rsi, 0.0,
            f"RSI should be >= 0, got {rsi}")
        self.assertLessEqual(rsi, 100.0,
            f"RSI should be <= 100, got {rsi}")
    
    @given(
        base_price=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        decline_pct=st.floats(min_value=0.05, max_value=0.20, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, deadline=None)
    def test_rsi_low_on_consecutive_declines(self, base_price: float, decline_pct: float):
        """
        Property: RSI should be low (< 30) after consecutive price declines.
        
        Feature: strategy-pool, Property 7: RSI Strategy Signal Generation
        Validates: Requirements 5.1
        """
        # Arrange - create consecutive declining prices
        prices = [base_price]
        current = base_price
        for _ in range(5):
            current = current * (1 - decline_pct)
            prices.append(current)
        
        # Act
        rsi = calculate_rsi(prices, period=2)
        
        # Assert - RSI should be low after declines
        self.assertLess(rsi, 30.0,
            f"RSI should be < 30 after consecutive declines, got {rsi}")


class TestSMACalculationProperty(unittest.TestCase):
    """
    Property-Based Tests for SMA Calculation
    
    Feature: strategy-pool, Property 7: RSI Strategy Signal Generation
    Validates: Requirements 5.1
    """
    
    @given(
        prices=st.lists(
            st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
            min_size=20,
            max_size=250
        ),
        period=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=100, deadline=None)
    def test_sma_within_price_range(self, prices: List[float], period: int):
        """
        Property: SMA should be within the range of prices used in calculation.
        
        Feature: strategy-pool, Property 7: RSI Strategy Signal Generation
        Validates: Requirements 5.1
        """
        assume(len(prices) >= period)
        
        # Act
        sma = calculate_sma(prices, period)
        
        # Assert
        recent_prices = prices[-period:]
        min_price = min(recent_prices)
        max_price = max(recent_prices)
        
        self.assertGreaterEqual(sma, min_price,
            f"SMA {sma} should be >= min price {min_price}")
        self.assertLessEqual(sma, max_price,
            f"SMA {sma} should be <= max price {max_price}")


if __name__ == "__main__":
    unittest.main()
