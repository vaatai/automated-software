"use client";

import { useAuth } from "@/contexts/auth-context";
import { useTheme } from "@/contexts/theme-context";
import { AutoRegLogo } from "@/components/ui/logo";
import { Lock, Eye, EyeOff } from "lucide-react";
import { useState, type FormEvent } from "react";

export function LoginScreen() {
  const { login } = useAuth();
  const { theme } = useTheme();
  const dark = theme === "dark";

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    const err = await login(username, password);
    if (err) setError(err);
    setLoading(false);
  };

  return (
    <div className={`fixed inset-0 z-[100] flex items-center justify-center p-4 ${
      dark ? "bg-gray-950" : "bg-slate-50"
    }`}>
      {/* Animated background orbs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className={`absolute -top-40 -left-40 h-80 w-80 rounded-full blur-3xl animate-float-slow ${
          dark ? "bg-blue-500/10" : "bg-blue-200/40"
        }`} />
        <div className={`absolute -bottom-40 -right-40 h-96 w-96 rounded-full blur-3xl animate-float-slower ${
          dark ? "bg-violet-500/10" : "bg-violet-200/30"
        }`} />
      </div>

      <div className={`relative w-full max-w-sm rounded-2xl border p-8 shadow-2xl animate-fade-in-up ${
        dark
          ? "border-gray-800/60 bg-gray-900/95 backdrop-blur-xl"
          : "border-slate-200 bg-white/95 backdrop-blur-xl"
      }`}>
        {/* Logo */}
        <div className="mb-6 flex flex-col items-center gap-3">
          <AutoRegLogo size={56} />
          <div className="text-center">
            <h1 className={`text-xl font-bold tracking-tight ${dark ? "text-white" : "text-slate-900"}`}>
              AutoReg Dashboard
            </h1>
            <p className={`mt-1 text-sm ${dark ? "text-gray-400" : "text-slate-500"}`}>
              Sign in to continue
            </p>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-sm text-red-400 animate-fade-in">
            <Lock className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={`mb-1.5 block text-sm font-medium ${dark ? "text-gray-300" : "text-slate-700"}`}>
              Username
            </label>
            <input
              type="text"
              required
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              className={`w-full rounded-xl border px-4 py-2.5 text-sm outline-none transition-all focus:ring-2 focus:ring-blue-500/40 ${
                dark
                  ? "border-gray-700 bg-gray-800/60 text-white placeholder-gray-500"
                  : "border-slate-200 bg-slate-50 text-slate-900 placeholder-slate-400"
              }`}
            />
          </div>

          <div>
            <label className={`mb-1.5 block text-sm font-medium ${dark ? "text-gray-300" : "text-slate-700"}`}>
              Password
            </label>
            <div className="relative">
              <input
                type={showPass ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className={`w-full rounded-xl border px-4 py-2.5 pr-10 text-sm outline-none transition-all focus:ring-2 focus:ring-blue-500/40 ${
                  dark
                    ? "border-gray-700 bg-gray-800/60 text-white placeholder-gray-500"
                    : "border-slate-200 bg-slate-50 text-slate-900 placeholder-slate-400"
                }`}
              />
              <button
                type="button"
                onClick={() => setShowPass((p) => !p)}
                className={`absolute right-3 top-1/2 -translate-y-1/2 ${dark ? "text-gray-500 hover:text-gray-300" : "text-slate-400 hover:text-slate-600"}`}
              >
                {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 py-2.5 text-sm font-medium text-white shadow-lg shadow-blue-500/20 transition-all hover:-translate-y-0.5 hover:shadow-xl hover:shadow-blue-500/30 disabled:opacity-50 disabled:hover:translate-y-0"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}
