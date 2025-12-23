"use client";

import { useState, useEffect, useCallback } from "react";
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
} from "lucide-react";
import { UserHeader } from "@/components/ui/UserHeader";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

interface UserInfo {
  username: string;
  phone?: string;
}

interface WatchlistItem {
  symbol: string;
  name?: string;
  type?: string;
  added_at?: string;
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

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [tasks, setTasks] = useState<Record<string, TaskStatus>>({});
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(false);

  // 弹窗状态
  const [showAddModal, setShowAddModal] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);
  const [showOcrModal, setShowOcrModal] = useState(false);
  const [currentReport, setCurrentReport] = useState<any>(null);
  const [addSymbol, setAddSymbol] = useState("");

  // OCR 相关状态
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrResults, setOcrResults] = useState<Array<{ symbol: string; name: string; type: string; selected: boolean }>>([]);

  const getToken = () => localStorage.getItem("token");

  // 检查登录状态
  useEffect(() => {
    const checkAuth = async () => {
      const token = getToken();
      const storedUser = localStorage.getItem("user");

      if (!token || !storedUser) {
        router.push("/login");
        return;
      }

      try {
        const response = await fetch(`${API_BASE}/api/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!response.ok) {
          localStorage.removeItem("token");
          localStorage.removeItem("user");
          router.push("/login");
          return;
        }

        const data = await response.json();
        setUser(data.user);
        setAuthChecked(true);
      } catch (error) {
        router.push("/login");
      }
    };

    checkAuth();
  }, [router]);

  // 获取自选列表
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
  }, []);

  // 获取任务状态
  const fetchTasks = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE}/api/analyze/tasks`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setTasks(data.tasks || {});
      }
    } catch (error) {
      console.error("获取任务状态失败:", error);
    }
  }, []);

  // 获取报告列表
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
  }, []);

  // 初始化数据
  useEffect(() => {
    if (authChecked) {
      fetchWatchlist();
      fetchTasks();
      fetchReports();

      // 定时刷新任务状态
      const interval = setInterval(() => {
        fetchTasks();
        fetchReports();
      }, 5000);

      return () => clearInterval(interval);
    }
  }, [authChecked, fetchWatchlist, fetchTasks, fetchReports]);

  // 退出登录
  const handleLogout = () => {
    setUser(null);
    router.push("/login");
  };

  // 切换选择
  const toggleSelect = (symbol: string) => {
    const newSelected = new Set(selectedItems);
    if (newSelected.has(symbol)) {
      newSelected.delete(symbol);
    } else {
      newSelected.add(symbol);
    }
    setSelectedItems(newSelected);
  };

  // 全选/取消全选
  const toggleSelectAll = () => {
    if (selectedItems.size === watchlist.length) {
      setSelectedItems(new Set());
    } else {
      setSelectedItems(new Set(watchlist.map((item) => item.symbol)));
    }
  };

  // 添加自选
  const handleAddSymbol = async () => {
    if (!addSymbol.trim()) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/watchlist`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ symbol: addSymbol.trim().toUpperCase() }),
      });

      if (response.ok) {
        setAddSymbol("");
        setShowAddModal(false);
        fetchWatchlist();
      }
    } catch (error) {
      console.error("添加失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 图片上传 OCR 识别（支持多张图片，最多10张）
  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    // 限制最多10张
    if (files.length > 10) {
      alert("最多只能上传10张图片");
      e.target.value = "";
      return;
    }

    setOcrLoading(true);
    const formData = new FormData();
    
    // 添加所有图片
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
      // 重置 input
      e.target.value = "";
    }
  };

  // 切换 OCR 结果选中状态
  const toggleOcrResult = (index: number) => {
    setOcrResults(prev => prev.map((item, i) => 
      i === index ? { ...item, selected: !item.selected } : item
    ));
  };

  // 批量添加 OCR 识别结果
  const handleAddOcrResults = async () => {
    const selectedSymbols = ocrResults
      .filter(item => item.selected)
      .map(item => ({ symbol: item.symbol, name: item.name, type: item.type }));

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
        setShowOcrModal(false);
        setOcrResults([]);
        fetchWatchlist();
      }
    } catch (error) {
      console.error("批量添加失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 删除单个自选
  const handleDeleteSingle = async (symbol: string) => {
    try {
      const response = await fetch(
        `${API_BASE}/api/watchlist/${encodeURIComponent(symbol)}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${getToken()}` },
        }
      );

      if (response.ok) {
        fetchWatchlist();
        selectedItems.delete(symbol);
        setSelectedItems(new Set(selectedItems));
      }
    } catch (error) {
      console.error("删除失败:", error);
    }
  };

  // 批量删除
  const handleBatchDelete = async () => {
    if (selectedItems.size === 0) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/watchlist/batch-delete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(Array.from(selectedItems)),
      });

      if (response.ok) {
        setSelectedItems(new Set());
        fetchWatchlist();
      }
    } catch (error) {
      console.error("批量删除失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 单个分析
  const handleAnalyzeSingle = async (symbol: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/analyze/background`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ ticker: symbol }),
      });

      if (response.ok) {
        fetchTasks();
      }
    } catch (error) {
      console.error("启动分析失败:", error);
    }
  };

  // 批量分析
  const handleBatchAnalyze = async () => {
    if (selectedItems.size === 0) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/analyze/batch`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(Array.from(selectedItems)),
      });

      if (response.ok) {
        fetchTasks();
      }
    } catch (error) {
      console.error("批量分析失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 查看报告 - 跳转到独立的报告页面
  const handleViewReport = (symbol: string) => {
    router.push(`/report/${encodeURIComponent(symbol)}`);
  };

  // 获取任务状态
  const getTaskStatus = (symbol: string): TaskStatus | null => {
    return tasks[symbol] || null;
  };

  // 获取报告
  const getReport = (symbol: string): ReportSummary | null => {
    return reports.find((r) => r.symbol === symbol) || null;
  };

  // 获取类型标签
  const getTypeLabel = (type?: string) => {
    switch (type) {
      case "stock":
        return "股票";
      case "etf":
        return "ETF";
      case "fund":
        return "基金";
      default:
        return "";
    }
  };

  if (!authChecked) {
    return (
      <main className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto mb-4"></div>
          <p className="text-slate-400">加载中...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#020617] relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 -left-1/4 w-[800px] h-[800px] bg-indigo-500/5 rounded-full blur-[150px]" />
        <div className="absolute bottom-0 -right-1/4 w-[600px] h-[600px] bg-violet-500/5 rounded-full blur-[120px]" />
      </div>

      {/* Header */}
      <header className="relative z-10 border-b border-white/[0.06] bg-[#020617]/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 p-[1px]">
              <div className="w-full h-full rounded-xl bg-[#020617] flex items-center justify-center">
                <Bot className="w-5 h-5 text-indigo-400" />
              </div>
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-100">AI 智能投研</h1>
              <p className="text-xs text-slate-500">Dashboard</p>
            </div>
          </div>

          {user && <UserHeader user={user} onLogout={handleLogout} />}
        </div>
      </header>

      {/* Main Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-4 py-8">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-semibold text-slate-100">我的自选</h2>
            <span className="text-sm text-slate-500">
              ({watchlist.length} 个标的)
            </span>
          </div>

          <div className="flex items-center gap-2">
            {selectedItems.size > 0 && (
              <>
                <button
                  onClick={handleBatchAnalyze}
                  disabled={loading}
                  className="flex items-center gap-2 px-4 py-2 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-400 rounded-lg transition-all disabled:opacity-50"
                >
                  <Play className="w-4 h-4" />
                  批量分析 ({selectedItems.size})
                </button>
                <button
                  onClick={handleBatchDelete}
                  disabled={loading}
                  className="flex items-center gap-2 px-4 py-2 bg-rose-600/20 hover:bg-rose-600/30 text-rose-400 rounded-lg transition-all disabled:opacity-50"
                >
                  <Trash2 className="w-4 h-4" />
                  批量删除
                </button>
              </>
            )}
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-white/[0.05] hover:bg-white/[0.08] text-slate-300 rounded-lg transition-all"
            >
              <Plus className="w-4 h-4" />
              添加自选
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

        {/* Watchlist Table */}
        <div className="bg-white/[0.02] backdrop-blur-xl rounded-2xl border border-white/[0.06] overflow-hidden">
          {/* Table Header */}
          <div className="grid grid-cols-12 gap-4 px-6 py-4 border-b border-white/[0.06] bg-white/[0.02]">
            <div className="col-span-1 flex items-center">
              <button
                onClick={toggleSelectAll}
                className="text-slate-400 hover:text-slate-200"
              >
                {selectedItems.size === watchlist.length && watchlist.length > 0 ? (
                  <CheckSquare className="w-5 h-5" />
                ) : (
                  <Square className="w-5 h-5" />
                )}
              </button>
            </div>
            <div className="col-span-3 text-sm font-medium text-slate-400">
              代码 / 名称
            </div>
            <div className="col-span-2 text-sm font-medium text-slate-400">
              类型
            </div>
            <div className="col-span-2 text-sm font-medium text-slate-400">
              分析状态
            </div>
            <div className="col-span-4 text-sm font-medium text-slate-400 text-right">
              操作
            </div>
          </div>

          {/* Table Body */}
          {watchlist.length === 0 ? (
            <div className="py-16 text-center">
              <Bot className="w-16 h-16 text-slate-700 mx-auto mb-4" />
              <p className="text-slate-500 mb-2">暂无自选标的</p>
              <button
                onClick={() => setShowAddModal(true)}
                className="text-indigo-400 hover:text-indigo-300 text-sm"
              >
                点击添加自选
              </button>
            </div>
          ) : (
            <div className="divide-y divide-white/[0.04]">
              {watchlist.map((item) => {
                const task = getTaskStatus(item.symbol);
                const report = getReport(item.symbol);
                const isSelected = selectedItems.has(item.symbol);

                return (
                  <div
                    key={item.symbol}
                    className={`grid grid-cols-12 gap-4 px-6 py-4 hover:bg-white/[0.02] transition-all ${
                      isSelected ? "bg-indigo-500/5" : ""
                    }`}
                  >
                    {/* Checkbox */}
                    <div className="col-span-1 flex items-center">
                      <button
                        onClick={() => toggleSelect(item.symbol)}
                        className="text-slate-400 hover:text-slate-200"
                      >
                        {isSelected ? (
                          <CheckSquare className="w-5 h-5 text-indigo-400" />
                        ) : (
                          <Square className="w-5 h-5" />
                        )}
                      </button>
                    </div>

                    {/* Symbol / Name */}
                    <div className="col-span-3">
                      <div className="font-mono font-semibold text-slate-100">
                        {item.symbol}
                      </div>
                      {item.name && (
                        <div className="text-sm text-slate-500">{item.name}</div>
                      )}
                    </div>

                    {/* Type */}
                    <div className="col-span-2 flex items-center">
                      {item.type && (
                        <span className="px-2 py-1 text-xs bg-slate-800 text-slate-400 rounded">
                          {getTypeLabel(item.type)}
                        </span>
                      )}
                    </div>

                    {/* Status */}
                    <div className="col-span-2 flex items-center">
                      {(() => {
                        // 检测任务是否超时（超过10分钟未完成视为失败）
                        const isTaskTimeout = task?.status === "running" && task?.updated_at && 
                          (Date.now() - new Date(task.updated_at).getTime() > 10 * 60 * 1000);
                        
                        if (task?.status === "failed" || isTaskTimeout) {
                          return (
                            <div className="flex items-center gap-2 text-rose-400">
                              <AlertCircle className="w-4 h-4" />
                              <span className="text-sm">分析失败</span>
                            </div>
                          );
                        } else if (task?.status === "running") {
                          return (
                            <div className="flex items-center gap-2 text-amber-400">
                              <Loader2 className="w-4 h-4 animate-spin" />
                              <span className="text-sm">{task.progress}%</span>
                            </div>
                          );
                        } else if (task?.status === "pending") {
                          return (
                            <div className="flex items-center gap-2 text-slate-400">
                              <Clock className="w-4 h-4" />
                              <span className="text-sm">等待中</span>
                            </div>
                          );
                        } else if (report) {
                          return (
                            <div className="flex items-center gap-2 text-emerald-400">
                              <Check className="w-4 h-4" />
                              <span className="text-sm">已完成</span>
                            </div>
                          );
                        } else {
                          return <span className="text-sm text-slate-500">未分析</span>;
                        }
                      })()}
                    </div>

                    {/* Actions */}
                    <div className="col-span-4 flex items-center justify-end gap-2">
                      {(() => {
                        // 检测任务是否超时
                        const isTaskTimeout = task?.status === "running" && task?.updated_at && 
                          (Date.now() - new Date(task.updated_at).getTime() > 10 * 60 * 1000);
                        const isFailed = task?.status === "failed" || isTaskTimeout;
                        const isRunning = task?.status === "running" && !isTaskTimeout;
                        const isPending = task?.status === "pending";
                        
                        return (
                          <button
                            onClick={() => handleAnalyzeSingle(item.symbol)}
                            disabled={isRunning || isPending}
                            className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
                              isFailed 
                                ? "bg-rose-600/20 hover:bg-rose-600/30 text-rose-400" 
                                : "bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-400"
                            }`}
                          >
                            <Play className="w-3.5 h-3.5" />
                            {isFailed ? "重新分析" : "AI分析"}
                          </button>
                        );
                      })()}

                      {report && (
                        <button
                          onClick={() => handleViewReport(item.symbol)}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 text-sm rounded-lg transition-all"
                        >
                          <FileText className="w-3.5 h-3.5" />
                          查看报告
                        </button>
                      )}

                      <button
                        onClick={() => handleDeleteSingle(item.symbol)}
                        className="p-1.5 hover:bg-rose-600/20 text-slate-500 hover:text-rose-400 rounded-lg transition-all"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Recent Reports Section */}
        {reports.length > 0 && (
          <div className="mt-8">
            <h3 className="text-lg font-semibold text-slate-100 mb-4">
              最近分析报告
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {reports.slice(0, 6).map((report) => (
                <div
                  key={report.id}
                  onClick={() => handleViewReport(report.symbol)}
                  className="bg-white/[0.02] backdrop-blur-xl rounded-xl border border-white/[0.06] p-4 hover:bg-white/[0.04] transition-all cursor-pointer"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="font-mono font-semibold text-slate-100">
                        {report.symbol}
                      </div>
                      <div className="text-sm text-slate-500">{report.name}</div>
                    </div>
                    {report.quant_score && (
                      <div
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          report.quant_score >= 70
                            ? "bg-emerald-500/20 text-emerald-400"
                            : report.quant_score >= 50
                            ? "bg-amber-500/20 text-amber-400"
                            : "bg-rose-500/20 text-rose-400"
                        }`}
                      >
                        {report.quant_score}分
                      </div>
                    )}
                  </div>
                  <div className="text-xs text-slate-500">
                    {new Date(report.created_at).toLocaleString("zh-CN")}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Add Modal */}
      <AnimatePresence>
        {showAddModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50"
            onClick={() => setShowAddModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-slate-800 rounded-2xl border border-slate-700 p-6 w-full max-w-md mx-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">添加自选</h3>
                <button
                  onClick={() => setShowAddModal(false)}
                  className="p-1 hover:bg-slate-700 rounded-lg"
                >
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              {/* 手动输入 */}
              <div className="relative mb-4">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  type="text"
                  value={addSymbol}
                  onChange={(e) => setAddSymbol(e.target.value)}
                  placeholder="输入股票/ETF/基金代码"
                  className="w-full pl-10 pr-4 py-3 bg-slate-700/50 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  onKeyDown={(e) => e.key === "Enter" && handleAddSymbol()}
                />
              </div>

              <div className="flex gap-3 mb-4">
                <button
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 py-2.5 bg-slate-700 text-slate-300 rounded-xl hover:bg-slate-600"
                >
                  取消
                </button>
                <button
                  onClick={handleAddSymbol}
                  disabled={loading || !addSymbol.trim()}
                  className="flex-1 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-500 disabled:opacity-50"
                >
                  {loading ? "添加中..." : "添加"}
                </button>
              </div>

              {/* 分割线 */}
              <div className="relative my-4">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-600"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-slate-800 text-slate-500">或者</span>
                </div>
              </div>

              {/* 图片上传 */}
              <label className="block cursor-pointer">
                <div className={`border-2 border-dashed border-slate-600 rounded-xl p-6 text-center hover:border-indigo-500/50 hover:bg-indigo-500/5 transition-all ${ocrLoading ? 'pointer-events-none opacity-50' : ''}`}>
                  {ocrLoading ? (
                    <div className="flex flex-col items-center">
                      <Loader2 className="w-10 h-10 text-indigo-400 animate-spin mb-2" />
                      <p className="text-slate-400">AI 识别中...</p>
                    </div>
                  ) : (
                    <>
                      <Camera className="w-10 h-10 text-slate-500 mx-auto mb-2" />
                      <p className="text-slate-400 mb-1">上传截图自动识别</p>
                      <p className="text-slate-600 text-xs">支持多选，最多10张图片</p>
                    </>
                  )}
                </div>
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleImageUpload}
                  className="hidden"
                  disabled={ocrLoading}
                />
              </label>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* OCR Results Modal */}
      <AnimatePresence>
        {showOcrModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50"
            onClick={() => setShowOcrModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-slate-800 rounded-2xl border border-slate-700 p-6 w-full max-w-lg mx-4 max-h-[80vh] overflow-hidden flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">
                  识别结果 ({ocrResults.filter(r => r.selected).length}/{ocrResults.length})
                </h3>
                <button
                  onClick={() => setShowOcrModal(false)}
                  className="p-1 hover:bg-slate-700 rounded-lg"
                >
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              <p className="text-slate-500 text-sm mb-4">
                请选择要添加到自选的标的
              </p>

              <div className="flex-1 overflow-y-auto space-y-2 mb-4">
                {ocrResults.map((item, index) => (
                  <div
                    key={index}
                    onClick={() => toggleOcrResult(index)}
                    className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${
                      item.selected
                        ? "bg-indigo-600/20 border border-indigo-500/30"
                        : "bg-slate-700/30 border border-transparent hover:bg-slate-700/50"
                    }`}
                  >
                    <div className="text-slate-300">
                      {item.selected ? (
                        <CheckSquare className="w-5 h-5 text-indigo-400" />
                      ) : (
                        <Square className="w-5 h-5" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="font-mono font-semibold text-white">
                        {item.symbol}
                      </div>
                      {item.name && (
                        <div className="text-sm text-slate-500">{item.name}</div>
                      )}
                    </div>
                    {item.type && (
                      <span className="px-2 py-1 text-xs bg-slate-600 text-slate-300 rounded">
                        {item.type === "stock" ? "股票" : item.type === "etf" ? "ETF" : item.type === "fund" ? "基金" : item.type}
                      </span>
                    )}
                  </div>
                ))}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setShowOcrModal(false)}
                  className="flex-1 py-2.5 bg-slate-700 text-slate-300 rounded-xl hover:bg-slate-600"
                >
                  取消
                </button>
                <button
                  onClick={handleAddOcrResults}
                  disabled={loading || ocrResults.filter(r => r.selected).length === 0}
                  className="flex-1 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-500 disabled:opacity-50"
                >
                  {loading ? "添加中..." : `添加 (${ocrResults.filter(r => r.selected).length})`}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
