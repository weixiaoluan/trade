"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Bot, FileText, AlertCircle, ExternalLink } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { StockCard } from "@/components/ui/StockCard";
import { QuantDashboardCard } from "@/components/ui/QuantDashboardCard";
import { AIRecommendationCard } from "@/components/ui/AIRecommendationCard";
import { PredictionTimeline } from "@/components/ui/PredictionTimeline";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export default function ReportPage() {
  const router = useRouter();
  const params = useParams();
  const symbol = params.symbol as string;

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

  // 下载报告
  const handleDownloadReport = () => {
    const result = parseReportData(report);
    const reportHtml = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${result.ticker} - ${result.name} 分析报告</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #e2e8f0; min-height: 100vh; padding: 40px 20px; line-height: 1.6; }
    .container { max-width: 900px; margin: 0 auto; }
    .header { text-align: center; margin-bottom: 40px; padding: 30px; background: rgba(30, 41, 59, 0.8); border-radius: 16px; border: 1px solid rgba(56, 189, 248, 0.2); }
    .header h1 { font-size: 28px; color: #38bdf8; margin-bottom: 8px; }
    .header .subtitle { color: #94a3b8; font-size: 14px; }
    .card { background: rgba(30, 41, 59, 0.6); border-radius: 12px; padding: 24px; margin-bottom: 20px; border: 1px solid rgba(71, 85, 105, 0.5); }
    .card h2 { color: #38bdf8; font-size: 18px; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid rgba(71, 85, 105, 0.5); }
    .footer { text-align: center; margin-top: 40px; padding: 20px; color: #64748b; font-size: 12px; }
    strong { color: #f8fafc; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>${result.ticker} - ${result.name}</h1>
      <p class="subtitle">生成时间: ${new Date().toLocaleString('zh-CN')} | AI 多维度分析报告</p>
    </div>
    <div class="card">
      <h2>📊 详细分析报告</h2>
      ${result.report.replace(/\n/g, '<br>')}
    </div>
    <div class="footer">
      <p>ℹ️ 本报告由 AI 多智能体系统生成，仅供参考，不构成投资建议。</p>
    </div>
  </div>
</body>
</html>`;
    const blob = new Blob([reportHtml], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${result.ticker}_分析报告.html`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <main className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-24 w-24 border-b-4 border-indigo-500 mx-auto"></div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-rose-400 mx-auto mb-4" />
          <p className="text-slate-300 mb-4">{error}</p>
          <button
            onClick={() => router.push("/dashboard")}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500"
          >
            返回首页
          </button>
        </div>
      </main>
    );
  }

  const result = parseReportData(report);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen bg-[#020617]"
    >
      {/* Sticky Header - 完全按照原始代码 */}
      <div className="sticky top-0 z-40 bg-[#020617]/90 backdrop-blur-md border-b border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <button
              onClick={() => router.push("/dashboard")}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.08] hover:bg-white/[0.06] text-sm text-slate-400 hover:text-slate-200 transition-all"
            >
              <Bot className="w-4 h-4" />
              <span>返回</span>
            </button>
            
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase tracking-wider text-slate-600">标的</span>
                <span className="font-mono font-bold text-indigo-400">{result.ticker}</span>
              </div>
              <div className="w-px h-4 bg-white/10" />
              <span className="text-sm text-slate-400 max-w-[200px] truncate">{result.name}</span>
              {typeof result.quantScore === 'number' && (
                <div
                  className={`ml-2 px-2.5 py-1 rounded-full border text-[10px] flex items-center gap-1 whitespace-nowrap
                    ${result.quantScore >= 80
                      ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                      : result.quantScore >= 60
                      ? 'bg-sky-500/10 text-sky-300 border-sky-500/30'
                      : result.quantScore <= 40
                      ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                      : 'bg-slate-900/80 text-slate-300 border-slate-600/60'
                    }`}
                >
                  <span className="font-mono text-[11px]">{result.quantScore.toFixed(1)}</span>
                  <span className="opacity-70">分</span>
                  <span className="w-px h-3 bg-white/10 mx-1" />
                  <span className="truncate max-w-[80px]">
                    {result.marketRegime === 'trending' ? '趋势市'
                      : result.marketRegime === 'ranging' ? '震荡市'
                      : result.marketRegime === 'squeeze' ? '窄幅整理'
                      : '待判定'}
                  </span>
                  <span className="hidden sm:inline text-[9px] opacity-60">
                    · {result.volatilityState === 'low' ? '低波动'
                      : result.volatilityState === 'high' ? '高波动'
                      : '中等波动'}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content - Bento Grid Layout 完全按照原始代码 */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Stock Overview Card */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:col-span-1"
          >
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
          </motion.div>

          {/* AI Analysis Panel */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="lg:col-span-2 flex flex-col gap-4"
          >
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
              <div className="glass-card rounded-xl border border-white/[0.06] p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="badge-tech text-indigo-300 border-indigo-500/30 bg-indigo-500/10 text-[10px]">
                      QUANT STRATEGY SIGNALS
                    </span>
                    <span className="text-xs text-slate-500">量化策略信号（核心打分依据）</span>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1.5">
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
                        className={`px-2 py-0.5 rounded-full text-[11px] border font-mono ${tone}`}
                      >
                        {s}
                      </span>
                    );
                  })}
                </div>
              </div>
            )}
          </motion.div>

          {/* Prediction Timeline - Full Width */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="lg:col-span-3"
          >
            <div className="glass-card rounded-xl p-5 border border-white/[0.06]">
              <PredictionTimeline
                predictions={result.predictions}
                onHoverHorizon={setActiveHorizon}
              />
            </div>
          </motion.div>

          {/* Analysis Report */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
            className="lg:col-span-3"
            id="analysis-report-section"
          >
            <div className="glass-card rounded-xl border border-white/[0.06] overflow-hidden">
              {/* Report Header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06] bg-white/[0.02]">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                    <FileText className="w-4 h-4 text-indigo-400" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white tracking-wide">智能研报</h3>
                    <span className="text-[10px] uppercase tracking-wider text-slate-500">AI QUANTITATIVE ANALYSIS</span>
                  </div>
                </div>
                <button
                  onClick={handleDownloadReport}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 hover:bg-indigo-500/20 text-xs font-medium text-indigo-400 transition-all"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  下载报告
                </button>
              </div>

              {/* Report Content */}
              <div className="p-8">
                <div 
                  className="markdown-content prose prose-invert prose-sm max-w-none overflow-y-auto scrollbar-thin" 
                  style={{ maxHeight: 'calc(100vh - 400px)', minHeight: '450px' }}
                >
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {result.report || '报告生成中...'}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
}
