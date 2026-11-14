"""The ACQ customer set: deterministic build, balanced counts, gold agrees with the engine, writer independence."""

import inspect
import json
import re
from collections import Counter

import pytest
from acq_build import FILES, build
from acq_common import DATA, FIELDS, FLAG_FIELD
from acq_write import build_messages

from samajh.amounts import spoken_amount
from samajh.server.records import CallRecord
from samajh.types import FlagReason, Language

DIGIT = re.compile(r"[0-9०-९]")


@pytest.fixture(scope="module")
def built():
    out, exclusions = build()
    rows = lambda name: [json.loads(x) for x in out[DATA / name].splitlines()]  # noqa: E731
    return {"out": out, "exclusions": exclusions, "customers": rows("customers.jsonl"), "gold": rows("gold.jsonl"),
            "topics": json.loads(out[DATA / "topics.json"]), "closed": rows("closed_statements.jsonl")}


def test_build_is_deterministic(built):
    again, _ = build()
    assert again == built["out"]


def test_built_files_match_disk(built):
    for path, text in built["out"].items():
        assert path.read_text(encoding="utf-8") == text, path


def test_all_records_validate(built):
    records = [CallRecord.model_validate_json(t) for p, t in built["out"].items() if p.parent.name == "records"]
    assert len(records) == 160
    for r in records:
        p = r.record.products[0]
        assert p.cover_inr == r.record.sanctioned_inr and p.term_months == r.record.tenure_months
        assert r.record.disbursed_inr == r.record.sanctioned_inr - (p.premium_inr if p.paid_from_loan else 0)
        assert r.record.loan_id.startswith("TEST-ACQ-LN-") and r.record.borrower.name.endswith(" Namoona")


def test_counts(built):
    c = built["customers"]
    assert Counter(x["kind"] for x in c) == {"informed": 32, "knowledge_gap": 48, "misled": 40, "misled_with_gaps": 40}
    cells = Counter((x["kind"], x["language"], x["writer_model"]) for x in c)
    assert len(cells) == 16
    for (kind, _, _), n in cells.items():
        assert n * 4 == dict(informed=32, knowledge_gap=48, misled=40, misled_with_gaps=40)[kind]
    genders = Counter((x["kind"], x["language"], x["writer_model"], x["gender"]) for x in c)
    assert all(genders[(*k, "f")] == genders[(*k, "m")] for k in cells)


def test_belief_states_per_kind(built):
    for x in built["customers"]:
        st = {f: x["belief"][f]["state"] for f in FIELDS}
        n_false, n_dk = sum(s == "false" for s in st.values()), sum(s == "dk" for s in st.values())
        assert {"informed": (n_false, n_dk) == (0, 0), "knowledge_gap": n_false == 0 and 1 <= n_dk <= 3,
                "misled": 1 <= n_false <= 2 and n_dk == 0,
                "misled_with_gaps": 1 <= n_false <= 2 and 1 <= n_dk <= 2}[x["kind"]], x["id"]
        assert all(st[f] != "dk" for f in ("kind", "source", "required", "consent"))
        assert st["consent"] == "correct"


def test_gold_agrees_with_engine(built):
    assert built["exclusions"] == []
    want = {"no_problem": "clear", "knowledge_gap_only": "understanding_gap", "problem": "refer"}
    for g in built["gold"]:
        assert g["engine_tier"] == want[g["class"]], g["id"]
        fields = {FLAG_FIELD[FlagReason(r)] for r in g["engine_flags"]}
        assert set(g["ground"]) <= fields, g["id"]


def test_flag_field_covers_every_reason():
    assert set(FLAG_FIELD) == set(FlagReason)
    assert set(FLAG_FIELD.values()) - {None} <= set(FIELDS)


def test_writer_request_takes_no_record():
    assert list(inspect.signature(build_messages).parameters) == ["customer", "topics"]


def test_writer_request_hides_record_figures(built):
    records = {p.stem: CallRecord.model_validate_json(t) for p, t in built["out"].items() if p.parent.name == "records"}
    checked = 0
    for x in built["customers"]:
        system, user = build_messages(x, built["topics"])
        assert not DIGIT.search(system + user), x["id"]
        p = records[x["record_id"]].record.products[0]
        for field, value in (("premium", p.premium_inr), ("cover", p.cover_inr)):
            if x["belief"][field]["state"] != "correct":
                checked += 1
                for lang in (Language.hi_en, Language.hi):
                    assert spoken_amount(value, lang) not in user, (x["id"], field)
    assert checked > 50


def test_topics_carry_no_digits_and_every_variant(built):
    t = built["topics"]
    assert not DIGIT.search(json.dumps(t, ensure_ascii=False))
    assert {x["field"] for x in t["open_call"]} == set(FIELDS)
    assert all(x["variants"] == ["own", "again", "defer"] for x in t["open_call"])


def test_closed_statements(built):
    assert len(built["closed"]) == 160
    for row in built["closed"]:
        assert [s["field"] for s in row["statements"]] == list(FIELDS)
        assert all(s["text"].endswith("क्या यह सही है?") and not DIGIT.search(s["text"]) for s in row["statements"])


def test_frozen_inputs_list_every_file():
    frozen = json.loads((DATA / "FROZEN_INPUTS.json").read_text())
    assert set(FILES) | {"records"} <= set(frozen) <= set(FILES) | {"records", "knowledge.jsonl", "writer_requests.jsonl"}
