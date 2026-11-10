"""Gnani speech client: Prisma STT (REST and batch) and Timbre TTS behind one lock, cache and ledger."""

from samajh.clients.gnani.client import BatchTimeout, GnaniClient, parse_error
from samajh.clients.gnani.types import (
    VOICES,
    AudioFormat,
    BatchOptions,
    BatchTranscript,
    CallInfo,
    Container,
    PrismaV25,
    PrismaV30,
    SampleRate,
    Segment,
    Speech,
    SttLanguage,
    SttOptions,
    Timbre,
    Transcript,
    TtsLanguage,
    Voice,
)
from samajh.clients.gnani.wav import fix_wav_header, wav_sample_rate, wav_seconds

__all__ = [
    "VOICES",
    "AudioFormat",
    "BatchOptions",
    "BatchTimeout",
    "BatchTranscript",
    "CallInfo",
    "Container",
    "GnaniClient",
    "PrismaV25",
    "PrismaV30",
    "SampleRate",
    "Segment",
    "Speech",
    "SttLanguage",
    "SttOptions",
    "Timbre",
    "Transcript",
    "TtsLanguage",
    "Voice",
    "fix_wav_header",
    "parse_error",
    "wav_sample_rate",
    "wav_seconds",
]
