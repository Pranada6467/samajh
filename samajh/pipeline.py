"""The text path: transcript -> extraction -> beliefs -> verdict. Orchestration only."""

from dataclasses import dataclass

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


def run_text(transcript: Transcript, record: LoanRecord, llm: Llm, *, model: str | None = None) -> TextRun:
    extraction = extract_traced(transcript, record, llm, model=model)
    beliefs = to_beliefs(extraction.raw, record, transcript)
    return TextRun(extraction=extraction, beliefs=beliefs, result=evaluate(record, beliefs))


def run_text_case(transcript: Transcript, record: LoanRecord, llm: Llm | None = None) -> CaseResult:
    """The verdict for one transcribed call. `llm` defaults to the OpenRouter client from the environment."""
    return run_text(transcript, record, llm or LlmClient.from_env()).result
