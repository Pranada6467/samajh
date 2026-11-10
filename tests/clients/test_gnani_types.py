from __future__ import annotations

from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from samajh.clients.gnani import VOICES, BatchOptions, PrismaV25, PrismaV30, SttOptions, Timbre


def test_voice_tables() -> None:
    v30, v25 = VOICES["timbre-v3.0"], VOICES["timbre-v2.5"]
    assert len(v30) == 13 and all(v.gender and v.language is None for v in v30)
    assert len({v.name for v in v25}) == len(v25) == 73
    assert sum(v.language is not None for v in v25) == 42
    assert all((v.gender is None) == (v.language is None) for v in v25)
    assert next(v for v in v25 if v.name == "Poorvi").language == "hi-en"


def test_valid_options() -> None:
    assert PrismaV30(language=("hi-IN", "en-IN"), format="codemix", keyterms=("EMI",), topic="loan call")
    assert PrismaV30(language="indic-auto", format="transliterate")
    assert PrismaV25(language="hi-IN", format="transcribe", bias_list=("लोन", "EMI"), bias_score=1.5)
    assert Timbre(model="timbre-v2.5", voice="Nalini", language="hi-IN", container="mulaw")
    assert BatchOptions(model="prisma-v2.5", language=("hi-IN", "en-IN", "ta-IN"))
    adapter: TypeAdapter[Any] = TypeAdapter(SttOptions)
    picked = adapter.validate_python({"model": "prisma-v2.5", "language": "kn-IN", "format": "verbatim"})
    assert isinstance(picked, PrismaV25)


@pytest.mark.parametrize(
    ("cls", "kwargs"),
    [
        (PrismaV25, {"language": "hi-IN", "format": "codemix"}),
        (PrismaV25, {"language": "indic-auto", "format": "verbatim"}),
        (PrismaV25, {"language": "hi-IN", "format": "verbatim", "bias_list": ("EMI",)}),
        (PrismaV25, {"language": "hi-IN", "format": "verbatim", "bias_score": 1.0}),
        (PrismaV25, {"language": "hi-IN", "format": "verbatim", "bias_list": ("EMI",), "bias_score": 0.7}),
        (PrismaV25, {"language": "hi-IN", "format": "verbatim", "bias_list": ("EMI2",), "bias_score": 1.0}),
        (
            PrismaV25,
            {"language": "hi-IN", "format": "verbatim", "bias_list": ("two words",), "bias_score": 1.0},
        ),
        (
            PrismaV25,
            {"language": "hi-IN", "format": "verbatim", "bias_list": ("x",) * 101, "bias_score": 1.0},
        ),
        (PrismaV25, {"language": "hi-IN", "format": "verbatim", "keyterms": ("EMI",)}),
        (PrismaV30, {"language": "hi-IN"}),
        (PrismaV30, {"language": ("hi-IN", "en-IN", "ta-IN", "te-IN", "kn-IN"), "format": "verbatim"}),
        (PrismaV30, {"language": (), "format": "verbatim"}),
        (PrismaV30, {"language": "or-IN", "format": "verbatim"}),
        (PrismaV30, {"language": "hi-IN", "format": "verbatim", "keyterms": ("x",) * 201}),
        (PrismaV30, {"language": "hi-IN", "format": "verbatim", "keyterms": ("",)}),
        (PrismaV30, {"language": "hi-IN", "format": "verbatim", "topic": " "}),
        (PrismaV30, {"language": "hi-IN", "format": "verbatim", "topic": "x" * 1601}),
        (PrismaV30, {"language": "hi-IN", "format": "verbatim", "topic": "a <|im_start|> b"}),
        (Timbre, {"model": "timbre-v3.0", "voice": "Nalini", "language": "hi-IN"}),
        (Timbre, {"model": "timbre-v2.5", "voice": "Shivani", "language": "hi-IN"}),
        (Timbre, {"model": "timbre-v3.0", "voice": "Shivani", "language": "xx-XX"}),
        (Timbre, {"model": "timbre-v3.0", "voice": "Shivani", "language": "hi-IN", "sample_rate": 11025}),
        (
            Timbre,
            {
                "model": "timbre-v3.0",
                "voice": "Shivani",
                "language": "hi-IN",
                "container": "mulaw",
                "sample_rate": 16000,
            },
        ),
        (Timbre, {"model": "timbre-v3.0", "voice": "Shivani", "language": "hi-IN", "speed": 3}),
        (BatchOptions, {"model": "prisma-v2.5", "language": "hi-IN", "format": "transcribe"}),
        (BatchOptions, {"model": "prisma-v2.5", "language": "hi-IN", "keyterms": ("EMI",)}),
        (BatchOptions, {"model": "prisma-v2.5", "language": "indic-auto"}),
        (BatchOptions, {"model": "prisma-v2.5", "language": ("hi-IN", "en-IN", "ta-IN", "te-IN")}),
        (BatchOptions, {"model": "prisma-v3.0", "language": "hi-IN"}),
        (BatchOptions, {"model": "prisma-v3.0", "language": "hi-IN", "format": "transliterate"}),
        (
            BatchOptions,
            {"model": "prisma-v3.0", "language": "hi-IN", "format": "verbatim", "num_speakers": 9},
        ),
    ],
)
def test_illegal_combinations_fail_at_construction(cls: type, kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        cls(**kwargs)


def test_options_are_frozen() -> None:
    options = PrismaV30(language="hi-IN", format="verbatim")
    with pytest.raises(ValidationError):
        options.format = "codemix"  # type: ignore[misc]
