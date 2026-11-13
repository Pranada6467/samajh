"""The written notice before a Samajh call (P8 contract section 6). MOCKED: nothing is ever sent.

`render_notice(lender_name, language)` reads `notices/<lang>.toml` and fills its two slots: the lender
and the number series (`SERIES`, the only digits the text may hold). The notice says who will call, that
the voice is automated, that it is a short feedback call and not sales, that the number starts with the
series, that the caller never asks for an OTP, PIN or password, and that the customer can check by
calling the customer-care number on their papers. It names the lender and never the borrower, the loan or
a product: a message can be read on a locked screen by someone else.

Every file is checked when it is loaded, so a notice that breaks a rule cannot be shown: each part passes
the bot-line bans (`samajh.dialogue.lint`; a secret word only in the part that denies asking for it, a
sales word only in the part that denies selling), no part names the loan, and no template holds a digit.
Tamil and Kannada are `not human-reviewed`.
"""

from __future__ import annotations

import tomllib
from functools import cache
from pathlib import Path
from string import Formatter

from pydantic import BaseModel, ConfigDict

from samajh.dialogue._lexicon import found, tokens
from samajh.dialogue.lint import lint_line
from samajh.types import Language

NOTICE_DIR = Path(__file__).with_name("notices")
SERIES = "1600"  # the number series of service and transactional calls the notice names
# The parts every notice has, in the order it reads.
PARTS = ("who", "automated", "not_sales", "number", "never_ask", "check")
SLOTS = frozenset({"lender", "series"})
# A part is linted as the bot line whose denial it shares: only these two may use a banned word, and
# only beside a denial. Every other part is linted under its own name, which no ban exempts.
_LINT_AS = {"never_ask": "disclosure.never_ask", "not_sales": "disclosure.not_sales"}
# The notice never names the loan (the bot lines may, after the right-party check; a message may not).
_LOAN_WORDS = frozenset(
    tokens(text) for text in ("loan", "लोन", "ऋण", "कर्ज", "कर्ज़", "क़र्ज़", "கடன்", "ಸಾಲ", "ಸಾಲದ", "ಸಾಲವನ್ನು")
)


class NoticePart(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    text: str


class Notice(BaseModel):
    """A rendered notice. `mocked` is always true: the demo shows it and nothing is sent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    language: Language
    lender: str
    series: str = SERIES
    parts: tuple[NoticePart, ...]
    text: str  # the parts joined, as the message would read
    review: str  # "not human-reviewed" for Tamil and Kannada
    mocked: bool = True
    channel: str = "SMS"


def lint_notice(parts: list[NoticePart]) -> list[str]:
    """Problems with a notice's templates; an empty list means it may be shown."""
    problems = []
    names = [part.name for part in parts]
    if tuple(names) != PARTS:
        problems.append(f"the parts must be {list(PARTS)} in that order, not {names}")
    for part in parts:
        slots = {field for _, field, _, _ in Formatter().parse(part.text) if field is not None}
        if slots - SLOTS:
            problems.append(f"{part.name}: unknown slot(s) {sorted(slots - SLOTS)}")
        if ("series" in slots) != (part.name == "number"):
            problems.append(f"{part.name}: the number series belongs in the 'number' part, once")
        problems += lint_line(_LINT_AS.get(part.name, f"notice.{part.name}"), part.text)
        if found(tokens(part.text), _LOAN_WORDS):
            problems.append(f"{part.name}: names the loan")
    if not any("{lender}" in part.text for part in parts):
        problems.append("the notice must name the lender")
    return problems


@cache
def load_notice(language: Language) -> tuple[tuple[NoticePart, ...], str]:
    """The checked templates of one language and its review label. Raises ValueError on a file that
    breaks a rule."""
    data = tomllib.loads((NOTICE_DIR / f"{language.value}.toml").read_text(encoding="utf-8"))
    if data.get("language") != language.value:
        raise ValueError(f"{language.value}.toml names the language {data.get('language')!r}")
    parts = [NoticePart.model_validate(part) for part in data.get("parts", [])]
    problems = lint_notice(parts)
    if language in (Language.ta, Language.kn) and data.get("review") != "not human-reviewed":
        problems.append("a Tamil or Kannada notice must be labelled 'not human-reviewed'")
    if problems:
        raise ValueError(f"notice {language.value}: " + "; ".join(problems))
    return tuple(parts), str(data.get("review", ""))


def render_notice(lender_name: str, language: Language) -> Notice:
    """The notice for a call from `lender_name`, in `language`. Raises ValueError on an empty lender
    name or a lender name with a digit (the series must be the only figure)."""
    lender = lender_name.strip()
    if not lender:
        raise ValueError("lender_name is empty")
    if any(ch.isdigit() for ch in lender):
        raise ValueError("a lender name with a digit would put a second figure in the notice")
    templates, review = load_notice(language)
    parts = tuple(
        NoticePart(name=part.name, text=part.text.format(lender=lender, series=SERIES)) for part in templates
    )
    return Notice(
        language=language,
        lender=lender,
        parts=parts,
        text=" ".join(part.text for part in parts),
        review=review,
    )
