// Drives the browser phone in headless Chrome with a WAV file standing in for the microphone,
// so real getUserMedia capture, the end-of-speech detector and the upload path run unattended.
//
//   node tests/server/browser_check.mjs --url http://127.0.0.1:8085 --mic FILE.wav
//        [--clips 02-emi.wav,03-what-else.wav] [--query "line=8000"] [--shot OUT.png]
//        [--width 390 --height 844] [--timeout 120] [--case]
//
// --query takes the phone's URL parameters, e.g. "record=hero&lang=hi&mode=hands-free".
// --case waits after the call for the case file and prints it (as the phone last saw it).
//
// Without --mic the microphone permission is refused and every turn comes from --clips.
//
// --mic is played once into the fake microphone from the moment the page asks for it; pad it
// with silence so the speech starts after the first prompt has finished. The first customer
// turn is taken from the microphone; each later turn sends the next name in --clips through
// the clip picker. Prints one JSON object: the phone's own turn log, its final state, and what
// the status line showed along the way. Needs Node 22+ (global WebSocket) and Google Chrome.

import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const args = Object.fromEntries(
  process.argv.slice(2).reduce((pairs, arg, i, all) => {
    if (arg.startsWith("--")) pairs.push([arg.slice(2), all[i + 1]?.startsWith("--") ? "1" : (all[i + 1] ?? "1")]);
    return pairs;
  }, []),
);
const url = args.url ?? "http://127.0.0.1:8085";
const clips = (args.clips ?? "").split(",").filter(Boolean);
const timeoutMs = Number(args.timeout ?? 120) * 1000;
const chrome = process.env.CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const port = 9300 + Math.floor(Math.random() * 500);
const profile = mkdtempSync(join(tmpdir(), "samajh-chrome-"));

const flags = [
  "--headless=new",
  `--remote-debugging-port=${port}`,
  `--user-data-dir=${profile}`,
  "--no-first-run",
  "--autoplay-policy=no-user-gesture-required",
  "--mute-audio",
  `--window-size=${args.width ?? 390},${args.height ?? 844}`,
];
if (args.mic) {
  flags.push(
    "--use-fake-ui-for-media-stream",
    "--use-fake-device-for-media-stream",
    `--use-file-for-fake-audio-capture=${resolve(args.mic)}%noloop`,
    // With the audio service sandboxed, macOS Chrome cannot open the file and captures silence.
    "--disable-features=AudioServiceSandbox",
  );
} else {
  // No microphone: the permission prompt is refused, so the phone has to fall back to file turns.
  flags.push("--deny-permission-prompts");
}
const browser = spawn(chrome, [...flags, "about:blank"], { stdio: "ignore" });

const sleep = (ms) => new Promise((done) => setTimeout(done, ms));

async function pageSocket() {
  for (let i = 0; i < 100; i++) {
    try {
      const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = targets.find((t) => t.type === "page");
      if (page) return new WebSocket(page.webSocketDebuggerUrl);
    } catch {
      /* Chrome is still starting */
    }
    await sleep(100);
  }
  throw new Error("Chrome did not open a debugging port");
}

let nextId = 0;
const waiting = new Map();
const consoleLines = [];
async function connect() {
  const socket = await pageSocket();
  await new Promise((done, fail) => {
    socket.onopen = done;
    socket.onerror = fail;
  });
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.id && waiting.has(message.id)) {
      waiting.get(message.id)(message);
      waiting.delete(message.id);
    } else if (message.method === "Runtime.consoleAPICalled") {
      consoleLines.push(message.params.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 300));
    } else if (message.method === "Runtime.exceptionThrown") {
      consoleLines.push("EXCEPTION " + (message.params.exceptionDetails.exception?.description ?? "").slice(0, 300));
    }
  };
  return (method, params = {}) =>
    new Promise((done) => {
      const id = ++nextId;
      waiting.set(id, done);
      socket.send(JSON.stringify({ id, method, params }));
    });
}

async function main() {
  const send = await connect();
  const evaluate = async (expression) => {
    const reply = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (reply.result?.exceptionDetails) throw new Error(reply.result.exceptionDetails.exception?.description);
    return reply.result?.result?.value;
  };
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", {
    width: Number(args.width ?? 390),
    height: Number(args.height ?? 844),
    deviceScaleFactor: 2,
    mobile: Number(args.width ?? 390) < 700,
  });
  await send("Page.navigate", { url: `${url}/${args.query ? "?" + args.query : ""}` });
  const started = Date.now();
  const states = [];
  const shot = async (path) => {
    const png = await send("Page.captureScreenshot", { format: "png" });
    writeFileSync(path, Buffer.from(png.result.data, "base64"));
  };
  const state = async () => {
    const now = await evaluate("window.samajhPhone ? window.samajhPhone.state() : 'loading'");
    if (states.at(-1)?.[1] !== now) states.push([Date.now() - started, now]);
    return now;
  };
  const until = async (wanted, what) => {
    while (Date.now() - started < timeoutMs) {
      const now = await state();
      if (wanted.includes(now)) return now;
      if (now === "error" && !wanted.includes("error")) {
        const code = await evaluate("document.querySelector('#error-code')?.textContent");
        throw new Error(`phone is in the error state while waiting for ${what}: ${code}`);
      }
      await sleep(50);
    }
    throw new Error(`timed out waiting for ${what}; states so far: ${JSON.stringify(states)}`);
  };
  const turns = () => evaluate("window.samajhPhone.log().length");

  await until(["idle"], "the idle screen");
  for (let i = 0; i < 100 && !(await evaluate("document.querySelector('#record')?.value || ''")); i++) await sleep(50);
  if (args.shot) await shot(args.shot.replace(/\.png$/, "-idle.png"));
  await evaluate("document.querySelector('#place-call').click()");
  await until(["ringing"], "ringing");
  if (args.shot) await shot(args.shot.replace(/\.png$/, "-ringing.png"));
  await evaluate("document.querySelector('#answer').click()");

  let queue = [...clips];
  let done = 0;
  let shotListening = false;
  while (true) {
    const now = await until(["listening", "ended"], "the customer's turn or the end of the call");
    if (now === "ended") break;
    if (args.shot && !shotListening) {
      await shot(args.shot.replace(/\.png$/, "-listening.png"));
      shotListening = true;
    }
    if (done > 0 || !args.mic) {
      const clip = queue.shift();
      if (!clip) {
        await evaluate("document.querySelector('#hangup').click()");
        continue;
      }
      await evaluate(`(() => { const s = document.querySelector('#clip-select'); s.value = ${JSON.stringify(clip)};
        s.dispatchEvent(new Event('change', { bubbles: true })); document.querySelector('#send-clip').click(); })()`);
    }
    while ((await turns()) === done) {
      if ((await state()) === "error") throw new Error("turn failed: " + (await evaluate("document.querySelector('#error-code')?.textContent")));
      if (Date.now() - started > timeoutMs) throw new Error("timed out inside a turn");
      await sleep(50);
    }
    done = await turns();
  }
  let caseFile = null;
  if (args.case) {
    while (Date.now() - started < timeoutMs) {
      caseFile = await evaluate("window.samajhPhone.caseFile()");
      if (caseFile.error || (caseFile.file && caseFile.file.status !== "running")) break;
      await sleep(500);
    }
    await evaluate("document.querySelector('#case')?.scrollIntoView()");
  }
  if (args.shot) await shot(args.shot);
  return {
    final_state: await state(),
    case: caseFile && {
      error: caseFile.error,
      status: caseFile.file?.status,
      failed: caseFile.file?.failed,
      tier: caseFile.file?.tier,
      call_outcome: caseFile.file?.call_outcome,
      session_id: caseFile.file?.session_id,
      lines: caseFile.file?.summary?.lines?.map((l) => [l.tier, l.title]),
      case_text: await evaluate("document.querySelector('#case-status')?.textContent"),
    },
    turns: await evaluate("window.samajhPhone.log()"),
    states,
    status_text: await evaluate("document.querySelector('#status')?.textContent?.trim()"),
    console: consoleLines.slice(0, 20),
  };
}

let code = 0;
try {
  console.log(JSON.stringify(await main(), null, 1));
} catch (error) {
  console.log(JSON.stringify({ failed: String(error.message ?? error), console: consoleLines.slice(0, 20) }, null, 1));
  code = 1;
} finally {
  browser.kill();
  await sleep(300);
  rmSync(profile, { recursive: true, force: true });
}
process.exit(code);
