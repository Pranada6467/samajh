"""The two readings of a figure turn, through the HTTP route: v2.5 first when it has text.

The dialogue holds and reads back the first reading's figure where the two differ
(references/pilots/P2-contract.md section 5), so the order the server hands them in decides
which figure the customer hears read back. No network: the speech client is faked per model.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from serverkit import FakeSpeech, make_wav
from starlette.testclient import TestClient
from test_casefile import FailingLlm, wait_case
from test_samajh_dialogue import CUSTOMERS, answer

from samajh.clients.errors import ServerError
from samajh.server import create_app
from samajh.server.records import PACKAGED_DIR, load_book
from samajh.server.samajh_dialogue import call_state, samajh_factory
from samajh.server.sessionlog import CustomerEvent, SessionStore
from samajh.server.settings import load_settings
from samajh.types import Language

BOOK = load_book(PACKAGED_DIR)
SETTINGS = load_settings().model_copy(
    update={"fallback": load_settings().fallback.model_copy(update={"enabled": False})}
)
V30, V25 = "prisma-v3.0", "prisma-v2.5"
FIFTY_FIVE, FIFTY_TWO = "पचपन हज़ार", "बावन हज़ार"
CUSTOMERS_HI = CUSTOMERS[Language.hi]


def phone_for(fake: FakeSpeech, state: Path) -> TestClient:
    app = create_app(
        gnani=fake,
        state=state,
        web_dir=None,
        clips_dir=None,
        dialogues={"samajh": samajh_factory(BOOK, SETTINGS)},
        records=BOOK,
        settings=SETTINGS,
        llm=FailingLlm,
    )
    return TestClient(app)


def _asks_premium(bot: dict) -> bool:
    return bot["second_reading"] and bot["lines"][-1]["key"].startswith("premium.")


class Call:
    """One call on the hero record. Each turn is a new clip; `heard` says what each model reads."""

    def __init__(self, phone: TestClient, fake: FakeSpeech, state: Path) -> None:
        self.phone, self.fake, self.state = phone, fake, state
        created = phone.post("/api/sessions", json={"params": {"record": "hero", "language": "hi"}})
        assert created.status_code == 201, created.text
        self.sid, self.bot = created.json()["session_id"], created.json()["bot"]
        self.turns = 0

    def log(self):
        return SessionStore(self.state / "sessions").load(self.sid)

    def say(self, v30: str, v25: str | None = None) -> dict:
        self.fake.model_transcripts = {V30: [v30], V25: [v30 if v25 is None else v25]}
        clip = make_wav(0.5 + self.turns / 100, tone=300 + self.turns)
        self.turns += 1
        url = f"/api/sessions/{self.sid}/turns?source=file&reply_to={self.bot['seq']}"
        turn = self.phone.post(url, content=clip)
        assert turn.status_code == 200, turn.text
        self.bot = turn.json()["bot"]
        return turn.json()

    def to_premium(self) -> None:
        """Answer as the informed customer until the bot asks what the add-on cost."""
        twin = samajh_factory(BOOK, SETTINGS)({"record": "hero", "language": "hi"})
        step = twin.start()
        while not _asks_premium(self.bot):
            assert not self.bot["end_call"] and self.turns < 30
            reply = answer("hi", step.say)
            self.say(reply)
            step = twin.step(step.state, _heard(reply, step.say.second_reading))


def _heard(reply: str, second: bool):
    from samajh.server.dialogue import Heard

    return Heard(text=reply, second=reply if second else None)


def test_where_the_readings_differ_twice_the_v25_figure_is_read_back(fake: FakeSpeech, state: Path) -> None:
    call = Call(phone_for(fake, state), fake, state)
    call.to_premium()

    first = call.say(v30=FIFTY_FIVE, v25=FIFTY_TWO)
    assert call.bot["lines"][-1]["key"] == "premium.say_again"  # they differ: asked again
    again = call.say(v30=FIFTY_FIVE, v25=FIFTY_TWO)

    position = call_state(call.log()).position
    assert position.at == "read_back" and position.amount_inr == 52_000  # the v2.5 figure, not 55,000
    for turn in (first, again):
        customer = turn["customer"]
        assert customer["transcript"] == FIFTY_TWO and customer["acted_on"] == "second"
        assert [(r["role"], r["model"], r["text"]) for r in customer["readings"]] == [
            ("primary", V30, FIFTY_FIVE),
            ("second", V25, FIFTY_TWO),
        ]


@pytest.mark.parametrize("failure", ["error", "empty"])
def test_with_no_v25_text_the_call_acts_on_v30s_figure(fake: FakeSpeech, state: Path, failure: str) -> None:
    call = Call(phone_for(fake, state), fake, state)
    call.to_premium()
    if failure == "error":
        fake.model_errors[V25] = ServerError(
            status=504, code="TIMEOUT", message="v2.5 answered 504", attempts=1
        )

    for _ in range(2):  # one reading only holds a figure: asked again once, then read back
        turn = call.say(v30=FIFTY_TWO, v25="")
        customer = turn["customer"]
        assert customer["transcript"] == FIFTY_TWO and customer["acted_on"] == "primary"
        assert customer["readings"][1]["ok"] is (failure == "empty")

    position = call_state(call.log()).position
    assert position.at == "read_back" and position.amount_inr == 52_000


def test_a_refusal_heard_only_by_v30_ends_the_call(fake: FakeSpeech, state: Path) -> None:
    call = Call(phone_for(fake, state), fake, state)
    call.to_premium()
    fake.model_errors[V25] = ServerError(status=504, code="TIMEOUT", message="v2.5 answered 504", attempts=1)

    turn = call.say(v30=CUSTOMERS_HI.decline)

    assert turn["ended"] and call.bot["end_call"]
    assert call_state(call.log()).position.outcome == "declined"
    assert turn["customer"]["transcript"] == CUSTOMERS_HI.decline


def test_the_log_and_case_file_label_each_reading_and_the_one_acted_on(fake: FakeSpeech, state: Path) -> None:
    call = Call(phone_for(fake, state), fake, state)
    call.to_premium()
    call.say(v30=FIFTY_FIVE, v25=FIFTY_TWO)
    assert call.phone.post(f"/api/sessions/{call.sid}/end", json={}).status_code == 200

    log = call.log()
    figure = next(e for e in log.events if isinstance(e, CustomerEvent) and len(e.readings) == 2)
    assert (figure.transcript, figure.acted_on, figure.literal) == (FIFTY_TWO, "second", "शब्दों में")
    assert call.phone.post(f"/api/sessions/{call.sid}/case").status_code == 200
    case = wait_case(call.phone, call.sid)

    evidence = next(t for t in case["turns"] if t["seq"] == figure.seq)
    assert (evidence["text"], evidence["acted_on"], evidence["source"]) == (FIFTY_TWO, V25, "file")
    assert {r["role"]: r["model"] for r in evidence["readings"]} == {"primary": V30, "second": V25}
    assert evidence["readings_agreed"] is False
    once = [t for t in case["turns"] if len(t["readings"]) == 1]
    assert once and all(t["acted_on"] == V30 for t in once if t["text"])
    assert case["models"]["dialogue_reads_first"] == f"{V25} when it has text, else {V30}"
