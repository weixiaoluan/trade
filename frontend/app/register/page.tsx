"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Bot, Check } from "lucide-react";

import { API_BASE } from "@/lib/config";

export default function RegisterPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    username: "",
    password: "",
    confirm_password: "",
    phone: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    // 验证用户名：必须是中文或英文，2-20位
    const usernameRegex = /^[\u4e00-\u9fa5a-zA-Z]{2,20}$/;
    if (!usernameRegex.test(formData.username)) {
      newErrors.username = "用户名必须为2-20位中文或英文字母";
    }

    // 验证密码长度
    if (formData.password.length < 6 || formData.password.length > 20) {
      newErrors.password = "密码长度必须为6-20位";
    }

    // 验证确认密码
    if (formData.password !== formData.confirm_password) {
      newErrors.confirm_password = "两次输入的密码不一致";
    }

    // 验证手机号
    const phoneRegex = /^1[3-9]\d{9}$/;
    if (!phoneRegex.test(formData.phone)) {
      newErrors.phone = "请输入有效的手机号码";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    // 清除对应字段的错误
    if (errors[e.target.name]) {
      setErrors({
        ...errors,
        [e.target.name]: "",
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "注册失败");
      }

      setSuccess(true);

      // 3秒后跳转到登录页
      setTimeout(() => {
        router.push("/login");
      }, 2000);
    } catch (err: any) {
      setErrors({
        ...errors,
        submit: err.message || "注册失败，请重试",
      });
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center p-4 relative overflow-hidden">
        {/* Background Gradient Mesh */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 -left-1/4 w-[600px] h-[600px] bg-indigo-500/10 rounded-full blur-[120px]" />
          <div className="absolute bottom-1/4 -right-1/4 w-[500px] h-[500px] bg-violet-500/10 rounded-full blur-[100px]" />
        </div>
        
        <div className="w-full max-w-md relative z-10">
          <div className="bg-white/[0.03] backdrop-blur-xl rounded-2xl border border-white/[0.08] p-8 text-center">
            <div className="w-20 h-20 bg-emerald-500/10 border border-emerald-500/30 rounded-full flex items-center justify-center mx-auto mb-6">
              <Check className="w-10 h-10 text-emerald-400" />
            </div>
            <h2 className="text-2xl font-semibold text-slate-100 mb-2">
              注册成功！
            </h2>
            <p className="text-slate-500 mb-6">即将跳转到登录页面...</p>
            <div className="flex justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Gradient Mesh - 与主页一致 */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-1/4 w-[600px] h-[600px] bg-indigo-500/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 -right-1/4 w-[500px] h-[500px] bg-violet-500/10 rounded-full blur-[100px]" />
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Logo - 与主页一致 */}
        <div className="text-center mb-8">
          <div className="inline-block mb-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 p-[1px]">
              <div className="w-full h-full rounded-2xl bg-[#020617] flex items-center justify-center">
                <Bot className="w-8 h-8 text-indigo-400" />
              </div>
            </div>
          </div>
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight">
            <span className="bg-gradient-to-r from-slate-100 via-indigo-200 to-slate-100 bg-clip-text text-transparent">
              证券数据研究工具
            </span>
          </h1>
          <p className="text-slate-500 mt-2 text-sm">
            个人学习研究用 · 技术指标计算与可视化
          </p>
        </div>

        {/* Register Form */}
        <div className="bg-white/[0.03] backdrop-blur-xl rounded-2xl border border-white/[0.08] p-8">
          <h2 className="text-xl font-semibold text-slate-100 text-center mb-6">
            注册账号
          </h2>
          
          {/* 免责声明 */}
          <div className="mb-6 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
            <p className="text-amber-300/90 text-xs leading-relaxed">
              ⚠️ 本工具仅供个人学习研究使用，所有数据分析结果不构成任何投资建议。注册即表示您已阅读并同意此声明。
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username */}
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">
                用户名 <span className="text-rose-400">*</span>
              </label>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                placeholder="请输入中文或英文用户名"
                className={`w-full px-4 py-3 bg-white/[0.03] border rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all ${
                  errors.username ? "border-rose-500/50" : "border-white/[0.08]"
                }`}
                required
              />
              {errors.username && (
                <p className="text-rose-400 text-sm mt-1">{errors.username}</p>
              )}
              <p className="text-slate-600 text-xs mt-1">
                2-20位中文或英文字母
              </p>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">
                密码 <span className="text-rose-400">*</span>
              </label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="请输入密码"
                className={`w-full px-4 py-3 bg-white/[0.03] border rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all ${
                  errors.password ? "border-rose-500/50" : "border-white/[0.08]"
                }`}
                required
              />
              {errors.password && (
                <p className="text-rose-400 text-sm mt-1">{errors.password}</p>
              )}
              <p className="text-slate-600 text-xs mt-1">6-20位字符</p>
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">
                确认密码 <span className="text-rose-400">*</span>
              </label>
              <input
                type="password"
                name="confirm_password"
                value={formData.confirm_password}
                onChange={handleChange}
                placeholder="请再次输入密码"
                className={`w-full px-4 py-3 bg-white/[0.03] border rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all ${
                  errors.confirm_password ? "border-rose-500/50" : "border-white/[0.08]"
                }`}
                required
              />
              {errors.confirm_password && (
                <p className="text-rose-400 text-sm mt-1">
                  {errors.confirm_password}
                </p>
              )}
            </div>

            {/* Phone */}
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">
                手机号 <span className="text-rose-400">*</span>
              </label>
              <input
                type="tel"
                name="phone"
                value={formData.phone}
                onChange={handleChange}
                placeholder="请输入手机号"
                className={`w-full px-4 py-3 bg-white/[0.03] border rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all ${
                  errors.phone ? "border-rose-500/50" : "border-white/[0.08]"
                }`}
                required
              />
              {errors.phone && (
                <p className="text-rose-400 text-sm mt-1">{errors.phone}</p>
              )}
            </div>

            {/* Submit Error */}
            {errors.submit && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl">
                <p className="text-rose-400 text-sm text-center">
                  {errors.submit}
                </p>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-indigo-500 to-violet-600 text-white font-semibold rounded-xl hover:from-indigo-600 hover:to-violet-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-[#020617] transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-6"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <svg
                    className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  注册中...
                </span>
              ) : (
                "注 册"
              )}
            </button>
          </form>

          {/* Login Link */}
          <div className="mt-6 text-center">
            <p className="text-slate-500">
              已有账号？{" "}
              <Link
                href="/login"
                className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
              >
                立即登录
              </Link>
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-slate-600 text-xs mt-8">
          © 2025 AI-Trade · 基于 DeepSeek + AutoGen 构建
        </p>
      </div>
    </div>
  );
}
