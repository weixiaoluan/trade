"use client";

import { memo } from "react";
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  AlertTriangle,
  Target,
  Shield,
  CheckCircle2,
  Clock,
  Info
} from "lucide-react";

interface TradingSignalProps {
  signal: {
    type: string;
    type_cn: string;
    strength: number;
    strength_label: string;
    confidence: number;
    description: string;
    triggered_conditions: string[];
    pending_conditions: string[];
  };
  riskManagement: {
    stop_loss: number;
    stop_loss_pct: number;
    take_profit_targets: Array<{
      level: number;
      price: number;
      ratio: string;
    }>;
    suggested_position_pct: number;
    max_loss_per_trade: number;
  };
  actionSuggestion: string;
  currentPrice: number;
}

export const TradingSignalCard = memo(function TradingSignalCard({
  signal,
  riskManagement,
  actionSuggestion,
  currentPrice
}: TradingSignalProps) {
  // 信号类型样式
  const getSignalStyle = () => {
    switch (signal.type) {
      case "buy":
        return {
          bg: "bg-emerald-500/10",
          border: "border-emerald-500/30",
          text: "text-emerald-400",
          icon: TrendingUp,
          label: "🟢 买入信号"
        };
      case "sell":
        return {
          bg: "bg-rose-500/10",
          border: "border-rose-500/30",
          text: "text-rose-400",
          icon: TrendingDown,
          label: "🔴 卖出信号"
        };
      default:
        return {
          bg: "bg-slate-500/10",
          border: "border-slate-500/30",
          text: "text-slate-400",
          icon: Minus,
          label: "⚪ 观望信号"
        };
    }
  };

  const style = getSignalStyle();
  const SignalIcon = style.icon;

  // 信号强度星星
  const renderStrength = () => {
    const stars = [];
    for (let i = 0; i < 5; i++) {
      stars.push(
        <span key={i} className={i < signal.strength ? "text-amber-400" : "text-slate-600"}>
          ★
        </span>
      );
    }
    return stars;
  };

  // 格式化价格
  const formatPrice = (price: number) => {
    if (price >= 1000) return price.toFixed(2);
    if (price >= 100) return price.toFixed(2);
    if (price >= 10) return price.toFixed(3);
    return price.toFixed(4);
  };

  return (
    <div className="glass-card rounded-xl border border-white/[0.06] overflow-hidden">
      {/* 标题栏 */}
      <div className={`px-4 py-3 ${style.bg} border-b ${style.border}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SignalIcon className={`w-5 h-5 ${style.text}`} />
            <span className={`font-bold ${style.text}`}>{style.label}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">信号强度:</span>
            <span className="text-sm">{renderStrength()}</span>
          </div>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* 信号描述 */}
        <div className="flex items-start gap-3">
          <Info className="w-4 h-4 text-indigo-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className={`text-sm font-medium ${style.text}`}>{signal.description}</p>
            <p className="text-xs text-slate-500 mt-1">置信度: {signal.confidence}%</p>
          </div>
        </div>

        {/* 触发条件 */}
        {signal.triggered_conditions.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span className="text-xs text-slate-400">已触发条件</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {signal.triggered_conditions.map((condition, idx) => (
                <span
                  key={idx}
                  className={`px-2 py-1 rounded-full text-[10px] border ${
                    signal.type === "buy"
                      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                      : signal.type === "sell"
                      ? "border-rose-500/40 bg-rose-500/10 text-rose-300"
                      : "border-slate-600/60 bg-slate-900/60 text-slate-300"
                  }`}
                >
                  ✓ {condition}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 待确认条件 */}
        {signal.pending_conditions.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-4 h-4 text-amber-400" />
              <span className="text-xs text-slate-400">待确认/注意事项</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {signal.pending_conditions.slice(0, 5).map((condition, idx) => (
                <span
                  key={idx}
                  className="px-2 py-1 rounded-full text-[10px] border border-amber-500/30 bg-amber-500/10 text-amber-300"
                >
                  {condition}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 风险管理 */}
        <div className="border-t border-white/[0.06] pt-4">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="w-4 h-4 text-sky-400" />
            <span className="text-xs text-slate-400 font-medium">风险管理参考</span>
          </div>
          
          <div className="grid grid-cols-2 gap-3">
            {/* 止损位 */}
            <div className="bg-rose-500/5 border border-rose-500/20 rounded-lg p-3">
              <div className="text-[10px] text-rose-400 mb-1">止损参考位</div>
              <div className="text-lg font-mono font-bold text-rose-300">
                {formatPrice(riskManagement.stop_loss)}
              </div>
              <div className="text-[10px] text-slate-500">
                距当前 -{riskManagement.stop_loss_pct.toFixed(1)}%
              </div>
            </div>
            
            {/* 建议仓位 */}
            <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-lg p-3">
              <div className="text-[10px] text-indigo-400 mb-1">建议仓位上限</div>
              <div className="text-lg font-mono font-bold text-indigo-300">
                {riskManagement.suggested_position_pct}%
              </div>
              <div className="text-[10px] text-slate-500">
                单笔最大亏损 ¥{riskManagement.max_loss_per_trade}
              </div>
            </div>
          </div>

          {/* 止盈目标 */}
          <div className="mt-3">
            <div className="flex items-center gap-2 mb-2">
              <Target className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-[10px] text-slate-400">止盈目标参考</span>
            </div>
            <div className="flex gap-2">
              {riskManagement.take_profit_targets.map((target) => (
                <div
                  key={target.level}
                  className="flex-1 bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-2 text-center"
                >
                  <div className="text-[9px] text-emerald-400/70">目标{target.level} ({target.ratio})</div>
                  <div className="text-sm font-mono font-medium text-emerald-300">
                    {formatPrice(target.price)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 操作建议 */}
        <div className="border-t border-white/[0.06] pt-4">
          <div className={`p-3 rounded-lg ${style.bg} border ${style.border}`}>
            <div className="flex items-start gap-2">
              <AlertTriangle className={`w-4 h-4 ${style.text} mt-0.5 flex-shrink-0`} />
              <div>
                <div className={`text-sm font-medium ${style.text}`}>操作参考</div>
                <p className="text-xs text-slate-400 mt-1">{actionSuggestion}</p>
              </div>
            </div>
          </div>
        </div>

        {/* 免责声明 */}
        <div className="text-[10px] text-slate-600 text-center pt-2 border-t border-white/[0.04]">
          ⚠️ 以上内容仅为技术分析工具输出，不构成投资建议，请独立判断并自行承担风险
        </div>
      </div>
    </div>
  );
});

export default TradingSignalCard;
