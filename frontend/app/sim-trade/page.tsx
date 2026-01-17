"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  BarChart3,
  RefreshCw,
  Play,
  Pause,
  History,
  AlertCircle,
  Loader2,
  ArrowLeft,
  RotateCcw,
  DollarSign,
  Activity,
  Eye,
  Target,
  Shield,
  Zap,
  Clock,
  ChevronDown,
  ChevronUp,
  Radio,
  Edit3,
  X,
} from "lucide-react";
import { AlertModal } from "@/components/ui/AlertModal";
import { ConfirmModal } from "@/components/ui/ConfirmModal";
import { API_BASE } from "@/lib/config";

interface UserInfo {
  username: string;
  phone?: string;
  role?: string;
  status?: string;
}

interface SimAccount {
  initial_capital: number;
  current_capital: number;
  total_profit: number;
  total_profit_pct: number;
  win_count: number;
  loss_count: number;
  win_rate: number;
  auto_trade_enabled: number;
}

interface SimPosition {
  symbol: string;
  name: string;
  type: string;
  quantity: number;
  cost_price: number;
  current_price: number;
  profit: number;
  profit_pct: number;
  buy_date: string;
  holding_period: string;
  trade_rule: string;
  can_sell_date: string;
  highest_price?: number;
}

interface SimTradeRecord {
  id: number;
  symbol: string;
  name: string;
  trade_type: string;
  quantity: number;
  price: number;
  amount: number;
  signal_type: string;
  profit: number;
  profit_pct: number;
  holding_days: number;
  trade_date: string;
  created_at: string;
}

interface SimStats {
  total_trades: number;
  buy_count: number;
  sell_count: number;
  total_profit: number;
  win_count: number;
  loss_count: number;
  win_rate: number;
  avg_profit_pct: number;
  max_profit_pct: number;
  min_profit_pct: number;
  avg_holding_days: number;
}

interface MonitorItem {
  symbol: string;
  name: string;
  type: string;
  holding_period: string;
  current_price: number;
  change_pct: number;
  support: number;
  resistance: number;
  risk: number;
  dist_to_support: number | null;
  dist_to_resistance: number | null;
  signal_status: string;
  signal_reason: string;
  has_position: boolean;
  position: {
    quantity: number;
    cost_price: number;
    profit_pct: number;
    holding_days: number;
    buy_date: string;
  } | null;
  starred: number;
}

interface TradeLog {
  id: number;
  type: string;
  icon: string;
  message: string;
  symbol: string;
  name: string;
  signal_type: string;
  profit: number;
  profit_pct: number;
  created_at: string;
}

interface MonitorLog {
  id: number;
  type: string;
  icon: string;
  symbol?: string;
  message: string;
  details?: string;
  created_at: string;
}

interface QuoteData {
  symbol: string;
  current_price: number;
  change_percent: number;
}

export default function SimTradePage() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [account, setAccount] = useState<SimAccount | null>(null);
  const [positions, setPositions] = useState<SimPosition[]>([]);
  const [records, setRecords] = useState<SimTradeRecord[]>([]);
  const [stats, setStats] = useState<SimStats | null>(null);
  const [totalAssets, setTotalAssets] = useState(0);
  const [positionValue, setPositionValue] = useState(0);
  const [positionRatio, setPositionRatio] = useState(0);
  const [maxDrawdown, setMaxDrawdown] = useState(0);
  const [floatingProfit, setFloatingProfit] = useState(0);

  // 监控相关状态
  const [monitorItems, setMonitorItems] = useState<MonitorItem[]>([]);
  const [tradeLogs, setTradeLogs] = useState<TradeLog[]>([]);
  const [monitorLogs, setMonitorLogs] = useState<MonitorLog[]>([]);
  const [monitorLoading, setMonitorLoading] = useState(false);

  const [activeTab, setActiveTab] = useState<'monitor' | 'positions' | 'records' | 'stats'>('monitor');
  const [refreshing, setRefreshing] = useState(false);
  const [autoTrading, setAutoTrading] = useState(false);
  const [processingTrade, setProcessingTrade] = useState(false);
  const [lastUpdateTime, setLastUpdateTime] = useState<string>('');

  // 实时行情
  const [realtimeQuotes, setRealtimeQuotes] = useState<Record<string, QuoteData>>({});
  const quotesRef = useRef<Record<string, QuoteData>>({});
  const positionsRef = useRef<SimPosition[]>([]);
  const isFetchingRef = useRef(false);

  // 展开/收起状态
  const [expandedSections, setExpandedSections] = useState({
    account: true,
    risk: true,
    autoTrade: true,
  });

  // 编辑初始资金
  const [showEditCapital, setShowEditCapital] = useState(false);
  const [editCapitalValue, setEditCapitalValue] = useState('');

  const [showAlert, setShowAlert] = useState(false);
  const [alertConfig, setAlertConfig] = useState({
    title: "",
    message: "",
    type: "warning" as "warning" | "info" | "success" | "error",
  });

  const [showConfirm, setShowConfirm] = useState(false);
  const [confirmConfig, setConfirmConfig] = useState({
    title: "",
    message: "",
    type: "question" as "warning" | "info" | "success" | "error" | "question",
    onConfirm: () => {},
  });

  const getToken = useCallback(() => localStorage.getItem("token"), []);

  const showAlertModal = useCallback(
    (title: string, message: string, type: "warning" | "info" | "success" | "error" = "warning") => {
      setAlertConfig({ title, message, type });
      setShowAlert(true);
    },
    []
  );

  const showConfirmModal = useCallback(
    (title: string, message: string, onConfirm: () => void, type: "warning" | "info" | "success" | "error" | "question" = "question") => {
      setConfirmConfig({ title, message, type, onConfirm });
      setShowConfirm(true);
    },
    []
  );

  // 检查登录状态
  useEffect(() => {
    const token = getToken();
    const storedUser = localStorage.getItem("user");
    if (!token || !storedUser) {
      router.push("/login");
      return;
    }
    try {
      setUser(JSON.parse(storedUser));
    } catch {
      router.push("/login");
    }
  }, [router, getToken]);

  // 判断是否为交易时间
  const isTradingTime = useCallback(() => {
    const now = new Date();
    const day = now.getDay();
    if (day === 0 || day === 6) return false;
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const time = hours * 60 + minutes;
    return (time >= 570 && time <= 690) || (time >= 780 && time <= 900);
  }, []);

  useEffect(() => {
    positionsRef.current = positions;
  }, [positions]);

  // 获取实时行情
  const fetchQuotesOnly = useCallback(async () => {
    const token = getToken();
    if (!token || positionsRef.current.length === 0 || isFetchingRef.current) return;
    isFetchingRef.current = true;
    try {
      const symbols = positionsRef.current.map(p => p.symbol).join(',');
      const response = await fetch(`${API_BASE}/api/quotes?symbols=${encodeURIComponent(symbols)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        const newQuotes: Record<string, QuoteData> = {};
        if (data.quotes) {
          Object.entries(data.quotes).forEach(([symbol, quote]: [string, any]) => {
            newQuotes[symbol.toUpperCase()] = {
              symbol: symbol.toUpperCase(),
              current_price: quote.current_price || 0,
              change_percent: quote.change_percent || 0,
            };
          });
        }
        quotesRef.current = newQuotes;
        setRealtimeQuotes({ ...newQuotes });
        setLastUpdateTime(new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
      }
    } catch (error) {
      // 静默失败
    } finally {
      isFetchingRef.current = false;
    }
  }, [getToken]);

  // 计算持仓盈亏
  const getPositionWithRealtime = useCallback((position: SimPosition) => {
    const quote = realtimeQuotes[position.symbol.toUpperCase()];
    if (quote && quote.current_price > 0) {
      const currentPrice = quote.current_price;
      const profit = (currentPrice - position.cost_price) * position.quantity;
      const profitPct = ((currentPrice / position.cost_price) - 1) * 100;
      return { ...position, current_price: currentPrice, profit, profit_pct: profitPct };
    }
    return position;
  }, [realtimeQuotes]);

  // 计算总资产
  const calculateTotalAssets = useCallback(() => {
    let posValue = 0;
    positions.forEach((p: SimPosition) => {
      const quote = realtimeQuotes[p.symbol.toUpperCase()];
      const price = quote?.current_price || p.current_price || p.cost_price;
      posValue += p.quantity * price;
    });
    return {
      positionValue: posValue,
      totalAssets: (account?.current_capital || 0) + posValue,
    };
  }, [positions, realtimeQuotes, account]);

  const { positionValue: realtimePositionValue, totalAssets: realtimeTotalAssets } = calculateTotalAssets();

  // 获取账户信息
  const fetchAccountInfo = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    try {
      const response = await fetch(`${API_BASE}/api/sim-trade/account`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setAccount(data.data.account);
        setPositions(data.data.positions as SimPosition[] || []);
        setStats(data.data.stats);
        setTotalAssets(data.data.total_assets || 0);
        setPositionValue(data.data.position_value || 0);
        setPositionRatio(data.data.position_ratio || 0);
        setMaxDrawdown(data.data.max_drawdown || 0);
        setFloatingProfit(data.data.floating_profit || 0);
        setAutoTrading(data.data.account?.auto_trade_enabled === 1);
      }
    } catch (error) {
      console.error("获取账户信息失败:", error);
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  // 获取交易记录
  const fetchRecords = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    try {
      const response = await fetch(`${API_BASE}/api/sim-trade/records?limit=100`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setRecords(data.records || []);
      }
    } catch (error) {
      console.error("获取交易记录失败:", error);
    }
  }, [getToken]);

  // 获取监控数据
  const fetchMonitorData = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    setMonitorLoading(true);
    try {
      const [monitorRes, logsRes, monitorLogsRes] = await Promise.all([
        fetch(`${API_BASE}/api/sim-trade/monitor`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_BASE}/api/sim-trade/logs?limit=30`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_BASE}/api/sim-trade/monitor-logs?limit=50`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (monitorRes.ok) {
        const data = await monitorRes.json();
        console.log("监控数据:", data);
        setMonitorItems(data.monitor_items || []);
      } else {
        console.error("获取监控数据失败:", await monitorRes.text());
      }
      if (logsRes.ok) {
        const data = await logsRes.json();
        setTradeLogs(data.logs || []);
      }
      if (monitorLogsRes.ok) {
        const data = await monitorLogsRes.json();
        setMonitorLogs(data.logs || []);
      }
    } catch (error) {
      console.error("获取监控数据失败:", error);
    } finally {
      setMonitorLoading(false);
    }
  }, [getToken]);

  // 手动刷新
  const updatePrices = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    setRefreshing(true);
    try {
      await fetch(`${API_BASE}/api/sim-trade/update-prices`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      await Promise.all([fetchAccountInfo(), fetchQuotesOnly(), fetchMonitorData()]);
    } catch (error) {
      console.error("更新价格失败:", error);
    } finally {
      setRefreshing(false);
    }
  }, [getToken, fetchAccountInfo, fetchQuotesOnly, fetchMonitorData]);

  // 修改初始资金
  const updateCapital = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    
    const newCapital = parseFloat(editCapitalValue);
    if (isNaN(newCapital) || newCapital <= 0) {
      showAlertModal("输入错误", "请输入有效的金额", "error");
      return;
    }
    
    try {
      const response = await fetch(`${API_BASE}/api/sim-trade/update-capital`, {
        method: "POST",
        headers: { 
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ initial_capital: newCapital }),
      });
      const data = await response.json();
      if (response.ok) {
        setShowEditCapital(false);
        showAlertModal("修改成功", `初始资金已修改为 ¥${newCapital.toLocaleString()}`, "success");
        fetchAccountInfo();
      } else {
        showAlertModal("修改失败", data.detail || "请稍后重试", "error");
      }
    } catch (error) {
      showAlertModal("操作失败", "请稍后重试", "error");
    }
  }, [getToken, editCapitalValue, showAlertModal, fetchAccountInfo]);

  // 切换自动交易
  const toggleAutoTrade = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    try {
      const response = await fetch(`${API_BASE}/api/sim-trade/auto-trade/toggle`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !autoTrading }),
      });
      if (response.ok) {
        setAutoTrading(!autoTrading);
        showAlertModal("设置成功", `自动交易已${!autoTrading ? '开启' : '关闭'}`, "success");
      }
    } catch (error) {
      showAlertModal("操作失败", "请稍后重试", "error");
    }
  }, [getToken, autoTrading, showAlertModal]);

  // 处理自动交易
  const processAutoTrade = useCallback(async () => {
    const token = getToken();
    if (!token) {
      showAlertModal("未登录", "请先登录", "error");
      return;
    }
    setProcessingTrade(true);
    try {
      const response = await fetch(`${API_BASE}/api/sim-trade/process`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      if (response.ok) {
        if (data.trades && data.trades.length > 0) {
          showAlertModal("交易执行完成", `执行了 ${data.trades.length} 笔交易`, "success");
        } else {
          showAlertModal("无交易信号", data.message || "当前没有符合条件的交易信号", "info");
        }
        await Promise.all([fetchAccountInfo(), fetchRecords(), fetchMonitorData()]);
      } else {
        showAlertModal("执行失败", data.detail || data.message || "请稍后重试", "error");
      }
    } catch (error) {
      console.error("处理自动交易失败:", error);
      showAlertModal("处理失败", "网络错误，请稍后重试", "error");
    } finally {
      setProcessingTrade(false);
    }
  }, [getToken, showAlertModal, fetchAccountInfo, fetchRecords, fetchMonitorData]);

  // 重置账户
  const handleResetAccount = useCallback(() => {
    showConfirmModal(
      "确认重置",
      "重置后将清空所有持仓和交易记录，恢复初始资金。此操作不可撤销！",
      async () => {
        const token = getToken();
        if (!token) return;
        try {
          const response = await fetch(`${API_BASE}/api/sim-trade/reset`, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
          });
          if (response.ok) {
            showAlertModal("重置成功", "模拟账户已重置", "success");
            await Promise.all([fetchAccountInfo(), fetchRecords(), fetchMonitorData()]);
          }
        } catch (error) {
          showAlertModal("重置失败", "请稍后重试", "error");
        }
      },
      "warning"
    );
  }, [getToken, showConfirmModal, showAlertModal, fetchAccountInfo, fetchRecords, fetchMonitorData]);

  // 初始化加载
  useEffect(() => {
    fetchAccountInfo();
    fetchRecords();
    fetchMonitorData();
  }, [fetchAccountInfo, fetchRecords, fetchMonitorData]);

  // 实时行情轮询
  useEffect(() => {
    if (positions.length === 0) return;
    fetchQuotesOnly();
    const getInterval = () => isTradingTime() ? 1000 : 30000;  // 交易时间1秒，非交易30秒
    let intervalId = setInterval(() => { fetchQuotesOnly(); }, getInterval());
    const checkIntervalId = setInterval(() => {
      clearInterval(intervalId);
      intervalId = setInterval(() => { fetchQuotesOnly(); }, getInterval());
    }, 60000);
    return () => { clearInterval(intervalId); clearInterval(checkIntervalId); };
  }, [positions.length, fetchQuotesOnly, isTradingTime]);

  // 监控数据轮询
  useEffect(() => {
    const interval = setInterval(() => {
      if (activeTab === 'monitor') {
        fetchMonitorData();
      }
    }, isTradingTime() ? 5000 : 30000);  // 交易时间5秒，非交易30秒
    return () => clearInterval(interval);
  }, [activeTab, fetchMonitorData, isTradingTime]);

  const formatMoney = (value: number) => {
    if (Math.abs(value) >= 10000) return `${(value / 10000).toFixed(2)}万`;
    return value.toFixed(2);
  };

  const formatPercent = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections((prev: typeof expandedSections) => ({ ...prev, [section]: !prev[section] }));
  };

  // 获取信号状态样式
  const getSignalStyle = (status: string) => {
    switch (status) {
      case 'near_support': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
      case 'below_support': return 'bg-rose-500/20 text-rose-400 border-rose-500/40';
      case 'near_resistance': return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      case 'above_resistance': return 'bg-blue-500/20 text-blue-400 border-blue-500/40';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/40';
    }
  };

  const getSignalText = (status: string) => {
    switch (status) {
      case 'near_support': return '接近支撑';
      case 'below_support': return '跌破支撑';
      case 'near_resistance': return '接近阻力';
      case 'above_resistance': return '突破阻力';
      default: return '观望';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* 顶部导航 */}
      <header className="sticky top-0 z-50 bg-slate-900/80 backdrop-blur-xl border-b border-slate-700/50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => router.push('/dashboard')} className="p-2 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 transition-colors">
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </button>
            <div>
              <h1 className="text-lg font-bold text-white flex items-center gap-2">
                <Activity className="w-5 h-5 text-indigo-400" />
                模拟交易系统
              </h1>
              <div className="flex items-center gap-2 text-[10px] text-slate-500">
                {lastUpdateTime && <span>更新: {lastUpdateTime}</span>}
                {isTradingTime() ? (
                  <span className="flex items-center gap-1 text-emerald-400"><Radio className="w-3 h-3 animate-pulse" />交易中</span>
                ) : (
                  <span className="text-slate-500">休市</span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={updatePrices} disabled={refreshing} className="p-2 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 transition-colors">
              <RefreshCw className={`w-5 h-5 text-slate-400 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
            <button onClick={handleResetAccount} className="p-2 rounded-lg bg-slate-800/50 hover:bg-rose-500/20 transition-colors">
              <RotateCcw className="w-5 h-5 text-slate-400 hover:text-rose-400" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-4 space-y-4">
        {/* 免责声明 */}
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-2">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0" />
            <p className="text-xs text-amber-300/80">本功能仅供学习研究使用，不构成任何投资建议。模拟交易结果不代表真实交易表现。</p>
          </div>
        </div>

        {/* 账户概览卡片 */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
          <button onClick={() => toggleSection('account')} className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-700/30 transition-colors">
            <div className="flex items-center gap-2">
              <Wallet className="w-4 h-4 text-indigo-400" />
              <span className="text-sm font-medium text-white">账户概览</span>
            </div>
            {expandedSections.account ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
          </button>
          {expandedSections.account && (
            <div className="px-4 pb-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-slate-900/50 rounded-lg p-3">
                  <div className="text-xs text-slate-400 mb-1">总资产</div>
                  <div className="text-lg font-bold text-white">¥{formatMoney(realtimeTotalAssets || totalAssets)}</div>
                  <div className={`text-xs ${((realtimeTotalAssets || totalAssets) - (account?.initial_capital || 1000000)) >= 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {formatPercent((((realtimeTotalAssets || totalAssets) / (account?.initial_capital || 1000000)) - 1) * 100)}
                  </div>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-3">
                  <div className="text-xs text-slate-400 mb-1">可用资金</div>
                  <div className="text-lg font-bold text-white">¥{formatMoney(account?.current_capital || 0)}</div>
                  <button 
                    onClick={() => {
                      setEditCapitalValue(String(account?.initial_capital || 1000000));
                      setShowEditCapital(true);
                    }}
                    className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
                  >
                    初始: ¥{formatMoney(account?.initial_capital || 1000000)}
                    <Edit3 className="w-3 h-3" />
                  </button>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-3">
                  <div className="text-xs text-slate-400 mb-1">持仓市值</div>
                  <div className="text-lg font-bold text-white">¥{formatMoney(realtimePositionValue || positionValue)}</div>
                  <div className="text-xs text-slate-500">{positions.length} 只持仓</div>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-3">
                  <div className="text-xs text-slate-400 mb-1">浮动盈亏</div>
                  <div className={`text-lg font-bold ${floatingProfit >= 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {floatingProfit >= 0 ? '+' : ''}¥{formatMoney(floatingProfit)}
                  </div>
                  <div className="text-xs text-slate-500">胜率: {(account?.win_rate || 0).toFixed(1)}%</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 风险指标卡片 */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
          <button onClick={() => toggleSection('risk')} className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-700/30 transition-colors">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-amber-400" />
              <span className="text-sm font-medium text-white">风险指标</span>
            </div>
            {expandedSections.risk ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
          </button>
          {expandedSections.risk && (
            <div className="px-4 pb-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-slate-900/50 rounded-lg p-3">
                  <div className="text-xs text-slate-400 mb-2">仓位占比</div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${positionRatio > 70 ? 'bg-rose-500' : positionRatio > 50 ? 'bg-amber-500' : 'bg-emerald-500'}`} style={{ width: `${Math.min(positionRatio, 100)}%` }} />
                    </div>
                    <span className="text-sm font-medium text-white">{positionRatio.toFixed(1)}%</span>
                  </div>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-3">
                  <div className="text-xs text-slate-400 mb-2">最大回撤</div>
                  <div className={`text-lg font-bold ${maxDrawdown > 10 ? 'text-rose-400' : maxDrawdown > 5 ? 'text-amber-400' : 'text-emerald-400'}`}>
                    -{maxDrawdown.toFixed(2)}%
                  </div>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-3">
                  <div className="text-xs text-slate-400 mb-2">交易统计</div>
                  <div className="text-sm text-white">
                    <span className="text-emerald-400">{account?.win_count || 0}胜</span>
                    <span className="mx-1">/</span>
                    <span className="text-rose-400">{account?.loss_count || 0}负</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 自动交易控制 */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
          <button onClick={() => toggleSection('autoTrade')} className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-700/30 transition-colors">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-yellow-400" />
              <span className="text-sm font-medium text-white">自动交易</span>
              <span className={`px-2 py-0.5 rounded text-xs ${autoTrading ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-600/50 text-slate-400'}`}>
                {autoTrading ? '已开启' : '已关闭'}
              </span>
            </div>
            {expandedSections.autoTrade ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
          </button>
          {expandedSections.autoTrade && (
            <div className="px-4 pb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${autoTrading ? 'bg-emerald-500/20' : 'bg-slate-700/50'}`}>
                    {autoTrading ? <Play className="w-5 h-5 text-emerald-400" /> : <Pause className="w-5 h-5 text-slate-400" />}
                  </div>
                  <div>
                    <div className="text-sm text-white">{autoTrading ? '监控中，将根据信号自动买卖' : '已暂停自动交易'}</div>
                    <div className="text-xs text-slate-400">基于ATR动态风控 + 金字塔式分仓策略</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={processAutoTrade} disabled={processingTrade} className="px-3 py-1.5 rounded-lg bg-indigo-500/20 text-indigo-400 text-sm hover:bg-indigo-500/30 transition-colors disabled:opacity-50">
                    {processingTrade ? <Loader2 className="w-4 h-4 animate-spin" /> : '立即执行'}
                  </button>
                  <button onClick={toggleAutoTrade} className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${autoTrading ? 'bg-rose-500/20 text-rose-400 hover:bg-rose-500/30' : 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'}`}>
                    {autoTrading ? '关闭' : '开启'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 策略池入口 */}
        <button
          onClick={() => router.push('/sim-trade/strategies')}
          className="w-full bg-gradient-to-r from-indigo-500/20 to-purple-500/20 rounded-xl border border-indigo-500/30 p-4 hover:from-indigo-500/30 hover:to-purple-500/30 transition-all"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-indigo-500/20">
                <Zap className="w-5 h-5 text-indigo-400" />
              </div>
              <div className="text-left">
                <div className="text-sm font-medium text-white">策略池</div>
                <div className="text-xs text-slate-400">选择和配置量化交易策略</div>
              </div>
            </div>
            <ChevronDown className="w-5 h-5 text-slate-400 -rotate-90" />
          </div>
        </button>

        {/* Tab 切换 */}
        <div className="flex gap-1 bg-slate-800/50 rounded-xl p-1 border border-slate-700/50">
          {[
            { key: 'monitor', label: '实时监控', icon: Eye, count: monitorItems.length },
            { key: 'positions', label: '持仓', icon: Target, count: positions.length },
            { key: 'records', label: '交易记录', icon: History, count: records.length },
            { key: 'stats', label: '统计', icon: BarChart3 },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.key ? 'bg-indigo-500/20 text-indigo-400' : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              <span className="hidden sm:inline">{tab.label}</span>
              {tab.count !== undefined && <span className="text-xs opacity-60">({tab.count})</span>}
            </button>
          ))}
        </div>

        {/* 实时监控面板 */}
        {activeTab === 'monitor' && (
          <div className="space-y-4">
            {/* 监控列表 */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-700/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Eye className="w-4 h-4 text-indigo-400" />
                  <span className="text-sm font-medium text-white">监控列表</span>
                  <span className="text-xs text-slate-400">({monitorItems.length}个标的)</span>
                </div>
                {monitorLoading && <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />}
              </div>
              <div className="divide-y divide-slate-700/50 max-h-[400px] overflow-y-auto">
                {monitorItems.length === 0 ? (
                  <div className="p-8 text-center text-slate-400">
                    <Eye className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>暂无监控标的</p>
                    <p className="text-xs mt-1">请先在自选列表中添加标的</p>
                  </div>
                ) : (
                  monitorItems.map(item => (
                    <div key={item.symbol} className={`px-4 py-3 hover:bg-slate-700/30 transition-colors ${item.has_position ? 'bg-indigo-500/5' : ''}`}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {item.has_position && <div className="w-1 h-8 bg-indigo-500 rounded-full" />}
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-white">{item.name}</span>
                              <span className="text-xs text-slate-400">{item.symbol}</span>
                              <span className={`px-1.5 py-0.5 rounded text-[10px] border ${getSignalStyle(item.signal_status)}`}>
                                {getSignalText(item.signal_status)}
                              </span>
                            </div>
                            <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                              <span>支撑: ¥{item.support?.toFixed(3) || '-'}</span>
                              <span>阻力: ¥{item.resistance?.toFixed(3) || '-'}</span>
                              {item.dist_to_support !== null && (
                                <span className={item.dist_to_support <= 1.5 ? 'text-emerald-400' : ''}>
                                  距支撑: {item.dist_to_support.toFixed(1)}%
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-lg font-bold text-white">¥{item.current_price?.toFixed(3) || '-'}</div>
                          <div className={`text-sm ${item.change_pct >= 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                            {item.change_pct >= 0 ? '+' : ''}{item.change_pct?.toFixed(2)}%
                          </div>
                          {item.position && (
                            <div className={`text-xs mt-1 ${item.position.profit_pct >= 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                              持仓盈亏: {item.position.profit_pct >= 0 ? '+' : ''}{item.position.profit_pct.toFixed(2)}%
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* 交易日志 */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-700/50 flex items-center gap-2">
                <History className="w-4 h-4 text-amber-400" />
                <span className="text-sm font-medium text-white">交易日志</span>
              </div>
              <div className="divide-y divide-slate-700/50 max-h-[300px] overflow-y-auto">
                {tradeLogs.length === 0 ? (
                  <div className="p-6 text-center text-slate-400">
                    <History className="w-10 h-10 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">暂无交易记录</p>
                  </div>
                ) : (
                  tradeLogs.map(log => (
                    <div key={log.id} className="px-4 py-2 hover:bg-slate-700/30 transition-colors">
                      <div className="flex items-start gap-2">
                        <span className="text-lg">{log.icon}</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-white">{log.message}</div>
                          <div className="text-xs text-slate-400 mt-0.5">{log.created_at}</div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* 自动交易监控日志 */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-700/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  <span className="text-sm font-medium text-white">自动交易监控日志</span>
                </div>
                <span className="text-xs text-slate-400">{monitorLogs.length} 条记录</span>
              </div>
              <div className="divide-y divide-slate-700/50 max-h-[400px] overflow-y-auto">
                {monitorLogs.length === 0 ? (
                  <div className="p-6 text-center text-slate-400">
                    <Activity className="w-10 h-10 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">暂无监控日志</p>
                    <p className="text-xs mt-1">开启自动交易后，系统将记录监控活动</p>
                  </div>
                ) : (
                  monitorLogs.map(log => (
                    <div key={log.id} className="px-4 py-2 hover:bg-slate-700/30 transition-colors">
                      <div className="flex items-start gap-2">
                        <span className="text-lg">{log.icon}</span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className={`text-xs px-1.5 py-0.5 rounded ${
                              log.type === 'trade' ? 'bg-emerald-500/20 text-emerald-400' :
                              log.type === 'signal' ? 'bg-amber-500/20 text-amber-400' :
                              log.type === 'scan' ? 'bg-blue-500/20 text-blue-400' :
                              log.type === 'risk' ? 'bg-rose-500/20 text-rose-400' :
                              log.type === 'error' ? 'bg-red-500/20 text-red-400' :
                              'bg-slate-500/20 text-slate-400'
                            }`}>
                              {log.type === 'trade' ? '交易' :
                               log.type === 'signal' ? '信号' :
                               log.type === 'scan' ? '扫描' :
                               log.type === 'risk' ? '风控' :
                               log.type === 'error' ? '错误' : '信息'}
                            </span>
                            {log.symbol && <span className="text-xs text-slate-400">{log.symbol}</span>}
                          </div>
                          <div className="text-sm text-white mt-1">{log.message}</div>
                          {log.details && (
                            <div className="text-xs text-slate-400 mt-0.5">{log.details}</div>
                          )}
                          <div className="text-xs text-slate-500 mt-0.5">{log.created_at}</div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* 持仓列表 */}
        {activeTab === 'positions' && (
          <div className="space-y-3">
            {positions.length === 0 ? (
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-12 text-center text-slate-400">
                <Target className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>暂无持仓</p>
                <p className="text-xs mt-1">开启自动交易后，系统将根据信号自动买入</p>
              </div>
            ) : (
              positions.map(position => {
                const realtimePosition = getPositionWithRealtime(position);
                return (
                  <div key={position.symbol} className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <div className="font-medium text-white">{position.name}</div>
                        <div className="text-xs text-slate-400">{position.symbol}</div>
                      </div>
                      <div className="text-right">
                        <div className={`text-lg font-bold ${realtimePosition.profit >= 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                          {realtimePosition.profit >= 0 ? '+' : ''}¥{realtimePosition.profit.toFixed(2)}
                        </div>
                        <div className={`text-xs ${realtimePosition.profit_pct >= 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                          {formatPercent(realtimePosition.profit_pct)}
                        </div>
                      </div>
                    </div>
                    <div className="grid grid-cols-4 gap-2 text-xs">
                      <div><div className="text-slate-400">持仓</div><div className="text-white">{position.quantity}股</div></div>
                      <div><div className="text-slate-400">成本</div><div className="text-white">¥{position.cost_price.toFixed(3)}</div></div>
                      <div><div className="text-slate-400">现价</div><div className={`font-medium ${realtimePosition.profit_pct >= 0 ? 'text-rose-400' : 'text-emerald-400'}`}>¥{realtimePosition.current_price.toFixed(3)}</div></div>
                      <div><div className="text-slate-400">规则</div><div className="text-white">{position.trade_rule}</div></div>
                    </div>
                    <div className="mt-2 pt-2 border-t border-slate-700/50 flex items-center justify-between text-xs">
                      <span className="text-slate-400">买入: {position.buy_date} | 可卖: {position.can_sell_date}</span>
                      <span className={`px-2 py-0.5 rounded ${position.holding_period === 'short' ? 'bg-amber-500/20 text-amber-400' : position.holding_period === 'long' ? 'bg-blue-500/20 text-blue-400' : 'bg-indigo-500/20 text-indigo-400'}`}>
                        {position.holding_period === 'short' ? '短线' : position.holding_period === 'long' ? '中长线' : '波段'}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* 交易记录 */}
        {activeTab === 'records' && (
          <div className="space-y-3">
            {records.length === 0 ? (
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-12 text-center text-slate-400">
                <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>暂无交易记录</p>
              </div>
            ) : (
              records.map(record => (
                <div key={record.id} className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${record.trade_type === 'buy' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                        {record.trade_type === 'buy' ? '买入' : '卖出'}
                      </span>
                      <span className="font-medium text-white">{record.name}</span>
                      <span className="text-xs text-slate-400">{record.symbol}</span>
                    </div>
                    <div className="text-xs text-slate-400">{record.created_at}</div>
                  </div>
                  <div className="grid grid-cols-4 gap-2 text-xs">
                    <div><div className="text-slate-400">数量</div><div className="text-white">{record.quantity}股</div></div>
                    <div><div className="text-slate-400">价格</div><div className="text-white">¥{record.price.toFixed(3)}</div></div>
                    <div><div className="text-slate-400">金额</div><div className="text-white">¥{(record.quantity * record.price).toFixed(2)}</div></div>
                    {record.trade_type === 'sell' && (
                      <div>
                        <div className="text-slate-400">盈亏</div>
                        <div className={record.profit >= 0 ? 'text-rose-400' : 'text-emerald-400'}>
                          {record.profit >= 0 ? '+' : ''}¥{record.profit.toFixed(2)} ({formatPercent(record.profit_pct)})
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* 详细统计 */}
        {activeTab === 'stats' && stats && (
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-indigo-400" />
              交易统计
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-white">{stats.total_trades}</div>
                <div className="text-xs text-slate-400">总交易次数</div>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-indigo-400">{stats.win_rate.toFixed(1)}%</div>
                <div className="text-xs text-slate-400">胜率</div>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                <div className={`text-2xl font-bold ${stats.avg_profit_pct >= 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                  {formatPercent(stats.avg_profit_pct)}
                </div>
                <div className="text-xs text-slate-400">平均收益</div>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-blue-400">{stats.avg_holding_days.toFixed(1)}天</div>
                <div className="text-xs text-slate-400">平均持有</div>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-emerald-400">{stats.win_count}</div>
                <div className="text-xs text-slate-400">盈利次数</div>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-rose-400">{stats.loss_count}</div>
                <div className="text-xs text-slate-400">亏损次数</div>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-rose-400">{formatPercent(stats.max_profit_pct)}</div>
                <div className="text-xs text-slate-400">最大盈利</div>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-emerald-400">{formatPercent(stats.min_profit_pct)}</div>
                <div className="text-xs text-slate-400">最大亏损</div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* 弹窗 */}
      <AlertModal isOpen={showAlert} onClose={() => setShowAlert(false)} title={alertConfig.title} message={alertConfig.message} type={alertConfig.type} />
      <ConfirmModal isOpen={showConfirm} onClose={() => setShowConfirm(false)} onConfirm={() => { confirmConfig.onConfirm(); setShowConfirm(false); }} title={confirmConfig.title} message={confirmConfig.message} type={confirmConfig.type} />
      
      {/* 编辑初始资金弹窗 */}
      <AnimatePresence>
        {showEditCapital && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setShowEditCapital(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-slate-800 rounded-xl border border-slate-700 p-6 w-full max-w-sm"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-white">修改初始资金</h3>
                <button onClick={() => setShowEditCapital(false)} className="text-slate-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="mb-4">
                <label className="block text-sm text-slate-400 mb-2">初始资金金额 (元)</label>
                <input
                  type="number"
                  value={editCapitalValue}
                  onChange={(e) => setEditCapitalValue(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-cyan-500"
                  placeholder="请输入金额"
                  min="1"
                  max="100000000"
                />
                <p className="text-xs text-slate-500 mt-2">修改后可用资金将自动调整</p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowEditCapital(false)}
                  className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={updateCapital}
                  className="flex-1 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors"
                >
                  确认修改
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
