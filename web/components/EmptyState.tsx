interface EmptyStateProps {
  title: string;
  subtitle?: string;
  className?: string;
}

/** Reusable empty state with dashed border, centered title and optional subtitle. */
export function EmptyState({ title, subtitle, className }: EmptyStateProps) {
  return (
    <div className={`rounded-xl border border-dashed px-8 py-12 text-center bg-card ${className ?? ""}`}>
      <p className="text-sm font-medium text-foreground">{title}</p>
      {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
    </div>
  );
}
