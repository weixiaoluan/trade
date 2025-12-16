'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Database, Brain, MessageSquare, Shield, BarChart3 } from 'lucide-react';

const loadingStages = [
  { icon: Bot, text: 'AI Agents 正在集结...', color: 'text-electric-blue' },
  { icon: Database, text: '正在获取实时行情数据...', color: 'text-emerald' },
  { icon: Brain, text: '技术面分析师正在计算指标...', color: 'text-purple-400' },
  { icon: BarChart3, text: '基本面分析师正在评估价值...', color: 'text-gold' },
  { icon: Shield, text: '数据审计员正在验证来源...', color: 'text-rose' },
  { icon: MessageSquare, text: '首席投资官正在生成报告...', color: 'text-neon-cyan' },
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
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex flex-col items-center justify-center py-20"
    >
      {/* Radar Animation */}
      <div className="relative w-48 h-48 mb-8">
        {/* Outer rings */}
        {[1, 2, 3].map((ring) => (
          <motion.div
            key={ring}
            className="absolute inset-0 rounded-full border border-electric-blue/20"
            style={{
              transform: `scale(${0.3 + ring * 0.25})`,
            }}
            animate={{
              opacity: [0.2, 0.5, 0.2],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              delay: ring * 0.3,
            }}
          />
        ))}

        {/* Scanning line */}
        <motion.div
          className="absolute inset-0"
          animate={{ rotate: 360 }}
          transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
        >
          <div className="absolute top-1/2 left-1/2 w-1/2 h-0.5 bg-gradient-to-r from-electric-blue to-transparent origin-left" />
        </motion.div>

        {/* Center icon */}
        <motion.div
          className="absolute inset-0 flex items-center justify-center"
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-electric-blue/20 to-purple-500/20 flex items-center justify-center backdrop-blur-sm border border-electric-blue/30">
            <Icon className={`w-10 h-10 ${currentStage.color}`} />
          </div>
        </motion.div>

        {/* Floating particles */}
        {[...Array(6)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-2 h-2 rounded-full bg-electric-blue/50"
            style={{
              top: '50%',
              left: '50%',
            }}
            animate={{
              x: [0, Math.cos((i * Math.PI) / 3) * 60],
              y: [0, Math.sin((i * Math.PI) / 3) * 60],
              opacity: [1, 0],
              scale: [0, 1],
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
        <motion.div
          key={stageIndex}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="text-center"
        >
          <p className={`text-xl font-medium mb-2 ${currentStage.color}`}>
            {currentStep || currentStage.text}
          </p>
          <p className="text-slate-500 text-sm">
            多智能体协同分析中，请稍候...
          </p>
        </motion.div>
      </AnimatePresence>

      {/* Progress Bar */}
      <div className="w-80 mt-8">
        <div className="flex justify-between text-sm text-slate-500 mb-2">
          <span>分析进度</span>
          <span>{progress}%</span>
        </div>
        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-electric-blue via-purple-500 to-rose"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>

      {/* Agent Status Grid */}
      <div className="grid grid-cols-3 gap-4 mt-8">
        {loadingStages.slice(0, 6).map((stage, index) => {
          const StageIcon = stage.icon;
          const isActive = index <= Math.floor((progress / 100) * 5);
          return (
            <motion.div
              key={index}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
                isActive ? 'bg-slate-800/50' : 'bg-slate-900/30'
              }`}
              animate={isActive ? { opacity: 1 } : { opacity: 0.4 }}
            >
              <StageIcon
                className={`w-4 h-4 ${isActive ? stage.color : 'text-slate-600'}`}
              />
              <span
                className={`text-xs ${isActive ? 'text-slate-300' : 'text-slate-600'}`}
              >
                {stage.text.split('...')[0]}
              </span>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
