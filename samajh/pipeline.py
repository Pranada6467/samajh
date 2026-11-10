"""The text path: transcript -> extraction -> beliefs -> verdict. Orchestration only."""

from dataclasses import dataclass

import httpx

from samajh.clients.llm import LlmClient
from samajh.extract import Extraction, Llm, extract_traced
from samajh.rules import evaluate, to_beliefs
from samajh.types import Beliefs, CaseResult, LoanRecord, Transcript


@dataclass(frozen=True)
class TextRun:
    """Every stage of one case, for the evaluation and the evidence log."""

    extraction: Extraction
    beliefs: Beliefs
    result: CaseResult


class WithoutTemperature:
    """`LlmClient` for a model that rejects the `temperature` parameter (OpenRouter answers 404)."""

    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm

    def complete(self, schema, messages, **options):
        return self._llm.complete(schema, messages, temperature=None, **options)


def takes_temperature(model: str) -> bool:
    """What OpenRouter's public model list says. True when the list cannot be read."""
    try:
        listed = httpx.get("https://openrouter.ai/api/v1/models", timeout=30).json()["data"]
        return "temperature" in next(m for m in listed if m["id"] == model)["supported_parameters"]
    except (httpx.HTTPError, KeyError, StopIteration, ValueError):
        return True


def default_llm() -> Llm:
    """The OpenRouter client from the environment, asked at temperature 0 where the model allows it."""
    client = LlmClient.from_env()
    return client if takes_temperature(client._model) else WithoutTemperature(client)


def run_text(
    transcript: Transcript, record: LoanRecord, llm: Llm, *, model: str | None = None, max_workers: int = 8
) -> TextRun:
    extraction = extract_traced(transcript, record, llm, model=model, max_workers=max_workers)
    beliefs = to_beliefs(extraction.raw, record, transcript)
    return TextRun(extraction=extraction, beliefs=beliefs, result=evaluate(record, beliefs))


def run_text_case(transcript: Transcript, record: LoanRecord, llm: Llm | None = None) -> CaseResult:
    """The verdict for one transcribed call. `llm` defaults to `default_llm()`."""
    return run_text(transcript, record, llm or default_llm()).result
