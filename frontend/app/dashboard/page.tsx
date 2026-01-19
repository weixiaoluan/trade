"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { flushSync } from "react-dom";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot,
  Plus,
  Trash2,
  Play,
  FileText,
  Camera,
  Search,
  X,
  Check,
  CheckSquare,
  Square,
  RefreshCw,
  Clock,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertCircle,
  Loader2,
  Star,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Menu,
  MoreVertical,
  Settings,
  MessageSquare,
  ExternalLink,
  AlertTriangle,
  Edit3,
  Sparkles,
  Share2,
} from "lucide-react";
import { UserHeader } from "@/components/ui/UserHeader";
import { AlertModal } from "@/components/ui/AlertModal";
import { ConfirmModal } from "@/components/ui/ConfirmModal";

import { API_BASE } from "@/lib/config";

// 判断是否是美股，返回对应的货币符号
const getCurrencySymbol = (symbol: string): string => {
  if (!symbol) return "¥";
  // 移除可能的后缀
  const code = symbol.replace(/\.(SH|SZ|HK|sh|sz|hk)$/i, '');
  // 如果是纯数字，是中国股票
  if (/^\d+$/.test(code)) return "¥";
  // 如果包含 .HK 后缀，是港股
  if (symbol.toUpperCase().includes('.HK')) return "HK$";
  // 美股代码通常是字母或字母+数字组合
  const codeNoDot = code.replace(/[._]/g, '');
  if (/^[A-Za-z]/.test(codeNoDot)) return "$";
  return "¥";
};

interface UserInfo {
  username: string;
  phone?: string;
  role?: string;
  status?: string;
}

interface WatchlistItem {
  symbol: string;
  name?: string;
  type?: string;
  added_at?: string;
  position?: number;
  cost_price?: number;
  starred?: number;
  ai_buy_price?: number;
  ai_sell_price?: number;
  ai_buy_quantity?: number;
  ai_sell_quantity?: number;
  ai_recommendation?: string;
  ai_price_updated_at?: string;
  last_alert_at?: string;
  holding_period?: string;
  from_ai_pick?: number;
  // 多周期价位字段
  short_support?: number;
  short_resistance?: number;
  short_risk?: number;
  swing_support?: number;
  swing_resistance?: number;
  swing_risk?: number;
  long_support?: number;
  long_resistance?: number;
  long_risk?: number;
  // 多周期信号类型字段
  short_signal?: string;
  swing_signal?: string;
  long_signal?: string;
}

interface TaskStatus {
  task_id: string;
  symbol: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  current_step: string;
  created_at?: string;
  updated_at?: string;
}

interface ReportSummary {
  id: string;
  symbol: string;
  created_at: string;
  status: string;
  name: string;
  recommendation: string;
  quant_score: number;
  price: number;
  change_percent: number;
}

interface QuoteData {
  symbol: string;
  current_price: number;
  change_percent: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const initialDataLoadedRef = useRef(false);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [tasks, setTasks] = useState<Record<string, TaskStatus>>({});
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(false);

  const [showAddModal, setShowAddModal] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);
  const [showOcrModal, setShowOcrModal] = useState(false);
  const [currentReport, setCurrentReport] = useState<any>(null);
  const [addSymbol, setAddSymbol] = useState("");

  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrResults, setOcrResults] = useState<Array<{ symbol: string; name: string; type: string; selected: boolean; position?: number; cost_price?: number }>>([]);

  const [addPosition, setAddPosition] = useState<string>("");
  const [addCostPrice, setAddCostPrice] = useState<string>("");

  const [currentPage, setCurrentPage] = useState(1);
  // 移动端默认10条，桌面端默认50条
  const [pageSize, setPageSize] = useState(10);
  const [isMobile, setIsMobile] = useState(true);

  const [quotes, setQuotes] = useState<Record<string, QuoteData>>({});

  const [showAlert, setShowAlert] = useState(false);
  const [alertConfig, setAlertConfig] = useState({
    title: "",
    message: "",
    type: "warning" as "warning" | "info" | "success" | "error",
  });

  const [sortField, setSortField] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">('desc');
  
  // 搜索状态
  const [searchQuery, setSearchQuery] = useState('');
  // 周期筛选状态
  const [periodFilter, setPeriodFilter] = useState<string>('all');
  
  // 信号类型筛选状态
  const [ratingFilter, setRatingFilter] = useState<string>('all');
  
  // 客户端挂载后从 localStorage 读取初始状态
  useEffect(() => {
    if (typeof window !== 'undefined') {
      // 读取用户信息
      const storedUser = localStorage.getItem("user");
      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser));
        } catch {
          // ignore
        }
      }
      // 检查是否已登录
      if (localStorage.getItem("token") && localStorage.getItem("user")) {
        setAuthChecked(true);
      }
      // 读取筛选状态
      const savedSortField = localStorage.getItem('dashboard_sortField');
      if (savedSortField) setSortField(savedSortField);
      
      const savedSortOrder = localStorage.getItem('dashboard_sortOrder');
      if (savedSortOrder === 'asc' || savedSortOrder === 'desc') setSortOrder(savedSortOrder);
      
      const savedSearchQuery = localStorage.getItem('dashboard_searchQuery');
      if (savedSearchQuery) setSearchQuery(savedSearchQuery);
      
      const savedPeriodFilter = localStorage.getItem('dashboard_periodFilter');
      if (savedPeriodFilter) setPeriodFilter(savedPeriodFilter);
      
      const savedRatingFilter = localStorage.getItem('dashboard_ratingFilter');
      if (savedRatingFilter) setRatingFilter(savedRatingFilter);
    }
  }, []);
  
  // 保存筛选状态到 localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      if (sortField) {
        localStorage.setItem('dashboard_sortField', sortField);
      } else {
        localStorage.removeItem('dashboard_sortField');
      }
    }
  }, [sortField]);
  
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('dashboard_sortOrder', sortOrder);
    }
  }, [sortOrder]);
  
  useEffect(() => {
    if (typeof window !== 'undefined') {
      if (searchQuery) {
        localStorage.setItem('dashboard_searchQuery', searchQuery);
      } else {
        localStorage.removeItem('dashboard_searchQuery');
      }
    }
  }, [searchQuery]);
  
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('dashboard_periodFilter', periodFilter);
    }
  }, [periodFilter]);
  
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('dashboard_ratingFilter', ratingFilter);
    }
  }, [ratingFilter]);
  
  // 移动端操作菜单
  const [activeActionMenu, setActiveActionMenu] = useState<string | null>(null);

  // 用户设置相关
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [userSettings, setUserSettings] = useState<{
    wechat_openid: string;
    wechat_configured: boolean;
    wechat_gh_id: string;
    wechat_account: string;
  } | null>(null);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [wechatOpenId, setWechatOpenId] = useState("");
  const [testPushLoading, setTestPushLoading] = useState(false);

  // 错误弹窗控制 - 避免重复弹窗
  const [shownErrorTasks, setShownErrorTasks] = useState<Set<string>>(new Set());

  // 确认弹窗状态
  const [showConfirm, setShowConfirm] = useState(false);
  const [confirmConfig, setConfirmConfig] = useState({
    title: "",
    message: "",
    type: "question" as "warning" | "info" | "success" | "error" | "question",
    onConfirm: () => {},
  });

  // 持有周期选择弹窗状态
  const [showHoldingPeriodModal, setShowHoldingPeriodModal] = useState(false);
  const [holdingPeriod, setHoldingPeriod] = useState<string>("short");

  // 每个标的的显示周期选择（用于切换显示不同周期的支撑位/阻力位/风险位）
  const [itemDisplayPeriods, setItemDisplayPeriods] = useState<Record<string, string>>({});
  
  // 实时价位数据缓存（按周期缓存）
  const [realtimePricesCache, setRealtimePricesCache] = useState<Record<string, Record<string, {
    support: number;
    resistance: number;
    risk: number;
    updated_at: string;
  }>>>({});
  
  // 正在加载价位的标的
  const [loadingPrices, setLoadingPrices] = useState<Set<string>>(new Set());

  // 获取token（提前定义，供后续函数使用）
  const getToken = useCallback(() => localStorage.getItem("token"), []);

  // 获取标的当前显示周期（默认使用标的的holding_period）
  const getItemDisplayPeriod = useCallback((item: WatchlistItem) => {
    return itemDisplayPeriods[item.symbol] || item.holding_period || 'swing';
  }, [itemDisplayPeriods]);

  // 从接口实时获取价位数据
  const fetchRealtimePrices = useCallback(async (symbols: string[], period: string) => {
    const token = getToken();
    if (!token || symbols.length === 0) return;
    
    // 标记正在加载
    setLoadingPrices(prev => new Set([...Array.from(prev), ...symbols]));
    
    try {
      const symbolsStr = symbols.join(",");
      const response = await fetch(`${API_BASE}/api/watchlist/prices/realtime?symbols=${encodeURIComponent(symbolsStr)}&period=${period}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.prices) {
          // 更新缓存
          setRealtimePricesCache(prev => {
            const newCache = { ...prev };
            Object.entries(data.prices).forEach(([symbol, priceData]: [string, any]) => {
              if (!priceData.error) {
                if (!newCache[symbol]) {
                  newCache[symbol] = {};
                }
                newCache[symbol][period] = {
                  support: priceData.support,
                  resistance: priceData.resistance,
                  risk: priceData.risk,
                  updated_at: priceData.updated_at
                };
              }
            });
            return newCache;
          });
          
          // 同时更新watchlist状态（用于持久化显示）
          setWatchlist(prev => prev.map(item => {
            const priceData = data.prices[item.symbol];
            if (priceData && !priceData.error) {
              const updates: Partial<WatchlistItem> = {};
              if (period === 'short') {
                updates.short_support = priceData.support;
                updates.short_resistance = priceData.resistance;
                updates.short_risk = priceData.risk;
              } else if (period === 'swing') {
                updates.swing_support = priceData.support;
                updates.swing_resistance = priceData.resistance;
                updates.swing_risk = priceData.risk;
              } else if (period === 'long') {
                updates.long_support = priceData.support;
                updates.long_resistance = priceData.resistance;
                updates.long_risk = priceData.risk;
              }
              return { ...item, ...updates };
            }
            return item;
          }));
        }
      }
    } catch (error) {
      console.error("获取实时价位失败:", error);
    } finally {
      // 移除加载状态
      setLoadingPrices(prev => {
        const next = new Set(prev);
        symbols.forEach(s => next.delete(s));
        return next;
      });
    }
  }, [getToken]);

  // 切换标的显示周期（同时触发实时获取价位）
  const toggleItemDisplayPeriod = useCallback((symbol: string, currentPeriod: string) => {
    const periods = ['short', 'swing', 'long'];
    const currentIndex = periods.indexOf(currentPeriod);
    const nextPeriod = periods[(currentIndex + 1) % periods.length];
    setItemDisplayPeriods(prev => ({ ...prev, [symbol]: nextPeriod }));
    
    // 检查缓存中是否有该周期的数据，如果没有则实时获取
    const cachedData = realtimePricesCache[symbol]?.[nextPeriod];
    const item = watchlist.find(w => w.symbol === symbol);
    
    // 检查是否需要获取数据（缓存不存在或数据库中没有对应周期的数据）
    let needFetch = !cachedData;
    if (!needFetch && item) {
      if (nextPeriod === 'short' && !item.short_support) needFetch = true;
      if (nextPeriod === 'swing' && !item.swing_support) needFetch = true;
      if (nextPeriod === 'long' && !item.long_support) needFetch = true;
    }
    
    if (needFetch && !loadingPrices.has(symbol)) {
      fetchRealtimePrices([symbol], nextPeriod);
    }
  }, [realtimePricesCache, watchlist, loadingPrices, fetchRealtimePrices]);

  // 根据周期获取对应的价位数据（优先使用缓存，其次使用数据库数据）
  const getPeriodPrices = useCallback((item: WatchlistItem, period: string) => {
    // 优先使用实时缓存数据
    const cachedData = realtimePricesCache[item.symbol]?.[period];
    if (cachedData) {
      return {
        support: cachedData.support,
        resistance: cachedData.resistance,
        risk: cachedData.risk,
      };
    }
    
    // 其次使用数据库中的数据
    switch (period) {
      case 'short':
        return {
          support: item.short_support,
          resistance: item.short_resistance,
          risk: item.short_risk,
        };
      case 'long':
        return {
          support: item.long_support,
          resistance: item.long_resistance,
          risk: item.long_risk,
        };
      case 'swing':
      default:
        return {
          support: item.swing_support || item.ai_buy_price,
          resistance: item.swing_resistance || item.ai_sell_price,
          risk: item.swing_risk,
        };
    }
  }, [realtimePricesCache]);

  // 计算价格与当前价的差异（支撑位/阻力位/风险位）
  // 正数用红色，负数用绿色，触达用黄色
  const getPriceDiff = useCallback((currentPrice: number | undefined, targetPrice: number | undefined, type: 'support' | 'resistance' | 'risk') => {
    if (!currentPrice || !targetPrice || currentPrice <= 0 || targetPrice <= 0) {
      return null;
    }
    
    const diff = currentPrice - targetPrice;
    const diffPercent = (diff / targetPrice) * 100;
    
    // 触达判断（差异小于0.1%）
    if (Math.abs(diffPercent) < 0.1) {
      return { status: 'touch', text: '触达', color: 'text-amber-400 font-semibold' };
    }
    
    // 简化格式：正数红色，负数绿色，不带"差:"前缀
    if (diff > 0) {
      return { 
        status: 'positive', 
        text: `+${diff.toFixed(3)}/${diffPercent.toFixed(1)}%`, 
        color: 'text-rose-400 font-medium' 
      };
    } else {
      return { 
        status: 'negative', 
        text: `${diff.toFixed(3)}/${diffPercent.toFixed(1)}%`, 
        color: 'text-emerald-400 font-medium' 
      };
    }
  }, []);

  // 获取支撑位/阻力位/风险位数值的颜色（与涨跌幅逻辑一致）
  // 当前价高于目标价（正数）用红色，当前价低于目标价（负数）用绿色
  const getPriceValueColor = useCallback((currentPrice: number | undefined, targetPrice: number | undefined, type: 'support' | 'resistance' | 'risk') => {
    // 默认颜色
    const defaultColors = {
      support: 'text-emerald-400',
      resistance: 'text-rose-400',
      risk: 'text-orange-400'
    };
    
    if (!currentPrice || !targetPrice || currentPrice <= 0 || targetPrice <= 0) {
      return defaultColors[type];
    }
    
    const diff = currentPrice - targetPrice;
    const diffPercent = (diff / targetPrice) * 100;
    
    // 触达判断（差异小于0.5%）- 用黄色
    if (Math.abs(diffPercent) < 0.5) {
      return 'text-amber-400 font-bold';
    }
    
    // 当前价高于目标价 - 红色（涨）
    if (diff > 0) {
      return 'text-rose-400';
    }
    // 当前价低于目标价 - 绿色（跌）
    return 'text-emerald-400';
  }, []);

  // 获取技术评级的颜色样式（强势红色深浅，弱势绿色深浅）
  // 样式参考周期按钮，使用圆角和背景色
  const getRatingStyle = useCallback((rating: string | undefined) => {
    if (!rating) return 'bg-slate-600/30 text-slate-400';
    
    const r = rating.toLowerCase();
    
    // 强势系列 - 红色（越强颜色越深）
    if (r.includes('强势') || r === '强势') {
      return 'bg-rose-600/40 text-rose-300 font-bold border border-rose-500/50';
    }
    if (r.includes('偏强') || r === '偏强') {
      return 'bg-rose-500/25 text-rose-400 font-semibold';
    }
    // 弱势系列 - 绿色（越弱颜色越深）
    if (r.includes('弱势') || r === '弱势') {
      return 'bg-emerald-600/40 text-emerald-300 font-bold border border-emerald-500/50';
    }
    if (r.includes('偏弱') || r === '偏弱') {
      return 'bg-emerald-500/25 text-emerald-400 font-semibold';
    }
    // 中性/震荡 - 蓝灰色
    if (r.includes('中性') || r.includes('震荡') || r === '中性' || r === '震荡') {
      return 'bg-slate-500/30 text-slate-300 font-medium';
    }
    
    return 'bg-slate-600/30 text-slate-400';
  }, []);

  // 根据周期获取对应的信号类型
  const getPeriodSignal = useCallback((item: WatchlistItem, period: string) => {
    switch (period) {
      case 'short':
        return item.short_signal;
      case 'long':
        return item.long_signal;
      case 'swing':
      default:
        return item.swing_signal;
    }
  }, []);

  // 获取信号类型的显示样式和文本
  const getSignalDisplay = useCallback((signal: string | undefined) => {
    if (!signal) return { icon: '⚪', text: '观望', style: 'bg-slate-500/20 text-slate-400 border border-slate-500/30' };
    
    const s = signal.toLowerCase();
    if (s === 'buy' || s === '买入') {
      return { icon: '🟢', text: '买入', style: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 font-semibold' };
    }
    if (s === 'sell' || s === '卖出') {
      return { icon: '🔴', text: '卖出', style: 'bg-rose-500/20 text-rose-400 border border-rose-500/40 font-semibold' };
    }
    return { icon: '⚪', text: '观望', style: 'bg-slate-500/20 text-slate-400 border border-slate-500/30' };
  }, []);

  const [pendingAnalysisSymbols, setPendingAnalysisSymbols] = useState<string[]>([]);
  const [isBatchAnalysis, setIsBatchAnalysis] = useState(false);

  // 编辑持仓弹窗状态
  const [showEditPositionModal, setShowEditPositionModal] = useState(false);
  const [editingItem, setEditingItem] = useState<WatchlistItem | null>(null);
  const [editPosition, setEditPosition] = useState<string>("");
  const [editCostPrice, setEditCostPrice] = useState<string>("");
  const [editHoldingPeriod, setEditHoldingPeriod] = useState<string>("swing");

  // 研究列表相关状态
  const [showAiPicksModal, setShowAiPicksModal] = useState(false);
  const [aiPicks, setAiPicks] = useState<Array<{ symbol: string; name: string; type: string; added_by: string; added_at: string }>>([]);
  const [aiPicksLoading, setAiPicksLoading] = useState(false);
  const [selectedAiPicks, setSelectedAiPicks] = useState<Set<string>>(new Set());
  const [addAsAiPick, setAddAsAiPick] = useState(false);  // 添加自选时是否同时添加到研究列表

  // 计算用户还没有添加到自选的研究列表标的
  const availableAiPicks = useMemo(() => {
    const watchlistSymbols = new Set(watchlist.map(item => item.symbol.toUpperCase()));
    return aiPicks.filter(pick => !watchlistSymbols.has(pick.symbol.toUpperCase()));
  }, [aiPicks, watchlist]);

  // 新增的研究列表数量（用于角标显示）
  const newAiPicksCount = availableAiPicks.length;

  const tasksRef = useRef(tasks);
  useEffect(() => {
    tasksRef.current = tasks;
  }, [tasks]);

  const reportsRef = useRef(reports);
  useEffect(() => {
    reportsRef.current = reports;
  }, [reports]);

  // 检测移动端并设置合适的分页大小
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      // 只在首次加载时设置默认分页大小
      if (mobile && pageSize === 50) {
        setPageSize(10);
      } else if (!mobile && pageSize === 10) {
        setPageSize(50);
      }
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const showAlertModal = useCallback(
    (title: string, message: string, type: "warning" | "info" | "success" | "error" = "warning") => {
      setAlertConfig({ title, message, type });
      setShowAlert(true);
    },
    []
  );

  const showConfirmModal = useCallback(
    (
      title: string,
      message: string,
      onConfirm: () => void,
      type: "warning" | "info" | "success" | "error" | "question" = "question"
    ) => {
      setConfirmConfig({ title, message, type, onConfirm });
      setShowConfirm(true);
    },
    []
  );

  const getErrorMessageFromResponse = useCallback(async (response: Response) => {
    try {
      const data = await response.json();
      return data?.detail || data?.message || JSON.stringify(data);
    } catch {
      return response.statusText || `HTTP ${response.status}`;
    }
  }, []);

  const openNativeTimePicker = useCallback((e: React.MouseEvent<HTMLInputElement>) => {
    try {
      const el = e.currentTarget as any;
      if (typeof el?.showPicker === "function") {
        el.showPicker();
      }
    } catch (err) {
      // 忽略 showPicker 错误，让浏览器使用默认行为
    }
  }, []);

  useEffect(() => {
    const checkAuth = async () => {
      const token = getToken();
      const storedUser = localStorage.getItem("user");

      if (!token || !storedUser) {
        router.push("/login");
        return;
      }

      // 立即加载 dashboard 数据（不依赖 authChecked 状态变化）
      try {
        const dashboardResponse = await fetch(`${API_BASE}/api/dashboard/init`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        
        if (dashboardResponse.ok) {
          const dashboardData = await dashboardResponse.json();
          setWatchlist(dashboardData.watchlist || []);
          setTasks(dashboardData.tasks || {});
          setReports(dashboardData.reports || []);
          setUserSettings(dashboardData.settings);
          setWechatOpenId(dashboardData.settings?.wechat_openid || "");
          if (dashboardData.quotes) {
            setQuotes(dashboardData.quotes);
          }
          // 标记初始数据已加载，防止 authChecked useEffect 重复加载
          initialDataLoadedRef.current = true;
        }
      } catch (error) {
        console.error("获取dashboard数据失败:", error);
      }

      // 设置 authChecked 用于后续轮询
      setAuthChecked(true);

      // 后台静默验证 token 有效性
      try {
        const response = await fetch(`${API_BASE}/api/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!response.ok) {
          // token 无效，清除并跳转登录
          localStorage.removeItem("token");
          localStorage.removeItem("user");
          router.push("/login");
          return;
        }

        // 更新用户信息（可能有变化）
        const data = await response.json();
        localStorage.setItem("user", JSON.stringify(data.user));
        setUser(data.user);
      } catch (error) {
        // 网络错误时不跳转，使用缓存的用户信息继续
        console.error("验证token失败:", error);
      }
    };

    checkAuth();
  }, [router, getToken]);

  const fetchWatchlist = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE}/api/watchlist`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setWatchlist(data.watchlist || []);
      }
    } catch (error) {
      console.error("获取自选列表失败:", error);
    }
  }, [getToken]);

  const fetchReports = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE}/api/reports`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setReports(data.reports || []);
      }
    } catch (error) {
      console.error("获取报告列表失败:", error);
    }
  }, [getToken]);

  // 一次性获取所有dashboard数据（包括行情）
  const fetchDashboardInit = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE}/api/dashboard/init`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setWatchlist(data.watchlist || []);
        setTasks(data.tasks || {});
        setReports(data.reports || []);
        setUserSettings(data.settings);
        setWechatOpenId(data.settings?.wechat_openid || "");
        
        // 如果返回了行情数据，直接使用
        if (data.quotes) {
          setQuotes(data.quotes);
        }
      }
    } catch (error) {
      console.error("获取dashboard数据失败:", error);
    }
  }, [getToken]);

  const fetchTasks = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE}/api/analyze/tasks`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        const newTasks = data.tasks || {};
        
        // 检查是否有新变成失败的任务（之前是 running，现在是 failed）
        const failedTasks: string[] = [];
        const failedErrors: string[] = [];
        // 检查是否有新完成的任务，需要刷新报告
        let hasNewCompleted = false;
        
        Object.entries(newTasks).forEach(([symbol, task]: [string, any]) => {
          const prevTask = tasksRef.current[symbol];
          // 只有从 running/pending 变成 failed 才弹窗
          // 必须有 prevTask 且之前是 running/pending 状态，才说明是刚刚失败的
          // 额外检查：如果该标的已有报告，不弹失败提示（可能是旧任务状态）
          const hasReport = reportsRef.current.some(r => r.symbol?.toUpperCase() === symbol.toUpperCase());
          if (task.status === "failed" && 
              prevTask && 
              (prevTask.status === "running" || prevTask.status === "pending") &&
              !hasReport) {
            // 检查是否已经弹过窗
            if (!shownErrorTasks.has(symbol)) {
              failedTasks.push(symbol);
              if (task.error) {
                failedErrors.push(`${symbol}: ${task.error}`);
              }
            }
          }
          // 检查是否有新完成的任务（两种情况都触发刷新）
          // 1. 从 running/pending 变成 completed
          // 2. 任务状态为 completed 且 progress 为 100，但之前的 progress 不是 100
          if (task.status === "completed") {
            if (prevTask && (prevTask.status === "running" || prevTask.status === "pending")) {
              hasNewCompleted = true;
            } else if (prevTask && prevTask.progress !== 100 && task.progress === 100) {
              hasNewCompleted = true;
            }
          }
        });
        
        // 如果有新失败的任务，弹窗提示
        if (failedTasks.length > 0) {
          setShownErrorTasks(prev => new Set([...Array.from(prev), ...failedTasks]));
          
          if (failedTasks.length === 1) {
            showAlertModal(
              "分析失败",
              failedErrors[0] || `${failedTasks[0]} 分析失败，请稍后重试`,
              "error"
            );
          } else {
            showAlertModal(
              "部分分析失败",
              `${failedTasks.length} 个标的分析失败：${failedTasks.join(", ")}`,
              "error"
            );
          }
        }
        
        setTasks(newTasks);
        
        // 如果有新完成的任务，立即刷新报告列表和自选列表（获取最新的AI建议价格）
        if (hasNewCompleted) {
          fetchReports();
          fetchWatchlist();
        }
      }
    } catch (error) {
      console.error("获取任务状态失败:", error);
    }
  }, [getToken, shownErrorTasks, showAlertModal, fetchReports, fetchWatchlist]);

  // 判断是否为交易时间（A股: 9:30-11:30, 13:00-15:00，周一到周五）
  const isTradingTime = useCallback(() => {
    const now = new Date();
    const day = now.getDay();
    // 周末不交易
    if (day === 0 || day === 6) return false;
    
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const time = hours * 60 + minutes;
    
    // 上午 9:30-11:30 (570-690)
    // 下午 13:00-15:00 (780-900)
    return (time >= 570 && time <= 690) || (time >= 780 && time <= 900);
  }, []);

  const fetchQuotes = useCallback(async () => {
    const token = getToken();
    if (!token || watchlist.length === 0) return;

    try {
      const symbols = watchlist.map(item => item.symbol).join(",");
      const response = await fetch(`${API_BASE}/api/quotes?symbols=${encodeURIComponent(symbols)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setQuotes(data.quotes || {});
      }
    } catch (error) {
      console.error("获取实时行情失败:", error);
    }
  }, [getToken, watchlist]);

  // 信号刷新状态
  const [signalRefreshing, setSignalRefreshing] = useState(false);
  const [lastSignalUpdate, setLastSignalUpdate] = useState<string | null>(null);
  
  // 价位刷新状态
  const [pricesRefreshing, setPricesRefreshing] = useState(false);
  const [lastPricesUpdate, setLastPricesUpdate] = useState<string | null>(null);

  // 获取实时行情和缓存的价位数据（轻量级，适合高频轮询）
  const fetchRealtimeData = useCallback(async () => {
    const token = getToken();
    if (!token || watchlist.length === 0) return;

    try {
      const response = await fetch(`${API_BASE}/api/watchlist/realtime-prices`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        if (data.items) {
          // 更新行情数据
          const newQuotes: Record<string, QuoteData> = {};
          data.items.forEach((item: any) => {
            newQuotes[item.symbol] = {
              symbol: item.symbol,
              current_price: item.current_price,
              change_percent: item.change_pct,
            };
          });
          setQuotes(newQuotes);
          
          // 更新价位数据到watchlist
          setWatchlist(prev => prev.map(w => {
            const item = data.items.find((i: any) => i.symbol.toUpperCase() === w.symbol.toUpperCase());
            if (item) {
              return {
                ...w,
                short_support: item.short_support || w.short_support,
                short_resistance: item.short_resistance || w.short_resistance,
                short_risk: item.short_risk || w.short_risk,
                swing_support: item.swing_support || w.swing_support,
                swing_resistance: item.swing_resistance || w.swing_resistance,
                swing_risk: item.swing_risk || w.swing_risk,
                long_support: item.long_support || w.long_support,
                long_resistance: item.long_resistance || w.long_resistance,
                long_risk: item.long_risk || w.long_risk,
              };
            }
            return w;
          }));
          
          if (data.timestamp) {
            setLastPricesUpdate(data.timestamp);
          }
        }
      }
    } catch (error) {
      console.error("获取实时数据失败:", error);
    }
  }, [getToken, watchlist]);

  // 批量计算所有标的的价位数据（重量级，手动触发）
  const refreshAllPrices = useCallback(async () => {
    const token = getToken();
    if (!token || watchlist.length === 0) return;
    
    setPricesRefreshing(true);
    
    try {
      const symbols = watchlist.map(item => item.symbol);
      
      // 调用计算接口
      const response = await fetch(`${API_BASE}/api/watchlist/calculate-prices`, {
        method: 'POST',
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ symbols, force: true })
      });
      
      if (response.ok) {
        const data = await response.json();
        
        if (data.async) {
          // 异步处理，显示提示
          showAlertModal("计算中", `正在后台计算 ${symbols.length} 个标的的价位，请稍后刷新查看`, "info");
        } else if (data.results) {
          // 同步处理完成，更新本地状态
          setWatchlist(prev => prev.map(item => {
            const result = data.results[item.symbol];
            if (result && !result.error && result.prices) {
              return {
                ...item,
                short_support: result.prices.short?.support,
                short_resistance: result.prices.short?.resistance,
                short_risk: result.prices.short?.risk,
                swing_support: result.prices.swing?.support,
                swing_resistance: result.prices.swing?.resistance,
                swing_risk: result.prices.swing?.risk,
                long_support: result.prices.long?.support,
                long_resistance: result.prices.long?.resistance,
                long_risk: result.prices.long?.risk,
              };
            }
            return item;
          }));
          
          if (data.timestamp) {
            setLastPricesUpdate(data.timestamp);
          }
          
          showAlertModal("刷新完成", `已更新 ${Object.keys(data.results).length} 个标的的价位数据`, "success");
        }
      }
    } catch (error) {
      console.error("刷新价位失败:", error);
      showAlertModal("刷新失败", "请稍后重试", "error");
    } finally {
      setPricesRefreshing(false);
    }
  }, [getToken, watchlist, showAlertModal]);

  // 获取实时交易信号
  const fetchRealtimeSignals = useCallback(async (forceRefresh: boolean = false) => {
    const token = getToken();
    if (!token || watchlist.length === 0) return;

    try {
      // 如果是强制刷新，获取所有标的；否则只获取没有信号的标的
      const symbolsToUpdate = forceRefresh 
        ? watchlist.map(item => item.symbol)
        : watchlist
            .filter(item => !item.short_signal || !item.swing_signal || !item.long_signal)
            .map(item => item.symbol);
      
      if (symbolsToUpdate.length === 0) return;
      
      if (forceRefresh) {
        setSignalRefreshing(true);
      }
      
      // 分批获取，每批最多10个
      const batchSize = 10;
      for (let i = 0; i < symbolsToUpdate.length; i += batchSize) {
        const batch = symbolsToUpdate.slice(i, i + batchSize);
        const symbols = batch.join(",");
        
        const response = await fetch(`${API_BASE}/api/signals/realtime?symbols=${encodeURIComponent(symbols)}`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (response.ok) {
          const data = await response.json();
          if (data.signals) {
            // 更新本地状态
            setWatchlist(prev => prev.map(item => {
              const signal = data.signals[item.symbol];
              if (signal && !signal.error) {
                return {
                  ...item,
                  short_signal: signal.short?.signal || item.short_signal,
                  swing_signal: signal.swing?.signal || item.swing_signal,
                  long_signal: signal.long?.signal || item.long_signal,
                };
              }
              return item;
            }));
            // 更新最后刷新时间
            if (data.timestamp) {
              setLastSignalUpdate(data.timestamp);
            }
          }
        }
        
        // 批次间延迟，避免请求过快
        if (i + batchSize < symbolsToUpdate.length) {
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      }
    } catch (error) {
      console.error("获取实时信号失败:", error);
    } finally {
      setSignalRefreshing(false);
    }
  }, [getToken, watchlist]);

  // 获取用户设置
  const fetchUserSettings = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/user/settings`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (response.ok) {
        const data = await response.json();
        setUserSettings(data.settings);
        setWechatOpenId(data.settings?.wechat_openid || "");
      }
    } catch (error) {
      console.error("获取用户设置失败:", error);
    }
  }, [getToken]);

  // 更新用户设置
  const handleSaveSettings = useCallback(async () => {
    setSettingsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/user/settings?wechat_openid=${encodeURIComponent(wechatOpenId)}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      
      if (response.ok) {
        showAlertModal("保存成功", "微信 OpenID 已保存，您将收到价格提醒推送", "success");
        fetchUserSettings();
      } else {
        const data = await response.json();
        showAlertModal("保存失败", data.detail || "请检查 OpenID 是否正确", "error");
      }
    } catch (error) {
      showAlertModal("保存失败", "网络错误，请稍后重试", "error");
    } finally {
      setSettingsLoading(false);
    }
  }, [getToken, wechatOpenId, showAlertModal, fetchUserSettings]);

  // 测试推送
  const handleTestPush = useCallback(async () => {
    if (!wechatOpenId.trim()) {
      showAlertModal("请输入 OpenID", "请先输入您的微信 OpenID 再测试", "warning");
      return;
    }
    
    setTestPushLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/user/test-push?openid=${encodeURIComponent(wechatOpenId)}&push_type=wechat`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      
      const data = await response.json();
      if (response.ok) {
        showAlertModal("测试成功", "测试消息已发送，请查看微信公众号消息", "success");
        fetchUserSettings();
      } else {
        showAlertModal("测试失败", data.detail || "推送失败，请检查 OpenID 是否正确", "error");
      }
    } catch (error) {
      showAlertModal("测试失败", "网络错误，请稍后重试", "error");
    } finally {
      setTestPushLoading(false);
    }
  }, [getToken, wechatOpenId, showAlertModal, fetchUserSettings]);

  // 获取研究列表
  const [aiPicksPermissionDenied, setAiPicksPermissionDenied] = useState(false);
  const fetchAiPicks = useCallback(async () => {
    setAiPicksLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/ai-picks`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (response.ok) {
        const data = await response.json();
        setAiPicks(data.picks || []);
        setAiPicksPermissionDenied(false);
      } else if (response.status === 403) {
        // 无权限
        setAiPicks([]);
        setAiPicksPermissionDenied(true);
      }
    } catch (error) {
      console.error("获取研究列表失败:", error);
    } finally {
      setAiPicksLoading(false);
    }
  }, [getToken]);

  // 打开研究列表弹窗 - 定义在后面（需要 canUseFeatures）
  const handleOpenAiPicksRef = useRef<() => void>(() => {});

  // 切换研究列表选中状态
  const toggleAiPickSelect = useCallback((symbol: string) => {
    setSelectedAiPicks(prev => {
      const next = new Set(prev);
      if (next.has(symbol)) {
        next.delete(symbol);
      } else {
        next.add(symbol);
      }
      return next;
    });
  }, []);

  // 全选/取消全选研究列表（只针对可用的，即用户还没添加到自选的）
  const toggleSelectAllAiPicks = useCallback(() => {
    setSelectedAiPicks(prev => {
      if (prev.size === availableAiPicks.length) {
        return new Set();
      }
      return new Set(availableAiPicks.map(p => p.symbol));
    });
  }, [availableAiPicks]);

  // 添加选中的研究列表到自选
  const handleAddAiPicksToWatchlist = useCallback(async () => {
    if (selectedAiPicks.size === 0) {
      showAlertModal("请选择标的", "请至少选择一个标的添加到自选", "warning");
      return;
    }

    const items = availableAiPicks
      .filter(p => selectedAiPicks.has(p.symbol))
      .map(p => ({ symbol: p.symbol, name: p.name, type: p.type, from_ai_pick: 1 }));

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/watchlist/batch`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(items),
      });

      if (response.ok) {
        const data = await response.json();
        
        // 标记这些标的为已处理（用户不再看到）
        const symbolsToDissmiss = items.map(i => i.symbol);
        await fetch(`${API_BASE}/api/ai-picks/dismiss-batch`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({ symbols: symbolsToDissmiss }),
        });
        
        setShowAiPicksModal(false);
        setSelectedAiPicks(new Set());
        fetchWatchlist();
        fetchAiPicks();  // 刷新研究列表
        
        if (data.skipped && data.skipped.length > 0) {
          showAlertModal(
            "部分标的已存在",
            `已跳过 ${data.skipped.length} 个已存在的标的，成功添加 ${data.added?.length || 0} 个`,
            "info"
          );
        } else {
          showAlertModal("添加成功", `成功添加 ${data.added?.length || 0} 个标的到自选`, "success");
        }
      }
    } catch (error) {
      showAlertModal("添加失败", "网络错误，请稍后重试", "error");
    } finally {
      setLoading(false);
    }
  }, [selectedAiPicks, availableAiPicks, getToken, fetchWatchlist, fetchAiPicks, showAlertModal]);

  // 添加标的到研究列表（管理员）
  const handleAddToAiPicks = useCallback(async (symbol: string, name: string, type: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/ai-picks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ symbol, name, type }),
      });

      if (response.ok) {
        showAlertModal("添加成功", `${symbol} 已添加到研究列表`, "success");
      } else {
        const data = await response.json();
        showAlertModal("添加失败", data.detail || "添加失败", "error");
      }
    } catch (error) {
      showAlertModal("添加失败", "网络错误，请稍后重试", "error");
    }
  }, [getToken, showAlertModal]);

  // 从研究列表移除（管理员 - 全局删除）
  const handleRemoveFromAiPicks = useCallback(async (symbol: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/ai-picks/${encodeURIComponent(symbol)}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${getToken()}` },
      });

      if (response.ok) {
        showAlertModal("移除成功", `${symbol} 已从研究列表移除（全局）`, "success");
        fetchAiPicks();
      } else {
        const data = await response.json();
        showAlertModal("移除失败", data.detail || "移除失败", "error");
      }
    } catch (error) {
      showAlertModal("移除失败", "网络错误，请稍后重试", "error");
    }
  }, [getToken, showAlertModal, fetchAiPicks]);

  // 用户从研究列表中移除单个标的（仅对自己隐藏）
  const handleDismissAiPick = useCallback(async (symbol: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/ai-picks/dismiss`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ symbol }),
      });

      if (response.ok) {
        fetchAiPicks();
      } else {
        const data = await response.json();
        showAlertModal("移除失败", data.detail || "移除失败", "error");
      }
    } catch (error) {
      showAlertModal("移除失败", "网络错误，请稍后重试", "error");
    }
  }, [getToken, showAlertModal, fetchAiPicks]);

  // 用户批量移除选中的研究列表
  const handleDismissSelectedAiPicks = useCallback(async () => {
    if (selectedAiPicks.size === 0) {
      showAlertModal("请选择标的", "请至少选择一个标的", "warning");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/ai-picks/dismiss-batch`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ symbols: Array.from(selectedAiPicks) }),
      });

      if (response.ok) {
        const data = await response.json();
        setSelectedAiPicks(new Set());
        fetchAiPicks();
        showAlertModal("移除成功", `已移除 ${data.count || selectedAiPicks.size} 个标的`, "success");
      } else {
        const data = await response.json();
        showAlertModal("移除失败", data.detail || "移除失败", "error");
      }
    } catch (error) {
      showAlertModal("移除失败", "网络错误，请稍后重试", "error");
    } finally {
      setLoading(false);
    }
  }, [selectedAiPicks, getToken, showAlertModal, fetchAiPicks]);

  // 用户清空所有研究列表
  const handleDismissAllAiPicks = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/ai-picks/dismiss-all`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken()}` },
      });

      if (response.ok) {
        const data = await response.json();
        setSelectedAiPicks(new Set());
        fetchAiPicks();
        showAlertModal("清空成功", `已清空 ${data.count || 0} 个标的`, "success");
      } else {
        const data = await response.json();
        showAlertModal("清空失败", data.detail || "清空失败", "error");
      }
    } catch (error) {
      showAlertModal("清空失败", "网络错误，请稍后重试", "error");
    } finally {
      setLoading(false);
    }
  }, [getToken, showAlertModal, fetchAiPicks]);

  const hasActiveTasks = useMemo(() => {
    return Object.values(tasks).some((t) => t.status === "running" || t.status === "pending");
  }, [tasks]);

  useEffect(() => {
    if (authChecked) {
      // 如果初始数据已经在 checkAuth 中加载过，跳过重复加载
      if (!initialDataLoadedRef.current) {
        fetchDashboardInit();
      }
      // 获取研究列表（用于显示角标）
      fetchAiPicks();

      // 根据是否有活跃任务调整轮询频率
      // 有活跃任务时3秒轮询，无活跃任务时30秒轮询
      const intervalMs = hasActiveTasks ? 3000 : 30000;
      const interval = setInterval(() => {
        if (document.visibilityState !== "visible") return;
        // 只轮询任务状态，报告在任务完成时刷新
        fetchTasks();
      }, intervalMs);

      return () => clearInterval(interval);
    }
  }, [authChecked, fetchDashboardInit, fetchTasks, fetchAiPicks, hasActiveTasks]);

  useEffect(() => {
    if (authChecked && watchlist.length > 0) {
      // 立即获取一次实时数据（行情+价位）
      fetchRealtimeData();
      // 获取实时信号（首次加载时）
      fetchRealtimeSignals();
      
      // 根据是否交易时间动态调整刷新频率
      // 交易时间: 1秒刷新一次行情
      // 非交易时间: 30秒刷新一次
      let quoteInterval: NodeJS.Timeout;
      let signalInterval: NodeJS.Timeout;
      
      const setupInterval = () => {
        const interval = isTradingTime() ? 1000 : 30000;
        quoteInterval = setInterval(() => {
          if (document.visibilityState !== "visible") return;
          fetchRealtimeData();
        }, interval);
        
        // 信号更新频率：交易时间5分钟，非交易时间30分钟
        const signalIntervalMs = isTradingTime() ? 300000 : 1800000;
        signalInterval = setInterval(() => {
          if (document.visibilityState !== "visible") return;
          fetchRealtimeSignals();
        }, signalIntervalMs);
      };
      
      setupInterval();
      
      // 每分钟检查一次是否需要调整刷新频率
      const checkInterval = setInterval(() => {
        clearInterval(quoteInterval);
        clearInterval(signalInterval);
        setupInterval();
      }, 60000);

      return () => {
        clearInterval(quoteInterval);
        clearInterval(signalInterval);
        clearInterval(checkInterval);
      };
    }
  }, [authChecked, watchlist.length, fetchRealtimeData, fetchRealtimeSignals, isTradingTime]);

  const handleLogout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setUser(null);
    window.location.href = "/login";
  }, []);

  const toggleSelect = useCallback((symbol: string) => {
    setSelectedItems((prev) => {
      const next = new Set(prev);
      if (next.has(symbol)) {
        next.delete(symbol);
      } else {
        next.add(symbol);
      }
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    setSelectedItems((prev) => {
      if (prev.size === watchlist.length) {
        return new Set();
      }
      return new Set(watchlist.map((item) => item.symbol));
    });
  }, [watchlist]);

  const canUseFeatures = useCallback(() => {
    return user && (user.status === "approved" || user.role === "admin");
  }, [user]);

  const showPendingAlert = useCallback(() => {
    showAlertModal(
      "账户待审核",
      "您的账户正在等待管理员审核，审核通过后即可使用所有功能。",
      "warning"
    );
  }, [showAlertModal]);

  // 手动刷新所有信号
  const handleRefreshSignals = useCallback(() => {
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }
    fetchRealtimeSignals(true);
  }, [canUseFeatures, showPendingAlert, fetchRealtimeSignals]);

  // 打开研究列表弹窗
  const handleOpenAiPicks = useCallback(() => {
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }
    setSelectedAiPicks(new Set());
    fetchAiPicks();
    setShowAiPicksModal(true);
  }, [canUseFeatures, showPendingAlert, fetchAiPicks]);

  // 更新 ref
  useEffect(() => {
    handleOpenAiPicksRef.current = handleOpenAiPicks;
  }, [handleOpenAiPicks]);

  const checkPermissionAndRun = (callback: () => void) => {
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }
    callback();
  };

  const handleSort = useCallback((field: string) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  }, [sortField, sortOrder]);

  // 报告映射表 - 需要在 sortedWatchlist 之前定义，因为排序需要用到
  const reportsBySymbol = useMemo(() => {
    const map: Record<string, ReportSummary> = {};
    for (const r of reports) {
      // 原始 symbol 作为 key
      map[r.symbol] = r;
      // 同时添加点号和下划线两种格式的映射，确保能匹配到
      // 例如：SPAX_PVT 和 SPAX.PVT 都能找到同一个报告
      const symbolWithDot = r.symbol.replace(/_/g, '.');
      const symbolWithUnderscore = r.symbol.replace(/\./g, '_');
      if (symbolWithDot !== r.symbol) {
        map[symbolWithDot] = r;
      }
      if (symbolWithUnderscore !== r.symbol) {
        map[symbolWithUnderscore] = r;
      }
    }
    return map;
  }, [reports]);

  const sortedWatchlist = useMemo(() => {
    let sorted = [...watchlist];
    
    // 搜索过滤
    if (searchQuery.trim()) {
      const query = searchQuery.trim().toLowerCase();
      sorted = sorted.filter(item => 
        item.symbol.toLowerCase().includes(query) ||
        (item.name && item.name.toLowerCase().includes(query))
      );
    }
    
    // 周期筛选
    if (periodFilter !== "all") {
      sorted = sorted.filter(item => item.holding_period === periodFilter);
    }
    
    // 信号类型筛选（根据当前显示周期筛选）
    if (ratingFilter !== "all") {
      sorted = sorted.filter(item => {
        // 获取当前显示周期的信号
        const displayPeriod = itemDisplayPeriods[item.symbol] || item.holding_period || 'swing';
        const signal = (displayPeriod === 'short' ? item.short_signal : 
                       displayPeriod === 'long' ? item.long_signal : 
                       item.swing_signal) || '';
        const s = signal.toLowerCase();
        switch (ratingFilter) {
          case 'buy':
            return s === 'buy' || s === '买入';
          case 'sell':
            return s === 'sell' || s === '卖出';
          case 'hold':
            return s === 'hold' || s === '观望' || !signal;
          default:
            return true;
        }
      });
    }
    
    sorted.sort((a, b) => (b.starred || 0) - (a.starred || 0));
    
    if (sortField && quotes) {
      sorted.sort((a, b) => {
        if ((a.starred || 0) !== (b.starred || 0)) {
          return (b.starred || 0) - (a.starred || 0);
        }
        
        let aVal = 0, bVal = 0;
        const aQuote = quotes[a.symbol];
        const bQuote = quotes[b.symbol];
        
        if (sortField === "change_percent") {
          aVal = aQuote?.change_percent || 0;
          bVal = bQuote?.change_percent || 0;
        } else if (sortField === "position") {
          aVal = a.position || 0;
          bVal = b.position || 0;
        } else if (sortField === "ai_buy_price") {
          // 支撑位排序：按距离当前价的百分比绝对值排序（由近到远）
          const aPrice = aQuote?.current_price || 0;
          const bPrice = bQuote?.current_price || 0;
          // 获取当前显示周期的支撑位
          const aDisplayPeriod = itemDisplayPeriods[a.symbol] || a.holding_period || 'swing';
          const bDisplayPeriod = itemDisplayPeriods[b.symbol] || b.holding_period || 'swing';
          const aSupport = (aDisplayPeriod === 'short' ? a.short_support : 
                           aDisplayPeriod === 'long' ? a.long_support : 
                           a.swing_support) || a.ai_buy_price || 0;
          const bSupport = (bDisplayPeriod === 'short' ? b.short_support : 
                           bDisplayPeriod === 'long' ? b.long_support : 
                           b.swing_support) || b.ai_buy_price || 0;
          // 计算距离百分比绝对值：|当前价 - 支撑位| / 当前价 * 100
          aVal = aSupport > 0 && aPrice > 0 ? Math.abs((aPrice - aSupport) / aPrice * 100) : Infinity;
          bVal = bSupport > 0 && bPrice > 0 ? Math.abs((bPrice - bSupport) / bPrice * 100) : Infinity;
        } else if (sortField === "ai_sell_price") {
          // 阻力位排序：按距离当前价的百分比绝对值排序（由近到远）
          const aPrice = aQuote?.current_price || 0;
          const bPrice = bQuote?.current_price || 0;
          // 获取当前显示周期的阻力位
          const aDisplayPeriod = itemDisplayPeriods[a.symbol] || a.holding_period || 'swing';
          const bDisplayPeriod = itemDisplayPeriods[b.symbol] || b.holding_period || 'swing';
          const aResistance = (aDisplayPeriod === 'short' ? a.short_resistance : 
                              aDisplayPeriod === 'long' ? a.long_resistance : 
                              a.swing_resistance) || a.ai_sell_price || 0;
          const bResistance = (bDisplayPeriod === 'short' ? b.short_resistance : 
                              bDisplayPeriod === 'long' ? b.long_resistance : 
                              b.swing_resistance) || b.ai_sell_price || 0;
          // 计算距离百分比绝对值：|阻力位 - 当前价| / 当前价 * 100
          aVal = aResistance > 0 && aPrice > 0 ? Math.abs((aResistance - aPrice) / aPrice * 100) : Infinity;
          bVal = bResistance > 0 && bPrice > 0 ? Math.abs((bResistance - bPrice) / bPrice * 100) : Infinity;
        } else if (sortField === "report_time") {
          // 报告更新时间排序
          const aReport = reportsBySymbol[a.symbol] || reportsBySymbol[a.symbol.replace(/\./g, '_')] || reportsBySymbol[a.symbol.replace(/_/g, '.')];
          const bReport = reportsBySymbol[b.symbol] || reportsBySymbol[b.symbol.replace(/\./g, '_')] || reportsBySymbol[b.symbol.replace(/_/g, '.')];
          aVal = aReport?.created_at ? new Date(aReport.created_at).getTime() : 0;
          bVal = bReport?.created_at ? new Date(bReport.created_at).getTime() : 0;
        }
        
        return sortOrder === "asc" ? aVal - bVal : bVal - aVal;
      });
    }
    
    return sorted;
  }, [watchlist, sortField, sortOrder, quotes, searchQuery, periodFilter, ratingFilter, reportsBySymbol, itemDisplayPeriods]);

  const pagedWatchlist = useMemo(() => {
    return sortedWatchlist.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  }, [sortedWatchlist, currentPage, pageSize]);

  const handleToggleStar = useCallback(async (symbol: string) => {
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }
    
    try {
      const response = await fetch(`${API_BASE}/api/watchlist/${encodeURIComponent(symbol)}/star`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      
      if (response.ok) {
        fetchWatchlist();
      }
    } catch (error) {
      console.error("切换关注失败:", error);
    }
  }, [canUseFeatures, fetchWatchlist, getToken, showPendingAlert]);

  const handleAddSymbol = useCallback(async (closeAfterAdd: boolean = true) => {
    if (!addSymbol.trim()) return;
    
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }

    const symbolToAdd = addSymbol.trim().toUpperCase();
    const positionVal = addPosition && parseFloat(addPosition) > 0 ? parseFloat(addPosition) : undefined;
    const costPriceVal = addCostPrice && parseFloat(addCostPrice) > 0 ? parseFloat(addCostPrice) : undefined;

    // 保存当前的研究列表状态
    const shouldAddAsAiPick = addAsAiPick && user?.role === 'admin';

    // 检查是否已存在于自选列表
    const existsInWatchlist = watchlist.some(item => item.symbol === symbolToAdd);
    // 检查是否已存在于研究列表
    const existsInAiPicks = aiPicks.some(item => item.symbol === symbolToAdd);

    // 如果勾选了研究列表，需要检查两个列表
    if (shouldAddAsAiPick) {
      if (existsInWatchlist && existsInAiPicks) {
        showAlertModal("已存在", `${symbolToAdd} 已在自选列表和研究列表中，不能重复添加`, "warning");
        return;
      }
    } else {
      // 没勾选研究列表，只检查自选列表
      if (existsInWatchlist) {
        showAlertModal("已存在", `${symbolToAdd} 已在自选列表中`, "warning");
        return;
      }
    }

    // 乐观更新：如果自选列表不存在，立即添加到列表
    const optimisticItem: WatchlistItem = {
      symbol: symbolToAdd,
      name: symbolToAdd,
      type: 'stock',
      added_at: new Date().toISOString(),
      position: positionVal,
      cost_price: costPriceVal,
    };
    
    flushSync(() => {
      if (!existsInWatchlist) {
        setWatchlist(prev => [optimisticItem, ...prev]);
      }
      setAddSymbol("");
      setAddPosition("");
      setAddCostPrice("");
      if (closeAfterAdd) {
        setShowAddModal(false);
        setAddAsAiPick(false);
      }
    });

    // 记录添加结果
    let watchlistAdded = false;
    let aiPicksAdded = false;
    let addedName = symbolToAdd;

    // 添加到自选列表（如果不存在）
    if (!existsInWatchlist) {
      try {
        const payload: any = { symbol: symbolToAdd };
        if (positionVal) payload.position = positionVal;
        if (costPriceVal) payload.cost_price = costPriceVal;

        const response = await fetch(`${API_BASE}/api/watchlist`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify(payload),
        });

        const data = await response.json();
        if (response.ok && data.status === "success") {
          watchlistAdded = true;
          addedName = data.name || symbolToAdd;
          fetchWatchlist();
        } else {
          // 添加失败，回滚
          setWatchlist(prev => prev.filter(item => item.symbol !== symbolToAdd));
        }
      } catch (error) {
        // 网络错误，回滚
        setWatchlist(prev => prev.filter(item => item.symbol !== symbolToAdd));
      }
    }

    // 添加到研究列表（如果勾选了且不存在）
    if (shouldAddAsAiPick && !existsInAiPicks) {
      try {
        const response = await fetch(`${API_BASE}/api/ai-picks`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({ symbol: symbolToAdd, name: addedName, type: 'stock' }),
        });

        if (response.ok) {
          aiPicksAdded = true;
          // 刷新研究列表
          fetchAiPicks();
        }
      } catch (error) {
        // 静默失败
      }
    }

    // 显示结果提示
    if (shouldAddAsAiPick) {
      if (existsInWatchlist && aiPicksAdded) {
        showAlertModal("添加成功", `${symbolToAdd} 已存在于自选列表，已添加到研究列表`, "success");
      } else if (watchlistAdded && existsInAiPicks) {
        showAlertModal("添加成功", `${symbolToAdd} 已添加到自选列表，研究列表已存在`, "success");
      } else if (watchlistAdded && aiPicksAdded) {
        showAlertModal("添加成功", `${symbolToAdd} 已添加到自选列表和研究列表`, "success");
      } else if (watchlistAdded) {
        showAlertModal("部分成功", `${symbolToAdd} 已添加到自选列表，研究列表添加失败`, "warning");
      } else if (aiPicksAdded) {
        showAlertModal("部分成功", `${symbolToAdd} 自选添加失败，已添加到研究列表`, "warning");
      } else {
        showAlertModal("添加失败", "网络错误，请稍后重试", "error");
      }
    } else {
      // 没勾选研究列表，只提示自选结果
      if (!closeAfterAdd) {
        if (watchlistAdded) {
          showAlertModal("添加成功", `${symbolToAdd} 已添加到自选，可继续添加下一个`, "success");
        } else {
          showAlertModal("添加失败", "网络错误，请稍后重试", "error");
        }
      }
    }
  }, [addCostPrice, addPosition, addSymbol, addAsAiPick, user, canUseFeatures, fetchWatchlist, fetchAiPicks, getToken, showPendingAlert, showAlertModal, watchlist, aiPicks]);

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    if (!canUseFeatures()) {
      showPendingAlert();
      e.target.value = "";
      return;
    }

    if (files.length > 10) {
      alert("最多只能上传10张图片");
      e.target.value = "";
      return;
    }

    setOcrLoading(true);
    const formData = new FormData();
    
    for (let i = 0; i < files.length; i++) {
      formData.append("files", files[i]);
    }

    try {
      const response = await fetch(`${API_BASE}/api/ocr/recognize`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getToken()}`,
        },
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        const results = (data.recognized || []).map((item: any) => ({
          ...item,
          selected: true,
        }));
        
        if (results.length > 0) {
          setOcrResults(results);
          setShowAddModal(false);
          setShowOcrModal(true);
        } else {
          alert(`已分析 ${data.image_count || files.length} 张图片，未识别到任何股票代码`);
        }
      } else {
        const errData = await response.json().catch(() => ({}));
        alert(errData.detail || "识别失败，请重试");
      }
    } catch (error) {
      console.error("OCR 识别失败:", error);
      alert("识别失败，请检查网络后重试");
    } finally {
      setOcrLoading(false);
      e.target.value = "";
    }
  };

  const toggleOcrResult = (index: number) => {
    setOcrResults(prev => prev.map((item, i) => 
      i === index ? { ...item, selected: !item.selected } : item
    ));
  };

  const handleAddOcrResults = async () => {
    const selectedSymbols = ocrResults
      .filter(item => item.selected)
      .map(item => ({
        symbol: item.symbol,
        name: item.name,
        type: item.type,
        position: item.position,
        cost_price: item.cost_price,
      }));

    if (selectedSymbols.length === 0) {
      alert("请选择至少一个标的");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/watchlist/batch`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(selectedSymbols),
      });

      if (response.ok) {
        const data = await response.json();
        setShowOcrModal(false);
        setOcrResults([]);
        fetchWatchlist();
        
        // 如果有重复的标的，显示提示
        if (data.skipped && data.skipped.length > 0) {
          showAlertModal(
            "部分标的已存在",
            `以下标的已在自选列表中，已跳过：\n${data.skipped.join("、")}\n\n成功添加 ${data.added?.length || 0} 个标的`
          );
        }
      }
    } catch (error) {
      console.error("批量添加失败:", error);
    } finally {
      setLoading(false);
    }
  };

  const updateOcrPosition = (index: number, field: 'position' | 'cost_price', value: string) => {
    setOcrResults(prev => prev.map((item, i) =>
      i === index ? { ...item, [field]: value ? parseFloat(value) : undefined } : item
    ));
  };

  const handleDeleteSingle = useCallback((symbol: string) => {
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }
    
    // 检查是否正在分析中
    const task = tasksRef.current[symbol];
    if (task && (task.status === "running" || task.status === "pending")) {
      showAlertModal("无法删除", `${symbol} 正在分析中，请等待分析完成后再删除`, "warning");
      return;
    }
    
    // 使用 flushSync 强制同步更新 UI，确保立即响应
    flushSync(() => {
      setWatchlist(prev => prev.filter(item => item.symbol !== symbol));
      setSelectedItems(prev => {
        const next = new Set(prev);
        next.delete(symbol);
        return next;
      });
    });
    
    // 后台异步删除
    fetch(`${API_BASE}/api/watchlist/${encodeURIComponent(symbol)}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${getToken()}` },
    }).catch(() => {
      // 静默失败，下次刷新会恢复
    });
  }, [canUseFeatures, getToken, showPendingAlert, showAlertModal]);

  const handleBatchDelete = useCallback(() => {
    if (selectedItems.size === 0) return;
    
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }

    // 检查是否有正在分析中的标的
    const analyzingSymbols = Array.from(selectedItems).filter(symbol => {
      const task = tasksRef.current[symbol];
      return task && (task.status === "running" || task.status === "pending");
    });
    
    if (analyzingSymbols.length > 0) {
      showAlertModal(
        "无法删除",
        `以下标的正在分析中：${analyzingSymbols.join("、")}，请等待分析完成后再删除`,
        "warning"
      );
      return;
    }

    // 使用 flushSync 强制同步更新 UI
    const symbolsToDelete = Array.from(selectedItems);
    flushSync(() => {
      setWatchlist(prev => prev.filter(item => !selectedItems.has(item.symbol)));
      setSelectedItems(new Set());
    });

    // 后台异步删除
    fetch(`${API_BASE}/api/watchlist/batch-delete`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify(symbolsToDelete),
    }).catch(() => {
      // 静默失败
    });
  }, [canUseFeatures, getToken, selectedItems, showPendingAlert, showAlertModal]);

  const handleAnalyzeSingle = useCallback(async (symbol: string) => {
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }

    // 检查是否正在分析中
    const task = tasksRef.current[symbol];
    if (task && (task.status === "running" || task.status === "pending")) {
      showAlertModal("正在分析中", `${symbol} 正在分析中，请等待分析完成`, "warning");
      return;
    }

    // 弹窗选择持有周期
    setPendingAnalysisSymbols([symbol]);
    setIsBatchAnalysis(false);
    setHoldingPeriod("short");
    setShowHoldingPeriodModal(true);
  }, [canUseFeatures, showPendingAlert, showAlertModal]);

  // 实际执行单个分析
  const executeAnalyzeSingle = useCallback(async (symbol: string, period: string) => {
    // 重置该标的的错误状态
    setShownErrorTasks(prev => {
      const next = new Set(prev);
      next.delete(symbol);
      return next;
    });

    const existing = tasksRef.current[symbol];
    const optimisticTaskId = existing?.task_id || `optimistic-${Date.now()}`;
    setTasks((prev) => ({
      ...prev,
      [symbol]: {
        task_id: optimisticTaskId,
        symbol,
        status: "running",
        progress: 0,
        current_step: "分析中",
        updated_at: new Date().toISOString(),
      },
    }));

    try {
      const response = await fetch(`${API_BASE}/api/analyze/background`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ ticker: symbol, holding_period: period }),
      });

      if (!response.ok) {
        const msg = await getErrorMessageFromResponse(response);
        setTasks((prev) => {
          const next = { ...prev };
          if (existing) {
            next[symbol] = existing;
          } else {
            delete next[symbol];
          }
          return next;
        });
        showAlertModal("分析失败", msg, "error");
        return;
      }

      const data = await response.json().catch(() => ({}));
      if (data?.task_id) {
        setTasks((prev) => ({
          ...prev,
          [symbol]: {
            task_id: data.task_id,
            symbol: data.symbol || symbol,
            status: "running",
            progress: 0,
            current_step: "分析中",
            updated_at: new Date().toISOString(),
          },
        }));
      }

      fetchTasks();
    } catch (error) {
      console.error("启动分析失败:", error);
      setTasks((prev) => {
        const next = { ...prev };
        if (existing) {
          next[symbol] = existing;
        } else {
          delete next[symbol];
        }
        return next;
      });
      showAlertModal("分析失败", error instanceof Error ? error.message : "网络错误，请稍后重试", "error");
    }
  }, [fetchTasks, getErrorMessageFromResponse, getToken, showAlertModal]);

  const handleBatchAnalyze = useCallback(async () => {
    if (selectedItems.size === 0) return;
    
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }
    
    // 过滤掉正在分析中的标的
    const symbolsToAnalyze = Array.from(selectedItems).filter(symbol => {
      const task = tasksRef.current[symbol];
      return !(task && (task.status === "running" || task.status === "pending"));
    });
    
    if (symbolsToAnalyze.length === 0) {
      showAlertModal("全部在分析中", "所选标的都在分析中，请等待分析完成", "warning");
      return;
    }
    
    const skippedCount = selectedItems.size - symbolsToAnalyze.length;
    if (skippedCount > 0) {
      showAlertModal("部分跳过", `已跳过 ${skippedCount} 个正在分析中的标的，将分析剩余 ${symbolsToAnalyze.length} 个`, "info");
    }
    
    // 弹窗选择持有周期
    setPendingAnalysisSymbols(symbolsToAnalyze);
    setIsBatchAnalysis(true);
    setHoldingPeriod("short");
    setShowHoldingPeriodModal(true);
  }, [canUseFeatures, selectedItems, showPendingAlert, showAlertModal]);

  // 实际执行批量分析
  const executeBatchAnalyze = useCallback(async (symbols: string[], period: string) => {
    // 重置错误状态
    setShownErrorTasks(new Set());
    
    const prevTasks: Record<string, TaskStatus | undefined> = {};
    for (const sym of symbols) {
      prevTasks[sym] = tasksRef.current[sym];
    }

    setTasks((prev) => {
      const next = { ...prev };
      for (const sym of symbols) {
        const optimisticTaskId = next[sym]?.task_id || `optimistic-${Date.now()}-${sym}`;
        next[sym] = {
          task_id: optimisticTaskId,
          symbol: sym,
          status: "running",
          progress: 0,
          current_step: "分析中",
          updated_at: new Date().toISOString(),
        };
      }
      return next;
    });

    try {
      const response = await fetch(`${API_BASE}/api/analyze/batch`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ symbols, holding_period: period }),
      });

      if (!response.ok) {
        const msg = await getErrorMessageFromResponse(response);
        setTasks((prev) => {
          const next = { ...prev };
          for (const sym of symbols) {
            const old = prevTasks[sym];
            if (old) {
              next[sym] = old;
            } else {
              delete next[sym];
            }
          }
          return next;
        });
        showAlertModal("批量分析失败", msg, "error");
        return;
      }

      const data = await response.json().catch(() => ({}));
      if (Array.isArray(data?.tasks)) {
        setTasks((prev) => {
          const next = { ...prev };
          for (const t of data.tasks) {
            if (!t?.symbol) continue;
            next[t.symbol] = {
              task_id: t.task_id,
              symbol: t.symbol,
              status: "running",
              progress: 0,
              current_step: "分析中",
              updated_at: new Date().toISOString(),
            };
          }
          return next;
        });
      }

      fetchTasks();
    } catch (error) {
      console.error("批量分析失败:", error);
      setTasks((prev) => {
        const next = { ...prev };
        for (const sym of symbols) {
          const old = prevTasks[sym];
          if (old) {
            next[sym] = old;
          } else {
            delete next[sym];
          }
        }
        return next;
      });
      showAlertModal("批量分析失败", error instanceof Error ? error.message : "网络错误，请稍后重试", "error");
    }
  }, [fetchTasks, getErrorMessageFromResponse, getToken, showAlertModal]);

  // 确认持有周期后执行分析
  const handleConfirmHoldingPeriod = useCallback(() => {
    setShowHoldingPeriodModal(false);
    if (isBatchAnalysis) {
      executeBatchAnalyze(pendingAnalysisSymbols, holdingPeriod);
    } else if (pendingAnalysisSymbols.length === 1) {
      executeAnalyzeSingle(pendingAnalysisSymbols[0], holdingPeriod);
    }
    setPendingAnalysisSymbols([]);
  }, [isBatchAnalysis, pendingAnalysisSymbols, holdingPeriod, executeBatchAnalyze, executeAnalyzeSingle]);

  const handleViewReport = useCallback((symbol: string) => {
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }
    // 将点号替换为下划线，避免URL解析问题（如 SPAX.PVT -> SPAX_PVT）
    const urlSymbol = symbol.replace(/\./g, '_');
    router.push(`/report/${encodeURIComponent(urlSymbol)}`);
  }, [canUseFeatures, router, showPendingAlert]);

  // 预加载报告页面
  const prefetchReport = useCallback((symbol: string) => {
    const urlSymbol = symbol.replace(/\./g, '_');
    router.prefetch(`/report/${encodeURIComponent(urlSymbol)}`);
  }, [router]);

  const getTaskStatus = (symbol: string): TaskStatus | null => {
    return tasks[symbol] || null;
  };

  const getReport = (symbol: string): ReportSummary | null => {
    return reportsBySymbol[symbol] || null;
  };

  const getTypeLabel = (type?: string) => {
    switch (type) {
      case "stock": return "股票";
      case "etf": return "ETF";
      case "fund": return "基金";
      case "lof": return "LOF";
      default: return type || "";
    }
  };

  const getHoldingPeriodLabel = (period?: string) => {
    switch (period) {
      case "short": return "短线";
      case "swing": return "波段";
      case "long": return "中长线";
      default: return "波段";
    }
  };

  // 打开编辑持仓弹窗
  const openEditPositionModal = useCallback((item: WatchlistItem) => {
    setEditingItem(item);
    setEditPosition(item.position?.toString() || "");
    setEditCostPrice(item.cost_price?.toString() || "");
    setEditHoldingPeriod(item.holding_period || "swing");
    setShowEditPositionModal(true);
  }, []);

  // 保存编辑的持仓信息
  const handleSavePosition = useCallback(async () => {
    if (!editingItem) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/watchlist/${encodeURIComponent(editingItem.symbol)}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          position: editPosition ? parseFloat(editPosition) : null,
          cost_price: editCostPrice ? parseFloat(editCostPrice) : null,
          holding_period: editHoldingPeriod,
        }),
      });

      if (response.ok) {
        setShowEditPositionModal(false);
        fetchWatchlist();
        showAlertModal("保存成功", "持仓信息已更新", "success");
      } else {
        const data = await response.json();
        showAlertModal("保存失败", data.detail || "请稍后重试", "error");
      }
    } catch (error) {
      showAlertModal("保存失败", "网络错误，请稍后重试", "error");
    } finally {
      setLoading(false);
    }
  }, [editingItem, editPosition, editCostPrice, editHoldingPeriod, getToken, fetchWatchlist, showAlertModal]);

  // 只有在没有缓存用户信息时才显示加载动画
  // 有缓存时直接显示页面，后台静默验证
  if (!authChecked && !user) {
    return (
      <main className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 sm:h-24 sm:w-24 border-b-4 border-indigo-500 mx-auto"></div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#020617] relative">
      {/* Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 -left-1/4 w-[400px] sm:w-[800px] h-[400px] sm:h-[800px] bg-indigo-500/5 rounded-full blur-[100px] sm:blur-[150px]" />
        <div className="absolute bottom-0 -right-1/4 w-[300px] sm:w-[600px] h-[300px] sm:h-[600px] bg-violet-500/5 rounded-full blur-[80px] sm:blur-[120px]" />
      </div>

      {/* Header - 移动端优化 */}
      <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-[#020617]/80 backdrop-blur-xl safe-area-top">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 py-3 sm:py-4 flex items-center justify-between">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg sm:rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 p-[1px]">
              <div className="w-full h-full rounded-lg sm:rounded-xl bg-[#020617] flex items-center justify-center">
                <Bot className="w-4 h-4 sm:w-5 sm:h-5 text-indigo-400" />
              </div>
            </div>
            <div>
              <h1 className="text-base sm:text-lg font-bold text-slate-100">数据研究工具</h1>
              <p className="text-[10px] sm:text-xs text-slate-500 hidden sm:block">个人学习研究用</p>
            </div>
          </div>

          {user && (
            <div className="flex items-center gap-2">
              {/* 模拟交易按钮 */}
              <button
                onClick={() => router.push('/sim-trade')}
                className="flex items-center gap-1.5 px-2.5 py-1.5 bg-gradient-to-r from-emerald-500/20 to-teal-500/20 border border-emerald-500/30 text-emerald-400 rounded-lg text-xs sm:text-sm hover:from-emerald-500/30 hover:to-teal-500/30 transition-all"
                title="模拟交易"
              >
                <TrendingUp className="w-4 h-4" />
                <span className="hidden sm:inline">模拟交易</span>
              </button>
              {/* 研究列表按钮 - 无权限时隐藏 */}
              {!aiPicksPermissionDenied && (
                <button
                  onClick={handleOpenAiPicks}
                  className="relative flex items-center gap-1.5 px-2.5 py-1.5 bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/30 text-amber-400 rounded-lg text-xs sm:text-sm hover:from-amber-500/30 hover:to-orange-500/30 transition-all"
                  title="研究列表"
                >
                  <Sparkles className="w-4 h-4" />
                  <span className="hidden sm:inline">研究列表</span>
                  {/* 新增数量角标 */}
                  {newAiPicksCount > 0 && (
                    <span className="absolute -top-3 -right-3 min-w-[24px] h-6 px-1.5 bg-red-500 text-white text-sm font-bold rounded-full flex items-center justify-center shadow-lg animate-pulse">
                      +{newAiPicksCount > 99 ? '99' : newAiPicksCount}
                    </span>
                  )}
                </button>
              )}
              <UserHeader user={user} onLogout={handleLogout} />
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <div className="relative z-10 px-3 sm:px-4 lg:px-6 py-4 sm:py-8">
        {/* 未审核用户提示 */}
        {user && user.status !== 'approved' && user.role !== 'admin' && (
          <div className="mb-4 sm:mb-6 p-3 sm:p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg sm:rounded-xl">
            <div className="flex items-center gap-2 sm:gap-3">
              <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-amber-500/20 flex items-center justify-center flex-shrink-0">
                <AlertCircle className="w-4 h-4 sm:w-5 sm:h-5 text-amber-400" />
              </div>
              <div className="min-w-0">
                <h3 className="text-xs sm:text-sm font-medium text-amber-400">账户待审核</h3>
                <p className="text-[10px] sm:text-xs text-amber-400/70 mt-0.5 truncate">
                  您的账户正在等待管理员审核
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Toolbar - 移动端优化 */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 mb-4 sm:mb-6">
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
            <h2 className="text-lg sm:text-xl font-semibold text-slate-100">我的自选</h2>
            <span className="text-xs sm:text-sm text-slate-500">
              ({(searchQuery || periodFilter !== "all") ? `${sortedWatchlist.length}/${watchlist.length}` : watchlist.length})
            </span>
            {/* 搜索框 */}
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1); // 搜索时重置到第一页
                }}
                placeholder="搜索代码/名称"
                className="w-32 sm:w-40 pl-8 pr-8 py-1.5 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 text-xs sm:text-sm"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 hover:bg-white/[0.1] rounded"
                >
                  <X className="w-3.5 h-3.5 text-slate-400" />
                </button>
              )}
            </div>
            {/* 周期筛选 */}
            <select
              value={periodFilter}
              onChange={(e) => {
                setPeriodFilter(e.target.value);
                setCurrentPage(1); // 筛选时重置到第一页
              }}
              className="px-2 py-1.5 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white focus:outline-none focus:ring-1 focus:ring-indigo-500/50 text-xs sm:text-sm cursor-pointer"
            >
              <option value="all" className="bg-slate-800">全部周期</option>
              <option value="short" className="bg-slate-800">短线</option>
              <option value="swing" className="bg-slate-800">波段</option>
              <option value="long" className="bg-slate-800">中长线</option>
            </select>
            {/* 信号类型筛选 */}
            <select
              value={ratingFilter}
              onChange={(e) => {
                setRatingFilter(e.target.value);
                setCurrentPage(1); // 筛选时重置到第一页
              }}
              className="px-2 py-1.5 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white focus:outline-none focus:ring-1 focus:ring-indigo-500/50 text-xs sm:text-sm cursor-pointer"
            >
              <option value="all" className="bg-slate-800">全部信号</option>
              <option value="buy" className="bg-slate-800">🟢 买入</option>
              <option value="sell" className="bg-slate-800">🔴 卖出</option>
              <option value="hold" className="bg-slate-800">⚪ 观望</option>
            </select>
            {/* 信号刷新按钮 */}
            <button
              onClick={handleRefreshSignals}
              disabled={signalRefreshing}
              className="flex items-center gap-1.5 px-2 py-1.5 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 rounded-lg transition-all disabled:opacity-50 text-xs sm:text-sm"
              title={lastSignalUpdate ? `上次更新: ${new Date(lastSignalUpdate).toLocaleTimeString('zh-CN')}` : '刷新信号'}
            >
              <RefreshCw className={`w-3.5 h-3.5 ${signalRefreshing ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">{signalRefreshing ? '刷新中...' : '刷新信号'}</span>
            </button>
            {/* 价位刷新按钮 */}
            <button
              onClick={refreshAllPrices}
              disabled={pricesRefreshing}
              className="flex items-center gap-1.5 px-2 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 rounded-lg transition-all disabled:opacity-50 text-xs sm:text-sm"
              title={lastPricesUpdate ? `上次更新: ${new Date(lastPricesUpdate).toLocaleTimeString('zh-CN')}` : '刷新价位'}
            >
              <TrendingUp className={`w-3.5 h-3.5 ${pricesRefreshing ? 'animate-pulse' : ''}`} />
              <span className="hidden sm:inline">{pricesRefreshing ? '刷新中...' : '刷新价位'}</span>
            </button>
            {/* 排序选择 */}
            <select
              value={sortField ? `${sortField}:${sortOrder}` : "default"}
              onChange={(e) => {
                const val = e.target.value;
                if (val === "default") {
                  setSortField(null);
                  setSortOrder("desc");
                } else {
                  const lastColonIndex = val.lastIndexOf(":");
                  const field = val.substring(0, lastColonIndex);
                  const order = val.substring(lastColonIndex + 1);
                  setSortField(field);
                  setSortOrder(order as "asc" | "desc");
                }
                setCurrentPage(1);
              }}
              className="px-2 py-1.5 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white focus:outline-none focus:ring-1 focus:ring-indigo-500/50 text-xs sm:text-sm cursor-pointer"
            >
              <option value="default" className="bg-slate-800">默认排序</option>
              <option value="change_percent:desc" className="bg-slate-800">涨跌幅↓</option>
              <option value="change_percent:asc" className="bg-slate-800">涨跌幅↑</option>
              <option value="ai_buy_price:asc" className="bg-slate-800">支撑位(近→远)</option>
              <option value="ai_buy_price:desc" className="bg-slate-800">支撑位(远→近)</option>
              <option value="ai_sell_price:asc" className="bg-slate-800">阻力位(近→远)</option>
              <option value="ai_sell_price:desc" className="bg-slate-800">阻力位(远→近)</option>
              <option value="report_time:desc" className="bg-slate-800">报告时间(新→旧)</option>
              <option value="report_time:asc" className="bg-slate-800">报告时间(旧→新)</option>
            </select>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {selectedItems.size > 0 && (
              <>
                <button
                  onClick={handleBatchAnalyze}
                  disabled={loading}
                  className="flex items-center gap-1.5 px-3 py-2 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-400 rounded-lg transition-all disabled:opacity-50 text-xs sm:text-sm"
                >
                  <Play className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">批量分析</span>
                  <span className="sm:hidden">分析</span>
                  <span>({selectedItems.size})</span>
                </button>
                <button
                  onClick={handleBatchDelete}
                  disabled={loading}
                  className="flex items-center gap-1.5 px-3 py-2 bg-rose-600/20 hover:bg-rose-600/30 text-rose-400 rounded-lg transition-all disabled:opacity-50 text-xs sm:text-sm"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">批量删除</span>
                </button>
              </>
            )}
            <button
              onClick={() => {
                if (!canUseFeatures()) {
                  showPendingAlert();
                  return;
                }
                setShowAddModal(true);
              }}
              className="flex items-center gap-1.5 px-3 py-2 bg-white/[0.05] hover:bg-white/[0.08] text-slate-300 rounded-lg transition-all text-xs sm:text-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>添加</span>
            </button>
            <button
              onClick={() => {
                fetchWatchlist();
                fetchTasks();
                fetchReports();
              }}
              className="p-2 bg-white/[0.05] hover:bg-white/[0.08] text-slate-400 rounded-lg transition-all"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Watchlist - 移动端卡片视图 */}
        <div className="glass-card rounded-xl sm:rounded-2xl border border-white/[0.06] overflow-hidden">
          {/* 桌面端表头 */}
          <div className="hidden md:block">
            <div className="flex items-center gap-5 px-6 py-4 border-b border-white/[0.06] bg-white/[0.02]">
              <div className="w-8 flex-shrink-0">
                <button onClick={toggleSelectAll} className="text-slate-400 hover:text-slate-200">
                  {selectedItems.size === watchlist.length && watchlist.length > 0 ? (
                    <CheckSquare className="w-5 h-5" />
                  ) : (
                    <Square className="w-5 h-5" />
                  )}
                </button>
              </div>
              <div className="w-40 flex-shrink-0 text-sm font-semibold text-slate-300">代码 / 名称</div>
              <div className="w-16 flex-shrink-0 text-sm font-semibold text-slate-300">类型</div>
              <div className="w-24 flex-shrink-0 text-sm font-semibold text-slate-300 text-right">当前价</div>
              <div 
                className="w-24 flex-shrink-0 text-sm font-semibold text-slate-300 text-right flex items-center justify-end gap-1 cursor-pointer hover:text-slate-200"
                onClick={() => handleSort("change_percent")}
              >
                涨跌幅
                {sortField === "change_percent" ? (
                  sortOrder === "asc" ? <ArrowUp className="w-3.5 h-3.5" /> : <ArrowDown className="w-3.5 h-3.5" />
                ) : (
                  <ArrowUpDown className="w-3.5 h-3.5 opacity-50" />
                )}
              </div>
              <div className="w-20 flex-shrink-0 text-sm font-semibold text-slate-300 text-right">持仓</div>
              <div className="w-24 flex-shrink-0 text-sm font-semibold text-slate-300 text-right">成本价</div>
              <div className="w-24 flex-shrink-0 text-sm font-semibold text-slate-300 text-right">持仓盈亏</div>
              <div className="w-16 flex-shrink-0 text-sm font-semibold text-slate-300">周期</div>
              <div className="w-20 flex-shrink-0 text-sm font-semibold text-indigo-400">信号类型</div>
              <div 
                className="w-28 flex-shrink-0 text-sm font-semibold text-emerald-400 text-right flex items-center justify-end gap-1 cursor-pointer hover:text-emerald-300"
                onClick={() => handleSort("ai_buy_price")}
                title="按与当前价的差距排序"
              >
                支撑位
                {sortField === "ai_buy_price" ? (
                  sortOrder === "asc" ? <ArrowUp className="w-3.5 h-3.5" /> : <ArrowDown className="w-3.5 h-3.5" />
                ) : (
                  <ArrowUpDown className="w-3.5 h-3.5 opacity-50" />
                )}
              </div>
              <div 
                className="w-28 flex-shrink-0 text-sm font-semibold text-rose-400 text-right flex items-center justify-end gap-1 cursor-pointer hover:text-rose-300"
                onClick={() => handleSort("ai_sell_price")}
                title="按与当前价的差距排序"
              >
                阻力位
                {sortField === "ai_sell_price" ? (
                  sortOrder === "asc" ? <ArrowUp className="w-3.5 h-3.5" /> : <ArrowDown className="w-3.5 h-3.5" />
                ) : (
                  <ArrowUpDown className="w-3.5 h-3.5 opacity-50" />
                )}
              </div>
              <div className="w-28 flex-shrink-0 text-sm font-semibold text-orange-400 text-right">风险位</div>
              <div className="w-20 flex-shrink-0 text-sm font-semibold text-slate-300">状态</div>
              <div className="flex-1 min-w-[220px] text-sm font-semibold text-slate-300 text-right">操作</div>
            </div>
          </div>

          {/* 列表内容 */}
          {watchlist.length === 0 ? (
            <div className="py-12 sm:py-16 text-center">
              <Bot className="w-12 h-12 sm:w-16 sm:h-16 text-slate-700 mx-auto mb-3 sm:mb-4" />
              <p className="text-slate-500 mb-2 text-sm sm:text-base">暂无自选标的</p>
              <button
                onClick={() => setShowAddModal(true)}
                className="text-indigo-400 hover:text-indigo-300 text-xs sm:text-sm"
              >
                点击添加自选
              </button>
            </div>
          ) : (
            <div className="divide-y divide-white/[0.04]">
              {pagedWatchlist.map((item) => {
                const task = getTaskStatus(item.symbol);
                const report = getReport(item.symbol);
                const isSelected = selectedItems.has(item.symbol);
                const quote = quotes[item.symbol];
                
                // 改进状态判断逻辑：
                // 1. 如果任务正在运行且超过10分钟没更新，视为超时失败
                // 2. 如果任务显示running但报告更新时间比任务更新时间新，说明已完成
                // 3. 如果任务显示completed，以任务状态为准
                const taskUpdatedAt = task?.updated_at ? new Date(task.updated_at).getTime() : 0;
                const reportCreatedAt = report?.created_at ? new Date(report.created_at).getTime() : 0;
                const isTaskTimeout = task?.status === "running" && task?.updated_at && 
                  (Date.now() - taskUpdatedAt > 10 * 60 * 1000);
                
                // 如果报告比任务更新时间新，说明分析已完成（任务状态可能还没同步）
                const isReportNewer = report && reportCreatedAt > taskUpdatedAt;
                
                // 最终状态判断
                const isFailed = (task?.status === "failed" || isTaskTimeout) && !isReportNewer;
                const isRunning = task?.status === "running" && !isTaskTimeout && !isReportNewer;
                const isPending = task?.status === "pending" && !isReportNewer;
                const isCompleted = task?.status === "completed" || isReportNewer;
                
                // 是否正在分析中（用于禁用分析按钮）
                const isAnalyzing = isRunning || isPending;

                return (
                  <div
                    key={item.symbol}
                    className={`p-3 sm:p-4 md:px-6 hover:bg-white/[0.02] transition-all ${
                      isSelected ? "bg-indigo-500/5" : ""
                    }`}
                  >
                    {/* 移动端布局 */}
                    <div className="md:hidden">
                      <div className="flex items-start gap-3">
                        <button
                          onClick={() => toggleSelect(item.symbol)}
                          className="text-slate-400 hover:text-slate-200 mt-1"
                        >
                          {isSelected ? (
                            <CheckSquare className="w-5 h-5 text-indigo-400" />
                          ) : (
                            <Square className="w-5 h-5" />
                          )}
                        </button>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-mono text-sm font-semibold text-slate-100">{item.symbol}</span>
                            {/* 研究列表标识 */}
                            {item.from_ai_pick === 1 && (
                              <span className="px-1.5 py-0.5 text-[10px] bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/30 text-amber-400 rounded flex items-center gap-0.5">
                                <Sparkles className="w-3 h-3" />
                                研究
                              </span>
                            )}
                            <button
                              onClick={() => handleToggleStar(item.symbol)}
                              className={`p-1.5 rounded-lg touch-target ${item.starred ? "text-amber-400 bg-amber-500/10" : "text-slate-500 bg-white/[0.05]"}`}
                            >
                              <Star className={`w-5 h-5 ${item.starred ? "fill-current" : ""}`} />
                            </button>
                            {item.type && (
                              <span className="px-1.5 py-0.5 text-[10px] bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded">
                                {getTypeLabel(item.type)}
                              </span>
                            )}
                          </div>
                          {item.name && (
                            <div className="text-xs text-slate-500 truncate mb-2">{item.name}</div>
                          )}
                          
                          {/* 价格信息 */}
                          <div className="flex flex-wrap items-center gap-4 mb-3">
                            <div className="min-w-[60px]">
                              <div className="text-[10px] text-slate-500 mb-0.5">当前价</div>
                              <span 
                                className="font-mono text-sm font-semibold"
                                style={{
                                  color: (quote?.change_percent || 0) > 0 ? "#f87171" : (quote?.change_percent || 0) < 0 ? "#34d399" : "#e2e8f0"
                                }}
                              >
                                {quote?.current_price?.toFixed(3) || "-"}
                              </span>
                            </div>
                            <div className="min-w-[60px]">
                              <div className="text-[10px] text-slate-500 mb-0.5">涨跌幅</div>
                              <span 
                                className="font-mono text-sm font-semibold"
                                style={{
                                  color: (quote?.change_percent || 0) > 0 ? "#f87171" : (quote?.change_percent || 0) < 0 ? "#34d399" : "#94a3b8"
                                }}
                              >
                                {quote?.change_percent !== undefined ? `${quote.change_percent > 0 ? "+" : ""}${quote.change_percent.toFixed(2)}%` : "-"}
                              </span>
                            </div>
                            <div className="min-w-[70px]">
                              <div className="text-[10px] text-slate-500 mb-0.5">持仓</div>
                              <span className="font-mono text-sm text-slate-200">{item.position?.toLocaleString() || "-"}</span>
                            </div>
                            <div className="min-w-[70px]">
                              <div className="text-[10px] text-slate-500 mb-0.5">成本</div>
                              <span className="font-mono text-sm text-slate-200">{item.cost_price ? `${getCurrencySymbol(item.symbol)}${item.cost_price.toFixed(3)}` : "-"}</span>
                            </div>
                            <div className="min-w-[70px]">
                              <div className="text-[10px] text-slate-500 mb-0.5">盈亏</div>
                              {item.position && item.cost_price && quote?.current_price ? (
                                (() => {
                                  const profitLoss = (quote.current_price - item.cost_price) * item.position;
                                  const isProfit = profitLoss >= 0;
                                  return (
                                    <span 
                                      className="font-mono text-sm font-semibold"
                                      style={{ color: isProfit ? "#f87171" : "#34d399" }}
                                    >
                                      {isProfit ? "+" : ""}{profitLoss.toFixed(2)}
                                    </span>
                                  );
                                })()
                              ) : (
                                <span className="text-sm text-slate-500">-</span>
                              )}
                            </div>
                            <div className="min-w-[50px]">
                              <div className="text-[10px] text-slate-500 mb-0.5">周期</div>
                              <button
                                onClick={() => toggleItemDisplayPeriod(item.symbol, getItemDisplayPeriod(item))}
                                disabled={loadingPrices.has(item.symbol)}
                                className={`px-1.5 py-0.5 text-[10px] rounded cursor-pointer hover:opacity-80 disabled:opacity-50 flex items-center gap-1 ${
                                  getItemDisplayPeriod(item) === 'short' ? 'bg-amber-500/10 text-amber-400' :
                                  getItemDisplayPeriod(item) === 'long' ? 'bg-violet-500/10 text-violet-400' :
                                  'bg-indigo-500/10 text-indigo-400'
                                }`}
                                title="点击切换周期（实时获取价位）"
                              >
                                {loadingPrices.has(item.symbol) && (
                                  <Loader2 className="w-2.5 h-2.5 animate-spin" />
                                )}
                                {getItemDisplayPeriod(item) === 'short' ? '短线' : 
                                 getItemDisplayPeriod(item) === 'long' ? '中长线' : '波段'}
                              </button>
                            </div>
                          </div>
                          
                          {/* 技术指标参考价位 - 移动端（始终显示预留空间） */}
                          <div className="flex flex-wrap items-start gap-4 mb-3 pt-2 border-t border-white/[0.05]">
                            <div className="min-w-[70px]">
                              <div className="text-xs text-indigo-400/80 mb-1">信号类型</div>
                              {(() => {
                                const signal = getPeriodSignal(item, getItemDisplayPeriod(item));
                                const display = getSignalDisplay(signal);
                                return (
                                  <span className={`px-2 py-1 text-sm rounded-md inline-flex items-center gap-1 ${display.style}`}>
                                    <span>{display.icon}</span>
                                    <span>{display.text}</span>
                                  </span>
                                );
                              })()}
                            </div>
                            <div className="min-w-[95px]">
                              <div className="text-xs text-emerald-400/80 mb-1">支撑位</div>
                              <div className="flex flex-col">
                                <span className={`font-mono text-base font-semibold ${(() => {
                                    const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                                    return getPriceValueColor(quote?.current_price, prices.support, 'support');
                                  })()}`}>
                                  {(() => {
                                    const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                                    return prices.support ? `${getCurrencySymbol(item.symbol)}${prices.support.toFixed(3)}` : "-";
                                  })()}
                                </span>
                                <span className="font-mono text-sm mt-0.5">
                                  {(() => {
                                    const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                                    const diff = getPriceDiff(quote?.current_price, prices.support, 'support');
                                    return diff ? <span className={diff.color}>{diff.text}</span> : "-";
                                  })()}
                                </span>
                              </div>
                            </div>
                            <div className="min-w-[95px]">
                              <div className="text-xs text-rose-400/80 mb-1">阻力位</div>
                              <div className="flex flex-col">
                                <span className={`font-mono text-base font-semibold ${(() => {
                                    const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                                    return getPriceValueColor(quote?.current_price, prices.resistance, 'resistance');
                                  })()}`}>
                                  {(() => {
                                    const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                                    return prices.resistance ? `${getCurrencySymbol(item.symbol)}${prices.resistance.toFixed(3)}` : "-";
                                  })()}
                                </span>
                                <span className="font-mono text-sm mt-0.5">
                                  {(() => {
                                    const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                                    const diff = getPriceDiff(quote?.current_price, prices.resistance, 'resistance');
                                    return diff ? <span className={diff.color}>{diff.text}</span> : "-";
                                  })()}
                                </span>
                              </div>
                            </div>
                            <div className="min-w-[95px]">
                              <div className="text-xs text-orange-400/80 mb-1">风险位</div>
                              <div className="flex flex-col">
                                <span className={`font-mono text-base font-semibold ${(() => {
                                    const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                                    return getPriceValueColor(quote?.current_price, prices.risk, 'risk');
                                  })()}`}>
                                  {(() => {
                                    const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                                    return prices.risk ? `${getCurrencySymbol(item.symbol)}${prices.risk.toFixed(3)}` : "-";
                                  })()}
                                </span>
                                <span className="font-mono text-sm mt-0.5">
                                  {(() => {
                                    const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                                    const diff = getPriceDiff(quote?.current_price, prices.risk, 'risk');
                                    return diff ? <span className={diff.color}>{diff.text}</span> : "-";
                                  })()}
                                </span>
                              </div>
                            </div>
                          </div>
                          
                          {/* 操作按钮 - 移动端竖向排列 */}
                          <div className="flex flex-col gap-2">
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleAnalyzeSingle(item.symbol)}
                                disabled={isRunning || isPending}
                                className={`flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm rounded-xl transition-all disabled:opacity-50 min-w-[90px] touch-target ${
                                  isFailed 
                                    ? "bg-rose-600/20 text-rose-400 active:bg-rose-600/30" 
                                    : (isRunning || isPending)
                                    ? "bg-amber-600/20 text-amber-400"
                                    : "bg-indigo-600/20 text-indigo-400 active:bg-indigo-600/30"
                                }`}
                              >
                                {(isRunning || isPending) ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <Play className="w-4 h-4" />
                                )}
                                {isRunning ? `${task?.progress}%` : isPending ? "排队中" : isFailed ? "重新分析" : "AI分析"}
                              </button>
                              
                              {report && (
                                <div className="flex flex-col">
                                  <button
                                    onClick={() => handleViewReport(item.symbol)}
                                    onTouchStart={() => prefetchReport(item.symbol)}
                                    className="flex items-center justify-center gap-1.5 px-4 py-2.5 bg-emerald-600/20 text-emerald-400 text-sm rounded-xl min-w-[90px] touch-target active:bg-emerald-600/30"
                                  >
                                    <FileText className="w-4 h-4" />
                                    AI报告
                                  </button>
                                  <span className="text-[10px] text-slate-500 text-center mt-1">
                                    {(() => {
                                      const d = new Date(report.created_at);
                                      return `${d.getFullYear()}/${String(d.getMonth()+1).padStart(2,'0')}/${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
                                    })()}
                                  </span>
                                </div>
                              )}
                            </div>
                            
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => openEditPositionModal(item)}
                                className="flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm rounded-xl min-w-[70px] touch-target bg-white/[0.05] text-slate-400 active:bg-white/[0.1]"
                              >
                                <Edit3 className="w-4 h-4" />
                                编辑
                              </button>
                              
                              <button
                                onClick={() => handleDeleteSingle(item.symbol)}
                                disabled={isRunning || isPending}
                                className={`flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm rounded-xl min-w-[70px] touch-target ${
                                  isRunning || isPending
                                    ? "bg-slate-700/30 text-slate-600 cursor-not-allowed"
                                    : "bg-white/[0.05] text-slate-400 hover:text-rose-400 active:bg-rose-600/20"
                                }`}
                              >
                                <Trash2 className="w-4 h-4" />
                                删除
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 桌面端布局 */}
                    <div className="hidden md:flex items-center gap-5 py-1">
                      <div className="w-8 flex-shrink-0">
                        <button onClick={() => toggleSelect(item.symbol)} className="text-slate-400 hover:text-slate-200">
                          {isSelected ? <CheckSquare className="w-5 h-5 text-indigo-400" /> : <Square className="w-5 h-5" />}
                        </button>
                      </div>

                      <div className="w-40 flex-shrink-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-base font-bold text-slate-50 truncate">{item.symbol}</span>
                          {/* 研究列表标识 */}
                          {item.from_ai_pick === 1 && (
                            <span className="px-1.5 py-0.5 text-[10px] bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/30 text-amber-400 rounded flex items-center gap-0.5 whitespace-nowrap">
                              <Sparkles className="w-3 h-3" />
                              研究
                            </span>
                          )}
                          <button
                            onClick={() => handleToggleStar(item.symbol)}
                            className={`p-0.5 ${item.starred ? "text-amber-400" : "text-slate-600 hover:text-amber-400"}`}
                          >
                            <Star className={`w-4 h-4 ${item.starred ? "fill-current" : ""}`} />
                          </button>
                        </div>
                        {item.name && <div className="text-sm text-slate-400 truncate mt-0.5">{item.name}</div>}
                      </div>

                      <div className="w-16 flex-shrink-0">
                        {item.type && (
                          <span className="px-2.5 py-1 text-sm bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-md">
                            {getTypeLabel(item.type)}
                          </span>
                        )}
                      </div>

                      <div className="w-24 flex-shrink-0 text-right">
                        <span 
                          className="font-mono text-base font-bold"
                          style={{ color: (quote?.change_percent || 0) > 0 ? "#f87171" : (quote?.change_percent || 0) < 0 ? "#34d399" : "#f1f5f9" }}
                        >
                          {quote?.current_price?.toFixed(3) || "-"}
                        </span>
                      </div>

                      <div className="w-24 flex-shrink-0 text-right">
                        <span 
                          className="font-mono text-base font-bold"
                          style={{ color: (quote?.change_percent || 0) > 0 ? "#f87171" : (quote?.change_percent || 0) < 0 ? "#34d399" : "#94a3b8" }}
                        >
                          {quote?.change_percent !== undefined ? `${quote.change_percent > 0 ? "+" : ""}${quote.change_percent.toFixed(2)}%` : "-"}
                        </span>
                      </div>

                      <div className="w-20 flex-shrink-0 text-right">
                        <span className="font-mono text-base text-slate-100">{item.position?.toLocaleString() || "-"}</span>
                      </div>

                      <div className="w-24 flex-shrink-0 text-right">
                        <span className="font-mono text-base text-slate-100">{item.cost_price ? `${getCurrencySymbol(item.symbol)}${item.cost_price.toFixed(3)}` : "-"}</span>
                      </div>

                      {/* 持仓盈亏 */}
                      <div className="w-24 flex-shrink-0 text-right">
                        {item.position && item.cost_price && quote?.current_price ? (
                          (() => {
                            const profitLoss = (quote.current_price - item.cost_price) * item.position;
                            const isProfit = profitLoss >= 0;
                            return (
                              <span 
                                className="font-mono text-base font-bold"
                                style={{ color: isProfit ? "#f87171" : "#34d399" }}
                              >
                                {isProfit ? "+" : ""}{profitLoss.toFixed(2)}
                              </span>
                            );
                          })()
                        ) : (
                          <span className="text-sm text-slate-500">-</span>
                        )}
                      </div>

                      {/* 持有周期 - 可点击切换 */}
                      <div className="w-16 flex-shrink-0">
                        <button
                          onClick={() => toggleItemDisplayPeriod(item.symbol, getItemDisplayPeriod(item))}
                          disabled={loadingPrices.has(item.symbol)}
                          className={`px-2.5 py-1 text-sm rounded-md cursor-pointer hover:opacity-80 transition-opacity disabled:opacity-50 flex items-center gap-1 ${
                            getItemDisplayPeriod(item) === 'short' ? 'bg-amber-500/10 text-amber-400' :
                            getItemDisplayPeriod(item) === 'long' ? 'bg-violet-500/10 text-violet-400' :
                            'bg-indigo-500/10 text-indigo-400'
                          }`}
                          title="点击切换周期（实时获取价位）"
                        >
                          {loadingPrices.has(item.symbol) && (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          )}
                          {getItemDisplayPeriod(item) === 'short' ? '短线' : 
                           getItemDisplayPeriod(item) === 'long' ? '中长线' : '波段'}
                        </button>
                      </div>

                      {/* 信号类型 */}
                      <div className="w-20 flex-shrink-0">
                        {(() => {
                          const signal = getPeriodSignal(item, getItemDisplayPeriod(item));
                          const display = getSignalDisplay(signal);
                          return (
                            <span className={`px-2.5 py-1.5 text-sm rounded-md whitespace-nowrap inline-flex items-center gap-1 ${display.style}`}>
                              <span>{display.icon}</span>
                              <span>{display.text}</span>
                            </span>
                          );
                        })()}
                      </div>

                      {/* 支撑位 - 根据选择的周期显示 */}
                      <div className="w-28 flex-shrink-0 text-right">
                        <div className="flex flex-col">
                          <span className={`font-mono text-base font-semibold ${(() => {
                              const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                              return getPriceValueColor(quote?.current_price, prices.support, 'support');
                            })()}`}>
                            {(() => {
                              const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                              return prices.support ? `${getCurrencySymbol(item.symbol)}${prices.support.toFixed(3)}` : "-";
                            })()}
                          </span>
                          <span className="font-mono text-sm">
                            {(() => {
                              const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                              const diff = getPriceDiff(quote?.current_price, prices.support, 'support');
                              return diff ? <span className={diff.color}>{diff.text}</span> : "-";
                            })()}
                          </span>
                        </div>
                      </div>

                      {/* 阻力位 - 根据选择的周期显示 */}
                      <div className="w-28 flex-shrink-0 text-right">
                        <div className="flex flex-col">
                          <span className={`font-mono text-base font-semibold ${(() => {
                              const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                              return getPriceValueColor(quote?.current_price, prices.resistance, 'resistance');
                            })()}`}>
                            {(() => {
                              const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                              return prices.resistance ? `${getCurrencySymbol(item.symbol)}${prices.resistance.toFixed(3)}` : "-";
                            })()}
                          </span>
                          <span className="font-mono text-sm">
                            {(() => {
                              const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                              const diff = getPriceDiff(quote?.current_price, prices.resistance, 'resistance');
                              return diff ? <span className={diff.color}>{diff.text}</span> : "-";
                            })()}
                          </span>
                        </div>
                      </div>

                      {/* 风险位 - 根据选择的周期显示 */}
                      <div className="w-28 flex-shrink-0 text-right">
                        <div className="flex flex-col">
                          <span className={`font-mono text-base font-semibold ${(() => {
                              const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                              return getPriceValueColor(quote?.current_price, prices.risk, 'risk');
                            })()}`}>
                            {(() => {
                              const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                              return prices.risk ? `${getCurrencySymbol(item.symbol)}${prices.risk.toFixed(3)}` : "-";
                            })()}
                          </span>
                          <span className="font-mono text-sm">
                            {(() => {
                              const prices = getPeriodPrices(item, getItemDisplayPeriod(item));
                              const diff = getPriceDiff(quote?.current_price, prices.risk, 'risk');
                              return diff ? <span className={diff.color}>{diff.text}</span> : "-";
                            })()}
                          </span>
                        </div>
                      </div>

                      <div className="w-20 flex-shrink-0">
                        {isFailed ? (
                          <div className="flex items-center gap-1.5 text-rose-400">
                            <AlertCircle className="w-4 h-4" />
                            <span className="text-sm font-medium">失败</span>
                          </div>
                        ) : isRunning ? (
                          <div className="flex items-center gap-1.5 text-amber-400">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span className="text-sm font-medium">{task?.progress}%</span>
                          </div>
                        ) : isPending ? (
                          <div className="flex items-center gap-1.5 text-amber-400">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span className="text-sm font-medium">分析中</span>
                          </div>
                        ) : report ? (
                          <div className="flex items-center gap-1.5 text-emerald-400">
                            <Check className="w-4 h-4" />
                            <span className="text-sm font-medium">完成</span>
                          </div>
                        ) : (
                          <span className="text-sm text-slate-500">未分析</span>
                        )}
                      </div>

                      <div className="flex-1 min-w-[220px] flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleAnalyzeSingle(item.symbol)}
                          disabled={isRunning || isPending}
                          className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-all disabled:opacity-50 ${
                            isFailed ? "bg-rose-600/20 text-rose-400 hover:bg-rose-600/30" : "bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30"
                          }`}
                        >
                          <Play className="w-5 h-5" />
                          {isFailed ? "重试" : "AI分析"}
                        </button>

                        {report && (
                          <div className="flex flex-col items-center">
                            <button
                              onClick={() => handleViewReport(item.symbol)}
                              onMouseEnter={() => prefetchReport(item.symbol)}
                              className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600/20 text-emerald-400 text-sm rounded-lg hover:bg-emerald-600/30 transition-colors"
                            >
                              <FileText className="w-5 h-5" />
                              AI报告
                            </button>
                            <span className="text-[10px] text-slate-500 mt-0.5">
                              {(() => {
                                const d = new Date(report.created_at);
                                return `${d.getFullYear()}/${String(d.getMonth()+1).padStart(2,'0')}/${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
                              })()}
                            </span>
                          </div>
                        )}

                        <button
                          onClick={() => openEditPositionModal(item)}
                          className="p-2 rounded-lg text-slate-500 hover:text-indigo-400 hover:bg-indigo-600/20"
                          title="编辑"
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>

                        <button
                          onClick={() => handleDeleteSingle(item.symbol)}
                          disabled={isRunning || isPending}
                          className={`p-2 rounded-lg ${
                            isRunning || isPending
                              ? "text-slate-600 cursor-not-allowed"
                              : "hover:bg-rose-600/20 text-slate-500 hover:text-rose-400"
                          }`}
                          title="删除"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* 分页 */}
          {watchlist.length > 0 && (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-3 sm:px-6 py-3 sm:py-4 border-t border-white/[0.06] bg-white/[0.02]">
              <div className="flex items-center gap-2 sm:gap-4 text-xs sm:text-sm text-slate-500">
                <span>共 {watchlist.length} 条</span>
                <select
                  value={pageSize}
                  onChange={(e) => { setPageSize(Number(e.target.value)); setCurrentPage(1); }}
                  className="px-2 py-1 bg-white/[0.05] border border-white/[0.1] rounded text-slate-300 focus:outline-none text-xs sm:text-sm"
                >
                  <option value={10} className="bg-slate-800">10条/页</option>
                  <option value={20} className="bg-slate-800">20条/页</option>
                  <option value={50} className="bg-slate-800">50条/页</option>
                  <option value={100} className="bg-slate-800">100条/页</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1.5 bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 rounded text-xs sm:text-sm disabled:opacity-50"
                >
                  上一页
                </button>
                <span className="text-xs sm:text-sm text-slate-500">{currentPage}/{Math.ceil(watchlist.length / pageSize) || 1}</span>
                <button
                  onClick={() => setCurrentPage(p => Math.min(Math.ceil(watchlist.length / pageSize), p + 1))}
                  disabled={currentPage >= Math.ceil(watchlist.length / pageSize)}
                  className="px-3 py-1.5 bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 rounded text-xs sm:text-sm disabled:opacity-50"
                >
                  下一页
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 添加自选弹窗 */}
      <AnimatePresence>
        {showAddModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center z-50"
            onClick={() => setShowAddModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              className="glass-card rounded-t-2xl sm:rounded-2xl border border-white/[0.08] p-4 sm:p-6 w-full sm:max-w-md sm:mx-4 max-h-[85vh] overflow-y-auto safe-area-bottom"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base sm:text-lg font-semibold text-white">添加自选</h3>
                <button onClick={() => setShowAddModal(false)} className="p-1 hover:bg-white/[0.05] rounded-lg">
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              <div className="relative mb-4">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  type="text"
                  value={addSymbol}
                  onChange={(e) => setAddSymbol(e.target.value)}
                  placeholder="输入股票/ETF/基金代码"
                  className="w-full pl-10 pr-4 py-3 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-sm sm:text-base"
                  onKeyDown={(e) => e.key === "Enter" && handleAddSymbol()}
                />
              </div>

              <div className="grid grid-cols-2 gap-3 mb-4">
                <div>
                  <label className="text-[10px] sm:text-xs text-slate-500 mb-1 block">持仓数量（可选）</label>
                  <input
                    type="number"
                    value={addPosition}
                    onChange={(e) => setAddPosition(e.target.value)}
                    placeholder="如：1000"
                    className="w-full px-3 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-sm"
                  />
                </div>
                <div>
                  <label className="text-[10px] sm:text-xs text-slate-500 mb-1 block">成本价（可选）</label>
                  <input
                    type="number"
                    step="0.01"
                    value={addCostPrice}
                    onChange={(e) => setAddCostPrice(e.target.value)}
                    placeholder="如：10.50"
                    className="w-full px-3 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-sm"
                  />
                </div>
              </div>

              {/* 管理员：研究列表勾选框 */}
              {user?.role === 'admin' && (
                <div className="mb-4">
                  <label 
                    className="flex items-center gap-2 cursor-pointer p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl hover:bg-amber-500/15 transition-all"
                    onClick={() => setAddAsAiPick(!addAsAiPick)}
                  >
                    <div className="text-amber-400">
                      {addAsAiPick ? <CheckSquare className="w-5 h-5" /> : <Square className="w-5 h-5" />}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-amber-400" />
                        <span className="text-sm font-medium text-amber-400">同时添加到研究列表</span>
                      </div>
                      <p className="text-[10px] text-slate-500 mt-0.5">共享给所有已审核用户查看</p>
                    </div>
                  </label>
                </div>
              )}

              <div className="flex gap-3 mb-4">
                <button
                  onClick={() => handleAddSymbol(true)}
                  disabled={loading || !addSymbol.trim()}
                  className="flex-1 py-2.5 sm:py-3 bg-white/[0.05] border border-white/[0.08] text-slate-300 rounded-xl hover:bg-white/[0.08] disabled:opacity-50 text-sm sm:text-base"
                >
                  {loading ? "添加中..." : "添加"}
                </button>
                <button
                  onClick={() => handleAddSymbol(false)}
                  disabled={loading || !addSymbol.trim()}
                  className="flex-1 py-2.5 sm:py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-500 disabled:opacity-50 text-sm sm:text-base"
                >
                  {loading ? "添加中..." : "继续添加"}
                </button>
              </div>

              <div className="relative my-4">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/[0.06]"></div>
                </div>
                <div className="relative flex justify-center text-xs sm:text-sm">
                  <span className="px-3 bg-[#0f172a] text-slate-500">或者</span>
                </div>
              </div>

              <label className="block cursor-pointer">
                <div className={`border-2 border-dashed border-white/[0.1] rounded-xl p-4 sm:p-6 text-center hover:border-indigo-500/40 hover:bg-indigo-500/5 transition-all ${ocrLoading ? 'pointer-events-none opacity-50' : ''}`}>
                  {ocrLoading ? (
                    <div className="flex flex-col items-center">
                      <Loader2 className="w-8 h-8 sm:w-10 sm:h-10 text-indigo-400 animate-spin mb-2" />
                      <p className="text-slate-400 text-sm">AI 识别中...</p>
                    </div>
                  ) : (
                    <>
                      <Camera className="w-8 h-8 sm:w-10 sm:h-10 text-indigo-400/60 mx-auto mb-2" />
                      <p className="text-slate-400 mb-1 text-sm">上传截图自动识别</p>
                      <p className="text-slate-600 text-[10px] sm:text-xs">支持多选，最多10张图片</p>
                    </>
                  )}
                </div>
                <input type="file" accept="image/*" multiple onChange={handleImageUpload} className="hidden" disabled={ocrLoading} />
              </label>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* OCR 结果弹窗 */}
      <AnimatePresence>
        {showOcrModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center z-50"
            onClick={() => setShowOcrModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              className="glass-card rounded-t-2xl sm:rounded-2xl border border-white/[0.08] p-4 sm:p-6 w-full sm:max-w-lg sm:mx-4 max-h-[85vh] overflow-hidden flex flex-col safe-area-bottom"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base sm:text-lg font-semibold text-white">
                  识别结果 ({ocrResults.filter(r => r.selected).length}/{ocrResults.length})
                </h3>
                <button onClick={() => setShowOcrModal(false)} className="p-1 hover:bg-white/[0.05] rounded-lg">
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              <p className="text-slate-500 text-xs sm:text-sm mb-4">请选择要添加到自选的标的</p>

              {/* 免责提示 */}
              <div className="mb-4 p-2.5 bg-amber-500/5 border border-amber-500/20 rounded-lg">
                <p className="text-amber-400/80 text-[10px] sm:text-xs leading-relaxed">
                  ⚠️ 本功能仅用于从图片中提取证券代码，便于添加到研究列表。识别结果不代表任何投资建议或推荐。
                  <span className="text-rose-400"> 🚫 严禁转发、截图保存或分享。</span>
                </p>
              </div>

              <div className="flex-1 overflow-y-auto space-y-2 sm:space-y-3 mb-4">
                {ocrResults.map((item, index) => (
                  <div
                    key={index}
                    className={`p-3 rounded-xl transition-all ${
                      item.selected ? "bg-indigo-500/10 border border-indigo-500/20" : "bg-white/[0.02] border border-white/[0.06]"
                    }`}
                  >
                    <div className="flex items-center gap-3 cursor-pointer" onClick={() => toggleOcrResult(index)}>
                      <div className="text-slate-300">
                        {item.selected ? <CheckSquare className="w-5 h-5 text-indigo-400" /> : <Square className="w-5 h-5" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-mono font-semibold text-white text-sm">{item.symbol}</div>
                        {item.name && <div className="text-xs text-slate-500 truncate">{item.name}</div>}
                      </div>
                      {item.type && (
                        <span className="px-2 py-1 text-[10px] sm:text-xs bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded flex-shrink-0">
                          {item.type === "stock" ? "股票" : item.type === "etf" ? "ETF" : "基金"}
                        </span>
                      )}
                    </div>
                    {item.selected && (
                      <div className="mt-3 pt-3 border-t border-white/[0.06] grid grid-cols-2 gap-2">
                        <input
                          type="number"
                          placeholder="持仓数量"
                          value={item.position || ""}
                          onClick={(e) => e.stopPropagation()}
                          onChange={(e) => updateOcrPosition(index, 'position', e.target.value)}
                          className="px-2.5 py-1.5 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white placeholder-slate-500 focus:outline-none text-xs sm:text-sm"
                        />
                        <input
                          type="number"
                          step="0.01"
                          placeholder="成本价"
                          value={item.cost_price || ""}
                          onClick={(e) => e.stopPropagation()}
                          onChange={(e) => updateOcrPosition(index, 'cost_price', e.target.value)}
                          className="px-2.5 py-1.5 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white placeholder-slate-500 focus:outline-none text-xs sm:text-sm"
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setShowOcrModal(false)}
                  className="flex-1 py-2.5 sm:py-3 bg-white/[0.05] border border-white/[0.08] text-slate-300 rounded-xl text-sm sm:text-base"
                >
                  取消
                </button>
                <button
                  onClick={handleAddOcrResults}
                  disabled={loading || ocrResults.filter(r => r.selected).length === 0}
                  className="flex-1 py-2.5 sm:py-3 bg-indigo-600 text-white rounded-xl disabled:opacity-50 text-sm sm:text-base"
                >
                  {loading ? "添加中..." : `添加 ${ocrResults.filter(r => r.selected).length} 个`}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 设置弹窗 */}
      <AnimatePresence>
        {showSettingsModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center z-50"
            onClick={() => setShowSettingsModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              className="glass-card rounded-t-2xl sm:rounded-2xl border border-white/[0.08] p-4 sm:p-6 w-full sm:max-w-md sm:mx-4 max-h-[85vh] overflow-y-auto safe-area-bottom"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base sm:text-lg font-semibold text-white flex items-center gap-2">
                  <Settings className="w-5 h-5 text-indigo-400" />
                  推送设置
                </h3>
                <button onClick={() => setShowSettingsModal(false)} className="p-1 hover:bg-white/[0.05] rounded-lg">
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              {/* 微信公众号说明 */}
              <div className="mb-4 p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
                <div className="flex items-start gap-2">
                  <MessageSquare className="w-5 h-5 text-indigo-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-medium text-indigo-400 mb-1">微信公众号推送</h4>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      本系统使用微信测试公众号实现消息推送，每天可推送 10 万条消息，完全免费。
                    </p>
                  </div>
                </div>
              </div>

              {/* 操作指引 */}
              <div className="mb-4 p-3 bg-white/[0.02] border border-white/[0.06] rounded-xl">
                <h4 className="text-sm font-medium text-slate-300 mb-2">绑定步骤</h4>
                <ol className="text-xs text-slate-400 space-y-2">
                  <li className="flex items-start gap-2">
                    <span className="w-5 h-5 bg-indigo-600 text-white rounded-full flex items-center justify-center flex-shrink-0 text-[10px]">1</span>
                    <span>微信扫描下方二维码关注测试公众号</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-5 h-5 bg-indigo-600 text-white rounded-full flex items-center justify-center flex-shrink-0 text-[10px]">2</span>
                    <span>关注后自动回复您的 OpenID（或发送任意消息获取）</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-5 h-5 bg-indigo-600 text-white rounded-full flex items-center justify-center flex-shrink-0 text-[10px]">3</span>
                    <span>复制 OpenID 填入下方输入框并保存</span>
                  </li>
                </ol>
                {/* 公众号二维码 */}
                <div className="mt-3 flex flex-col items-center">
                  <div className="p-2 bg-white rounded-lg">
                    <img 
                      src="/wechat-qrcode.png" 
                      alt="微信公众号二维码" 
                      className="w-32 h-32"
                    />
                  </div>
                  <p className="text-xs text-slate-500 mt-2">扫码关注「AI智能投资提醒」公众号</p>
                </div>
              </div>

              {/* OpenID 输入 */}
              <div className="mb-4">
                <label className="text-xs sm:text-sm text-slate-400 mb-2 block">微信 OpenID</label>
                <input
                  type="text"
                  value={wechatOpenId}
                  onChange={(e) => setWechatOpenId(e.target.value)}
                  placeholder="请输入您的微信 OpenID（关注公众号后获取）"
                  className="w-full px-3 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-sm font-mono"
                />
                <p className="text-[10px] text-slate-500 mt-1">OpenID 格式类似：oZqdM3GW6B******************</p>
              </div>

              {/* 状态显示 */}
              {userSettings?.wechat_configured && (
                <div className="mb-4 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
                  <div className="flex items-center gap-2">
                    <Check className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm text-emerald-400">已配置微信推送</span>
                  </div>
                </div>
              )}

              {/* 操作按钮 */}
              <div className="flex gap-3">
                <button
                  onClick={handleTestPush}
                  disabled={testPushLoading || !wechatOpenId.trim()}
                  className="flex-1 py-2.5 sm:py-3 bg-white/[0.05] border border-white/[0.08] text-slate-300 rounded-xl text-sm sm:text-base disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {testPushLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <MessageSquare className="w-4 h-4" />
                  )}
                  测试推送
                </button>
                <button
                  onClick={handleSaveSettings}
                  disabled={settingsLoading || !wechatOpenId.trim()}
                  className="flex-1 py-2.5 sm:py-3 bg-indigo-600 text-white rounded-xl disabled:opacity-50 text-sm sm:text-base flex items-center justify-center gap-2"
                >
                  {settingsLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Check className="w-4 h-4" />
                  )}
                  保存设置
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 持有周期选择弹窗 */}
      <AnimatePresence>
        {showHoldingPeriodModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center z-50"
            onClick={() => setShowHoldingPeriodModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              className="glass-card rounded-t-2xl sm:rounded-2xl border border-white/[0.08] p-4 sm:p-6 w-full sm:max-w-md sm:mx-4 safe-area-bottom"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base sm:text-lg font-semibold text-white flex items-center gap-2">
                  <Clock className="w-5 h-5 text-indigo-400" />
                  选择持有周期
                </h3>
                <button onClick={() => setShowHoldingPeriodModal(false)} className="p-1 hover:bg-white/[0.05] rounded-lg">
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              <p className="text-sm text-slate-400 mb-4">
                {isBatchAnalysis 
                  ? `即将分析 ${pendingAnalysisSymbols.length} 个标的，请选择持有周期：`
                  : `即将分析 ${pendingAnalysisSymbols[0]}，请选择持有周期：`
                }
              </p>

              <div className="space-y-3 mb-6">
                {[
                  { v: "short", l: "短线", desc: "1-5天", detail: "适合快进快出，关注日内波动和短期技术指标" },
                  { v: "swing", l: "波段", desc: "1-4周", detail: "适合波段操作，关注周线趋势和中期支撑阻力" },
                  { v: "long", l: "中长线", desc: "1月以上", detail: "适合价值投资，关注基本面和长期趋势" }
                ].map(({ v, l, desc, detail }) => (
                  <button
                    key={v}
                    onClick={() => setHoldingPeriod(v)}
                    className={`w-full p-4 rounded-xl text-left transition-all ${
                      holdingPeriod === v 
                        ? "bg-indigo-600/20 border-2 border-indigo-500" 
                        : "bg-white/[0.03] border border-white/[0.08] hover:bg-white/[0.05]"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className={`font-medium ${holdingPeriod === v ? "text-indigo-400" : "text-slate-200"}`}>{l}</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        holdingPeriod === v 
                          ? "bg-indigo-500/30 text-indigo-300" 
                          : "bg-white/[0.05] text-slate-400"
                      }`}>{desc}</span>
                    </div>
                    <p className={`text-xs ${holdingPeriod === v ? "text-indigo-300/70" : "text-slate-500"}`}>{detail}</p>
                  </button>
                ))}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setShowHoldingPeriodModal(false)}
                  className="flex-1 py-2.5 sm:py-3 bg-white/[0.05] border border-white/[0.08] text-slate-300 rounded-xl text-sm sm:text-base"
                >
                  取消
                </button>
                <button
                  onClick={handleConfirmHoldingPeriod}
                  className="flex-1 py-2.5 sm:py-3 bg-indigo-600 text-white rounded-xl text-sm sm:text-base flex items-center justify-center gap-2"
                >
                  <Play className="w-4 h-4" />
                  开始分析
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 编辑持仓弹窗 */}
      <AnimatePresence>
        {showEditPositionModal && editingItem && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center z-50"
            onClick={() => setShowEditPositionModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              className="glass-card rounded-t-2xl sm:rounded-2xl border border-white/[0.08] p-4 sm:p-6 w-full sm:max-w-md sm:mx-4 safe-area-bottom"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base sm:text-lg font-semibold text-white flex items-center gap-2">
                  <Edit3 className="w-5 h-5 text-indigo-400" />
                  编辑持仓 - {editingItem.symbol}
                </h3>
                <button onClick={() => setShowEditPositionModal(false)} className="p-1 hover:bg-white/[0.05] rounded-lg">
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-xs text-slate-400 mb-1.5 block">持仓数量</label>
                  <input
                    type="number"
                    value={editPosition}
                    onChange={(e) => setEditPosition(e.target.value)}
                    placeholder="如：1000"
                    className="w-full px-3 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-sm"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400 mb-1.5 block">成本价</label>
                  <input
                    type="number"
                    step="0.01"
                    value={editCostPrice}
                    onChange={(e) => setEditCostPrice(e.target.value)}
                    placeholder="如：10.50"
                    className="w-full px-3 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-sm"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400 mb-1.5 block">持有周期</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { v: "short", l: "短线", desc: "1-5天" },
                      { v: "swing", l: "波段", desc: "1-4周" },
                      { v: "long", l: "中长线", desc: "1月以上" }
                    ].map(({ v, l, desc }) => (
                      <button
                        key={v}
                        onClick={() => setEditHoldingPeriod(v)}
                        className={`py-2 rounded-lg text-xs font-medium transition-all flex flex-col items-center ${
                          editHoldingPeriod === v 
                            ? "bg-indigo-600 text-white" 
                            : "bg-white/[0.05] text-slate-300 hover:bg-white/[0.08]"
                        }`}
                      >
                        <span>{l}</span>
                        <span className={`text-[10px] ${editHoldingPeriod === v ? "text-indigo-200" : "text-slate-500"}`}>{desc}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowEditPositionModal(false)}
                  className="flex-1 py-2.5 sm:py-3 bg-white/[0.05] border border-white/[0.08] text-slate-300 rounded-xl text-sm sm:text-base"
                >
                  取消
                </button>
                <button
                  onClick={handleSavePosition}
                  disabled={loading}
                  className="flex-1 py-2.5 sm:py-3 bg-indigo-600 text-white rounded-xl disabled:opacity-50 text-sm sm:text-base flex items-center justify-center gap-2"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  保存
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Alert Modal */}
      <AlertModal
        isOpen={showAlert}
        onClose={() => setShowAlert(false)}
        title={alertConfig.title}
        message={alertConfig.message}
        type={alertConfig.type}
      />

      {/* Confirm Modal */}
      <ConfirmModal
        isOpen={showConfirm}
        onClose={() => setShowConfirm(false)}
        onConfirm={confirmConfig.onConfirm}
        title={confirmConfig.title}
        message={confirmConfig.message}
        type={confirmConfig.type}
        confirmText="立即分析"
        cancelText="稍后再说"
      />

      {/* 研究列表弹窗 */}
      <AnimatePresence>
        {showAiPicksModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center z-50"
            onClick={() => setShowAiPicksModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              className="glass-card rounded-t-2xl sm:rounded-2xl border border-white/[0.08] p-4 sm:p-6 w-full sm:max-w-lg sm:mx-4 max-h-[85vh] overflow-hidden flex flex-col safe-area-bottom"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base sm:text-lg font-semibold text-white flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-amber-400" />
                  研究列表
                </h3>
                <button onClick={() => setShowAiPicksModal(false)} className="p-1 hover:bg-white/[0.05] rounded-lg">
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              <p className="text-slate-500 text-xs sm:text-sm mb-4">
                管理员整理的研究标的列表，可批量添加到自选进行学习研究（不构成任何投资建议）
              </p>

              {aiPicksLoading ? (
                <div className="flex-1 flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
                </div>
              ) : availableAiPicks.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center py-12 text-slate-500">
                  <Sparkles className="w-12 h-12 mb-3 opacity-30" />
                  <p>暂无新的研究标的</p>
                  <p className="text-xs mt-1">您已添加所有标的到自选</p>
                </div>
              ) : (
                <>
                  {/* 全选/已选数量 */}
                  <div className="flex items-center justify-between mb-3 pb-3 border-b border-white/[0.06]">
                    <button
                      onClick={toggleSelectAllAiPicks}
                      className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200"
                    >
                      {selectedAiPicks.size === availableAiPicks.length ? (
                        <CheckSquare className="w-4 h-4 text-amber-400" />
                      ) : (
                        <Square className="w-4 h-4" />
                      )}
                      全选
                    </button>
                    <span className="text-xs text-slate-500">
                      已选 {selectedAiPicks.size}/{availableAiPicks.length}
                    </span>
                  </div>

                  {/* 列表 */}
                  <div className="flex-1 overflow-y-auto space-y-2 mb-4">
                    {availableAiPicks.map((pick) => (
                      <div
                        key={pick.symbol}
                        className={`p-3 rounded-xl transition-all cursor-pointer ${
                          selectedAiPicks.has(pick.symbol)
                            ? "bg-amber-500/10 border border-amber-500/20"
                            : "bg-white/[0.02] border border-white/[0.06] hover:bg-white/[0.04]"
                        }`}
                        onClick={() => toggleAiPickSelect(pick.symbol)}
                      >
                        <div className="flex items-center gap-3">
                          <div className="text-slate-300">
                            {selectedAiPicks.has(pick.symbol) ? (
                              <CheckSquare className="w-5 h-5 text-amber-400" />
                            ) : (
                              <Square className="w-5 h-5" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-semibold text-white text-sm">{pick.symbol}</span>
                              {pick.type && (
                                <span className="px-1.5 py-0.5 text-[10px] bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded">
                                  {pick.type === "stock" ? "股票" : pick.type === "etf" ? "ETF" : pick.type === "lof" ? "LOF" : "基金"}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 mt-0.5">
                              {pick.name && pick.name !== pick.symbol && (
                                <span className="text-xs text-slate-500 truncate">{pick.name}</span>
                              )}
                              {pick.added_at && (
                                <span className="text-[10px] text-slate-600 flex-shrink-0">
                                  {new Date(pick.added_at).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })}
                                </span>
                              )}
                            </div>
                          </div>
                          {/* 删除按钮 - 管理员全局删除，普通用户仅隐藏 */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              if (user?.role === 'admin') {
                                handleRemoveFromAiPicks(pick.symbol);
                              } else {
                                handleDismissAiPick(pick.symbol);
                              }
                            }}
                            className="p-1.5 hover:bg-rose-500/20 rounded-lg text-slate-500 hover:text-rose-400 transition-all"
                            title={user?.role === 'admin' ? "全局删除" : "不再显示"}
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* 操作按钮区域 */}
                  <div className="space-y-2">
                    {/* 添加到自选按钮 */}
                    <button
                      onClick={handleAddAiPicksToWatchlist}
                      disabled={loading || selectedAiPicks.size === 0}
                      className="w-full py-2.5 sm:py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-xl disabled:opacity-50 text-sm sm:text-base flex items-center justify-center gap-2 font-medium"
                    >
                      {loading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Plus className="w-4 h-4" />
                      )}
                      添加到自选 ({selectedAiPicks.size})
                    </button>
                    
                    {/* 批量删除和清空按钮 */}
                    <div className="flex gap-2">
                      <button
                        onClick={handleDismissSelectedAiPicks}
                        disabled={loading || selectedAiPicks.size === 0}
                        className="flex-1 py-2 bg-slate-700/50 hover:bg-slate-700 text-slate-300 rounded-xl disabled:opacity-50 text-sm flex items-center justify-center gap-1.5 transition-all"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        {user?.role === 'admin' ? '批量删除' : '批量移除'} ({selectedAiPicks.size})
                      </button>
                      <button
                        onClick={() => {
                          showConfirmModal(
                            user?.role === 'admin' ? "确认清空全部？" : "确认清空？",
                            user?.role === 'admin' 
                              ? "此操作将删除所有研究列表标的（全局生效），确定继续吗？" 
                              : "清空后这些标的将不再显示，除非管理员重新添加。确定继续吗？",
                            handleDismissAllAiPicks,
                            "warning"
                          );
                        }}
                        disabled={loading || availableAiPicks.length === 0}
                        className="py-2 px-4 bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 rounded-xl disabled:opacity-50 text-sm flex items-center justify-center gap-1.5 transition-all"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        清空
                      </button>
                    </div>
                  </div>
                </>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
