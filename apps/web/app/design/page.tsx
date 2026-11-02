import type { Metadata } from "next";
import { DesignPageClient } from "./design-client";

export const metadata: Metadata = {
  title: "Design QA",
  description: "Visual QA page — design tokens, type scale, components.",
};

/**
 * /design — visual quality assurance page.
 * Server wrapper; all interactive demos live in DesignPageClient.
 */
export default function DesignPage() {
  return <DesignPageClient />;
}

