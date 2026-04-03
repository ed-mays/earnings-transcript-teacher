/** Renders a topic cluster as a card with a label and narrative summary. */

import { Card } from "@/components/ui/card";

interface ThemeCardProps {
  /** The theme label (topic name). */
  label: string;
  /** One-sentence narrative summary for this theme. */
  summary: string;
}

export function ThemeCard({ label, summary }: ThemeCardProps) {
  return (
    <Card className="p-4 gap-2">
      <p className="text-sm font-semibold text-foreground">{label}</p>
      {summary && (
        <p className="text-sm text-muted-foreground leading-snug">{summary}</p>
      )}
    </Card>
  );
}
