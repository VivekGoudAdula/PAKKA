import { chromium } from "../apps/web/node_modules/playwright/index.mjs";
import { spawn } from "child_process";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const screenshotsDir = path.resolve(__dirname, "../docs/screenshots");
const webDir = path.resolve(__dirname, "../apps/web");

if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir, { recursive: true });
}

async function waitServerReady(url, maxWaitMs = 35000) {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    try {
      const res = await fetch(url);
      if (res.ok) return true;
    } catch {
      // not ready yet
    }
    await new Promise((r) => setTimeout(r, 600));
  }
  return false;
}

const RESPONSIVE_ROUTES = [
  { path: "/", slug: "landing" },
  { path: "/app/live", slug: "live-director" },
  { path: "/app/payments", slug: "payments-director" },
  { path: "/app/metrics", slug: "metrics-phase7" },
];

const VIEWPORTS = [
  { name: "360px", width: 360, height: 800 },
  { name: "768px", width: 768, height: 1024 },
  { name: "1440px", width: 1440, height: 900 },
];

const BEATS = [
  { beat: 1, route: "/app/live?beat=1", slug: "beat_1_customer_call" },
  { beat: 2, route: "/app/live?beat=2", slug: "beat_2_booking_confirmed" },
  { beat: 3, route: "/app/live?beat=3", slug: "beat_3_auto_dispatch" },
  { beat: 4, route: "/app/live?beat=4", slug: "beat_4_tech_acceptance" },
  { beat: 5, route: "/app/payments?beat=5", slug: "beat_5_payment_collection" },
];

async function main() {
  console.log("Starting Next.js server on port 3007 for Phase 7 screenshots...");
  const server = spawn("pnpm.cmd", ["exec", "next", "start", "-p", "3007", "-H", "127.0.0.1"], {
    cwd: webDir,
    stdio: "inherit",
    shell: true,
  });

  try {
    const ready = await waitServerReady("http://127.0.0.1:3007/app", 35000);
    if (!ready) {
      throw new Error("Server failed to respond at http://127.0.0.1:3007/app within timeout");
    }
    console.log("Next.js server is ready at http://127.0.0.1:3007");

    let browser;
    try {
      browser = await chromium.launch({ channel: "chrome", headless: true });
    } catch {
      console.log("Chrome channel failed, trying msedge...");
      browser = await chromium.launch({ channel: "msedge", headless: true });
    }

    // 1. Responsive screenshots (360, 768, 1440 px)
    for (const r of RESPONSIVE_ROUTES) {
      for (const vp of VIEWPORTS) {
        const page = await browser.newPage({
          viewport: { width: vp.width, height: vp.height },
          deviceScaleFactor: 2,
        });

        const targetUrl = `http://127.0.0.1:3007${r.path}`;
        console.log(`Capturing ${r.slug} at ${vp.name} -> ${targetUrl}`);
        await page.goto(targetUrl, { waitUntil: "networkidle" });
        await page.waitForTimeout(600);

        const screenshotPath = path.join(screenshotsDir, `${r.slug}-${vp.name}.png`);
        await page.screenshot({ path: screenshotPath, fullPage: false });
        console.log(`Saved: ${screenshotPath}`);
        await page.close();
      }
    }

    // 2. 1920x1080 px for each of the 5 Demo Director beats
    for (const beat of BEATS) {
      const page = await browser.newPage({
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1,
      });

      const targetUrl = `http://127.0.0.1:3007${beat.route}`;
      console.log(`Capturing 1080p Beat ${beat.beat}: ${beat.slug} -> ${targetUrl}`);
      await page.goto(targetUrl, { waitUntil: "networkidle" });
      await page.waitForTimeout(1000);

      const screenshotPath = path.join(screenshotsDir, `${beat.slug}-1080p.png`);
      await page.screenshot({ path: screenshotPath, fullPage: false });
      console.log(`Saved: ${screenshotPath}`);
      await page.close();
    }

    await browser.close();
    console.log("All Phase 7 screenshots captured successfully!");
  } finally {
    console.log("Shutting down Next.js server...");
    server.kill("SIGTERM");
  }
}

main().catch((err) => {
  console.error("Screenshot capture failed:", err);
  process.exit(1);
});
