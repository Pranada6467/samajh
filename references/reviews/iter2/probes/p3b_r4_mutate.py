"""P3b round 4, claim 8: mutations of samajh/ops in a COPY of the repo; is each caught by tests/ops?

usage: .venv/bin/python references/reviews/iter2/probes/p3b_r4_mutate.py <repo copy> <python>
Refuses to run on the working tree. Each mutation is applied, tests/ops run, the file restored.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

COPY = Path(sys.argv[1]).resolve()
PY = sys.argv[2]
if (COPY / ".git").exists() or COPY == Path(__file__).resolve().parents[4]:
    sys.exit("refusing: that is the working tree")

M = [
    ("M1 torn line not set aside", "samajh/ops/store.py", "        if not tail:\n            return\n        if _parse_or_none(model, tail) is not None:\n            fd",
     "        return\n        if _parse_or_none(model, tail) is not None:\n            fd"),
    ("M2 ratio compared in floats", "samajh/ops/report.py", "high <= NARROW_RATIO * low", "float(high) / float(low) <= 1.25"),
    ("M3 catch only ValueError/KeyError/TypeError per session", "samajh/ops/sessions.py",
     "            except Exception as error:  # noqa: BLE001 - no session may stop the run\n                store.drop",
     "            except (ValueError, KeyError, TypeError) as error:\n                store.drop"),
    ("M4 changed brought-in session listed as skipped", "samajh/ops/sessions.py", "        place = brought.get(sid)\n", "        place = None\n"),
    ("M5 started_at must-be-text check dropped", "samajh/ops/sessions.py",
     '        if not isinstance(value, str):\n            raise ValueError("the start time is not written as text")',
     '        if False:\n            raise ValueError("the start time is not written as text")'),
    ("M6 request_unconfirmed mapped to do_not_call", "samajh/ops/model.py",
     "        return AttemptOutcome.request_unconfirmed\n", "        return AttemptOutcome.do_not_call\n"),
    ("M7 at <= last.at to <", "samajh/ops/chain.py", "    if at <= last.at:", "    if at < last.at:"),
    ("M8 sold tile shows the eligible count", "samajh/ops/report.py", "        sold=chosen.sales_in_period,", "        sold=chosen.eligible,"),
    ("M9 reading text shown when ok is false", "samajh/ops/views.py", "    if reading.ok and reading.text:", "    if reading.text:"),
    ("M10 ok taken in lax mode", "samajh/ops/sessions.py", "        return value if isinstance(value, bool) else False", "        return bool(value)"),
    ("M11 readings_agreed taken in lax mode", "samajh/ops/sessions.py", "        return value if isinstance(value, bool) else None",
     "        return None if value is None else bool(value)"),
    ("M12 year check on started_at dropped", "samajh/ops/sessions.py", "        _check_year(utc.date())\n        return utc", "        return utc"),
    ("M13 request_unconfirmed not retryable", "samajh/ops/model.py",
     "        AttemptOutcome.language_switch,\n        AttemptOutcome.request_unconfirmed,\n", "        AttemptOutcome.language_switch,\n"),
    ("M14 only-outside batch gets simulated-only limits", "samajh/ops/wording.py", "    if not phone_attempts and not phone_outside:", "    if not phone_attempts:"),
    ("M15 changed analysed call not noticed", "samajh/ops/sessions.py", "        if call is not None and not _same_call(saved, call):", "        if False:"),
]

env = dict(os.environ, PYTHONPATH=str(COPY))
base = subprocess.run([PY, "-m", "pytest", "tests/ops", "-q", "-x", "-p", "no:cacheprovider"], cwd=COPY, env=env, capture_output=True, text=True)
print("baseline:", base.stdout.strip().splitlines()[-1])
caught, survived = [], []
for name, rel, old, new in M:
    p = COPY / rel
    src = p.read_text()
    if src.count(old) != 1:
        print(f"{name}: pattern found {src.count(old)} times; not applied")
        continue
    p.write_text(src.replace(old, new))
    try:
        r = subprocess.run([PY, "-m", "pytest", "tests/ops", "-q", "-x", "-p", "no:cacheprovider"], cwd=COPY, env=env,
                           capture_output=True, text=True, timeout=300)
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:]
        (caught if r.returncode else survived).append(name)
        print(f"{name}: {'CAUGHT' if r.returncode else 'SURVIVED'} ({last})")
    finally:
        p.write_text(src)
print(f"caught {len(caught)}, survived {len(survived)}: {survived}")
