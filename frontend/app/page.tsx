'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { API_BASE } from "@/lib/config";

export default function HomePage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('token');
      
      if (!token) {
        router.push('/login');
        return;
      }

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10秒超时
        
        const response = await fetch(`${API_BASE}/api/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });
        
        clearTimeout(timeoutId);

        if (response.ok) {
          router.push('/dashboard');
        } else {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          router.push('/login');
        }
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
          setError('服务器响应超时，请刷新重试');
        } else {
          router.push('/login');
        }
      }
    };

    checkAuth();
  }, [router]);

  return (
    <main className="min-h-screen bg-[#020617] flex items-center justify-center">
      <div className="text-center">
        {error ? (
          <div className="text-red-400 text-sm">{error}</div>
        ) : (
          <div className="animate-spin rounded-full h-24 w-24 border-b-4 border-indigo-500 mx-auto"></div>
        )}
      </div>
    </main>
  );
}
