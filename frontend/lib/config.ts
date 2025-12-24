// API 配置
// 动态获取 API 地址，支持手机和电脑访问

function getApiBase(): string {
  // 如果设置了环境变量，优先使用
  if (process.env.NEXT_PUBLIC_API_BASE) {
    return process.env.NEXT_PUBLIC_API_BASE;
  }
  
  // 服务端渲染时使用 Docker 内部地址
  if (typeof window === 'undefined') {
    return 'http://backend:8000';
  }
  
  // 客户端：根据访问地址决定 API 地址
  const hostname = window.location.hostname;
  const protocol = window.location.protocol;
  
  // 本地开发环境
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  
  // 生产环境：使用 Nginx 反向代理，API 路径为 /api
  // 不暴露内部端口，所有请求通过同一域名
  return `${protocol}//${hostname}`;
}

export const API_BASE = getApiBase();
