"""Score the held-out TTS set or the real-voice set with the frozen parser and write the tables.

  uv run python eval/amounts_v2/analyze.py tts         -> eval/amounts_v2/tables-tts.md
  uv run python eval/amounts_v2/analyze.py realvoice   -> eval/amounts_v2/tables-realvoice.md

Offline: reads the stored Prisma transcripts, makes no API call. The parser is `samajh.amounts`
as it was at commit 59c12d9 (`frozen_parser.py`), not the working copy, which changed after the
held-out set was frozen. The real-voice tables hold ids, counts and amounts only, never words.
"""

from __future__ import annotations

import argparse
import statistics
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

from frozen_parser import COMMIT, load

from samajh.evalkit.manifest import load_manifest
from samajh.evalkit.plan import load_experiment
from samajh.evalkit.readings import (
    READINGS,
    Clip,
    Scheme,
    acceptance,
    clips,
    disagreement,
    mechanism,
    outcomes,
    rate,
    where,
)
from samajh.evalkit.runner import RunStore, SttRow, current_rows, jobs
from samajh.evalkit.score import (
    Hypothesis,
    Prediction,
    Scorer,
    aggregate,
    cell_text,
    markdown_table,
    mcnemar_exact,
    score,
)
from samajh.evalkit.scorers import naive_digits

SETS = {
    "tts": (HERE / "experiment.toml", HERE / "run", HERE / "tables-tts.md"),
    "realvoice": (HERE / "realvoice.toml", REPO / ".samajh-realvoice" / "run", HERE / "tables-realvoice.md"),
}
T3, V3, T25, L25 = "v3.0 transcribe", "v3.0 verbatim", "v2.5 transcribe", "v2.5 literal"

# Fixed before the real-voice run; the reference is the two-model scheme of experiment.toml.
SCHEMES = (
    Scheme("v3.0 transcribe alone", (T3,)),
    Scheme("v2.5 transcribe alone", (T25,)),
    Scheme("v2.5 literal alone", (L25,)),
    Scheme("v2.5 transcribe = v2.5 literal (one request)", (T25, L25)),
    Scheme("v3.0 transcribe = v2.5 transcribe (reference)", (T3, T25)),
    Scheme("v3.0 transcribe = v2.5 literal", (T3, L25)),
    Scheme("v3.0 transcribe = v2.5 transcribe = v2.5 literal", (T3, T25, L25)),
    Scheme("v3.0 transcribe = v3.0 verbatim", (T3, V3)),
    Scheme("v3.0 verbatim = v2.5 literal", (V3, L25)),
)


def frozen_scorer() -> tuple[Scorer, str]:
    amounts = load()

    def parser(hypothesis: Hypothesis) -> Prediction:
        result = amounts.parse_amount(hypothesis.text)
        if isinstance(result, amounts.Parsed):
            return Prediction(value=result.rupees)
        return Prediction(value=None, note="ambiguous" if isinstance(result, amounts.Ambiguous) else "none")

    scorer = Scorer(name="amount", gold_field="amount_inr", methods={"naive": naive_digits, "parser": parser})
    return scorer, amounts.FINGERPRINT


def subsets(which: str, all_: Sequence[Clip]) -> list[tuple[str, list[Clip]]]:
    out = [("all", list(all_)), ("retail band", where(all_, band="retail"))]
    if which == "tts":
        for stratum in ("skipped", "control", "general", "fraction", "large"):
            out.append((stratum, where(all_, stratum=stratum)))
        # "X lakh Y" with Y under 100 may colloquially mean X.Y lakh; the other shapes cannot.
        for stratum in ("skipped", "control"):
            out.append((f"{stratum}, unambiguous phrase", unambiguous(where(all_, stratum=stratum))))
            out.append((f"{stratum}, X lakh Y", where(all_, stratum=stratum, shape=AMBIGUOUS_SHAPE)))
        for language in ("hi", "hi-en"):
            out.append((f"language {language}", where(all_, language=language)))
    else:
        for shape in ("skipped", "multi", "single"):
            out.append((f"shape {shape}", where(all_, shape=shape)))
        out.append(("gold 1,000 and above", [c for c in all_ if int(c.tags["gold"]) >= 1000]))
        for split in ("train", "valid"):
            out.append((f"split {split}", where(all_, split=split)))
        for source in ("indicvoices", "kathbath"):
            out.append((f"source {source}", where(all_, source=source)))
    return out


def outcome_table(which: str, condition_clips: Sequence[Clip]) -> str:
    rows = []
    for name, part in subsets(which, condition_clips):
        for reading in (T3, V3, T25, L25):
            tally = outcomes(part, reading)
            rows.append(
                [
                    name,
                    reading,
                    tally.n,
                    rate(tally.correct, tally.n),
                    rate(tally.refused, tally.n),
                    rate(tally.wrong, tally.n),
                ]
            )
    return markdown_table(["subset", "reading", "n", "correct", "refused", "silent wrong"], rows)


AMBIGUOUS_SHAPE = "lakh_units"


def unambiguous(clips_: Sequence[Clip]) -> list[Clip]:
    return [clip for clip in clips_ if clip.tags.get("shape") != AMBIGUOUS_SHAPE]


def colloquial(clip: Clip, reading: str) -> bool:
    """A wrong "X lakh Y" reading that equals X lakh plus Y thousand (X.Y lakh)."""
    gold, value = int(clip.tags["gold"]), clip.values[reading]
    lakhs, rest = divmod(gold, 100_000)
    return clip.tags.get("shape") == AMBIGUOUS_SHAPE and value == lakhs * 100_000 + rest * 1_000


def split_failures(condition_clips: Sequence[Clip], reading: str) -> str:
    wrong = [c for c in condition_clips if c.outcome(reading) == "wrong"]
    loose = sum(colloquial(c, reading) for c in wrong)
    return (
        f'{reading}: {len(wrong)} silent wrong; {loose} are an "X lakh Y" phrase written as X lakh '
        f"Y thousand (ambiguous in colloquial Hindi), {len(wrong) - loose} are wrong under any reading"
    )


def flips(clips_: Sequence[Clip], reading: str, a: str, b: str, **tags: str) -> str:
    by_item: dict[str, dict[str, str]] = {}
    for clip in where(clips_, **tags):
        by_item.setdefault(clip.item_id, {})[clip.condition] = clip.outcome(reading)
    both = [o for o in by_item.values() if a in o and b in o]
    changed = sum(o[a] != o[b] for o in both)
    return (
        f"{reading}: outcome differs between `{a}` and `{b}` on {changed} of {len(both)} items {tags or ''}"
    )


def pair_test(condition_clips: Sequence[Clip], reading: str) -> str:
    """Matched pairs (TTS): skipped item wrong and control right, against the reverse."""
    by_pair: dict[str, dict[str, Clip]] = {}
    for clip in condition_clips:
        if "pair" in clip.tags:
            by_pair.setdefault(f"{clip.language}:{clip.tags['pair']}", {})[clip.tags["stratum"]] = clip
    only_skipped = only_control = both = 0
    for pair in by_pair.values():
        if len(pair) != 2:
            continue
        s, c = pair["skipped"].outcome(reading) == "wrong", pair["control"].outcome(reading) == "wrong"
        only_skipped += s and not c
        only_control += c and not s
        both += s and c
    p = mcnemar_exact(only_skipped, only_control)
    return (
        f"{reading}: {len(by_pair)} pairs; silent wrong on the skipped item only {only_skipped}, "
        f"on the control only {only_control}, on both {both}; exact McNemar p = {p:.2g}"
    )


def model_test(condition_clips: Sequence[Clip], a: str, b: str) -> str:
    only_a = sum(c.outcome(a) == "wrong" and c.outcome(b) != "wrong" for c in condition_clips)
    only_b = sum(c.outcome(b) == "wrong" and c.outcome(a) != "wrong" for c in condition_clips)
    return f"silent wrong {a} only {only_a}, {b} only {only_b}; exact McNemar p = {mcnemar_exact(only_a, only_b):.2g}"


def mechanism_table(condition_clips: Sequence[Clip], which: str) -> str:
    rows = []
    for name, part in subsets(which, condition_clips)[: 4 if which == "tts" else 3]:
        for digits, words in ((T3, V3), (T25, L25)):
            m = mechanism(part, digits=digits, words=words)
            rows.append(
                [
                    name,
                    f"{digits} wrong; {words}",
                    m.digits_wrong,
                    rate(m.words_right, m.digits_wrong),
                    m.words_same_wrong,
                    m.words_other_wrong,
                    m.words_refused,
                ]
            )
    return markdown_table(
        [
            "subset",
            "digits wrong; words from",
            "digits wrong",
            "words right",
            "words same wrong",
            "words other wrong",
            "words refused",
        ],
        rows,
    )


def scheme_table(condition_clips: Sequence[Clip], which: str) -> str:
    rows = []
    for name, part in subsets(which, condition_clips)[: 4 if which == "tts" else 3]:
        for scheme in SCHEMES:
            a = acceptance(part, scheme)
            rows.append(
                [
                    name,
                    scheme.name,
                    len(scheme.requests),
                    rate(a.accepted, a.n),
                    a.accepted_wrong,
                    rate(a.accepted_right, a.accepted),
                ]
            )
    return markdown_table(
        [
            "subset",
            "scheme (accept when equal)",
            "requests",
            "accepted (coverage)",
            "accepted wrong",
            "P(correct | accepted)",
        ],
        rows,
    )


def disagreement_table(condition_clips: Sequence[Clip]) -> str:
    rows = []
    for first, second in ((T3, T25), (T25, L25), (T3, L25)):
        d = disagreement(condition_clips, first, second)
        rows.append(
            [
                f"{first} vs {second}",
                d.n,
                d.both_answered,
                d.one_refused,
                d.both_refused,
                d.first_right,
                d.second_right,
                d.neither_right,
            ]
        )
    return markdown_table(
        [
            "pair",
            "not accepted",
            "two amounts",
            "one refused",
            "both refused",
            "first right",
            "second right",
            "neither right",
        ],
        rows,
    )


def latency_table(stt_rows: Sequence[SttRow]) -> str:
    rows = []
    for label in dict.fromkeys(key for key, _ in READINGS.values()):
        mine = [row for row in stt_rows if row.stt.label == label]
        live = [row.seconds for row in mine if not row.cache_hit]
        audio = sum(row.audio_seconds for row in mine)
        rows.append(
            [
                label,
                len(mine),
                len(live),
                f"{statistics.median(live):.2f}" if live else "-",
                f"{statistics.quantiles(live, n=10)[-1]:.2f}" if len(live) >= 10 else "-",
                f"{sum(row.est_credits for row in mine):.2f}",
                f"{audio:.0f}",
            ]
        )
    return markdown_table(
        ["request", "rows", "live calls", "median s", "p90 s", "est. credits", "audio s"], rows
    )


def failures(condition_clips: Sequence[Clip], which: str) -> str:
    rows = []
    for clip in sorted(condition_clips, key=lambda c: c.item_id):
        if all(clip.right[r] for r in (T3, V3, T25, L25)):
            continue
        kind = clip.tags.get("stratum") or clip.tags.get("shape", "")
        shape = clip.tags.get("shape", "") if which == "tts" else clip.tags.get("source", "")
        rows.append(
            [clip.item_id, kind, shape, clip.tags["gold"], *(_cell(clip, r) for r in (T3, V3, T25, L25))]
        )
    return markdown_table(["item", "stratum", "shape/source", "gold", T3, V3, T25, L25], rows)


def _cell(clip: Clip, reading: str) -> str:
    value = clip.values[reading]
    if clip.right[reading]:
        return "ok"
    return "refused" if value is None else f"**{value}**"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("which", choices=sorted(SETS))
    args = parser.parse_args(argv)
    experiment_path, store_path, out_path = SETS[args.which]
    experiment = load_experiment(experiment_path)
    items = load_manifest(experiment.manifest, expect_sha256=experiment.manifest_sha256)
    stt_rows = list(current_rows(RunStore(store_path), jobs(items, experiment)).values())
    scorer, fingerprint = frozen_scorer()
    scored = score(items, stt_rows, scorer)
    gold = {item.id: item.gold["amount_inr"] for item in items}
    found = clips(scored)
    complete = [c for c in found if set(c.values) == set(READINGS)]
    # The gold amount rides in the tags for the failure table only; readings never see it.
    complete = [
        Clip(c.item_id, c.condition, {**c.tags, "gold": str(gold[c.item_id])}, c.language, c.values, c.right)
        for c in complete
    ]
    missing = sorted({item.id for item in items} - {c.item_id for c in complete})

    parts = [
        f"# {experiment.name}: tables\n",
        (
            f"Written by `uv run python eval/amounts_v2/analyze.py {args.which}`. Parser: `samajh.amounts` "
            f"at commit {COMMIT}, exported outside the repository (files sha256 `{fingerprint[:16]}`). "
            f"Manifest sha256 `{experiment.manifest_sha256}`. Every reading is the parser's reading of "
            "that output; a refusal is no amount (ambiguous or none); a silent wrong amount is an amount "
            "that is not gold. Rates: count/n (percent, Wilson 95% interval).\n"
        ),
        (
            f"Items in the manifest {len(items)}; clips with all four readings {len(complete)}; "
            f"items without a complete clip: {', '.join(missing) or 'none'}.\n"
        ),
    ]
    for condition in experiment.conditions:
        cc = where(complete, condition=condition)
        parts += [
            f"\n## Condition `{condition}` (n = {len(cc)} clips)\n",
            "\n### Outcomes per reading\n",
            outcome_table(args.which, cc),
            "\n### Paired tests\n",
            "- " + model_test(cc, T3, T25),
            "- " + model_test(cc, T25, L25),
        ]
        if args.which == "tts":
            parts += [
                "- " + pair_test(cc, T3),
                "- unambiguous phrases only, " + pair_test(unambiguous(cc), T3),
                "- " + pair_test(cc, T25),
                "- " + split_failures(cc, T3),
            ]
        naive = [
            r
            for r in scored
            if r.method == "naive"
            and r.condition == condition
            and r.output == "text"
            and r.stt.label == READINGS[T3][0]
        ]
        naive_wrong = sum(r.predicted is not None and not r.correct for r in naive)
        parts += [
            f"- Context: the naive digits rule on v3.0 transcribe text: silent wrong {rate(naive_wrong, len(naive))}",
            "\n### Mechanism: where the digits are wrong, what the words of the same clip say\n",
            mechanism_table(cc, args.which),
            "\n### Acceptance schemes\n",
            scheme_table(cc, args.which),
            "\n### Clips a two-reading scheme does not accept\n",
            disagreement_table(cc),
            "\n### Clips where any reading is not gold\n",
            failures(cc, args.which),
        ]
    conditions = list(experiment.conditions)
    parts += [
        "\n## Stability across the two copies of each clip\n",
        "- " + flips(complete, T3, *conditions),
        "- " + flips(complete, T3, *conditions, stratum="skipped") if args.which == "tts" else "",
        "\n## Requests: latency and estimated cost\n",
        latency_table(stt_rows),
        (
            "\nLatency is wall time per live request through the client lock (cache hits left out). "
            "Credits are the client's estimate (0.010 per audio second for both models), not a dashboard reading.\n"
        ),
    ]
    counts = Counter(c.condition for c in complete)
    out_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    if args.which == "tts":
        # The runner's summary, rescored with the pinned parser (the TTS text is synthetic).
        by = ["language", "condition", "stt", "output", "method"]
        table = markdown_table(
            [*by, "correct/n (rate, Wilson 95%)"],
            ([*summary.group.values(), cell_text(summary)] for summary in aggregate(scored, by)),
        )
        note = f"Parser: samajh.amounts at {COMMIT} (eval/amounts_v2/frozen_parser.py). Written by analyze.py.\n\n"
        (store_path / "summary.md").write_text(note + table + "\n", encoding="utf-8")
        (store_path / "scores.jsonl").write_text(
            "".join(r.model_dump_json() + "\n" for r in scored), encoding="utf-8"
        )
    print(f"{out_path}: {dict(counts)} clips; parser {COMMIT} ({fingerprint[:16]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
