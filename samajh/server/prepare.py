"""Prepare a voiced call for the replay: a scripted customer's replies, spoken by Timbre.

    uv run python -m samajh.server.prepare PERSONA OUT [--dry-run]
    uv run python -m samajh.server.prepare --loan ID --state DIR OUT [--dry-run]

PERSONA is one of `PERSONAS` below. With `--loan`, the customer is a loan that `samajh.ops` drew
into the batch under DIR (`DIR/ops`), and the words are the ops simulator's own scripted call for
that loan (`samajh.ops.simulate.script_call` over `data/loanbook/sim-customers.jsonl`): the same
hidden customer the simulated batch uses, phrase-bank text, so a phone call and a simulated call on
that loan say the same things. Only this customer simulator reads that file; the server never does. The dialogue is run in text with the persona answering each
prompt (chosen by the key and tags of the bot's last line, so the script follows whatever the
dialogue asks), then every reply is synthesised in the persona's voice and written as
`OUT/NN.wav`, with `OUT/call.json` naming the record, the language and the line each turn
answers. The replay stops with `script_drift` if the live call asks something else (for example
when a reading differs from the text and the bot re-asks).

When the dialogue changes, rerun this: the Gnani client caches every reply already spoken. All
personas are synthetic; their words are written by the builder, not taken from any real call.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path

from samajh.clients.gnani import Timbre
from samajh.server import speech
from samajh.server.dialogue import BotUtterance, Heard
from samajh.server.records import PACKAGED_DIR, load_book
from samajh.server.samajh_dialogue import TTS_LANGUAGE, samajh_factory
from samajh.server.settings import load_settings
from samajh.types import Language

MAX_TURNS = 60


@dataclass(frozen=True)
class Persona:
    record: str  # a packaged record id, or a loan id when `loan` is set
    language: Language
    voice: str  # a Timbre v3.0 voice other than the bot's
    # Reply by the key of the bot's last line, then by its `asks` tag, then by its `step` tag
    # (a read-back by its step first), then by what the bot listens for ("yes_no", ...), then
    # "default".
    replies: Mapping[str, str]
    note: str
    loan: bool = False  # `record` is a loan on the synthetic loan book
    # Measured readings of a reply, by its text: (Prisma v3.0 transcribe, Prisma v2.5 transcribe),
    # as the shared client returned them for this persona's clip on the 8 kHz line. The text run
    # of the dialogue (`script`) hears such a reply as those two readings on a turn read twice, so
    # the script follows what the live call will hear. Every other reply is heard as written.
    measured: Mapping[str, tuple[str, str]] = field(default_factory=dict)

    def params(self) -> dict[str, str]:
        """The session params the replay creates the call with."""
        return {"loan" if self.loan else "record": self.record, "language": self.language.value}

    def reply(self, said: BotUtterance) -> str:
        last = said.lines[-1]
        step = last.tags.get("step")
        # A read-back carries the question it confirms (asks=premium): it is answered as a read-back.
        order = (
            (last.key, step, last.tags.get("asks"))
            if step == "read_back"
            else (last.key, last.tags.get("asks"), step)
        )
        for key in (*order, said.listen, "default"):
            if key is not None and key in self.replies:
                return self.replies[key]
        raise KeyError("no reply")  # unreachable: every persona has a default


# The misled customer of the hero record: he believes the add-on is an FD that the loan required.
# Wording follows the scripted customer of the dialogue's own tests (tests/dialogue/dialogue_kit.py).
HERO = Persona(
    record="hero",
    language=Language.hi,
    voice="Avinash",
    note="misled: believes the credit-life add-on is a fixed deposit that the loan required",
    replies={
        "right_party_check": "हाँ जी, बोल रहा हूँ",
        "second_check": "उन्नीस सौ चौरासी",
        "open_recall": "बस एक एफडी करवाई थी, लोन की सिक्योरिटी के लिए, बावन हज़ार की",
        "kind": "एफडी है",
        "premium": "बावन हज़ार",
        "premium.say_again": "बावन हज़ार",
        "payment_source": "लोन में से कट गया",
        "payment_frequency": "एक ही बार दिया था",
        "required_for_loan": "हाँ, बोला था ज़रूरी है, उसके बिना लोन नहीं मिलेगा",
        "provider_choice": "कुछ नहीं बताया",
        "cover": "पैसा सुरक्षित रहेगा",
        "term": "दो साल",
        "cancel_window": "नहीं बताया",
        "features": "एक साल बाद ब्याज के साथ निकाल सकते हैं",
        "consent": "फॉर्म पर साइन किया था बस",
        "read_back": "हाँ, सही है",
        "callback_time": "शाम को",
        "stop_check.disengaged": "नहीं नहीं, पूछिए",
        "yes_no": "हाँ, ठीक है",
        "default": "पता नहीं",
    },
)

# An ordinary customer who understood the sale, in Hinglish.
INFORMED = Persona(
    record="informed",
    language=Language.hi_en,
    voice="Avinash",
    note="informed: can say what he bought, what it cost, how it was paid and how he agreed",
    replies={
        "right_party_check": "yes, speaking",
        "second_check": "nineteen eighty four",
        "open_recall": "एक credit life insurance लिया था, fifty two thousand का",
        "kind": "life insurance है, अगर मुझे कुछ हो गया तो loan उससे चुक जाएगा",
        "premium": "fifty two thousand",
        "premium.say_again": "fifty two thousand",
        "payment_source": "loan amount में से cut हुआ",
        "payment_frequency": "one time, एक ही बार",
        "required_for_loan": "ज़रूरी नहीं था, मेरी अपनी मर्ज़ी थी",
        "provider_choice": "बोला था किसी भी company से ले सकते हो, मैंने यही चुना",
        "cover": "मुझे कुछ हुआ तो five lakh तक का loan cover होता है",
        "term": "two years",
        "cancel_window": "हाँ, thirty days में cancel करा सकते हैं",
        "features": "वापस नहीं मिलता, ये insurance है, investment नहीं",
        # The first wording ("... insurance के लिए भी अलग से हाँ की थी") was read by the extractor as
        # consent by word of mouth only (references/pilots/P1-report.md); this one says the form.
        "consent": "loan form पर sign किया था, insurance के form पर भी अलग से sign किया था",
        "read_back": "yes, correct",
        "callback_time": "evening में",
        "cover.say_again": "five lakh",
        "stop_check.disengaged": "हाँ, पूछिए",
        "yes_no": "हाँ okay",
        "default": "pata nahin",
    },
)

# The borrower's husband picks up her phone and says so.
THIRD_PARTY = Persona(
    record="third-party",
    language=Language.hi,
    voice="Shubham",
    note="third party: the borrower's husband answers and says he is not her",
    replies={
        "right_party_check": "नहीं, मैं उनका पति बोल रहा हूँ, वो अभी घर पर नहीं हैं",
        "default": "मैंने बताया ना, मैं सुनीता नहीं हूँ, उनका पति हूँ",
    },
)

# An informed Hindi customer whose premium is an amount that skips a place-value group (two
# thousand and twelve). Chosen because Prisma v3.0 `transcribe` and v2.5 `transcribe` are known to
# write it differently on phone-line TTS audio (eval/amounts_v2: amt2-hi-skipped-028, voice
# Kalpana, v3.0 wrote 2,000); measured again on this persona's own clip (`measured`). One chosen
# clip, not a rate. She does not name the amount in open recall, so the premium is asked.
AMOUNT_CHECK = Persona(
    record="amount-check",
    language=Language.hi,
    voice="Kalpana",
    note="informed; her premium is an amount the two Prisma models are known to write differently (chosen clip)",
    replies={
        "right_party_check": "हाँ जी, बोल रही हूँ",
        "second_check": "उन्नीस सौ इक्यानवे",
        "open_recall": "लोन के साथ एक बीमा लिया था, मुझे कुछ हो जाए तो बाकी लोन उससे भर जाएगा",
        "kind": "लाइफ़ इंश्योरेंस है, मुझे कुछ हुआ तो बाकी लोन उससे चुक जाएगा",
        "premium": "दो हज़ार बारह रुपये दिए थे",
        "premium.say_again": "दो हज़ार बारह रुपये दिए थे",  # the same words again: the same clip
        "payment_source": "लोन की रकम में से कट गया",
        "payment_frequency": "एक ही बार दिया था",
        "required_for_loan": "ज़रूरी नहीं था, मैंने अपनी मर्ज़ी से लिया",
        "provider_choice": "बोला था किसी और कंपनी से भी ले सकते हैं, मैंने यही चुना",
        "cover": "मुझे कुछ हुआ तो एक लाख तक का लोन चुक जाता है",
        "cover.say_again": "एक लाख",
        "term": "एक साल का",
        "cancel_window": "हाँ, तीस दिन में कैंसल करा सकते हैं",
        "features": "पैसा वापस नहीं मिलता, ये बीमा है, निवेश नहीं",
        "consent": "लोन के फॉर्म पर साइन किया था, बीमा के फॉर्म पर भी अलग से साइन किया था",
        "read_back": "हाँ, सही है",
        "callback_time": "शाम को",
        "stop_check.disengaged": "नहीं नहीं, पूछिए",
        "yes_no": "हाँ, ठीक है",
        "default": "पता नहीं",
    },
    # Measured on 2026-11-10 through samajh.clients.gnani: Timbre v3.0 Kalpana, 8 kHz, then the
    # server's turn normalisation, with the server's figure-turn options (hi-IN, transcribe).
    measured={"दो हज़ार बारह रुपये दिए थे": ("2,000 रुपये रुपये दिए थे।", "₹2,012 दिए थे")},
)

PERSONAS: dict[str, Persona] = {
    "hero": HERO,
    "informed": INFORMED,
    "third-party": THIRD_PARTY,
    "amount-check": AMOUNT_CHECK,
}


_DONT_KNOW = {Language.hi: "पता नहीं", Language.hi_en: "pata nahin"}
_YES = {Language.hi: "हाँ, ठीक है", Language.hi_en: "हाँ okay"}
# The answer to "am I speaking to <name>?". The simulator's phrase-bank answers ("जी हाँ, बोलिए।")
# are not read as a yes by today's word lists, so a scripted call would end at the first question;
# the identity answer is not what the call tests, so these fixed ones (the packaged personas') stand in.
_ITS_ME = {Language.hi: "हाँ जी, बोल रहा हूँ", Language.hi_en: "yes, speaking"}


def loan_persona(state: Path, loan_id: str, voice: str = "Avinash") -> Persona:
    """The customer of a drawn loan, with the words of the ops simulator's scripted call for it.

    Each customer turn of that script answers the bot turn before it, keyed as `Persona.reply`
    looks lines up: the read-back by its step, a teach-back question by what it asks, any other by
    its step. The one exception is the identity answer (`_ITS_ME`). Raises `LoanRefused` when a call may not be placed on the loan."""
    from samajh.ops.book import load_customers
    from samajh.ops.simulate import script_call
    from samajh.server.loanbook import LoanBook

    book = LoanBook(state)
    book.open_call(loan_id)
    loan = next(loan for loan in book.store.book() if loan.record.loan_id == loan_id)
    customer = load_customers()[loan_id]
    turns = script_call(loan, customer).transcript.turns
    language = loan.record.borrower.language
    replies = {
        "yes_no": _YES[language],
        "default": _DONT_KNOW[language],
        "right_party_check": _ITS_ME[language],
    }
    for asked, said in pairwise(turns):
        if asked.speaker.value != "bot" or said.speaker.value != "customer":
            continue
        step = asked.step.value
        key = asked.asks.value if asked.asks is not None and step != "read_back" else step
        replies.setdefault(key, said.text)
    return Persona(
        record=loan_id,
        language=language,
        voice=voice,
        replies=replies,
        note=f"loan-book customer {loan_id}: the ops simulator's '{customer.archetype}' script, phrase-bank text",
        loan=True,
    )


def script(persona: Persona, state: Path | None = None) -> list[dict[str, str]]:
    """The persona's turns, in order, against the dialogue as it is now (word lists only). A
    loan-book persona needs the `state` directory that holds its batch."""
    from samajh.server.loanbook import LoanBook

    settings = load_settings()
    settings = settings.model_copy(
        update={"fallback": settings.fallback.model_copy(update={"enabled": False})}
    )
    params = persona.params() | {"fallback": "off"}
    loans = None
    if persona.loan:
        if state is None:
            raise ValueError("a loan-book persona needs the state directory of its batch")
        loans = LoanBook(state)
        params |= loans.open_call(persona.record).params()
    call = samajh_factory(load_book(PACKAGED_DIR), settings, loans=loans)(params)
    step, turns = call.start(), []
    while not step.say.end_call:
        if len(turns) >= MAX_TURNS:
            raise RuntimeError(f"{persona.record}: the call did not end within {MAX_TURNS} turns")
        reply = persona.reply(step.say)
        turns.append(
            {"file": f"{len(turns) + 1:02d}.wav", "answers": step.say.lines[-1].key or "", "text": reply}
        )
        primary, second = persona.measured.get(reply, (reply, reply))
        step = call.step(step.state, Heard(text=primary, second=second if step.say.second_reading else None))
    return turns


def customer_voice(persona: Persona, line_rate: int = 8000) -> Timbre:
    return Timbre(
        model="timbre-v3.0",
        voice=persona.voice,
        language=TTS_LANGUAGE[persona.language],
        sample_rate=line_rate,
        container="wav",
    )


def prepare(
    persona: Persona,
    out: Path,
    client: speech.SpeechClient,
    *,
    line_rate: int = 8000,
    state: Path | None = None,
) -> list[dict]:
    """Write the turn audio and call.json. Idempotent: the same persona and dialogue give the
    same files, and every Timbre request is served from the cache after the first run."""
    from samajh.server.audio import to_line_pcm

    turns = script(persona, state)
    out.mkdir(parents=True, exist_ok=True)
    options = customer_voice(persona, line_rate)
    for turn in turns:
        spoken = client.tts(turn["text"], options)
        # Timbre's WAV header has streaming-style sizes; rewrite it as a plain PCM WAV.
        (out / turn["file"]).write_bytes(to_line_pcm(spoken.audio, line_rate, 30.0)[0])
    for stale in out.glob("*.wav"):
        if stale.name not in {t["file"] for t in turns}:
            stale.unlink()
    manifest = {
        "persona": persona.note,
        "voice": {"model": options.model, "voice": options.voice, "language": options.language},
        "synthetic": True,
        "params": persona.params(),
        "turns": turns,
    }
    (out / "call.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return turns


def main(argv: Sequence[str] | None = None, *, client: speech.SpeechClient | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m samajh.server.prepare", description=__doc__.split("\n")[0]
    )
    parser.add_argument("persona", nargs="?", choices=sorted(PERSONAS))
    parser.add_argument("out", type=Path)
    parser.add_argument("--loan", help="a drawn loan of the batch under --state, instead of a persona")
    parser.add_argument("--state", type=Path, help="the state directory whose ops/ holds the batch")
    parser.add_argument("--dry-run", action="store_true", help="print the script; make no Timbre call")
    args = parser.parse_args(argv)
    if (args.persona is None) == (args.loan is None):
        parser.error("name a PERSONA or --loan ID, not both")
    if args.loan is not None and args.state is None:
        parser.error("--loan needs --state")
    if args.loan is not None:
        from samajh.server.loanbook import LoanRefused

        try:
            persona = loan_persona(args.state, args.loan)
        except LoanRefused as refused:
            parser.error(f"{refused.code}: {refused.message}")
    else:
        persona = PERSONAS[args.persona]
    if args.dry_run:
        turns = script(persona, args.state)
        chars = sum(len(t["text"]) for t in turns)
        for turn in turns:
            print(f"{turn['file']}  {turn['answers']:<24} {turn['text']}")
        print(f"{len(turns)} turns, {chars} characters")
        return 0
    turns = prepare(persona, args.out, client or speech.live_client(speech.PATIENT), state=args.state)
    print(f"{args.persona or args.loan}: {len(turns)} turns written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
