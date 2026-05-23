import { createHmac, timingSafeEqual } from "crypto";
import { NextRequest } from "next/server";

const DASHBOARD_USER = process.env.DASHBOARD_USER || "admin";
const DASHBOARD_PASS = process.env.DASHBOARD_PASS || "autoreg2024";
const TOKEN_SECRET = process.env.SECRET_KEY || process.env.DASHBOARD_PASS || "autoreg2024";

function signPayload(payload: string): string {
  return createHmac("sha256", TOKEN_SECRET).update(payload).digest("hex");
}

function createToken(username: string): string {
  const payload = `${username}:${Date.now()}`;
  const sig = signPayload(payload);
  return Buffer.from(`${payload}:${sig}`).toString("base64");
}

function verifyToken(token: string): boolean {
  try {
    const decoded = Buffer.from(token, "base64").toString();
    const parts = decoded.split(":");
    if (parts.length < 3) return false;
    const sig = parts.pop()!;
    const payload = parts.join(":");
    const expected = signPayload(payload);
    const sigBuf = Buffer.from(sig, "utf8");
    const expectedBuf = Buffer.from(expected, "utf8");
    if (sigBuf.length !== expectedBuf.length) return false;
    return timingSafeEqual(sigBuf, expectedBuf);
  } catch {
    return false;
  }
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { username, password } = body;

  if (username === DASHBOARD_USER && password === DASHBOARD_PASS) {
    const token = createToken(username);
    return Response.json({ ok: true, token });
  }

  return Response.json({ ok: false, error: "Invalid credentials" }, { status: 401 });
}

export async function PUT(request: NextRequest) {
  const body = await request.json();
  const { token } = body;

  if (!token || !verifyToken(token)) {
    return Response.json({ ok: false }, { status: 401 });
  }

  return Response.json({ ok: true });
}
