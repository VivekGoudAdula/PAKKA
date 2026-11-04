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
  console.log("Starting Next.js server on port 3007...");
  const server = spawn("pnpm.cmd", ["exec", "next", "start", "-p", "3007"], {
    cwd: webDir,
    stdio: "inherit",
    shell: true,
  });

  try {
    const ready = await waitServerReady("http://127.0.0.1:3007/app/payments", 35000);
    if (!ready) {
      throw new Error("Server failed to respond at http://127.0.0.1:3007/app/payments within timeout");
    }
    console.log("Next.js server is ready at http://127.0.0.1:3007");

    let browser;
    try {
      browser = await chromium.launch({ channel: "chrome", headless: true });
    } catch {
      console.log("Chrome channel failed, trying msedge...");
      browser = await chromium.launch({ channel: "msedge", headless: true });
    }

    let allPass = true;

    for (const vp of VIEWPORTS) {
      console.log(`\n=== Capturing /app/payments at ${vp.name} ===`);
      const context = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
        deviceScaleFactor: 2,
      });
      const page = await context.newPage();
      await page.goto("http://127.0.0.1:3007/app/payments", { waitUntil: "networkidle" });
      await page.waitForTimeout(1000);

      // Check overflow helper
      const checkOverflow = async (label) => {
        const hasOverflow = await page.evaluate(() => {
          return document.documentElement.scrollWidth > window.innerWidth;
        });
        if (hasOverflow) {
          console.error(`[OVERFLOW ERROR] ${label} at ${vp.name}: horizontal overflow detected!`);
          allPass = false;
        } else {
          console.log(`[PASS] ${label} at ${vp.name}: no horizontal overflow.`);
        }
      };

      // 1. Initial State (base date)
      await checkOverflow("payments-initial");
      const initialPath = path.join(screenshotsDir, `payments-initial-${vp.name}.png`);
      await page.screenshot({ path: initialPath, fullPage: true });
      console.log(`  Saved: ${initialPath}`);

      // 2. Advance +1 Day
      console.log("  Advancing clock +1 Day...");
      const plusOneBtn = page.getByRole("button", { name: "+1 Day" });
      if (await plusOneBtn.isVisible()) {
        await plusOneBtn.click();
        await page.waitForTimeout(600);
      }
      await checkOverflow("payments-plus1day");
      const plus1Path = path.join(screenshotsDir, `payments-plus1day-${vp.name}.png`);
      await page.screenshot({ path: plus1Path, fullPage: true });
      console.log(`  Saved: ${plus1Path}`);

      // 3. Advance +2 Days
      console.log("  Advancing clock +2 Days...");
      const plusTwoBtn = page.getByRole("button", { name: "+2 Days" });
      if (await plusTwoBtn.isVisible()) {
        await plusTwoBtn.click();
        await page.waitForTimeout(600);
      }
      await checkOverflow("payments-plus2days");
      const plus2Path = path.join(screenshotsDir, `payments-plus2days-${vp.name}.png`);
      await page.screenshot({ path: plus2Path, fullPage: true });
      console.log(`  Saved: ${plus2Path}`);

      // 4. Open Trail Dialog on 1440px
      if (vp.name === "1440px") {
        const trailBtn = page.getByRole("button", { name: /Trail/ }).first();
        if (await trailBtn.isVisible()) {
          await trailBtn.click();
          await page.waitForTimeout(500);
          const trailPath = path.join(screenshotsDir, `payments-trail-dialog-${vp.name}.png`);
          await page.screenshot({ path: trailPath });
          console.log(`  Saved: ${trailPath}`);
        }
      }

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
