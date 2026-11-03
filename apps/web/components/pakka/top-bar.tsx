"use client";

import Link from "next/link";
import { Search, Settings } from "lucide-react";
import { PakkaLogo } from "@/components/pakka/pakka-logo";
import { ModeToggle } from "@/components/pakka/mode-toggle";
import { ClockChip } from "@/components/pakka/clock-chip";
import { Button } from "@/components/ui/button";

interface TopBarProps {
  onOpenCommand?: () => void;
}

export function TopBar({ onOpenCommand }: TopBarProps) {
  const triggerCommandPalette = () => {
    if (onOpenCommand) {
      onOpenCommand();
    } else {
      // Dispatch keydown event for Ctrl+K
      const event = new KeyboardEvent("keydown", {
        key: "k",
        ctrlKey: true,
        bubbles: true,
      });
      document.dispatchEvent(event);
    }
  };

  return (
    <header className="sticky top-0 z-20 w-full h-16 border-b border-border bg-card/80 backdrop-blur-md px-2.5 sm:px-6 flex items-center justify-between gap-1.5 sm:gap-3">
      {/* Left: Mobile Brand / Title */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        <div className="md:hidden">
          <PakkaLogo size="sm" showTagline={false} />
        </div>
        <button
          type="button"
          onClick={triggerCommandPalette}
          className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground bg-muted/60 hover:bg-muted border border-border px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
        >
          <Search className="w-3.5 h-3.5" />
          <span>Search screens & commands...</span>
          <kbd className="ml-2 font-mono text-[10px] bg-background/80 px-1.5 py-0.5 rounded border border-border">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right: Clock Chip + Mode Toggle + Settings */}
      <div className="flex items-center gap-1 sm:gap-3 shrink-0">
        <ClockChip />
        <ModeToggle />
        <div className="hidden sm:block">
          <Link href="/app/settings">
            <Button variant="ghost" size="icon-sm" aria-label="Settings">
              <Settings className="w-4 h-4 text-muted-foreground hover:text-foreground" />
            </Button>
          </Link>
        </div>
      </div>
    </header>
  );
}
