"use client";

import { useState, useEffect, memo } from "react";
import { useRouter, useParams } from "next/navigation";
import dynamic from "next/dynamic";
import { FileText, AlertCircle, ArrowLeft } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { API_BASE } from "@/lib/config";

// 动态导入重型组件，减少首屏加载
const StockCard = dynamic(() => import("@/components/ui/StockCard").then(m => ({ default: m.StockCard })), { ssr: false });
const QuantDashboardCard = dynamic(() => import("@/components/ui/QuantDashboardCard").then(m => ({ default: m.QuantDashboardCard })), { ssr: false });
const AIRecommendationCard = dynamic(() => import("@/components/ui/AIRecommendationCard").then(m => ({ default: m.AIRecommendationCard })), { ssr: false });
const PredictionTimeline = dynamic(() => import("@/components/ui/PredictionTimeline").then(m => ({ default: m.PredictionTimeline })), { ssr: false });

// 骨架屏组件
const SkeletonCard = memo(({ className = "" }: { className?: string }) => (
  <div className={`glass-card rounded-xl border border-white/[0.06] p-4 sm:p-5 ${className}`}>
    <div className="skeleton h-4 w-24 rounded mb-3"></div>
    <div className="skeleton h-8 w-32 rounded mb-2"></div>
    <div className="skeleton h-3 w-full rounded mb-2"></div>
    <div className="skeleton h-3 w-3/4 rounded"></div>
  </div>
));

const ReportSkeleton = memo(() => (
  <div className="min-h-screen bg-[#020617]">
    <div className="sticky top-0 z-40 bg-[#020617]/90 backdrop-blur-md border-b border-white/[0.06]">
      <div className="max-w-7xl mx-auto px-3 sm:px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="skeleton h-8 w-20 rounded-lg"></div>
          <div className="flex items-center gap-3">
            <div className="skeleton h-6 w-24 rounded"></div>
            <div className="skeleton h-6 w-32 rounded"></div>
          </div>
        </div>
      </div>
    </div>
    <div className="max-w-7xl mx-auto px-3 sm:px-4 py-4 sm:py-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 sm:gap-4">
        <SkeletonCard className="lg:col-span-1 h-48" />
        <div className="lg:col-span-2 space-y-3 sm:space-y-4">
          <SkeletonCard className="h-32" />
          <SkeletonCard className="h-24" />
        </div>
        <SkeletonCard className="lg:col-span-3 h-40" />
        <div className="lg:col-span-3 glass-card rounded-xl border border-white/[0.06] p-4 sm:p-6">
          <div className="skeleton h-6 w-32 rounded mb-4"></div>
          <div className="space-y-3">
            <div className="skeleton h-4 w-full rounded"></div>
            <div className="skeleton h-4 w-5/6 rounded"></div>
            <div className="skeleton h-4 w-4/5 rounded"></div>
            <div className="skeleton h-4 w-full rounded"></div>
            <div className="skeleton h-4 w-3/4 rounded"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
));

export default function ReportPage() {
  const router = useRouter();
  const params = useParams();
  // 解码URL中的symbol参数，处理特殊字符如 SPAX.PVT
  const symbol = decodeURIComponent(params.symbol as string);

  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeHorizon, setActiveHorizon] = useState<'short' | 'mid' | 'long' | null>(null);

  const getToken = () => localStorage.getItem("token");

  useEffect(() => {
    const fetchReport = async () => {
      const token = getToken();
      if (!token) {
        router.push("/login");
        return;
      }

      try {
        const response = await fetch(
          `${API_BASE}/api/reports/${encodeURIComponent(symbol)}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );

        if (!response.ok) {
          if (response.status === 401) {
            router.push("/login");
            return;
          }
          throw new Error("报告不存在或已被删除");
        }

        const data = await response.json();
        setReport(data.report);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (symbol) fetchReport();
  }, [symbol, router]);

  // 解析报告数据 - 完全按照原始 page.tsx 的逻辑
  const parseReportData = (report: any) => {
    const data = report?.data || {};
    const stockInfo = data.stock_info || {};
    const quantAnalysis = data.quant_analysis || {};
    const indicatorOverview = data.indicator_overview || {};
    const priceInfo = stockInfo.price_info || {};
    const basicInfo = stockInfo.basic_info || {};
    const valuation = stockInfo.valuation || {};
    const volumeInfo = stockInfo.volume_info || {};

    // 资产类型
    const assetType = basicInfo.quote_type || 'EQUITY';

    // 市值/规模 - 优先使用格式化字符串
    const marketCapDisplay = valuation.market_cap_str || formatMarketCap(valuation.market_cap);

    // 成交额
    const volumeDisplay = volumeInfo.amount_str;

    // 净值(ETF)
    const navValue = valuation.nav || stockInfo.etf_specific?.nav;

    // 价格数据
    const currentPrice = priceInfo.current_price || 0;
    const prevClose = priceInfo.previous_close || 0;

    // 涨跌幅
    let changePercent = priceInfo.change_pct || 0;
    let priceChange = 0;
    if (prevClose > 0 && currentPrice > 0) {
      priceChange = currentPrice - prevClose;
      if (!priceInfo.change_pct) {
        changePercent = ((currentPrice - prevClose) / prevClose) * 100;
      }
    }

    // 量化分析结果
    const rawReco = (quantAnalysis.recommendation || 'hold') as string;
    const validRecos = ['strong_buy', 'buy', 'hold', 'sell', 'strong_sell'];
    const finalReco = validRecos.includes(rawReco) ? rawReco : 'hold';

    const quantScore = typeof quantAnalysis.score === 'number' ? quantAnalysis.score : undefined;
    const marketRegime = quantAnalysis.market_regime as string | undefined;
    const volatilityState = (quantAnalysis.volatility_state || 'medium') as string;
    const quantConfidence = quantAnalysis.confidence as 'high' | 'medium' | 'low' | undefined;

    const adxValue = typeof indicatorOverview.adx_value === 'number' ? indicatorOverview.adx_value : undefined;
    const atrPct = typeof indicatorOverview.atr_pct === 'number' ? indicatorOverview.atr_pct : undefined;
    const adxTrendStrength = indicatorOverview.adx_trend_strength as string | undefined;

    const summaryText = data.ai_summary || '基于量化评分和多维技术指标，系统已综合评估该标的当前趋势与风险水平，请参考下方详细报告。';

    const signalDetails = Array.isArray(data.signal_details) ? data.signal_details : [];

    return {
      ticker: data.ticker || symbol,
      name: basicInfo.name || symbol,
      price: currentPrice,
      change: priceChange,
      changePercent: changePercent,
      high52w: priceInfo['52_week_high'] || 0,
      low52w: priceInfo['52_week_low'] || 0,
      marketCap: marketCapDisplay,
      pe: valuation.pe_ratio || 0,
      recommendation: finalReco,
      summary: summaryText,
      report: data.report || '',
      predictions: data.predictions || [],
      assetType: assetType,
      nav: navValue,
      volume: volumeDisplay,
      quantScore,
      marketRegime,
      volatilityState,
      quantConfidence,
      adxValue,
      adxTrendStrength,
      atrPct,
      signalDetails,
    };
  };

  const formatMarketCap = (value: number) => {
    if (!value) return 'N/A';
    if (value >= 1e12) return `¥${(value / 1e12).toFixed(2)}万亿`;
    if (value >= 1e8) return `¥${(value / 1e8).toFixed(2)}亿`;
    if (value >= 1e4) return `¥${(value / 1e4).toFixed(2)}万`;
    return `¥${value.toLocaleString()}`;
  };

  if (loading) {
    return <ReportSkeleton />;
  }

  if (error) {
    return (
      <main className="min-h-screen bg-[#020617] flex items-center justify-center px-4">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 sm:w-16 sm:h-16 text-rose-400 mx-auto mb-4" />
          <p className="text-slate-300 mb-4 text-sm sm:text-base">{error}</p>
          <button
            onClick={() => router.push("/dashboard")}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 text-sm sm:text-base"
          >
            返回首页
          </button>
        </div>
      </main>
    );
  }

  const result = parseReportData(report);

  return (
    <div className="min-h-screen bg-[#020617] animate-fadeIn">
      {/* Sticky Header - 移动端优化 */}
      <div className="sticky top-0 z-40 bg-[#020617]/90 backdrop-blur-md border-b border-white/[0.06] safe-area-top">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 py-2 sm:py-3">
          <div className="flex items-center justify-between gap-2">
            <button
              onClick={() => router.push("/dashboard")}
              className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.08] hover:bg-white/[0.06] text-xs sm:text-sm text-slate-400 hover:text-slate-200 transition-all flex-shrink-0"
            >
              <ArrowLeft className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              <span className="hidden sm:inline">返回</span>
            </button>
            
            <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1 justify-end">
              <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
                <span className="font-mono font-bold text-indigo-400 text-sm sm:text-base">{result.ticker}</span>
                <span className="text-xs sm:text-sm text-slate-400 truncate max-w-[100px] sm:max-w-[200px]">{result.name}</span>
              </div>
              {typeof result.quantScore === 'number' && (
                <div
                  className={`px-2 py-1 rounded-full border text-[9px] sm:text-[10px] flex items-center gap-1 whitespace-nowrap flex-shrink-0
                    ${result.quantScore >= 80
                      ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                      : result.quantScore >= 60
                      ? 'bg-sky-500/10 text-sky-300 border-sky-500/30'
                      : result.quantScore <= 40
                      ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                      : 'bg-slate-900/80 text-slate-300 border-slate-600/60'
                    }`}
                >
                  <span className="font-mono text-[10px] sm:text-[11px]">{result.quantScore.toFixed(1)}</span>
                  <span className="opacity-70">分</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content - 移动端优化的 Bento Grid */}
      <div className="max-w-7xl mx-auto px-3 sm:px-4 py-4 sm:py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 sm:gap-4">
          {/* Stock Overview Card */}
          <div className="lg:col-span-1 animate-slideUp" style={{ animationDelay: '0.1s' }}>
            <StockCard
              ticker={result.ticker}
              name={result.name}
              price={result.price}
              change={result.change}
              changePercent={result.changePercent}
              high52w={result.high52w}
              low52w={result.low52w}
              marketCap={result.marketCap}
              pe={result.pe}
              assetType={result.assetType}
              nav={result.nav}
              volume={result.volume}
            />
          </div>

          {/* AI Analysis Panel */}
          <div className="lg:col-span-2 flex flex-col gap-3 sm:gap-4 animate-slideUp" style={{ animationDelay: '0.15s' }}>
            <AIRecommendationCard
              recommendation={result.recommendation as any}
              summary={result.summary}
              confidence={
                result.quantConfidence === 'high' ? 85
                  : result.quantConfidence === 'low' ? 60
                  : 75
              }
              riskLevel={
                result.volatilityState === 'low' ? 'low'
                  : result.volatilityState === 'high' ? 'high'
                  : 'medium'
              }
            />

            <QuantDashboardCard
              score={result.quantScore}
              marketRegime={result.marketRegime}
              volatilityState={result.volatilityState}
              adxValue={result.adxValue}
              adxTrendStrength={result.adxTrendStrength}
              atrPct={result.atrPct}
              activeHorizon={activeHorizon || undefined}
            />

            {result.signalDetails && result.signalDetails.length > 0 && (
              <div className="glass-card rounded-xl border border-white/[0.06] p-3 sm:p-4">
                <div className="flex items-center justify-between mb-2 sm:mb-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="badge-tech text-indigo-300 border-indigo-500/30 bg-indigo-500/10 text-[9px] sm:text-[10px]">
                      QUANT SIGNALS
                    </span>
                    <span className="text-[10px] sm:text-xs text-slate-500">量化策略信号</span>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1 sm:gap-1.5">
                  {result.signalDetails.slice(0, 12).map((signal: string, idx: number) => {
                    const s = signal as string;
                    const bullish = /多头|金叉|支撑|超卖|放量确认上涨|资金流入/.test(s);
                    const bearish = /空头|死叉|压力|超买|放量确认下跌|资金流出/.test(s);
                    const tone = bullish
                      ? 'border-rose-500/40 bg-rose-500/10 text-rose-300'
                      : bearish
                      ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                      : 'border-slate-600/60 bg-slate-900/60 text-slate-300';
                    return (
                      <span
                        key={idx}
                        className={`px-1.5 sm:px-2 py-0.5 rounded-full text-[10px] sm:text-[11px] border font-mono ${tone}`}
                      >
                        {s}
                      </span>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Analysis Report */}
          <div
            className="lg:col-span-3 animate-slideUp"
            style={{ animationDelay: '0.25s' }}
            id="analysis-report-section"
          >
            <div className="glass-card rounded-xl border border-white/[0.06] overflow-hidden">
              {/* Report Header */}
              <div className="flex flex-col items-center justify-center px-3 sm:px-5 py-3 sm:py-4 border-b border-white/[0.06] bg-white/[0.02] gap-3">
                <div className="flex items-center gap-2 sm:gap-3">
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                    <FileText className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-indigo-400" />
                  </div>
                  <div>
                    <h3 className="text-xs sm:text-sm font-bold text-white tracking-wide">技术研报</h3>
                    <span className="text-[9px] sm:text-[10px] uppercase tracking-wider text-slate-500 hidden sm:block">AI QUANTITATIVE ANALYSIS</span>
                  </div>
                </div>
                {/* 免责声明 - 居中显示 */}
                <div className="text-[10px] sm:text-xs text-amber-400/80 leading-relaxed text-center max-w-2xl">
                  <span className="font-medium">⚠️ 免责声明：</span>
                  <span className="text-slate-400">本报告由AI技术生成，数据来源于公开市场信息，仅供个人技术分析参考与学习交流之用。报告内容不构成任何具体的投资操作建议，使用者应独立判断并对投资决策负全部责任。</span>
                  <span className="text-rose-400 font-medium"> 🚫 严禁转发、截图保存或分享本页面任何内容。</span>
                </div>
              </div>

              {/* Report Content */}
              <div className="p-4 sm:p-6 md:p-8">
                <div 
                  className="markdown-content prose prose-invert prose-sm max-w-none"
                >
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {result.report || '报告生成中...'}
                  </ReactMarkdown>
                </div>
              </div>
              
              {/* 免责声明 */}
              <div className="px-4 sm:px-6 md:px-8 pb-4 sm:pb-6 md:pb-8 pt-4 border-t border-white/[0.06] bg-amber-500/5">
                <div className="text-xs sm:text-sm text-amber-300/80 text-center space-y-2">
                  <p className="font-medium">⚠️ 重要声明</p>
                  <p className="text-slate-500 leading-relaxed">
                    本工具为个人学习研究用途，所有分析内容均基于公开数据和技术指标自动生成，仅供学习交流参考。
                    本工具不具备证券投资咨询资质，所有内容不构成任何投资建议、推荐或指导。
                    投资有风险，任何投资决策请咨询持牌专业人士并自行承担风险。
                  </p>
                  <p className="text-rose-400 font-medium">
                    🚫 严禁转发、截图保存或分享本网站上的任何内容
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
