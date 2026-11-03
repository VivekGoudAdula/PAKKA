"use client";

import { useState } from "react";
import { toast } from "sonner";
import {
  Wrench,
  Clock,
  ShieldAlert,
  Plus,
  Trash2,
  Save,
  Bot,
  RotateCcw,
} from "lucide-react";
import { SEED_PRICE_LIST } from "@/lib/api/seed-data";
import { PriceItem } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function SettingsPage() {
  const [priceList, setPriceList] = useState<PriceItem[]>(SEED_PRICE_LIST);
  const [businessName, setBusinessName] = useState("Sharma Plumbing & Geyser Care");
  const [handoffPhone, setHandoffPhone] = useState("+91 98765 43210");
  const [outboundStart, setOutboundStart] = useState("09:00");
  const [outboundEnd, setOutboundEnd] = useState("20:00");
  const [autoStopOnWrongNumber, setAutoStopOnWrongNumber] = useState(true);
  const [neverDenyAi, setNeverDenyAi] = useState(true);

  // New item draft state
  const [newItemName, setNewItemName] = useState("");
  const [newItemCategory, setNewItemCategory] = useState<PriceItem["category"]>("Plumbing");
  const [newItemMin, setNewItemMin] = useState(250);
  const [newItemMax, setNewItemMax] = useState(450);

  const handleAddItem = () => {
    if (!newItemName.trim()) {
      toast.error("Please enter a service name");
      return;
    }
    const item: PriceItem = {
      id: `price_${Date.now()}`,
      service_name: newItemName.trim(),
      category: newItemCategory,
      min_price: Number(newItemMin),
      max_price: Number(newItemMax),
      unit: "per visit / unit",
    };
    setPriceList((prev) => [item, ...prev]);
    setNewItemName("");
    toast.success(`Added ${item.service_name} to price list`);
  };

  const handleDeleteItem = (id: string, name: string) => {
    setPriceList((prev) => prev.filter((p) => p.id !== id));
    toast.info(`Removed ${name} from price list`);
  };

  const handleSaveSettings = () => {
    toast.success("Settings saved successfully", {
      description: "Voice brain prompts and calling bounds updated for live/demo sessions.",
    });
  };

  const handleResetDefaults = () => {
    setPriceList(SEED_PRICE_LIST);
    setBusinessName("Sharma Plumbing & Geyser Care");
    setHandoffPhone("+91 98765 43210");
    setOutboundStart("09:00");
    setOutboundEnd("20:00");
    toast.info("Settings reset to defaults");
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-ink">
            Business & Voice Settings
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Configure price list, outbound calling rules, emergency handoff, and voice identity.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleResetDefaults} className="text-xs gap-1.5">
            <RotateCcw className="w-3.5 h-3.5 text-muted-foreground" />
            <span>Reset</span>
          </Button>
          <Button size="sm" onClick={handleSaveSettings} className="text-xs gap-1.5 bg-primary hover:bg-primary/90 text-white font-semibold">
            <Save className="w-3.5 h-3.5" />
            <span>Save Configuration</span>
          </Button>
        </div>
      </div>

      {/* Voice Assistant Greeting & Identity Card */}
      <div className="p-5 sm:p-6 rounded-2xl border border-primary/30 bg-gradient-to-br from-card to-primary/5 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-primary" />
            <h2 className="text-base font-bold text-ink">Voice Assistant Spoken Identity</h2>
          </div>
          <Badge className="bg-emerald-50 text-emerald-800 border-emerald-300 text-[11px]">
            Strict Compliance Enabled
          </Badge>
        </div>

        {/* Spoken Greeting Preview */}
        <div className="p-4 rounded-xl bg-background border border-border space-y-2">
          <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider block">
            Mandatory Spoken Opening Line
          </span>
          <p className="text-sm font-semibold text-ink leading-relaxed">
            &ldquo;Namaste, <span className="text-primary">{businessName}</span> ki digital sahayak bol rahi hoon. Bataiye, kya kaam hai?&rdquo;
          </p>
          <p className="text-xs text-muted-foreground">
            The assistant opens every call announcing its identity as a digital sahayak in natural Hinglish.
          </p>
        </div>

        {/* AI Non-denial Rule Banner */}
        <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-900 space-y-1">
          <div className="flex items-center gap-1.5 font-bold">
            <ShieldAlert className="w-4 h-4 text-amber-700" />
            <span>Non-Negotiable AI Non-Denial Policy</span>
          </div>
          <p className="text-[11px] leading-relaxed text-amber-950/80">
            If the caller asks &ldquo;Are you an AI? / Kya aap robot ho?&rdquo;, Pakka will never deny being an AI. It will honestly confirm and immediately offer a human owner callback.
          </p>
        </div>
      </div>

      {/* Outbound Calling Hours & Handoff */}
      <div className="p-5 sm:p-6 rounded-2xl border border-border bg-card shadow-xs space-y-5">
        <div className="flex items-center gap-2">
          <Clock className="w-5 h-5 text-primary" />
          <h2 className="text-base font-bold text-ink">Outbound Calling Hours & Handoff</h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Business Name</label>
            <Input
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
              placeholder="e.g. Ramesh Plumbing Works"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Emergency Owner Phone</label>
            <Input
              value={handoffPhone}
              onChange={(e) => setHandoffPhone(e.target.value)}
              placeholder="+91 98XXXXXX00"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">Outbound Calling Window (IST)</label>
            <div className="flex items-center gap-2">
              <Input
                type="time"
                value={outboundStart}
                onChange={(e) => setOutboundStart(e.target.value)}
                className="w-full text-xs"
              />
              <span className="text-xs text-muted-foreground font-semibold">to</span>
              <Input
                type="time"
                value={outboundEnd}
                onChange={(e) => setOutboundEnd(e.target.value)}
                className="w-full text-xs"
              />
            </div>
            <span className="text-[10px] text-muted-foreground block">
              Default 9 AM to 8 PM IST. Server refuses calls outside window.
            </span>
          </div>
        </div>

        {/* Toggles */}
        <div className="pt-2 border-t border-border/60 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-semibold text-ink block">
                Immediate Stop on &ldquo;Wrong Number&rdquo;
              </span>
              <span className="text-[11px] text-muted-foreground">
                Permanently suppress follow-up calls if recipient states it is a wrong number.
              </span>
            </div>
            <Switch
              checked={autoStopOnWrongNumber}
              onCheckedChange={setAutoStopOnWrongNumber}
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-semibold text-ink block">
                Enforce AI Non-Denial Response
              </span>
              <span className="text-[11px] text-muted-foreground">
                Assistant always admits AI identity when asked and offers human owner escalation.
              </span>
            </div>
            <Switch
              checked={neverDenyAi}
              onCheckedChange={setNeverDenyAi}
            />
          </div>
        </div>
      </div>

      {/* Editable Price List Table */}
      <div className="p-5 sm:p-6 rounded-2xl border border-border bg-card shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Wrench className="w-5 h-5 text-primary" />
            <div>
              <h2 className="text-base font-bold text-ink">Service Rate Card (Price List)</h2>
              <p className="text-xs text-muted-foreground">
                Used by Evon v3.3 to quote price ranges during customer inbound bookings.
              </p>
            </div>
          </div>
        </div>

        {/* Add New Item Row */}
        <div className="p-4 rounded-xl border border-border/80 bg-muted/20 space-y-3">
          <span className="text-xs font-bold text-ink flex items-center gap-1.5">
            <Plus className="w-3.5 h-3.5 text-primary" />
            <span>Add New Service to Price List</span>
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
            <Input
              placeholder="Service Name (e.g. Geyser Descaling)"
              value={newItemName}
              onChange={(e) => setNewItemName(e.target.value)}
              className="text-xs sm:col-span-2"
            />
            <select
              aria-label="Service Category"
              value={newItemCategory}
              onChange={(e) => setNewItemCategory(e.target.value as PriceItem["category"])}
              className="h-8 rounded-lg border border-input bg-transparent px-2.5 py-1 text-xs text-foreground focus-visible:border-ring outline-none"
            >
              <option value="Plumbing">Plumbing</option>
              <option value="Geyser">Geyser</option>
              <option value="Motor">Motor</option>
              <option value="Drainage">Drainage</option>
              <option value="General">General</option>
            </select>
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground">Min ₹</span>
              <Input
                type="number"
                value={newItemMin}
                onChange={(e) => setNewItemMin(Number(e.target.value))}
                className="text-xs"
              />
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground">Max ₹</span>
              <Input
                type="number"
                value={newItemMax}
                onChange={(e) => setNewItemMax(Number(e.target.value))}
                className="text-xs"
              />
            </div>
          </div>
          <div className="flex justify-end pt-1">
            <Button size="sm" onClick={handleAddItem} className="gap-1.5 text-xs font-semibold">
              <Plus className="w-3.5 h-3.5" />
              <span>Add Service Rate</span>
            </Button>
          </div>
        </div>

        {/* Price Table */}
        <div className="rounded-xl border border-border overflow-hidden">
          <Table>
            <TableHeader className="bg-muted/40">
              <TableRow>
                <TableHead className="font-bold text-ink">Service</TableHead>
                <TableHead className="font-bold text-ink">Category</TableHead>
                <TableHead className="font-bold text-ink">Price Range</TableHead>
                <TableHead className="font-bold text-ink">Billing Unit</TableHead>
                <TableHead className="text-right font-bold text-ink">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {priceList.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-semibold text-ink text-xs">
                    {item.service_name}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-[10px]">
                      {item.category}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs font-bold text-emerald-700">
                    ₹{item.min_price} – ₹{item.max_price}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {item.unit}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      onClick={() => handleDeleteItem(item.id, item.service_name)}
                      className="text-muted-foreground hover:text-destructive"
                      aria-label={`Delete ${item.service_name}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
