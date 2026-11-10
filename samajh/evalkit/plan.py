"""The experiment file and the cells it implies.

An experiment names a frozen manifest, the voices per language, the audio conditions (each a
chain of `samajh.audio` steps) and a list of arms. An arm is a grid: its items (filtered by
`where`) x its conditions x its STT configurations. The plan is the de-duplicated union of the
arms' cells, so a cell that two arms share is transcribed once.
"""

from __future__ import annotations

import json
import random
import tomllib
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator

from samajh.audio import Step
from samajh.clients.gnani import PrismaV25, PrismaV30, Timbre
from samajh.clients.gnani.types import SttLanguage, TtsLanguage, TtsModel
from samajh.evalkit.manifest import Item
from samajh.types import Frozen, Language

TTS_LANGUAGE: dict[Language, TtsLanguage] = {
    Language.hi: "hi-IN",
    Language.hi_en: "hi-en",
    Language.ta: "ta-IN",
    Language.kn: "kn-IN",
}
# Prisma takes locales, and Hinglish has none of its own: the call language is Hindi.
STT_LANGUAGE: dict[Language, SttLanguage] = {
    Language.hi: "hi-IN",
    Language.hi_en: "hi-IN",
    Language.ta: "ta-IN",
    Language.kn: "kn-IN",
}


class VoiceSpec(Frozen):
    model: TtsModel
    voice: str

    def timbre(self, language: Language, sample_rate: Literal[8000, 16000]) -> Timbre:
        return Timbre(
            model=self.model, voice=self.voice, language=TTS_LANGUAGE[language], sample_rate=sample_rate
        )


class SttSpec(Frozen):
    """One STT configuration. `language` says how the request's language is chosen per item:
    `item` sends the item's own locale, `item+en` that locale plus en-IN, `indic-auto` lets
    Prisma detect it."""

    model: Literal["prisma-v2.5", "prisma-v3.0"]
    format: Literal["verbatim", "transcribe", "codemix", "transliterate"]
    language: Literal["item", "item+en", "indic-auto"] = "item"

    def options(self, language: Language) -> PrismaV30 | PrismaV25:
        own = STT_LANGUAGE[language]
        if self.model == "prisma-v2.5":
            if self.language != "item":
                raise ValueError("prisma-v2.5 takes one language code: language must be 'item'")
            return PrismaV25(language=own, format=self.format)
        chosen = {"item": own, "item+en": (own, "en-IN"), "indic-auto": "indic-auto"}[self.language]
        return PrismaV30(language=chosen, format=self.format)

    @model_validator(mode="after")
    def _valid_for_the_model(self) -> Self:
        self.options(Language.hi)
        return self

    @property
    def label(self) -> str:
        return f"{self.model.removeprefix('prisma-')} {self.format} {self.language}"


class Arm(Frozen):
    name: str = Field(min_length=1)
    conditions: tuple[str, ...] = Field(min_length=1)
    stt: tuple[SttSpec, ...] = Field(min_length=1)
    # Keep an item only if every pair matches: "language" is the item's language, any other key a tag.
    where: dict[str, str] = Field(default_factory=dict)

    def takes(self, item: Item) -> bool:
        return all(
            (item.language.value if key == "language" else item.tags.get(key)) == value
            for key, value in self.where.items()
        )


class Experiment(Frozen):
    name: str = Field(min_length=1)
    manifest: Path
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    scorer: str
    budget_credits: float = Field(ge=0)
    tts_sample_rate: Literal[8000, 16000] = 16000
    voices: dict[Language, tuple[VoiceSpec, ...]]
    voice_seed: int = 0
    # Voices are rotated within each (language, this tag) group so no stratum hears one voice only.
    balance_by: str | None = None
    conditions: dict[str, tuple[Step, ...]]
    arms: tuple[Arm, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        names = [arm.name for arm in self.arms]
        if len(set(names)) != len(names):
            raise ValueError("arm names must be unique")
        for arm in self.arms:
            unknown = set(arm.conditions) - set(self.conditions)
            if unknown:
                raise ValueError(f"arm {arm.name!r} names undefined conditions: {sorted(unknown)}")
        for language, voices in self.voices.items():
            if not voices:
                raise ValueError(f"no voices for {language.value}")
            for voice in voices:
                voice.timbre(language, self.tts_sample_rate)
        return self


def load_experiment(path: Path) -> Experiment:
    """Parse the TOML file. `manifest` is resolved against the file's own directory."""
    with path.open("rb") as f:
        raw = tomllib.load(f)
    raw["arms"] = raw.pop("arm", [])
    experiment = Experiment.model_validate(raw)
    return experiment.model_copy(update={"manifest": (path.parent / experiment.manifest).resolve()})


class Cell(Frozen):
    """One paid transcription: an item, voiced by one voice, under one condition, one STT config."""

    item_id: str
    voice: VoiceSpec
    condition: str
    stt: SttSpec

    @property
    def key(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def assign_voices(items: tuple[Item, ...], experiment: Experiment) -> dict[str, VoiceSpec]:
    """One voice per item, by a seeded shuffle inside each (language, balance tag) group.

    Depends only on the manifest and the experiment, so a rerun voices every item the same way.
    """
    groups: dict[tuple[str, str], list[Item]] = {}
    for item in items:
        tag = item.tags.get(experiment.balance_by, "") if experiment.balance_by else ""
        groups.setdefault((item.language.value, tag), []).append(item)
    assigned: dict[str, VoiceSpec] = {}
    for offset, ((language, tag), members) in enumerate(sorted(groups.items())):
        voices = experiment.voices.get(Language(language))
        if not voices:
            continue
        members = sorted(members, key=lambda item: item.id)
        random.Random(f"{experiment.voice_seed}:{language}:{tag}").shuffle(members)
        for rank, item in enumerate(members):
            assigned[item.id] = voices[(rank + offset) % len(voices)]
    return assigned


def plan(items: tuple[Item, ...], experiment: Experiment) -> list[Cell]:
    """Every cell of every arm, once, in manifest order (then condition, then STT config)."""
    voices = assign_voices(items, experiment)
    cells: dict[str, Cell] = {}
    for item in items:
        for arm in experiment.arms:
            if not arm.takes(item):
                continue
            for condition in arm.conditions:
                for stt in arm.stt:
                    if item.id not in voices:
                        raise ValueError(
                            f"arm {arm.name!r} takes {item.id} but no voice speaks {item.language}"
                        )
                    cell = Cell(item_id=item.id, voice=voices[item.id], condition=condition, stt=stt)
                    cells.setdefault(cell.key, cell)
    return list(cells.values())
