import type { Metadata } from 'next'
import { Playfair_Display, Source_Sans_3, JetBrains_Mono } from 'next/font/google'
import './globals.css'
import { ThemeProvider } from '@/components/ThemeProvider'
import Navbar from '@/components/Navbar'

const display = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
})
const body = Source_Sans_3({
  subsets: ['latin'],
  variable: '--font-body',
  weight: ['300', '400', '600'],
  display: 'swap',
})
const mono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  weight: ['400'],
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'BookIQ — Intelligent Book Discovery',
  description: 'AI-powered book discovery and Q&A platform',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${display.variable} ${body.variable} ${mono.variable} font-body bg-ink-50 dark:bg-ink-950 text-ink-900 dark:text-ink-100 antialiased transition-colors duration-300`}>
        <ThemeProvider>
          <Navbar />
          <main className="min-h-screen">
            {children}
          </main>
        </ThemeProvider>
      </body>
    </html>
  )
}
