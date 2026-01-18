"use client";

// framer-motion removed

interface HarmonyLoaderProps {
  size?: "sm" | "md" | "lg";
  text?: string;
  fullScreen?: boolean;
}

export default function HarmonyLoader({ 
  size = "md", 
  text,
  fullScreen = false 
}: HarmonyLoaderProps) {
  const sizeConfig = {
    sm: { container: 32, dot: 6, gap: 3 },
    md: { container: 48, dot: 8, gap: 4 },
    lg: { container: 64, dot: 10, gap: 5 },
  };

  const config = sizeConfig[size];
  
  // 鸿蒙风格�?个点围绕中心旋转，带有脉冲和流动效果
  const dots = [0, 1, 2, 3];
  
  const containerVariants = {
    animate: {
      rotate: 360,
      transition: {
        duration: 2,
        repeat: Infinity,
        ease: "linear",
      },
    },
  };

  const dotVariants = {
    animate: (i: number) => ({
      scale: [1, 1.3, 1],
      opacity: [0.5, 1, 0.5],
      transition: {
        duration: 1.2,
        repeat: Infinity,
        delay: i * 0.15,
        ease: "easeInOut",
      },
    }),
  };

  const pulseVariants = {
    animate: {
      scale: [1, 1.5, 1],
      opacity: [0.3, 0, 0.3],
      transition: {
        duration: 1.5,
        repeat: Infinity,
        ease: "easeOut",
      },
    },
  };

  const loader = (
    <div className="flex flex-col items-center justify-center gap-4">
      {/* 主加载动�?*/}
      <div className="relative" style={{ width: config.container, height: config.container }}>
        {/* 外层脉冲光环 */}
        <div
          className="absolute inset-0 rounded-full bg-gradient-to-r from-indigo-500/30 to-violet-500/30"
          variants={pulseVariants}
          animate="animate"
        />
        
        {/* 旋转容器 */}
        <div
          className="absolute inset-0"
          variants={containerVariants}
          animate="animate"
        >
          {dots.map((i) => {
            const angle = (i * 360) / dots.length;
            const radius = config.container / 2 - config.dot / 2 - 2;
            const x = Math.cos((angle * Math.PI) / 180) * radius;
            const y = Math.sin((angle * Math.PI) / 180) * radius;
            
            return (
              <div
                key={i}
                className="absolute rounded-full bg-gradient-to-br from-indigo-400 to-violet-500"
                style={{
                  width: config.dot,
                  height: config.dot,
                  left: config.container / 2 + x - config.dot / 2,
                  top: config.container / 2 + y - config.dot / 2,
                  boxShadow: "0 0 10px rgba(99, 102, 241, 0.5)",
                }}
                custom={i}
                variants={dotVariants}
                animate="animate"
              />
            );
          })}
        </div>

        {/* 中心�?*/}
        <div
          className="absolute rounded-full bg-gradient-to-br from-indigo-300 to-violet-400"
          style={{
            width: config.dot * 0.8,
            height: config.dot * 0.8,
            left: config.container / 2 - (config.dot * 0.8) / 2,
            top: config.container / 2 - (config.dot * 0.8) / 2,
          }}
          transition={{
            duration: 1,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      </div>

      {/* 加载文字 */}
      {text && (
        <motion.span
          className="text-sm text-slate-400 font-medium"
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          {text}
        </motion.span>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 bg-[#020617]/90 backdrop-blur-sm flex items-center justify-center z-50">
        {loader}
      </div>
    );
  }

  return loader;
}

// 按钮内嵌的简化版加载�?
export function ButtonLoader() {
  return (
    <div className="flex items-center gap-1.5">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-white"
          transition={{
            duration: 0.6,
            repeat: Infinity,
            delay: i * 0.1,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}

// 线性进度条加载�?
export function LinearLoader() {
  return (
    <div className="w-full h-1 bg-white/10 rounded-full overflow-hidden">
      <div
        className="h-full bg-gradient-to-r from-indigo-500 via-violet-500 to-indigo-500 rounded-full"
        style={{ backgroundSize: "200% 100%" }}
        transition={{
          duration: 1.5,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
    </div>
  );
}
