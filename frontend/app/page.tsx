'use client'
import { useEffect, useState, useCallback } from 'react'
import { fetchBooks, fetchGenres } from '@/lib/api'
import BookCard from '@/components/BookCard'
import { BookCardSkeleton } from '@/components/Skeletons'

const SORT_OPTIONS = [
  { value: '-created_at', label: 'Newest' },
  { value: 'rating',      label: 'Rating ↑' },
  { value: '-rating',     label: 'Rating ↓' },
  { value: 'title',       label: 'A–Z' },
  { value: 'price',       label: 'Price ↑' },
]

export default function HomePage() {
  const [books, setBooks]       = useState<any[]>([])
  const [genres, setGenres]     = useState<string[]>([])
  const [loading, setLoading]   = useState(true)
  const [search, setSearch]     = useState('')
  const [genre, setGenre]       = useState('')
  const [ordering, setOrdering] = useState('-created_at')
  const [page, setPage]         = useState(1)
  const [totalCount, setTotal]  = useState(0)
  const [debouncedSearch, setDebouncedSearch] = useState('')

  // Debounce search input
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 400)
    return () => clearTimeout(t)
  }, [search])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = { ordering, page: String(page) }
      if (debouncedSearch) params.search = debouncedSearch
      if (genre) params.genre = genre
      const data = await fetchBooks(params)
      setBooks(data.results ?? data)
      setTotal(data.count ?? (data.results ?? data).length)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [debouncedSearch, genre, ordering, page])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    fetchGenres().then(setGenres).catch(() => {})
  }, [])

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Hero */}
      <div className="mb-10">
        <h1 className="font-display text-4xl md:text-5xl font-bold mb-2">
          Discover Books<span className="text-amber-500">.</span>
        </h1>
        <p className="text-ink-500 dark:text-ink-400 text-lg">
          {totalCount} books · AI-powered insights and recommendations
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-8">
        <input
          type="text"
          placeholder="Search titles or authors…"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
          className="input max-w-xs"
        />

        <select
          value={genre}
          onChange={e => { setGenre(e.target.value); setPage(1) }}
          className="input max-w-[160px]"
        >
          <option value="">All genres</option>
          {genres.map(g => <option key={g} value={g}>{g}</option>)}
        </select>

        <select
          value={ordering}
          onChange={e => { setOrdering(e.target.value); setPage(1) }}
          className="input max-w-[140px]"
        >
          {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>

        {(search || genre) && (
          <button
            onClick={() => { setSearch(''); setGenre(''); setPage(1) }}
            className="btn-ghost"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {[...Array(12)].map((_, i) => <BookCardSkeleton key={i} />)}
        </div>
      ) : books.length === 0 ? (
        <div className="text-center py-24">
          <p className="font-display text-2xl text-ink-400 mb-4">No books found</p>
          <p className="text-ink-400">Try scraping some books first →{' '}
            <a href="/scrape" className="text-amber-500 hover:underline">Scrape page</a>
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {books.map(book => <BookCard key={book.id} book={book} />)}
        </div>
      )}

      {/* Pagination */}
      {totalCount > 20 && (
        <div className="flex items-center justify-center gap-3 mt-12">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-ghost"
          >← Prev</button>
          <span className="text-sm text-ink-500">
            Page {page} of {Math.ceil(totalCount / 20)}
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page >= Math.ceil(totalCount / 20)}
            className="btn-ghost"
          >Next →</button>
        </div>
      )}
    </div>
  )
}
