'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowUpRight, ArrowDownRight, Activity, TrendingUp, BarChart2, Wallet } from 'lucide-react';

interface StockCardProps {
  ticker: string;
  name?: string;
  price?: number;
  change?: number;
  changePercent?: number;
  high52w?: number;
  low52w?: number;
  marketCap?: string;
  pe?: number;
  volume?: string;
  nav?: number;
  assetType?: string;
}

export function StockCard({
  ticker,
  name = '',
  price = 0,
  change = 0,
  changePercent = 0,
  high52w,
  low52w,
  marketCap,
  pe,
  volume,
  nav,
  assetType = 'EQUITY',
}: StockCardProps) {
  const [displayPrice, setDisplayPrice] = useState(price);
  const isPositive = change >= 0;
  // A�?中概风格：上涨用红色，下跌用绿色
  const trendColor = isPositive ? 'text-rose-400' : 'text-emerald-400';
  const trendBg = isPositive ? 'bg-rose-500/10' : 'bg-emerald-500/10';
  const trendBorder = isPositive ? 'border-rose-500/30' : 'border-emerald-500/30';
  const glowColor = isPositive
    ? 'from-rose-500/30 via-pink-500/20 to-red-500/10'
    : 'from-emerald-500/30 via-teal-500/20 to-cyan-500/10';

  useEffect(() => {
    setDisplayPrice(price);
  }, [price]);

  // 移除模拟价格波动，保持真实价�?

  const pricePosition = high52w && low52w && high52w !== low52w 
    ? Math.min(Math.max(((price - low52w) / (high52w - low52w)) * 100, 0), 100)
    : 50;

  // 格式化价格显�?
  const formatPrice = (p: number) => {
    if (p >= 1000) return p.toFixed(2);
    if (p >= 100) return p.toFixed(3);
    return p.toFixed(4);
  };

  return (
    <div
      className="relative group h-full"
    >
      {/* Dynamic Glow Effect */}
      <div className={`absolute -inset-1 bg-gradient-to-br ${glowColor} rounded-2xl blur-xl opacity-40 group-hover:opacity-70 transition-all duration-700`} />
      
      <div className="relative h-full rounded-xl overflow-hidden bg-gradient-to-br from-slate-900/90 via-slate-900/80 to-slate-800/70 backdrop-blur-xl border border-white/[0.08] shadow-2xl shadow-black/40">
        {/* Top Accent Line */}
        <div className={`absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r ${isPositive ? 'from-transparent via-rose-500 to-transparent' : 'from-transparent via-emerald-500 to-transparent'}`} />
        
        {/* Header - 响应�?*/}
        <div className="px-3 sm:px-5 py-3 sm:py-4 border-b border-white/[0.06] bg-gradient-to-r from-white/[0.02] to-transparent">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 sm:gap-2 mb-1 sm:mb-1.5 flex-wrap">
                <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">{ticker}</h2>
                <span className={`px-1.5 sm:px-2 py-0.5 rounded text-[8px] sm:text-[9px] font-bold tracking-wider border ${
                  assetType === 'ETF' 
                    ? 'bg-violet-500/10 border-violet-500/30 text-violet-400' 
                    : 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400'
                }`}>
                  {assetType}
                </span>
                {/* Live indicator */}
                <div
                  transition={{ duration: 2, repeat: Infinity }}
                  className="hidden sm:flex items-center gap-1"
                >
                  <div className={`w-1.5 h-1.5 rounded-full ${isPositive ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                  <span className="text-[9px] text-slate-500 font-mono">LIVE</span>
                </div>
              </div>
              <p className="text-slate-400 text-xs sm:text-sm font-medium truncate">{name || ticker}</p>
            </div>
            
            <div className={`flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg border shrink-0 ${trendBg} ${trendBorder}`}>
              {isPositive ? (
                <ArrowUpRight className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-rose-400" />
              ) : (
                <ArrowDownRight className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-emerald-400" />
              )}
              <span className={`font-mono text-sm sm:text-base font-bold ${trendColor}`}>
                {isPositive ? '+' : ''}{changePercent.toFixed(2)}%
              </span>
            </div>
          </div>
        </div>

        {/* Main Price Section - 响应�?*/}
        <div className="px-3 sm:px-5 py-4 sm:py-5">
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5 sm:gap-2 mb-1.5 sm:mb-2">
              <TrendingUp className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-slate-500" />
              <span className="text-slate-500 text-[10px] sm:text-xs font-bold tracking-widest uppercase">最新价�?/span>
            </div>
            <div className="flex items-baseline gap-2 sm:gap-3">
              <motion.span
                key={Math.floor(displayPrice * 1000)}
                className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white font-mono tracking-tighter"
                style={{ textShadow: `0 0 60px ${isPositive ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}` }}
              >
                ¥{formatPrice(displayPrice)}
              </motion.span>
            </div>
            <div className={`text-base sm:text-lg font-mono font-semibold mt-1.5 sm:mt-2 ${trendColor} flex items-center gap-1.5 sm:gap-2`}>
              <span>{change > 0 ? '+' : ''}{change.toFixed(4)}</span>
              <span className="text-slate-600 text-[10px] sm:text-xs font-sans">TODAY</span>
            </div>
          </div>

          {/* 52 Week Range - 响应�?*/}
          {high52w && low52w && high52w > 0 && low52w > 0 && (
            <div className="mt-4 sm:mt-6 pt-3 sm:pt-4 border-t border-white/[0.06]">
              <div className="flex items-center gap-1.5 sm:gap-2 mb-2 sm:mb-3">
                <Activity className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-slate-500" />
                <span className="text-[9px] sm:text-[10px] text-slate-500 uppercase tracking-widest font-bold">52周价格区�?/span>
              </div>
              <div className="relative">
                <div className="flex justify-between text-xs font-mono text-slate-500 mb-2">
                  <span>¥{low52w.toFixed(2)}</span>
                  <span>¥{high52w.toFixed(2)}</span>
                </div>
                <div className="h-2 bg-slate-800/80 rounded-full overflow-hidden relative">
                  {/* Gradient Track */}
                  <div className="absolute inset-0 bg-gradient-to-r from-rose-500/40 via-amber-500/40 to-emerald-500/40" />
                  {/* Position Indicator */}
                  <div
                    className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-white border-2 border-slate-900 shadow-lg shadow-black/50"
                    animate={{ left: `calc(${pricePosition}% - 6px)` }}
                    transition={{ duration: 1.2, ease: "easeOut" }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Key Stats Grid - 响应�?*/}
          <div className="grid grid-cols-2 gap-2 sm:gap-3 mt-4 sm:mt-5">
            <div className="bg-gradient-to-br from-slate-800/60 to-slate-800/30 rounded-lg p-2.5 sm:p-3 border border-white/[0.05] hover:border-white/[0.1] transition-colors">
              <div className="flex items-center gap-1 sm:gap-1.5 mb-1 sm:mb-1.5">
                <Wallet className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-slate-500" />
                <span className="text-[9px] sm:text-[10px] text-slate-500 uppercase tracking-widest font-bold">规模/市�?/span>
              </div>
              <div className="font-mono text-xs sm:text-sm text-white font-semibold truncate">{marketCap || '�?}</div>
            </div>
            <div className="bg-gradient-to-br from-slate-800/60 to-slate-800/30 rounded-lg p-2.5 sm:p-3 border border-white/[0.05] hover:border-white/[0.1] transition-colors">
              <div className="flex items-center gap-1 sm:gap-1.5 mb-1 sm:mb-1.5">
                <BarChart2 className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-slate-500" />
                <span className="text-[9px] sm:text-[10px] text-slate-500 uppercase tracking-widest font-bold">{(assetType === 'ETF' || assetType === 'LOF') ? '净�?NAV' : 'P/E'}</span>
              </div>
              <div className="font-mono text-xs sm:text-sm text-white font-semibold">
                {(assetType === 'ETF' || assetType === 'LOF')
                  ? (nav ? `¥${nav.toFixed(4)}` : '�?)
                  : (pe && pe > 0 ? pe.toFixed(2) : '�?)
                }
              </div>
            </div>
          </div>

          {/* Volume if available - 响应�?*/}
          {volume && (
            <div className="mt-2 sm:mt-3 bg-gradient-to-br from-slate-800/40 to-transparent rounded-lg p-2.5 sm:p-3 border border-white/[0.04]">
              <div className="flex items-center justify-between">
                <span className="text-[9px] sm:text-[10px] text-slate-500 uppercase tracking-widest font-bold">成交�?/span>
                <span className="font-mono text-xs sm:text-sm text-slate-300">{volume}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
