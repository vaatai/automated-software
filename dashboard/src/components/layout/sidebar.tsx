"use client";

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
  Zap,
} from "lucide-react";
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

  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-64 flex-col border-r border-gray-800/60 bg-gray-950/95 backdrop-blur-xl">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-gray-800/60 px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 shadow-lg shadow-blue-500/20">
          <Zap className="h-5 w-5 text-white" />
        </div>
        <div>
          <span className="text-lg font-bold tracking-tight text-white">AutoReg</span>
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
                      ? "bg-gradient-to-r from-blue-600/15 to-violet-600/10 text-blue-400"
                      : "text-gray-400 hover:bg-gray-800/60 hover:text-gray-200",
                  )}
                >
                  {active && (
                    <div className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-gradient-to-b from-blue-400 to-violet-500" />
                  )}
                  <Icon className={cn(
                    "h-4 w-4 transition-transform duration-200 group-hover:scale-110",
                    active && "text-blue-400",
                  )} />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-800/60 px-6 py-4">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50" />
          <p className="text-xs text-gray-500">AutoReg v1.0 · Production</p>
        </div>
      </div>
    </aside>
  );
}
