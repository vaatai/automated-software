import { NextRequest } from "next/server";
import { findUser, verifyPassword, createToken, verifyToken, hasAnyUsers } from "./users";

const DASHBOARD_USER = process.env.DASHBOARD_USER || "admin";
const DASHBOARD_PASS = process.env.DASHBOARD_PASS || "autoreg2024";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { identifier, password } = body;

  if (!identifier || !password) {
    return Response.json({ ok: false, error: "Email/phone and password required" }, { status: 400 });
  }

  // Check registered users first
  const user = findUser(identifier);
  if (user) {
    if (verifyPassword(password, user)) {
      const token = createToken(user.id, user.identifier);
      return Response.json({ ok: true, token, displayName: user.displayName });
    }
    return Response.json({ ok: false, error: "Invalid credentials" }, { status: 401 });
  }

  // Fallback to env-based admin credentials (username or email match)
  if (
    identifier === DASHBOARD_USER &&
    password === DASHBOARD_PASS
  ) {
    const token = createToken("env-admin", identifier);
    return Response.json({ ok: true, token, displayName: "Admin" });
  }

  return Response.json({ ok: false, error: "Invalid credentials" }, { status: 401 });
}

export async function PUT(request: NextRequest) {
  const body = await request.json();
  const { token } = body;

  if (!token) {
    return Response.json({ ok: false }, { status: 401 });
  }

  const result = verifyToken(token);
  if (!result.valid) {
    return Response.json({ ok: false }, { status: 401 });
  }

  return Response.json({ ok: true, identifier: result.identifier });
}

export async function GET() {
  return Response.json({ hasUsers: hasAnyUsers() });
}
