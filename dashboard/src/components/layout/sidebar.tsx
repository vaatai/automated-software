"use client";

import { useTheme } from "@/contexts/theme-context";
import { cn } from "@/lib/utils";
import {
  Activity,
  AlertCircle,
  BarChart3,
  Camera,
  ChevronLeft,
  ChevronRight,
  Clock,
  Globe,
  Inbox,
  LayoutDashboard,
  Mail,
  Play,
  Server,
  X,
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

interface SidebarProps {
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  onCloseMobile?: () => void;
  isMobileOpen?: boolean;
}

export function Sidebar({ collapsed = false, onToggleCollapse, onCloseMobile, isMobileOpen = false }: SidebarProps) {
  const pathname = usePathname();
  const { theme } = useTheme();
  const dark = theme === "dark";

  return (
    <aside className={cn(
      "fixed inset-y-0 left-0 z-30 flex flex-col border-r backdrop-blur-xl transition-all duration-300",
      collapsed ? "w-16" : "w-64",
      dark
        ? "border-gray-800/60 bg-gray-950/95"
        : "border-slate-200 bg-white/90",
    )}>
      {/* Logo */}
      <div className={cn(
        "flex h-16 items-center border-b",
        collapsed ? "justify-center px-2" : "justify-between px-5",
        dark ? "border-gray-800/60" : "border-slate-200",
      )}>
        <div className={cn("flex items-center", collapsed ? "" : "gap-3")}>
          <AutoRegLogo size={collapsed ? 32 : 40} />
          {!collapsed && (
            <div>
              <span className={cn("text-lg font-bold tracking-tight", dark ? "text-white" : "text-slate-900")}>
                AutoReg
              </span>
              <div className="h-0.5 w-8 rounded-full bg-gradient-to-r from-blue-500 to-violet-500" />
            </div>
          )}
        </div>
        {/* Close button on mobile when sidebar is open as overlay */}
        {!collapsed && isMobileOpen && (
          <button
            onClick={onCloseMobile}
            className={cn(
              "rounded-lg p-1.5 transition-colors lg:hidden",
              dark
                ? "text-gray-400 hover:bg-gray-800 hover:text-white"
                : "text-slate-400 hover:bg-slate-100 hover:text-slate-900",
            )}
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-2 py-4">
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
                  title={collapsed ? label : undefined}
                  onClick={onCloseMobile}
                  className={cn(
                    "group relative flex items-center rounded-lg text-sm font-medium transition-all duration-200",
                    collapsed ? "justify-center px-2 py-2.5" : "gap-3 px-3 py-2.5",
                    active
                      ? dark
                        ? "bg-gradient-to-r from-blue-600/15 to-violet-600/10 text-blue-400"
                        : "bg-gradient-to-r from-blue-50 to-violet-50 text-blue-600"
                      : dark
                        ? "text-gray-400 hover:bg-gray-800/60 hover:text-gray-200"
                        : "text-slate-500 hover:bg-slate-100 hover:text-slate-900",
                  )}
                >
                  {active && !collapsed && (
                    <div className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-gradient-to-b from-blue-400 to-violet-500" />
                  )}
                  {active && collapsed && (
                    <div className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-r-full bg-gradient-to-b from-blue-400 to-violet-500" />
                  )}
                  <Icon className={cn(
                    "h-4 w-4 shrink-0 transition-transform duration-200 group-hover:scale-110",
                    active && (dark ? "text-blue-400" : "text-blue-600"),
                  )} />
                  {!collapsed && label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Collapse toggle — visible on all devices */}
      <div className={cn(
        "border-t",
        collapsed ? "px-2 py-3" : "px-3 py-3",
        dark ? "border-gray-800/60" : "border-slate-200",
      )}>
        <button
          onClick={onToggleCollapse}
          className={cn(
            "flex w-full items-center rounded-lg py-2 text-xs font-medium transition-all duration-200",
            collapsed ? "justify-center px-2" : "gap-2 px-3",
            dark
              ? "text-gray-500 hover:bg-gray-800/60 hover:text-gray-300"
              : "text-slate-400 hover:bg-slate-100 hover:text-slate-600",
          )}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4" />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>

      {/* Footer */}
      {!collapsed && (
        <div className={cn(
          "border-t px-6 py-4",
          dark ? "border-gray-800/60" : "border-slate-200",
        )}>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50" />
            <p className={cn("text-xs", dark ? "text-gray-500" : "text-slate-400")}>AutoReg v1.0 · Production</p>
          </div>
        </div>
      )}
    </aside>
  );
}
