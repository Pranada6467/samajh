"""The contract between the voice transport and whatever decides what the bot says.

The transport owns audio, STT, TTS and the event log. A `Dialogue` owns the words: it is asked
once at call start (`heard=None`) and once after each customer turn, and answers with the next
bot utterance. One `Dialogue` object serves one call, so it may keep state.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from samajh.clients.gnani import TtsLanguage


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class BotUtterance(_Frozen):
    text: str = Field(min_length=1, max_length=600)
    # Spoken by Timbre in this language; the customer's reply is transcribed in the matching one.
    language: TtsLanguage
    end_call: bool = False
    # Opaque to the transport and copied to the event log (for example step, asks, product_id).
    tags: Mapping[str, str] = Field(default_factory=dict)


class Heard(_Frozen):
    """The customer's latest turn. `text == ""` means nothing was heard (silence or empty STT)."""

    text: str
    literal: str | None = None  # prisma-v2.5 transcribe only: the wording before number formatting
    detected_language: str | None = None  # prisma-v3.0 only


class Exchange(_Frozen):
    bot: BotUtterance
    heard: Heard | None  # None until the customer has answered this utterance


class CallView(_Frozen):
    session_id: str
    params: Mapping[str, str]  # what the session was created with (for example a scenario id)
    exchanges: tuple[Exchange, ...]  # every utterance so far, oldest first


class Dialogue(Protocol):
    def next(self, call: CallView, heard: Heard | None) -> BotUtterance:
        """The next bot utterance. `heard` is None at call start. Must not block on network I/O
        for long: the customer is waiting on the line."""
        ...


# Builds the Dialogue for one call from the session's params. Raise ValueError for bad params.
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

    def next(self, call: CallView, heard: Heard | None) -> BotUtterance:
        asked = len(call.exchanges)
        if heard is None:
            echo = ""
        elif heard.text.strip():
            echo = f"मैंने सुना: {heard.text.strip()[:300]} "
        else:
            echo = self.NOTHING_HEARD + " "
        if asked < len(self.QUESTIONS):
            return BotUtterance(
                text=echo + self.QUESTIONS[asked], language="hi-IN", tags={"stub_step": f"q{asked + 1}"}
            )
        return BotUtterance(
            text=echo + self.CLOSING, language="hi-IN", end_call=True, tags={"stub_step": "close"}
        )


def stub_factory(params: Mapping[str, str]) -> Dialogue:
    return StubDialogue()
