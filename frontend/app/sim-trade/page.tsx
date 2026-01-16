"use client";

import { useState, useEffect, useCallback } from "react";
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
  Settings,
  RotateCcw,
  DollarSign,
  Percent,
  Calendar,
  Target,
} from "lucide-react";
import { UserHeader } from "@/components/ui/UserHeader";
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

  const [activeTab, setActiveTab] = useState<'positions' | 'records'>('positions');
  const [refreshing, setRefreshing] = useState(false);
  const [autoTrading, setAutoTrading] = useState(false);
  const [processingTrade, setProcessingTrade] = useState(false);
  const [lastUpdateTime, setLastUpdateTime] = useState<string>('');

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
    
    // 上午 9:30-11:30 (570-690), 下午 13:00-15:00 (780-900)
    return (time >= 570 && time <= 690) || (time >= 780 && time <= 900);
  }, []);

  // 获取账户信息（不更新价格，快速）
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
        setPositions(data.data.positions || []);
        setStats(data.data.stats);
        setTotalAssets(data.data.total_assets || 0);
        setPositionValue(data.data.position_value || 0);
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

  // 更新持仓价格（静默更新，不显示loading）
  const updatePricesSilent = useCallback(async () => {
    const token = getToken();
    if (!token || positions.length === 0) return;

    try {
      await fetch(`${API_BASE}/api/sim-trade/update-prices`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      // 只获取账户信息，不触发loading
      const response = await fetch(`${API_BASE}/api/sim-trade/account`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        // 增量更新，只更新变化的数据
        setPositions(data.data.positions || []);
        setTotalAssets(data.data.total_assets || 0);
        setPositionValue(data.data.position_value || 0);
        setLastUpdateTime(new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
      }
    } catch (error) {
      console.error("静默更新价格失败:", error);
    }
  }, [getToken, positions.length]);

  // 更新持仓价格（手动刷新，显示loading）
  const updatePrices = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    setRefreshing(true);
    try {
      await fetch(`${API_BASE}/api/sim-trade/update-prices`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      await fetchAccountInfo();
      setLastUpdateTime(new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    } catch (error) {
      console.error("更新价格失败:", error);
    } finally {
      setRefreshing(false);
    }
  }, [getToken, fetchAccountInfo]);

  // 切换自动交易
  const toggleAutoTrade = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE}/api/sim-trade/auto-trade/toggle`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
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
    if (!token) return;

    setProcessingTrade(true);
    try {
      const response = await fetch(`${API_BASE}/api/sim-trade/process`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        if (data.trades && data.trades.length > 0) {
          showAlertModal("交易执行完成", `执行了 ${data.trades.length} 笔交易`, "success");
        } else {
          showAlertModal("无交易信号", "当前没有符合条件的交易信号", "info");
        }
        await fetchAccountInfo();
        await fetchRecords();
      }
    } catch (error) {
      showAlertModal("处理失败", "请稍后重试", "error");
    } finally {
      setProcessingTrade(false);
    }
  }, [getToken, showAlertModal, fetchAccountInfo, fetchRecords]);

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
            await fetchAccountInfo();
            await fetchRecords();
          }
        } catch (error) {
          showAlertModal("重置失败", "请稍后重试", "error");
        }
      },
      "warning"
    );
  }, [getToken, showConfirmModal, showAlertModal, fetchAccountInfo, fetchRecords]);

  // 初始化加载
  useEffect(() => {
    fetchAccountInfo();
    fetchRecords();
  }, [fetchAccountInfo, fetchRecords]);

  // 实时行情轮询（交易时间10秒，非交易时间60秒）
  useEffect(() => {
    if (positions.length === 0) return;

    // 首次加载时更新价格
    updatePricesSilent();

    const interval = setInterval(() => {
      const trading = isTradingTime();
      // 交易时间内才自动刷新
      if (trading) {
        updatePricesSilent();
      }
    }, isTradingTime() ? 10000 : 60000); // 交易时间10秒，非交易时间60秒

    return () => clearInterval(interval);
  }, [positions.length, updatePricesSilent, isTradingTime]);

  // 格式化金额
  const formatMoney = (value: number) => {
    if (value >= 10000) {
      return `${(value / 10000).toFixed(2)}万`;
    }
    return value.toFixed(2);
  };

  // 格式化百分比
  const formatPercent = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
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
            <button
              onClick={() => router.push('/dashboard')}
              className="p-2 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </button>
            <div>
              <h1 className="text-lg font-bold text-white">模拟交易</h1>
              {lastUpdateTime && (
                <p className="text-[10px] text-slate-500">更新: {lastUpdateTime}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={updatePrices}
              disabled={refreshing}
              className="p-2 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 transition-colors"
            >
              <RefreshCw className={`w-5 h-5 text-slate-400 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={handleResetAccount}
              className="p-2 rounded-lg bg-slate-800/50 hover:bg-rose-500/20 transition-colors"
            >
              <RotateCcw className="w-5 h-5 text-slate-400 hover:text-rose-400" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* 免责声明 */}
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-amber-300/80">
              本功能仅供学习研究使用，不构成任何投资建议。模拟交易结果不代表真实交易表现。
            </p>
          </div>
        </div>

        {/* 账户概览 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* 总资产 */}
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <Wallet className="w-4 h-4 text-indigo-400" />
              <span className="text-xs text-slate-400">总资产</span>
            </div>
            <div className="text-xl font-bold text-white">
              ¥{formatMoney(totalAssets)}
            </div>
            <div className={`text-xs mt-1 ${(account?.total_profit || 0) >= 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
              {formatPercent(account?.total_profit_pct || 0)}
            </div>
          </div>

          {/* 可用资金 */}
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="w-4 h-4 text-emerald-400" />
              <span className="text-xs text-slate-400">可用资金</span>
            </div>
            <div className="text-xl font-bold text-white">
              ¥{formatMoney(account?.current_capital || 0)}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              初始: ¥{formatMoney(account?.initial_capital || 1000000)}
            </div>
          </div>

          {/* 持仓市值 */}
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="w-4 h-4 text-blue-400" />
              <span className="text-xs text-slate-400">持仓市值</span>
            </div>
            <div className="text-xl font-bold text-white">
              ¥{formatMoney(positionValue)}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              {positions.length} 只持仓
            </div>
          </div>

          {/* 累计盈亏 */}
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-2 mb-2">
              {(account?.total_profit || 0) >= 0 ? (
                <TrendingUp className="w-4 h-4 text-rose-400" />
              ) : (
                <TrendingDown className="w-4 h-4 text-emerald-400" />
              )}
              <span className="text-xs text-slate-400">累计盈亏</span>
            </div>
            <div className={`text-xl font-bold ${(account?.total_profit || 0) >= 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
              {(account?.total_profit || 0) >= 0 ? '+' : ''}¥{formatMoney(account?.total_profit || 0)}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              胜率: {(account?.win_rate || 0).toFixed(1)}%
            </div>
          </div>
        </div>

        {/* 自动交易控制 */}
        <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${autoTrading ? 'bg-emerald-500/20' : 'bg-slate-700/50'}`}>
                {autoTrading ? (
                  <Play className="w-5 h-5 text-emerald-400" />
                ) : (
                  <Pause className="w-5 h-5 text-slate-400" />
                )}
              </div>
              <div>
                <div className="text-sm font-medium text-white">自动交易</div>
                <div className="text-xs text-slate-400">
                  {autoTrading ? '已开启，将根据信号自动买卖' : '已关闭'}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={processAutoTrade}
                disabled={processingTrade}
                className="px-3 py-1.5 rounded-lg bg-indigo-500/20 text-indigo-400 text-sm hover:bg-indigo-500/30 transition-colors disabled:opacity-50"
              >
                {processingTrade ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  '立即执行'
                )}
              </button>
              <button
                onClick={toggleAutoTrade}
                className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  autoTrading
                    ? 'bg-rose-500/20 text-rose-400 hover:bg-rose-500/30'
                    : 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
                }`}
              >
                {autoTrading ? '关闭' : '开启'}
              </button>
            </div>
          </div>
        </div>

        {/* 交易统计 */}
        {stats && (
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <h3 className="text-sm font-medium text-white mb-3">交易统计</h3>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-4 text-center">
              <div>
                <div className="text-lg font-bold text-white">{stats.total_trades}</div>
                <div className="text-xs text-slate-400">总交易</div>
              </div>
              <div>
                <div className="text-lg font-bold text-emerald-400">{stats.win_count}</div>
                <div className="text-xs text-slate-400">盈利</div>
              </div>
              <div>
                <div className="text-lg font-bold text-rose-400">{stats.loss_count}</div>
                <div className="text-xs text-slate-400">亏损</div>
              </div>
              <div>
                <div className="text-lg font-bold text-indigo-400">{stats.win_rate.toFixed(1)}%</div>
                <div className="text-xs text-slate-400">胜率</div>
              </div>
              <div>
                <div className={`text-lg font-bold ${stats.avg_profit_pct >= 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                  {formatPercent(stats.avg_profit_pct)}
                </div>
                <div className="text-xs text-slate-400">平均收益</div>
              </div>
              <div>
                <div className="text-lg font-bold text-blue-400">{stats.avg_holding_days.toFixed(1)}天</div>
                <div className="text-xs text-slate-400">平均持有</div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 切换 */}
        <div className="flex gap-2 border-b border-slate-700/50 pb-2">
          <button
            onClick={() => setActiveTab('positions')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'positions'
                ? 'bg-indigo-500/20 text-indigo-400'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            持仓 ({positions.length})
          </button>
          <button
            onClick={() => setActiveTab('records')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'records'
                ? 'bg-indigo-500/20 text-indigo-400'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            交易记录 ({records.length})
          </button>
        </div>

        {/* 持仓列表 */}
        {activeTab === 'positions' && (
          <div className="space-y-3">
            {positions.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>暂无持仓</p>
                <p className="text-xs mt-1">开启自动交易后，系统将根据信号自动买入</p>
              </div>
            ) : (
              positions.map((position) => (
                <div
                  key={position.symbol}
                  className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <div className="font-medium text-white">{position.name}</div>
                      <div className="text-xs text-slate-400">{position.symbol}</div>
                    </div>
                    <div className="text-right">
                      <div className={`text-lg font-bold ${position.profit >= 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                        {position.profit >= 0 ? '+' : ''}¥{position.profit.toFixed(2)}
                      </div>
                      <div className={`text-xs ${position.profit_pct >= 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                        {formatPercent(position.profit_pct)}
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-4 gap-2 text-xs">
                    <div>
                      <div className="text-slate-400">持仓</div>
                      <div className="text-white">{position.quantity}股</div>
                    </div>
                    <div>
                      <div className="text-slate-400">成本</div>
                      <div className="text-white">¥{position.cost_price.toFixed(3)}</div>
                    </div>
                    <div>
                      <div className="text-slate-400">现价</div>
                      <div className="text-white">¥{(position.current_price || position.cost_price).toFixed(3)}</div>
                    </div>
                    <div>
                      <div className="text-slate-400">规则</div>
                      <div className="text-white">{position.trade_rule}</div>
                    </div>
                  </div>
                  <div className="mt-2 pt-2 border-t border-slate-700/50 flex items-center justify-between text-xs">
                    <span className="text-slate-400">
                      买入: {position.buy_date} | 可卖: {position.can_sell_date}
                    </span>
                    <span className={`px-2 py-0.5 rounded ${
                      position.holding_period === 'short' ? 'bg-amber-500/20 text-amber-400' :
                      position.holding_period === 'long' ? 'bg-blue-500/20 text-blue-400' :
                      'bg-indigo-500/20 text-indigo-400'
                    }`}>
                      {position.holding_period === 'short' ? '短线' :
                       position.holding_period === 'long' ? '中长线' : '波段'}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* 交易记录 */}
        {activeTab === 'records' && (
          <div className="space-y-3">
            {records.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>暂无交易记录</p>
              </div>
            ) : (
              records.map((record) => (
                <div
                  key={record.id}
                  className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        record.trade_type === 'buy'
                          ? 'bg-rose-500/20 text-rose-400'
                          : 'bg-emerald-500/20 text-emerald-400'
                      }`}>
                        {record.trade_type === 'buy' ? '买入' : '卖出'}
                      </span>
                      <span className="font-medium text-white">{record.name}</span>
                      <span className="text-xs text-slate-400">{record.symbol}</span>
                    </div>
                    <div className="text-xs text-slate-400">{record.trade_date}</div>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <div className="text-slate-400">数量</div>
                      <div className="text-white">{record.quantity}股</div>
                    </div>
                    <div>
                      <div className="text-slate-400">价格</div>
                      <div className="text-white">¥{record.price.toFixed(3)}</div>
                    </div>
                    <div>
                      <div className="text-slate-400">金额</div>
                      <div className="text-white">¥{formatMoney(record.amount)}</div>
                    </div>
                  </div>
                  {record.trade_type === 'sell' && record.profit !== null && (
                    <div className="mt-2 pt-2 border-t border-slate-700/50 flex items-center justify-between text-xs">
                      <span className="text-slate-400">
                        持有 {record.holding_days || 0} 天
                      </span>
                      <span className={`font-medium ${record.profit >= 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                        {record.profit >= 0 ? '+' : ''}¥{record.profit.toFixed(2)} ({formatPercent(record.profit_pct)})
                      </span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </main>

      {/* 弹窗 */}
      <AlertModal
        isOpen={showAlert}
        onClose={() => setShowAlert(false)}
        title={alertConfig.title}
        message={alertConfig.message}
        type={alertConfig.type}
      />
      <ConfirmModal
        isOpen={showConfirm}
        onClose={() => setShowConfirm(false)}
        onConfirm={() => {
          confirmConfig.onConfirm();
          setShowConfirm(false);
        }}
        title={confirmConfig.title}
        message={confirmConfig.message}
        type={confirmConfig.type}
      />
    </div>
  );
}
