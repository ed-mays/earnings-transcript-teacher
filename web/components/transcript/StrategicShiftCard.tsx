/** Renders a strategic shift item showing prior vs current position. */

import type { StrategicShift } from "./types";

interface StrategicShiftCardProps {
  shift: StrategicShift;
}

export function StrategicShiftCard({ shift }: StrategicShiftCardProps) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-400">
            Before
          </p>
          <p className="text-sm text-zinc-700">{shift.prior_position}</p>
        </div>
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-400">
            Now
          </p>
          <p className="text-sm text-zinc-700">{shift.current_position}</p>
        </div>
      </div>
      <div className="mt-3 border-t border-zinc-100 pt-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-zinc-400">
          Investor significance
        </p>
        <p className="mt-1 text-sm text-zinc-600">{shift.investor_significance}</p>
      </div>
    </div>
  );
}
