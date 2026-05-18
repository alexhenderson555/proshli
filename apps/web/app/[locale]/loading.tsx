// Top-level loading UI shown during route transitions. Next.js streams
// this in instead of blocking on the server component tree, so the user
// always sees something within ~100ms.

export default function Loading() {
  return (
    <div className="flex flex-col gap-6 py-16">
      <div className="h-8 w-64 animate-pulse rounded-lg bg-muted" />
      <div className="h-4 w-96 max-w-full animate-pulse rounded bg-muted" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="panel flex animate-pulse flex-col gap-3 p-5"
            aria-hidden="true"
          >
            <div className="h-5 w-3/4 rounded bg-muted" />
            <div className="h-3 w-1/2 rounded bg-muted" />
            <div className="h-3 w-full rounded bg-muted" />
            <div className="h-3 w-5/6 rounded bg-muted" />
          </div>
        ))}
      </div>
    </div>
  );
}
