"use client";

import { useState, useRef } from "react";
import { Plus, Trash2, Upload, X, Search, Star, Camera } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

interface WatchlistItem {
  symbol: string;
  name?: string;
  type?: string;
  added_at?: string;
}

interface RecognizedItem {
  symbol: string;
  name: string;
  type: string;
}

interface WatchlistPanelProps {
  watchlist: WatchlistItem[];
  onRefresh: () => void;
  onSelectItem: (symbol: string) => void;
}

export function WatchlistPanel({
  watchlist,
  onRefresh,
  onSelectItem,
}: WatchlistPanelProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [showOcrModal, setShowOcrModal] = useState(false);
  const [addSymbol, setAddSymbol] = useState("");
  const [addLoading, setAddLoading] = useState(false);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [recognizedItems, setRecognizedItems] = useState<RecognizedItem[]>([]);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const fileInputRef = useRef<HTMLInputElement>(null);

  const getToken = () => localStorage.getItem("token");

  const handleAddSymbol = async () => {
    if (!addSymbol.trim()) return;

    setAddLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/watchlist`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ symbol: addSymbol.trim().toUpperCase() }),
      });

      if (response.ok) {
        setAddSymbol("");
        setShowAddModal(false);
        onRefresh();
      }
    } catch (error) {
      console.error("添加自选失败:", error);
    } finally {
      setAddLoading(false);
    }
  };

  const handleDelete = async (symbol: string) => {
    try {
      const response = await fetch(
        `${API_BASE}/api/watchlist/${encodeURIComponent(symbol)}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${getToken()}`,
          },
        }
      );

      if (response.ok) {
        onRefresh();
      }
    } catch (error) {
      console.error("删除自选失败:", error);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setOcrLoading(true);
    setShowOcrModal(true);
    setRecognizedItems([]);
    setSelectedItems(new Set());

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE}/api/ocr/recognize`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getToken()}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (data.status === "success" && data.recognized) {
        setRecognizedItems(data.recognized);
        // 默认全选
        setSelectedItems(new Set(data.recognized.map((item: RecognizedItem) => item.symbol)));
      }
    } catch (error) {
      console.error("图片识别失败:", error);
    } finally {
      setOcrLoading(false);
    }

    // 清空文件输入
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleConfirmOcr = async () => {
    if (selectedItems.size === 0) {
      setShowOcrModal(false);
      return;
    }

    const itemsToAdd = recognizedItems
      .filter((item) => selectedItems.has(item.symbol))
      .map((item) => ({
        symbol: item.symbol,
        name: item.name,
        type: item.type,
      }));

    try {
      const response = await fetch(`${API_BASE}/api/watchlist/batch`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(itemsToAdd),
      });

      if (response.ok) {
        onRefresh();
      }
    } catch (error) {
      console.error("批量添加失败:", error);
    }

    setShowOcrModal(false);
    setRecognizedItems([]);
    setSelectedItems(new Set());
  };

  const toggleItem = (symbol: string) => {
    const newSelected = new Set(selectedItems);
    if (newSelected.has(symbol)) {
      newSelected.delete(symbol);
    } else {
      newSelected.add(symbol);
    }
    setSelectedItems(newSelected);
  };

  const getTypeLabel = (type?: string) => {
    switch (type) {
      case "stock":
        return "股票";
      case "etf":
        return "ETF";
      case "fund":
        return "基金";
      default:
        return "";
    }
  };

  return (
    <div className="bg-slate-800/30 backdrop-blur-xl rounded-xl border border-slate-700/50 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Star className="w-5 h-5 text-yellow-400" />
          <h3 className="text-lg font-semibold text-white">我的自选</h3>
          <span className="text-xs text-slate-500">({watchlist.length})</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="p-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-slate-400 hover:text-white transition-all"
            title="上传截图识别"
          >
            <Camera className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="p-2 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 hover:text-blue-300 transition-all"
            title="手动添加"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileUpload}
      />

      {/* Watchlist */}
      {watchlist.length === 0 ? (
        <div className="text-center py-8">
          <Star className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-500 text-sm">暂无自选</p>
          <p className="text-slate-600 text-xs mt-1">
            点击右上角按钮添加自选标的
          </p>
        </div>
      ) : (
        <div className="space-y-2 max-h-[400px] overflow-y-auto">
          {watchlist.map((item) => (
            <div
              key={item.symbol}
              className="flex items-center justify-between p-3 rounded-lg bg-slate-700/30 hover:bg-slate-700/50 transition-all group"
            >
              <button
                onClick={() => onSelectItem(item.symbol)}
                className="flex items-center gap-3 flex-1 text-left"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold text-white">
                      {item.symbol}
                    </span>
                    {item.type && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-600/50 text-slate-400">
                        {getTypeLabel(item.type)}
                      </span>
                    )}
                  </div>
                  {item.name && (
                    <span className="text-xs text-slate-500">{item.name}</span>
                  )}
                </div>
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(item.symbol);
                }}
                className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-500/20 text-slate-500 hover:text-red-400 transition-all"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">添加自选</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 hover:bg-slate-700 rounded-lg transition-all"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
              <input
                type="text"
                value={addSymbol}
                onChange={(e) => setAddSymbol(e.target.value)}
                placeholder="输入股票/ETF/基金代码，如 AAPL、600519"
                className="w-full pl-10 pr-4 py-3 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                onKeyDown={(e) => e.key === "Enter" && handleAddSymbol()}
              />
            </div>

            <div className="flex gap-3 mt-4">
              <button
                onClick={() => setShowAddModal(false)}
                className="flex-1 py-2.5 bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 transition-all"
              >
                取消
              </button>
              <button
                onClick={handleAddSymbol}
                disabled={addLoading || !addSymbol.trim()}
                className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition-all disabled:opacity-50"
              >
                {addLoading ? "添加中..." : "添加"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* OCR Recognition Modal */}
      {showOcrModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6 w-full max-w-lg mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">
                识别结果确认
              </h3>
              <button
                onClick={() => setShowOcrModal(false)}
                className="p-1 hover:bg-slate-700 rounded-lg transition-all"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            {ocrLoading ? (
              <div className="py-12 text-center">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <p className="text-slate-400">AI 正在识别图片中的股票代码...</p>
              </div>
            ) : recognizedItems.length === 0 ? (
              <div className="py-12 text-center">
                <Camera className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-500">未识别到股票代码</p>
                <p className="text-slate-600 text-sm mt-1">
                  请上传包含股票代码的截图
                </p>
              </div>
            ) : (
              <>
                <p className="text-sm text-slate-400 mb-3">
                  识别到 {recognizedItems.length} 个标的，请选择要添加的：
                </p>
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {recognizedItems.map((item) => (
                    <label
                      key={item.symbol}
                      className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all ${
                        selectedItems.has(item.symbol)
                          ? "bg-blue-600/20 border border-blue-500/50"
                          : "bg-slate-700/30 border border-transparent hover:bg-slate-700/50"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedItems.has(item.symbol)}
                        onChange={() => toggleItem(item.symbol)}
                        className="w-4 h-4 rounded border-slate-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-semibold text-white">
                            {item.symbol}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-600/50 text-slate-400">
                            {getTypeLabel(item.type)}
                          </span>
                        </div>
                        {item.name && (
                          <span className="text-xs text-slate-500">
                            {item.name}
                          </span>
                        )}
                      </div>
                    </label>
                  ))}
                </div>
              </>
            )}

            <div className="flex gap-3 mt-4">
              <button
                onClick={() => setShowOcrModal(false)}
                className="flex-1 py-2.5 bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 transition-all"
              >
                取消
              </button>
              <button
                onClick={handleConfirmOcr}
                disabled={ocrLoading || selectedItems.size === 0}
                className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition-all disabled:opacity-50"
              >
                添加选中 ({selectedItems.size})
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
