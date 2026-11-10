"""Read-back figures, two readings, state round trip, random termination and Transcript tags (verifier, iter 2)."""

from __future__ import annotations

import random
import sys

sys.path.insert(0, "../../../../tests/dialogue")
from dialogue_kit import product, record  # noqa: E402
from p2_kit import LENDER, RECORD, dump, play  # noqa: E402

from samajh.dialogue import CallState, EndOfCall, Limits, start, step  # noqa: E402
from samajh.dialogue.interpret import Intent, Interpretation  # noqa: E402
from samajh.types import Language, Question, Speaker, Transcript  # noqa: E402

OPEN = ["हाँ जी, बोल रहा हूँ", "हाँ", "1984", "हाँ, एक बीमा लिया था", "बीमा है"]

print("== read-back figures")
cases = {
    "301 said": (OPEN + ["तीन सौ एक दिए"], {}),
    "readings disagree twice": (OPEN + ["बावन हज़ार", "बावन हज़ार"], {5: "बासठ हज़ार", 6: "बासठ हज़ार"}),
    "v3 misformat first": (OPEN + ["3,02,000", "3,02,000"], {5: "तीन लाख दो सौ", 6: "तीन लाख दो सौ"}),
    "yes + other figure at read-back": (OPEN + ["बावन हज़ार", "हाँ, पचपन हज़ार"], {}),
    "premium and cover in one": (OPEN + ["बावन हज़ार दिए, पाँच लाख का कवर है"], {}),
    "loan amount said": (OPEN + ["पाँच लाख का लोन था उसी में से"], {}),
    "approx": (OPEN + ["पचास बावन हज़ार के आसपास"], {}),
    "approx 2": (OPEN + ["लगभग पचास हज़ार"], {}),
    "only second has figure at restate": (OPEN + ["बावन हज़ार", "नहीं", "हम्म"], {7: "पचपन हज़ार"}),
}
for name, (turns, seconds) in cases.items():
    log, outcome, _ = play(turns, seconds=seconds)
    rb = [t for w, t, k in log if w == "BOT" and any(x.startswith("read_back") or x == "premium.say_again" for x in k)]
    print(f"-- {name}: {outcome}")
    for t in rb:
        print("   BOT:", t)
    if not rb:
        print("   last BOT:", log[-1][1])

print("\n== cover two readings (second ignored at the cover question?)")
turns = OPEN + ["बावन हज़ार", "हाँ", "लोन से", "एक बार", "मेरी मर्ज़ी", "3,02,000 का कवर"]
log, outcome, _ = play(turns, seconds={11: "तीन लाख दो सौ का कवर"})
print("  ", log[-1][1])

print("\n== state round trip at every step of a call")
turns = OPEN + ["बावन हज़ार", "हाँ", "लोन से कटा", "एक बार", "ज़रूरी था", "नहीं बताया", "पाँच लाख", "हाँ",
                "दो साल", "पता नहीं", "वापस नहीं", "साइन किया"]
state, said = start(RECORD, Language.hi, lender_name=LENDER)
ok = True
for t in turns:
    state = CallState.model_validate_json(state.model_dump_json())
    a = step(state, t)
    b = step(CallState.model_validate_json(state.model_dump_json()), t)
    ok &= a[0] == b[0]
    state, said = a
    if isinstance(said, EndOfCall):
        break
print("   resumed state identical at every step:", ok, "| outcome", said.outcome.value)
tr = Transcript.model_validate_json(said.transcript.model_dump_json())
print("   Transcript re-validates:", len(tr.turns), "turns")
for turn in tr.turns:
    if turn.speaker is Speaker.bot and turn.asks is not None:
        print(f"   {turn.step.value:18s} {turn.asks.value:18s} {turn.product_id} {turn.text[:50]}")

print("\n== random interpreter: every call ends inside the budget")
class RandomInterp:
    def __init__(self, rng): self.rng = rng
    def interpret(self, text, *, language, expecting, question):
        intent = self.rng.choice(list(Intent))
        amount = self.rng.choice([None, None, 52000, 55000, 100, 999_999_999])
        approx = self.rng.choice([None, None, (50000, 52000)])
        return Interpretation(intent=intent, amount_inr=amount, approx=approx,
                              year=self.rng.choice([None, 1984, 84, 1985]),
                              figures=tuple(self.rng.sample([1, 52000, 7], self.rng.randint(0, 2))),
                              only_amount=self.rng.random() < .3, own_choice=self.rng.random() < .3,
                              callback=self.rng.choice([None, "time", "busy", "ask"]))
rec3 = record(product("P1"), product("P2"), product("P3"))
worst, outcomes = 0, {}
for seed in range(3000):
    rng = random.Random(seed)
    lim = Limits(max_bot_turns=10_000)
    state, said = start(rec3, rng.choice(list(Language)), lender_name=LENDER, limits=lim)
    n = 0
    while not isinstance(said, EndOfCall):
        state, said = step(state, "x", second_reading=rng.choice([None, "", "y"]), interpreter=RandomInterp(rng))
        n += 1
        if n > 5000:
            print("   RUNAWAY seed", seed); break
    worst = max(worst, n)
    outcomes[said.outcome.value] = outcomes.get(said.outcome.value, 0) + 1
    Transcript.model_validate_json(said.transcript.model_dump_json())
print("   3000 random calls, budget 10,000: longest", worst, "customer turns;", outcomes)
