"""The contract between the voice transport and whatever decides what the bot says.

The transport owns audio, STT, TTS, the event log and the stored state. A `Dialogue` owns the
words and is stateless: `start` opens a call, `step` takes one customer turn, and both return the
state to keep as an opaque string. The transport stores that string with the events in one atomic
write, so a turn is applied exactly once and a call continues after a server restart: the factory
is called again with the session's params and `step` gets the stored state.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from samajh.clients.gnani import TtsLanguage

# The kind of reply the bot's last line calls for. It sets how long the phone waits through a
# pause before it takes the turn as finished (`samajh.server.settings`).
ListenKind = Literal["yes_no", "short", "amount", "open"]
MAX_LINES = 16
MAX_STATE_BYTES = 1024 * 1024


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class BotLine(_Frozen):
    """One sentence group, spoken as its own Timbre clip so that a line shared by many calls is
    synthesised once."""

    text: str = Field(min_length=1, max_length=600)
    key: str | None = None  # the template the line came from, for the log; None for free text
    # Opaque to the transport and copied to the event log (for example step, asks, product_id).
    tags: Mapping[str, str] = Field(default_factory=dict)


class BotUtterance(_Frozen):
    """What the bot says before it listens again. The customer answers the last line."""

    lines: tuple[BotLine, ...] = Field(min_length=1, max_length=MAX_LINES)
    # Spoken by Timbre in this language; the customer's reply is transcribed in the matching one.
    language: TtsLanguage
    end_call: bool = False
    listen: ListenKind = "open"
    # The reply may carry a figure: the transport reads it with the second speech model as well.
    second_reading: bool = False
    tags: Mapping[str, str] = Field(default_factory=dict)  # about the whole utterance (an outcome)

    @property
    def text(self) -> str:
        return " ".join(line.text for line in self.lines)


class Heard(_Frozen):
    """The customer's latest turn. `text == ""` means nothing was heard (silence or empty STT).

    The transport fills it by role, not by preference: `text` is the primary reading and `second`
    the second one (the models are named in the settings). Which of them a dialogue acts on first
    is the dialogue's business (`samajh.server.samajh_dialogue.readings`)."""

    text: str  # the primary reading
    literal: str | None = None  # prisma-v2.5 transcribe only: the wording before number formatting
    detected_language: str | None = None  # prisma-v3.0 only
    # The second model's transcript of the same audio. None: the bot did not ask for one.
    # "": it asked, and the reading failed or came too late, which a dialogue must treat as the
    # two readings disagreeing.
    second: str | None = None


class ClassifierRecord(_Frozen):
    """What the LLM turn classifier did on one customer turn. No text of any kind.

    `ran`: a classifier label was used or the classifier was asked and failed (`degraded`). A
    classifier answer of "unclear" is not kept as a label by the fallback, so it records as
    `ran=False`. `latency_ms`: from begin to answer: an upper bound on the LLM's own time; with a
    prefetch it includes the second-reading wait (it runs from the prefetch's `begin` of the same
    turn when there was one, else from the start of `interpret`, to its end). `wait_ms`: the wall
    time spent inside `interpret` calls in this step (summed): what the classifier added to the
    turn after the readings were in."""

    ran: bool
    label: str | None = None
    latency_ms: float | None = None
    model: str | None = None
    degraded: bool = False
    wait_ms: float | None = None


class Step(_Frozen):
    state: str = Field(max_length=MAX_STATE_BYTES)  # opaque; handed back on the next `step`
    say: BotUtterance
    # The customer's turn as the dialogue recorded it (the reading it acted on). None: `start`,
    # or a dialogue that does not say, and the transport then logs the primary reading.
    heard: str | None = None
    # On a turn read twice: whether the dialogue took the two readings as the same figure. None:
    # read once, or a dialogue that does not say.
    agreed: bool | None = None
    # The turn was read without the dialogue's classifier (it failed or ran out of time).
    degraded: bool = False
    # Whether the person on the line has passed the identity checks, as the dialogue says. None:
    # the dialogue does not say.
    speaker_confirmed: bool | None = None
    # The turn classifier's record for this turn (`ClassifierRecord`). None: `start`, or not recorded.
    classifier: ClassifierRecord | None = None


class Dialogue(Protocol):
    """Stateless. Must not block on network I/O for long: the customer is waiting on the line."""

    def start(self) -> Step:
        """The opening utterance and the state of a call that has just begun."""
        ...

    def step(self, state: str, heard: Heard) -> Step:
        """The customer answered the last utterance. Raises ValueError if the call had ended."""
        ...

    def prefetch(self, state: str, text: str) -> None:
        """The primary transcript of a turn exists: start any slow reading of it now, before the
        transport waits for the second reading. `step` follows with the same text. Optional: the
        transport calls it only when the dialogue has it, and a failure never reaches the turn."""
        ...


# Builds the Dialogue for one call from the session's params. It is called when the session is
# created and again whenever a later server run continues the call, so it must give the same
# dialogue for the same params. Raise ValueError for bad params.
DialogueFactory = Callable[[Mapping[str, str]], Dialogue]


class StubDialogue:
    """Three fixed Hindi questions, each echoing what was heard. For exercising the transport."""

    QUESTIONS = (
        "नमस्ते। यह समझ की परीक्षण कॉल है। आपने कितने रुपये का लोन लिया था?",
        "आपकी हर महीने की किस्त कितनी है?",
        "लोन के साथ आपने और क्या लिया, और कितने का?",
    )
    CLOSING = "धन्यवाद। यह कॉल अब समाप्त होती है।"
    NOTHING_HEARD = "मुझे कुछ सुनाई नहीं दिया।"

    def _say(self, asked: int, heard: Heard | None) -> Step:
        lines: list[BotLine] = []
        if heard is not None:
            said = heard.text.strip()
            lines.append(BotLine(text=f"मैंने सुना: {said[:300]}" if said else self.NOTHING_HEARD))
        ended = asked >= len(self.QUESTIONS)
        name = "close" if ended else f"q{asked + 1}"
        lines.append(BotLine(text=self.CLOSING if ended else self.QUESTIONS[asked], key=f"stub.{name}"))
        utterance = BotUtterance(
            lines=tuple(lines),
            language="hi-IN",
            end_call=ended,
            listen="amount",
            second_reading=not ended and asked == 0,
            tags={"stub_step": name},
        )
        return Step(state=json.dumps({"asked": asked + 1}), say=utterance)

    def start(self) -> Step:
        return self._say(0, None)

    def prefetch(self, state: str, text: str) -> None:
        """Nothing to start: every reply is echoed."""

    def step(self, state: str, heard: Heard) -> Step:
        asked = json.loads(state)["asked"]
        if asked > len(self.QUESTIONS):
            raise ValueError("the call has ended")
        return self._say(asked, heard)


def stub_factory(params: Mapping[str, str]) -> Dialogue:
    return StubDialogue()
