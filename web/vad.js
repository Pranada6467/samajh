// Energy-based end-of-speech detector. Pure: no DOM, no Web Audio, runs under Node.
//
// Samples are cut into frames of `frameMs`. A frame is voiced when its RMS is at least
// `startFactor` times the noise estimate, and the estimate never counts as lower than `floorRms`.
// The noise estimate follows unvoiced frames with a 400 ms time constant. On voiced frames it
// creeps up (doubling every 4 s), so a steady noise that starts above the threshold is absorbed
// after a few seconds instead of reading as speech for the rest of the turn; ordinary speech
// pulls it back down at every gap between words.
// `initialNoiseRms` seeds the estimate, so a caller can carry what one turn learned about the room
// into the next instead of starting from the fixed minimum every time.
// Speech starts after `minSpeechMs` of consecutive voiced frames and ends once `hangoverMs` have
// passed without a voiced frame. All times are stream time in ms from the first sample pushed.
//
// Event = { type: "speech_start", atMs, voicedFromMs }
//       | { type: "speech_end", atMs, lastVoicedMs }
// atMs: when the decision was made. voicedFromMs: start of the voiced run that triggered the
// start. lastVoicedMs: end of the last voiced frame.

const NOISE_TRACK_MS = 400;
const NOISE_DOUBLING_MS = 4000;

export function createVad({
  sampleRate,
  frameMs = 20,
  minSpeechMs = 120,
  hangoverMs = 700,
  startFactor = 3.0,
  floorRms = 0.004,
  initialNoiseRms = 0,
} = {}) {
  if (!(sampleRate > 0)) throw new TypeError("createVad needs a positive sampleRate");
  const frameLen = Math.max(1, Math.round((sampleRate * frameMs) / 1000));
  const frameDur = (frameLen * 1000) / sampleRate;
  // Counted in frames so float rounding of frameDur cannot add a frame.
  const minFrames = Math.max(1, Math.ceil(minSpeechMs / frameDur - 1e-9));
  const hangFrames = Math.max(1, Math.ceil(hangoverMs / frameDur - 1e-9));
  const track = Math.min(1, frameDur / NOISE_TRACK_MS);
  const creep = 2 ** (frameDur / NOISE_DOUBLING_MS);

  let noise = Math.max(floorRms, initialNoiseRms);
  let speaking = false;
  let frames = 0;
  let voicedRun = 0;
  let quietRun = 0;
  let runStartMs = 0;
  let lastVoicedMs = 0;
  let sumSquares = 0;
  let filled = 0;

  const threshold = () => startFactor * Math.max(noise, floorRms);

  function frame(rms, events) {
    const startMs = frames * frameDur;
    frames += 1;
    const endMs = frames * frameDur;
    if (rms >= threshold()) {
      noise = Math.max(noise, floorRms) * creep;
      if (voicedRun === 0) runStartMs = startMs;
      voicedRun += 1;
      quietRun = 0;
      lastVoicedMs = endMs;
    } else {
      noise += track * (rms - noise);
      voicedRun = 0;
      quietRun += 1;
    }
    if (!speaking && voicedRun >= minFrames) {
      speaking = true;
      events.push({ type: "speech_start", atMs: endMs, voicedFromMs: runStartMs });
    } else if (speaking && quietRun >= hangFrames) {
      speaking = false;
      events.push({ type: "speech_end", atMs: endMs, lastVoicedMs });
    }
  }

  return {
    push(samples) {
      const events = [];
      for (let i = 0; i < samples.length; i++) {
        sumSquares += samples[i] * samples[i];
        filled += 1;
        if (filled === frameLen) {
          frame(Math.sqrt(sumSquares / frameLen), events);
          sumSquares = 0;
          filled = 0;
        }
      }
      return events;
    },
    state() {
      return { speaking, timeMs: frames * frameDur, noiseRms: noise, thresholdRms: threshold() };
    },
  };
}
