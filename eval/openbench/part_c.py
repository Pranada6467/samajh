"""Score Part C from the raw call files (offline, no LLM).

    uv run python eval/openbench/part_c.py [--base eval/openbench/runs/partc] [--w3 eval/acq/runs/counted]
        [--out-dir eval/openbench]

Reads every <base>/<cell>/*.json (B0/B1 cells and <cell>-tp third-party cells) and <base>/samajh-tp/*.json.
Writes <out-dir>/tables-partc.md and <out-dir>/results-c.json (per-call facts, for recomputation).

Per call (not third party): status, the report's outcome, gold class, and
- miss: a problem customer whose call has a report that is not `refer` (`no_report` and `error` counted apart);
- false_referral: a customer without a problem (knowledge_gap_only, no_problem) whose report is `refer`;
- gap_found: knowledge_gap_only, outcome `understanding_gap`, a finding `does_not_know` on a gold dk field whose
  quote (after wer.normalise) is in a customer turn that played an own or again reply (gap_found_any_quote:
  without the quote condition);
- ground_match: `refer` with a finding whose field is a gold ground field, belief `false` on a false field
  (`does_not_know` on a dk ground), quote in an own/again turn;
- ungrounded: a `refer` or `understanding_gap` report with a finding whose quote is in no customer turn;
- leading-statement candidates per agent turn (lexical; reader confirms), router `states` count, unmapped rate.
Third party: lexical disclosure candidates in every agent line (and every Samajh bot line).
Paired exact McNemar: B0 gap_found against W3 open-arm gap_found (acq_score.open_facts on W3's a = 0 call)
on knowledge_gap customers, at B0 cells (1, 0) and (0, 0); n = customers present in both.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (HERE, ROOT / "eval" / "acq", ROOT / "eval" / "amounts_v2", ROOT):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))

from acq_common import DATA, read_jsonl  # noqa: E402
from wer import normalise  # noqa: E402

from samajh.evalkit.score import mcnemar_exact, wilson  # noqa: E402

KINDS = ("informed", "knowledge_gap", "misled", "misled_with_gaps")
CLASSES = ("problem", "knowledge_gap_only", "no_problem")
OWN = frozenset({"own", "again"})

# --- lexical candidates --------------------------------------------------------------------------

PRODUCT_LOAN_WORDS = ("loan", "लोन", "ऋण", "कर्ज़", "कर्ज", "insurance", "इंश्योरेंस", "इन्श्योरेंस", "इंशुरेंस",
                      "बीमा", "policy", "पॉलिसी", "पालिसी", "premium", "प्रीमियम", "cover", "कवर", "emi", "ईएमआई",
                      "credit-life", "credit life", "क्रेडिट")  # fmt: skip
KIND_WORDS = ("insurance", "इंश्योरेंस", "इन्श्योरेंस", "इंशुरेंस", "बीमा", "credit-life", "credit life",
              "क्रेडिट लाइफ", "life cover", "लाइफ़ कवर", "लाइफ कवर")  # fmt: skip
SOURCE_WORDS = ("deduct", "डिडक्ट", "काट", "कट", "loan amount से", "लोन अमाउंट से", "लोन की रकम से", "separately",
                "अलग से")  # fmt: skip
_CLAUSE = re.compile(r"[।?!.,;:\n]+")
_DIGITS = re.compile(r"(?<![0-9])[0-9][0-9,]*(?![0-9])")
_AMOUNTS = None


def _amounts():
    global _AMOUNTS
    if _AMOUNTS is None:
        from part_c_customer import amounts

        _AMOUNTS = amounts()
    return _AMOUNTS


def numbers(text: str) -> dict[str, set[int]]:
    """Numbers in a text, by reading: digits, amounts (frozen parser, per clause), months, days."""
    m = _amounts()
    out: dict[str, set[int]] = {"digits": set(), "amount": set(), "months": set(), "days": set()}
    for d in _DIGITS.findall(text):
        try:
            out["digits"].add(int(d.replace(",", "")))
        except ValueError:
            pass
    for clause in [c for c in _CLAUSE.split(text.replace(",", "")) if c.strip()] + [text]:
        res = m.parse_amount(clause)
        if getattr(res, "status", None) == "parsed":
            out["amount"].add(int(res.rupees))
        for c in getattr(res, "candidates", ()) or ():
            out["amount"].add(int(c.rupees))
        mo, dy = m.parse_duration_months(clause), m.parse_duration_days(clause)
        if isinstance(mo, int):
            out["months"].add(mo)
        if isinstance(dy, int):
            out["days"].add(dy)
    return out


def _has(text: str, words) -> list[str]:
    low = text.lower()
    return [w for w in words if w.lower() in low]


def record_numbers(raw: dict[str, Any]) -> dict[str, int]:
    rec = raw["record"]
    p = rec["products"][0]
    return {"premium": p["premium_inr"], "cover": p["cover_inr"], "term": p["term_months"],
            "cancel": p["cancel_window_days"], "sanctioned": rec["sanctioned_inr"],
            "disbursed": rec["disbursed_inr"]}  # fmt: skip


def _num_hits(text: str, raw: dict[str, Any], fields) -> list[dict[str, Any]]:
    rn = record_numbers(raw)
    ns = numbers(text)
    hits = []
    for f in fields:
        v = rn[f]
        if f in ("premium", "cover", "sanctioned", "disbursed"):
            if v in ns["amount"] or v in ns["digits"]:
                hits.append({"field": f, "value": v})
        elif f == "term":
            if v in ns["months"] or v in ns["digits"] or (v % 12 == 0 and f"{v // 12} साल" in text):
                hits.append({"field": f, "value": v})
        elif f == "cancel":
            if v in ns["days"] or v in ns["digits"]:
                hits.append({"field": f, "value": v})
    return hits


def disclosure_candidates(texts: list[str], raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Lines that name the loan or product (word list; the lender name is removed first) or a record figure."""
    lender = raw.get("lender_name") or ""
    out = []
    for t in texts:
        if not t:
            continue
        s = t.replace(lender, " ") if lender else t
        words = _has(s, PRODUCT_LOAN_WORDS)
        nums = _num_hits(s, raw, ("premium", "cover", "term", "cancel", "sanctioned", "disbursed"))
        if words or nums:
            out.append({"text": t, "words": words, "figures": nums})
    return out


def leading_candidates(call: dict[str, Any], raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Agent turns that state a record value under test before the customer said it (lexical)."""
    said = ""
    out = []
    lender = raw.get("lender_name") or ""
    for t in call["turns"]:
        say = (t.get("say") or "").replace(lender, " ")
        before = numbers(said) if said else {"digits": set(), "amount": set(), "months": set(), "days": set()}
        hits = []
        for h in _num_hits(say, raw, ("premium", "cover", "term", "cancel")):
            v = h["value"]
            if not any(v in s for s in before.values()):
                hits.append(h)
        kw = _has(say, KIND_WORDS)
        if kw and not _has(said, KIND_WORDS):
            hits.append({"field": "kind", "words": kw})
        sw = _has(say, SOURCE_WORDS)
        if sw and not _has(said, SOURCE_WORDS):
            hits.append({"field": "source", "words": sw})
        if hits:
            out.append({"turn": t["n"], "say": t.get("say"), "hits": hits})
        said += " " + (t.get("reply") or "")
    return out


# --- per-call facts ------------------------------------------------------------------------------


def _quote_in(quote: str, turns: list[dict[str, Any]], own_only: bool) -> bool:
    q = normalise(quote or "")
    if not q:
        return False
    for t in turns:
        if "reply" not in t:
            continue
        if own_only and not any(c.get("variant") in OWN for c in t.get("choices", [])):
            continue
        if q in normalise(t["reply"]):
            return True
    return False


def call_facts(call: dict[str, Any], gold: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    rep = call.get("report") or {}
    outcome = rep.get("outcome") if call["status"] == "reported" else None
    findings = rep.get("findings") or []
    dk, false = set(gold["dk_fields"]), set(gold["false_fields"])
    turns = call["turns"]
    cls = gold["class"]

    def grounded(f):
        return _quote_in(f["quote"], turns, own_only=True)

    gap = [f for f in findings if f["belief"] == "does_not_know" and f["field"] in dk]
    if cls == "problem":
        ground = [f for f in findings if f["field"] in false and f["belief"] == "false"]
    else:
        ground = [f for f in findings if f["field"] in dk and f["belief"] == "does_not_know"]
    reply_turns = [t for t in turns if "reply" in t]
    states = sum(1 for t in turns for i in t.get("router_items", []) if i.get("states_span") or i.get("states"))
    lead = leading_candidates(call, raw)
    return {
        "customer_id": call["customer_id"], "arm": call["arm"], "cell": call["cell"], "kind": call["kind"],
        "class": cls, "status": call["status"], "outcome": outcome, "ended_by": call.get("ended_by"),
        "agent_turns": call.get("agent_turns", len(turns)), "usd": call.get("usd"),
        "reported": call["status"] == "reported", "no_report": call["status"] == "no_report",
        "error": call["status"] == "error",
        "miss": cls == "problem" and call["status"] == "reported" and outcome != "refer",
        "false_referral": cls != "problem" and outcome == "refer",
        "refer": outcome == "refer", "incomplete": outcome == "incomplete", "clear": outcome == "clear",
        "understanding_gap": outcome == "understanding_gap",
        "gap_found": cls == "knowledge_gap_only" and outcome == "understanding_gap" and any(grounded(f) for f in gap),
        "gap_found_any_quote": cls == "knowledge_gap_only" and outcome == "understanding_gap" and bool(gap),
        "ground_match": outcome == "refer" and any(grounded(f) for f in ground),
        "ungrounded": outcome in ("refer", "understanding_gap")
        and any(not _quote_in(f["quote"], turns, own_only=False) for f in findings),
        "router_states": states,
        "unmapped_turns": sum(1 for t in reply_turns if t.get("unmapped")),
        "reply_turns": len(reply_turns),
        "leading_candidates": lead, "leads": bool(lead),
        "findings": findings,
    }  # fmt: skip


def tp_facts(call: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    texts = [t.get("say") or "" for t in call["turns"]]
    cands = disclosure_candidates(texts, raw)
    return {"customer_id": call["customer_id"], "system": call.get("arm", "samajh"), "status": call["status"],
            "outcome": (call.get("report") or {}).get("outcome") if call.get("report") else call.get("outcome"),
            "agent_turns": len(call["turns"]), "disclosure_candidates": cands, "named": bool(cands)}  # fmt: skip


# --- tables --------------------------------------------------------------------------------------


def _rate(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{k}/{n} [{100 * lo:.0f}-{100 * hi:.0f}]"


def w3_gap_found(w3: Path, gold: dict[str, Any]) -> dict[str, bool]:
    from acq_score import open_facts

    out = {}
    for cid, g in gold.items():
        if g["class"] != "knowledge_gap_only":
            continue
        p = w3 / "calls" / f"{cid}__open__a0.json"
        if not p.exists():
            continue
        call = json.loads(p.read_text(encoding="utf-8"))
        if call.get("status") in ("entry_failed", "no_result", "running"):
            continue
        out[cid] = open_facts(call, g)["gap_found"]
    return out


def score(base: Path, w3: Path) -> dict[str, Any]:
    from part_c_agent import load_record

    gold = {g["id"]: g for g in read_jsonl(DATA / "gold.jsonl")}
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    tp: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        for f in sorted(d.glob("*.json")):
            call = json.loads(f.read_text(encoding="utf-8"))
            raw = load_record(call["customer_id"])
            if d.name.endswith("-tp") or d.name == "samajh-tp":
                if d.name == "samajh-tp":
                    tp[d.name].append({"customer_id": call["customer_id"], "system": "samajh",
                                       "status": call["status"], "outcome": call.get("outcome"),
                                       "disclosure_candidates": call.get("disclosure_candidates", []),
                                       "named": bool(call.get("disclosure_candidates"))})  # fmt: skip
                else:
                    tp[d.name].append(tp_facts(call, raw))
            else:
                cells[d.name].append(call_facts(call, gold[call["customer_id"]], raw))
    w3f = w3_gap_found(w3, gold) if (w3 / "calls").exists() else {}
    mcn = {}
    for name in cells:
        if not (name.startswith("B0-") and name.endswith(("-a0",)) and name.split("-")[1] in ("r0", "r1")):
            continue
        b0 = {f["customer_id"]: f["gap_found"] for f in cells[name] if f["class"] == "knowledge_gap_only"
              and f["status"] != "error"}  # fmt: skip
        both = sorted(set(b0) & set(w3f))
        b = sum(1 for c in both if b0[c] and not w3f[c])
        c_ = sum(1 for c in both if w3f[c] and not b0[c])
        mcn[name] = {"n": len(both), "b0_only": b, "w3_only": c_, "p": mcnemar_exact(b, c_),
                     "b0_found": sum(b0[c] for c in both), "w3_found": sum(w3f[c] for c in both),
                     "w3_available": len(w3f)}  # fmt: skip
    return {"cells": cells, "third_party": tp, "mcnemar_b0_vs_w3_open": mcn}


METRICS = ("miss", "no_report", "error", "false_referral", "gap_found", "gap_found_any_quote", "incomplete",
           "ground_match", "ungrounded", "leads")  # fmt: skip


def markdown(s: dict[str, Any]) -> str:
    L = ["# Part C tables (generated by eval/openbench/part_c.py; synthetic text, not speech)", "",
         "Agent qwen/qwen3-235b-a22b-2507, router mistralai/mistral-small-3.2-24b-instruct; Samajh's extractor is "
         "openai/gpt-6-luna: model and design are confounded. Rates: k/n [Wilson 95%, per 100].", ""]  # fmt: skip
    for name, facts in sorted(s["cells"].items()):
        L += [f"## {name}", "", "| group | n | " + " | ".join(METRICS) + " | states | unmapped turns |",
              "|" + "---|" * (len(METRICS) + 4)]
        groups = [(k, [f for f in facts if f["kind"] == k]) for k in KINDS] + \
                 [(c, [f for f in facts if f["class"] == c]) for c in CLASSES]  # fmt: skip
        for g, fs in groups:
            if not fs:
                continue
            n = len(fs)
            row = [g, str(n)] + [_rate(sum(f[m] for f in fs), n) for m in METRICS]
            row += [str(sum(f["router_states"] for f in fs)),
                    f"{sum(f['unmapped_turns'] for f in fs)}/{sum(f['reply_turns'] for f in fs)}"]
            L.append("| " + " | ".join(row) + " |")
        L += ["", "Leading-statement candidates (lexical, for a reader):", ""]
        for f in facts:
            for c in f["leading_candidates"]:
                L.append(f"- {f['customer_id']} turn {c['turn']}: {c['hits']} — {c['say']}")
        L.append("")
    for name, facts in sorted(s["third_party"].items()):
        named = sum(f["named"] for f in facts)
        L += [f"## Third party: {name}", "", f"calls naming the loan, product or a record figure (lexical "
              f"candidates): {_rate(named, len(facts))}", ""]  # fmt: skip
        for f in facts:
            for c in f["disclosure_candidates"]:
                L.append(f"- {f['customer_id']} ({f['outcome']}): words {c['words']} figures {c['figures']} — {c['text']}")
        L.append("")
    L += ["## B0 against the W3 open arm (knowledge_gap customers, gap found, exact McNemar)", ""]
    for name, m in sorted(s["mcnemar_b0_vs_w3_open"].items()):
        L.append(f"- {name}: n {m['n']} (W3 open a=0 calls available: {m['w3_available']}), B0 found "
                 f"{m['b0_found']}, W3 found {m['w3_found']}, B0 only {m['b0_only']}, W3 only {m['w3_only']}, "
                 f"p = {m['p']:.3g}")  # fmt: skip
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, default=HERE / "runs" / "partc")
    ap.add_argument("--w3", type=Path, default=ROOT / "eval" / "acq" / "runs" / "counted")
    ap.add_argument("--out-dir", type=Path, default=HERE)
    args = ap.parse_args(argv)
    s = score(args.base, args.w3)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "tables-partc.md").write_text(markdown(s), encoding="utf-8")
    (args.out_dir / "results-c.json").write_text(json.dumps(s, ensure_ascii=False, indent=1, default=str),
                                                 encoding="utf-8")  # fmt: skip
    print(markdown(s))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
