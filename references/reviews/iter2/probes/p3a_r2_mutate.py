"""P3a re-verification (round 2): mutation check of the fix-round behaviours. Never touches the repo.

    uv run python references/reviews/iter2/probes/p3a_r2_mutate.py <scratch-dir-outside-repo> [NAME ...]

Reuses the iter1 harness (copy samajh/, tests/, eval/, data/ to the scratch dir, baseline must
pass, one mutation at a time, restore). Runs tests/core, tests/scenarios, tests/extract and the
LLM single-flight test. SURVIVED = no test noticed the broken behaviour.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "iter1" / "probes"))
import mutate  # noqa: E402

mutate.TESTS = ["tests/core", "tests/scenarios", "tests/extract", "tests/clients/test_llm_single_flight.py"]

N, C, T, X, P, L, A, LLM = (
    "samajh/rules/normalise.py",
    "samajh/rules/checks.py",
    "samajh/types.py",
    "samajh/extract/_extract.py",
    "samajh/amounts/_parse.py",
    "samajh/amounts/_lexicon.py",
    "samajh/amounts/_approx.py",
    "samajh/clients/llm.py",
)

mutate.MUTATIONS = [
    # retraction in a later clause
    ("RT1", "retraction() finds nothing", N, "    for match in _RETRACTION.finditer(reply):", "    for match in ():"),
    ("RT2", "a retraction with a correction adds no conflict", N,
     "            taken_back.setdefault(question, AnswerConflict(question=question, answers=answers))", "            pass"),
    ("RT3", "a retracted stated answer is kept", N,
     "        return Unclear(reason=GapReason.no_usable_answer, evidence=answer.evidence)\n\n    def ground",
     "        return answer\n\n    def ground"),
    ("RT4", "'नहीं नहीं' is not a retraction", N, "|नहीं\\W+नहीं|", "|"),
    ("RT5", "'सॉरी' is not a retraction", N, "|सॉरी\"", "\""),
    ("RT6", "Latin 'sorry' is not a retraction", N, "|not\\s+that|sorry", "|not\\s+that"),
    # denial persistence
    ("DN1", "a denial is never retracted by naming", C, "    if denial is not None and not named:", "    if denial is not None:"),
    ("DN2", "naming at the kind question does not retract the denial", C, "        named.append(answer.evidence)", "        pass"),
    ("DN3", "naming in a later recall reply does not retract the denial", C,
     "    named = [i.evidence for i in _matched(p, beliefs)]", "    named = []"),
    ("DN4", "only the last recall reply's denial counts (old behaviour)", X,
     "        if wire.took_nothing and not wire.items and self.recall_denial is None:\n            self.recall_denial = g.whole()",
     "        self.recall_denial = g.whole() if wire.took_nothing and not wire.items else None"),
    ("DN5", "a denial is dropped when any recall item exists (old behaviour)", X,
     "            denial=assembly.recall_denial,", "            denial=None if assembly.recall_items else assembly.recall_denial,"),
    # cover read-back tier
    ("CV1", "any wrong plain cover is confirmed", C, "        elif isinstance(readback, Stated) and readback.value:", "        elif True:"),
    ("CV2", "a wrong plain cover is never confirmed", C, "        elif isinstance(readback, Stated) and readback.value:", "        elif False:"),
    ("CV3", "a hedged wrong cover is treated as plain", C,
     "        if a.hedged or a.approximate:\n            why = Why.cover_differs", "        if a.approximate:\n            why = Why.cover_differs"),
    ("CV4", "unconfirmed wrong cover is understanding_gap", T,
     "    _R.cover_differs_unconfirmed: Tier.incomplete,", "    _R.cover_differs_unconfirmed: Tier.understanding_gap,"),
    ("CV5", "the extractor ignores a cover read-back turn", X,
     "read_back = {Question.premium: SlotKind.readback, Question.cover: SlotKind.cover_readback}",
     "read_back = {Question.premium: SlotKind.readback}"),
    ("CV6", "cover: a too-wide range is compared", C,
     "        if _too_wide(a):\n            return (_gap(rule, p.id, GapReason.not_comparable, a.evidence),)\n        if _exact(a, p.cover_inr)",
     "        if _exact(a, p.cover_inr)"),
    # re-ask accounting and the conflict rule
    ("RA1", "a failed call on one asking is hidden by another reply", X, "    if failed is not None:\n        return failed",
     "    if False:\n        return failed"),
    ("RA2", "the first stated answer stands, not the last", X, "        last = stated[-1]", "        last = stated[0]"),
    ("RA3", "amount conflict tolerance 50%", X, "        tol = max(x[2], y[2])", "        tol = 50"),
    ("RA4", "no stated answers ever conflict", X,
     "        if isinstance(answer, Stated) and (not kept or not _compatible(name, answer, kept[-1])):",
     "        if isinstance(answer, Stated) and not kept:"),
    ("RA5", "approximate tolerance ignored in the conflict rule", X,
     "    return low, high, APPROX_AMOUNT_TOLERANCE_PERCENT if approximate else AMOUNT_TOLERANCE_PERCENT",
     "    return low, high, AMOUNT_TOLERANCE_PERCENT"),
    # structural fraction refusal and range width
    ("FR1", "near_fraction never fires", L, "    if norm_key(word) in ORDINARY:\n        return False",
     "    return False\n    if norm_key(word) in ORDINARY:\n        return False"),
    ("FR2", "Devanagari near-miss needs an exact skeleton match", L,
     "_ALLOWED_DEVA = {1: -1, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2}", "_ALLOWED_DEVA = {1: -1, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}"),
    ("FR3", "widen() returns the model's span unchanged", N, "            return reply[words[first][0] : words[last][1]]",
     "            return span"),
    ("FR4", "range ratio 5", A, "MAX_RANGE_RATIO = 2", "MAX_RANGE_RATIO = 5"),
    # "one" after hundreds / before a verb
    ("ON1", "no verb is recognised after 'one'", P,
     "        return k + 1 < len(toks) and kind(k + 1, k) == \"other\" and norm_key(word_at(k + 1)) in VERB_AFTER",
     "        return False"),
    ("ON2", "'one' after a hundreds word is a determiner again", P,
     "            or (determiner(j) and not verb_after(j) and toks[j - 1].atoms[-1].value >= THOUSAND)",
     "            or determiner(j)"),
    # one LLM request per cache key
    ("SF1", "no single-flight lock", LLM,
     "        with single_flight(self._locks / f\"{key}.lock\", timeout=self._lock_timeout(max_output_retries)):",
     "        with open(os.devnull):"),
    ("SF2", "no cache re-check inside the lock", LLM,
     "            cached = self._cached(schema, key, model, started)\n            if cached is not None:\n                return cached\n            return self._ask(",
     "            return self._ask("),
]

if __name__ == "__main__":
    sys.exit(mutate.main())
