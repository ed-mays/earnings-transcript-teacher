import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import SignOutButton from "./SignOutButton";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ThemePicker } from "@/components/ThemePicker";
import { BreadcrumbBar } from "@/components/BreadcrumbBar";
import { FlagProvider } from "@/components/FlagProvider";
import { getFeatureFlags } from "@/lib/flags-server";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Menu } from "lucide-react";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "EarningsFluency",
  description: "Learn from earnings call transcripts",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const supabase = await createSupabaseServerClient();
  const [{ data: { user } }, flags] = await Promise.all([
    supabase.auth.getUser(),
    getFeatureFlags(),
  ]);

  let isAdmin = false;
  if (user) {
    const { data: profile } = await supabase
      .from("profiles")
      .select("role")
      .eq("id", user.id)
      .single();
    isAdmin = profile?.role === "admin";
  }

  const chatEnabled = flags["chat_enabled"] ?? true;

  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="flex min-h-full flex-col bg-background">
        <ThemeProvider>
          <FlagProvider initialFlags={flags}>
            {user && (
              <>
                <nav className="border-b bg-card">
                  <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
                    <Link
                      href="/"
                      className="text-lg font-semibold text-foreground hover:text-foreground/80"
                    >
                      EarningsFluency
                    </Link>
                    <div className="flex items-center gap-4">
                      {/* Learn link — gated by chat_enabled kill switch */}
                      {chatEnabled && (
                        <Link
                          href="/"
                          className="hidden text-sm text-muted-foreground hover:text-foreground md:block"
                        >
                          Library
                        </Link>
                      )}
                      {/* Desktop admin links */}
                      {isAdmin && (
                        <div className="hidden items-center gap-4 md:flex">
                          <Link
                            href="/admin"
                            className="text-sm text-muted-foreground hover:text-foreground"
                          >
                            Admin Analytics
                          </Link>
                          <Link
                            href="/admin/health"
                            className="text-sm text-muted-foreground hover:text-foreground"
                          >
                            Admin Health
                          </Link>
                          <Link
                            href="/admin/ingest"
                            className="text-sm text-muted-foreground hover:text-foreground"
                          >
                            Admin Ingest
                          </Link>
                        </div>
                      )}
                      <span className="text-sm text-muted-foreground">{user.email}</span>
                      <ThemePicker />
                      <SignOutButton />
                      {/* Mobile hamburger — admin only */}
                      {isAdmin && (
                        <div className="md:hidden">
                          <Sheet>
                            <SheetTrigger
                              render={
                                <Button variant="ghost" size="icon" aria-label="Open menu" />
                              }
                            >
                              <Menu className="h-4 w-4" />
                              <span className="sr-only">Open menu</span>
                            </SheetTrigger>
                            <SheetContent side="right">
                              <SheetHeader>
                                <SheetTitle>Menu</SheetTitle>
                              </SheetHeader>
                              <nav className="flex flex-col gap-1 px-4 pb-4">
                                <Link
                                  href="/admin"
                                  className="py-2 text-sm text-muted-foreground hover:text-foreground"
                                >
                                  Admin Analytics
                                </Link>
                                <Link
                                  href="/admin/health"
                                  className="py-2 text-sm text-muted-foreground hover:text-foreground"
                                >
                                  Admin Health
                                </Link>
                                <Link
                                  href="/admin/ingest"
                                  className="py-2 text-sm text-muted-foreground hover:text-foreground"
                                >
                                  Admin Ingest
                                </Link>
                              </nav>
                            </SheetContent>
                          </Sheet>
                        </div>
                      )}
                    </div>
                  </div>
                </nav>
                <BreadcrumbBar />
              </>
            )}
            <main className="flex flex-1 flex-col">{children}</main>
          </FlagProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
