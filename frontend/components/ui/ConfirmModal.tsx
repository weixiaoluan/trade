"use client";

import { memo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, Info, CheckCircle, XCircle, HelpCircle } from "lucide-react";

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  type?: "warning" | "info" | "success" | "error" | "question";
  confirmText?: string;
  cancelText?: string;
  loading?: boolean;
}

export const ConfirmModal = memo(function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  type = "question",
  confirmText = "确定",
  cancelText = "取消",
  loading = false,
}: ConfirmModalProps) {
  const iconMap = {
    warning: <AlertTriangle className="w-6 h-6 text-amber-400" />,
    info: <Info className="w-6 h-6 text-blue-400" />,
    success: <CheckCircle className="w-6 h-6 text-emerald-400" />,
    error: <XCircle className="w-6 h-6 text-rose-400" />,
    question: <HelpCircle className="w-6 h-6 text-indigo-400" />,
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
    question: {
      bg: "bg-indigo-500/10",
      border: "border-indigo-500/30",
      iconBg: "bg-indigo-500/20",
      button: "bg-indigo-500 hover:bg-indigo-600",
    },
  };

  const colors = colorMap[type];

  const handleConfirm = () => {
    if (!loading) {
      onConfirm();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-[1000] p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            transition={{ type: "spring", duration: 0.3 }}
            className={`w-full max-w-sm ${colors.bg} border ${colors.border} rounded-2xl shadow-2xl overflow-hidden`}
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
                  <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
                    {message}
                  </p>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 pb-6 pt-2 flex gap-3">
              <button
                onClick={onClose}
                disabled={loading}
                className="flex-1 py-3 bg-slate-700/50 hover:bg-slate-700 text-slate-300 font-medium rounded-xl transition-all active:scale-[0.98] disabled:opacity-50"
              >
                {cancelText}
              </button>
              <button
                onClick={handleConfirm}
                disabled={loading}
                className={`flex-1 py-3 ${colors.button} text-white font-medium rounded-xl transition-all active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-2`}
              >
                {loading && (
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                )}
                {confirmText}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
});
