"""Public request and result types for the Gnani client. Illegal option combinations fail here,
at construction, because the server ignores several of them silently."""

from __future__ import annotations

import unicodedata
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SttLanguage = Literal[
    "bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN", "ml-IN", "mr-IN", "pa-IN", "ta-IN", "te-IN"
]
# [unverified] list from the docs; the server accepts any string here, so this type is the only guard.
TtsLanguage = Literal[
    "auto", "hi-IN", "en-IN", "ta-IN", "te-IN", "kn-IN", "ml-IN", "mr-IN", "pa-IN", "bn-IN", "gu-IN", "hi-en"
]
SampleRate = Literal[8000, 16000, 22050, 24000, 44100, 48000]
Container = Literal["wav", "raw", "mp3", "ogg", "mulaw", "alaw"]
AudioFormat = Literal["wav", "mp3", "ogg", "flac", "aac", "m4a"]
SttModel = Literal["prisma-v3.0", "prisma-v2.5"]
TtsModel = Literal["timbre-v2.5", "timbre-v3.0"]

_Keyterms = Annotated[tuple[Annotated[str, Field(min_length=1)], ...], Field(max_length=200)]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PrismaV30(_Frozen):
    model: Literal["prisma-v3.0"] = "prisma-v3.0"
    language: (
        SttLanguage
        | Literal["indic-auto"]
        | Annotated[tuple[SttLanguage, ...], Field(min_length=1, max_length=4)]
    )
    format: Literal["verbatim", "transcribe", "codemix", "transliterate"]
    keyterms: _Keyterms = ()
    topic: str | None = None

    @field_validator("topic")
    @classmethod
    def _topic(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or len(value) > 1600 or "<|" in value or "|>" in value):
            raise ValueError("topic must be non-empty, at most 1600 characters, without '<|' or '|>'")
        return value


class PrismaV25(_Frozen):
    model: Literal["prisma-v2.5"] = "prisma-v2.5"
    language: SttLanguage
    format: Literal["verbatim", "transcribe"]
    bias_list: Annotated[tuple[str, ...], Field(max_length=100)] = ()
    bias_score: Literal[0.5, 1.0, 1.5, 2.0] | None = None

    @model_validator(mode="after")
    def _bias(self) -> Self:
        for word in self.bias_list:
            # Letters and combining marks (Indic vowel signs are marks, so str.isalpha is too strict).
            if not word or any(unicodedata.category(ch)[0] not in "LM" for ch in word):
                raise ValueError(f"bias_list entry {word!r} must be a single word of letters only")
        if bool(self.bias_list) != (self.bias_score is not None):
            raise ValueError("bias_score must be set exactly when bias_list is non-empty")
        return self


SttOptions = Annotated[PrismaV30 | PrismaV25, Field(discriminator="model")]


class Voice(_Frozen):
    name: str
    model: TtsModel
    gender: Literal["F", "M"] | None
    language: TtsLanguage | None  # None = any (v3.0) or not documented (v2.5)


def _v30(gender: Literal["F", "M"], names: str) -> list[Voice]:
    return [Voice(name=n, model="timbre-v3.0", gender=gender, language=None) for n in names.split()]


def _v25(language: TtsLanguage | None, female: str, male: str = "", unknown: str = "") -> list[Voice]:
    groups: tuple[tuple[Literal["F", "M"] | None, str], ...] = (("F", female), ("M", male), (None, unknown))
    return [
        Voice(name=n, model="timbre-v2.5", gender=gender, language=language)
        for gender, names in groups
        for n in names.split()
    ]


# Names are the live lists; gender and preferred language are [unverified] (docs only).
VOICES: dict[TtsModel, tuple[Voice, ...]] = {
    "timbre-v3.0": tuple(
        _v30("F", "Shivani Lakshmi Kalpana Chetana Vasudha Riyaa Tarika")
        + _v30("M", "Avinash Shubham Prakash Devansh Yashraj Harshad")
    ),
    "timbre-v2.5": tuple(
        _v25("en-IN", "Kaveri Trupti Devika", "Pranav Shlok Girish")
        + _v25(
            "hi-IN",
            "Nalini Bhavna Yashvi Urmila Jwala Chitra Ambuja",
            "Deepak Roopesh Vikrant Hemraj Jalaj Omkar",
        )
        + _v25("hi-en", "Poorvi")
        + _v25("ta-IN", "Asmita Trisha Brinda Vedika Noopur")
        + _v25("te-IN", "Suhana Lehara Lavanya Yukti Varuni")
        + _v25("kn-IN", "Saanvi", "Kavin")
        + _v25("ml-IN", "Reshma", "Riyaan")
        + _v25("mr-IN", "Zahira", "Ishaan")
        + _v25("bn-IN", "Kirra", "Dhruva")
        + _v25("gu-IN", "Falak", "Veera")
        + _v25("pa-IN", "Mehuli", "Zayan")
        + _v25(
            None,
            "",
            "",
            "Aarohi Bhavini Charvi Eishani Falguni Gauri Iravati Janaki Kamakshi Madhuri Radhika Shweta "
            "Tanvi Vidya Wamika Yamini Abhimanyu Chirag Deven Farhan Jatin Kartik Oviya Parvati Hansika "
            "Damini Urvashi Lalita Nayana Gaurav Harshit",
        )
    ),
}


class Timbre(_Frozen):
    model: TtsModel
    voice: str
    language: TtsLanguage
    sample_rate: SampleRate = 8000
    container: Container = "wav"
    speed: float = Field(default=1.0, ge=0.85, le=1.15)

    @model_validator(mode="after")
    def _combination(self) -> Self:
        if self.voice not in {v.name for v in VOICES[self.model]}:
            raise ValueError(f"voice {self.voice!r} does not belong to {self.model}")
        if self.container in ("mulaw", "alaw") and self.sample_rate != 8000:
            raise ValueError(f"{self.container} is 8000 Hz only")
        return self


class BatchOptions(_Frozen):
    model: SttModel
    language: (
        SttLanguage
        | Literal["indic-auto"]
        | Annotated[tuple[SttLanguage, ...], Field(min_length=1, max_length=4)]
    )
    format: Literal["verbatim", "transcribe", "codemix"] | None = None
    diarize: bool = True
    num_speakers: int | None = Field(default=None, ge=1, le=8)
    denoise: bool = False
    keyterms: _Keyterms = ()

    @model_validator(mode="after")
    def _per_model(self) -> Self:
        if self.model == "prisma-v2.5":
            if self.language == "indic-auto" or (isinstance(self.language, tuple) and len(self.language) > 3):
                raise ValueError("prisma-v2.5 batch takes 1 to 3 language codes and no indic-auto")
            if self.format is not None or self.keyterms:
                raise ValueError("format and keyterms are prisma-v3.0 only")
        elif self.format is None:
            # The REST default depends on model and language; batch is assumed to behave alike.
            raise ValueError("format is required on prisma-v3.0")
        return self


class CallInfo(_Frozen):
    cache_hit: bool
    cache_key: str
    seconds: float  # wall time of the network phase, backoff included; 0 on a cache hit
    est_credits: float
    attempts: int


class Transcript(_Frozen):
    text: str
    literal: str | None  # v2.5 transcribe only: the words before number formatting
    model: str
    detected_language: str | None
    request_id: str | None
    truncated: bool
    call: CallInfo


class Speech(_Frozen):
    audio: bytes
    content_type: str
    container: Container
    sample_rate: SampleRate
    audio_seconds: float | None
    request_id: str | None
    call: CallInfo


class Segment(_Frozen):
    index: int
    start: float
    end: float
    text: str
    speaker: int | None
    language: str | None


class BatchTranscript(_Frozen):
    segments: tuple[Segment, ...]
    text: str
    duration_seconds: float
    language: str | None
    model: str
    job_id: str
    file_id: str
    call: CallInfo
