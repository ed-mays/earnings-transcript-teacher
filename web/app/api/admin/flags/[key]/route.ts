/** Server-side proxy for PUT /admin/flags/{key} (update) and DELETE /admin/flags/{key}. Admin only. */
import { requireAdminUser } from "@/lib/admin-auth";
import { NextRequest, NextResponse } from "next/server";

type Context = { params: Promise<{ key: string }> };

function apiUrl(): string | undefined {
  return process.env.NEXT_PUBLIC_API_URL;
}

function misconfigured(): NextResponse {
  return NextResponse.json(
    { error: "Server misconfiguration: NEXT_PUBLIC_API_URL is not set" },
    { status: 500 }
  );
}

export async function PUT(request: NextRequest, { params }: Context): Promise<NextResponse> {
  if (!apiUrl()) return misconfigured();

  const authResult = await requireAdminUser();
  if (authResult instanceof NextResponse) return authResult;

  const { key } = await params;

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }

  try {
    const resp = await fetch(`${apiUrl()}/admin/flags/${encodeURIComponent(key)}`, {
      method: "PUT",
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

export async function DELETE(_request: NextRequest, { params }: Context): Promise<NextResponse> {
  if (!apiUrl()) return misconfigured();

  const authResult = await requireAdminUser();
  if (authResult instanceof NextResponse) return authResult;

  const { key } = await params;

  try {
    const resp = await fetch(`${apiUrl()}/admin/flags/${encodeURIComponent(key)}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${authResult.accessToken}` },
    });
    if (resp.status === 204) {
      return new NextResponse(null, { status: 204 });
    }
    const data: unknown = await resp.json();
    return NextResponse.json(data, { status: resp.status });
  } catch {
    return NextResponse.json({ error: "Failed to reach backend" }, { status: 502 });
  }
}
