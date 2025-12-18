import type { Metadata, Viewport } from 'next';
import './globals.css';

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  themeColor: '#020617',
};

export const metadata: Metadata = {
  title: '证券AI智能分析引擎',
  description: '基于 Multi-Agent AI 的量化分析系统，覆盖全球股票、ETF、基金',
  icons: {
    icon: '/favicon.svg?v=2',
  },
  formatDetection: {
    telephone: false,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className="dark">
      <body className="bg-obsidian min-h-screen antialiased">
        {/* Background Effects */}
        <div className="fixed inset-0 bg-grid pointer-events-none" />
        <div className="fixed inset-0 bg-gradient-radial from-electric-blue/5 via-transparent to-transparent pointer-events-none" />
        <div className="fixed inset-0 noise pointer-events-none" />
        
        {/* Main Content */}
        <div className="relative z-10">
          {children}
        </div>
      </body>
    </html>
  );
}
