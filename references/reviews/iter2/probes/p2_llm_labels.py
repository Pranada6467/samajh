"""Which label the fallback LLM gave (cached replies from p2_refusals --llm), and the failure paths."""
import time
from samajh.clients.llm import LlmClient
from samajh.clients.errors import TransportError
from samajh.dialogue import llm_fallback as lf
from samajh.dialogue.interpret import Expecting
from samajh.dialogue.__main__ import effect_of
from samajh.types import Language
from p2_refusals import REFUSALS

client = LlmClient.from_env(usd_cap=0.05, timeout=10.0)
fb = lf.LlmFallbackInterpreter(client, timeout_s=None)
orig = fb._label
seen = []
fb._label = lambda m: (seen.append(orig(m)) or seen[-1])
for key, lang, text in REFUSALS:
    seen.clear()
    eff = effect_of(Language(lang), key, text, fb)
    if seen: print(f"{seen[0].value:12s} {eff:14s} {text}")

class Slow:
    def complete(self, *a, **k): time.sleep(4); raise AssertionError("late answer used")
class Broken:
    def complete(self, *a, **k): raise TransportError("down")
class Weird:
    def complete(self, *a, **k): raise ValueError("unexpected")
for name, llm in (("slow", Slow()), ("broken", Broken()), ("weird", Weird())):
    f = lf.LlmFallbackInterpreter(llm, timeout_s=2.5)
    for text in ("mere bete se baat karo, wahi sab dekhta hai", "ab bas, aur sawal nahi"):
        t = time.monotonic()
        try:
            r = f.interpret(text, language=Language.hi_en, expecting=Expecting.open, question="q")
            print(name, round(time.monotonic()-t,2), r.intent.value, "degraded", r.degraded, "|", text)
        except Exception as e:
            print(name, "RAISED", type(e).__name__, e)
