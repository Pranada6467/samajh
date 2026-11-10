"""Prepare a voiced call for the replay: a scripted customer's replies, spoken by Timbre.

    uv run python -m samajh.server.prepare PERSONA OUT [--dry-run]

PERSONA is one of `PERSONAS` below. The dialogue is run in text with the persona answering each
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
from dataclasses import dataclass
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
    record: str
    language: Language
    voice: str  # a Timbre v3.0 voice other than the bot's
    # Reply by the key of the bot's last line, then by its `asks` tag, then by its `step` tag
    # (a read-back by its step first), then by what the bot listens for ("yes_no", ...), then
    # "default".
    replies: Mapping[str, str]
    note: str

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

PERSONAS: dict[str, Persona] = {"hero": HERO, "informed": INFORMED, "third-party": THIRD_PARTY}


def script(persona: Persona) -> list[dict[str, str]]:
    """The persona's turns, in order, against the dialogue as it is now (word lists only)."""
    settings = load_settings()
    settings = settings.model_copy(
        update={"fallback": settings.fallback.model_copy(update={"enabled": False})}
    )
    call = samajh_factory(load_book(PACKAGED_DIR), settings)(
        {"record": persona.record, "language": persona.language.value, "fallback": "off"}
    )
    step, turns = call.start(), []
    while not step.say.end_call:
        if len(turns) >= MAX_TURNS:
            raise RuntimeError(f"{persona.record}: the call did not end within {MAX_TURNS} turns")
        reply = persona.reply(step.say)
        turns.append(
            {"file": f"{len(turns) + 1:02d}.wav", "answers": step.say.lines[-1].key or "", "text": reply}
        )
        step = call.step(step.state, Heard(text=reply, second=reply if step.say.second_reading else None))
    return turns


def customer_voice(persona: Persona, line_rate: int = 8000) -> Timbre:
    return Timbre(
        model="timbre-v3.0",
        voice=persona.voice,
        language=TTS_LANGUAGE[persona.language],
        sample_rate=line_rate,
        container="wav",
    )


def prepare(persona: Persona, out: Path, client: speech.SpeechClient, *, line_rate: int = 8000) -> list[dict]:
    """Write the turn audio and call.json. Idempotent: the same persona and dialogue give the
    same files, and every Timbre request is served from the cache after the first run."""
    from samajh.server.audio import to_line_pcm

    turns = script(persona)
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
        "params": {"record": persona.record, "language": persona.language.value},
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
    parser.add_argument("persona", choices=sorted(PERSONAS))
    parser.add_argument("out", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="print the script; make no Timbre call")
    args = parser.parse_args(argv)
    persona = PERSONAS[args.persona]
    if args.dry_run:
        turns = script(persona)
        chars = sum(len(t["text"]) for t in turns)
        for turn in turns:
            print(f"{turn['file']}  {turn['answers']:<24} {turn['text']}")
        print(f"{len(turns)} turns, {chars} characters")
        return 0
    turns = prepare(persona, args.out, client or speech.live_client(speech.PATIENT))
    print(f"{args.persona}: {len(turns)} turns written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
