/** Renders a ranked list of keyword chips. */

import { Badge } from "@/components/ui/badge";

interface KeywordListProps {
  keywords: string[];
}

export function KeywordList({ keywords }: KeywordListProps) {
  if (keywords.length === 0) {
    return <p className="text-sm text-muted-foreground">No keywords extracted.</p>;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {keywords.map((kw, i) => (
        <Badge key={i} variant="secondary" className="rounded-full px-3 py-1 text-xs font-medium">
          {kw}
        </Badge>
      ))}
    </div>
  );
}
