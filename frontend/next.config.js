/** @type {import('next').NextConfig} */
const nextConfig = {
  // 启用生产优化
  reactStrictMode: false,
  swcMinify: true,
  
  // 禁用powered by header
  poweredByHeader: false,
  
  // 压缩
  compress: true,
  
  // 生产构建优化
  productionBrowserSourceMaps: false,
  
  // 优化图片
  images: {
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 60 * 60 * 24 * 30, // 30天缓存
    deviceSizes: [640, 750, 828, 1080, 1200],
    imageSizes: [16, 32, 48, 64, 96],
    unoptimized: false,
  },
  
  // 编译优化
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
    // 移除 framer-motion 的调试代码
    ...(process.env.NODE_ENV === 'production' && {
      reactRemoveProperties: { properties: ['^data-framer'] },
    }),
  },
  
  // 实验性优化
  experimental: {
    optimizePackageImports: [
      'lucide-react', 
      'framer-motion', 
      'recharts', 
      '@radix-ui/react-accordion', 
      '@radix-ui/react-tabs',
      '@radix-ui/react-progress',
      '@radix-ui/react-slot',
      'clsx',
      'tailwind-merge',
    ],
    // CSS 优化 (需要 critters 包，Docker 环境下禁用)
    // optimizeCss: true,
  },
  
  // 模块化导入优化
  modularizeImports: {
    'lucide-react': {
      transform: 'lucide-react/dist/esm/icons/{{kebabCase member}}',
    },
  },
  
  // 打包优化
  webpack: (config, { isServer, dev }) => {
    // 生产环境优化
    if (!dev) {
      config.devtool = false;
    }
    
    if (!isServer) {
      // 别名优化 - 使用轻量级替代品
      config.resolve.alias = {
        ...config.resolve.alias,
        // 使用 preact 兼容层（可选，如需更极致性能可启用）
        // 'react': 'preact/compat',
        // 'react-dom': 'preact/compat',
      };
      
      config.optimization = {
        ...config.optimization,
        moduleIds: 'deterministic',
        runtimeChunk: 'single',
        splitChunks: {
          chunks: 'all',
          minSize: 15000,
          maxSize: 200000,
          minChunks: 1,
          maxAsyncRequests: 30,
          maxInitialRequests: 25,
          cacheGroups: {
            default: false,
            vendors: false,
            // React 框架核心 - 最高优先级
            framework: {
              test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/,
              name: 'framework',
              chunks: 'all',
              priority: 50,
              enforce: true,
            },
            // 图表库（懒加载）
            recharts: {
              test: /[\\/]node_modules[\\/](recharts|d3-.*)[\\/]/,
              name: 'recharts',
              chunks: 'async',
              priority: 40,
              reuseExistingChunk: true,
            },
            // 动画库（懒加载）
            framer: {
              test: /[\\/]node_modules[\\/]framer-motion[\\/]/,
              name: 'framer',
              chunks: 'async',
              priority: 40,
              reuseExistingChunk: true,
            },
            // Radix UI 组件
            radix: {
              test: /[\\/]node_modules[\\/]@radix-ui[\\/]/,
              name: 'radix',
              chunks: 'async',
              priority: 35,
            },
            // Lucide 图标
            icons: {
              test: /[\\/]node_modules[\\/]lucide-react[\\/]/,
              name: 'icons',
              chunks: 'all',
              priority: 30,
            },
            // 其他第三方库
            lib: {
              test: /[\\/]node_modules[\\/]/,
              name: 'lib',
              chunks: 'all',
              priority: 20,
              minChunks: 2,
            },
            // 公共模块
            commons: {
              name: 'commons',
              minChunks: 2,
              priority: 10,
              reuseExistingChunk: true,
            },
          },
        },
      };
    }
    return config;
  },
  
  // HTTP headers优化
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-DNS-Prefetch-Control', value: 'on' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
          // 预连接到 API 服务器
          { key: 'Link', value: '<http://127.0.0.1:8000>; rel=preconnect' },
        ],
      },
      {
        source: '/static/:path*',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
      {
        // JS/CSS 文件长期缓存
        source: '/_next/static/:path*',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
      {
        // 字体文件缓存
        source: '/fonts/:path*',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
    ];
  },
  
  async rewrites() {
    // Docker 环境使用内部服务名，本地开发使用 localhost
    const apiHost = process.env.NODE_ENV === 'production' 
      ? 'http://backend:8000' 
      : 'http://127.0.0.1:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${apiHost}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
