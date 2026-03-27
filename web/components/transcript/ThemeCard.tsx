/** Renders a topic cluster as a card with a label and term chips. */

interface ThemeCardProps {
  /** The leading term used as the card label. */
  label: string;
  /** All terms in the topic cluster. */
  terms: string[];
}

export function ThemeCard({ label, terms }: ThemeCardProps) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4">
      <p className="mb-2 text-sm font-semibold text-zinc-800">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {terms.map((term, i) => (
          <span
            key={i}
            className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs text-blue-700"
          >
            {term}
          </span>
        ))}
      </div>
    </div>
  );
}
