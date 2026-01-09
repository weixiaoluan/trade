/** @type {import('next').NextConfig} */
const nextConfig = {
  // 启用生产优化
  reactStrictMode: false,
  swcMinify: true,
  
  // 优化图片
  images: {
    formats: ['image/avif', 'image/webp'],
  },
  
  // 编译优化
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
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
