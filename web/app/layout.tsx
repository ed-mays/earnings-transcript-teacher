import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import SignOutButton from "./SignOutButton";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ThemePicker } from "@/components/ThemePicker";

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
  const {
    data: { user },
  } = await supabase.auth.getUser();

  let isAdmin = false;
  if (user) {
    const { data: profile } = await supabase
      .from("profiles")
      .select("role")
      .eq("id", user.id)
      .single();
    isAdmin = profile?.role === "admin";
  }

  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="flex min-h-full flex-col bg-background">
        <ThemeProvider>
          {user && (
            <nav className="border-b bg-card">
              <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
                <a
                  href="/"
                  className="text-lg font-semibold text-foreground hover:text-foreground/80"
                >
                  EarningsFluency
                </a>
                <div className="flex items-center gap-4">
                  {isAdmin && (
                    <>
                      <a
                        href="/admin"
                        className="text-sm text-muted-foreground hover:text-foreground"
                      >
                        Admin Analytics
                      </a>
                      <a
                        href="/admin/health"
                        className="text-sm text-muted-foreground hover:text-foreground"
                      >
                        Admin Health
                      </a>
                      <a
                        href="/admin/ingest"
                        className="text-sm text-muted-foreground hover:text-foreground"
                      >
                        Admin Ingest
                      </a>
                    </>
                  )}
                  <span className="text-sm text-muted-foreground">{user.email}</span>
                  <ThemePicker />
                  <SignOutButton />
                </div>
              </div>
            </nav>
          )}
          <main className="flex flex-1 flex-col">{children}</main>
        </ThemeProvider>
      </body>
    </html>
  );
}
