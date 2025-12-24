"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { 
  Bot, Shield, Users, Check, X, ArrowLeft, 
  Crown, Clock, UserCheck, UserX 
} from "lucide-react";

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
                      {new Date(user.created_at).toLocaleString("zh-CN")}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {user.role !== "admin" && (
                        <div className="flex items-center justify-end gap-2">
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
                              className="p-2 rounded-lg bg-rose-500/20 text-rose-400 hover:bg-rose-500/30 transition-all disabled:opacity-50"
                              title="拒绝"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          )}
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
    </div>
  );
}
