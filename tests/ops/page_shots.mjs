// Renders the review pages in headless Chrome and saves what a reviewer would see.
//
//   node tests/ops/page_shots.mjs --url http://127.0.0.1:8085 --out DIR [--case CASE_ID]
//
// For each page (queue, one case, attempt log, report), at phone (390 px) and laptop (1280 px)
// width, in light and dark: a full-page PNG. Once per page: the rendered HTML. The report is also
// printed to PDF, and shown as a PNG at A4 width with print styles (report-print.png). Prints one JSON line per render with any horizontal overflow, console errors and
// banned words found in the page text, and exits 1 if any render has one. Needs Node 22+ and Chrome.

import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const args = Object.fromEntries(
  process.argv.slice(2).reduce((pairs, arg, i, all) => {
    if (arg.startsWith("--")) pairs.push([arg.slice(2), all[i + 1] ?? "1"]);
    return pairs;
  }, []),
);
const url = args.url ?? "http://127.0.0.1:8085";
const out = args.out ?? "p3b-shots";
mkdirSync(out, { recursive: true });
const chrome = process.env.CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const port = 9800 + Math.floor(Math.random() * 150);
const profile = mkdtempSync(join(tmpdir(), "samajh-shots-"));
const browser = spawn(
  chrome,
  ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--no-first-run", "about:blank"],
  { stdio: "ignore" },
);
const sleep = (ms) => new Promise((done) => setTimeout(done, ms));
// Mirrors samajh/ops/wording.py BANNED.
const BANNED = [/mis[\s-]?s(?:ell|old)/i, /\brefund/i, /\bviolat/i, /\bbreach/i, /\bfraud/i, /\bguilty\b/i, /\bverdict/i, /\bproven\b/i, /\bnon[\s-]?compliant/i];

async function connect() {
  for (let i = 0; i < 100; i++) {
    try {
      const page = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page");
      if (page) {
        const socket = new WebSocket(page.webSocketDebuggerUrl);
        await new Promise((done, fail) => ((socket.onopen = done), (socket.onerror = fail)));
        return socket;
      }
    } catch {
      /* Chrome is still starting */
    }
    await sleep(100);
  }
  throw new Error("Chrome did not open a debugging port");
}

const socket = await connect();
let nextId = 0;
const waiting = new Map();
let errors = [];
socket.onmessage = (event) => {
  const m = JSON.parse(event.data);
  if (m.id && waiting.has(m.id)) {
    waiting.get(m.id)(m);
    waiting.delete(m.id);
  } else if (m.method === "Runtime.exceptionThrown") {
    errors.push(m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text);
  } else if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") {
    errors.push(m.params.args.map((a) => a.value ?? a.description).join(" "));
  }
};
const send = (method, params = {}) =>
  new Promise((done) => {
    const id = ++nextId;
    waiting.set(id, done);
    socket.send(JSON.stringify({ id, method, params }));
  });
const evaluate = async (expression) => (await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true })).result?.result?.value;

await send("Runtime.enable");
await send("Page.enable");
const caseId = args.case ?? (await (await fetch(`${url}/api/review/queue`)).json()).items[0].case_id;
const pages = [
  ["queue", "review/index.html"],
  ["case", `review/case.html?id=${encodeURIComponent(caseId)}`],
  ["attempts", "review/attempts.html"],
  ["report", "review/report.html"],
];
let failed = false;
for (const [name, path] of pages) {
  for (const width of [390, 1280]) {
    for (const scheme of ["light", "dark"]) {
      errors = [];
      await send("Emulation.setDeviceMetricsOverride", { width, height: 900, deviceScaleFactor: 1, mobile: width < 700 });
      await send("Emulation.setEmulatedMedia", { media: "screen", features: [{ name: "prefers-color-scheme", value: scheme }] });
      await send("Page.navigate", { url: `${url}/${path}` });
      for (let i = 0; i < 100 && !(await evaluate("!!document.querySelector('main h1')")); i++) await sleep(100);
      await sleep(300);
      const overflow = await evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth");
      const text = await evaluate("document.body.innerText");
      const banned = BANNED.filter((re) => re.test(text)).map(String);
      const simulated = /simulated/i.test(text);
      const shot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
      writeFileSync(join(out, `${name}-${width}-${scheme}.png`), Buffer.from(shot.result.data, "base64"));
      if (width === 1280 && scheme === "light") {
        writeFileSync(join(out, `${name}.html`), await evaluate("'<!doctype html>\\n' + document.documentElement.outerHTML"));
      }
      const bad = overflow > 0 || errors.length > 0 || banned.length > 0 || !simulated;
      failed ||= bad;
      console.log(JSON.stringify({ page: name, width, scheme, overflow, errors, banned, simulated }));
    }
  }
}
await send("Emulation.setEmulatedMedia", { media: "print" });
await send("Page.navigate", { url: `${url}/review/report.html` });
for (let i = 0; i < 100 && !(await evaluate("!!document.querySelector('main h1')")); i++) await sleep(100);
await sleep(300);
await send("Emulation.setDeviceMetricsOverride", { width: 794, height: 1123, deviceScaleFactor: 1, mobile: false });
await sleep(300);
const printed = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
writeFileSync(join(out, "report-print.png"), Buffer.from(printed.result.data, "base64"));
const pdf = await send("Page.printToPDF", { printBackground: false, preferCSSPageSize: true });
writeFileSync(join(out, "report.pdf"), Buffer.from(pdf.result.data, "base64"));
browser.kill();
await sleep(200);
rmSync(profile, { recursive: true, force: true });
process.exit(failed ? 1 : 0);
