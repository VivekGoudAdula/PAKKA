"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  PhoneCall,
  Briefcase,
  Users,
  IndianRupee,
  Settings,
  ChevronLeft,
  ChevronRight,
  Headphones,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { PakkaLogo } from "@/components/pakka/pakka-logo";
import { Button } from "@/components/ui/button";

const navItems = [
  {
    name: "Overview",
    href: "/app",
    icon: LayoutDashboard,
    badge: null,
  },
  {
    name: "Calls",
    href: "/app/calls",
    icon: PhoneCall,
    badge: "12",
  },
  {
    name: "Jobs Board",
    href: "/app/jobs",
    icon: Briefcase,
    badge: "10",
  },
  {
    name: "Technicians",
    href: "/app/technicians",
    icon: Users,
    badge: "4",
  },
  {
    name: "Payments",
    href: "/app/payments",
    icon: IndianRupee,
    badge: "₹2.3k",
  },
  {
    name: "Settings",
    href: "/app/settings",
    icon: Settings,
    badge: null,
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "hidden md:flex flex-col border-r border-border bg-card/60 backdrop-blur-md transition-all duration-300 select-none z-30",
        collapsed ? "w-18" : "w-64"
      )}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-border">
        {!collapsed && <PakkaLogo size="sm" showTagline={false} />}
        {collapsed && (
          <div className="w-full flex justify-center">
            <span className="font-black text-xl text-primary tracking-tight">P✓</span>
          </div>
        )}
        <Button
          variant="ghost"
          size="icon-xs"
          onClick={() => setCollapsed(!collapsed)}
          className={cn("text-muted-foreground hover:text-foreground", collapsed && "mx-auto")}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
      </div>

      {/* Nav items */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {navItems.map((item) => {
          const isActive =
            item.href === "/app"
              ? pathname === "/app"
              : pathname.startsWith(item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors group relative",
                isActive
                  ? "bg-primary/10 text-primary font-semibold shadow-xs"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
              title={collapsed ? item.name : undefined}
            >
              <Icon
                className={cn(
                  "h-5 w-5 shrink-0 transition-transform group-hover:scale-105",
                  isActive ? "text-primary" : "text-muted-foreground"
                )}
              />
              {!collapsed && <span className="truncate">{item.name}</span>}

              {!collapsed && item.badge && (
                <span
                  className={cn(
                    "ml-auto text-[11px] px-1.5 py-0.5 rounded-full font-bold",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground"
                  )}
                >
                  {item.badge}
                </span>
              )}

              {collapsed && isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-primary rounded-r" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Voice pipeline indicator card */}
      {!collapsed ? (
        <div className="m-3 p-3 rounded-xl border border-primary/20 bg-primary/5 text-xs">
          <div className="flex items-center gap-2 mb-1">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span className="font-semibold text-ink">Gnani Voice Stack</span>
          </div>
          <p className="text-[11px] text-muted-foreground leading-tight">
            Prisma v3.0 STT &bull; Timbre TTS &bull; Evon v3.3
          </p>
        </div>
      ) : (
        <div className="p-3 flex justify-center" title="Gnani Voice Stack Active">
          <Headphones className="h-4 w-4 text-emerald-600" />
        </div>
      )}
    </aside>
  );
}
