"""The bot's wording is data. These tests hold the data to the design: complete, slot-safe, and free of banned wording."""

from __future__ import annotations

import random
import shutil
import tomllib

import pytest
from dialogue_kit import LANGUAGES

from samajh.amounts import (
    NOT_HUMAN_REVIEWED,
    Approximate,
    Parsed,
    format_inr,
    parse_amount,
    parse_approx_amount,
    spoken_amount,
)
from samajh.dialogue import LINES, load_prompts
from samajh.dialogue.lint import lint_line
from samajh.dialogue.prompts import PROMPT_DIR, slots_of
from samajh.types import Language

MAX_LINE_CHARS = 240  # one line is one TTS request and one breath on a phone line


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_language_defines_every_line_with_its_design_paragraph(language):
    pack = load_prompts(language)
    assert pack.templates.keys() == LINES.keys() == pack.design.keys()
    assert all(note.strip() for note in pack.design.values())
    assert len(pack.ordinals) >= 5 and len(set(pack.ordinals)) == len(pack.ordinals)


@pytest.mark.parametrize("language", LANGUAGES)
def test_tamil_and_kannada_are_labelled_not_human_reviewed(language):
    review = load_prompts(language).review
    assert (review == "not human-reviewed") == (language in NOT_HUMAN_REVIEWED)
    assert "review" in review


@pytest.mark.parametrize("language", LANGUAGES)
def test_templates_use_only_their_declared_slots(language):
    pack = load_prompts(language)
    allowed_anywhere = {"first_name", "lender", "ordinal"}
    for key, template in pack.templates.items():
        assert slots_of(template) == LINES[key].slots
        if not key.startswith("read_back."):
            assert slots_of(template) <= allowed_anywhere, key
    amount_lines = {key for key, spec in LINES.items() if "amount_words" in spec.slots}
    assert amount_lines == {
        "read_back.confirm", "read_back.confirm_about", "read_back.cover_confirm", "read_back.reconfirm"
    }  # fmt: skip


@pytest.mark.parametrize("language", LANGUAGES)
def test_no_template_holds_banned_wording_or_a_digit(language):
    pack = load_prompts(language)
    problems = [problem for key, template in pack.templates.items() for problem in lint_line(key, template)]
    assert problems == []


@pytest.mark.parametrize("language", LANGUAGES)
def test_lines_are_short_enough_to_speak(language):
    pack = load_prompts(language)
    slots = {"first_name": "Ramesh", "lender": "Udaharan Bank", "ordinal": pack.ordinal(0),
             "amount_words": spoken_amount(1_275_450, language), "amount_digits": format_inr(1_275_450)}  # fmt: skip
    for key in LINES:
        text = pack.render(key, **{name: slots[name] for name in LINES[key].slots})
        assert len(text) <= MAX_LINE_CHARS, (key, len(text))


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_disclosure_denies_what_it_names(language):
    pack = load_prompts(language)
    for key, ban in [("disclosure.never_ask", "a secret"), ("disclosure.not_sales", "sales talk"),
                     ("disclosure.reask", "sales talk")]:  # fmt: skip
        assert lint_line(key, pack.templates[key]) == []
        spoken_elsewhere = lint_line("close.thanks", pack.templates[key])
        assert spoken_elsewhere and all(ban in problem for problem in spoken_elsewhere), key


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_read_back_line_parses_back_to_the_amount_it_reads(language):
    """The rules read the amount out of the read-back turn (W1 report section 3), so it must parse."""
    pack = load_prompts(language)
    rng = random.Random(20261110)
    amounts = {rng.randrange(100, 100_000) for _ in range(1500)} | {
        rng.randrange(100_000, 50_000_000) for _ in range(700)
    }
    amounts |= {k * 1000 for k in range(1, 200)} | {k * 100 for k in range(1, 100)} | {52000, 55000, 175000}
    for key in ("read_back.confirm", "read_back.cover_confirm", "read_back.reconfirm"):
        for amount in amounts:
            text = pack.render(
                key, amount_words=spoken_amount(amount, language), amount_digits=format_inr(amount)
            )
            heard = parse_amount(text)
            assert isinstance(heard, Parsed) and heard.rupees == amount, text


@pytest.mark.parametrize("language", [Language.hi, Language.hi_en])
def test_an_approximate_read_back_parses_back_to_the_range_it_reads(language):
    """P3a contract §4: the rules read an approximate read-back with `parse_approx_amount`."""
    pack = load_prompts(language)
    for low, high in [(50_000, 52_000), (50_000, 50_000), (1_500, 2_000), (2_00_000, 2_50_000), (900, 900)]:
        words = spoken_amount(high, language)
        if low != high:
            words = f"{spoken_amount(low, language)} {pack.range_word} {words}"
        heard = parse_approx_amount(pack.render("read_back.confirm_about", amount_words=words))
        assert isinstance(heard, Approximate) and (heard.low, heard.high) == (low, high), words


BAD_LINES = [
    ("kind.ask", "क्या यह बीमा है या एफडी?", "names or explains the product"),
    ("kind.ask", "Is this insurance?", "names or explains the product"),
    ("kind.ask", "இது காப்பீடா?", "names or explains the product"),
    ("kind.ask", "ಇದು ವಿಮೆಯೇ?", "names or explains the product"),
    ("premium.ask", "क्या आपने 52,000 दिए?", "digit"),
    ("premium.ask", "क्या आपने ५२००० दिए?", "digit"),
    ("payment_source.ask", "क्या यह लोन में से कटा था या अलग से दिया?", "how the product was paid"),
    ("consent.ask", "क्या आपने ओटीपी से हाँ कहा था?", "secret"),
    ("consent.ask", "क्या आपने फॉर्म पर साइन किया था?", "how consent was given"),
    ("second_check.ask", "अपना ओ-टी-पी बताइए।", "secret"),
    ("second_check.ask", "अपना पिन बताइए।", "secret"),
    ("second_check.ask", "Please tell me your password.", "secret"),
    ("second_check.ask", "अपना खाता नंबर बताइए।", "secret"),
    ("second_check.ask", "अपनी जन्म तिथि बताइए।", "secret"),
    ("second_check.ask", "Tell me your date of birth.", "secret"),
    ("second_check.ask", "உங்கள் பிறந்த தேதி சொல்லுங்கள்.", "secret"),
    ("second_check.ask", "ನಿಮ್ಮ ಹುಟ್ಟಿದ ದಿನಾಂಕ ಹೇಳಿ.", "secret"),
    ("disclosure.never_ask", "अपना ओ-टी-पी और पिन बताइए।", "only when it is denied"),
    ("close.thanks", "यह मिस-सेलिंग का मामला है।", "finding"),
    ("close.thanks", "This looks like mis-selling.", "finding"),
    ("close.may_call_back", "आपका पैसा वापस मिलेगा।", "promise of money back"),
    ("close.may_call_back", "आपको रिफंड मिलेगा।", "promise of money back"),
    ("close.may_call_back", "You will get a refund.", "promise of money back"),
    ("close.may_call_back", "ನಿಮಗೆ ರೀಫಂಡ್ ಸಿಗುತ್ತದೆ.", "promise of money back"),
    ("close.thanks", "आरबीआई के नियम के अनुसार यह कॉल अनिवार्य है।", "regulator"),
    ("close.thanks", "हमारे पास आपके लिए एक नया ऑफर है।", "offer"),
    ("close.thanks", "एक नई स्कीम में छूट मिल रही है।", "offer"),
    ("close.thanks", "We have a special offer for you.", "offer"),
    ("close.thanks", "यह सेल्स कॉल है।", "sales talk"),
    ("disclosure.not_sales", "यह सेल्स कॉल है।", "only when it is denied"),
]


@pytest.mark.parametrize("key, text, problem", BAD_LINES)
def test_the_lint_rejects_bad_wording(key, text, problem):
    problems = lint_line(key, text)
    assert any(problem in found for found in problems), problems


def test_a_prompt_file_with_banned_wording_or_a_wrong_slot_does_not_load(tmp_path):
    def broken(change) -> None:
        shutil.copytree(PROMPT_DIR, tmp_path / "p", dirs_exist_ok=True)
        path = tmp_path / "p" / "hi.toml"
        text = path.read_text(encoding="utf-8")
        assert change[0] in text
        path.write_text(text.replace(change[0], change[1]), encoding="utf-8")
        tomllib.loads(path.read_text(encoding="utf-8"))
        load_prompts.cache_clear()

    for change, error in [
        (("वो क्या है? अपने शब्दों में बताइए।", "क्या वो चीज़ बीमा है?"), "banned wording"),
        (("उसके लिए आपने कितने पैसे दिए?", "{first_name}, उसके लिए आपने कितने पैसे दिए?"), "uses slots"),
        (("उसके लिए आपने कितने पैसे दिए?", "क्या आपने {amount_digits} दिए?"), "uses slots"),
        (('[lines."close.bye"]', '[lines."close.extra"]'), "missing lines"),
    ]:
        broken(change)
        with pytest.raises(ValueError, match=error):
            load_prompts(Language.hi, tmp_path / "p")
    load_prompts.cache_clear()
