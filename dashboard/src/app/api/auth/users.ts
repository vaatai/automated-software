import { createHash, createHmac, randomBytes, timingSafeEqual } from "crypto";
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";
import { join } from "path";

const TOKEN_SECRET = process.env.SECRET_KEY || process.env.DASHBOARD_PASS || "autoreg2024";
const DATA_DIR = join(process.cwd(), ".data");
const USERS_FILE = join(DATA_DIR, "users.json");

export interface StoredUser {
  id: string;
  identifier: string;
  identifierType: "email" | "phone";
  displayName: string;
  passwordHash: string;
  salt: string;
  createdAt: string;
}

function ensureDataDir() {
  if (!existsSync(DATA_DIR)) {
    mkdirSync(DATA_DIR, { recursive: true });
  }
}

function loadUsers(): StoredUser[] {
  ensureDataDir();
  if (!existsSync(USERS_FILE)) return [];
  try {
    return JSON.parse(readFileSync(USERS_FILE, "utf8"));
  } catch {
    return [];
  }
}

function saveUsers(users: StoredUser[]) {
  ensureDataDir();
  writeFileSync(USERS_FILE, JSON.stringify(users, null, 2));
}

export function hashPassword(password: string, salt: string): string {
  return createHash("sha256").update(salt + password).digest("hex");
}

export function findUser(identifier: string): StoredUser | undefined {
  const users = loadUsers();
  const normalized = identifier.toLowerCase().trim();
  return users.find((u) => u.identifier.toLowerCase() === normalized);
}

export function createUser(identifier: string, identifierType: "email" | "phone", displayName: string, password: string): StoredUser | null {
  const users = loadUsers();
  const normalized = identifier.toLowerCase().trim();
  if (users.some((u) => u.identifier.toLowerCase() === normalized)) {
    return null;
  }
  const salt = randomBytes(16).toString("hex");
  const user: StoredUser = {
    id: randomBytes(8).toString("hex"),
    identifier: normalized,
    identifierType,
    displayName,
    passwordHash: hashPassword(password, salt),
    salt,
    createdAt: new Date().toISOString(),
  };
  users.push(user);
  saveUsers(users);
  return user;
}

export function verifyPassword(password: string, user: StoredUser): boolean {
  const hash = hashPassword(password, user.salt);
  const hashBuf = Buffer.from(hash, "utf8");
  const storedBuf = Buffer.from(user.passwordHash, "utf8");
  if (hashBuf.length !== storedBuf.length) return false;
  return timingSafeEqual(hashBuf, storedBuf);
}

export function signPayload(payload: string): string {
  return createHmac("sha256", TOKEN_SECRET).update(payload).digest("hex");
}

export function createToken(userId: string, identifier: string): string {
  const payload = `${userId}:${identifier}:${Date.now()}`;
  const sig = signPayload(payload);
  return Buffer.from(`${payload}:${sig}`).toString("base64");
}

export function verifyToken(token: string): { valid: boolean; userId?: string; identifier?: string } {
  try {
    const decoded = Buffer.from(token, "base64").toString();
    const parts = decoded.split(":");
    if (parts.length < 4) return { valid: false };
    const sig = parts.pop()!;
    const payload = parts.join(":");
    const expected = signPayload(payload);
    const sigBuf = Buffer.from(sig, "utf8");
    const expectedBuf = Buffer.from(expected, "utf8");
    if (sigBuf.length !== expectedBuf.length) return { valid: false };
    if (!timingSafeEqual(sigBuf, expectedBuf)) return { valid: false };
    return { valid: true, userId: parts[0], identifier: parts[1] };
  } catch {
    return { valid: false };
  }
}

export function hasAnyUsers(): boolean {
  return loadUsers().length > 0;
}
