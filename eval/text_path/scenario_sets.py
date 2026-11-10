"""The scenario sets the text-path evaluation can run on."""

import hashlib
import json

import devset
import e1
from scenario import GoldLabels, Scenario, YesNoArm

from samajh.rules import evaluate, to_beliefs
from samajh.scenarios import DATA_DIR, load_calls, load_scenarios, verify

FROZEN = DATA_DIR / "FROZEN.json"

# Base cases where the customer agreed to a product described to them as something else. The
# set's expected `consent_given` is true; `data/scenarios/README.md` ("Using the set") calls a
# false there a defensible reading and asks for these to be scored apart.
CONSENT_READING = frozenset({"U08", "V04", "V06", "C02"})

_DEV_NOTE = (
    "Development set: 20 hand-written calls (5 each hi, hi-en, ta, kn), typed text, one author for "
    "replies, gold and prompt. Tamil and Kannada not human-reviewed. Gold verdicts and flags are the "
    "rule engine run on the hand-labelled extraction. Used for prompt iteration, so these numbers "
    "are in-sample."
)


def _frozen() -> tuple[str, tuple[Scenario, ...]]:
    problems = verify()
    if problems:
        raise SystemExit("the frozen set does not match its hashes: " + "; ".join(problems))
    frozen = json.loads(FROZEN.read_text())
    hashes = {
        name: hashlib.sha256((DATA_DIR / name).read_bytes()).hexdigest()[:12] for name in frozen["files"]
    }
    calls = {c.id: c for c in load_calls()}
    found = []
    for s in load_scenarios():
        call = calls[s.id].teach_back
        gold = GoldLabels(
            verdict=s.gold.verdict,
            products=tuple((p.product_id, p.verdict) for p in s.gold.products),
            flags=s.gold.flag_keys(),
        )
        perfect = evaluate(s.record, to_beliefs(call.extraction, s.record, call.transcript))
        note = f"{s.title} [{s.scenario_class.value}, target rule {s.target_rule.value}]"
        confirmed = calls[s.id].yes_no.outcome.value == "confirmed"
        arm = YesNoArm(
            stratum=e1.stratum(s.customer_state.value == "informed", s.yes_no.value, confirmed),
            confirmed=confirmed,
            target_rule=s.target_rule,
        )
        found.append(
            Scenario(
                s.id,
                s.record,
                call.transcript,
                gold,
                call.extraction,
                perfect,
                note,
                base=s.base,
                yes_no=arm,
                consent_reading=s.base in CONSENT_READING,
            )
        )
    note = (
        f"Frozen set version {frozen['version']} of {frozen['frozen_on']}: {len(found)} scripted calls "
        f"(sha256 gold.jsonl {hashes['gold.jsonl']}, calls.jsonl {hashes['calls.jsonl']}). Synthetic, "
        "templated text, no speech-to-text, Tamil and Kannada not human-reviewed. Verdicts and flags are "
        "scored against the hand-written gold; fields against the set's perfect extraction. Not used "
        "for prompt or model selection."
    )
    return note, tuple(found)


def load(name: str) -> tuple[str, tuple[Scenario, ...]] | None:
    """(note for the report, scenarios), or None when the set does not exist yet."""
    if name == "dev":
        return _DEV_NOTE, devset.scenarios()
    return _frozen() if FROZEN.exists() else None
