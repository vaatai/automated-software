import { NextRequest } from "next/server";
import { createUser, createToken } from "../users";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { identifier, identifierType, displayName, password } = body;

  if (!identifier || !password || !identifierType) {
    return Response.json({ ok: false, error: "All fields are required" }, { status: 400 });
  }

  if (password.length < 6) {
    return Response.json({ ok: false, error: "Password must be at least 6 characters" }, { status: 400 });
  }

  if (identifierType === "email") {
    const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRe.test(identifier)) {
      return Response.json({ ok: false, error: "Invalid email address" }, { status: 400 });
    }
  } else if (identifierType === "phone") {
    const phoneRe = /^\+?\d{7,15}$/;
    if (!phoneRe.test(identifier.replace(/[\s-]/g, ""))) {
      return Response.json({ ok: false, error: "Invalid phone number" }, { status: 400 });
    }
  }

  const name = displayName || identifier.split("@")[0] || "User";
  const user = createUser(identifier, identifierType, name, password);
  if (!user) {
    return Response.json({ ok: false, error: "Account already exists with this " + identifierType }, { status: 409 });
  }
  const token = createToken(user.id, user.identifier);

  return Response.json({ ok: true, token, displayName: user.displayName });
}
