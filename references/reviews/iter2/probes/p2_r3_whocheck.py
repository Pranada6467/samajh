"""Who-check replies that restate the third party with a leading yes (not in the frozen set)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import p2_r3_run as H
from samajh.dialogue import EndOfCall, step, start
from samajh.types import Language
st_ = H.Stats()
for arm in ("rules", "failing"):
    interp = H.make(arm, st_)
    for take, reply in [("मैं उनका बेटा बोल रहा हूँ, पापा बाहर चले गए", "हाँ, मैं उनका बेटा, बोलो"),
                        ("रुको, मैं उनकी वाइफ हूँ, उन्होंने फोन दे दिया", "हाँ जी, मैं उनकी वाइफ"),
                        ("main unka dost, unhone phone diya", "haan, main dost hoon, bolo")]:
        interp.local.flags = []
        lang = "hi-en" if take.startswith("main") else "hi"
        s, said = start(H.REC, Language(lang), lender_name=H.LENDER)
        p = H.P[lang]; out = None
        for t in [p["yes"], p["year"], p["go"], take, reply, "पता नहीं"]:
            s, said = step(s, t, interpreter=interp)
            if isinstance(said, EndOfCall): out = "END " + said.outcome.value; break
            last = said.text
        print(arm, "|", reply, "->", out or (type(s.position).__name__ + " | " + last[:90]))
