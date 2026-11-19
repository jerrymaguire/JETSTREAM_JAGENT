import { chromium } from "playwright-core";

const browser = await chromium.launch({
  executablePath:
    process.env.PLAYWRIGHT_CHROME ??
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  headless: true,
});
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));

await page.goto("http://127.0.0.1:8000/", { waitUntil: "networkidle" });
const created = await page.evaluate(async () => {
  const response = await fetch("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: "临时会话" }),
  });
  return response.json();
});
await page.reload({ waitUntil: "networkidle" });

let item = page.locator(".session-item", { hasText: "临时会话" });
await item.waitFor();
await item.hover();
await item.getByRole("button", { name: "重命名对话" }).click();
const input = page.locator(".session-title-input");
await input.fill("手动命名测试");
await input.press("Enter");
await page.getByText("手动命名测试").first().waitFor();

item = page.locator(".session-item", { hasText: "手动命名测试" });
page.once("dialog", (dialog) => dialog.accept());
await item.hover();
await item.getByRole("button", { name: "删除对话" }).click();
await page.waitForTimeout(300);
if ((await page.getByText("手动命名测试").count()) !== 0) {
  throw new Error("Renamed session was not removed");
}

await browser.close();
console.log(JSON.stringify({ ok: true, created_session: created.id, errors }, null, 2));

