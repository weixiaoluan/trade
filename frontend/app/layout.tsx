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
  title: 'AI Securities Analyzer | 全能证券分析引擎',
  description: '基于 AutoGen + DeepSeek-R1 的多智能体证券分析系统',
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
