"use client";

import { useAuth } from "@/contexts/auth-context";
import { useTheme } from "@/contexts/theme-context";
import { AutoRegLogo } from "@/components/ui/logo";
import { Lock, Eye, EyeOff, Mail, Phone, User } from "lucide-react";
import { useState, type FormEvent } from "react";

type Mode = "signin" | "signup";
type IdType = "email" | "phone";

export function LoginScreen() {
  const { login, signup } = useAuth();
  const { theme } = useTheme();
  const dark = theme === "dark";

  const [mode, setMode] = useState<Mode>("signin");
  const [idType, setIdType] = useState<IdType>("email");
  const [identifier, setIdentifier] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const switchMode = () => {
    setMode((m) => (m === "signin" ? "signup" : "signin"));
    setError("");
    setPassword("");
    setConfirmPassword("");
  };

  const switchIdType = (t: IdType) => {
    setIdType(t);
    setIdentifier("");
    setError("");
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    if (mode === "signup") {
      if (password !== confirmPassword) {
        setError("Passwords do not match");
        setLoading(false);
        return;
      }
      if (password.length < 6) {
        setError("Password must be at least 6 characters");
        setLoading(false);
        return;
      }
      const err = await signup(identifier, idType, displayName || identifier.split("@")[0], password);
      if (err) setError(err);
    } else {
      const err = await login(identifier, password);
      if (err) setError(err);
    }

    setLoading(false);
  };

  const inputCls = `w-full rounded-xl border px-4 py-2.5 text-sm outline-none transition-all focus:ring-2 focus:ring-blue-500/40 ${
    dark
      ? "border-gray-700 bg-gray-800/60 text-white placeholder-gray-500"
      : "border-slate-200 bg-slate-50 text-slate-900 placeholder-slate-400"
  }`;

  const labelCls = `mb-1.5 block text-sm font-medium ${dark ? "text-gray-300" : "text-slate-700"}`;

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

      <div className={`relative w-full max-w-sm max-h-[95vh] overflow-y-auto rounded-2xl border p-8 shadow-2xl animate-fade-in-up ${
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
              {mode === "signin" ? "Sign in to continue" : "Create your account"}
            </p>
          </div>
        </div>

        {/* Email / Phone toggle */}
        <div className={`mb-5 flex rounded-xl border p-1 ${
          dark ? "border-gray-700 bg-gray-800/40" : "border-slate-200 bg-slate-100"
        }`}>
          <button
            type="button"
            onClick={() => switchIdType("email")}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-medium transition-all ${
              idType === "email"
                ? "bg-gradient-to-r from-blue-600 to-violet-600 text-white shadow-sm"
                : dark ? "text-gray-400 hover:text-gray-200" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            <Mail className="h-3.5 w-3.5" /> Email
          </button>
          <button
            type="button"
            onClick={() => switchIdType("phone")}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-medium transition-all ${
              idType === "phone"
                ? "bg-gradient-to-r from-blue-600 to-violet-600 text-white shadow-sm"
                : dark ? "text-gray-400 hover:text-gray-200" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            <Phone className="h-3.5 w-3.5" /> Phone
          </button>
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
          {/* Identifier (email or phone) */}
          <div>
            <label className={labelCls}>
              {idType === "email" ? "Email Address" : "Phone Number"}
            </label>
            <input
              type={idType === "email" ? "email" : "tel"}
              required
              autoFocus
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder={idType === "email" ? "you@example.com" : "+1234567890"}
              className={inputCls}
            />
          </div>

          {/* Display name (signup only) */}
          {mode === "signup" && (
            <div className="animate-fade-in">
              <label className={labelCls}>Display Name</label>
              <div className="relative">
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Your name"
                  className={`${inputCls} pl-10`}
                />
                <User className={`absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 ${dark ? "text-gray-500" : "text-slate-400"}`} />
              </div>
            </div>
          )}

          {/* Password */}
          <div>
            <label className={labelCls}>Password</label>
            <div className="relative">
              <input
                type={showPass ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className={`${inputCls} pr-10`}
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

          {/* Confirm password (signup only) */}
          {mode === "signup" && (
            <div className="animate-fade-in">
              <label className={labelCls}>Confirm Password</label>
              <input
                type={showPass ? "text" : "password"}
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                className={inputCls}
              />
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 py-2.5 text-sm font-medium text-white shadow-lg shadow-blue-500/20 transition-all hover:-translate-y-0.5 hover:shadow-xl hover:shadow-blue-500/30 disabled:opacity-50 disabled:hover:translate-y-0"
          >
            {loading
              ? (mode === "signin" ? "Signing in..." : "Creating account...")
              : (mode === "signin" ? "Sign In" : "Create Account")
            }
          </button>
        </form>

        {/* Toggle mode */}
        <div className="mt-5 text-center">
          <p className={`text-sm ${dark ? "text-gray-400" : "text-slate-500"}`}>
            {mode === "signin" ? "Don't have an account?" : "Already have an account?"}
            <button
              type="button"
              onClick={switchMode}
              className="ml-1.5 font-medium text-blue-500 hover:text-blue-400 transition-colors"
            >
              {mode === "signin" ? "Sign Up" : "Sign In"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
