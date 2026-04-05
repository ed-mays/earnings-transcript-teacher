"use client";

import Link from "next/link";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/** Error boundary for the transcript route — shown when fetchCallDetail throws. */
export default function TranscriptError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-8">
      <div className="flex justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Failed to load transcript</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">{error.message}</p>
            <div className="flex gap-2">
              <Button variant="outline" onClick={reset}>
                Try again
              </Button>
              <Link href="/" className={buttonVariants({ variant: "ghost" })}>
                Back to library
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
