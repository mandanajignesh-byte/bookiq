import Link from 'next/link'

interface BookCardProps {
  book: {
    id: number
    title: string
    author: string
    rating: number | null
    genre: string
    ai_genre: string
    price: string | null
    cover_image_url: string
    ai_insights_generated: boolean
    ai_sentiment?: string
  }
}

const SENTIMENT_COLORS: Record<string, string> = {
  positive: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  neutral:  'bg-ink-100 text-ink-600 dark:bg-ink-800 dark:text-ink-400',
  negative: 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400',
}

function StarRating({ rating }: { rating: number | null }) {
  if (!rating) return null
  const full = Math.floor(rating)
  return (
    <div className="flex items-center gap-1">
      {[1,2,3,4,5].map(i => (
        <svg key={i} width="12" height="12" viewBox="0 0 12 12"
          className={i <= full ? 'text-amber-400' : 'text-ink-200 dark:text-ink-700'}
          fill="currentColor"
        >
          <path d="M6 1l1.39 2.82L10.5 4.27l-2.25 2.19.53 3.1L6 8.02l-2.78 1.54.53-3.1L1.5 4.27l3.11-.45z"/>
        </svg>
      ))}
      <span className="text-xs text-ink-500 ml-0.5">{rating.toFixed(1)}</span>
    </div>
  )
}

export default function BookCard({ book }: BookCardProps) {
  const displayGenre = book.ai_genre || book.genre || 'General'
  const sentiment = book.ai_sentiment || 'neutral'

  return (
    <Link href={`/books/${book.id}`}>
      <div className="card group cursor-pointer overflow-hidden animate-fade-in">
        {/* Cover image */}
        <div className="relative aspect-[2/3] bg-ink-100 dark:bg-ink-800 overflow-hidden">
          {book.cover_image_url ? (
            <img
              src={book.cover_image_url}
              alt={book.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <span className="font-display text-4xl text-ink-300 dark:text-ink-700">
                {book.title[0]}
              </span>
            </div>
          )}
          {/* AI badge */}
          {book.ai_insights_generated && (
            <div className="absolute top-2 right-2 bg-amber-400 text-ink-950 text-xs font-semibold px-1.5 py-0.5 rounded-md">
              AI✦
            </div>
          )}
        </div>

        {/* Info */}
        <div className="p-3 space-y-1.5">
          <h3 className="font-display font-bold text-sm leading-tight line-clamp-2 group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors">
            {book.title}
          </h3>
          <p className="text-xs text-ink-500 dark:text-ink-400 truncate">{book.author}</p>

          <StarRating rating={book.rating} />

          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="badge bg-ink-100 dark:bg-ink-800 text-ink-600 dark:text-ink-400">
              {displayGenre}
            </span>
            {book.ai_insights_generated && (
              <span className={`badge ${SENTIMENT_COLORS[sentiment]}`}>
                {sentiment}
              </span>
            )}
          </div>

          {book.price && (
            <p className="text-xs font-semibold text-ink-700 dark:text-ink-300">£{book.price}</p>
          )}
        </div>
      </div>
    </Link>
  )
}
