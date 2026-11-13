"""One P5 call on text, open or closed, as one JSON-ready dict. No audio and no Gnani call.

Open: `samajh.dialogue.start` then `step` with replies from `player.choose_open`, the turn interpreter
the server uses (the LLM classifier over the word lists) with no wall-clock limit, `second_reading=None`
(no second speech model on text); then the real extractor and rules (`samajh.pipeline.run_text`), the
tier, flags with their basis, the referral basis and `samajh.rules.summarise`.

Closed: the same opening through `step` until the bot reaches open recall (or the call ends there: the
closed call then ends the same way), then the ten statements of `data/p5/closed_statements.jsonl` in
order, each reply read by the same interpreter as a confirmation: yes, no or other. `closed_confirmed`
only when all ten are a plain yes, else `closed_not_confirmed`.

A call that raises returns `status: "no_result"` with the error and everything up to it.
"""

from __future__ import annotations

import traceback
from dataclasses import asdict
from typing import Any

from bank import Customer, Topics, load_closed_statements, load_record
from player import BotLineView, Choice, Condition, Said, choose_closed, choose_open

from samajh.dialogue import BotUtterance, EndOfCall, Expecting, Intent, Line, TurnInterpreter, start, step
from samajh.rules import summarise
from samajh.types import CallStep, Language

MAX_STEPS = 80  # above the dialogue's own 60-utterance limit: a guard against a loop, never expected


class RecordingInterpreter:
    """Wraps the shared interpreter and keeps every reading it gives, for the call file."""

    def __init__(self, inner: TurnInterpreter) -> None:
        self._inner = inner
        self.readings: list[dict[str, Any]] = []

    def interpret(self, text: str, *, language: Language, expecting: Expecting, question: str):
        try:
            heard = self._inner.interpret(text, language=language, expecting=expecting, question=question)
        except Exception as error:
            self.readings.append({"expecting": str(expecting), "raised": repr(error)})
            raise
        self.readings.append({
            "expecting": str(expecting), "intent": str(heard.intent), "settled": heard.settled,
            "degraded": heard.degraded, "classifier_label": getattr(heard, "classifier_label", None),
            "amount_inr": heard.amount_inr, "approx": heard.approx,
        })  # fmt: skip
        return heard

    def take(self) -> list[dict[str, Any]]:
        out, self.readings = self.readings, []
        return out


def view(line: Line) -> BotLineView:
    return BotLineView(
        key=line.key,
        text=line.text,
        step=str(line.step),
        asks=str(line.asks) if line.asks is not None else None,
        slots=dict(line.slots),
    )


def _lines(utterance: BotUtterance) -> list[dict[str, Any]]:
    return [{"key": ln.key, "text": ln.text, "step": str(ln.step),
             "asks": str(ln.asks) if ln.asks is not None else None} for ln in utterance.lines]  # fmt: skip


def _reply(choice: Choice) -> dict[str, Any]:
    return asdict(choice)


def _base(customer: Customer, arm: str, condition: str, level: float) -> dict[str, Any]:
    return {
        "customer_id": customer.id, "arm": arm, "condition": condition, "level": level,
        "language": customer.language, "kind": customer.kind, "gold_class": customer.gold["class"],
        "record_id": customer.record_id, "writer_model": customer.writer_model_by_arm[arm if arm == "closed" else "open"],
        "second_reading": None, "status": "running", "turns": [], "unmapped": [], "errors": [],
    }  # fmt: skip


def _opening(
    record: dict[str, Any],
    customer: Customer,
    topics: Topics,
    level: float,
    condition: Condition,
    interpreter: RecordingInterpreter,
    *,
    stop_at_recall: bool,
):
    """Drive the dialogue with the player. Returns (state, last utterance or EndOfCall)."""
    call = load_record(customer.record_id, customer.data_dir)
    language = Language(customer.language)
    state, said = start(call.record, language, lender_name=call.lender_name, call_id=f"p5-{record['customer_id']}-"
                        f"{record['arm']}-{record['condition']}-L{level}")  # fmt: skip
    history: list[Said] = []
    for _ in range(MAX_STEPS):
        if stop_at_recall and said.lines[-1].step is CallStep.open_recall:
            return state, said
        lines = [view(ln) for ln in said.lines]
        choice = choose_open(customer, topics, level, condition, lines, history)
        if not choice.mapped:
            record["unmapped"].append({"line_key": choice.line_key, "note": choice.note})
        state, nxt = step(state, choice.text, second_reading=None, interpreter=interpreter)
        reply_turn = len(state.turns) - (
            len(nxt.utterance.lines) if isinstance(nxt, EndOfCall) else len(nxt.lines)
        )
        record["turns"].append({
            "bot": _lines(said), "reply": _reply(choice), "readings": interpreter.take(),
            "degraded": reply_turn in state.degraded_turns,
        })  # fmt: skip
        history.append(Said(choice.topic, choice.variant, choice.text))
        if isinstance(nxt, EndOfCall):
            return state, nxt
        said = nxt
    raise RuntimeError(f"no end after {MAX_STEPS} customer turns")


def _end_fields(record: dict[str, Any], end: EndOfCall) -> None:
    record["final_bot"] = _lines(end.utterance)
    record["outcome"] = str(end.outcome)
    record["speaker_confirmed"] = end.speaker_confirmed
    record["degraded_turns"] = len(end.degraded_turns)
    record["unresolved"] = [u.model_dump(mode="json") for u in end.unresolved]


def _case_fields(record: dict[str, Any], customer: Customer, end: EndOfCall, llm, run_text) -> None:
    call = load_record(customer.record_id, customer.data_dir)
    run = run_text(end.transcript, call.record, llm)
    result = run.result
    record["tier"] = str(result.tier)
    record["flags"] = [
        {"rule_id": str(f.rule_id), "reason": str(f.reason), "tier": str(f.tier), "basis": str(f.basis),
         "product_id": f.product_id, "quote": f.quote}
        for f in result.all_flags()
    ]  # fmt: skip
    record["gaps"] = [
        {"rule_id": str(g.rule_id), "reason": str(g.reason), "tier": str(g.tier)} for g in result.all_gaps()
    ]
    basis = result.referral_basis
    record["referral_basis"] = str(basis) if basis is not None else None
    record["summary"] = summarise(call.record, result).model_dump(mode="json")
    record["transcript"] = end.transcript.model_dump(mode="json")


def run_open(
    customer: Customer,
    topics: Topics,
    level: float,
    condition: Condition,
    interpreter: TurnInterpreter,
    llm,
    run_text,
) -> dict[str, Any]:
    """One open call (condition `disposition` at any level, or `terse` at level 0)."""
    record = _base(customer, "open", condition, level)
    recorder = RecordingInterpreter(interpreter)
    try:
        _, end = _opening(record, customer, topics, level, condition, recorder, stop_at_recall=False)
        _end_fields(record, end)
        _case_fields(record, customer, end, llm, run_text)
        record["status"] = "ok"
    except Exception as error:  # noqa: BLE001 - the call stays as a row with its error
        record["status"] = "no_result"
        record["errors"].append({"error": repr(error), "traceback": traceback.format_exc()})
    return record


def _reading(intent: Intent) -> str:
    return "yes" if intent is Intent.yes else "no" if intent is Intent.no else "other"


def run_closed(
    customer: Customer, topics: Topics, level: float, interpreter: TurnInterpreter
) -> dict[str, Any]:
    """One closed call: the shared opening, then the ten statements."""
    record = _base(customer, "closed", "disposition", level)
    recorder = RecordingInterpreter(interpreter)
    try:
        state, at = _opening(record, customer, topics, level, "disposition", recorder, stop_at_recall=True)
        if isinstance(at, EndOfCall):
            _end_fields(record, at)
            record["closed"] = []
            record["status"] = "ok"
            return record
        script = load_closed_statements(customer.data_dir)[customer.id]
        language = Language(customer.language)
        record["closed"] = []
        record["degraded_turns"] = len(state.degraded_turns)
        for k, statement in enumerate(script["statements"]):
            said = f"{script['intro']} {statement['text']}" if k == 0 else statement["text"]
            choice = choose_closed(customer, topics, level, statement["id"])
            heard = recorder.interpret(choice.text, language=language, expecting=Expecting.confirmation,
                                       question=statement["text"])  # fmt: skip
            reading = recorder.take()
            record["closed"].append({
                "statement_id": statement["id"], "bot": said, "reply": _reply(choice), "readings": reading,
                "reading": _reading(heard.intent), "degraded": heard.degraded,
            })  # fmt: skip
            record["degraded_turns"] += int(heard.degraded)
        plain = all(s["reading"] == "yes" for s in record["closed"])
        record["outcome"] = "closed_confirmed" if plain else "closed_not_confirmed"
        record["speaker_confirmed"] = state.speaker_confirmed
        record["status"] = "ok"
    except Exception as error:  # noqa: BLE001 - the call stays as a row with its error
        record["status"] = "no_result"
        record["errors"].append({"error": repr(error), "traceback": traceback.format_exc()})
    return record
