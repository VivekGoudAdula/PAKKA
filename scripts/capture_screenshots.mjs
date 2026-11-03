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

async function waitServerReady(url, maxWaitMs = 30000) {
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

async function main() {
  console.log("Starting Next.js production server for screenshots...");
  const server = spawn("pnpm.cmd", ["start", "-p", "3005"], {
    cwd: webDir,
    stdio: "inherit",
    shell: true,
  });

  try {
    const ready = await waitServerReady("http://127.0.0.1:3005/design", 35000);
    if (!ready) {
      throw new Error("Server failed to respond at http://127.0.0.1:3005/design within timeout");
    }
    console.log("Next.js server is ready at http://127.0.0.1:3005/design");

    // Launch browser using system Chrome or Edge
    let browser;
    try {
      browser = await chromium.launch({ channel: "chrome", headless: true });
    } catch {
      console.log("Chrome channel failed, trying msedge...");
      browser = await chromium.launch({ channel: "msedge", headless: true });
    }

    const viewports = [
      { name: "360px", width: 360, height: 800 },
      { name: "768px", width: 768, height: 1024 },
      { name: "1440px", width: 1440, height: 900 },
    ];

    for (const vp of viewports) {
      console.log(`Capturing viewport: ${vp.name} (${vp.width}x${vp.height})...`);
      const context = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
        deviceScaleFactor: 2,
      });
      const page = await context.newPage();
      await page.goto("http://127.0.0.1:3005/design", { waitUntil: "networkidle" });
      await page.waitForTimeout(1000);

      // Check horizontal overflow
      const overflow = await page.evaluate(() => {
        return document.documentElement.scrollWidth > window.innerWidth;
      });
      console.log(`Viewport ${vp.name} horizontal overflow: ${overflow ? "DETECTED!" : "NONE (PASS)"}`);

      const outPath = path.join(screenshotsDir, `design-${vp.name}.png`);
      await page.screenshot({ path: outPath, fullPage: true });
      console.log(`Saved screenshot to: ${outPath}`);
      await context.close();
    }

    await browser.close();
    console.log("All screenshots captured successfully!");
    if (server.pid) {
      process.kill(-server.pid, "SIGTERM").catch(() => {});
    }
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
