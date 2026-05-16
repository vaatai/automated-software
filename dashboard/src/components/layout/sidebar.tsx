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
  Settings,
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
    <aside className="fixed inset-y-0 left-0 z-30 flex w-64 flex-col border-r border-gray-800 bg-gray-950">
      <div className="flex h-16 items-center gap-3 border-b border-gray-800 px-6">
        <Settings className="h-6 w-6 text-blue-500" />
        <span className="text-lg font-semibold text-white">AutoReg</span>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-1">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || (href !== "/" && pathname.startsWith(href));
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-blue-600/10 text-blue-400"
                      : "text-gray-400 hover:bg-gray-800 hover:text-gray-200",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="border-t border-gray-800 px-6 py-4">
        <p className="text-xs text-gray-600">AutoReg Dashboard v1.0</p>
      </div>
    </aside>
  );
}
