'use client'
import { useState, useRef, useEffect } from 'react'
import { startScrape, createScrapeSocket } from '@/lib/api'
import Link from 'next/link'

interface ProgressEvent {
  current: number
  total: number
  percent: number
  message: string
  status: 'running' | 'saving' | 'done' | 'error'
}

interface LogEntry {
  time: string
  message: string
  status: ProgressEvent['status']
}

const STATUS_COLORS: Record<string, string> = {
  running: 'text-blue-500',
  saving:  'text-amber-500',
  done:    'text-emerald-500',
  error:   'text-red-500',
}

const STATUS_BG: Record<string, string> = {
  running: 'bg-blue-500',
  saving:  'bg-amber-500',
  done:    'bg-emerald-500',
  error:   'bg-red-500',
}

export default function ScrapePage() {
  const [maxBooks, setMaxBooks]     = useState(50)
  const [progress, setProgress]     = useState<ProgressEvent | null>(null)
  const [log, setLog]               = useState<LogEntry[]>([])
  const [running, setRunning]       = useState(false)
  const [jobId, setJobId]           = useState<string | null>(null)
  const wsRef                       = useRef<WebSocket | null>(null)
  const logRef                      = useRef<HTMLDivElement>(null)

  // Auto-scroll log
  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [log])

  // Cleanup WS on unmount
  useEffect(() => () => { wsRef.current?.close() }, [])

  const addLog = (msg: string, status: ProgressEvent['status']) => {
    const time = new Date().toLocaleTimeString()
    setLog(prev => [...prev, { time, message: msg, status }])
  }

  const handleStart = async () => {
    if (running) return
    setRunning(true)
    setProgress(null)
    setLog([])

    try {
      const res = await startScrape(maxBooks)
      const id: string = res.job_id
      setJobId(id)
      addLog(`Job started (ID: ${id.slice(0, 8)}…). Connecting to live feed…`, 'running')

      // Open WebSocket for live updates
      const ws = createScrapeSocket(id)
      wsRef.current = ws

      ws.onmessage = (e) => {
        const evt: ProgressEvent = JSON.parse(e.data)
        setProgress(evt)
        addLog(evt.message, evt.status)

        if (evt.status === 'done' || evt.status === 'error') {
          setRunning(false)
          ws.close()
        }
      }

      ws.onerror = () => {
        addLog('WebSocket error — check if Daphne is running.', 'error')
        setRunning(false)
      }

      ws.onclose = () => {
        if (running) addLog('Connection closed.', 'running')
      }

    } catch (err: any) {
      addLog(`Failed to start scrape: ${err.message}`, 'error')
      setRunning(false)
    }
  }

  const isDone  = progress?.status === 'done'
  const isError = progress?.status === 'error'

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold mb-1">
          Scrape Books<span className="text-amber-500">.</span>
        </h1>
        <p className="text-ink-500 dark:text-ink-400 text-sm">
          Scrapes <a href="https://books.toscrape.com" target="_blank" rel="noopener noreferrer"
            className="text-amber-500 hover:underline">books.toscrape.com</a> and enriches with Open Library data.
          AI insights are generated automatically in the background.
        </p>
      </div>

      {/* Config card */}
      <div className="card p-6 mb-6">
        <label className="block text-sm font-semibold text-ink-700 dark:text-ink-300 mb-2">
          Number of books to scrape
        </label>
        <div className="flex items-center gap-4 mb-1">
          <input
            type="range"
            min={10} max={200} step={10}
            value={maxBooks}
            onChange={e => setMaxBooks(Number(e.target.value))}
            disabled={running}
            className="flex-1 accent-amber-500"
          />
          <span className="font-mono text-lg font-bold text-ink-900 dark:text-ink-100 w-12 text-right">
            {maxBooks}
          </span>
        </div>
        <p className="text-xs text-ink-400 mb-5">
          ~{Math.round(maxBooks * 0.4)}s estimated · includes Open Library enrichment
        </p>

        <button
          onClick={handleStart}
          disabled={running}
          className="btn-primary w-full flex items-center justify-center gap-2 py-3"
        >
          {running ? (
            <>
              <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              Scraping in progress…
            </>
          ) : isDone ? (
            '✓ Done — Scrape again'
          ) : (
            `Start scraping ${maxBooks} books`
          )}
        </button>
      </div>

      {/* Progress section */}
      {progress && (
        <div className="card p-6 mb-6 animate-fade-in">
          {/* Status pill */}
          <div className="flex items-center justify-between mb-4">
            <span className={`badge px-3 py-1 text-xs font-semibold uppercase tracking-wide
              ${isDone  ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300' :
                isError ? 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300' :
                          'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'}`}>
              {progress.status}
            </span>
            <span className="font-mono text-sm text-ink-500">
              {progress.current} / {progress.total || '?'}
            </span>
          </div>

          {/* Progress bar */}
          <div className="h-2 rounded-full bg-ink-100 dark:bg-ink-800 overflow-hidden mb-3">
            <div
              className={`h-full rounded-full transition-all duration-500 ${STATUS_BG[progress.status]}`}
              style={{ width: `${progress.percent || 0}%` }}
            />
          </div>

          <p className="text-sm text-ink-600 dark:text-ink-400 truncate">{progress.message}</p>

          {/* Done CTA */}
          {isDone && (
            <div className="mt-4 flex gap-3">
              <Link href="/" className="btn-primary text-sm">
                View Library →
              </Link>
              <Link href="/ask" className="btn-ghost text-sm">
                Ask AI
              </Link>
            </div>
          )}
        </div>
      )}

      {/* Live log */}
      {log.length > 0 && (
        <div className="card overflow-hidden animate-fade-in">
          <div className="px-4 py-2.5 border-b border-ink-100 dark:border-ink-800 flex items-center justify-between">
            <span className="text-xs font-semibold text-ink-500 uppercase tracking-wide">Live log</span>
            <button
              onClick={() => setLog([])}
              className="text-xs text-ink-400 hover:text-ink-600 dark:hover:text-ink-200 transition-colors"
            >
              Clear
            </button>
          </div>
          <div
            ref={logRef}
            className="font-mono text-xs p-4 space-y-1 max-h-64 overflow-y-auto bg-ink-950/5 dark:bg-ink-950/40"
          >
            {log.map((entry, i) => (
              <div key={i} className="flex gap-3">
                <span className="text-ink-400 flex-shrink-0">{entry.time}</span>
                <span className={STATUS_COLORS[entry.status]}>{entry.message}</span>
              </div>
            ))}
            {running && (
              <div className="flex gap-2 items-center text-ink-400">
                <span className="animate-pulse">▌</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Info cards */}
      <div className="grid grid-cols-3 gap-4 mt-8">
        {[
          { icon: '🔍', title: 'Smart scrape', desc: 'Requests + BeautifulSoup with polite crawl delays' },
          { icon: '✦',  title: 'AI insights',  desc: 'Claude generates summary, genre & sentiment per book' },
          { icon: '⚡', title: 'Async pipeline', desc: 'Celery tasks + WebSocket progress, cached embeddings' },
        ].map(item => (
          <div key={item.title} className="card p-4 text-center">
            <div className="text-2xl mb-1">{item.icon}</div>
            <div className="font-semibold text-xs text-ink-700 dark:text-ink-300 mb-1">{item.title}</div>
            <div className="text-xs text-ink-400 leading-snug">{item.desc}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
