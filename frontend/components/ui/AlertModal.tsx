"use client";

import { memo, useMemo } from "react";
// framer-motion removed
import { AlertTriangle, Info, CheckCircle, XCircle } from "lucide-react";

interface AlertModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  message: string;
  type?: "warning" | "info" | "success" | "error";
  confirmText?: string;
}

const AlertModalComponent = memo(function AlertModal({
  isOpen,
  onClose,
  title,
  message,
  type = "warning",
  confirmText = "确定",
}: AlertModalProps) {
  const iconMap = {
    warning: <AlertTriangle className="w-6 h-6 text-amber-400" />,
    info: <Info className="w-6 h-6 text-blue-400" />,
    success: <CheckCircle className="w-6 h-6 text-emerald-400" />,
    error: <XCircle className="w-6 h-6 text-rose-400" />,
  };

  const colorMap = {
    warning: {
      bg: "bg-amber-500/10",
      border: "border-amber-500/30",
      iconBg: "bg-amber-500/20",
      button: "bg-amber-500 hover:bg-amber-600",
    },
    info: {
      bg: "bg-blue-500/10",
      border: "border-blue-500/30",
      iconBg: "bg-blue-500/20",
      button: "bg-blue-500 hover:bg-blue-600",
    },
    success: {
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/30",
      iconBg: "bg-emerald-500/20",
      button: "bg-emerald-500 hover:bg-emerald-600",
    },
    error: {
      bg: "bg-rose-500/10",
      border: "border-rose-500/30",
      iconBg: "bg-rose-500/20",
      button: "bg-rose-500 hover:bg-rose-600",
    },
  };

  const colors = colorMap[type];

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-[1000] p-4 modal-overlay"
      onClick={onClose}
    >
      <div
        className={`w-full max-w-sm ${colors.bg} border ${colors.border} rounded-2xl shadow-2xl overflow-hidden modal-content`}
        onClick={(e) => e.stopPropagation()}
      >
            {/* Header */}
            <div className="px-6 pt-6 pb-4">
              <div className="flex items-start gap-4">
                <div className={`w-12 h-12 rounded-xl ${colors.iconBg} flex items-center justify-center flex-shrink-0`}>
                  {iconMap[type]}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-white mb-1">
                    {title}
                  </h3>
                  <p className="text-sm text-slate-300 leading-relaxed">
                    {message}
                  </p>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 pb-6 pt-2">
              <button
                onClick={onClose}
                className={`w-full py-3 ${colors.button} text-white font-medium rounded-xl transition-all active:scale-[0.98]`}
              >
                {confirmText}
              </button>
            </div>
      </div>
    </div>
  );
});

export const AlertModal = AlertModalComponent;
