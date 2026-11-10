"""Mutation run for P2 (verifier, iteration 2). Applies one mutation at a time to a scratch copy of HEAD
(never the repo), runs tests/dialogue, and reports whether the suite caught it.
    uv run python p2_mutate.py /path/to/scratch/head
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

M = "samajh/dialogue/machine.py"
I = "samajh/dialogue/interpret.py"

MUTATIONS = [
    ("first-person: any yes-word passes, rest ignored", I,
     "        if not rest:\n            return True\n",
     "        return True\n"),
    ("first-person: unplaced reply at identity treated as yes", M,
     "    if heard.intent is Intent.yes:\n        return _say(state, AtGoAhead())",
     "    if heard.intent in (Intent.yes, Intent.said):\n        return _say(state, AtGoAhead())"),
    ("third party: wrong_person at identity goes on", M,
     "    if heard.intent in (Intent.no, Intent.wrong_person):\n        return _end(state, Outcome.wrong_party)",
     "    if heard.intent is Intent.no:\n        return _end(state, Outcome.wrong_party)\n    if heard.intent is Intent.wrong_person:\n        return _say(state, AtGoAhead())"),
    ("third party: birth-year step ignores relation words", M,
     "    if heard.intent is Intent.wrong_person:  # \"पापा",
     "    if False:  # \"पापा"),
    ("third party: end line names the lender", "data/prompts/hi.toml",
     'text = "यह {first_name} जी के लिए कस्टमर केयर की कॉल थी।',
     'text = "यह {first_name} जी के लिए {lender} कस्टमर केयर की कॉल थी।'),
    ("refusal: decline intent no longer ends the call", M,
     "    if heard.intent is Intent.decline:\n        return _end(state, Outcome.declined)\n",
     ""),
    ("refusal: decline word list ignored", I,
     "        refuses = _has(words, lexicon.decline)\n",
     "        refuses = False\n"),
    ("refusal: narrated refusals end the call", I,
     "        if narrated:\n            return Intent.said, {}\n",
     ""),
    ("no-leak: provider choice skipped when the RECORD says not required", M,
     "        position=AtIdentity(),\n    )\n",
     "        position=AtIdentity(),\n        own_choice=tuple(p.id for p in record.products if not p.required_for_loan),\n    )\n"),
    ("no-leak: read back the record premium", M,
     "    figure = first or second\n    if figure is not None:",
     "    figure = first or second\n    if figure is not None:\n        figure = Figure(low=_REC[product], high=_REC[product])"),
    ("limits: re-ask forever at a teach-back question", M,
     "    if not position.reasked:\n        return _say(state, position.model_copy(update={\"reasked\": True}))\n    state = _mark_unresolved(state, position)\n    return _go(state, _after(state, position), bridge=True)",
     "    return _say(state, position.model_copy(update={\"reasked\": True}))"),
    ("limits: turn budget ignored", M,
     "    if state.bot_turns + 1 >= state.limits.max_bot_turns:\n        return _end(state, Outcome.turn_limit)\n",
     ""),
    ("limits: read-backs unlimited", M,
     "    more = position.read_backs < state.limits.max_read_backs\n",
     "    more = True\n"),
    ("limits: silence never ends the call", M,
     "    if silent and state.silences >= state.limits.max_silences:\n        return _end(state, Outcome.no_response)\n",
     ""),
    ("read-back: no say-again on disagreement (first reading read back at once)", M,
     "    may_say_again = state.plan.product_ids[product] not in state.said_again\n",
     "    may_say_again = False\n"),
    ("read-back: a correction does not change the figure", M,
     "        figure = _figure(heard)\n        state = _keep(state, position, figure)\n        if more:\n            return _say(\n                state, _read_back_at(position.product, figure, position.read_backs + 1, position.item)",
     "        figure = Figure(low=position.amount_inr, high=position.amount_inr)\n        state = _keep(state, position, figure)\n        if more:\n            return _say(\n                state, _read_back_at(position.product, figure, position.read_backs + 1, position.item)"),
    ("read-back: second reading preferred on the second try", M,
     "    figure = first or second\n",
     "    figure = second or first\n"),
]


def main() -> int:
    root = Path(sys.argv[1])
    results = []
    for name, rel, old, new in MUTATIONS:
        path = root / rel
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            results.append((name, "NOT APPLIED"))
            continue
        mutated = original.replace(old, new)
        if "_REC[" in new:  # the record-premium mutation needs the record's premiums in reach
            mutated = mutated.replace(
                "    plan = CallPlan(", "    global _REC\n    _REC = [p.premium_inr for p in record.products]\n    plan = CallPlan(")
        path.write_text(mutated, encoding="utf-8")
        try:
            run = subprocess.run(["uv", "run", "pytest", "tests/dialogue", "-q", "-x", "-p", "no:cacheprovider"],
                                 cwd=root, capture_output=True, text=True, timeout=900)
            tail = run.stdout.strip().splitlines()[-1] if run.stdout.strip() else run.stderr[-200:]
            results.append((name, ("CAUGHT" if run.returncode else "SURVIVED") + "  " + tail))
        finally:
            path.write_text(original, encoding="utf-8")
        print(results[-1], flush=True)
    print()
    for name, verdict in results:
        print(f"{verdict[:8]:9s} {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
