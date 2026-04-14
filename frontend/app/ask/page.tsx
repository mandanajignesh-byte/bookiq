'use client'
import { useEffect, useRef, useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { v4 as uuidv4 } from 'uuid'
import { askQuestion, fetchChatHistory } from '@/lib/api'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{ book_id: number; title: string; excerpt: string; citation_number: number }>
  cached?: boolean
  loading?: boolean
}

const SAMPLE_QUESTIONS = [
  'What are some mystery books in the collection?',
  'Recommend books with positive reviews',
  'Which books are suitable for young adults?',
  'What romance novels are available?',
]

function AskPageInner() {
  const searchParams = useSearchParams()
  const bookIdParam = searchParams.get('book')

  const [sessionId] = useState(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('bookiq_session')
      if (stored) return stored
      const id = uuidv4()
      localStorage.setItem('bookiq_session', id)
      return id
    }
    return uuidv4()
  })

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput]       = useState('')
  const [loading, setLoading]   = useState(false)
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Load prior chat history
  useEffect(() => {
    fetchChatHistory(sessionId).then(history => {
      const restored: Message[] = []
      history.reverse().forEach((h: any) => {
        restored.push({ id: h.id + '_q', role: 'user', content: h.question })
        restored.push({ id: h.id + '_a', role: 'assistant', content: h.answer, sources: h.sources, cached: false })
      })
      setMessages(restored)
      setHistoryLoaded(true)
    }).catch(() => setHistoryLoaded(true))
  }, [sessionId])

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (question: string) => {
    if (!question.trim() || loading) return
    setInput('')
    setLoading(true)

    const userMsg: Message = { id: uuidv4(), role: 'user', content: question }
    const placeholder: Message = { id: uuidv4(), role: 'assistant', content: '', loading: true }
    setMessages(prev => [...prev, userMsg, placeholder])

    try {
      const res = await askQuestion({
        question,
        session_id: sessionId,
        book_id: bookIdParam ? Number(bookIdParam) : undefined,
      })
      setMessages(prev => prev.map(m =>
        m.loading ? { ...m, content: res.answer, sources: res.sources, cached: res.cached, loading: false } : m
      ))
    } catch {
      setMessages(prev => prev.map(m =>
        m.loading ? { ...m, content: 'Sorry, something went wrong. Please try again.', loading: false } : m
      ))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-8 flex flex-col" style={{ height: 'calc(100vh - 56px)' }}>
      <div className="mb-6 flex-shrink-0">
        <h1 className="font-display text-3xl font-bold mb-1">
          Ask AI<span className="text-amber-500">.</span>
        </h1>
        <p className="text-ink-500 dark:text-ink-400 text-sm">
          {bookIdParam
            ? 'Asking about a specific book. Remove ?book= from URL to search all books.'
            : 'Ask anything about books in the library. Powered by Claude + semantic search.'}
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {!historyLoaded && (
          <div className="text-center text-ink-400 text-sm py-8">Loading history…</div>
        )}

        {historyLoaded && messages.length === 0 && (
          <div className="py-8 space-y-4">
            <p className="text-ink-400 text-sm text-center">Try asking one of these:</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {SAMPLE_QUESTIONS.map(q => (
                <button
                  key={q}
                  onClick={() => send(q)}
                  className="text-left p-3 rounded-xl border border-ink-200 dark:border-ink-700 text-sm text-ink-600 dark:text-ink-400 hover:border-amber-400 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up`}
          >
            <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'bg-ink-900 dark:bg-amber-400 text-white dark:text-ink-950 rounded-br-sm'
                : 'bg-white dark:bg-ink-900 border border-ink-100 dark:border-ink-800 text-ink-800 dark:text-ink-200 rounded-bl-sm shadow-sm'
            }`}>
              {msg.loading ? (
                <div className="flex items-center gap-1.5">
                  {[0,1,2].map(i => (
                    <span key={i} className="w-2 h-2 rounded-full bg-ink-300 dark:bg-ink-600 animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }} />
                  ))}
                </div>
              ) : (
                <>
                  <p className="whitespace-pre-wrap">{msg.content}</p>

                  {/* Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-ink-100 dark:border-ink-800 space-y-1.5">
                      <p className="text-xs font-semibold text-ink-400 uppercase tracking-wide">Sources</p>
                      {msg.sources.map(s => (
                        <a key={s.book_id} href={`/books/${s.book_id}`}
                          className="block text-xs p-2 rounded-lg bg-ink-50 dark:bg-ink-800 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors">
                          <span className="font-semibold text-amber-600 dark:text-amber-400">[{s.citation_number}]</span>
                          {' '}<span className="font-medium">{s.title}</span>
                          <span className="text-ink-400 block mt-0.5 line-clamp-1">{s.excerpt}</span>
                        </a>
                      ))}
                    </div>
                  )}

                  {/* Cache indicator */}
                  {msg.cached !== undefined && msg.role === 'assistant' && (
                    <p className="text-xs text-ink-300 dark:text-ink-600 mt-2">
                      {msg.cached ? '⚡ cached response' : ''}
                    </p>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex-shrink-0 flex gap-3 pt-4 border-t border-ink-100 dark:border-ink-800">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send(input)}
          placeholder="Ask about books…"
          disabled={loading}
          className="input flex-1"
        />
        <button
          onClick={() => send(input)}
          disabled={loading || !input.trim()}
          className="btn-primary px-6"
        >
          {loading ? '…' : 'Ask'}
        </button>
      </div>
    </div>
  )
}

export default function AskPage() {
  return (
    <Suspense fallback={<div className="p-8 text-ink-400">Loading…</div>}>
      <AskPageInner />
    </Suspense>
  )
}
