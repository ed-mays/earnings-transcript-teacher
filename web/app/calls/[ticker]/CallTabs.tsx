"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

interface CallTabsProps {
  ticker: string;
}

interface TabDef {
  href: string;
  label: string;
}

/** Sub-navigation between transcript view and Q&A Forensics mode for a single call.
 *  Active state derives from the URL so deep links land on the right tab. */
export function CallTabs({ ticker }: CallTabsProps) {
  const pathname = usePathname();
  const tabs: TabDef[] = [
    { href: `/calls/${ticker}`, label: "Transcript" },
    { href: `/calls/${ticker}/qa-forensics`, label: "Q&A Forensics" },
  ];

  return (
    <nav
      aria-label="Call sections"
      className="flex shrink-0 items-center gap-1 border-b bg-background px-4 py-2"
    >
      {tabs.map((tab) => {
        const isActive =
          tab.href === `/calls/${ticker}`
            ? pathname === tab.href
            : pathname?.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              isActive
                ? "bg-muted text-foreground"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
            )}
            aria-current={isActive ? "page" : undefined}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
