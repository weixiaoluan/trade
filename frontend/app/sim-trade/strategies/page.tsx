"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  TrendingUp,
  TrendingDown,
  ArrowLeft,
  RefreshCw,
  Loader2,
  Settings,
  Play,
  Pause,
  ChevronDown,
  ChevronUp,
  Zap,
  Shield,
  Clock,
  Target,
  DollarSign,
  BarChart3,
  AlertCircle,
  Check,
  X,
  Info,
} from "lucide-react";
import { API_BASE } from "@/lib/config";

interface UserInfo {
  username: string;
  phone?: string;
  role?: string;
  status?: string;
}

interface Strategy {
  id: string;
  name: string;
  category: string;
  description: string;
  risk_level: string;
  applicable_types: string[];
  entry_logic: string;
  exit_logic: string;
  min_capital: number;
  backtest_return: number | null;
  backtest_sharpe: number | null;
  backtest_max_drawdown: number | null;
}

interface StrategyConfig {
  id: number;
  strategy_id: string;
  strategy_name: string;
  strategy_category: string;
  enabled: number;
  allocated_capital: number;
  min_capital: number;
  params: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface StrategyPerformance {
  strategy_id: string;
  strategy_name: string;
  total_return: number;
  daily_return: number;
  win_rate: number;
  max_drawdown: number;
  sharpe_ratio: number;
  trade_count: number;
}

interface StrategyTradeStats {
  strategy_id: string;
  strategy_name: string;
  total_trades: number;
  buy_count: number;
  sell_count: number;
  total_amount: number;
  total_profit: number;
  win_count: number;
  loss_count: number;
  win_rate: number;
  avg_profit_pct: number;
  max_profit_pct: number;
  min_profit_pct: number;
  avg_holding_days: number;
}

interface TradeRecord {
  id: number;
  symbol: string;
  name: string;
  trade_type: string;
  quantity: number;
  price: number;
  amount: number;
  profit: number | null;
  profit_pct: number | null;
  holding_days: number | null;
  trade_date: string;
  created_at: string;
}

const categoryLabels: Record<string, string> = {
  short: "短线",
  swing: "波段",
  long: "长线",
};

const riskLabels: Record<string, { label: string; color: string }> = {
  low: { label: "低风险", color: "text-green-400" },
  medium: { label: "中风险", color: "text-yellow-400" },
  high: { label: "高风险", color: "text-red-400" },
};

export default function StrategiesPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [userConfigs, setUserConfigs] = useState<StrategyConfig[]>([]);
  const [performances, setPerformances] = useState<StrategyPerformance[]>([]);
  const [totalAllocated, setTotalAllocated] = useState(0);
  const [availableCapital, setAvailableCapital] = useState(100000);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [expandedStrategy, setExpandedStrategy] = useState<string | null>(null);
  const [editingConfig, setEditingConfig] = useState<string | null>(null);
  const [editCapital, setEditCapital] = useState<number>(0);
  const [saving, setSaving] = useState(false);
  const [executing, setExecuting] = useState<string | null>(null);
  const [tradeStats, setTradeStats] = useState<Record<string, StrategyTradeStats>>({});
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const getAuthHeader = useCallback((): Record<string, string> => {
    const token = localStorage.getItem("token");
    if (token) {
      return { Authorization: `Bearer ${token}` };
    }
    return {};
  }, []);

  const checkAuth = useCallback(() => {
    const token = localStorage.getItem("token");
    const storedUser = localStorage.getItem("user");
    if (!token || !storedUser) {
      router.push("/login");
      return false;
    }
    try {
      setUser(JSON.parse(storedUser));
      return true;
    } catch {
      router.push("/login");
      return false;
    }
  }, [router]);

  const fetchStrategies = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/strategies`, {
        headers: getAuthHeader(),
      });
      if (response.ok) {
        const data = await response.json();
        setStrategies(data.strategies || []);
      }
    } catch (err) {
      console.error("获取策略列表失败:", err);
    }
  }, [getAuthHeader]);

  const fetchUserConfigs = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/sim-trade/strategies`, {
        headers: getAuthHeader(),
      });
      if (response.ok) {
        const data = await response.json();
        setUserConfigs(data.configs || []);
        setTotalAllocated(data.total_allocated || 0);
      }
    } catch (err) {
      console.error("获取用户配置失败:", err);
    }
  }, [getAuthHeader]);

  const fetchPerformances = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/sim-trade/strategies/performance`, {
        headers: getAuthHeader(),
      });
      if (response.ok) {
        const data = await response.json();
        setPerformances(data.performances || []);
      }
    } catch (err) {
      console.error("获取性能数据失败:", err);
    }
  }, [getAuthHeader]);

  const fetchAccountInfo = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/sim-trade/account`, {
        headers: getAuthHeader(),
      });
      if (response.ok) {
        const data = await response.json();
        setAvailableCapital(data.account?.current_capital || 100000);
      }
    } catch (err) {
      console.error("获取账户信息失败:", err);
    }
  }, [getAuthHeader]);

  const fetchTradeStats = useCallback(async (strategyId: string) => {
    try {
      const response = await fetch(
        `${API_BASE}/api/sim-trade/strategies/${strategyId}/stats`,
        { headers: getAuthHeader() }
      );
      if (response.ok) {
        const data = await response.json();
        setTradeStats(prev => ({ ...prev, [strategyId]: data }));
      }
    } catch (err) {
      console.error("获取交易统计失败:", err);
    }
  }, [getAuthHeader]);

  const handleExecuteStrategy = async (strategyId: string) => {
    setExecuting(strategyId);
    setError(null);
    setSuccessMsg(null);
    try {
      const response = await fetch(
        `${API_BASE}/api/sim-trade/strategies/${strategyId}/execute`,
        {
          method: "POST",
          headers: getAuthHeader(),
        }
      );
      const data = await response.json();
      if (response.ok) {
        if (data.orders > 0) {
          setSuccessMsg(`策略执行成功: ${data.executed}/${data.orders} 笔交易, 目标: ${data.target || '-'}`);
        } else {
          setSuccessMsg(data.message || "策略执行完成，无需交易");
        }
        // 刷新数据
        fetchUserConfigs();
        fetchPerformances();
        fetchAccountInfo();
        fetchTradeStats(strategyId);
      } else {
        setError(data.detail || "策略执行失败");
      }
    } catch (err) {
      console.error("执行策略失败:", err);
      setError("网络错误，请稍后重试");
    } finally {
      setExecuting(null);
    }
  };

  useEffect(() => {
    const init = async () => {
      const isAuth = checkAuth();
      if (!isAuth) return;
      
      // 优先加载策略列表，快速显示页面
      await fetchStrategies();
      setLoading(false);
      
      // 后台加载次要数据
      fetchUserConfigs();
      fetchPerformances();
      fetchAccountInfo();
    };
    init();
  }, [checkAuth, fetchStrategies, fetchUserConfigs, fetchPerformances, fetchAccountInfo]);

  const getUserConfig = (strategyId: string) => {
    return userConfigs.find((c) => c.strategy_id === strategyId);
  };

  const getPerformance = (strategyId: string) => {
    return performances.find((p) => p.strategy_id === strategyId);
  };

  const handleToggleStrategy = async (strategyId: string, currentEnabled: boolean) => {
    setSaving(true);
    setError(null);
    try {
      const config = getUserConfig(strategyId);
      if (config) {
        const response = await fetch(
          `${API_BASE}/api/sim-trade/strategies/${strategyId}`,
          {
            method: "PUT",
            headers: {
              ...getAuthHeader(),
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ enabled: !currentEnabled }),
          }
        );
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail || "更新失败");
        }
      } else {
        const strategy = strategies.find((s) => s.id === strategyId);
        const response = await fetch(`${API_BASE}/api/sim-trade/strategies`, {
          method: "POST",
          headers: {
            ...getAuthHeader(),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            strategy_id: strategyId,
            enabled: true,
            allocated_capital: strategy?.min_capital || 10000,
          }),
        });
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail || "添加失败");
        }
      }
      await fetchUserConfigs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveCapital = async (strategyId: string) => {
    if (editCapital <= 0) {
      setError("分配资金必须大于0");
      return;
    }

    const strategy = strategies.find((s) => s.id === strategyId);
    if (strategy && editCapital < strategy.min_capital) {
      setError(`分配资金不能低于最低要求 ¥${strategy.min_capital.toLocaleString()}`);
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const config = getUserConfig(strategyId);
      if (config) {
        const response = await fetch(
          `${API_BASE}/api/sim-trade/strategies/${strategyId}`,
          {
            method: "PUT",
            headers: {
              ...getAuthHeader(),
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ allocated_capital: editCapital }),
          }
        );
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail || "更新失败");
        }
      } else {
        const response = await fetch(`${API_BASE}/api/sim-trade/strategies`, {
          method: "POST",
          headers: {
            ...getAuthHeader(),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            strategy_id: strategyId,
            enabled: true,
            allocated_capital: editCapital,
          }),
        });
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail || "添加失败");
        }
      }
      await fetchUserConfigs();
      setEditingConfig(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteConfig = async (strategyId: string) => {
    setSaving(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/api/sim-trade/strategies/${strategyId}`,
        {
          method: "DELETE",
          headers: getAuthHeader(),
        }
      );
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "删除失败");
      }
      await fetchUserConfigs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除失败");
    } finally {
      setSaving(false);
    }
  };

  const filteredStrategies = strategies.filter((s) => {
    if (selectedCategory === "all") return true;
    return s.category === selectedCategory;
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-gray-900/80 backdrop-blur-lg border-b border-gray-700/50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.push("/sim-trade")}
                className="p-2 hover:bg-gray-700/50 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-5 h-5 text-gray-400" />
              </button>
              <div>
                <h1 className="text-xl font-bold text-white">策略池</h1>
                <p className="text-sm text-gray-400">选择和配置交易策略</p>
              </div>
            </div>
            <button
              onClick={() => {
                fetchStrategies();
                fetchUserConfigs();
                fetchPerformances();
              }}
              className="p-2 hover:bg-gray-700/50 rounded-lg transition-colors"
            >
              <RefreshCw className="w-5 h-5 text-gray-400" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* 资金分配概览 */}
        <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-green-400" />
              资金分配
            </h2>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <p className="text-sm text-gray-400">可用资金</p>
              <p className="text-xl font-bold text-white">
                ¥{availableCapital.toLocaleString()}
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-400">已分配</p>
              <p className="text-xl font-bold text-yellow-400">
                ¥{totalAllocated.toLocaleString()}
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-400">剩余可分配</p>
              <p className="text-xl font-bold text-green-400">
                ¥{Math.max(0, availableCapital - totalAllocated).toLocaleString()}
              </p>
            </div>
          </div>
          {totalAllocated > availableCapital && (
            <div className="mt-3 p-2 bg-red-500/20 rounded-lg flex items-center gap-2 text-red-400 text-sm">
              <AlertCircle className="w-4 h-4" />
              已分配资金超过可用资金
            </div>
          )}
        </div>

        {/* 错误提示 */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg flex items-center gap-2 text-red-400"
            >
              <AlertCircle className="w-4 h-4" />
              {error}
              <button onClick={() => setError(null)} className="ml-auto">
                <X className="w-4 h-4" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 成功提示 */}
        <AnimatePresence>
          {successMsg && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="p-3 bg-green-500/20 border border-green-500/50 rounded-lg flex items-center gap-2 text-green-400"
            >
              <Check className="w-4 h-4" />
              {successMsg}
              <button onClick={() => setSuccessMsg(null)} className="ml-auto">
                <X className="w-4 h-4" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 分类筛选 */}
        <div className="flex gap-2">
          {[
            { value: "all", label: "全部" },
            { value: "short", label: "短线" },
            { value: "swing", label: "波段" },
            { value: "long", label: "长线" },
          ].map((cat) => (
            <button
              key={cat.value}
              onClick={() => setSelectedCategory(cat.value)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedCategory === cat.value
                  ? "bg-blue-500 text-white"
                  : "bg-gray-700/50 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* 策略列表 */}
        <div className="space-y-4">
          {filteredStrategies.map((strategy) => {
            const config = getUserConfig(strategy.id);
            const perf = getPerformance(strategy.id);
            const isEnabled = config?.enabled === 1;
            const isExpanded = expandedStrategy === strategy.id;
            const isEditing = editingConfig === strategy.id;
            const risk = riskLabels[strategy.risk_level] || riskLabels.medium;

            return (
              <motion.div
                key={strategy.id}
                layout
                className="bg-gray-800/50 rounded-xl border border-gray-700/50 overflow-hidden"
              >
                {/* 策略头部 */}
                <div className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-lg font-semibold text-white">
                          {strategy.name}
                        </h3>
                        <span className="px-2 py-0.5 text-xs rounded bg-gray-700 text-gray-300">
                          {categoryLabels[strategy.category] || strategy.category}
                        </span>
                        <span className={`text-xs ${risk.color}`}>
                          {risk.label}
                        </span>
                      </div>
                      <p className="text-sm text-gray-400 line-clamp-2">
                        {strategy.description}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {/* 立即执行按钮 */}
                      {isEnabled && (
                        <button
                          onClick={() => handleExecuteStrategy(strategy.id)}
                          disabled={executing === strategy.id}
                          className="p-2 rounded-lg transition-colors bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 disabled:opacity-50"
                          title="立即执行策略"
                        >
                          {executing === strategy.id ? (
                            <Loader2 className="w-5 h-5 animate-spin" />
                          ) : (
                            <Zap className="w-5 h-5" />
                          )}
                        </button>
                      )}
                      <button
                        onClick={() => handleToggleStrategy(strategy.id, isEnabled)}
                        disabled={saving}
                        className={`p-2 rounded-lg transition-colors ${
                          isEnabled
                            ? "bg-green-500/20 text-green-400 hover:bg-green-500/30"
                            : "bg-gray-700/50 text-gray-400 hover:bg-gray-700"
                        }`}
                        title={isEnabled ? "已启用自动交易" : "未启用"}
                      >
                        {isEnabled ? (
                          <Play className="w-5 h-5" />
                        ) : (
                          <Pause className="w-5 h-5" />
                        )}
                      </button>
                      <button
                        onClick={() => {
                          setExpandedStrategy(isExpanded ? null : strategy.id);
                          if (!isExpanded && isEnabled) {
                            fetchTradeStats(strategy.id);
                          }
                        }}
                        className="p-2 hover:bg-gray-700/50 rounded-lg transition-colors"
                      >
                        {isExpanded ? (
                          <ChevronUp className="w-5 h-5 text-gray-400" />
                        ) : (
                          <ChevronDown className="w-5 h-5 text-gray-400" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* 简要信息 */}
                  <div className="mt-3 grid grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500">最低资金</p>
                      <p className="text-white font-medium">
                        ¥{strategy.min_capital.toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500">回测收益</p>
                      <p
                        className={`font-medium ${
                          (strategy.backtest_return || 0) >= 0
                            ? "text-green-400"
                            : "text-red-400"
                        }`}
                      >
                        {strategy.backtest_return
                          ? `${strategy.backtest_return > 0 ? "+" : ""}${strategy.backtest_return}%`
                          : "-"}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500">已分配</p>
                      <p className="text-white font-medium">
                        {config
                          ? `¥${config.allocated_capital.toLocaleString()}`
                          : "-"}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500">实盘收益</p>
                      <p
                        className={`font-medium ${
                          (perf?.total_return || 0) >= 0
                            ? "text-green-400"
                            : "text-red-400"
                        }`}
                      >
                        {perf
                          ? `${perf.total_return > 0 ? "+" : ""}${perf.total_return.toFixed(2)}%`
                          : "-"}
                      </p>
                    </div>
                  </div>
                </div>

                {/* 展开详情 */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="border-t border-gray-700/50"
                    >
                      <div className="p-4 space-y-4">
                        {/* 策略逻辑 */}
                        <div className="grid grid-cols-2 gap-4">
                          <div className="bg-gray-700/30 rounded-lg p-3">
                            <h4 className="text-sm font-medium text-green-400 mb-2 flex items-center gap-1">
                              <TrendingUp className="w-4 h-4" />
                              入场逻辑
                            </h4>
                            <p className="text-sm text-gray-300">
                              {strategy.entry_logic}
                            </p>
                          </div>
                          <div className="bg-gray-700/30 rounded-lg p-3">
                            <h4 className="text-sm font-medium text-red-400 mb-2 flex items-center gap-1">
                              <TrendingDown className="w-4 h-4" />
                              出场逻辑
                            </h4>
                            <p className="text-sm text-gray-300">
                              {strategy.exit_logic}
                            </p>
                          </div>
                        </div>

                        {/* 适用标的 */}
                        <div>
                          <h4 className="text-sm font-medium text-gray-400 mb-2">
                            适用标的
                          </h4>
                          <div className="flex flex-wrap gap-2">
                            {strategy.applicable_types.map((type) => (
                              <span
                                key={type}
                                className="px-2 py-1 text-xs bg-blue-500/20 text-blue-400 rounded"
                              >
                                {type}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* 回测指标 */}
                        <div className="grid grid-cols-3 gap-4">
                          <div className="bg-gray-700/30 rounded-lg p-3 text-center">
                            <p className="text-xs text-gray-500 mb-1">夏普比率</p>
                            <p className="text-lg font-bold text-white">
                              {strategy.backtest_sharpe?.toFixed(2) || "-"}
                            </p>
                          </div>
                          <div className="bg-gray-700/30 rounded-lg p-3 text-center">
                            <p className="text-xs text-gray-500 mb-1">最大回撤</p>
                            <p className="text-lg font-bold text-red-400">
                              {strategy.backtest_max_drawdown
                                ? `-${strategy.backtest_max_drawdown}%`
                                : "-"}
                            </p>
                          </div>
                          <div className="bg-gray-700/30 rounded-lg p-3 text-center">
                            <p className="text-xs text-gray-500 mb-1">年化收益</p>
                            <p className="text-lg font-bold text-green-400">
                              {strategy.backtest_return
                                ? `${strategy.backtest_return > 0 ? "+" : ""}${strategy.backtest_return}%`
                                : "-"}
                            </p>
                          </div>
                        </div>

                        {/* 资金配置 */}
                        <div className="bg-gray-700/30 rounded-lg p-3">
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="text-sm font-medium text-gray-400">
                              资金配置
                            </h4>
                            {config && !isEditing && (
                              <button
                                onClick={() => {
                                  setEditingConfig(strategy.id);
                                  setEditCapital(config.allocated_capital);
                                }}
                                className="text-sm text-blue-400 hover:text-blue-300"
                              >
                                编辑
                              </button>
                            )}
                          </div>
                          {isEditing ? (
                            <div className="flex items-center gap-2">
                              <input
                                type="number"
                                value={editCapital}
                                onChange={(e) =>
                                  setEditCapital(Number(e.target.value))
                                }
                                className="flex-1 px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm"
                                placeholder="分配资金"
                                min={strategy.min_capital}
                              />
                              <button
                                onClick={() => handleSaveCapital(strategy.id)}
                                disabled={saving}
                                className="p-2 bg-green-500 hover:bg-green-600 rounded-lg text-white"
                              >
                                <Check className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => setEditingConfig(null)}
                                className="p-2 bg-gray-600 hover:bg-gray-500 rounded-lg text-white"
                              >
                                <X className="w-4 h-4" />
                              </button>
                            </div>
                          ) : config ? (
                            <div className="flex items-center justify-between">
                              <p className="text-white">
                                ¥{config.allocated_capital.toLocaleString()}
                              </p>
                              <button
                                onClick={() => handleDeleteConfig(strategy.id)}
                                disabled={saving}
                                className="text-sm text-red-400 hover:text-red-300"
                              >
                                删除配置
                              </button>
                            </div>
                          ) : (
                            <div className="flex items-center gap-2">
                              <input
                                type="number"
                                value={editCapital || strategy.min_capital}
                                onChange={(e) =>
                                  setEditCapital(Number(e.target.value))
                                }
                                className="flex-1 px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm"
                                placeholder="分配资金"
                                min={strategy.min_capital}
                              />
                              <button
                                onClick={() => {
                                  setEditCapital(
                                    editCapital || strategy.min_capital
                                  );
                                  handleSaveCapital(strategy.id);
                                }}
                                disabled={saving}
                                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 rounded-lg text-white text-sm"
                              >
                                启用策略
                              </button>
                            </div>
                          )}
                        </div>

                        {/* 交易统计（实盘数据） */}
                        {tradeStats[strategy.id] && (
                          <div className="bg-gray-700/30 rounded-lg p-3">
                            <h4 className="text-sm font-medium text-blue-400 mb-3 flex items-center gap-2">
                              <BarChart3 className="w-4 h-4" />
                              实盘交易统计
                            </h4>
                            <div className="grid grid-cols-4 gap-4 text-center mb-3">
                              <div>
                                <p className="text-xs text-gray-500">总交易</p>
                                <p className="font-bold text-white">
                                  {tradeStats[strategy.id].total_trades}笔
                                </p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-500">买入/卖出</p>
                                <p className="font-bold text-white">
                                  {tradeStats[strategy.id].buy_count}/{tradeStats[strategy.id].sell_count}
                                </p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-500">胜率</p>
                                <p className={`font-bold ${tradeStats[strategy.id].win_rate >= 50 ? 'text-green-400' : 'text-yellow-400'}`}>
                                  {tradeStats[strategy.id].win_rate.toFixed(1)}%
                                </p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-500">总盈亏</p>
                                <p className={`font-bold ${tradeStats[strategy.id].total_profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                  {tradeStats[strategy.id].total_profit >= 0 ? '+' : ''}¥{tradeStats[strategy.id].total_profit.toLocaleString()}
                                </p>
                              </div>
                            </div>
                            <div className="grid grid-cols-4 gap-4 text-center">
                              <div>
                                <p className="text-xs text-gray-500">平均收益</p>
                                <p className={`font-bold ${tradeStats[strategy.id].avg_profit_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                  {tradeStats[strategy.id].avg_profit_pct >= 0 ? '+' : ''}{tradeStats[strategy.id].avg_profit_pct.toFixed(2)}%
                                </p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-500">最大盈利</p>
                                <p className="font-bold text-green-400">
                                  +{tradeStats[strategy.id].max_profit_pct.toFixed(2)}%
                                </p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-500">最大亏损</p>
                                <p className="font-bold text-red-400">
                                  {tradeStats[strategy.id].min_profit_pct.toFixed(2)}%
                                </p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-500">平均持仓</p>
                                <p className="font-bold text-white">
                                  {tradeStats[strategy.id].avg_holding_days.toFixed(1)}天
                                </p>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* 实盘性能（如果有） */}
                        {perf && (
                          <div className="bg-gray-700/30 rounded-lg p-3">
                            <h4 className="text-sm font-medium text-gray-400 mb-3">
                              策略性能
                            </h4>
                            <div className="grid grid-cols-4 gap-4 text-center">
                              <div>
                                <p className="text-xs text-gray-500">总收益率</p>
                                <p
                                  className={`font-bold ${
                                    perf.total_return >= 0
                                      ? "text-green-400"
                                      : "text-red-400"
                                  }`}
                                >
                                  {perf.total_return > 0 ? "+" : ""}
                                  {perf.total_return.toFixed(2)}%
                                </p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-500">胜率</p>
                                <p className="font-bold text-white">
                                  {perf.win_rate.toFixed(1)}%
                                </p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-500">最大回撤</p>
                                <p className="font-bold text-red-400">
                                  -{perf.max_drawdown.toFixed(2)}%
                                </p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-500">夏普比率</p>
                                <p className="font-bold text-white">
                                  {perf.sharpe_ratio?.toFixed(2) || '-'}
                                </p>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>

        {filteredStrategies.length === 0 && (
          <div className="text-center py-12">
            <Info className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">没有找到相关策略</p>
          </div>
        )}
      </main>
    </div>
  );
}
