"use client";

import { useState, useEffect, useRef } from "react";
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
  const dropdownRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭下拉菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };

    if (showDropdown) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showDropdown]);

  const handleLogout = () => {
    console.log("执行退出登录");
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    onLogout();
    window.location.href = "/login";
  };

  const handleAdminClick = () => {
    console.log("跳转到管理页面");
    setShowDropdown(false);
    router.push("/admin");
  };

  const isAdmin = user.role === "admin";
  const isSVIP = user.status === "approved" && user.role !== "admin";
  const isPending = user.status === "pending";

  return (
    <div className="relative" ref={dropdownRef}>
      {/* 头像按钮 */}
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/50 hover:bg-slate-700/50 transition-all"
      >
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center ${
            isAdmin
              ? "bg-gradient-to-br from-amber-500 to-orange-600"
              : isSVIP
              ? "bg-gradient-to-br from-violet-500 to-purple-600"
              : "bg-gradient-to-br from-blue-500 to-cyan-500"
          }`}
        >
          {isAdmin ? (
            <Shield className="w-4 h-4 text-white" />
          ) : isSVIP ? (
            <Crown className="w-4 h-4 text-white" />
          ) : (
            <User className="w-4 h-4 text-white" />
          )}
        </div>
        <span className="text-sm text-slate-300 max-w-[120px] truncate hidden sm:flex items-center gap-1">
          {user.username}
          {isSVIP && <Crown className="w-3.5 h-3.5 text-amber-400" />}
          {isAdmin && <Shield className="w-3.5 h-3.5 text-amber-400" />}
        </span>
        <ChevronDown className="w-4 h-4 text-slate-500" />
      </button>

      {/* 下拉菜单 */}
      {showDropdown && (
        <div className="absolute right-0 top-full mt-2 w-52 bg-[#0f172a] border border-white/[0.08] rounded-xl shadow-2xl z-[9999] overflow-visible">
          {/* 用户信息 */}
          <div className="px-4 py-3 border-b border-white/[0.06] bg-white/[0.02]">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium text-white truncate">
                {user.username}
              </p>
              {isAdmin && (
                <span className="px-1.5 py-0.5 text-[10px] bg-amber-500/20 text-amber-400 rounded">
                  管理员
                </span>
              )}
              {isSVIP && (
                <span className="px-1.5 py-0.5 text-[10px] bg-violet-500/20 text-violet-400 rounded flex items-center gap-0.5">
                  <Crown className="w-2.5 h-2.5" />
                  SVIP
                </span>
              )}
              {isPending && (
                <span className="px-1.5 py-0.5 text-[10px] bg-slate-500/20 text-slate-400 rounded">
                  待审核
                </span>
              )}
            </div>
            {user.phone && (
              <p className="text-xs text-slate-500 mt-0.5">{user.phone}</p>
            )}
          </div>

          {/* 管理员菜单 */}
          {isAdmin && (
            <button
              onClick={handleAdminClick}
              className="w-full flex items-center gap-2 px-4 py-3 text-sm text-amber-400 hover:bg-white/[0.05] transition-all border-b border-white/[0.06]"
            >
              <Shield className="w-4 h-4" />
              用户管理
            </button>
          )}

          {/* 退出登录 */}
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-4 py-3 text-sm text-rose-400 hover:bg-white/[0.05] transition-all"
          >
            <LogOut className="w-4 h-4" />
            退出登录
          </button>
        </div>
      )}
    </div>
  );
}
