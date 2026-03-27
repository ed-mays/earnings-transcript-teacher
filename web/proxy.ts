import { createServerClient } from "@supabase/ssr";
import { NextRequest, NextResponse } from "next/server";

/** Refreshes the Supabase session on every request and redirects unauthenticated users to sign-in. */
export async function proxy(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          for (const { name, value } of cookiesToSet) {
            request.cookies.set(name, value);
          }
          supabaseResponse = NextResponse.next({ request });
          for (const { name, value, options } of cookiesToSet) {
            supabaseResponse.cookies.set(name, value, options);
          }
        },
      },
    }
  );

  // Validate session — getUser() contacts the Auth server to verify the token.
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { pathname } = request.nextUrl;
  const isAuthRoute = pathname.startsWith("/auth/");

  if (!user && !isAuthRoute) {
    const signInUrl = request.nextUrl.clone();
    signInUrl.pathname = "/auth/sign-in";
    return NextResponse.redirect(signInUrl);
  }

  return supabaseResponse;
}

export const config = {
  matcher: [
    /*
     * Match all routes except Next.js internals and static files.
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
