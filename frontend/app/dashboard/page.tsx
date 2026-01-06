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
  Edit3,
  Sparkles,
  Share2,
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
  const [user, setUser] = useState<UserInfo | null>(() => {
    // 从 localStorage 初始化用户信息，避免等待API
    if (typeof window !== 'undefined') {
      const storedUser = localStorage.getItem("user");
      if (storedUser) {
        try {
          return JSON.parse(storedUser);
        } catch {
          return null;
        }
      }
    }
    return null;
  });
  const [authChecked, setAuthChecked] = useState(() => {
    // 如果有缓存的用户信息，直接标记为已检查
    if (typeof window !== 'undefined') {
      return !!(localStorage.getItem("token") && localStorage.getItem("user"));
    }
    return false;
  });
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

  // 提醒记录
  const [showReminderLogsModal, setShowReminderLogsModal] = useState(false);
  const [reminderLogsSymbol, setReminderLogsSymbol] = useState<string>("");
  const [reminderLogsName, setReminderLogsName] = useState<string>("");
  const [reminderLogs, setReminderLogs] = useState<any[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  // AI 自动分析设置
  const [aiAnalysisFrequency, setAiAnalysisFrequency] = useState<string>("trading_day");
  const [aiAnalysisTime, setAiAnalysisTime] = useState<string>("09:30");
  const [aiAnalysisWeekday, setAiAnalysisWeekday] = useState<number>(1);
  const [aiAnalysisDayOfMonth, setAiAnalysisDayOfMonth] = useState<number>(1);
  const [reminderHoldingPeriod, setReminderHoldingPeriod] = useState<string>("short");

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
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  
  // 搜索状态
  const [searchQuery, setSearchQuery] = useState("");
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
  const [pendingAnalysisSymbols, setPendingAnalysisSymbols] = useState<string[]>([]);
  const [isBatchAnalysis, setIsBatchAnalysis] = useState(false);

  // 编辑持仓弹窗状态
  const [showEditPositionModal, setShowEditPositionModal] = useState(false);
  const [editingItem, setEditingItem] = useState<WatchlistItem | null>(null);
  const [editPosition, setEditPosition] = useState<string>("");
  const [editCostPrice, setEditCostPrice] = useState<string>("");
  const [editHoldingPeriod, setEditHoldingPeriod] = useState<string>("swing");

  // AI 优选相关状态
  const [showAiPicksModal, setShowAiPicksModal] = useState(false);
  const [aiPicks, setAiPicks] = useState<Array<{ symbol: string; name: string; type: string; added_by: string; added_at: string }>>([]);
  const [aiPicksLoading, setAiPicksLoading] = useState(false);
  const [selectedAiPicks, setSelectedAiPicks] = useState<Set<string>>(new Set());
  const [addAsAiPick, setAddAsAiPick] = useState(false);  // 添加自选时是否同时添加为AI优选

  // 计算用户还没有添加到自选的 AI 优选标的
  const availableAiPicks = useMemo(() => {
    const watchlistSymbols = new Set(watchlist.map(item => item.symbol.toUpperCase()));
    return aiPicks.filter(pick => !watchlistSymbols.has(pick.symbol.toUpperCase()));
  }, [aiPicks, watchlist]);

  // 新增的 AI 优选数量（用于角标显示）
  const newAiPicksCount = availableAiPicks.length;

  const getToken = useCallback(() => localStorage.getItem("token"), []);

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

      // 已经从 localStorage 初始化了用户信息，页面可以立即显示
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

  // 一次性获取所有dashboard数据
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
        setReminders(data.reminders || []);
        setUserSettings(data.settings);
        setWechatOpenId(data.settings?.wechat_openid || "");
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

  // 获取 AI 优选列表
  const fetchAiPicks = useCallback(async () => {
    setAiPicksLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/ai-picks`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (response.ok) {
        const data = await response.json();
        setAiPicks(data.picks || []);
      }
    } catch (error) {
      console.error("获取 AI 优选失败:", error);
    } finally {
      setAiPicksLoading(false);
    }
  }, [getToken]);

  // 打开 AI 优选弹窗 - 定义在后面（需要 canUseFeatures）
  const handleOpenAiPicksRef = useRef<() => void>(() => {});

  // 切换 AI 优选选中状态
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

  // 全选/取消全选 AI 优选（只针对可用的，即用户还没添加到自选的）
  const toggleSelectAllAiPicks = useCallback(() => {
    setSelectedAiPicks(prev => {
      if (prev.size === availableAiPicks.length) {
        return new Set();
      }
      return new Set(availableAiPicks.map(p => p.symbol));
    });
  }, [availableAiPicks]);

  // 添加选中的 AI 优选到自选
  const handleAddAiPicksToWatchlist = useCallback(async () => {
    if (selectedAiPicks.size === 0) {
      showAlertModal("请选择标的", "请至少选择一个标的添加到自选", "warning");
      return;
    }

    const items = availableAiPicks
      .filter(p => selectedAiPicks.has(p.symbol))
      .map(p => ({ symbol: p.symbol, name: p.name, type: p.type }));

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
        fetchAiPicks();  // 刷新 AI 优选列表
        
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

  // 添加标的为 AI 优选（管理员）
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
        showAlertModal("添加成功", `${symbol} 已添加到 AI 优选`, "success");
      } else {
        const data = await response.json();
        showAlertModal("添加失败", data.detail || "添加失败", "error");
      }
    } catch (error) {
      showAlertModal("添加失败", "网络错误，请稍后重试", "error");
    }
  }, [getToken, showAlertModal]);

  // 从 AI 优选移除（管理员 - 全局删除）
  const handleRemoveFromAiPicks = useCallback(async (symbol: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/ai-picks/${encodeURIComponent(symbol)}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${getToken()}` },
      });

      if (response.ok) {
        showAlertModal("移除成功", `${symbol} 已从 AI 优选移除（全局）`, "success");
        fetchAiPicks();
      } else {
        const data = await response.json();
        showAlertModal("移除失败", data.detail || "移除失败", "error");
      }
    } catch (error) {
      showAlertModal("移除失败", "网络错误，请稍后重试", "error");
    }
  }, [getToken, showAlertModal, fetchAiPicks]);

  // 用户从 AI 优选中移除单个标的（仅对自己隐藏）
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

  // 用户批量移除选中的 AI 优选
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

  // 用户清空所有 AI 优选
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
      // 初始加载 - 一次性获取所有数据
      fetchDashboardInit();
      // 获取 AI 优选列表（用于显示角标）
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
      fetchQuotes();
      
      // 行情数据15秒刷新一次（非交易时间可以更长）
      const quoteInterval = setInterval(() => {
        if (document.visibilityState !== "visible") return;
        fetchQuotes();
      }, 15000);

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

  // 打开 AI 优选弹窗
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
  }, [watchlist, sortField, sortOrder, quotes, searchQuery]);

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

  const handleAddSymbol = useCallback(async (closeAfterAdd: boolean = true) => {
    if (!addSymbol.trim()) return;
    
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }

    const symbolToAdd = addSymbol.trim().toUpperCase();
    const positionVal = addPosition && parseFloat(addPosition) > 0 ? parseFloat(addPosition) : undefined;
    const costPriceVal = addCostPrice && parseFloat(addCostPrice) > 0 ? parseFloat(addCostPrice) : undefined;

    // 保存当前的 AI 优选状态
    const shouldAddAsAiPick = addAsAiPick && user?.role === 'admin';

    // 检查是否已存在于自选列表
    const existsInWatchlist = watchlist.some(item => item.symbol === symbolToAdd);
    // 检查是否已存在于 AI 优选列表
    const existsInAiPicks = aiPicks.some(item => item.symbol === symbolToAdd);

    // 如果勾选了 AI 优选，需要检查两个列表
    if (shouldAddAsAiPick) {
      if (existsInWatchlist && existsInAiPicks) {
        showAlertModal("已存在", `${symbolToAdd} 已在自选列表和 AI 优选列表中，不能重复添加`, "warning");
        return;
      }
    } else {
      // 没勾选 AI 优选，只检查自选列表
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

    // 添加到 AI 优选列表（如果勾选了且不存在）
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
          // 刷新 AI 优选列表
          fetchAiPicks();
        }
      } catch (error) {
        // 静默失败
      }
    }

    // 显示结果提示
    if (shouldAddAsAiPick) {
      if (existsInWatchlist && aiPicksAdded) {
        showAlertModal("添加成功", `${symbolToAdd} 已存在于自选列表，已添加到 AI 优选列表`, "success");
      } else if (watchlistAdded && existsInAiPicks) {
        showAlertModal("添加成功", `${symbolToAdd} 已添加到自选列表，AI 优选列表已存在`, "success");
      } else if (watchlistAdded && aiPicksAdded) {
        showAlertModal("添加成功", `${symbolToAdd} 已添加到自选列表和 AI 优选列表`, "success");
      } else if (watchlistAdded) {
        showAlertModal("部分成功", `${symbolToAdd} 已添加到自选列表，AI 优选添加失败`, "warning");
      } else if (aiPicksAdded) {
        showAlertModal("部分成功", `${symbolToAdd} 自选添加失败，已添加到 AI 优选列表`, "warning");
      } else {
        showAlertModal("添加失败", "网络错误，请稍后重试", "error");
      }
    } else {
      // 没勾选 AI 优选，只提示自选结果
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

    // 弹窗选择持有周期
    setPendingAnalysisSymbols([symbol]);
    setIsBatchAnalysis(false);
    setHoldingPeriod("short");
    setShowHoldingPeriodModal(true);
  }, [canUseFeatures, showPendingAlert]);

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
    
    // 弹窗选择持有周期
    setPendingAnalysisSymbols(Array.from(selectedItems));
    setIsBatchAnalysis(true);
    setHoldingPeriod("short");
    setShowHoldingPeriodModal(true);
  }, [canUseFeatures, selectedItems, showPendingAlert]);

  // 批量提醒
  const handleBatchReminder = useCallback(() => {
    if (selectedItems.size === 0) return;
    
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }
    
    // 检查是否配置了微信推送
    if (!userSettings?.wechat_openid) {
      showAlertModal(
        "请先配置推送",
        "您还未配置微信推送，请先在设置中绑定微信 OpenID 才能使用提醒功能。",
        "warning"
      );
      setShowSettingsModal(true);
      return;
    }
    
    // 重置提醒设置为默认值
    setReminderType("both");
    setReminderFrequency("trading_day");
    setAnalysisWeekday(1);
    setAnalysisDayOfMonth(1);
    setAiAnalysisFrequency("trading_day");
    setAiAnalysisTime("09:30");
    setAiAnalysisWeekday(1);
    setAiAnalysisDayOfMonth(1);
    setReminderHoldingPeriod("short");
    setShowBatchReminderModal(true);
  }, [canUseFeatures, selectedItems, showPendingAlert, userSettings, showAlertModal]);

  // 批量创建提醒
  const handleCreateBatchReminder = useCallback(async () => {
    if (selectedItems.size === 0) return;

    setLoading(true);
    let successCount = 0;
    let failCount = 0;
    const failedSymbols: string[] = [];

    try {
      for (const symbol of Array.from(selectedItems)) {
        const item = watchlist.find(w => w.symbol === symbol);
        const payload = {
          symbol: symbol,
          name: item?.name || symbol,
          reminder_type: reminderType,
          frequency: reminderFrequency,
          analysis_time: aiAnalysisTime,
          weekday: reminderFrequency === "weekly" ? analysisWeekday : undefined,
          day_of_month: reminderFrequency === "monthly" ? analysisDayOfMonth : undefined,
          ai_analysis_frequency: aiAnalysisFrequency,
          ai_analysis_time: aiAnalysisTime,
          ai_analysis_weekday: aiAnalysisFrequency === "weekly" ? aiAnalysisWeekday : undefined,
          ai_analysis_day_of_month: aiAnalysisFrequency === "monthly" ? aiAnalysisDayOfMonth : undefined,
          holding_period: reminderHoldingPeriod,
        };

        try {
          const response = await fetch(`${API_BASE}/api/reminders`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${getToken()}`,
            },
            body: JSON.stringify(payload),
          });

          const data = await response.json();
          
          if (response.ok && data.status !== "error") {
            successCount++;
          } else {
            failCount++;
            failedSymbols.push(symbol);
          }
        } catch {
          failCount++;
          failedSymbols.push(symbol);
        }
      }

      setShowBatchReminderModal(false);
      fetchReminders();
      setSelectedItems(new Set());

      if (failCount === 0) {
        showAlertModal("批量提醒创建成功", `已为 ${successCount} 个标的创建提醒`, "success");
      } else if (successCount === 0) {
        showAlertModal("批量提醒创建失败", `所有 ${failCount} 个标的创建失败（可能已存在相同提醒）`, "error");
      } else {
        showAlertModal(
          "部分提醒创建成功",
          `成功: ${successCount} 个，失败: ${failCount} 个（${failedSymbols.join(", ")}）`,
          "warning"
        );
      }
    } catch (error) {
      showAlertModal("批量提醒创建失败", "网络错误，请稍后重试", "error");
    } finally {
      setLoading(false);
    }
  }, [selectedItems, watchlist, reminderType, reminderFrequency, aiAnalysisTime, analysisWeekday, analysisDayOfMonth, aiAnalysisFrequency, aiAnalysisWeekday, aiAnalysisDayOfMonth, reminderHoldingPeriod, getToken, fetchReminders, showAlertModal]);

  // 查看提醒记录
  const openReminderLogsModal = useCallback(async (symbol: string, name?: string) => {
    setReminderLogsSymbol(symbol);
    setReminderLogsName(name || symbol);
    setReminderLogs([]);
    setShowReminderLogsModal(true);
    setLoadingLogs(true);
    
    try {
      const response = await fetch(`${API_BASE}/api/reminder-logs/${symbol}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (response.ok) {
        const data = await response.json();
        setReminderLogs(data.logs || []);
      }
    } catch (error) {
      console.error("获取提醒记录失败:", error);
    } finally {
      setLoadingLogs(false);
    }
  }, [getToken]);

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
    router.push(`/report/${encodeURIComponent(symbol)}`);
  }, [canUseFeatures, router, showPendingAlert]);

  // 预加载报告页面
  const prefetchReport = useCallback((symbol: string) => {
    router.prefetch(`/report/${encodeURIComponent(symbol)}`);
  }, [router]);

  const openReminderModal = useCallback((symbol: string, name?: string) => {
    if (!canUseFeatures()) {
      showPendingAlert();
      return;
    }
    
    // 检查是否配置了微信公众号 OpenID
    if (!userSettings?.wechat_configured) {
      showAlertModal(
        "请先配置推送",
        "您还未配置微信推送，请先在设置中绑定微信 OpenID 才能使用提醒功能。",
        "warning"
      );
      setShowSettingsModal(true);
      return;
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
    setReminderHoldingPeriod("short");
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
        // 持有周期
        holding_period: reminderHoldingPeriod,
      };

      const response = await fetch(`${API_BASE}/api/reminders`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      
      if (data.status === "error") {
        showAlertModal("提醒已存在", data.message || "该提醒已存在，请勿重复设置", "warning");
        return;
      }
      
      if (response.ok) {
        setShowReminderModal(false);
        fetchReminders();
        
        if (!data.has_report) {
          const symbolToAnalyze = reminderSymbol;
          showAlertModal(
            "提醒已创建",
            `${symbolToAnalyze} 尚无AI分析报告，建议先进行分析以获取买卖价格建议。`,
            "info"
          );
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
          showAlertModal(
            "提醒已创建",
            `以下证券尚无AI分析报告，建议先进行分析：\n${data.symbols_without_report.join("、")}`,
            "info"
          );
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
              <h1 className="text-base sm:text-lg font-bold text-slate-100">AI 智能投研</h1>
              <p className="text-[10px] sm:text-xs text-slate-500 hidden sm:block">Dashboard</p>
            </div>
          </div>

          {user && (
            <div className="flex items-center gap-2">
              {/* AI 优选按钮 */}
              <button
                onClick={handleOpenAiPicks}
                className="relative flex items-center gap-1.5 px-2.5 py-1.5 bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/30 text-amber-400 rounded-lg text-xs sm:text-sm hover:from-amber-500/30 hover:to-orange-500/30 transition-all"
                title="AI 优选"
              >
                <Sparkles className="w-4 h-4" />
                <span className="hidden sm:inline">AI 优选</span>
                {/* 新增数量角标 */}
                {newAiPicksCount > 0 && (
                  <span className="absolute -top-3 -right-3 min-w-[24px] h-6 px-1.5 bg-red-500 text-white text-sm font-bold rounded-full flex items-center justify-center shadow-lg animate-pulse">
                    +{newAiPicksCount > 99 ? '99' : newAiPicksCount}
                  </span>
                )}
              </button>
              {/* 设置按钮 */}
              <button
                onClick={() => setShowSettingsModal(true)}
                className="p-2 hover:bg-white/[0.05] rounded-lg transition-all relative"
                title="设置"
              >
                <Settings className="w-5 h-5 text-slate-400" />
                {!userSettings?.wechat_configured && (
                  <span className="absolute top-1 right-1 w-2 h-2 bg-amber-500 rounded-full"></span>
                )}
              </button>
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
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
            <h2 className="text-lg sm:text-xl font-semibold text-slate-100">我的自选</h2>
            <span className="text-xs sm:text-sm text-slate-500">
              ({searchQuery ? `${sortedWatchlist.length}/${watchlist.length}` : watchlist.length})
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
                  onClick={handleBatchReminder}
                  disabled={loading}
                  className="flex items-center gap-1.5 px-3 py-2 bg-amber-600/20 hover:bg-amber-600/30 text-amber-400 rounded-lg transition-all disabled:opacity-50 text-xs sm:text-sm"
                >
                  <Bell className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">批量提醒</span>
                  <span className="sm:hidden">提醒</span>
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
              <div className="w-20 flex-shrink-0 text-sm font-semibold text-indigo-400">AI建议</div>
              <div className="w-28 flex-shrink-0 text-sm font-semibold text-emerald-400 text-right">买入价/量</div>
              <div className="w-28 flex-shrink-0 text-sm font-semibold text-rose-400 text-right">卖出价/量</div>
              <div className="w-20 flex-shrink-0 text-sm font-semibold text-slate-300">状态</div>
              <div className="w-20 flex-shrink-0 text-sm font-semibold text-slate-300">提醒记录</div>
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
                              <span className="font-mono text-sm text-slate-200">{item.cost_price ? `¥${item.cost_price.toFixed(3)}` : "-"}</span>
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
                              <span className={`px-1.5 py-0.5 text-[10px] rounded ${
                                item.holding_period === 'short' ? 'bg-amber-500/10 text-amber-400' :
                                item.holding_period === 'long' ? 'bg-violet-500/10 text-violet-400' :
                                'bg-indigo-500/10 text-indigo-400'
                              }`}>
                                {getHoldingPeriodLabel(item.holding_period)}
                              </span>
                            </div>
                          </div>
                          
                          {/* AI建议价格/数量 - 移动端（始终显示预留空间） */}
                          <div className="flex flex-wrap items-start gap-4 mb-3 pt-2 border-t border-white/[0.05]">
                            <div className="min-w-[70px]">
                              <div className="text-[10px] text-indigo-400/70 mb-0.5">AI建议</div>
                              {item.ai_recommendation ? (
                                <span className={`px-1.5 py-0.5 text-xs rounded ${
                                  item.ai_recommendation.includes('买入') ? 'bg-emerald-500/10 text-emerald-400' :
                                  item.ai_recommendation.includes('卖出') || item.ai_recommendation.includes('减持') ? 'bg-rose-500/10 text-rose-400' :
                                  'bg-slate-500/10 text-slate-400'
                                }`}>
                                  {item.ai_recommendation}
                                </span>
                              ) : (
                                <span className="text-xs text-slate-500">-</span>
                              )}
                            </div>
                            <div className="min-w-[90px]">
                              <div className="text-[10px] text-emerald-400/70 mb-0.5">建议买入价/量</div>
                              <div className="flex flex-col">
                                <span className="font-mono text-sm font-semibold text-emerald-400">
                                  {item.ai_buy_price ? `¥${item.ai_buy_price.toFixed(3)}` : "-"}
                                </span>
                                <span className="font-mono text-xs text-emerald-400/70">
                                  {item.ai_buy_quantity ? `${item.ai_buy_quantity.toLocaleString()}股` : "-"}
                                </span>
                              </div>
                            </div>
                            <div className="min-w-[90px]">
                              <div className="text-[10px] text-rose-400/70 mb-0.5">建议卖出价/量</div>
                              <div className="flex flex-col">
                                <span className="font-mono text-sm font-semibold text-rose-400">
                                  {item.ai_sell_price ? `¥${item.ai_sell_price.toFixed(3)}` : "-"}
                                </span>
                                <span className="font-mono text-xs text-rose-400/70">
                                  {item.ai_sell_quantity ? `${item.ai_sell_quantity.toLocaleString()}股` : "-"}
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
                        <span className="font-mono text-base text-slate-100">{item.cost_price ? `¥${item.cost_price.toFixed(3)}` : "-"}</span>
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

                      {/* 持有周期 */}
                      <div className="w-16 flex-shrink-0">
                        <span className={`px-2.5 py-1 text-sm rounded-md ${
                          item.holding_period === 'short' ? 'bg-amber-500/10 text-amber-400' :
                          item.holding_period === 'long' ? 'bg-violet-500/10 text-violet-400' :
                          'bg-indigo-500/10 text-indigo-400'
                        }`}>
                          {getHoldingPeriodLabel(item.holding_period)}
                        </span>
                      </div>

                      {/* AI建议 */}
                      <div className="w-20 flex-shrink-0">
                        {item.ai_recommendation ? (
                          <span className={`px-2.5 py-1 text-sm font-medium rounded-md whitespace-nowrap ${
                            item.ai_recommendation.includes('买入') ? 'bg-emerald-500/15 text-emerald-400' :
                            item.ai_recommendation.includes('卖出') || item.ai_recommendation.includes('减持') ? 'bg-rose-500/15 text-rose-400' :
                            'bg-slate-500/15 text-slate-300'
                          }`}>
                            {item.ai_recommendation}
                          </span>
                        ) : (
                          <span className="text-sm text-slate-500">-</span>
                        )}
                      </div>

                      {/* AI建议买入价/量 */}
                      <div className="w-28 flex-shrink-0 text-right">
                        <div className="flex flex-col">
                          <span className="font-mono text-base font-semibold text-emerald-400">
                            {item.ai_buy_price ? `¥${item.ai_buy_price.toFixed(3)}` : "-"}
                          </span>
                          <span className="font-mono text-sm text-emerald-400/70">
                            {item.ai_buy_quantity ? `${item.ai_buy_quantity.toLocaleString()}股` : "-"}
                          </span>
                        </div>
                      </div>

                      {/* AI建议卖出价/量 */}
                      <div className="w-28 flex-shrink-0 text-right">
                        <div className="flex flex-col">
                          <span className="font-mono text-base font-semibold text-rose-400">
                            {item.ai_sell_price ? `¥${item.ai_sell_price.toFixed(3)}` : "-"}
                          </span>
                          <span className="font-mono text-sm text-rose-400/70">
                            {item.ai_sell_quantity ? `${item.ai_sell_quantity.toLocaleString()}股` : "-"}
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

                      {/* 提醒记录 */}
                      <div className="w-20 flex-shrink-0">
                        <button
                          onClick={() => openReminderLogsModal(item.symbol, item.name)}
                          className="text-sm text-indigo-400 hover:text-indigo-300 hover:underline font-medium"
                        >
                          查看详情
                        </button>
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
                          onClick={() => openReminderModal(item.symbol, item.name)}
                          className={`relative p-2 rounded-lg ${
                            getReminderCount(item.symbol) > 0 ? "bg-amber-600/20 text-amber-400" : "text-slate-500 hover:text-amber-400 hover:bg-amber-600/10"
                          }`}
                          title="提醒"
                        >
                          {getReminderCount(item.symbol) > 0 ? <BellRing className="w-4 h-4" /> : <Bell className="w-4 h-4" />}
                          {getReminderCount(item.symbol) > 0 && (
                            <span className="absolute -top-1 -right-1 w-4 h-4 bg-amber-500 text-white text-[10px] rounded-full flex items-center justify-center">
                              {getReminderCount(item.symbol)}
                            </span>
                          )}
                        </button>

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

              {/* 管理员：AI 优选勾选框 */}
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
                        <span className="text-sm font-medium text-amber-400">同时添加为 AI 优选</span>
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
                      <select
                        value={aiAnalysisTime}
                        onChange={(e) => setAiAnalysisTime(e.target.value)}
                        className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white focus:outline-none text-sm"
                      >
                        {Array.from({ length: 24 }, (_, h) => 
                          ["00", "30"].map(m => {
                            const time = `${h.toString().padStart(2, "0")}:${m}`;
                            return <option key={time} value={time} className="bg-slate-800">{time}</option>;
                          })
                        ).flat()}
                      </select>
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
                            onClick={() => setReminderHoldingPeriod(v)}
                            className={`py-2 rounded-lg text-xs font-medium transition-all flex flex-col items-center ${
                              reminderHoldingPeriod === v 
                                ? "bg-indigo-600 text-white" 
                                : "bg-white/[0.05] text-slate-300 hover:bg-white/[0.08]"
                            }`}
                          >
                            <span>{l}</span>
                            <span className={`text-[10px] ${reminderHoldingPeriod === v ? "text-indigo-200" : "text-slate-500"}`}>{desc}</span>
                          </button>
                        ))}
                      </div>
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

      {/* 批量提醒设置弹窗 */}
      <AnimatePresence>
        {showBatchReminderModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center z-50"
            onClick={() => setShowBatchReminderModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              className="glass-card rounded-t-2xl sm:rounded-2xl border border-white/[0.08] p-4 sm:p-6 w-full sm:max-w-md sm:mx-4 max-h-[85vh] overflow-y-auto safe-area-bottom"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base sm:text-lg font-semibold text-white">提醒设置 - 批量提醒（{selectedItems.size}个）</h3>
                <button onClick={() => setShowBatchReminderModal(false)} className="p-1 hover:bg-white/[0.05] rounded-lg">
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              {/* 已选标的列表 */}
              <div className="mb-4 p-3 bg-white/[0.02] border border-white/[0.06] rounded-xl">
                <div className="flex items-center gap-2 mb-2">
                  <Bell className="w-4 h-4 text-amber-400" />
                  <span className="text-sm font-medium text-slate-300">已选标的</span>
                </div>
                <div className="flex flex-wrap gap-1.5 max-h-20 overflow-y-auto">
                  {Array.from(selectedItems).map((symbol) => {
                    const item = watchlist.find(w => w.symbol === symbol);
                    return (
                      <span key={symbol} className="px-2 py-0.5 bg-amber-500/10 text-amber-400 text-xs rounded">
                        {item?.name || symbol}
                      </span>
                    );
                  })}
                </div>
              </div>

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
                      <select
                        value={aiAnalysisTime}
                        onChange={(e) => setAiAnalysisTime(e.target.value)}
                        className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white focus:outline-none text-sm"
                      >
                        {Array.from({ length: 24 }, (_, h) => 
                          ["00", "30"].map(m => {
                            const time = `${h.toString().padStart(2, "0")}:${m}`;
                            return <option key={time} value={time} className="bg-slate-800">{time}</option>;
                          })
                        ).flat()}
                      </select>
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
                            onClick={() => setReminderHoldingPeriod(v)}
                            className={`py-2 rounded-lg text-xs font-medium transition-all flex flex-col items-center ${
                              reminderHoldingPeriod === v 
                                ? "bg-indigo-600 text-white" 
                                : "bg-white/[0.05] text-slate-300 hover:bg-white/[0.08]"
                            }`}
                          >
                            <span>{l}</span>
                            <span className={`text-[10px] ${reminderHoldingPeriod === v ? "text-indigo-200" : "text-slate-500"}`}>{desc}</span>
                          </button>
                        ))}
                      </div>
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
                  onClick={() => setShowBatchReminderModal(false)}
                  className="flex-1 py-2.5 sm:py-3 bg-white/[0.05] border border-white/[0.08] text-slate-300 rounded-xl text-sm sm:text-base"
                >
                  取消
                </button>
                <button
                  onClick={handleCreateBatchReminder}
                  disabled={loading}
                  className="flex-1 py-2.5 sm:py-3 bg-amber-600 text-white rounded-xl disabled:opacity-50 text-sm sm:text-base"
                >
                  {loading ? "创建中..." : `批量创建（${selectedItems.size}个）`}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 提醒记录弹窗 */}
      <AnimatePresence>
        {showReminderLogsModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center z-50"
            onClick={() => setShowReminderLogsModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              className="glass-card rounded-t-2xl sm:rounded-2xl border border-white/[0.08] p-4 sm:p-6 w-full sm:max-w-lg sm:mx-4 max-h-[85vh] overflow-y-auto safe-area-bottom"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base sm:text-lg font-semibold text-white">
                  提醒记录 - {reminderLogsName} ({reminderLogsSymbol})
                </h3>
                <button onClick={() => setShowReminderLogsModal(false)} className="p-1 hover:bg-white/[0.05] rounded-lg">
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              {loadingLogs ? (
                <div className="py-8 text-center">
                  <Loader2 className="w-8 h-8 text-indigo-400 animate-spin mx-auto mb-2" />
                  <span className="text-sm text-slate-400">加载中...</span>
                </div>
              ) : reminderLogs.length === 0 ? (
                <div className="py-8 text-center">
                  <Bell className="w-12 h-12 text-slate-600 mx-auto mb-2" />
                  <span className="text-sm text-slate-500">暂无提醒记录</span>
                </div>
              ) : (
                <div className="space-y-3 max-h-[60vh] overflow-y-auto">
                  {reminderLogs.map((log, index) => (
                    <div key={index} className="p-3 bg-white/[0.02] border border-white/[0.06] rounded-xl">
                      <div className="flex items-center justify-between mb-2">
                        <span className={`px-2 py-0.5 text-xs rounded ${
                          log.reminder_type === 'buy' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                        }`}>
                          {log.reminder_type === 'buy' ? '买入提醒' : '卖出提醒'}
                        </span>
                        <span className="text-xs text-slate-500">
                          {(() => {
                            const d = new Date(log.created_at);
                            return `${d.getFullYear()}/${String(d.getMonth()+1).padStart(2,'0')}/${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
                          })()}
                        </span>
                      </div>
                      <div className="text-sm text-slate-300 mb-2">{log.message}</div>
                      <div className="flex flex-wrap gap-3 text-xs">
                        {log.current_price && (
                          <span className="text-slate-400">当前价: <span className="text-white">¥{log.current_price.toFixed(3)}</span></span>
                        )}
                        {log.buy_price && (
                          <span className="text-emerald-400/70">买入价: ¥{log.buy_price.toFixed(3)}</span>
                        )}
                        {log.buy_quantity && (
                          <span className="text-emerald-400/70">买入量: {log.buy_quantity}股</span>
                        )}
                        {log.sell_price && (
                          <span className="text-rose-400/70">卖出价: ¥{log.sell_price.toFixed(3)}</span>
                        )}
                        {log.sell_quantity && (
                          <span className="text-rose-400/70">卖出量: {log.sell_quantity}股</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-4">
                <button
                  onClick={() => setShowReminderLogsModal(false)}
                  className="w-full py-2.5 bg-white/[0.05] border border-white/[0.08] text-slate-300 rounded-xl text-sm"
                >
                  关闭
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

      {/* AI 优选弹窗 */}
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
                  AI 优选
                </h3>
                <button onClick={() => setShowAiPicksModal(false)} className="p-1 hover:bg-white/[0.05] rounded-lg">
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              <p className="text-slate-500 text-xs sm:text-sm mb-4">
                管理员精选的优质标的，可批量添加到自选列表
              </p>

              {aiPicksLoading ? (
                <div className="flex-1 flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
                </div>
              ) : availableAiPicks.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center py-12 text-slate-500">
                  <Sparkles className="w-12 h-12 mb-3 opacity-30" />
                  <p>暂无新的 AI 优选标的</p>
                  <p className="text-xs mt-1">您已添加所有推荐标的到自选</p>
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
                            {pick.name && pick.name !== pick.symbol && (
                              <div className="text-xs text-slate-500 truncate mt-0.5">{pick.name}</div>
                            )}
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
                              ? "此操作将删除所有 AI 优选标的（全局生效），确定继续吗？" 
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
