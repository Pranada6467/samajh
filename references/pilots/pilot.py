"""Spoken-Indian-amounts pilot: Timbre TTS -> (clean 16k, 8k mu-law phone) -> Prisma v2.5 / v3.0.

Single-flight, backoff on 429, every response cached by content hash. Usage:
  python3 -I pilot.py probe      # one TTS call, print headers
  python3 -I pilot.py run        # full pilot
"""
import hashlib, json, os, subprocess, sys, time
from pathlib import Path
import requests

HERE = Path(__file__).resolve().parent
KEY = os.environ["GNANI_API_KEY"]  # never commit the key
CACHE = HERE / "cache"; CACHE.mkdir(exist_ok=True)
AUDIO = HERE / "audio"; AUDIO.mkdir(exist_ok=True)
LEDGER = HERE / "ledger.jsonl"
BASE = "https://api.vachana.ai"
TTS_VOICE, TTS_MODEL = "Shivani", "timbre-v3.0"

# id, tts language, text (amount spoken as words), gold amount in rupees
ITEMS = [
    ("hi01", "hi-IN", "मेरे लोन से बावन हज़ार रुपये कटे।", 52000),
    ("hi02", "hi-IN", "प्रीमियम डेढ़ लाख रुपये था।", 150000),
    ("hi03", "hi-IN", "सवा दो लाख का लोन मिला।", 225000),
    ("hi04", "hi-IN", "साढ़े तीन हज़ार की किस्त है।", 3500),
    ("hi05", "hi-IN", "ढाई करोड़ का कवर बताया था।", 25000000),
    ("hi06", "hi-IN", "पाँच लाख बीस हज़ार रुपये का लोन है।", 520000),
    ("hi07", "hi-IN", "अड़तीस हज़ार चार सौ पचास रुपये काटे गए।", 38450),
    ("hi08", "hi-IN", "पौने दो लाख रुपये जमा किए।", 175000),
    ("he01", "hi-en", "लोन के साथ twenty five thousand का insurance दिया।", 25000),
    ("he02", "hi-en", "प्रीमियम one point five lakh rupees था।", 150000),
    ("he03", "hi-en", "मेरी EMI eleven thousand two hundred rupees है।", 11200),
    ("he04", "hi-en", "cover ten lakh rupees का बताया।", 1000000),
    ("ta01", "ta-IN", "ஐம்பத்திரண்டாயிரம் ரூபாய் கழித்தார்கள்.", 52000),
    ("ta02", "ta-IN", "ஒன்றரை லட்சம் ரூபாய் பிரீமியம்.", 150000),
    ("ta03", "ta-IN", "மூன்று லட்சத்து இருபதாயிரம் ரூபாய் கடன்.", 320000),
    ("ta04", "ta-IN", "இரண்டரை கோடி ரூபாய் காப்பீடு.", 25000000),
    ("kn01", "kn-IN", "ಐವತ್ತೆರಡು ಸಾವಿರ ರೂಪಾಯಿ ಕಡಿತ ಮಾಡಿದರು.", 52000),
    ("kn02", "kn-IN", "ಒಂದೂವರೆ ಲಕ್ಷ ರೂಪಾಯಿ ಪ್ರೀಮಿಯಂ.", 150000),
    ("kn03", "kn-IN", "ಮೂರು ಲಕ್ಷದ ಇಪ್ಪತ್ತು ಸಾವಿರ ರೂಪಾಯಿ ಸಾಲ.", 320000),
    ("kn04", "kn-IN", "ಎರಡೂವರೆ ಕೋಟಿ ರೂಪಾಯಿ ವಿಮೆ.", 25000000),
]

def stt_lang(tts_lang):  # Prisma takes one locale; Hinglish -> hi-IN
    return "hi-IN" if tts_lang == "hi-en" else tts_lang

def log(entry):
    with LEDGER.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def call(kind, fn):
    """Single-flight with exponential backoff on 429."""
    delay = 1.0
    for attempt in range(8):
        t0 = time.time()
        r = fn()
        dt = round(time.time() - t0, 2)
        hdrs = {k: v for k, v in r.headers.items() if any(s in k.lower() for s in ("credit", "usage", "balance", "quota", "ratelimit", "cost"))}
        log({"kind": kind, "status": r.status_code, "secs": dt, "attempt": attempt, "hdrs": hdrs})
        if r.status_code == 429:
            time.sleep(delay); delay = min(delay * 2, 30); continue
        return r
    raise RuntimeError(f"{kind}: still rate limited")

def tts(item_id, lang, text):
    out = AUDIO / f"{item_id}_16k.wav"
    if out.exists():
        return out
    body = {"text": text, "voice": TTS_VOICE, "model": TTS_MODEL, "language": lang,
            "audio_config": {"sample_rate": 16000, "container": "wav"}}
    r = call("tts", lambda: requests.post(f"{BASE}/api/v1/tts/inference", json=body,
                                          headers={"X-API-Key-ID": KEY}, timeout=60))
    if r.status_code != 200:
        raise RuntimeError(f"TTS {item_id}: {r.status_code} {r.text[:300]}")
    out.write_bytes(r.content)
    return out

def phone(src):
    """Simulate a phone line: 8 kHz, G.711 mu-law, back to 8 kHz PCM WAV."""
    out = src.with_name(src.name.replace("_16k", "_8k"))
    if not out.exists():
        mu = src.with_suffix(".mulaw.wav")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-ar", "8000", "-ac", "1", "-c:a", "pcm_mulaw", str(mu)], check=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(mu), "-ar", "8000", "-c:a", "pcm_s16le", str(out)], check=True)
        mu.unlink()
    return out

def stt(wav, fields):
    key = hashlib.sha256(wav.read_bytes() + json.dumps(fields, sort_keys=True).encode()).hexdigest()[:24]
    cached = CACHE / f"{key}.json"
    if cached.exists():
        return json.loads(cached.read_text())
    def go():
        with wav.open("rb") as f:
            return requests.post(f"{BASE}/stt/v3", headers={"X-API-Key-ID": KEY},
                                 files={"audio_file": (wav.name, f, "audio/wav")}, data=fields, timeout=60)
    r = call("stt", go)
    res = {"status": r.status_code, "body": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text[:300]}
    if r.status_code == 200:
        cached.write_text(json.dumps(res, ensure_ascii=False))
    return res

CONFIGS = {
    # name: fields builder
    "v2.5_transcribe": lambda lang: {"language_code": lang, "format": "transcribe"},
    "v3.0_transcribe": lambda lang: {"model": "prisma-v3.0", "language_code": lang, "format": "transcribe"},
    "v3.0_auto":       lambda lang: {"model": "prisma-v3.0", "language_code": "indic-auto"},
}

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    if mode == "probe":
        i = ITEMS[0]
        p = tts(i[0], i[1], i[2])
        print("tts ok", p.stat().st_size, "bytes")
        print(open(LEDGER).read())
        return
    results = []
    for item_id, lang, text, gold in ITEMS:
        clean = tts(item_id, lang, text)
        tel = phone(clean)
        for cond, wav in (("clean16k", clean), ("phone8k", tel)):
            for cname, build in CONFIGS.items():
                if cond == "clean16k" and cname != "v3.0_transcribe":
                    continue  # clean only as a reference point for one config
                res = stt(wav, build(stt_lang(lang)))
                results.append({"id": item_id, "lang": lang, "gold": gold, "cond": cond, "config": cname,
                                "status": res["status"],
                                "transcript": res["body"].get("transcript") if isinstance(res["body"], dict) else res["body"]})
                print(item_id, cond, cname, res["status"], (results[-1]["transcript"] or "")[:80], flush=True)
    (HERE / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
