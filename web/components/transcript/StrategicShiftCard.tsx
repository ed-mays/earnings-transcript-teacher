/** Renders a strategic shift item showing prior vs current position. */

import type { StrategicShift } from "./types";
import { Card } from "@/components/ui/card";

interface StrategicShiftCardProps {
  shift: StrategicShift;
}

export function StrategicShiftCard({ shift }: StrategicShiftCardProps) {
  return (
    <Card className="p-4 gap-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Before
          </p>
          <p className="text-sm text-foreground">{shift.prior_position}</p>
        </div>
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Now
          </p>
          <p className="text-sm text-foreground">{shift.current_position}</p>
        </div>
      </div>
      <div className="border-t border pt-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Investor significance
        </p>
        <p className="mt-1 text-sm text-foreground/80">{shift.investor_significance}</p>
      </div>
    </Card>
  );
}
