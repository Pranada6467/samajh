"""`python -m samajh.server.prompts build`: which lines it makes, and that a call then finds them."""

from __future__ import annotations

import pytest
from test_samajh_dialogue import answer  # the scripted customer's reply to a prompt

from samajh.clients.errors import ClientError, ConfigError
from samajh.clients.gnani import CallInfo, Speech, Timbre
from samajh.dialogue import LINES, load_prompts
from samajh.server import prompts, samajh_dialogue, speech
from samajh.server.dialogue import Heard
from samajh.server.records import PACKAGED_DIR, load_book
from samajh.server.samajh_dialogue import samajh_factory
from samajh.server.settings import load_settings
from samajh.types import Language

SETTINGS = load_settings()
BOOK = load_book(PACKAGED_DIR)
RECORDS = [BOOK.get(record_id) for record_id in BOOK.ids()]
# A line that says the customer's figure back cannot be made before the call.
ON_DEMAND = {key for key, spec in LINES.items() if spec.slots & {"amount_words", "amount_digits"}}


class FakeTimbre:
    """Caches like the Gnani client: the same text and options a second time is a hit."""

    def __init__(self, fail_on: str | None = None) -> None:
        self.requests: list[tuple[str, Timbre]] = []
        self.fail_on = fail_on

    def tts(self, text: str, options: Timbre) -> Speech:
        if self.fail_on is not None and self.fail_on in text:
            raise ClientError("Timbre answered 500")
        hit = (text, options) in self.requests
        self.requests.append((text, options))
        call = CallInfo(
            cache_hit=hit,
            cache_key="k",
            seconds=0.0,
            est_credits=0.0 if hit else 0.002 * len(text),
            attempts=0 if hit else 1,
        )
        return Speech(audio=b"RIFF", content_type="audio/wav", container="wav", sample_rate=options.sample_rate,
                      audio_seconds=1.0, request_id=None, call=call)  # fmt: skip

    def stt(self, *args, **kwargs):
        raise AssertionError("the prompts command never transcribes")


@pytest.fixture(autouse=True)
def no_live_client(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("a test reached for the live Gnani client")

    def no_key(**overrides):
        raise ConfigError("OPENROUTER_API_KEY is not set")

    monkeypatch.setattr(speech, "live_client", refuse)
    monkeypatch.setattr(samajh_dialogue.LlmClient, "from_env", no_key)
    monkeypatch.delenv("SAMAJH_RECORDS_DIR", raising=False)


@pytest.mark.parametrize("language", list(Language))
def test_the_fixed_lines_are_every_line_that_does_not_carry_the_customers_figure(language: Language) -> None:
    fixed = prompts.fixed_lines(language, RECORDS)

    assert set(fixed.on_demand) == ON_DEMAND
    assert {key for key, _ in fixed.clips} == LINES.keys() - ON_DEMAND
    texts = [text for _, text in fixed.clips]
    assert len(texts) == len(set(texts)) and all(0 < len(text) <= 600 for text in texts)
    assert fixed.chars == sum(map(len, texts))
    pack = load_prompts(language)
    assert pack.render("disclosure.go_ahead") in texts
    for record in RECORDS:  # a name or lender line once for each record that differs in it
        assert pack.render("right_party.ask", first_name=record.record.borrower.name.split()[0]) in texts
        assert pack.render("context.loan", lender=record.lender_name) in texts
    assert pack.render("teach_back.intro_nth", ordinal=pack.ordinals[0]) in texts
    assert pack.render("teach_back.intro_nth", ordinal=pack.ordinals[1]) not in texts  # one product each


def test_no_record_named_leaves_only_the_lines_without_a_slot() -> None:
    fixed = prompts.fixed_lines(Language.hi, [])
    assert {key for key, _ in fixed.clips} == {key for key, spec in LINES.items() if not spec.slots}


@pytest.mark.parametrize("language", ["hi", "hi-en"])
def test_a_call_after_a_build_finds_every_fixed_line_in_the_cache(language: str) -> None:
    client = FakeTimbre()
    prompts.build([Language(language)], RECORDS, client, settings=SETTINGS, line_rate=8000)
    built = len(client.requests)

    call = samajh_factory(BOOK, SETTINGS)({"record": "hero", "language": language})
    step = call.start()
    made_on_the_call = set()
    while not step.say.end_call:
        for line in step.say.lines:
            options = speech.tts_options(SETTINGS.tts_for(Language(language)), step.say.language, 8000)
            if not client.tts(line.text, options).call.cache_hit:
                made_on_the_call.add(line.key)
        reply = answer(language, step.say)
        step = call.step(step.state, Heard(text=reply, second=reply if step.say.second_reading else None))
    for line in step.say.lines:
        options = speech.tts_options(SETTINGS.tts_for(Language(language)), step.say.language, 8000)
        if not client.tts(line.text, options).call.cache_hit:
            made_on_the_call.add(line.key)

    assert built > 40
    assert made_on_the_call == {"read_back.confirm"}


def test_a_second_build_is_all_cache_hits() -> None:
    client = FakeTimbre()
    languages = [Language.hi, Language.hi_en]

    first = prompts.build(languages, RECORDS, client, settings=SETTINGS)
    second = prompts.build(languages, RECORDS, client, settings=SETTINGS)

    for before, after in zip(first, second, strict=True):
        assert before.lines == before.new_calls == after.lines == after.cache_hits > 0
        assert (before.cache_hits, after.new_calls, after.est_credits, after.failed) == (0, 0, 0.0, [])
        assert before.est_credits == pytest.approx(
            0.002 * prompts.fixed_lines(before.language, RECORDS).chars
        )
    assert [report.language for report in first] == languages


def test_the_request_is_the_one_the_server_makes_on_a_call() -> None:
    client = FakeTimbre()
    prompts.build([Language.hi_en], RECORDS[:1], client, settings=SETTINGS, line_rate=16000)

    assert {options for _, options in client.requests} == {
        speech.tts_options(SETTINGS.tts_for(Language.hi_en), "hi-en", 16000)
    }


def test_the_dry_run_makes_no_call_and_prints_the_totals(capsys: pytest.CaptureFixture[str]) -> None:
    client = FakeTimbre()

    code = prompts.main(["build", "--lang", "hi", "--lang", "hi-en", "--dry-run"], client=client)

    out = capsys.readouterr().out.splitlines()
    assert code == 0 and client.requests == []
    for line, language in zip(out, (Language.hi, Language.hi_en), strict=True):
        fixed = prompts.fixed_lines(language, RECORDS)
        assert line.startswith(f"{language.value}: {len(fixed.clips)} lines, {fixed.chars} characters, ")
        assert f"about {fixed.chars * 0.002:.2f} credits" in line and f"{len(ON_DEMAND)} on demand" in line


def test_a_real_run_prints_hits_and_new_calls_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    client = FakeTimbre()
    lines = len(prompts.fixed_lines(Language.hi, RECORDS[:1]).clips)

    assert prompts.main(["build", "--lang", "hi", "--record", "hero"], client=client) == 0
    assert f"hi: {lines} lines, 0 cache hits, {lines} new calls" in capsys.readouterr().out
    assert prompts.main(["build", "--lang", "hi", "--record", "hero"], client=client) == 0
    assert (
        f"hi: {lines} lines, {lines} cache hits, 0 new calls, about 0.00 credits" in capsys.readouterr().out
    )
    assert {options.sample_rate for _, options in client.requests} == {8000}


def test_a_failed_line_is_named_the_rest_still_run_and_the_exit_is_non_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    broken = load_prompts(Language.hi).render("disclosure.not_sales")
    client = FakeTimbre(fail_on=broken)
    lines = len(prompts.fixed_lines(Language.hi, RECORDS).clips)

    code = prompts.main(["build", "--lang", "hi"], client=client)

    captured = capsys.readouterr()
    assert code == 1 and len(client.requests) == lines - 1
    assert "hi: FAILED disclosure.not_sales: ClientError: Timbre answered 500" in captured.err
    assert f"hi: {lines} lines, 0 cache hits, {lines - 1} new calls" in captured.out


def test_an_unknown_record_or_language_is_a_usage_error() -> None:
    for argv in (["build", "--lang", "hi", "--record", "nobody"], ["build", "--lang", "fr"], ["build"]):
        with pytest.raises(SystemExit) as stop:
            prompts.main(argv, client=FakeTimbre())
        assert stop.value.code == 2
