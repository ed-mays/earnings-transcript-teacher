/** Renders a ranked list of keyword chips. */

interface KeywordListProps {
  keywords: string[];
}

export function KeywordList({ keywords }: KeywordListProps) {
  if (keywords.length === 0) {
    return <p className="text-sm text-zinc-400">No keywords extracted.</p>;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {keywords.map((kw, i) => (
        <span
          key={i}
          className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-700"
        >
          {kw}
        </span>
      ))}
    </div>
  );
}
