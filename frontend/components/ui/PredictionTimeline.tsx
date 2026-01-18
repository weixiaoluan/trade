'use client';

import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Minus, Activity, ArrowUpRight, ArrowDownRight, Zap } from 'lucide-react';
import { useMemo } from 'react';

interface PredictionCard {
  period: string;
  label: string;
  trend: 'bullish' | 'bearish' | 'neutral';
  confidence: 'high' | 'medium' | 'low';
  target?: string;
}

const defaultPredictions: PredictionCard[] = [
  { period: '1D', label: '明日', trend: 'bullish', confidence: 'medium', target: '+0.5%' },
  { period: '3D', label: '3�?, trend: 'bullish', confidence: 'medium', target: '+1.2%' },
  { period: '1W', label: '1�?, trend: 'bullish', confidence: 'high', target: '+2.5%' },
  { period: '15D', label: '15�?, trend: 'neutral', confidence: 'medium', target: '±1%' },
  { period: '1M', label: '1个月', trend: 'bullish', confidence: 'high', target: '+5%' },
  { period: '3M', label: '3个月', trend: 'bullish', confidence: 'medium', target: '+10%' },
  { period: '6M', label: '6个月', trend: 'bullish', confidence: 'low', target: '+15%' },
  { period: '1Y', label: '1�?, trend: 'bullish', confidence: 'low', target: '+25%' },
];

interface SparklineProps {
  trend: string;
  color: string;
  id: string;
}

// SVG-based sparkline component (no recharts dependency)
const Sparkline = ({ trend, color, id }: SparklineProps) => {
  const points = useMemo(() => {
    const pts = [];
    let value = 50;
    const numPoints = 12;
    for (let i = 0; i < numPoints; i++) {
      if (trend === 'bullish') value += Math.random() * 8 - 2;
      else if (trend === 'bearish') value -= Math.random() * 8 - 2;
      else value += Math.random() * 10 - 5;
      pts.push({ x: (i / (numPoints - 1)) * 100, y: Math.max(10, Math.min(90, value)) });
    }
    return pts;
  }, [trend]);
  
  const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${100 - p.y}`).join(' ');
  const areaD = `${pathD} L 100 100 L 0 100 Z`;
  
  return (
    <svg 
      className="absolute bottom-0 left-0 right-0 h-12 opacity-30 group-hover:opacity-50 transition-opacity" 
      viewBox="0 0 100 100" 
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id={`grad-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.6}/>
          <stop offset="100%" stopColor={color} stopOpacity={0}/>
        </linearGradient>
      </defs>
      <path d={areaD} fill={`url(#grad-${id})`} />
      <path d={pathD} fill="none" stroke={color} strokeWidth="2" vectorEffect="non-scaling-stroke" />
    </svg>
  );
};

interface PredictionTimelineProps {
  predictions?: PredictionCard[];
  onHoverHorizon?: (horizon: 'short' | 'mid' | 'long' | null) => void;
}

const horizonMap: Record<string, 'short' | 'mid' | 'long'> = {
  '1D': 'short',
  '3D': 'short',
  '1W': 'mid',
  '15D': 'mid',
  '1M': 'mid',
  '3M': 'long',
  '6M': 'long',
  '1Y': 'long',
};

export function PredictionTimeline({ predictions = defaultPredictions, onHoverHorizon }: PredictionTimelineProps) {
  return (
    <div className="w-full">
      {/* Header - 响应�?*/}
      <div className="flex items-center justify-between mb-4 sm:mb-6">
        <div className="flex items-center gap-2 sm:gap-3">
          <div className="p-1 sm:p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
            <TrendingUp className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-xs sm:text-sm font-bold text-white uppercase tracking-wider">
              多周期技术分�?
            </h3>
            <p className="text-[9px] sm:text-[10px] text-slate-500 font-mono mt-0.5">AI技术指标模�?/p>
          </div>
        </div>
      </div>

      {/* Grid Layout - 响应�?*/}
      <div className="grid grid-cols-4 sm:grid-cols-4 md:grid-cols-4 lg:grid-cols-8 gap-2 sm:gap-3">
        {predictions.map((prediction, index) => {
          const isBullish = prediction.trend === 'bullish';
          const isBearish = prediction.trend === 'bearish';
          const color = isBullish ? '#10B981' : isBearish ? '#F43F5E' : '#F59E0B';
          const glowClass = isBullish 
            ? 'from-emerald-500/10 to-transparent' 
            : isBearish 
            ? 'from-rose-500/10 to-transparent' 
            : 'from-amber-500/10 to-transparent';
          const borderClass = isBullish 
            ? 'border-emerald-500/30 hover:border-emerald-500/50' 
            : isBearish 
            ? 'border-rose-500/30 hover:border-rose-500/50' 
            : 'border-amber-500/30 hover:border-amber-500/50';
          const textClass = isBullish ? 'text-emerald-400' : isBearish ? 'text-rose-400' : 'text-amber-400';
          const confColor = prediction.confidence === 'high' 
            ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' 
            : prediction.confidence === 'medium' 
            ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' 
            : 'bg-slate-500/20 text-slate-400 border-slate-500/30';

          return (
            <div
              key={prediction.period}
              transition={{ delay: index * 0.06, duration: 0.4 }}
              className="relative group"
              onMouseEnter={() => onHoverHorizon?.(horizonMap[prediction.period] || null)}
              onMouseLeave={() => onHoverHorizon?.(null)}
            >
              {/* Card */}
              <div className={`
                relative overflow-hidden rounded-xl border ${borderClass}
                bg-gradient-to-br from-slate-900/80 via-slate-900/60 to-slate-800/40
                backdrop-blur-sm
                hover:shadow-lg hover:shadow-black/20
                transition-all duration-300 cursor-default
              `}>
                {/* Top accent line */}
                <div className={`absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r ${glowClass}`} />
                
                <div className="p-2 sm:p-3 md:p-4 relative z-10">
                  {/* Header - 响应�?*/}
                  <div className="flex justify-between items-center mb-1.5 sm:mb-3">
                    <span className="text-[10px] sm:text-xs font-bold text-white font-mono tracking-wider">
                      {prediction.period}
                    </span>
                    <div className={`p-0.5 sm:p-1 rounded ${isBullish ? 'bg-emerald-500/20' : isBearish ? 'bg-rose-500/20' : 'bg-amber-500/20'}`}>
                      {isBullish && <ArrowUpRight className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-emerald-400" />}
                      {isBearish && <ArrowDownRight className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-rose-400" />}
                      {!isBullish && !isBearish && <Minus className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-amber-400" />}
                    </div>
                  </div>

                  {/* Target Percentage - 响应�?*/}
                  <div className={`text-base sm:text-xl md:text-2xl lg:text-3xl font-bold font-mono tracking-tighter ${textClass} mb-1.5 sm:mb-3`}
                    style={{ textShadow: `0 0 30px ${color}40` }}
                  >
                    {prediction.target}
                  </div>

                  {/* Footer Info - 响应�?*/}
                  <div className="flex justify-between items-end gap-1">
                    <span className="text-[8px] sm:text-[10px] text-slate-400 font-medium truncate">
                      {prediction.label}
                    </span>
                    <div className={`text-[7px] sm:text-[8px] font-mono px-1 sm:px-1.5 py-0.5 rounded border shrink-0 ${confColor}`}>
                      {prediction.confidence === 'high' ? '�? : prediction.confidence === 'medium' ? '�? : '�?}
                    </div>
                  </div>
                </div>

                {/* Sparkline Chart */}
                <Sparkline trend={prediction.trend} color={color} id={`sparkline-${prediction.period}`} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
