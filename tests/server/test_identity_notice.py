"""The prior notice before a call (P8 contract section 6): mocked, checked by the bot-line bans."""

from __future__ import annotations

import re
import unicodedata

import pytest

from samajh.dialogue.lint import lint_line
from samajh.identity import notice as notice_module
from samajh.identity.notice import PARTS, SERIES, NoticePart, lint_notice, load_notice, render_notice
from samajh.server.records import PACKAGED_DIR, load_book
from samajh.types import Language

BOOK = load_book(PACKAGED_DIR)
# Words that name a product or a record value under test, in the four languages (the lint's own
# product ban covers most; these are checked on the rendered text as well).
PRODUCT_OR_VALUE = re.compile(
    r"insurance|policy|premium|cover|deposit|बीमा|इंश्योरेंस|पॉलिसी|प्रीमियम|कवर|एफडी|जमा|लोन|loan|"
    r"காப்பீ|இன்சூரன்ஸ்|பிரீமியம்|கடன்|ವಿಮೆ|ಪ್ರೀಮಿಯಂ|ಸಾಲ",
    re.IGNORECASE,
)


@pytest.mark.parametrize("language", list(Language))
def test_every_language_renders_every_part_and_names_the_lender(language: Language) -> None:
    for record in (BOOK.get(record_id) for record_id in BOOK.ids()):
        shown = render_notice(record.lender_name, language)
        assert tuple(part.name for part in shown.parts) == PARTS
        assert shown.mocked is True and shown.channel == "SMS" and shown.series == SERIES == "1600"
        assert record.lender_name in shown.parts[0].text and record.lender_name in shown.text
        # Never the borrower: a message can be read on a locked screen.
        assert record.record.borrower.name.split()[0] not in shown.text


@pytest.mark.parametrize("language", list(Language))
def test_the_only_digits_are_the_series(language: Language) -> None:
    shown = render_notice("Namoona Finance", language)
    digits = [ch for ch in shown.text if unicodedata.category(ch) == "Nd"]
    assert "".join(digits) == SERIES
    assert shown.text.count(SERIES) == 1
    (number,) = [part for part in shown.parts if SERIES in part.text]
    assert number.name == "number"


@pytest.mark.parametrize("language", list(Language))
def test_no_product_loan_or_record_value_is_named(language: Language) -> None:
    for record in (BOOK.get(record_id) for record_id in BOOK.ids()):
        text = render_notice(record.lender_name, language).text
        assert not PRODUCT_OR_VALUE.search(text.replace(record.lender_name, ""))
        assert str(record.record.borrower.dob.year) not in text


@pytest.mark.parametrize("language", list(Language))
def test_a_secret_word_appears_only_where_it_is_denied(language: Language) -> None:
    templates, _ = load_notice(language)
    by_name = {part.name: part.text for part in templates}
    # The never_ask part names the secrets: under any other name the bans refuse it, so it passes
    # only because it denies asking (the same rule as the bot's `disclosure.never_ask`).
    assert lint_line("notice.never_ask", by_name["never_ask"]), by_name["never_ask"]
    assert lint_line("notice.not_sales", by_name["not_sales"]), by_name["not_sales"]
    assert lint_notice(list(templates)) == []
    for name in ("who", "automated", "number", "check"):
        assert lint_line(f"notice.{name}", by_name[name]) == []


def test_tamil_and_kannada_are_labelled_not_human_reviewed() -> None:
    for language in (Language.ta, Language.kn):
        assert render_notice("Namoona Finance", language).review == "not human-reviewed"
        source = (notice_module.NOTICE_DIR / f"{language.value}.toml").read_text(encoding="utf-8")
        assert "NOT HUMAN-REVIEWED" in source


def _parts(**texts: str) -> list[NoticePart]:
    base = {name: f"{{lender}} {name}" for name in PARTS} | {"number": "{series} से"}
    return [NoticePart(name=name, text=texts.get(name, base[name])) for name in PARTS]


@pytest.mark.parametrize(
    ("texts", "problem"),
    [
        ({"who": "{lender}: हम आपका ओटीपी लेंगे"}, "secret"),  # a secret word, not denied, not in never_ask
        ({"never_ask": "हम ओटीपी माँगेंगे"}, "only when it is denied"),  # a secret word, not denied
        ({"automated": "आपके बीमा के बारे में"}, "names or explains the product"),
        ({"check": "{lender} आपके लोन के बारे में"}, "names the loan"),
        ({"check": "{lender} 1800 पर कॉल करें"}, "digit"),
        ({"who": "{lender} {first_name} जी"}, "unknown slot"),
        ({"check": "{lender} {series}"}, "number series"),
    ],
)
def test_the_lint_refuses_a_notice_that_breaks_a_rule(texts: dict[str, str], problem: str) -> None:
    assert lint_notice(_parts()) == []
    found = lint_notice(_parts(**texts))
    assert any(problem in item for item in found), found


def test_parts_out_of_order_or_missing_are_refused() -> None:
    parts = _parts()
    assert lint_notice(parts[::-1]) and lint_notice(parts[:-1])


def test_a_lender_name_with_a_digit_or_none_is_refused() -> None:
    with pytest.raises(ValueError, match="digit"):
        render_notice("Finance 24", Language.hi)
    with pytest.raises(ValueError, match="empty"):
        render_notice("  ", Language.hi)
