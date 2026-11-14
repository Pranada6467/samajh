// Drives the browser phone in headless Chrome through a whole call in which EVERY customer turn
// goes through the microphone path (hands-free), so the real end-of-speech detector, its cut and
// grace window, and the phone's own `bot_start_ms` run. For latency measurement.
//
//   node tests/server/browser_calls.mjs --url http://127.0.0.1:8085 \
//        --query "record=hero&lang=hi&mode=hands-free&autoanswer=1" \
//        --turns 01.wav,02.wav,none,04.wav [--gap-ms 400] [--noise-dbfs -60] \
//        [--timeout 300] [--out FILE.json]
//
// --query is the phone's URL parameters (web/phone.js): record, loan, lang, mode (hands-free | ptt),
//   line (8000 | 16000), identity (none | year_of_birth), attempts (1 | 2), autoanswer=1.
//   mode=hands-free is forced if missing; without it there is no VAD.
// --turns are clip names served by the server's /api/clips (its clips dir: SAMAJH_CLIPS_DIR).
//   `none` stays silent: the phone reports no speech after NO_SPEECH_MS (8 s, phone.js) of
//   listening, the server logs a `source: "none"` turn, and bot_start_ms for it is measured from
//   the moment the phone gave up waiting, not from any speech.
// --gap-ms is waited after the phone enters `listening` before the clip starts.
// --noise-dbfs adds steady white noise at that RMS level between and under clips (default: none,
//   digital silence).
//
// getUserMedia is replaced before the page loads: it returns the stream of a
// MediaStreamAudioDestinationNode in an AudioContext this script owns; window.__mic.play(url)
// plays a WAV into it and resolves when it has finished. When clips run out the script hangs up.
// Prints (and with --out writes) one JSON object: session id, the phone's turn log
// (window.samajhPhone.log(): latency.bot_start_ms, eos_wait_ms, post_ms), final state, errors.
// Needs Node 22+ (global WebSocket) and Google Chrome (CHROME overrides its path).

import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const args = Object.fromEntries(
  process.argv.slice(2).reduce((pairs, arg, i, all) => {
    if (arg.startsWith("--")) pairs.push([arg.slice(2), all[i + 1]?.startsWith("--") ? "1" : (all[i + 1] ?? "1")]);
    return pairs;
  }, []),
);
const url = (args.url ?? "http://127.0.0.1:8085").replace(/\/$/, "");
const query = new URLSearchParams(args.query ?? "");
if (!query.get("mode")) query.set("mode", "hands-free");
if (!query.get("autoanswer")) query.set("autoanswer", "1");
const turnsWanted = (args.turns ?? "").split(",").filter(Boolean);
const gapMs = Number(args["gap-ms"] ?? 400);
const noiseDbfs = args["noise-dbfs"] == null ? null : Number(args["noise-dbfs"]);
const timeoutMs = Number(args.timeout ?? 300) * 1000;
const chrome = process.env.CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const port = 9300 + Math.floor(Math.random() * 500);
const profile = mkdtempSync(join(tmpdir(), "samajh-chrome-"));

const browser = spawn(
  chrome,
  [
    "--headless=new",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    "--no-first-run",
    "--autoplay-policy=no-user-gesture-required",
    "--mute-audio",
    "--window-size=390,844",
    "about:blank",
  ],
  { stdio: "ignore" },
);

const sleep = (ms) => new Promise((done) => setTimeout(done, ms));

// Runs in the page before its own scripts. `NOISE` is replaced with the level (or null).
const FAKE_MIC = `(() => {
  const NOISE = __NOISE__;
  let ctx = null, dest = null;
  const ensure = () => {
    if (ctx) return;
    ctx = new AudioContext();
    dest = ctx.createMediaStreamDestination();
    dest.channelCount = 1;
    if (NOISE != null) {
      const a = Math.pow(10, NOISE / 20) * Math.sqrt(3); // uniform noise of that RMS
      const buf = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
      const d = buf.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * a;
      const src = ctx.createBufferSource();
      src.buffer = buf; src.loop = true; src.connect(dest); src.start();
    }
  };
  window.__mic = {
    calls: 0,
    state: () => ctx?.state ?? "none",
    async play(url) {
      ensure();
      await ctx.resume();
      const bytes = await (await fetch(url)).arrayBuffer();
      const buffer = await ctx.decodeAudioData(bytes);
      await new Promise((done) => {
        const src = ctx.createBufferSource();
        src.buffer = buffer; src.connect(dest); src.onended = done; src.start();
      });
      return buffer.duration;
    },
  };
  navigator.mediaDevices.getUserMedia = async (constraints) => {
    if (!constraints || !constraints.audio) throw new DOMException("audio only", "NotSupportedError");
    ensure();
    await ctx.resume();
    window.__mic.calls += 1;
    return dest.stream;
  };
  // The phone does not expose its session id: take it from the create-session reply.
  const realFetch = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const res = await realFetch(input, init);
    const path = typeof input === "string" ? input : input.url;
    if (init?.method === "POST" && /\\/api\\/sessions$/.test(path) && res.ok) {
      res.clone().json().then((j) => { window.__sessionId = j.session_id; }).catch(() => {});
    }
    return res;
  };
})();`;

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

const errors = [];
const states = [];
const started = Date.now();
let evaluate;

async function main() {
  const send = await connect();
  evaluate = async (expression) => {
    const reply = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (reply.result?.exceptionDetails) throw new Error(reply.result.exceptionDetails.exception?.description);
    return reply.result?.result?.value;
  };
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Page.addScriptToEvaluateOnNewDocument", {
    source: FAKE_MIC.replace("__NOISE__", noiseDbfs == null ? "null" : String(noiseDbfs)),
  });
  await send("Page.navigate", { url: `${url}/?${query}` });

  const state = async () => {
    const now = await evaluate("window.samajhPhone ? window.samajhPhone.state() : 'loading'");
    if (states.at(-1)?.[1] !== now) states.push([Date.now() - started, now]);
    return now;
  };
  const errorCode = () => evaluate("document.querySelector('#error-code')?.textContent || ''");
  const until = async (wanted, what) => {
    while (Date.now() - started < timeoutMs) {
      const now = await state();
      if (wanted.includes(now)) return now;
      if (now === "error") throw new Error(`phone in the error state waiting for ${what}: ${await errorCode()}`);
      await sleep(25);
    }
    throw new Error(`timed out waiting for ${what}; states: ${JSON.stringify(states.slice(-8))}`);
  };
  const turnCount = () => evaluate("window.samajhPhone.log().length");

  await until(["idle", "ringing", "connecting", "bot_speaking", "listening"], "the phone page");
  // The record picker fills from /api/records; give it a moment before placing the call.
  for (let i = 0; i < 100 && !(await evaluate("document.querySelector('#record')?.value || ''")); i++) await sleep(50);
  if ((await state()) === "idle") await evaluate("document.querySelector('#place-call').click()");
  if ((await state()) === "ringing" && query.get("autoanswer") !== "1") await evaluate("document.querySelector('#answer').click()");

  const played = [];
  for (const clip of turnsWanted) {
    const now = await until(["listening", "ended"], "the customer's turn");
    if (now === "ended") {
      errors.push(`call ended before clip ${clip}`);
      break;
    }
    const before = await turnCount();
    await sleep(gapMs);
    const t0 = Date.now() - started;
    let seconds = null;
    if (clip !== "none") seconds = await evaluate(`window.__mic.play(${JSON.stringify(`/api/clips/${encodeURIComponent(clip)}`)})`);
    played.push({ clip, at_ms: t0, seconds });
    // The turn is in once the phone's log grows; then wait out the reply (back to listening, or ended).
    while ((await turnCount()) === before) {
      const s = await state();
      if (s === "error") throw new Error(`turn ${clip} failed: ${await errorCode()}`);
      if (s === "ended") break;
      if (Date.now() - started > timeoutMs) throw new Error(`timed out inside turn ${clip}`);
      await sleep(25);
    }
  }
  if ((await until(["listening", "ended"], "the end of the last reply")) === "listening") {
    await evaluate("document.querySelector('#hangup').click()");
  }
  await until(["ended"], "the call to end");
  // The playback report of the last utterance is posted asynchronously.
  await sleep(500);
  return played;
}

let code = 0;
let played = [];
try {
  played = await main();
} catch (error) {
  errors.push(String(error.message ?? error));
  code = 1;
}
let result;
try {
  const turns = await evaluate("window.samajhPhone ? window.samajhPhone.log() : []");
  result = {
    session_id: await evaluate("window.__sessionId ?? null"),
    url,
    query: query.toString(),
    final_state: await evaluate("window.samajhPhone ? window.samajhPhone.state() : null"),
    mic_status: await evaluate("document.querySelector('#mon-mode')?.textContent ?? null"),
    mic_requests: await evaluate("window.__mic?.calls ?? 0"),
    played,
    turns,
    bot_start_ms: turns.map((t) => t.latency?.bot_start_ms ?? null),
    states,
    errors,
    console: consoleLines.filter((l) => !l.startsWith("[samajh] customer")).slice(0, 40),
  };
} catch (error) {
  result = { session_id: null, errors: [...errors, String(error.message ?? error)], states, console: consoleLines.slice(0, 40) };
  code = 1;
}
const text = JSON.stringify(result, null, 1);
if (args.out) writeFileSync(args.out, text);
console.log(text);
browser.kill();
await sleep(300);
rmSync(profile, { recursive: true, force: true });
process.exit(code);
