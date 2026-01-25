/**
 * API缓存和数据获取优化工具
 * 提供请求去重、缓存、预加载、并发控制等功能
 */

interface CacheItem<T> {
  data: T;
  timestamp: number;
  expiresAt: number;
}

interface PendingRequest {
  promise: Promise<any>;
  timestamp: number;
}

// 请求队列管理
interface QueuedRequest {
  url: string;
  options: RequestInit;
  resolve: (value: any) => void;
  reject: (error: any) => void;
}

class RequestQueue {
  private queue: QueuedRequest[] = [];
  private processing = 0;
  private maxConcurrent: number;

  constructor(maxConcurrent = 6) {
    this.maxConcurrent = maxConcurrent;
  }

  async add<T>(url: string, options: RequestInit): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push({ url, options, resolve, reject });
      this.process();
    });
  }

  private async process() {
    if (this.processing >= this.maxConcurrent || this.queue.length === 0) return;

    this.processing++;
    const request = this.queue.shift()!;

    try {
      const response = await fetch(request.url, request.options);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      request.resolve(data);
    } catch (error) {
      request.reject(error);
    } finally {
      this.processing--;
      this.process();
    }
  }
}

// 全局请求队列
const requestQueue = new RequestQueue(6);

class ApiCache {
  private cache: Map<string, CacheItem<any>> = new Map();
  private pendingRequests: Map<string, PendingRequest> = new Map();
  private defaultTTL = 30000; // 默认缓存30秒
  private maxCacheSize = 100; // 最大缓存条目数

  // 获取缓存数据
  get<T>(key: string): T | null {
    const item = this.cache.get(key);
    if (!item) return null;
    if (Date.now() > item.expiresAt) {
      this.cache.delete(key);
      return null;
    }
    return item.data as T;
  }

  // 设置缓存
  set<T>(key: string, data: T, ttl: number = this.defaultTTL): void {
    // LRU 清理：如果缓存满了，删除最早的条目
    if (this.cache.size >= this.maxCacheSize) {
      const oldestKey = this.cache.keys().next().value;
      if (oldestKey) this.cache.delete(oldestKey);
    }
    
    const now = Date.now();
    this.cache.set(key, {
      data,
      timestamp: now,
      expiresAt: now + ttl,
    });
  }

  // 删除缓存
  delete(key: string): void {
    this.cache.delete(key);
  }

  // 清空所有缓存
  clear(): void {
    this.cache.clear();
  }

  // 带去重的fetch请求
  async fetchWithDedup<T>(
    key: string,
    fetcher: () => Promise<T>,
    options: { ttl?: number; forceRefresh?: boolean } = {}
  ): Promise<T> {
    const { ttl = this.defaultTTL, forceRefresh = false } = options;

    // 检查缓存
    if (!forceRefresh) {
      const cached = this.get<T>(key);
      if (cached !== null) {
        return cached;
      }
    }

    // 检查是否有pending请求
    const pending = this.pendingRequests.get(key);
    if (pending) {
      return pending.promise;
    }

    // 创建新请求
    const promise = fetcher()
      .then((data) => {
        this.set(key, data, ttl);
        this.pendingRequests.delete(key);
        return data;
      })
      .catch((error) => {
        this.pendingRequests.delete(key);
        throw error;
      });

    this.pendingRequests.set(key, { promise, timestamp: Date.now() });
    return promise;
  }
}

// 单例实例
export const apiCache = new ApiCache();

// 优化的fetch函数
export async function cachedFetch<T>(
  url: string,
  options: RequestInit & { ttl?: number; forceRefresh?: boolean } = {}
): Promise<T> {
  const { ttl, forceRefresh, ...fetchOptions } = options;
  const cacheKey = `${url}:${JSON.stringify(fetchOptions)}`;

  return apiCache.fetchWithDedup<T>(
    cacheKey,
    async () => {
      const response = await fetch(url, fetchOptions);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return response.json();
    },
    { ttl, forceRefresh }
  );
}

// 批量预加载 - 优化版：使用空闲时间加载
export function preloadApis(
  urls: string[],
  token: string,
  ttl: number = 30000
): void {
  // 使用 requestIdleCallback 在空闲时加载
  const preload = () => {
    urls.forEach((url) => {
      cachedFetch(url, {
        headers: { Authorization: `Bearer ${token}` },
        ttl,
      }).catch(() => {}); // 静默失败
    });
  };
  
  if ('requestIdleCallback' in window) {
    (window as any).requestIdleCallback(preload, { timeout: 2000 });
  } else {
    setTimeout(preload, 100);
  }
}

// 并发请求控制
export async function batchFetch<T>(
  urls: string[],
  options: RequestInit = {}
): Promise<Map<string, T>> {
  const results = new Map<string, T>();
  const promises = urls.map(async (url) => {
    try {
      const data = await requestQueue.add<T>(url, options);
      results.set(url, data);
    } catch (error) {
      console.error(`Batch fetch failed for ${url}:`, error);
    }
  });
  await Promise.all(promises);
  return results;
}

// 缓存统计信息
export function getCacheStats() {
  return {
    size: apiCache['cache'].size,
    pendingRequests: apiCache['pendingRequests'].size,
  };
}

// 清理过期缓存
export function cleanExpiredCache() {
  const now = Date.now();
  const cache = apiCache['cache'] as Map<string, CacheItem<any>>;
  Array.from(cache.entries()).forEach(([key, item]) => {
    if (now > item.expiresAt) {
      cache.delete(key);
    }
  });
}

// 判断是否为交易时间
export function isTradingTime(): boolean {
  const now = new Date();
  const day = now.getDay();
  if (day === 0 || day === 6) return false;
  const hours = now.getHours();
  const minutes = now.getMinutes();
  const time = hours * 60 + minutes;
  return (time >= 570 && time <= 690) || (time >= 780 && time <= 900);
}

// 获取轮询间隔
export function getPollingInterval(tradingInterval: number = 3000, idleInterval: number = 60000): number {
  return isTradingTime() ? tradingInterval : idleInterval;
}

// 智能轮询 - 根据页面可见性和网络状态调整
export function getSmartPollingInterval(
  baseInterval: number,
  options: {
    isPageVisible?: boolean;
    isSlowConnection?: boolean;
    isBatteryLow?: boolean;
  } = {}
): number {
  const { isPageVisible = true, isSlowConnection = false, isBatteryLow = false } = options;
  
  let interval = baseInterval;
  
  // 非交易时间，增加间隔
  if (!isTradingTime()) {
    interval = Math.max(interval, 60000);
  }
  
  // 页面不可见，大幅增加间隔
  if (!isPageVisible) {
    interval = Math.max(interval * 4, 120000);
  }
  
  // 慢速网络，增加间隔
  if (isSlowConnection) {
    interval = interval * 2;
  }
  
  // 低电量，增加间隔
  if (isBatteryLow) {
    interval = interval * 2;
  }
  
  return interval;
}

// 页面可见性检测
export function isPageVisible(): boolean {
  if (typeof document === 'undefined') return true;
  return document.visibilityState === 'visible';
}

// 网络连接检测
export function isSlowConnection(): boolean {
  if (typeof navigator === 'undefined') return false;
  const connection = (navigator as any).connection;
  if (!connection) return false;
  return connection.effectiveType === 'slow-2g' || 
         connection.effectiveType === '2g' || 
         connection.saveData === true;
}
