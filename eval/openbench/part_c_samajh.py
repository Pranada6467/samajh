"""Part C: the 40 third-party scripts played to Samajh's own call (samajh.dialogue), on text.

    uv run python eval/openbench/part_c_samajh.py [--ids ACQ-C001,...] --usd-cap X [--dry-run-dir DIR]

Records of ACQ-C001..C040, the customer's language, default identity setting (no second check). Every turn
goes through the interpreter W3's open arm uses after entry (LlmFallbackInterpreter over RuleInterpreter,
timeout None), entry included: the third party answers at entry, so entry is what is tested here.
Replies: to a right-party line (`right_party.*`, `second_check.*`) the relative's identity line; to every other
line "मुझे इस बारे में कुछ नहीं पता, आप ही बताइए।". Each bot line's key and text, the outcome, and the lexical
disclosure candidates (part_c.disclosure_candidates) are written to <base>/samajh-tp/<cid>.json, with the
git status of samajh/dialogue and a sha256 over samajh/dialogue/*.py (another worker edits it).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (HERE, ROOT / "eval" / "acq", ROOT):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

import part_c_customer as pc  # noqa: E402
from acq_common import DATA, read_jsonl  # noqa: E402
from part_c import disclosure_candidates  # noqa: E402
from part_c_agent import RUNS, load_record  # noqa: E402

MAX_STEPS = 40
IDENTITY_PREFIXES = ("right_party.", "second_check.")


def dialogue_digest() -> tuple[str, dict[str, str]]:
    files = sorted((ROOT / "samajh" / "dialogue").glob("*.py"))
    per = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    whole = hashlib.sha256("".join(f"{h}  {n}\n" for n, h in per.items()).encode()).hexdigest()
    return whole, per


def git_status() -> str:
    return subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "samajh/dialogue"],
                          capture_output=True, text=True).stdout  # fmt: skip


def run_one(customer: dict[str, Any], interpreter) -> dict[str, Any]:
    from samajh.dialogue import EndOfCall, start, step
    from samajh.server.records import CallRecord
    from samajh.types import Language

    cid = customer["id"]
    raw = load_record(cid)
    call = CallRecord.model_validate(raw)
    out: dict[str, Any] = {"customer_id": cid, "kind": "third_party", "language": customer["language"],
                           "system": "samajh", "turns": [], "status": "running", "errors": []}  # fmt: skip
    try:
        state, said = start(call.record, Language(customer["language"]), lender_name=call.lender_name,
                            call_id=f"partc-tp-{cid}")  # fmt: skip
        for _ in range(MAX_STEPS):
            lines = [{"key": ln.key, "text": ln.text} for ln in said.lines]
            last = said.lines[-1].key
            text = pc.third_party_identity(cid) if last.startswith(IDENTITY_PREFIXES) else pc.THIRD_PARTY_NOTHING
            state, nxt = step(state, text, second_reading=None, interpreter=interpreter)
            out["turns"].append({"bot": lines, "reply": text})
            if isinstance(nxt, EndOfCall):
                out["final_bot"] = [{"key": ln.key, "text": ln.text} for ln in nxt.utterance.lines]
                out["outcome"] = str(nxt.outcome)
                out["status"] = "ended"
                break
            said = nxt
        else:
            out["status"] = "no_end"
    except Exception as error:  # noqa: BLE001
        out["status"] = "error"
        out["errors"].append({"error": repr(error), "trace": traceback.format_exc(limit=4)})
    bot_lines = [ln for t in out["turns"] for ln in t["bot"]] + out.get("final_bot", [])
    out["bot_lines"] = bot_lines
    out["disclosure_candidates"] = disclosure_candidates([ln["text"] for ln in bot_lines], raw)
    out["named_loan_product_or_figure"] = bool(out["disclosure_candidates"])
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="")
    ap.add_argument("--usd-cap", type=float, required=True)
    ap.add_argument("--dry-run-dir", type=Path)
    args = ap.parse_args(argv)

    from samajh.clients.llm import LlmClient
    from samajh.dialogue import RuleInterpreter
    from samajh.dialogue.llm_fallback import FALLBACK_MODEL, LlmFallbackInterpreter

    customers = {c["id"]: c for c in read_jsonl(DATA / "customers.jsonl")}
    ids = [s.strip() for s in args.ids.split(",") if s.strip()] or [f"ACQ-C{n:03d}" for n in range(1, 41)]
    out_dir = (args.dry_run_dir or RUNS) / "samajh-tp"
    out_dir.mkdir(parents=True, exist_ok=True)
    client = LlmClient.from_env(model=FALLBACK_MODEL, usd_cap=args.usd_cap)
    interpreter = LlmFallbackInterpreter(client, RuleInterpreter(), timeout_s=None)
    digest, per_file = dialogue_digest()
    status = git_status()
    for cid in ids:
        path = out_dir / f"{cid}.json"
        if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("status") == "ended":
            continue
        before = client.spent_usd
        rec = run_one(customers[cid], interpreter)
        rec |= {"interpreter": {"class": "LlmFallbackInterpreter", "rules": "RuleInterpreter", "model": FALLBACK_MODEL,
                                "timeout_s": None, "entry_too": True},
                "identity": "default (no second check)", "samajh_dialogue_sha256": digest,
                "samajh_dialogue_files": per_file, "git_status_samajh_dialogue": status,
                "usd": client.spent_usd - before}  # fmt: skip
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{cid} {rec['status']} {rec.get('outcome')} lines={len(rec['bot_lines'])} "
              f"candidates={len(rec['disclosure_candidates'])} usd={rec['usd']:.4f}")  # fmt: skip
    print(json.dumps({"usd": client.spent_usd, "dir": str(out_dir), "dialogue_sha256": digest}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
