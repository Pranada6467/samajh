"""ACQ driver: open calls on text per (customer, a) and symbolic closed calls per (customer, r, a). No Gnani call.

    uv run python eval/acq/acq_run.py --out eval/acq/runs/NAME --usd-budget X [--customers ACQ-C001,...]
        [--a-levels 0,0.25,0.5,0.75,1] [--workers 2] [--label ...] [--knowledge PATH] [--dry-run-unfrozen]

Resumable: a call whose file exists is skipped (a no_result file is not rerun). Refuses to start unless
data/acq/FROZEN.json exists and every digest in it matches the disk (`check_frozen`), except with
`--dry-run-unfrozen`, which marks the manifest `"frozen": false`.

Open call: entry with `RuleInterpreter()` only and fixed replies (acq_player.entry_reply) until the first
utterance whose last line is `open_recall.ask` (anything else first: `status: "entry_failed"`); then the
LLM turn classifier over the word lists, no wall-clock limit, `second_reading=None`; then
`samajh.pipeline.run_text` as P5 does. `--usd-budget` is a hard stop on this process's OpenRouter spend;
the client's own cap is 2 x budget + 0.10.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from collections.abc import Sequence
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (HERE, ROOT / "eval" / "p5", ROOT):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

from acq_common import DATA, FLAG_FIELD, RECORDS, read_jsonl, records_digest, sha256  # noqa: E402
from acq_common import FIELDS  # noqa: E402,F401
from acq_player import (  # noqa: E402
    SCORED_START_KEY, AcqChoice, choose_open, closed_answers, closed_outcomes, entry_reply,
    load_knowledge, load_topic_fields,
)  # fmt: skip
from player import Said  # noqa: E402
from text_run import RecordingInterpreter, _end_fields, _lines, view  # noqa: E402

from samajh.types import FlagReason, Language  # noqa: E402

# The belief field each gap's rule is about (coordinator's map, fix round 1); others -> None.
GAP_FIELD: dict[str, str] = {
    "kind": "kind", "premium": "premium", "cover": "cover", "term": "term", "cancel_window": "cancel",
    "consent": "consent", "loan_funded": "source", "bundling": "required", "belief_mismatch": "money_back",
    "recall": "kind", "recall_unmatched": "kind",
}  # fmt: skip
LEVELS = (0.0, 0.25, 0.5, 0.75, 1.0)
MAX_STEPS = 80
SOURCE_DIRS = ("samajh/dialogue", "samajh/extract", "samajh/rules")


class FrozenMismatch(RuntimeError):
    """A file does not match the digest in data/acq/FROZEN.json."""


P5_FILES = ("eval/p5/player.py", "eval/p5/text_run.py", "eval/p5/bank.py", "eval/p5/write_customers.py")
TREE_DIRS = ("samajh", "data/prompts")


def _tree(root: Path, dirs: Sequence[str]) -> tuple[str, list[list[str]]]:
    files = sorted(
        [str(p.relative_to(root)), sha256(p)]
        for d in dirs for p in (root / d).rglob("*") if p.is_file() and "__pycache__" not in p.parts
    )  # fmt: skip
    joined = "".join(f"{path}\t{digest}\n" for path, digest in files)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest(), files


def frozen_files(root: Path = ROOT) -> list[str]:
    """eval/acq/*.py, the P5 harness files the ACQ run imports, and every top-level data/acq file."""
    acq = sorted(str(p.relative_to(root)) for p in (root / "eval" / "acq").glob("*.py"))
    data = sorted(str(p.relative_to(root)) for p in (root / "data" / "acq").iterdir()
                  if p.is_file() and p.name != "FROZEN.json")  # fmt: skip
    return acq + list(P5_FILES) + data


def make_frozen(root: Path = ROOT) -> dict[str, Any]:
    tree, _ = _tree(root, TREE_DIRS)
    return {"files": {f: sha256(root / f) for f in frozen_files(root)},
            "records": records_digest(root / "data" / "acq" / "records"),
            "source_tree": {"commit": _git("rev-parse", "HEAD"), "sha256": tree,
                            "covers": list(TREE_DIRS)}}  # fmt: skip


def check_frozen(path: Path = DATA / "FROZEN.json", root: Path = ROOT) -> dict[str, Any]:
    """Every digest in FROZEN.json against the disk: files (paths relative to the repo root), the records
    digest, the source tree (samajh/ and data/prompts/), and no data/acq file left unlisted. Raises on any
    mismatch."""
    if not path.exists():
        raise FrozenMismatch(f"{path} does not exist: freeze first (acq_run.py freeze)")
    frozen = json.loads(path.read_text(encoding="utf-8"))
    bad = []
    for key in ("files", "records", "source_tree"):
        if key not in frozen:
            bad.append(f"{key}: missing from FROZEN.json")
    for rel, want in sorted(frozen.get("files", {}).items()):
        target = root / rel
        got = sha256(target) if target.is_file() else None
        if got != want:
            bad.append(f"{rel}: frozen {want[:12]}, disk {got[:12] if got else 'missing'}")
    unlisted = sorted(set(frozen_files(root)) - set(frozen.get("files", {})))
    bad += [f"{rel}: on disk, not in FROZEN.json" for rel in unlisted]
    if "records" in frozen and records_digest(root / "data" / "acq" / "records") != frozen["records"]:
        bad.append("records: digest differs")
    if "source_tree" in frozen and _tree(root, TREE_DIRS)[0] != frozen["source_tree"].get("sha256"):
        bad.append("source_tree: samajh/ or data/prompts/ differs")
    if bad:
        raise FrozenMismatch("FROZEN.json does not match the disk:\n  " + "\n  ".join(bad))
    return frozen


def harness_hashes() -> dict[str, str]:
    return {f"eval/acq/{p.name}": sha256(p) for p in sorted(HERE.glob("*.py"))}


def source_hashes(root: Path = ROOT) -> tuple[str, list[list[str]]]:
    return _tree(root, SOURCE_DIRS)


def open_name(cid: str, a: float) -> str:
    return f"{cid}__open__a{a:g}.json"


def closed_name(cid: str, r: float, a: float) -> str:
    return f"{cid}__closed__r{r:g}__a{a:g}.json"


def load_call_record(record_id: str):
    from samajh.server.records import CallRecord

    return CallRecord.model_validate_json((RECORDS / f"{record_id}.json").read_bytes())


def _base(customer: dict[str, Any], gold: dict[str, Any], arm: str) -> dict[str, Any]:
    return {
        "customer_id": customer["id"], "arm": arm, "kind": customer["kind"], "gold_class": gold["class"],
        "language": customer["language"], "gender": customer["gender"], "record_id": customer["record_id"],
        "writer_model": customer["writer_model"],
    }  # fmt: skip


def run_closed(customer: dict[str, Any], gold: dict[str, Any], statements: dict[str, Any], r: float,
               a: float) -> dict[str, Any]:  # fmt: skip
    answers = {x["field"]: x for x in closed_answers(customer, r, a)}
    ordered = [answers[s["field"]] | {"statement": s["text"]} for s in statements["statements"]]
    if len(ordered) != len(answers):
        raise ValueError(f"{customer['id']}: closed statements do not cover every field")
    return _base(customer, gold, "closed") | {"r": r, "a": a, "status": "ok", "answers": ordered,
                                               **closed_outcomes(ordered)}  # fmt: skip


def _choice(c: AcqChoice) -> dict[str, Any]:
    return {k: getattr(c, k) for k in ("topic", "variant", "text", "line_key", "mapped", "note", "field",
                                       "draw_a", "readback", "recall_rule", "source_topic")}  # fmt: skip


def drive_open(record: dict[str, Any], customer, knowledge, topic_fields, a, entry_interpreter, interpreter,
               *, entry_only: bool = False):  # fmt: skip
    """Drive one open call. Returns the EndOfCall, or None when entry failed (record says so) or when
    `entry_only` and the scored part was reached."""
    from samajh.dialogue import EndOfCall, start, step

    call = load_call_record(customer["record_id"])
    state, said = start(call.record, Language(customer["language"]), lender_name=call.lender_name,
                        call_id=f"acq-{customer['id']}-a{a:g}")  # fmt: skip
    history: list[Said] = []
    scored = False
    for _ in range(MAX_STEPS):
        lines = [view(ln) for ln in said.lines]
        last = lines[-1].key
        if not scored and last == SCORED_START_KEY:
            scored = True
            record["scored_from_turn"] = len(record["turns"])
            if entry_only:
                return None
        if scored:
            choice = choose_open(customer, knowledge, topic_fields, a, lines, history)
            if not choice.mapped:
                record["unmapped"].append({"line_key": choice.line_key, "note": choice.note})
            reply, rec, interp = choice.text, _choice(choice), interpreter
        else:
            text = entry_reply(last, customer["gender"])
            if text is None:
                record["status"] = "entry_failed"
                record["entry_failed_at"] = {"line_key": last, "bot": _lines(said)}
                return None
            reply, rec, interp = text, {"topic": "entry", "variant": "fixed", "field": None, "text": text,
                                        "line_key": last}, \
                entry_interpreter  # fmt: skip
        state, nxt = step(state, reply, second_reading=None, interpreter=interp)
        reply_turn = len(state.turns) - (len(nxt.utterance.lines) if isinstance(nxt, EndOfCall) else len(nxt.lines))
        record["turns"].append({"bot": _lines(said), "reply": rec, "field": rec.get("field"),
                                "variant": rec["variant"], "readings": interp.take(),
                                "degraded": reply_turn in state.degraded_turns, "scored": scored})  # fmt: skip
        if rec["topic"] == "anything_else":
            record["anything_else_turns"] = record.get("anything_else_turns", 0) + 1
        if scored:
            history.append(Said(choice.topic, choice.variant, choice.text))
        if isinstance(nxt, EndOfCall):
            if not scored:
                record["status"] = "entry_failed"
                record["entry_failed_at"] = {"end_of_call": str(nxt.outcome), "bot": _lines(nxt.utterance)}
                _end_fields(record, nxt)
                return None
            return nxt
        said = nxt
    raise RuntimeError(f"no end after {MAX_STEPS} customer turns")


class CountingLlm:
    """Forwards to an LLM client and counts this call's requests, cache hits and USD (safe across threads)."""

    def __init__(self, inner) -> None:
        self._inner = inner
        self._lock = threading.Lock()
        self.requests = self.cache_hits = 0
        self.usd = 0.0

    def complete(self, schema, messages, **options):
        result = self._inner.complete(schema, messages, **options)
        with self._lock:
            self.requests += 1
            self.cache_hits += bool(getattr(result, "cache_hit", False))
            self.usd += float(getattr(result, "usd", 0.0) or 0.0)
        return result

    def __getattr__(self, name):
        return getattr(self._inner, name)


def run_open(customer, gold, knowledge, topic_fields, a, client, *, without_temperature: bool, run_text=None
             ) -> dict[str, Any]:  # fmt: skip
    """One open call. `client` is the shared LLM client; this call gets its own counting wrapper."""
    from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
    from samajh.pipeline import WithoutTemperature
    from samajh.pipeline import run_text as _run_text

    run_text = run_text or _run_text
    counter = CountingLlm(client)
    llm = WithoutTemperature(counter) if without_temperature else counter
    from samajh.dialogue import RuleInterpreter
    from samajh.rules import summarise

    interpreter = LlmFallbackInterpreter(counter, RuleInterpreter(), timeout_s=None)

    record = _base(customer, gold, "open") | {"a": a, "second_reading": None, "status": "running",
                                              "turns": [], "unmapped": [], "errors": []}  # fmt: skip
    record["anything_else_turns"] = 0
    try:
        end = drive_open(record, customer, knowledge, topic_fields, a, RecordingInterpreter(RuleInterpreter()),
                         RecordingInterpreter(interpreter))  # fmt: skip
        if end is not None:
            _end_fields(record, end)
            call = load_call_record(customer["record_id"])
            result = run_text(end.transcript, call.record, llm).result
            record["tier"] = str(result.tier)
            record["flags"] = [
                {"rule_id": str(f.rule_id), "reason": str(f.reason), "tier": str(f.tier), "basis": str(f.basis),
                 "product_id": f.product_id, "quote": f.quote, "field": FLAG_FIELD[FlagReason(f.reason)]}
                for f in result.all_flags()
            ]  # fmt: skip
            record["gaps"] = [{"rule_id": str(g.rule_id), "reason": str(g.reason), "tier": str(g.tier),
                               "quote": g.quote, "field": GAP_FIELD.get(str(g.rule_id))}
                              for g in result.all_gaps()]  # fmt: skip
            basis = result.referral_basis
            record["referral_basis"] = str(basis) if basis is not None else None
            record["summary"] = summarise(call.record, result).model_dump(mode="json")
            record["transcript"] = end.transcript.model_dump(mode="json")
            record["status"] = "ok"
    except Exception as error:  # noqa: BLE001 - the call stays as a row with its error
        record["status"] = "no_result"
        record["errors"].append({"error": repr(error), "traceback": traceback.format_exc()})
    record["llm_requests"], record["llm_cache_hits"] = counter.requests, counter.cache_hits
    record["usd_this_call"] = round(counter.usd, 6)
    record["degraded_turn_count"] = sum(bool(t.get("degraded")) for t in record["turns"])
    return record


def preflight(customers: dict[str, dict[str, Any]], topic_fields: dict[str, str]) -> list[str]:
    """Run the entry for every customer with RuleInterpreter only; the ids that do not reach open recall."""
    from samajh.dialogue import RuleInterpreter

    failed = []
    for cid, customer in sorted(customers.items()):
        record: dict[str, Any] = {"turns": [], "unmapped": []}
        rule = RecordingInterpreter(RuleInterpreter())
        try:
            drive_open(record, customer, None, topic_fields, 0.0, rule, rule, entry_only=True)
        except Exception:  # noqa: BLE001
            record["status"] = "entry_failed"
        if record.get("status") == "entry_failed" or "scored_from_turn" not in record:
            failed.append(cid)
    return failed


def plan_calls(ids: Sequence[str], a_levels: Sequence[float]) -> list[tuple[str, float]]:
    """Customer-major: every a for one customer, then the next, so a budget stop never drops a whole a cell."""
    return [(cid, a) for cid in ids for a in a_levels]


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False).stdout.rstrip("\n")


def _write(path: Path, record: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["freeze"]:
        fp = argparse.ArgumentParser(description="write data/acq/FROZEN.json")
        fp.add_argument("--out", type=Path, required=True)
        out = fp.parse_args(argv[1:]).out
        frozen = make_frozen()
        out.write_text(json.dumps(frozen, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {out}: {len(frozen['files'])} files, records {frozen['records'][:12]}, "
              f"source_tree {frozen['source_tree']['sha256'][:12]} at {frozen['source_tree']['commit'][:12]}")
        return 0
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--usd-budget", type=float, required=True)
    parser.add_argument("--customers", default="", help="comma-separated ids; all 160 when empty")
    parser.add_argument("--a-levels", default="0,0.25,0.5,0.75,1")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--label", default="")
    parser.add_argument("--knowledge", type=Path, default=DATA / "knowledge.jsonl")
    parser.add_argument("--dry-run-unfrozen", action="store_true")
    args = parser.parse_args(argv)

    if args.dry_run_unfrozen:
        print("!" * 72 + "\nWARNING: --dry-run-unfrozen: FROZEN.json NOT CHECKED. NOT A RESULT.\n" + "!" * 72,
              flush=True)  # fmt: skip
        frozen: dict[str, Any] | None = None
    else:
        try:
            frozen = check_frozen()
        except FrozenMismatch as error:
            print(f"REFUSED: {error}", file=sys.stderr)
            return 1
    a_levels = [float(x) for x in args.a_levels.split(",") if x]
    if set(a_levels) - set(LEVELS):
        parser.error(f"a levels are {LEVELS}")
    customers = {c["id"]: c for c in read_jsonl(DATA / "customers.jsonl")}
    gold = {g["id"]: g for g in read_jsonl(DATA / "gold.jsonl")}
    statements = {s["id"]: s for s in read_jsonl(DATA / "closed_statements.jsonl")}
    knowledge = load_knowledge(args.knowledge)
    topic_fields = load_topic_fields()
    ids = [x for x in args.customers.split(",") if x] or sorted(customers)
    missing = [i for i in ids if i not in knowledge]
    if missing:
        parser.error(f"no knowledge row for {missing[:5]} (of {len(missing)}) in {args.knowledge}")

    failed = preflight(customers, topic_fields)
    if failed:
        print(f"REFUSED: preflight entry reached open recall on {len(customers) - len(failed)} of "
              f"{len(customers)}; failed: {failed[:10]}", file=sys.stderr)  # fmt: skip
        return 1
    print(f"preflight: entry reached open recall on {len(customers)} of {len(customers)}", flush=True)

    calls_dir = args.out / "calls"
    calls_dir.mkdir(parents=True, exist_ok=True)
    closed_written = 0
    for cid in ids:
        for a in LEVELS:
            for r in LEVELS:
                path = calls_dir / closed_name(cid, r, a)
                if not path.exists():
                    _write(path, run_closed(customers[cid], gold[cid], statements[cid], r, a))
                    closed_written += 1

    from samajh.clients.llm import LlmClient
    from samajh.dialogue.llm_fallback import FALLBACK_MODEL
    from samajh.pipeline import takes_temperature

    cap = 2 * args.usd_budget + 0.10
    client = LlmClient.from_env(usd_cap=cap)
    extraction_model = client._model
    without_temperature = not takes_temperature(extraction_model)

    src_digest, src_files = source_hashes()
    tree_digest, _ = _tree(ROOT, TREE_DIRS)
    plan = plan_calls(ids, a_levels)
    manifest_path = args.out / "manifest.json"
    runs = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    manifest: dict[str, Any] = {
        "started_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_status_samajh_prompts": _git("status", "--porcelain", "samajh", "data/prompts"),
        "label": args.label, "frozen": frozen is not None, "frozen_digests": frozen,
        "knowledge": str(args.knowledge), "knowledge_sha256": sha256(args.knowledge),
        "source_sha256": src_digest, "source_files": src_files, "source_tree_sha256": tree_digest,
        "harness_sha256": harness_hashes(), "preflight": {"reached_open_recall": len(customers), "of": len(customers)},
        "interpreter": {"entry": "RuleInterpreter", "class": "LlmFallbackInterpreter", "model": FALLBACK_MODEL,
                        "timeout_s": None},
        "extraction_model": extraction_model, "second_reading": None,
        "a_levels": a_levels, "r_levels": list(LEVELS), "customers": ids, "planned_open_calls": len(plan),
        "plan": [[cid, a] for cid, a in plan],
        "closed_files_written": closed_written, "usd_budget": args.usd_budget, "client_usd_cap": cap,
    }  # fmt: skip

    lock = threading.Lock()
    stopped = threading.Event()
    counts = {"done": 0, "skipped": 0, "no_result": 0, "entry_failed": 0, "not_started": 0}

    def one(item: tuple[str, float]) -> None:
        cid, a = item
        path = calls_dir / open_name(cid, a)
        if path.exists():
            with lock:
                counts["skipped"] += 1
            return
        if stopped.is_set() or client.spent_usd >= args.usd_budget:
            stopped.set()
            with lock:
                counts["not_started"] += 1
            return
        record = run_open(customers[cid], gold[cid], knowledge[cid], topic_fields, a, client,
                          without_temperature=without_temperature)  # fmt: skip
        record["finished_utc"] = datetime.now(UTC).isoformat(timespec="seconds")
        _write(path, record)
        with lock:
            counts["done"] += 1
            counts["no_result"] += record["status"] == "no_result"
            counts["entry_failed"] += record["status"] == "entry_failed"
        print(f"{cid} open a{a:g}: {record.get('outcome')} tier={record.get('tier')} status={record['status']} "
              f"usd={record['usd_this_call']} requests={record['llm_requests']} hits={record['llm_cache_hits']}",
              flush=True)  # fmt: skip

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        list(pool.map(one, plan))

    complete = all((calls_dir / open_name(cid, a)).exists() for cid, a in plan)
    manifest |= {"finished_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                 "usd_spent_this_process": round(client.spent_usd, 6), "budget_reached": stopped.is_set(),
                 "complete": complete, **counts}  # fmt: skip
    runs.append(manifest)
    manifest_path.write_text(json.dumps(runs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("frozen", "complete", "usd_spent_this_process", "budget_reached",
                                               *counts)}))  # fmt: skip
    return 2 if stopped.is_set() else 0


if __name__ == "__main__":
    raise SystemExit(main())
