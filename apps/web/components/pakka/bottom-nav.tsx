"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Radio,
  PhoneCall,
  Briefcase,
  Users,
  IndianRupee,
  Mic,
} from "lucide-react";
import { cn } from "@/lib/utils";

const mobileItems = [
  { name: "Talk", href: "/app/talk", icon: Mic },
  { name: "Live", href: "/app/live", icon: Radio, isLive: true },
  { name: "Overview", href: "/app", icon: LayoutDashboard },
  { name: "Calls", href: "/app/calls", icon: PhoneCall },
  { name: "Jobs", href: "/app/jobs", icon: Briefcase },
  { name: "Techs", href: "/app/technicians", icon: Users },
  { name: "Money", href: "/app/payments", icon: IndianRupee },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-card/95 backdrop-blur-md border-t border-border px-2 py-1.5 flex items-center justify-around safe-area-inset-bottom">
      {mobileItems.map((item) => {
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
              "flex flex-col items-center justify-center py-1 px-3 rounded-lg text-[10px] font-medium transition-colors",
              isActive
                ? "text-primary font-bold"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Icon
              className={cn(
                "h-5 w-5 mb-0.5",
                isActive ? "text-primary stroke-[2.5]" : "text-muted-foreground stroke-[1.75]"
              )}
            />
            <span>{item.name}</span>
          </Link>
        );
      })}
    </nav>
  );
}

