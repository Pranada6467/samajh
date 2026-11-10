"""Scoring: transcript -> prediction -> compared with gold, then counted with Wilson intervals.

A scorer is a set of named predictors. A predictor sees a `Hypothesis` (the words Prisma wrote
and the call language) and nothing else, so gold cannot reach it: the comparison with the item's
gold happens here, by equality, after the predictor has answered.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import JsonValue

from samajh.evalkit.manifest import Item
from samajh.evalkit.plan import SttSpec, VoiceSpec
from samajh.evalkit.runner import SttRow
from samajh.types import Frozen, Language


class Hypothesis(Frozen):
    text: str
    language: Language


class Prediction(Frozen):
    value: JsonValue  # None: the method gives no answer
    note: str = ""


Predictor = Callable[[Hypothesis], Prediction]


@dataclass(frozen=True)
class Scorer:
    name: str
    gold_field: str
    methods: Mapping[str, Predictor]


class ScoreRow(Frozen):
    item_id: str
    language: Language
    tags: dict[str, str]
    voice: VoiceSpec
    condition: str
    stt: SttSpec
    # `literal` is prisma-v2.5's wording before number formatting, returned by the same call.
    output: Literal["text", "literal"]
    method: str
    transcript: str
    gold: JsonValue
    predicted: JsonValue
    note: str
    correct: bool

    def field(self, name: str) -> str:
        """Grouping value by dotted name: `language`, `condition`, `output`, `method`, `stt`
        (the label), `stt.model`, `stt.format`, `stt.language`, `voice`, `voice.model`, `tags.<tag>`."""
        head, _, rest = name.partition(".")
        if head == "tags":
            return self.tags.get(rest, "")
        if head == "stt" and not rest:
            return self.stt.label
        if head == "voice" and not rest:
            return f"{self.voice.voice} ({self.voice.model.removeprefix('timbre-')})"
        value = getattr(self, head)
        value = getattr(value, rest) if rest else value
        return value.value if isinstance(value, Language) else str(value)


def score(items: Iterable[Item], rows: Iterable[SttRow], scorer: Scorer) -> list[ScoreRow]:
    by_id = {item.id: item for item in items}
    out = []
    for row in rows:
        item = by_id[row.item_id]
        gold = item.gold[scorer.gold_field]
        outputs = [("text", row.text)] + ([("literal", row.literal)] if row.literal is not None else [])
        for output, transcript in outputs:
            hypothesis = Hypothesis(text=transcript, language=item.language)
            for method, predict in scorer.methods.items():
                prediction = predict(hypothesis)
                out.append(
                    ScoreRow(
                        item_id=item.id,
                        language=item.language,
                        tags=item.tags,
                        voice=row.voice,
                        condition=row.condition,
                        stt=row.stt,
                        output=output,
                        method=method,
                        transcript=transcript,
                        gold=gold,
                        predicted=prediction.value,
                        note=prediction.note,
                        # bool == int in Python: 1 must not match True.
                        correct=prediction.value is not None
                        and type(prediction.value) is type(gold)
                        and prediction.value == gold,
                    )
                )
    return out


def wilson(correct: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (95% by default). (0, 1) when n is 0."""
    if n == 0:
        return 0.0, 1.0
    p = correct / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    # Clamp: at correct == 0 or n the exact bound is 0 or 1 and rounding can step past it.
    return max(0.0, centre - half), min(1.0, centre + half)


def mcnemar_exact(only_a: int, only_b: int) -> float:
    """Two-sided exact McNemar p-value from the discordant pairs (a binomial test at 1/2)."""
    n = only_a + only_b
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(only_a, only_b) + 1)) / 2**n
    return min(1.0, 2 * tail)


class Summary(Frozen):
    group: dict[str, str]
    n: int
    correct: int
    rate: float
    low: float
    high: float


def aggregate(rows: Iterable[ScoreRow], by: Sequence[str]) -> list[Summary]:
    """Count correct rows per group. `by` lists `ScoreRow.field` names; groups keep first-seen order."""
    counts: dict[tuple[str, ...], list[int]] = {}
    for row in rows:
        tally = counts.setdefault(tuple(row.field(name) for name in by), [0, 0])
        tally[0] += 1
        tally[1] += row.correct
    out = []
    for key, (n, correct) in counts.items():
        low, high = wilson(correct, n)
        out.append(
            Summary(
                group=dict(zip(by, key, strict=True)),
                n=n,
                correct=correct,
                rate=correct / n,
                low=low,
                high=high,
            )
        )
    return out


def paired(a: Iterable[ScoreRow], b: Iterable[ScoreRow], unit: Sequence[str]) -> tuple[int, int, int, int]:
    """Pair rows of `a` and `b` on the `unit` fields; units present on one side only are dropped.

    Returns (both correct, only a correct, only b correct, both wrong).
    """
    left = {tuple(row.field(name) for name in unit): row.correct for row in a}
    right = {tuple(row.field(name) for name in unit): row.correct for row in b}
    cells = [0, 0, 0, 0]
    for key in left.keys() & right.keys():
        cells[
            {(True, True): 0, (True, False): 1, (False, True): 2, (False, False): 3}[left[key], right[key]]
        ] += 1
    return cells[0], cells[1], cells[2], cells[3]


def cell_text(summary: Summary) -> str:
    """`52/60 (87%, 76-93)`: count, rate and the Wilson 95% interval in percent."""
    return (
        f"{summary.correct}/{summary.n} "
        f"({100 * summary.rate:.0f}%, {100 * summary.low:.0f}-{100 * summary.high:.0f})"
    )


def markdown_table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    def line(cells: Sequence[object]) -> str:
        return "| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", " ") for cell in cells) + " |"

    return "\n".join([line(headers), line(["---"] * len(headers)), *(line(row) for row in rows)])


def pivot(
    rows: Iterable[ScoreRow], *, down: Sequence[str], across: str, columns: Sequence[str] | None = None
) -> str:
    """A markdown table: one line per `down` group, one column per value of `across`."""
    summaries = aggregate(rows, [*down, across])
    seen = list(dict.fromkeys(s.group[across] for s in summaries))
    names = list(columns) if columns is not None else seen
    table: dict[tuple[str, ...], dict[str, Summary]] = {}
    for summary in summaries:
        table.setdefault(tuple(summary.group[name] for name in down), {})[summary.group[across]] = summary
    body = [
        [*key, *(cell_text(cells[name]) if name in cells else "" for name in names)]
        for key, cells in table.items()
    ]
    return markdown_table([*down, *names], body)
