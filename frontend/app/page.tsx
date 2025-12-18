'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, BarChart3, FileText, TrendingUp, AlertCircle, ChevronDown, ExternalLink } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { TypewriterText } from '@/components/ui/TypewriterText';
import { SearchBox } from '@/components/ui/SearchBox';
import { LoadingState } from '@/components/ui/LoadingState';
import { StockCard } from '@/components/ui/StockCard';
import { PredictionTimeline } from '@/components/ui/PredictionTimeline';
import { AIRecommendationCard } from '@/components/ui/AIRecommendationCard';
import { QuantDashboardCard } from '@/components/ui/QuantDashboardCard';
import { MultiPeriodPerformance } from '@/components/ui/MultiPeriodPerformance';

// Types
interface PredictionItem {
  period: string;
  label: string;
  trend: 'bullish' | 'bearish' | 'neutral';
  confidence: 'high' | 'medium' | 'low';
  target: string;
}

interface AnalysisResult {
  ticker: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  high52w: number;
  low52w: number;
  marketCap: string;
  pe: number;
  recommendation: 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell';
  summary: string;
  report: string;
  predictions?: PredictionItem[];
  // Enhanced fields
  assetType?: string;
  nav?: number;
  volume?: string;
  quantScore?: number;
  marketRegime?: string;
  volatilityState?: string;
  quantConfidence?: 'high' | 'medium' | 'low';
  adxValue?: number;
  adxTrendStrength?: string;
  atrPct?: number;
  signalDetails?: string[];
  periodReturns?: { period: string; label: string; return: number; }[];
}

type ViewState = 'hero' | 'loading' | 'dashboard';

export default function Home() {
  const [viewState, setViewState] = useState<ViewState>('hero');
  const [ticker, setTicker] = useState('');
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [activeHorizon, setActiveHorizon] = useState<'short' | 'mid' | 'long' | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'technical' | 'fundamental' | 'report'>('overview');
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  const [errorDialog, setErrorDialog] = useState<{
    open: boolean;
    title?: string;
    message?: string;
  }>({ open: false });

  const showErrorDialog = (title: string, message: string) => {
    setErrorDialog({ open: true, title, message });
  };

  const handleSearch = async (query: string) => {
    setTicker(query);
    setViewState('loading');
    setProgress(0);
    
    try {
      // Start analysis
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: query }),
      });
      
      const data = await response.json();
      const taskId = data.task_id;

      // Poll for status
      const pollStatus = async () => {
        const statusRes = await fetch(`/api/task/${taskId}`);
        
        // 处理 404 或其他错误状态
        if (!statusRes.ok) {
          console.error('Task fetch failed:', statusRes.status);
          showErrorDialog('任务状态获取失败', '任务状态获取失败，请刷新页面重试');
          setViewState('hero');
          return;
        }
        
        const status = await statusRes.json();
        
        // 确保返回的状态对象有效
        if (!status || !status.status) {
          console.error('Invalid status response:', status);
          showErrorDialog('服务响应异常', '服务响应异常，请刷新页面重试');
          setViewState('hero');
          return;
        }
        
        setProgress(status.progress || 0);
        setCurrentStep(status.current_step || '处理中');

        if (status.status === 'completed') {
          // 解析结果获取标准化的 ticker
          let normalizedTicker = query;
          try {
            const resultPreview = JSON.parse(status.result || '{}');
            // 从分析结果中获取标准化的 ticker（后端已转换）
            if (resultPreview.ticker) {
              normalizedTicker = resultPreview.ticker;
            }
          } catch {}
          
          // Fetch stock data for display - 使用标准化的 ticker
          const quoteRes = await fetch(`/api/stock/${normalizedTicker}/quote`);
          const quoteData = await quoteRes.json();
          
          const quote = quoteData.quote?.summary || {};
          const info = quoteData.info || {};
          
          // 解析结果（可能是 JSON 字符串或纯文本）
          let report = '';
          let predictions: PredictionItem[] = [];
          let quantAnalysis: any = null;
          let aiSummary = '';
          let indicatorOverview: any = null;
          let signalDetails: string[] | null = null;
          
          try {
            const resultData = JSON.parse(status.result || '{}');
            report = resultData.report || status.result || '';
            predictions = resultData.predictions || [];
            quantAnalysis = resultData.quant_analysis || null;
            const trendAnalysis = resultData.trend_analysis || null;
            aiSummary = resultData.ai_summary || '';
            indicatorOverview = resultData.indicator_overview || null;
            signalDetails = Array.isArray(resultData.signal_details)
              ? (resultData.signal_details as string[])
              : null;
          } catch {
            report = status.result || '';
          }
          
          // 定义 trendAnalysis 以便后续使用
          const trendAnalysis = quantAnalysis?.trend_analysis || null;
          
          // 获取资产类型
          const assetType = info.basic_info?.quote_type || 'EQUITY';
          
          // 获取市值/规模 - 优先使用格式化字符串
          const marketCapDisplay = info.valuation?.market_cap_str || formatMarketCap(info.valuation?.market_cap);
          
          // 获取成交额
          const volumeDisplay = info.volume_info?.amount_str;
          
          // 获取净值(ETF/基金) - 多来源fallback
          const navValue = info.valuation?.nav || info.etf_specific?.nav || info.fund_specific?.nav || info.fund_specific?.estimated_nav;
          
          // 获取价格数据 - 优先使用 info 数据（更准确）
          const currentPrice = info.price_info?.current_price || quote.latest_price || 0;
          const prevClose = info.price_info?.previous_close || 0;
          
          // 计算涨跌幅 - 优先使用 info 中的 change_pct
          let changePercent = info.price_info?.change_pct || 0;
          let priceChange = 0;
          
          if (prevClose > 0 && currentPrice > 0) {
            priceChange = currentPrice - prevClose;
            // 如果 info 没有 change_pct，则计算
            if (!info.price_info?.change_pct) {
              changePercent = ((currentPrice - prevClose) / prevClose) * 100;
            }
          }
          
          // 使用量化分析结果驱动前端 AI 推荐卡片
          const rawReco = (quantAnalysis?.recommendation || 'hold') as string;
          const validRecos = ['strong_buy', 'buy', 'hold', 'sell', 'strong_sell'];
          const finalReco = (validRecos.includes(rawReco) ? rawReco : 'hold') as AnalysisResult['recommendation'];

          const quantScore = typeof quantAnalysis?.score === 'number' ? quantAnalysis.score : undefined;
          const marketRegime = quantAnalysis?.market_regime as string | undefined;
          const volatilityState = (quantAnalysis?.volatility_state || 'medium') as string;
          const quantConfidence = (quantAnalysis?.confidence || undefined) as 'high' | 'medium' | 'low' | undefined;

          const adxValue = typeof indicatorOverview?.adx_value === 'number' ? indicatorOverview.adx_value : undefined;
          const atrPct = typeof indicatorOverview?.atr_pct === 'number' ? indicatorOverview.atr_pct : undefined;
          const adxTrendStrength = indicatorOverview?.adx_trend_strength as string | undefined;

          const summaryText =
            aiSummary ||
            '基于量化评分和多维技术指标，系统已综合评估该标的当前趋势与风险水平，请参考下方详细报告。';
          
          // 解析多周期表现数据
          const periodReturnsData = [];
          // 尝试从 trend_analysis 或 quant_analysis 中获取 period_returns
          let periodReturnsObj: any = {};
          if (quantAnalysis?.period_returns) {
            periodReturnsObj = quantAnalysis.period_returns;
          } else if (trendAnalysis?.period_returns) {
            periodReturnsObj = trendAnalysis.period_returns;
          }
          
          const periodMapping = [
            { key: '1日', label: '周期 | 涨跌幅', period: '1d' },
            { key: '5日', label: '5日', period: '5d' },
            { key: '10日', label: '10日', period: '10d' },
            { key: '20日', label: '20日', period: '20d' },
            { key: '60日', label: '60日', period: '60d' },
            { key: '120日', label: '120日', period: '120d' },
            { key: '250日', label: '250日', period: '250d' },
          ];
          
          for (const mapping of periodMapping) {
            const value = periodReturnsObj[mapping.key];
            if (typeof value === 'number') {
              periodReturnsData.push({
                period: mapping.period,
                label: mapping.label,
                return: value
              });
            }
          }
          
          setResult({
            ticker: query,
            name: info.basic_info?.name || query,
            price: currentPrice,
            change: priceChange,
            changePercent: changePercent,
            high52w: info.price_info?.['52_week_high'] || 0,
            low52w: info.price_info?.['52_week_low'] || 0,
            marketCap: marketCapDisplay,
            pe: info.valuation?.pe_ratio || 0,
            recommendation: finalReco,
            summary: summaryText,
            report: report,
            predictions: predictions,
            // Enhanced fields
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
            signalDetails: signalDetails || undefined,
            periodReturns: periodReturnsData.length > 0 ? periodReturnsData : undefined,
          });
          
          setViewState('dashboard');
        } else if (status.status === 'failed') {
          const errorMsg = status.error || '未知错误';
          showErrorDialog(
            '分析失败',
            `LLM 请求超时或服务异常。\n\n${errorMsg}\n\n请检查：\n1. 证券代码是否正确\n2. 中国A股 / ETF / 基金可直接输入6位数字代码（如：600519、159941、000001），系统会自动识别市场\n3. 若多次出现超时，请稍后重试或更换网络环境`
          );
          setViewState('hero');
        } else {
          setTimeout(pollStatus, 1000);
        }
      };

      pollStatus();
    } catch (error) {
      console.error('Analysis error:', error);
      showErrorDialog('分析出错', '分析过程中出现异常，请稍后重试');
      setViewState('hero');
    }
  };

  const formatMarketCap = (value: number) => {
    if (!value) return 'N/A';
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    return `$${value.toLocaleString()}`;
  };

  return (
    <main className="min-h-screen">
      {/* 去掉导航栏，改为简洁的返回按钮 */}

      {/* Hero Section */}
      <AnimatePresence mode="wait">
        {viewState === 'hero' && (
          <motion.div
            key="hero"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, y: -30 }}
            className="min-h-screen flex flex-col items-center justify-center px-4 relative overflow-hidden"
          >
            {/* Subtle Background Gradient Mesh */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
              <div className="absolute top-1/4 -left-1/4 w-[600px] h-[600px] bg-indigo-500/10 rounded-full blur-[120px]" />
              <div className="absolute bottom-1/4 -right-1/4 w-[500px] h-[500px] bg-violet-500/10 rounded-full blur-[100px]" />
            </div>

            {/* Content */}
            <div className="relative z-10 flex flex-col items-center">
              {/* Logo */}
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ type: 'spring', delay: 0.1, duration: 0.6 }}
                className="mb-8"
              >
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 p-[1px]">
                  <div className="w-full h-full rounded-2xl bg-[#020617] flex items-center justify-center">
                    <Bot className="w-8 h-8 text-indigo-400" />
                  </div>
                </div>
              </motion.div>

              {/* Title */}
              <motion.h1
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="text-3xl md:text-5xl font-bold text-center mb-3 tracking-tight"
              >
                <span className="bg-gradient-to-r from-slate-100 via-indigo-200 to-slate-100 bg-clip-text text-transparent">
                  证券AI智能分析引擎
                </span>
              </motion.h1>

              <motion.p
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="text-slate-500 text-center mb-10 max-w-md text-sm"
              >
                基于 Multi-Agent AI 的量化分析系统，覆盖全球股票、ETF、基金
              </motion.p>

              {/* Search Box */}
              <motion.div
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="w-full max-w-2xl"
              >
                <SearchBox onSearch={handleSearch} />
              </motion.div>

              {/* Features */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6 }}
                className="flex flex-wrap justify-center gap-6 mt-16"
              >
                {[
                  { icon: BarChart3, label: '技术分析', color: 'text-indigo-400' },
                  { icon: FileText, label: '基本面', color: 'text-violet-400' },
                  { icon: TrendingUp, label: '多周期预测', color: 'text-emerald-400' },
                  { icon: AlertCircle, label: '风险评估', color: 'text-amber-400' },
                ].map((feature) => (
                  <div key={feature.label} className="flex items-center gap-2 text-xs text-slate-500">
                    <feature.icon className={`w-3.5 h-3.5 ${feature.color}`} />
                    <span className="uppercase tracking-wider">{feature.label}</span>
                  </div>
                ))}
              </motion.div>
            </div>
          </motion.div>
        )}

        {/* Loading State */}
        {viewState === 'loading' && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="min-h-screen flex items-center justify-center px-4"
          >
            <LoadingState progress={progress} currentStep={currentStep} />
          </motion.div>
        )}

        {/* Dashboard */}
        {viewState === 'dashboard' && result && (
          <motion.div
            key="dashboard"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="min-h-screen bg-[#020617]"
          >
            {/* Sticky Header - 响应式 */}
            <div className="sticky top-0 z-40 bg-[#020617]/90 backdrop-blur-md border-b border-white/[0.06]">
              <div className="max-w-7xl mx-auto px-2 sm:px-4 py-2 sm:py-3">
                <div className="flex items-center justify-between gap-2">
                  <button
                    onClick={() => {
                      setViewState('hero');
                      setResult(null);
                    }}
                    className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.08] hover:bg-white/[0.06] text-xs sm:text-sm text-slate-400 hover:text-slate-200 transition-all shrink-0"
                  >
                    <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                    <span className="hidden sm:inline">新建分析</span>
                    <span className="sm:hidden">新建</span>
                  </button>
                  
                  <div className="flex items-center gap-2 sm:gap-3 min-w-0 overflow-hidden">
                    <div className="flex items-center gap-1 sm:gap-2 shrink-0">
                      <span className="hidden sm:inline text-[10px] uppercase tracking-wider text-slate-600">标的</span>
                      <span className="font-mono font-bold text-indigo-400 text-sm sm:text-base">{result.ticker}</span>
                    </div>
                    <div className="hidden sm:block w-px h-4 bg-white/10" />
                    <span className="hidden md:block text-sm text-slate-400 max-w-[200px] truncate">{result.name}</span>
                    {typeof result.quantScore === 'number' && (
                      <div
                        className={`hidden sm:flex ml-1 sm:ml-2 px-1.5 sm:px-2.5 py-0.5 sm:py-1 rounded-full border text-[9px] sm:text-[10px] items-center gap-1 whitespace-nowrap
                          ${
                            result.quantScore >= 80
                              ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                              : result.quantScore >= 60
                              ? 'bg-sky-500/10 text-sky-300 border-sky-500/30'
                              : result.quantScore <= 40
                              ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                              : 'bg-slate-900/80 text-slate-300 border-slate-600/60'
                          }
                        `}
                      >
                        <span className="font-mono text-[10px] sm:text-[11px]">{result.quantScore.toFixed(1)}</span>
                        <span className="opacity-70">分</span>
                        <span className="hidden md:inline w-px h-3 bg-white/10 mx-1" />
                        <span className="hidden md:inline truncate max-w-[80px]">
                          {result.marketRegime === 'trending'
                            ? '趋势市'
                            : result.marketRegime === 'ranging'
                            ? '震荡市'
                            : result.marketRegime === 'squeeze'
                            ? '窄幅整理'
                            : '待判定'}
                        </span>
                        <span className="hidden lg:inline text-[9px] opacity-60">
                          ·
                          {result.volatilityState === 'low'
                            ? '低波动'
                            : result.volatilityState === 'high'
                            ? '高波动'
                            : '中等波动'}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Main Content */}
            <div className="max-w-7xl mx-auto px-2 sm:px-4 py-4 sm:py-6">
              {/* Bento Grid Layout - 响应式网格 */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
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

                {/* AI Analysis Panel: Recommendation + Quant Dashboard + Signals */}
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.15 }}
                  className="lg:col-span-2 flex flex-col gap-4"
                >
                  <AIRecommendationCard
                    recommendation={result.recommendation}
                    summary={result.summary}
                    confidence={
                      result.quantConfidence === 'high'
                        ? 85
                        : result.quantConfidence === 'low'
                        ? 60
                        : 75
                    }
                    riskLevel={
                      result.volatilityState === 'low'
                        ? 'low'
                        : result.volatilityState === 'high'
                        ? 'high'
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
                            量化策略信号
                          </span>
                          <span className="text-xs text-slate-500">量化策略信号（核心打分依据）</span>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {result.signalDetails.slice(0, 24).map((signal, idx) => {
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

                {/* Multi-Period Performance - 1 column */}
                {result.periodReturns && result.periodReturns.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="lg:col-span-1"
                  >
                    <MultiPeriodPerformance data={result.periodReturns} />
                  </motion.div>
                )}

                {/* Prediction Timeline - 3 columns全宽，右侧完全对齐 */}
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.25 }}
                  className="lg:col-span-3"
                >
                  <div className="glass-card rounded-xl p-5 border border-white/[0.06]">
                    <PredictionTimeline
                      predictions={result.predictions}
                      onHoverHorizon={setActiveHorizon}
                    />
                  </div>
                </motion.div>

                {/* Analysis Report - 响应式 */}
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.25 }}
                  className="md:col-span-2 lg:col-span-3"
                  id="analysis-report-section"
                >
                  <div className="glass-card rounded-xl border border-white/[0.06] overflow-hidden">
                    {/* Report Header - 响应式 */}
                    <div className="flex items-center justify-between px-3 sm:px-5 py-3 sm:py-4 border-b border-white/[0.06] bg-white/[0.02]">
                      <div className="flex items-center gap-2 sm:gap-3">
                        <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                          <FileText className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-indigo-400" />
                        </div>
                        <div>
                          <h3 className="text-xs sm:text-sm font-bold text-white tracking-wide">智能研报</h3>
                          <span className="text-[9px] sm:text-[10px] uppercase tracking-wider text-slate-500">AI量化分析</span>
                        </div>
                      </div>
                      <button
                        onClick={() => {
                          // 直接克隆当前页面HTML下载
                          const htmlContent = document.documentElement.outerHTML;
                          
                          // 获取所有样式表内容
                          let styles = '';
                          const styleSheets = document.styleSheets;
                          for (let i = 0; i < styleSheets.length; i++) {
                            try {
                              const rules = styleSheets[i].cssRules || styleSheets[i].rules;
                              if (rules) {
                                for (let j = 0; j < rules.length; j++) {
                                  styles += rules[j].cssText + '\n';
                                }
                              }
                            } catch (e) {
                              // 跨域样式表无法访问，跳过
                            }
                          }
                          
                          // 构建完整的HTML文档
                          const fullHtml = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${result.ticker} - ${result.name} AI智能分析报告</title>
  <style>
    ${styles}
    /* 额外的内联样式确保显示正确 */
    body { background: linear-gradient(135deg, #020617 0%, #0f172a 50%, #1e1b4b 100%); min-height: 100vh; }
  </style>
</head>
<body>
  ${document.body.innerHTML}
</body>
</html>`;
                          
                          const blob = new Blob([fullHtml], { type: 'text/html;charset=utf-8' });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = `${result.ticker}_AI智能分析报告.html`;
                          a.click();
                          URL.revokeObjectURL(url);
                        }}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 hover:bg-indigo-500/20 text-xs font-medium text-indigo-400 transition-all"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        下载报告
                      </button>
                    </div>

                    {/* Report Content - 响应式 */}
                    <div className="p-4 sm:p-6 md:p-8">
                      <div 
                        className="markdown-content prose prose-invert prose-sm max-w-none overflow-y-auto scrollbar-thin" 
                        style={{ maxHeight: 'calc(100vh - 350px)', minHeight: '300px' }}
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
        )}
      </AnimatePresence>

      {/* Error Dialog */}
      {errorDialog.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="glass-card w-full max-w-sm mx-4 rounded-2xl border border-white/[0.15] bg-[#020617]/95 shadow-xl shadow-black/40">
            <div className="flex items-start gap-3 px-4 pt-4">
              <div className="w-9 h-9 rounded-xl bg-rose-500/10 border border-rose-500/40 flex items-center justify-center">
                <AlertCircle className="w-5 h-5 text-rose-400" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-white truncate">
                  {errorDialog.title || '分析失败'}
                </h3>
                <p className="mt-2 text-xs text-slate-400 whitespace-pre-line">
                  {errorDialog.message}
                </p>
              </div>
            </div>
            <div className="px-4 pb-4 pt-3 flex justify-end">
              <button
                onClick={() => setErrorDialog({ open: false })}
                className="px-4 py-1.5 rounded-lg bg-indigo-500 text-xs font-medium text-white hover:bg-indigo-400 transition-colors"
              >
                确定
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
