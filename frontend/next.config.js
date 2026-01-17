/** @type {import('next').NextConfig} */
const nextConfig = {
  // 启用生产优化
  reactStrictMode: false,
  swcMinify: true,
  
  // 优化图片
  images: {
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 60 * 60 * 24, // 24小时缓存
  },
  
  // 编译优化
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  
  // 实验性优化
  experimental: {
    optimizeCss: true, // CSS优化
    optimizePackageImports: ['lucide-react', 'framer-motion', 'recharts'], // 按需导入优化
  },
  
  // 模块化导入优化
  modularizeImports: {
    'lucide-react': {
      transform: 'lucide-react/dist/esm/icons/{{kebabCase member}}',
    },
  },
  
  // 打包优化
  webpack: (config, { isServer }) => {
    // 生产环境优化
    if (!isServer) {
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          chunks: 'all',
          cacheGroups: {
            // 第三方库分离
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: 'vendors',
              chunks: 'all',
              priority: 10,
            },
            // 图表库单独分离（较大）
            recharts: {
              test: /[\\/]node_modules[\\/](recharts|d3-.*)[\\/]/,
              name: 'recharts',
              chunks: 'all',
              priority: 20,
            },
            // 动画库单独分离
            framer: {
              test: /[\\/]node_modules[\\/]framer-motion[\\/]/,
              name: 'framer',
              chunks: 'all',
              priority: 20,
            },
          },
        },
      };
    }
    return config;
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
