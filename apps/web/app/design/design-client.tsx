"use client";

import { useState } from "react";
import { toast } from "sonner";
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
  Badge,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  Skeleton,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  ScrollArea,
  Switch,
  Slider,
  Progress,
  Avatar,
  AvatarFallback,
  AvatarImage,
  Separator,
} from "@/components/ui";
import { PakkaStamp } from "@/components/pakka/pakka-stamp";
import { NumberTicker } from "@/components/sera/number-ticker";
import { Marquee } from "@/components/sera/marquee";
import { TranscriptBubble } from "@/components/daisy/transcript-bubble";
import { Phone, Wrench, ShieldCheck, ChevronDown, Check } from "lucide-react";

/* ── Swatch Helper ────────────────────────────────────────────────────── */

interface SwatchProps {
  cssVar: string;
  label: string;
  hex: string;
}

function ColorSwatch({ cssVar, label, hex }: SwatchProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <div
        className="h-14 w-full rounded-xl border border-border shadow-sm"
        style={{ background: `var(${cssVar})` }}
        aria-label={`Color: ${label}`}
      />
      <div>
        <p className="text-xs font-semibold text-ink">{label}</p>
        <p className="font-mono text-[10px] text-muted">{cssVar}</p>
        <p className="font-mono text-[10px] text-muted">{hex}</p>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4">
      <h2 className="font-display text-2xl font-bold text-ink border-b border-border pb-2">
        {title}
      </h2>
      {children}
    </section>
  );
}

export function DesignPageClient() {
  const [stampVisible, setStampVisible] = useState(false);
  const [switchActive, setSwitchActive] = useState(true);
  const [sliderVal, setSliderVal] = useState([65]);

  const colorTokens: SwatchProps[] = [
    { cssVar: "--background", label: "Background", hex: "#FBF9F4" },
    { cssVar: "--surface", label: "Surface", hex: "#FFFFFF" },
    { cssVar: "--surface-2", label: "Surface 2", hex: "#F4F0E8" },
    { cssVar: "--ink", label: "Ink", hex: "#15130F" },
    { cssVar: "--muted", label: "Muted", hex: "#6B6558" },
    { cssVar: "--border", label: "Border", hex: "#E8E2D5" },
    { cssVar: "--primary", label: "Primary (Saffron)", hex: "#FF9F1C" },
    { cssVar: "--success", label: "Success (Pakka Green)", hex: "#12805C" },
    { cssVar: "--warning", label: "Warning", hex: "#D97706" },
    { cssVar: "--danger", label: "Danger", hex: "#D64545" },
    { cssVar: "--info", label: "Info", hex: "#3B5BDB" },
  ];

  const marqueeItems = [
    "Booking confirmed ✓",
    "Nali theek ho gayi 🔧",
    "Payment pakka 💰",
    "Plumber dispatch hoga ⚡",
    "Geyser repair booked ✓",
    "Har call ka jawab 📞",
  ];

  return (
    <div className="min-h-screen bg-background overflow-x-hidden w-full">
      {/* Page Header */}
      <header className="sticky top-0 z-50 glass border-b border-border px-4 sm:px-6 py-3 sm:py-4">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <h1 className="font-display text-lg sm:text-xl font-bold text-ink">
              Pakka <span className="text-primary">✓</span>
              <span className="ml-2 text-xs sm:text-sm font-normal text-muted">Design & Component QA</span>
            </h1>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="border-border bg-surface text-ink text-xs">
              Phase 0 Complete
            </Badge>
            <Button
              size="sm"
              variant="default"
              className="bg-primary text-primary-fg hover:bg-primary-hover min-h-[36px]"
              onClick={() => toast.success("Toast notification working via sonner!")}
            >
              Test Toast
            </Button>
          </div>
        </div>
      </header>

      {/* Marquee Banner */}
      <div className="border-b border-border py-2.5">
        <Marquee
          items={marqueeItems.map((item) => (
            <span
              key={item}
              className="rounded-full border border-border bg-surface px-4 py-1.5 text-sm font-medium text-ink shadow-sm"
            >
              {item}
            </span>
          ))}
          duration={25}
        />
      </div>

      <main className="mx-auto max-w-5xl space-y-16 px-4 py-12">
        {/* ── 1. Color Tokens ──────────────────────────── */}
        <Section title="1. Color Tokens">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {colorTokens.map((t) => (
              <ColorSwatch key={t.cssVar} {...t} />
            ))}
          </div>
        </Section>

        {/* ── 2. Typography Scale ──────────────────────── */}
        <Section title="2. Typography Scale">
          <div className="space-y-4">
            <div>
              <p className="text-xs text-muted mb-1">Display / Bricolage Grotesque</p>
              <p className="font-display text-4xl sm:text-5xl font-extrabold text-ink leading-tight">
                हर missed call का cost है
              </p>
            </div>
            <div>
              <p className="text-xs text-muted mb-1">Heading / Bricolage Grotesque Bold</p>
              <p className="font-display text-2xl sm:text-3xl font-bold text-ink">
                Pakka picks up, books the job.
              </p>
            </div>
            <div>
              <p className="text-xs text-muted mb-1">Body / Geist</p>
              <p className="font-sans text-base text-ink">
                A voice assistant for small Indian service businesses. Answers in Hinglish, 24/7.
              </p>
            </div>
            <div>
              <p className="text-xs text-muted mb-1">Mono / JetBrains Mono (transcripts)</p>
              <p className="font-mono text-sm text-ink bg-surface-2 rounded-lg px-4 py-3 border border-border">
                {"[09:41 AM] caller: Bhai, geyser kharab hai. Subah se nahi chal raha."}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted mb-1">Devanagari / Noto Sans Devanagari</p>
              <p className="font-devanagari text-xl text-ink">
                पक्की बुकिंग — हर मिस्ड कॉल का जवाब
              </p>
            </div>
          </div>
        </Section>

        {/* ── 3. shadcn/ui Buttons ─────────────────────── */}
        <Section title="3. shadcn/ui Buttons">
          <div className="flex flex-wrap gap-3 items-center">
            <Button className="bg-primary text-primary-fg hover:bg-primary-hover min-h-[44px]">
              Primary Saffron
            </Button>
            <Button variant="secondary" className="bg-surface-2 text-ink border border-border min-h-[44px]">
              Secondary
            </Button>
            <Button variant="outline" className="border-border text-ink hover:bg-surface-2 min-h-[44px]">
              Outline
            </Button>
            <Button variant="destructive" className="bg-danger text-white min-h-[44px]">
              Destructive
            </Button>
            <Button variant="ghost" className="text-muted hover:text-ink min-h-[44px]">
              Ghost
            </Button>
            <Button className="bg-success text-white hover:opacity-90 min-h-[44px]">
              <Check className="mr-2 h-4 w-4" /> Pakka Success
            </Button>
          </div>
        </Section>

        {/* ── 4. shadcn/ui Cards ───────────────────────── */}
        <Section title="4. shadcn/ui Cards">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {/* Job Card with Stamp */}
            <Card className="relative border-border bg-surface shadow-sm">
              <div className="absolute -top-3 -right-3 z-10">
                <PakkaStamp size="sm" visible />
              </div>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2 text-xs text-muted">
                  <Wrench className="h-3.5 w-3.5" />
                  <span>Job #PK-1042</span>
                </div>
                <CardTitle className="font-display text-xl text-ink">Geyser Repair</CardTitle>
                <CardDescription className="text-muted">
                  Sector 12, Rohini · Shaam 5 baje
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <Badge className="bg-success/15 text-success border-success/30 font-semibold">
                    Pakka ✓ Confirmed
                  </Badge>
                  <Badge variant="outline" className="text-muted">
                    ₹350–500
                  </Badge>
                </div>
              </CardContent>
              <CardFooter className="pt-0 text-xs text-muted flex justify-between">
                <span>Technician: Ramesh Kumar</span>
                <span className="text-success font-medium">Ready</span>
              </CardFooter>
            </Card>

            {/* Stat Card with NumberTicker */}
            <Card className="border-border bg-surface shadow-sm">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardDescription className="uppercase tracking-wider text-xs font-semibold">
                    Calls Answered
                  </CardDescription>
                  <Phone className="h-4 w-4 text-muted" />
                </div>
                <CardTitle className="font-display text-4xl text-ink mt-2">
                  <NumberTicker value={247} suffix="+" />
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-success font-medium">↑ 12% over last week</p>
                <Progress value={82} className="mt-3 h-2 bg-surface-2" />
              </CardContent>
            </Card>

            {/* Revenue Card with Glow */}
            <Card className="border-primary/40 bg-surface shadow-sm glow-saffron overflow-hidden">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs font-semibold uppercase tracking-wider">
                  Revenue Protected
                </CardDescription>
                <CardTitle className="font-display text-4xl text-primary mt-2">
                  <NumberTicker value={18450} prefix="₹" />
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted">48 missed calls recovered into bookings</p>
              </CardContent>
            </Card>
          </div>
        </Section>

        {/* ── 5. Badges, Inputs, Select, Switch, Slider ── */}
        <Section title="5. Inputs, Controls & Form Primitives">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <Card className="border-border bg-surface p-5 space-y-4">
              <div>
                <label className="text-xs font-semibold text-ink">Text Input</label>
                <Input
                  placeholder="Customer address (e.g. Near Shiv Mandir)..."
                  className="mt-1.5 border-border bg-surface text-ink"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-ink">Service Category Select</label>
                <Select defaultValue="geyser">
                  <SelectTrigger className="mt-1.5 border-border bg-surface text-ink">
                    <SelectValue placeholder="Select service" />
                  </SelectTrigger>
                  <SelectContent className="bg-surface border-border">
                    <SelectItem value="geyser">Geyser Repair & Service</SelectItem>
                    <SelectItem value="pipe">Pipe Leakage & Fitting</SelectItem>
                    <SelectItem value="motor">Water Motor Replacement</SelectItem>
                    <SelectItem value="tap">Tap & Shower Installation</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center justify-between pt-2">
                <div>
                  <p className="text-sm font-semibold text-ink">Outbound Calling (Owner Setting)</p>
                  <p className="text-xs text-muted">Active hours: 9:00 AM – 8:00 PM IST</p>
                </div>
                <Switch
                  checked={switchActive}
                  onCheckedChange={setSwitchActive}
                  aria-label="Toggle outbound calling"
                />
              </div>

              <div className="pt-2">
                <div className="flex justify-between text-xs text-muted mb-2">
                  <span>VAD Threshold: {sliderVal[0]}%</span>
                  <span>Min Speech: 200ms</span>
                </div>
                <Slider
                  value={sliderVal}
                  onValueChange={(val) => {
                    if (typeof val === "number") setSliderVal([val]);
                    else if (Array.isArray(val)) setSliderVal([...val]);
                  }}
                  max={100}
                  step={1}
                  className="w-full"
                />
              </div>
            </Card>

            <Card className="border-border bg-surface p-5 space-y-4">
              <p className="text-sm font-semibold text-ink">Badge System</p>
              <div className="flex flex-wrap gap-2">
                <Badge className="bg-primary text-primary-fg font-semibold">Primary Saffron</Badge>
                <Badge className="bg-success text-white">Pakka ✓ Success</Badge>
                <Badge className="bg-warning text-white">Pending Follow-up</Badge>
                <Badge className="bg-danger text-white">Declined</Badge>
                <Badge className="bg-info text-white">Information</Badge>
                <Badge variant="outline" className="border-border text-muted">Neutral Outline</Badge>
              </div>

              <Separator className="my-3 bg-border" />

              <p className="text-sm font-semibold text-ink">Avatar & Status Indicator</p>
              <div className="flex items-center gap-4">
                <Avatar className="h-12 w-12 border border-border">
                  <AvatarImage src="/avatar-demo.png" alt="Ramesh" />
                  <AvatarFallback className="bg-primary/20 text-ink font-bold">RK</AvatarFallback>
                </Avatar>
                <div>
                  <p className="text-sm font-semibold text-ink">Ramesh Kumar (Plumber)</p>
                  <p className="text-xs text-success flex items-center gap-1 font-medium">
                    <span className="h-2 w-2 rounded-full bg-success inline-block" />
                    Available for dispatch
                  </p>
                </div>
              </div>

              <Separator className="my-3 bg-border" />

              <p className="text-sm font-semibold text-ink">Skeleton Loading States</p>
              <div className="space-y-2">
                <Skeleton className="h-4 w-3/4 bg-surface-2" />
                <Skeleton className="h-4 w-1/2 bg-surface-2" />
              </div>
            </Card>
          </div>
        </Section>

        {/* ── 6. Modals & Overlays (Dialog, Sheet, Dropdown, Tooltip) ── */}
        <Section title="6. Overlays & Action Primitives">
          <div className="flex flex-wrap gap-4 items-center">
            {/* Dialog */}
            <Dialog>
              <DialogTrigger>
                <Button variant="outline" className="border-border text-ink hover:bg-surface-2">
                  Open Dialog
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-surface border-border sm:max-w-md">
                <DialogHeader>
                  <DialogTitle className="font-display text-xl text-ink">
                    Manual Booking Confirmation
                  </DialogTitle>
                  <DialogDescription className="text-muted">
                    Review extracted job details before confirming technician dispatch.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-3 py-2 text-sm text-ink">
                  <p><strong>Customer:</strong> Sunita Sharma (+91 98765-XXXXX)</p>
                  <p><strong>Problem:</strong> Geyser heating coil failure</p>
                  <p><strong>Quote Range:</strong> ₹400 – ₹600</p>
                </div>
                <div className="flex justify-end gap-2 mt-4">
                  <Button className="bg-primary text-primary-fg hover:bg-primary-hover">
                    Confirm Booking ✓
                  </Button>
                </div>
              </DialogContent>
            </Dialog>

            {/* Sheet */}
            <Sheet>
              <SheetTrigger>
                <Button variant="outline" className="border-border text-ink hover:bg-surface-2">
                  Open Slide-Over Sheet
                </Button>
              </SheetTrigger>
              <SheetContent className="bg-surface border-border">
                <SheetHeader>
                  <SheetTitle className="font-display text-xl text-ink">
                    Technician Dispatch Queue
                  </SheetTitle>
                  <SheetDescription className="text-muted">
                    Fallback roster if first technician declines.
                  </SheetDescription>
                </SheetHeader>
                <div className="space-y-4 py-4 text-sm">
                  <div className="rounded-lg border border-border p-3 bg-surface-2">
                    <p className="font-semibold text-ink">1. Ramesh Kumar (Primary)</p>
                    <p className="text-xs text-muted">Response: Pending call...</p>
                  </div>
                  <div className="rounded-lg border border-border p-3 bg-surface">
                    <p className="font-semibold text-ink">2. Sonu Electrician (Backup)</p>
                    <p className="text-xs text-muted">Status: On standby</p>
                  </div>
                </div>
              </SheetContent>
            </Sheet>

            {/* Dropdown Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger>
                <Button variant="outline" className="border-border text-ink hover:bg-surface-2">
                  Actions Menu <ChevronDown className="ml-2 h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="bg-surface border-border">
                <DropdownMenuLabel>Job Actions</DropdownMenuLabel>
                <DropdownMenuSeparator className="bg-border" />
                <DropdownMenuItem className="text-ink hover:bg-surface-2 cursor-pointer">
                  Assign Technician
                </DropdownMenuItem>
                <DropdownMenuItem className="text-ink hover:bg-surface-2 cursor-pointer">
                  Trigger Payment Follow-up
                </DropdownMenuItem>
                <DropdownMenuItem className="text-danger hover:bg-surface-2 cursor-pointer">
                  Mark Wrong Number
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Tooltip */}
            <Tooltip>
              <TooltipTrigger>
                <Button variant="ghost" size="icon" className="text-muted hover:text-ink">
                  <ShieldCheck className="h-5 w-5 text-success" />
                </Button>
              </TooltipTrigger>
              <TooltipContent className="bg-ink text-surface text-xs">
                AI Disclosure: Verified digital assistant on all calls
              </TooltipContent>
            </Tooltip>
          </div>
        </Section>

        {/* ── 7. Tabs, Table & ScrollArea ─────────────── */}
        <Section title="7. Tabs & Data Table">
          <Tabs defaultValue="all" className="w-full">
            <TabsList className="bg-surface-2 border border-border">
              <TabsTrigger value="all" className="text-xs data-[state=active]:bg-surface data-[state=active]:text-ink">
                All Jobs (3)
              </TabsTrigger>
              <TabsTrigger value="booked" className="text-xs data-[state=active]:bg-surface data-[state=active]:text-ink">
                Booked ✓
              </TabsTrigger>
              <TabsTrigger value="collection" className="text-xs data-[state=active]:bg-surface data-[state=active]:text-ink">
                Collection
              </TabsTrigger>
            </TabsList>

            <TabsContent value="all" className="mt-4">
              <Card className="border-border bg-surface overflow-hidden">
                <ScrollArea className="w-full">
                  <Table>
                    <TableHeader className="bg-surface-2">
                      <TableRow className="border-border">
                        <TableHead className="text-xs font-semibold text-ink">Job ID</TableHead>
                        <TableHead className="text-xs font-semibold text-ink">Service</TableHead>
                        <TableHead className="text-xs font-semibold text-ink">Location</TableHead>
                        <TableHead className="text-xs font-semibold text-ink">Status</TableHead>
                        <TableHead className="text-xs font-semibold text-ink text-right">Estimate</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      <TableRow className="border-border">
                        <TableCell className="font-mono text-xs">#PK-1042</TableCell>
                        <TableCell className="font-medium text-ink">Geyser Repair</TableCell>
                        <TableCell className="text-muted">Rohini Sec-12</TableCell>
                        <TableCell>
                          <Badge className="bg-success/15 text-success border-success/30">Pakka ✓</Badge>
                        </TableCell>
                        <TableCell className="text-right font-medium text-ink">₹350–500</TableCell>
                      </TableRow>
                      <TableRow className="border-border">
                        <TableCell className="font-mono text-xs">#PK-1043</TableCell>
                        <TableCell className="font-medium text-ink">Kitchen Tap Fitting</TableCell>
                        <TableCell className="text-muted">Janakpuri B-Block</TableCell>
                        <TableCell>
                          <Badge className="bg-primary/15 text-primary border-primary/30">Dispatching</Badge>
                        </TableCell>
                        <TableCell className="text-right font-medium text-ink">₹200–300</TableCell>
                      </TableRow>
                      <TableRow className="border-border">
                        <TableCell className="font-mono text-xs">#PK-1044</TableCell>
                        <TableCell className="font-medium text-ink">Water Motor Repair</TableCell>
                        <TableCell className="text-muted">Pitampura</TableCell>
                        <TableCell>
                          <Badge className="bg-warning/15 text-warning border-warning/30">Payment Due</Badge>
                        </TableCell>
                        <TableCell className="text-right font-medium text-ink">₹800</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </ScrollArea>
              </Card>
            </TabsContent>
            <TabsContent value="booked">
              <p className="text-xs text-muted p-4">Filter: Showing confirmed jobs only.</p>
            </TabsContent>
            <TabsContent value="collection">
              <p className="text-xs text-muted p-4">Filter: Showing pending payments only.</p>
            </TabsContent>
          </Tabs>
        </Section>

        {/* ── 8. Signature PAKKA ✓ Stamp ───────────────── */}
        <Section title="8. Signature Element — PAKKA ✓ Stamp">
          <div className="flex flex-wrap items-center gap-8">
            <div className="flex flex-col items-center gap-4">
              <Button
                onClick={() => setStampVisible((v) => !v)}
                className="bg-primary text-primary-fg hover:bg-primary-hover min-h-[44px]"
              >
                {stampVisible ? "Reset Stamp" : "Trigger Stamp Spring ✓"}
              </Button>
              <PakkaStamp size="lg" variant="success" visible={stampVisible} />
            </div>

            <div className="flex flex-wrap items-end gap-4 sm:gap-6">
              <div className="flex flex-col items-center gap-2">
                <PakkaStamp size="sm" variant="primary" />
                <span className="text-xs text-muted">sm / saffron</span>
              </div>
              <div className="flex flex-col items-center gap-2">
                <PakkaStamp size="md" variant="success" />
                <span className="text-xs text-muted">md / success</span>
              </div>
              <div className="flex flex-col items-center gap-2">
                <PakkaStamp size="sm" variant="primary" className="sm:hidden" />
                <PakkaStamp size="lg" variant="primary" className="hidden sm:inline-flex" />
                <span className="text-xs text-muted">lg / saffron</span>
              </div>
            </div>
          </div>
        </Section>

        {/* ── 9. daisyUI Chat Bubbles ─────────────────── */}
        <Section title="9. daisyUI — Live Call Transcript (Scoped with daisy- prefix)">
          <div className="rounded-[var(--radius-lg)] border border-border bg-surface-2 p-4 space-y-1">
            <TranscriptBubble
              role="caller"
              text="Bhai, geyser kharab hai. Subah se paani garam nahi ho raha."
              timestamp="09:41 AM"
            />
            <TranscriptBubble
              role="assistant"
              text="Namaste, Pakka demo shop ki digital sahayak bol rahi hoon. Koi baat nahi! Main abhi aapki booking kar deti hoon. Pilot light jal rahi hai kya?"
              timestamp="09:41 AM"
            />
            <TranscriptBubble
              role="caller"
              text="Nahi, light bhi band hai. Shaam tak karwa do."
              timestamp="09:42 AM"
            />
            <TranscriptBubble
              role="assistant"
              text="Theek hai ji! Shaam 5 se 7 baje ka slot pakka kar diya. Estimate do sau se chaar sau rupaye."
              timestamp="09:42 AM"
              isPartial
            />
          </div>
        </Section>

        {/* ── 10. Sera UI Number Ticker ──────────────── */}
        <Section title="10. Sera UI — Number Ticker (Light Re-themed)">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "Calls Handled", value: 42, suffix: "" },
              { label: "Bookings Made", value: 38, suffix: "" },
              { label: "Money Collected", value: 92, suffix: "%" },
              { label: "Voice Latency", value: 1.2, suffix: "s", decimalPlaces: 1 },
            ].map((s) => (
              <Card key={s.label} className="border-border bg-surface p-4 text-center">
                <p className="font-display text-3xl font-bold text-ink">
                  <NumberTicker
                    value={s.value}
                    suffix={s.suffix}
                    decimalPlaces={s.decimalPlaces ?? 0}
                  />
                </p>
                <p className="mt-1 text-xs text-muted">{s.label}</p>
              </Card>
            ))}
          </div>
        </Section>
      </main>
    </div>
  );
}
