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
            return json.dumps({
                "status": "success",
                "ticker": data.get("ticker", ""),
                "asset_type": "cn_fund",
                "latest_price": nav,
                "support_levels": [round(nav * 0.95, 4), round(nav * 0.90, 4)],
                "resistance_levels": [round(nav * 1.05, 4), round(nav * 1.10, 4)],
                "key_levels": [
                    {"price": round(nav * 0.95, 4), "type": "support", "method": "estimated"},
                    {"price": round(nav * 1.05, 4), "type": "resistance", "method": "estimated"}
                ],
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
