"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { User, LogOut, ChevronDown, Crown, Shield } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

interface UserHeaderProps {
  user: {
    username: string;
    phone?: string;
    role?: string;
    status?: string;
  };
  onLogout: () => void;
}

export function UserHeader({ user, onLogout }: UserHeaderProps) {
  const router = useRouter();
  const [showDropdown, setShowDropdown] = useState(false);

  const handleLogout = async () => {
    const token = localStorage.getItem("token");

    try {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
    } catch (error) {
      console.error("Logout error:", error);
    }

    localStorage.removeItem("token");
    localStorage.removeItem("user");
    onLogout();
    router.push("/login");
  };

  return (
    <div className="relative">
      <button
        onClick={(e) => {
          e.stopPropagation();
          setShowDropdown(!showDropdown);
        }}
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/50 hover:bg-slate-700/50 transition-all relative z-50"
      >
        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
          user.role === 'admin' 
            ? 'bg-gradient-to-br from-amber-500 to-orange-600' 
            : user.status === 'approved'
              ? 'bg-gradient-to-br from-violet-500 to-purple-600'
              : 'bg-gradient-to-br from-blue-500 to-cyan-500'
        }`}>
          {user.role === 'admin' ? (
            <Shield className="w-4 h-4 text-white" />
          ) : user.status === 'approved' ? (
            <Crown className="w-4 h-4 text-white" />
          ) : (
            <User className="w-4 h-4 text-white" />
          )}
        </div>
        <span className="text-sm text-slate-300 max-w-[120px] truncate hidden sm:flex items-center gap-1">
          {user.username}
          {user.status === 'approved' && user.role !== 'admin' && (
            <Crown className="w-3.5 h-3.5 text-amber-400" />
          )}
          {user.role === 'admin' && (
            <Shield className="w-3.5 h-3.5 text-amber-400" />
          )}
        </span>
        <ChevronDown className="w-4 h-4 text-slate-500" />
      </button>

      {/* Dropdown */}
      {showDropdown && (
        <>
          <div
            className="fixed inset-0 z-[100]"
            onClick={() => setShowDropdown(false)}
          />
          <div className="absolute right-0 top-full mt-2 w-52 bg-[#0f172a] border border-white/[0.08] rounded-xl shadow-2xl z-[101] overflow-hidden">
            <div className="px-4 py-3 border-b border-white/[0.06] bg-white/[0.02]">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-white truncate">
                  {user.username}
                </p>
                {user.role === 'admin' && (
                  <span className="px-1.5 py-0.5 text-[10px] bg-amber-500/20 text-amber-400 rounded">管理员</span>
                )}
                {user.status === 'approved' && user.role !== 'admin' && (
                  <span className="px-1.5 py-0.5 text-[10px] bg-violet-500/20 text-violet-400 rounded flex items-center gap-0.5">
                    <Crown className="w-2.5 h-2.5" />SVIP
                  </span>
                )}
                {user.status === 'pending' && (
                  <span className="px-1.5 py-0.5 text-[10px] bg-slate-500/20 text-slate-400 rounded">待审核</span>
                )}
              </div>
              {user.phone && (
                <p className="text-xs text-slate-500 mt-0.5">{user.phone}</p>
              )}
            </div>
            {user.role === 'admin' && (
              <button
                onClick={() => {
                  setShowDropdown(false);
                  router.push('/admin');
                }}
                className="w-full flex items-center gap-2 px-4 py-3 text-sm text-amber-400 hover:bg-white/[0.05] transition-all border-b border-white/[0.06]"
              >
                <Shield className="w-4 h-4" />
                用户管理
              </button>
            )}
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-2 px-4 py-3 text-sm text-rose-400 hover:bg-white/[0.05] transition-all"
            >
              <LogOut className="w-4 h-4" />
              退出登录
            </button>
          </div>
        </>
      )}
    </div>
  );
}
