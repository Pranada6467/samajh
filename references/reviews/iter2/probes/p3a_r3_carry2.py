"""P3a r3 addendum: the carried-premium fix (`_carries`) on fresh recall replies, real gpt-6-luna.

    uv run python references/reviews/iter2/probes/p3a_r3_carry2.py

The premium question is never asked; the recall reply gives a premium; the bot reads 41,300 back and
the customer says "हाँ जी।". Record premium 41,300 (iter1 BASE). Gold before the run:
  take     the premium is taken back or replaced in the same reply -> never clear with premium stated
  product  only the product is corrected; the amount stands -> my reading: premium may carry, case refer
  informed emphasis / filler / apology, no change, 2+ clauses -> carries and ends clear
  oneclause unpunctuated withdrawal -> expected unprotected (failure 2)
  regress  the four r3 withdrawals (seen by the builder) -> not clear
Then the summary note line on two calls (toward-record kind correction; plain BASE).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "iter1" / "probes"))
import extractor_attacks as ea  # noqa: E402
from p3a_r3_carry import RB41, rows  # noqa: E402

from samajh.clients.llm import LlmClient  # noqa: E402
from samajh.pipeline import WithoutTemperature, run_text, takes_temperature  # noqa: E402
from samajh.rules import summarise  # noqa: E402

CASES = [
    ("take", "एक बीमा लिया था, इकतालीस हज़ार तीन सौ का, ग़लत बोल गया, रकम याद नहीं।"),
    ("take", "बीमा था, इकतालीस हज़ार तीन सौ, एक मिनट, नहीं, वो तो प्रोसेसिंग फ़ीस थी।"),
    ("take", "insurance liya, iske 41,300, nahi yaar, ye amount galat hai, pata nahi."),
    ("take", "एक बीमा, इकतालीस हज़ार तीन सौ का बोला था, मतलब नहीं, ठीक से नहीं पता।"),
    ("take", "बीमा लिया था, 41,300 का, wait, नहीं, amount मुझे याद नहीं।"),
    ("take", "एक पॉलिसी ली थी, इकतालीस हज़ार तीन सौ की, छोड़िए, रकम का अंदाज़ा नहीं।"),
    ("take", "बीमा लिया, इकतालीस हज़ार तीन सौ, ना ना, वो लोन का चार्ज था, बीमे का नहीं पता।"),
    ("take", "इकतालीस हज़ार तीन सौ का बीमा, नहीं, उससे ज़्यादा था।"),
    ("take", "policy li thi, 41,300 ki, actually galat, kitne ki thi yaad nahi."),
    ("product", "बीमा लिया था, नहीं, एफ़डी, इकतालीस हज़ार तीन सौ की।"),
    ("informed", "जी, एक बीमा लिया था, इकतालीस हज़ार तीन सौ का।"),
    ("informed", "हाँ, बीमा लिया था, इकतालीस हज़ार तीन सौ का, हाँ जी।"),
    ("informed", "देखिए, लोन के साथ एक बीमा था, इकतालीस हज़ार तीन सौ रुपये का।"),
    ("informed", "insurance liya tha, 41,300 ka, bas itna hi."),
    ("informed", "एक बीमा, इकतालीस हज़ार तीन सौ वाला, और कुछ नहीं।"),
    ("informed", "माफ़ कीजिए, आवाज़ कट रही थी, एक बीमा लिया था, इकतालीस हज़ार तीन सौ का।"),
    ("informed", "मतलब, एक बीमा लिया, इकतालीस हज़ार तीन सौ का, बिल्कुल इतना ही।"),
    ("informed", "haan ji, ek insurance tha, 41,300 rupaye ka, haan haan."),
    ("oneclause", "बीमा लिया था इकतालीस हज़ार तीन सौ का नहीं नहीं पता नहीं कितने का"),
    ("oneclause", "insurance liya 41,300 ka ruko yaad nahi"),
    ("regress", "एक बीमा लिया था, इकतालीस हज़ार तीन सौ, नहीं नहीं, पता नहीं कितने का।"),
    ("regress", "एक बीमा लिया था, इकतालीस हज़ार तीन सौ का, नहीं, याद नहीं ठीक से।"),
    ("regress", "insurance liya tha, 41,300 ka, ruko, nahi, pakka nahi pata kitne ka."),
    ("regress", "बीमा लिया था, इकतालीस हज़ार तीन सौ, अरे नहीं, वो तो लोन की किस्त थी।"),
]


def main() -> int:
    client = LlmClient.from_env(usd_cap=0.08)
    llm = client if takes_temperature(client._model) else WithoutTemperature(client)
    for group, reply in CASES:
        transcript, _ = ea.build(rows(reply, None, RB41, "हाँ जी।", None))
        run = run_text(transcript, ea.record(), llm, max_workers=6)
        prem = run.beliefs.products[0].premium_inr
        res = run.result
        checks = [s.change for s in run.extraction.slots if s.check and s.kind.value == "recall"]
        rs = sorted({f.reason.value for f in res.all_flags()} | {f"gap:{g.rule_id.value}:{g.reason.value}"
                                                                for g in res.all_gaps()})
        if group in ("take", "oneclause", "regress"):
            ok = not (res.tier.value == "clear" and type(prem).__name__ == "Stated")
        elif group == "informed":
            ok = res.tier.value == "clear"
        else:
            ok = res.tier.value != "clear"
        print(f"{'ok ' if ok else 'BAD'} [{group:9}] {res.tier.value:17} premium={type(prem).__name__}"
              f"({getattr(prem, 'value', None)}, {getattr(getattr(prem, 'reason', None), 'value', '')}) "
              f"check={checks} | {reply}\n      {rs}")
    print("== note line ==")
    for name, reply in (("kind corrected toward the record", "डिपॉज़िट है, ओह नहीं, बीमा है जी।"),
                        ("no correction (BASE)", None)):
        rws = ea.BASE if reply is None else [
            (r[0], r[1], r[2], reply, r[4]) if r[1] == "kind" else r for r in ea.BASE]
        transcript, _ = ea.build(rws)
        run = run_text(transcript, ea.record(), llm, max_workers=6)
        s = summarise(ea.record(), run.result)
        print(f"{name}: result tier {run.result.tier.value}, summary tier {s.tier.value}, "
              f"self_corrections={len(run.result.products[0].self_corrections)}")
        for line in s.lines:
            print(f"   tier={line.tier.value} note={line.note} title={line.title!r} quote={line.quote!r}")
    print(f"spent {client.spent_usd:.4f} USD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
