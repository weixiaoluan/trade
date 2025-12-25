"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
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
  Menu,
  MoreVertical,
  Settings,
  MessageSquare,
  ExternalLink,
  AlertTriangle,
} from "lucide-react";
import { UserHeader } from "@/components/ui/UserHeader";
import { AlertModal } from "@/components/ui/AlertModal";

import { API_BASE } from "@/lib/config";

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
  reminder_type: string;
  frequency: string;
  analysis_time: string;
  weekday?: number;
  day_of_month?: number;
  // AI 分析设置
  ai_analysis_frequency?: string;
  ai_analysis_time?: string;
  ai_analysis_weekday?: number;
  ai_analysis_day_of_month?: number;
  buy_price?: number;
  sell_price?: number;
  enabled: boolean;
  created_at: string;
  last_notified_type?: string;
  last_notified_at?: string;
  last_analysis_at?: string;
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

  const [showReminderModal, setShowReminderModal] = useState(false);
  const [reminderSymbol, setReminderSymbol] = useState<string>("");
  const [reminderName, setReminderName] = useState<string>("");
  const [reminders, setReminders] = useState<ReminderItem[]>([]);
  const [reminderType, setReminderType] = useState<string>("both");
  const [reminderFrequency, setReminderFrequency] = useState<string>("trading_day");
  const [analysisWeekday, setAnalysisWeekday] = useState<number>(1);
  const [analysisDayOfMonth, setAnalysisDayOfMonth] = useState<number>(1);
  const [showBatchReminderModal, setShowBatchReminderModal] = useState(false);

  // AI 自动分析设置
  const [aiAnalysisFrequency, setAiAnalysisFrequency] = useState<string>("trading_day");
  const [aiAnalysisTime, setAiAnalysisTime] = useState<string>("09:30");
  const [aiAnalysisWeekday, setAiAnalysisWeekday] = useState<number>(1);
  const [aiAnalysisDayOfMonth, setAiAnalysisDayOfMonth] = useState<number>(1);

  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  const [quotes, setQuotes] = useState<Record<string, QuoteData>>({});

  const [showAlert, setShowAlert] = useState(false);
  const [alertConfig, setAlertConfig] = useState({
    title: "",
    message: "",
    type: "warning" as "warning" | "info" | "success" | "error",
  });

  const [sortField, setSortField] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  
  // 移动端操作菜单
  const [activeActionMenu, setActiveActionMenu] = useState<string | null>(null);

  // 用户设置相关
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [userSettings, setUserSettings] = useState<{
    pushplus_token: string;
    pushplus_configured: boolean;
    pushplus_remaining: { remaining: number; total: number } | null;
  } | null>(null);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [pushplusToken, setPushplusToken] = useState("");
  const [testPushLoading, setTestPushLoading] = useState(false);

  // 错误弹窗控制 - 避免重复弹窗
  const [shownErrorTasks, setShownErrorTasks] = useState<Set<string>>(new Set());
  const [hasShownBatchError, setHasShownBatchError] = useState(false);

  const getToken = useCallback(() => localStorage.getItem("token"), []);

  const tasksRef = useRef(tasks);
  useEffect(() => {
    tasksRef.current = tasks;
  }, [tasks]);

  const showAlertModal = useCallback(
    (title: string, message: string, type: "warning" | "info" | "success" | "error" = "warning") => {
      setAlertConfig({ title, message, type });
      setShowAlert(true);
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
        localStorage.setItem("user", JSON.stringify(data.user));
        setUser(data.user);
        setAuthChecked(true);
      } catch (error) {
        router.push("/login");
      }
    };

    checkAuth();
  }, [router]);

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
        
        Object.entries(newTasks).forEach(([symbol, task]: [string, any]) => {
          const prevTask = tasksRef.current[symbol];
          // 只有从 running/pending 变成 failed 才弹窗
          if (task.status === "failed" && 
              prevTask && 
              (prevTask.status === "running" || prevTask.status === "pending") &&
              !shownErrorTasks.has(symbol)) {
            failedTasks.push(symbol);
            if (task.error) {
              failedErrors.push(`${symbol}: ${task.error}`);
            }
          }
        });
        
        // 如果有新失败的任务，弹窗提示（只弹一次）
        if (failedTasks.length > 0 && !hasShownBatchError) {
          setShownErrorTasks(prev => new Set([...Array.from(prev), ...failedTasks]));
          setHasShownBatchError(true);
          
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
      }
    } catch (error) {
      console.error("获取任务状态失败:", error);
    }
  }, [getToken, shownErrorTasks, hasShownBatchError, showAlertModal]);

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

  const fetchReminders = useCallback(async () => {
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
  }, [getToken]);

  // 获取用户设置
  const fetchUserSettings = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/user/settings`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (response.ok) {
        const data = await response.json();
        setUserSettings(data.settings);
        setPushplusToken(data.settings?.pushplus_token || "");
      }
    } catch (error) {
      console.error("获取用户设置失败:", error);
    }
  }, [getToken]);

  // 更新用户设置
  const handleSaveSettings = useCallback(async () => {
    setSettingsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/user/settings?pushplus_token=${encodeURIComponent(pushplusToken)}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      
      if (response.ok) {
        showAlertModal("保存成功", "PushPlus Token 已保存", "success");
        fetchUserSettings();
      } else {
        const data = await response.json();
        showAlertModal("保存失败", data.detail || "请检查 Token 是否正确", "error");
      }
    } catch (error) {
      showAlertModal("保存失败", "网络错误，请稍后重试", "error");
    } finally {
      setSettingsLoading(false);
    }
  }, [getToken, pushplusToken, showAlertModal, fetchUserSettings]);

  // 测试推送
  const handleTestPush = useCallback(async () => {
    if (!pushplusToken.trim()) {
      showAlertModal("请输入 Token", "请先输入 PushPlus Token 再测试", "warning");
      return;
    }
    
    setTestPushLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/user/test-push?token=${encodeURIComponent(pushplusToken)}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      
      const data = await response.json();
      if (response.ok) {
        showAlertModal("测试成功", "测试消息已发送，请查看微信", "success");
        fetchUserSettings(); // 刷新剩余次数
      } else {
        showAlertModal("测试失败", data.detail || "推送失败，请检查配置", "error");
      }
    } catch (error) {
      showAlertModal("测试失败", "网络错误，请稍后重试", "error");
    } finally {
      setTestPushLoading(false);
    }
  }, [getToken, pushplusToken, showAlertModal, fetchUserSettings]);

  const hasActiveTasks = useMemo(() => {
    return Object.values(tasks).some((t) => t.status === "running" || t.status === "pending");
  }, [tasks]);

  useEffect(() => {
    if (authChecked) {
      fetchWatchlist();
      fetchTasks();
      fetchReports();
      fetchReminders();
      fetchUserSettings();

      const intervalMs = hasActiveTasks ? 2000 : 15000;
      const interval = setInterval(() => {
        if (document.visibilityState !== "visible") return;
        fetchTasks();
        fetchReports();
      }, intervalMs);

      return () => clearInterval(interval);
    }
  }, [authChecked, fetchWatchlist, fetchTasks, fetchReports, fetchReminders, fetchUserSettings, hasActiveTasks]);

  useEffect(() => {
    if (authChecked && watchlist.length > 0) {
      fetchQuotes();
      
      const quoteInterval = setInterval(() => {
        fetchQuotes();
      }, 10000);

      return () => clearInterval(quoteInterval);
    }
  }, [authChecked, watchlist, fetchQuotes]);

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

  const sortedWatchlist = useMemo(() => {
    let sorted = [...watchlist];
    
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
        }
        
        return sortOrder === "asc" ? aVal - bVal : bVal - aVal;
      });
    }
    
    return sorted;
  }, [watchlist, sortField, sortOrder, quotes]);

  const reportsBySymbol = useMemo(() => {
    const map: Record<string, ReportSummary> = {};
    for (const r of reports) {
      map[r.symbol] = r;
    }
    return map;
  }, [reports]);

  const reminderCountBySymbol = useMemo(() => {
    const map: Record<string, number> = {};
    for (const r of reminders) {
      map[r.symbol] = (map[r.symbol] || 0) + 1;
    }
    return map;
  }, [reminders]);

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

  const handleAddSymbol = useCallback(async () => {
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
  }, [addCostPrice, addPosition, addSymbol, canUseFeatures, fetchWatchlist, getToken, showPendingAlert]);

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

  const updateOcrPosition = (index: number, field: 'position' | 'cost_price', value: string) => {
    setOcrResults(prev => prev.map((item, i) =>
      i === index ? { ...item, [field]: value ? parseFloat(value) : undefined } : item
    ));
  };

  const handleDeleteSingle = useCallback(async (symbol: string) => {
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
        setSelectedItems((prev) => {
          const next = new Set(prev);
          next.delete(symbol);
          return next;
        });
      }
    } catch (error) {
      console.error("删除失败:", error);
    }
  }, [canUseFeatures, fetchWatchlist, getToken, showPendingAlert]);

  const handleBatchDelete = useCallback(async () => {
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
  }, [canUseFeatures, fetchWatchlist, getToken, selectedItems, showPendingAlert]);

  const handleAnalyzeSingle = useCallback(async (symbol: string) => {
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }

    // 重置该标的的错误状态
    setShownErrorTasks(prev => {
      const next = new Set(prev);
      next.delete(symbol);
      return next;
    });
    setHasShownBatchError(false);

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
        body: JSON.stringify({ ticker: symbol }),
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
  }, [canUseFeatures, fetchTasks, getErrorMessageFromResponse, getToken, showAlertModal, showPendingAlert]);

  const handleBatchAnalyze = useCallback(async () => {
    if (selectedItems.size === 0) return;
    
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }
    
    // 重置错误状态
    setShownErrorTasks(new Set());
    setHasShownBatchError(false);
    
    const symbols = Array.from(selectedItems);
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
        body: JSON.stringify(Array.from(selectedItems)),
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
  }, [canUseFeatures, fetchTasks, getErrorMessageFromResponse, getToken, selectedItems, showAlertModal, showPendingAlert]);

  const handleViewReport = useCallback((symbol: string) => {
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }
    router.push(`/report/${encodeURIComponent(symbol)}`);
  }, [canUseFeatures, router, showPendingAlert]);

  const openReminderModal = useCallback((symbol: string, name?: string) => {
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }
    
    // 检查是否配置了 PushPlus Token
    if (!userSettings?.pushplus_configured) {
      showAlertModal(
        "请先配置推送",
        "您还未配置微信推送，请先在设置中绑定 PushPlus Token 才能使用提醒功能。",
        "warning"
      );
      setShowSettingsModal(true);
      return;
    }
    
    // 检查剩余推送次数
    if (userSettings?.pushplus_remaining && userSettings.pushplus_remaining.remaining >= 0 && userSettings.pushplus_remaining.remaining < 10) {
      showAlertModal(
        "推送额度不足",
        `您本月剩余推送次数仅 ${userSettings.pushplus_remaining.remaining} 次，请合理设置提醒频率。`,
        "warning"
      );
    }
    
    setReminderSymbol(symbol);
    setReminderName(name || symbol);
    setReminderType("both");
    setReminderFrequency("trading_day");
    setAnalysisWeekday(1);
    setAnalysisDayOfMonth(1);
    setAiAnalysisFrequency("trading_day");
    setAiAnalysisTime("09:30");
    setAiAnalysisWeekday(1);
    setAiAnalysisDayOfMonth(1);
    setShowReminderModal(true);
  }, [canUseFeatures, showPendingAlert, userSettings, showAlertModal]);

  const handleCreateReminder = async () => {
    if (!reminderSymbol) return;

    setLoading(true);
    try {
      const payload = {
        symbol: reminderSymbol,
        name: reminderName,
        reminder_type: reminderType,
        frequency: reminderFrequency,
        analysis_time: aiAnalysisTime,
        weekday: reminderFrequency === "weekly" ? analysisWeekday : undefined,
        day_of_month: reminderFrequency === "monthly" ? analysisDayOfMonth : undefined,
        // AI 自动分析设置
        ai_analysis_frequency: aiAnalysisFrequency,
        ai_analysis_time: aiAnalysisTime,
        ai_analysis_weekday: aiAnalysisFrequency === "weekly" ? aiAnalysisWeekday : undefined,
        ai_analysis_day_of_month: aiAnalysisFrequency === "monthly" ? aiAnalysisDayOfMonth : undefined,
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
        
        if (!data.has_report) {
          if (confirm(`${reminderSymbol} 尚无AI分析报告，无法获取买卖价格。是否立即分析？`)) {
            handleAnalyzeSingle(reminderSymbol);
          }
        }
      }
    } catch (error) {
      console.error("创建提醒失败:", error);
      showAlertModal("创建提醒失败", error instanceof Error ? error.message : "网络错误，请稍后重试", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteReminder = async (reminderId: string) => {
    if (!reminderId) return;
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

  const handleBatchCreateReminder = async () => {
    if (selectedItems.size === 0) return;

    setLoading(true);
    try {
      const params = new URLSearchParams({
        reminder_type: reminderType,
        frequency: reminderFrequency,
        analysis_time: aiAnalysisTime,
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
        
        if (data.symbols_without_report?.length > 0) {
          if (confirm(`以下证券尚无AI分析报告：${data.symbols_without_report.join(", ")}，是否批量分析？`)) {
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

  const getReminderCount = (symbol: string) => {
    return reminderCountBySymbol[symbol] || 0;
  };

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
      default: return "";
    }
  };

  if (!authChecked) {
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
              <h1 className="text-base sm:text-lg font-bold text-slate-100">AI 智能投研</h1>
              <p className="text-[10px] sm:text-xs text-slate-500 hidden sm:block">Dashboard</p>
            </div>
          </div>

          {user && (
            <div className="flex items-center gap-2">
              {/* 推送额度提醒 */}
              {userSettings?.pushplus_remaining && userSettings.pushplus_remaining.remaining >= 0 && userSettings.pushplus_remaining.remaining < 10 && (
                <div className="hidden sm:flex items-center gap-1 px-2 py-1 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                  <span className="text-xs text-amber-400">剩余{userSettings.pushplus_remaining.remaining}次</span>
                </div>
              )}
              {/* 设置按钮 */}
              <button
                onClick={() => setShowSettingsModal(true)}
                className="p-2 hover:bg-white/[0.05] rounded-lg transition-all relative"
                title="设置"
              >
                <Settings className="w-5 h-5 text-slate-400" />
                {!userSettings?.pushplus_configured && (
                  <span className="absolute top-1 right-1 w-2 h-2 bg-amber-500 rounded-full"></span>
                )}
              </button>
              <UserHeader user={user} onLogout={handleLogout} />
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-3 sm:px-4 py-4 sm:py-8">
        {/* 未审核用户提示 */}
        {user && user.status !== 'approved' && user.role !== 'admin' && (
          <div className="mb-4 sm:mb-6 p-3 sm:p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg sm:rounded-xl">
            <div className="flex items-center gap-2 sm:gap-3">
              <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-amber-500/20 flex items-center justify-center flex-shrink-0">
                <Bell className="w-4 h-4 sm:w-5 sm:h-5 text-amber-400" />
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
          <div className="flex items-center gap-2 sm:gap-3">
            <h2 className="text-lg sm:text-xl font-semibold text-slate-100">我的自选</h2>
            <span className="text-xs sm:text-sm text-slate-500">
              ({watchlist.length})
            </span>
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
          <div className="hidden md:flex items-center gap-3 px-4 lg:px-6 py-3 border-b border-white/[0.06] bg-white/[0.02]">
            <div className="w-8 flex-shrink-0">
              <button onClick={toggleSelectAll} className="text-slate-400 hover:text-slate-200">
                {selectedItems.size === watchlist.length && watchlist.length > 0 ? (
                  <CheckSquare className="w-5 h-5" />
                ) : (
                  <Square className="w-5 h-5" />
                )}
              </button>
            </div>
            <div className="w-32 flex-shrink-0 text-sm font-medium text-slate-400">代码 / 名称</div>
            <div className="w-16 flex-shrink-0 text-sm font-medium text-slate-400">类型</div>
            <div className="w-20 flex-shrink-0 text-sm font-medium text-slate-400 text-right">当前价</div>
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
            <div className="w-16 flex-shrink-0 text-sm font-medium text-slate-400 text-right">持仓</div>
            <div className="w-16 flex-shrink-0 text-sm font-medium text-slate-400 text-right">成本价</div>
            <div className="w-20 flex-shrink-0 text-sm font-medium text-slate-400">状态</div>
            <div className="flex-1 text-sm font-medium text-slate-400 text-right">操作</div>
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
                const isTaskTimeout = task?.status === "running" && task?.updated_at && 
                  (Date.now() - new Date(task.updated_at).getTime() > 10 * 60 * 1000);
                const isFailed = task?.status === "failed" || isTaskTimeout;
                const isRunning = task?.status === "running" && !isTaskTimeout;
                const isPending = task?.status === "pending";

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
                          <div className="flex items-center gap-4 mb-3">
                            <div>
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
                            <div>
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
                            {item.position && (
                              <div>
                                <div className="text-[10px] text-slate-500 mb-0.5">持仓</div>
                                <span className="font-mono text-sm text-slate-200">{item.position.toLocaleString()}</span>
                              </div>
                            )}
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
                                    : "bg-indigo-600/20 text-indigo-400 active:bg-indigo-600/30"
                                }`}
                              >
                                {isRunning ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <Play className="w-4 h-4" />
                                )}
                                {isRunning ? `${task?.progress}%` : isFailed ? "重新分析" : "分析"}
                              </button>
                              
                              {report && (
                                <div className="flex flex-col">
                                  <button
                                    onClick={() => handleViewReport(item.symbol)}
                                    className="flex items-center justify-center gap-1.5 px-4 py-2.5 bg-emerald-600/20 text-emerald-400 text-sm rounded-xl min-w-[90px] touch-target active:bg-emerald-600/30"
                                  >
                                    <FileText className="w-4 h-4" />
                                    报告
                                  </button>
                                  <span className="text-[10px] text-slate-500 text-center mt-1">
                                    {new Date(report.created_at).toLocaleString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}
                                  </span>
                                </div>
                              )}
                            </div>
                            
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => openReminderModal(item.symbol, item.name)}
                                className={`flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm rounded-xl min-w-[90px] touch-target ${
                                  getReminderCount(item.symbol) > 0
                                    ? "bg-amber-600/20 text-amber-400 active:bg-amber-600/30"
                                    : "bg-white/[0.05] text-slate-400 active:bg-white/[0.1]"
                                }`}
                              >
                                {getReminderCount(item.symbol) > 0 ? (
                                  <BellRing className="w-4 h-4" />
                                ) : (
                                  <Bell className="w-4 h-4" />
                                )}
                                提醒
                              </button>
                              
                              <button
                                onClick={() => handleDeleteSingle(item.symbol)}
                                className="flex items-center justify-center gap-1.5 px-4 py-2.5 bg-white/[0.05] text-slate-400 hover:text-rose-400 text-sm rounded-xl min-w-[90px] touch-target active:bg-rose-600/20"
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
                    <div className="hidden md:flex items-center gap-3">
                      <div className="w-8 flex-shrink-0">
                        <button onClick={() => toggleSelect(item.symbol)} className="text-slate-400 hover:text-slate-200">
                          {isSelected ? <CheckSquare className="w-5 h-5 text-indigo-400" /> : <Square className="w-5 h-5" />}
                        </button>
                      </div>

                      <div className="w-32 flex-shrink-0">
                        <div className="flex items-center gap-1">
                          <span className="font-mono text-sm font-semibold text-slate-100 truncate">{item.symbol}</span>
                          <button
                            onClick={() => handleToggleStar(item.symbol)}
                            className={`p-0.5 ${item.starred ? "text-amber-400" : "text-slate-600 hover:text-amber-400"}`}
                          >
                            <Star className={`w-3.5 h-3.5 ${item.starred ? "fill-current" : ""}`} />
                          </button>
                        </div>
                        {item.name && <div className="text-xs text-slate-500 truncate">{item.name}</div>}
                      </div>

                      <div className="w-16 flex-shrink-0">
                        {item.type && (
                          <span className="px-2 py-0.5 text-xs bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded">
                            {getTypeLabel(item.type)}
                          </span>
                        )}
                      </div>

                      <div className="w-20 flex-shrink-0 text-right">
                        <span 
                          className="font-mono text-sm font-semibold"
                          style={{ color: (quote?.change_percent || 0) > 0 ? "#f87171" : (quote?.change_percent || 0) < 0 ? "#34d399" : "#e2e8f0" }}
                        >
                          {quote?.current_price?.toFixed(3) || "-"}
                        </span>
                      </div>

                      <div className="w-20 flex-shrink-0 text-right">
                        <span 
                          className="font-mono text-sm font-semibold"
                          style={{ color: (quote?.change_percent || 0) > 0 ? "#f87171" : (quote?.change_percent || 0) < 0 ? "#34d399" : "#94a3b8" }}
                        >
                          {quote?.change_percent !== undefined ? `${quote.change_percent > 0 ? "+" : ""}${quote.change_percent.toFixed(2)}%` : "-"}
                        </span>
                      </div>

                      <div className="w-16 flex-shrink-0 text-right">
                        <span className="font-mono text-sm text-slate-200">{item.position?.toLocaleString() || "-"}</span>
                      </div>

                      <div className="w-16 flex-shrink-0 text-right">
                        <span className="font-mono text-sm text-slate-200">{item.cost_price ? `¥${item.cost_price.toFixed(2)}` : "-"}</span>
                      </div>

                      <div className="w-20 flex-shrink-0">
                        {isFailed ? (
                          <div className="flex items-center gap-1 text-rose-400">
                            <AlertCircle className="w-4 h-4" />
                            <span className="text-xs">失败</span>
                          </div>
                        ) : isRunning ? (
                          <div className="flex items-center gap-1 text-amber-400">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span className="text-xs">{task?.progress}%</span>
                          </div>
                        ) : isPending ? (
                          <div className="flex items-center gap-1 text-amber-400">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span className="text-xs">分析中</span>
                          </div>
                        ) : report ? (
                          <div className="flex items-center gap-1 text-emerald-400">
                            <Check className="w-4 h-4" />
                            <span className="text-xs">完成</span>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-500">未分析</span>
                        )}
                      </div>

                      <div className="flex-1 flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleAnalyzeSingle(item.symbol)}
                          disabled={isRunning || isPending}
                          className={`flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg transition-all disabled:opacity-50 ${
                            isFailed ? "bg-rose-600/20 text-rose-400" : "bg-indigo-600/20 text-indigo-400"
                          }`}
                        >
                          <Play className="w-3.5 h-3.5" />
                          {isFailed ? "重新分析" : "AI分析"}
                        </button>

                        {report && (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleViewReport(item.symbol)}
                              className="flex items-center gap-1 px-2.5 py-1.5 bg-emerald-600/20 text-emerald-400 text-xs rounded-lg"
                            >
                              <FileText className="w-3.5 h-3.5" />
                              报告
                            </button>
                            <span className="text-[10px] text-slate-500">
                              {new Date(report.created_at).toLocaleString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}
                            </span>
                          </div>
                        )}

                        <button
                          onClick={() => openReminderModal(item.symbol, item.name)}
                          className={`relative p-2 rounded-lg ${
                            getReminderCount(item.symbol) > 0 ? "bg-amber-600/20 text-amber-400" : "text-slate-500 hover:text-amber-400"
                          }`}
                        >
                          {getReminderCount(item.symbol) > 0 ? <BellRing className="w-4 h-4" /> : <Bell className="w-4 h-4" />}
                          {getReminderCount(item.symbol) > 0 && (
                            <span className="absolute -top-1 -right-1 w-4 h-4 bg-amber-500 text-white text-[10px] rounded-full flex items-center justify-center">
                              {getReminderCount(item.symbol)}
                            </span>
                          )}
                        </button>

                        <button
                          onClick={() => handleDeleteSingle(item.symbol)}
                          className="p-2 hover:bg-rose-600/20 text-slate-500 hover:text-rose-400 rounded-lg"
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
                <span className="text-xs sm:text-sm text-slate-500">{currentPage}/{Math.ceil(watchlist.length / pageSize)}</span>
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

        {/* 最近报告 */}
        {reports.length > 0 && (
          <div className="mt-6 sm:mt-8">
            <h3 className="text-base sm:text-lg font-semibold text-slate-100 mb-3 sm:mb-4">最近分析报告</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
              {reports.slice(0, 6).map((report) => (
                <div
                  key={report.id}
                  onClick={() => handleViewReport(report.symbol)}
                  className="bg-white/[0.02] backdrop-blur-xl rounded-lg sm:rounded-xl border border-white/[0.06] p-3 sm:p-4 hover:bg-white/[0.04] transition-all cursor-pointer"
                >
                  <div className="flex items-start justify-between mb-2 sm:mb-3">
                    <div className="min-w-0">
                      <div className="font-mono font-semibold text-slate-100 text-sm sm:text-base">{report.symbol}</div>
                      <div className="text-xs sm:text-sm text-slate-500 truncate">{report.name}</div>
                    </div>
                    {report.quant_score && (
                      <div className={`px-2 py-1 rounded text-[10px] sm:text-xs font-medium flex-shrink-0 ${
                        report.quant_score >= 70 ? "bg-emerald-500/20 text-emerald-400" :
                        report.quant_score >= 50 ? "bg-amber-500/20 text-amber-400" : "bg-rose-500/20 text-rose-400"
                      }`}>
                        {report.quant_score}分
                      </div>
                    )}
                  </div>
                  <div className="text-[10px] sm:text-xs text-slate-500">
                    {new Date(report.created_at).toLocaleString("zh-CN")}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
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

              <div className="flex gap-3 mb-4">
                <button
                  onClick={() => { setShowAddModal(false); setAddSymbol(""); setAddPosition(""); setAddCostPrice(""); }}
                  className="flex-1 py-2.5 sm:py-3 bg-white/[0.05] border border-white/[0.08] text-slate-300 rounded-xl hover:bg-white/[0.08] text-sm sm:text-base"
                >
                  取消
                </button>
                <button
                  onClick={handleAddSymbol}
                  disabled={loading || !addSymbol.trim()}
                  className="flex-1 py-2.5 sm:py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-500 disabled:opacity-50 text-sm sm:text-base"
                >
                  {loading ? "添加中..." : "添加"}
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

      {/* 提醒设置弹窗 */}
      <AnimatePresence>
        {showReminderModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center z-50"
            onClick={() => setShowReminderModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              className="glass-card rounded-t-2xl sm:rounded-2xl border border-white/[0.08] p-4 sm:p-6 w-full sm:max-w-md sm:mx-4 max-h-[85vh] overflow-y-auto safe-area-bottom"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base sm:text-lg font-semibold text-white">提醒设置 - {reminderSymbol}</h3>
                <button onClick={() => setShowReminderModal(false)} className="p-1 hover:bg-white/[0.05] rounded-lg">
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              {/* 已有提醒列表 */}
              {reminders.filter(r => r.symbol === reminderSymbol).length > 0 && (
                <div className="mb-4 p-3 bg-white/[0.02] border border-white/[0.06] rounded-xl">
                  <div className="flex items-center gap-2 mb-3">
                    <BellRing className="w-4 h-4 text-amber-400" />
                    <span className="text-sm font-medium text-slate-300">已设置的提醒</span>
                  </div>
                  <div className="space-y-2">
                    {reminders.filter(r => r.symbol === reminderSymbol).map((reminder) => (
                      <div key={reminder.id} className="flex items-center justify-between p-2 bg-white/[0.03] rounded-lg">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 text-xs">
                            <span className={`px-1.5 py-0.5 rounded ${
                              reminder.reminder_type === 'buy' ? 'bg-emerald-500/20 text-emerald-400' :
                              reminder.reminder_type === 'sell' ? 'bg-rose-500/20 text-rose-400' :
                              'bg-indigo-500/20 text-indigo-400'
                            }`}>
                              {reminder.reminder_type === 'buy' ? '买入' : reminder.reminder_type === 'sell' ? '卖出' : '买+卖'}
                            </span>
                            <span className="text-slate-400">
                              {reminder.ai_analysis_frequency === 'trading_day' ? '每交易日' :
                               reminder.ai_analysis_frequency === 'weekly' ? `每周${['一','二','三','四','五','六','日'][((reminder.ai_analysis_weekday || 1) - 1)]}` :
                               `每月${reminder.ai_analysis_day_of_month || 1}号`}
                            </span>
                            <span className="text-slate-500">{reminder.ai_analysis_time || '09:30'}</span>
                          </div>
                          {(reminder.buy_price || reminder.sell_price) && (
                            <div className="text-[10px] text-slate-500 mt-1">
                              {reminder.buy_price && <span className="mr-2">买入价: ¥{reminder.buy_price}</span>}
                              {reminder.sell_price && <span>卖出价: ¥{reminder.sell_price}</span>}
                            </div>
                          )}
                        </div>
                        <button
                          onClick={() => handleDeleteReminder(reminder.id)}
                          className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-all"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-4">
                {/* AI 自动分析设置 */}
                <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
                  <div className="flex items-center gap-2 mb-3">
                    <Bot className="w-4 h-4 text-indigo-400" />
                    <span className="text-sm font-medium text-indigo-400">AI 自动分析</span>
                  </div>
                  
                  <div className="space-y-3">
                    <div>
                      <label className="text-xs text-slate-400 mb-1.5 block">分析频率</label>
                      <select
                        value={aiAnalysisFrequency}
                        onChange={(e) => setAiAnalysisFrequency(e.target.value)}
                        className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white focus:outline-none text-sm"
                      >
                        <option value="trading_day" className="bg-slate-800">每个交易日</option>
                        <option value="weekly" className="bg-slate-800">每周</option>
                        <option value="monthly" className="bg-slate-800">每月</option>
                      </select>
                    </div>

                    {aiAnalysisFrequency === "weekly" && (
                      <div>
                        <label className="text-xs text-slate-400 mb-1.5 block">选择周几</label>
                        <div className="grid grid-cols-7 gap-1">
                          {["一", "二", "三", "四", "五", "六", "日"].map((day, idx) => (
                            <button
                              key={idx}
                              onClick={() => setAiAnalysisWeekday(idx + 1)}
                              className={`py-1.5 rounded text-xs font-medium ${aiAnalysisWeekday === idx + 1 ? "bg-indigo-600 text-white" : "bg-white/[0.05] text-slate-300"}`}
                            >
                              {day}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {aiAnalysisFrequency === "monthly" && (
                      <div>
                        <label className="text-xs text-slate-400 mb-1.5 block">选择日期</label>
                        <select
                          value={aiAnalysisDayOfMonth}
                          onChange={(e) => setAiAnalysisDayOfMonth(Number(e.target.value))}
                          className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white focus:outline-none text-sm"
                        >
                          {Array.from({ length: 31 }, (_, i) => i + 1).map((day) => (
                            <option key={day} value={day} className="bg-slate-800">
                              {day} 号
                            </option>
                          ))}
                        </select>
                      </div>
                    )}

                    <div>
                      <label className="text-xs text-slate-400 mb-1.5 block">分析时间</label>
                      <input
                        type="time"
                        value={aiAnalysisTime}
                        onChange={(e) => setAiAnalysisTime(e.target.value)}
                        onClick={openNativeTimePicker}
                        className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white focus:outline-none text-sm"
                      />
                    </div>
                  </div>
                </div>
                <div>
                  <label className="text-xs sm:text-sm text-slate-400 mb-2 block">提醒类型</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[{v: "buy", l: "买入"}, {v: "sell", l: "卖出"}, {v: "both", l: "买+卖"}].map(({v, l}) => (
                      <button
                        key={v}
                        onClick={() => setReminderType(v)}
                        className={`py-2.5 rounded-xl text-sm font-medium transition-all ${reminderType === v ? "bg-indigo-600 text-white" : "bg-white/[0.05] text-slate-300 active:bg-white/[0.1]"}`}
                      >
                        {l}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-xs sm:text-sm text-slate-400 mb-2 block">提醒频率</label>
                  <select
                    value={reminderFrequency}
                    onChange={(e) => setReminderFrequency(e.target.value)}
                    className="w-full px-3 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white focus:outline-none text-sm"
                  >
                    <option value="trading_day" className="bg-slate-800">每个交易日</option>
                    <option value="weekly" className="bg-slate-800">每周</option>
                    <option value="monthly" className="bg-slate-800">每月</option>
                  </select>
                </div>

                {reminderFrequency === "weekly" && (
                  <div>
                    <label className="text-xs sm:text-sm text-slate-400 mb-2 block">选择周几</label>
                    <div className="grid grid-cols-7 gap-1">
                      {["一", "二", "三", "四", "五", "六", "日"].map((day, idx) => (
                        <button
                          key={idx}
                          onClick={() => setAnalysisWeekday(idx + 1)}
                          className={`py-2 rounded-lg text-xs font-medium transition-all ${analysisWeekday === idx + 1 ? "bg-indigo-600 text-white" : "bg-white/[0.05] text-slate-300"}`}
                        >
                          {day}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {reminderFrequency === "monthly" && (
                  <div>
                    <label className="text-xs sm:text-sm text-slate-400 mb-2 block">选择日期</label>
                    <select
                      value={analysisDayOfMonth}
                      onChange={(e) => setAnalysisDayOfMonth(Number(e.target.value))}
                      className="w-full px-3 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white focus:outline-none text-sm"
                    >
                      {Array.from({ length: 31 }, (_, i) => i + 1).map((day) => (
                        <option key={day} value={day} className="bg-slate-800">
                          {day} 号
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowReminderModal(false)}
                  className="flex-1 py-2.5 sm:py-3 bg-white/[0.05] border border-white/[0.08] text-slate-300 rounded-xl text-sm sm:text-base"
                >
                  取消
                </button>
                <button
                  onClick={handleCreateReminder}
                  disabled={loading}
                  className="flex-1 py-2.5 sm:py-3 bg-indigo-600 text-white rounded-xl disabled:opacity-50 text-sm sm:text-base"
                >
                  {loading ? "创建中..." : "创建提醒"}
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

              {/* PushPlus 说明 */}
              <div className="mb-4 p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
                <div className="flex items-start gap-2">
                  <MessageSquare className="w-5 h-5 text-indigo-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-medium text-indigo-400 mb-1">微信推送服务</h4>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      本系统使用 PushPlus 实现微信推送。免费版每月 200 次推送额度，足够日常使用。
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
                    <span>访问 PushPlus 官网注册账号</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-5 h-5 bg-indigo-600 text-white rounded-full flex items-center justify-center flex-shrink-0 text-[10px]">2</span>
                    <span>微信扫码关注公众号并绑定</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-5 h-5 bg-indigo-600 text-white rounded-full flex items-center justify-center flex-shrink-0 text-[10px]">3</span>
                    <span>在个人中心复制 Token 填入下方</span>
                  </li>
                </ol>
                <a
                  href="https://www.pushplus.plus"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 flex items-center justify-center gap-1.5 py-2 bg-indigo-600/20 text-indigo-400 rounded-lg text-sm hover:bg-indigo-600/30 transition-all"
                >
                  <ExternalLink className="w-4 h-4" />
                  前往 PushPlus 官网
                </a>
              </div>

              {/* Token 输入 */}
              <div className="mb-4">
                <label className="text-xs sm:text-sm text-slate-400 mb-2 block">PushPlus Token</label>
                <input
                  type="text"
                  value={pushplusToken}
                  onChange={(e) => setPushplusToken(e.target.value)}
                  placeholder="请输入您的 PushPlus Token"
                  className="w-full px-3 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-sm font-mono"
                />
              </div>

              {/* 状态显示 */}
              {userSettings?.pushplus_configured && (
                <div className="mb-4 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Check className="w-4 h-4 text-emerald-400" />
                      <span className="text-sm text-emerald-400">已配置</span>
                    </div>
                    {userSettings.pushplus_remaining && userSettings.pushplus_remaining.remaining >= 0 && (
                      <div className="text-xs text-slate-400">
                        本月剩余: <span className={userSettings.pushplus_remaining.remaining < 10 ? "text-amber-400 font-medium" : "text-emerald-400"}>
                          {userSettings.pushplus_remaining.remaining}
                        </span> / {userSettings.pushplus_remaining.total} 次
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 低额度警告 */}
              {userSettings?.pushplus_remaining && userSettings.pushplus_remaining.remaining >= 0 && userSettings.pushplus_remaining.remaining < 10 && (
                <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-medium text-amber-400">推送额度不足</h4>
                      <p className="text-xs text-amber-400/70 mt-0.5">
                        本月剩余推送次数较少，建议减少提醒频率或等待下月额度刷新。
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* 操作按钮 */}
              <div className="flex gap-3">
                <button
                  onClick={handleTestPush}
                  disabled={testPushLoading || !pushplusToken.trim()}
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
                  disabled={settingsLoading || !pushplusToken.trim()}
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

      {/* Alert Modal */}
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
