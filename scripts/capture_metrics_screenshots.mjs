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
  console.log("Starting Next.js server on port 3008...");
  const server = spawn("pnpm.cmd", ["exec", "next", "start", "-p", "3008"], {
    cwd: webDir,
    stdio: "inherit",
    shell: true,
  });

  try {
    const ready = await waitServerReady("http://127.0.0.1:3008/app/metrics", 35000);
    if (!ready) {
      throw new Error("Server failed to respond at http://127.0.0.1:3008/app/metrics within timeout");
    }
    console.log("Next.js server is ready at http://127.0.0.1:3008");

    let browser;
    try {
      browser = await chromium.launch({ headless: true });
    } catch (launchErr) {
      console.log("Standard launch failed, trying executable paths...", launchErr.message);
      const possiblePaths = [
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
      ];
      for (const p of possiblePaths) {
        if (fs.existsSync(p)) {
          browser = await chromium.launch({ headless: true, executablePath: p });
          break;
        }
      }
    }

    if (!browser) {
      throw new Error("Could not launch Chromium or system browser.");
    }

    for (const vp of VIEWPORTS) {
      console.log(`Capturing /app/metrics at ${vp.width}x${vp.height} (${vp.name})...`);
      const context = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
        deviceScaleFactor: 1,
      });
      const page = await context.newPage();
      await page.goto("http://127.0.0.1:3008/app/metrics", { waitUntil: "domcontentloaded", timeout: 15000 });
      await page.waitForTimeout(2000);

      const shotPath = path.join(screenshotsDir, `metrics-${vp.name}.png`);
      await page.screenshot({ path: shotPath, fullPage: true });
      console.log(`Saved screenshot: ${shotPath}`);
      await context.close();
    }

    await browser.close();
    console.log("All screenshots captured successfully!");
  } finally {
    console.log("Shutting down Next.js server...");
    try {
      spawn("taskkill", ["/pid", server.pid.toString(), "/f", "/t"]);
    } catch {
      // ignore
    }
  }
}

main().catch((err) => {
  console.error("Screenshot error:", err);
  process.exit(1);
});

