"use client";

import { memo } from "react";

interface SkeletonProps {
  className?: string;
  animate?: boolean;
}

// 基础骨架元素
export const Skeleton = memo(function Skeleton({ 
  className = "", 
  animate = true 
}: SkeletonProps) {
  return (
    <div 
      className={`bg-slate-700/50 rounded ${animate ? 'animate-pulse' : ''} ${className}`} 
    />
  );
});

// 卡片骨架
export const CardSkeleton = memo(function CardSkeleton() {
  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
      <div className="flex items-center gap-2 mb-4">
        <Skeleton className="w-4 h-4 rounded" />
        <Skeleton className="h-4 w-20" />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-slate-900/50 rounded-lg p-3">
            <Skeleton className="h-3 w-12 mb-2" />
            <Skeleton className="h-6 w-24 mb-1" />
            <Skeleton className="h-3 w-16" />
          </div>
        ))}
      </div>
    </div>
  );
});

// 表格行骨架
export const TableRowSkeleton = memo(function TableRowSkeleton({ cols = 5 }: { cols?: number }) {
  return (
    <div className="flex items-center gap-4 p-3 border-b border-slate-700/30">
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton key={i} className="h-4 flex-1" />
      ))}
    </div>
  );
});

// 列表骨架
export const ListSkeleton = memo(function ListSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 p-3 bg-slate-800/30 rounded-lg">
          <Skeleton className="w-10 h-10 rounded-lg" />
          <div className="flex-1">
            <Skeleton className="h-4 w-24 mb-1" />
            <Skeleton className="h-3 w-16" />
          </div>
          <Skeleton className="h-6 w-16" />
        </div>
      ))}
    </div>
  );
});

// 页面头部骨架
export const HeaderSkeleton = memo(function HeaderSkeleton() {
  return (
    <header className="sticky top-0 z-50 bg-slate-900/80 backdrop-blur-xl border-b border-slate-700/50">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Skeleton className="w-9 h-9 rounded-lg" />
          <div>
            <Skeleton className="h-5 w-32 mb-1" />
            <Skeleton className="h-3 w-20" />
          </div>
        </div>
        <div className="flex gap-2">
          <Skeleton className="w-9 h-9 rounded-lg" />
          <Skeleton className="w-9 h-9 rounded-lg" />
        </div>
      </div>
    </header>
  );
});

// 模拟交易页面骨架
export const SimTradePageSkeleton = memo(function SimTradePageSkeleton() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <HeaderSkeleton />
      <main className="max-w-7xl mx-auto px-4 py-4 space-y-4">
        <Skeleton className="h-10 w-full rounded-xl" />
        <CardSkeleton />
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Skeleton className="w-4 h-4 rounded" />
            <Skeleton className="h-4 w-20" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-slate-900/50 rounded-lg p-3">
                <Skeleton className="h-3 w-12 mb-2" />
                <Skeleton className="h-5 w-16" />
              </div>
            ))}
          </div>
        </div>
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Skeleton className="w-9 h-9 rounded-lg" />
              <div>
                <Skeleton className="h-4 w-40 mb-1" />
                <Skeleton className="h-3 w-32" />
              </div>
            </div>
            <div className="flex gap-2">
              <Skeleton className="w-16 h-8 rounded-lg" />
              <Skeleton className="w-12 h-8 rounded-lg" />
            </div>
          </div>
        </div>
        <ListSkeleton rows={3} />
      </main>
    </div>
  );
});

// Dashboard页面骨架
export const DashboardPageSkeleton = memo(function DashboardPageSkeleton() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <HeaderSkeleton />
      <main className="max-w-7xl mx-auto px-4 py-4 space-y-4">
        <div className="flex gap-2 overflow-x-auto pb-2">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-8 w-20 rounded-lg flex-shrink-0" />
          ))}
        </div>
        <ListSkeleton rows={8} />
      </main>
    </div>
  );
});
