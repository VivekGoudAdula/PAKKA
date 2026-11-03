import type { Metadata, Viewport } from "next";
import {
  Bricolage_Grotesque,
  Geist,
  JetBrains_Mono,
  Noto_Sans_Devanagari,
} from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

/* ── Fonts ──────────────────────────────────────────────────────────────── */

/** Display / headlines */
const bricolage = Bricolage_Grotesque({
  subsets: ["latin"],
  variable: "--font-bricolage",
  display: "swap",
  weight: ["400", "500", "600", "700", "800"],
});

/** Monospace — live transcripts, code */
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
  weight: ["400", "500"],
});

/** Hindi / Devanagari bilingual microcopy */
const notoDevanagari = Noto_Sans_Devanagari({
  subsets: ["devanagari"],
  variable: "--font-noto-devanagari",
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

/** UI body — Geist (via Google Fonts) */
const geist = Geist({
  subsets: ["latin"],
  variable: "--font-geist",
  display: "swap",
});

/* ── Metadata ───────────────────────────────────────────────────────────── */

export const metadata: Metadata = {
  title: {
    default: "Pakka — Every missed call has a cost",
    template: "%s | Pakka",
  },
  description:
    "Pakka picks up, books the job, tells the technician, and chases the payment. " +
    "A voice assistant for small Indian service businesses.",
  keywords: ["pakka", "voice AI", "booking assistant", "plumber", "geyser repair", "Hinglish"],
  authors: [{ name: "Pakka Team" }],
  robots: { index: false }, // Private app — don't index
};

export const viewport: Viewport = {
  themeColor: "#FF9F1C",
  width: "device-width",
  initialScale: 1,
};

/* ── Root layout ────────────────────────────────────────────────────────── */

/** Combined font class string for the <html> element */
const fontClasses = [
  bricolage.variable,
  jetbrainsMono.variable,
  notoDevanagari.variable,
  geist.variable,
].join(" ");

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="hi" className={fontClasses} suppressHydrationWarning>
      <body className="min-h-screen bg-background text-foreground antialiased">
        <TooltipProvider>
          {children}
          <Toaster position="bottom-right" richColors />
        </TooltipProvider>
      </body>
    </html>
  );
}
