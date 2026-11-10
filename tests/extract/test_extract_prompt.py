"""What the model is shown, and what it is allowed to return."""

import inspect
import re

import devset
import pytest

from samajh.amounts import format_inr, spoken_amount
from samajh.clients.llm import strict_json_schema
from samajh.extract import _prompt, extract, slots
from samajh.extract._ground import Reply
from samajh.extract._prompt import change_messages, messages, screen_messages
from samajh.extract._wire import SCHEMA, ChangeReply, ScreenReply, SlotKind
from samajh.types import Language, LoanRecord

SCENARIOS = {s.id: s for s in devset.scenarios()}
EXAMPLE = re.compile(r"^\{.*\}$", re.MULTILINE)


@pytest.mark.parametrize(
    "schema", [*dict.fromkeys(SCHEMA.values()), ScreenReply, ChangeReply], ids=lambda s: s.__name__
)
def test_every_wire_schema_is_valid_for_strict_structured_output(schema):
    strict_json_schema(schema)


def test_every_checked_question_has_a_schema_and_a_prompt():
    assert set(SCHEMA) == set(SlotKind) - {SlotKind.other}
    for kind in SCHEMA:
        assert messages(kind, Language.hi, "q", "r")[0].content


@pytest.mark.parametrize("kind", SCHEMA, ids=lambda k: k.value)
def test_every_example_in_a_prompt_is_valid_output_for_its_schema(kind):
    examples = EXAMPLE.findall(messages(kind, Language.hi, "q", "r")[0].content)
    assert examples
    for example in examples:
        SCHEMA[kind].model_validate_json(example)


def test_every_example_in_the_screening_prompt_is_valid_output():
    examples = EXAMPLE.findall(screen_messages(Language.hi, "q", "r")[0].content)
    assert len(examples) >= 8
    for example in examples:
        ScreenReply.model_validate_json(example)


@pytest.mark.parametrize("kind", SCHEMA, ids=lambda k: k.value)
def test_every_example_in_the_change_check_prompt_is_valid_output_with_the_grounders_clauses(kind):
    system = change_messages(kind, Language.hi, "q", "r")[0].content
    examples = EXAMPLE.findall(system)
    shown = CHANGE_EXAMPLE.findall(system)
    assert len(examples) == len(shown) >= 12
    for example, (reply, clauses) in zip(examples, shown, strict=True):
        ChangeReply.model_validate_json(example)
        numbered = " ".join(f"[{n}] {c}" for n, c in enumerate(Reply(reply).clauses(), start=1))
        assert clauses == numbered, reply


CHANGE_EXAMPLE = re.compile(r'Reply: "(.*?)"  Clauses: (.*?)\n\{', re.DOTALL)


def test_no_prompt_example_is_a_development_set_reply():
    prompts = "\n".join(messages(k, Language.hi, "", "")[0].content for k in SCHEMA)
    prompts += screen_messages(Language.hi, "", "")[0].content
    examples = set(re.findall(r'^Reply: "(.*?)"', prompts, re.MULTILINE))
    examples |= {reply for reply, _ in CHANGE_EXAMPLE.findall(change_messages(SlotKind.kind, Language.hi, "", "")[0].content)}
    replies = {t.text for s in SCENARIOS.values() for t in s.transcript.turns if t.speaker == "customer"}
    assert len(examples) > 40
    assert not examples & replies


def test_the_prompt_builders_cannot_be_given_a_record():
    for build in (messages, screen_messages, change_messages):
        names = set(inspect.signature(build).parameters)
        assert names <= {"kind", "language", "question", "reply"}
    source = inspect.getsource(_prompt)
    assert "LoanRecord" not in source and "record." not in source and "Product" not in source


def _forms(rupees: int) -> set[str]:
    spoken = {spoken_amount(rupees, language) for language in Language}
    return {str(rupees), format_inr(rupees), f"{rupees:,}", *spoken}


def test_no_value_of_the_record_reaches_any_prompt(llm):
    """A record whose every value differs from anything said on the call: none may appear in a prompt."""
    scenario = SCENARIOS["hi-02"]  # the customer believes it is an FD; nobody on the call says otherwise
    product = scenario.record.products[0].model_dump(mode="json") | {
        "provider": "Zzyzx Suraksha Jeevan Beema (synthetic)",
        "premium_inr": 98765,
        "cover_inr": 7654321,
        "term_months": 77,
        "cancel_window_days": 23,
        "paid_from_loan": False,
        "features": ["guaranteed_return"],
        "consent": {"method": "recorded_call", "at": "2031-03-17"},
    }
    record = LoanRecord.model_validate(
        scenario.record.model_dump(mode="json")
        | {
            "products": [product],
            "sanctioned_inr": 8642097,
            "disbursed_inr": 8543332,
            "disbursed_on": "2031-03-17",
            "borrower": {"name": "Qwertyuiop Asdfgh (synthetic)", "dob": "1961-07-29", "language": "hi"},
        }
    )
    extract(scenario.transcript, record, llm)
    assert len(llm.sent) > 20
    prompts = llm.prompts()
    secrets = {
        "Zzyzx", "Suraksha", "Qwertyuiop", "Asdfgh", "1961", "2031", "credit_life", "credit life", "recorded_call_on",
        scenario.record.loan_id, *_forms(98765), *_forms(7654321), *_forms(8642097), *_forms(8543332), "77", "23",
    }  # fmt: skip
    leaked = sorted(secret for secret in secrets if secret in prompts)
    assert not leaked


def test_a_prompt_holds_only_the_bot_turn_and_the_reply_of_its_own_exchange(llm):
    scenario = SCENARIOS["en-02"]
    extract(scenario.transcript, scenario.record, llm)
    pairs = {(s.question, s.turn.text) for s in slots(scenario.transcript, scenario.record)}
    spoken = {t.text for t in scenario.transcript.turns}
    for request in llm.sent:
        user = request[1].content
        shown = [text for text in spoken if text in user]
        question = re.search(r"Assistant's question: <<<(.*?)>>>", user, re.DOTALL).group(1)
        reply = re.search(r"Customer's reply: <<<(.*?)>>>", user, re.DOTALL).group(1)
        assert (question, reply) in pairs
        assert all(text in (question, reply) or text in reply or text in question for text in shown)
        assert not any(text in request[0].content for text in spoken if len(text) > 12)


def test_the_numbered_clauses_in_the_prompt_are_the_ones_the_grounder_resolves():
    user = messages(SlotKind.kind, Language.hi, "q", "कवर? कवर का मुझे नहीं पता।")[1].content
    assert user.endswith("[1] कवर\n[2] कवर का मुझे नहीं पता")
