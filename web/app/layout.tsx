import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import SignOutButton from "./SignOutButton";

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

  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-zinc-50">
        {user && (
          <nav className="border-b border-zinc-200 bg-white">
            <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
              <a
                href="/"
                className="text-lg font-semibold text-zinc-900 hover:text-zinc-700"
              >
                EarningsFluency
              </a>
              <div className="flex items-center gap-4">
                <span className="text-sm text-zinc-500">{user.email}</span>
                <SignOutButton />
              </div>
            </div>
          </nav>
        )}
        <main className="flex flex-1 flex-col">{children}</main>
      </body>
    </html>
  );
}
