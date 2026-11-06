import { chromium } from "../apps/web/node_modules/playwright/index.mjs";
import { spawn } from "child_process";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const screenshotsDir = path.resolve(__dirname, "../docs/screenshots");
const webDir = path.resolve(__dirname, "../apps/web");
const apiDir = path.resolve(__dirname, "../apps/api");

if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir, { recursive: true });
}

async function waitServerReady(url, maxWaitMs = 40000) {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    try {
      const res = await fetch(url);
      if (res.ok) return true;
    } catch {
      // Wait
    }
    await new Promise((r) => setTimeout(r, 600));
  }
  return false;
}

const VIEWPORTS = [
  { name: "360px", width: 360, height: 800 },
  { name: "768px", width: 768, height: 1024 },
  { name: "1440px", width: 1440, height: 900 },
];

async function main() {
  console.log("Starting backend on port 8000...");
  const apiServer = spawn(".venv\\Scripts\\python.exe", ["-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1"], {
    cwd: apiDir,
    stdio: "inherit",
    shell: true,
  });

  console.log("Starting Next.js on port 3008 for Phase 8 screenshots...");
  const webServer = spawn("pnpm.cmd", ["exec", "next", "start", "-p", "3008", "-H", "127.0.0.1"], {
    cwd: webDir,
    stdio: "inherit",
    shell: true,
  });

  try {
    const apiReady = await waitServerReady("http://127.0.0.1:8000/health", 30000);
    const webReady = await waitServerReady("http://127.0.0.1:3008/app/talk", 35000);

    if (!webReady) {
      throw new Error("Web server did not become ready in time.");
    }
    console.log(`Servers ready! API: ${apiReady ? "OK" : "TIMEOUT"}, Web: OK`);

    let browser;
    try {
      browser = await chromium.launch({ channel: "chrome", headless: true });
    } catch {
      console.log("Chrome channel failed, trying msedge...");
      browser = await chromium.launch({ channel: "msedge", headless: true });
    }
    const context = await browser.newContext();

    // 1. Capture Idle Responsive Screens
    for (const vp of VIEWPORTS) {
      console.log(`Capturing /app/talk at ${vp.name}...`);
      const page = await context.newPage();
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("http://127.0.0.1:3008/app/talk", { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(1200);

      const filePath = path.join(screenshotsDir, `phase8_talk_${vp.name}.png`);
      await page.screenshot({ path: filePath, fullPage: false });
      console.log(`Saved: ${filePath}`);
      await page.close();
    }

    // 2. Interactive Booking Turn
    {
      console.log("Capturing conversation state on 1440px...");
      const page = await context.newPage();
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto("http://127.0.0.1:3008/app/talk", { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(1200);

      // Open typed input and type message
      const typeBtn = page.getByRole("button", { name: "Type instead" });
      if (await typeBtn.isVisible()) {
        await typeBtn.click();
      }

      const input = page.locator("input[placeholder*='Hinglish']");
      await input.fill("Mera geyser se paani tapak raha hai neeche se");
      await page.locator("button[type='submit']").click();
      await page.waitForTimeout(1500);

      const filePath = path.join(screenshotsDir, "phase8_talk_conversation_1440px.png");
      await page.screenshot({ path: filePath, fullPage: false });
      console.log(`Saved: ${filePath}`);
      await page.close();
    }

    // 3. Emergency Hazard State
    {
      console.log("Capturing emergency danger hazard banner...");
      const page = await context.newPage();
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto("http://127.0.0.1:3008/app/talk", { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(1200);

      const typeBtn = page.getByRole("button", { name: "Type instead" });
      if (await typeBtn.isVisible()) {
        await typeBtn.click();
      }

      const input = page.locator("input[placeholder*='Hinglish']");
      await input.fill("Geyser mein current aa raha hai shock lag raha");
      await page.locator("button[type='submit']").click();
      await page.waitForTimeout(1500);

      const filePath = path.join(screenshotsDir, "phase8_talk_emergency_1440px.png");
      await page.screenshot({ path: filePath, fullPage: false });
      console.log(`Saved: ${filePath}`);
      await page.close();
    }

    // 4. Collection Flow
    {
      console.log("Capturing collection flow state...");
      const page = await context.newPage();
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto("http://127.0.0.1:3008/app/talk", { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(1200);

      const colTab = page.getByRole("tab", { name: "Payment Reminder" });
      await colTab.click();
      await page.waitForTimeout(1000);

      const filePath = path.join(screenshotsDir, "phase8_talk_collection_1440px.png");
      await page.screenshot({ path: filePath, fullPage: false });
      console.log(`Saved: ${filePath}`);
      await page.close();
    }

    await browser.close();
    console.log("Phase 8 screenshots captured successfully!");
  } finally {
    try {
      webServer.kill();
    } catch {}
    try {
      apiServer.kill();
    } catch {}
    if (webServer.pid) {
      spawn("taskkill", ["/F", "/PID", String(webServer.pid), "/T"]);
    }
    if (apiServer.pid) {
      spawn("taskkill", ["/F", "/PID", String(apiServer.pid), "/T"]);
    }
  }
}

main().catch((err) => {
  console.error("Screenshot capture failed:", err);
  process.exit(1);
});
