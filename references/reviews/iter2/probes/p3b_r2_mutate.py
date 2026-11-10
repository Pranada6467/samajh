"""P3b re-verification (round 2): do tests/ops catch a regression of each fix? Runs ONLY in a copy.

Usage: python p3b_r2_mutate.py <copy of the repo> <python with the project's deps>
Each mutation is one exact string replacement in the copy; the copy is restored after each run.
Baseline in the working tree of 2026-11-10: 72 passed, 1 failed (do_not_call / written_requested).
"""
import subprocess, sys, os
from pathlib import Path

COPY, PY = Path(sys.argv[1]).resolve(), sys.argv[2]
if COPY == Path(__file__).resolve().parents[4]:
    sys.exit("refusing to mutate the working tree")
MUTS = [
    ("M1 window boundary: a sale on the previous draw day is eligible again", "samajh/ops/sampler.py",
     "loan.sold_on > after", "loan.sold_on >= after"),
    ("M2 day 30 excluded from eligibility", "samajh/ops/sampler.py",
     "min_day <= (as_of - loan.sold_on).days <= max_day", "min_day <= (as_of - loan.sold_on).days < max_day"),
    ("M3 attempts allowed on day 31", "samajh/ops/simulate.py",
     "if (day - loan.sold_on).days > WINDOW_DAYS:", "if (day - loan.sold_on).days > WINDOW_DAYS + 1:"),
    ("M4 retry on day 30 counted as unreachable", "samajh/ops/batch.py",
     "last.day_since_sale >= WINDOW_DAYS", "last.day_since_sale > WINDOW_DAYS"),
    ("M5 late completion counted in findings", "samajh/ops/batch.py",
     "in_window = 0 <= last.day_since_sale <= WINDOW_DAYS", "in_window = True"),
    ("M6 store accepts an unchained draw", "samajh/ops/store.py",
     "if draw not in earlier and draw.after != (earlier[-1].as_of if earlier else None):", "if False:"),
    ("M7 verify ignores chaining", "samajh/ops/sampler.py",
     "return chained and found == (draw.eligible, draw.drawn)", "return found == (draw.eligible, draw.drawn)"),
    ("M8 decision label says Established", "samajh/ops/wording.py",
     '"Concern supported by the file (reviewer\'s view)"', '"Established"'),
    ("M9 decision label says mis-selling found", "samajh/ops/wording.py",
     '"Concern supported by the file (reviewer\'s view)"', '"Mis-selling found"'),
    ("M10 decision counts get intervals", "samajh/ops/report.py",
     "value=Count(count=sum(d is not None and d.decision is decision for d in latest), n=n),",
     "value=proportion(sum(d is not None and d.decision is decision for d in latest), n),"),
    ("M11 failed case file counted as completed", "samajh/ops/sessions.py",
     'if outcome is AttemptOutcome.completed and case.status != "ready":', "if False:"),
    ("M12 phone day computed in UTC", "samajh/ops/sessions.py",
     "day_since_sale=(at.astimezone(IST).date() - loan.sold_on).days", "day_since_sale=(at.astimezone(UTC).date() - loan.sold_on).days"),
    ("M13 outside sessions counted (linked to first draw)", "samajh/ops/sessions.py",
     "        if link is None:\n            record = records(case.record_id)", "        if False:\n            record = records(case.record_id)"),
    ("M14 tier label 'No finding' back", "samajh/ops/wording.py", '"Nothing to refer"', '"No finding"'),
    ("M15 risks group dropped (belief_mismatch -> features)", "samajh/ops/wording.py",
     'RuleId.belief_mismatch: "risks",', 'RuleId.belief_mismatch: "features",'),
]
for name, rel, old, new in MUTS:
    p = COPY / rel
    src = p.read_text()
    if src.count(old) != 1:
        print(f"{name}: SKIP (anchor found {src.count(old)} times)")
        continue
    p.write_text(src.replace(old, new))
    try:
        r = subprocess.run([PY, "-m", "pytest", "tests/ops", "-q", "-p", "no:cacheprovider", "-x", "--deselect",
                            "tests/ops/test_ops_sessions.py::test_every_dialogue_outcome_has_an_attempt_outcome"],
                           cwd=COPY, capture_output=True, text=True, timeout=600,
                           env={**os.environ, "PYTHONPATH": str(COPY), "SAMAJH_STATE_DIR": str(COPY / ".state")})
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:]
        print(f"{name}: {'CAUGHT' if r.returncode else 'SURVIVED'} | {last}")
    finally:
        p.write_text(src)
