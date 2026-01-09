/** @type {import('next').NextConfig} */
const nextConfig = {
  // 启用 standalone 输出模式（优化 Docker 构建）
  output: 'standalone',
  
  // 启用生产优化
  reactStrictMode: false, // 关闭严格模式减少双重渲染
  swcMinify: true, // 使用SWC压缩
  
  // 优化图片
  images: {
    formats: ['image/avif', 'image/webp'],
  },
  
  // 编译优化
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production', // 生产环境移除console
  },
  
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
