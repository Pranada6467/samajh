"""Probe: Pipecat Smart Turn v3.2 (semantic end-of-turn) on our Timbre-voiced customer clips.

Probe only, not wired into the server or phone. All audio is TTS (Timbre), not human speech.

Run:
  uv run --with onnxruntime --with transformers python tests/server/probes/smart_turn_probe.py \
      --model DIR/smart-turn-v3.2-cpu.onnx --out OUTDIR [--extra-dir DIR_WITH_PAUSE_WAVS]

Inference follows pipecat-ai/smart-turn inference.py + audio_utils.py exactly: keep the last 8 s
(left-pad with zeros), WhisperFeatureExtractor(chunk_length=8), max_length=128000, do_normalize,
ORT sequential, 1 inter-op thread, ENABLE_ALL; output = sigmoid P(complete).

Voicing rule: 10 ms frames, frame RMS in dBFS; voiced if above max(-40 dBFS, loudest frame - 35 dB).
A pause is a run of >=15 unvoiced frames (150 ms) between voiced frames. End of speech = end of the
last voiced frame. Appended silence is digital zeros (as the reference's padding).
Resampler: FFT (zero-padded spectrum) 8 kHz -> 16 kHz, whole clip; no 16 kHz originals exist here.

Points:
  complete      clip to end of speech + 200 ms, and + the kind's cut (yes_no 700, short 800,
                amount 1000, open 1100; kind from the answered line key, approximate mapping)
  pause         every internal pause >=150 ms: audio to pause start + 200 ms
  splice        same-call consecutive answers A + 600/900/1200 ms silence + B: evaluated at A's
                end + 200 ms and + the kind cut (the model only sees A + silence there)
  midnum        clips whose text holds an amount: cut at the unvoiced/lowest-energy frame nearest
                40/55/70 % of the voiced span (a word-boundary proxy; not aligned to the number)
                + 200 ms. Internal pauses in amount clips are also tagged midnum_pause.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import statistics
import time
import wave

import numpy as np
import onnxruntime as ort
from transformers import WhisperFeatureExtractor

SR = 16000
CALLS = "tests/fixtures/server/calls"
CUT = {"yes_no": 700, "short": 800, "amount": 1000, "open": 1100}
GRACE = {"yes_no": 1000, "short": 1200, "amount": 1600, "open": 1800}
AMOUNT_RE = re.compile(r"लाख|हज़ार|हजार|सौ|करोड़|lakh|hazaar|hazar|thousand|crore|\d")


def kind_of(key: str) -> str:
    if key.startswith(("right_party", "disclosure.go_ahead", "read_back", "second_check")):
        return "yes_no"
    if key.startswith(("premium", "cover.ask")):
        return "amount"
    return "open"


def read_wav(path: str) -> tuple[np.ndarray, int]:
    with wave.open(path) as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    assert sw == 2, path
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def resample(x: np.ndarray, sr: int) -> np.ndarray:
    if sr == SR:
        return x
    n_out = int(round(len(x) * SR / sr))
    spec = np.fft.rfft(x)
    out = np.zeros(n_out // 2 + 1, dtype=complex)
    m = min(len(spec), len(out))
    out[:m] = spec[:m]
    return (np.fft.irfft(out, n_out) * (n_out / len(x))).astype(np.float32)


def frames_db(x: np.ndarray) -> np.ndarray:
    f = SR // 100
    n = len(x) // f
    rms = np.sqrt(np.mean(x[: n * f].reshape(n, f) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms)


def voicing(x: np.ndarray):
    db = frames_db(x)
    voiced = db > max(-40.0, db.max() - 35.0)
    idx = np.flatnonzero(voiced)
    first, last = int(idx[0]), int(idx[-1])
    pauses, i = [], first
    while i <= last:
        if not voiced[i]:
            j = i
            while not voiced[j]:
                j += 1
            if j - i >= 15:
                pauses.append((i, j))
            i = j
        else:
            i += 1
    return db, voiced, first, last + 1, pauses  # frame indices; end exclusive


def sil(ms: int) -> np.ndarray:
    return np.zeros(SR * ms // 1000, dtype=np.float32)


class Model:
    def __init__(self, path: str):
        so = ort.SessionOptions()
        so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        so.inter_op_num_threads = 1
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.sess = ort.InferenceSession(path, sess_options=so)
        self.fe = WhisperFeatureExtractor(chunk_length=8)
        self.times: list[float] = []

    def p(self, audio: np.ndarray) -> float:
        t0 = time.perf_counter()
        n = 8 * SR
        audio = audio[-n:] if len(audio) > n else np.pad(audio, (n - len(audio), 0))
        feats = self.fe(audio, sampling_rate=SR, return_tensors="np", padding="max_length",
                        max_length=n, truncation=True, do_normalize=True)
        x = np.expand_dims(feats.input_features.squeeze(0).astype(np.float32), 0)
        out = self.sess.run(None, {"input_features": x})[0][0].item()
        self.times.append((time.perf_counter() - t0) * 1000)
        return float(out)


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    z, ph = 1.96, k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return (max(0, c - h), min(1, c + h))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--extra-dir")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    m = Model(a.model)
    rows: list[dict] = []

    def add(cls, src, audio, **kw):
        rows.append({"class": cls, "src": src, "p": m.p(audio), **kw})

    clips = []
    for cj in sorted(glob.glob(f"{CALLS}/*/call.json")):
        call = os.path.basename(os.path.dirname(cj))
        for t in json.load(open(cj, encoding="utf-8"))["turns"]:
            x, sr = read_wav(os.path.join(os.path.dirname(cj), t["file"]))
            clips.append(dict(call=call, file=t["file"], text=t["text"], kind=kind_of(t["answers"]),
                              sr=sr, x=resample(x, sr)))
    if a.extra_dir:
        for p in sorted(glob.glob(os.path.join(a.extra_dir, "*.wav"))):
            x, sr = read_wav(p)
            clips.append(dict(call="extra", file=os.path.basename(p), text="", kind="open",
                              sr=sr, x=resample(x, sr)))

    f = SR // 100
    for c in clips:
        x = c["x"]
        _, _, first, end, pauses = voicing(x)
        c["end"] = end
        src = f'{c["call"]}/{c["file"]}'
        speech = x[: end * f]
        amount = bool(AMOUNT_RE.search(c["text"]))
        add("complete", src, np.concatenate([speech, sil(200)]), at_ms=200, kind=c["kind"], sr=c["sr"])
        add("complete", src, np.concatenate([speech, sil(CUT[c["kind"]])]), at_ms=CUT[c["kind"]],
            kind=c["kind"], sr=c["sr"])
        for (s, e) in pauses:
            add("midnum_pause" if amount else "pause", src,
                np.concatenate([x[: s * f], sil(200)]), at_ms=200, pause_ms=(e - s) * 10,
                kind=c["kind"], sr=c["sr"], extra=c["call"] == "extra")
        if amount:
            db = frames_db(x)
            for frac in (0.40, 0.55, 0.70):
                tgt = int(first + frac * (end - first))
                w0, w1 = max(first + 1, tgt - 15), min(end - 1, tgt + 15)
                cut = w0 + int(np.argmin(db[w0:w1]))
                add("midnum", src, np.concatenate([x[: cut * f], sil(200)]), at_ms=200,
                    frac=frac, kind=c["kind"], sr=c["sr"], text=c["text"])

    by_call: dict[str, list] = {}
    for c in clips:
        if c["call"] != "extra":
            by_call.setdefault(c["call"], []).append(c)
    for call, cs in by_call.items():
        for A, B in zip(cs, cs[1:]):
            head = A["x"][: A["end"] * f]
            for gap in (600, 900, 1200):
                # the model sees only A + silence up to the evaluation point; B is after it
                for at in (200, CUT[A["kind"]]):
                    if at < gap:
                        add("splice", f'{call}/{A["file"]}+{B["file"]}',
                            np.concatenate([head, sil(at)]), at_ms=at, gap_ms=gap, kind=A["kind"])

    with open(os.path.join(a.out, "points.jsonl"), "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # summary
    L = ["# Smart Turn v3.2 probe (TTS audio only: Timbre voices, not human speech)", "",
         f"onnxruntime {ort.__version__}; points {len(rows)}; all clips 8 kHz resampled to 16 kHz "
         "(no 16 kHz originals).", ""]
    def sel(cls, at=None):
        return [r["p"] for r in rows if r["class"] == cls and (at is None or r["at_ms"] == at)]
    groups = [("complete @200", sel("complete", 200)),
              ("complete @cut", [r["p"] for r in rows if r["class"] == "complete" and r["at_ms"] != 200]),
              ("pause (natural) @200", sel("pause")),
              ("midnum_pause (natural, amount clips) @200", sel("midnum_pause")),
              ("splice @200", sel("splice", 200)),
              ("splice @cut", [r["p"] for r in rows if r["class"] == "splice" and r["at_ms"] != 200]),
              ("midnum (made cut) @200", sel("midnum"))]
    L += ["| class | n | p10 | median | p90 |", "|---|---|---|---|---|"]
    for name, ps in groups:
        if ps:
            q = np.percentile(ps, [10, 50, 90])
            L.append(f"| {name} | {len(ps)} | {q[0]:.3f} | {q[1]:.3f} | {q[2]:.3f} |")
    L += ["", "Rate of P > threshold (true-complete for complete rows, false-complete otherwise), "
          "k/n [Wilson 95%]", "", "| class | " + " | ".join(f"t={t}" for t in (0.3, 0.5, 0.7, 0.9)) + " |",
          "|---|---|---|---|---|"]
    for name, ps in groups:
        if not ps:
            continue
        cells = []
        for t in (0.3, 0.5, 0.7, 0.9):
            k = sum(p > t for p in ps)
            lo, hi = wilson(k, len(ps))
            cells.append(f"{k}/{len(ps)} [{lo:.2f}-{hi:.2f}]")
        L.append(f"| {name} | " + " | ".join(cells) + " |")
    # modelled saving at the cut
    comp_cut = [r for r in rows if r["class"] == "complete" and r["at_ms"] != 200]
    inc_cut = [r for r in rows if r["class"] == "splice" and r["at_ms"] != 200]
    L += ["", "Modelled saving: at the cut, skip the remaining grace (grace - cut by kind) when P > t. "
          "Saving averaged over all complete turns; false-complete = splice points at the cut "
          "(customer resumes after 900/1200 ms) with P > t.", "",
          "| t | mean saving ms/turn | turns skipped | false-complete at cut |", "|---|---|---|---|"]
    for t in (0.3, 0.5, 0.7, 0.9):
        sav = [(GRACE[r["kind"]] - CUT[r["kind"]]) if r["p"] > t else 0 for r in comp_cut]
        k = sum(r["p"] > t for r in inc_cut)
        lo, hi = wilson(k, len(inc_cut))
        L.append(f"| {t} | {statistics.mean(sav):.0f} | {sum(s > 0 for s in sav)}/{len(sav)} | "
                 f"{k}/{len(inc_cut)} [{lo:.2f}-{hi:.2f}] |")
    ts = sorted(m.times[3:])
    L += ["", f"Inference ms per call (features + ONNX, after 3 warm-up): median "
          f"{statistics.median(ts):.1f}, p90 {ts[int(0.9 * len(ts))]:.1f}, n {len(ts)}."]
    open(os.path.join(a.out, "SUMMARY.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
