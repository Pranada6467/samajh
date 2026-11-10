"""P3a verifier probe: mutation check of the P3a behaviours. Never touches the repo.

    uv run python references/reviews/iter2/probes/p3a_mutate.py <scratch-dir-outside-repo>

Reuses the harness of references/reviews/iter1/probes/mutate.py (copy, baseline must pass,
apply one mutation, run tests/core tests/scenarios tests/extract, restore) with P3a mutations.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "iter1" / "probes"))
import mutate  # noqa: E402

T, C, E, X, P, A = (
    "samajh/types.py",
    "samajh/rules/checks.py",
    "samajh/rules/engine.py",
    "samajh/extract/_extract.py",
    "samajh/amounts/_parse.py",
    "samajh/amounts/_approx.py",
)
TIER_OF = "return next((tier for tier in Tier if tier in found), Tier.clear)"

mutate.MUTATIONS = [
    # tier_of ordering
    ("T1", "tier_of: refer outranks incomplete (swap)", T, TIER_OF,
     "return next((tier for tier in (Tier.incomplete, Tier.refer, Tier.understanding_gap) if tier in found), Tier.clear)"),
    ("T2", "tier_of: incomplete outranks understanding_gap (swap)", T, TIER_OF,
     "return next((tier for tier in (Tier.refer, Tier.understanding_gap, Tier.incomplete) if tier in found), Tier.clear)"),
    ("T3", "tier_of: least serious wins", T, TIER_OF,
     "return next((tier for tier in reversed(list(Tier)) if tier in found), Tier.clear)"),
    ("T4", "a refer-tier gap is incomplete, not understanding_gap", T,
     "return Tier.incomplete if self.rule_id in REFER_RULES else Tier.understanding_gap", "return Tier.understanding_gap"),
    # conflict on re-ask
    ("K1", "engine adds the conflict flags", E, "        outcomes += conflicting", "        outcomes += ()"),
    ("K2", "a conflict under a refer rule is refer", T,
     "return Tier.refer if rule_id in REFER_RULES else Tier.understanding_gap", "return Tier.understanding_gap"),
    ("K3", "extractor remembers every usable answer", X, "                heard.append(answer)", "                heard[:] = [answer]"),
    ("K4", "extractor reports the first differing answer too", X,
     "    return [answer.evidence for answer in kept]", "    return [answer.evidence for answer in kept][-1:]"),
    # unknown fraction word
    ("F1", "parse_amount refuses a near-fraction word before a number", P,
     "near_fraction(word_at(before))", "False"),
    ("F2", "parse_amount refuses a near-unit word after a number", P,
     "after == \"other\" and near_unit(word_at(j + 1))", "False"),
    ("F3", "range reader refuses a near-fraction word before a range", A,
     "            return None  # \"सारे पचास से बावन हज़ार\"", "            pass  # mutated"),
    # approximate tolerance
    ("A1", "approximate tolerance is 10%", C, "APPROX_AMOUNT_TOLERANCE_PERCENT = 10", "APPROX_AMOUNT_TOLERANCE_PERCENT = 60"),
    ("A2", "a confirmed amount not near is premium_differs_confirmed (approximation never upgrades)", C,
     "why = Why.premium_approximate if near else Why.premium_differs_confirmed", "why = Why.premium_approximate"),
    ("A3", "an unconfirmed near amount counts only when said as approximate", C,
     "if not (exact or (near and a.approximate)):", "if not (exact or near):"),
    ("A4", "a range is never exact", C, "return a.low is None and not _differs(a.value, on_record)",
     "return not _differs(a.value, on_record)"),
    ("A5", "cover: only an approximate answer may be near", C,
     "if _exact(a, p.cover_inr) or (a.approximate and _near(a, p.cover_inr)):",
     "if _exact(a, p.cover_inr) or _near(a, p.cover_inr):"),
    ("A6", "range reader caps width at 2x", A, "return (lo, hi) if 0 < lo < hi <= 2 * lo else None",
     "return (lo, hi) if 0 < lo < hi <= 10 * lo else None"),
    # silence is never a pass
    ("S1", "_decide: no usable answer is a gap", C, "    return (_gap_for(rule, product_id, answer),)",
     "    return _passed(rule, product_id)"),
    ("S2", "kind: asked-and-unclear (or nothing) is a gap", C,
     "    if isinstance(answer, Unclear) or not sources:\n        return (_gap_for(rule, p.id, answer),)",
     "    if isinstance(answer, Unclear) or not sources:\n        return _passed(rule, p.id)"),
    ("S3", "a failed answer call makes its fields unclear", X,
     "            self._no_answer(slot, Unclear(reason=GapReason.extraction_failed, evidence=whole))", "            pass"),
    ("S4", "a failed screening/recall call is listed as unscreened", X,
     "            self._add(self.unscreened, whole)", "            pass"),
    ("S5", "unscreened replies are a case-level gap", C,
     "        *(_gap(rule, None, GapReason.extraction_failed, ev) for ev in beliefs.unscreened),", ""),
    ("S6", "frequency asked and unclear is a gap", C,
     "    if isinstance(answer, Unclear):\n        return (_gap_for(rule, p.id, answer),)\n    if isinstance(answer, DontKnow):\n        return (_flag(rule, p.id, Why.frequency_dont_know",
     "    if isinstance(answer, Unclear):\n        return ()\n    if isinstance(answer, DontKnow):\n        return (_flag(rule, p.id, Why.frequency_dont_know"),
    ("S7", "a denial in recall is refer (recall_denied)", C,
     "    if denial is not None and not named_later:", "    if False:"),
]

if __name__ == "__main__":
    sys.exit(mutate.main())
