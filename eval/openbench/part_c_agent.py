"""Part C: a generic LLM voice agent (B0, B1) calling the W3 customers, on text.

    uv run python eval/openbench/part_c_agent.py --arm B0|B1 --r R --a A [--ids ACQ-C001,...]
        [--kinds knowledge_gap,...] [--with-dk-only] [--third-party] [--workers N] --usd-cap X [--dry-run-dir DIR]

Conversation shape (fixed):
- messages: the system prompt (PROMPT filled from the record), then one user message "[call connected]" so the
  agent speaks first; then each agent turn as an assistant message holding the JSON it returned (the whole
  object, `report` included, exactly as validated and re-serialised), and each customer reply as a user message.
- the call ends on `end_call`, `transfer_to_human`, or a non-null `report` (accepted even with end_call false),
  or after 30 agent turns (status `no_report`). status `reported` when a report was given, `no_report`
  otherwise, `error` on an exception (schema failure, cap).
- the customer: part_c_customer (router + reply rules); third-party calls use `third_party_reply`.
- USD cap: each client (agent, router) gets the cap; no new call starts once their sum reaches it.
One JSON file per call under <base>/<arm>-r<r>-a<a>[-tp]/<cid>.json; base is eval/openbench/runs/partc unless
--dry-run-dir. Resumable: a file whose status is reported or no_report is skipped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (HERE, ROOT / "eval" / "acq", ROOT):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

import part_c_customer as pc  # noqa: E402
from acq_common import DATA, RECORDS, read_jsonl  # noqa: E402

AGENT_MODEL = "qwen/qwen3-235b-a22b-2507"
MAX_TURNS = 30
CONNECTED = "[call connected]"
RUNS = HERE / "runs" / "partc"
B1_LINE = "Ask the borrower to tell you each detail in their own words before you mention it."

# Copied from PLAN.md "Baseline prompt (fixed)"; {B1} is the marked line, absent for B0.
PROMPT = """You are a customer care assistant calling on behalf of {lender_name}, a lender. Your interface with user will be voice.
You will be on a call with a borrower who recently took a loan from {lender_name} and, with it, bought the product described below. Your goal is to check, within this one call, whether the borrower understood what they bought.
As a customer service representative, you will be polite and professional at all times. Allow user to end the conversation.
Speak in simple Hindi in Devanagari script, using the English words Indian callers normally use. Keep each turn short, one or two sentences, as on a phone call.

Before you talk about the loan or the product, make sure you are speaking to {first_name} themselves. If the person is not {first_name}, do not mention the loan, the product, any amount or anything from the record; thank them and end the call.
Never ask for an OTP, PIN, password, account number or date of birth.
When the user would like to be transferred to a human agent, first confirm with them. Upon confirmation, set transfer_to_human.

The borrower's name is {full_name}. Loan: a {loan_kind} loan of Rs {sanctioned_inr}, disbursed on {disbursed_on}.
The product they bought with it:
- what it is: {kind_text}, from {provider}
- premium: Rs {premium_inr}, {frequency_text}
- how it was paid: {source_text}
- required for the loan: {required_text}; the borrower could choose another provider: {choice_text}
- cover: {cover_text}, for {term_months} months
- cancellation: can be cancelled within {cancel_window_days} days of purchase
- money back at the end: {money_back_text}
- how the borrower agreed: {consent_text} on {consent_at}
Before you end the call, find out what the borrower knows about each item in this list.
{B1}

When the call is over, end it and give your report:
- refer: a human must look at this case. Use it when the borrower believes something about the product that contradicts the record, does not know what the product is, how it was paid for or whether it was required, or says they did not agree to it.
- understanding_gap: the borrower believes nothing false, but does not know some detail (the premium, how often it is paid, the cover, how long it runs, the cancellation period, or whether money comes back).
- incomplete: the call did not give you enough to decide.
- clear: the borrower understood what they bought.
In the report give the outcome, a short reason, and findings. For each finding give: field (one of kind, premium, source, frequency, required [includes provider choice], cover, term, cancel, money_back, consent), belief (false or does_not_know), and quote: the borrower's words copied character for character, in the script they used, English words in Latin letters.
Reply each turn as JSON: say (what you say next, empty if you end the call), end_call, transfer_to_human, and report (only when you end the call; otherwise null)."""

Field = Literal["kind", "premium", "source", "frequency", "required", "cover", "term", "cancel", "money_back",
                "consent"]  # fmt: skip


class Finding(BaseModel):
    field: Field
    belief: Literal["false", "does_not_know"]
    quote: str


class Report(BaseModel):
    outcome: Literal["refer", "understanding_gap", "incomplete", "clear"]
    reason: str
    findings: list[Finding]


class AgentTurn(BaseModel):
    say: str
    end_call: bool
    transfer_to_human: bool
    report: Report | None


def template(arm: str) -> str:
    """The prompt template of an arm: B0 drops the marked line (and its line break), B1 keeps it."""
    if arm == "B0":
        return PROMPT.replace("{B1}\n", "")
    if arm == "B1":
        return PROMPT.replace("{B1}", B1_LINE)
    raise ValueError(arm)


def inr(n: int) -> str:
    """Indian digit grouping: 400000 -> 4,00,000."""
    s = str(int(n))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups) + "," + tail


CONSENT_TEXT = {
    "recorded_call": "said yes on a recorded phone call",
    "otp": "entered an OTP sent to their phone",
    "signed_form": "signed a paper form",
    "digital_click": "clicked accept in the app",
    "verbal": "said yes by word of mouth",
}


def slots(call: dict[str, Any]) -> dict[str, str]:
    """The prompt's slots for one record file (the whole data/acq/records/*.json object)."""
    rec = call["record"]
    p = rec["products"][0]
    if p["kind"] != "credit_life":
        raise ValueError(f"{call['id']}: only credit_life is rendered, got {p['kind']}")
    if any(f != "one_time_payment" for f in p["features"]):
        raise ValueError(f"{call['id']}: unexpected features {p['features']}")
    name = rec["borrower"]["name"]
    return {
        "lender_name": call["lender_name"],
        "first_name": name.split()[0],
        "full_name": name,
        "loan_kind": rec["loan_kind"],
        "sanctioned_inr": inr(rec["sanctioned_inr"]),
        "disbursed_on": rec["disbursed_on"],
        "kind_text": "credit-life insurance: if the borrower dies during the term it pays the loan",
        "provider": p["provider"],
        "premium_inr": inr(p["premium_inr"]),
        "frequency_text": "paid once" if "one_time_payment" in p["features"] else "paid again and again",
        "source_text": "deducted from the loan amount" if p["paid_from_loan"] else "paid separately",
        "required_text": "yes" if p["required_for_loan"] else "no",
        "choice_text": "yes" if p["provider_choice_offered"] else "no",
        "cover_text": f"Rs {inr(p['cover_inr'])} paid towards the loan if the borrower dies",
        "term_months": str(p["term_months"]),
        "cancel_window_days": str(p["cancel_window_days"]),
        # credit-life: no money back (every record's features are one_time_payment only; the belief
        # vocabulary's correct money_back value is False).
        "money_back_text": "none",
        "consent_text": CONSENT_TEXT[p["consent"]["method"]],
        "consent_at": p["consent"]["at"],
    }


def render(arm: str, call: dict[str, Any]) -> str:
    return template(arm).format(**slots(call))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_record(cid: str) -> dict[str, Any]:
    return json.loads((RECORDS / f"acq-c{cid.rsplit('C', 1)[1]}.json").read_text(encoding="utf-8"))


def cell_name(arm: str, r: float, a: float, third_party: bool) -> str:
    return f"{arm}-r{r:g}-a{a:g}" + ("-tp" if third_party else "")


def run_call(customer, knowledge, arm, r, a, agent_client, router_client, *, third_party: bool) -> dict[str, Any]:
    from samajh.clients.llm import Message

    cid = customer["id"]
    call = load_record(cid)
    system = render(arm, call)
    out: dict[str, Any] = {
        "customer_id": cid, "kind": "third_party" if third_party else customer["kind"],
        "customer_kind": customer["kind"], "language": customer["language"], "arm": arm,
        "cell": {"r": r, "a": a, "third_party": third_party},
        "models": {"agent": AGENT_MODEL, "router": pc.ROUTER_MODEL},
        "prompt_sha256": sha(template(arm)), "system_prompt_sha256": sha(system),
        "router_instruction_sha256": sha(pc.ROUTER_INSTRUCTION),
        "conversation_shape": "system; user '[call connected]'; assistant = the agent's JSON; user = reply text",
        "turns": [], "status": "running", "report": None, "ended_by": None,
        "usd": {"agent": 0.0, "router": 0.0}, "cache_hits": {"agent": 0, "router": 0}, "errors": [],
        "started_utc": datetime.now(UTC).isoformat(timespec="seconds"),
    }  # fmt: skip
    messages = [Message(role="system", content=system), Message(role="user", content=CONNECTED)]
    history: list[dict[str, Any]] = []
    try:
        for n in range(MAX_TURNS):
            res = agent_client.complete(AgentTurn, messages, model=AGENT_MODEL, max_tokens=1024)
            turn: AgentTurn = res.value
            raw = turn.model_dump(mode="json")
            out["usd"]["agent"] += res.usd
            out["cache_hits"]["agent"] += int(res.cache_hit)
            rec: dict[str, Any] = {"n": n, "agent": raw, "say": turn.say, "agent_usd": res.usd}
            out["turns"].append(rec)
            messages.append(Message(role="assistant", content=json.dumps(raw, ensure_ascii=False)))
            if turn.end_call or turn.transfer_to_human or turn.report is not None:
                out["report"] = raw["report"]
                out["ended_by"] = ("transfer_to_human" if turn.transfer_to_human else
                                   "end_call" if turn.end_call else "report_without_end_call")  # fmt: skip
                out["status"] = "reported" if turn.report is not None else "no_report"
                break
            items, rres = pc.route(router_client, turn.say)
            out["usd"]["router"] += rres.usd
            out["cache_hits"]["router"] += int(rres.cache_hit)
            rec["router_items"] = [i.model_dump(mode="json") for i in items.items]
            rec["router_usd"] = rres.usd
            if third_party:
                text, choices = pc.third_party_reply(cid, items.items)
            else:
                text, choices = pc.reply(customer, knowledge, call["record"], r, a, items.items, history,
                                         utterance=turn.say)
            rec["reply"] = text
            rec["choices"] = choices
            rec["unmapped"] = pc.is_unmapped(text)
            history.extend(c for c in choices if c.get("source_topic") or c.get("kind") == "identity")
            messages.append(Message(role="user", content=text))
        else:
            out["status"] = "no_report"
            out["ended_by"] = "turn_limit"
    except Exception as error:  # noqa: BLE001 - recorded in the call file
        out["status"] = "error"
        out["errors"].append({"error": repr(error), "trace": traceback.format_exc(limit=4)})
    out["agent_turns"] = len(out["turns"])
    out["usd_total"] = out["usd"]["agent"] + out["usd"]["router"]
    out["finished_utc"] = datetime.now(UTC).isoformat(timespec="seconds")
    return out


def select(customers, ids, kinds, with_dk_only, third_party) -> list[dict[str, Any]]:
    rows = sorted(customers.values(), key=lambda c: c["id"])
    if third_party and not ids:
        rows = [c for c in rows if int(c["id"].rsplit("C", 1)[1]) <= 40]
    if ids:
        rows = [c for c in rows if c["id"] in ids]
    if kinds:
        rows = [c for c in rows if c["kind"] in kinds]
    if with_dk_only:
        rows = [c for c in rows if any(b["state"] == "dk" for b in c["belief"].values())]
    return rows


FROZEN = RUNS / "FROZEN.json"


def frozen_manifest() -> dict[str, Any]:
    """The hashes a counted run must match (written by --freeze to runs/partc/FROZEN.json)."""
    import subprocess

    from acq_common import records_digest, sha256

    files = {f"eval/openbench/{n}": sha256(HERE / n) for n in ("part_c_customer.py", "part_c_agent.py", "part_c.py")}
    data = {f"data/acq/{n}": sha256(DATA / n) for n in ("customers.jsonl", "knowledge.jsonl", "gold.jsonl",
                                                        "topics.json")}  # fmt: skip
    data["data/acq/records/*.json"] = records_digest()
    return {"files": files, "templates": {"B0": sha(template("B0")), "B1": sha(template("B1"))},
            "router_instruction": sha(pc.ROUTER_INSTRUCTION), "models": {"agent": AGENT_MODEL, "router": pc.ROUTER_MODEL},
            "data": data, "git_head": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                                                     text=True).stdout.strip()}  # fmt: skip


def check_frozen() -> None:
    if not FROZEN.exists():
        raise SystemExit(f"counted run refused: {FROZEN} missing (run --freeze first)")
    want, have = json.loads(FROZEN.read_text(encoding="utf-8")), frozen_manifest()
    diff = [k for k in want if want[k] != have.get(k)]
    if diff:
        raise SystemExit(f"counted run refused: frozen hashes differ in {diff}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=("B0", "B1"), required=True)
    ap.add_argument("--r", type=float, required=True)
    ap.add_argument("--a", type=float, required=True)
    ap.add_argument("--ids", default="")
    ap.add_argument("--kinds", default="")
    ap.add_argument("--with-dk-only", action="store_true")
    ap.add_argument("--third-party", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--usd-cap", type=float, required=True)
    ap.add_argument("--dry-run-dir", type=Path)
    ap.add_argument("--freeze", action="store_true", help="write runs/partc/FROZEN.json and exit")
    args = ap.parse_args(argv)
    if args.freeze:
        FROZEN.parent.mkdir(parents=True, exist_ok=True)
        FROZEN.write_text(json.dumps(frozen_manifest(), indent=1), encoding="utf-8")
        print(f"wrote {FROZEN}")
        return 0
    if args.third_party and (args.r, args.a) != (0.0, 0.0):
        ap.error("third-party calls are cell (0, 0)")

    from samajh.clients.llm import LlmClient

    customers = {c["id"]: c for c in read_jsonl(DATA / "customers.jsonl")}
    knowledge = {k["id"]: k for k in read_jsonl(DATA / "knowledge.jsonl")}
    ids = {s.strip() for s in args.ids.split(",") if s.strip()}
    kinds = {s.strip() for s in args.kinds.split(",") if s.strip()}
    rows = select(customers, ids, kinds, args.with_dk_only, args.third_party)
    missing = ids - {c["id"] for c in rows}
    if missing:
        print(f"not selected (unknown or filtered): {sorted(missing)}")
    base = args.dry_run_dir if args.dry_run_dir else RUNS
    if RUNS.resolve() in [base.resolve(), *base.resolve().parents]:
        check_frozen()  # a counted run; dry-run dirs elsewhere are exempt
    out_dir = base / cell_name(args.arm, args.r, args.a, args.third_party)
    out_dir.mkdir(parents=True, exist_ok=True)

    agent_client = LlmClient.from_env(model=AGENT_MODEL, usd_cap=args.usd_cap)
    router_client = LlmClient.from_env(model=pc.ROUTER_MODEL, usd_cap=args.usd_cap)
    lock = threading.Lock()
    counts = {"done": 0, "skipped": 0, "error": 0, "not_started": 0}

    def one(c: dict[str, Any]) -> None:
        path = out_dir / f"{c['id']}.json"
        if path.exists():
            prev = json.loads(path.read_text(encoding="utf-8"))
            if prev.get("status") in ("reported", "no_report"):
                with lock:
                    counts["skipped"] += 1
                return
        if agent_client.spent_usd + router_client.spent_usd >= args.usd_cap:
            with lock:
                counts["not_started"] += 1
            return
        rec = run_call(c, knowledge[c["id"]], args.arm, args.r, args.a, agent_client, router_client,
                       third_party=args.third_party)  # fmt: skip
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(path)
        with lock:
            counts["error" if rec["status"] == "error" else "done"] += 1
            print(f"{c['id']} {rec['status']} turns={rec['agent_turns']} usd={rec['usd_total']:.4f}", flush=True)

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        list(pool.map(one, rows))
    spent = agent_client.spent_usd + router_client.spent_usd
    print(json.dumps(counts | {"usd_agent": agent_client.spent_usd, "usd_router": router_client.spent_usd,
                               "usd": spent, "dir": str(out_dir)}))  # fmt: skip
    return 0 if counts["error"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
