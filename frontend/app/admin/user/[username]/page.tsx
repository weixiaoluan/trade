"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { 
  Bot, Shield, ArrowLeft, User, Phone, Clock, 
  FileText, Bell, Star, Trash2, Save, X, Loader2,
  Check, AlertCircle, Edit3
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { API_BASE } from "@/lib/config";

interface UserDetail {
  username: string;
  phone: string;
  role: string;
  status: string;
  wechat_openid: string;
  created_at: string;
}

interface WatchlistItem {
  symbol: string;
  name?: string;
  type?: string;
  position?: number;
  cost_price?: number;
  ai_buy_price?: number;
  ai_sell_price?: number;
  holding_period?: string;
}

interface ReminderItem {
  id: string;
  reminder_id: string;
  symbol: string;
  name?: string;
  reminder_type: string;
  frequency: string;
}

interface ReportItem {
  id: string;
  symbol: string;
  name?: string;
  created_at: string;
}

export default function UserDetailPage() {
  const router = useRouter();
  const params = useParams();
  const username = params.username as string;

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [userDetail, setUserDetail] = useState<UserDetail | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [reminders, setReminders] = useState<ReminderItem[]>([]);
  const [reports, setReports] = useState<ReportItem[]>([]);

  // 编辑状态
  const [editMode, setEditMode] = useState(false);
  const [editUsername, setEditUsername] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [editOpenId, setEditOpenId] = useState("");

  // 确认删除弹窗
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const getToken = () => localStorage.getItem("token");

  const fetchUserDetail = useCallback(async () => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/admin/users/${encodeURIComponent(username)}/detail`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setUserDetail(data.user);
        setWatchlist(data.watchlist || []);
        setReminders(data.reminders || []);
        setReports(data.reports || []);
        
        // 初始化编辑字段
        setEditUsername(data.user.username);
        setEditPhone(data.user.phone);
        setEditOpenId(data.user.wechat_openid || "");
      } else if (response.status === 403) {
        router.push("/dashboard");
      } else if (response.status === 404) {
        router.push("/admin");
      }
    } catch (error) {
      console.error("获取用户详情失败:", error);
    } finally {
      setLoading(false);
    }
  }, [username, router]);

  useEffect(() => {
    // 检查权限
    const userStr = localStorage.getItem("user");
    if (userStr) {
      const user = JSON.parse(userStr);
      if (user.role !== "admin") {
        router.push("/dashboard");
        return;
      }
    }
    fetchUserDetail();
  }, [fetchUserDetail, router]);

  const handleSave = async () => {
    const token = getToken();
    if (!token) return;

    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/api/admin/users/${encodeURIComponent(username)}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          new_username: editUsername !== username ? editUsername : null,
          phone: editPhone,
          wechat_openid: editOpenId,
        }),
      });

      if (response.ok) {
        setEditMode(false);
        // 如果用户名变更，跳转到新页面
        if (editUsername !== username) {
          router.push(`/admin/user/${encodeURIComponent(editUsername)}`);
        } else {
          fetchUserDetail();
        }
      }
    } catch (error) {
      console.error("保存失败:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    const token = getToken();
    if (!token) return;

    setDeleting(true);
    try {
      const response = await fetch(`${API_BASE}/api/admin/users/${encodeURIComponent(username)}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        router.push("/admin");
      }
    } catch (error) {
      console.error("删除失败:", error);
    } finally {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "approved":
        return <span className="px-2 py-1 text-xs bg-emerald-500/20 text-emerald-400 rounded-full">已审核</span>;
      case "rejected":
        return <span className="px-2 py-1 text-xs bg-rose-500/20 text-rose-400 rounded-full">已拒绝</span>;
      default:
        return <span className="px-2 py-1 text-xs bg-amber-500/20 text-amber-400 rounded-full">待审核</span>;
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

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  if (!userDetail) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <p className="text-slate-400">用户不存在</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      {/* Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-1/4 w-[600px] h-[600px] bg-indigo-500/5 rounded-full blur-[120px]" />
      </div>

      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#020617]/80 backdrop-blur-xl border-b border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push("/admin")}
              className="p-2 rounded-lg hover:bg-white/[0.05] transition-all"
            >
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </button>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 p-[1px]">
                <div className="w-full h-full rounded-xl bg-[#020617] flex items-center justify-center">
                  <User className="w-5 h-5 text-indigo-400" />
                </div>
              </div>
              <div>
                <h1 className="text-lg font-semibold text-white">用户详情</h1>
                <p className="text-xs text-slate-500">{username}</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {!editMode ? (
              <>
                <button
                  onClick={() => setEditMode(true)}
                  className="flex items-center gap-2 px-3 py-2 bg-indigo-600/20 text-indigo-400 rounded-lg hover:bg-indigo-600/30"
                >
                  <Edit3 className="w-4 h-4" />
                  编辑
                </button>
                {userDetail.role !== "admin" && (
                  <button
                    onClick={() => setShowDeleteConfirm(true)}
                    className="flex items-center gap-2 px-3 py-2 bg-rose-600/20 text-rose-400 rounded-lg hover:bg-rose-600/30"
                  >
                    <Trash2 className="w-4 h-4" />
                    注销
                  </button>
                )}
              </>
            ) : (
              <>
                <button
                  onClick={() => setEditMode(false)}
                  className="flex items-center gap-2 px-3 py-2 bg-white/[0.05] text-slate-300 rounded-lg"
                >
                  <X className="w-4 h-4" />
                  取消
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-2 px-3 py-2 bg-indigo-600 text-white rounded-lg disabled:opacity-50"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  保存
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10">
        {/* 用户基本信息 */}
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <User className="w-5 h-5 text-indigo-400" />
            基本信息
          </h2>
          
          {editMode ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-400 mb-1 block">用户名</label>
                <input
                  type="text"
                  value={editUsername}
                  onChange={(e) => setEditUsername(e.target.value)}
                  className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 mb-1 block">手机号</label>
                <input
                  type="text"
                  value={editPhone}
                  onChange={(e) => setEditPhone(e.target.value)}
                  className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>
              <div className="md:col-span-2">
                <label className="text-xs text-slate-400 mb-1 block">微信 OpenID</label>
                <input
                  type="text"
                  value={editOpenId}
                  onChange={(e) => setEditOpenId(e.target.value)}
                  placeholder="未配置"
                  className="w-full px-3 py-2 bg-white/[0.03] border border-white/[0.08] rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 font-mono"
                />
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-slate-500 mb-1">用户名</p>
                <p className="text-sm text-white">{userDetail.username}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500 mb-1">手机号</p>
                <p className="text-sm text-white">{userDetail.phone}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500 mb-1">状态</p>
                {getStatusBadge(userDetail.status)}
              </div>
              <div>
                <p className="text-xs text-slate-500 mb-1">注册时间</p>
                <p className="text-sm text-slate-300">
                  {new Date(userDetail.created_at).toLocaleString("zh-CN")}
                </p>
              </div>
              <div className="col-span-2">
                <p className="text-xs text-slate-500 mb-1">微信 OpenID</p>
                <p className="text-sm text-slate-300 font-mono">
                  {userDetail.wechat_openid || "未配置"}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* 自选列表 */}
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl overflow-hidden mb-6">
          <div className="px-6 py-4 border-b border-white/[0.06] flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Star className="w-5 h-5 text-amber-400" />
              自选列表 ({watchlist.length})
            </h2>
          </div>
          {watchlist.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-white/[0.02]">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">代码</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">名称</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-slate-400">持仓</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-slate-400">成本价</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">周期</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-emerald-400">建议买入</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-rose-400">建议卖出</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.06]">
                  {watchlist.map((item) => (
                    <tr key={item.symbol} className="hover:bg-white/[0.02]">
                      <td className="px-4 py-3 text-sm font-mono text-white">{item.symbol}</td>
                      <td className="px-4 py-3 text-sm text-slate-300">{item.name || "-"}</td>
                      <td className="px-4 py-3 text-sm text-slate-300 text-right">{item.position?.toLocaleString() || "-"}</td>
                      <td className="px-4 py-3 text-sm text-slate-300 text-right">{item.cost_price ? `¥${item.cost_price.toFixed(2)}` : "-"}</td>
                      <td className="px-4 py-3 text-sm">
                        <span className="px-1.5 py-0.5 text-xs bg-indigo-500/10 text-indigo-400 rounded">
                          {getHoldingPeriodLabel(item.holding_period)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-emerald-400 text-right">{item.ai_buy_price ? `¥${item.ai_buy_price.toFixed(3)}` : "-"}</td>
                      <td className="px-4 py-3 text-sm text-rose-400 text-right">{item.ai_sell_price ? `¥${item.ai_sell_price.toFixed(3)}` : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-8 text-center text-slate-500">暂无自选</div>
          )}
        </div>

        {/* 提醒设置 */}
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl overflow-hidden mb-6">
          <div className="px-6 py-4 border-b border-white/[0.06]">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Bell className="w-5 h-5 text-amber-400" />
              提醒设置 ({reminders.length})
            </h2>
          </div>
          {reminders.length > 0 ? (
            <div className="divide-y divide-white/[0.06]">
              {reminders.map((reminder) => (
                <div key={reminder.id || reminder.reminder_id} className="px-6 py-3 flex items-center justify-between">
                  <div>
                    <span className="text-sm font-mono text-white">{reminder.symbol}</span>
                    {reminder.name && <span className="text-sm text-slate-500 ml-2">{reminder.name}</span>}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 text-xs rounded ${
                      reminder.reminder_type === 'buy' ? 'bg-emerald-500/20 text-emerald-400' :
                      reminder.reminder_type === 'sell' ? 'bg-rose-500/20 text-rose-400' :
                      'bg-indigo-500/20 text-indigo-400'
                    }`}>
                      {reminder.reminder_type === 'buy' ? '买入' : reminder.reminder_type === 'sell' ? '卖出' : '买+卖'}
                    </span>
                    <span className="text-xs text-slate-500">{reminder.frequency}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-slate-500">暂无提醒</div>
          )}
        </div>

        {/* AI分析报告 */}
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-white/[0.06]">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <FileText className="w-5 h-5 text-emerald-400" />
              AI分析报告 ({reports.length})
            </h2>
          </div>
          {reports.length > 0 ? (
            <div className="divide-y divide-white/[0.06]">
              {reports.map((report) => (
                <div key={report.id} className="px-6 py-3 flex items-center justify-between">
                  <div>
                    <span className="text-sm font-mono text-white">{report.symbol}</span>
                    {report.name && <span className="text-sm text-slate-500 ml-2">{report.name}</span>}
                  </div>
                  <span className="text-xs text-slate-500">
                    {new Date(report.created_at).toLocaleString("zh-CN")}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-slate-500">暂无报告</div>
          )}
        </div>
      </main>

      {/* 删除确认弹窗 */}
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
                  <AlertCircle className="w-5 h-5 text-rose-400" />
                </div>
                <h3 className="text-lg font-semibold text-white">确认注销用户</h3>
              </div>
              <p className="text-slate-400 mb-6">
                确定要注销用户 <span className="text-white font-medium">{username}</span> 吗？
                此操作将删除该用户的所有数据，包括自选列表、提醒设置和分析报告，且无法恢复。
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
    </div>
  );
}
