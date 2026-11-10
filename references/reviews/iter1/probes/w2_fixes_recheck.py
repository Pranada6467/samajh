"""Verifier probe: try to break W2's fix round (W2-clients-report.md section 2, items 1 to 13) and the
LLM client's per-model sampling change, with inputs the builders' tests do not use. Offline: respx
mocks every request; fake keys; temporary state directories.

    uv run python references/reviews/iter1/probes/w2_fixes_recheck.py
"""

from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path

import httpx
import respx
from pydantic import BaseModel

from samajh.clients._runtime import Ledger
from samajh.clients.errors import ClientError
from samajh.clients.gnani import GnaniClient, PrismaV30, Timbre
from samajh.clients.gnani.wav import wav_seconds
from samajh.clients.llm import LlmClient, Message, _Sampling

KEY = "FAKEKEY-" + "a1B2" * 12
OPT = PrismaV30(language="hi-IN", format="transcribe")
HEADER = b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00"


def wav(seconds: float, declared: int | None = None) -> bytes:
    body = b"\x01\x00" * int(8000 * seconds)
    size = len(body) if declared is None else declared
    return HEADER + b"data" + size.to_bytes(4, "little") + body


def leaked(state: Path, *texts: str) -> list[str]:
    where = [p.name for p in state.rglob("*") if p.is_file() and KEY.encode() in p.read_bytes()]
    where += [f"text#{k}" for k, t in enumerate(texts) if KEY in t or KEY[:20] in t or KEY[-20:] in t]
    return where


def outcome(call) -> str:
    try:
        result = call()
        return f"returned {type(result).__name__}"
    except ClientError as error:
        return f"{type(error).__name__}: {str(error)[:110]}"
    except Exception as error:  # noqa: BLE001 - an untyped escape is itself a finding
        return f"UNTYPED {type(error).__name__}: {str(error)[:110]}"


class Out(BaseModel):
    ok: bool


def chat(content: str = '{"ok": true}', **usage) -> dict:
    return {"id": "g", "model": "m", "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, **usage}}  # fmt: skip


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp, respx.mock(assert_all_called=False) as mock:
        tmp = Path(tmp)
        base = "https://gnani.invalid"

        def gnani(name: str, **kwargs) -> tuple[GnaniClient, Path]:
            state = tmp / name
            return GnaniClient(api_key=KEY, credit_cap=50.0, state=state, base_url=base,
                               sleep=lambda s: None, **kwargs), state  # fmt: skip

        # fix 3: the key echoed back in an error, placed so that it straddles the 300-character cut,
        # and in every error body shape
        shapes = {
            "gateway detail": {"detail": {"error_code": f"BAD_{KEY}", "message": "x" * 290 + KEY}},
            "stt error": {"error": {"type": KEY, "message": "y" * 280 + KEY + "tail"}},
            "batch error": {"error": f"oops {KEY}", "code": KEY, "message": KEY},
            "fastapi list": {"detail": [{"loc": ["body", KEY], "msg": KEY, "type": KEY}]},
            "plain string detail": {"detail": "z" * 299 + KEY},
        }
        for name, body in shapes.items():
            mock.post(f"{base}/stt/v3").mock(return_value=httpx.Response(400, json=body))
            client, state = gnani(f"redact-{name.replace(' ', '-')}")
            text = outcome(lambda: client.stt(wav(1.0), OPT))  # noqa: B023
            print(f"fix 3  key echoed in a {name:20s}: leaks {leaked(state, text) or 'none'}")
        mock.post(f"{base}/stt/v3").mock(return_value=httpx.Response(400, content=b"<html>" + KEY.encode() + b"</html>"))
        client, state = gnani("redact-html")
        print(f"fix 3  key echoed in a non-JSON body       : leaks {leaked(state, outcome(lambda: client.stt(wav(1.0), OPT))) or 'none'}")
        mock.post(f"{base}/stt/v3").mock(return_value=httpx.Response(200, json={"success": True, "oops": KEY}))
        client, state = gnani("redact-200")
        print(f"fix 3  key echoed in a 200 that does not parse: leaks {leaked(state, outcome(lambda: client.stt(wav(1.0), OPT))) or 'none'}")

        # fix 4: malformed keys
        for bad in (KEY + "\n", " " + KEY, KEY + " ", "", KEY[:10] + "\t" + KEY[10:], "ключ"):
            text = outcome(lambda: GnaniClient(api_key=bad, credit_cap=1.0, state=tmp / "k"))  # noqa: B023
            print(f"fix 4  key {bad[:3]!r}...{bad[-3:]!r}: {text[:60]} | key in message: {bad.strip() in text if bad.strip() else False}")

        # fix 9: caps that would disable the guard
        for cap in (float("nan"), float("inf"), -1.0, 0.0):
            print(f"fix 9  credit_cap={cap}: {outcome(lambda: GnaniClient(api_key=KEY, credit_cap=cap, state=tmp / 'c'))[:70]}")  # noqa: B023

        # fix 5: TTS bodies that are not the audio asked for
        timbre = Timbre(model="timbre-v3.0", voice="Shivani", language="hi-IN")
        bodies = {
            "JSON error with audio/wav type": (b'{"error":"quota"}', "audio/wav"),
            "WAV at 16 kHz when 8 kHz was asked": (wav(1.0).replace(b"\x40\x1f\x00\x00", b"\x80\x3e\x00\x00", 1), "audio/wav"),
            "WAV header and no samples": (wav(0.0), "audio/wav"),
            "good WAV, text/html type": (wav(1.0), "text/html"),
            "empty body": (b"", "audio/wav"),
        }
        for name, (body, ctype) in bodies.items():
            mock.post(f"{base}/api/v1/tts/inference").mock(return_value=httpx.Response(200, content=body, headers={"content-type": ctype}))
            client, state = gnani(f"tts-{abs(hash(name))}")
            text = outcome(lambda: client.tts("नमस्ते", timbre))  # noqa: B023
            cached = len(list((state / "cache").rglob("*.bin"))) if (state / "cache").exists() else 0
            booked = sum(r.est_credits for r in Ledger(state / "ledger.jsonl").entries())
            print(f"fix 5  {name:36s}: {text[:58]:58s} cached {cached}, credits booked {booked}")

        # fix 12: clips whose header understates their length
        for name, clip in (("31 s, data size 0", wav(31.0, 0)), ("31 s, data size 0xFFFFFFFF", wav(31.0, 0xFFFFFFFF)),
                           ("31 s, data size says 1 s", wav(31.0, 16000)), ("30.0 s", wav(30.0))):  # fmt: skip
            mock.post(f"{base}/stt/v3").mock(return_value=httpx.Response(200, json={"success": True, "transcript": "x"}))
            client, state = gnani(f"len-{abs(hash(name))}")
            print(f"fix 12 {name:28s}: wav_seconds {wav_seconds(clip)!s:6s} -> {outcome(lambda: client.stt(clip, OPT))[:70]}")  # noqa: B023

        # fix 8: redirects, and the key on the pre-signed storage request
        route = mock.post(f"{base}/stt/v3").mock(return_value=httpx.Response(302, headers={"location": "https://evil.invalid/steal"}))
        evil = mock.route(host="evil.invalid").mock(return_value=httpx.Response(200, json={"success": True, "transcript": "x"}))
        injected = httpx.Client(follow_redirects=True, headers={"X-API-Key-ID": KEY})
        client, state = gnani("redirect", http=injected)
        print(f"fix 8  API answers 302 to another host, injected client follows redirects: {outcome(lambda: client.stt(wav(1.0), OPT))[:50]}; "
              f"other host called {evil.call_count} times")  # fmt: skip
        request = client._presigned_get  # the storage fetch, with a client that carries the key by default
        storage = mock.get("https://storage.invalid/t.json").mock(return_value=httpx.Response(200, json={}))
        request("https://storage.invalid/t.json")
        sent = storage.calls.last.request.headers
        print(f"fix 8  pre-signed GET with a key-carrying injected client: key header sent {'x-api-key-id' in sent}")
        _ = route

        # LLM: fix 6 (cap 0, missing cost), fix 11 (0 vs 0.0), fixes 1 and 10 (gzip), and the sampling table
        url = "https://llm.invalid/api/v1"

        def llm(name: str, **kwargs) -> tuple[LlmClient, Path]:
            state = tmp / name
            return LlmClient(api_key=KEY, model=kwargs.pop("model", "some/model"), state=state, base_url=url,
                             sleep=lambda s: None, **kwargs), state  # fmt: skip

        posts = mock.post(f"{url}/chat/completions").mock(return_value=httpx.Response(200, json=chat(cost=0.01)))
        client, _ = llm("cap0", usd_cap=0.0)
        print(f"fix 6  usd_cap=0: {outcome(lambda: client.complete(Out, [Message(role='user', content='a')]))[:60]}; requests {posts.call_count}")
        mock.post(f"{url}/chat/completions").mock(side_effect=[httpx.Response(200, json=chat(cost=0.03)), httpx.Response(200, json=chat()),
                                                               httpx.Response(200, json=chat(cost=0.01))])  # fmt: skip
        client, state = llm("nocost", usd_cap=0.05)
        results = [outcome(lambda k=k: client.complete(Out, [Message(role="user", content=f"q{k}")]))[:28] for k in range(3)]
        rows = [(r.usd, r.error_code) for r in Ledger(state / "ledger.jsonl").entries()]
        print(f"fix 6  cap 0.05; costs 0.03, missing, 0.01: {results}; ledger {rows}; spent {client.spent_usd}")
        mock.post(f"{url}/chat/completions").mock(return_value=httpx.Response(200, json=chat(cost=0.001)))
        client, state = llm("temp", usd_cap=1.0)
        a = client.complete(Out, [Message(role="user", content="t")], temperature=0)
        b = client.complete(Out, [Message(role="user", content="t")], temperature=0.0)
        c = client.complete(Out, [Message(role="user", content="t")], temperature=None)
        print(f"fix 11 temperature 0, 0.0, None: cache hits {a.cache_hit}, {b.cache_hit}, {c.cache_hit} (None is a different request)")
        broken = httpx.DecodingError("Error -3 while decompressing data")  # what httpx raises for a body that is not gzip
        inbody = httpx.Response(200, content=gzip.compress(json.dumps({"error": {"code": 502, "message": f"upstream {KEY}"}}).encode()),
                                headers={"content-encoding": "gzip", "content-type": "application/json"})  # fmt: skip
        for name, response in (("a body that is not gzip", broken), ("an in-body 502 that echoes the key", inbody)):
            if isinstance(response, Exception):
                mock.post(f"{url}/chat/completions").mock(side_effect=response)
            else:
                mock.post(f"{url}/chat/completions").mock(return_value=response)
            client, state = llm(f"gz-{name[:6].strip()}", usd_cap=1.0)
            text = outcome(lambda: client.complete(Out, [Message(role="user", content="z")]))  # noqa: B023
            rows = [r.status for r in Ledger(state / "ledger.jsonl").entries()]
            print(f"fix 1/10 gzip, {name}: {text[:64]}; ledger statuses {rows}; leaks {leaked(state, text) or 'none'}")

        # the per-model sampling change
        sampling = _Sampling.model_validate({"default": ["temperature"], "by_model_prefix": {"openai/gpt-6-luna": []}})
        for model in ("openai/gpt-6-luna", "openai/gpt-6-luna-mini", "openai/gpt-6-luna:nitro", "openai/gpt-6", "OpenAI/GPT-6-Luna",
                      "mistralai/mistral-small-3.2-24b-instruct"):  # fmt: skip
            print(f"sampling: {model:44s} temperature sent: {'temperature' in sampling.sent_to(model)}")
        seen = []
        mock.post(f"{url}/chat/completions").mock(side_effect=lambda request: (seen.append(json.loads(request.content)), httpx.Response(200, json=chat(cost=0.001)))[1])
        client, _ = llm("luna", usd_cap=1.0, model="openai/gpt-6-luna")
        client.complete(Out, [Message(role="user", content="s1")])
        client.complete(Out, [Message(role="user", content="s2")], model="mistralai/mistral-small-3.2-24b-instruct")
        print(f"sampling: request bodies carry temperature: {[(b['model'], b.get('temperature', 'absent')) for b in seen]}")


if __name__ == "__main__":
    main()
