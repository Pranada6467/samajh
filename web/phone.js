import { ApiError, api } from "./api.js";
import { createVad } from "./vad.js";
import { encodeWav } from "./wav.js";

const NO_SPEECH_MS = 8000;
const CASE_POLL_MS = 1500;
const CASE_WAIT_MS = 15 * 60 * 1000;
const MAX_TURN_MS = 28000; // the server refuses more than 30 s
const PREROLL_MS = 300;
const TAIL_MS = 200; // silence kept after the last voiced frame
const MIN_PTT_MS = 200;
const VAD_MIN_SPEECH_MS = 120;
const MAX_CARRIED_NOISE_RMS = 0.02;
// The speaker is still sounding for a moment after the buffer ends; do not hear the bot as the customer.
const ECHO_GUARD_MS = 150;
const VAD_PAUSE_MS = 150; // unvoiced gaps inside speech worth a mark in the turn's report
const MAX_MARKS = 400;
const MAX_TALK_OVER = 200;

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
const audio = { ctx: null, workletReady: false, mic: null, playing: null, ring: null, talk: null };

// ---- measurement reports -------------------------------------------------------------------
// The phone tells the server how it took each turn and played each prompt. Logged by the server,
// never acted on: a failed report only warns and never touches the call.

const boundedMs = (x) => (Number.isFinite(x) ? Math.min(600000, Math.max(0, x)) : null);

function postReport(sessionId, seq, body) {
  if (!sessionId || seq == null) return;
  const url = `/api/sessions/${encodeURIComponent(sessionId)}/events/${seq}/browser`;
  fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
    .then((res) => {
      if (!res.ok) console.warn(`[samajh] report for event ${seq} refused: HTTP ${res.status}`);
    })
    .catch((e) => console.warn(`[samajh] report for event ${seq} not sent: ${e.message}`));
}

// One customer turn's marks, from when listening opened.
function newListenReport() {
  return { openedAt: performance.now(), marks: [], takes: 0, graceUsed: false };
}

function mark(report, type, ms = null) {
  if (!report || report.marks.length >= MAX_MARKS) return;
  const m = { type, at_ms: boundedMs(performance.now() - report.openedAt) ?? 0 };
  if (ms != null && boundedMs(ms) != null) m.ms = boundedMs(ms);
  report.marks.push(m);
}

// Voiced runs on the mic while bot audio plays, for the playback report. Never a turn.
function startTalkOver() {
  if (!audio.mic || !audio.ctx) return (audio.talk = null);
  audio.talk = {
    startAt: performance.now(),
    vad: createVad({ sampleRate: audio.ctx.sampleRate, hangoverMs: 300, minSpeechMs: 120, initialNoiseRms: call.noiseRms ?? 0 }),
    open: null, // { start_ms, from } of the run being heard
    runs: [],
  };
}

function hearTalkOver(samples) {
  const T = audio.talk;
  for (const ev of T.vad.push(samples)) {
    if (ev.type === "speech_start") {
      T.open = { start_ms: performance.now() - T.startAt - (ev.atMs - ev.voicedFromMs), from: ev.voicedFromMs };
    } else if (ev.type === "speech_end" && T.open) {
      closeTalkRun(T, ev.lastVoicedMs);
    }
  }
}

function closeTalkRun(T, untilMs) {
  if (T.runs.length < MAX_TALK_OVER) {
    T.runs.push({ start_ms: boundedMs(T.open.start_ms) ?? 0, ms: boundedMs(untilMs - T.open.from) ?? 0 });
  }
  T.open = null;
}

function stopTalkOver() {
  const T = audio.talk;
  audio.talk = null;
  if (!T) return [];
  if (T.open) closeTalkRun(T, T.vad.state().timeMs);
  return T.runs;
}

function newCall() {
  return {
    settings: {
      lineRate: Number($("line-rate").value),
      record: $("record").value,
      language: $("language").value,
      mode: $("turn-mode").value,
      identityCheck: $("identity-check").value,
      identityAttempts: Number($("identity-attempts").value),
    },
    sessionId: null,
    streaming: false, // the server streams this call's primary readings (session create says)
    bot: null,
    turns: [],
    pending: null,
    failure: null,
    summary: null,
    endError: null,
    caseFile: null, // the after-call case file, as the server last reported it
    caseError: null,
    outcome: null, // the dialogue's outcome, from the turn response that ended the call
    speakerConfirmed: null, // true, false, or null when the dialogue does not say
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
    clearTimeout(listen?.graceTimer);
    // What this turn learned about the room's noise carries to the next one. Capped, and taken
    // only between utterances, so a loud turn cannot deafen the detector.
    const heard = listen?.vad?.state();
    if (heard && !heard.speaking) call.noiseRms = Math.min(heard.noiseRms, MAX_CARRIED_NOISE_RMS);
    listen?.streamer?.close();
    call.lastListen = listen;
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
      const params = sessionParams(call.settings);
      const identity = identityRequest(call.settings.identityCheck, call.settings.identityAttempts, identityMenu?.default);
      const s = await api.createSession({ line_rate: call.settings.lineRate, params, identity });
      if (!live()) return void api.endSession(s.session_id).catch(() => {});
      call.sessionId = s.session_id;
      call.settings.lineRate = s.line_rate;
      call.dialogue = s.dialogue;
      call.streaming = s.streaming === true;
      call.bot = s.bot;
      dispatch("SESSION");
    } catch (e) {
      if (live()) dispatch("FAIL", e);
    }
  },

  async bot_speaking(_, from, event) {
    const live = guard();
    const bot = call.bot;
    const sessionId = call.sessionId;
    if (event !== "RETRY") addBotBubble(bot);
    // One file per line when the server offers it, so line 0 plays as soon as it is made; an older
    // server's utterance is the one joined file.
    const perLine = bot.lines?.length > 0 && bot.lines.every((line) => line.audio_url);
    const urls = perLine ? bot.lines.map((line) => line.audio_url) : [bot.audio_url];
    const gapMs = perLine ? (bot.line_gap_ms ?? 150) : 0;
    // Line k+1 is fetched as soon as line k's fetch returns, so it is on its way while k plays.
    // Nothing more is fetched once the call has moved on (a hang-up); a fetch in flight is dropped.
    const fetches = [];
    const fetchLine = (k) => {
      fetches[k] = api.bytes(urls[k]).then((bytes) => {
        if (k + 1 < urls.length && live()) fetchLine(k + 1);
        return bytes;
      });
      fetches[k].catch(() => {}); // awaited below, in order; a failure no one awaits is not unhandled
    };
    fetchLine(0);
    let botStartMs = null;
    let started = false;
    let playedMs = 0;
    let completed = false;
    let reported = false;
    // One report per utterance, across all its lines, once line 0 has begun.
    const report = () => {
      if (!started || reported) return;
      reported = true;
      const talkOver = stopTalkOver();
      const sent = {
        bot_start_ms: boundedMs(botStartMs),
        output_latency_ms: boundedMs((audio.ctx?.outputLatency ?? NaN) * 1000),
        played_ms: boundedMs(playedMs),
        completed,
        talk_over: talkOver,
      };
      console.info(
        `[samajh] bot ${bot.seq}: lines=${urls.length} bot_start_ms=${sent.bot_start_ms == null ? "n/a" : Math.round(sent.bot_start_ms)} played_ms=${Math.round(playedMs)} completed=${completed} talk_over=${talkOver.length}`,
      );
      postReport(sessionId, bot.seq, sent);
    };
    try {
      for (let k = 0; k < urls.length; k += 1) {
        if (k > 0) await new Promise((done) => setTimeout(done, gapMs));
        if (!live()) break;
        const bytes = await fetches[k];
        if (!live()) break;
        let lineCompleted = false;
        await play(
          bytes,
          live,
          () => {
            if (k > 0) return;
            started = true;
            // End of the customer's speech (or of the upload) to the first sample of the reply.
            const last = call.turns.at(-1);
            if (last && last.botSeq === bot.seq) {
              if (last.latency.bot_start_ms == null) {
                last.latency.bot_start_ms = performance.now() - last.voiceEndAt;
                render();
              }
              botStartMs = last.latency.bot_start_ms;
            }
            startTalkOver();
          },
          ({ playedMs: ms, completed: done }) => {
            playedMs += ms;
            lineCompleted = done;
          },
        );
        if (!lineCompleted) break;
        if (k === urls.length - 1) completed = true;
      }
      report();
      if (completed && live()) dispatch("BOT_DONE");
    } catch (e) {
      report();
      if (live()) dispatch("FAIL", e);
    }
  },

  listening() {
    const handsFree = call.settings.mode === "handsfree" && call.mic.status === "on";
    // How patient to be is the bot's to say: it knows whether it asked a yes/no or an open question.
    const patience = call.bot.listen ?? { kind: "open", cut_ms: 1100, grace_ms: 1800 };
    listen = {
      vad: handsFree
        ? createVad({
            sampleRate: audio.ctx.sampleRate,
            minSpeechMs: VAD_MIN_SPEECH_MS,
            hangoverMs: patience.cut_ms,
            initialNoiseRms: call.noiseRms ?? 0,
            pauseMs: VAD_PAUSE_MS,
          })
        : null,
      patience,
      report: newListenReport(),
      started: false, // speech has begun in this turn: from then on nothing captured is dropped
      take: null, // the take sent at the last cut, waiting out the grace window
      part: 0,
      graceTimer: null,
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
      // Hands-free only: the reply's audio also goes to the server's stream from the pre-roll on,
      // and the first cut commits it. The take's WAV is uploaded as before; the server reads it
      // by REST when the stream fails, and a later take is always read by REST.
      streamer: handsFree && call.streaming ? openStreamer(call.sessionId, call.bot.seq, audio.ctx.sampleRate, call.settings.lineRate) : null,
    };
    note("");
  },

  async transcribing(data, from, event) {
    if (event === "TURN") {
      // A take sent at the cut is already on its way; anything else is sent now.
      call.pending = data.take ?? newTake(data.source, data.body, data.voiceEndAt ?? performance.now(), 1);
    }
    const turn = call.pending;
    const live = guard();
    if (!turn.request) turn.request = sendTake(turn);
    const eosWaitMs = turn.eosWaitMs;
    try {
      const reply = await turn.request;
      const postMs = performance.now() - turn.sentAt;
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
        readings: c.readings,
        acted_on: c.acted_on,
        readings_agreed: c.readings_agreed,
        followed_by: c.followed_by,
        degraded: c.degraded,
        part: c.part,
        sends: turn.tries,
        botSeq: reply.bot.seq,
        voiceEndAt: turn.voiceEndAt,
        latency: {
          ...c.latency,
          eos_wait_ms: eosWaitMs,
          post_ms: postMs,
          headline_ms: (eosWaitMs ?? 0) + postMs,
          bot_start_ms: null,
        },
        pauses: c.pauses,
      };
      call.turns.push(record);
      reportListen(call.sessionId, c.seq, turn, eosWaitMs, postMs);
      call.outcome = reply.outcome;
      call.speakerConfirmed = reply.speaker_confirmed;
      addCustomerBubble(record, call.bot.language);
      call.bot = reply.bot;
      call.pending = null;
      dispatch("REPLY");
    } catch (e) {
      turn.request = null; // Try again sends the same take once more; the server answers it once
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
    if (!live()) return;
    render();
    if (!call.endError) await followCase(live);
  },
};

// The after-call job: start it, then poll until the case file is ready or a step has failed.
async function followCase(live) {
  const mine = call;
  const until = performance.now() + CASE_WAIT_MS;
  try {
    mine.caseFile = await api.startCase(mine.sessionId);
    while (mine.caseFile.status === "running" && performance.now() < until) {
      if (live()) render();
      await new Promise((done) => setTimeout(done, CASE_POLL_MS));
      if (call !== mine) return;
      mine.caseFile = await api.getCase(mine.sessionId);
    }
    if (mine.caseFile.status === "running") {
      mine.caseError = new ApiError({ stage: "case", code: "case_timeout", message: "The case file was not ready after 15 minutes." });
    }
  } catch (e) {
    mine.caseError = asApiError(e);
  }
  if (call === mine) render();
}

function reportListen(sessionId, seq, turn, eosWaitMs, postMs) {
  const r = turn.report ?? newListenReport();
  const p = turn.patience;
  const vadMode = turn.source !== "file" && call.settings.mode !== "ptt";
  const report = {
    mode: turn.source === "file" ? "file" : call.settings.mode === "ptt" ? "ptt" : "vad",
    cut_ms: vadMode ? boundedMs(p?.cut_ms) : null,
    grace_ms: vadMode ? boundedMs(p?.grace_ms) : null,
    marks: r.marks,
    takes: r.takes,
    grace_used: r.graceUsed,
    eos_wait_ms: boundedMs(eosWaitMs),
    post_ms: boundedMs(postMs),
    echo_cancellation: audio.mic?.stream.getAudioTracks()[0]?.getSettings().echoCancellation ?? null,
  };
  console.info(
    `[samajh] customer ${seq}: takes=${report.takes} grace_used=${report.grace_used} marks=${report.marks.length} eos_wait_ms=${report.eos_wait_ms == null ? "n/a" : Math.round(report.eos_wait_ms)} post_ms=${Math.round(postMs)}`,
  );
  postReport(sessionId, seq, report);
}

function newTake(source, body, voiceEndAt, part) {
  // The turn's report and patience go with the take: listening has closed by the time it is answered.
  const L = listen ?? call.lastListen;
  return {
    source, body, voiceEndAt, part, tries: 0, request: null, sentAt: 0, eosWaitMs: null, botSeq: call.bot.seq,
    report: L?.report ?? null, patience: L?.patience ?? call.bot.listen,
  };
}

function sendTake(take) {
  take.tries += 1;
  if (take.report) {
    if (take.tries === 1) take.report.takes += 1;
    mark(take.report, "send");
  }
  take.sentAt = performance.now();
  // Measured once: a second send after an error screen must not count the time spent on it.
  if (take.eosWaitMs == null) take.eosWaitMs = take.source === "mic" ? take.sentAt - take.voiceEndAt : null;
  const p = listen?.patience ?? call.bot.listen;
  return api.postTurn(call.sessionId, {
    source: take.source,
    body: take.body,
    eosWaitMs: take.eosWaitMs,
    // Names the prompt being answered, so a turn sent twice is answered once.
    replyTo: take.botSeq,
    part: take.part,
    mode: take.source === "file" ? "file" : call.settings.mode === "ptt" ? "ptt" : "vad",
    cutMs: take.source === "mic" && call.settings.mode !== "ptt" ? p?.cut_ms : null,
    graceMs: take.source === "mic" && call.settings.mode !== "ptt" ? p?.grace_ms : null,
  });
}

function asApiError(e) {
  if (e instanceof ApiError) return e;
  return new ApiError({ stage: "phone", code: "phone_bug", message: `${e.name}: ${e.message}` });
}

// ---- audio out -----------------------------------------------------------------------------

// onEnd({ playedMs, completed }) runs once when the audio ends or is stopped.
async function play(bytes, live, onStart = () => {}, onEnd = () => {}) {
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
    let startedAt = 0;
    source.onended = () => {
      try {
        onEnd({ playedMs: performance.now() - startedAt, completed: !source.stopped });
      } catch (e) {
        console.warn(`[samajh] playback report failed: ${e.message}`);
      }
      done();
    };
    audio.playing = source;
    source.start();
    startedAt = performance.now();
    onStart();
  });
}

function stopPlayback() {
  try {
    if (audio.playing) audio.playing.stopped = true;
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
  // While the bot plays, frames are only measured for talk-over, never kept or sent.
  if (state === "bot_speaking" && audio.talk) return hearTalkOver(samples);
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
  // Before the first word only the preroll is kept. After it nothing is dropped: an answer the
  // detector cut at a pause may go on, and the next take carries the whole answer.
  if (!L.started && !L.ptt) {
    while (toMs(L.buffered - L.chunks[0].length) >= L.prerollMs) L.buffered -= L.chunks.shift().length;
  }

  for (const ev of L.vad?.push(samples) ?? []) {
    if (ev.type === "speech_start") {
      L.speaking = true;
      L.started = true;
      mark(L.report, "speech_start");
      if (L.take) {
        mark(L.report, "resume");
        L.report.graceUsed = true;
        resumed(L);
      }
      render();
    } else if (ev.type === "pause") {
      mark(L.report, "pause", ev.toMs - ev.fromMs);
    } else if (L.speaking) {
      L.speaking = false;
      const keepUntil = Math.round(((ev.lastVoicedMs + TAIL_MS) * rate) / 1000);
      const drop = Math.max(0, L.stream - keepUntil);
      const voiceEndAt = performance.now() - (ev.atMs - ev.lastVoicedMs);
      cut(L, L.buffered - drop, voiceEndAt);
      render();
    }
  }
  if (L.streamer && L.started) {
    if (!L.streamer.began) {
      L.streamer.began = true;
      for (const c of L.chunks) L.streamer.push(c); // the pre-roll and this frame
    } else {
      L.streamer.push(samples);
    }
  }
  if (L.silenceTimer && !L.started && toMs(L.stream) >= NO_SPEECH_MS) {
    return dispatch("TURN", { source: "none", body: null });
  }
  if ((L.speaking || L.ptt) && toMs(L.buffered) >= MAX_TURN_MS) sendMic(L.buffered, performance.now());
}

// The detector heard a pause as long as the cut: send what was said so far at once, so its
// readings are under way, and wait out the grace window before the bot may answer it.
function cut(L, sampleCount, voiceEndAt) {
  mark(L.report, "cut", L.patience.cut_ms);
  L.part += 1;
  if (L.part === 1) L.streamer?.commit();
  const take = newTake("mic", encodeWav(L.chunks, audio.ctx.sampleRate, sampleCount), voiceEndAt, L.part);
  take.request = sendTake(take);
  take.request.catch(() => {}); // a take that is replaced may fail unread
  L.take = take;
  clearTimeout(L.graceTimer);
  const wait = Math.max(0, L.patience.grace_ms - (performance.now() - voiceEndAt));
  L.graceTimer = setTimeout(() => {
    if (listen === L && state === "listening" && L.take === take) {
      mark(L.report, "grace_expired");
      dispatch("TURN", { source: "mic", take });
    }
  }, wait);
}

// The customer went on within the grace window: the take sent at the cut will be replaced by a
// later one holding the whole answer, and its reply is never played.
function resumed(L) {
  clearTimeout(L.graceTimer);
  L.take = null;
}

// ---- streaming ------------------------------------------------------------------------------

// Float32 frames at the AudioContext rate to PCM s16le at the line rate. Cheap on purpose: a
// running box filter as wide as the rate ratio (its first null is at the output rate, so it damps
// what would alias) and then linear interpolation, with the state carried across frames.
function createResampler(inRate, outRate) {
  const step = inRate / outRate;
  const taps = Math.max(1, Math.round(step));
  const hist = new Float32Array(taps);
  let at = 0, sum = 0, prev = 0, pos = 0; // pos: next output time, in input samples of this frame
  return (samples) => {
    const out = new Int16Array(Math.ceil((samples.length - pos) / step) + 1);
    let n = 0;
    for (let i = 0; i < samples.length; i++) {
      sum += samples[i] - hist[at];
      hist[at] = samples[i];
      at = (at + 1) % taps;
      const cur = sum / taps;
      for (; pos <= i; pos += step) {
        const v = prev + (cur - prev) * (pos - (i - 1));
        out[n++] = Math.max(-1, Math.min(1, v)) * 32767;
      }
      prev = cur;
    }
    pos -= samples.length;
    return out.subarray(0, n);
  };
}

// One reply's stream: frames before the socket opens are held, then sent in order.
function openStreamer(sessionId, replyTo, inRate, lineRate) {
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${scheme}://${location.host}/api/sessions/${encodeURIComponent(sessionId)}/stream?reply_to=${replyTo}`);
  ws.binaryType = "arraybuffer";
  const resample = createResampler(inRate, lineRate);
  const held = [];
  const S = { began: false, committed: false, closed: false, sentBytes: 0 };
  const out = (m) => {
    if (ws.readyState === WebSocket.OPEN) ws.send(m);
    else if (ws.readyState === WebSocket.CONNECTING) held.push(m);
  };
  ws.onopen = () => held.splice(0).forEach((m) => ws.send(m));
  ws.onmessage = (e) => {
    try {
      const m = JSON.parse(e.data);
      console.info(`[samajh] stream ${replyTo}: ${m.type}${m.reason ? ` (${m.reason})` : ""} after ${S.sentBytes} bytes`);
    } catch {}
  };
  ws.onclose = () => (S.closed = true);
  // About 40 ms per message, not one per render quantum (~375 tiny messages a second).
  const batchSamples = Math.round(lineRate * 0.04);
  let parts = [], partSamples = 0;
  const flush = () => {
    if (!partSamples) return;
    const pcm = new Int16Array(partSamples);
    let at = 0;
    for (const p of parts) { pcm.set(p, at); at += p.length; }
    parts = []; partSamples = 0;
    S.sentBytes += pcm.byteLength;
    out(pcm.buffer);
  };
  S.push = (samples) => {
    if (S.committed || S.closed) return;
    const pcm = resample(samples);
    parts.push(pcm.slice());
    partSamples += pcm.length;
    if (partSamples >= batchSamples) flush();
  };
  S.commit = () => {
    if (S.committed || S.closed) return;
    flush();
    S.committed = true;
    out(JSON.stringify({ type: "commit" }));
  };
  // Leaving the turn: an uncommitted stream is dropped; a committed one is closed by the server.
  S.close = () => {
    if (!S.committed && !S.closed) ws.close();
  };
  return S;
}

// voiceEndAt: when the customer stopped (push to talk: release; a turn at the length limit: now).
function sendMic(sampleCount, voiceEndAt) {
  listen.part += 1;
  if (listen.part === 1) listen.streamer?.commit();
  const take = newTake("mic", encodeWav(listen.chunks, audio.ctx.sampleRate, sampleCount), voiceEndAt, listen.part);
  dispatch("TURN", { source: "mic", take });
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
    if (live()) dispatch("TURN", { source: "file", body, voiceEndAt: performance.now() });
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

// "prisma-v3.0" -> "Prisma v3.0": the name is the reading's own `model` field, only re-cased.
function modelName(model) {
  const [family, ...rest] = String(model).split("-");
  return [family.charAt(0).toUpperCase() + family.slice(1), ...rest].join(" ");
}

// Requests that must not read as the borrower's own when the speaker was never confirmed.
const NEEDS_CONFIRMED_SPEAKER = new Set(["do_not_call", "human_requested", "call_back_later", "written_requested"]);

function outcomeText(outcome, speakerConfirmed) {
  const unconfirmed = speakerConfirmed === false && NEEDS_CONFIRMED_SPEAKER.has(outcome);
  return `${outcome.replaceAll("_", " ")}${unconfirmed ? " (from an unconfirmed speaker)" : ""}`;
}

// The two readings of a figure turn in one line, from the server's fields alone: the readings
// (each with its model and text), `readings_agreed` as the dialogue recorded it, `followed_by`
// as the server derived it from the bot's next line, and the model of the reading acted on.
// Null when the turn was read once or neither reading holds a figure (readings_agreed is null).
function readingsLine(readings, agreed, followedBy, actedModel) {
  if (readings.length < 2 || agreed == null) return null;
  const said = readings.map((r) => `${modelName(r.model)}: ${r.ok ? r.text || "(no text)" : `no reading (${r.error})`}`);
  const missing = readings.find((r) => !r.ok);
  let verdict = agreed ? "same amount" : missing ? `${modelName(missing.model)} missing` : "differ";
  if (followedBy === "asked_again") verdict += ", asked again";
  else if (followedBy === "read_back") verdict += agreed ? ", read back" : `, ${modelName(actedModel)}'s figure read back`;
  return [...said, verdict].join(" · ");
}

const DEGRADED_TEXT = "The classifier did not answer in time; this turn was read by the word lists.";
const readingsNotes = new Map(); // record id -> the record's `readings_note`, from /api/records

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
  const acted = turn.readings.find((r) => r.role === turn.acted_on);
  const both = readingsLine(turn.readings, turn.readings_agreed, turn.followed_by, acted?.model);
  if (both) {
    li.append(setLang(el("p", { className: "readings", textContent: both }), botLanguage));
    // A demo record whose clip was chosen for this: said where the readings differ, not as a rate.
    const chosen = turn.readings_agreed === false ? readingsNotes.get(call.settings.record) : null;
    if (chosen) li.append(el("p", { className: "readings-note", textContent: chosen }));
  }
  if (turn.degraded) li.append(el("p", { className: "degraded", textContent: DEGRADED_TEXT }));

  const t = turn.latency;
  const rows = [
    turn.source === "mic" && ["Detector wait (last voiced frame to upload)", fmtMs(t.eos_wait_ms)],
    ["Request (upload, server, reply)", fmtMs(t.post_ms)],
    ["Server total", fmtMs(t.server_ms)],
    turn.audio_url && ["Server: resample to line rate", fmtMs(t.normalise_ms)],
    turn.readings.length > 0 && [`Server: ${turn.readings[0].model}, first call`, fmtMs(t.stt_ms)],
    turn.readings.length > 1 && [`Server: ${turn.readings[1].model}, second call`, fmtMs(t.second_stt_ms)],
    ["Server: dialogue", fmtMs(t.dialogue_ms)],
    ...turn.readings.map((r) => [
      `Reading by ${r.model}${r.role === turn.acted_on ? " (the call acted on this one)" : ""}`,
      r.ok ? `${r.text || "(no text)"}${r.cache_hit ? " · cached" : ""}` : `missing (${r.error})`,
    ]),
    turn.part > 1 && ["Takes of this answer", `${turn.part} (resumed after a pause)`],
    turn.pauses && ["Longest pause inside the answer", fmtMs(turn.pauses.longest_pause_ms)],
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
      if (listen?.take) return "Heard a pause. Keep talking to add to your answer, or wait for the reply.";
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
  const outcome = call.outcome ? ` Outcome: ${outcomeText(call.outcome, call.speakerConfirmed)}.` : "";
  return `${s.turns} customer turns, ${s.events} events, ${recording}. Ended by: ${s.ended_reason ?? "unknown"}.${outcome}`;
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
    $("retry").textContent = from === "transcribing" && call.pending?.body ? "Send again" : "Try again";
    $("continue").hidden = from === "connecting";
    $("continue").textContent = from === "transcribing" ? "Record the turn again" : "Continue without this audio";
  }

  if (state === "ended") {
    $("summary-text").textContent = summaryText();
    renderCase();
    $("log-link").hidden = $("recording-link").hidden = !call.sessionId;
    if (call.sessionId) {
      $("log-link").href = api.logUrl(call.sessionId);
      $("recording-link").href = api.recordingUrl(call.sessionId);
    }
  }
  for (const b of document.querySelectorAll(".heard")) b.disabled = state !== "ended" && state !== "error";

  $("mon-session").textContent = call.sessionId ?? "none";
  $("mon-line").textContent = `${call.settings.lineRate / 1000} kHz`;
  $("mon-record").textContent = call.settings.record ? `${call.settings.record} · ${call.settings.language}` : "none";
  $("mon-listen").textContent = state === "listening" && listen ? `${listen.patience.kind}: cut ${listen.patience.cut_ms} ms, grace ${listen.patience.grace_ms} ms` : "n/a";
  $("mon-mode").textContent = call.settings.mode === "ptt" ? "push to talk" : "hands-free";
  $("mon-identity").textContent =
    call.settings.identityCheck === "year_of_birth" ? `year of birth, ${call.settings.identityAttempts} attempt(s)` : "none";
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
          String(t.part ?? 1),
          fmtMs(t.latency.bot_start_ms),
          t.readings.length ? fmtMs(t.latency.stt_ms + (t.latency.second_stt_ms ?? 0)) : "none",
          t.readings.length ? t.readings.map((r) => (r.cache_hit ? "hit" : "miss")).join("/") : "none",
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
preset($("language"), params.get("lang"));
preset($("turn-mode"), params.get("mode") === "hands-free" ? "handsfree" : params.get("mode"));

preset($("identity-check"), params.get("identity"));
preset($("identity-attempts"), params.get("attempts"));

for (const id of ["line-rate", "record", "language", "turn-mode", "identity-check", "identity-attempts"]) {
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
  caseFile: () => structuredClone({ file: call.caseFile, error: call.caseError ? { code: call.caseError.code, message: call.caseError.message } : null }),
};

// A picker value is a packaged record id, or "loan:<loan id>" for a loan drawn from the synthetic loan book.
const LOAN = "loan:";

function sessionParams(settings) {
  if (!settings.record) return {};
  if (settings.record.startsWith(LOAN)) return { loan: settings.record.slice(LOAN.length), language: settings.language };
  return { record: settings.record, language: settings.language };
}

// ---- the right-party setting (samajh.identity) and the prior notice ------------------------------

let identityMenu = null; // GET /api/identity/menu: the options, their descriptions, the server's default

// The session request's `identity` for the picker's choice. The two fields the picker does not
// offer (prior_notice, call_back_line) keep the server's setting. Attempts only with a second check.
// Pure: tests/server/test_phone_identity.py runs it under Node.
function identityRequest(check, attempts, defaults) {
  const year = check === "year_of_birth";
  const body = { second_check: year ? "year_of_birth" : "none", attempts: year && attempts === 2 ? 2 : 1 };
  if (defaults && typeof defaults.prior_notice === "boolean") body.prior_notice = defaults.prior_notice;
  if (defaults && typeof defaults.call_back_line === "boolean") body.call_back_line = defaults.call_back_line;
  return body;
}

// The server's honest description of a choice, from the menu; null before the menu has loaded.
// Pure: tests/server/test_phone_identity.py runs it under Node.
function identityDescription(menu, check, attempts) {
  const option = menu?.options?.find((o) => o.id === check);
  if (!option) return null;
  const n = option.attempts.includes(attempts) ? attempts : option.attempts[0];
  return option.descriptions[String(n)] ?? null;
}

function renderIdentity() {
  const year = $("identity-check").value === "year_of_birth";
  $("identity-attempts").disabled = !year;
  $("identity-attempts").hidden = $("identity-attempts-label").hidden = !year;
  $("identity-note").textContent = identityDescription(identityMenu, $("identity-check").value, Number($("identity-attempts").value)) ?? "";
}

let noticeAsked = 0;
async function renderNotice() {
  const card = $("notice-card");
  const shown = identityMenu?.default?.prior_notice === true;
  const value = $("record").value;
  if (!shown || !value) return void (card.hidden = true);
  const mine = ++noticeAsked;
  const query = value.startsWith(LOAN) ? { loan: value.slice(LOAN.length) } : { record: value };
  try {
    const n = await api.identityNotice({ ...query, lang: $("language").value });
    if (mine !== noticeAsked) return;
    $("notice-text").textContent = n.text;
    setLang($("notice-text"), n.language);
    $("notice-review").textContent = n.review === "not human-reviewed" ? "· not human-reviewed" : "";
    card.hidden = false;
  } catch {
    if (mine === noticeAsked) card.hidden = true;
  }
}

async function loadIdentity() {
  try {
    identityMenu = await api.identityMenu();
    if (!params.get("identity")) preset($("identity-check"), identityMenu.default.second_check);
    if (!params.get("attempts")) preset($("identity-attempts"), String(identityMenu.default.attempts));
  } catch {
    identityMenu = null; // an older server: the session request then carries the picker's choice alone
  }
  renderIdentity();
  renderNotice();
  if (state === "idle") {
    call = newCall();
    render();
  }
}

for (const id of ["identity-check", "identity-attempts"]) $(id).addEventListener("change", renderIdentity);
for (const id of ["record", "language"]) $(id).addEventListener("change", renderNotice);

function loanNote(l) {
  return (
    `From the synthetic loan book of ${l.lender_name}: drawn in ${l.draw_id}, sold on ${l.sold_on}, ` +
    `call date ${l.call_date} (day ${l.day_since_sale} after the sale, in the book's calendar). ` +
    `The customer is ${l.first_name}, born in ${l.birth_year}. Synthetic record.`
  );
}

async function loadRecords() {
  const select = $("record");
  try {
    const { records } = await api.records();
    readingsNotes.clear();
    for (const r of records) if (r.readings_note) readingsNotes.set(r.id, r.readings_note);
    let loans = [];
    try {
      loans = (await api.loans()).loans;
    } catch {
      // no loan book on this server: the demo records alone
    }
    const demo = el("optgroup", { label: "Demo records" }, ...records.map((r) => new Option(`${r.label} · ${r.first_name}`, r.id)));
    const book = el("optgroup", { label: "Synthetic loan book (drawn loans)" }, ...loans.map((l) => new Option(`${l.loan_id} · ${l.first_name} · ${l.draw_id}`, LOAN + l.loan_id)));
    select.replaceChildren(demo, ...(loans.length ? [book] : []));
    if (!records.length && !loans.length) select.replaceChildren(new Option("No records on this server", ""));
    preset(select, params.get("record"));
    if (params.get("loan")) preset(select, LOAN + params.get("loan"));
    const describe = () => {
      const r = records.find((x) => x.id === select.value);
      const l = loans.find((x) => LOAN + x.loan_id === select.value);
      if (l && state === "idle") preset($("language"), l.language);
      $("record-note").textContent = l ? loanNote(l) : r ? `${r.description} Synthetic record.` : "";
    };
    select.addEventListener("change", describe);
    describe();
  } catch (e) {
    select.replaceChildren(new Option(`Records unavailable (${e.code})`, ""));
  }
  if (state === "idle") {
    call = newCall();
    render();
  }
}

const TIER_TEXT = {
  refer: "Refer to a reviewer",
  incomplete: "Incomplete: not enough to decide",
  understanding_gap: "Understanding gap (reported in aggregate)",
  clear: "Clear",
};

// The notice for a call with a turn the classifier failed on (the case file's `degraded_turns`):
// the session is void, samajh.ops does not count it, and the call is to be repeated. Null when the
// case file lists none, or is written before the field. Pure: tests/server/test_phone_card.py runs it.
function voidNotice(caseFile) {
  const n = Array.isArray(caseFile?.degraded_turns) ? caseFile.degraded_turns.length : 0;
  if (!n) return null;
  const turns = n === 1 ? "1 turn" : `${n} turns`;
  const read = n === 1 ? "That turn was" : "Those turns were";
  return `Repeat this call: the classifier failed on ${turns}, so this session is not counted. ${read} read by the word lists alone.`;
}

// What a referral rests on, from the case file's `summary.referral_basis` (samajh.types.Basis):
// "on what the customer said", "on the record alone", or null when the call is not a referral or
// the case file was written before the field. Pure: tests/server/test_phone_basis.py runs it.
function basisText(caseFile) {
  const words = { customer_statement: "on what the customer said", record_only: "on the record alone" };
  return words[caseFile?.summary?.referral_basis] ?? null;
}

// Shown above the case status, so it is read first whatever the rest of the card says.
function voidBox() {
  let node = $("case-void");
  if (!node) {
    node = el("p", { id: "case-void" });
    node.setAttribute("role", "alert");
    node.style.cssText = "margin: 0; color: var(--danger); font-weight: 600;";
    $("case-status").before(node);
  }
  return node;
}

function renderCase() {
  const box = $("case");
  const c = call.caseFile;
  const err = call.caseError;
  box.hidden = !call.sessionId || call.endError != null;
  $("case-link").hidden = !c;
  if (call.sessionId) $("case-link").href = api.caseUrl(call.sessionId);
  let status;
  let lines = [];
  let figures = [];
  let first = null; // the summary's first line, on a referral on the record alone
  if (err && err.code === "no_case_file") status = "This call's dialogue makes no case file.";
  else if (err) status = `The case file could not be made. ${err.code}: ${err.message}`;
  else if (!c) status = "Starting the case file.";
  else if (c.status === "running") status = "Preparing the case file: Prisma Batch on the recording, then extraction and the rules.";
  else if (c.status === "failed") {
    // A failed step is never shown as a result, whatever the other steps found.
    const failed = c.steps.filter((x) => !x.ok).map((x) => `${x.name} (${x.error})`);
    status = `The case file is not complete. Failed: ${failed.join("; ")}.`;
  } else {
    const basis = basisText(c);
    status = `${TIER_TEXT[c.tier] ?? c.tier}${basis ? `, ${basis}` : ""}. Call outcome: ${outcomeText(c.call_outcome, c.speaker_confirmed)}.`;
    lines = c.summary?.lines ?? [];
    first = c.summary?.first_line ?? null;
    // Both readings of every figure turn, from the case file (its `acted_on` is the model's name).
    figures = (c.turns ?? []).map((t) => readingsLine(t.readings, t.readings_agreed, t.followed_by, t.acted_on)).filter(Boolean);
  }
  box.dataset.status = err ? "failed" : (c?.status ?? "running");
  const notice = err ? null : voidNotice(c);
  const voided = voidBox();
  voided.hidden = !notice;
  voided.textContent = notice ?? "";
  $("case-status").textContent = status;
  const checked = c?.status === "ready" && c.identity?.sentence ? [el("li", { className: "identity-line", textContent: c.identity.sentence })] : [];
  $("case-lines").replaceChildren(
    ...checked,
    ...(first ? [el("li", { className: "first-line", textContent: first })] : []),
    ...lines.map((l) =>
      el(
        "li",
        {},
        el("span", { className: "tier", textContent: `${TIER_TEXT[l.tier] ?? l.tier}: ` }),
        l.title,
        ...(l.quote ? [setLang(el("q", { textContent: l.quote }), call.bot?.language)] : []),
      ),
    ),
  );
  const chosen = figures.length ? readingsNotes.get(call.settings.record) : null;
  $("case-readings").replaceChildren(
    ...figures.map((line) => setLang(el("li", { textContent: line }), call.bot?.language)),
    ...(chosen ? [el("li", { className: "readings-note", textContent: chosen })] : []),
  );
}

render();
loadClips();
loadRecords().then(renderNotice);
loadIdentity();
api.health().then(
  (h) => {
    $("mon-server").textContent = h.gnani_key_configured ? "ok, Gnani key configured" : "ok, no Gnani key configured";
    const m = h.models;
    if (m) {
      $("mon-models").textContent =
        `${modelName(m.stt_primary.model)} ${m.stt_primary.format} and ${modelName(m.stt_second.model)} ${m.stt_second.format} (figures) · ` +
        `${modelName(m.tts.model)} voice · ${modelName(m.batch.model)} Batch after the call`;
    }
    if (!h.gnani_key_configured) {
      $("server-note").textContent = "This server has no Gnani key. Speech steps will fail and show the server's error.";
    }
  },
  (e) => {
    $("mon-server").textContent = `${e.code}: ${e.message}`;
    $("server-note").textContent = `The local server is not answering (${e.code}). A call will fail at Connecting.`;
  },
);
