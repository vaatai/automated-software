"use client";

import { useAuth } from "@/contexts/auth-context";
import { LoginScreen } from "@/components/ui/login-screen";
import { Spinner } from "@/components/ui/spinner";
import type { ReactNode } from "react";

export function AuthGate({ children }: { children: ReactNode }) {
  const { authenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-950">
        <Spinner />
      </div>
    );
  }

  if (!authenticated) {
    return <LoginScreen />;
  }

  return <>{children}</>;
}
