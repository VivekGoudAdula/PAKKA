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
    await new Promise((r) => setTimeout(r, 800));
  }
  return false;
}

const ROUTES = [
  { path: "/app", slug: "overview" },
  { path: "/app/calls", slug: "calls" },
  { path: "/app/jobs", slug: "jobs" },
  { path: "/app/technicians", slug: "technicians" },
  { path: "/app/payments", slug: "payments" },
  { path: "/app/settings", slug: "settings" },
];

const VIEWPORTS = [
  { name: "360px", width: 360, height: 800 },
  { name: "768px", width: 768, height: 1024 },
  { name: "1440px", width: 1440, height: 900 },
];

async function main() {
  console.log("Building Next.js application first for clean production run...");
  // Check if build is needed or start dev
  console.log("Starting Next.js server on port 3005...");
  const server = spawn("pnpm.cmd", ["exec", "next", "start", "-p", "3005"], {
    cwd: webDir,
    stdio: "inherit",
    shell: true,
  });

  try {
    const ready = await waitServerReady("http://127.0.0.1:3005/app", 35000);
    if (!ready) {
      throw new Error("Server failed to respond at http://127.0.0.1:3005/app within timeout");
    }
    console.log("Next.js server is ready at http://127.0.0.1:3005");

    let browser;
    try {
      browser = await chromium.launch({ channel: "chrome", headless: true });
    } catch {
      console.log("Chrome channel failed, trying msedge...");
      browser = await chromium.launch({ channel: "msedge", headless: true });
    }

    let allPass = true;

    for (const route of ROUTES) {
      console.log(`\n=== Testing route: ${route.path} (${route.slug}) ===`);
      for (const vp of VIEWPORTS) {
        const context = await browser.newContext({
          viewport: { width: vp.width, height: vp.height },
          deviceScaleFactor: 2,
        });
        const page = await context.newPage();
        await page.goto(`http://127.0.0.1:3005${route.path}`, { waitUntil: "networkidle" });
        await page.waitForTimeout(800);

        // Check horizontal overflow
        const overflow = await page.evaluate(() => {
          return document.documentElement.scrollWidth > window.innerWidth;
        });

        if (overflow) {
          console.error(`[OVERFLOW ERROR] ${route.slug} at ${vp.name}: horizontal overflow detected!`);
          allPass = false;
        } else {
          console.log(`[PASS] ${route.slug} at ${vp.name}: no horizontal overflow.`);
        }

        const outPath = path.join(screenshotsDir, `${route.slug}-${vp.name}.png`);
        await page.screenshot({ path: outPath, fullPage: true });
        console.log(`  Saved: ${outPath}`);
        await context.close();
      }
    }

    await browser.close();
    if (!allPass) {
      throw new Error("Some viewports had horizontal overflow issues!");
    }
    console.log("\nAll 6 screens captured at 360, 768, and 1440 px with zero horizontal overflow!");
    process.exit(0);
  } finally {
    try {
      server.kill();
    } catch {}
  }
}

main().catch((err) => {
  console.error("Screenshot capture failed:", err);
  process.exit(1);
});
