"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  PhoneCall,
  Briefcase,
  Users,
  IndianRupee,
  Settings,
  FastForward,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { useClockStore } from "@/lib/stores/clock-store";
import { useModeStore } from "@/lib/stores/mode-store";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const { advanceHours, advanceDays, resetClock } = useClockStore();
  const { mode, setMode } = useModeStore();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const runCommand = (command: () => void) => {
    setOpen(false);
    command();
  };

  return (
    <CommandDialog
      open={open}
      onOpenChange={setOpen}
      title="Pakka Commands"
      description="Quickly navigate or trigger actions"
    >
      <CommandInput placeholder="Type a command or search screens..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Navigation">
          <CommandItem
            onSelect={() => runCommand(() => router.push("/app"))}
            className="cursor-pointer"
          >
            <LayoutDashboard className="mr-2 h-4 w-4 text-primary" />
            <span>Overview Dashboard</span>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push("/app/calls"))}
            className="cursor-pointer"
          >
            <PhoneCall className="mr-2 h-4 w-4 text-primary" />
            <span>Calls & Transcripts</span>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push("/app/jobs"))}
            className="cursor-pointer"
          >
            <Briefcase className="mr-2 h-4 w-4 text-primary" />
            <span>Jobs Board</span>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push("/app/technicians"))}
            className="cursor-pointer"
          >
            <Users className="mr-2 h-4 w-4 text-primary" />
            <span>Technicians Directory</span>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push("/app/payments"))}
            className="cursor-pointer"
          >
            <IndianRupee className="mr-2 h-4 w-4 text-primary" />
            <span>Payments & Reminder Trail</span>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push("/app/settings"))}
            className="cursor-pointer"
          >
            <Settings className="mr-2 h-4 w-4 text-primary" />
            <span>Settings & Price List</span>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        <CommandGroup heading="Simulated Clock & Environment">
          <CommandItem
            onSelect={() => runCommand(() => advanceHours(1))}
            className="cursor-pointer"
          >
            <FastForward className="mr-2 h-4 w-4 text-amber-600" />
            <span>Clock: Fast-forward 1 hour</span>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => advanceDays(1))}
            className="cursor-pointer"
          >
            <FastForward className="mr-2 h-4 w-4 text-amber-600" />
            <span>Clock: Fast-forward 1 day</span>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => resetClock())}
            className="cursor-pointer"
          >
            <RotateCcw className="mr-2 h-4 w-4 text-muted-foreground" />
            <span>Clock: Reset to baseline</span>
          </CommandItem>
          <CommandItem
            onSelect={() =>
              runCommand(() => setMode(mode === "DEMO" ? "LIVE" : "DEMO"))
            }
            className="cursor-pointer"
          >
            <Sparkles className="mr-2 h-4 w-4 text-primary" />
            <span>Switch to {mode === "DEMO" ? "LIVE" : "DEMO"} Mode</span>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
