'use client';

import { motion } from 'framer-motion';
import { 
  ThumbsUp, 
  ThumbsDown, 
  Minus, 
  TrendingUp, 
  TrendingDown,
  Sparkles,
  AlertCircle,
  Shield,
  Copy,
  Share2
} from 'lucide-react';
import { useState } from 'react';

type Recommendation = 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell';

interface AIRecommendationCardProps {
  recommendation: Recommendation;
  summary: string;
  confidence?: number;
  riskLevel?: 'low' | 'medium' | 'high';
}

// 技术面评级配置 - 仅表示技术指标状态，不构成投资建�?
const recommendationConfig = {
  strong_buy: {
    label: '强势',
    labelEn: 'STRONG',
    icon: TrendingUp,
    accentColor: 'bg-gradient-to-b from-emerald-500 to-emerald-600',
    bgTint: 'bg-emerald-500/5',
    textColor: 'text-emerald-400',
    badgeColor: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
  },
  buy: {
    label: '偏强',
    labelEn: 'BULLISH',
    icon: ThumbsUp,
    accentColor: 'bg-gradient-to-b from-emerald-500 to-teal-600',
    bgTint: 'bg-emerald-500/5',
    textColor: 'text-emerald-400',
    badgeColor: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
  },
  hold: {
    label: '中�?,
    labelEn: 'NEUTRAL',
    icon: Minus,
    accentColor: 'bg-gradient-to-b from-amber-500 to-amber-600',
    bgTint: 'bg-amber-500/5',
    textColor: 'text-amber-400',
    badgeColor: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
  },
  sell: {
    label: '偏弱',
    labelEn: 'BEARISH',
    icon: ThumbsDown,
    accentColor: 'bg-gradient-to-b from-rose-500 to-rose-600',
    bgTint: 'bg-rose-500/5',
    textColor: 'text-rose-400',
    badgeColor: 'bg-rose-500/10 border-rose-500/20 text-rose-400',
  },
  strong_sell: {
    label: '弱势',
    labelEn: 'WEAK',
    icon: TrendingDown,
    accentColor: 'bg-gradient-to-b from-rose-500 to-red-600',
    bgTint: 'bg-rose-500/5',
    textColor: 'text-rose-400',
    badgeColor: 'bg-rose-500/10 border-rose-500/20 text-rose-400',
  },
};

export function AIRecommendationCard({
  recommendation,
  summary,
  confidence = 75,
  riskLevel = 'medium',
}: AIRecommendationCardProps) {
  // 确保 recommendation 有效，默认为 hold
  const safeRecommendation = (recommendation && recommendationConfig[recommendation]) 
    ? recommendation 
    : 'hold';
  const config = recommendationConfig[safeRecommendation];
  const Icon = config.icon;
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(summary);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className="glass-card rounded-xl overflow-hidden"
    >
      {/* Left Accent Border */}
      <div className="flex h-full">
        <div className={`w-1 ${config.accentColor} flex-shrink-0`} />
        
        <div className="flex-1 p-3 sm:p-5">
          {/* Header - 移动端优�?*/}
          <div className="flex items-start justify-between mb-3 sm:mb-5 gap-2">
            <div className="flex items-center gap-2 sm:gap-4 min-w-0">
              {/* Icon */}
              <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-lg sm:rounded-xl ${config.bgTint} border border-white/10 flex items-center justify-center shadow-lg shadow-black/20 flex-shrink-0`}>
                <Icon className={`w-5 h-5 sm:w-6 sm:h-6 ${config.textColor}`} />
              </div>
              
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 sm:gap-2 mb-1 sm:mb-1.5 flex-wrap">
                  <span className="badge-tech text-indigo-300 border-indigo-500/30 bg-indigo-500/10 text-[9px] sm:text-[10px]">AI深度解读</span>
                  <span className="text-[9px] sm:text-[10px] text-slate-500 font-mono hidden sm:inline">{new Date().toLocaleDateString()}</span>
                </div>
                <div className="flex items-baseline gap-1.5 sm:gap-2">
                  <span className={`text-base sm:text-xl font-bold tracking-tight ${config.textColor}`}>{config.label}</span>
                  <span className="text-[10px] sm:text-xs font-bold opacity-60 tracking-wider hidden sm:inline">{config.labelEn}</span>
                </div>
              </div>
            </div>
            
            {/* Actions */}
            <div className="flex items-center gap-1 flex-shrink-0">
              <button 
                onClick={handleCopy}
                className="p-1.5 rounded-md hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-colors"
                title="复制"
              >
                <Copy className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Confidence Meter */}
          <div className="mb-3 sm:mb-4">
            <div className="flex items-center justify-between mb-1 sm:mb-1.5">
              <span className="text-[9px] sm:text-[10px] uppercase tracking-wider text-slate-500">AI 置信�?/span>
              <span className={`text-xs sm:text-sm font-mono font-bold ${config.textColor}`}>{confidence}%</span>
            </div>
            <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
              <div
                animate={{ width: `${confidence}%` }}
                transition={{ duration: 1, delay: 0.3 }}
                className={`h-full ${config.accentColor}`}
              />
            </div>
          </div>

          {/* Summary */}
          {summary && (
            <div className={`p-2.5 sm:p-3 rounded-lg ${config.bgTint} border border-white/5 mb-3 sm:mb-4`}>
              <p className="text-slate-300 text-xs sm:text-sm leading-relaxed">{summary}</p>
            </div>
          )}

          {/* Risk Level - 移动端优�?*/}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-2.5 sm:pt-3 border-t border-white/[0.06]">
            <div className="flex items-center gap-1.5 sm:gap-2">
              <Shield className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-slate-500" />
              <span className="text-[9px] sm:text-[10px] uppercase tracking-wider text-slate-500">风险</span>
              <div className={`px-1.5 sm:px-2 py-0.5 rounded text-[10px] sm:text-xs font-medium ${
                riskLevel === 'low' 
                  ? 'bg-emerald-500/10 text-emerald-400' 
                  : riskLevel === 'medium' 
                  ? 'bg-amber-500/10 text-amber-400' 
                  : 'bg-rose-500/10 text-rose-400'
              }`}>
                {riskLevel === 'low' ? '�? : riskLevel === 'medium' ? '�? : '�?}
              </div>
              {/* Risk Dots */}
              <div className="flex items-center gap-0.5">
                {[1, 2, 3].map((level) => (
                  <div
                    key={level}
                    className={`w-1 h-1 sm:w-1.5 sm:h-1.5 rounded-full transition-colors ${
                      level <= (riskLevel === 'low' ? 1 : riskLevel === 'medium' ? 2 : 3)
                        ? riskLevel === 'low' ? 'bg-emerald-500' : riskLevel === 'medium' ? 'bg-amber-500' : 'bg-rose-500'
                        : 'bg-slate-700'
                    }`}
                  />
                ))}
              </div>
            </div>
            
            <div className="flex items-center gap-1 text-[9px] sm:text-[10px] text-slate-600">
              <AlertCircle className="w-2.5 h-2.5 sm:w-3 sm:h-3" />
              <span>仅供参�?/span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
