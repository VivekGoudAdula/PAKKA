"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Radio,
  PhoneCall,
  Briefcase,
  Users,
  IndianRupee,
  Settings,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Headphones,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { PakkaLogo } from "@/components/pakka/pakka-logo";
import { Button } from "@/components/ui/button";
import { useModeStore } from "@/lib/stores/mode-store";

const navItems = [
  {
    name: "Live Console",
    href: "/app/live",
    icon: Radio,
    badge: "LIVE",
    isLive: true,
  },
  {
    name: "Overview",
    href: "/app",
    icon: LayoutDashboard,
    badge: null,
    isLive: false,
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
    name: "Metrics",
    href: "/app/metrics",
    icon: BarChart3,
    badge: "v3.3",
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
  const { mode, wsConnected } = useModeStore();

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
              <div className="relative shrink-0">
                <Icon
                  className={cn(
                    "h-5 w-5 transition-transform group-hover:scale-105",
                    isActive ? "text-primary" : "text-muted-foreground"
                  )}
                />
                {item.isLive && (
                  <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
                  </span>
                )}
              </div>
              {!collapsed && <span className="truncate">{item.name}</span>}

              {!collapsed && item.badge && (
                <span
                  className={cn(
                    "ml-auto text-[11px] px-1.5 py-0.5 rounded-full font-bold flex items-center gap-1",
                    item.isLive
                      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                      : isActive
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground"
                  )}
                >
                  {item.isLive && <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />}
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
        <div className="m-3 p-3 rounded-xl border border-border bg-card/80 text-xs shadow-2xs">
          {mode === "DEMO" ? (
            <>
              <div className="flex items-center gap-2 mb-1">
                <span className="relative flex h-2 w-2">
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
                </span>
                <span className="font-semibold text-ink">Demo (simulated)</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-tight">
                Operating with seeded data &amp; simulated clock.
              </p>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-1">
                <span className="relative flex h-2 w-2">
                  {wsConnected && (
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  )}
                  <span
                    className={cn(
                      "relative inline-flex rounded-full h-2 w-2",
                      wsConnected ? "bg-emerald-500" : "bg-amber-500"
                    )}
                  />
                </span>
                <span className="font-semibold text-ink">Live Telephony</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-tight">
                {wsConnected
                  ? "Connected to Exotel &amp; Gnani WS."
                  : "Connecting to ws://localhost:8000..."}
              </p>
            </>
          )}
        </div>
      ) : (
        <div
          className="p-3 flex justify-center"
          title={mode === "DEMO" ? "Demo (simulated)" : "Live Telephony"}
        >
          <Headphones
            className={cn(
              "h-4 w-4",
              mode === "DEMO" ? "text-amber-600" : wsConnected ? "text-emerald-600" : "text-muted-foreground"
            )}
          />
        </div>
      )}
    </aside>
  );
}

