"""P3a re-verification (round 2): one LLM request per cache key across real OS processes. Offline.

    uv run python references/reviews/iter2/probes/p3a_r2_single_flight.py <scratch-dir-outside-repo>

A local HTTP server stands in for OpenRouter and answers every request differently, after a delay.
Scenario A: 4 processes x 6 threads send the same request at once on one state directory.
Scenario B: the same, with 3 different requests interleaved (each key must get exactly one request,
and different keys must overlap in time). Scenario C: the first answer is invalid JSON every time
(LlmOutputInvalid): how many requests do the waiters then send? Uses samajh.clients.llm.LlmClient
with a fake key and base_url pointing at the local server; nothing leaves the machine.
"""

import json
import multiprocessing as mp
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n: int
    text: str


def serve(mode: str):
    state = {"count": 0, "by_body": {}, "running": 0, "most": 0}
    lock = threading.Lock()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            user = json.loads(body)["messages"][-1]["content"]
            with lock:
                n = state["count"]
                state["count"] += 1
                state["by_body"][user] = state["by_body"].get(user, 0) + 1
                state["running"] += 1
                state["most"] = max(state["most"], state["running"])
            time.sleep(0.3)
            with lock:
                state["running"] -= 1
            content = "not json" if mode == "invalid" else json.dumps({"n": n, "text": user})
            out = json.dumps({
                "id": f"gen-{n}", "model": "test/model",
                "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost": 0.0},
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

    server = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, state


def worker(args):
    port, state_dir, texts, start_at, q = args
    from samajh.clients._runtime import RetryPolicy
    from samajh.clients.llm import LlmClient, Message

    client = LlmClient(api_key="sk-test-not-real", model="test/model", usd_cap=1.0, state=Path(state_dir),
                       base_url=f"http://127.0.0.1:{port}", retry=RetryPolicy(max_attempts=1, base_delay=0, max_delay=0))
    while time.time() < start_at:
        time.sleep(0.001)

    def one(text):
        try:
            r = client.complete(Answer, [Message(role="system", content="x"), Message(role="user", content=text)],
                                max_output_retries=0)
            return ("ok", r.value.n, r.value.text, r.cache_hit)
        except Exception as exc:  # noqa: BLE001
            return ("error", type(exc).__name__, text, None)

    with ThreadPoolExecutor(max_workers=len(texts)) as pool:
        q.put(list(pool.map(one, texts)))


def scenario(name, scratch: Path, mode: str, texts_per_proc: list[list[str]]):
    server, state = serve(mode)
    state_dir = scratch / f"sf_{name}"
    state_dir.mkdir(parents=True, exist_ok=True)
    q = mp.Queue()
    start_at = time.time() + 1.5
    procs = [mp.Process(target=worker, args=((server.server_port, str(state_dir), t, start_at, q),)) for t in texts_per_proc]
    for p in procs:
        p.start()
    results = [r for _ in procs for r in q.get(timeout=120)]
    for p in procs:
        p.join()
    server.shutdown()
    oks = [r for r in results if r[0] == "ok"]
    per_text = {}
    for r in oks:
        per_text.setdefault(r[2], set()).add(r[1])
    print(f"{name}: callers {len(results)}, ok {len(oks)}, errors {len(results) - len(oks)} "
          f"({sorted({r[1] for r in results if r[0] == 'error'})}); HTTP requests {state['count']} "
          f"by text {state['by_body']}; most at once {state['most']}; distinct answers per text "
          f"{ {t: len(v) for t, v in per_text.items()} }; non-cache answers {sum(not r[3] for r in oks)}")


def main() -> int:
    scratch = Path(sys.argv[1]).resolve()
    if Path(__file__).resolve().parents[4] in scratch.parents:
        raise SystemExit("scratch must be outside the repo")
    same = [["बीमा है"] * 6 for _ in range(4)]
    scenario("A_same_key", scratch, "ok", same)
    mixed = [[("एक", "दो", "तीन")[(i + k) % 3] for i in range(6)] for k in range(4)]
    scenario("B_three_keys", scratch, "ok", mixed)
    scenario("C_invalid_output", scratch, "invalid", [["एफ़डी है"] * 3 for _ in range(2)])
    return 0


if __name__ == "__main__":
    mp.set_start_method("spawn")
    sys.exit(main())
