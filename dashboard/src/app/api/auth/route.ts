import { NextRequest } from "next/server";

const DASHBOARD_USER = process.env.DASHBOARD_USER || "admin";
const DASHBOARD_PASS = process.env.DASHBOARD_PASS || "autoreg2024";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { username, password } = body;

  if (username === DASHBOARD_USER && password === DASHBOARD_PASS) {
    const token = Buffer.from(`${username}:${Date.now()}`).toString("base64");
    return Response.json({ ok: true, token });
  }

  return Response.json({ ok: false, error: "Invalid credentials" }, { status: 401 });
}

export async function PUT(request: NextRequest) {
  const body = await request.json();
  const { token } = body;

  if (!token) {
    return Response.json({ ok: false }, { status: 401 });
  }

  try {
    const decoded = Buffer.from(token, "base64").toString();
    const [user] = decoded.split(":");
    if (user === DASHBOARD_USER) {
      return Response.json({ ok: true });
    }
  } catch {
    // invalid token
  }

  return Response.json({ ok: false }, { status: 401 });
}
