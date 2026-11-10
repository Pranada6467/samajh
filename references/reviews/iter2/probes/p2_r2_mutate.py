"""Mutation checks for P2 round 2, run ONLY on a scratch copy of the repo (never the working tree).

uv run python references/reviews/iter2/probes/p2_r2_mutate.py <scratch_dir>
  <scratch_dir>/base must be a copy of the repo (rsync without .git/.venv/references/eval/tests/fixtures).
Each mutant is a fresh copy of base with one exact-string edit; `pytest tests/dialogue -q -x` decides killed/survived.
Writes p2_r2_mutate.json beside this file (a timestamped copy if it exists).
"""

import json
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = str(HERE.parents[3] / ".venv/bin/python")

FB = "samajh/dialogue/llm_fallback.py"
MC = "samajh/dialogue/machine.py"
MUTANTS = [
    ("opening_default_off: a failed classifier at the first-name question keeps the word lists' yes",
     FB, "            return self._unjudged(first, expecting)\n        if expecting is Expecting.birth_year",
     "            return first.model_copy(update={'degraded': True})\n        if expecting is Expecting.birth_year"),
    ("unjudged_identity_yes_kept: _unjudged no longer downgrades a word-list yes at identity",
     FB, "        if expecting is Expecting.identity and first.intent is Intent.yes:\n            first = first.model_copy(update={\"intent\": Intent.said})",
     "        pass"),
    ("classifier_secondary: consulted only when the word lists say said/unclear/off_topic",
     FB, "        if table is None or first.settled:\n            return first",
     "        if table is None or first.settled or first.intent not in (Intent.said, Intent.unclear, Intent.off_topic):\n            return first"),
    ("first_person_guard_off: confirms_self accepted without a first-person word",
     FB, "        if label is _Label.confirms_self and not speaks_in_first_person(text, language):\n            label = _Label.unclear",
     "        pass"),
    ("refusal_falls_through: a plain decline no longer ends the call",
     MC, "    if heard.intent is Intent.decline:\n        return _end(state, Outcome.declined)",
     "    if heard.intent is Intent.decline:\n        heard = heard.model_copy(update={'intent': Intent.said})"),
    ("do_not_call_dropped: do_not_call ends as declined",
     MC, "    if heard.intent is Intent.do_not_call:\n        return _end(state, Outcome.do_not_call)",
     "    if heard.intent is Intent.do_not_call:\n        return _end(state, Outcome.declined)"),
    ("written_dropped: written_request ends as declined",
     MC, "    if heard.intent is Intent.written_request:\n        return _end(state, Outcome.written_requested)",
     "    if heard.intent is Intent.written_request:\n        return _end(state, Outcome.declined)"),
    ("degraded_check_off: no 'shall I go on?' after a failed classifier",
     MC, "    if failed and not state.degraded_checked:", "    if False:"),
    ("timeout_unbounded: the 2.5 s wall-clock bound is not enforced",
     FB, "        return _POOL.submit(ask).result(timeout=self._timeout_s)", "        return ask()"),
    ("weak_signal_guard_off: a weak stop signal is overridden by any classifier label",
     FB, "        if first.intent in _WEAK and intent not in _KEEPS_WEAK:\n            return first",
     "        pass"),
    ("callback_ask_off: a call-later with no time ends at once instead of asking when",
     MC, "        if heard.callback == \"ask\":\n            return _say(state, AtCallbackTime())", "        pass"),
    ("third_party_midcall_off: a hand-off after the opening no longer ends the call",
     MC, "    if heard.intent is Intent.wrong_person and not isinstance(position, (*_BEFORE_LOAN, AtStopCheck)):\n        return _end(state, Outcome.wrong_party)",
     "    pass"),
]


def main(scratch: Path):
    base = scratch / "base"
    assert (base / MC).exists(), "base copy missing"
    rows = []
    b = subprocess.run([PY, "-m", "pytest", "tests/dialogue", "-q", "-p", "no:cacheprovider"], cwd=base,
                       capture_output=True, text=True, timeout=900)
    print("baseline:", b.stdout.strip().splitlines()[-1], flush=True)
    if b.returncode != 0:
        raise SystemExit("the unmutated copy fails its tests: fix the copy first (e.g. references/pilots/P2-lines-for-review.md)")
    rows.append({"mutant": "baseline (no mutation)", "result": "passes", "summary": b.stdout.strip().splitlines()[-1]})
    for name, rel, old, new in MUTANTS:
        d = scratch / "m"
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(base, d, symlinks=True)
        f = d / rel
        src = f.read_text()
        if src.count(old) != 1:
            rows.append({"mutant": name, "result": "anchor_not_found"})
            print(name, "ANCHOR NOT FOUND")
            continue
        f.write_text(src.replace(old, new))
        t0 = time.time()
        p = subprocess.run([PY, "-m", "pytest", "tests/dialogue", "-q", "-x", "-p", "no:cacheprovider"],
                           cwd=d, capture_output=True, text=True, timeout=900)
        tail = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-300:]
        failed_test = next((l for l in p.stdout.splitlines() if l.startswith("FAILED")), "")
        res = "killed" if p.returncode != 0 else "survived"
        rows.append({"mutant": name, "file": rel, "result": res, "summary": tail, "first_failure": failed_test,
                     "seconds": round(time.time() - t0, 1)})
        print(f"{res:9s} {name} :: {tail} {failed_test[:120]}", flush=True)
    out = HERE / "p2_r2_mutate.json"
    if out.exists():
        out = HERE / f"p2_r2_mutate_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
