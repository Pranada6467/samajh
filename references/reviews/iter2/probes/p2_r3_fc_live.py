"""False claimants, flow adapted to the first-person path: claim, then answer whatever is asked (go-ahead: yes; year: the case's year)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import p2_r3_run as H
from samajh.dialogue import EndOfCall, step, start
from samajh.types import Language
cases = [c for c in json.loads((H.HERE / "p2_r3_inputs.json").read_text()) if c["kind"].startswith("false_")]
out = []
for arm in sys.argv[1:]:
    st_ = H.Stats(); interp = H.make(arm, st_)
    for c in cases:
        interp.local.flags = []
        s, said = start(H.REC, Language(c["lang"]), lender_name=H.LENDER)
        log = [("BOT", H.keys(said), said.text)]; end = None; years = [c["text"], "1984"]
        for t in [c["first"]] + ["?"] * 5:
            pos = type(s.position).__name__
            if t == "?":
                if pos == "AtBirthYear": t = years.pop(0) if years else "1984"
                elif pos == "AtGoAhead": t = "हाँ" if c["lang"] == "hi" else "haan"
                else: break
            s, said = step(s, t, interpreter=interp); log.append(("YOU", [], t))
            if isinstance(said, EndOfCall): log.append(("BOT", H.keys(said.utterance), said.utterance.text)); end = said.outcome.value; break
            log.append(("BOT", H.keys(said), said.text))
        bot = [x for x in log if x[0] == "BOT"]
        row = dict(arm=arm, id=c["id"], kind=c["kind"], first=c["first"], year=c["text"], end=end, pos=None if end else type(s.position).__name__,
                   lender_named=any("Udaharan" in x[2] for x in bot), loan_named=any(H.LEAK["loan"].search(x[2]) for x in bot),
                   years_used=2 - len(years), log=log)
        out.append(row)
        print(arm, c["kind"], "|", c["first"], "|", c["text"], "->", end or row["pos"], "| lender", row["lender_named"], "loan", row["loan_named"], "| years said", row["years_used"])
    print(arm, "llm", st_.calls, "hits", st_.hits, "usd", round(st_.usd, 5))
(H.HERE / "p2_r3_out_fc.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n", encoding="utf-8")
