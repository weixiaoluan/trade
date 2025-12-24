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
  
  // 客户端：使用当前访问的域名/IP + 后端端口
  const hostname = window.location.hostname;
  
  // 本地开发环境
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  
  // 生产环境：使用相同的域名/IP，端口8000
  return `http://${hostname}:8000`;
}

export const API_BASE = getApiBase();
