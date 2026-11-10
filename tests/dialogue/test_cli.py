"""`python -m samajh.dialogue play`: a call typed in the terminal."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from dialogue_kit import CUSTOMERS

from samajh.dialogue.__main__ import main
from samajh.types import Language, Transcript

RECORD = str(Path(__file__).parent / "fixtures" / "record_gold_loan.json")


def typed(monkeypatch, replies: list[str]) -> None:
    waiting = iter(replies)

    def fake_input(prompt: str = "") -> str:
        try:
            reply = next(waiting)
        except StopIteration:
            raise EOFError from None
        print(f"{prompt}{reply}")
        return reply

    monkeypatch.setattr("builtins.input", fake_input)


@pytest.mark.parametrize("language", list(Language))
def test_play_runs_a_whole_call_and_writes_the_transcript(language, monkeypatch, capsys, tmp_path):
    typed(monkeypatch, CUSTOMERS[language].happy())
    out = tmp_path / "call.json"
    code = main(["play", "--record", RECORD, "--lang", language.value, "--out", str(out)])

    printed = capsys.readouterr().out
    assert code == 0
    assert "[call ended: completed; unresolved questions: 0]" in printed
    assert "BOT  [right_party_check]" in printed and "BOT  [read_back/premium]" in printed
    transcript = Transcript.model_validate(json.loads(out.read_text(encoding="utf-8")))
    assert transcript.language is language and transcript.loan_id == "LN-DEMO-0001"


def test_play_reports_when_typing_stops_before_the_call_ends(monkeypatch, capsys):
    typed(monkeypatch, CUSTOMERS[Language.hi].happy()[:3])
    assert main(["play", "--record", RECORD, "--lang", "hi"]) == 1
    assert "input ended before the call did" in capsys.readouterr().out


def test_play_shows_the_review_label_of_the_language(monkeypatch, capsys):
    typed(monkeypatch, [CUSTOMERS[Language.ta].wrong_person])
    assert main(["play", "--record", RECORD, "--lang", "ta"]) == 0
    printed = capsys.readouterr().out
    assert "not human-reviewed" in printed and "[call ended: wrong_party" in printed


def test_a_turn_typed_as_two_transcripts_is_heard_twice(monkeypatch, capsys):
    replies = CUSTOMERS[Language.hi].happy()
    replies[5] = "bavan hazaar || 52,000"  # the premium answer; the parser refuses the first transcript
    typed(monkeypatch, replies)
    assert main(["play", "--record", RECORD, "--lang", "hi"]) == 0
    printed = capsys.readouterr().out
    assert printed.count("BOT  [teach_back/premium]") == 1  # not asked again
    assert "52,000। क्या यह सही है?" in printed and "unresolved questions: 0" in printed
