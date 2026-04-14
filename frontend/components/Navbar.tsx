'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useTheme } from './ThemeProvider'

export default function Navbar() {
  const { dark, toggle } = useTheme()
  const path = usePathname()

  const navLink = (href: string, label: string) => (
    <Link
      href={href}
      className={`text-sm font-medium transition-colors ${
        path === href
          ? 'text-ink-900 dark:text-amber-400'
          : 'text-ink-500 dark:text-ink-400 hover:text-ink-900 dark:hover:text-ink-100'
      }`}
    >
      {label}
    </Link>
  )

  return (
    <nav className="sticky top-0 z-50 bg-ink-50/80 dark:bg-ink-950/80 backdrop-blur border-b border-ink-100 dark:border-ink-800">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">

        {/* Logo */}
        <Link href="/" className="font-display text-xl font-bold tracking-tight">
          Book<span className="text-amber-500">IQ</span>
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-6">
          {navLink('/', 'Library')}
          {navLink('/ask', 'Ask AI')}
          {navLink('/scrape', 'Scrape')}
        </div>

        {/* Dark mode toggle */}
        <button
          onClick={toggle}
          className="w-9 h-9 flex items-center justify-center rounded-lg border border-ink-200 dark:border-ink-700 hover:bg-ink-100 dark:hover:bg-ink-800 transition-colors text-ink-600 dark:text-ink-300"
          aria-label="Toggle theme"
        >
          {dark ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
              <path d="M8 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM8 0a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 0zm0 13a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-1 0v-2A.5.5 0 0 1 8 13zm8-5a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2a.5.5 0 0 1 .5.5zM3 8a.5.5 0 0 1-.5.5h-2a.5.5 0 0 1 0-1h2A.5.5 0 0 1 3 8z"/>
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
              <path d="M6 .278a.768.768 0 0 1 .08.858 7.208 7.208 0 0 0-.878 3.46c0 4.021 3.278 7.277 7.318 7.277.527 0 1.04-.055 1.533-.16a.787.787 0 0 1 .81.316.733.733 0 0 1-.031.893A8.349 8.349 0 0 1 8.344 16C3.734 16 0 12.286 0 7.71 0 4.266 2.114 1.312 5.124.06A.752.752 0 0 1 6 .278z"/>
            </svg>
          )}
        </button>
      </div>
    </nav>
  )
}
