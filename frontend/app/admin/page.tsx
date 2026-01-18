"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { 
  Shield, Users, Check, X, ArrowLeft, 
  Crown, Clock, UserCheck, UserX, Eye, Trash2, Loader2, UserPlus, Star, RefreshCw,
  Database, Download, Upload, Settings, Save, RotateCcw, Layers, Plus, Search, Import
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import { API_BASE } from "@/lib/config";

interface User {
  id: number;
  username: string;
  phone: string;
  role: string;
  status: string;
  created_at: string;
}

interface AiPick {
  symbol: string;
  name: string;
  type: string;
  added_by: string;
  added_at: string;
}

interface StrategyAsset {
  id: number;
  strategy_id: string;
  symbol: string;
  name: string;
  asset_type: string;
  category: string;
  trading_rule: string;
  is_qdii: number;
  max_premium_rate: number;
  enabled: number;
  sort_order: number;
}

interface StrategyInfo {
  id: string;
  name: string;
  category: string;
  risk_level: string;
  assets: StrategyAsset[];
}

interface WatchlistItem {
  symbol: string;
  name: string;
  type: string;
}

export default function AdminPage() {
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  
  // 注销确认弹窗
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteUsername, setDeleteUsername] = useState<string>("");
  const [deleting, setDeleting] = useState(false);
  
  // 新增用户弹窗
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [addUserForm, setAddUserForm] = useState({
    username: "",
    password: "",
    confirm_password: "",
    phone: "",
  });
  const [addUserErrors, setAddUserErrors] = useState<Record<string, string>>({});
  const [addingUser, setAddingUser] = useState(false);

  // 研究列表记录
  const [aiPicks, setAiPicks] = useState<AiPick[]>([]);
  const [aiPicksLoading, setAiPicksLoading] = useState(false);

  // 数据库管理
  const [activeTab, setActiveTab] = useState<'users' | 'database' | 'assets'>('users');
  const [backups, setBackups] = useState<any[]>([]);
  const [backupsLoading, setBackupsLoading] = useState(false);
  const [backupSettings, setBackupSettings] = useState<{
    auto_backup_enabled: boolean;
    backup_time: string;
    backup_interval_minutes: number;
    keep_days: number;
  }>({ auto_backup_enabled: true, backup_time: '03:00', backup_interval_minutes: 0, keep_days: 7 });
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [backupOperating, setBackupOperating] = useState<string | null>(null);

  // 策略标的池管理
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);
  const [strategiesLoading, setStrategiesLoading] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState<string>('');
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [assetOperating, setAssetOperating] = useState<string | null>(null);
  const [showAddAssetModal, setShowAddAssetModal] = useState(false);
  const [newAsset, setNewAsset] = useState({
    symbol: '',
    name: '',
    category: 'risk',
    trading_rule: 'T+1',
    is_qdii: false,
  });
  
  // 市场标的搜索
  const [showMarketModal, setShowMarketModal] = useState(false);
  const [marketType, setMarketType] = useState<'etf' | 'stock' | 'bond'>('etf');
  const [marketKeyword, setMarketKeyword] = useState('');
  const [marketSymbols, setMarketSymbols] = useState<{symbol: string; name: string; type: string}[]>([]);
  const [marketLoading, setMarketLoading] = useState(false);

  const getToken = () => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("token");
    }
    return null;
  };

  // 检查权限
  useEffect(() => {
    const token = getToken();
    const userStr = localStorage.getItem("user");
    
    if (!token || !userStr) {
      router.push("/login");
      return;
    }

    const user = JSON.parse(userStr);
    if (user.role !== "admin") {
      router.push("/dashboard");
      return;
    }

    setCurrentUser(user);
  }, [router]);

  // 获取用户列表
  const fetchUsers = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE}/api/admin/users`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setUsers(data.users || []);
      } else if (response.status === 403) {
        router.push("/dashboard");
      }
    } catch (error) {
      console.error("获取用户列表失败:", error);
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    if (currentUser) {
      fetchUsers();
      fetchAiPicks();
    }
  }, [currentUser, fetchUsers]);

  // 切换到策略标的管理时加载数据
  useEffect(() => {
    if (currentUser && activeTab === 'assets') {
      const loadAssetsData = async () => {
        const token = getToken();
        if (!token) return;
        
        setStrategiesLoading(true);
        try {
          const response = await fetch(`${API_BASE}/api/strategy/assets`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          
          if (response.ok) {
            const data = await response.json();
            setStrategies(data.strategies || []);
            if (data.strategies?.length > 0 && !selectedStrategy) {
              setSelectedStrategy(data.strategies[0].id);
            }
          }
        } catch (error) {
          console.error("加载策略标的数据失败:", error);
        } finally {
          setStrategiesLoading(false);
        }
      };
      loadAssetsData();
      
      // 加载自选列表
      const loadWatchlist = async () => {
        const token = getToken();
        if (!token) return;
        
        setWatchlistLoading(true);
        try {
          const response = await fetch(`${API_BASE}/api/watchlist`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          
          if (response.ok) {
            const data = await response.json();
            setWatchlist(data.watchlist || []);
          }
        } catch (error) {
          console.error("加载自选列表失败:", error);
        } finally {
          setWatchlistLoading(false);
        }
      };
      loadWatchlist();
    }
  }, [currentUser, activeTab, selectedStrategy]);

  // 切换到数据库管理时加载数据
  useEffect(() => {
    if (currentUser && activeTab === 'database') {
      const loadDatabaseData = async () => {
        const token = getToken();
        if (!token) return;
        
        setBackupsLoading(true);
        try {
          const [backupsRes, settingsRes] = await Promise.all([
            fetch(`${API_BASE}/api/admin/database/backups`, {
              headers: { Authorization: `Bearer ${token}` },
            }),
            fetch(`${API_BASE}/api/admin/database/settings`, {
              headers: { Authorization: `Bearer ${token}` },
            }),
          ]);
          
          if (backupsRes.ok) {
            const data = await backupsRes.json();
            setBackups(data.backups || []);
          }
          if (settingsRes.ok) {
            const data = await settingsRes.json();
            setBackupSettings({
              auto_backup_enabled: data.auto_backup_enabled ?? true,
              backup_time: data.backup_time || '03:00',
              backup_interval_minutes: data.backup_interval_minutes || 0,
              keep_days: data.keep_days || 7,
            });
          }
        } catch (error) {
          console.error("加载数据库管理数据失败:", error);
        } finally {
          setBackupsLoading(false);
        }
      };
      loadDatabaseData();
    }
  }, [currentUser, activeTab]);

  // 获取研究列表记录
  const fetchAiPicks = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    setAiPicksLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/ai-picks`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setAiPicks(data.picks || []);
      }
    } catch (error) {
      console.error("获取研究列表失败:", error);
    } finally {
      setAiPicksLoading(false);
    }
  }, []);

  // 获取备份列表
  const fetchBackups = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    setBackupsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/admin/database/backups`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setBackups(data.backups || []);
      }
    } catch (error) {
      console.error("获取备份列表失败:", error);
    } finally {
      setBackupsLoading(false);
    }
  }, []);

  // 获取备份设置
  const fetchBackupSettings = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE}/api/admin/database/settings`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setBackupSettings({
          auto_backup_enabled: data.auto_backup_enabled ?? true,
          backup_time: data.backup_time || '03:00',
          backup_interval_minutes: data.backup_interval_minutes || 0,
          keep_days: data.keep_days || 7,
        });
      }
    } catch (error) {
      console.error("获取备份设置失败:", error);
    }
  }, []);

  // 创建备份
  const handleCreateBackup = async () => {
    const token = getToken();
    if (!token) return;

    setBackupOperating('create');
    try {
      const response = await fetch(`${API_BASE}/api/admin/database/backup`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        fetchBackups();
      }
    } catch (error) {
      console.error("创建备份失败:", error);
    } finally {
      setBackupOperating(null);
    }
  };

  // 恢复备份
  const handleRestoreBackup = async (backupName: string) => {
    const token = getToken();
    if (!token) return;

    if (!confirm(`确定要恢复备份 ${backupName} 吗？当前数据将被覆盖！`)) return;

    setBackupOperating(backupName);
    try {
      const response = await fetch(`${API_BASE}/api/admin/database/restore/${encodeURIComponent(backupName)}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        alert("备份恢复成功！");
        fetchBackups();
      }
    } catch (error) {
      console.error("恢复备份失败:", error);
    } finally {
      setBackupOperating(null);
    }
  };

  // 删除备份
  const handleDeleteBackup = async (backupName: string) => {
    const token = getToken();
    if (!token) return;

    if (!confirm(`确定要删除备份 ${backupName} 吗？`)) return;

    setBackupOperating(backupName);
    try {
      const response = await fetch(`${API_BASE}/api/admin/database/backup/${encodeURIComponent(backupName)}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        fetchBackups();
      }
    } catch (error) {
      console.error("删除备份失败:", error);
    } finally {
      setBackupOperating(null);
    }
  };

  // 保存备份设置
  const handleSaveBackupSettings = async () => {
    const token = getToken();
    if (!token) return;

    setSettingsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/admin/database/settings`, {
        method: "POST",
        headers: { 
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(backupSettings),
      });

      if (response.ok) {
        alert("设置保存成功！");
      }
    } catch (error) {
      console.error("保存设置失败:", error);
    } finally {
      setSettingsLoading(false);
    }
  };

  // 删除研究列表标的
  const handleDeleteAiPick = async (symbol: string) => {
    const token = getToken();
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE}/api/ai-picks/${encodeURIComponent(symbol)}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        fetchAiPicks();
      }
    } catch (error) {
      console.error("删除研究列表标的失败:", error);
    }
  };

  // 审核通过
  const handleApprove = async (username: string) => {
    const token = getToken();
    if (!token) return;

    setActionLoading(username);
    try {
      const response = await fetch(`${API_BASE}/api/admin/users/${username}/approve`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        fetchUsers();
      }
    } catch (error) {
      console.error("审核失败:", error);
    } finally {
      setActionLoading(null);
    }
  };

  // 拒绝
  const handleReject = async (username: string) => {
    const token = getToken();
    if (!token) return;

    setActionLoading(username);
    try {
      const response = await fetch(`${API_BASE}/api/admin/users/${username}/reject`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        fetchUsers();
      }
    } catch (error) {
      console.error("拒绝失败:", error);
    } finally {
      setActionLoading(null);
    }
  };

  // 注销用户
  const handleDelete = async () => {
    const token = getToken();
    if (!token || !deleteUsername) return;

    setDeleting(true);
    try {
      const response = await fetch(`${API_BASE}/api/admin/users/${encodeURIComponent(deleteUsername)}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        fetchUsers();
        setShowDeleteConfirm(false);
        setDeleteUsername("");
      }
    } catch (error) {
      console.error("注销失败:", error);
    } finally {
      setDeleting(false);
    }
  };

  // 打开注销确认弹窗
  const openDeleteConfirm = (username: string) => {
    setDeleteUsername(username);
    setShowDeleteConfirm(true);
  };

  // 验证新增用户表单
  const validateAddUserForm = () => {
    const newErrors: Record<string, string> = {};

    // 验证用户名：必须是中文或英文，2-20位
    const usernameRegex = /^[\u4e00-\u9fa5a-zA-Z]{2,20}$/;
    if (!usernameRegex.test(addUserForm.username)) {
      newErrors.username = "用户名必须为2-20位中文或英文字母";
    }

    // 验证密码长度
    if (addUserForm.password.length < 6 || addUserForm.password.length > 20) {
      newErrors.password = "密码长度必须为6-20位";
    }

    // 验证确认密码
    if (addUserForm.password !== addUserForm.confirm_password) {
      newErrors.confirm_password = "两次输入的密码不一致";
    }

    // 验证手机号
    const phoneRegex = /^1[3-9]\d{9}$/;
    if (!phoneRegex.test(addUserForm.phone)) {
      newErrors.phone = "请输入有效的手机号码";
    }

    setAddUserErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // 新增用户
  const handleAddUser = async () => {
    if (!validateAddUserForm()) return;

    const token = getToken();
    if (!token) return;

    setAddingUser(true);
    try {
      const response = await fetch(`${API_BASE}/api/admin/users/create`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          username: addUserForm.username,
          password: addUserForm.password,
          phone: addUserForm.phone,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setShowAddUserModal(false);
        setAddUserForm({ username: "", password: "", confirm_password: "", phone: "" });
        setAddUserErrors({});
        fetchUsers();
      } else {
        setAddUserErrors({ submit: data.detail || "创建用户失败" });
      }
    } catch (error) {
      setAddUserErrors({ submit: "创建用户失败，请重试" });
    } finally {
      setAddingUser(false);
    }
  };

  // 添加策略标的
  const handleAddAsset = async () => {
    if (!selectedStrategy || !newAsset.symbol) return;
    
    const token = getToken();
    if (!token) return;
    
    setAssetOperating(newAsset.symbol);
    try {
      const response = await fetch(`${API_BASE}/api/admin/strategy/assets/${selectedStrategy}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(newAsset),
      });
      
      if (response.ok) {
        // 刷新策略列表
        const res = await fetch(`${API_BASE}/api/strategy/assets`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setStrategies(data.strategies || []);
        }
        setShowAddAssetModal(false);
        setNewAsset({ symbol: '', name: '', category: 'risk', trading_rule: 'T+1', is_qdii: false });
      }
    } catch (error) {
      console.error("添加标的失败:", error);
    } finally {
      setAssetOperating(null);
    }
  };

  // 移除策略标的
  const handleRemoveAsset = async (symbol: string) => {
    if (!selectedStrategy) return;
    
    const token = getToken();
    if (!token) return;
    
    setAssetOperating(symbol);
    try {
      const response = await fetch(`${API_BASE}/api/admin/strategy/assets/${selectedStrategy}/${encodeURIComponent(symbol)}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        // 刷新策略列表
        const res = await fetch(`${API_BASE}/api/strategy/assets`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setStrategies(data.strategies || []);
        }
      }
    } catch (error) {
      console.error("移除标的失败:", error);
    } finally {
      setAssetOperating(null);
    }
  };

  // 从自选列表导入标的
  const handleImportFromWatchlist = async (symbols: string[]) => {
    if (!selectedStrategy || symbols.length === 0) {
      alert("请先选择策略，且自选列表不能为空");
      return;
    }
    
    const token = getToken();
    if (!token) return;
    
    setAssetOperating('import');
    try {
      const response = await fetch(`${API_BASE}/api/admin/strategy/assets/${selectedStrategy}/import-watchlist`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          username: currentUser?.username,
          symbols: symbols,
        }),
      });
      
      if (response.ok) {
        const result = await response.json();
        alert(`成功导入 ${result.imported_count || 0} 个标的`);
        // 刷新策略列表
        const res = await fetch(`${API_BASE}/api/strategy/assets`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setStrategies(data.strategies || []);
        }
      } else {
        const err = await response.json();
        alert(`导入失败: ${err.detail || '未知错误'}`);
      }
    } catch (error) {
      console.error("导入标的失败:", error);
      alert("导入标的失败，请检查网络连接");
    } finally {
      setAssetOperating(null);
    }
  };

  // 搜索市场标的
  const handleSearchMarketSymbols = async () => {
    const token = getToken();
    if (!token) return;
    
    setMarketLoading(true);
    try {
      const params = new URLSearchParams({
        type: marketType,
        keyword: marketKeyword,
      });
      const response = await fetch(`${API_BASE}/api/market/symbols?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        setMarketSymbols(data.symbols || []);
      } else {
        alert("获取标的列表失败");
      }
    } catch (error) {
      console.error("搜索市场标的失败:", error);
      alert("搜索失败，请检查网络");
    } finally {
      setMarketLoading(false);
    }
  };

  // 从市场标的添加到策略
  const handleAddFromMarket = async (item: {symbol: string; name: string; type: string}) => {
    if (!selectedStrategy) return;
    
    const token = getToken();
    if (!token) return;
    
    setAssetOperating(item.symbol);
    try {
      const response = await fetch(`${API_BASE}/api/admin/strategy/assets/${selectedStrategy}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          symbol: item.symbol,
          name: item.name,
          category: 'risk',
          trading_rule: item.type === 'ETF' ? 'T+1' : 'T+1',
          is_qdii: false,
        }),
      });
      
      if (response.ok) {
        alert(`成功添加 ${item.name}`);
        // 刷新策略列表
        const res = await fetch(`${API_BASE}/api/strategy/assets`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setStrategies(data.strategies || []);
        }
      } else {
        const err = await response.json();
        alert(`添加失败: ${err.detail || '未知错误'}`);
      }
    } catch (error) {
      console.error("添加标的失败:", error);
    } finally {
      setAssetOperating(null);
    }
  };

  // 获取当前选中策略的标的列表
  const currentStrategyAssets = strategies.find(s => s.id === selectedStrategy)?.assets || [];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "approved":
        return (
          <span className="px-2 py-1 text-xs bg-emerald-500/20 text-emerald-400 rounded-full flex items-center gap-1">
            <UserCheck className="w-3 h-3" />
            已审核
          </span>
        );
      case "rejected":
        return (
          <span className="px-2 py-1 text-xs bg-rose-500/20 text-rose-400 rounded-full flex items-center gap-1">
            <UserX className="w-3 h-3" />
            已拒绝
          </span>
        );
      case "deleted":
        return (
          <span className="px-2 py-1 text-xs bg-slate-500/20 text-slate-400 rounded-full flex items-center gap-1">
            <Trash2 className="w-3 h-3" />
            已注销
          </span>
        );
      default:
        return (
          <span className="px-2 py-1 text-xs bg-amber-500/20 text-amber-400 rounded-full flex items-center gap-1">
            <Clock className="w-3 h-3" />
            待审核
          </span>
        );
    }
  };

  const getRoleBadge = (role: string) => {
    if (role === "admin") {
      return (
        <span className="px-2 py-1 text-xs bg-amber-500/20 text-amber-400 rounded-full flex items-center gap-1">
          <Shield className="w-3 h-3" />
          管理员
        </span>
      );
    }
    return (
      <span className="px-2 py-1 text-xs bg-slate-500/20 text-slate-400 rounded-full flex items-center gap-1">
        <Users className="w-3 h-3" />
        普通用户
      </span>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      {/* Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-1/4 w-[600px] h-[600px] bg-amber-500/5 rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 -right-1/4 w-[500px] h-[500px] bg-orange-500/5 rounded-full blur-[100px]" />
      </div>

      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#020617]/80 backdrop-blur-xl border-b border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push("/dashboard")}
              className="p-2 rounded-lg hover:bg-white/[0.05] transition-all"
            >
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </button>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 p-[1px]">
                <div className="w-full h-full rounded-xl bg-[#020617] flex items-center justify-center">
                  <Shield className="w-5 h-5 text-amber-400" />
                </div>
              </div>
              <div>
                <h1 className="text-lg font-semibold text-white">管理员控制台</h1>
                <p className="text-xs text-slate-500">用户管理 / 数据库管理 / 标的管理</p>
              </div>
            </div>
          </div>
          {activeTab === 'users' && (
            <button
              onClick={() => setShowAddUserModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-500 to-violet-600 text-white rounded-xl hover:from-indigo-600 hover:to-violet-700 transition-all"
            >
              <UserPlus className="w-4 h-4" />
              <span className="hidden sm:inline">新增用户</span>
            </button>
          )}
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10">
        {/* Tab Navigation */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('users')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all ${
              activeTab === 'users'
                ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/40'
                : 'bg-white/[0.03] text-slate-400 border border-white/[0.06] hover:bg-white/[0.05]'
            }`}
          >
            <Users className="w-4 h-4" />
            用户管理
          </button>
          <button
            onClick={() => setActiveTab('database')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all ${
              activeTab === 'database'
                ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/40'
                : 'bg-white/[0.03] text-slate-400 border border-white/[0.06] hover:bg-white/[0.05]'
            }`}
          >
            <Database className="w-4 h-4" />
            数据库管理
          </button>
          <button
            onClick={() => setActiveTab('assets')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all ${
              activeTab === 'assets'
                ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/40'
                : 'bg-white/[0.03] text-slate-400 border border-white/[0.06] hover:bg-white/[0.05]'
            }`}
          >
            <Layers className="w-4 h-4" />
            标的管理
          </button>
        </div>

        {activeTab === 'users' && (
          <>
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-indigo-500/20 flex items-center justify-center">
                <Users className="w-5 h-5 text-indigo-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{users.length}</p>
                <p className="text-xs text-slate-500">总用户数</p>
              </div>
            </div>
          </div>
          <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
                <Clock className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">
                  {users.filter(u => u.status === "pending").length}
                </p>
                <p className="text-xs text-slate-500">待审核</p>
              </div>
            </div>
          </div>
          <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                <UserCheck className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">
                  {users.filter(u => u.status === "approved").length}
                </p>
                <p className="text-xs text-slate-500">已审核</p>
              </div>
            </div>
          </div>
          <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-violet-500/20 flex items-center justify-center">
                <Crown className="w-5 h-5 text-violet-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">
                  {users.filter(u => u.status === "approved" && u.role !== "admin").length}
                </p>
                <p className="text-xs text-slate-500">SVIP会员</p>
              </div>
            </div>
          </div>
        </div>

        {/* User Table */}
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-white/[0.06]">
            <h2 className="text-lg font-semibold text-white">用户列表</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-white/[0.02]">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">用户名</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">手机号</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">角色</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">状态</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">注册时间</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.06]">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-white">{user.username}</span>
                        {user.status === "approved" && user.role !== "admin" && (
                          <Crown className="w-4 h-4 text-amber-400" />
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-400">{user.phone}</td>
                    <td className="px-6 py-4">{getRoleBadge(user.role)}</td>
                    <td className="px-6 py-4">{getStatusBadge(user.status)}</td>
                    <td className="px-6 py-4 text-sm text-slate-400">
                      {new Date(user.created_at).toLocaleString("zh-CN", { hour12: false })}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {user.role !== "admin" && user.status !== "deleted" && (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => router.push(`/admin/user/${encodeURIComponent(user.username)}`)}
                            className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400 hover:bg-indigo-500/30 transition-all"
                            title="查看详情"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          {user.status !== "approved" && (
                            <button
                              onClick={() => handleApprove(user.username)}
                              disabled={actionLoading === user.username}
                              className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-all disabled:opacity-50"
                              title="审核通过"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                          )}
                          {user.status !== "rejected" && (
                            <button
                              onClick={() => handleReject(user.username)}
                              disabled={actionLoading === user.username}
                              className="p-2 rounded-lg bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 transition-all disabled:opacity-50"
                              title="拒绝"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            onClick={() => openDeleteConfirm(user.username)}
                            className="p-2 rounded-lg bg-rose-500/20 text-rose-400 hover:bg-rose-500/30 transition-all"
                            title="注销用户"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 研究列表记录 */}
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl overflow-hidden mt-8">
          <div className="px-6 py-4 border-b border-white/[0.06] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Star className="w-5 h-5 text-amber-400" />
              <h2 className="text-lg font-semibold text-white">研究列表记录</h2>
              <span className="text-xs text-slate-500">（今日添加）</span>
            </div>
            <button
              onClick={fetchAiPicks}
              disabled={aiPicksLoading}
              className="p-2 rounded-lg bg-white/[0.05] text-slate-400 hover:bg-white/[0.08] transition-all disabled:opacity-50"
              title="刷新"
            >
              <RefreshCw className={`w-4 h-4 ${aiPicksLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <div className="overflow-x-auto">
            {aiPicksLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
              </div>
            ) : aiPicks.length === 0 ? (
              <div className="text-center py-12 text-slate-500">
                <Star className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>暂无研究列表记录</p>
              </div>
            ) : (
              <table className="w-full">
                <thead className="bg-white/[0.02]">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">代码</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">名称</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">类型</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">添加人</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">添加时间</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.06]">
                  {aiPicks.map((pick) => (
                    <tr key={pick.symbol} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-6 py-4">
                        <span className="text-sm font-mono font-medium text-white">{pick.symbol}</span>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-300">{pick.name || "-"}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          pick.type === 'ETF' ? 'bg-indigo-500/20 text-indigo-400' :
                          pick.type === '股票' ? 'bg-emerald-500/20 text-emerald-400' :
                          pick.type === '基金' ? 'bg-violet-500/20 text-violet-400' :
                          'bg-slate-500/20 text-slate-400'
                        }`}>
                          {pick.type || "未知"}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-400">{pick.added_by || "-"}</td>
                      <td className="px-6 py-4 text-sm text-slate-400">
                        {pick.added_at ? new Date(pick.added_at).toLocaleString("zh-CN", { hour12: false }) : "-"}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => handleDeleteAiPick(pick.symbol)}
                          className="p-2 rounded-lg bg-rose-500/20 text-rose-400 hover:bg-rose-500/30 transition-all"
                          title="删除"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
          </>
        )}

        {/* Database Management Tab */}
        {activeTab === 'database' && (
          <div className="space-y-6">
            {/* Backup Settings */}
            <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-white/[0.06] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Settings className="w-5 h-5 text-indigo-400" />
                  <h2 className="text-lg font-semibold text-white">自动备份设置</h2>
                </div>
                <button
                  onClick={handleSaveBackupSettings}
                  disabled={settingsLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-indigo-500/20 text-indigo-400 rounded-lg hover:bg-indigo-500/30 transition-all disabled:opacity-50"
                >
                  {settingsLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  保存设置
                </button>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">定时备份</label>
                    <button
                      onClick={() => setBackupSettings(prev => ({ ...prev, auto_backup_enabled: !prev.auto_backup_enabled }))}
                      className={`w-full px-4 py-3 rounded-xl border transition-all ${
                        backupSettings.auto_backup_enabled
                          ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400'
                          : 'bg-white/[0.03] border-white/[0.08] text-slate-400'
                      }`}
                    >
                      {backupSettings.auto_backup_enabled ? '已启用' : '已禁用'}
                    </button>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">备份时间</label>
                    <input
                      type="time"
                      value={backupSettings.backup_time}
                      onChange={(e) => setBackupSettings(prev => ({ ...prev, backup_time: e.target.value }))}
                      className="w-full px-4 py-3 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">间隔备份(分钟)</label>
                    <input
                      type="number"
                      min="0"
                      max="1440"
                      value={backupSettings.backup_interval_minutes}
                      onChange={(e) => setBackupSettings(prev => ({ ...prev, backup_interval_minutes: parseInt(e.target.value) || 0 }))}
                      placeholder="0表示禁用"
                      className="w-full px-4 py-3 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                    />
                    <p className="text-xs text-slate-500 mt-1">0表示禁用，建议60-240分钟</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">保留天数</label>
                    <input
                      type="number"
                      min="1"
                      max="30"
                      value={backupSettings.keep_days}
                      onChange={(e) => setBackupSettings(prev => ({ ...prev, keep_days: parseInt(e.target.value) || 7 }))}
                      className="w-full px-4 py-3 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Manual Backup */}
            <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-white/[0.06] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Database className="w-5 h-5 text-emerald-400" />
                  <h2 className="text-lg font-semibold text-white">备份管理</h2>
                  <span className="text-xs text-slate-500">（共 {backups.length} 个备份）</span>
                </div>
                <button
                  onClick={handleCreateBackup}
                  disabled={backupOperating === 'create'}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-500/20 text-emerald-400 rounded-lg hover:bg-emerald-500/30 transition-all disabled:opacity-50"
                >
                  {backupOperating === 'create' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                  立即备份
                </button>
              </div>
              <div className="overflow-x-auto">
                {backupsLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
                  </div>
                ) : backups.length === 0 ? (
                  <div className="text-center py-12 text-slate-500">
                    <Database className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>暂无备份记录</p>
                  </div>
                ) : (
                  <table className="w-full">
                    <thead className="bg-white/[0.02]">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">备份名称</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">类型</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">大小</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">创建时间</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase">操作</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.06]">
                      {backups.map((backup) => (
                        <tr key={backup.backup_name} className="hover:bg-white/[0.02] transition-colors">
                          <td className="px-6 py-4">
                            <span className="text-sm font-mono text-white">{backup.backup_name}</span>
                          </td>
                          <td className="px-6 py-4">
                            <span className={`px-2 py-1 text-xs rounded-full ${
                              backup.type === 'manual'
                                ? 'bg-indigo-500/20 text-indigo-400'
                                : 'bg-slate-500/20 text-slate-400'
                            }`}>
                              {backup.type === 'manual' ? '手动' : '自动'}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-sm text-slate-400">{backup.size_display}</td>
                          <td className="px-6 py-4 text-sm text-slate-400">
                            {backup.created_at ? new Date(backup.created_at).toLocaleString("zh-CN", { hour12: false }) : "-"}
                          </td>
                          <td className="px-6 py-4 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => handleRestoreBackup(backup.backup_name)}
                                disabled={backupOperating === backup.backup_name}
                                className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-all disabled:opacity-50"
                                title="恢复此备份"
                              >
                                {backupOperating === backup.backup_name ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
                              </button>
                              <button
                                onClick={() => handleDeleteBackup(backup.backup_name)}
                                disabled={backupOperating === backup.backup_name}
                                className="p-2 rounded-lg bg-rose-500/20 text-rose-400 hover:bg-rose-500/30 transition-all disabled:opacity-50"
                                title="删除备份"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 标的管理 Tab */}
        {activeTab === 'assets' && (
          <div className="space-y-6">
            {/* 策略选择 */}
            <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Layers className="w-5 h-5 text-indigo-400" />
                  <h2 className="text-lg font-semibold text-white">选择策略</h2>
                </div>
                <button
                  onClick={() => setShowAddAssetModal(true)}
                  disabled={!selectedStrategy}
                  className="flex items-center gap-2 px-4 py-2 bg-indigo-500/20 text-indigo-400 rounded-lg hover:bg-indigo-500/30 transition-all disabled:opacity-50"
                >
                  <Plus className="w-4 h-4" />
                  添加标的
                </button>
              </div>
              
              {strategiesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {strategies.map((strategy) => (
                    <button
                      key={strategy.id}
                      onClick={() => setSelectedStrategy(strategy.id)}
                      className={`px-4 py-2 rounded-lg transition-all ${
                        selectedStrategy === strategy.id
                          ? 'bg-indigo-500/30 text-indigo-300 border border-indigo-500/50'
                          : 'bg-white/[0.03] text-slate-400 border border-white/[0.06] hover:bg-white/[0.05]'
                      }`}
                    >
                      <div className="text-sm font-medium">{strategy.name}</div>
                      <div className="text-xs opacity-60">{strategy.assets.length} 个标的</div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* 当前策略标的列表 */}
            {selectedStrategy && (
              <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl overflow-hidden">
                <div className="px-6 py-4 border-b border-white/[0.06] flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-semibold text-white">
                      {strategies.find(s => s.id === selectedStrategy)?.name} - 标的池
                    </h2>
                    <span className="text-xs text-slate-500">（共 {currentStrategyAssets.length} 个）</span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setShowMarketModal(true)}
                      disabled={!selectedStrategy}
                      className="flex items-center gap-2 px-4 py-2 bg-indigo-500/20 text-indigo-400 rounded-lg hover:bg-indigo-500/30 transition-all disabled:opacity-50"
                    >
                      <Search className="w-4 h-4" />
                      从市场搜索
                    </button>
                    <button
                      onClick={() => {
                        const symbols = watchlist.map(w => w.symbol);
                        if (symbols.length > 0) {
                          handleImportFromWatchlist(symbols);
                        }
                      }}
                      disabled={assetOperating === 'import' || watchlist.length === 0}
                      className="flex items-center gap-2 px-4 py-2 bg-emerald-500/20 text-emerald-400 rounded-lg hover:bg-emerald-500/30 transition-all disabled:opacity-50"
                    >
                      {assetOperating === 'import' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Import className="w-4 h-4" />}
                      从自选导入 ({watchlist.length})
                    </button>
                  </div>
                </div>
                
                {currentStrategyAssets.length === 0 ? (
                  <div className="text-center py-12 text-slate-500">
                    <Layers className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>暂无标的，点击"添加标的"或"从自选导入"</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-white/[0.02]">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">代码</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">名称</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">分类</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">交易规则</th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase">操作</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.06]">
                        {currentStrategyAssets.map((asset) => (
                          <tr key={asset.symbol} className="hover:bg-white/[0.02] transition-colors">
                            <td className="px-6 py-4">
                              <span className="text-sm font-mono text-indigo-400">{asset.symbol}</span>
                            </td>
                            <td className="px-6 py-4 text-sm text-white">{asset.name || '-'}</td>
                            <td className="px-6 py-4">
                              <span className={`px-2 py-1 text-xs rounded-full ${
                                asset.category === 'cash'
                                  ? 'bg-emerald-500/20 text-emerald-400'
                                  : 'bg-indigo-500/20 text-indigo-400'
                              }`}>
                                {asset.category === 'cash' ? '现金' : '风险'}
                              </span>
                            </td>
                            <td className="px-6 py-4">
                              <span className={`px-2 py-1 text-xs rounded-full ${
                                asset.trading_rule === 'T+0'
                                  ? 'bg-amber-500/20 text-amber-400'
                                  : 'bg-slate-500/20 text-slate-400'
                              }`}>
                                {asset.trading_rule}
                              </span>
                            </td>
                            <td className="px-6 py-4 text-right">
                              <button
                                onClick={() => handleRemoveAsset(asset.symbol)}
                                disabled={assetOperating === asset.symbol}
                                className="p-2 rounded-lg bg-rose-500/20 text-rose-400 hover:bg-rose-500/30 transition-all disabled:opacity-50"
                                title="移除标的"
                              >
                                {assetOperating === asset.symbol ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      {/* 注销确认弹窗 */}
      <AnimatePresence>
        {showDeleteConfirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50"
            onClick={() => setShowDeleteConfirm(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-[#0f172a] border border-white/[0.08] rounded-2xl p-6 max-w-md mx-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-rose-500/20 flex items-center justify-center">
                  <Trash2 className="w-5 h-5 text-rose-400" />
                </div>
                <h3 className="text-lg font-semibold text-white">确认注销用户</h3>
              </div>
              <p className="text-slate-400 mb-6">
                确定要注销用户 <span className="text-white font-medium">{deleteUsername}</span> 吗？
                此操作将删除该用户的所有数据，包括自选列表和分析报告，且无法恢复。
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="flex-1 py-2.5 bg-white/[0.05] text-slate-300 rounded-xl"
                >
                  取消
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="flex-1 py-2.5 bg-rose-600 text-white rounded-xl disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                  确认注销
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 新增用户弹窗 */}
      <AnimatePresence>
        {showAddUserModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50"
            onClick={() => setShowAddUserModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-[#0f172a] border border-white/[0.08] rounded-2xl p-6 max-w-md w-full mx-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-full bg-indigo-500/20 flex items-center justify-center">
                  <UserPlus className="w-5 h-5 text-indigo-400" />
                </div>
                <h3 className="text-lg font-semibold text-white">新增用户</h3>
              </div>

              <div className="space-y-4">
                {/* 用户名 */}
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">
                    用户名 <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={addUserForm.username}
                    onChange={(e) => setAddUserForm({ ...addUserForm, username: e.target.value })}
                    placeholder="请输入中文或英文用户名"
                    className={`w-full px-4 py-3 bg-white/[0.03] border rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all ${
                      addUserErrors.username ? "border-rose-500/50" : "border-white/[0.08]"
                    }`}
                  />
                  {addUserErrors.username && (
                    <p className="text-rose-400 text-sm mt-1">{addUserErrors.username}</p>
                  )}
                  <p className="text-slate-600 text-xs mt-1">2-20位中文或英文字母</p>
                </div>

                {/* 密码 */}
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">
                    密码 <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="password"
                    value={addUserForm.password}
                    onChange={(e) => setAddUserForm({ ...addUserForm, password: e.target.value })}
                    placeholder="请输入密码"
                    className={`w-full px-4 py-3 bg-white/[0.03] border rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all ${
                      addUserErrors.password ? "border-rose-500/50" : "border-white/[0.08]"
                    }`}
                  />
                  {addUserErrors.password && (
                    <p className="text-rose-400 text-sm mt-1">{addUserErrors.password}</p>
                  )}
                  <p className="text-slate-600 text-xs mt-1">6-20位字符</p>
                </div>

                {/* 确认密码 */}
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">
                    确认密码 <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="password"
                    value={addUserForm.confirm_password}
                    onChange={(e) => setAddUserForm({ ...addUserForm, confirm_password: e.target.value })}
                    placeholder="请再次输入密码"
                    className={`w-full px-4 py-3 bg-white/[0.03] border rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all ${
                      addUserErrors.confirm_password ? "border-rose-500/50" : "border-white/[0.08]"
                    }`}
                  />
                  {addUserErrors.confirm_password && (
                    <p className="text-rose-400 text-sm mt-1">{addUserErrors.confirm_password}</p>
                  )}
                </div>

                {/* 手机号 */}
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">
                    手机号 <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="tel"
                    value={addUserForm.phone}
                    onChange={(e) => setAddUserForm({ ...addUserForm, phone: e.target.value })}
                    placeholder="请输入手机号"
                    className={`w-full px-4 py-3 bg-white/[0.03] border rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all ${
                      addUserErrors.phone ? "border-rose-500/50" : "border-white/[0.08]"
                    }`}
                  />
                  {addUserErrors.phone && (
                    <p className="text-rose-400 text-sm mt-1">{addUserErrors.phone}</p>
                  )}
                </div>

                {/* 提交错误 */}
                {addUserErrors.submit && (
                  <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl">
                    <p className="text-rose-400 text-sm text-center">{addUserErrors.submit}</p>
                  </div>
                )}
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => {
                    setShowAddUserModal(false);
                    setAddUserForm({ username: "", password: "", confirm_password: "", phone: "" });
                    setAddUserErrors({});
                  }}
                  className="flex-1 py-2.5 bg-white/[0.05] text-slate-300 rounded-xl hover:bg-white/[0.08] transition-all"
                >
                  取消
                </button>
                <button
                  onClick={handleAddUser}
                  disabled={addingUser}
                  className="flex-1 py-2.5 bg-gradient-to-r from-indigo-500 to-violet-600 text-white rounded-xl disabled:opacity-50 flex items-center justify-center gap-2 hover:from-indigo-600 hover:to-violet-700 transition-all"
                >
                  {addingUser ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
                  创建用户
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 添加标的弹窗 */}
      <AnimatePresence>
        {showAddAssetModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50"
            onClick={() => setShowAddAssetModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-[#0f172a] border border-white/[0.08] rounded-2xl p-6 max-w-md w-full mx-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-full bg-indigo-500/20 flex items-center justify-center">
                  <Plus className="w-5 h-5 text-indigo-400" />
                </div>
                <h3 className="text-lg font-semibold text-white">添加标的</h3>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">
                    标的代码 <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={newAsset.symbol}
                    onChange={(e) => setNewAsset({ ...newAsset, symbol: e.target.value })}
                    placeholder="如: 510300.SH"
                    className="w-full px-4 py-3 bg-white/[0.03] border border-white/[0.08] rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">名称</label>
                  <input
                    type="text"
                    value={newAsset.name}
                    onChange={(e) => setNewAsset({ ...newAsset, name: e.target.value })}
                    placeholder="如: 沪深300ETF"
                    className="w-full px-4 py-3 bg-white/[0.03] border border-white/[0.08] rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">分类</label>
                    <select
                      value={newAsset.category}
                      onChange={(e) => setNewAsset({ ...newAsset, category: e.target.value })}
                      className="w-full px-4 py-3 bg-white/[0.03] border border-white/[0.08] rounded-xl text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                    >
                      <option value="risk">风险资产</option>
                      <option value="cash">现金资产</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">交易规则</label>
                    <select
                      value={newAsset.trading_rule}
                      onChange={(e) => setNewAsset({ ...newAsset, trading_rule: e.target.value })}
                      className="w-full px-4 py-3 bg-white/[0.03] border border-white/[0.08] rounded-xl text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                    >
                      <option value="T+1">T+1</option>
                      <option value="T+0">T+0</option>
                    </select>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="is_qdii"
                    checked={newAsset.is_qdii}
                    onChange={(e) => setNewAsset({ ...newAsset, is_qdii: e.target.checked })}
                    className="w-4 h-4 rounded border-white/[0.08] bg-white/[0.03] text-indigo-500 focus:ring-indigo-500/50"
                  />
                  <label htmlFor="is_qdii" className="text-sm text-slate-400">跨境ETF (QDII)</label>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => {
                    setShowAddAssetModal(false);
                    setNewAsset({ symbol: '', name: '', category: 'risk', trading_rule: 'T+1', is_qdii: false });
                  }}
                  className="flex-1 py-2.5 bg-white/[0.05] text-slate-300 rounded-xl hover:bg-white/[0.08] transition-all"
                >
                  取消
                </button>
                <button
                  onClick={handleAddAsset}
                  disabled={!newAsset.symbol || assetOperating !== null}
                  className="flex-1 py-2.5 bg-gradient-to-r from-indigo-500 to-violet-600 text-white rounded-xl disabled:opacity-50 flex items-center justify-center gap-2 hover:from-indigo-600 hover:to-violet-700 transition-all"
                >
                  {assetOperating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                  添加
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 市场标的搜索弹窗 */}
      <AnimatePresence>
        {showMarketModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50"
            onClick={() => setShowMarketModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-[#0f172a] border border-white/[0.08] rounded-2xl p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-full bg-indigo-500/20 flex items-center justify-center">
                  <Search className="w-5 h-5 text-indigo-400" />
                </div>
                <h3 className="text-lg font-semibold text-white">从市场搜索标的</h3>
              </div>

              <div className="flex gap-4 mb-4">
                <div className="flex gap-2">
                  {(['etf', 'stock', 'bond'] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => setMarketType(t)}
                      className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                        marketType === t
                          ? 'bg-indigo-500/30 text-indigo-300 border border-indigo-500/50'
                          : 'bg-white/[0.03] text-slate-400 border border-white/[0.06]'
                      }`}
                    >
                      {t === 'etf' ? 'ETF' : t === 'stock' ? '股票' : '可转债'}
                    </button>
                  ))}
                </div>
                <div className="flex-1 flex gap-2">
                  <input
                    type="text"
                    value={marketKeyword}
                    onChange={(e) => setMarketKeyword(e.target.value)}
                    placeholder="输入关键字搜索..."
                    className="flex-1 px-4 py-2 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                    onKeyDown={(e) => e.key === 'Enter' && handleSearchMarketSymbols()}
                  />
                  <button
                    onClick={handleSearchMarketSymbols}
                    disabled={marketLoading}
                    className="px-4 py-2 bg-indigo-500/20 text-indigo-400 rounded-xl hover:bg-indigo-500/30 transition-all disabled:opacity-50"
                  >
                    {marketLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto min-h-[300px]">
                {marketSymbols.length === 0 ? (
                  <div className="text-center py-12 text-slate-500">
                    <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>点击搜索按钮获取标的列表</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {marketSymbols.map((item) => (
                      <div
                        key={item.symbol}
                        className="flex items-center justify-between p-3 bg-white/[0.02] rounded-lg hover:bg-white/[0.04] transition-all"
                      >
                        <div>
                          <span className="text-sm font-mono text-indigo-400">{item.symbol}</span>
                          <span className="text-sm text-white ml-3">{item.name}</span>
                          <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${
                            item.type === 'ETF' ? 'bg-indigo-500/20 text-indigo-400' :
                            item.type === '股票' ? 'bg-emerald-500/20 text-emerald-400' :
                            'bg-amber-500/20 text-amber-400'
                          }`}>{item.type}</span>
                        </div>
                        <button
                          onClick={() => handleAddFromMarket(item)}
                          disabled={assetOperating === item.symbol}
                          className="px-3 py-1.5 bg-indigo-500/20 text-indigo-400 rounded-lg hover:bg-indigo-500/30 transition-all disabled:opacity-50 text-sm"
                        >
                          {assetOperating === item.symbol ? <Loader2 className="w-4 h-4 animate-spin" /> : '添加'}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="mt-4 pt-4 border-t border-white/[0.06]">
                <button
                  onClick={() => setShowMarketModal(false)}
                  className="w-full py-2.5 bg-white/[0.05] text-slate-300 rounded-xl hover:bg-white/[0.08] transition-all"
                >
                  关闭
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
