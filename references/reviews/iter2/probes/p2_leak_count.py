"""Record-dependent lines: the number of products in the record changes what the bot says,
including to a customer who never named anything."""
import sys
sys.path.insert(0, "../../../../tests/dialogue")
from dialogue_kit import product, record
from p2_kit import play, dump
from samajh.types import LoanRecord

one = record(product("P1"))
two = record(product("P1"), product("P2", premium_inr=9000))
try:
    zero = LoanRecord.model_validate(one.model_dump(mode="json") | {"products": []})
except Exception as e:
    zero = None; print("zero products rejected:", type(e).__name__)
script = ["हाँ जी, बोल रहा हूँ", "हाँ", "1984",
          "हम्म",            # recall: unclear
          "पता नहीं क्या",     # recall reask -> dont_know -> follow-up
          "हाँ शायद कुछ बोले थे"]  # follow-up: anything that is not a no -> product questions
for name, rec in (("one", one), ("two", two)) + ((("zero", zero),) if zero else ()):
    log, outcome, _ = play(script, record=rec)
    print(f"--- {name} product(s): {outcome}"); print(dump(log[-3:]))
script2 = ["हाँ जी, बोल रहा हूँ", "हाँ", "1984", "हाँ, एक बीमा लिया था बस"]
for name, rec in (("one", one), ("two", two)):
    log, outcome, st = play(script2 + ["बीमा है"] + ["दस हज़ार"] + ["हाँ"] + ["लोन से कटा"] + ["एक बार"] + ["ज़रूरी था"] + ["नहीं बताया"] + ["पता नहीं"]*4, record=rec)
    print(f"--- {name}: customer named ONE thing"); print(dump([l for l in log if 'रिकॉर्ड' in l[1] or 'record' in l[1]]))
