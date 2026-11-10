"""What a referral rests on, on the phone's case card: the case file's summary carries
`referral_basis` and `first_line` (samajh.rules.CaseSummary, dumped by samajh/server/casefile.py
with no change of its own), and `basisText` in web/phone.js turns the basis into words. The JS
helper is cut out of the file and run under Node, as tests/server/test_phone_card.py does."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from serverkit import FakeSpeech
from test_casefile import phone_for, run_call, wait_case

from samajh.ops.wording import banned_in
from samajh.rules.summary import RECORD_ONLY_FIRST_LINE

NODE = shutil.which("node")
PHONE = Path(__file__).resolve().parents[2] / "web" / "phone.js"


def test_the_case_file_summary_carries_the_basis_and_the_first_line(fake: FakeSpeech, state: Path) -> None:
    """The hero record has no consent on record. The fake model fails every request, so nothing
    the customer said is decided: the referral rests on the record alone."""
    phone = phone_for(fake, state)
    sid = run_call(phone, fake)
    assert phone.post(f"/api/sessions/{sid}/case").status_code == 200
    case = wait_case(phone, sid)
    assert case["status"] == "ready", case["steps"]
    summary = case["summary"]
    assert summary["tier"] == "refer"
    assert summary["referral_basis"] == "record_only"
    # The open recall named nothing (`recall_not_named`, an understanding gap that rests on what the
    # customer said); the first line is still true: that is not the reason for the referral.
    flags = [f for p in case["result"]["products"] for f in p["flags"]] + case["result"]["case_flags"]
    assert sorted(f["reason"] for f in flags) == [
        "consent_no_record",
        "funded_no_consent",
        "recall_not_named",
    ]
    assert summary["first_line"] == RECORD_ONLY_FIRST_LINE
    refer = [line for line in summary["lines"] if line["tier"] == "refer"]
    assert refer and all(line["basis"] == "record_only" for line in refer)
    assert basis_text(case) == "on the record alone"


def _function(name: str) -> str:
    found = re.search(
        rf"^function {name}\(.*?^\}}$", PHONE.read_text(encoding="utf-8"), re.MULTILINE | re.DOTALL
    )
    assert found, f"no top-level function {name} in phone.js"
    return found.group(0)


def basis_text(case_file: object) -> str | None:
    if NODE is None:
        pytest.skip("node is not on PATH")
    script = (
        f"{_function('basisText')}\nprocess.stdout.write(JSON.stringify(basisText({json.dumps(case_file)})));"
    )
    done = subprocess.run([NODE, "-e", script], check=False, capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@pytest.mark.parametrize(
    ("basis", "words"),
    [("customer_statement", "on what the customer said"), ("record_only", "on the record alone")],
)
def test_the_basis_in_words(basis: str, words: str) -> None:
    text = basis_text({"status": "ready", "tier": "refer", "summary": {"referral_basis": basis}})
    assert text == words and not banned_in(text)


@pytest.mark.parametrize(
    "case_file",
    [
        {
            "status": "ready",
            "tier": "refer",
            "summary": {"tier": "refer", "lines": []},
        },  # written before the field
        {"status": "ready", "tier": "clear", "summary": {"tier": "clear", "lines": []}},
        {"status": "running"},
        None,
    ],
)
def test_no_basis_for_a_case_file_without_one(case_file) -> None:
    assert basis_text(case_file) is None
