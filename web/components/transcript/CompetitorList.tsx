/** Renders a split list of competitors: mentioned in call vs. other. */

import type { Competitor } from "./types";

interface CompetitorListProps {
  competitors: Competitor[];
}

function CompetitorItem({ competitor }: { competitor: Competitor }) {
  return (
    <div className="flex items-start gap-2 py-2">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-foreground">{competitor.name}</span>
          {competitor.ticker && (
            <span className="inline-flex rounded px-1.5 py-0.5 text-xs font-mono font-semibold bg-muted text-muted-foreground">
              {competitor.ticker}
            </span>
          )}
        </div>
        {competitor.description && (
          <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
            {competitor.description}
          </p>
        )}
      </div>
    </div>
  );
}

export function CompetitorList({ competitors }: CompetitorListProps) {
  const mentioned = competitors.filter((c) => c.mentioned_in_transcript);
  const others = competitors.filter((c) => !c.mentioned_in_transcript);

  return (
    <div className="space-y-4">
      {mentioned.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
            Mentioned in this call
          </h4>
          <div className="divide-y divide-border rounded-lg border bg-card px-3">
            {mentioned.map((c) => (
              <CompetitorItem key={c.name} competitor={c} />
            ))}
          </div>
        </div>
      )}
      {others.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
            Other competitors
          </h4>
          <div className="divide-y divide-border rounded-lg border bg-card px-3">
            {others.map((c) => (
              <CompetitorItem key={c.name} competitor={c} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
