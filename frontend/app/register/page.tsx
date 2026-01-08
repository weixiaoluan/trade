"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function RegisterPage() {
  const router = useRouter();

  useEffect(() => {
    // 注册功能已关闭，重定向到登录页面
    router.replace("/login");
  }, [router]);

  return (
    <div className="min-h-screen bg-[#020617] flex items-center justify-center p-4">
      <div className="text-center">
        <p className="text-slate-400">正在跳转到登录页面...</p>
      </div>
    </div>
  );
}
