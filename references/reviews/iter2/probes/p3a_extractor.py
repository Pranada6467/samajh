"""P3a verifier probe: extractor changes with a scripted model. Offline, no network.

    uv run python references/reviews/iter2/probes/p3a_extractor.py

Reuses the iter1 extractor_attacks scaffolding (BASE call, Scripted model, build), adding
"took_nothing" to the recall outputs. Cases: re-asked questions, failed model calls (also on a
re-ask), parallel determinism with random delays, quote handling next to a number and before a
negation, a denial in a re-asked open recall.
"""

import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "iter1" / "probes"))
import extractor_attacks as ea  # noqa: E402

from samajh.clients.errors import LlmOutputInvalid  # noqa: E402
from samajh.extract import extract  # noqa: E402
from samajh.rules import evaluate, to_beliefs  # noqa: E402

BASE = [r if r[0] != "open_recall" else (*r[:4], {**r[4], "took_nothing": False}) for r in ea.BASE]
KIND_Q = "वह क्या है: बीमा, एफ़डी, या कुछ और?"
KIND_Q2 = "माफ़ कीजिए, फिर से बताइए: वह बीमा है, एफ़डी है, या कुछ और?"


class Failing(ea.Scripted):
    """Raises LlmOutputInvalid for the answer call of the listed replies; optional random delay."""

    def __init__(self, outputs, screens=None, fail=(), jitter=0.0):
        super().__init__(outputs, screens)
        self.fail, self.jitter = set(fail), jitter

    def complete(self, schema, messages, *, model=None, max_tokens=1024):
        if self.jitter:
            time.sleep(random.random() * self.jitter)
        question, reply = ea._USER.search(messages[1].content).groups()
        if schema.__name__ != "ScreenReply" and reply in self.fail:
            raise LlmOutputInvalid(model="scripted", attempts=3, last_error="x")
        return super().complete(schema, messages, model=model, max_tokens=max_tokens)


def run(name, rows, *, fail=(), screens=None, workers=8, jitter=0.0, show=True):
    transcript, outputs = ea.build(rows)
    llm = Failing(outputs, screens, fail, jitter)
    rec = ea.record()
    raw = extract(transcript, rec, llm, max_workers=workers)
    res = evaluate(rec, to_beliefs(raw, rec, transcript))
    if show:
        flags = ", ".join(f"{f.rule_id.value}:{f.reason.value}" for f in res.all_flags()) or "-"
        gaps = ", ".join(f"{g.rule_id.value}:{g.reason.value}" for g in res.all_gaps()) or "-"
        print(f"{name}\n    tier {res.tier.value} | flags {flags} | gaps {gaps}")
    return raw, res


def insert_after(rows, asks, extra):
    out = []
    for r in rows:
        out.append(r)
        if r[1] == asks and r[0] != "read_back":
            out.append(extra)
    return out


def main() -> int:
    run("0. baseline", BASE)
    fd = ("teach_back", "kind", KIND_Q2, "एफ़डी है, जमा किया है।", {"status": "stated", "kind": "deposit", "clauses": [1, 2]})
    run("1. kind 'बीमा' then re-ask 'एफ़डी' (both outputs fine)", insert_after(BASE, "kind", fd))
    run("2. kind 'बीमा' then re-ask 'एफ़डी', but the re-ask's ANSWER call fails (screen returns nothing)",
        insert_after(BASE, "kind", fd), fail={"एफ़डी है, जमा किया है।"})
    run("2b. same, but the screen sees the FD as a deposit claim",
        insert_after(BASE, "kind", fd), fail={"एफ़डी है, जमा किया है।"},
        screens={"एफ़डी है, जमा किया है।": {"claims": [{"claim": "is_deposit", "span": "एफ़डी है"}], "concerns": []}})
    sep = ("teach_back", "payment_source", "फिर से बताइए, वह रकम कैसे दी?", "मैंने अलग से नकद दिया था।",
           {"status": "stated", "source": "separately", "clauses": [1]})
    run("3. payment 'from loan' then re-ask 'cash separately', re-ask call fails",
        insert_after(BASE, "payment_source", sep), fail={"मैंने अलग से नकद दिया था।"})
    run("4. one failed output on cover only", BASE, fail={"साढ़े तीन लाख रुपये।"})
    run("5. failed output on the consent reply", BASE, fail={"लोन और बीमा, बीमे का ओटीपी दिया था।"})
    run("6. failed output on the open-recall reply", BASE, fail={"एक बीमा लिया था।"})

    # parallel determinism
    reference = None
    same = True
    rows = insert_after(BASE, "kind", fd)
    for workers in (1, 2, 8, 32):
        for _ in range(3):
            raw, _res = run("", rows, workers=workers, jitter=0.01, show=False)
            dump = raw.model_dump_json()
            reference = reference or dump
            same &= dump == reference
    print(f"7. parallel: 12 runs at 1, 2, 8, 32 workers with random delays give identical RawExtraction: {same}")

    # quotes next to a number
    for reply, span in (
        ("सारे तीन लाख रुपये।", "तीन लाख"),
        ("सारे तीन लाख रुपये।", "सारे तीन लाख"),
        ("सारहे तीन लाख रुपये।", "तीन लाख"),
        ("सारहे तीन लाख रुपये।", "सारहे तीन लाख"),
        ("swa 3 lakh रुपये।", "3 lakh"),
        ("तीन लाख तक का कवर।", "तीन लाख"),
        ("तीन लाख तक का कवर।", "तीन लाख तक"),
        ("करीब साढ़े तीन लाख।", "साढ़े तीन लाख"),
    ):
        rows = ea.swap(BASE, "cover", reply, {"status": "stated", "span": span, "clauses": [1]})
        raw, res = run("", rows, show=False)
        cov = [p.cover for p in raw.products][0]
        b = to_beliefs(raw, ea.record(), ea.build(rows)[0]).products[0].cover_inr
        print(f"8. cover reply {reply!r} span {span!r}: raw span kept {getattr(cov, 'value', None)!r}; belief {type(b).__name__}"
              f"{'' if not hasattr(b, 'value') else ' ' + str(b.value)}{'' if not hasattr(b, 'reason') else ' ' + str(b.reason)}")

    # negation after the answer
    rows = ea.swap(BASE, "kind", "बीमा है, ऐसा तो नहीं था।", {"status": "stated", "kind": "insurance", "clauses": [1]})
    raw, res = run("9. kind 'बीमा है, ऐसा तो नहीं था।' model says insurance clause 1", rows)
    print("    kept quote:", raw.products[0].kind.evidence.quote)
    rows = ea.swap(BASE, "premium", "इकतालीस हज़ार तीन सौ, ऐसा तो नहीं था।",
                   {"status": "stated", "span": "इकतालीस हज़ार तीन सौ", "clauses": [1]})
    raw, res = run("10. premium 'इकतालीस हज़ार तीन सौ, ऐसा तो नहीं था।' model says stated", rows)

    # denial in a re-asked open recall
    rec2 = ("open_recall", None, "और कुछ लिया था लोन के साथ?", "याद नहीं आ रहा।", {"items": [], "took_nothing": False})
    rows = [("open_recall", None, BASE[0][2], "कुछ नहीं लिया, बस लोन।", {"items": [], "took_nothing": True}), rec2,
            *[r for r in BASE[1:]]]
    run("11. recall 'took nothing' then re-asked 'can't remember'; rest informed", rows)
    rows = [("open_recall", None, BASE[0][2], "कुछ नहीं लिया, बस लोन।", {"items": [], "took_nothing": True}),
            *[r for r in BASE[1:]]]
    run("12. recall 'took nothing' once; rest informed (names insurance at kind question)", rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
