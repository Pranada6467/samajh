"""ACQ player and runner: the closed rule, the shared draw, the open variant choice, entry, the frozen check."""

from __future__ import annotations

import json

import pytest
from acq_common import FIELDS, read_jsonl, u, DATA
from acq_player import closed_answers, closed_outcomes, choose_open, entry_reply, load_topic_fields
from acq_run import P5_FILES, FrozenMismatch, check_frozen, drive_open, make_frozen, plan_calls, preflight, run_closed
from player import BotLineView, Said
from text_run import RecordingInterpreter

from samajh.dialogue import RuleInterpreter

TOPIC_FIELDS = load_topic_fields()
CUSTOMERS = {c["id"]: c for c in read_jsonl(DATA / "customers.jsonl")}


def _customer(states: dict[str, str], cid: str = "ACQ-T001", gender: str = "m") -> dict:
    return {"id": cid, "gender": gender, "belief": {f: {"state": states.get(f, "correct")} for f in FIELDS}}


def _knowledge() -> dict:
    return {"replies": {t: {v: f"{t}:{v}" for v in ("own", "again", "defer")} for t in TOPIC_FIELDS}}


def _ans(customer, r, a):
    return {x["field"]: x["answer"] for x in closed_answers(customer, r, a)}


@pytest.mark.parametrize("r", [0.0, 0.5, 1.0])
@pytest.mark.parametrize("a", [0.0, 0.5, 1.0])
def test_closed_rule_each_state(r, a):
    c = _customer({"premium": "false", "cover": "dk"})
    got = _ans(c, r, a)
    ua, ur = u(c["id"], "premium", "a"), u(c["id"], "cover", "r")
    assert got["premium"] == ("yes" if ua < a else "no")
    assert got["cover"] == ("yes" if ur < r else "dont_know")
    assert all(got[f] == "yes" for f in FIELDS if f not in ("premium", "cover"))


def test_closed_extremes_and_outcomes():
    c = _customer({"premium": "false", "cover": "dk"})
    at0 = closed_answers(c, 0.0, 0.0)
    assert closed_outcomes(at0) == {"outcome_strict": "caught", "caught_fields_strict": ["premium", "cover"],
                                    "outcome_lenient": "caught", "caught_fields_lenient": ["premium"]}
    at1 = closed_answers(c, 1.0, 1.0)  # draws are < 1, so everyone goes along
    assert closed_outcomes(at1)["outcome_strict"] == "confirmed"
    only_dk = closed_answers(_customer({"cover": "dk"}), 0.0, 0.0)
    assert closed_outcomes(only_dk)["outcome_lenient"] == "confirmed"
    assert closed_outcomes(only_dk)["outcome_strict"] == "caught"


def test_closed_file_follows_statement_order():
    cid = "ACQ-C002"
    gold = {g["id"]: g for g in read_jsonl(DATA / "gold.jsonl")}[cid]
    st = {s["id"]: s for s in read_jsonl(DATA / "closed_statements.jsonl")}[cid]
    rec = run_closed(CUSTOMERS[cid], gold, st, 0.0, 0.0)
    assert [x["field"] for x in rec["answers"]] == [s["field"] for s in st["statements"]]
    assert rec["answers"][0]["statement"] == st["statements"][0]["text"]


def _line(key):
    return [BotLineView(key=key, text="…")]


def test_same_draw_drives_open_defer_and_closed_yes():
    c = _customer({"premium": "false"})
    ua = u(c["id"], "premium", "a")
    for a in (0.0, 0.25, 0.5, 0.75, 1.0):
        ch = choose_open(c, _knowledge(), TOPIC_FIELDS, a, _line("premium.ask"), [])
        closed_yes = _ans(c, 0.0, a)["premium"] == "yes"
        assert (ch.variant == "defer") == closed_yes == (ua < a)


def test_open_variant_choice():
    c, k = _customer({}), _knowledge()
    assert choose_open(c, k, TOPIC_FIELDS, 0.0, _line("premium.ask"), []).text == "how_much:own"
    assert choose_open(c, k, TOPIC_FIELDS, 0.0, _line("premium.reask"), []).variant == "again"
    assert choose_open(c, k, TOPIC_FIELDS, 0.0, _line("cover.say_again"), []).variant == "again"
    hist = [Said("how_much", "own", "how_much:own")]
    assert choose_open(c, k, TOPIC_FIELDS, 0.0, _line("premium.ask"), hist).variant == "again"
    assert choose_open(c, k, TOPIC_FIELDS, 1.0, _line("premium.reask"), hist).variant == "defer"
    # borrowed and canned topics
    wrong = choose_open(c, k, TOPIC_FIELDS, 0.0, _line("read_back.restate"), [])
    assert (wrong.topic, wrong.text) == ("what_is_right_amount", "how_much:again")
    assert choose_open(c, k, TOPIC_FIELDS, 1.0, _line("read_back.restate"), []).text == "how_much:defer"
    odd = choose_open(c, k, TOPIC_FIELDS, 0.0, _line("second_check.ask"), [])
    assert not odd.mapped and odd.text == "जी, समझ नहीं आया।"
    assert choose_open(c, k, TOPIC_FIELDS, 0.0, _line("no.such.key"), []).mapped is False


@pytest.mark.parametrize("gender", ["m", "f"])
def test_entry_reaches_open_recall_on_every_record(gender):
    for cid, row in CUSTOMERS.items():
        customer = row | {"gender": gender}
        record = {"turns": [], "unmapped": []}
        rule = RecordingInterpreter(RuleInterpreter())
        drive_open(record, customer, None, TOPIC_FIELDS, 0.0, rule, rule, entry_only=True)
        assert record.get("status") != "entry_failed", (cid, record.get("entry_failed_at"))
        assert record["scored_from_turn"] == len(record["turns"]) == 3
        first = row["record_id"]
        name = json.loads((DATA / "records" / f"{first}.json").read_text())["record"]["borrower"]["name"].split()[0]
        assert all(name not in t["reply"]["text"] for t in record["turns"])
    assert "रही" in entry_reply("right_party.reask", "f") and "रहा" in entry_reply("right_party.reask", "m")


def _tree(root):
    for rel in ("samajh/x.py", "data/prompts/hi.toml", "data/acq/gold.jsonl", "data/acq/records/r.json",
                "eval/acq/acq_run.py", *P5_FILES):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(rel)


def test_frozen_check_refuses_any_change(tmp_path):
    _tree(tmp_path)
    frozen_path = tmp_path / "data" / "acq" / "FROZEN.json"

    def freeze():
        frozen_path.write_text(json.dumps(make_frozen(tmp_path)))

    freeze()
    assert check_frozen(frozen_path, tmp_path)["files"]["data/acq/gold.jsonl"]
    for rel in ("data/acq/gold.jsonl", "data/acq/records/r.json", "samajh/x.py", "eval/p5/player.py"):
        before = (tmp_path / rel).read_text()
        (tmp_path / rel).write_text(before + " ")
        with pytest.raises(FrozenMismatch):
            check_frozen(frozen_path, tmp_path)
        (tmp_path / rel).write_text(before)
    check_frozen(frozen_path, tmp_path)
    (tmp_path / "data" / "acq" / "knowledge.jsonl").write_text("{}")  # a new, unlisted data file
    with pytest.raises(FrozenMismatch):
        check_frozen(frozen_path, tmp_path)
    frozen_path.unlink()
    with pytest.raises(FrozenMismatch):
        check_frozen(frozen_path, tmp_path)


def test_preflight_and_customer_major_plan():
    assert preflight(CUSTOMERS, TOPIC_FIELDS) == []
    broken = {"ACQ-C001": CUSTOMERS["ACQ-C001"] | {"gender": "m", "record_id": "no-such-record"}}
    assert preflight(broken, TOPIC_FIELDS) == ["ACQ-C001"]
    assert plan_calls(["A", "B"], [0.0, 1.0]) == [("A", 0.0), ("A", 1.0), ("B", 0.0), ("B", 1.0)]


def test_open_recall_under_premium_defer():
    # find a customer whose kind draw is high and premium draw low, so at a between them premium defers only
    cid = next(c for c in CUSTOMERS if u(c, "premium", "a") < u(c, "kind", "a"))
    a = (u(cid, "premium", "a") + u(cid, "kind", "a")) / 2
    c = _customer({}, cid=cid)
    ch = choose_open(c, _knowledge(), TOPIC_FIELDS, a, _line("open_recall.ask"), [])
    assert (ch.recall_rule, ch.text, ch.field) == ("what_is_it_for_premium_defer", "what_is_it:own", "kind")
    assert choose_open(c, _knowledge(), TOPIC_FIELDS, 0.0, _line("open_recall.ask"), []).recall_rule == "own_recall"
    full = choose_open(c, _knowledge(), TOPIC_FIELDS, 1.0, _line("open_recall.ask"), [])
    assert (full.recall_rule, full.variant) == ("defer", "defer")


def test_anything_else_answers_with_the_recall_reply():
    c = _customer({})
    ch = choose_open(c, _knowledge(), TOPIC_FIELDS, 0.0, _line("open_recall.nothing"), [])
    assert (ch.topic, ch.text, ch.recall_rule) == ("anything_else", "what_did_you_take:again", "own_recall")
    assert choose_open(c, _knowledge(), TOPIC_FIELDS, 1.0, _line("open_recall.nothing"), []).variant == "defer"
