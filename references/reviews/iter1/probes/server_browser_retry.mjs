// Reviewer probe: the browser phone against a FAKE-backed server (never Gnani), in headless Chrome,
// file mode (microphone refused). Checks what the phone does when a turn fails and when the reply
// to a turn is lost, and whether the dialogue advances once.
//
//   node references/reviews/iter1/probes/server_browser_retry.mjs --url http://127.0.0.1:8191 --ctl <scratch>/ctl
//
// CDP plumbing follows tests/server/browser_check.mjs.

import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, rmSync, unlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const args = Object.fromEntries(
  process.argv.slice(2).reduce((pairs, arg, i, all) => {
    if (arg.startsWith("--")) pairs.push([arg.slice(2), all[i + 1] ?? "1"]);
    return pairs;
  }, []),
);
const url = args.url ?? "http://127.0.0.1:8191";
const ctl = args.ctl;
const chrome = process.env.CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const port = 9300 + Math.floor(Math.random() * 500);
const profile = mkdtempSync(join(tmpdir(), "samajh-review-chrome-"));
const browser = spawn(
  chrome,
  ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--no-first-run",
   "--autoplay-policy=no-user-gesture-required", "--mute-audio", "--deny-permission-prompts",
   "--disable-background-networking", "--disable-component-update", "--disable-sync", "--no-default-browser-check",
   "--window-size=390,844", "about:blank"],
  { stdio: "ignore" },
);
const sleep = (ms) => new Promise((done) => setTimeout(done, ms));
const setCtl = (name, value) => (value == null ? existsSync(join(ctl, name)) && unlinkSync(join(ctl, name)) : writeFileSync(join(ctl, name), String(value)));

async function pageSocket() {
  for (let i = 0; i < 100; i++) {
    try {
      const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = targets.find((t) => t.type === "page");
      if (page) return new WebSocket(page.webSocketDebuggerUrl);
    } catch {
      /* starting */
    }
    await sleep(100);
  }
  throw new Error("Chrome did not open a debugging port");
}

let nextId = 0;
const waiting = new Map();
const consoleLines = [];
const requests = [];
const lost = [];
let loseNextTurnReply = false;
async function connect() {
  const socket = await pageSocket();
  await new Promise((done, fail) => {
    socket.onopen = done;
    socket.onerror = fail;
  });
  socket.onmessage = (event) => {
    const m = JSON.parse(event.data);
    if (m.id && waiting.has(m.id)) {
      waiting.get(m.id)(m);
      waiting.delete(m.id);
    } else if (m.method === "Runtime.exceptionThrown") {
      consoleLines.push("EXCEPTION " + (m.params.exceptionDetails.exception?.description ?? "").slice(0, 300));
    } else if (m.method === "Fetch.requestPaused") {
      const lose = loseNextTurnReply && m.params.request.method === "POST";
      if (lose) loseNextTurnReply = false;
      lost.push(`${lose ? "DROPPED" : "passed"} reply ${m.params.responseStatusCode} to ${m.params.request.method} ${new URL(m.params.request.url).search}`);
      const id = ++nextId;
      socket.send(JSON.stringify(lose
        ? { id, method: "Fetch.failRequest", params: { requestId: m.params.requestId, errorReason: "ConnectionReset" } }
        : { id, method: "Fetch.continueRequest", params: { requestId: m.params.requestId } }));
    } else if (m.method === "Network.requestWillBeSent") {
      const u = new URL(m.params.request.url);
      requests.push(`${m.params.request.method} ${u.host === new URL(url).host ? u.pathname.replace(/\d{8}T\d{6}-[0-9a-f]{12}/, "<sid>") + u.search : u.origin}`);
    }
  };
  return (method, params = {}) =>
    new Promise((done) => {
      const id = ++nextId;
      waiting.set(id, done);
      socket.send(JSON.stringify({ id, method, params }));
    });
}

const out = { steps: [] };
const say = (text) => out.steps.push(text);

async function main() {
  const send = await connect();
  const evaluate = async (expression) => {
    const reply = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (reply.result?.exceptionDetails) throw new Error(reply.result.exceptionDetails.exception?.description);
    return reply.result?.result?.value;
  };
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Network.enable");
  await send("Fetch.enable", { patterns: [{ urlPattern: "*/turns?*", requestStage: "Response" }] });
  await send("Page.navigate", { url: `${url}/` });
  const started = Date.now();
  const state = () => evaluate("window.samajhPhone ? window.samajhPhone.state() : 'loading'");
  const until = async (wanted, what, ms = 30000) => {
    const t = Date.now();
    while (Date.now() - t < ms) {
      const now = await state();
      if (wanted.includes(now)) return now;
      await sleep(40);
    }
    throw new Error(`timed out waiting for ${what}; state ${await state()}`);
  };
  const click = (id) => evaluate(`document.querySelector('#${id}').click()`);
  const text = (id) => evaluate(`document.querySelector('#${id}')?.textContent?.trim()`);
  const hidden = (id) => evaluate(`document.querySelector('#${id}')?.hidden`);
  const sendClip = (clip) =>
    evaluate(`(() => { const s = document.querySelector('#clip-select'); s.value = ${JSON.stringify(clip)};
      s.dispatchEvent(new Event('change', { bubbles: true })); document.querySelector('#send-clip').click(); })()`);
  const sessionId = () => text("mon-session");
  const serverLog = async () => (await fetch(`${url}/api/sessions/${await sessionId()}`)).json();
  const shape = (log) => log.events.map((e) => `${e.seq}${e.type[0]}${e.type === "error" ? "(" + e.code + ")" : ""}`).join(" ");

  await until(["idle"], "idle");
  await click("place-call");
  await until(["ringing"], "ringing");
  await click("answer");
  await until(["listening"], "first listening");
  say(`call up in file mode; mic line reads: ${await text("mon-mic")}; status detail: ${await text("status-detail")}`);

  // 1. the STT step fails, then "Send again"
  setCtl("stt_error", 1);
  await sendClip("01-loan-amount.wav");
  await until(["error"], "error after a failed STT");
  say(`1. STT fails -> state error; code ${await text("error-code")}; stage ${await text("error-stage")}; message ${await text("error-message")}; ` +
      `retry button hidden=${await hidden("retry")} label '${await text("retry")}'; continue label '${await text("continue")}'`);
  say(`   server log now: ${shape(await serverLog())}`);
  setCtl("stt_error", null);
  await click("retry");
  await until(["listening"], "listening after Send again");
  let turns = await evaluate("window.samajhPhone.log()");
  say(`   after Send again: phone turns ${turns.length}, sends of turn 1 = ${turns[0].sends}, transcript '${turns[0].transcript}'; server log: ${shape(await serverLog())}`);

  // 2. the reply to a turn is lost: the server answers 200, the browser's fetch fails
  loseNextTurnReply = true;
  await sendClip("02-emi.wav");
  await until(["error"], "error after the reply was dropped", 15000);
  say(`2. the reply to the turn was dropped on its way back -> phone state error; code ${await text("error-code")}; stage ${await text("error-stage")}; ` +
      `retry hidden=${await hidden("retry")} label '${await text("retry")}'; continue label '${await text("continue")}'`);
  say(`   server log (the server did take the turn): ${shape(await serverLog())}`);
  await click("retry");
  await until(["listening", "ended"], "listening after Send again");
  turns = await evaluate("window.samajhPhone.log()");
  const log2 = await serverLog();
  say(`   after Send again: phone turns ${turns.length} (sends ${turns.map((t) => t.sends)}); server log: ${shape(log2)}; ` +
      `bot prompts: ${log2.events.filter((e) => e.type === "bot").map((e) => e.tags.stub_step)}`);

  // 3. the same, but the customer picks "Record the turn again" and answers with different audio
  loseNextTurnReply = true;
  await sendClip("03-what-else.wav");
  await until(["error"], "error", 15000);
  say(`3. reply dropped again; server log: ${shape(await serverLog())} status ${(await serverLog()).status}`);
  await click("continue");
  const then = await until(["listening", "ended", "bot_speaking"], "state after Record the turn again");
  say(`   customer chose 'Record the turn again' -> phone state ${then}`);
  if (then === "listening") {
    await sendClip("01-loan-amount.wav");
    const end = await until(["ended", "error"], "after the re-recorded turn", 15000);
    turns = await evaluate("window.samajhPhone.log()");
    const log3 = await serverLog();
    say(`   re-recorded with a DIFFERENT clip (01, 2.32 s, instead of 03, 4.32 s) -> phone state ${end}; the phone shows transcript '${turns.at(-1)?.transcript}' ` +
        `and audio ${turns.at(-1)?.audio_seconds} s; server log: ${shape(log3)} status ${log3.status}; customer audio seconds on the server: ${log3.events.filter((e) => e.type === "customer").map((e) => e.audio_seconds)}`);
  }
  await sleep(1500);
  out.final_state = await state();
  out.summary = await text("summary-text");
  out.elapsed_s = (Date.now() - started) / 1000;
  out.hosts_contacted = [...new Set(requests.map((r) => (r.startsWith("GET /") || r.startsWith("POST /") ? new URL(url).host : r)))];
  out.requests = requests;
  out.turn_replies = lost;
  out.console = consoleLines.slice(0, 10);
}

let code = 0;
try {
  await main();
} catch (error) {
  out.failed = String(error.message ?? error);
  code = 1;
} finally {
  for (const name of ["stt_error"]) setCtl(name, null);
  setCtl("stt_delay", 0);
  console.log(JSON.stringify(out, null, 1));
  browser.kill();
  await sleep(300);
  rmSync(profile, { recursive: true, force: true });
}
process.exit(code);
