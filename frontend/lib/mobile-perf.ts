/**
 * 移动端性能优化工具
 * 提供触摸优化、视口检测、设备适配等功能
 */

import { useCallback, useEffect, useRef, useState } from 'react';

// ============ 设备检测 ============

/**
 * 检测是否为移动设备
 */
export function useMobileDetect() {
  const [isMobile, setIsMobile] = useState(false);
  const [isTablet, setIsTablet] = useState(false);
  const [isTouchDevice, setIsTouchDevice] = useState(false);

  useEffect(() => {
    const checkDevice = () => {
      const ua = navigator.userAgent;
      const mobile = /Android|webOS|iPhone|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua);
      const tablet = /iPad|Android/i.test(ua) && !/Mobile/i.test(ua);
      const touch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
      const width = window.innerWidth;
      
      setIsMobile(mobile || width < 768);
      setIsTablet(tablet || (width >= 768 && width < 1024));
      setIsTouchDevice(touch);
    };

    checkDevice();
    window.addEventListener('resize', checkDevice);
    return () => window.removeEventListener('resize', checkDevice);
  }, []);

  return { isMobile, isTablet, isTouchDevice };
}

// ============ 触摸优化 ============

/**
 * 触摸滑动检测
 */
export function useSwipe(onSwipe: (direction: 'left' | 'right' | 'up' | 'down') => void, threshold = 50) {
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);

  const handleTouchStart = useCallback((e: TouchEvent) => {
    touchStartRef.current = {
      x: e.touches[0].clientX,
      y: e.touches[0].clientY,
    };
  }, []);

  const handleTouchEnd = useCallback((e: TouchEvent) => {
    if (!touchStartRef.current) return;

    const deltaX = e.changedTouches[0].clientX - touchStartRef.current.x;
    const deltaY = e.changedTouches[0].clientY - touchStartRef.current.y;

    if (Math.abs(deltaX) > Math.abs(deltaY)) {
      if (Math.abs(deltaX) > threshold) {
        onSwipe(deltaX > 0 ? 'right' : 'left');
      }
    } else {
      if (Math.abs(deltaY) > threshold) {
        onSwipe(deltaY > 0 ? 'down' : 'up');
      }
    }

    touchStartRef.current = null;
  }, [onSwipe, threshold]);

  useEffect(() => {
    document.addEventListener('touchstart', handleTouchStart, { passive: true });
    document.addEventListener('touchend', handleTouchEnd, { passive: true });
    return () => {
      document.removeEventListener('touchstart', handleTouchStart);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  }, [handleTouchStart, handleTouchEnd]);
}

/**
 * 快速点击（消除 300ms 延迟）
 */
export function useFastClick(ref: React.RefObject<HTMLElement>, onClick: () => void) {
  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    let touchStartTime = 0;
    let touchStartX = 0;
    let touchStartY = 0;

    const handleTouchStart = (e: TouchEvent) => {
      touchStartTime = Date.now();
      touchStartX = e.touches[0].clientX;
      touchStartY = e.touches[0].clientY;
    };

    const handleTouchEnd = (e: TouchEvent) => {
      const touchEndTime = Date.now();
      const touchEndX = e.changedTouches[0].clientX;
      const touchEndY = e.changedTouches[0].clientY;

      // 检查是否为有效点击（时间短、移动距离小）
      const timeDiff = touchEndTime - touchStartTime;
      const distX = Math.abs(touchEndX - touchStartX);
      const distY = Math.abs(touchEndY - touchStartY);

      if (timeDiff < 300 && distX < 10 && distY < 10) {
        e.preventDefault();
        onClick();
      }
    };

    element.addEventListener('touchstart', handleTouchStart, { passive: true });
    element.addEventListener('touchend', handleTouchEnd, { passive: false });

    return () => {
      element.removeEventListener('touchstart', handleTouchStart);
      element.removeEventListener('touchend', handleTouchEnd);
    };
  }, [ref, onClick]);
}

// ============ 视口优化 ============

/**
 * 安全区域检测（刘海屏、底部指示条）
 */
export function useSafeArea() {
  const [safeArea, setSafeArea] = useState({
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
  });

  useEffect(() => {
    const updateSafeArea = () => {
      const style = getComputedStyle(document.documentElement);
      setSafeArea({
        top: parseInt(style.getPropertyValue('--safe-area-inset-top') || '0'),
        bottom: parseInt(style.getPropertyValue('--safe-area-inset-bottom') || '0'),
        left: parseInt(style.getPropertyValue('--safe-area-inset-left') || '0'),
        right: parseInt(style.getPropertyValue('--safe-area-inset-right') || '0'),
      });
    };

    updateSafeArea();
    window.addEventListener('resize', updateSafeArea);
    return () => window.removeEventListener('resize', updateSafeArea);
  }, []);

  return safeArea;
}

/**
 * 键盘高度检测（移动端输入时）
 */
export function useKeyboardHeight() {
  const [keyboardHeight, setKeyboardHeight] = useState(0);

  useEffect(() => {
    if (typeof window === 'undefined' || !('visualViewport' in window)) return;

    const viewport = window.visualViewport!;
    
    const handleResize = () => {
      const heightDiff = window.innerHeight - viewport.height;
      setKeyboardHeight(Math.max(0, heightDiff));
    };

    viewport.addEventListener('resize', handleResize);
    return () => viewport.removeEventListener('resize', handleResize);
  }, []);

  return keyboardHeight;
}

// ============ 性能优化 ============

/**
 * 页面可见性优化 - 页面不可见时暂停更新
 */
export function usePageVisibility() {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const handleVisibilityChange = () => {
      setIsVisible(document.visibilityState === 'visible');
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  return isVisible;
}

/**
 * 网络状态检测
 */
export function useNetworkStatus() {
  const [status, setStatus] = useState<{
    online: boolean;
    effectiveType: string;
    saveData: boolean;
  }>({
    online: true,
    effectiveType: '4g',
    saveData: false,
  });

  useEffect(() => {
    const updateStatus = () => {
      const connection = (navigator as any).connection;
      setStatus({
        online: navigator.onLine,
        effectiveType: connection?.effectiveType || '4g',
        saveData: connection?.saveData || false,
      });
    };

    updateStatus();
    window.addEventListener('online', updateStatus);
    window.addEventListener('offline', updateStatus);

    const connection = (navigator as any).connection;
    if (connection) {
      connection.addEventListener('change', updateStatus);
    }

    return () => {
      window.removeEventListener('online', updateStatus);
      window.removeEventListener('offline', updateStatus);
      if (connection) {
        connection.removeEventListener('change', updateStatus);
      }
    };
  }, []);

  return status;
}

/**
 * 电池状态检测（用于降低动画等耗电操作）
 */
export function useBatteryStatus() {
  const [battery, setBattery] = useState<{
    level: number;
    charging: boolean;
    lowPower: boolean;
  }>({
    level: 1,
    charging: true,
    lowPower: false,
  });

  useEffect(() => {
    if (!('getBattery' in navigator)) return;

    (navigator as any).getBattery().then((bat: any) => {
      const updateBattery = () => {
        setBattery({
          level: bat.level,
          charging: bat.charging,
          lowPower: bat.level < 0.2 && !bat.charging,
        });
      };

      updateBattery();
      bat.addEventListener('levelchange', updateBattery);
      bat.addEventListener('chargingchange', updateBattery);

      return () => {
        bat.removeEventListener('levelchange', updateBattery);
        bat.removeEventListener('chargingchange', updateBattery);
      };
    });
  }, []);

  return battery;
}

// ============ 滚动优化 ============

/**
 * 惯性滚动优化
 */
export function useMomentumScroll(ref: React.RefObject<HTMLElement>) {
  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    // 启用 iOS 惯性滚动
    (element.style as any).webkitOverflowScrolling = 'touch';
    element.style.overscrollBehavior = 'contain';
  }, [ref]);
}

/**
 * 下拉刷新
 */
export function usePullToRefresh(onRefresh: () => Promise<void>, threshold = 80) {
  const [isPulling, setIsPulling] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const startYRef = useRef(0);

  const handleTouchStart = useCallback((e: TouchEvent) => {
    if (window.scrollY === 0) {
      startYRef.current = e.touches[0].clientY;
      setIsPulling(true);
    }
  }, []);

  const handleTouchMove = useCallback((e: TouchEvent) => {
    if (!isPulling) return;
    const currentY = e.touches[0].clientY;
    const diff = currentY - startYRef.current;
    if (diff > 0) {
      setPullDistance(Math.min(diff * 0.5, threshold * 1.5));
    }
  }, [isPulling, threshold]);

  const handleTouchEnd = useCallback(async () => {
    if (pullDistance >= threshold && !isRefreshing) {
      setIsRefreshing(true);
      try {
        await onRefresh();
      } finally {
        setIsRefreshing(false);
      }
    }
    setIsPulling(false);
    setPullDistance(0);
  }, [pullDistance, threshold, isRefreshing, onRefresh]);

  useEffect(() => {
    document.addEventListener('touchstart', handleTouchStart, { passive: true });
    document.addEventListener('touchmove', handleTouchMove, { passive: true });
    document.addEventListener('touchend', handleTouchEnd, { passive: true });

    return () => {
      document.removeEventListener('touchstart', handleTouchStart);
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  }, [handleTouchStart, handleTouchMove, handleTouchEnd]);

  return { isPulling, pullDistance, isRefreshing };
}

// ============ 性能模式选择 ============

/**
 * 根据设备性能自动选择性能模式
 */
export function usePerformanceMode(): 'high' | 'medium' | 'low' {
  const [mode, setMode] = useState<'high' | 'medium' | 'low'>('high');

  useEffect(() => {
    const memory = (navigator as any).deviceMemory;
    const cores = navigator.hardwareConcurrency;
    const connection = (navigator as any).connection;
    
    // 根据设备配置选择性能模式
    if (memory && memory < 2 || cores && cores < 2) {
      setMode('low');
    } else if (
      (memory && memory < 4) || 
      (cores && cores < 4) ||
      (connection?.effectiveType === '2g' || connection?.effectiveType === 'slow-2g')
    ) {
      setMode('medium');
    } else {
      setMode('high');
    }
  }, []);

  return mode;
}
