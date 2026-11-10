"""Mutation check for P2 round 2: break one round-2 behaviour at a time in a scratch copy and see the suite fail.

    uv run python tests/dialogue/probes/p2_round2_mutate.py /path/to/scratch/copy

The copy must hold pyproject.toml, uv.lock, samajh/, data/ and tests/ (never point this at the repo).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

M, I, L = "samajh/dialogue/machine.py", "samajh/dialogue/interpret.py", "samajh/dialogue/llm_fallback.py"

MUTATIONS = [
    ("opening: an acknowledgement confirms", I,
     '# "हाँ जी", "बोलिए", "हेलो": an acknowledgement, not a claim\n                return Intent.said, {"settled": True}',
     '# mutated\n                return Intent.yes, {"settled": True}'),
    ("opening: a failed classifier confirms at the first name", L,
     "        if expecting is Expecting.identity and first.intent is Intent.yes:\n            first = first.model_copy(update={\"intent\": Intent.said})\n        return first.model_copy(update={\"degraded\": True, \"year\": None})",
     "        if expecting is Expecting.identity:\n            return first.model_copy(update={\"intent\": Intent.yes, \"degraded\": True})\n        return first.model_copy(update={\"degraded\": True, \"year\": None})"),
    ("opening: the wrong_person label is ignored", L,
     "    _Label.wrong_person: Intent.wrong_person,\n", ""),
    ("opening: confirms_self needs no first-person word", L,
     "        if label is _Label.confirms_self and not speaks_in_first_person(text, language):\n",
     "        if False:\n"),
    ("opening: a loose year passes the second check", I,
     "            else:\n                loose = heard\n", "            else:\n                year = loose = heard\n"),
    ("opening: 'sahab is in a meeting' is a call-back", I,
     "            return Intent.wrong_person, {}  # \"साहब मीटिंग में हैं\": busy, but someone else is\n",
     "            pass\n"),
    ("refusal: a failed classifier later never asks to go on", M,
     "    if failed and not state.degraded_checked:", "    if False:"),
    ("refusal: do_not_call ends as declined", M,
     "        return _end(state, Outcome.do_not_call)", "        return _end(state, Outcome.declined)"),
    ("refusal: a weak stop signal is cleared by an unclear label", L,
     "        if first.intent in _WEAK and intent not in _KEEPS_WEAK:\n", "        if False:\n"),
    ("refusal: an interpreter exception escapes step", M,
     "        except Exception:  # an interpreter's failure must never escape `step`",
     "        except ZeroDivisionError:"),
    ("who/why: before confirmation it names the lender", M,
     '                return _say(state, AtIdentity(reasked=True), before=("purpose.before_confirm",))',
     '                return _say(state, AtIdentity(reasked=True), before=("verify.before_loan",))'),
    ("disengaged: never checked", M,
     '    if state.disengage_checked or (runs["unusable_run"] < 2 and runs["dont_know_run"] < 3):',
     "    if True:"),
    ("recall: a figure from recall is asked again", M,
     "        and state.recall_figure is not None\n    ):", "        and False\n    ):"),
    ("amounts: no say-again for cover", M,
     "    if differ and product_id not in done:", "    if differ and not cover and product_id not in done:"),
    ("count: the follow-up's 'no' still goes to the product questions", M,
     "    if heard.intent in (Intent.took_nothing, Intent.no, Intent.dont_know):\n        return _say(state, AtConsent())\n    if heard.intent in UNCLEAR:\n        return _say(_mark_unresolved(state, position), AtConsent())",
     "    if heard.intent in UNCLEAR:\n        return _say(_mark_unresolved(state, position), AtConsent())"),
    ("limits: silence never ends the call", M,
     "    if silent and state.silences >= state.limits.max_silences:\n        return _end(state, Outcome.no_response)\n",
     ""),
    ("limits: read-backs unlimited", M,
     "    more = position.read_backs < state.limits.max_read_backs\n", "    more = True\n"),
]  # fmt: skip


def main() -> int:
    root = Path(sys.argv[1])
    results = []
    for name, rel, old, new in MUTATIONS:
        path = root / rel
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            results.append((name, "NOT APPLIED"))
            print(results[-1], flush=True)
            continue
        path.write_text(original.replace(old, new), encoding="utf-8")
        try:
            run = subprocess.run(
                ["uv", "run", "pytest", "tests/dialogue", "-q", "-x", "-p", "no:cacheprovider"],
                check=False, cwd=root, capture_output=True, text=True, timeout=900,
            )  # fmt: skip
            tail = run.stdout.strip().splitlines()[-1] if run.stdout.strip() else run.stderr[-200:]
            results.append((name, ("CAUGHT" if run.returncode else "SURVIVED") + "  " + tail))
        finally:
            path.write_text(original, encoding="utf-8")
        print(results[-1], flush=True)
    print()
    for name, verdict in results:
        print(f"{verdict[:11]:12s} {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
