/**
 * API缓存和数据获取优化工具
 * 提供请求去重、缓存、预加载等功能
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

class ApiCache {
  private cache: Map<string, CacheItem<any>> = new Map();
  private pendingRequests: Map<string, PendingRequest> = new Map();
  private defaultTTL = 30000; // 默认缓存30秒

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

// 批量预加载
export function preloadApis(
  urls: string[],
  token: string,
  ttl: number = 30000
): void {
  urls.forEach((url) => {
    cachedFetch(url, {
      headers: { Authorization: `Bearer ${token}` },
      ttl,
    }).catch(() => {}); // 静默失败
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
