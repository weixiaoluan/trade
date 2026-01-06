"""
============================================
量化执行官 Agent (参考 vnpy StrategyTemplate)
Quant Agent (Based on vnpy StrategyTemplate)
============================================
"""

import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from .array_manager import QuantArrayManager
from .event_engine import QuantEventEngine, Event, EVENT_SIGNAL, EVENT_ANALYSIS


class QuantAgent:
    """
    量化执行官 Agent
    
    职责：
    - 处理 OHLCV 数据
    - 利用 ArrayManager 计算技术指标
    - 基于硬数据生成多空信号和仓位建议
    
    参考 vnpy.app.cta_strategy.StrategyTemplate
    """
    
    def __init__(self, event_engine: QuantEventEngine, size: int = 250):
        self.event_engine = event_engine
        self.am = QuantArrayManager(size=size)
        self.inited = False
        self.trading = False
        
        # 信号和状态
        self.pos = 0  # 仓位：1多头，0空仓，-1空头
        self.signal_score = 50.0  # 量化评分 0-100
        self.signals = []  # 信号列表
        
        # 注册事件处理
        self.event_engine.register("eBar", self.on_bar)
        
    def on_bar(self, event: Event):
        """K线回调（类似 vnpy 的 on_bar）"""
        bar_data = event.data
        self.am.update_bar(bar_data)
        
        if not self.am.inited:
            return
        
        if not self.inited:
            self.inited = True
            self.on_init()
        
        if not self.trading:
            self.trading = True
            self.on_start()
        
        # 执行策略逻辑
        self.calculate_signals()
        
    def on_init(self):
        """初始化完成回调"""
        print(f"[QuantAgent] 初始化完成，数据量: {self.am.count}")
        
    def on_start(self):
        """启动策略回调"""
        print(f"[QuantAgent] 策略启动")
        
    def calculate_signals(self) -> Dict:
        """
        计算量化信号（核心策略逻辑）
        
        Returns:
            信号字典，包含评分和仓位建议
        """
        signals = []
        bullish_count = 0
        bearish_count = 0
        
        # 1. 均线系统信号
        ma_signal = self._check_ma_system()
        signals.extend(ma_signal['signals'])
        bullish_count += ma_signal['bullish']
        bearish_count += ma_signal['bearish']
        
        # 2. MACD 信号
        macd_signal = self._check_macd()
        signals.extend(macd_signal['signals'])
        bullish_count += macd_signal['bullish']
        bearish_count += macd_signal['bearish']
        
        # 3. RSI 信号
        rsi_signal = self._check_rsi()
        signals.extend(rsi_signal['signals'])
        bullish_count += rsi_signal['bullish']
        bearish_count += rsi_signal['bearish']
        
        # 4. KDJ 信号
        kdj_signal = self._check_kdj()
        signals.extend(kdj_signal['signals'])
        bullish_count += kdj_signal['bullish']
        bearish_count += kdj_signal['bearish']
        
        # 5. 布林带信号
        bb_signal = self._check_bollinger()
        signals.extend(bb_signal['signals'])
        bullish_count += bb_signal['bullish']
        bearish_count += bb_signal['bearish']
        
        # 6. ATR 波动率
        atr_signal = self._check_atr()
        signals.extend(atr_signal['signals'])
        
        # ============================================
        # 新增指标信号检查 (7-14)
        # ============================================
        
        # 7. VWAP 成交量加权平均价
        vwap_signal = self._check_vwap()
        signals.extend(vwap_signal['signals'])
        bullish_count += vwap_signal['bullish']
        bearish_count += vwap_signal['bearish']
        
        # 8. MFI 资金流量指数
        mfi_signal = self._check_mfi()
        signals.extend(mfi_signal['signals'])
        bullish_count += mfi_signal['bullish']
        bearish_count += mfi_signal['bearish']
        
        # 9. 换手率
        turnover_signal = self._check_turnover()
        signals.extend(turnover_signal['signals'])
        bullish_count += turnover_signal['bullish']
        bearish_count += turnover_signal['bearish']
        
        # 10. BIAS 乖离率
        bias_signal = self._check_bias()
        signals.extend(bias_signal['signals'])
        bullish_count += bias_signal['bullish']
        bearish_count += bias_signal['bearish']
        
        # 11. DMI 趋向指标
        dmi_signal = self._check_dmi()
        signals.extend(dmi_signal['signals'])
        bullish_count += dmi_signal['bullish']
        bearish_count += dmi_signal['bearish']
        
        # 12. SAR 抛物线
        sar_signal = self._check_sar()
        signals.extend(sar_signal['signals'])
        bullish_count += sar_signal['bullish']
        bearish_count += sar_signal['bearish']
        
        # 13. Ichimoku 云图
        ichimoku_signal = self._check_ichimoku()
        signals.extend(ichimoku_signal['signals'])
        bullish_count += ichimoku_signal['bullish']
        bearish_count += ichimoku_signal['bearish']
        
        # 计算综合评分 (0-100)
        total_signals = bullish_count + bearish_count
        if total_signals > 0:
            bullish_ratio = bullish_count / total_signals
            self.signal_score = bullish_ratio * 100
        else:
            self.signal_score = 50.0
        
        # 确定仓位
        if self.signal_score >= 70:
            self.pos = 1  # 多头
        elif self.signal_score <= 30:
            self.pos = -1  # 空头
        else:
            self.pos = 0  # 空仓
        
        # 保存信号
        self.signals = signals
        
        # 发送信号事件
        result = {
            "score": round(self.signal_score, 1),
            "pos": self.pos,
            "bullish_signals": bullish_count,
            "bearish_signals": bearish_count,
            "signals": signals,
            "timestamp": datetime.now().isoformat()
        }
        
        self.event_engine.emit(EVENT_SIGNAL, result)
        
        return result
    
    def _check_ma_system(self) -> Dict:
        """检查均线系统"""
        signals = []
        bullish = 0
        bearish = 0
        
        try:
            ma5 = self.am.sma(5)
            ma10 = self.am.sma(10)
            ma20 = self.am.sma(20)
            ma60 = self.am.sma(60)
            
            close = self.am.close_array[-1]
            
            # 多头排列
            if ma5 > ma10 > ma20 > ma60:
                signals.append("均线多头排列")
                bullish += 1
            elif ma5 < ma10 < ma20 < ma60:
                signals.append("均线空头排列")
                bearish += 1
            
            # 价格与均线关系
            if close > ma20:
                signals.append("价格站上MA20")
                bullish += 1
            elif close < ma20:
                signals.append("价格跌破MA20")
                bearish += 1
                
        except Exception as e:
            print(f"均线计算错误: {e}")
        
        return {"signals": signals, "bullish": bullish, "bearish": bearish}
    
    def _check_macd(self) -> Dict:
        """检查MACD"""
        signals = []
        bullish = 0
        bearish = 0
        
        try:
            dif, dea, macd = self.am.macd()
            
            if dif > dea and macd > 0:
                signals.append("MACD金叉且柱状图为正")
                bullish += 1
            elif dif < dea and macd < 0:
                signals.append("MACD死叉且柱状图为负")
                bearish += 1
                
        except Exception as e:
            print(f"MACD计算错误: {e}")
        
        return {"signals": signals, "bullish": bullish, "bearish": bearish}
    
    def _check_rsi(self) -> Dict:
        """检查RSI"""
        signals = []
        bullish = 0
        bearish = 0
        
        try:
            rsi = self.am.rsi(14)
            
            if rsi < 30:
                signals.append("RSI超卖")
                bullish += 1
            elif rsi > 70:
                signals.append("RSI超买")
                bearish += 1
            elif 40 <= rsi <= 60:
                signals.append("RSI中性")
                
        except Exception as e:
            print(f"RSI计算错误: {e}")
        
        return {"signals": signals, "bullish": bullish, "bearish": bearish}
    
    def _check_kdj(self) -> Dict:
        """检查KDJ"""
        signals = []
        bullish = 0
        bearish = 0
        
        try:
            k, d, j = self.am.kdj()
            
            if k < 20 and d < 20:
                signals.append("KDJ超卖区域")
                bullish += 1
            elif k > 80 and d > 80:
                signals.append("KDJ超买区域")
                bearish += 1
            
            if k > d:
                signals.append("KDJ金叉")
                bullish += 1
            elif k < d:
                signals.append("KDJ死叉")
                bearish += 1
                
        except Exception as e:
            print(f"KDJ计算错误: {e}")
        
        return {"signals": signals, "bullish": bullish, "bearish": bearish}
    
    def _check_bollinger(self) -> Dict:
        """检查布林带"""
        signals = []
        bullish = 0
        bearish = 0
        
        try:
            upper, middle, lower = self.am.bollinger(20)
            close = self.am.close_array[-1]
            
            if close < lower:
                signals.append("价格触及布林下轨")
                bullish += 1
            elif close > upper:
                signals.append("价格触及布林上轨")
                bearish += 1
                
        except Exception as e:
            print(f"布林带计算错误: {e}")
        
        return {"signals": signals, "bullish": bullish, "bearish": bearish}
    
    def _check_atr(self) -> Dict:
        """检查ATR"""
        signals = []
        
        try:
            atr = self.am.atr(14)
            close = self.am.close_array[-1]
            atr_pct = (atr / close) * 100
            
            if atr_pct > 3:
                signals.append(f"高波动(ATR {atr_pct:.2f}%)")
            elif atr_pct < 1:
                signals.append(f"低波动(ATR {atr_pct:.2f}%)")
                
        except Exception as e:
            print(f"ATR计算错误: {e}")
        
        return {"signals": signals, "bullish": 0, "bearish": 0}
    
    # ============================================
    # 新增指标检查方法
    # ============================================
    
    def _check_vwap(self) -> Dict:
        """检查VWAP成交量加权平均价"""
        signals = []
        bullish = 0
        bearish = 0
        
        try:
            vwap = self.am.vwap()
            close = self.am.close_array[-1]
            deviation = (close - vwap) / vwap * 100 if vwap > 0 else 0
            
            if deviation > 2:
                signals.append(f"价格高于VWAP {deviation:.1f}%")
                bullish += 1
            elif deviation < -2:
                signals.append(f"价格低于VWAP {abs(deviation):.1f}%")
                bearish += 1
                
        except Exception as e:
            print(f"VWAP计算错误: {e}")
        
        return {"signals": signals, "bullish": bullish, "bearish": bearish}
    
    def _check_mfi(self) -> Dict:
        """检查MFI资金流量指数"""
        signals = []
        bullish = 0
        bearish = 0
        
        try:
            mfi = self.am.mfi(14)
            
            if mfi > 80:
                signals.append("MFI超买(资金过热)")
                bearish += 1
            elif mfi < 20:
                signals.append("MFI超卖(资金枯竭)")
                bullish += 1
            elif mfi > 50:
                signals.append("MFI显示资金流入")
                bullish += 1
            else:
                signals.append("MFI显示资金流出")
                bearish += 1
                
        except Exception as e:
            print(f"MFI计算错误: {e}")
        
        return {"signals": signals, "bullish": bullish, "bearish": bearish}
    
    def _check_turnover(self) -> Dict:
        """检查换手率"""
        signals = []
        bullish = 0
        bearish = 0
        
        try:
            turnover = self.am.turnover_rate(60)
            
            if turnover > 200:
                signals.append(f"换手率异常放大({turnover:.0f}%)")
                # 结合价格趋势判断
                if self.am.close_array[-1] > self.am.close_array[-5]:
                    bullish += 1
                else:
                    bearish += 1
            elif turnover < 50:
                signals.append(f"换手率较低({turnover:.0f}%)")
                
        except Exception as e:
            print(f"换手率计算错误: {e}")
        
        return {"signals": signals, "bullish": bullish, "bearish": bearish}
    
    def _check_bias(self) -> Dict:
        """检查BIAS乖离率"""
        signals = []
        bullish = 0
        bearish = 0
        
        try:
            bias6 = self.am.bias(6)
            
            if bias6 > 5:
                signals.append(f"BIAS超买({bias6:.1f}%)")
                bearish += 1
            elif bias6 < -5:
                signals.append(f"BIAS超卖({bias6:.1f}%)")
                bullish += 1
            elif bias6 > 2:
                signals.append(f"BIAS偏多({bias6:.1f}%)")
            elif bias6 < -2:
                signals.append(f"BIAS偏空({bias6:.1f}%)")
                
        except Exception as e:
            print(f"BIAS计算错误: {e}")
        
        return {"signals": signals, "bullish": bullish, "bearish": bearish}
    
    def _check_dmi(self) -> Dict:
        """检查DMI趋向指标"""
        signals = []
        bullish = 0
        bearish = 0
        
        try:
            plus_di, minus_di, adx = self.am.dmi(14)
            
            if adx > 25:
                if plus_di > minus_di:
                    signals.append(f"DMI强势上涨(ADX={adx:.1f})")
                    bullish += 1
                else:
                    signals.append(f"DMI强势下跌(ADX={adx:.1f})")
                    bearish += 1
            elif adx < 15:
                signals.append(f"DMI显示震荡(ADX={adx:.1f})")
            else:
                if plus_di > minus_di:
                    signals.append("DMI偏多")
                else:
                    signals.append("DMI偏空")
                
        except Exception as e:
            print(f"DMI计算错误: {e}")
        
        return {"signals": signals, "bullish": bullish, "bearish": bearish}
    
    def _check_sar(self) -> Dict:
        """检查SAR抛物线指标"""
        signals = []
        bullish = 0
        bearish = 0
        
        try:
            sar_value, trend = self.am.sar()
            close = self.am.close_array[-1]
            
            if trend == 1:
                signals.append(f"SAR上升趋势(止损:{sar_value:.2f})")
                bullish += 1
            else:
                signals.append(f"SAR下降趋势(止损:{sar_value:.2f})")
                bearish += 1
                
        except Exception as e:
            print(f"SAR计算错误: {e}")
        
        return {"signals": signals, "bullish": bullish, "bearish": bearish}
    
    def _check_ichimoku(self) -> Dict:
        """检查Ichimoku云图"""
        signals = []
        bullish = 0
        bearish = 0
        
        try:
            ichimoku = self.am.ichimoku()
            close = self.am.close_array[-1]
            
            cloud_top = ichimoku['cloud_top']
            cloud_bottom = ichimoku['cloud_bottom']
            tenkan = ichimoku['tenkan_sen']
            kijun = ichimoku['kijun_sen']
            
            # 价格与云层关系
            if close > cloud_top:
                signals.append("云图:价格在云上(强势)")
                bullish += 1
            elif close < cloud_bottom:
                signals.append("云图:价格在云下(弱势)")
                bearish += 1
            else:
                signals.append("云图:价格在云中(方向不明)")
            
            # 转换线与基准线关系
            if tenkan > kijun:
                signals.append("云图:转换线>基准线(看多)")
                bullish += 1
            else:
                signals.append("云图:转换线<基准线(看空)")
                bearish += 1
                
        except Exception as e:
            print(f"Ichimoku计算错误: {e}")
        
        return {"signals": signals, "bullish": bullish, "bearish": bearish}
    
    def get_analysis(self) -> Dict:
        """获取当前分析结果"""
        return {
            "score": round(self.signal_score, 1),
            "position": self.pos,
            "position_label": "多头" if self.pos == 1 else "空头" if self.pos == -1 else "空仓",
            "signals": self.signals,
            "recommendation": self._get_recommendation()
        }
    
    def _get_recommendation(self) -> str:
        """获取操作建议"""
        if self.signal_score >= 80:
            return "强力买入"
        elif self.signal_score >= 60:
            return "买入"
        elif self.signal_score >= 40:
            return "持有"
        elif self.signal_score >= 20:
            return "减持"
        else:
            return "卖出"
