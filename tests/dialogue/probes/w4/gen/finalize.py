"""Turn the written replies into the frozen banks with the checker's gold labels. Every manual change is listed here."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANKS = HERE.parent / "banks"


def load(name):
    return [json.loads(x) for x in (HERE / f"written-{name}.jsonl").read_text().splitlines() if x.strip()]


def dump(name, rows):
    path = BANKS / f"{name}.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---- A
AMBIG_A = {"A-057": "borrower says 'मनोज शायद बोल रहा हूँ' (maybe Manoj speaking)"}
a = []
for r in load("A"):
    row = {k: r[k] for k in ("id", "kind", "subkind", "first_name", "spoken_dev", "spoken_variant", "region", "language",
                             "replies", "writer_model", "accepted_residual", "event_turn")}
    row["bot_questions_shown"] = r["bot_questions"]
    row["ambiguous"] = r["id"] in AMBIG_A
    if row["ambiguous"]:
        row["ambiguous_why"] = AMBIG_A[r["id"]]
    if r["kind"] == "borrower":
        row["gold"] = "pass"
    elif r["kind"] == "third_party":
        row["gold"] = "not_pass"
        row["other_name"] = r.get("other_name")
    elif r["kind"] == "refusal":
        row["gold"] = r["gold"]  # the specific outcome expected; any of declined/do_not_call/human/call_back counts
        row["event_position"] = r["event_position"]
    elif r["kind"] == "call_back":
        row["gold"] = "call_back_later"
        row["event_position"] = r["event_position"]
    elif r["kind"] == "language":
        row["gold"] = r["gold"]
        row["requested"] = r["requested"]
        row["has_file"] = r["has_file"]
        row["inside_yes"] = r["inside_yes"]
        row["event_position"] = r["event_position"]
    a.append(row)

# ---- B
RELABEL_B = {"B-016": {"what": False, "how": True}}  # 'documents bhi sign kiye the' names a way of agreeing
b = []
for r in load("B"):
    halves = RELABEL_B.get(r["id"], r["halves"])
    if r["slot"] == "consent":
        missing = [h for h in ("what", "how") if not halves[h]]
    else:
        missing = [h for h in ("what", "does") if not halves[h]]
    partial = r["subkind"] in ("how_only", "what_only", "figure_only", "does_only", "kind_only") or r["id"] in RELABEL_B
    b.append({
        "id": r["id"], "slot": r["slot"], "subkind": r["subkind"], "language": r["language"], "first": r["first"],
        "followup": r["followup"], "writer_model": r["writer_model"], "halves": halves, "missing": missing,
        "followup_needed": partial, "ambiguous": False,
        "note": "relabelled by checker" if r["id"] in RELABEL_B else None,
    })

# ---- C
TALK = {"hi": ("हाँ जी, पूछिए", "नहीं नहीं, अभी बात कर लीजिए"), "hi-en": ("haan ji, poochiye", "nahi nahi, abhi baat kar lo")}
FIX_COND = {"C-032", "C-033", "C-034", "C-035", "C-036", "C-064", "C-065", "C-066", "C-017"}  # writer gave 'stop' replies
FIX_REASK = {"C-037", "C-039", "C-040", "C-042", "C-050", "C-051", "C-052", "C-053", "C-054"}  # writer asked the bot back
c = []
for r in load("C"):
    edits = []
    s, w = TALK[r["language"]]
    if_stop, if_when, if_reask = r["if_stop_check"], r["if_when"], r["if_reask"]
    if r["id"] in FIX_COND:
        if_stop, if_when = s, w
        edits.append("if_stop_check and if_when replaced by the checker (writer wrote a stop for a willing customer)")
    if r["id"] in FIX_REASK:
        if_reask = r["first"]
        edits.append("if_reask replaced by the first reply (writer wrote a question back to the bot)")
    c.append({
        "id": r["id"], "group": r["group"], "subkind": r["subkind"], "slot": r["slot"], "language": r["language"],
        "first": r["first"], "if_reask": if_reask, "if_stop_check": if_stop, "if_when": if_when,
        "writer_model": r["writer_model"], "gold": r["gold"], "ambiguous": False, "checker_edits": edits,
    })

# ---- Y: year-of-birth probe (hand-written by the checker; record dob 1984-06-15)
Y_NAMES = [("Ramesh", "hi"), ("Kavitha", "hi"), ("Imran", "hi-en"), ("Gurpreet", "hi"), ("Joseph", "hi-en"),
           ("Lakshmi", "hi"), ("Tomba", "hi-en"), ("Sourav", "hi"), ("Hetal", "hi-en"), ("Venkatesh", "hi")]
Y_YEARS = ["उन्नीस सौ चौरासी", "1984", "84 में पैदा हुआ था", "nineteen eighty four", "चौरासी", "saal 1984 hai",
           "उन्नीस सौ चौरासी का हूँ", "1984 hai ji", "eighty four", "जी 1984"]
y = [{"id": f"Y-{i + 1:02d}", "first_name": n, "language": lang, "year_reply": Y_YEARS[i],
      "self_claim": "हाँ, मैं ही हूँ" if lang == "hi" else "haan ji, main hi hoon", "writer_model": "checker (hand-written)"}
     for i, (n, lang) in enumerate(Y_NAMES)]

if __name__ == "__main__":
    BANKS.mkdir(exist_ok=True)
    for name, rows in (("A-openings", a), ("B-half-answers", b), ("C-midcall", c), ("Y-birth-year", y)):
        print(name, len(rows), dump(name, rows))
