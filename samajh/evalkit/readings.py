"""Several readings of one clip, compared: silent wrong amounts, agreement, acceptance schemes.

A reading is what one predictor made of one Prisma output of a clip: a value, or None for a
refusal. Everything here works on `ScoreRow`s, so gold reaches a reading only through the
`correct` flag that `score` already computed by equality.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from pydantic import JsonValue

from samajh.evalkit.score import ScoreRow, wilson

# Reading name -> (STT label, output). The two v2.5 readings come from one request.
READINGS: dict[str, tuple[str, str]] = {
    "v3.0 transcribe": ("v3.0 transcribe item", "text"),
    "v3.0 verbatim": ("v3.0 verbatim item", "text"),
    "v2.5 transcribe": ("v2.5 transcribe item", "text"),
    "v2.5 literal": ("v2.5 transcribe item", "literal"),
}


@dataclass(frozen=True)
class Clip:
    """One item under one audio condition, with every reading taken of it."""

    item_id: str
    condition: str
    tags: Mapping[str, str]
    language: str
    values: Mapping[str, JsonValue]  # reading name -> predicted value, None for a refusal
    right: Mapping[str, bool]  # reading name -> equal to gold

    def outcome(self, reading: str) -> str:
        if self.right[reading]:
            return "correct"
        return "refused" if self.values[reading] is None else "wrong"


def clips(rows: Iterable[ScoreRow], *, method: str = "parser") -> list[Clip]:
    """Group the rows of one method by (item, condition). A clip keeps only the readings it has."""
    names = {key: name for name, key in READINGS.items()}
    found: dict[tuple[str, str], tuple[ScoreRow, dict[str, JsonValue], dict[str, bool]]] = {}
    for row in rows:
        name = names.get((row.stt.label, row.output))
        if row.method != method or name is None:
            continue
        _, values, right = found.setdefault((row.item_id, row.condition), (row, {}, {}))
        values[name] = row.predicted
        right[name] = row.correct
    return [
        Clip(
            item_id=row.item_id,
            condition=row.condition,
            tags=row.tags,
            language=row.language.value,
            values=values,
            right=right,
        )
        for row, values, right in found.values()
    ]


@dataclass(frozen=True)
class Tally:
    n: int
    correct: int
    refused: int
    wrong: int  # an amount was returned and it is not gold: nothing warns the caller


def outcomes(clips_: Iterable[Clip], reading: str) -> Tally:
    counts = {"correct": 0, "refused": 0, "wrong": 0}
    for clip in clips_:
        counts[clip.outcome(reading)] += 1
    return Tally(n=sum(counts.values()), **counts)


@dataclass(frozen=True)
class Mechanism:
    """Where the digit reading is wrong, what the word reading of the same clip says."""

    digits_wrong: int
    words_right: int  # the words carry the right amount: the fault is in writing the digits
    words_same_wrong: int  # the words carry the same wrong amount: heard wrong, or said wrong
    words_other_wrong: int
    words_refused: int


def mechanism(clips_: Iterable[Clip], *, digits: str, words: str) -> Mechanism:
    wrong = [clip for clip in clips_ if clip.outcome(digits) == "wrong"]
    return Mechanism(
        digits_wrong=len(wrong),
        words_right=sum(clip.right[words] for clip in wrong),
        words_same_wrong=sum(
            clip.outcome(words) == "wrong" and clip.values[words] == clip.values[digits] for clip in wrong
        ),
        words_other_wrong=sum(
            clip.outcome(words) == "wrong" and clip.values[words] != clip.values[digits] for clip in wrong
        ),
        words_refused=sum(clip.outcome(words) == "refused" for clip in wrong),
    )


@dataclass(frozen=True)
class Scheme:
    """Accept a clip's amount when every listed reading gives the same amount; otherwise ask again."""

    name: str
    readings: tuple[str, ...]

    @property
    def requests(self) -> tuple[str, ...]:
        """The distinct STT requests the scheme needs, in order."""
        return tuple(dict.fromkeys(READINGS[reading][0] for reading in self.readings))

    def accepted(self, clip: Clip) -> JsonValue:
        """The accepted amount, or None when the readings differ or one of them refused."""
        first = clip.values[self.readings[0]]
        if first is None or any(clip.values[reading] != first for reading in self.readings[1:]):
            return None
        return first


@dataclass(frozen=True)
class Acceptance:
    n: int
    accepted: int
    accepted_right: int

    @property
    def accepted_wrong(self) -> int:
        return self.accepted - self.accepted_right


def acceptance(clips_: Iterable[Clip], scheme: Scheme) -> Acceptance:
    n = accepted = right = 0
    for clip in clips_:
        n += 1
        if scheme.accepted(clip) is not None:
            accepted += 1
            # Every reading equals the first, so the first being right means the accepted amount is.
            right += clip.right[scheme.readings[0]]
    return Acceptance(n=n, accepted=accepted, accepted_right=right)


@dataclass(frozen=True)
class Disagreement:
    """What happens on the clips a two-reading scheme does not accept."""

    n: int
    both_answered: int  # two different amounts
    one_refused: int
    both_refused: int
    first_right: int
    second_right: int
    neither_right: int


def disagreement(clips_: Iterable[Clip], first: str, second: str) -> Disagreement:
    scheme = Scheme(name="", readings=(first, second))
    rest = [clip for clip in clips_ if scheme.accepted(clip) is None]
    answered = [sum(clip.values[reading] is not None for reading in (first, second)) for clip in rest]
    return Disagreement(
        n=len(rest),
        both_answered=answered.count(2),
        one_refused=answered.count(1),
        both_refused=answered.count(0),
        first_right=sum(clip.right[first] for clip in rest),
        second_right=sum(clip.right[second] for clip in rest),
        neither_right=sum(not clip.right[first] and not clip.right[second] for clip in rest),
    )


def rate(count: int, n: int) -> str:
    """`3/68 (4%, 2-12)`: count, rate and the Wilson 95% interval in percent; `0/0` when n is 0."""
    if n == 0:
        return "0/0"
    low, high = wilson(count, n)
    return f"{count}/{n} ({100 * count / n:.0f}%, {100 * low:.0f}-{100 * high:.0f})"


def where(clips_: Sequence[Clip], **tags: str) -> list[Clip]:
    """The clips whose condition, language or tags equal every given value."""
    return [
        clip
        for clip in clips_
        if all(
            (
                clip.condition
                if key == "condition"
                else clip.language
                if key == "language"
                else clip.tags.get(key)
            )
            == value
            for key, value in tags.items()
        )
    ]
