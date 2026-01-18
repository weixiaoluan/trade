"use client";

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Sparkles, ArrowRight, Loader2, BarChart3 } from 'lucide-react';

interface SearchBoxProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
  isCompact?: boolean;
}

const DEFAULT_QUICK_TICKERS = [
  { symbol: '159941', name: '纳指100ETF' },
  { symbol: '159915', name: '创业板ETF' },
  { symbol: '510300', name: '沪深300ETF' },
  { symbol: '513180', name: '恒生科技ETF' },
  { symbol: '600519', name: '贵州茅台' },
];

const suggestions = [
  { symbol: 'AAPL', name: 'Apple Inc.', type: 'US' },
  { symbol: 'TSLA', name: 'Tesla Inc.', type: 'US' },
  { symbol: 'NVDA', name: 'NVIDIA Corp', type: 'US' },
  { symbol: '600519', name: '贵州茅台', type: 'A股' },
  { symbol: '513180', name: '恒生科技ETF', type: 'ETF' },
  { symbol: '159941', name: '纳指100ETF', type: 'ETF' },
  { symbol: '020398', name: '诺安创新驱动混合A', type: '基金' },
];

export function SearchBox({ onSearch, isLoading = false, isCompact = false }: SearchBoxProps) {
  const [query, setQuery] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [quickTickers, setQuickTickers] = useState(DEFAULT_QUICK_TICKERS);
  const inputRef = useRef<HTMLInputElement>(null);

  const filteredSuggestions = suggestions.filter(
    (s) =>
      s.symbol.toLowerCase().includes(query.toLowerCase()) ||
      s.name.toLowerCase().includes(query.toLowerCase())
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim().toUpperCase());
      setShowSuggestions(false);
    }
  };

  const handleSuggestionClick = (symbol: string) => {
    setQuery(symbol);
    onSearch(symbol);
    setShowSuggestions(false);
  };

  useEffect(() => {
    const fetchPopularTickers = async () => {
      try {
        const res = await fetch('/api/popular_tickers');
        if (!res.ok) return;
        const data = await res.json();
        const items = (data?.items || []) as { symbol: string; count?: number }[];
        if (items.length > 0) {
          setQuickTickers(
            items.slice(0, 5).map((item) => ({ symbol: item.symbol, name: item.symbol }))
          );
        }
      } catch {
        // ignore
      }
    };

    fetchPopularTickers();
  }, []);

  return (
    <div className={`relative w-full ${isCompact ? 'max-w-md' : 'max-w-2xl'} mx-auto`}>
      <form onSubmit={handleSubmit}>
        <div
          className={`
            relative bg-slate-900/80 backdrop-blur-sm rounded-2xl
            border transition-all duration-300
            ${isFocused
              ? 'border-indigo-500/50 ring-2 ring-indigo-500/20'
              : 'border-white/[0.08] hover:border-white/[0.15]'
            }
          `}
        >
          <div className="flex items-center">
            <div className="pl-3 sm:pl-5 text-slate-500">
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
              ) : (
                <Search className="w-5 h-5" />
              )}
            </div>

            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setShowSuggestions(true);
              }}
              onFocus={() => {
                setIsFocused(true);
                setShowSuggestions(true);
              }}
              onBlur={() => {
                setIsFocused(false);
                setTimeout(() => setShowSuggestions(false), 200);
              }}
              placeholder="输入代码（推荐直接输入6位数字，如: 600519、159941；美股可输入 AAPL）"
              className={`
                flex-1 bg-transparent border-none outline-none
                text-slate-100 placeholder-slate-500 font-medium
                w-full min-w-0
                ${isCompact ? 'py-3 px-2 text-sm' : 'py-4 px-3 text-sm sm:text-base'}
              `}
              disabled={isLoading}
            />

            <motion.button
              type="submit"
              disabled={isLoading || !query.trim()}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={`
                shrink-0
                ${isCompact ? 'mx-1 px-3 py-2' : 'mx-1.5 sm:mx-3 px-3 sm:px-5 py-2 sm:py-2.5'}
                bg-gradient-to-r from-indigo-600 to-violet-600
                hover:from-indigo-500 hover:to-violet-500
                text-white text-xs sm:text-sm font-medium rounded-xl
                transition-all duration-300
                disabled:opacity-40 disabled:cursor-not-allowed
                flex items-center gap-1 sm:gap-2
              `}
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-3 h-3 sm:w-4 sm:h-4 animate-spin" />
                  <span className={isCompact ? 'hidden' : 'hidden sm:inline'}>分析中</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3 h-3 sm:w-4 sm:h-4" />
                  <span className={isCompact ? 'hidden sm:inline' : 'whitespace-nowrap'}>AI 分析</span>
                </>
              )}
            </motion.button>
          </div>
        </div>
      </form>

      {!isCompact && !isFocused && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex flex-wrap items-center justify-center gap-2 mt-4"
        >
          <span className="text-xs text-slate-600 mr-1">快速访问:</span>
          {quickTickers.map((ticker) => (
            <button
              key={ticker.symbol}
              onClick={() => handleSuggestionClick(ticker.symbol)}
              className="
                px-3 py-1.5 rounded-full text-xs font-medium
                bg-white/[0.03] border border-white/[0.08]
                text-slate-400 hover:text-slate-200
                hover:bg-white/[0.08] hover:border-white/[0.15]
                transition-all duration-200
              "
            >
              {ticker.symbol}
            </button>
          ))}
        </motion.div>
      )}

      <AnimatePresence>
        {showSuggestions && query && filteredSuggestions.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="absolute w-full mt-2 bg-slate-900/95 backdrop-blur-md rounded-xl border border-white/[0.08] overflow-hidden z-50 shadow-2xl"
          >
            {filteredSuggestions.map((suggestion, index) => (
              <motion.button
                key={suggestion.symbol}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: index * 0.03 }}
                onClick={() => handleSuggestionClick(suggestion.symbol)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/[0.05] transition-colors text-left group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                    <BarChart3 className="w-4 h-4 text-indigo-400" />
                  </div>
                  <div>
                    <div className="font-mono font-medium text-slate-200 text-sm">{suggestion.symbol}</div>
                    <div className="text-xs text-slate-500">{suggestion.name}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 uppercase tracking-wider">
                    {suggestion.type}
                  </span>
                  <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-slate-400 transition-colors" />
                </div>
              </motion.button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
