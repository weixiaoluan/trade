'use client';

// framer-motion removed for performance
import { Gauge, Activity, Waves } from 'lucide-react';

interface QuantDashboardCardProps {
  score?: number;
  marketRegime?: string;
  volatilityState?: string;
  adxValue?: number;
  adxTrendStrength?: string;
  atrPct?: number;
  activeHorizon?: 'short' | 'mid' | 'long';
}

function mapRegime(regime?: string): { label: string; tone: string } {
  switch (regime) {
    case 'trending':
      return { label: '趋势市', tone: 'text-emerald-400' };
    case 'ranging':
      return { label: '震荡市', tone: 'text-amber-400' };
    case 'squeeze':
      return { label: '窄幅整理 / 突破蓄势', tone: 'text-sky-400' };
    default:
      return { label: '待判定', tone: 'text-slate-400' };
  }
}

function mapVolatility(vol?: string): { label: string; tone: string } {
  switch (vol) {
    case 'low':
      return { label: '低波动', tone: 'text-emerald-400' };
    case 'high':
      return { label: '高波动', tone: 'text-rose-400' };
    default:
      return { label: '中等波动', tone: 'text-amber-400' };
  }
}

function mapAdxStrength(strength?: string): string {
  switch (strength) {
    case 'strong':
      return '趋势强';
    case 'weak':
      return '趋势弱';
    case 'moderate':
      return '趋势中等';
    default:
      return '';
  }
}

function deriveStrategyMode(
  score?: number,
  regime?: string,
): { label: string; en: string; badgeClass: string } {
  if (typeof score !== 'number') {
    return {
      label: '观望',
      en: 'OBSERVE',
      badgeClass: 'bg-slate-900/80 border-slate-700 text-slate-300',
    };
  }

  // 高分 + 趋势市 → 趋势跟随
  if (score >= 60 && regime === 'trending') {
    return {
      label: '趋势跟随',
      en: 'TREND FOLLOW',
      badgeClass: 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300',
    };
  }

  // 中高分 + 震荡市 → 区间交易
  if (score >= 60 && regime === 'ranging') {
    return {
      label: '区间交易',
      en: 'RANGE TRADE',
      badgeClass: 'bg-amber-500/10 border-amber-500/40 text-amber-300',
    };
  }

  // 其他情况以观望/防守为主
  return {
    label: '观望',
    en: 'OBSERVE',
    badgeClass:
      score <= 40
        ? 'bg-rose-500/10 border-rose-500/40 text-rose-300'
        : 'bg-slate-900/80 border-slate-700 text-slate-300',
  };
}

export function QuantDashboardCard({
  score,
  marketRegime,
  volatilityState,
  adxValue,
  adxTrendStrength,
  atrPct,
  activeHorizon,
}: QuantDashboardCardProps) {
  const displayScore = typeof score === 'number' ? Math.max(0, Math.min(100, score)) : undefined;
  const scoreText = displayScore !== undefined ? displayScore.toFixed(1) : 'N/A';

  const regimeInfo = mapRegime(marketRegime);
  const volInfo = mapVolatility(volatilityState);

  const adxText =
    typeof adxValue === 'number'
      ? `${adxValue.toFixed(1)} · ${mapAdxStrength(adxTrendStrength)}`
      : undefined;
  const atrText = typeof atrPct === 'number' ? `${atrPct.toFixed(2)}% / 日` : undefined;

  const strategyMode = deriveStrategyMode(displayScore, marketRegime);

  const scoreLevel = displayScore !== undefined ? (displayScore >= 80 ? 'strong' : displayScore >= 60 ? 'positive' : displayScore >= 40 ? 'neutral' : 'negative') : 'neutral';

  const scoreColor =
    scoreLevel === 'strong'
      ? 'from-emerald-400 to-teal-500'
      : scoreLevel === 'positive'
      ? 'from-sky-400 to-emerald-400'
      : scoreLevel === 'neutral'
      ? 'from-slate-400 to-slate-500'
      : 'from-rose-400 to-red-500';

  return (
    <div className="glass-card rounded-xl border border-white/[0.06] p-3 sm:p-4 flex flex-col gap-3 sm:gap-4 animate-fadeIn">
      {/* Header - 移动端优化 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 sm:gap-3">
          <div className="w-7 h-7 sm:w-9 sm:h-9 rounded-lg sm:rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
            <Gauge className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-indigo-300" />
          </div>
          <div>
            <div className="text-[10px] sm:text-xs font-semibold text-slate-400 tracking-wider">量化状态仪表盘</div>
            <div className="text-[8px] sm:text-[10px] uppercase tracking-wider text-slate-600 hidden sm:block">QUANT SCORE · REGIME · VOLATILITY</div>
          </div>
        </div>
      </div>

      {/* Stats Grid - 移动端优化为垂直布局 */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 items-start">
        {/* 量化评分 */}
        <div className="flex sm:flex-col items-center sm:items-start justify-between sm:justify-start gap-2">
          <div className="flex items-center sm:flex-col sm:items-start gap-2 sm:gap-0">
            <div className="text-[9px] sm:text-[10px] uppercase tracking-wider text-slate-500">量化评分</div>
            <div className="flex items-baseline gap-1">
              <span className="text-xl sm:text-2xl font-bold text-slate-50 font-mono">{scoreText}</span>
              {displayScore !== undefined && <span className="text-[10px] sm:text-[11px] text-slate-500">/ 100</span>}
            </div>
          </div>
          {displayScore !== undefined && (
            <div className="w-24 sm:w-full h-1.5 bg-slate-900 rounded-full overflow-hidden">
              <div
                className={`h-full bg-gradient-to-r ${scoreColor}`}
                style={{ width: `${displayScore}%` }}
              />
            </div>
          )}
        </div>

        {/* 市场状态 */}
        <div className="flex sm:flex-col items-start gap-1.5 sm:gap-2">
          <div className="flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs text-slate-400">
            <Activity className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-emerald-400" />
            <span>市场状态</span>
          </div>
          <div className="text-xs sm:text-sm font-medium flex flex-col gap-0.5 sm:gap-1">
            <span className={regimeInfo.tone}>{regimeInfo.label}</span>
            <span className="text-[9px] sm:text-[11px] text-slate-500 hidden sm:block">
              {marketRegime === 'trending'
                ? '趋势主导，适合顺势策略'
                : marketRegime === 'ranging'
                ? '区间震荡，适合高抛低吸'
                : marketRegime === 'squeeze'
                ? '波动收窄，警惕突破'
                : '信号有限，建议降低仓位'}
            </span>
          </div>
        </div>

        {/* 波动强度 */}
        <div className="flex sm:flex-col items-start gap-1.5 sm:gap-2">
          <div className="flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs text-slate-400">
            <Waves className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-sky-400" />
            <span>波动强度</span>
          </div>
          <div className="text-xs sm:text-sm font-medium flex flex-col gap-0.5 sm:gap-1">
            <span className={volInfo.tone}>{volInfo.label}</span>
            <span className="text-[9px] sm:text-[11px] text-slate-500 hidden sm:block">
              {volatilityState === 'low'
                ? '价格相对平稳，适合稳健资金'
                : volatilityState === 'high'
                ? '波动放大，需严格控制仓位与止损'
                : '波动适中，可根据策略灵活调仓'}
            </span>
          </div>
        </div>
      </div>

      {/* Footer - 移动端优化 */}
      <div className="mt-1 sm:mt-3 flex flex-col sm:flex-row sm:flex-wrap items-start sm:items-center justify-between gap-2 sm:gap-3 text-[10px] sm:text-[11px] text-slate-500">
        <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
          {adxText && <span className="font-mono text-[9px] sm:text-[11px]">ADX {adxText}</span>}
          {atrText && <span className="font-mono text-[9px] sm:text-[11px]">ATR {atrText}</span>}
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <div className="flex items-center gap-1.5">
            <span className="text-[9px] sm:text-[10px] uppercase tracking-wider text-slate-600">策略</span>
            <span
              className={`px-1.5 sm:px-2 py-0.5 rounded-full border text-[9px] sm:text-[10px] font-medium ${strategyMode.badgeClass}`}
            >
              {strategyMode.label}
            </span>
          </div>
          <div className="flex items-center gap-1">
            {['short', 'mid', 'long'].map((h) => (
              <span
                key={h}
                className={`px-1.5 sm:px-2 py-0.5 rounded-full border text-[8px] sm:text-[10px] cursor-default ${
                  activeHorizon === h
                    ? h === 'short' ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
                      : h === 'mid' ? 'bg-sky-500/20 border-sky-500/40 text-sky-300'
                      : 'bg-violet-500/20 border-violet-500/40 text-violet-300'
                    : 'bg-slate-900/80 border-slate-700 text-slate-400'
                }`}
              >
                {h === 'short' ? '短' : h === 'mid' ? '中' : '长'}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
