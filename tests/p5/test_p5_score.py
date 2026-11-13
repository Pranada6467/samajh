"""The P5 scorer on hand-made call files (never on data/p5 outcomes)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from score import load_calls, markdown, paired, score

GOLD = {
    "P1": {"class": "problem", "kind": "misled", "expected_outcome": "completed"},
    "P2": {"class": "problem", "kind": "misled", "expected_outcome": "completed"},
    "P3": {"class": "problem", "kind": "misled", "expected_outcome": "completed"},
    "P4": {"class": "problem", "kind": "took_nothing", "expected_outcome": "completed"},
    "N1": {"class": "no_problem", "kind": "well_informed", "expected_outcome": "completed"},
    "G1": {"class": "knowledge_gap_only", "kind": "ordinary_informed", "expected_outcome": "completed"},
    "T1": {"class": "procedural", "kind": "third_party", "expected_outcome": "wrong_party"},
    "R1": {"class": "procedural", "kind": "refusal", "expected_outcome": "declined"},
}


def open_call(cid: str, tier: str | None, *, outcome: str = "completed", level: float = 0.0, basis=None,
              status: str = "ok", condition: str = "disposition", turns=None, final_bot=None) -> dict:  # fmt: skip
    return {"customer_id": cid, "arm": "open", "condition": condition, "level": level, "status": status,
            "tier": tier, "outcome": outcome, "referral_basis": basis, "writer_model": "w1",
            "turns": turns or [], "final_bot": final_bot or [], "unmapped": [], "degraded_turns": 0,
            "errors": [{"error": "RuntimeError('boom')"}] if status != "ok" else []}  # fmt: skip


def closed_call(cid: str, outcome: str, *, level: float = 0.0, status: str = "ok") -> dict:
    return {"customer_id": cid, "arm": "closed", "condition": "disposition", "level": level, "status": status,
            "outcome": outcome, "writer_model": "w1", "turns": [], "closed": [], "unmapped": [],
            "degraded_turns": 0, "errors": []}  # fmt: skip


def row(rows: list[dict], **match) -> dict:
    found = [r for r in rows if all(r[k] == v for k, v in match.items())]
    assert len(found) == 1, found
    return found[0]


def test_miss_catch_and_incomplete_apart() -> None:
    calls = [open_call("P1", "clear"), open_call("P2", "refer", basis="customer_statement"),
             open_call("P3", "incomplete"), open_call("P4", "understanding_gap")]  # fmt: skip
    result = score(calls, GOLD)
    misled = row(result["misses"], arm="open", kind="misled")
    assert (misled["n"], misled["caught"], misled["miss"], misled["incomplete"]) == (3, 1, 1, 1)
    assert row(result["misses"], arm="open", kind="took_nothing")["miss"] == 1  # a gap is a miss on a problem


def test_refer_counts_even_when_the_call_ended_early_and_other_early_ends_are_apart() -> None:
    calls = [open_call("P1", "clear", outcome="declined"), open_call("P2", "refer", outcome="declined")]
    misled = row(score(calls, GOLD)["misses"], kind="misled")
    assert (misled["ended_early"], misled["caught"], misled["miss"]) == (1, 1, 0)


def test_false_referral_by_gold_class() -> None:
    calls = [open_call("N1", "refer", basis="customer_statement"), open_call("G1", "understanding_gap")]
    result = score(calls, GOLD)
    assert row(result["referrals"], gold_class="no_problem")["referred"] == 1
    gap = row(result["referrals"], gold_class="knowledge_gap_only")
    assert (gap["referred"], gap["understanding_gap"]) == (0, 1)


def test_no_result_row_stays_and_is_not_in_the_denominator() -> None:
    calls = [open_call("P1", None, status="no_result"), open_call("P2", "clear")]
    result = score(calls, GOLD)
    misled = row(result["misses"], kind="misled")
    assert (misled["n"], misled["no_result"], misled["miss"]) == (1, 1, 1)
    assert [r["customer_id"] for r in result["no_result"]] == ["P1"]
    assert "boom" in markdown(result, "t")


def test_record_only_basis_is_split_out() -> None:
    calls = [
        open_call("N1", "refer", basis="record_only"),
        open_call("P1", "refer", basis="customer_statement"),
    ]
    split = score(calls, GOLD)["referral_basis"]
    assert row(split, gold_class="no_problem")["record_only"] == 1
    assert row(split, gold_class="problem")["customer_statement"] == 1


def test_closed_confirmed_is_the_miss_and_paired_discordance_at_level_0() -> None:
    calls = [
        open_call("P1", "refer", basis="customer_statement"), closed_call("P1", "closed_confirmed"),
        open_call("P2", "refer", basis="customer_statement"), closed_call("P2", "closed_confirmed"),
        open_call("P3", "clear"), closed_call("P3", "closed_not_confirmed"),
        open_call("P4", "refer", basis="customer_statement"), closed_call("P4", "closed_not_confirmed"),
    ]  # fmt: skip
    result = score(calls, GOLD)
    assert row(result["misses"], arm="closed", kind="misled")["miss"] == 2
    allkinds = row(result["paired_level0"], gold_class="problem", kind="all kinds")
    assert (allkinds["open_only"], allkinds["closed_only"], allkinds["both"]) == (2, 1, 1)
    assert allkinds["mcnemar_p"] == 1.0


def test_no_open_minus_closed_comparison_above_level_0() -> None:
    calls = [open_call("P1", "refer", level=0.5, basis="customer_statement"),
             closed_call("P1", "closed_confirmed", level=0.5)]  # fmt: skip
    result = score(calls, GOLD)
    assert result["paired_level0"] == []
    with pytest.raises(ValueError):
        paired(calls, GOLD, level=0.5)
    # each arm still has its own row at 0.5
    assert row(result["misses"], arm="open", level=0.5)["caught"] == 1
    assert row(result["misses"], arm="closed", level=0.5)["miss"] == 1


def test_terse_condition_is_reported_apart() -> None:
    result = score([open_call("P1", "clear", condition="terse"), open_call("P1", "refer")], GOLD)
    assert row(result["misses"], arm="open-terse")["miss"] == 1
    assert row(result["misses"], arm="open")["caught"] == 1


def test_opening_kinds_loan_named_and_refusal_asked_further() -> None:
    leak = open_call("T1", "incomplete", outcome="wrong_party",
                     turns=[{"bot": [{"key": "right_party.ask", "step": "right_party_check"}], "readings": []},
                            {"bot": [{"key": "context.loan", "step": "context"}], "readings": []}])  # fmt: skip
    pressed = open_call("R1", "incomplete", outcome="declined",
                        turns=[{"bot": [{"key": "disclosure.go_ahead", "step": "disclosure"}],
                                "readings": [{"intent": "maybe_decline"}]},
                               {"bot": [{"key": "stop_check.decline", "step": "close"}], "readings": [{"intent": "no"}]}])  # fmt: skip
    kinds = score([leak, pressed], GOLD)["opening_kinds"]
    third = row(kinds, kind="third_party")
    assert (third["reached"], third["loan_named"]) == (1, 1)
    refusal = row(kinds, kind="refusal")
    assert (refusal["reached"], refusal["asked_further"], refusal["asked_about_loan_after"]) == (1, 1, 0)


def test_reads_call_files_from_a_run_directory(tmp_path: Path) -> None:
    (tmp_path / "calls").mkdir()
    (tmp_path / "calls" / "P1__open__L0.json").write_text(json.dumps(open_call("P1", "clear")))
    assert score(load_calls(tmp_path), GOLD)["misses"][0]["miss"] == 1


# --- closed lenient reading and text against voice --------------------------------------------------

STATEMENT = "यह बीमा दो साल तक चलता है। क्या यह सही है?"
NEGATIVE = "यह बीमा कोई जमा या बचत नहीं है। क्या यह सही है?"
INTRO = "अब मैं आपको बताऊँगी। हर बात के बाद बताइए कि वह सही है या नहीं। "


def stmt(sid: str, reply: str, reading: str, bot: str = STATEMENT) -> dict:
    return {"statement_id": sid, "bot": bot, "reply": {"text": reply}, "reading": reading}


def closed_with(cid: str, statements: list[dict], level: float = 0.0) -> dict:
    call = closed_call(cid, "closed_confirmed" if all(s["reading"] == "yes" for s in statements)
                       else "closed_not_confirmed", level=level)  # fmt: skip
    call["closed"] = statements
    return call


@pytest.mark.parametrize(
    ("reply", "bot", "lenient"),
    [
        ("हाँ, दो साल का है।", STATEMENT, True),
        ("हाँ, पर मुझे नहीं पता।", STATEMENT, False),  # a negation, and the claim holds none
        ("हाँ, मैं जानती हूँ कि यह बचत नहीं है।", NEGATIVE, True),  # agrees with a negative claim
        ("हाँ, यह बचत नहीं है।", INTRO + NEGATIVE, True),  # the intro's "या नहीं" is not the claim
        ("जी नहीं, यह जमा है।", NEGATIVE, False),  # negation in the first two words
        ("मुझे लगता है हाँ।", STATEMENT, False),  # first word is not an affirmative
        ("yes, correct", STATEMENT, True),
    ],
)  # fmt: skip
def test_lenient_rule(reply: str, bot: str, lenient: bool) -> None:
    from score import lenient_yes

    assert lenient_yes(stmt("c_term", reply, "other", bot)) is lenient
    assert lenient_yes(stmt("c_term", "कुछ भी", "yes", bot)) is True  # the interpreter's yes always stands


def test_closed_both_readings_and_the_verbatim_list() -> None:
    calls = [
        closed_with("N1", [stmt("c_kind", "हाँ।", "yes"), stmt("c_not_savings", "हाँ, बचत नहीं है।", "no", NEGATIVE)]),
        open_call("N1", "clear"),
        closed_with("P1", [stmt("c_kind", "नहीं, एफडी है।", "no")]),
        open_call("P1", "refer", basis="customer_statement"),
    ]  # fmt: skip
    result = score(calls, GOLD)
    n1 = row(result["closed_readings"], kind="well_informed")
    assert (n1["confirmed_primary"], n1["confirmed_lenient"]) == (0, 1)
    assert row(result["closed_readings"], kind="misled")["confirmed_lenient"] == 0
    listed = result["closed_not_yes_without_problem"]
    assert [(r["customer_id"], r["statement_id"], r["reply"], r["reading"]) for r in listed] == [
        ("N1", "c_not_savings", "हाँ, बचत नहीं है।", "no")
    ]  # a problem customer's "no" is not listed
    primary = row(result["paired_level0"], gold_class="no_problem_or_gap", kind="all kinds")
    lenient = row(result["paired_level0_lenient"], gold_class="no_problem_or_gap", kind="all kinds")
    assert (primary["closed_only"], lenient["closed_only"], lenient["neither"]) == (1, 0, 1)
    md = markdown(result, "t")
    assert "Closed, lenient" in md and "हाँ, बचत नहीं है।" in md


def test_voice_tables_and_differences() -> None:
    text = [open_call("P1", "refer", basis="customer_statement"), open_call("N1", "clear"),
            open_call("T1", "incomplete", outcome="wrong_party")]  # fmt: skip
    voice = [dict(open_call("P1", "clear"), path="voice"), dict(open_call("N1", "clear"), path="voice")]
    result = score(text, GOLD, voice)
    assert row(result["voice"]["misses"], kind="misled")["miss"] == 1
    assert [d["customer_id"] for d in result["voice"]["differs"]] == ["P1"]
    assert result["voice"]["text_calls_without_voice"] == ["T1"]
    assert "V1. Misses" in markdown(result, "t")


def test_voice_files_must_say_voice() -> None:
    with pytest.raises(ValueError, match="path"):
        score([open_call("P1", "clear")], GOLD, [open_call("P1", "clear")])
