"""Turn the run store into the tables and failure lists of REPORT.md.

  uv run python eval/amounts/analyze.py            rewrite the generated blocks in REPORT.md
  uv run python eval/amounts/analyze.py --review   print the failures that still need a label

Everything here is offline and free: it reads `run/stt.jsonl`, the frozen manifest and the
labels in `failure_labels.tsv`. A block in REPORT.md between `<!-- BEGIN name -->` and
`<!-- END name -->` is replaced; the prose around the blocks is written by hand.
"""

from __future__ import annotations

import csv
import hashlib
import re
import statistics
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from samajh.amounts import format_inr
from samajh.clients._runtime import Ledger, state_dir
from samajh.evalkit.manifest import load_manifest
from samajh.evalkit.plan import load_experiment
from samajh.evalkit.runner import RunStore, current_rows, jobs, run_spend
from samajh.evalkit.score import (
    Hypothesis,
    ScoreRow,
    aggregate,
    cell_text,
    markdown_table,
    mcnemar_exact,
    paired,
    score,
    wilson,
)
from samajh.evalkit.scorers import AMOUNT, parser

HERE = Path(__file__).resolve().parent
LABELS = HERE / "failure_labels.tsv"
REPORT = HERE / "REPORT.md"
LANGUAGES = ("hi", "hi-en", "ta", "kn")
CONDITIONS = ("clean16k", "phone", "narrowband", "street10", "street5", "babble10", "babble5")
TRANSCRIBE = ("v2.5 transcribe item", "v3.0 transcribe item")
UNIT = ["item_id", "condition", "stt", "output"]


def pct(correct: int, n: int) -> str:
    low, high = wilson(correct, n)
    return f"{correct}/{n} ({100 * correct / n:.0f}%, {100 * low:.0f}-{100 * high:.0f})" if n else ""


def cells(rows: list[ScoreRow], down: list[str], across: str, columns: tuple[str, ...]) -> str:
    table: dict[tuple[str, ...], dict[str, str]] = defaultdict(dict)
    for summary in aggregate(rows, [*down, across]):
        table[tuple(summary.group[name] for name in down)][summary.group[across]] = cell_text(summary)
    body = [[*key, *(found.get(name, "") for name in columns)] for key, found in table.items()]
    return markdown_table([*down, *columns], body)


def ordered(rows: list[ScoreRow], *fields: tuple[str, tuple[str, ...]]) -> list[ScoreRow]:
    def rank(row: ScoreRow) -> tuple[int, ...]:
        return tuple(
            order.index(row.field(name)) if row.field(name) in order else 99 for name, order in fields
        )

    return sorted(rows, key=rank)


def versus(rows: list[ScoreRow], down: list[str]) -> str:
    """Naive and parser side by side per group, with the paired discordant counts."""
    groups: dict[tuple[str, ...], list[ScoreRow]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.field(name) for name in down)].append(row)
    body = []
    for key, members in groups.items():
        naive = [row for row in members if row.method == "naive"]
        parsed = [row for row in members if row.method == "parser"]
        _, only_naive, only_parser, _ = paired(naive, parsed, UNIT)
        body.append(
            [
                *key,
                pct(sum(row.correct for row in naive), len(naive)),
                pct(sum(row.correct for row in parsed), len(parsed)),
                only_parser,
                only_naive,
                f"{mcnemar_exact(only_parser, only_naive):.2g}",
            ]
        )
    headers = [*down, "naive digit reading", "parser", "parser only ✓", "naive only ✓", "McNemar p"]
    return markdown_table(headers, body)


def squash(text: str) -> str:
    """Letters, marks and digits only: two transcripts that differ in punctuation or spacing compare equal."""
    return "".join(ch for ch in text if unicodedata.category(ch)[0] in "LMN")


def load_labels() -> dict[tuple[str, str], tuple[str, str]]:
    if not LABELS.exists():
        return {}
    with LABELS.open(encoding="utf-8", newline="") as f:
        return {
            (r["item_id"], r["transcript"]): (r["label"], r["comment"])
            for r in csv.DictReader(f, delimiter="\t")
        }


def failures(rows: list[ScoreRow]) -> list[ScoreRow]:
    return [row for row in rows if row.method == "parser" and not row.correct]


def main() -> int:
    experiment = load_experiment(HERE / "experiment.toml")
    items = load_manifest(experiment.manifest, expect_sha256=experiment.manifest_sha256)
    by_id = {item.id: item for item in items}
    store = RunStore(HERE / "run")
    planned = jobs(items, experiment)
    stt_rows = list(current_rows(store, planned).values())
    rows = score(items, stt_rows, AMOUNT)
    rows = ordered(rows, ("language", LANGUAGES), ("condition", CONDITIONS))
    labels = load_labels()
    failed = failures(rows)

    if "--review" in sys.argv:
        seen = set()
        for row in failed:
            key = (row.item_id, row.transcript)
            if key in labels or key in seen:
                continue
            seen.add(key)
            print(
                f"{row.item_id}\t{row.gold}\t{row.predicted}\t{row.note}\t{row.transcript}\t{by_id[row.item_id].text}"
            )
        print(
            f"{len(seen)} distinct unlabelled failures of {len({(r.item_id, r.transcript) for r in failed})}",
            file=sys.stderr,
        )
        return 0

    text = [row for row in rows if row.output == "text"]
    transcribe = [row for row in text if row.stt.label in TRANSCRIBE]
    blocks: dict[str, str] = {}

    parser_files = sorted((HERE.parents[1] / "samajh" / "amounts").glob("*.py"))
    parser_hash = hashlib.sha256(b"".join(path.read_bytes() for path in parser_files)).hexdigest()
    tools = store.run_rows()[-1] if store.run_rows() else None
    blocks["coverage"] = (
        markdown_table(
            [
                "planned cells",
                "transcribed",
                "missing",
                "clips voiced",
                "ledger estimate for this run (credits)",
            ],
            [
                [
                    len(planned),
                    len(stt_rows),
                    len(planned) - len(stt_rows),
                    len({row.clip_sha256 for row in stt_rows}),
                    f"{run_spend(store, Ledger(state_dir() / 'ledger.jsonl')):.2f}",
                ]
            ],
        )
        + f"\n\nParser scored: sha256 `{parser_hash[:16]}…` over `samajh/amounts/*.py` as they were when this "
        "table was generated."
        + (f" ffmpeg {tools.ffmpeg}, transform version {tools.transform_version}." if tools else "")
    )

    core = [row for row in transcribe if row.condition in ("clean16k", "phone")]
    blocks["headline"] = versus(core, ["stt", "condition"])
    blocks["by_language"] = versus(core, ["language", "stt", "condition"])
    parsed = [row for row in transcribe if row.method == "parser"]
    naive = [row for row in transcribe if row.method == "naive"]
    blocks["conditions_parser"] = cells(parsed, ["language", "stt"], "condition", CONDITIONS)
    blocks["conditions_naive"] = cells(naive, ["language", "stt"], "condition", CONDITIONS)
    blocks["conditions_pooled"] = cells(transcribe, ["stt", "method"], "condition", CONDITIONS)

    phone = [row for row in rows if row.condition == "phone"]
    methods = ("naive", "parser")
    fold_0 = [row for row in phone if row.tags.get("fold") == "0"]
    fold_1 = [row for row in phone if row.tags.get("fold") == "1"]
    blocks["formats"] = (
        cells(fold_0, ["language", "stt", "output"], "method", methods)
        + "\n\n"
        + cells(fold_1, ["language", "stt", "output"], "method", methods)
    )
    blocks["formats_pooled"] = (
        cells(fold_0, ["tags.fold", "stt", "output"], "method", methods)
        + "\n\n"
        + cells(fold_1, ["tags.fold", "stt", "output"], "method", methods)
    )

    noisy = []
    for label in TRANSCRIBE:
        on_phone = [row for row in parsed if row.stt.label == label and row.condition == "phone"]
        for condition in CONDITIONS[2:]:
            here = [row for row in parsed if row.stt.label == label and row.condition == condition]
            both, only_phone, only_here, neither = paired(on_phone, here, ["item_id"])
            n = both + only_phone + only_here + neither
            noisy.append(
                [
                    label,
                    condition,
                    pct(both + only_here, n),
                    pct(both + only_phone, n),
                    only_phone,
                    only_here,
                    f"{mcnemar_exact(only_phone, only_here):.2g}",
                ]
            )
    blocks["noise_paired"] = markdown_table(
        [
            "stt",
            "condition",
            "parser, this condition",
            "parser, phone, same sentences",
            "phone only ✓",
            "condition only ✓",
            "McNemar p",
        ],
        noisy,
    )

    strata = ("plain", "lakh_crore", "fraction", "irregular_21_99")
    on_phone = [row for row in core if row.condition == "phone"]
    blocks["strata"] = versus(ordered(on_phone, ("tags.stratum", strata)), ["tags.stratum", "stt"])
    blocks["strata_by_language"] = cells(
        [row for row in core if row.method == "parser"],
        ["language", "stt", "condition"],
        "tags.stratum",
        strata,
    )
    blocks["voices"] = cells(
        [row for row in on_phone if row.method == "parser"], ["language", "voice"], "stt", TRANSCRIBE
    )

    outcomes: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for row in parsed:
        kind = "correct" if row.correct else "no answer" if row.predicted is None else "wrong amount"
        outcomes[row.stt.label, row.condition][kind] += 1
    blocks["outcomes"] = markdown_table(
        [
            "stt",
            "condition",
            "n",
            "correct",
            "no answer (re-ask)",
            "wrong amount (only a read-back catches it)",
        ],
        [
            [
                *key,
                sum(c.values()),
                c["correct"],
                pct(c["no answer"], sum(c.values())),
                pct(c["wrong amount"], sum(c.values())),
            ]
            for key, c in outcomes.items()
        ],
    )

    verbatim = {row.item_id: row.text for row in stt_rows if row.stt.label == "v2.5 verbatim item"}
    same = differ = 0
    for row in stt_rows:
        if row.stt.label == "v2.5 transcribe item" and row.condition == "phone" and row.item_id in verbatim:
            if squash(row.literal or "") == squash(verbatim[row.item_id]):
                same += 1
            else:
                differ += 1
    blocks["literal_check"] = (
        f"`literal` of v2.5 transcribe equals the v2.5 verbatim transcript of the same phone clip, ignoring "
        f"punctuation and spaces, in {same} of {same + differ} items (fold 1)."
    )

    detected = Counter(
        (row.language.value, row.detected_language or "none")
        for row in stt_rows
        if row.stt.language == "indic-auto"
    )
    blocks["detected"] = markdown_table(
        ["item language", "detected_language_code", "clips"],
        [[language, code, count] for (language, code), count in sorted(detected.items())],
    )

    latency: dict[str, list[float]] = defaultdict(list)
    for row in stt_rows:
        if not row.cache_hit:
            latency[row.stt.model].append(row.seconds)
    blocks["latency"] = markdown_table(
        ["model", "calls", "median s", "p95 s", "calls needing a retry"],
        [
            [
                model,
                len(values),
                f"{statistics.median(values):.2f}",
                f"{sorted(values)[int(0.95 * (len(values) - 1))]:.2f}",
                sum(1 for row in stt_rows if row.stt.model == model and row.attempts > 1),
            ]
            for model, values in sorted(latency.items())
        ],
    )

    control = Counter()
    for item in items:
        got = parser(Hypothesis(text=item.text, language=item.language)).value
        control[item.language.value, got == item.gold["amount_inr"]] += 1
    blocks["text_control"] = markdown_table(
        ["language", "parser on the source sentence (no audio)"],
        [
            [language, pct(control[language, True], control[language, True] + control[language, False])]
            for language in LANGUAGES
        ],
    )

    def family(row: ScoreRow) -> str:
        if row.output == "literal" or row.stt.format in ("verbatim", "codemix"):
            return f"{row.stt.model.removeprefix('prisma-')} words (literal, verbatim, codemix)"
        return f"{row.stt.model.removeprefix('prisma-')} transcribe"

    families = sorted({family(row) for row in rows})
    by_label: dict[str, Counter] = defaultdict(Counter)
    sentences: dict[str, set[str]] = defaultdict(set)
    patterns: dict[tuple[str, str], list[ScoreRow]] = defaultdict(list)
    listing = []
    for row in failed:
        label, comment = labels.get((row.item_id, row.transcript), ("UNREVIEWED", ""))
        by_label[label][family(row), row.predicted is not None] += 1
        sentences[label].add(row.item_id)
        if label in ("parser_gap", "partial_itn"):
            patterns[label, comment].append(row)
        listing.append(
            [
                row.item_id,
                row.condition,
                f"{row.stt.label}" + (" (literal)" if row.output == "literal" else ""),
                format_inr(row.gold),
                format_inr(row.predicted) if row.predicted is not None else row.note,
                label,
                row.transcript,
                comment,
            ]
        )
    blocks["failure_counts"] = markdown_table(
        ["label", "sentences", *families],
        [
            [
                label,
                len(sentences[label]),
                *(f"{counts[name, True]} wrong amount, {counts[name, False]} no answer" for name in families),
            ]
            for label, counts in sorted(by_label.items())
        ],
    )

    def pick(stt_label: str, condition: str, output: str = "text", fold: str | None = None) -> list[ScoreRow]:
        return [
            row
            for row in rows
            if row.method == "parser"
            and row.stt.label == stt_label
            and row.condition == condition
            and row.output == output
            and (fold is None or row.tags.get("fold") == fold)
        ]

    contrasts = [
        (
            "v3.0 transcribe",
            "v2.5 transcribe",
            pick(TRANSCRIBE[1], "clean16k"),
            pick(TRANSCRIBE[0], "clean16k"),
            "clean16k, all",
        ),
        (
            "v3.0 transcribe",
            "v2.5 transcribe",
            pick(TRANSCRIBE[1], "phone"),
            pick(TRANSCRIBE[0], "phone"),
            "phone, all",
        ),
        (
            "phone",
            "clean16k",
            pick(TRANSCRIBE[0], "phone"),
            pick(TRANSCRIBE[0], "clean16k"),
            "v2.5 transcribe, all",
        ),
        (
            "phone",
            "clean16k",
            pick(TRANSCRIBE[1], "phone"),
            pick(TRANSCRIBE[1], "clean16k"),
            "v3.0 transcribe, all",
        ),
        (
            "v3.0 codemix",
            "v3.0 transcribe",
            pick("v3.0 codemix item", "phone"),
            pick(TRANSCRIBE[1], "phone", fold="0"),
            "phone, fold 0",
        ),
        (
            "v3.0 verbatim",
            "v3.0 transcribe",
            pick("v3.0 verbatim item", "phone"),
            pick(TRANSCRIBE[1], "phone", fold="0"),
            "phone, fold 0",
        ),
        (
            "v3.0 indic-auto",
            "v3.0 language set",
            pick("v3.0 transcribe indic-auto", "phone"),
            pick(TRANSCRIBE[1], "phone", fold="0"),
            "phone, fold 0, transcribe",
        ),
        (
            "v2.5 literal",
            "v2.5 transcribe text",
            pick(TRANSCRIBE[0], "phone", "literal"),
            pick(TRANSCRIBE[0], "phone"),
            "phone, all",
        ),
    ]
    contrast_body = []
    for name_a, name_b, a, b, where in contrasts:
        both, only_a, only_b, neither = paired(a, b, ["item_id"])
        n = both + only_a + only_b + neither
        contrast_body.append(
            [
                f"{name_a} against {name_b}",
                where,
                pct(both + only_a, n),
                pct(both + only_b, n),
                only_a,
                only_b,
                f"{mcnemar_exact(only_a, only_b):.2g}",
            ]
        )
    blocks["contrasts"] = markdown_table(
        ["parser, A against B", "sentences", "A", "B", "A only ✓", "B only ✓", "McNemar p"], contrast_body
    )

    checks = [
        (
            "v2.5 transcribe",
            "v3.0 transcribe",
            pick(TRANSCRIBE[0], "phone"),
            pick(TRANSCRIBE[1], "phone"),
            "phone, all",
        ),
        (
            "v2.5 transcribe",
            "its own literal",
            pick(TRANSCRIBE[0], "phone"),
            pick(TRANSCRIBE[0], "phone", "literal"),
            "phone, all",
        ),
        (
            "v3.0 transcribe",
            "v3.0 verbatim",
            pick(TRANSCRIBE[1], "phone", fold="0"),
            pick("v3.0 verbatim item", "phone"),
            "phone, fold 0",
        ),
        (
            "v3.0 transcribe",
            "v3.0 codemix",
            pick(TRANSCRIBE[1], "phone", fold="0"),
            pick("v3.0 codemix item", "phone"),
            "phone, fold 0",
        ),
    ]
    check_body = []
    for name_a, name_b, a, b, where in checks:
        other = {row.item_id: row for row in b}
        agree = [
            row for row in a if row.predicted is not None and row.predicted == other[row.item_id].predicted
        ]
        differ = [row for row in a if row not in agree]
        check_body.append(
            [
                f"{name_a} and {name_b}",
                where,
                len(a),
                pct(sum(row.correct for row in agree), len(agree)),
                len(differ),
                sum(row.correct or other[row.item_id].correct for row in differ),
            ]
        )
    blocks["agreement"] = markdown_table(
        [
            "two readings of the same clip",
            "sentences",
            "n",
            "same amount from both: how often right",
            "different, or one has no answer",
            "of those, at least one right",
        ],
        check_body,
    )

    def skips_a_group(rupees: int) -> bool:
        """True when a zero group sits between two non-zero groups: 5,00,200 or 6,025 or 19,080."""
        crore, rest = divmod(rupees, 10_000_000)
        lakh, rest = divmod(rest, 100_000)
        thousand, rest = divmod(rest, 1_000)
        hundred, below = divmod(rest, 100)
        used = [bool(part) for part in (crore, lakh, thousand, hundred, below)]
        first, last = used.index(True), len(used) - 1 - used[::-1].index(True)
        return not all(used[first : last + 1])

    whole = [
        row
        for row in core
        if row.method == "parser" and row.condition == "phone" and row.tags.get("stratum") != "fraction"
    ]
    gap_counts: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for row in whole:
        tally = gap_counts[row.stt.label, "yes" if skips_a_group(row.gold) else "no"]
        tally[0] += 1
        tally[1] += row.correct
    blocks["skipped_groups"] = markdown_table(
        ["stt", "amount skips a group", "parser, phone, non-fraction sentences"],
        [[*key, pct(correct, n)] for key, (n, correct) in sorted(gap_counts.items())],
    )

    kinds = ("parser_gap", "partial_itn", "prisma_formatting", "unresolved", "recognition", "source_or_voice")

    def breakdown(cell: list[ScoreRow]) -> list[object]:
        wrong = Counter(
            labels.get((row.item_id, row.transcript), ("UNREVIEWED", ""))[0]
            for row in cell
            if not row.correct
        )
        right = sum(row.correct for row in cell)
        return [
            pct(right, len(cell)),
            *(wrong[kind] for kind in kinds),
            pct(right + wrong["parser_gap"] + wrong["partial_itn"], len(cell)),
        ]

    breakdown_headers = ["parser now", *kinds, "if both parser-side kinds were fixed"]
    parser_rows = [row for row in rows if row.method == "parser"]
    blocks["failure_core"] = markdown_table(
        ["stt", "condition", *breakdown_headers],
        [
            [
                stt_label,
                condition,
                *breakdown(
                    [
                        row
                        for row in parser_rows
                        if row.output == "text" and row.stt.label == stt_label and row.condition == condition
                    ]
                ),
            ]
            for stt_label in TRANSCRIBE
            for condition in ("clean16k", "phone")
        ],
    )
    by_output: dict[tuple[str, str, str], list[ScoreRow]] = defaultdict(list)
    for row in parser_rows:
        if row.condition == "phone":
            by_output[row.tags.get("fold", ""), row.stt.label, row.output].append(row)
    blocks["failure_formats"] = markdown_table(
        ["fold", "stt", "output", *breakdown_headers],
        [[*key, *breakdown(cell)] for key, cell in sorted(by_output.items())],
    )

    blocks["parser_gaps"] = markdown_table(
        [
            "kind",
            "what the parser meets",
            "failed cells",
            "of them a wrong amount",
            "sentences",
            "example transcript",
            "gold",
            "parser said",
        ],
        [
            [
                label,
                comment,
                len(members),
                sum(row.predicted is not None for row in members),
                len({row.item_id for row in members}),
                members[0].transcript,
                format_inr(members[0].gold),
                format_inr(members[0].predicted) if members[0].predicted is not None else members[0].note,
            ]
            for (label, comment), members in sorted(patterns.items(), key=lambda kv: (kv[0][0], -len(kv[1])))
        ],
    )
    (HERE / "FAILURES.md").write_text(
        "# Every parser failure, with its transcript\n\n"
        "Generated by `analyze.py` from `run/stt.jsonl`. One line per failed cell (parser answer is not gold).\n"
        "Labels are explained in REPORT.md. Tamil and Kannada labels are `not human-reviewed`.\n\n"
        + markdown_table(
            ["item", "condition", "STT", "gold", "parser said", "label", "transcript", "comment"], listing
        )
        + "\n",
        encoding="utf-8",
    )

    report = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
    for name, body in blocks.items():
        pattern = re.compile(rf"(<!-- BEGIN {name} -->\n).*?(<!-- END {name} -->)", re.DOTALL)
        if not pattern.search(report):
            print(f"REPORT.md has no block named {name}: skipped", file=sys.stderr)
        report = pattern.sub(lambda m, body=body: f"{m.group(1)}{body}\n{m.group(2)}", report)
    REPORT.write_text(report, encoding="utf-8")
    print(f"{len(rows)} scored rows, {len(failed)} parser failures, blocks: {', '.join(blocks)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
