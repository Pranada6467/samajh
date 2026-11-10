"""P2 round 4: a blind probe set for items 1, 2, 3, 4 and 6, and a runner for the three arms.

Written by the round 4 builder before any round 4 code change and before the first run. Typed text, not
speech. Record: tests/dialogue/fixtures/record_gold_loan.json (Ramesh, born 1984, one product).

    uv run python tests/dialogue/probes/p2_round4_fresh.py rules|failing|live [--show]

The setup turns before each probe are read by the word lists (so every arm reaches the same position);
the probe turn is read by the arm's interpreter. `live` uses the real classifier through `LlmClient`
(cached) at most 3 threads at a time and prints the request count and USD.
"""

from __future__ import annotations

import argparse
import re
import sys
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from samajh.dialogue import EndOfCall, RuleInterpreter, start, step
from samajh.types import Language, LoanRecord

HERE = Path(__file__).resolve().parent
RECORD = LoanRecord.model_validate_json((HERE.parent / "fixtures" / "record_gold_loan.json").read_text())
LENDER = "Udaharan Bank"
LEAK = re.compile(r"Udaharan|लोन|loan|बीमा|insurance|पॉलिसी|policy|एफडी|एफ़डी|\bFD\b|premium|प्रीमियम", re.IGNORECASE)

# Setup replies (word lists). "who" reaches the who-check by a plain takeover at the kind question.
SETUP = {
    "year": ["हाँ जी"],
    "recall": ["हाँ जी", "1984", "हाँ"],
    "kind": ["हाँ जी", "1984", "हाँ", "हाँ, एक बीमा लिया था"],
    "premium": ["हाँ जी", "1984", "हाँ", "हाँ, एक बीमा लिया था", "बीमा है"],
    "read_back": ["हाँ जी", "1984", "हाँ", "हाँ, एक बीमा लिया था", "बीमा है", "बावन हज़ार"],
    "source": ["हाँ जी", "1984", "हाँ", "हाँ, एक बीमा लिया था", "बीमा है", "बावन हज़ार", "हाँ, सही है"],
    "stop": ["हाँ जी", "1984", "हाँ", "हाँ, एक बीमा लिया था", "रहने दो"],
    "callback": ["हाँ जी", "1984", "हाँ", "हाँ, एक बीमा लिया था", "बाद में बात करते हैं"],
    "who": ["हाँ जी", "1984", "हाँ", "हाँ, एक बीमा लिया था", "मैं उनका भाई बोल रहा हूँ"],
    "opening": [],
}
WANT_LAST = {"stop": "stop_check.decline", "callback": "callback.when", "who": "right_party.reask"}

# (group, stage, text, expect). Expectations say what should happen for the person who speaks.
CASES: list[tuple[str, str, str, str]] = [
    # --- W: replies at the who-check (item 1) ------------------------------------------------------
    *(("W", "who", t, "resume") for t in [
        "जी हाँ, मैं ही रमेश हूँ", "हाँ, बोल रहा हूँ", "हाँ जी, मैं ही बोल रहा हूँ, बोलिए", "haan main hi hoon",
        "ji haan, Ramesh speaking", "हाँ भाई, मैं ख़ुद बोल रहा हूँ", "yes, it's me", "जी, मैं ही हूँ, पूछिए",
        "haan ji bolo", "हाँ हाँ, मैं रमेश", "हम्म हाँ जी",
    ]),
    *(("W", "who", t, "end") for t in [
        "हाँ, मैं उनका छोटा भाई हूँ, बोलो", "जी, मैं उनकी बहू", "haan main unka dost, aap bolo",
        "नहीं, वो तो बाहर गए हैं", "हाँ जी, मैं उनके साथ काम करता हूँ", "मैं सुरेश बोल रहा हूँ, उनका भाई",
        "हाँ, पर मैं उनकी तरफ़ से बात कर रही हूँ", "haan bolo, main unki beti hoon", "yes, I am his son, tell me",
        "हाँ, उनका ही फ़ोन है, मैं उठा रहा हूँ", "जी, मेरे पापा का लोन है, मैं देख लेता हूँ",
        "haan haan, papa ne bola baat karne ko", "मैं नहीं, उनकी वाइफ़ हूँ",
    ]),
    # --- T: mid-call takeovers (item 2): the next line is the who-check or an end -------------------
    ("T", "kind", "रुकिए, मैं उनकी पत्नी हूँ, आप क्या पूछ रहे थे?", "who"),
    ("T", "premium", "हैलो? हाँ, अब मैं बात कर रहा हूँ, क्या चाहिए", "who"),
    ("T", "read_back", "उनके बेटे बोल रहे हैं, पापा अभी निकल गए", "who"),
    ("T", "recall", "ये मेरी माँ का फ़ोन है, उनसे बाद में बात करना", "who"),
    ("T", "kind", "main unka bhanja hoon, mama bahar gaye", "who"),
    ("T", "premium", "hello? kaun? kya baat chal rahi thi?", "who"),
    ("T", "source", "sir abhi bahar gaye hain, main ghar ka naukar hoon", "who"),
    ("T", "read_back", "ये मेरे ससुर जी का लोन है, मुझसे बात कर लो", "who"),
    ("T", "kind", "मेरे हस्बैंड ने लिया था सब, मुझे कुछ नहीं पता", "who"),
    ("T", "recall", "hello hello, abhi main bol rahi hoon, unki wife", "who"),
    ("T", "stop", "हाँ, मैं उनका भाई हूँ, बोलिए", "who"),
    ("T", "callback", "मैं उनका बेटा हूँ, पापा शाम को आएँगे", "who"),
    ("T", "premium", "वो चले गए, फ़ोन मुझे पकड़ा दिया", "who"),
    ("T", "source", "मैं रमेश नहीं, उनका पड़ोसी हूँ", "who"),
    ("T", "kind", "hello? ye kiska phone hai? kya puch rahe ho?", "who"),
    ("T", "read_back", "this is his wife speaking, he just left", "who"),
    ("T", "recall", "mere papa ka loan hai, unhone mujhe phone de diya", "who"),
    ("T", "premium", "अरे सुनिए, मैं उनका ड्राइवर, साहब मीटिंग में चले गए", "who"),
    ("T", "kind", "ab mujhse baat karo, main unka bada beta hoon", "who"),
    ("T", "callback", "abhi wo nahi hain, main unki behen bol rahi hoon", "who"),
    ("T", "stop", "nahi nahi, main unka cousin hoon", "who"),
    ("T", "source", "हाँ, मैं उनका मुनीम हूँ, सब हिसाब मैं देखता हूँ", "who"),
    # controls: genuine answers ("plain": no who-check wanted; "ambiguous": a who-check is the accepted cost)
    ("Tc", "premium", "बावन हज़ार दिए थे", "plain"),
    ("Tc", "kind", "एक बीमा है, एजेंट ने बताया था", "plain"),
    ("Tc", "read_back", "हाँ, सही है", "plain"),
    ("Tc", "source", "लोन में से ही कट गया था", "plain"),
    ("Tc", "kind", "insurance tha, unhone bola zaroori hai", "plain"),
    ("Tc", "kind", "मेरी पत्नी के कहने पर लिया था, बीमा है", "ambiguous"),
    ("Tc", "recall", "मेरे बेटे की पढ़ाई के लिए लोन लिया, साथ में बीमा भी", "ambiguous"),
    ("Tc", "premium", "pata nahi, mere bhai ne bhara tha form", "ambiguous"),
    # --- Y: the birth year, genuine borrowers born 1984 and claimants with another year (item 3) -----
    *(("Y", "year", t, "pass") for t in [
        "उन्निस सौ चौरासी", "उन्नीस सो चौरासी", "उनीस सौ चौरासी", "उन्नीस सौ चोरासी", "उन्नीस सौ चौरासि",
        "उन्नीस सौ चौरासी में", "unnis sau chaurasee", "unnees sau chorasi", "unnis sau chaurasii",
        "nineteen eighty four", "उन्नीस सौ चौरासी, पक्का", "उन्नीस सौ चौराशी", "उन्नीस सौ चौरासी जी",
        "उन्नसी सौ चौरासी", "उन्नीस सौ चौंरासी", "उन्नीस सौ छौरासी",
    ]),
    ("Y", "year", "उन्नीस सौ चौरस", "not_ended"),
    *(("Y", "year", t, "fail") for t in [
        "उन्नीस सौ पचासी", "उन्नीस सौ पचासि", "उन्नीस सौ तिरासि", "उन्नीस सौ चौरानवे", "unnis sau pachasi",
        "उन्नीस सौ चौबीस", "उन्नीस सौ अस्सी",
    ]),
    # --- R: refusals at the opening (item 4) --------------------------------------------------------
    *(("R", "opening", t, "declined") for t in [
        "मुझे किसी से कोई बात नहीं करनी", "नहीं भाई, अभी बात नहीं करनी, फ़ोन रखो", "बात नहीं करना है मुझे, रख दीजिए",
        "nahi karni baat, rakho phone", "mujhe baat nahi karni hai", "I don't want to talk, please hang up",
        "रहने दो, नहीं करनी कोई बात", "kuch nahi sunna mujhe, phone rakh do", "नहीं चाहिए कुछ, रखिए",
        "फ़ोन काटो, बात नहीं करनी", "na baba, koi baat nahi karni, bye",
    ]),
    *(("R", "opening", t, "do_not_call") for t in [
        "दोबारा फ़ोन मत करना, नंबर हटा दो", "mera number list se hata do, phir call mat karna",
        "मुझे कॉल मत किया करो", "don't call this number again",
    ]),
    *(("R", "opening", t, "wrong_party") for t in [
        "नहीं", "नहीं, वो घर पर नहीं हैं, बाद में करना", "रॉन्ग नंबर है, फ़ोन रखो", "नहीं जी, मैं उनकी बेटी हूँ, बात नहीं करनी",
        "nahi, wo bahar gaye hain, phone rakho", "ना", "वो नहीं हैं, बात नहीं हो सकती",
    ]),
    ("R", "kind", "अब बस, कोई बात नहीं करनी", "declined"),
    ("R", "premium", "nahi karni mujhe aur baat, rakho", "declined"),
    ("R", "read_back", "बात नहीं करनी अब, फ़ोन रखिए", "declined"),
    # --- C: the call-back question and "I don't remember" at the year (item 6) ----------------------
    *(("C", "callback", t, "now") for t in [
        "नहीं नहीं, अभी पूछ लीजिए", "बाद में नहीं, अभी कर लो", "nahi, abhi karo", "na na, abhi hi kar lijiye",
        "अभी ठीक है, बाद में नहीं", "later nahi, abhi chalega", "नहीं, अभी कर लेते हैं",
        "abhi kar lo, baad mein time nahi milega", "अभी ही कर लीजिए", "nahin nahin, abhi",
    ]),
    *(("C", "callback", t, "later") for t in [
        "अभी नहीं, कल शाम", "abhi nahi", "नहीं, अभी बिज़ी हूँ", "कल सुबह दस बजे", "abhi nahi, baad mein",
    ]),
    *(("C", "year", t, "reask") for t in [
        "साल तो याद नहीं", "वो तो याद नहीं आ रहा", "पता नहीं, वो तो भूल गया", "saal? wo toh yaad nahi",
        "वो साल याद नहीं", "yaad nahi abhi",
    ]),
    *(("C", "year", t, "wrong_party") for t in ["वो बाहर गए हैं", "पता नहीं, वो घर पर नहीं हैं", "wo toh bahar gaye hain"]),
]

RULES = RuleInterpreter()


def language_of(text: str) -> Language:
    return Language.hi if re.search(r"[ऀ-ॿ]", text) else Language.hi_en


def keys(said) -> list[str]:
    lines = said.utterance.lines if isinstance(said, EndOfCall) else said.lines
    return [line.key for line in lines]


def text_of(said) -> str:
    return said.utterance.text if isinstance(said, EndOfCall) else said.text


def run_case(case, interpreter) -> dict:
    group, stage, text, expect = case
    state, said = start(RECORD, language_of(text), lender_name=LENDER)
    for setup in SETUP[stage]:
        state, said = step(state, setup, interpreter=RULES)
        assert not isinstance(said, EndOfCall), (case, setup, keys(said))
    if stage in WANT_LAST:
        assert keys(said)[-1] == WANT_LAST[stage], (case, keys(said))
    position = type(state.position).__name__
    state, said = step(state, text, interpreter=interpreter)
    ended = isinstance(said, EndOfCall)
    row = {
        "group": group, "stage": stage, "text": text, "expect": expect, "at": position,
        "outcome": said.outcome.value if ended else None, "next": keys(said)[-1],
        "leak": bool(LEAK.search(text_of(said))) and not ended, "degraded": bool(state.degraded_turns),
        "confirmed": said.speaker_confirmed if ended else state.speaker_confirmed,
    }
    row["ok"] = judge(row)
    return row


def judge(row: dict) -> bool:
    expect, outcome, nxt = row["expect"], row["outcome"], row["next"]
    if expect == "resume":
        return outcome is None and nxt != "right_party.reask"
    if expect == "end":
        return outcome is not None and not row["leak"]
    if expect == "who":
        return (nxt == "right_party.reask" and outcome is None) or outcome is not None
    if expect == "plain":
        return nxt != "right_party.reask" and outcome is None
    if expect == "ambiguous":
        return outcome is None or outcome == "wrong_party"
    if expect == "pass":
        return outcome is None and nxt != "second_check.reask"
    if expect == "not_ended":
        return outcome is None
    if expect == "fail":
        return outcome == "second_check_failed"
    if expect in ("declined", "do_not_call", "wrong_party"):
        # At the opening a refusal must not mark the speaker confirmed; after the year it is.
        return outcome == expect and not (row["stage"] == "opening" and row["confirmed"])
    if expect == "now":
        return outcome is None
    if expect == "later":
        return outcome == "call_back_later"
    if expect == "reask":
        return outcome is None and nxt == "second_check.reask"
    raise ValueError(expect)


class Counting:
    def __init__(self, inner):
        self.inner, self.lock = inner, threading.Lock()
        self.requests = self.hits = 0
        self.usd = 0.0

    def complete(self, *args, **kwargs):
        reply = self.inner.complete(*args, **kwargs)
        with self.lock:
            self.requests += 1
            self.hits += bool(getattr(reply, "cache_hit", False))
            self.usd += getattr(reply, "usd", 0.0) or 0.0
        return reply


class Raising:
    def complete(self, *args, **kwargs):
        raise RuntimeError("probe: classifier down")


def build(arm: str):
    if arm == "rules":
        return RULES, None
    from samajh.dialogue.llm_fallback import LlmFallbackInterpreter

    if arm == "failing":
        return LlmFallbackInterpreter(Raising()), None
    from samajh.clients._runtime import RetryPolicy
    from samajh.clients.llm import LlmClient

    counting = Counting(LlmClient.from_env(usd_cap=1.0, timeout=10.0, retry=RetryPolicy(max_attempts=1)))
    return LlmFallbackInterpreter(counting, timeout_s=10.0), counting


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("arm", choices=("rules", "failing", "live"))
    parser.add_argument("--show", action="store_true", help="print every row, not only the failures")
    args = parser.parse_args()
    import logging

    logging.disable(logging.WARNING)
    interpreter, counting = build(args.arm)
    with ThreadPoolExecutor(max_workers=3 if args.arm == "live" else 1) as pool:
        rows = list(pool.map(lambda case: run_case(case, interpreter), CASES))
    by = defaultdict(Counter)
    for row in rows:
        by[(row["group"], row["expect"])]["n"] += 1
        by[(row["group"], row["expect"])]["ok"] += row["ok"]
    print(f"arm={args.arm} n={len(rows)}")
    for (group, expect), count in sorted(by.items()):
        print(f"  {group:3} {expect:12} {count['ok']:3} of {count['n']:3} as expected")
    for row in rows:
        if args.show or not row["ok"]:
            mark = "  " if row["ok"] else "X "
            print(f"{mark}{row['group']:3} {row['stage']:9} {row['expect']:11} -> {row['outcome'] or row['next']}"
                  f"{' LEAK' if row['leak'] else ''} | {row['text']}")
    if counting is not None:
        print(f"classifier requests: {counting.requests} ({counting.hits} from cache), USD {counting.usd:.5f}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
