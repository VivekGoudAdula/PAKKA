import type { Metadata } from "next";
import { AppProviders } from "@/components/providers";
import {
  Sidebar,
  TopBar,
  BottomNav,
  Footer,
  CommandPalette,
} from "@/components/pakka";
import { NoiseBackground } from "@/components/sera";

export const metadata: Metadata = {
  title: "Pakka - Voice Assistant for Local Services",
  description:
    "Pakka picks up, books the job, tells the technician, and chases the payment.",
};

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AppProviders>
      <div className="relative min-h-screen flex bg-background text-foreground antialiased selection:bg-primary/20 overflow-x-hidden w-full max-w-full">
        <NoiseBackground opacity={0.03} />

        {/* Desktop Sidebar */}
        <Sidebar />

        {/* Main Content Column */}
        <div className="flex-1 flex flex-col min-w-0 pb-16 md:pb-0 overflow-x-hidden">
          <TopBar />
          <main className="flex-1 p-3.5 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto overflow-x-hidden">
            {children}
          </main>
          <Footer />
        </div>

        {/* Mobile Navigation */}
        <BottomNav />

        {/* Global Command Palette */}
        <CommandPalette />
      </div>
    </AppProviders>
  );
}
