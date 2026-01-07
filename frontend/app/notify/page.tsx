'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { TrendingUp, TrendingDown, Clock, AlertTriangle, Bot, ArrowLeft } from 'lucide-react';

function NotifyContent() {
  const searchParams = useSearchParams();
  
  const title = searchParams.get('title') || '投资提醒';
  const content = searchParams.get('content') || '';
  const time = searchParams.get('time') || new Date().toLocaleString('zh-CN');
  const type = searchParams.get('type') || 'buy';
  const symbol = searchParams.get('symbol') || '';
  const name = searchParams.get('name') || '';
  const price = searchParams.get('price') || '';
  const targetPrice = searchParams.get('target') || '';
  const aiReason = searchParams.get('ai') || '';
  
  const isBuy = type === 'buy';
  
  // 解析 content 中的换行
  const contentLines = content.split('\n').filter(line => line.trim());

  // 从 content 中提取信息（如果没有结构化参数）
  let extractedSymbol = symbol;
  let extractedName = name;
  let extractedPrice = price;
  let extractedTarget = targetPrice;
  let extractedTime = time;
  let extractedAi = aiReason;

  if (!symbol && content) {
    contentLines.forEach(line => {
      if (line.includes('股票代码') && line.includes('：')) {
        extractedSymbol = line.split('：')[1]?.trim() || '';
      }
      if (line.includes('名称') && line.includes('：')) {
        extractedName = line.split('：')[1]?.trim() || '';
      }
      if (line.includes('当前价格') && line.includes('：')) {
        extractedPrice = line.split('：')[1]?.trim().replace('¥', '') || '';
      }
      if (line.includes('触发时间') && line.includes('：')) {
        extractedTime = line.split('：')[1]?.trim() || '';
      }
    });
    
    // 提取 AI 分析原因
    const aiIndex = content.indexOf('AI分析');
    if (aiIndex !== -1) {
      const afterAi = content.substring(aiIndex);
      const reasonStart = afterAi.indexOf('：') || afterAi.indexOf(':');
      if (reasonStart !== -1) {
        extractedAi = afterAi.substring(reasonStart + 1).trim();
      }
    }
    
    // 提取目标价格
    const targetMatch = content.match(/[买入|卖出]价格\s*[¥￥]?([\d.]+)/);
    if (targetMatch) {
      extractedTarget = targetMatch[1];
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-[#0B1121] to-slate-900 text-slate-300">
      {/* Background Effects */}
      <div className="fixed inset-0 bg-grid pointer-events-none opacity-30" />
      <div className={`fixed inset-0 bg-gradient-radial ${isBuy ? 'from-emerald-500/5' : 'from-rose-500/5'} via-transparent to-transparent pointer-events-none`} />
      
      <div className="relative z-10 px-4 py-6 max-w-lg mx-auto">
        {/* 顶部 Logo */}
        <div className="flex items-center justify-center gap-2 mb-6">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
            <Bot className="w-5 h-5 text-indigo-400" />
          </div>
          <span className="text-lg font-semibold text-white">数据分析学习</span>
        </div>
        
        {/* 主卡片 */}
        <div className="glass-card rounded-2xl overflow-hidden">
          {/* 头部 */}
          <div className={`p-5 ${isBuy ? 'bg-gradient-to-r from-emerald-500/20 to-green-500/10 border-b border-emerald-500/20' : 'bg-gradient-to-r from-rose-500/20 to-red-500/10 border-b border-rose-500/20'}`}>
            <div className="flex items-center gap-4">
              <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${isBuy ? 'bg-emerald-500/20 border border-emerald-500/30' : 'bg-rose-500/20 border border-rose-500/30'}`}>
                {isBuy ? (
                  <TrendingUp className="w-7 h-7 text-emerald-400" />
                ) : (
                  <TrendingDown className="w-7 h-7 text-rose-400" />
                )}
              </div>
              <div>
                <h1 className={`text-xl font-bold ${isBuy ? 'text-emerald-400' : 'text-rose-400'}`}>
                  触及{isBuy ? '参考低位' : '参考高位'}
                </h1>
                <div className="flex items-center gap-1.5 text-slate-400 text-sm mt-1">
                  <Clock className="w-3.5 h-3.5" />
                  <span>{extractedTime}</span>
                </div>
              </div>
            </div>
          </div>
          
          {/* 内容区域 */}
          <div className="p-5 space-y-4">
            {/* 股票信息 */}
            {(extractedSymbol || extractedName) && (
              <div className="bg-slate-800/50 rounded-xl p-4 border border-white/5">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-slate-500 text-xs mb-1 uppercase tracking-wider">股票代码</p>
                    <p className="text-lg font-mono font-bold text-white">{extractedSymbol}</p>
                    <p className="text-slate-400 mt-0.5">{extractedName}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-slate-500 text-xs mb-1 uppercase tracking-wider">当前价格</p>
                    <p className={`text-2xl font-mono font-bold ${isBuy ? 'text-emerald-400' : 'text-rose-400'}`}>
                      ¥{extractedPrice}
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {/* 价格提醒 */}
            <div className={`rounded-xl p-4 border ${isBuy ? 'bg-emerald-500/10 border-emerald-500/20' : 'bg-rose-500/10 border-rose-500/20'}`}>
              <div className="flex items-start gap-3">
                <AlertTriangle className={`w-5 h-5 mt-0.5 ${isBuy ? 'text-emerald-400' : 'text-rose-400'}`} />
                <div>
                  <p className={`font-semibold ${isBuy ? 'text-emerald-300' : 'text-rose-300'}`}>
                    触及{isBuy ? '参考低位' : '参考高位'}
                  </p>
                  <p className="text-slate-300 mt-1">
                    当前价格已触及技术分析的{isBuy ? '参考低位（支撑位）' : '参考高位（阻力位）'} 
                    <span className={`font-mono font-bold ml-1 ${isBuy ? 'text-emerald-400' : 'text-rose-400'}`}>
                      ¥{extractedTarget}
                    </span>
                  </p>
                  <p className="mt-2 text-slate-400 text-sm">
                    请自行判断是否进行操作，本提醒不构成任何投资建议。
                  </p>
                </div>
              </div>
            </div>
            
            {/* 技术分析说明 */}
            {extractedAi && (
              <div className="bg-indigo-500/10 rounded-xl p-4 border-l-2 border-indigo-500">
                <div className="flex items-center gap-2 mb-3">
                  <Bot className="w-4 h-4 text-indigo-400" />
                  <span className="font-semibold text-indigo-300 text-sm">
                    技术分析说明
                  </span>
                </div>
                <p className="text-slate-300 leading-relaxed text-sm">
                  {extractedAi}
                </p>
              </div>
            )}
            
            {/* 如果没有结构化数据，显示原始内容 */}
            {!extractedSymbol && !extractedName && contentLines.length > 0 && (
              <div className="space-y-3">
                {contentLines.map((line, index) => {
                  // 跳过标题行
                  if (line.includes('提醒') && index === 0) return null;
                  
                  // 普通信息行
                  if (line.includes('：') || line.includes(':')) {
                    const [label, value] = line.split(/：|:/);
                    return (
                      <div key={index} className="flex justify-between items-center py-2 border-b border-white/5 last:border-0">
                        <span className="text-slate-500 text-sm">{label}</span>
                        <span className="font-medium text-white">{value}</span>
                      </div>
                    );
                  }
                  
                  return (
                    <p key={index} className="text-slate-300 leading-relaxed">{line}</p>
                  );
                })}
              </div>
            )}
          </div>
          
          {/* 底部 */}
          <div className="px-5 py-4 bg-slate-900/50 border-t border-white/5">
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>数据分析学习 · 价格提醒</span>
              <span>仅供参考，投资有风险</span>
            </div>
          </div>
        </div>
        
        {/* 免责声明 */}
        <p className="text-center text-slate-600 text-xs mt-6 px-4">
          本提醒由数据分析系统生成，仅供学习研究参考，不构成任何投资建议。投资有风险，入市需谨慎。
        </p>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-[#0B1121] to-slate-900 flex items-center justify-center">
      <div className="text-center">
        <div className="w-10 h-10 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-slate-500">加载中...</p>
      </div>
    </div>
  );
}

export default function NotifyPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <NotifyContent />
    </Suspense>
  );
}
