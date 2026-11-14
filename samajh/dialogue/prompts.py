"""Bot lines: the wording lives in `data/prompts/<language>.toml`, the meaning of each line here.

`LINES` is the single list of what the bot can say: for each key, the call step it belongs to,
the question it asks (if any) and the slots its template may use. A language file must define
exactly these keys and use no other slot, so a template cannot carry a value from the record:
the only slots are the first name, the lender's name, an ordinal, and (for read-backs) the
amount the customer said. Each template is also checked by `samajh.dialogue.lint`.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from string import Formatter

from samajh.dialogue.lint import lint_line
from samajh.types import CallStep, Language, Question

PROMPT_DIR = Path(__file__).resolve().parents[2] / "data" / "prompts"

_ORDINAL = frozenset({"ordinal"})
# Read-backs say the figure in words only: the digit form made the voice say it twice.
_AMOUNT = frozenset({"amount_words"})


@dataclass(frozen=True)
class LineSpec:
    step: CallStep
    asks: Question | None = None
    slots: frozenset[str] = frozenset()
    # Slots a language's text may leave out (wave 2: Hindi and Hinglish `teach_back.intro_nth` no longer
    # names an ordinal; Tamil and Kannada still do). The caller always passes them.
    optional: frozenset[str] = frozenset()


def _question(key: str, question: Question) -> dict[str, LineSpec]:
    spec = LineSpec(CallStep.teach_back, question)
    return {f"{key}.ask": spec, f"{key}.reask": spec}


LINES: dict[str, LineSpec] = {
    "right_party.ask": LineSpec(CallStep.right_party_check, slots=frozenset({"first_name"})),
    "right_party.reask": LineSpec(CallStep.right_party_check, slots=frozenset({"first_name"})),
    # Iteration 3: the who-check after a sign of another speaker, a choice question; no lender, no loan.
    "right_party.who_check": LineSpec(CallStep.right_party_check, slots=frozenset({"first_name"})),
    "purpose.before_confirm": LineSpec(CallStep.right_party_check),  # no lender, no loan
    "disclosure.who": LineSpec(CallStep.disclosure, slots=frozenset({"lender"})),
    "disclosure.not_sales": LineSpec(CallStep.disclosure),
    "disclosure.recording": LineSpec(CallStep.disclosure, slots=frozenset({"lender"})),
    "disclosure.go_ahead": LineSpec(CallStep.disclosure),
    "disclosure.reask": LineSpec(CallStep.disclosure, slots=frozenset({"lender"})),
    "disclosure.never_ask": LineSpec(CallStep.second_check),  # said with the birth-year question
    "disclosure.rights": LineSpec(CallStep.context),  # said with the first mention of the loan
    "verify.before_loan": LineSpec(CallStep.disclosure, slots=frozenset({"lender"})),
    "verify.after_loan": LineSpec(CallStep.context, slots=frozenset({"lender"})),
    "verify.short": LineSpec(
        CallStep.second_check, slots=frozenset({"lender"})
    ),  # with the birth-year question
    "second_check.ask": LineSpec(CallStep.second_check),
    "second_check.reask": LineSpec(CallStep.second_check),
    "context.loan": LineSpec(CallStep.context, slots=frozenset({"lender"})),
    "open_recall.ask": LineSpec(CallStep.open_recall),
    "open_recall.reask": LineSpec(CallStep.open_recall),
    "open_recall.nothing": LineSpec(CallStep.open_recall),
    "teach_back.intro": LineSpec(CallStep.teach_back),
    "teach_back.intro_nth": LineSpec(CallStep.teach_back, slots=_ORDINAL, optional=_ORDINAL),
    **_question("kind", Question.kind),
    "kind.ask_named": LineSpec(CallStep.teach_back, Question.kind),  # gain 8: the customer named something
    "kind.follow_what": LineSpec(CallStep.teach_back, Question.kind),  # W4: what it is called, nothing else
    "ack.neutral": LineSpec(CallStep.teach_back),  # gain 8: "जी।" by position only (Hindi and Hinglish)
    **_question("premium", Question.premium),
    "premium.say_again": LineSpec(CallStep.teach_back, Question.premium),
    **_question("payment_source", Question.payment_source),
    **_question("payment_frequency", Question.payment_frequency),
    **_question("required_for_loan", Question.required_for_loan),
    **_question("provider_choice", Question.provider_choice),
    **_question("cover", Question.cover),
    "cover.say_again": LineSpec(CallStep.teach_back, Question.cover),
    **_question("term", Question.term),
    **_question("cancel_window", Question.cancel_window),
    **_question("features", Question.features),
    "consent.ask": LineSpec(CallStep.consent_check, Question.consent),
    "consent.reask": LineSpec(CallStep.consent_check, Question.consent),
    "consent.follow_what": LineSpec(CallStep.consent_check, Question.consent),  # W4: the missing half only
    "consent.follow_how": LineSpec(CallStep.consent_check, Question.consent),  # W4
    "read_back.confirm": LineSpec(CallStep.read_back, Question.premium, _AMOUNT),
    "read_back.confirm_about": LineSpec(CallStep.read_back, Question.premium, _AMOUNT),
    "read_back.cover_confirm": LineSpec(CallStep.read_back, Question.cover, _AMOUNT),
    "read_back.reconfirm": LineSpec(CallStep.read_back, Question.premium, _AMOUNT),
    "read_back.restate": LineSpec(CallStep.read_back, Question.premium),
    "bridge.moving_on": LineSpec(CallStep.teach_back),
    "defer.reask": LineSpec(CallStep.teach_back),  # W4: before the re-ask after a deferral; takes the question's step
    "stop_check.decline": LineSpec(CallStep.close),
    "stop_check.human": LineSpec(CallStep.close),
    "stop_check.disengaged": LineSpec(CallStep.close),
    "callback.when": LineSpec(CallStep.close),
    "end.third_party": LineSpec(CallStep.close, slots=frozenset({"first_name"})),
    "end.neutral": LineSpec(CallStep.close),
    "end.check_failed": LineSpec(CallStep.close, slots=frozenset({"lender"})),
    "end.declined": LineSpec(CallStep.close),
    "end.human": LineSpec(CallStep.close),
    "end.call_back": LineSpec(CallStep.close),
    "end.language": LineSpec(CallStep.close),
    "language.switched": LineSpec(CallStep.disclosure),  # W4: said in the new language before the question
    "end.no_response": LineSpec(CallStep.close),
    "end.do_not_call": LineSpec(CallStep.close),
    "end.written": LineSpec(CallStep.close),
    "close.thanks": LineSpec(CallStep.close),
    "close.may_call_back": LineSpec(CallStep.close),
    "close.verify": LineSpec(CallStep.close, slots=frozenset({"lender"})),
    "close.bye": LineSpec(CallStep.close),
}

# The teach-back questions put to the customer for each product, in order. The list is the same
# for every record: which questions are asked must not depend on what the record says.
PRODUCT_QUESTIONS: tuple[Question, ...] = (
    Question.kind,
    Question.premium,
    Question.payment_source,
    Question.payment_frequency,
    Question.required_for_loan,
    Question.provider_choice,
    Question.cover,
    Question.term,
    Question.cancel_window,
    Question.features,
)


def slots_of(template: str) -> frozenset[str]:
    """The slot names a template uses."""
    return frozenset(name for _, name, _, _ in Formatter().parse(template) if name is not None)


@dataclass(frozen=True)
class PromptPack:
    """Every bot line in one language."""

    language: Language
    review: str  # who has read the wording; "not human-reviewed" for Tamil and Kannada
    ordinals: tuple[str, ...]
    range_word: str  # joins the two ends of a spoken range in a read-back ("पचास हज़ार से बावन हज़ार")
    templates: dict[str, str]
    design: dict[str, str]  # key -> the DESIGN.md paragraph the line implements

    def render(self, key: str, **slots: str) -> str:
        """The spoken text of one line. Raises unless `slots` are exactly the ones the line declares."""
        declared = LINES[key].slots
        if slots.keys() != declared:
            raise ValueError(f"line {key!r} takes slots {sorted(declared)}, got {sorted(slots)}")
        return self.templates[key].format(**slots)

    def ordinal(self, index: int) -> str:
        return self.ordinals[index]


@cache
def load_prompts(language: Language, directory: Path = PROMPT_DIR) -> PromptPack:
    """Read and check one language file.

    Raises ValueError when it does not match `LINES` or holds wording `samajh.dialogue.lint` bans.
    """
    path = directory / f"{language.value}.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if data.get("language") != language.value:
        raise ValueError(f"{path.name}: language is {data.get('language')!r}, expected {language.value!r}")
    lines = data.get("lines", {})
    if lines.keys() != LINES.keys():
        missing, extra = sorted(LINES.keys() - lines.keys()), sorted(lines.keys() - LINES.keys())
        raise ValueError(f"{path.name}: missing lines {missing}, unknown lines {extra}")
    templates, design = {}, {}
    for key, line in lines.items():
        if line.keys() != {"text", "design"} or not line["text"].strip() or not line["design"].strip():
            raise ValueError(
                f"{path.name}: line {key!r} needs a non-empty `text` and `design` and nothing else"
            )
        used, spec = slots_of(line["text"]), LINES[key]
        if not (used <= spec.slots and spec.slots - used <= spec.optional):
            raise ValueError(
                f"{path.name}: line {key!r} uses slots {sorted(slots_of(line['text']))}, "
                f"allowed exactly {sorted(LINES[key].slots)}"
            )
        templates[key], design[key] = line["text"], line["design"]
    problems = [problem for key, text in templates.items() for problem in lint_line(key, text)]
    if problems:
        raise ValueError(f"{path.name}: banned wording: " + "; ".join(problems))
    ordinals = tuple(data.get("ordinals", ()))
    if not ordinals or not all(isinstance(o, str) and o.strip() for o in ordinals):
        raise ValueError(f"{path.name}: `ordinals` must be a non-empty list of words")
    review = data.get("review")
    if not isinstance(review, str) or not review.strip():
        raise ValueError(f"{path.name}: `review` must say who has read the wording")
    range_word = data.get("range_word")
    if not isinstance(range_word, str) or not range_word.strip() or slots_of(range_word):
        raise ValueError(f"{path.name}: `range_word` must be a plain word")
    return PromptPack(language, review, ordinals, range_word.strip(), templates, design)
