"use client";

import { useState, useEffect, memo, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import dynamic from "next/dynamic";
import { FileText, AlertCircle, ArrowLeft, ExternalLink, Share2, Copy, Check, X } from "lucide-react";
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
  
  // 分享相关状态
  const [showShareMenu, setShowShareMenu] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);

  const getToken = () => localStorage.getItem("token");
  
  // 获取分享链接
  const getShareUrl = useCallback(() => {
    if (typeof window === 'undefined') return '';
    // 使用公开分享页面路径，将点号替换为下划线
    const urlSymbol = symbol.replace(/\./g, '_');
    return `${window.location.origin}/share/report/${encodeURIComponent(urlSymbol)}`;
  }, [symbol]);
  
  // 复制链接
  const handleCopyLink = useCallback(async () => {
    const url = getShareUrl();
    try {
      await navigator.clipboard.writeText(url);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      // 降级方案
      const input = document.createElement('input');
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    }
  }, [getShareUrl]);
  
  // 分享到微信 - 复制链接并提示用户
  const handleShareWeChat = useCallback(async () => {
    const url = getShareUrl();
    try {
      await navigator.clipboard.writeText(url);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      const input = document.createElement('input');
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
    }
    setShowShareMenu(false);
    // 显示提示
    alert('链接已复制！请打开微信，粘贴链接发送给好友');
  }, [getShareUrl]);
  
  // 分享到QQ
  const handleShareQQ = useCallback(() => {
    const url = getShareUrl();
    const result = parseReportData(report);
    const title = `${result.ticker} ${result.name} AI分析报告`;
    const summary = result.summary?.substring(0, 100) || '技术分析报告';
    // QQ分享链接
    const qqShareUrl = `https://connect.qq.com/widget/shareqq/index.html?url=${encodeURIComponent(url)}&title=${encodeURIComponent(title)}&summary=${encodeURIComponent(summary)}`;
    window.open(qqShareUrl, '_blank', 'width=600,height=500');
    setShowShareMenu(false);
  }, [getShareUrl, report]);
  
  // 分享到钉钉 - 复制链接并提示用户
  const handleShareDingTalk = useCallback(async () => {
    const url = getShareUrl();
    try {
      await navigator.clipboard.writeText(url);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      const input = document.createElement('input');
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
    }
    setShowShareMenu(false);
    alert('链接已复制！请打开钉钉，粘贴链接发送给好友');
  }, [getShareUrl]);

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

  // 备用的Markdown转HTML函数（当无法获取页面渲染内容时使用）
  const convertMarkdownToHtml = (markdown: string): string => {
    if (!markdown) return '';
    
    let html = markdown;
    
    // 1. 先处理代码块（避免内部内容被其他规则处理）
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    
    // 2. 处理表格
    const lines = html.split('\n');
    let inTable = false;
    let tableHtml = '';
    let resultLines: string[] = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const isTableRow = /^\|.*\|$/.test(line.trim());
      const isSeparator = /^\|[-:\s|]+\|$/.test(line.trim());
      
      if (isTableRow && !isSeparator) {
        if (!inTable) {
          inTable = true;
          tableHtml = '<table>';
          // 这是表头
          const cells = line.split('|').filter(c => c.trim());
          tableHtml += '<thead><tr>' + cells.map(c => `<th>${c.trim().replace(/\*\*/g, '')}</th>`).join('') + '</tr></thead><tbody>';
        } else {
          // 这是数据行
          const cells = line.split('|').filter(c => c.trim());
          tableHtml += '<tr>' + cells.map(c => `<td>${c.trim().replace(/\*\*/g, '')}</td>`).join('') + '</tr>';
        }
      } else if (isSeparator) {
        // 跳过分隔行
        continue;
      } else {
        if (inTable) {
          tableHtml += '</tbody></table>';
          resultLines.push(tableHtml);
          inTable = false;
          tableHtml = '';
        }
        resultLines.push(line);
      }
    }
    if (inTable) {
      tableHtml += '</tbody></table>';
      resultLines.push(tableHtml);
    }
    
    html = resultLines.join('\n');
    
    // 3. 处理标题
    html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    
    // 4. 处理粗体和斜体
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    
    // 5. 处理无序列表
    const listLines = html.split('\n');
    let inList = false;
    let listResult: string[] = [];
    
    for (const line of listLines) {
      if (/^[-*] (.+)$/.test(line)) {
        if (!inList) {
          listResult.push('<ul>');
          inList = true;
        }
        listResult.push(`<li>${line.replace(/^[-*] /, '')}</li>`);
      } else {
        if (inList) {
          listResult.push('</ul>');
          inList = false;
        }
        listResult.push(line);
      }
    }
    if (inList) listResult.push('</ul>');
    html = listResult.join('\n');
    
    // 6. 处理分隔线
    html = html.replace(/^---$/gm, '<hr>');
    
    // 7. 处理段落 - 将连续的非标签行包装成段落
    const paragraphLines = html.split('\n');
    let finalResult: string[] = [];
    let paragraphBuffer: string[] = [];
    
    const isHtmlTag = (line: string) => /^<[a-z]|^<\/[a-z]/i.test(line.trim());
    
    for (const line of paragraphLines) {
      const trimmed = line.trim();
      if (!trimmed) {
        if (paragraphBuffer.length > 0) {
          finalResult.push('<p>' + paragraphBuffer.join(' ') + '</p>');
          paragraphBuffer = [];
        }
      } else if (isHtmlTag(trimmed)) {
        if (paragraphBuffer.length > 0) {
          finalResult.push('<p>' + paragraphBuffer.join(' ') + '</p>');
          paragraphBuffer = [];
        }
        finalResult.push(line);
      } else {
        paragraphBuffer.push(trimmed);
      }
    }
    if (paragraphBuffer.length > 0) {
      finalResult.push('<p>' + paragraphBuffer.join(' ') + '</p>');
    }
    
    return finalResult.join('\n');
  };

  // 下载报告 - 直接捕获页面渲染后的内容
  const handleDownloadReport = () => {
    const result = parseReportData(report);
    const createdAt = report?.created_at 
      ? new Date(report.created_at).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).replace(/\//g, '/') 
      : new Date().toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).replace(/\//g, '/');
    
    // 直接获取页面上已渲染的Markdown内容（ReactMarkdown已经转换为HTML）
    // 注意：ReactMarkdown 渲染后的内容在 .markdown-content 内部
    const markdownContainer = document.querySelector('#analysis-report-section .markdown-content');
    let reportContentHtml = '';
    
    if (markdownContainer) {
      // 获取ReactMarkdown渲染后的HTML内容
      const innerHtml = markdownContainer.innerHTML;
      // 检查是否是真正的HTML（包含标签）还是纯文本
      if (innerHtml && innerHtml.includes('<')) {
        reportContentHtml = innerHtml;
      }
    }
    
    // 如果获取失败或内容不是HTML，使用备用的Markdown转HTML方法
    if (!reportContentHtml || !reportContentHtml.includes('<p>') && !reportContentHtml.includes('<h')) {
      reportContentHtml = convertMarkdownToHtml(result.report);
    }
    
    const reportHtml = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${result.ticker} - ${result.name} 分析报告</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { 
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif; 
      background: #020617; 
      color: #e2e8f0; 
      min-height: 100vh; 
      line-height: 1.7;
    }
    .container { 
      width: 100%; 
      max-width: 100%; 
      margin: 0; 
      padding: 24px 40px; 
    }
    
    /* 头部样式 - 占满宽度 */
    .header { 
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 24px; 
      padding: 16px 24px; 
      background: rgba(15, 23, 42, 0.6); 
      border-radius: 12px; 
      border: 1px solid rgba(255, 255, 255, 0.06);
    }
    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .header-icon {
      width: 32px;
      height: 32px;
      background: rgba(99, 102, 241, 0.1);
      border: 1px solid rgba(99, 102, 241, 0.2);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 6px rgba(99, 102, 241, 0.2);
    }
    .header-icon svg {
      width: 16px;
      height: 16px;
      color: #818cf8;
    }
    .header-title {
      font-size: 16px;
      font-weight: 700;
      color: #fff;
      letter-spacing: 0.5px;
    }
    .header-subtitle {
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: #64748b;
    }
    .header-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .ticker {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-weight: 700;
      color: #818cf8;
      font-size: 16px;
    }
    .name {
      font-size: 14px;
      color: #94a3b8;
    }
    .score-badge {
      padding: 6px 12px;
      border-radius: 9999px;
      font-size: 12px;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .score-high { background: rgba(16, 185, 129, 0.1); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.3); }
    .score-mid { background: rgba(14, 165, 233, 0.1); color: #7dd3fc; border: 1px solid rgba(14, 165, 233, 0.3); }
    .score-low { background: rgba(244, 63, 94, 0.1); color: #fda4af; border: 1px solid rgba(244, 63, 94, 0.3); }
    .score-neutral { background: rgba(100, 116, 139, 0.1); color: #cbd5e1; border: 1px solid rgba(100, 116, 139, 0.6); }
    
    /* 报告卡片样式 - 占满宽度 */
    .report-card { 
      width: 100%;
      background: rgba(15, 23, 42, 0.4); 
      border-radius: 12px; 
      border: 1px solid rgba(255, 255, 255, 0.06);
      overflow: hidden;
    }
    .report-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 24px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      background: rgba(255, 255, 255, 0.02);
    }
    .report-card-header-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .report-card-icon {
      width: 36px;
      height: 36px;
      background: rgba(99, 102, 241, 0.1);
      border: 1px solid rgba(99, 102, 241, 0.2);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 6px rgba(99, 102, 241, 0.2);
    }
    .report-card-title {
      font-size: 16px;
      font-weight: 700;
      color: #fff;
    }
    .report-card-subtitle {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: #64748b;
    }
    .report-time {
      font-size: 13px;
      color: #64748b;
    }
    
    /* 报告内容样式 - 更大的内边距 */
    .report-content {
      padding: 32px 40px;
      color: #cbd5e1;
      font-size: 15px;
      line-height: 1.8;
    }
    .report-content h1 {
      color: #f1f5f9;
      font-size: 1.6em;
      font-weight: 800;
      margin-top: 0;
      margin-bottom: 0.8em;
      line-height: 1.3;
    }
    .report-content h2 {
      color: #f1f5f9;
      font-size: 1.35em;
      font-weight: 700;
      margin-top: 1.5em;
      margin-bottom: 0.75em;
      line-height: 1.4;
    }
    .report-content h3 {
      color: #e2e8f0;
      font-size: 1.15em;
      font-weight: 600;
      margin-top: 1.25em;
      margin-bottom: 0.5em;
    }
    .report-content p {
      margin-top: 1em;
      margin-bottom: 1em;
    }
    .report-content strong {
      color: #f1f5f9;
      font-weight: 600;
    }
    .report-content ul, .report-content ol {
      margin-top: 1em;
      margin-bottom: 1em;
      padding-left: 1.5em;
    }
    .report-content li {
      margin-top: 0.25em;
      margin-bottom: 0.25em;
    }
    .report-content table {
      width: 100%;
      border-collapse: collapse;
      margin: 1.5em 0;
      font-size: 0.875em;
    }
    .report-content thead {
      border-bottom: 1px solid rgba(71, 85, 105, 0.5);
    }
    .report-content th {
      color: #94a3b8;
      font-weight: 600;
      padding: 8px 12px;
      text-align: left;
    }
    .report-content td {
      padding: 10px 16px;
      border-bottom: 1px solid rgba(51, 65, 85, 0.5);
    }
    .report-content tbody tr:last-child td {
      border-bottom: none;
    }
    .report-content hr {
      border: none;
      border-top: 1px solid rgba(71, 85, 105, 0.5);
      margin: 2em 0;
    }
    .report-content blockquote {
      border-left: 3px solid #818cf8;
      padding-left: 1em;
      margin: 1.5em 0;
      color: #94a3b8;
      font-style: italic;
    }
    .report-content code {
      background: rgba(51, 65, 85, 0.5);
      padding: 0.2em 0.4em;
      border-radius: 4px;
      font-size: 0.875em;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }
    .report-content pre {
      background: rgba(15, 23, 42, 0.8);
      padding: 1em;
      border-radius: 8px;
      overflow-x: auto;
      margin: 1.5em 0;
    }
    .report-content pre code {
      background: none;
      padding: 0;
    }
    .report-content a {
      color: #818cf8;
      text-decoration: none;
    }
    .report-content a:hover {
      text-decoration: underline;
    }
    
    /* 页脚样式 */
    .footer { 
      text-align: center; 
      margin-top: 32px; 
      padding: 24px 40px; 
      color: #475569; 
      font-size: 12px;
      border-top: 1px solid rgba(71, 85, 105, 0.3);
    }
  </style>
</head>
<body>
  <div class="container">
    <!-- 头部信息 -->
    <div class="header">
      <div class="header-left">
        <div class="header-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/><line x1="10" x2="8" y1="9" y2="9"/></svg>
        </div>
        <div>
          <div class="header-title">技术研报</div>
          <div class="header-subtitle">AI QUANTITATIVE ANALYSIS</div>
        </div>
      </div>
      <div class="header-right">
        <span class="ticker">${result.ticker}</span>
        <span class="name">${result.name}</span>
        ${typeof result.quantScore === 'number' ? `
        <span class="score-badge ${result.quantScore >= 80 ? 'score-high' : result.quantScore >= 60 ? 'score-mid' : result.quantScore <= 40 ? 'score-low' : 'score-neutral'}">
          <span style="font-family: monospace; font-size: 11px;">${result.quantScore.toFixed(1)}</span>
          <span style="opacity: 0.7;">分</span>
        </span>
        ` : ''}
      </div>
    </div>
    
    <!-- 报告卡片 -->
    <div class="report-card">
      <div class="report-card-header">
        <div class="report-card-header-left">
          <div class="report-card-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#818cf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/><line x1="10" x2="8" y1="9" y2="9"/></svg>
          </div>
          <div>
            <div class="report-card-title">详细分析报告</div>
            <div class="report-card-subtitle">DETAILED ANALYSIS</div>
          </div>
        </div>
        <div class="report-time">生成时间: ${createdAt}</div>
      </div>
      <div class="report-content">
        ${reportContentHtml}
      </div>
    </div>
    
    <div class="footer">
      ℹ️ 本报告由数据分析系统生成，仅供学习研究参考，不构成任何投资建议。投资有风险，入市需谨慎。
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

          {/* Prediction Timeline */}
          <div className="lg:col-span-3 animate-slideUp" style={{ animationDelay: '0.2s' }}>
            <div className="glass-card rounded-xl p-3 sm:p-5 border border-white/[0.06]">
              <PredictionTimeline
                predictions={result.predictions}
                onHoverHorizon={setActiveHorizon}
              />
            </div>
          </div>

          {/* Analysis Report */}
          <div
            className="lg:col-span-3 animate-slideUp"
            style={{ animationDelay: '0.25s' }}
            id="analysis-report-section"
          >
            <div className="glass-card rounded-xl border border-white/[0.06] overflow-hidden">
              {/* Report Header */}
              <div className="flex items-center justify-between px-3 sm:px-5 py-3 sm:py-4 border-b border-white/[0.06] bg-white/[0.02]">
                <div className="flex items-center gap-2 sm:gap-3">
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                    <FileText className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-indigo-400" />
                  </div>
                  <div>
                    <h3 className="text-xs sm:text-sm font-bold text-white tracking-wide">技术研报</h3>
                    <span className="text-[9px] sm:text-[10px] uppercase tracking-wider text-slate-500 hidden sm:block">AI QUANTITATIVE ANALYSIS</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {/* 分享按钮 */}
                  <div className="relative">
                    <button
                      onClick={() => setShowShareMenu(!showShareMenu)}
                      className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 hover:bg-emerald-500/20 text-[10px] sm:text-xs font-medium text-emerald-400 transition-all"
                    >
                      <Share2 className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                      <span className="hidden sm:inline">分享</span>
                    </button>
                    
                    {/* 分享菜单 */}
                    {showShareMenu && (
                      <>
                        <div 
                          className="fixed inset-0 z-40" 
                          onClick={() => setShowShareMenu(false)}
                        />
                        <div className="absolute right-0 top-full mt-2 z-50 w-48 bg-slate-800/95 backdrop-blur-md rounded-xl border border-white/10 shadow-xl overflow-hidden">
                          <div className="p-2">
                            <button
                              onClick={handleShareWeChat}
                              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/5 transition-colors"
                            >
                              <div className="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center">
                                <svg className="w-5 h-5 text-green-400" viewBox="0 0 24 24" fill="currentColor">
                                  <path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 01.213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.326.326 0 00.167-.054l1.903-1.114a.864.864 0 01.717-.098 10.16 10.16 0 002.837.403c.276 0 .543-.027.811-.05-.857-2.578.157-4.972 1.932-6.446 1.703-1.415 3.882-1.98 5.853-1.838-.576-3.583-4.196-6.348-8.596-6.348zM5.785 5.991c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 01-1.162 1.178A1.17 1.17 0 014.623 7.17c0-.651.52-1.18 1.162-1.18zm5.813 0c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 01-1.162 1.178 1.17 1.17 0 01-1.162-1.178c0-.651.52-1.18 1.162-1.18zm5.34 2.867c-1.797-.052-3.746.512-5.28 1.786-1.72 1.428-2.687 3.72-1.78 6.22.942 2.453 3.666 4.229 6.884 4.229.826 0 1.622-.12 2.361-.336a.722.722 0 01.598.082l1.584.926a.272.272 0 00.14.045c.134 0 .24-.111.24-.247 0-.06-.023-.12-.038-.177l-.327-1.233a.582.582 0 01-.023-.156.49.49 0 01.201-.398C23.024 18.48 24 16.82 24 14.98c0-3.21-2.931-5.837-6.656-6.088V8.89c-.135-.01-.269-.03-.407-.03zm-2.53 3.274c.535 0 .969.44.969.982a.976.976 0 01-.969.983.976.976 0 01-.969-.983c0-.542.434-.982.97-.982zm4.844 0c.535 0 .969.44.969.982a.976.976 0 01-.969.983.976.976 0 01-.969-.983c0-.542.434-.982.969-.982z"/>
                                </svg>
                              </div>
                              <span className="text-sm text-slate-200">微信</span>
                            </button>
                            
                            <button
                              onClick={handleShareQQ}
                              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/5 transition-colors"
                            >
                              <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                                <svg className="w-5 h-5 text-blue-400" viewBox="0 0 24 24" fill="currentColor">
                                  <path d="M12.003 2c-2.265 0-6.29 1.364-6.29 7.325v1.195S3.55 14.96 3.55 17.474c0 .665.17 1.025.281 1.025.114 0 .902-.484 1.748-2.072 0 0-.18 2.197 1.904 3.967 0 0-1.77.495-1.77 1.182 0 .686 4.078.43 6.29.43 2.212 0 6.29.256 6.29-.43 0-.687-1.77-1.182-1.77-1.182 2.085-1.77 1.905-3.967 1.905-3.967.845 1.588 1.634 2.072 1.746 2.072.111 0 .283-.36.283-1.025 0-2.514-2.166-6.954-2.166-6.954V9.325C18.29 3.364 14.268 2 12.003 2z"/>
                                </svg>
                              </div>
                              <span className="text-sm text-slate-200">QQ</span>
                            </button>
                            
                            <button
                              onClick={handleShareDingTalk}
                              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/5 transition-colors"
                            >
                              <div className="w-8 h-8 rounded-lg bg-sky-500/20 flex items-center justify-center">
                                <svg className="w-5 h-5 text-sky-400" viewBox="0 0 24 24" fill="currentColor">
                                  <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 14.957c-.09.188-.31.344-.482.406l-2.042.734.64 1.953c.063.188.016.39-.125.516-.14.125-.344.156-.515.078l-2.016-.922-1.266 1.656c-.11.14-.28.219-.453.219-.063 0-.125-.016-.188-.031-.234-.078-.39-.297-.39-.547v-2.078l-4.5-3.266c-.172-.125-.266-.328-.25-.531.016-.203.14-.39.328-.484l9-4.5c.172-.094.375-.078.531.031.156.11.25.297.234.5l-.516 6.266z"/>
                                </svg>
                              </div>
                              <span className="text-sm text-slate-200">钉钉</span>
                            </button>
                            
                            <div className="border-t border-white/10 my-1"></div>
                            
                            <button
                              onClick={() => { handleCopyLink(); setShowShareMenu(false); }}
                              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/5 transition-colors"
                            >
                              <div className="w-8 h-8 rounded-lg bg-slate-500/20 flex items-center justify-center">
                                {copySuccess ? (
                                  <Check className="w-5 h-5 text-emerald-400" />
                                ) : (
                                  <Copy className="w-5 h-5 text-slate-400" />
                                )}
                              </div>
                              <span className="text-sm text-slate-200">
                                {copySuccess ? '已复制' : '复制链接'}
                              </span>
                            </button>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                  
                  {/* 下载按钮 */}
                  <button
                    onClick={handleDownloadReport}
                    className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 hover:bg-indigo-500/20 text-[10px] sm:text-xs font-medium text-indigo-400 transition-all"
                  >
                    <ExternalLink className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                    <span className="hidden sm:inline">下载报告</span>
                    <span className="sm:hidden">下载</span>
                  </button>
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
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
