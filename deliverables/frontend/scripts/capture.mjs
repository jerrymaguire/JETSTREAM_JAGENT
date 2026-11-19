import { chromium } from "playwright-core";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..", "..", "..");
const screenshots = path.join(root, "screenshots");
await mkdir(screenshots, { recursive: true });

const executablePath =
  process.env.PLAYWRIGHT_CHROME ??
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

const browser = await chromium.launch({ executablePath, headless: true });
const errors = [];
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 1,
});
const page = await context.newPage();
page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(`console: ${message.text()}`);
});

await page.goto("http://127.0.0.1:8000/", { waitUntil: "networkidle" });
if ((await page.locator(".session-item").count()) === 0) {
  await page.evaluate(async () => {
    await fetch("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "JAgent 演示会话" }),
    });
  });
  await page.reload({ waitUntil: "networkidle" });
}
await page.locator(".session-item").first().waitFor();
await page.screenshot({
  path: path.join(screenshots, "agentshow-desktop-chat.png"),
  fullPage: true,
});

await page.locator(".skill-trigger").click();
await page.locator(".skill-popover").waitFor();
await page.screenshot({
  path: path.join(screenshots, "agentshow-skills.png"),
  fullPage: true,
});
await page.locator(".skill-trigger").click();

await page.getByRole("button", { name: "切换主题" }).click();
await page.waitForTimeout(150);
await page.screenshot({
  path: path.join(screenshots, "agentshow-desktop-light.png"),
  fullPage: true,
});
await page.getByRole("button", { name: "切换主题" }).click();
await page.waitForTimeout(150);

await page.getByRole("button", { name: /轨迹/ }).click();
await page.getByText("调用轨迹").waitFor();
await page.screenshot({
  path: path.join(screenshots, "agentshow-desktop-trace.png"),
  fullPage: true,
});

await page.getByRole("button", { name: /搜索名称/ }).click().catch(() => {});
const traceRows = page.locator(".trace-row");
if ((await traceRows.count()) > 2) {
  await traceRows.nth(2).click();
}
await page.screenshot({
  path: path.join(screenshots, "agentshow-desktop-inspector.png"),
  fullPage: true,
});

const mobile = await browser.newContext({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 1,
});
const mobilePage = await mobile.newPage();
mobilePage.on("pageerror", (error) => errors.push(`mobile pageerror: ${error.message}`));
await mobilePage.goto("http://127.0.0.1:8000/", { waitUntil: "networkidle" });
await mobilePage.locator(".app-shell").waitFor();
await mobilePage.locator(".session-item").first().waitFor();
await mobilePage.getByRole("button", { name: "打开会话栏" }).click();
await mobilePage.locator(".session-sidebar").waitFor();
await mobilePage.waitForTimeout(250);
await mobilePage.screenshot({
  path: path.join(screenshots, "agentshow-mobile.png"),
  fullPage: true,
});

await mobile.close();
await context.close();
await browser.close();

console.log(
  JSON.stringify(
    {
      screenshot_dir: screenshots,
      errors,
    },
    null,
    2,
  ),
);

