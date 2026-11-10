"""The Samajh call: what the bot says next, given the loan record and what the customer has said.

Transport-agnostic and pure. `start` opens a call, `step` takes each customer turn, and the
finished call is a `samajh.types.Transcript` with every bot question tagged for the extractor.
The wording is data in `data/prompts/`. See `machine` for the states and `interpret` for the
turn reading.
"""

from samajh.dialogue.interpret import (
    UNCLEAR,
    Expecting,
    Intent,
    Interpretation,
    RuleInterpreter,
    TurnInterpreter,
)
from samajh.dialogue.machine import (
    BotUtterance,
    CallPlan,
    CallState,
    Ended,
    EndOfCall,
    Limits,
    Line,
    Outcome,
    SecondReading,
    Unresolved,
    expecting,
    start,
    step,
)
from samajh.dialogue.prompts import LINES, PRODUCT_QUESTIONS, PromptPack, load_prompts

__all__ = [
    "LINES",
    "PRODUCT_QUESTIONS",
    "UNCLEAR",
    "BotUtterance",
    "CallPlan",
    "CallState",
    "EndOfCall",
    "Ended",
    "Expecting",
    "Intent",
    "Interpretation",
    "Limits",
    "Line",
    "Outcome",
    "PromptPack",
    "RuleInterpreter",
    "SecondReading",
    "TurnInterpreter",
    "Unresolved",
    "expecting",
    "load_prompts",
    "start",
    "step",
]
