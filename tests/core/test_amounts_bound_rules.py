"""A bound ("X तक", "up to X") through the rules: accepted for the cover, refused for the premium.

The parser reads a bound as its ceiling and marks it (`Parsed.bound`); `samajh.rules.normalise`
decides per field. The cover is a maximum by nature, and the bot's own cover read-back line says
"… रुपये तक मिलता है": both must keep reading. A premium said as a ceiling is no premium.
The read-back lines are read from data/prompts, never copied, so a changed line is tested as it is.
"""

import tomllib
from pathlib import Path

import pytest
from test_core_normalise import (
    CUSTOMER,
    TURNS,
    cover_read_back_call,
    judge,
    product_gaps,
    raw,
    record,
    stated,
    swap,
    transcript,
)

from samajh.amounts import Parsed, parse_amount, parse_approx_amount
from samajh.rules.normalise import carried_premiums
from samajh.types import GapReason, RuleId

PROMPTS = Path(__file__).parents[2] / "data" / "prompts"


def line(language: str, key: str, amount_words: str) -> str:
    lines = tomllib.loads((PROMPTS / f"{language}.toml").read_text(encoding="utf-8"))["lines"]
    return lines[key]["text"].format(amount_words=amount_words)


LANGS = ["hi", "hi-en"]


# --- the bot's own read-back lines -------------------------------------------------------


@pytest.mark.parametrize("language", LANGS)
@pytest.mark.parametrize(("words", "rupees"), [("पाँच लाख", 500_000), ("साढ़े तीन लाख", 350_000), ("दस लाख", 1_000_000)])
def test_the_cover_read_back_line_reads_its_figure(language, words, rupees):
    text = line(language, "read_back.cover_confirm", words)
    for parse in (parse_amount, parse_approx_amount):
        result = parse(text)
        assert isinstance(result, Parsed) and result.rupees == rupees, f"{text!r} -> {result}"


@pytest.mark.parametrize("language", LANGS)
@pytest.mark.parametrize("key", ["read_back.confirm", "read_back.reconfirm"])
def test_the_premium_read_back_lines_read_their_figure_unbounded(language, key):
    result = parse_amount(line(language, key, "बावन हज़ार"))
    assert isinstance(result, Parsed) and (result.rupees, result.bound) == (52_000, False)


@pytest.mark.parametrize("language", LANGS)
def test_a_cover_confirmed_on_the_real_read_back_line_is_clear(language):
    call = cover_read_back_call("5,00,000 का कवर है।", line(language, "read_back.cover_confirm", "पाँच लाख"), "हाँ जी।")
    extraction = raw(cover=stated("5,00,000", "5,00,000 का कवर है।", 14), cover_readback=stated(True, "हाँ जी।", 26))
    result = judge(extraction, call)
    assert result.tier.value == "clear", result.all_flags()
    assert result.products[0].gaps == ()


@pytest.mark.parametrize("language", LANGS)
def test_a_bounded_cover_confirmed_on_the_real_read_back_line_is_clear(language):
    reply = "साढ़े तीन लाख तक मिलता है।"
    call = cover_read_back_call(reply, line(language, "read_back.cover_confirm", "साढ़े तीन लाख"), "हाँ जी।")
    extraction = raw(cover=stated("साढ़े तीन लाख तक मिलता है", reply, 14), cover_readback=stated(True, "हाँ जी।", 26))
    result = judge(extraction, call, record(cover_inr=350_000))
    assert result.tier.value == "clear", (result.all_flags(), result.products[0].gaps)


def test_a_cover_read_back_of_another_figure_on_the_real_line_still_confirms_nothing():
    call = cover_read_back_call("5,00,000 का कवर है।", line("hi", "read_back.cover_confirm", "दस लाख"), "हाँ जी।")
    extraction = raw(cover=stated("5,00,000", "5,00,000 का कवर है।", 14), cover_readback=stated(True, "हाँ जी।", 26))
    assert (RuleId.cover, GapReason.readback_mismatch) in product_gaps(judge(extraction, call))


# --- cover against premium bound replies -------------------------------------------------


@pytest.mark.parametrize(
    "reply",
    ["पाँच लाख तक का कवर है।", "5 lakh tak ka cover hai.", "up to 5,00,000 rupees.", "पाँच लाख के अंदर मिलता है।"],
)
def test_a_bounded_cover_reply_is_the_cover(reply):
    quote = reply.rstrip("।.")
    result = judge(raw(cover=stated(quote, reply, 14)), swap({14: reply}))
    assert result.tier.value == "clear", (result.all_flags(), result.products[0].gaps)


@pytest.mark.parametrize(
    "reply",
    ["बावन हज़ार तक का था।", "52000 tak ki premium thi.", "up to 52,000 rupees.", "बावन हज़ार के अंदर।", "within 52,000."],
)
def test_a_bounded_premium_reply_is_not_parsed(reply):
    quote = reply.rstrip("।.")
    result = judge(raw(premium=stated(quote, reply, 6)), swap({6: reply}))
    assert (RuleId.premium, GapReason.value_not_parsed) in product_gaps(result)
    assert result.tier.value != "clear"


@pytest.mark.parametrize("reply", ["बावन हज़ार रुपये।", "52000 ki premium thi."])
def test_the_same_premium_without_the_bound_still_reads(reply):
    quote = reply.rstrip("।.")
    assert judge(raw(premium=stated(quote, reply, 6)), swap({6: reply})).tier.value == "clear"


def _recall_call(reply: str):
    turns = [t for t in TURNS if t[0] not in (5, 6)]  # the bot reads back 52,000 without asking
    return transcript([(2, CUSTOMER, "open_recall", reply, None) if t[0] == 2 else t for t in turns])


def test_a_bounded_premium_in_open_recall_is_never_carried_to_a_read_back():
    carried = carried_premiums(_recall_call("लोन के साथ एक बीमा लिया था, बावन हज़ार तक का।"))
    assert carried["P1"].reply is None
    plain = carried_premiums(_recall_call("लोन के साथ एक बीमा लिया था, बावन हज़ार का।"))
    assert plain["P1"].reply == 2
