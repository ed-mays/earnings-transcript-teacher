import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getEvasionStyle, getSentimentStyle } from "@/lib/signal-colors";

export interface CallSummary {
  ticker: string;
  company_name: string | null;
  call_date: string | null;
  industry: string | null;
  evasion_level: "low" | "medium" | "high" | null;
  overall_sentiment: string | null;
  top_strategic_shift: string | null;
}

interface CallCardProps {
  call: CallSummary;
}


/** Card displaying summary metadata for a single earnings call. */
export function CallCard({ call }: CallCardProps) {
  return (
    <Link
      href={`/calls/${call.ticker}`}
      className="block transition-shadow hover:shadow-md focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 rounded-xl"
    >
      <Card className="p-6 gap-2 shadow-sm cursor-pointer h-full">
        <div className="flex items-start justify-between gap-4">
          <span className="text-2xl font-bold tracking-tight text-foreground">
            {call.ticker}
          </span>
          {call.call_date && (
            <span className="shrink-0 text-sm text-muted-foreground">{call.call_date}</span>
          )}
        </div>
        {call.company_name && (
          <p className="text-sm font-medium text-foreground/80">
            {call.company_name}
          </p>
        )}
        {call.industry && (
          <div>
            <Badge variant="secondary" className="rounded-md">
              {call.industry}
            </Badge>
          </div>
        )}
        {(call.evasion_level || call.overall_sentiment) && (
          <div className="flex flex-wrap gap-1.5">
            {call.overall_sentiment && (() => {
              const s = getSentimentStyle(call.overall_sentiment);
              return (
                <Badge className={`rounded-md whitespace-normal h-auto w-auto shrink ${s.bg} ${s.text}`}>
                  {call.overall_sentiment}
                </Badge>
              );
            })()}
            {call.evasion_level && (() => {
              const s = getEvasionStyle(call.evasion_level);
              return (
                <Badge className={`rounded-md whitespace-normal h-auto w-auto shrink ${s.bg} ${s.text}`}>
                  {call.evasion_level} evasion
                </Badge>
              );
            })()}
          </div>
        )}
        {call.top_strategic_shift && (
          <p className="truncate text-xs text-muted-foreground">
            {call.top_strategic_shift}
          </p>
        )}
      </Card>
    </Link>
  );
}
