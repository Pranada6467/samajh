// node tests/server/vad_check.mjs FILE.wav [--tail-ms 1500] [--hangover-ms 700] [--chunk 128]
//      [--initial-noise 0.02]
// Runs web/vad.js over a 16-bit PCM WAV followed by silence and prints the events as JSON.
import { readFileSync } from "node:fs";
import { parseArgs } from "node:util";

import { createVad } from "../../web/vad.js";

const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    "tail-ms": { type: "string", default: "1500" },
    "hangover-ms": { type: "string", default: "700" },
    chunk: { type: "string", default: "128" },
    "initial-noise": { type: "string", default: "0" },
  },
});
if (positionals.length !== 1) {
  console.error("usage: vad_check.mjs FILE.wav [--tail-ms 1500] [--hangover-ms 700] [--chunk 128]");
  process.exit(2);
}

function readWav(path) {
  const bytes = readFileSync(path);
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const tag = (at) => bytes.toString("latin1", at, at + 4);
  if (tag(0) !== "RIFF" || tag(8) !== "WAVE") throw new Error("not a RIFF/WAVE file");
  let fmt = null;
  for (let at = 12; at + 8 <= bytes.length; ) {
    const size = view.getUint32(at + 4, true);
    const body = at + 8;
    if (tag(at) === "fmt ") {
      fmt = {
        format: view.getUint16(body, true),
        channels: view.getUint16(body + 2, true),
        sampleRate: view.getUint32(body + 4, true),
        bits: view.getUint16(body + 14, true),
      };
    } else if (tag(at) === "data") {
      if (!fmt || fmt.format !== 1 || fmt.bits !== 16) throw new Error("only 16-bit PCM is supported");
      const frames = Math.floor(Math.min(size, bytes.length - body) / (2 * fmt.channels));
      const samples = new Float32Array(frames);
      for (let i = 0; i < frames; i++) {
        let sum = 0;
        for (let c = 0; c < fmt.channels; c++) sum += view.getInt16(body + (i * fmt.channels + c) * 2, true);
        samples[i] = sum / fmt.channels / 32768;
      }
      return { sampleRate: fmt.sampleRate, samples };
    }
    at = body + size + (size % 2);
  }
  throw new Error("no data chunk");
}

const { sampleRate, samples } = readWav(positionals[0]);
const tail = Math.round((Number(values["tail-ms"]) * sampleRate) / 1000);
const stream = new Float32Array(samples.length + tail);
stream.set(samples);

const vad = createVad({
  sampleRate,
  hangoverMs: Number(values["hangover-ms"]),
  initialNoiseRms: Number(values["initial-noise"]),
});

const chunk = Math.max(1, Number(values.chunk));
const events = [];
for (let at = 0; at < stream.length; at += chunk) events.push(...vad.push(stream.subarray(at, at + chunk)));

console.log(
  JSON.stringify({ sampleRate, durationMs: (samples.length * 1000) / sampleRate, events, state: vad.state() }),
);
