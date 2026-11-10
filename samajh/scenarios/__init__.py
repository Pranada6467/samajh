"""The scenario set: synthetic loan records, what each customer believes, gold verdicts, scripted calls.

    uv run python -m samajh.scenarios build     # regenerate data/scenarios/ byte for byte
    uv run python -m samajh.scenarios verify    # fail if the files differ from FROZEN.json
    uv run python -m samajh.scenarios check     # gold against the rule engine on perfect input

Gold is written by hand in `cases.py` and never comes from the rule engine. Importing this
package does not import `samajh.rules`; only `samajh.scenarios.consistency` does.
"""

from samajh.scenarios.build import (
    DATA_DIR,
    call_scripts,
    generate,
    load_calls,
    load_scenarios,
    scenarios,
    verify,
)
from samajh.scenarios.model import (
    CallScripts,
    CustomerState,
    Gold,
    ProductBelief,
    ProductGold,
    Scenario,
    ScenarioClass,
    TeachBackCall,
    Template,
    YesNoAnswer,
    YesNoCall,
    YesNoDisposition,
    YesNoOutcome,
    YesNoQuestion,
)

__all__ = [
    "DATA_DIR",
    "CallScripts",
    "CustomerState",
    "Gold",
    "ProductBelief",
    "ProductGold",
    "Scenario",
    "ScenarioClass",
    "TeachBackCall",
    "Template",
    "YesNoAnswer",
    "YesNoCall",
    "YesNoDisposition",
    "YesNoOutcome",
    "YesNoQuestion",
    "call_scripts",
    "generate",
    "load_calls",
    "load_scenarios",
    "scenarios",
    "verify",
]
