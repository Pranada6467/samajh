"""The transport's settings, parsed once from `settings.toml` (or the file `SAMAJH_SERVER_SETTINGS` names)."""

from __future__ import annotations

import os
import tomllib
from functools import cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from samajh.identity import IdentityPolicy, parse_policy
from samajh.server.dialogue import ListenKind
from samajh.server.sessionlog import SttSettings, TtsSettings
from samajh.types import Language

DEFAULT_FILE = Path(__file__).with_name("settings.toml")


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Patience(_Frozen):
    cut_ms: int = Field(ge=200, le=5000)
    grace_ms: int = Field(ge=200, le=8000)

    @model_validator(mode="after")
    def _grace_covers_cut(self) -> Patience:
        if self.grace_ms < self.cut_ms:
            raise ValueError("grace_ms must be at least cut_ms")
        return self


class TtsConfig(_Frozen):
    model: Literal["timbre-v3.0", "timbre-v2.5"]
    voice: dict[Language, str]

    @model_validator(mode="after")
    def _every_language(self) -> TtsConfig:
        missing = sorted(lang.value for lang in Language if lang not in self.voice)
        if missing:
            raise ValueError(f"no voice for {missing}")
        return self


class Fallback(_Frozen):
    enabled: bool
    timeout_s: float = Field(gt=0, le=30)


class BatchConfig(_Frozen):
    """Prisma Batch on the whole call, after it ends: segment times and speaker labels."""

    model: Literal["prisma-v3.0", "prisma-v2.5"] = "prisma-v3.0"
    num_speakers: int | None = Field(default=2, ge=1, le=8)
    timeout_s: float = Field(default=600.0, gt=0, le=3600)


class Settings(_Frozen):
    tts: TtsConfig
    stt: SttSettings
    turn_taking: dict[ListenKind, Patience]
    fallback: Fallback
    batch: BatchConfig = BatchConfig()
    # The lender's right-party setting (samajh.identity), read through `parse_policy`: only the menu.
    # A session request may override it for one call (the demo picker); absent, no second check.
    identity: IdentityPolicy = IdentityPolicy()

    @field_validator("identity", mode="before")
    @classmethod
    def _identity_menu(cls, value: object) -> object:
        return value if isinstance(value, IdentityPolicy) else parse_policy(value)  # type: ignore[arg-type]

    @model_validator(mode="after")
    def _every_listen_kind(self) -> Settings:
        if set(self.turn_taking) != {"yes_no", "short", "amount", "open"}:
            raise ValueError("turn_taking needs exactly yes_no, short, amount and open")
        return self

    def tts_for(self, language: Language) -> TtsSettings:
        return TtsSettings(model=self.tts.model, voice=self.tts.voice[language])


def parse_settings(text: str) -> Settings:
    """Raises ValueError (pydantic's or tomllib's) on anything that is not a full, valid file."""
    return Settings.model_validate(tomllib.loads(text))


@cache
def load_settings() -> Settings:
    path = Path(os.environ.get("SAMAJH_SERVER_SETTINGS") or DEFAULT_FILE)
    return parse_settings(path.read_text(encoding="utf-8"))
