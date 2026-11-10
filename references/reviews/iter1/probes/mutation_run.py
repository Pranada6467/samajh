"""Verifier probe: mutation runs for samajh/clients and samajh/dialogue, in a scratch copy only.

    uv run python references/reviews/iter1/probes/mutation_run.py /path/to/scratch/copy

The copy must be a copy of the repository without .git, .samajh and .venv. Each mutation is one
small edit that breaks one behaviour; the matching test directory is then run from inside the
copy with the repository's interpreter. "killed" means some test failed. The script refuses to
run on the repository itself.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]

MUTATIONS = [
    # (name, file, before, after, tests)
    ("M1 credit guard removed", "samajh/clients/gnani/client.py",
     "            self._check_cap(estimate)\n            response, info = self._send(send,",
     "            response, info = self._send(send,", "tests/clients"),
    ("M2 REST call without the cross-process lock", "samajh/clients/gnani/client.py",
     "        with single_flight(self._lock, timeout=self._lock_timeout):\n            hit = self._cached(key, kind, model, units, decode)",
     "        if True:\n            hit = self._cached(key, kind, model, units, decode)", "tests/clients"),
    ("M3 cache never hits", "samajh/clients/gnani/client.py",
     "        entry = self._cache.get(key)\n        if entry is None:\n            return None",
     "        entry = None\n        if entry is None:\n            return None", "tests/clients"),
    ("M4 one retry more than the policy allows", "samajh/clients/_runtime.py",
     "        last = number >= policy.max_attempts", "        last = number >= policy.max_attempts + 1", "tests/clients"),
    ("M5 key not redacted from error text", "samajh/clients/gnani/client.py",
     '        message = message.replace(self._api_key, "<key>")[:300]', "        message = message[:300]", "tests/clients"),
    ("M6 credits booked on failed attempts too", "samajh/clients/gnani/client.py",
     "                est_credits=estimate if ok else 0.0,", "                est_credits=estimate,", "tests/clients"),
    ("M7 LLM: temperature sent to every model", "samajh/clients/llm.py",
     'if temperature is not None and "temperature" in self._sampling.sent_to(model):', "if temperature is not None:", "tests/clients"),
    ("M8 LLM: USD cap never refuses", "samajh/clients/llm.py",
     "        if spent >= self._usd_cap or spent + estimate > self._usd_cap:", "        if False:", "tests/clients"),
    ("M9 wrong person at the first question is not an end", "samajh/dialogue/machine.py",
     "    if heard.intent in (Intent.no, Intent.wrong_person):\n        return _end(state, Outcome.wrong_party)",
     "    if heard.intent is Intent.no:\n        return _end(state, Outcome.wrong_party)", "tests/dialogue"),
    ("M10 wrong person passes the second check with the right year", "samajh/dialogue/machine.py",
     "    if heard.intent is Intent.wrong_person:  # \"I am his wife, he was born in 1984\" names the year too\n        return _end(state, Outcome.wrong_party)\n",
     "", "tests/dialogue"),
    ("M11 stop question has no limit", "samajh/dialogue/machine.py",
     "        if state.stop_checks >= state.limits.max_stop_checks:", "        if False:", "tests/dialogue"),
    ("M12 no turn budget", "samajh/dialogue/machine.py",
     "    if state.bot_turns + 1 >= state.limits.max_bot_turns:", "    if False:", "tests/dialogue"),
    ("M13 second reading never used", "samajh/dialogue/machine.py",
     "        if not agreed and _brings_no_figure(position, heard):", "        if False:", "tests/dialogue"),
    ("M14 a failed LLM call is passed over in silence", "samajh/dialogue/llm_fallback.py",
     '            return first.model_copy(update={"intent": Intent.unclear})', "            return first", "tests/dialogue"),
    ("M15 the lint accepts every line", "samajh/dialogue/lint.py",
     "    for ban, phrase in banned_in(template):", "    for ban, phrase in []:", "tests/dialogue"),
    ("M16 the call keeps the record's premium", "samajh/dialogue/machine.py",
     "        position=AtIdentity(),\n    )",
     "        position=AtIdentity(),\n        premiums=tuple(StatedPremium(product_id=p.id, amount_inr=p.premium_inr) for p in record.products),\n    )",
     "tests/dialogue"),
    ("M17 a quoted refusal ends the call (R4 undone)", "samajh/dialogue/interpret.py",
     "        quoted = expecting not in _NO_ACCOUNT_OF_THE_SALE and _has(words, lexicon.recounts)", "        quoted = False", "tests/dialogue"),
    ("M18 a single digit is a birth year (R2 undone)", "samajh/dialogue/machine.py",
     "(short >= 10 and heard.year == short)", "(heard.year == short)", "tests/dialogue"),
]  # fmt: skip


def main(copy: Path) -> None:
    copy = copy.resolve()
    if copy == REPO or REPO in copy.parents or (copy / ".git").exists():
        sys.exit("refusing: the target must be a scratch copy outside the repository")
    python = REPO / ".venv" / "bin" / "python"
    env = dict(os.environ, SAMAJH_STATE_DIR=str(copy / ".state"), PYTHONDONTWRITEBYTECODE="1")
    where = subprocess.run([python, "-c", "import samajh; print(samajh.__file__)"], cwd=copy, env=env,
                           capture_output=True, text=True).stdout.strip()  # fmt: skip
    print(f"imports resolve to: {where}")
    if not where.startswith(str(copy)):
        sys.exit("refusing: the copy is not what gets imported")
    wanted = sys.argv[2:]
    for name, file, before, after, tests in MUTATIONS:
        if wanted and not any(name.startswith(w) for w in wanted):
            continue
        path = copy / file
        original = path.read_text(encoding="utf-8")
        if original.count(before) != 1:
            print(f"{name}: SKIPPED, pattern found {original.count(before)} times")
            continue
        path.write_text(original.replace(before, after), encoding="utf-8")
        try:
            run = subprocess.run([python, "-m", "pytest", tests, "-q", "-x", "-p", "no:cacheprovider", "--no-header"],
                                 cwd=copy, env=env, capture_output=True, text=True, timeout=900)  # fmt: skip
        finally:
            path.write_text(original, encoding="utf-8")
        tail = run.stdout.strip().splitlines()
        failed = next((line for line in tail if line.startswith("FAILED") or line.startswith("ERROR")), "")
        verdict = "killed" if run.returncode != 0 else "SURVIVED"
        print(f"{name}: {verdict} | {tail[-1] if tail else ''} | {failed[:160]}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
