"""`samajh.dialogue` behind the transport's `Dialogue` protocol.

The stored state is the dialogue's `CallState` as JSON and nothing else, so a call continues on
any server run that has the same record book: the factory is called again with the session's
params and `step` gets the stored state.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Mapping, Sequence
from functools import cache
from typing import Protocol

from samajh import dialogue as core
from samajh.amounts import Parsed, parse_amount
from samajh.clients._runtime import RetryPolicy
from samajh.clients.errors import ConfigError
from samajh.clients.gnani import TtsLanguage
from samajh.clients.llm import LlmClient
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter
from samajh.identity import IdentityPolicy, IdentityRecord, parse_policy
from samajh.server.dialogue import BotLine, BotUtterance, Dialogue, DialogueFactory, Heard, ListenKind, Step
from samajh.server.loanbook import LINK_PARAMS, LoanBook, resolve_record
from samajh.server.records import CallRecord, RecordBook
from samajh.server.sessionlog import BotEvent, BotLineLog, CustomerEvent, FollowedBy, SessionLog, SttReading
from samajh.server.settings import Settings
from samajh.types import Language, Question, Speaker, Transcript, Turn

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

# The session param that carries a per-call identity setting (the demo picker's), as canonical JSON.
# The server writes it at creation from the request's top-level `identity`, after `parse_policy`.
IDENTITY_PARAM = "identity"


def identity_param(policy: IdentityPolicy) -> str:
    """The session param's value for `policy`: canonical JSON of the menu fields."""
    return json.dumps(policy.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def session_policy(params: Mapping[str, str], default: IdentityPolicy) -> IdentityPolicy:
    """The identity setting of a session: its own (`IDENTITY_PARAM`) or the server's `default`.
    Raises ValueError on a value outside the menu."""
    text = params.get(IDENTITY_PARAM)
    if text is None:
        return default
    try:
        mapping = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError("the identity param is not JSON") from error
    return parse_policy(mapping)


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
# Why each `Expecting` value the table leaves out listens as "open", the longest patience:
#   open           an answer in the customer's own words (open recall, kind, consent): it can run
#                  long and pause mid-sentence.
#   told           "were you told ...?": a bare yes or no answers it, but so does a sentence, and a
#                  700 ms yes/no cut would split the sentence.
#   either_or      "required, or your choice?": a bare yes or no is not an answer, so the reply is
#                  a phrase; open patience.
#   callback_time  "when should we call?": any reply is the answer, often a time with a pause
#                  ("kal ... shaam ko").
_MAY_CARRY_A_FIGURE = frozenset({"amount", "confirmation"})
_SENTENCE_END = re.compile(r"(?<=[।.?!])\s+")


def readings(heard: Heard) -> tuple[str, str | None]:
    """`(customer_text, second_reading)` for `samajh.dialogue.step`: the one place that orders them.

    The dialogue's contract (references/pilots/P2-contract.md section 5, after the verifier's
    finding H4) asks for Prisma v2.5 first on figure turns: where the two readings differ, the
    dialogue holds and reads back the first reading's figure. The settings make the second
    reading v2.5 and the primary v3.0 (`tests/server/test_samajh_dialogue.py` pins both, so a
    swap there fails a test until this order is revisited). So:

    * a second reading with text goes first, and the primary reading is the second;
    * a second reading that is missing or empty (failed, late, heard nothing) leaves the primary
      first and is handed on as `""`, so a refusal heard by v3.0 alone is still acted on and the
      turn is never empty because v2.5 timed out;
    * a turn with no second reading (None) is the primary reading alone.
    """
    if heard.second:
        return heard.second, heard.text
    return heard.text, heard.second


class _KeyedLine(Protocol):
    @property
    def key(self) -> str | None: ...
    @property
    def tags(self) -> Mapping[str, str]: ...


# A line that reads the customer's figure back: a read-back line with the figure as a slot.
_READ_BACK_KEYS = frozenset(key for key, spec in core.LINES.items() if "amount_words" in spec.slots)
# A line that asks for the premium or cover figure once more: after two readings that differ
# (`say_again`), an unclear answer (`reask`) or a read-back the customer turned down (`restate`).
_ASKED_AGAIN_KEYS = frozenset(
    key
    for key, spec in core.LINES.items()
    if spec.asks in (Question.premium, Question.cover)
    and key.rsplit(".", 1)[-1] in ("say_again", "reask", "restate")
)


def followed_by(lines: Sequence[_KeyedLine]) -> FollowedBy:
    """What the bot did right after a customer turn, from the last line of its reply (the one the
    customer answers next): its key and its `step` tag."""
    if not lines:
        return "other"
    last = lines[-1]
    if last.tags.get("step") == "read_back" and last.key in _READ_BACK_KEYS:
        return "read_back"
    if last.key in _ASKED_AGAIN_KEYS:
        return "asked_again"
    return "other"


def holds_figure(readings: Sequence[SttReading]) -> bool:
    """Whether any reading that came back holds a rupee figure (`samajh.amounts.parse_amount`)."""
    return any(isinstance(parse_amount(r.text), Parsed) for r in readings if r.ok)


def readings_agreed(readings: Sequence[SttReading], agreed: bool | None) -> bool | None:
    """The turn's `readings_agreed`: the dialogue's record, kept only on a turn read twice where
    either reading holds a figure (a plain yes at a read-back is None)."""
    return agreed if len(readings) > 1 and holds_figure(readings) else None


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


def _step(
    state: core.CallState,
    said: core.BotUtterance | core.EndOfCall,
    heard: str | None = None,
    agreed: bool | None = None,
    degraded: bool = False,
) -> Step:
    confirmed = speaker_confirmed(state)
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
        heard=heard,
        agreed=agreed,
        degraded=degraded,
        speaker_confirmed=confirmed,
    )


class SamajhDialogue:
    """One Samajh call. Stateless: everything a call has said and heard is in the state string."""

    def __init__(
        self,
        record: CallRecord,
        language: Language,
        interpreter: Callable[[], core.TurnInterpreter],
        identity: IdentityPolicy = IdentityPolicy(),  # noqa: B008 - frozen, so one shared default is safe
    ) -> None:
        self._record, self._language, self._interpreter = record, language, interpreter
        self._identity = identity

    def start(self) -> Step:
        return _step(
            *core.start(
                self._record.record,
                self._language,
                lender_name=self._record.lender_name,
                identity=self._identity,
            )
        )

    def prefetch(self, state: str, text: str) -> None:
        """Start the classifier on the primary transcript while the second reading is awaited.
        `step` reuses the begun call when it reads the same text at the same question; it begins
        both readings itself, so the order `readings` gives does not matter. Never raises."""
        try:
            core.prefetch(core.CallState.model_validate_json(state), text, interpreter=self._interpreter())
        except Exception:
            log.warning("dialogue prefetch failed", exc_info=True)

    def step(self, state: str, heard: Heard) -> Step:
        text, second = readings(heard)
        after, said = core.step(
            core.CallState.model_validate_json(state),
            text,
            second_reading=second,
            interpreter=self._interpreter(),
        )
        # The turn as the dialogue kept it: it may act on the other reading (only that one held a figure).
        reply = next(turn for turn in reversed(after.turns) if turn.speaker is Speaker.customer)
        agreed = next((r.agreed for r in after.second_readings if r.turn_id == reply.id), None)
        return _step(after, said, heard=reply.text, agreed=agreed, degraded=reply.id in degraded_turns(after))


def samajh_factory(
    book: RecordBook,
    settings: Settings,
    *,
    interpreter: core.TurnInterpreter | None = None,
    loans: LoanBook | None = None,
) -> DialogueFactory:
    """The `Dialogue` for a session's params: `record` (an id in `book`) or `loan` (a loan of the
    batch in `loans`, with the link the server stored at creation: `LINK_PARAMS`), `language`,
    `fallback=off` to read turns with the word lists alone, and `identity` (`IDENTITY_PARAM`) for a
    call whose right-party setting is not the server's (`settings.identity`). The setting is used
    at `start` only: a call in progress keeps the one in its stored state. Building it never checks whether a
    call may be placed on the loan (`LoanBook.open_call` does, once, at creation).

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
        unknown = params.keys() - {"record", "loan", "language", "fallback", IDENTITY_PARAM, *LINK_PARAMS}
        if unknown:
            raise ValueError(f"unknown params {sorted(unknown)}")
        record, _ = resolve_record(params, book, loans)
        language = Language(params.get("language", ""))  # ValueError names the bad value
        fallback = params.get("fallback", "on")
        if fallback not in ("on", "off"):
            raise ValueError(f"fallback is 'on' or 'off', not {fallback!r}")
        identity = session_policy(params, settings.identity)
        if interpreter is not None:
            dialogue = SamajhDialogue(record, language, lambda: interpreter, identity)
        else:
            reader = with_fallback if fallback == "on" else lambda: rules
            dialogue = SamajhDialogue(record, language, reader, identity)
        dialogue.start()  # a record the dialogue cannot call is refused here, not on the line
        return dialogue

    return build


# --- reading a finished or running call back out of its log -------------------


def call_state(log: SessionLog) -> core.CallState:
    """Raises ValueError when the log holds no state of a Samajh call."""
    if log.dialogue_state is None:
        raise ValueError(f"session {log.session_id} has no dialogue state")
    return core.CallState.model_validate_json(log.dialogue_state)


def degraded_turns(state: core.CallState) -> tuple[int, ...]:
    """The transcript turn ids of the customer turns the dialogue read without its classifier
    (it failed or ran out of time). The one place the server reads the dialogue's mark."""
    return tuple(int(turn_id) for turn_id in state.degraded_turns)


def speaker_confirmed(state: object) -> bool | None:
    """Whether the dialogue's state says the person on the line passed its right-party check (the
    year of birth, or with no second check the affirmation the policy asks for): True or False when the state has `speaker_confirmed`, None (unknown) when it does not (the
    dialogue before P2 round 3). Never guessed from the outcome. The one place it is read."""
    value = getattr(state, "speaker_confirmed", None)
    return value if isinstance(value, bool) else None


def call_speaker_confirmed(log: SessionLog) -> bool | None:
    return speaker_confirmed(call_state(log))


# --- the reply to the year-of-birth question is withheld -------------------------
#
# What the customer says to the second check (`second_check.ask`, `second_check.reask`, the retry of
# a two-attempt check) is the expected answer whenever the check passes. It is kept out of everything
# a phone, a reviewer or a model reads: the turn response, `GET /api/sessions/{id}`, the session log's
# events on disk, the case file (turn text, readings, Batch segment text, transcript) and the
# transcript handed to the extractor. The turn itself stays: its id, timing, audio offset and audio.
# The dialogue's own state (`dialogue_state` on disk) still holds the words; no response serves it.
WITHHELD = "[reply to the year-of-birth question: withheld]"
_YEAR_STEP = "second_check"  # `samajh.dialogue.Step.second_check`, as a bot line's `step` tag


def answers_year_question(lines: Sequence[_KeyedLine]) -> bool:
    """Whether a reply to these bot lines answers the year-of-birth question: the last line (the
    one the customer answers) is a second-check line."""
    return bool(lines) and lines[-1].tags.get("step") == _YEAR_STEP


def withhold_reply(event: CustomerEvent) -> CustomerEvent:
    """The event with the words of every reading replaced by `WITHHELD` (silence stays silence)."""

    def mask(text: str) -> str:
        return WITHHELD if text else text

    return event.model_copy(
        update={
            "transcript": mask(event.transcript),
            "literal": None,
            "readings": [
                r.model_copy(update={"text": mask(r.text), "literal": None}) for r in event.readings
            ],
        }
    )


def shown_event(log: SessionLog, event: CustomerEvent) -> CustomerEvent:
    """A customer event as anything outside the dialogue may see it: withheld when it answers the
    year-of-birth question (also for a log written before the server withheld it)."""
    asked = (
        log.events[event.reply_to]
        if event.reply_to is not None and event.reply_to < len(log.events)
        else None
    )
    if isinstance(asked, BotEvent) and answers_year_question(asked.lines):
        return withhold_reply(event)
    return event


def shown_log(log: SessionLog) -> SessionLog:
    """The session log with every reply to the year-of-birth question withheld."""
    events = [shown_event(log, e) if isinstance(e, CustomerEvent) else e for e in log.events]
    return log.model_copy(update={"events": events})


def call_identity(log: SessionLog) -> IdentityRecord:
    """The call's right-party record (`samajh.dialogue.identity_record`): the policy, the check, the
    attempts, whether it passed and one fixed sentence. It holds no expected answer and no reply."""
    return core.identity_record(call_state(log))


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
    the call id. A turn whose audio was never made keeps None. The reply to the year-of-birth
    question reads `WITHHELD`.

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
        update: dict[str, object] = {"start_s": start_s, "end_s": end_s}
        if turn.speaker is Speaker.customer and turn.step.value == _YEAR_STEP and turn.text:
            update["text"] = WITHHELD  # the reply to the year-of-birth question (see `WITHHELD`)
        turns.append(turn.model_copy(update=update))
    return state.transcript().model_copy(update={"call_id": log.session_id, "turns": tuple(turns)})
