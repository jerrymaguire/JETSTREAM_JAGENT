import { chromium } from "../../deliverables/frontend/node_modules/playwright-core/index.mjs";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..", "..");
const reports = path.join(root, "test", "reports");
await mkdir(reports, { recursive: true });

const baseUrl = "http://127.0.0.1:8000";
const chromePath =
  process.env.PLAYWRIGHT_CHROME ??
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

const errors = [];
let sessionId = "";
let browser;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function api(pathname, options = {}) {
  const response = await fetch(`${baseUrl}${pathname}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`${pathname} failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

try {
  browser = await chromium.launch({ executablePath: chromePath, headless: true });
  const desktop = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  });
  const page = await desktop.newPage();
  page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`console: ${message.text()}`);
  });

  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.locator(".app-shell").waitFor();
  assert(
    (await page.locator(".brand strong").innerText()).trim().toLowerCase() === "jagent",
    "JAgent brand is not rendered",
  );

  const created = await api("/api/sessions", {
    method: "POST",
    body: JSON.stringify({ title: "E2E 自动测试" }),
  });
  sessionId = created.id;
  await api(`/api/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({
      content: "请回复一条用于 E2E 测试的示例消息",
      skills: ["software-delivery-frontend"],
    }),
  });

  let trace;
  for (let attempt = 0; attempt < 50; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 200));
    trace = await api(`/api/sessions/${sessionId}/trace`);
    if (trace.spans.length >= 2) break;
  }
  assert(trace && trace.spans.length >= 2, "Trace was not generated");
  assert(trace.summary.call_count >= 2, "Trace call count is incorrect");
  let sessionDetail;
  for (let attempt = 0; attempt < 50; attempt += 1) {
    sessionDetail = await api(`/api/sessions/${sessionId}`);
    if (sessionDetail.messages.some((message) => message.role === "assistant")) break;
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  assert(
    sessionDetail?.messages.some((message) => message.role === "assistant"),
    "Assistant message was not persisted",
  );

  await page.reload({ waitUntil: "networkidle" });
  let sessionItem = page.locator(".session-item", { hasText: "E2E 自动测试" });
  await sessionItem.waitFor();
  await sessionItem.click();
  const composer = page.locator(".composer textarea");
  await composer.fill("@software-delivery-pm");
  const mention = page.locator(".mention-item").filter({
    has: page.getByText("software-delivery-pm", { exact: true }),
  });
  await mention.waitFor();
  await mention.click();
  await page.locator(".skill-chip", { hasText: "software-delivery-pm" }).waitFor();
  await page.locator(".skill-trigger").click();
  assert((await page.locator(".skill-option").count()) >= 10, "Default skills were not loaded");
  assert(
    (await page.locator('.skill-path-form input[placeholder*="SKILL.md"]').count()) === 1,
    "Skill path input is missing",
  );
  await page.locator(".skill-trigger").click();
  assert(
    (await page.locator('.hidden-file-input').getAttribute("accept")).includes(".docx"),
    "Document import accepts Word files",
  );
  await page.locator(".message-row.assistant").first().waitFor();
  await page.locator(".message-export-actions").first().waitFor();
  await page.locator(".message-row.assistant").first().hover();
  assert(
    (await page.locator(".message-export-actions button").count()) >= 3,
    "Assistant export actions are missing",
  );

  await page.getByRole("button", { name: /轨迹/ }).click();
  await page.getByText("调用轨迹").waitFor();
  await page.getByText("Token 速度").waitFor();
  assert((await page.locator(".trace-row").count()) >= 2, "Trace rows are missing");
  await page.locator(".trace-row").first().click();
  assert((await page.locator(".inspector").innerText()).includes("Span ID"), "Inspector is missing Span ID");

  sessionItem = page.locator(".session-item", { hasText: "E2E 自动测试" });
  await sessionItem.hover();
  await sessionItem.getByRole("button", { name: "重命名对话" }).click();
  const titleInput = page.locator(".session-title-input");
  await titleInput.fill("E2E 重命名成功");
  await titleInput.press("Enter");
  await page.getByText("E2E 重命名成功").first().waitFor();

  await page.screenshot({
    path: path.join(reports, "e2e-desktop.png"),
    fullPage: true,
  });

  sessionItem = page.locator(".session-item", { hasText: "E2E 重命名成功" });
  page.once("dialog", (dialog) => dialog.accept());
  await sessionItem.hover();
  await sessionItem.getByRole("button", { name: "删除对话" }).click();
  await page.waitForTimeout(300);
  assert((await page.getByText("E2E 重命名成功").count()) === 0, "Session was not deleted");
  sessionId = "";

  const mobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 1,
  });
  const mobilePage = await mobile.newPage();
  mobilePage.on("pageerror", (error) => errors.push(`mobile pageerror: ${error.message}`));
  await mobilePage.goto(baseUrl, { waitUntil: "networkidle" });
  await mobilePage.getByRole("button", { name: "打开会话栏" }).click();
  await mobilePage.locator(".session-sidebar").waitFor();
  const overflow = await mobilePage.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 1,
  );
  assert(!overflow, "Mobile page has horizontal overflow");
  await mobilePage.screenshot({
    path: path.join(reports, "e2e-mobile.png"),
    fullPage: true,
  });

  await mobile.close();
  await desktop.close();
  assert(errors.length === 0, `Browser errors: ${errors.join("; ")}`);

  const summary = {
    status: "passed",
    session_trace_calls: trace.summary.call_count,
    desktop_screenshot: path.join(reports, "e2e-desktop.png"),
    mobile_screenshot: path.join(reports, "e2e-mobile.png"),
    browser_errors: errors,
  };
  await writeFile(path.join(reports, "e2e-summary.json"), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary, null, 2));
} catch (error) {
  if (sessionId) {
    await fetch(`${baseUrl}/api/sessions/${sessionId}`, { method: "DELETE" }).catch(() => {});
  }
  const summary = {
    status: "failed",
    error: error instanceof Error ? error.message : String(error),
    browser_errors: errors,
  };
  await writeFile(path.join(reports, "e2e-summary.json"), JSON.stringify(summary, null, 2));
  console.error(JSON.stringify(summary, null, 2));
  process.exitCode = 1;
} finally {
  await browser?.close();
}

