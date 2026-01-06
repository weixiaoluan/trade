"""
============================================
技术分析工具模块
计算各种技术指标并进行趋势分析
============================================
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime

# 使用 ta 库进行技术指标计算
try:
    import ta
    from ta.trend import MACD, SMAIndicator, EMAIndicator
    from ta.momentum import RSIIndicator, StochasticOscillator
    from ta.volatility import BollingerBands, AverageTrueRange
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False


def _calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """计算简单移动平均线"""
    return series.rolling(window=period).mean()


def _calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """计算指数移动平均线"""
    return series.ewm(span=period, adjust=False).mean()


def _calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """计算 RSI 指标"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def _calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """计算 MACD 指标"""
    ema_fast = _calculate_ema(series, fast)
    ema_slow = _calculate_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _calculate_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """计算 KDJ 指标"""
    low_list = df['Low'].rolling(window=n).min()
    high_list = df['High'].rolling(window=n).max()
    rsv = (df['Close'] - low_list) / (high_list - low_list) * 100
    
    k = rsv.ewm(com=m1-1, adjust=False).mean()
    d = k.ewm(com=m2-1, adjust=False).mean()
    j = 3 * k - 2 * d
    
    return k, d, j


def _calculate_bollinger_bands(series: pd.Series, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """计算布林带"""
    middle = _calculate_sma(series, period)
    std = series.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return upper, middle, lower


def _calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """计算 ATR (平均真实波幅)"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def _calculate_obv(df: pd.DataFrame) -> pd.Series:
    """计算 OBV (能量潮)"""
    obv = [0]
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
            obv.append(obv[-1] + df['Volume'].iloc[i])
        elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
            obv.append(obv[-1] - df['Volume'].iloc[i])
        else:
            obv.append(obv[-1])
    return pd.Series(obv, index=df.index)


def _calculate_williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """计算威廉指标 Williams %R"""
    highest_high = df['High'].rolling(window=period).max()
    lowest_low = df['Low'].rolling(window=period).min()
    wr = -100 * (highest_high - df['Close']) / (highest_high - lowest_low)
    return wr


def _calculate_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """计算 CCI (顺势指标)"""
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    sma_tp = tp.rolling(window=period).mean()
    mean_dev = tp.rolling(window=period).apply(lambda x: abs(x - x.mean()).mean())
    cci = (tp - sma_tp) / (0.015 * mean_dev)
    return cci


def _calculate_adx(df: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """计算 ADX (平均方向指数)"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    plus_dm = high.diff()
    minus_dm = low.diff().abs()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return adx, plus_di, minus_di


def _calculate_momentum(series: pd.Series, period: int = 10) -> pd.Series:
    """计算动量指标"""
    return series - series.shift(period)


def _calculate_roc(series: pd.Series, period: int = 12) -> pd.Series:
    """计算 ROC (变动率指标)"""
    return (series - series.shift(period)) / series.shift(period) * 100


# ============================================
# 新增技术指标计算函数
# ============================================

def _calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    计算 VWAP (成交量加权平均价)
    Volume Weighted Average Price - 机构常用参考价格
    """
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    vwap = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
    return vwap


def _calculate_money_flow(df: pd.DataFrame, period: int = 20) -> Dict:
    """
    计算资金流向指标
    基于价格和成交量判断主力资金净流入/流出
    """
    # 典型价格
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    
    # 资金流量 = 典型价格 × 成交量
    money_flow = typical_price * df['Volume']
    
    # 判断资金流向：当日收盘价 > 前日收盘价 为流入，否则为流出
    price_change = df['Close'].diff()
    
    # 正向资金流（流入）
    positive_flow = money_flow.where(price_change > 0, 0)
    # 负向资金流（流出）
    negative_flow = money_flow.where(price_change < 0, 0)
    
    # N日累计
    positive_sum = positive_flow.rolling(window=period).sum()
    negative_sum = negative_flow.rolling(window=period).sum().abs()
    
    # 资金流量比率
    money_flow_ratio = positive_sum / negative_sum.replace(0, np.nan)
    
    # MFI (Money Flow Index) 资金流量指数
    mfi = 100 - (100 / (1 + money_flow_ratio))
    
    # 净流入 = 流入 - 流出
    net_flow = positive_sum - negative_sum
    
    return {
        'mfi': mfi,
        'net_flow': net_flow,
        'positive_flow': positive_sum,
        'negative_flow': negative_sum
    }


def _calculate_turnover_rate(df: pd.DataFrame, total_shares: float = None) -> pd.Series:
    """
    计算换手率
    换手率 = 成交量 / 流通股本 × 100%
    如果没有流通股本数据，使用近期平均成交量作为基准估算
    """
    if total_shares and total_shares > 0:
        turnover = (df['Volume'] / total_shares) * 100
    else:
        # 使用60日平均成交量作为基准估算相对换手率
        avg_volume_60 = df['Volume'].rolling(window=60).mean()
        turnover = (df['Volume'] / avg_volume_60) * 100
    return turnover


def _calculate_chip_distribution(df: pd.DataFrame, period: int = 60) -> Dict:
    """
    计算筹码分布（简化版）
    分析近期成本分布情况
    """
    recent_df = df.tail(period)
    
    # 计算加权平均成本
    total_volume = recent_df['Volume'].sum()
    if total_volume == 0:
        return {'avg_cost': 0, 'profit_ratio': 0, 'concentration': 0}
    
    # 成交量加权平均价格作为平均成本
    avg_cost = (recent_df['Close'] * recent_df['Volume']).sum() / total_volume
    
    # 当前价格相对平均成本的位置（获利比例估算）
    current_price = df['Close'].iloc[-1]
    profit_ratio = (current_price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0
    
    # 筹码集中度：用价格标准差/均价来衡量
    price_std = recent_df['Close'].std()
    price_mean = recent_df['Close'].mean()
    concentration = (1 - price_std / price_mean) * 100 if price_mean > 0 else 0
    
    # 计算不同价格区间的成交量分布
    price_min = recent_df['Low'].min()
    price_max = recent_df['High'].max()
    price_range = price_max - price_min
    
    if price_range > 0:
        # 分成5个价格区间
        bins = 5
        bin_size = price_range / bins
        distribution = []
        for i in range(bins):
            bin_low = price_min + i * bin_size
            bin_high = price_min + (i + 1) * bin_size
            bin_volume = recent_df[(recent_df['Close'] >= bin_low) & (recent_df['Close'] < bin_high)]['Volume'].sum()
            distribution.append({
                'price_range': f"{bin_low:.2f}-{bin_high:.2f}",
                'volume_pct': round(bin_volume / total_volume * 100, 2) if total_volume > 0 else 0
            })
    else:
        distribution = []
    
    return {
        'avg_cost': avg_cost,
        'profit_ratio': profit_ratio,
        'concentration': concentration,
        'distribution': distribution
    }


def _calculate_bias(series: pd.Series, periods: List[int] = [6, 12, 24]) -> Dict:
    """
    计算 BIAS 乖离率
    乖离率 = (当前价格 - N日均线) / N日均线 × 100%
    """
    result = {}
    for period in periods:
        if len(series) >= period:
            ma = _calculate_sma(series, period)
            bias = (series - ma) / ma * 100
            result[f'bias_{period}'] = bias
    return result


def _calculate_dmi(df: pd.DataFrame, period: int = 14) -> Dict:
    """
    计算 DMI 趋向指标 (Directional Movement Index)
    包含 +DI, -DI, ADX, ADXR
    """
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    # 计算方向移动
    up_move = high.diff()
    down_move = -low.diff()
    
    # +DM 和 -DM
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)
    
    # 真实波幅 TR
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # 平滑处理
    atr = tr.ewm(span=period, adjust=False).mean()
    plus_dm_smooth = plus_dm.ewm(span=period, adjust=False).mean()
    minus_dm_smooth = minus_dm.ewm(span=period, adjust=False).mean()
    
    # +DI 和 -DI
    plus_di = 100 * plus_dm_smooth / atr
    minus_di = 100 * minus_dm_smooth / atr
    
    # DX 和 ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.ewm(span=period, adjust=False).mean()
    
    # ADXR (ADX的移动平均)
    adxr = (adx + adx.shift(period)) / 2
    
    return {
        'plus_di': plus_di,
        'minus_di': minus_di,
        'adx': adx,
        'adxr': adxr,
        'dx': dx
    }


def _calculate_sar(df: pd.DataFrame, af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.2) -> pd.Series:
    """
    计算 SAR 抛物线指标 (Parabolic SAR)
    用于判断趋势反转点和止损位
    """
    high = df['High'].values
    low = df['Low'].values
    close = df['Close'].values
    n = len(df)
    
    sar = np.zeros(n)
    ep = np.zeros(n)  # 极值点
    af = np.zeros(n)  # 加速因子
    trend = np.zeros(n)  # 1=上升趋势, -1=下降趋势
    
    # 初始化
    trend[0] = 1 if close[0] > close[min(1, n-1)] else -1
    sar[0] = low[0] if trend[0] == 1 else high[0]
    ep[0] = high[0] if trend[0] == 1 else low[0]
    af[0] = af_start
    
    for i in range(1, n):
        # 计算当前SAR
        sar[i] = sar[i-1] + af[i-1] * (ep[i-1] - sar[i-1])
        
        # 检查趋势反转
        if trend[i-1] == 1:  # 上升趋势
            # SAR不能高于前两根K线的最低价
            sar[i] = min(sar[i], low[i-1])
            if i >= 2:
                sar[i] = min(sar[i], low[i-2])
            
            if low[i] < sar[i]:  # 趋势反转
                trend[i] = -1
                sar[i] = ep[i-1]
                ep[i] = low[i]
                af[i] = af_start
            else:
                trend[i] = 1
                if high[i] > ep[i-1]:
                    ep[i] = high[i]
                    af[i] = min(af[i-1] + af_step, af_max)
                else:
                    ep[i] = ep[i-1]
                    af[i] = af[i-1]
        else:  # 下降趋势
            # SAR不能低于前两根K线的最高价
            sar[i] = max(sar[i], high[i-1])
            if i >= 2:
                sar[i] = max(sar[i], high[i-2])
            
            if high[i] > sar[i]:  # 趋势反转
                trend[i] = 1
                sar[i] = ep[i-1]
                ep[i] = high[i]
                af[i] = af_start
            else:
                trend[i] = -1
                if low[i] < ep[i-1]:
                    ep[i] = low[i]
                    af[i] = min(af[i-1] + af_step, af_max)
                else:
                    ep[i] = ep[i-1]
                    af[i] = af[i-1]
    
    return pd.Series(sar, index=df.index), pd.Series(trend, index=df.index)


def _calculate_ichimoku(df: pd.DataFrame, tenkan: int = 9, kijun: int = 26, senkou_b: int = 52) -> Dict:
    """
    计算 Ichimoku 云图 (一目均衡表)
    日本流行的综合技术指标
    
    包含:
    - 转换线 (Tenkan-sen): 9日最高最低价中值
    - 基准线 (Kijun-sen): 26日最高最低价中值
    - 先行带A (Senkou Span A): 转换线和基准线的中值，向前移动26日
    - 先行带B (Senkou Span B): 52日最高最低价中值，向前移动26日
    - 延迟线 (Chikou Span): 收盘价向后移动26日
    """
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    # 转换线 (Tenkan-sen)
    tenkan_high = high.rolling(window=tenkan).max()
    tenkan_low = low.rolling(window=tenkan).min()
    tenkan_sen = (tenkan_high + tenkan_low) / 2
    
    # 基准线 (Kijun-sen)
    kijun_high = high.rolling(window=kijun).max()
    kijun_low = low.rolling(window=kijun).min()
    kijun_sen = (kijun_high + kijun_low) / 2
    
    # 先行带A (Senkou Span A) - 向前移动26日
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)
    
    # 先行带B (Senkou Span B) - 向前移动26日
    senkou_b_high = high.rolling(window=senkou_b).max()
    senkou_b_low = low.rolling(window=senkou_b).min()
    senkou_span_b = ((senkou_b_high + senkou_b_low) / 2).shift(kijun)
    
    # 延迟线 (Chikou Span) - 向后移动26日
    chikou_span = close.shift(-kijun)
    
    return {
        'tenkan_sen': tenkan_sen,
        'kijun_sen': kijun_sen,
        'senkou_span_a': senkou_span_a,
        'senkou_span_b': senkou_span_b,
        'chikou_span': chikou_span
    }


def calculate_all_indicators(ohlcv_data: str) -> str:
    """
    计算所有技术指标
    
    Args:
        ohlcv_data: JSON 格式的 OHLCV 数据 (来自 get_stock_data)
    
    Returns:
        JSON 格式的技术指标结果
    """
    try:
        data = json.loads(ohlcv_data)
        
        if data.get("status") != "success":
            return json.dumps({
                "status": "error",
                "message": "输入数据无效"
            }, ensure_ascii=False)
        
        # 转换为 DataFrame
        ohlcv = data.get("ohlcv", [])
        if not ohlcv:
            # 如果没有 OHLCV 数据，返回错误
            return json.dumps({
                "status": "error",
                "message": "OHLCV 数据为空，无法计算技术指标"
            }, ensure_ascii=False)
        
        df = pd.DataFrame(ohlcv)
        
        # 确保列名正确
        df.columns = [c.title() if c != "Date" and c != "Datetime" else c for c in df.columns]
        if "Datetime" in df.columns:
            df["Date"] = df["Datetime"]
        
        # 转换数据类型
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        close = df["Close"]
        latest_price = float(close.iloc[-1])
        
        # ============================================
        # 计算各项技术指标
        # ============================================
        
        indicators = {
            "ticker": data.get("ticker", ""),
            "latest_price": latest_price,
            "calculation_date": datetime.now().isoformat(),
            "data_points": len(df),
        }
        
        # 1. 移动平均线系统
        ma_periods = [5, 10, 20, 50, 60, 120, 250]
        ma_values = {}
        for period in ma_periods:
            if len(df) >= period:
                ma = _calculate_sma(close, period)
                ma_values[f"MA{period}"] = round(float(ma.iloc[-1]), 2)
        
        indicators["moving_averages"] = ma_values
        
        # 判断均线排列
        ma_trend = "unknown"
        if all(k in ma_values for k in ["MA5", "MA10", "MA20"]):
            if ma_values["MA5"] > ma_values["MA10"] > ma_values["MA20"]:
                ma_trend = "bullish_alignment"  # 多头排列
            elif ma_values["MA5"] < ma_values["MA10"] < ma_values["MA20"]:
                ma_trend = "bearish_alignment"  # 空头排列
            else:
                ma_trend = "mixed"
        indicators["ma_trend"] = ma_trend
        
        # 2. MACD
        macd_line, signal_line, histogram = _calculate_macd(close)
        indicators["macd"] = {
            "macd_line": round(float(macd_line.iloc[-1]), 4),
            "signal_line": round(float(signal_line.iloc[-1]), 4),
            "histogram": round(float(histogram.iloc[-1]), 4),
            "trend": "bullish" if histogram.iloc[-1] > 0 else "bearish",
            "crossover": "golden_cross" if (histogram.iloc[-1] > 0 and histogram.iloc[-2] <= 0) else (
                "death_cross" if (histogram.iloc[-1] < 0 and histogram.iloc[-2] >= 0) else "none"
            )
        }
        
        # 3. RSI
        rsi = _calculate_rsi(close, 14)
        rsi_value = float(rsi.iloc[-1])
        indicators["rsi"] = {
            "value": round(rsi_value, 2),
            "status": "overbought" if rsi_value > 70 else ("oversold" if rsi_value < 30 else "neutral"),
            "interpretation": "超买区间,注意回调风险" if rsi_value > 70 else (
                "超卖区间,可能存在反弹机会" if rsi_value < 30 else "中性区间"
            )
        }
        
        # 4. KDJ
        k, d, j = _calculate_kdj(df)
        indicators["kdj"] = {
            "k": round(float(k.iloc[-1]), 2),
            "d": round(float(d.iloc[-1]), 2),
            "j": round(float(j.iloc[-1]), 2),
            "status": "overbought" if j.iloc[-1] > 80 else ("oversold" if j.iloc[-1] < 20 else "neutral"),
            "crossover": "golden_cross" if (k.iloc[-1] > d.iloc[-1] and k.iloc[-2] <= d.iloc[-2]) else (
                "death_cross" if (k.iloc[-1] < d.iloc[-1] and k.iloc[-2] >= d.iloc[-2]) else "none"
            )
        }
        
        # 5. 布林带
        bb_upper, bb_middle, bb_lower = _calculate_bollinger_bands(close)
        bb_position = (latest_price - float(bb_lower.iloc[-1])) / (float(bb_upper.iloc[-1]) - float(bb_lower.iloc[-1]))
        indicators["bollinger_bands"] = {
            "upper": round(float(bb_upper.iloc[-1]), 2),
            "middle": round(float(bb_middle.iloc[-1]), 2),
            "lower": round(float(bb_lower.iloc[-1]), 2),
            "bandwidth": round((float(bb_upper.iloc[-1]) - float(bb_lower.iloc[-1])) / float(bb_middle.iloc[-1]) * 100, 2),
            "position": round(bb_position * 100, 2),  # 0=下轨, 100=上轨
            "status": "near_upper" if bb_position > 0.8 else ("near_lower" if bb_position < 0.2 else "middle")
        }
        
        # 6. 成交量分析
        volume = df["Volume"]
        avg_volume_5 = float(volume.tail(5).mean())
        avg_volume_20 = float(volume.tail(20).mean())
        latest_volume = float(volume.iloc[-1])
        
        indicators["volume_analysis"] = {
            "latest_volume": int(latest_volume),
            "avg_volume_5d": int(avg_volume_5),
            "avg_volume_20d": int(avg_volume_20),
            "volume_ratio": round(latest_volume / avg_volume_20 if avg_volume_20 > 0 else 0, 2),
            "status": "high_volume" if latest_volume > avg_volume_20 * 1.5 else (
                "low_volume" if latest_volume < avg_volume_20 * 0.5 else "normal"
            )
        }
        
        # 7. 价格位置分析
        high_52w = float(df["High"].max())
        low_52w = float(df["Low"].min())
        price_position = (latest_price - low_52w) / (high_52w - low_52w) if high_52w != low_52w else 0.5
        
        indicators["price_position"] = {
            "52_week_high": round(high_52w, 2),
            "52_week_low": round(low_52w, 2),
            "position_pct": round(price_position * 100, 2),
            "distance_from_high_pct": round((high_52w - latest_price) / high_52w * 100, 2),
            "distance_from_low_pct": round((latest_price - low_52w) / low_52w * 100, 2),
        }
        
        # 8. ATR 波动率分析
        if len(df) >= 14:
            atr = _calculate_atr(df, 14)
            atr_value = float(atr.iloc[-1])
            atr_pct = atr_value / latest_price * 100
            indicators["atr"] = {
                "value": round(atr_value, 4),
                "percentage": round(atr_pct, 2),
                "volatility": "high" if atr_pct > 3 else ("low" if atr_pct < 1 else "medium"),
                "interpretation": "高波动性，注意风险控制" if atr_pct > 3 else (
                    "低波动性，适合稳健投资" if atr_pct < 1 else "中等波动性"
                )
            }
        
        # 9. Williams %R
        if len(df) >= 14:
            wr = _calculate_williams_r(df, 14)
            wr_value = float(wr.iloc[-1])
            indicators["williams_r"] = {
                "value": round(wr_value, 2),
                "status": "overbought" if wr_value > -20 else ("oversold" if wr_value < -80 else "neutral"),
                "interpretation": "超买区间，可能回调" if wr_value > -20 else (
                    "超卖区间，可能反弹" if wr_value < -80 else "中性区间"
                )
            }
        
        # 10. CCI 顺势指标
        if len(df) >= 20:
            cci = _calculate_cci(df, 20)
            cci_value = float(cci.iloc[-1])
            indicators["cci"] = {
                "value": round(cci_value, 2),
                "status": "overbought" if cci_value > 100 else ("oversold" if cci_value < -100 else "neutral"),
                "trend": "strong_bullish" if cci_value > 200 else (
                    "bullish" if cci_value > 100 else (
                        "strong_bearish" if cci_value < -200 else (
                            "bearish" if cci_value < -100 else "neutral"
                        )
                    )
                )
            }
        
        # 11. ADX 趋势强度
        if len(df) >= 28:
            adx, plus_di, minus_di = _calculate_adx(df, 14)
            adx_value = float(adx.iloc[-1]) if not np.isnan(adx.iloc[-1]) else 0
            plus_di_value = float(plus_di.iloc[-1]) if not np.isnan(plus_di.iloc[-1]) else 0
            minus_di_value = float(minus_di.iloc[-1]) if not np.isnan(minus_di.iloc[-1]) else 0
            indicators["adx"] = {
                "adx": round(adx_value, 2),
                "plus_di": round(plus_di_value, 2),
                "minus_di": round(minus_di_value, 2),
                "trend_strength": "strong" if adx_value > 25 else ("weak" if adx_value < 15 else "moderate"),
                "trend_direction": "bullish" if plus_di_value > minus_di_value else "bearish",
                "interpretation": f"趋势{'强' if adx_value > 25 else '弱'}，方向{'看多' if plus_di_value > minus_di_value else '看空'}"
            }
        
        # 12. 动量指标
        if len(df) >= 10:
            momentum = _calculate_momentum(close, 10)
            mom_value = float(momentum.iloc[-1])
            indicators["momentum"] = {
                "value": round(mom_value, 4),
                "direction": "positive" if mom_value > 0 else "negative",
                "strength": "strong" if abs(mom_value) > latest_price * 0.05 else (
                    "weak" if abs(mom_value) < latest_price * 0.01 else "moderate"
                )
            }
        
        # 13. ROC 变动率
        if len(df) >= 12:
            roc = _calculate_roc(close, 12)
            roc_value = float(roc.iloc[-1])
            indicators["roc"] = {
                "value": round(roc_value, 2),
                "trend": "bullish" if roc_value > 0 else "bearish",
                "strength": "strong" if abs(roc_value) > 10 else ("weak" if abs(roc_value) < 2 else "moderate")
            }
        
        # 14. OBV 能量潮
        if len(df) >= 5 and float(df["Volume"].sum()) > 0:
            obv = _calculate_obv(df)
            obv_value = float(obv.iloc[-1])
            obv_ma = float(obv.tail(20).mean())
            indicators["obv"] = {
                "value": int(obv_value),
                "ma20": int(obv_ma),
                "trend": "accumulation" if obv_value > obv_ma else "distribution",
                "interpretation": "资金流入，看涨" if obv_value > obv_ma else "资金流出，看跌"
            }
        
        # 15. 日线涨跌幅统计
        daily_returns = close.pct_change() * 100
        indicators["daily_change_pct"] = round(float(daily_returns.iloc[-1]), 2) if len(daily_returns) > 0 else 0
        
        # 16. 多周期涨跌幅
        indicators["period_returns"] = {}
        periods_calc = [(5, "5日"), (10, "10日"), (20, "20日"), (60, "60日"), (120, "120日"), (250, "250日")]
        for days, label in periods_calc:
            if len(df) > days:
                pct_change = (latest_price - float(close.iloc[-days-1])) / float(close.iloc[-days-1]) * 100
                indicators["period_returns"][label] = round(pct_change, 2)
        
        # ============================================
        # 新增技术指标 (17-24)
        # ============================================
        
        # 17. VWAP 成交量加权平均价
        if len(df) >= 5 and float(df["Volume"].sum()) > 0:
            try:
                vwap = _calculate_vwap(df)
                vwap_value = float(vwap.iloc[-1])
                vwap_deviation = (latest_price - vwap_value) / vwap_value * 100 if vwap_value > 0 else 0
                indicators["vwap"] = {
                    "value": round(vwap_value, 4),
                    "deviation_pct": round(vwap_deviation, 2),
                    "position": "above" if latest_price > vwap_value else "below",
                    "interpretation": "价格高于VWAP，短期偏强" if latest_price > vwap_value else "价格低于VWAP，短期偏弱",
                    "signal": "bullish" if vwap_deviation > 1 else ("bearish" if vwap_deviation < -1 else "neutral")
                }
            except Exception as e:
                indicators["vwap"] = {"error": str(e)}
        
        # 18. 资金流向分析
        if len(df) >= 20 and float(df["Volume"].sum()) > 0:
            try:
                money_flow = _calculate_money_flow(df, 20)
                mfi_value = float(money_flow['mfi'].iloc[-1]) if not np.isnan(money_flow['mfi'].iloc[-1]) else 50
                net_flow_value = float(money_flow['net_flow'].iloc[-1]) if not np.isnan(money_flow['net_flow'].iloc[-1]) else 0
                
                # 判断资金流向状态
                if mfi_value > 80:
                    mfi_status = "overbought"
                    mfi_interpretation = "资金过热，注意回调风险"
                elif mfi_value < 20:
                    mfi_status = "oversold"
                    mfi_interpretation = "资金超卖，可能存在反弹机会"
                elif mfi_value > 50:
                    mfi_status = "inflow"
                    mfi_interpretation = "资金净流入，看涨"
                else:
                    mfi_status = "outflow"
                    mfi_interpretation = "资金净流出，看跌"
                
                indicators["money_flow"] = {
                    "mfi": round(mfi_value, 2),
                    "mfi_status": mfi_status,
                    "net_flow": round(net_flow_value, 0),
                    "net_flow_direction": "inflow" if net_flow_value > 0 else "outflow",
                    "interpretation": mfi_interpretation,
                    "signal": "bullish" if mfi_value > 50 and mfi_value < 80 else (
                        "bearish" if mfi_value < 50 and mfi_value > 20 else "neutral"
                    )
                }
            except Exception as e:
                indicators["money_flow"] = {"error": str(e)}
        
        # 19. 换手率分析
        if len(df) >= 5 and float(df["Volume"].sum()) > 0:
            try:
                turnover = _calculate_turnover_rate(df)
                turnover_value = float(turnover.iloc[-1]) if not np.isnan(turnover.iloc[-1]) else 100
                turnover_avg_5 = float(turnover.tail(5).mean()) if len(turnover) >= 5 else turnover_value
                turnover_avg_20 = float(turnover.tail(20).mean()) if len(turnover) >= 20 else turnover_value
                
                # 判断换手率状态
                if turnover_value > turnover_avg_20 * 2:
                    turnover_status = "very_high"
                    turnover_interpretation = "换手率异常放大，关注主力动向"
                elif turnover_value > turnover_avg_20 * 1.5:
                    turnover_status = "high"
                    turnover_interpretation = "换手率较高，交易活跃"
                elif turnover_value < turnover_avg_20 * 0.5:
                    turnover_status = "low"
                    turnover_interpretation = "换手率较低，交易清淡"
                else:
                    turnover_status = "normal"
                    turnover_interpretation = "换手率正常"
                
                indicators["turnover_rate"] = {
                    "value": round(turnover_value, 2),
                    "avg_5d": round(turnover_avg_5, 2),
                    "avg_20d": round(turnover_avg_20, 2),
                    "ratio": round(turnover_value / turnover_avg_20 if turnover_avg_20 > 0 else 1, 2),
                    "status": turnover_status,
                    "interpretation": turnover_interpretation
                }
            except Exception as e:
                indicators["turnover_rate"] = {"error": str(e)}
        
        # 20. 筹码分布分析
        if len(df) >= 60:
            try:
                chip_dist = _calculate_chip_distribution(df, 60)
                avg_cost = chip_dist['avg_cost']
                profit_ratio = chip_dist['profit_ratio']
                concentration = chip_dist['concentration']
                
                # 判断筹码状态
                if profit_ratio > 20:
                    chip_status = "high_profit"
                    chip_interpretation = "获利盘较多，注意抛压"
                elif profit_ratio < -10:
                    chip_status = "trapped"
                    chip_interpretation = "套牢盘较多，上方压力大"
                elif concentration > 70:
                    chip_status = "concentrated"
                    chip_interpretation = "筹码集中，可能有主力控盘"
                else:
                    chip_status = "normal"
                    chip_interpretation = "筹码分布正常"
                
                indicators["chip_distribution"] = {
                    "avg_cost": round(avg_cost, 4),
                    "profit_ratio_pct": round(profit_ratio, 2),
                    "concentration": round(concentration, 2),
                    "status": chip_status,
                    "interpretation": chip_interpretation,
                    "distribution": chip_dist.get('distribution', [])
                }
            except Exception as e:
                indicators["chip_distribution"] = {"error": str(e)}
        
        # 21. BIAS 乖离率
        if len(df) >= 24:
            try:
                bias_data = _calculate_bias(close, [6, 12, 24])
                bias_6 = float(bias_data['bias_6'].iloc[-1]) if 'bias_6' in bias_data else 0
                bias_12 = float(bias_data['bias_12'].iloc[-1]) if 'bias_12' in bias_data else 0
                bias_24 = float(bias_data['bias_24'].iloc[-1]) if 'bias_24' in bias_data else 0
                
                # 判断乖离率状态（以BIAS6为主）
                if bias_6 > 5:
                    bias_status = "overbought"
                    bias_interpretation = "短期乖离过大，注意回调风险"
                elif bias_6 < -5:
                    bias_status = "oversold"
                    bias_interpretation = "短期乖离过大，可能存在反弹机会"
                elif bias_6 > 2:
                    bias_status = "bullish"
                    bias_interpretation = "价格偏离均线向上，短期偏强"
                elif bias_6 < -2:
                    bias_status = "bearish"
                    bias_interpretation = "价格偏离均线向下，短期偏弱"
                else:
                    bias_status = "neutral"
                    bias_interpretation = "价格接近均线，走势中性"
                
                indicators["bias"] = {
                    "bias_6": round(bias_6, 2),
                    "bias_12": round(bias_12, 2),
                    "bias_24": round(bias_24, 2),
                    "status": bias_status,
                    "interpretation": bias_interpretation,
                    "signal": "sell" if bias_6 > 5 else ("buy" if bias_6 < -5 else "hold")
                }
            except Exception as e:
                indicators["bias"] = {"error": str(e)}
        
        # 22. DMI 趋向指标
        if len(df) >= 28:
            try:
                dmi_data = _calculate_dmi(df, 14)
                plus_di = float(dmi_data['plus_di'].iloc[-1]) if not np.isnan(dmi_data['plus_di'].iloc[-1]) else 0
                minus_di = float(dmi_data['minus_di'].iloc[-1]) if not np.isnan(dmi_data['minus_di'].iloc[-1]) else 0
                adx_dmi = float(dmi_data['adx'].iloc[-1]) if not np.isnan(dmi_data['adx'].iloc[-1]) else 0
                adxr = float(dmi_data['adxr'].iloc[-1]) if not np.isnan(dmi_data['adxr'].iloc[-1]) else 0
                
                # 判断DMI状态
                if adx_dmi > 25:
                    if plus_di > minus_di:
                        dmi_status = "strong_bullish"
                        dmi_interpretation = "强势上涨趋势"
                    else:
                        dmi_status = "strong_bearish"
                        dmi_interpretation = "强势下跌趋势"
                elif adx_dmi < 15:
                    dmi_status = "ranging"
                    dmi_interpretation = "趋势不明，震荡整理"
                else:
                    if plus_di > minus_di:
                        dmi_status = "bullish"
                        dmi_interpretation = "偏多趋势"
                    else:
                        dmi_status = "bearish"
                        dmi_interpretation = "偏空趋势"
                
                indicators["dmi"] = {
                    "plus_di": round(plus_di, 2),
                    "minus_di": round(minus_di, 2),
                    "adx": round(adx_dmi, 2),
                    "adxr": round(adxr, 2),
                    "di_diff": round(plus_di - minus_di, 2),
                    "status": dmi_status,
                    "interpretation": dmi_interpretation,
                    "trend_strength": "strong" if adx_dmi > 25 else ("weak" if adx_dmi < 15 else "moderate")
                }
            except Exception as e:
                indicators["dmi"] = {"error": str(e)}
        
        # 23. SAR 抛物线指标
        if len(df) >= 10:
            try:
                sar_values, sar_trend = _calculate_sar(df)
                sar_value = float(sar_values.iloc[-1])
                current_trend = int(sar_trend.iloc[-1])
                prev_trend = int(sar_trend.iloc[-2]) if len(sar_trend) > 1 else current_trend
                
                # 判断SAR状态
                if current_trend == 1:
                    sar_status = "bullish"
                    sar_interpretation = f"上升趋势，止损参考位: {sar_value:.4f}"
                else:
                    sar_status = "bearish"
                    sar_interpretation = f"下降趋势，止损参考位: {sar_value:.4f}"
                
                # 检测趋势反转
                trend_reversal = "none"
                if current_trend != prev_trend:
                    trend_reversal = "bullish_reversal" if current_trend == 1 else "bearish_reversal"
                
                indicators["sar"] = {
                    "value": round(sar_value, 4),
                    "trend": "up" if current_trend == 1 else "down",
                    "status": sar_status,
                    "reversal": trend_reversal,
                    "stop_loss": round(sar_value, 4),
                    "interpretation": sar_interpretation,
                    "signal": "buy" if trend_reversal == "bullish_reversal" else (
                        "sell" if trend_reversal == "bearish_reversal" else "hold"
                    )
                }
            except Exception as e:
                indicators["sar"] = {"error": str(e)}
        
        # 24. Ichimoku 云图
        if len(df) >= 52:
            try:
                ichimoku = _calculate_ichimoku(df)
                tenkan = float(ichimoku['tenkan_sen'].iloc[-1]) if not np.isnan(ichimoku['tenkan_sen'].iloc[-1]) else 0
                kijun = float(ichimoku['kijun_sen'].iloc[-1]) if not np.isnan(ichimoku['kijun_sen'].iloc[-1]) else 0
                senkou_a = float(ichimoku['senkou_span_a'].iloc[-1]) if not np.isnan(ichimoku['senkou_span_a'].iloc[-1]) else 0
                senkou_b = float(ichimoku['senkou_span_b'].iloc[-1]) if not np.isnan(ichimoku['senkou_span_b'].iloc[-1]) else 0
                
                # 云层上下边界
                cloud_top = max(senkou_a, senkou_b)
                cloud_bottom = min(senkou_a, senkou_b)
                cloud_color = "green" if senkou_a > senkou_b else "red"
                
                # 判断价格与云层的关系
                if latest_price > cloud_top:
                    cloud_position = "above_cloud"
                    cloud_interpretation = "价格在云层上方，强势"
                elif latest_price < cloud_bottom:
                    cloud_position = "below_cloud"
                    cloud_interpretation = "价格在云层下方，弱势"
                else:
                    cloud_position = "in_cloud"
                    cloud_interpretation = "价格在云层中，方向不明"
                
                # 转换线与基准线交叉
                tk_cross = "golden_cross" if tenkan > kijun else "death_cross"
                
                # 综合判断
                if latest_price > cloud_top and tenkan > kijun and cloud_color == "green":
                    ichimoku_status = "strong_bullish"
                    ichimoku_signal = "buy"
                elif latest_price < cloud_bottom and tenkan < kijun and cloud_color == "red":
                    ichimoku_status = "strong_bearish"
                    ichimoku_signal = "sell"
                elif latest_price > cloud_top:
                    ichimoku_status = "bullish"
                    ichimoku_signal = "hold"
                elif latest_price < cloud_bottom:
                    ichimoku_status = "bearish"
                    ichimoku_signal = "hold"
                else:
                    ichimoku_status = "neutral"
                    ichimoku_signal = "wait"
                
                indicators["ichimoku"] = {
                    "tenkan_sen": round(tenkan, 4),
                    "kijun_sen": round(kijun, 4),
                    "senkou_span_a": round(senkou_a, 4),
                    "senkou_span_b": round(senkou_b, 4),
                    "cloud_top": round(cloud_top, 4),
                    "cloud_bottom": round(cloud_bottom, 4),
                    "cloud_color": cloud_color,
                    "cloud_position": cloud_position,
                    "tk_cross": tk_cross,
                    "status": ichimoku_status,
                    "interpretation": cloud_interpretation,
                    "signal": ichimoku_signal
                }
            except Exception as e:
                indicators["ichimoku"] = {"error": str(e)}
        
        return json.dumps({
            "status": "success",
            "indicators": indicators
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False)


def analyze_trend(indicators_json: str) -> str:
    """
    基于技术指标进行趋势分析
    
    Args:
        indicators_json: calculate_all_indicators 的输出
    
    Returns:
        JSON 格式的趋势分析结果
    """
    try:
        data = json.loads(indicators_json)
        
        if data.get("status") != "success":
            return json.dumps({
                "status": "error",
                "message": "指标数据无效"
            }, ensure_ascii=False)
        
        # 如果是基金类型，返回简化的趋势分析
        if data.get("asset_type") == "cn_fund" or data.get("ma_trend") == "not_applicable":
            daily_change = data.get("indicators", {}).get("daily_change_pct", 0)
            trend = "bullish" if daily_change > 0 else "bearish" if daily_change < 0 else "neutral"
            return json.dumps({
                "status": "success",
                "trend_analysis": {
                    "overall_trend": trend,
                    "trend_strength": "moderate",
                    "bullish_signals": 1 if daily_change > 0 else 0,
                    "bearish_signals": 1 if daily_change < 0 else 0,
                    "signal_details": [f"当日净值变动: {daily_change:.2f}%"],
                    "recommendation": "观望" if abs(daily_change) < 1 else ("关注" if daily_change > 0 else "谨慎"),
                    "confidence": 0.5,
                    "asset_type": "cn_fund",
                    "message": "场外基金趋势分析基于净值变动"
                }
            }, ensure_ascii=False)
        
        ind = data.get("indicators", data)
        
        # ============================================
        # 市场状态判定 (Market Regime)
        # ============================================
        
        adx_data = ind.get("adx", {})
        bb_data = ind.get("bollinger_bands", {})
        atr_data = ind.get("atr", {})
        
        market_regime = "unknown"
        regime_confidence = "low"
        
        # 判断趋势 vs 震荡
        if adx_data.get("trend_strength") == "strong":
            market_regime = "trending"
            regime_confidence = "high"
        elif adx_data.get("trend_strength") == "weak":
            if bb_data.get("bandwidth", 20) < 10:  # 带宽收窄，往往预示突破
                market_regime = "squeeze"
            else:
                market_regime = "ranging"
            regime_confidence = "medium"
        
        # 结合波动率
        volatility_state = atr_data.get("volatility", "medium")
        
        # ============================================
        # 综合评分系统 (Quantitative Score 0-100)
        # ============================================
        
        bullish_signals = 0
        bearish_signals = 0
        neutral_signals = 0
        signal_details = []
        
        score = 50  # 初始 50 分
        
        # 1. 趋势类指标权重 (在趋势市场中权重更大)
        trend_weight = 1.5 if market_regime == "trending" else 1.0
        osc_weight = 0.8 if market_regime == "trending" else 1.2
        
        # MACD (趋势)
        macd = ind.get("macd", {})
        if macd.get("trend") == "bullish":
            bullish_signals += 1
            score += 5 * trend_weight
            signal_details.append("MACD 柱状图为正 (多头)")
        else:
            bearish_signals += 1
            score -= 5 * trend_weight
            signal_details.append("MACD 柱状图为负 (空头)")
            
        if macd.get("crossover") == "golden_cross":
            score += 10 * trend_weight
            signal_details.append("MACD 金叉 (+10)")
        elif macd.get("crossover") == "death_cross":
            score -= 10 * trend_weight
            signal_details.append("MACD 死叉 (-10)")
        
        # 均线系统 (趋势)
        ma_trend = ind.get("ma_trend", "")
        if ma_trend == "bullish_alignment":
            bullish_signals += 1
            score += 10 * trend_weight
            signal_details.append("均线多头排列 (+10)")
        elif ma_trend == "bearish_alignment":
            bearish_signals += 1
            score -= 10 * trend_weight
            signal_details.append("均线空头排列 (-10)")
        
        # ADX (趋势确认)
        if market_regime == "trending":
            if adx_data.get("trend_direction") == "bullish":
                score += 5
            elif adx_data.get("trend_direction") == "bearish":
                score -= 5
        
        # RSI (震荡)
        rsi = ind.get("rsi", {})
        rsi_val = rsi.get("value", 50)
        if rsi.get("status") == "overbought":
            if market_regime == "ranging":
                score -= 10 * osc_weight
                bearish_signals += 1
                signal_details.append("RSI 超买 (震荡市看空)")
            else:
                # 趋势市中超买不一定是卖点，可能是强势
                score += 2
                signal_details.append("RSI 进入强势区")
        elif rsi.get("status") == "oversold":
            if market_regime == "ranging":
                score += 10 * osc_weight
                bullish_signals += 1
                signal_details.append("RSI 超卖 (震荡市看多)")
            else:
                score -= 2
                signal_details.append("RSI 进入弱势区")
        
        # KDJ (震荡)
        kdj = ind.get("kdj", {})
        if kdj.get("crossover") == "golden_cross":
            score += 5 * osc_weight
            bullish_signals += 1
            signal_details.append("KDJ 金叉")
        elif kdj.get("crossover") == "death_cross":
            score -= 5 * osc_weight
            bearish_signals += 1
            signal_details.append("KDJ 死叉")
        
        # 布林带 (均值回归 vs 突破)
        bb = ind.get("bollinger_bands", {})
        bb_pos = bb.get("position", 50)
        if bb.get("status") == "near_upper":
            if market_regime == "trending" and adx_data.get("trend_direction") == "bullish":
                 score += 5  # 顺势突破
                 signal_details.append("股价沿布林带上轨运行 (强势)")
            else:
                 score -= 5  # 受阻回落
                 bearish_signals += 1
                 signal_details.append("触及布林带上轨 (压力)")
        elif bb.get("status") == "near_lower":
            if market_regime == "trending" and adx_data.get("trend_direction") == "bearish":
                score -= 5
                signal_details.append("股价沿布林带下轨运行 (弱势)")
            else:
                score += 5
                bullish_signals += 1
                signal_details.append("触及布林带下轨 (支撑)")

        # 成交量确认
        vol = ind.get("volume_analysis", {})
        if vol.get("status") == "high_volume":
            # 放量
            if score > 50:  # 上涨放量
                score += 5
                signal_details.append("放量确认上涨")
            else:  # 下跌放量
                score -= 5
                signal_details.append("放量确认下跌")
        
        # ============================================
        # 新增指标评分 (VWAP, 资金流向, 换手率, 筹码, BIAS, DMI, SAR, Ichimoku)
        # ============================================
        
        # VWAP 成交量加权平均价
        vwap = ind.get("vwap", {})
        if vwap and "error" not in vwap:
            if vwap.get("signal") == "bullish":
                score += 3
                bullish_signals += 1
                signal_details.append("价格高于VWAP (偏强)")
            elif vwap.get("signal") == "bearish":
                score -= 3
                bearish_signals += 1
                signal_details.append("价格低于VWAP (偏弱)")
        
        # 资金流向 MFI
        money_flow = ind.get("money_flow", {})
        if money_flow and "error" not in money_flow:
            mfi_status = money_flow.get("mfi_status", "")
            if mfi_status == "inflow":
                score += 5
                bullish_signals += 1
                signal_details.append("资金净流入 (MFI看多)")
            elif mfi_status == "outflow":
                score -= 5
                bearish_signals += 1
                signal_details.append("资金净流出 (MFI看空)")
            elif mfi_status == "overbought":
                score -= 3
                signal_details.append("MFI超买，注意回调")
            elif mfi_status == "oversold":
                score += 3
                signal_details.append("MFI超卖，可能反弹")
        
        # 换手率
        turnover = ind.get("turnover_rate", {})
        if turnover and "error" not in turnover:
            turnover_status = turnover.get("status", "")
            if turnover_status == "very_high":
                # 异常放量，结合趋势判断
                if score > 50:
                    score += 3
                    signal_details.append("换手率异常放大，关注主力动向")
                else:
                    score -= 3
                    signal_details.append("换手率异常放大，可能出货")
            elif turnover_status == "low":
                neutral_signals += 1
                signal_details.append("换手率较低，交易清淡")
        
        # 筹码分布
        chip = ind.get("chip_distribution", {})
        if chip and "error" not in chip:
            chip_status = chip.get("status", "")
            if chip_status == "high_profit":
                score -= 3
                bearish_signals += 1
                signal_details.append("获利盘较多，注意抛压")
            elif chip_status == "trapped":
                score -= 2
                signal_details.append("套牢盘较多，上方压力大")
            elif chip_status == "concentrated":
                score += 2
                signal_details.append("筹码集中，可能有主力控盘")
        
        # BIAS 乖离率
        bias = ind.get("bias", {})
        if bias and "error" not in bias:
            bias_signal = bias.get("signal", "")
            if bias_signal == "buy":
                score += 5 * osc_weight
                bullish_signals += 1
                signal_details.append("BIAS超卖，反弹机会")
            elif bias_signal == "sell":
                score -= 5 * osc_weight
                bearish_signals += 1
                signal_details.append("BIAS超买，回调风险")
        
        # DMI 趋向指标
        dmi = ind.get("dmi", {})
        if dmi and "error" not in dmi:
            dmi_status = dmi.get("status", "")
            if dmi_status == "strong_bullish":
                score += 8 * trend_weight
                bullish_signals += 1
                signal_details.append("DMI强势上涨趋势")
            elif dmi_status == "strong_bearish":
                score -= 8 * trend_weight
                bearish_signals += 1
                signal_details.append("DMI强势下跌趋势")
            elif dmi_status == "bullish":
                score += 3
                signal_details.append("DMI偏多趋势")
            elif dmi_status == "bearish":
                score -= 3
                signal_details.append("DMI偏空趋势")
            elif dmi_status == "ranging":
                neutral_signals += 1
                signal_details.append("DMI显示震荡整理")
        
        # SAR 抛物线
        sar = ind.get("sar", {})
        if sar and "error" not in sar:
            sar_signal = sar.get("signal", "")
            sar_status = sar.get("status", "")
            if sar_signal == "buy":
                score += 8
                bullish_signals += 1
                signal_details.append("SAR发出买入信号（趋势反转向上）")
            elif sar_signal == "sell":
                score -= 8
                bearish_signals += 1
                signal_details.append("SAR发出卖出信号（趋势反转向下）")
            elif sar_status == "bullish":
                score += 2
                signal_details.append("SAR显示上升趋势")
            elif sar_status == "bearish":
                score -= 2
                signal_details.append("SAR显示下降趋势")
        
        # Ichimoku 云图
        ichimoku = ind.get("ichimoku", {})
        if ichimoku and "error" not in ichimoku:
            ichimoku_status = ichimoku.get("status", "")
            ichimoku_signal = ichimoku.get("signal", "")
            if ichimoku_status == "strong_bullish":
                score += 10 * trend_weight
                bullish_signals += 1
                signal_details.append("云图强势看多（价格在云上+转换线>基准线+绿云）")
            elif ichimoku_status == "strong_bearish":
                score -= 10 * trend_weight
                bearish_signals += 1
                signal_details.append("云图强势看空（价格在云下+转换线<基准线+红云）")
            elif ichimoku_status == "bullish":
                score += 5
                bullish_signals += 1
                signal_details.append("云图偏多（价格在云层上方）")
            elif ichimoku_status == "bearish":
                score -= 5
                bearish_signals += 1
                signal_details.append("云图偏空（价格在云层下方）")
            elif ichimoku_status == "neutral":
                neutral_signals += 1
                signal_details.append("云图中性（价格在云层中）")
        
        # 限制分数范围
        score = max(0, min(100, score))

        # 统计信号比例
        total_signals = bullish_signals + bearish_signals + neutral_signals
        if total_signals > 0:
            bullish_ratio = bullish_signals / total_signals
            bearish_ratio = bearish_signals / total_signals
        else:
            bullish_ratio = 0.5
            bearish_ratio = 0.5

        # 趋势中文描述
        if score >= 60:
            trend_cn = "偏多（上涨概率相对占优）"
        elif score <= 40:
            trend_cn = "偏空（下跌压力相对更大）"
        else:
            trend_cn = "中性（多空力量大致均衡）"

        # 数值置信度（0-1），基于市场状态置信度
        if regime_confidence == "high":
            confidence = 0.8
        elif regime_confidence == "medium":
            confidence = 0.6
        else:
            confidence = 0.4

        # 生成建议
        recommendation = "hold"
        if score >= 80:
            recommendation = "strong_buy"
        elif score >= 60:
            recommendation = "buy"
        elif score <= 20:
            recommendation = "strong_sell"
        elif score <= 40:
            recommendation = "sell"

        recommendation_cn_map = {
            "strong_buy": "强力买入",
            "buy": "买入",
            "hold": "持有",
            "sell": "减持",
            "strong_sell": "卖出",
        }
        recommendation_cn = recommendation_cn_map.get(recommendation, "持有")

        trend_direction = "bullish" if score > 50 else "bearish"
        trend_strength = adx_data.get("trend_strength", "moderate")

        return json.dumps({
            "status": "success",
            "ticker": ind.get("ticker", ""),
            "quant_analysis": {
                "score": round(score, 1),
                "recommendation": recommendation,
                "market_regime": market_regime,
                "volatility_state": volatility_state,
                "confidence": regime_confidence
            },
            "trend_analysis": {
                "overall_trend": trend_direction,
                "trend": trend_direction,
                "trend_cn": trend_cn,
                "confidence": confidence,
                "bullish_signals": bullish_signals,
                "bearish_signals": bearish_signals,
                "neutral_signals": neutral_signals,
                "bullish_ratio": round(bullish_ratio * 100, 1),
                "bearish_ratio": round(bearish_ratio * 100, 1),
                "trend_strength": trend_strength,
                "recommendation": recommendation_cn,
            },
            "signal_details": signal_details,
            "indicators_summary": {
                "macd": macd,
                "rsi": rsi,
                "kdj": kdj,
                "bollinger_bands": bb,
                "ma_trend": ma_trend,
                "vwap": ind.get("vwap", {}),
                "money_flow": ind.get("money_flow", {}),
                "turnover_rate": ind.get("turnover_rate", {}),
                "chip_distribution": ind.get("chip_distribution", {}),
                "bias": ind.get("bias", {}),
                "dmi": ind.get("dmi", {}),
                "sar": ind.get("sar", {}),
                "ichimoku": ind.get("ichimoku", {}),
            },
            "analysis_timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False)


def get_support_resistance_levels(ohlcv_data: str) -> str:
    """
    计算支撑位和阻力位
    
    Args:
        ohlcv_data: JSON 格式的 OHLCV 数据
    
    Returns:
        JSON 格式的支撑阻力位
    """
    try:
        data = json.loads(ohlcv_data)
        
        if data.get("status") != "success":
            return json.dumps({
                "status": "error",
                "message": "输入数据无效"
            }, ensure_ascii=False)
        
        ohlcv = data.get("ohlcv", [])
        
        # 如果是基金类型或没有 OHLCV 数据，返回简化结果
        if not ohlcv or data.get("asset_type") == "cn_fund":
            summary = data.get("summary", {})
            nav = summary.get("latest_price", 1.0)
            # 如果summary中没有，尝试从ohlcv获取
            if nav == 1.0 and ohlcv:
                nav = float(ohlcv[-1].get('Close', 1.0))
            
            support_price = round(nav * 0.95, 4)
            resistance_price = round(nav * 1.05, 4)
            
            return json.dumps({
                "status": "success",
                "ticker": data.get("ticker", ""),
                "asset_type": "cn_fund",
                "latest_price": nav,
                "support_levels": [
                    {"price": support_price, "type": "support", "method": "estimated_5pct"},
                    {"price": round(nav * 0.90, 4), "type": "support", "method": "estimated_10pct"}
                ],
                "resistance_levels": [
                    {"price": resistance_price, "type": "resistance", "method": "estimated_5pct"},
                    {"price": round(nav * 1.10, 4), "type": "resistance", "method": "estimated_10pct"}
                ],
                "key_levels": {
                    "nearest_support": support_price,
                    "nearest_resistance": resistance_price
                },
                "message": "场外基金支撑阻力位基于净值估算"
            }, ensure_ascii=False)
        
        df = pd.DataFrame(ohlcv)
        
        for col in ["Open", "High", "Low", "Close"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        latest_price = float(df["Close"].iloc[-1])
        
        # 使用多种方法计算支撑阻力
        levels = []
        
        # 1. 历史高低点
        highs = df["High"].nlargest(5).tolist()
        lows = df["Low"].nsmallest(5).tolist()
        
        for h in highs:
            levels.append({"price": float(h), "type": "resistance", "method": "historical_high"})
        for l in lows:
            levels.append({"price": float(l), "type": "support", "method": "historical_low"})
        
        # 2. 移动平均线作为动态支撑阻力
        for period in [20, 50, 200]:
            if len(df) >= period:
                ma = float(df["Close"].tail(period).mean())
                level_type = "support" if ma < latest_price else "resistance"
                levels.append({"price": round(ma, 2), "type": level_type, "method": f"MA{period}"})
        
        # 3. 布林带
        close = df["Close"]
        bb_upper, bb_middle, bb_lower = _calculate_bollinger_bands(close)
        levels.append({"price": round(float(bb_upper.iloc[-1]), 2), "type": "resistance", "method": "bollinger_upper"})
        levels.append({"price": round(float(bb_lower.iloc[-1]), 2), "type": "support", "method": "bollinger_lower"})
        
        # 过滤并排序
        support_levels = sorted([l for l in levels if l["type"] == "support" and l["price"] < latest_price], 
                               key=lambda x: x["price"], reverse=True)[:5]
        resistance_levels = sorted([l for l in levels if l["type"] == "resistance" and l["price"] > latest_price],
                                  key=lambda x: x["price"])[:5]
        
        return json.dumps({
            "status": "success",
            "ticker": data.get("ticker", ""),
            "latest_price": latest_price,
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
            "key_levels": {
                "nearest_support": support_levels[0]["price"] if support_levels else None,
                "nearest_resistance": resistance_levels[0]["price"] if resistance_levels else None,
            },
            "calculation_timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }, ensure_ascii=False)
