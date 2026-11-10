// Pure: mono Float32 frames to a 16-bit PCM WAV.

export function encodeWav(frames, sampleRate, sampleCount = Infinity) {
  const total = Math.min(
    sampleCount,
    frames.reduce((n, f) => n + f.length, 0),
  );
  const view = new DataView(new ArrayBuffer(44 + total * 2));
  const ascii = (at, text) => {
    for (let i = 0; i < text.length; i++) view.setUint8(at + i, text.charCodeAt(i));
  };
  ascii(0, "RIFF");
  view.setUint32(4, 36 + total * 2, true);
  ascii(8, "WAVEfmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  ascii(36, "data");
  view.setUint32(40, total * 2, true);
  let written = 0;
  for (const f of frames) {
    for (let i = 0; i < f.length && written < total; i++, written++) {
      const s = Math.max(-1, Math.min(1, f[i]));
      view.setInt16(44 + written * 2, Math.round(s < 0 ? s * 32768 : s * 32767), true);
    }
  }
  return view.buffer;
}

export function wavBlob(frames, sampleRate, sampleCount) {
  return new Blob([encodeWav(frames, sampleRate, sampleCount)], { type: "audio/wav" });
}
