import random, sys
sys.path.insert(0, "../../../../tests/dialogue")
from dialogue_kit import product, record
from p2_kit import play, LENDER
from samajh.dialogue import EndOfCall, Limits, start, step
from samajh.dialogue.interpret import Intent, Interpretation
from samajh.amounts import parse_amount
from samajh.types import Language, Speaker, Transcript

OPEN = ["हाँ जी, बोल रहा हूँ", "हाँ", "1984", "हाँ, एक बीमा लिया था", "बीमा है"]
log, o, st = play(OPEN + ["बावन हज़ार", "बावन हज़ार", "नहीं", "पचपन हज़ार", "हाँ", "लोन से", "एक बार", "मर्ज़ी", "पाँच लाख", "नहीं", "छह लाख", "हाँ"],
                  seconds={5: "बासठ हज़ार", 6: "बासठ हज़ार"})
for t in st.turns:
    if t.speaker is Speaker.bot and t.asks: print(f"{t.step.value:12s} {t.asks.value:10s} {t.text[:60]}")
for s in ["बावन हज़ार पाँच सौ एक", "पचास हज़ार एक", "दो हज़ार एक सौ एक", "एक लाख एक", "ग्यारह सौ एक", "पचास हज़ार एक सौ"]:
    print(s, "->", parse_amount(s))

TERMINAL = {Intent.decline, Intent.wants_human, Intent.other_language, Intent.call_later, Intent.wrong_person}
class Biased:
    def __init__(self, rng): self.rng = rng
    def interpret(self, text, *, language, expecting, question):
        pool = [i for i in Intent if i not in TERMINAL] if self.rng.random() < .97 else list(Intent)
        return Interpretation(intent=self.rng.choice(pool), amount_inr=self.rng.choice([None, 52000, 55000, 100]),
                              approx=self.rng.choice([None, None, (50000, 52000)]), year=self.rng.choice([None, 1984]),
                              figures=tuple(self.rng.sample([1, 52000, 7], self.rng.randint(0, 2))),
                              only_amount=self.rng.random() < .3, own_choice=self.rng.random() < .3,
                              callback=self.rng.choice([None, "time", "busy", "ask"]))
rec3 = record(product("P1"), product("P2"), product("P3"))
worst, outcomes = 0, {}
for seed in range(2000):
    rng = random.Random(seed)
    state, said = start(rec3, rng.choice(list(Language)), lender_name=LENDER, limits=Limits(max_bot_turns=10_000))
    n = 0
    while not isinstance(said, EndOfCall):
        state, said = step(state, "x", second_reading=rng.choice([None, "", "y"]), interpreter=Biased(rng)); n += 1
        assert n < 3000, seed
    worst = max(worst, n); outcomes[said.outcome.value] = outcomes.get(said.outcome.value, 0) + 1
    Transcript.model_validate_json(said.transcript.model_dump_json())
print("biased 2000 calls, 3 products, budget 10k: longest", worst, outcomes)
# default budget with the biased interpreter
over = 0
for seed in range(500):
    rng = random.Random(seed)
    state, said = start(rec3, Language.hi, lender_name=LENDER)
    while not isinstance(said, EndOfCall):
        state, said = step(state, "x", interpreter=Biased(rng))
    over += state.bot_turns > 60
print("default budget: calls over 60 bot utterances:", over)
