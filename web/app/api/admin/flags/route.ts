/** Server-side proxy for GET /admin/flags (list) and POST /admin/flags (create). Admin only. */
import { requireAdminUser } from "@/lib/admin-auth";
import { NextRequest, NextResponse } from "next/server";

function apiUrl(): string | undefined {
  return process.env.NEXT_PUBLIC_API_URL;
}

function misconfigured(): NextResponse {
  return NextResponse.json(
    { error: "Server misconfiguration: NEXT_PUBLIC_API_URL is not set" },
    { status: 500 }
  );
}

export async function GET(): Promise<NextResponse> {
  if (!apiUrl()) return misconfigured();

  const authResult = await requireAdminUser();
  if (authResult instanceof NextResponse) return authResult;

  try {
    const resp = await fetch(`${apiUrl()}/admin/flags`, {
      headers: { Authorization: `Bearer ${authResult.accessToken}` },
      cache: "no-store",
    });
    const data: unknown = await resp.json();
    return NextResponse.json(data, { status: resp.status });
  } catch {
    return NextResponse.json({ error: "Failed to reach backend" }, { status: 502 });
  }
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  if (!apiUrl()) return misconfigured();

  const authResult = await requireAdminUser();
  if (authResult instanceof NextResponse) return authResult;

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }

  try {
    const resp = await fetch(`${apiUrl()}/admin/flags`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${authResult.accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    const data: unknown = await resp.json();
    return NextResponse.json(data, { status: resp.status });
  } catch {
    return NextResponse.json({ error: "Failed to reach backend" }, { status: 502 });
  }
}
