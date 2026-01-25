import type { Metadata, Viewport } from 'next';
import './globals.css';

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  themeColor: '#020617',
  colorScheme: 'dark',
};

export const metadata: Metadata = {
  title: '证券数据研究工具 - 个人学习研究用',
  description: '个人学习研究用的证券数据分析工具，基于公开数据的技术指标计算与可视化，仅供学习交流，不构成任何投资建议',
  icons: {
    icon: '/favicon.svg?v=2',
  },
  formatDetection: {
    telephone: false,
  },
  other: {
    'mobile-web-app-capable': 'yes',
    'apple-mobile-web-app-capable': 'yes',
    'apple-mobile-web-app-status-bar-style': 'black-translucent',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className="dark" suppressHydrationWarning>
      <head>
        {/* DNS 预解析和预连接 */}
        <link rel="dns-prefetch" href="//127.0.0.1:8000" />
        <link rel="preconnect" href="http://127.0.0.1:8000" crossOrigin="anonymous" />
        
        {/* 关键资源预加载提示 */}
        <meta httpEquiv="x-dns-prefetch-control" content="on" />
        
        {/* 性能优化 meta */}
        <meta name="renderer" content="webkit" />
        <meta name="force-rendering" content="webkit" />
      </head>
      <body className="bg-obsidian min-h-screen antialiased render-instant">
        {/* 简化背景效果 - 使用 CSS 变量减少重绘 */}
        <div className="fixed inset-0 bg-grid pointer-events-none opacity-50" aria-hidden="true" />
        <div className="fixed inset-0 bg-gradient-radial from-electric-blue/5 via-transparent to-transparent pointer-events-none" aria-hidden="true" />
        
        {/* Main Content */}
        <main className="relative z-10">
          {children}
        </main>
      </body>
    </html>
  );
}
