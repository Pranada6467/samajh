"""One request per cache key at a time: concurrent identical calls send one request and all read its answer."""

import itertools
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import respx
from test_llm_client import FAKE_KEY, MESSAGES, MODEL, URL, Answer, completion

from samajh.clients.llm import LlmClient


def test_concurrent_identical_requests_send_one_request_and_share_its_answer(tmp_path: Path):
    """The fake transport would answer each request differently; every caller must get the first answer."""
    counter = itertools.count()
    lock = threading.Lock()

    def answer(request: httpx.Request) -> httpx.Response:
        with lock:
            n = next(counter)
        time.sleep(0.05)  # long enough for every caller to be waiting
        return completion(f'{{"kind": "{"insurance" if n == 0 else "other"}", "quote": "{n}"}}')

    # Two client instances on one state directory stand in for two processes.
    clients = [LlmClient(api_key=FAKE_KEY, model=MODEL, usd_cap=1.0, state=tmp_path) for _ in range(2)]
    with respx.mock(assert_all_called=False) as router:
        route = router.post(URL).mock(side_effect=answer)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda i: clients[i % 2].complete(Answer, MESSAGES), range(8)))
    assert route.call_count == 1
    assert {(r.value.kind, r.value.quote) for r in results} == {("insurance", "0")}
    assert sum(not r.cache_hit for r in results) == 1


def test_different_requests_are_not_serialised_against_each_other(tmp_path: Path):
    client = LlmClient(api_key=FAKE_KEY, model=MODEL, usd_cap=1.0, state=tmp_path)
    running = most = 0
    lock = threading.Lock()

    def answer(request: httpx.Request) -> httpx.Response:
        nonlocal running, most
        with lock:
            running += 1
            most = max(most, running)
        time.sleep(0.05)
        with lock:
            running -= 1
        return completion('{"kind": "insurance", "quote": null}')

    other = [MESSAGES[0], MESSAGES[1].model_copy(update={"content": "दूसरा जवाब"})]
    with respx.mock(assert_all_called=False) as router:
        router.post(URL).mock(side_effect=answer)
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda m: client.complete(Answer, m), [MESSAGES, other]))
    assert most == 2
