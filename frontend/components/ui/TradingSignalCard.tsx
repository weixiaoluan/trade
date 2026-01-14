"use client";

import { memo, useState } from "react";
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  AlertTriangle,
  Target,
  Shield,
  CheckCircle2,
  Clock,
  Activity,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Gauge
} from "lucide-react";

interface PeriodAnalysis {
  signal_type: string;
  type_cn: string;
  strength: number;
  strength_label: string;
  confidence: number;
  triggered_conditions: string[];
  period_label: string;
  risk_management: {
    stop_loss: number;
    stop_loss_pct: number;
    take_profit_targets: Array<{
      level: number;
      price: number;
      ratio: string;
    }>;
    suggested_position_pct: number;
  };
  action_suggestion: string;
  position_strategy: {
    empty_position: string;
    first_entry: string;
    add_position: string;
    reduce_position: string;
    full_exit: string;
  };
}

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
    max_loss_per_trade?: number;
    position_strategy?: {
      empty_position: string;
      first_entry: string;
      add_position: string;
      reduce_position: string;
      full_exit: string;
    };
  };
  actionSuggestion: string;
  currentPrice: number;
  quantScore?: number;
  multiPeriodAnalysis?: {
    short: PeriodAnalysis;
    swing: PeriodAnalysis;
    long: PeriodAnalysis;
  };
}

export const TradingSignalCard = memo(function TradingSignalCard({
  signal,
  riskManagement,
  actionSuggestion,
  currentPrice,
  quantScore,
  multiPeriodAnalysis
}: TradingSignalProps) {
  const periods = ['short', 'swing', 'long'] as const;
  const periodLabels = { short: '短线', swing: '波段', long: '中长线' };
  const [activePeriod, setActivePeriod] = useState<'short' | 'swing' | 'long'>('swing');

  // 获取当前周期的分析数据
  const getCurrentAnalysis = () => {
    if (multiPeriodAnalysis && multiPeriodAnalysis[activePeriod]) {
      return multiPeriodAnalysis[activePeriod];
    }
    // 如果没有多周期数据，使用传入的单周期数据
    return null;
  };

  const currentAnalysis = getCurrentAnalysis();
  
  // 使用当前周期的数据或默认数据
  const displaySignal = currentAnalysis ? {
    type: currentAnalysis.signal_type,
    type_cn: currentAnalysis.type_cn,
    strength: currentAnalysis.strength,
    strength_label: currentAnalysis.strength_label,
    confidence: currentAnalysis.confidence,
    description: `${currentAnalysis.type_cn}信号触发 (${currentAnalysis.triggered_conditions.length}个条件满足)`,
    triggered_conditions: currentAnalysis.triggered_conditions,
    pending_conditions: []
  } : signal;

  const displayRiskManagement = currentAnalysis ? currentAnalysis.risk_management : riskManagement;
  const displayActionSuggestion = currentAnalysis ? currentAnalysis.action_suggestion : actionSuggestion;
  const displayPositionStrategy = currentAnalysis?.position_strategy || riskManagement.position_strategy;

  // 信号类型样式
  const getSignalStyle = (signalType: string) => {
    switch (signalType) {
      case "buy":
        return {
          bg: "from-emerald-500/20 via-emerald-500/10 to-transparent",
          border: "border-emerald-500/40",
          text: "text-emerald-400",
          glow: "shadow-emerald-500/20",
          icon: TrendingUp,
          label: "买入信号",
          emoji: "🟢"
        };
      case "sell":
        return {
          bg: "from-rose-500/20 via-rose-500/10 to-transparent",
          border: "border-rose-500/40",
          text: "text-rose-400",
          glow: "shadow-rose-500/20",
          icon: TrendingDown,
          label: "卖出信号",
          emoji: "🔴"
        };
      default:
        return {
          bg: "from-slate-500/20 via-slate-500/10 to-transparent",
          border: "border-slate-500/40",
          text: "text-slate-400",
          glow: "shadow-slate-500/20",
          icon: Minus,
          label: "观望信号",
          emoji: "⚪"
        };
    }
  };

  const style = getSignalStyle(displaySignal.type);
  const SignalIcon = style.icon;

  // 信号强度星星
  const renderStrength = (strength: number) => {
    const stars = [];
    for (let i = 0; i < 5; i++) {
      stars.push(
        <span key={i} className={`text-lg ${i < strength ? "text-amber-400 drop-shadow-[0_0_3px_rgba(251,191,36,0.5)]" : "text-slate-700"}`}>
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

  // 切换周期
  const switchPeriod = (direction: 'prev' | 'next') => {
    const currentIndex = periods.indexOf(activePeriod);
    if (direction === 'prev') {
      setActivePeriod(periods[(currentIndex - 1 + 3) % 3]);
    } else {
      setActivePeriod(periods[(currentIndex + 1) % 3]);
    }
  };

  // 默认仓位策略
  const positionStrategy = displayPositionStrategy || {
    empty_position: displaySignal.type === "buy" ? "可考虑首次建仓" : (displaySignal.type === "sell" ? "保持空仓观望" : "保持空仓等待信号"),
    first_entry: displaySignal.type === "buy" ? `建议首次建仓 ${Math.round(displayRiskManagement.suggested_position_pct / 3)}成仓位` : "不建议此时建仓",
    add_position: displaySignal.type === "buy" ? `突破阻力位可加仓至 ${Math.round(displayRiskManagement.suggested_position_pct / 10 * 2)}成` : "不建议加仓",
    reduce_position: displaySignal.type === "sell" ? "建议减仓或清仓" : `跌破止损位减仓至 ${Math.round(displayRiskManagement.suggested_position_pct / 10)}成`,
    full_exit: `触及止损位 ${formatPrice(displayRiskManagement.stop_loss)} 建议清仓`
  };

  return (
    <div className={`relative overflow-hidden rounded-2xl border-2 ${style.border} bg-gradient-to-br ${style.bg} backdrop-blur-xl shadow-2xl ${style.glow}`}>
      {/* 背景装饰 */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-white/[0.03] via-transparent to-transparent pointer-events-none" />
      
      {/* 标题栏 - 带周期切换 */}
      <div className={`relative px-5 py-4 border-b border-white/[0.08]`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-xl bg-gradient-to-br ${style.bg} border ${style.border}`}>
              <SignalIcon className={`w-6 h-6 ${style.text}`} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-2xl">{style.emoji}</span>
                <span className={`text-xl font-bold ${style.text}`}>{style.label}</span>
              </div>
              <div className="text-xs text-slate-500 mt-0.5">置信度 {displaySignal.confidence}%</div>
            </div>
          </div>
          
          {/* 量化评分 */}
          {quantScore !== undefined && (
            <div className="flex items-center gap-2 mr-4">
              <Gauge className="w-4 h-4 text-indigo-400" />
              <span className="text-xs text-slate-400">量化评分</span>
              <span className={`text-lg font-mono font-bold ${
                quantScore >= 70 ? 'text-emerald-400' : 
                quantScore >= 50 ? 'text-sky-400' : 
                quantScore >= 30 ? 'text-amber-400' : 'text-rose-400'
              }`}>{quantScore.toFixed(1)}</span>
            </div>
          )}
          
          <div className="text-right">
            <div className="text-xs text-slate-500 mb-1">信号强度</div>
            <div className="flex items-center gap-0.5">{renderStrength(displaySignal.strength)}</div>
          </div>
        </div>
        
        {/* 周期切换器 */}
        {multiPeriodAnalysis && (
          <div className="flex items-center justify-center gap-2 mt-4 pt-3 border-t border-white/[0.06]">
            <button 
              onClick={() => switchPeriod('prev')}
              className="p-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] transition-colors"
            >
              <ChevronLeft className="w-4 h-4 text-slate-400" />
            </button>
            
            <div className="flex items-center gap-1">
              {periods.map((period) => {
                const periodData = multiPeriodAnalysis[period];
                const periodStyle = getSignalStyle(periodData?.signal_type || 'hold');
                const isActive = period === activePeriod;
                
                return (
                  <button
                    key={period}
                    onClick={() => setActivePeriod(period)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      isActive 
                        ? `${periodStyle.bg} ${periodStyle.border} border ${periodStyle.text}` 
                        : 'bg-white/[0.03] border border-white/[0.08] text-slate-400 hover:bg-white/[0.06]'
                    }`}
                  >
                    <span className="mr-1">{periodStyle.emoji}</span>
                    {periodLabels[period]}
                  </button>
                );
              })}
            </div>
            
            <button 
              onClick={() => switchPeriod('next')}
              className="p-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] transition-colors"
            >
              <ChevronRight className="w-4 h-4 text-slate-400" />
            </button>
          </div>
        )}
      </div>

      <div className="relative p-5 space-y-5">
        {/* 当前周期标签 */}
        {currentAnalysis && (
          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${style.bg} ${style.border} border ${style.text}`}>
              {currentAnalysis.period_label}
            </span>
          </div>
        )}

        {/* 信号描述 */}
        <div className={`flex items-start gap-3 p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]`}>
          <Activity className={`w-5 h-5 ${style.text} mt-0.5 flex-shrink-0`} />
          <div className="flex-1">
            <p className={`text-base font-semibold ${style.text}`}>{displaySignal.description}</p>
            <p className="text-sm text-slate-400 mt-1.5 leading-relaxed">{displayActionSuggestion}</p>
          </div>
        </div>

        {/* 触发条件 */}
        {displaySignal.triggered_conditions.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span className="text-sm text-slate-300 font-medium">已触发条件</span>
              <span className="text-xs text-slate-500">({displaySignal.triggered_conditions.length}项)</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {displaySignal.triggered_conditions.map((condition, idx) => (
                <span
                  key={idx}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border backdrop-blur-sm ${
                    displaySignal.type === "buy"
                      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                      : displaySignal.type === "sell"
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
        {displaySignal.pending_conditions && displaySignal.pending_conditions.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Clock className="w-4 h-4 text-amber-400" />
              <span className="text-sm text-slate-300 font-medium">待确认/注意事项</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {displaySignal.pending_conditions.slice(0, 6).map((condition, idx) => (
                <span
                  key={idx}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium border border-amber-500/30 bg-amber-500/10 text-amber-300 backdrop-blur-sm"
                >
                  {condition}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 风险管理 */}
        <div className="border-t border-white/[0.08] pt-5">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-5 h-5 text-sky-400" />
            <span className="text-base text-slate-200 font-semibold">风险管理参考</span>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            {/* 止损位 */}
            <div className="relative overflow-hidden bg-gradient-to-br from-rose-500/10 to-rose-500/5 border border-rose-500/30 rounded-xl p-4">
              <div className="absolute top-0 right-0 w-16 h-16 bg-rose-500/10 rounded-full blur-2xl" />
              <div className="relative">
                <div className="text-xs text-rose-400/80 font-medium mb-2">止损参考位</div>
                <div className="text-2xl font-mono font-bold text-rose-300">
                  {formatPrice(displayRiskManagement.stop_loss)}
                </div>
                <div className="text-sm text-rose-400/60 mt-1">
                  距当前 <span className="font-semibold">-{displayRiskManagement.stop_loss_pct.toFixed(1)}%</span>
                </div>
              </div>
            </div>
            
            {/* 建议仓位 */}
            <div className="relative overflow-hidden bg-gradient-to-br from-indigo-500/10 to-indigo-500/5 border border-indigo-500/30 rounded-xl p-4">
              <div className="absolute top-0 right-0 w-16 h-16 bg-indigo-500/10 rounded-full blur-2xl" />
              <div className="relative">
                <div className="text-xs text-indigo-400/80 font-medium mb-2">建议仓位上限</div>
                <div className="text-2xl font-mono font-bold text-indigo-300">
                  {Math.round(displayRiskManagement.suggested_position_pct / 10)}成
                </div>
                <div className="text-sm text-indigo-400/60 mt-1">
                  约 <span className="font-semibold">{displayRiskManagement.suggested_position_pct}%</span> 总仓位
                </div>
              </div>
            </div>
          </div>

          {/* 止盈目标 */}
          <div className="mt-4">
            <div className="flex items-center gap-2 mb-3">
              <Target className="w-4 h-4 text-emerald-400" />
              <span className="text-sm text-slate-300 font-medium">止盈目标参考</span>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {displayRiskManagement.take_profit_targets.map((target) => (
                <div
                  key={target.level}
                  className="relative overflow-hidden bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border border-emerald-500/25 rounded-xl p-3 text-center"
                >
                  <div className="text-[10px] text-emerald-400/70 font-medium">目标{target.level}</div>
                  <div className="text-lg font-mono font-bold text-emerald-300 my-1">
                    {formatPrice(target.price)}
                  </div>
                  <div className="text-[10px] text-emerald-400/50">风险收益比 {target.ratio}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 操作策略参考 */}
        <div className="border-t border-white/[0.08] pt-5">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-violet-400" />
            <span className="text-base text-slate-200 font-semibold">操作策略参考</span>
          </div>
          
          <div className="space-y-3">
            {/* 空仓状态 */}
            <div className="flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
              <div className="w-2 h-2 rounded-full bg-slate-400 mt-2 flex-shrink-0" />
              <div>
                <div className="text-xs text-slate-500 mb-1">空仓状态</div>
                <div className="text-sm text-slate-300">{positionStrategy.empty_position}</div>
              </div>
            </div>
            
            {/* 首次建仓 */}
            <div className={`flex items-start gap-3 p-3 rounded-xl border ${
              displaySignal.type === "buy" 
                ? "bg-emerald-500/5 border-emerald-500/20" 
                : "bg-white/[0.02] border-white/[0.06]"
            }`}>
              <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${displaySignal.type === "buy" ? "bg-emerald-400" : "bg-slate-500"}`} />
              <div>
                <div className="text-xs text-slate-500 mb-1">首次建仓</div>
                <div className={`text-sm ${displaySignal.type === "buy" ? "text-emerald-300 font-medium" : "text-slate-400"}`}>
                  {positionStrategy.first_entry}
                </div>
              </div>
            </div>
            
            {/* 加仓条件 */}
            <div className={`flex items-start gap-3 p-3 rounded-xl border ${
              displaySignal.type === "buy" && displaySignal.strength >= 3
                ? "bg-emerald-500/5 border-emerald-500/20" 
                : "bg-white/[0.02] border-white/[0.06]"
            }`}>
              <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${displaySignal.type === "buy" && displaySignal.strength >= 3 ? "bg-emerald-400" : "bg-slate-500"}`} />
              <div>
                <div className="text-xs text-slate-500 mb-1">加仓条件</div>
                <div className={`text-sm ${displaySignal.type === "buy" && displaySignal.strength >= 3 ? "text-emerald-300 font-medium" : "text-slate-400"}`}>
                  {positionStrategy.add_position}
                </div>
              </div>
            </div>
            
            {/* 减仓条件 */}
            <div className={`flex items-start gap-3 p-3 rounded-xl border ${
              displaySignal.type === "sell" 
                ? "bg-rose-500/5 border-rose-500/20" 
                : "bg-white/[0.02] border-white/[0.06]"
            }`}>
              <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${displaySignal.type === "sell" ? "bg-rose-400" : "bg-amber-400"}`} />
              <div>
                <div className="text-xs text-slate-500 mb-1">减仓/止损</div>
                <div className={`text-sm ${displaySignal.type === "sell" ? "text-rose-300 font-medium" : "text-amber-300"}`}>
                  {positionStrategy.reduce_position}
                </div>
              </div>
            </div>
            
            {/* 清仓条件 */}
            <div className="flex items-start gap-3 p-3 rounded-xl bg-rose-500/5 border border-rose-500/20">
              <div className="w-2 h-2 rounded-full bg-rose-400 mt-2 flex-shrink-0" />
              <div>
                <div className="text-xs text-slate-500 mb-1">清仓条件</div>
                <div className="text-sm text-rose-300">{positionStrategy.full_exit}</div>
              </div>
            </div>
          </div>
        </div>

        {/* 免责声明 */}
        <div className="border-t border-white/[0.08] pt-5">
          <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-500/5 border border-amber-500/20">
            <AlertTriangle className="w-6 h-6 text-amber-400 flex-shrink-0" />
            <div>
              <div className="text-sm font-semibold text-amber-300 mb-1">⚠️ 重要提示</div>
              <p className="text-sm text-amber-200/80 leading-relaxed">
                以上内容仅为技术分析工具输出，不构成任何投资建议。市场有风险，投资需谨慎，请独立判断并自行承担风险。
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});

export default TradingSignalCard;
