"""The ACQ knowledge writer: one request per customer, built from its fact sheet and the topics alone.

Commands (from the repo root):
  uv run python eval/acq/acq_write.py smoke --ids ACQ-C001,... --out DIR --usd-cap 0.20
  uv run python eval/acq/acq_write.py run [--resume] --usd-cap USD [--workers N]
                 refuses unless data/acq/FROZEN_INPUTS.json matches the inputs on disk

Independence: the request carries the system prompt, the customer's fact sheet (customers.jsonl)
and the open-call topics (topics.json), nothing else. `build_messages` takes no record argument.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parents[1] / "p5"))

from acq_common import DATA, read_jsonl, write_jsonl  # noqa: E402
from pydantic import BaseModel, create_model  # noqa: E402
from write_customers import (  # noqa: E402
    _LANGUAGE,
    MAX_TOKENS,
    MODEL_A,
    TEMPERATURE,
    _Strict,
    _variant_model,
    fact_sheet_text,
    run_arm,
)

from samajh.clients.llm import LlmClient, Message  # noqa: E402

CUSTOMERS = DATA / "customers.jsonl"
TOPICS = DATA / "topics.json"
KNOWLEDGE = DATA / "knowledge.jsonl"
REQUESTS = DATA / "writer_requests.jsonl"
FROZEN_INPUTS = DATA / "FROZEN_INPUTS.json"
VARIANTS = ("own", "again", "defer")

_SYSTEM = """You are playing one person on a phone call. The message below says everything this person knows.

Answer each thing the caller says as this person would actually say it aloud on the phone, in their own manner (see "How you talk" and "On this call"). Stay inside the fact sheet and never add a fact it does not hold. Where the sheet says the person does not know something, or says nothing about it, answer as that person honestly would (often that they do not know).

Spoken language only: one or two short sentences, most replies under fifteen words, defer replies a few words. Fillers and half-sentences are fine. No stage directions, no explanations, no quotation marks.

{language}

Every number as spoken words, never digits.

{versions}

Return only the JSON object asked for."""


def system_prompt(language: str, topics: dict[str, Any]) -> str:
    v = topics["variants"]
    versions = "For each thing the caller says you write three versions:\n" + "\n".join(
        f"- {name}: {v[name]}" for name in VARIANTS)
    return _SYSTEM.format(language=_LANGUAGE[language], versions=versions)


def user_message(customer: dict[str, Any], topics: dict[str, Any]) -> str:
    parts = [fact_sheet_text(customer), "", "THE CALL",
             "Here is each thing the caller may say. For each one, write what you would say, in each version listed.", ""]
    for t in topics["open_call"]:
        parts.append(f"[{t['id']}] {t['caller']}\nVersions: {', '.join(t['variants'])}")
    parts += ["", "Return one JSON object with one key per id above; under each key, one string per version listed."]
    return "\n".join(parts)


def build_messages(customer: dict[str, Any], topics: dict[str, Any]) -> tuple[str, str]:
    """(system, user) for one customer: from its customers.jsonl row and topics.json only."""
    return system_prompt(customer["language"], topics), user_message(customer, topics)


def schema(topics: dict[str, Any]) -> type[BaseModel]:
    fields = {t["id"]: (_variant_model(tuple(t["variants"])), ...) for t in topics["open_call"]}
    return create_model("AcqKnowledgeReplies", __base__=_Strict, **fields)


def write_one(client: LlmClient, customer: dict[str, Any], topics: dict[str, Any]) -> dict[str, Any]:
    system, user = build_messages(customer, topics)
    arm = run_arm(client, customer["writer_model"], schema(topics), system, user,
                  customer["language"], customer["id"], "open")
    row = {"id": customer["id"], "writer_model": customer["writer_model"], "replies": arm["replies"],
           "checks": {"regenerated": arm["regenerated"], "failed": arm["failed"]},
           "attempts": len(arm["requests"]), "kept_attempt": arm["kept_attempt"], "usd": arm["usd"]}
    return {"row": row, "requests": arm["requests"]}


def load_topics() -> dict[str, Any]:
    return json.loads(TOPICS.read_text(encoding="utf-8"))


def frozen_problems() -> list[str]:
    from acq_build import input_digests  # the one definition of the frozen digests

    if not FROZEN_INPUTS.exists():
        return [f"{FROZEN_INPUTS} does not exist: run acq_build.py freeze-inputs first"]
    listed = json.loads(FROZEN_INPUTS.read_text(encoding="utf-8"))
    now = input_digests()
    return [f"{k}: frozen {listed.get(k)} on disk {v}" for k, v in now.items() if listed.get(k) != v or v is None]  # writer outputs are pinned too but may grow on --resume


def cmd_smoke(args: argparse.Namespace) -> None:
    ids = args.ids.split(",")
    customers = {c["id"]: c for c in read_jsonl(CUSTOMERS)}
    topics = load_topics()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    client = LlmClient.from_env(model=MODEL_A, usd_cap=args.usd_cap)
    rows, reqs, total = [], [], 0.0
    for cid in ids:
        result = write_one(client, customers[cid], topics)
        rows.append(result["row"])
        reqs += result["requests"]
        total += result["row"]["usd"]
        print(f"{cid} {customers[cid]['kind']} {customers[cid]['language']} {customers[cid]['writer_model']}: "
              f"attempts {result['row']['attempts']}, failed {len(result['row']['checks']['failed'])}, "
              f"usd {result['row']['usd']:.4f}", flush=True)
    write_jsonl(out / "knowledge.jsonl", rows)
    write_jsonl(out / "writer_requests.jsonl", reqs)
    print(f"total usd {total:.4f}")


def cmd_run(args: argparse.Namespace) -> None:
    problems = frozen_problems()
    if problems:
        sys.exit("refusing to run:\n  " + "\n  ".join(problems))
    if KNOWLEDGE.exists() and not args.resume:
        sys.exit(f"refusing to run: {KNOWLEDGE} exists (pass --resume to continue it)")
    customers, topics = read_jsonl(CUSTOMERS), load_topics()
    done = {r["id"]: r for r in read_jsonl(KNOWLEDGE)} if KNOWLEDGE.exists() else {}
    kept = [r for r in read_jsonl(REQUESTS) if r["id"] in done] if REQUESTS.exists() else []
    write_jsonl(KNOWLEDGE, list(done.values()))
    write_jsonl(REQUESTS, kept)
    client = LlmClient.from_env(model=MODEL_A, usd_cap=args.usd_cap)
    lock = threading.Lock()

    def one(customer: dict[str, Any]) -> None:
        result = write_one(client, customer, topics)
        with lock:  # requests first, then the row: a resume drops requests whose row is missing
            with REQUESTS.open("a", encoding="utf-8") as f:
                f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in result["requests"])
            with KNOWLEDGE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(result["row"], ensure_ascii=False) + "\n")
            print(f"{customer['id']}: failed {len(result['row']['checks']['failed'])}", flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(one, [c for c in customers if c["id"] not in done]))
    order = {c["id"]: i for i, c in enumerate(customers)}
    write_jsonl(KNOWLEDGE, sorted(read_jsonl(KNOWLEDGE), key=lambda r: order[r["id"]]))
    write_jsonl(REQUESTS, sorted(read_jsonl(REQUESTS), key=lambda r: (order[r["id"]], r["attempt"])))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("smoke")
    s.add_argument("--ids", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--usd-cap", type=float, required=True)
    s.set_defaults(fn=cmd_smoke)
    r = sub.add_parser("run")
    r.add_argument("--resume", action="store_true")
    r.add_argument("--usd-cap", type=float, required=True)
    r.add_argument("--workers", type=int, default=4)
    r.set_defaults(fn=cmd_run)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
