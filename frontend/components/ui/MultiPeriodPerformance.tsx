'use client';

import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface PeriodData {
  period: string;
  label: string;
  return: number;
}

interface MultiPeriodPerformanceProps {
  data?: PeriodData[];
}

const defaultData: PeriodData[] = [
  { period: '1d', label: '周期 | 涨跌幅', return: -4.5 },
  { period: '5d', label: '5日', return: -4.5 },
  { period: '10d', label: '10日', return: -1.63 },
  { period: '20d', label: '20日', return: -7.64 },
  { period: '60d', label: '60日', return: 3.69 },
  { period: '120d', label: '120日', return: 44.75 },
  { period: '250d', label: '250日', return: 13.09 },
];

export function MultiPeriodPerformance({ data = defaultData }: MultiPeriodPerformanceProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="glass-card rounded-xl border border-white/[0.06] p-5"
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp className="w-4 h-4 text-indigo-400" />
        <h3 className="text-sm font-bold text-slate-300 tracking-wide">多周期趋势分析</h3>
        <span className="text-xs text-slate-500 uppercase">MULTI-PERIOD TREND ANALYSIS</span>
      </div>

      {/* Performance Grid */}
      <div className="space-y-2">
        {data.map((item, index) => {
          const isPositive = item.return > 0;
          const isNeutral = Math.abs(item.return) < 0.1;
          
          const trendColor = isNeutral 
            ? 'text-slate-400' 
            : isPositive 
            ? 'text-rose-400' 
            : 'text-emerald-400';
          
          const bgColor = isNeutral
            ? 'bg-slate-800/40'
            : isPositive
            ? 'bg-rose-500/5'
            : 'bg-emerald-500/5';

          const borderColor = isNeutral
            ? 'border-slate-700/50'
            : isPositive
            ? 'border-rose-500/20'
            : 'border-emerald-500/20';

          return (
            <motion.div
              key={item.period}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className={`flex items-center justify-between px-4 py-2.5 rounded-lg border ${bgColor} ${borderColor} hover:border-white/10 transition-all`}
            >
              {/* Left: Period Label */}
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <span className="text-xs text-slate-500 font-mono w-14">{item.label}</span>
                
                {/* Separator */}
                {index === 0 && (
                  <div className="flex-1 flex items-center gap-2">
                    <div className="h-px bg-slate-700/50 flex-1" />
                    <span className="text-[10px] text-slate-600 font-mono whitespace-nowrap">
                      {item.period === '1d' && item.label.includes('|') ? '' : ''}
                    </span>
                  </div>
                )}
                {index > 0 && (
                  <div className="h-px bg-slate-700/30 flex-1" />
                )}
              </div>

              {/* Right: Return Value */}
              <div className="flex items-center gap-2">
                {!isNeutral && (
                  isPositive ? (
                    <TrendingUp className="w-3.5 h-3.5 text-rose-400" />
                  ) : (
                    <TrendingDown className="w-3.5 h-3.5 text-emerald-400" />
                  )
                )}
                {isNeutral && <Minus className="w-3.5 h-3.5 text-slate-500" />}
                
                <span className={`font-mono text-sm font-bold ${trendColor} min-w-[70px] text-right`}>
                  {isPositive && '+'}{item.return.toFixed(2)}%
                </span>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Footer Stats */}
      <div className="mt-4 pt-4 border-t border-white/[0.05] grid grid-cols-2 gap-3">
        <div className="text-center">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">最佳表现</div>
          <div className="text-sm font-mono font-bold text-rose-400">
            +{Math.max(...data.map(d => d.return)).toFixed(2)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">最差表现</div>
          <div className="text-sm font-mono font-bold text-emerald-400">
            {Math.min(...data.map(d => d.return)).toFixed(2)}%
          </div>
        </div>
      </div>
    </motion.div>
  );
}
