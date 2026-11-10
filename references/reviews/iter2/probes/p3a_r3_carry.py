"""P3a re-verification (round 3): the carried premium (addition A), scripted model, offline.

    uv run python references/reviews/iter2/probes/p3a_r3_carry.py

The premium is never asked; the customer gives an amount in open recall and the bot reads a
premium back. Record premium 41,300. Gold written before the run.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "iter1" / "probes"))
import extractor_attacks as ea  # noqa: E402
from p3a_r3_orders import Scripted, rb  # noqa: E402

from samajh.extract import extract  # noqa: E402
from samajh.rules import evaluate, to_beliefs  # noqa: E402

RQ = "लोन के साथ आपने क्या-क्या लिया, और कितने का?"
RB41 = "इकतालीस हज़ार तीन सौ, यानी 41,300 रुपये, सही है?"
RB60 = "साठ हज़ार, यानी 60,000 रुपये, सही है?"


def rows(recall_reply, amount_span, rb_text, rb_reply, rb_out):
    rest = [r for r in ea.BASE if r[1] != "premium" and r[0] != "open_recall" and r[0] != "read_back"]
    rec = ("open_recall", None, RQ, recall_reply,
           {"items": [{"span": "एक बीमा", "kind": "insurance", "amount_span": amount_span}], "took_nothing": False})
    return [rec, *rest, ("read_back", "premium", rb_text, rb_reply, rb_out)]


CASES = [
    ("right figure, confirmed", rows("एक बीमा लिया था, इकतालीस हज़ार तीन सौ का।", "इकतालीस हज़ार तीन सौ",
                                     RB41, "हाँ जी।", rb("", True)), {"clear"}),
    ("wrong figure (60,000), confirmed", rows("एक बीमा लिया था, साठ हज़ार का।", "साठ हज़ार",
                                              RB60, "हाँ जी।", rb("", True)), {"refer"}),
    ("right figure, read-back rejected", rows("एक बीमा लिया था, इकतालीस हज़ार तीन सौ का।", "इकतालीस हज़ार तीन सौ",
                                              RB41, "नहीं जी।", rb("", False)), {"incomplete"}),
    ("two amounts in recall reply (loan + premium), confirmed",
     rows("तीन लाख का लोन, और एक बीमा लिया था, इकतालीस हज़ार तीन सौ का।", "इकतालीस हज़ार तीन सौ",
          RB41, "हाँ जी।", rb("", True)), {"incomplete"}),
    ("recall said 60,000, bot reads back 41,300, yes", rows("एक बीमा लिया था, साठ हज़ार का।", "साठ हज़ार",
                                                           RB41, "हाँ जी।", rb("", True)), {"incomplete"}),
    ("recall NEGATES the figure ('41,300 का नहीं था'), bot reads 41,300, yes",
     rows("एक बीमा लिया था, इकतालीस हज़ार तीन सौ का नहीं था।", "इकतालीस हज़ार तीन सौ",
          RB41, "हाँ जी।", rb("", True)), {"incomplete", "refer"}),
    ("recall hedged ('शायद 41,300'), bot reads 41,300, yes",
     rows("एक बीमा लिया था, शायद इकतालीस हज़ार तीन सौ का।", "इकतालीस हज़ार तीन सौ",
          RB41, "हाँ जी।", rb("", True)), {"clear", "incomplete", "understanding_gap"}),
    ("recall: 'at least 41,300', bot reads 41,300, yes",
     rows("एक बीमा लिया था, कम से कम इकतालीस हज़ार तीन सौ का।", "इकतालीस हज़ार तीन सौ",
          RB41, "हाँ जी।", rb("", True)), {"incomplete"}),
    ("recall: amount said then taken back in same reply, bot reads 41,300, yes",
     rows("एक बीमा लिया था, इकतालीस हज़ार तीन सौ, नहीं नहीं, पता नहीं कितने का।", "इकतालीस हज़ार तीन सौ",
          RB41, "हाँ जी।", rb("", True)), {"incomplete"}),
]


def main() -> int:
    bad = 0
    for name, rws, want in CASES:
        transcript, outputs = ea.build(rws)
        rec = ea.record()
        raw = extract(transcript, rec, Scripted(outputs))
        b = to_beliefs(raw, rec, transcript)
        res = evaluate(rec, b)
        prem = b.products[0].premium_inr
        rs = sorted({f.reason.value for f in res.all_flags()} | {f"gap:{g.rule_id.value}:{g.reason.value}"
                                                                for g in res.all_gaps()})
        ok = res.tier.value in want
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {res.tier.value:17} want {sorted(want)} | {name}\n"
              f"      premium={type(prem).__name__}({getattr(prem, 'value', None)!r}, "
              f"reason={getattr(getattr(prem, 'reason', None), 'value', None)}, "
              f"approx={getattr(prem, 'approximate', None)}) {rs}")
    print(f"\n{len(CASES)} cases, {bad} outside gold")
    return 0


if __name__ == "__main__" and not any(a.startswith("--llm") for a in sys.argv):
    raise SystemExit(main())


def real_model() -> int:
    """`--llm`: the withdrawn-amount recall case and its premium-question twin through gpt-6-luna."""
    from samajh.clients.llm import LlmClient
    from samajh.pipeline import WithoutTemperature, run_text, takes_temperature

    client = LlmClient.from_env(usd_cap=0.05)
    llm = client if takes_temperature(client._model) else WithoutTemperature(client)
    withdrawn = "एक बीमा लिया था, इकतालीस हज़ार तीन सौ, नहीं नहीं, पता नहीं कितने का।"
    carried = rows(withdrawn, None, RB41, "हाँ जी।", None)
    twin = [r if r[1] != "premium" or r[0] == "read_back" else
            (r[0], r[1], r[2], "इकतालीस हज़ार तीन सौ, नहीं नहीं, पता नहीं कितने का।", r[4]) for r in ea.BASE]
    for name, rws in (("carried from recall", carried), ("asked as the premium question", twin)):
        transcript, _ = ea.build(rws)
        run = run_text(transcript, ea.record(), llm, max_workers=6)
        prem = run.beliefs.products[0].premium_inr
        checks = [(s.kind.value, s.change) for s in run.extraction.slots if s.check]
        print(f"{name}: tier={run.result.tier.value} premium={type(prem).__name__}({getattr(prem, 'value', None)}) "
              f"checks={checks}")
    print(f"spent {client.spent_usd:.4f} USD")
    return 0


if __name__ == "__main__" and "--llm" in sys.argv[1:2]:
    real_model()


def real_model_more() -> int:
    """`--llm2`: more carried-premium withdrawals through gpt-6-luna (gold: never clear)."""
    from samajh.clients.llm import LlmClient
    from samajh.pipeline import WithoutTemperature, run_text, takes_temperature

    client = LlmClient.from_env(usd_cap=0.05)
    llm = client if takes_temperature(client._model) else WithoutTemperature(client)
    for reply in ("एक बीमा लिया था, इकतालीस हज़ार तीन सौ का, नहीं, याद नहीं ठीक से।",
                  "insurance liya tha, 41,300 ka, ruko, nahi, pakka nahi pata kitne ka.",
                  "बीमा लिया था, इकतालीस हज़ार तीन सौ, अरे नहीं, वो तो लोन की किस्त थी।"):
        transcript, _ = ea.build(rows(reply, None, RB41, "हाँ जी।", None))
        run = run_text(transcript, ea.record(), llm, max_workers=6)
        prem = run.beliefs.products[0].premium_inr
        checks = [s.change for s in run.extraction.slots if s.check and s.kind.value == "recall"]
        print(f"tier={run.result.tier.value} premium={type(prem).__name__}({getattr(prem, 'value', None)}) "
              f"recall check={checks} | {reply}")
    print(f"spent {client.spent_usd:.4f} USD")
    return 0


if __name__ == "__main__" and "--llm2" in sys.argv:
    real_model_more()
