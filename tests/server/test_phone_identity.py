"""The phone's identity picker: `identityRequest` and `identityDescription` in web/phone.js, cut out of the
file and run under Node (the rest of phone.js needs a browser), against the server's real menu and the
session route's validation. The page itself (layout, the notice card) is checked in headless Chrome only
when `tests/server/browser_check.mjs` is run by hand."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from serverkit import FakeSpeech
from test_identity_server import phone_for

from samajh.identity import parse_policy

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not on PATH")

WEB = Path(__file__).resolve().parents[2] / "web"


def _function(name: str) -> str:
    found = re.search(
        rf"^function {name}\(.*?^\}}$",
        (WEB / "phone.js").read_text(encoding="utf-8"),
        re.MULTILINE | re.DOTALL,
    )
    assert found, f"no top-level function {name} in phone.js"
    return found.group(0)


def run(name: str, *args: object) -> object:
    call = ", ".join(json.dumps(a) for a in args)
    script = f"{_function(name)}\nprocess.stdout.write(JSON.stringify({name}({call})));"
    done = subprocess.run([NODE, "-e", script], check=False, capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@pytest.mark.parametrize(
    ("check", "attempts", "defaults", "wanted"),
    [
        ("none", 1, None, {"second_check": "none", "attempts": 1}),
        ("none", 2, None, {"second_check": "none", "attempts": 1}),  # attempts only with a check
        ("year_of_birth", 2, None, {"second_check": "year_of_birth", "attempts": 2}),
        ("year_of_birth", 7, None, {"second_check": "year_of_birth", "attempts": 1}),
        ("pin_code", 1, None, {"second_check": "none", "attempts": 1}),  # never outside the menu
        (
            "year_of_birth",
            1,
            {"prior_notice": False, "call_back_line": True},
            {"second_check": "year_of_birth", "attempts": 1, "prior_notice": False, "call_back_line": True},
        ),
    ],
)
def test_the_request_is_always_inside_the_menu(check, attempts, defaults, wanted) -> None:
    body = run("identityRequest", check, attempts, defaults)
    assert body == wanted
    parse_policy(body)  # the server's own check accepts it


def test_the_description_is_the_servers_for_each_choice(fake: FakeSpeech, tmp_path: Path) -> None:
    phone = phone_for(fake, tmp_path / "state")
    menu = phone.get("/api/identity/menu").json()
    none, year = menu["options"]
    assert run("identityDescription", menu, "none", 2) == none["descriptions"]["1"]
    assert run("identityDescription", menu, "year_of_birth", 2) == year["descriptions"]["2"]
    assert run("identityDescription", menu, "year_of_birth", 1) == year["descriptions"]["1"]
    assert run("identityDescription", None, "none", 1) is None


def test_the_page_sends_the_picker_with_the_session_and_shows_the_mocked_card() -> None:
    page = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "phone.js").read_text(encoding="utf-8")
    assert (
        'id="identity-check"' in page and 'value="year_of_birth"' in page and 'id="identity-attempts"' in page
    )
    assert "SMS, mocked: not sent" in page and 'id="notice-card"' in page
    assert "api.createSession({ line_rate: call.settings.lineRate, params, identity })" in script
