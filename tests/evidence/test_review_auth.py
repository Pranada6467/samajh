"""The review API behind a reviewer token, the 16 KiB body bound and the reviewer CLI."""

from __future__ import annotations

import os
import shutil
import stat
import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))  # serverkit.FakeSpeech
from serverkit import FakeSpeech

from samajh.ops import reviewers
from samajh.ops.__main__ import main
from samajh.ops.store import OpsStore
from samajh.server import create_app


@pytest.fixture(scope="module")
def demo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    state = tmp_path_factory.mktemp("demo")
    assert main(["demo", "--state", str(state)]) == 0
    return state


@pytest.fixture
def state(demo: Path, tmp_path: Path) -> Path:
    return Path(shutil.copytree(demo, tmp_path / "state"))


def _client(state: Path) -> TestClient:
    return TestClient(create_app(gnani=FakeSpeech(), state=state, web_dir=None, clips_dir=None))


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _first_case(client: TestClient, headers: dict[str, str]) -> dict:
    case_id = client.get("/api/review/queue", headers=headers).json()["items"][0]["case_id"]
    return client.get(f"/api/review/cases/{case_id}", headers=headers).json()


def test_no_reviewers_file_says_nobody_is_set_up(state: Path) -> None:
    reply = _client(state).get("/api/review/batch", headers=_bearer("anything"))
    assert reply.status_code == 401
    assert "no reviewer is set up" in reply.json()["error"]["message"]


@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer wrong-token"}, {"Authorization": "Basic x"}]
)
def test_a_missing_or_unknown_token_is_refused_without_echoing_it(state: Path, headers) -> None:
    reviewers.add(state / "ops", "Asha")
    for path in ("batch", "queue", "attempts", "draws", "report", "whoami"):
        reply = _client(state).get(f"/api/review/{path}", headers=headers)
        assert reply.status_code == 401, path
        message = reply.json()["error"]["message"]
        assert "reviewer add" in message and "wrong-token" not in reply.text


def test_the_right_token_signs_in_and_names_the_reviewer(state: Path) -> None:
    token = reviewers.add(state / "ops", "Asha")
    client = _client(state)
    assert client.get("/api/review/whoami", headers=_bearer(token)).json() == {"reviewer": "Asha"}
    assert client.get("/api/review/batch", headers=_bearer(token)).status_code == 200


def test_the_recorded_reviewer_is_the_token_name_whatever_the_body_says(state: Path) -> None:
    token = reviewers.add(state / "ops", "Asha")
    client = _client(state)
    case = _first_case(client, _bearer(token))
    body = {
        "decision": "call_customer",
        "note": "n",
        "reviewer": "Somebody Else",
        "case_digest": case["case_digest"],
    }
    reply = client.post(f"/api/review/cases/{case['case_id']}/disposition", json=body, headers=_bearer(token))
    assert reply.status_code == 200, reply.text
    stored = OpsStore(state / "ops").dispositions()[0]
    assert (stored.reviewer, stored.reviewer_auth) == ("Asha", "token")
    assert stored.case_digest == case["case_digest"]
    shown = reply.json()["disposition"]
    assert shown["reviewer"] == "Asha" and shown["reviewer_auth"] == "token"


def test_a_stale_case_digest_gives_409_and_nothing_is_appended(state: Path) -> None:
    token = reviewers.add(state / "ops", "Asha")
    client = _client(state)
    case = _first_case(client, _bearer(token))
    body = {"decision": "call_customer", "note": "n", "case_digest": "f" * 64}
    reply = client.post(f"/api/review/cases/{case['case_id']}/disposition", json=body, headers=_bearer(token))
    assert reply.status_code == 409
    assert reply.json()["error"]["message"] == "the case has changed since it was opened: reload it"
    assert OpsStore(state / "ops").dispositions() == ()


def test_a_body_over_16_kib_is_refused(state: Path) -> None:
    token = reviewers.add(state / "ops", "Asha")
    client = _client(state)
    case = _first_case(client, _bearer(token))
    url = f"/api/review/cases/{case['case_id']}/disposition"
    big = b'{"note": "' + b"x" * (17 * 1024) + b'"}'
    assert client.post(url, content=big, headers=_bearer(token)).status_code == 413

    def chunks():  # no Content-Length: the stream itself is cut off
        for _ in range(20):
            yield b"x" * 1024

    assert client.post(url, content=chunks(), headers=_bearer(token)).status_code == 413
    assert OpsStore(state / "ops").dispositions() == ()


def test_a_removed_reviewer_can_no_longer_sign_in(state: Path) -> None:
    token = reviewers.add(state / "ops", "Asha")
    reviewers.add(state / "ops", "Ravi")
    assert reviewers.remove(state / "ops", "Asha")
    assert _client(state).get("/api/review/whoami", headers=_bearer(token)).status_code == 401


def test_the_reviewer_cli_adds_lists_and_removes(state: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["reviewer", "add", "Asha", "--state", str(state)]) == 0
    token = capsys.readouterr().out.strip().splitlines()[-1]
    path = state / "ops" / "reviewers.json"
    assert token not in path.read_text() and stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert _client(state).get("/api/review/whoami", headers=_bearer(token)).json() == {"reviewer": "Asha"}

    assert main(["reviewer", "list", "--state", str(state)]) == 0
    assert capsys.readouterr().out.split() == ["Asha"]
    assert main(["reviewer", "remove", "Asha", "--state", str(state)]) == 0
    assert main(["reviewer", "remove", "Asha", "--state", str(state)]) == 1
    capsys.readouterr()
    assert main(["reviewer", "list", "--state", str(state)]) == 0
    assert capsys.readouterr().out == ""
