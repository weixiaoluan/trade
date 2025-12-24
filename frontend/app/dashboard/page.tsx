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
  Bell,
  BellRing,
  Star,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import { UserHeader } from "@/components/ui/UserHeader";
import { AlertModal } from "@/components/ui/AlertModal";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

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
  position?: number;  // 持仓数量
  cost_price?: number;  // 持仓成本价
  starred?: number;  // 特别关注 0/1
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

interface ReminderItem {
  id: string;
  symbol: string;
  name?: string;
  reminder_type: string;  // buy, sell, both
  frequency: string;  // trading_day, weekly, monthly
  analysis_time: string;  // HH:MM
  weekday?: number;  // 1-7 (周一-周日)
  day_of_month?: number;  // 1-31
  buy_price?: number;
  sell_price?: number;
  enabled: boolean;
  created_at: string;
  last_notified_type?: string;
  last_notified_at?: string;
  last_analysis_at?: string;
}

// 实时行情数据
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
  const [ocrResults, setOcrResults] = useState<Array<{ symbol: string; name: string; type: string; selected: boolean; position?: number; cost_price?: number }>>([]);

  // 添加自选时的持仓信息
  const [addPosition, setAddPosition] = useState<string>("");
  const [addCostPrice, setAddCostPrice] = useState<string>("");

  // 价格触发提醒相关状态
  const [showReminderModal, setShowReminderModal] = useState(false);
  const [reminderSymbol, setReminderSymbol] = useState<string>("");
  const [reminderName, setReminderName] = useState<string>("");
  const [reminders, setReminders] = useState<ReminderItem[]>([]);
  const [reminderType, setReminderType] = useState<string>("both");
  const [reminderFrequency, setReminderFrequency] = useState<string>("trading_day");
  const [analysisTime, setAnalysisTime] = useState<string>("09:30");
  const [analysisWeekday, setAnalysisWeekday] = useState<number>(1); // 1=周一
  const [analysisDayOfMonth, setAnalysisDayOfMonth] = useState<number>(1); // 1-31
  const [showBatchReminderModal, setShowBatchReminderModal] = useState(false);

  // 分页相关状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  // 实时行情数据
  const [quotes, setQuotes] = useState<Record<string, QuoteData>>({});

  // 自定义弹窗状态
  const [showAlert, setShowAlert] = useState(false);
  const [alertConfig, setAlertConfig] = useState({
    title: "",
    message: "",
    type: "warning" as "warning" | "info" | "success" | "error",
  });

  // 排序状态
  const [sortField, setSortField] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

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
        // 更新 localStorage 中的用户信息（包含最新的 role 和 status）
        localStorage.setItem("user", JSON.stringify(data.user));
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

  // 获取实时行情
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
  }, [watchlist]);

  // 初始化数据
  useEffect(() => {
    if (authChecked) {
      fetchWatchlist();
      fetchTasks();
      fetchReports();
      fetchReminders();

      // 定时刷新任务状态
      const interval = setInterval(() => {
        fetchTasks();
        fetchReports();
      }, 5000);

      return () => clearInterval(interval);
    }
  }, [authChecked, fetchWatchlist, fetchTasks, fetchReports]);

  // 获取实时行情（独立刷新，每10秒一次）
  useEffect(() => {
    if (authChecked && watchlist.length > 0) {
      // 立即获取一次
      fetchQuotes();
      
      // 每10秒刷新一次
      const quoteInterval = setInterval(() => {
        fetchQuotes();
      }, 10000);

      return () => clearInterval(quoteInterval);
    }
  }, [authChecked, watchlist, fetchQuotes]);

  // 退出登录
  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
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

  // 检查用户是否有权限
  const canUseFeatures = () => {
    return user && (user.status === 'approved' || user.role === 'admin');
  };

  // 显示待审核提示
  const showPendingAlert = () => {
    setAlertConfig({
      title: "账户待审核",
      message: "您的账户正在等待管理员审核，审核通过后即可使用所有功能。",
      type: "warning",
    });
    setShowAlert(true);
  };

  // 检查权限并执行操作
  const checkPermissionAndRun = (callback: () => void) => {
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }
    callback();
  };

  // 切换排序
  const handleSort = (field: string) => {
    if (sortField === field) {
      // 切换排序顺序
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  // 获取排序后的列表
  const getSortedWatchlist = () => {
    let sorted = [...watchlist];
    
    // 先按特别关注排序（starred 的在前面）
    sorted.sort((a, b) => (b.starred || 0) - (a.starred || 0));
    
    // 如果有指定排序字段，再按该字段排序
    if (sortField && quotes) {
      sorted.sort((a, b) => {
        // 保持 starred 优先
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
        }
        
        return sortOrder === "asc" ? aVal - bVal : bVal - aVal;
      });
    }
    
    return sorted;
  };

  // 切换特别关注
  const handleToggleStar = async (symbol: string) => {
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
  };

  // 添加自选
  const handleAddSymbol = async () => {
    if (!addSymbol.trim()) return;
    
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }

    setLoading(true);
    try {
      const payload: any = { symbol: addSymbol.trim().toUpperCase() };
      if (addPosition && parseFloat(addPosition) > 0) {
        payload.position = parseFloat(addPosition);
      }
      if (addCostPrice && parseFloat(addCostPrice) > 0) {
        payload.cost_price = parseFloat(addCostPrice);
      }

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
        setAddSymbol("");
        setAddPosition("");
        setAddCostPrice("");
        setShowAddModal(false);
        fetchWatchlist();
      } else {
        alert(data.message || "添加失败");
      }
    } catch (error) {
      console.error("添加失败:", error);
      alert("添加失败，请检查网络连接");
    } finally {
      setLoading(false);
    }
  };

  // 图片上传 OCR 识别（支持多张图片，最多10张）
  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    if (!canUseFeatures()) {
      showPendingAlert();
      e.target.value = "";
      return;
    }

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

  // 更新 OCR 结果的持仓信息
  const updateOcrPosition = (index: number, field: 'position' | 'cost_price', value: string) => {
    setOcrResults(prev => prev.map((item, i) =>
      i === index ? { ...item, [field]: value ? parseFloat(value) : undefined } : item
    ));
  };

  // 删除单个自选
  const handleDeleteSingle = async (symbol: string) => {
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }
    
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
    
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }

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
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }
    
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
    
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }

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
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }
    router.push(`/report/${encodeURIComponent(symbol)}`);
  };

  // ============================================
  // 定时提醒相关函数
  // ============================================

  // 获取提醒列表
  const fetchReminders = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/reminders`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (response.ok) {
        const data = await response.json();
        setReminders(data.reminders || []);
      }
    } catch (error) {
      console.error("获取提醒失败:", error);
    }
  };

  // 打开单个提醒设置
  const openReminderModal = (symbol: string, name?: string) => {
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }
    
    setReminderSymbol(symbol);
    setReminderName(name || symbol);
    setReminderType("both");
    setReminderFrequency("trading_day");
    setAnalysisTime("09:30");
    setAnalysisWeekday(1);
    setAnalysisDayOfMonth(1);
    setShowReminderModal(true);
  };

  // 创建价格触发提醒
  const handleCreateReminder = async () => {
    if (!reminderSymbol) return;

    setLoading(true);
    try {
      const payload = {
        symbol: reminderSymbol,
        name: reminderName,
        reminder_type: reminderType,
        frequency: reminderFrequency,
        analysis_time: analysisTime,
        weekday: reminderFrequency === "weekly" ? analysisWeekday : undefined,
        day_of_month: reminderFrequency === "monthly" ? analysisDayOfMonth : undefined,
      };

      const response = await fetch(`${API_BASE}/api/reminders`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const data = await response.json();
        setShowReminderModal(false);
        fetchReminders();
        
        // 如果没有报告，提示用户先分析
        if (!data.has_report) {
          if (confirm(`${reminderSymbol} 尚无AI分析报告，无法获取买卖价格。是否立即分析？`)) {
            handleAnalyzeSingle(reminderSymbol);
          }
        }
      }
    } catch (error) {
      console.error("创建提醒失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 删除提醒
  const handleDeleteReminder = async (reminderId: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/reminders/${reminderId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${getToken()}` },
      });

      if (response.ok) {
        fetchReminders();
      }
    } catch (error) {
      console.error("删除提醒失败:", error);
    }
  };

  // 批量创建价格触发提醒
  const handleBatchCreateReminder = async () => {
    if (selectedItems.size === 0) return;

    setLoading(true);
    try {
      const params = new URLSearchParams({
        reminder_type: reminderType,
        frequency: reminderFrequency,
        analysis_time: analysisTime,
      });
      if (reminderFrequency === "weekly") {
        params.set("weekday", analysisWeekday.toString());
      }
      if (reminderFrequency === "monthly") {
        params.set("day_of_month", analysisDayOfMonth.toString());
      }

      const response = await fetch(`${API_BASE}/api/reminders/batch?${params}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(Array.from(selectedItems)),
      });

      if (response.ok) {
        const data = await response.json();
        setShowBatchReminderModal(false);
        fetchReminders();
        
        // 提示没有报告的证券
        if (data.symbols_without_report?.length > 0) {
          if (confirm(`以下证券尚无AI分析报告，无法设置价格提醒：${data.symbols_without_report.join(", ")}，是否批量分析？`)) {
            for (const symbol of data.symbols_without_report) {
              handleAnalyzeSingle(symbol);
            }
          }
        }
      }
    } catch (error) {
      console.error("批量创建提醒失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 获取某个证券的提醒数量
  const getReminderCount = (symbol: string) => {
    return reminders.filter(r => r.symbol === symbol).length;
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
          <div className="animate-spin rounded-full h-24 w-24 border-b-4 border-indigo-500 mx-auto mb-4"></div>
          <p className="text-slate-400 text-lg">加载中...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#020617] relative">
      {/* Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 -left-1/4 w-[800px] h-[800px] bg-indigo-500/5 rounded-full blur-[150px]" />
        <div className="absolute bottom-0 -right-1/4 w-[600px] h-[600px] bg-violet-500/5 rounded-full blur-[120px]" />
      </div>

      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-[#020617]/80 backdrop-blur-xl">
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
        {/* 未审核用户提示 */}
        {user && user.status !== 'approved' && user.role !== 'admin' && (
          <div className="mb-6 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
                <Bell className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <h3 className="text-sm font-medium text-amber-400">账户待审核</h3>
                <p className="text-xs text-amber-400/70 mt-0.5">
                  您的账户正在等待管理员审核，审核通过后即可使用所有功能。
                </p>
              </div>
            </div>
          </div>
        )}

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
                <button
                  onClick={() => {
                    if (!canUseFeatures()) {
                      showPendingAlert();
                      return;
                    }
                    setShowBatchReminderModal(true);
                  }}
                  disabled={loading}
                  className="flex items-center gap-2 px-4 py-2 bg-amber-600/20 hover:bg-amber-600/30 text-amber-400 rounded-lg transition-all disabled:opacity-50"
                >
                  <Bell className="w-4 h-4" />
                  批量提醒
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
        <div className="glass-card rounded-2xl border border-white/[0.06] overflow-hidden">
          {/* Table Header */}
          <div className="flex items-center gap-4 px-6 py-4 border-b border-white/[0.06] bg-white/[0.02]">
            <div className="w-8 flex-shrink-0">
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
            <div className="w-32 flex-shrink-0 text-sm font-medium text-slate-400">
              代码 / 名称
            </div>
            <div className="w-16 flex-shrink-0 text-sm font-medium text-slate-400">
              类型
            </div>
            <div className="w-20 flex-shrink-0 text-sm font-medium text-slate-400 text-right">
              当前价
            </div>
            <div 
              className="w-20 flex-shrink-0 text-sm font-medium text-slate-400 text-right flex items-center justify-end gap-1 cursor-pointer hover:text-slate-300"
              onClick={() => handleSort("change_percent")}
            >
              涨跌幅
              {sortField === "change_percent" ? (
                sortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
              ) : (
                <ArrowUpDown className="w-3 h-3 opacity-50" />
              )}
            </div>
            <div 
              className="w-20 flex-shrink-0 text-sm font-medium text-slate-400 text-right flex items-center justify-end gap-1 cursor-pointer hover:text-slate-300"
              onClick={() => handleSort("position")}
            >
              持仓
              {sortField === "position" ? (
                sortOrder === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
              ) : (
                <ArrowUpDown className="w-3 h-3 opacity-50" />
              )}
            </div>
            <div className="w-20 flex-shrink-0 text-sm font-medium text-slate-400 text-right">
              成本价
            </div>
            <div className="w-8 flex-shrink-0"></div>
            <div className="w-24 flex-shrink-0 text-sm font-medium text-slate-400">
              分析状态
            </div>
            <div className="flex-1 text-sm font-medium text-slate-400 text-right">
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
              {getSortedWatchlist()
                .slice((currentPage - 1) * pageSize, currentPage * pageSize)
                .map((item) => {
                const task = getTaskStatus(item.symbol);
                const report = getReport(item.symbol);
                const isSelected = selectedItems.has(item.symbol);

                return (
                  <div
                    key={item.symbol}
                    className={`flex items-center gap-4 px-6 py-4 hover:bg-white/[0.02] transition-all ${
                      isSelected ? "bg-indigo-500/5" : ""
                    }`}
                  >
                    {/* Checkbox */}
                    <div className="w-8 flex-shrink-0 flex items-center">
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
                    <div className="w-32 flex-shrink-0">
                      <div className="flex items-center gap-1">
                        <span className="font-mono font-semibold text-slate-100 truncate">
                          {item.symbol}
                        </span>
                        <button
                          onClick={() => handleToggleStar(item.symbol)}
                          className={`p-0.5 transition-all ${
                            item.starred ? "text-amber-400" : "text-slate-600 hover:text-amber-400"
                          }`}
                          title={item.starred ? "取消关注" : "特别关注"}
                        >
                          <Star className={`w-3.5 h-3.5 ${item.starred ? "fill-current" : ""}`} />
                        </button>
                      </div>
                      {item.name && (
                        <div className="text-sm text-slate-500 truncate">{item.name}</div>
                      )}
                    </div>

                    {/* Type */}
                    <div className="w-16 flex-shrink-0 flex items-center">
                      {item.type && (
                        <span className="px-2 py-0.5 text-xs bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded">
                          {getTypeLabel(item.type)}
                        </span>
                      )}
                    </div>

                    {/* 当前价 */}
                    <div className="w-20 flex-shrink-0 flex items-center justify-end">
                      {quotes[item.symbol]?.current_price ? (
                        <span className={`font-mono text-sm font-medium ${
                          (quotes[item.symbol]?.change_percent || 0) > 0 
                            ? "text-rose-400" 
                            : (quotes[item.symbol]?.change_percent || 0) < 0 
                              ? "text-emerald-400" 
                              : "text-slate-200"
                        }`}>
                          {quotes[item.symbol].current_price.toFixed(3)}
                        </span>
                      ) : (
                        <span className="text-slate-600 text-sm">-</span>
                      )}
                    </div>

                    {/* 涨跌幅 */}
                    <div className="w-20 flex-shrink-0 flex items-center justify-end">
                      {quotes[item.symbol]?.change_percent !== undefined ? (
                        <span className={`font-mono text-sm font-medium ${
                          quotes[item.symbol].change_percent > 0 
                            ? "text-rose-400" 
                            : quotes[item.symbol].change_percent < 0 
                              ? "text-emerald-400" 
                              : "text-slate-400"
                        }`}>
                          {quotes[item.symbol].change_percent > 0 ? "+" : ""}
                          {quotes[item.symbol].change_percent.toFixed(2)}%
                        </span>
                      ) : (
                        <span className="text-slate-600 text-sm">-</span>
                      )}
                    </div>

                    {/* Position - 持仓 */}
                    <div className="w-20 flex-shrink-0 flex items-center justify-end">
                      {item.position ? (
                        <span className="font-mono text-sm text-slate-200">
                          {item.position.toLocaleString()}
                        </span>
                      ) : (
                        <span className="text-slate-600 text-sm">-</span>
                      )}
                    </div>

                    {/* Cost Price - 成本价 */}
                    <div className="w-20 flex-shrink-0 flex items-center justify-end">
                      {item.cost_price ? (
                        <span className="font-mono text-sm text-slate-200">
                          ¥{item.cost_price.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-slate-600 text-sm">-</span>
                      )}
                    </div>

                    {/* Spacer */}
                    <div className="w-8 flex-shrink-0"></div>

                    {/* Status */}
                    <div className="w-24 flex-shrink-0 flex items-center">
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
                    <div className="flex-1 flex items-center justify-end gap-2">
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
                        <div className="flex flex-col items-end">
                          <button
                            onClick={() => handleViewReport(item.symbol)}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 text-sm rounded-lg transition-all"
                          >
                            <FileText className="w-3.5 h-3.5" />
                            查看报告
                          </button>
                          <span className="text-xs text-slate-500 mt-1">
                            {new Date(report.created_at).toLocaleString("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                          </span>
                        </div>
                      )}

                      <button
                        onClick={() => openReminderModal(item.symbol, item.name)}
                        className={`relative p-1.5 rounded-lg transition-all ${
                          getReminderCount(item.symbol) > 0
                            ? "bg-amber-600/20 text-amber-400"
                            : "hover:bg-amber-600/20 text-slate-500 hover:text-amber-400"
                        }`}
                        title="设置提醒"
                      >
                        {getReminderCount(item.symbol) > 0 ? (
                          <BellRing className="w-4 h-4" />
                        ) : (
                          <Bell className="w-4 h-4" />
                        )}
                        {getReminderCount(item.symbol) > 0 && (
                          <span className="absolute -top-1 -right-1 w-4 h-4 bg-amber-500 text-white text-xs rounded-full flex items-center justify-center">
                            {getReminderCount(item.symbol)}
                          </span>
                        )}
                      </button>

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

          {/* 分页控件 */}
          {watchlist.length > 0 && (
            <div className="flex items-center justify-between px-6 py-4 border-t border-white/[0.06] bg-white/[0.02]">
              <div className="flex items-center gap-4">
                <span className="text-sm text-slate-500">
                  共 {watchlist.length} 条，当前第 {currentPage} 页 / 共 {Math.ceil(watchlist.length / pageSize)} 页
                </span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="px-2 py-1 bg-white/[0.05] border border-white/[0.1] rounded text-sm text-slate-300 focus:outline-none"
                >
                  <option value={50} className="bg-slate-800">50 条/页</option>
                  <option value={100} className="bg-slate-800">100 条/页</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1 bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  上一页
                </button>
                <button
                  onClick={() => setCurrentPage(p => Math.min(Math.ceil(watchlist.length / pageSize), p + 1))}
                  disabled={currentPage >= Math.ceil(watchlist.length / pageSize)}
                  className="px-3 py-1 bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  下一页
                </button>
              </div>
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
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50"
            onClick={() => setShowAddModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="glass-card rounded-2xl border border-white/[0.08] p-6 w-full max-w-md mx-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">添加自选</h3>
                <button
                  onClick={() => setShowAddModal(false)}
                  className="p-1 hover:bg-white/[0.05] rounded-lg transition-all"
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
                  className="w-full pl-10 pr-4 py-3 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  onKeyDown={(e) => e.key === "Enter" && handleAddSymbol()}
                />
              </div>

              {/* 持仓信息（可选） */}
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div>
                  <label className="text-xs text-slate-500 mb-1 block">持仓数量（可选）</label>
                  <input
                    type="number"
                    value={addPosition}
                    onChange={(e) => setAddPosition(e.target.value)}
                    placeholder="如：1000"
                    className="w-full px-3 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 mb-1 block">成本价（可选）</label>
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

              <div className="flex gap-3 mb-4">
                <button
                  onClick={() => {
                    setShowAddModal(false);
                    setAddSymbol("");
                    setAddPosition("");
                    setAddCostPrice("");
                  }}
                  className="flex-1 py-2.5 bg-white/[0.05] border border-white/[0.08] text-slate-300 rounded-xl hover:bg-white/[0.08] transition-all"
                >
                  取消
                </button>
                <button
                  onClick={handleAddSymbol}
                  disabled={loading || !addSymbol.trim()}
                  className="flex-1 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-500 disabled:opacity-50 transition-all"
                >
                  {loading ? "添加中..." : "添加"}
                </button>
              </div>

              {/* 分割线 */}
              <div className="relative my-4">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/[0.06]"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-3 bg-[#0f172a] text-slate-500">或者</span>
                </div>
              </div>

              {/* 图片上传 */}
              <label className="block cursor-pointer">
                <div className={`border-2 border-dashed border-white/[0.1] rounded-xl p-6 text-center hover:border-indigo-500/40 hover:bg-indigo-500/5 transition-all ${ocrLoading ? 'pointer-events-none opacity-50' : ''}`}>
                  {ocrLoading ? (
                    <div className="flex flex-col items-center">
                      <Loader2 className="w-10 h-10 text-indigo-400 animate-spin mb-2" />
                      <p className="text-slate-400">AI 识别中...</p>
                    </div>
                  ) : (
                    <>
                      <Camera className="w-10 h-10 text-indigo-400/60 mx-auto mb-2" />
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
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50"
            onClick={() => setShowOcrModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="glass-card rounded-2xl border border-white/[0.08] p-6 w-full max-w-lg mx-4 max-h-[80vh] overflow-hidden flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">
                  识别结果 ({ocrResults.filter(r => r.selected).length}/{ocrResults.length})
                </h3>
                <button
                  onClick={() => setShowOcrModal(false)}
                  className="p-1 hover:bg-white/[0.05] rounded-lg transition-all"
                >
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              <p className="text-slate-500 text-sm mb-4">
                请选择要添加到自选的标的，可输入持仓信息
              </p>

              <div className="flex-1 overflow-y-auto space-y-3 mb-4">
                {ocrResults.map((item, index) => (
                  <div
                    key={index}
                    className={`p-3 rounded-xl transition-all ${
                      item.selected
                        ? "bg-indigo-500/10 border border-indigo-500/20"
                        : "bg-white/[0.02] border border-white/[0.06] hover:bg-white/[0.04]"
                    }`}
                  >
                    <div 
                      className="flex items-center gap-3 cursor-pointer"
                      onClick={() => toggleOcrResult(index)}
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
                        <span className="px-2 py-1 text-xs bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded">
                          {item.type === "stock" ? "股票" : item.type === "etf" ? "ETF" : item.type === "fund" ? "基金" : item.type}
                        </span>
                      )}
                    </div>
                    {/* 持仓信息输入 */}
                    {item.selected && (
                      <div className="mt-3 pt-3 border-t border-white/[0.06] grid grid-cols-2 gap-2">
                        <input
                          type="number"
                          placeholder="持仓数量"
                          value={item.position || ""}
                          onClick={(e) => e.stopPropagation()}
                          onChange={(e) => updateOcrPosition(index, 'position', e.target.value)}
                          className="px-2.5 py-1.5 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 text-sm"
                        />
                        <input
                          type="number"
                          step="0.01"
                          placeholder="成本价"
                          value={item.cost_price || ""}
                          onClick={(e) => e.stopPropagation()}
                          onChange={(e) => updateOcrPosition(index, 'cost_price', e.target.value)}
                          className="px-2.5 py-1.5 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 text-sm"
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setShowOcrModal(false)}
                  className="flex-1 py-2.5 bg-white/[0.05] border border-white/[0.08] text-slate-300 rounded-xl hover:bg-white/[0.08] transition-all"
                >
                  取消
                </button>
                <button
                  onClick={handleAddOcrResults}
                  disabled={loading || ocrResults.filter(r => r.selected).length === 0}
                  className="flex-1 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-500 disabled:opacity-50 transition-all"
                >
                  {loading ? "添加中..." : `添加 (${ocrResults.filter(r => r.selected).length})`}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Reminder Modal - 单个提醒设置 */}
      <AnimatePresence>
        {showReminderModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50"
            onClick={() => setShowReminderModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="glass-card rounded-2xl border border-white/[0.08] p-6 w-full max-w-md mx-4 max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                  <Bell className="w-5 h-5 text-amber-400" />
                  设置定时提醒
                </h3>
                <button
                  onClick={() => setShowReminderModal(false)}
                  className="p-1 hover:bg-white/[0.05] rounded-lg transition-all"
                >
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              <div className="mb-4 p-3 bg-white/[0.02] rounded-lg border border-white/[0.06]">
                <div className="font-mono font-semibold text-slate-100">{reminderSymbol}</div>
                {reminderName !== reminderSymbol && (
                  <div className="text-sm text-slate-500">{reminderName}</div>
                )}
              </div>

              {/* 已有提醒列表 */}
              {reminders.filter(r => r.symbol === reminderSymbol).length > 0 && (
                <div className="mb-4">
                  <div className="text-sm text-slate-400 mb-2">已设置的提醒：</div>
                  <div className="space-y-2">
                    {reminders.filter(r => r.symbol === reminderSymbol).map((r) => (
                      <div key={r.id} className="flex items-center justify-between p-2 bg-white/[0.02] rounded-lg">
                        <div className="text-sm">
                          <span className={r.reminder_type === "buy" ? "text-emerald-400" : r.reminder_type === "sell" ? "text-rose-400" : "text-amber-400"}>
                            {r.reminder_type === "buy" ? "买入提醒" : r.reminder_type === "sell" ? "卖出提醒" : "买卖提醒"}
                          </span>
                          <span className="text-slate-500 ml-2">
                            {r.frequency === "trading_day" ? "交易日" : 
                             r.frequency === "weekly" ? `每周${["一","二","三","四","五","六","日"][((r.weekday || 1) - 1)]}` : 
                             `每月${r.day_of_month || 1}号`} {r.analysis_time}
                            {r.buy_price && ` | 买:${r.buy_price}`}
                            {r.sell_price && ` | 卖:${r.sell_price}`}
                          </span>
                        </div>
                        <button
                          onClick={() => handleDeleteReminder(r.id)}
                          className="p-1 hover:bg-rose-600/20 text-slate-500 hover:text-rose-400 rounded transition-all"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 提醒说明 */}
              <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <p className="text-amber-400 text-sm">
                  📢 当实时价格触发 AI 分析的买入/卖出价时，将立即发送短信提醒
                </p>
              </div>

              {/* 提醒类型 */}
              <div className="mb-4">
                <label className="text-sm text-slate-400 mb-2 block">提醒类型</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { value: "buy", label: "买入提醒", color: "emerald" },
                    { value: "sell", label: "卖出提醒", color: "rose" },
                    { value: "both", label: "买入+卖出", color: "amber" },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setReminderType(opt.value)}
                      className={`py-2.5 px-3 rounded-lg text-sm transition-all ${
                        reminderType === opt.value
                          ? `bg-${opt.color}-600/20 border border-${opt.color}-500/30 text-${opt.color}-400`
                          : "bg-white/[0.02] border border-white/[0.06] text-slate-400 hover:bg-white/[0.04]"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* AI分析频率 */}
              <div className="mb-4">
                <label className="text-sm text-slate-400 mb-2 block">AI分析频率</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { value: "trading_day", label: "交易日" },
                    { value: "weekly", label: "每周" },
                    { value: "monthly", label: "每月" },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setReminderFrequency(opt.value)}
                      className={`py-2.5 px-3 rounded-lg text-sm transition-all ${
                        reminderFrequency === opt.value
                          ? "bg-indigo-600/20 border border-indigo-500/30 text-indigo-400"
                          : "bg-white/[0.02] border border-white/[0.06] text-slate-400 hover:bg-white/[0.04]"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 每周选择周几 */}
              {reminderFrequency === "weekly" && (
                <div className="mb-4">
                  <label className="text-sm text-slate-400 mb-2 block">选择周几</label>
                  <div className="grid grid-cols-7 gap-1">
                    {[
                      { value: 1, label: "一" },
                      { value: 2, label: "二" },
                      { value: 3, label: "三" },
                      { value: 4, label: "四" },
                      { value: 5, label: "五" },
                      { value: 6, label: "六" },
                      { value: 7, label: "日" },
                    ].map((day) => (
                      <button
                        key={day.value}
                        onClick={() => setAnalysisWeekday(day.value)}
                        className={`py-2 rounded-lg text-sm transition-all ${
                          analysisWeekday === day.value
                            ? "bg-indigo-600/30 border border-indigo-500/50 text-indigo-300"
                            : "bg-white/[0.02] border border-white/[0.06] text-slate-400 hover:bg-white/[0.04]"
                        }`}
                      >
                        {day.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* 每月选择几号 */}
              {reminderFrequency === "monthly" && (
                <div className="mb-4">
                  <label className="text-sm text-slate-400 mb-2 block">选择几号</label>
                  <select
                    value={analysisDayOfMonth}
                    onChange={(e) => setAnalysisDayOfMonth(Number(e.target.value))}
                    className="w-full px-4 py-2.5 bg-[#0a0f1a] border border-white/[0.06] rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  >
                    {Array.from({ length: 31 }, (_, i) => i + 1).map((day) => (
                      <option key={day} value={day}>{day}号</option>
                    ))}
                  </select>
                </div>
              )}

              {/* 分析时间 */}
              <div className="mb-6">
                <label className="text-sm text-slate-400 mb-2 block">分析时间</label>
                <div className="flex gap-2">
                  <select
                    value={analysisTime.split(":")[0]}
                    onChange={(e) => setAnalysisTime(`${e.target.value}:${analysisTime.split(":")[1]}`)}
                    className="flex-1 px-4 py-2.5 bg-[#0a0f1a] border border-white/[0.06] rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  >
                    {Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, "0")).map((hour) => (
                      <option key={hour} value={hour}>{hour}时</option>
                    ))}
                  </select>
                  <span className="flex items-center text-slate-400">:</span>
                  <select
                    value={analysisTime.split(":")[1]}
                    onChange={(e) => setAnalysisTime(`${analysisTime.split(":")[0]}:${e.target.value}`)}
                    className="flex-1 px-4 py-2.5 bg-[#0a0f1a] border border-white/[0.06] rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  >
                    {Array.from({ length: 60 }, (_, i) => i.toString().padStart(2, "0")).map((min) => (
                      <option key={min} value={min}>{min}分</option>
                    ))}
                  </select>
                </div>
                <p className="text-xs text-slate-500 mt-1">AI将在此时间自动分析并更新买卖价格</p>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setShowReminderModal(false)}
                  className="flex-1 py-2.5 bg-white/[0.05] border border-white/[0.08] text-slate-300 rounded-xl hover:bg-white/[0.08] transition-all"
                >
                  取消
                </button>
                <button
                  onClick={handleCreateReminder}
                  disabled={loading}
                  className="flex-1 py-2.5 bg-amber-600 text-white rounded-xl hover:bg-amber-500 disabled:opacity-50 transition-all"
                >
                  {loading ? "创建中..." : "创建提醒"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Batch Reminder Modal - 批量提醒设置 */}
      <AnimatePresence>
        {showBatchReminderModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50"
            onClick={() => setShowBatchReminderModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="glass-card rounded-2xl border border-white/[0.08] p-6 w-full max-w-md mx-4 max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                  <Bell className="w-5 h-5 text-amber-400" />
                  批量设置提醒
                </h3>
                <button
                  onClick={() => setShowBatchReminderModal(false)}
                  className="p-1 hover:bg-white/[0.05] rounded-lg transition-all"
                >
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              <div className="mb-4 p-3 bg-white/[0.02] rounded-lg border border-white/[0.06]">
                <div className="text-sm text-slate-400">已选择 {selectedItems.size} 个标的</div>
                <div className="text-xs text-slate-500 mt-1 truncate">
                  {Array.from(selectedItems).slice(0, 5).join(", ")}
                  {selectedItems.size > 5 && ` 等`}
                </div>
              </div>

              {/* 提醒说明 */}
              <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <p className="text-amber-400 text-sm">
                  📢 当实时价格触发 AI 分析的买入/卖出价时，将立即发送短信提醒
                </p>
              </div>

              {/* 提醒类型 */}
              <div className="mb-4">
                <label className="text-sm text-slate-400 mb-2 block">提醒类型</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { value: "buy", label: "买入提醒", color: "emerald" },
                    { value: "sell", label: "卖出提醒", color: "rose" },
                    { value: "both", label: "买入+卖出", color: "amber" },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setReminderType(opt.value)}
                      className={`py-2.5 px-3 rounded-lg text-sm transition-all ${
                        reminderType === opt.value
                          ? `bg-${opt.color}-600/20 border border-${opt.color}-500/30 text-${opt.color}-400`
                          : "bg-white/[0.02] border border-white/[0.06] text-slate-400 hover:bg-white/[0.04]"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* AI分析频率 */}
              <div className="mb-4">
                <label className="text-sm text-slate-400 mb-2 block">AI分析频率</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { value: "trading_day", label: "交易日" },
                    { value: "weekly", label: "每周" },
                    { value: "monthly", label: "每月" },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setReminderFrequency(opt.value)}
                      className={`py-2.5 px-3 rounded-lg text-sm transition-all ${
                        reminderFrequency === opt.value
                          ? "bg-indigo-600/20 border border-indigo-500/30 text-indigo-400"
                          : "bg-white/[0.02] border border-white/[0.06] text-slate-400 hover:bg-white/[0.04]"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 每周选择周几 */}
              {reminderFrequency === "weekly" && (
                <div className="mb-4">
                  <label className="text-sm text-slate-400 mb-2 block">选择周几</label>
                  <div className="grid grid-cols-7 gap-1">
                    {[
                      { value: 1, label: "一" },
                      { value: 2, label: "二" },
                      { value: 3, label: "三" },
                      { value: 4, label: "四" },
                      { value: 5, label: "五" },
                      { value: 6, label: "六" },
                      { value: 7, label: "日" },
                    ].map((day) => (
                      <button
                        key={day.value}
                        onClick={() => setAnalysisWeekday(day.value)}
                        className={`py-2 rounded-lg text-sm transition-all ${
                          analysisWeekday === day.value
                            ? "bg-indigo-600/30 border border-indigo-500/50 text-indigo-300"
                            : "bg-white/[0.02] border border-white/[0.06] text-slate-400 hover:bg-white/[0.04]"
                        }`}
                      >
                        {day.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* 每月选择几号 */}
              {reminderFrequency === "monthly" && (
                <div className="mb-4">
                  <label className="text-sm text-slate-400 mb-2 block">选择几号</label>
                  <select
                    value={analysisDayOfMonth}
                    onChange={(e) => setAnalysisDayOfMonth(Number(e.target.value))}
                    className="w-full px-4 py-2.5 bg-[#0a0f1a] border border-white/[0.06] rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  >
                    {Array.from({ length: 31 }, (_, i) => i + 1).map((day) => (
                      <option key={day} value={day}>{day}号</option>
                    ))}
                  </select>
                </div>
              )}

              {/* 分析时间 */}
              <div className="mb-6">
                <label className="text-sm text-slate-400 mb-2 block">分析时间</label>
                <div className="flex gap-2">
                  <select
                    value={analysisTime.split(":")[0]}
                    onChange={(e) => setAnalysisTime(`${e.target.value}:${analysisTime.split(":")[1]}`)}
                    className="flex-1 px-4 py-2.5 bg-[#0a0f1a] border border-white/[0.06] rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  >
                    {Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, "0")).map((hour) => (
                      <option key={hour} value={hour}>{hour}时</option>
                    ))}
                  </select>
                  <span className="flex items-center text-slate-400">:</span>
                  <select
                    value={analysisTime.split(":")[1]}
                    onChange={(e) => setAnalysisTime(`${analysisTime.split(":")[0]}:${e.target.value}`)}
                    className="flex-1 px-4 py-2.5 bg-[#0a0f1a] border border-white/[0.06] rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  >
                    {Array.from({ length: 60 }, (_, i) => i.toString().padStart(2, "0")).map((min) => (
                      <option key={min} value={min}>{min}分</option>
                    ))}
                  </select>
                </div>
                <p className="text-xs text-slate-500 mt-1">AI将在此时间自动分析并更新买卖价格</p>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setShowBatchReminderModal(false)}
                  className="flex-1 py-2.5 bg-white/[0.05] border border-white/[0.08] text-slate-300 rounded-xl hover:bg-white/[0.08] transition-all"
                >
                  取消
                </button>
                <button
                  onClick={handleBatchCreateReminder}
                  disabled={loading}
                  className="flex-1 py-2.5 bg-amber-600 text-white rounded-xl hover:bg-amber-500 disabled:opacity-50 transition-all"
                >
                  {loading ? "创建中..." : `批量创建 (${selectedItems.size})`}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 自定义弹窗 */}
      <AlertModal
        isOpen={showAlert}
        onClose={() => setShowAlert(false)}
        title={alertConfig.title}
        message={alertConfig.message}
        type={alertConfig.type}
      />
    </main>
  );
}
