'use client'
import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { fetchBook } from '@/lib/api'
import { DetailSkeleton } from '@/components/Skeletons'

const SENTIMENT_PILL: Record<string, string> = {
  positive: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  neutral:  'bg-ink-100 text-ink-700 dark:bg-ink-800 dark:text-ink-300',
  negative: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
}

function StatBlock({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="text-center p-3 bg-ink-50 dark:bg-ink-800/50 rounded-xl">
      <div className="font-display font-bold text-lg text-ink-900 dark:text-ink-100">{value}</div>
      <div className="text-xs text-ink-500 mt-0.5">{label}</div>
    </div>
  )
}

export default function BookDetailPage() {
  const { id } = useParams()
  const router = useRouter()
  const [book, setBook] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchBook(Number(id))
      .then(setBook)
      .catch(() => router.push('/'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return (
    <div className="max-w-4xl mx-auto px-6 py-12"><DetailSkeleton /></div>
  )
  if (!book) return null

  const genre = book.ai_genre || book.genre || 'General'
  const sentiment = book.ai_sentiment || 'neutral'

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 animate-fade-in">
      {/* Back */}
      <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-ink-400 hover:text-ink-700 dark:hover:text-ink-200 mb-8 transition-colors">
        ← Back to Library
      </Link>

      <div className="grid md:grid-cols-[220px_1fr] gap-10">
        {/* Cover */}
        <div className="space-y-4">
          <div className="rounded-2xl overflow-hidden shadow-lg aspect-[2/3] bg-ink-100 dark:bg-ink-800">
            {book.cover_image_url ? (
              <img src={book.cover_image_url} alt={book.title} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <span className="font-display text-6xl text-ink-300 dark:text-ink-600">{book.title[0]}</span>
              </div>
            )}
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-2">
            {book.rating && <StatBlock label="Rating" value={`${book.rating} ★`} />}
            {book.price   && <StatBlock label="Price"  value={`£${book.price}`} />}
          </div>

          <a href={book.book_url} target="_blank" rel="noopener noreferrer" className="btn-primary w-full text-center block">
            View on Store ↗
          </a>

          <Link href={`/ask?book=${book.id}`} className="btn-ghost w-full text-center block">
            Ask AI about this book
          </Link>
        </div>

        {/* Details */}
        <div className="space-y-6">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="badge bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                {genre}
              </span>
              {book.ai_insights_generated && (
                <span className={`badge ${SENTIMENT_PILL[sentiment]}`}>
                  {sentiment} tone
                </span>
              )}
            </div>
            <h1 className="font-display text-3xl md:text-4xl font-bold leading-tight mb-1">
              {book.title}
            </h1>
            <p className="text-ink-500 dark:text-ink-400 text-lg">by {book.author || 'Unknown'}</p>
          </div>

          {/* AI Summary */}
          {book.ai_summary && (
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-100 dark:border-amber-800/40 rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-amber-500 font-semibold text-sm">✦ AI Summary</span>
              </div>
              <p className="text-ink-700 dark:text-ink-300 leading-relaxed text-sm">{book.ai_summary}</p>
            </div>
          )}

          {/* Description */}
          {book.description && (
            <div>
              <h2 className="font-display font-bold text-lg mb-2">Description</h2>
              <p className="text-ink-600 dark:text-ink-400 leading-relaxed text-sm">{book.description}</p>
            </div>
          )}

          {/* Meta */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm border-t border-ink-100 dark:border-ink-800 pt-4">
            {book.availability && (
              <>
                <span className="text-ink-400">Availability</span>
                <span className="text-ink-700 dark:text-ink-300">{book.availability}</span>
              </>
            )}
            {book.upc && (
              <>
                <span className="text-ink-400">UPC</span>
                <span className="font-mono text-xs text-ink-600 dark:text-ink-400">{book.upc}</span>
              </>
            )}
          </div>

          {/* Recommendations */}
          {book.recommendations?.length > 0 && (
            <div>
              <h2 className="font-display font-bold text-lg mb-3">
                If you like this, try…
              </h2>
              <div className="flex gap-3 overflow-x-auto pb-1">
                {book.recommendations.map((rec: any) => (
                  <Link key={rec.id} href={`/books/${rec.id}`} className="flex-shrink-0 w-24 group">
                    <div className="rounded-xl overflow-hidden aspect-[2/3] bg-ink-100 dark:bg-ink-800 mb-1.5">
                      {rec.cover_image_url ? (
                        <img src={rec.cover_image_url} alt={rec.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <span className="font-display text-2xl text-ink-300">{rec.title[0]}</span>
                        </div>
                      )}
                    </div>
                    <p className="text-xs font-medium line-clamp-2 leading-tight group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors">
                      {rec.title}
                    </p>
                    <p className="text-xs text-ink-400 mt-0.5">{Math.round(rec.similarity_score * 100)}% match</p>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
