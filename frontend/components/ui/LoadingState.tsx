'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Database, Brain, MessageSquare, Shield, BarChart3 } from 'lucide-react';

const loadingStages = [
  // 第一列：数据获取
  { icon: Bot, text: 'AI Agents正在集结', color: 'text-electric-blue', column: 1 },
  { icon: Database, text: '正在获取实时行情数据', color: 'text-emerald-400', column: 1 },
  { icon: BarChart3, text: '基本面分析师正在评估价�?, color: 'text-amber-400', column: 1 },
  // 第二列：量化分析
  { icon: Brain, text: '技术面分析师正在计算指�?, color: 'text-purple-400', column: 2 },
  { icon: BarChart3, text: '量化引擎正在生成信号', color: 'text-cyan-400', column: 2 },
  { icon: Shield, text: '数据审计员正在验证来�?, color: 'text-rose-400', column: 2 },
  // 第三列：AI分析
  { icon: Shield, text: '风险管理专家正在评估风险', color: 'text-orange-400', column: 3 },
  { icon: MessageSquare, text: '首席投资官正在生成报�?, color: 'text-indigo-400', column: 3 },
  { icon: Bot, text: '质量控制专员正在审核', color: 'text-teal-400', column: 3 },
];

interface LoadingStateProps {
  progress?: number;
  currentStep?: string;
}

export function LoadingState({ progress = 0, currentStep }: LoadingStateProps) {
  const [stageIndex, setStageIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setStageIndex((prev) => (prev + 1) % loadingStages.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const currentStage = loadingStages[stageIndex];
  const Icon = currentStage.icon;

  return (
    <div
      className="flex flex-col items-center justify-center py-20"
    >
      {/* Radar Animation */}
      <div className="relative w-48 h-48 mb-8">
        {/* Outer rings */}
        {[1, 2, 3].map((ring) => (
          <div
            key={ring}
            className="absolute inset-0 rounded-full border border-electric-blue/20"
            style={{
              transform: `scale(${0.3 + ring * 0.25})`,
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              delay: ring * 0.3,
            }}
          />
        ))}

        {/* Scanning line */}
        <div
          className="absolute inset-0"
          transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
        >
          <div className="absolute top-1/2 left-1/2 w-1/2 h-0.5 bg-gradient-to-r from-electric-blue to-transparent origin-left" />
        </div>

        {/* Center icon */}
        <div
          className="absolute inset-0 flex items-center justify-center"
          transition={{ duration: 2, repeat: Infinity }}
        >
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-electric-blue/20 to-purple-500/20 flex items-center justify-center backdrop-blur-sm border border-electric-blue/30">
            <Icon className={`w-10 h-10 ${currentStage.color}`} />
          </div>
        </div>

        {/* Floating particles */}
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="absolute w-2 h-2 rounded-full bg-electric-blue/50"
            style={{
              top: '50%',
              left: '50%',
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              delay: i * 0.3,
            }}
          />
        ))}
      </div>

      {/* Status Text */}
      <AnimatePresence mode="wait">
        <div
          key={stageIndex}
          className="text-center"
        >
          <p className={`text-xl font-medium mb-2 ${currentStage.color}`}>
            {currentStep || currentStage.text}
          </p>
          <p className="text-slate-500 text-sm">
            数据分析处理中，请稍�?..
          </p>
        </div>

      {/* Progress Bar */}
      <div className="w-80 mt-8">
        <div className="flex justify-between text-sm text-slate-500 mb-2">
          <span>分析进度</span>
          <span>{progress}%</span>
        </div>
        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-electric-blue via-purple-500 to-rose"
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>

      {/* Agent Status Grid - 3列�?�?*/}
      <div className="grid grid-cols-3 gap-3 mt-8 max-w-4xl">
        {loadingStages.map((stage, index) => {
          const StageIcon = stage.icon;
          const isActive = index <= Math.floor((progress / 100) * 8);
          const isCompleted = index < Math.floor((progress / 100) * 8);
          return (
            <div
              key={index}
              className={`flex flex-col gap-2 px-4 py-3 rounded-lg border transition-all ${
                isActive 
                  ? 'bg-slate-800/60 border-white/10 shadow-lg' 
                  : 'bg-slate-900/30 border-white/5'
              }`}
              animate={isActive ? { opacity: 1, scale: 1 } : { opacity: 0.5, scale: 0.98 }}
            >
              <div className="flex items-center gap-2">
                <StageIcon
                  className={`w-4 h-4 ${isActive ? stage.color : 'text-slate-600'}`}
                />
                {isCompleted && (
                  <div
                    className="ml-auto w-2 h-2 rounded-full bg-emerald-500"
                  />
                )}
              </div>
              <span
                className={`text-xs leading-tight ${
                  isActive ? 'text-slate-300 font-medium' : 'text-slate-600'
                }`}
              >
                {stage.text}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
