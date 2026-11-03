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

const VIEWPORTS = [
  { name: "360px", width: 360, height: 800 },
  { name: "768px", width: 768, height: 1024 },
  { name: "1440px", width: 1440, height: 900 },
];

async function main() {
  console.log("Starting Next.js server on port 3006...");
  const server = spawn("pnpm.cmd", ["exec", "next", "start", "-p", "3006"], {
    cwd: webDir,
    stdio: "inherit",
    shell: true,
  });

  try {
    const ready = await waitServerReady("http://127.0.0.1:3006/app/live", 35000);
    if (!ready) {
      throw new Error("Server failed to respond at http://127.0.0.1:3006/app/live within timeout");
    }
    console.log("Next.js server is ready at http://127.0.0.1:3006");

    let browser;
    try {
      browser = await chromium.launch({ channel: "chrome", headless: true });
    } catch {
      console.log("Chrome channel failed, trying msedge...");
      browser = await chromium.launch({ channel: "msedge", headless: true });
    }

    let allPass = true;

    for (const vp of VIEWPORTS) {
      console.log(`\n=== Capturing /app/live at ${vp.name} ===`);
      const context = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
        deviceScaleFactor: 2,
      });
      const page = await context.newPage();
      await page.goto("http://127.0.0.1:3006/app/live", { waitUntil: "networkidle" });

      // 1. Mid-call capture (after ~10 seconds of simulated dialogue)
      console.log("  Waiting for mid-call state (dialogue streaming)...");
      await page.waitForTimeout(10000);

      // Check horizontal overflow
      const overflowMid = await page.evaluate(() => {
        return document.documentElement.scrollWidth > window.innerWidth;
      });

      if (overflowMid) {
        console.error(`[OVERFLOW ERROR] live-midcall at ${vp.name}: horizontal overflow detected!`);
        allPass = false;
      } else {
        console.log(`[PASS] live-midcall at ${vp.name}: no horizontal overflow.`);
      }

      const midPath = path.join(screenshotsDir, `live-midcall-${vp.name}.png`);
      await page.screenshot({ path: midPath, fullPage: true });
      console.log(`  Saved: ${midPath}`);

      // 2. Booked + Dispatched capture (after ~18 more seconds when stamp & dispatch complete)
      console.log("  Waiting for booking + dispatch complete state...");
      await page.waitForTimeout(18000);

      const overflowEnd = await page.evaluate(() => {
        return document.documentElement.scrollWidth > window.innerWidth;
      });

      if (overflowEnd) {
        console.error(`[OVERFLOW ERROR] live-dispatched at ${vp.name}: horizontal overflow detected!`);
        allPass = false;
      } else {
        console.log(`[PASS] live-dispatched at ${vp.name}: no horizontal overflow.`);
      }

      const endPath = path.join(screenshotsDir, `live-dispatched-${vp.name}.png`);
      await page.screenshot({ path: endPath, fullPage: true });
      console.log(`  Saved: ${endPath}`);

      await context.close();
    }

    await browser.close();

    if (!allPass) {
      console.error("\n[FAIL] Visual verification failed on one or more viewports.");
      process.exit(1);
    } else {
      console.log("\n[SUCCESS] All viewports verified and screenshots saved to docs/screenshots/!");
    }
  } finally {
    console.log("Stopping Next.js server...");
    server.kill("SIGINT");
    if (process.platform === "win32") {
      try {
        spawn("taskkill", ["/pid", server.pid.toString(), "/f", "/t"]);
      } catch {
        // ignore
      }
    }
  }
}

main().catch((err) => {
  console.error("Fatal screenshot runner error:", err);
  process.exit(1);
});
