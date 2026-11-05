import Link from "next/link";
import { ArrowLeft, Home, PhoneCall } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-16 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary">
        <PhoneCall className="h-8 w-8 stroke-[2.2]" />
      </div>
      <h1 className="mt-6 font-display text-4xl font-extrabold tracking-tight text-ink sm:text-5xl">
        404 — Page Not Found
      </h1>
      <p className="mt-3 max-w-md text-base text-muted">
        Lagta hai aap galat number dial kar baithe hain. The screen or resource you are looking for
        does not exist.
      </p>

      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <Link
          href="/"
          className={cn(buttonVariants({ variant: "outline" }), "gap-2")}
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Home
        </Link>
        <Link
          href="/app"
          className={cn(
            buttonVariants({ variant: "default" }),
            "gap-2 bg-primary hover:bg-primary/90 text-white"
          )}
        >
          <Home className="h-4 w-4" />
          Open Dashboard
        </Link>
      </div>

      <footer className="mt-16 text-xs text-muted">
        Pakka — Great Indian AI Internship Challenge · Synthetic Demo Data
      </footer>
    </div>
  );
}
