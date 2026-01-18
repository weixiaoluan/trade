import { Loader2 } from "lucide-react";

export default function Loading() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-8 h-8 text-indigo-400 animate-spin mx-auto mb-3" />
        <p className="text-slate-400 text-sm">加载中...</p>
      </div>
    </div>
  );
}
