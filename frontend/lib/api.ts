import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
const WS_BASE  = process.env.NEXT_PUBLIC_WS_URL  || 'ws://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

// ── Books ─────────────────────────────────────────────
export const fetchBooks = (params?: Record<string, string>) =>
  api.get('/books/', { params }).then(r => r.data)

export const fetchBook = (id: number) =>
  api.get(`/books/${id}/`).then(r => r.data)

export const fetchRecommendations = (id: number) =>
  api.get(`/books/${id}/recommendations/`).then(r => r.data)

export const fetchGenres = () =>
  api.get('/books/genres/').then(r => r.data)

export const fetchChatHistory = (sessionId: string) =>
  api.get(`/books/history/${sessionId}/`).then(r => r.data)

// ── RAG ──────────────────────────────────────────────
export const askQuestion = (payload: {
  question: string
  session_id: string
  book_id?: number
}) => api.post('/rag/ask/', payload).then(r => r.data)

// ── Scraper ───────────────────────────────────────────
export const startScrape = (maxBooks: number) =>
  api.post('/scraper/start/', { max_books: maxBooks }).then(r => r.data)

export const createScrapeSocket = (jobId: string): WebSocket =>
  new WebSocket(`${WS_BASE}/ws/scrape/${jobId}/`)
