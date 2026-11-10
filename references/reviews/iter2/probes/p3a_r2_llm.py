"""P3a re-verification (round 2): the real extraction model on the retraction and over-firing replies
of p3a_r2_chain.py. Uses samajh/clients/llm.py (cache, single flight, ledger); cap 0.15 USD.

    uv run python references/reviews/iter2/probes/p3a_r2_llm.py

The chain probe scripts the adversarial model reading (the model quotes the clause that was taken
back). This probe asks what `openai/gpt-6-luna` actually returns for the same replies inside the
informed BASE call, then runs the rules. `want` is the chain probe's.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "iter1" / "probes"))
import extractor_attacks as ea  # noqa: E402
import p3a_r2_chain as chain  # noqa: E402

from samajh.clients.llm import LlmClient  # noqa: E402
from samajh.pipeline import WithoutTemperature, run_text, takes_temperature  # noqa: E402


def main() -> int:
    client = LlmClient.from_env(usd_cap=0.15)
    llm = client if takes_temperature(client._model) else WithoutTemperature(client)
    picked = [c for c in chain.CASES if c[0] in ("retract", "overfire")]
    bad = 0
    for group, name, rows, want, _recall, _fail in picked:
        transcript, _ = ea.build(rows)
        rec = ea.record()
        run = run_text(transcript, rec, llm, max_workers=4)
        res = run.result
        ok = res.tier in want
        bad += not ok
        # the field under test, as the model gave it (raw) and after the code's grounding (beliefs)
        field = {"kind": "kind", "payment": "payment_source", "required": "required_for_loan"}.get(
            name.split()[0], name.split()[0])
        raw = getattr(run.extraction.raw.products[0], field, None)
        belief = getattr(run.beliefs.products[0], field, None)
        def show(a):
            if a is None:
                return "-"
            v = getattr(a, "value", None)
            q = getattr(getattr(a, "evidence", None), "quote", None)
            return f"{type(a).__name__}({v!r}, quote={q!r}{', ' + str(a.reason) if hasattr(a, 'reason') else ''})"
        reasons = sorted({f"{f.rule_id.value}:{f.reason.value}" for f in res.all_flags()}
                         | {f"gap {g.rule_id.value}:{g.reason.value}" for g in res.all_gaps()})
        print(f"{'ok ' if ok else 'BAD'} [{group}] {res.tier.value:17} want {sorted(t.value for t in want)} | {name}\n"
              f"      model: {show(raw)}\n      rules: {show(belief)} | {reasons}")
    print(f"\n{len(picked)} cases, {bad} outside the verifier's reading; spent {client.spent_usd:.4f} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
