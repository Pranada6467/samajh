"""The phone's case card notice for a call with a turn the classifier failed on: `voidNotice` in
web/phone.js, cut out of the file and run under Node (the rest of phone.js needs a browser). Where
the notice sits on the card (above the status line) is not checked by automation."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from samajh.ops.wording import banned_in

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not on PATH")

PHONE = Path(__file__).resolve().parents[2] / "web" / "phone.js"


def _function(name: str) -> str:
    found = re.search(
        rf"^function {name}\(.*?^\}}$", PHONE.read_text(encoding="utf-8"), re.MULTILINE | re.DOTALL
    )
    assert found, f"no top-level function {name} in phone.js"
    return found.group(0)


def notice(case_file: object) -> str | None:
    script = f"{_function('voidNotice')}\nprocess.stdout.write(JSON.stringify(voidNotice({json.dumps(case_file)})));"
    done = subprocess.run([NODE, "-e", script], check=False, capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def test_one_failed_turn_says_repeat_and_not_counted() -> None:
    text = notice({"status": "ready", "tier": "clear", "degraded_turns": [3]})
    assert text == (
        "Repeat this call: the classifier failed on 1 turn, so this session is not counted. "
        "That turn was read by the word lists alone."
    )


def test_two_failed_turns_are_counted_in_words() -> None:
    text = notice({"status": "running", "degraded_turns": [3, 7]})
    assert text is not None and text.startswith("Repeat this call: the classifier failed on 2 turns,")
    assert "Those turns were read by the word lists alone." in text and not banned_in(text)


@pytest.mark.parametrize("case_file", [{"degraded_turns": []}, {"status": "ready"}, None])
def test_no_notice_without_a_failed_turn_or_for_a_case_file_written_before_the_field(case_file) -> None:
    assert notice(case_file) is None
