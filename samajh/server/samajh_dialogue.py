"""`samajh.dialogue` behind the transport's `Dialogue` protocol.

The stored state is the dialogue's `CallState` as JSON and nothing else, so a call continues on
any server run that has the same record book: the factory is called again with the session's
params and `step` gets the stored state.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Mapping
from functools import cache

from samajh import dialogue as core
from samajh.clients._runtime import RetryPolicy
from samajh.clients.errors import ConfigError
from samajh.clients.gnani import TtsLanguage
from samajh.clients.llm import LlmClient
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.server.dialogue import BotLine, BotUtterance, Dialogue, DialogueFactory, Heard, ListenKind, Step
from samajh.server.records import CallRecord, RecordBook
from samajh.server.sessionlog import BotEvent, BotLineLog, CustomerEvent, SessionLog
from samajh.server.settings import Settings
from samajh.types import Language, Speaker, Transcript, Turn

log = logging.getLogger(__name__)

TTS_LANGUAGE: dict[Language, TtsLanguage] = {
    Language.hi: "hi-IN",
    Language.hi_en: "hi-en",
    Language.ta: "ta-IN",
    Language.kn: "kn-IN",
}
MAX_LINE_CHARS = 600  # the most `BotLine.text` takes
# Tag on the pieces of a dialogue line that was too long for one clip: "2/3". `call_transcript`
# uses it to put the pieces back under their one transcript turn.
PIECE_TAG = "piece"

# By `Expecting` value, as strings: a value this table does not know listens as "open" and gets
# no second reading.
_LISTEN: dict[str, ListenKind] = {
    "identity": "yes_no",
    "go_ahead": "yes_no",
    "confirmation": "yes_no",
    "stop_check": "yes_no",
    "birth_year": "short",
    "amount": "amount",
}
_MAY_CARRY_A_FIGURE = frozenset({"amount", "confirmation"})
_SENTENCE_END = re.compile(r"(?<=[।.?!])\s+")


def readings(heard: Heard) -> tuple[str, str | None]:
    """`(customer_text, second_reading)` for `samajh.dialogue.step`: the one place that orders them.

    The primary reading (Prisma v3.0 by the settings) goes first. The verifier's finding H4
    (references/reviews/iter1/verifier-voice-and-dialogue.md) measured that today's machine holds
    fewer wrong figures with v2.5 first; change the order here if the dialogue's contract asks.
    """
    return heard.text, heard.second


def _pack(parts: list[str], limit: int) -> list[str]:
    packed: list[str] = []
    for part in parts:
        if packed and len(packed[-1]) + 1 + len(part) <= limit:
            packed[-1] += " " + part
        else:
            packed.append(part)
    return packed


def spoken_pieces(text: str, limit: int = MAX_LINE_CHARS) -> tuple[str, ...]:
    """The clips one dialogue line is spoken as: the line itself, or, when it is over `limit`
    characters, its sentences packed into as few pieces as fit (then words, then a hard cut)."""
    if len(text) <= limit:
        return (text,)
    parts = [
        part[k : k + limit]
        for sentence in _SENTENCE_END.split(text.strip())
        for part in ([sentence] if len(sentence) <= limit else sentence.split())
        for k in range(0, len(part), limit)
    ]
    return tuple(_pack(parts, limit))


def _bot_lines(line: core.Line) -> list[BotLine]:
    tags = {"step": line.step.value}
    if line.asks is not None:
        tags["asks"] = line.asks.value
    if line.product_id is not None:
        tags["product_id"] = line.product_id
    pieces = spoken_pieces(line.text)
    if len(pieces) == 1:
        return [BotLine(text=line.text, key=line.key, tags=tags)]
    return [
        BotLine(text=piece, key=line.key, tags=tags | {PIECE_TAG: f"{k}/{len(pieces)}"})
        for k, piece in enumerate(pieces, 1)
    ]


def _step(state: core.CallState, said: core.BotUtterance | core.EndOfCall) -> Step:
    if isinstance(said, core.EndOfCall):
        utterance, ended, tags = said.utterance, True, {"outcome": said.outcome.value}
        listen: ListenKind = "open"
        figure = False
    else:
        expects = core.expecting(state.position).value
        utterance, ended, tags = said, False, {}
        listen, figure = _LISTEN.get(expects, "open"), expects in _MAY_CARRY_A_FIGURE
    return Step(
        state=state.model_dump_json(),
        say=BotUtterance(
            lines=tuple(piece for line in utterance.lines for piece in _bot_lines(line)),
            language=TTS_LANGUAGE[utterance.language],
            end_call=ended,
            listen=listen,
            second_reading=figure,
            tags=tags,
        ),
    )


class SamajhDialogue:
    """One Samajh call. Stateless: everything a call has said and heard is in the state string."""

    def __init__(
        self,
        record: CallRecord,
        language: Language,
        interpreter: Callable[[], core.TurnInterpreter],
    ) -> None:
        self._record, self._language, self._interpreter = record, language, interpreter

    def start(self) -> Step:
        return _step(*core.start(self._record.record, self._language, lender_name=self._record.lender_name))

    def step(self, state: str, heard: Heard) -> Step:
        text, second = readings(heard)
        return _step(
            *core.step(
                core.CallState.model_validate_json(state),
                text,
                second_reading=second,
                interpreter=self._interpreter(),
            )
        )


def samajh_factory(
    book: RecordBook, settings: Settings, *, interpreter: core.TurnInterpreter | None = None
) -> DialogueFactory:
    """The `Dialogue` for a session's params: `record` (an id in `book`), `language`, and
    `fallback=off` to read turns with the word lists alone.

    The LLM fallback's client is built on the first turn that is not `fallback=off`, once for
    all calls. With no OpenRouter key it is the word lists alone. An `interpreter` given here
    reads every turn instead.
    """
    rules = core.RuleInterpreter()

    @cache
    def with_fallback() -> core.TurnInterpreter:
        if not settings.fallback.enabled:
            return rules
        try:
            llm = LlmClient.from_env(timeout=settings.fallback.timeout_s, retry=RetryPolicy(max_attempts=1))
        except ConfigError as error:
            log.info("no LLM fallback, turns are read by the word lists alone: %s", error)
            return rules
        return LlmFallbackInterpreter(llm, rules)

    def build(params: Mapping[str, str]) -> Dialogue:
        unknown = params.keys() - {"record", "language", "fallback"}
        if unknown:
            raise ValueError(f"unknown params {sorted(unknown)}")
        try:
            record = book.get(params.get("record", ""))
        except KeyError:
            raise ValueError(f"unknown record {params.get('record')!r}") from None
        language = Language(params.get("language", ""))  # ValueError names the bad value
        fallback = params.get("fallback", "on")
        if fallback not in ("on", "off"):
            raise ValueError(f"fallback is 'on' or 'off', not {fallback!r}")
        if interpreter is not None:
            dialogue = SamajhDialogue(record, language, lambda: interpreter)
        else:
            dialogue = SamajhDialogue(record, language, with_fallback if fallback == "on" else lambda: rules)
        dialogue.start()  # a record the dialogue cannot call is refused here, not on the line
        return dialogue

    return build


# --- reading a finished or running call back out of its log -------------------


def call_state(log: SessionLog) -> core.CallState:
    """Raises ValueError when the log holds no state of a Samajh call."""
    if log.dialogue_state is None:
        raise ValueError(f"session {log.session_id} has no dialogue state")
    return core.CallState.model_validate_json(log.dialogue_state)


def call_outcome(log: SessionLog) -> str:
    """The dialogue's `Outcome` value, or "in_progress" for a call hung up before it ended."""
    outcome = getattr(call_state(log).position, "outcome", None)
    return "in_progress" if outcome is None else str(outcome)


def _shifted(start: float | None, at: float | None) -> float | None:
    return None if start is None or at is None else round(start + at, 6)


def _spans(event: BotEvent) -> list[tuple[float | None, float | None]]:
    """Where each dialogue line of a bot event lies in the call recording, pieces rejoined."""
    grouped: list[list[BotLineLog]] = []
    for line in event.lines:
        if line.tags.get(PIECE_TAG, "1/").startswith("1/"):
            grouped.append([line])
        else:
            grouped[-1].append(line)
    return [
        (_shifted(event.rec_start, lines[0].start_s), _shifted(event.rec_start, lines[-1].end_s))
        for lines in grouped
    ]


def call_transcript(log: SessionLog) -> Transcript:
    """The dialogue's transcript with each turn's position in `call.wav`, and the session id as
    the call id. A turn whose audio was never made keeps None.

    Raises ValueError when the log's events and the stored state do not describe the same call.
    """
    state = call_state(log)
    live = [event for event in log.events if not event.superseded]
    spans = {
        Speaker.bot: [span for event in live if isinstance(event, BotEvent) for span in _spans(event)],
        Speaker.customer: [(e.rec_start, e.rec_end) for e in live if isinstance(e, CustomerEvent)],
    }
    for speaker, found in spans.items():
        wanted = sum(turn.speaker is speaker for turn in state.turns)
        if len(found) != wanted:
            raise ValueError(
                f"session {log.session_id}: the state has {wanted} {speaker.value} turns, "
                f"the log has {len(found)}"
            )
    taken = {speaker: iter(found) for speaker, found in spans.items()}
    turns: list[Turn] = []
    for turn in state.turns:
        start_s, end_s = next(taken[turn.speaker])
        turns.append(turn.model_copy(update={"start_s": start_s, "end_s": end_s}))
    return state.transcript().model_copy(update={"call_id": log.session_id, "turns": tuple(turns)})
