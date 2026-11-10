"""Extras, not in the frozen input file: classifier labels for live failures (cache), 'हाँ भाई बोलो', and realistic takeover follow-ups."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import p2_r3_run as H
from samajh.dialogue.llm_fallback import LlmFallbackInterpreter, _Verdict
from samajh.dialogue import EndOfCall, step, start, RuleInterpreter
from samajh.types import Language
from samajh.clients._runtime import RetryPolicy
from samajh.clients.llm import LlmClient
client = LlmClient.from_env(timeout=3.0, retry=RetryPolicy(max_attempts=1), usd_cap=2.0)
st = H.Stats(); C = H.Counting(client, st)
li = LlmFallbackInterpreter(C, RuleInterpreter())
from samajh.dialogue.interpret import Expecting
q = "क्या दो-तीन मिनट बात कर सकते हैं?"
for t in ["mana nahi hai, bolo", "no no, continue", "फोन मत काटो, सुन रहा हूँ", "मैं मना नहीं कर रहा"]:
    msgs = li._messages(t, Expecting.go_ahead, q)
    r = C.complete(_Verdict, msgs, model=li._model, max_tokens=li._max_tokens)
    print("label", repr(t), r.value.label, "cache", r.cache_hit)
def play(turns, arm):
    interp = H.make(arm, st)
    interp.local.flags = []
    s, said = start(H.REC, Language("hi" if any('ऀ' <= ch <= 'ॿ' for ch in turns[0]) else "hi-en"), lender_name=H.LENDER)
    out = [said.text[:60]]
    for t in turns:
        s, said = step(s, t, interpreter=interp)
        if isinstance(said, EndOfCall): out.append(f"[{t}] END {said.outcome.value}"); break
        out.append(f"[{t}] {[l.key for l in said.lines]}")
    return out
for arm in ("rules", "failing", "live"):
    print(arm, play(["हाँ भाई बोलो", "1984"], arm)[-2:])
    # takeover then a realistic answer to the who-check
    print(arm, play(["हाँ जी", "1984", "हाँ", "मैं उनका बेटा बोल रहा हूँ, पापा बाहर चले गए", "मैं उनका बेटा हूँ"], arm)[-2:])
    print(arm, play(["हाँ जी", "1984", "हाँ", "पापा ने फ़ोन पकड़ा दिया, मुझे बताओ", "बताओ ना क्या पूछना है"], arm)[-2:])
print("llm", st.calls, "hits", st.hits, "usd", round(st.usd, 5))
