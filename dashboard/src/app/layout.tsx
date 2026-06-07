import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Sidebar from '@/components/Sidebar';

const inter = Inter({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700', '800', '900'],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'TokenSaver Enterprise — LLM Cost Intelligence',
  description: 'Real-time analytics dashboard for LLM cost savings, cache analytics, and intelligent model routing.',
  keywords: ['LLM', 'cost savings', 'AI', 'analytics', 'token optimization'],
  authors: [{ name: 'TokenSaver' }],
  themeColor: '#0A0A0F',
  viewport: 'width=device-width, initial-scale=1',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        <div className="layout">
          <Sidebar />
          <main className="main-content">
            <div className="page-content">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
