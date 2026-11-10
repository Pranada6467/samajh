"""Checks the report makes about a scenario set, apart from scoring."""

from dataclasses import replace

import devset
from run import record_values_shown

from samajh.types import Transcript

SCENARIOS = {s.id: s for s in devset.scenarios()}


def asking(scenario, asks: str, text: str):
    """The scenario with the bot question tagged `asks` reworded."""
    turns = [
        t.model_dump() | ({"text": text} if t.asks == asks and t.step != "read_back" else {})
        for t in scenario.transcript.turns
    ]
    transcript = Transcript.model_validate(scenario.transcript.model_dump() | {"turns": turns})
    return replace(scenario, transcript=transcript)


def test_only_the_read_back_repeats_an_amount_that_is_on_the_record():
    assert set(record_values_shown(SCENARIOS["hi-01"])) == {("readback", "premium")}


def test_a_question_that_states_the_records_value_is_found():
    leaky = asking(SCENARIOS["hi-01"], "premium", "आपने चौबीस हज़ार दिए थे, सही?")
    assert record_values_shown(leaky)[("premium", "premium")] == 1
    leaky = asking(SCENARIOS["hi-01"], "cover", "कवर ₹4,00,000 का है ना?")
    assert record_values_shown(leaky)[("cover", "cover")] == 1


def test_the_providers_name_in_a_question_is_found():
    hi = SCENARIOS["hi-01"]
    provider = hi.record.products[0].provider
    leaky = asking(hi, "kind", f"{provider} से जो चीज़ ली, वह क्या है?")
    assert record_values_shown(leaky)[("kind", "provider")] == 1
