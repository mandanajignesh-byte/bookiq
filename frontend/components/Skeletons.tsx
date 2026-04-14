export function BookCardSkeleton() {
  return (
    <div className="card overflow-hidden">
      <div className="aspect-[2/3] skeleton" />
      <div className="p-3 space-y-2">
        <div className="h-4 skeleton rounded w-4/5" />
        <div className="h-3 skeleton rounded w-2/3" />
        <div className="h-3 skeleton rounded w-1/2" />
        <div className="h-5 skeleton rounded w-1/3" />
      </div>
    </div>
  )
}

export function DetailSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-8 skeleton rounded w-2/3" />
      <div className="h-4 skeleton rounded w-1/3" />
      <div className="space-y-2">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-4 skeleton rounded" />
        ))}
      </div>
    </div>
  )
}
