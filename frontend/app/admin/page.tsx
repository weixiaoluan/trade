"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { 
  Shield, Users, Check, X, ArrowLeft, 
  Crown, Clock, UserCheck, UserX, Eye, Trash2, Loader2, UserPlus
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
    }
  }, [currentUser, fetchUsers]);

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
                <h1 className="text-lg font-semibold text-white">用户管理</h1>
                <p className="text-xs text-slate-500">管理员控制台</p>
              </div>
            </div>
          </div>
          <button
            onClick={() => setShowAddUserModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-500 to-violet-600 text-white rounded-xl hover:from-indigo-600 hover:to-violet-700 transition-all"
          >
            <UserPlus className="w-4 h-4" />
            <span className="hidden sm:inline">新增用户</span>
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10">
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
    </div>
  );
}
