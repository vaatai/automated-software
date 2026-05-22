"use client";

import { useTheme } from "@/contexts/theme-context";
import { cn } from "@/lib/utils";
import {
  Activity,
  AlertCircle,
  BarChart3,
  Camera,
  Clock,
  Globe,
  Inbox,
  LayoutDashboard,
  Mail,
  Play,
  Server,
} from "lucide-react";
import { AutoRegLogo } from "@/components/ui/logo";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/websites", label: "Websites", icon: Globe },
  { href: "/registrations", label: "Registrations", icon: Play },
  { href: "/tasks", label: "Running Tasks", icon: Activity },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/otp", label: "OTP Tracking", icon: Mail },
  { href: "/workers", label: "Workers", icon: Server },
  { href: "/queues", label: "Queues", icon: Inbox },
  { href: "/limits", label: "Daily Limits", icon: Clock },
  { href: "/logs", label: "Error Logs", icon: AlertCircle },
  { href: "/screenshots", label: "Screenshots", icon: Camera },
];

export function Sidebar() {
  const pathname = usePathname();
  const { theme } = useTheme();
  const dark = theme === "dark";

  return (
    <aside className={cn(
      "fixed inset-y-0 left-0 z-30 flex w-64 flex-col border-r backdrop-blur-xl transition-colors duration-300",
      dark
        ? "border-gray-800/60 bg-gray-950/95"
        : "border-slate-200 bg-white/90",
    )}>
      {/* Logo */}
      <div className={cn(
        "flex h-16 items-center gap-3 border-b px-5",
        dark ? "border-gray-800/60" : "border-slate-200",
      )}>
        <AutoRegLogo size={40} />
        <div>
          <span className={cn("text-lg font-bold tracking-tight", dark ? "text-white" : "text-slate-900")}>
            AutoReg
          </span>
          <div className="h-0.5 w-8 rounded-full bg-gradient-to-r from-blue-500 to-violet-500" />
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-1">
          {NAV_ITEMS.map(({ href, label, icon: Icon }, i) => {
            const active = pathname === href || (href !== "/" && pathname.startsWith(href));
            return (
              <li
                key={href}
                className="animate-slide-in-left"
                style={{ animationDelay: `${i * 30}ms` }}
              >
                <Link
                  href={href}
                  className={cn(
                    "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                    active
                      ? dark
                        ? "bg-gradient-to-r from-blue-600/15 to-violet-600/10 text-blue-400"
                        : "bg-gradient-to-r from-blue-50 to-violet-50 text-blue-600"
                      : dark
                        ? "text-gray-400 hover:bg-gray-800/60 hover:text-gray-200"
                        : "text-slate-500 hover:bg-slate-100 hover:text-slate-900",
                  )}
                >
                  {active && (
                    <div className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-gradient-to-b from-blue-400 to-violet-500" />
                  )}
                  <Icon className={cn(
                    "h-4 w-4 transition-transform duration-200 group-hover:scale-110",
                    active && (dark ? "text-blue-400" : "text-blue-600"),
                  )} />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className={cn(
        "border-t px-6 py-4",
        dark ? "border-gray-800/60" : "border-slate-200",
      )}>
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50" />
          <p className={cn("text-xs", dark ? "text-gray-500" : "text-slate-400")}>AutoReg v1.0 · Production</p>
        </div>
      </div>
    </aside>
  );
}
