import { ApiError, api } from "./api.js";
import { createVad } from "./vad.js";
import { encodeWav } from "./wav.js";

const NO_SPEECH_MS = 8000;
const MAX_TURN_MS = 28000; // the server refuses more than 30 s
const PREROLL_MS = 300;
const TAIL_MS = 200; // silence kept after the last voiced frame
const MIN_PTT_MS = 200;
const VAD_MIN_SPEECH_MS = 120;
const MAX_CARRIED_NOISE_RMS = 0.02;
// The speaker is still sounding for a moment after the buffer ends; do not hear the bot as the customer.
const ECHO_GUARD_MS = 150;

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const autoanswer = params.get("autoanswer") === "1";

// ---- state machine -------------------------------------------------------------------------

const afterBot = (c) => (c.bot.end_call ? "ended" : "listening");

// state -> event -> next state (or a function of the call that picks it)
const TRANSITIONS = {
  idle: { PLACE: "ringing" },
  ringing: { ANSWER: "connecting", DECLINE: "idle" },
  connecting: { SESSION: "bot_speaking", FAIL: "error", HANGUP: "ended" },
  bot_speaking: { BOT_DONE: afterBot, FAIL: "error", HANGUP: "ended" },
  listening: { TURN: "transcribing", HANGUP: "ended" },
  transcribing: { REPLY: "bot_speaking", FAIL: "error", HANGUP: "ended" },
  error: {
    RETRY: (c) => c.failure.from,
    CONTINUE: (c) => ({ transcribing: "listening", bot_speaking: afterBot(c) })[c.failure.from],
    HANGUP: "ended",
  },
  ended: { RESET: "idle" },
};

const LABEL = {
  idle: "Ready",
  ringing: "Ringing",
  connecting: "Connecting",
  bot_speaking: "Bot speaking",
  listening: "Listening",
  transcribing: "Transcribing",
  ended: "Call ended",
  error: "Error",
};

let state = "idle";
let epoch = 0;
let call = newCall();
let listen = null; // capture state of the current customer turn
const audio = { ctx: null, workletReady: false, mic: null, playing: null, ring: null };

function newCall() {
  return {
    settings: {
      lineRate: Number($("line-rate").value),
      model: $("stt-model").value,
      mode: $("turn-mode").value,
    },
    sessionId: null,
    bot: null,
    turns: [],
    pending: null,
    failure: null,
    summary: null,
    endError: null,
    mic: { status: "off", reason: "" }, // off | asking | on | unavailable
  };
}

function dispatch(event, data) {
  const target = TRANSITIONS[state][event];
  const next = typeof target === "function" ? target(call) : target;
  if (!next) return;
  const from = state;
  state = next;
  epoch += 1;
  stopPlayback();
  LEAVE[from]?.();
  ENTER[next]?.(data, from, event);
  render();
  // Panels under the transcript change height with the state; keep the newest bubble in view.
  $("transcript").scrollTop = $("transcript").scrollHeight;
}

// Async work started in one state must not act after the call has moved on.
function guard() {
  const mine = epoch;
  return () => mine === epoch;
}

const LEAVE = {
  ringing: stopRing,
  listening() {
    // What this turn learned about the room's noise carries to the next one. Capped, and taken
    // only between utterances, so a loud turn cannot deafen the detector.
    const heard = listen?.vad?.state();
    if (heard && !heard.speaking) call.noiseRms = Math.min(heard.noiseRms, MAX_CARRIED_NOISE_RMS);
    listen = null;
  },
};

const ENTER = {
  ringing() {
    call = newCall();
    $("transcript").replaceChildren();
    audio.ctx ??= new AudioContext();
    audio.ctx.resume().catch(() => {});
    startRing();
    if (autoanswer) queueMicrotask(() => dispatch("ANSWER"));
  },

  async connecting() {
    const live = guard();
    try {
      if (call.mic.status === "off") {
        call.mic = { status: "asking", reason: "" };
        const mine = call;
        await openMic();
        // A newer call may own the microphone by now; only this call's is closed.
        if (!live()) return void (call === mine && closeMic());
        render();
      }
      const s = await api.createSession({ line_rate: call.settings.lineRate, stt_model: call.settings.model });
      if (!live()) return void api.endSession(s.session_id).catch(() => {});
      call.sessionId = s.session_id;
      call.settings.lineRate = s.line_rate;
      call.settings.model = s.stt_model;
      call.bot = s.bot;
      dispatch("SESSION");
    } catch (e) {
      if (live()) dispatch("FAIL", e);
    }
  },

  async bot_speaking(_, from, event) {
    const live = guard();
    const bot = call.bot;
    if (event !== "RETRY") addBotBubble(bot);
    try {
      const bytes = await api.bytes(bot.audio_url);
      if (!live()) return;
      await play(bytes, live);
      if (live()) dispatch("BOT_DONE");
    } catch (e) {
      if (live()) dispatch("FAIL", e);
    }
  },

  listening() {
    const handsFree = call.settings.mode === "handsfree" && call.mic.status === "on";
    listen = {
      vad: handsFree
        ? createVad({
            sampleRate: audio.ctx.sampleRate,
            minSpeechMs: VAD_MIN_SPEECH_MS,
            initialNoiseRms: call.noiseRms ?? 0,
          })
        : null,
      prerollMs: PREROLL_MS + (handsFree ? VAD_MIN_SPEECH_MS : 0),
      openAt: performance.now() + (audio.ctx.outputLatency || 0) * 1000 + ECHO_GUARD_MS,
      chunks: [],
      buffered: 0,
      stream: 0,
      speaking: false,
      ptt: false,
      pttAt: 0,
      silenceTimer: handsFree,
      level: 0,
    };
    note("");
  },

  async transcribing(data, from, event) {
    if (event === "TURN") {
      // Measured once: a second send after an error screen must not count the time spent on it.
      const eosWaitMs = data.source === "mic" ? performance.now() - data.voiceEndAt : null;
      call.pending = { ...data, tries: 0, eosWaitMs };
    }
    const turn = call.pending;
    const live = guard();
    turn.tries += 1;
    const sentAt = performance.now();
    const eosWaitMs = turn.eosWaitMs;
    try {
      const reply = await api.postTurn(call.sessionId, {
        source: turn.source,
        body: turn.body,
        eosWaitMs,
        // Names the prompt being answered, so a turn sent twice is answered once.
        replyTo: call.bot.seq,
      });
      const postMs = performance.now() - sentAt;
      if (!live()) return;
      const c = reply.customer;
      const record = {
        seq: c.seq,
        source: turn.source,
        transcript: c.transcript,
        literal: c.literal,
        detected_language: c.detected_language,
        audio_url: c.audio_url,
        audio_seconds: c.audio_seconds,
        stt: c.stt,
        sends: turn.tries,
        latency: { ...c.latency, eos_wait_ms: eosWaitMs, post_ms: postMs, headline_ms: (eosWaitMs ?? 0) + postMs },
      };
      call.turns.push(record);
      addCustomerBubble(record, call.bot.language);
      call.bot = reply.bot;
      call.pending = null;
      dispatch("REPLY");
    } catch (e) {
      if (live()) dispatch("FAIL", e);
    }
  },

  error(error, from) {
    call.failure = { from, error: asApiError(error) };
  },

  async ended() {
    const live = guard();
    closeMic();
    if (!call.sessionId) return;
    try {
      call.summary = await api.endSession(call.sessionId);
    } catch (e) {
      call.endError = asApiError(e);
    }
    if (live()) render();
  },
};

function asApiError(e) {
  if (e instanceof ApiError) return e;
  return new ApiError({ stage: "phone", code: "phone_bug", message: `${e.name}: ${e.message}` });
}

// ---- audio out -----------------------------------------------------------------------------

async function play(bytes, live) {
  const ctx = audio.ctx;
  if (ctx.state !== "running") {
    await Promise.race([ctx.resume(), new Promise((done) => setTimeout(done, 1000))]);
  }
  if (ctx.state !== "running") {
    throw new ApiError({
      stage: "playback",
      code: "audio_blocked",
      message: "The browser has not allowed this page to play audio yet. Try again starts it.",
      retryable: true,
    });
  }
  let buffer;
  try {
    buffer = await ctx.decodeAudioData(bytes);
  } catch (e) {
    throw new ApiError({
      stage: "playback",
      code: "audio_undecodable",
      message: `The browser could not decode the audio the server sent (${e.name}: ${e.message}).`,
      retryable: true,
    });
  }
  if (!live()) return;
  await new Promise((done) => {
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.onended = done;
    audio.playing = source;
    source.start();
  });
}

function stopPlayback() {
  try {
    audio.playing?.stop();
  } catch {
    // already stopped
  }
  audio.playing = null;
}

function startRing() {
  const ctx = audio.ctx;
  const gain = ctx.createGain();
  gain.gain.value = 0;
  gain.connect(ctx.destination);
  const oscillators = [440, 480].map((hz) => {
    const osc = ctx.createOscillator();
    osc.frequency.value = hz;
    osc.connect(gain);
    osc.start();
    return osc;
  });
  const burst = () => {
    const t = ctx.currentTime + 0.05;
    for (const at of [0, 0.6]) {
      gain.gain.setTargetAtTime(0.1, t + at, 0.01);
      gain.gain.setTargetAtTime(0, t + at + 0.4, 0.01);
    }
  };
  burst();
  audio.ring = { gain, oscillators, timer: setInterval(burst, 3000) };
}

function stopRing() {
  if (!audio.ring) return;
  clearInterval(audio.ring.timer);
  for (const osc of audio.ring.oscillators) osc.stop();
  audio.ring.gain.disconnect();
  audio.ring = null;
}

// ---- audio in ------------------------------------------------------------------------------

// Writes only to the call it was started for: the permission prompt can outlive that call.
async function openMic() {
  const mine = call;
  const stale = () => call !== mine;
  let stream = null;
  try {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error("this browser offers no microphone here");
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    if (stale()) return void stream.getTracks().forEach((t) => t.stop());
    const ctx = audio.ctx;
    if (!audio.workletReady) {
      await ctx.audioWorklet.addModule(new URL("./capture-worklet.js", import.meta.url));
      audio.workletReady = true;
    }
    if (stale()) return void stream.getTracks().forEach((t) => t.stop());
    const source = ctx.createMediaStreamSource(stream);
    const node = new AudioWorkletNode(ctx, "capture");
    // The graph is only pulled when it reaches the destination; the gain keeps the mic silent there.
    const mute = ctx.createGain();
    mute.gain.value = 0;
    source.connect(node).connect(mute).connect(ctx.destination);
    node.port.onmessage = (e) => onFrame(e.data);
    audio.mic = { stream, source, node, mute };
    mine.mic = { status: "on", reason: "" };
  } catch (e) {
    stream?.getTracks().forEach((t) => t.stop());
    mine.mic = { status: "unavailable", reason: e.name && e.name !== "Error" ? `${e.name}: ${e.message}` : e.message };
  }
}

function closeMic() {
  if (!audio.mic) return;
  audio.mic.node.port.onmessage = null;
  audio.mic.source.disconnect();
  audio.mic.node.disconnect();
  audio.mic.mute.disconnect();
  audio.mic.stream.getTracks().forEach((t) => t.stop());
  audio.mic = null;
}

// Half duplex: frames only count while it is the customer's turn.
function onFrame(samples) {
  const L = listen;
  if (state !== "listening" || !L || performance.now() < L.openAt) return;
  const rate = audio.ctx.sampleRate;
  const toMs = (n) => (n * 1000) / rate;

  let sum = 0;
  for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
  L.level = Math.sqrt(sum / samples.length);
  drawLevel();

  L.chunks.push(samples);
  L.buffered += samples.length;
  L.stream += samples.length;
  if (!L.speaking && !L.ptt) {
    while (toMs(L.buffered - L.chunks[0].length) >= L.prerollMs) L.buffered -= L.chunks.shift().length;
  }

  for (const ev of L.vad?.push(samples) ?? []) {
    if (ev.type === "speech_start") {
      L.speaking = true;
      render();
    } else if (L.speaking) {
      const keepUntil = Math.round(((ev.lastVoicedMs + TAIL_MS) * rate) / 1000);
      const drop = Math.max(0, L.stream - keepUntil);
      return sendMic(L.buffered - drop, performance.now() - (ev.atMs - ev.lastVoicedMs));
    }
  }
  if (L.silenceTimer && !L.speaking && toMs(L.stream) >= NO_SPEECH_MS) {
    return dispatch("TURN", { source: "none", body: null });
  }
  if ((L.speaking || L.ptt) && toMs(L.buffered) >= MAX_TURN_MS) sendMic(L.buffered, performance.now());
}

// voiceEndAt: when the customer stopped (hands-free: last voiced frame; push to talk: release).
function sendMic(sampleCount, voiceEndAt) {
  const body = encodeWav(listen.chunks, audio.ctx.sampleRate, sampleCount);
  dispatch("TURN", { source: "mic", body, voiceEndAt });
}

const canPtt = () =>
  state === "listening" && listen && call.settings.mode === "ptt" && call.mic.status === "on";

function pttDown() {
  if (!canPtt() || listen.ptt) return;
  listen.ptt = true;
  listen.pttAt = performance.now();
  note("");
  render();
}

function pttUp() {
  if (state !== "listening" || !listen?.ptt) return;
  if (performance.now() - listen.pttAt < MIN_PTT_MS) {
    listen.ptt = false;
    note("Too short to send. Hold while you speak, then release.");
    return render();
  }
  sendMic(listen.buffered, performance.now());
}

// ---- file turns ----------------------------------------------------------------------------

async function sendFileTurn(read) {
  if (state !== "listening") return;
  const live = guard();
  listen.silenceTimer = false;
  note("");
  try {
    const body = await read();
    if (live()) dispatch("TURN", { source: "file", body });
  } catch (e) {
    if (live()) note(e instanceof ApiError ? `${e.code}: ${e.message}` : `Could not read the file (${e.message}).`);
  }
}

async function loadClips() {
  const select = $("clip-select");
  try {
    const clips = await api.clips();
    select.replaceChildren(...clips.map((c) => new Option(`${c.name} · ${Number(c.seconds).toFixed(1)} s`, c.name)));
    if (!clips.length) select.add(new Option("No prepared clips on this server", ""));
  } catch (e) {
    select.replaceChildren(new Option(`Clips unavailable (${e.code})`, ""));
  }
  $("send-clip").disabled = !select.value;
}

// ---- rendering -----------------------------------------------------------------------------

const fmtMs = (ms) => (ms == null ? "n/a" : ms >= 1000 ? `${(ms / 1000).toFixed(2)} s` : `${Math.round(ms)} ms`);
const HEADLINE = { mic: "end of speech to transcript", file: "upload to transcript", none: "silence report to reply" };

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
}

// "hi-en" and "auto" are API codes, not language tags.
function setLang(node, code) {
  const tag = code === "hi-en" ? "hi" : code;
  if (/^[a-z]{2,3}(-[A-Z]{2})?$/.test(tag ?? "")) node.lang = tag;
  return node;
}

function addBubble(li) {
  const list = $("transcript");
  list.append(li);
  list.scrollTop = list.scrollHeight;
}

function addBotBubble(bot) {
  addBubble(
    el("li", { className: "bubble bot" }, el("span", { className: "who", textContent: "Bot" }), setLang(el("p", { textContent: bot.text }), bot.language)),
  );
}

function addCustomerBubble(turn, botLanguage) {
  const li = el("li", { className: "bubble customer" }, el("span", { className: "who", textContent: "Customer" }));
  if (turn.transcript) {
    li.append(setLang(el("p", { textContent: turn.transcript }), turn.detected_language ?? botLanguage));
  } else {
    const why = turn.source === "none" ? "No speech in 8 s. Nothing was sent to Prisma." : "Prisma returned no text for this audio.";
    li.append(el("p", { className: "empty", textContent: why }));
  }
  if (turn.literal && turn.literal !== turn.transcript) {
    li.append(setLang(el("p", { className: "literal", textContent: `Before number formatting: ${turn.literal}` }), botLanguage));
  }

  const t = turn.latency;
  const rows = [
    turn.source === "mic" && ["Detector wait (last voiced frame to upload)", fmtMs(t.eos_wait_ms)],
    ["Request (upload, server, reply)", fmtMs(t.post_ms)],
    ["Server total", fmtMs(t.server_ms)],
    turn.audio_url && ["Server: resample to line rate", fmtMs(t.normalise_ms)],
    turn.stt && ["Server: Prisma STT", fmtMs(t.stt_ms)],
    ["Server: dialogue", fmtMs(t.dialogue_ms)],
    turn.stt && ["Model", turn.stt.model],
    turn.stt && ["Cache hit", turn.stt.cache_hit ? "yes" : "no"],
    turn.stt && ["STT attempts", String(turn.stt.attempts)],
    turn.audio_seconds != null && ["Audio on the line", `${turn.audio_seconds.toFixed(2)} s`],
    turn.sends > 1 && ["Sent from this phone", `${turn.sends} times`],
  ].filter(Boolean);
  const details = el(
    "details",
    { className: "latency" },
    el("summary", {}, el("b", { textContent: fmtMs(t.headline_ms) }), ` ${HEADLINE[turn.source]}`),
    el("dl", {}, ...rows.flatMap(([k, v]) => [el("dt", { textContent: k }), el("dd", { textContent: v })])),
  );
  li.append(details);

  if (turn.audio_url) {
    const problem = el("span", { className: "heard-problem" });
    const button = el("button", { className: "heard", type: "button", textContent: "Play what the line heard", disabled: true });
    button.title = "Available when the call is not using the line";
    button.addEventListener("click", async () => {
      stopPlayback();
      problem.textContent = "";
      try {
        await play(await api.bytes(turn.audio_url), () => true);
      } catch (e) {
        problem.textContent = `${e.code}: ${e.message}`;
      }
    });
    li.append(button, problem);
  }
  addBubble(li);
}

function note(text) {
  $("turn-note").textContent = text;
}

let levelQueued = false;
function drawLevel() {
  if (levelQueued) return;
  levelQueued = true;
  requestAnimationFrame(() => {
    levelQueued = false;
    const rms = listen?.level ?? 0;
    // -60 dBFS to 0 dBFS across the bar
    const pct = Math.round(Math.max(0, Math.min(1, (20 * Math.log10(rms || 1e-6) + 60) / 60)) * 100);
    $("level").firstElementChild.style.width = `${pct}%`;
    $("level").setAttribute("aria-valuenow", String(pct));
  });
}

function detail() {
  const mic = call.mic;
  const fileMode = `No microphone (${mic.reason}). File mode: answer with a clip or a WAV.`;
  switch (state) {
    case "idle":
      return "Choose the line settings, then place the call.";
    case "ringing":
      return "Incoming demo call";
    case "connecting":
      return mic.status === "asking" ? "Asking for the microphone" : "Opening the session on the local server";
    case "bot_speaking":
      return "The microphone is ignored while the bot speaks.";
    case "listening":
      if (mic.status !== "on") return fileMode;
      if (call.settings.mode === "ptt") return listen?.ptt ? "Recording. Release to send." : "Hold the button or the Space key to talk.";
      if (listen?.speaking) return "Speech detected. Stop talking to send.";
      return listen?.silenceTimer ? "Waiting for speech. Silence is reported after 8 s." : "Waiting for speech or a clip.";
    case "transcribing":
      return "Waiting for Prisma through the local server";
    case "error":
      return `The step that failed: ${LABEL[call.failure.from].toLowerCase()}.`;
    case "ended":
      return mic.status === "unavailable" ? "This call ran in file mode." : "";
  }
}

function summaryText() {
  if (!call.sessionId) return "The call ended before a session was opened.";
  if (call.endError) {
    return `The server did not confirm the end of the session. ${call.endError.code}: ${call.endError.message}`;
  }
  const s = call.summary;
  if (!s) return "Closing the session on the server.";
  const recording = s.recording_seconds == null ? "no recording yet" : `recording ${s.recording_seconds.toFixed(1)} s`;
  return `${s.turns} customer turns, ${s.events} events, ${recording}. Ended by: ${s.ended_reason ?? "unknown"}.`;
}

function render() {
  const body = document.body;
  body.dataset.state = state;
  body.dataset.mode = call.settings.mode;
  body.dataset.mic = call.mic.status;
  $("status").dataset.state = state;
  if ($("status").textContent !== LABEL[state]) $("status").textContent = LABEL[state];
  $("status-detail").textContent = detail();

  if (state === "listening") {
    const active = listen.speaking || listen.ptt;
    const flag = $("speech-flag");
    flag.textContent = call.settings.mode === "ptt" ? (active ? "Recording" : "Not recording") : active ? "Speech detected" : "No speech";
    flag.classList.toggle("on", active);
    $("ptt").classList.toggle("held", listen.ptt);
    $("ptt").textContent = listen.ptt ? "Release to send" : "Hold to talk";
  }

  if (state === "error") {
    const { from, error } = call.failure;
    $("error-stage").textContent = error.stage;
    $("error-code").textContent = error.code;
    const upstream = error.upstreamStatus ? ` (upstream HTTP ${error.upstreamStatus})` : "";
    $("error-message").textContent = error.message + upstream;
    const resendable = error.retryable || ["stt", "tts", "dialogue", "playback", "network"].includes(error.stage);
    $("retry").hidden = !resendable;
    $("retry").textContent = from === "transcribing" && call.pending.body ? "Send again" : "Try again";
    $("continue").hidden = from === "connecting";
    $("continue").textContent = from === "transcribing" ? "Record the turn again" : "Continue without this audio";
  }

  if (state === "ended") {
    $("summary-text").textContent = summaryText();
    $("log-link").hidden = $("recording-link").hidden = !call.sessionId;
    if (call.sessionId) {
      $("log-link").href = api.logUrl(call.sessionId);
      $("recording-link").href = api.recordingUrl(call.sessionId);
    }
  }
  for (const b of document.querySelectorAll(".heard")) b.disabled = state !== "ended" && state !== "error";

  $("mon-session").textContent = call.sessionId ?? "none";
  $("mon-line").textContent = `${call.settings.lineRate / 1000} kHz`;
  $("mon-model").textContent = call.settings.model;
  $("mon-mode").textContent = call.settings.mode === "ptt" ? "push to talk" : "hands-free";
  $("mon-mic").textContent = { off: "not requested", asking: "asking", on: "on", unavailable: `file mode (${call.mic.reason})` }[call.mic.status];
  $("mon-turns").replaceChildren(
    ...call.turns.map((t) =>
      el(
        "tr",
        {},
        ...[
          t.seq,
          t.source,
          t.audio_seconds == null ? "none" : `${t.audio_seconds.toFixed(1)} s`,
          fmtMs(t.latency.headline_ms),
          t.stt ? fmtMs(t.latency.stt_ms) : "none",
          t.stt ? (t.stt.cache_hit ? "hit" : "miss") : "none",
        ].map((v) => el("td", { textContent: String(v) })),
      ),
    ),
  );
}

// ---- wiring --------------------------------------------------------------------------------

function preset(select, value) {
  if ([...select.options].some((o) => o.value === value)) select.value = value;
}
preset($("line-rate"), params.get("line"));
preset($("stt-model"), params.get("model"));
preset($("turn-mode"), params.get("mode") === "hands-free" ? "handsfree" : params.get("mode"));

for (const id of ["line-rate", "stt-model", "turn-mode"]) {
  $(id).addEventListener("change", () => {
    if (state === "idle") {
      call = newCall();
      render();
    }
  });
}

$("place-call").addEventListener("click", () => dispatch("PLACE"));
$("answer").addEventListener("click", () => dispatch("ANSWER"));
$("decline").addEventListener("click", () => dispatch("DECLINE"));
$("hangup").addEventListener("click", () => dispatch("HANGUP"));
$("new-call").addEventListener("click", () => dispatch("RESET"));
$("continue").addEventListener("click", () => dispatch("CONTINUE"));
$("retry").addEventListener("click", () => {
  audio.ctx?.resume().catch(() => {}); // this click is the gesture an audio_blocked error was waiting for
  dispatch("RETRY");
});

$("clip-select").addEventListener("change", (e) => {
  $("send-clip").disabled = !e.target.value;
});
// Someone choosing a file is not silent: stop the 8 s no-speech timer for this turn.
document.querySelector(".file-turn").addEventListener("focusin", () => {
  if (listen?.silenceTimer) {
    listen.silenceTimer = false;
    render();
  }
});
$("send-clip").addEventListener("click", () => {
  const name = $("clip-select").value;
  if (name) sendFileTurn(() => api.clipBytes(name));
});
$("file-input").addEventListener("change", (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (file) sendFileTurn(() => file.arrayBuffer());
});

const ptt = $("ptt");
ptt.addEventListener("pointerdown", (e) => {
  ptt.setPointerCapture(e.pointerId);
  pttDown();
});
ptt.addEventListener("pointerup", pttUp);
ptt.addEventListener("pointercancel", pttUp);
ptt.addEventListener("contextmenu", (e) => e.preventDefault());

// Space talks unless focus is on another control that Space would operate.
const spaceIsFree = (target) => target === ptt || !target.closest?.("button, select, input, textarea, a, summary");
document.addEventListener("keydown", (e) => {
  if (e.code !== "Space" || !canPtt() || !spaceIsFree(e.target)) return;
  e.preventDefault();
  if (!e.repeat) pttDown();
});
document.addEventListener("keyup", (e) => {
  if (e.code === "Space" && listen?.ptt) {
    e.preventDefault();
    pttUp();
  }
});

window.samajhPhone = {
  state: () => state,
  log: () => structuredClone(call.turns),
};

render();
loadClips();
api.health().then(
  (h) => {
    $("mon-server").textContent = h.gnani_key_configured ? "ok, Gnani key configured" : "ok, no Gnani key configured";
    if (!h.gnani_key_configured) {
      $("server-note").textContent = "This server has no Gnani key. Speech steps will fail and show the server's error.";
    }
  },
  (e) => {
    $("mon-server").textContent = `${e.code}: ${e.message}`;
    $("server-note").textContent = `The local server is not answering (${e.code}). A call will fail at Connecting.`;
  },
);
