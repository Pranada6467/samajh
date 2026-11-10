"""P2 round 4, item 7: do parallel calls starve each other's turn classifier?

N calls run in parallel in one process on ONE shared `LlmFallbackInterpreter` (as the server does).
Each call has T classifier turns, one after another: `begin` (as the turn route's prefetch), then
`interpret`. A turn the classifier did not answer within `timeout_s` comes back `degraded`.

Arms:
  old  - every request goes through a 4-worker `ThreadPoolExecutor` (the code before round 4)
  new  - the module as it is (`_start`: one daemon thread per request)

Modes:
  offline - a fake client that sleeps `--sleep` s per request (`--slow-calls` of the calls sleep
            `--slow-sleep` s instead). No network.
  live    - the real classifier through `LlmClient` (model `FALLBACK_MODEL`), built as the server
            builds it: HTTP timeout `--http-timeout` s, one attempt per send. Texts carry a fresh
            run nonce so they miss the response cache. Spend is capped at `--usd-cap`.

    uv run python tests/dialogue/probes/p2_round4_pool.py --mode offline --arm old
    uv run python tests/dialogue/probes/p2_round4_pool.py --mode offline --arm new --slow-calls 3
    uv run python tests/dialogue/probes/p2_round4_pool.py --mode live --arm new --calls 10 --turns 8
"""

from __future__ import annotations

import argparse
import logging
import random
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from types import SimpleNamespace

from samajh.dialogue import Expecting
from samajh.dialogue import llm_fallback as fb
from samajh.dialogue.interpret import RuleInterpreter
from samajh.types import Language

HI = Language.hi
QUESTION = "लोन लेते समय आपको और क्या-क्या दिया गया था, जो आपको याद हो?"
# Replies the word lists leave unsettled at the open question: only the classifier can read them.
OPENERS = ("उस दिन बैंक में बहुत भीड़ थी", "आज बहुत गर्मी है", "मेरा बेटा कॉलेज गया है",
           "बारिश की वजह से देर हो गई", "हमारे गाँव में मेला लगा है", "सड़क पर बहुत ट्रैफिक था",
           "मेरी तबीयत थोड़ी ठीक नहीं थी", "पड़ोस में शादी चल रही है")  # fmt: skip
PLACES = ("जयपुर", "इंदौर", "पटना", "लखनऊ", "भोपाल", "नागपुर", "कानपुर", "आगरा", "मेरठ", "रांची")
WHEN = ("सुबह", "दोपहर", "शाम", "रात", "कल", "परसों", "सोमवार", "मंगलवार", "बुधवार", "शनिवार")


@dataclass
class Tally:
    lock: threading.Lock = field(default_factory=threading.Lock)
    turns: int = 0
    degraded: int = 0
    degraded_fast_calls: int = 0  # degraded turns of calls whose requests are not slow
    request_s: list[float] = field(default_factory=list)  # requests that went to the network
    turn_wait_s: list[float] = field(default_factory=list)  # from `begin` to `interpret` returning
    cache_hits: int = 0
    failures: int = 0
    usd: float = 0.0
    in_flight: int = 0


class FakeLlm:
    def __init__(self, sleeps: dict[str, float]) -> None:
        self.sleeps = sleeps

    def complete(self, schema, messages, **_):
        time.sleep(self.sleeps[messages[-1].content.rsplit("Reply: ", 1)[-1]])
        return SimpleNamespace(value=schema(label="answer"), usd=0.0, cache_hit=False)


class Timed:
    """Wraps a client: records how long each request took, whether it was cached and what it cost."""

    def __init__(self, inner, tally: Tally) -> None:
        self.inner, self.tally = inner, tally

    def complete(self, schema, messages, **options):
        began = time.monotonic()
        with self.tally.lock:
            self.tally.in_flight += 1
        try:
            result = self.inner.complete(schema, messages, **options)
        except Exception:
            with self.tally.lock:
                self.tally.failures += 1
            raise
        finally:
            with self.tally.lock:
                self.tally.in_flight -= 1
        seconds = time.monotonic() - began
        with self.tally.lock:
            if result.cache_hit:
                self.tally.cache_hits += 1
            else:
                self.tally.request_s.append(seconds)
            self.tally.usd += result.usd
        return result


def texts(calls: int, turns: int, nonce: str) -> list[list[str]]:
    rules = RuleInterpreter()
    rng = random.Random(nonce)
    combos = [f"{o}, {w} {p} गए थे" for o in OPENERS for p in PLACES for w in WHEN]
    rng.shuffle(combos)
    unsettled = [
        f"{t} {nonce}" if nonce else t
        for t in combos
        if not rules.interpret(
            f"{t} {nonce}".strip(), language=HI, expecting=Expecting.open, question=QUESTION
        ).settled
    ]
    if len(unsettled) < calls * turns:
        raise SystemExit(f"only {len(unsettled)} unsettled texts for {calls * turns} turns")
    return [unsettled[c * turns : (c + 1) * turns] for c in range(calls)]


def run_call(fallback, replies: list[str], slow: bool, tally: Tally, gap: float) -> None:
    for text in replies:
        began = time.monotonic()
        fallback.begin(text, language=HI, expecting=Expecting.open, question=QUESTION)
        heard = fallback.interpret(text, language=HI, expecting=Expecting.open, question=QUESTION)
        waited = time.monotonic() - began
        with tally.lock:
            tally.turns += 1
            tally.turn_wait_s.append(waited)
            if heard.degraded:
                tally.degraded += 1
                tally.degraded_fast_calls += not slow
        if gap:
            time.sleep(gap)


def p95(xs: list[float]) -> float:
    return sorted(xs)[min(len(xs) - 1, round(0.95 * (len(xs) - 1)))] if xs else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("offline", "live"), default="offline")
    ap.add_argument("--arm", choices=("old", "new"), required=True)
    ap.add_argument("--calls", type=int, default=10)
    ap.add_argument("--turns", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=fb.TIMEOUT_S, help="the classifier's timeout_s")
    ap.add_argument("--gap", type=float, default=0.0, help="seconds between a call's turns")
    ap.add_argument("--sleep", type=float, default=1.0, help="offline: seconds per request")
    ap.add_argument("--slow-calls", type=int, default=0, help="offline: calls whose requests are slow")
    ap.add_argument("--slow-sleep", type=float, default=10.0, help="offline: seconds per slow request")
    ap.add_argument("--http-timeout", type=float, default=3.0, help="live: the server's [fallback] timeout_s")
    ap.add_argument("--usd-cap", type=float, default=0.025, help="live: cap for this run")
    args = ap.parse_args()
    logging.getLogger("samajh.dialogue.llm_fallback").setLevel(logging.ERROR)  # one warning per timeout

    if args.arm == "old":
        pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="old-pool")
        fb._start = lambda ask, messages: pool.submit(ask, messages)

    tally = Tally()
    nonce = f"#{random.randrange(16**6):06x}" if args.mode == "live" else ""
    per_call = texts(args.calls, args.turns, nonce)
    slow = [c < args.slow_calls for c in range(args.calls)]
    if args.mode == "offline":
        sleeps = {
            t: (args.slow_sleep if slow[c] else args.sleep) for c, ts in enumerate(per_call) for t in ts
        }
        client = Timed(FakeLlm(sleeps), tally)
    else:
        from samajh.clients._runtime import RetryPolicy
        from samajh.clients.llm import LlmClient

        live = LlmClient.from_env(
            model=fb.FALLBACK_MODEL, usd_cap=args.usd_cap, timeout=args.http_timeout,
            retry=RetryPolicy(max_attempts=1),
        )  # fmt: skip
        client = Timed(live, tally)
    fallback = fb.LlmFallbackInterpreter(client, timeout_s=args.timeout)

    began = time.monotonic()
    threads = [
        threading.Thread(target=run_call, args=(fallback, per_call[c], slow[c], tally, args.gap))
        for c in range(args.calls)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.monotonic() - began
    # Abandoned requests still cost money: wait (bounded) for them before counting the spend.
    if args.mode == "live" or not args.slow_calls:
        deadline = time.monotonic() + 60
        while tally.in_flight and time.monotonic() < deadline:
            time.sleep(0.1)

    print(f"mode={args.mode} arm={args.arm} calls={args.calls} turns/call={args.turns} timeout_s={args.timeout}"
          f" gap={args.gap}" + (f" sleep={args.sleep} slow_calls={args.slow_calls} slow_sleep={args.slow_sleep}"
                                 if args.mode == "offline" else f" http_timeout={args.http_timeout}"))  # fmt: skip
    print(f"turns={tally.turns} degraded={tally.degraded} degraded_in_fast_calls={tally.degraded_fast_calls}"
          f" wall={wall:.1f}s")  # fmt: skip
    rs, ws = tally.request_s, tally.turn_wait_s
    print(f"requests finished={len(rs)} still_running={tally.in_flight} cache_hits={tally.cache_hits} failures={tally.failures}"
          f" request_s median={statistics.median(rs) if rs else float('nan'):.2f} p95={p95(rs):.2f}"
          f" max={max(rs, default=float('nan')):.2f}")  # fmt: skip
    print(f"turn_wait_s median={statistics.median(ws):.2f} p95={p95(ws):.2f} usd={tally.usd:.6f}")
    # Requests still running are abandoned; in the new arm they are daemon threads and do not hold exit.
    # In the old arm the pool's threads are joined at exit (slow requests delay it).


if __name__ == "__main__":
    main()
