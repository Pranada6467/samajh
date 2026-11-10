"""P3b re-verification (round 3): do tests/ops catch a regression of each fix? Runs ONLY in a copy.

Usage: python p3b_r3_mutate.py <copy of the repo> <python with the project's deps>
Each mutation is one exact string replacement in the copy (anchor must occur exactly once); the copy
is restored after each run. Prints CAUGHT (tests/ops failed) or SURVIVED (tests/ops passed).
Baseline of an unmutated copy of the working tree on 2026-11-10: 157 passed.
"""

import os
import subprocess
import sys
from pathlib import Path

COPY, PY = Path(sys.argv[1]).resolve(), sys.argv[2]
if COPY == Path(__file__).resolve().parents[4]:
    sys.exit("refusing to mutate the working tree")

MUTS = [
    # --- draws ---
    ("M-r3-01 (M6) store accepts an unchained draw", "samajh/ops/store.py",
     "if draw not in earlier and draw.after != (earlier[-1].as_of if earlier else None):", "if False:"),
    # --- India time (M12) ---
    ("M-r3-02 (M12) phone attempt time of day taken in UTC", "samajh/ops/sessions.py",
     "at = datetime.combine(book.call_date, case.started.astimezone(IST).timetz())",
     "at = datetime.combine(book.call_date, case.started.astimezone(UTC).timetz())"),
    ("M-r3-03 (M12) chain.india_day uses UTC", "samajh/ops/chain.py",
     "return (at if at.tzinfo else at.replace(tzinfo=IST)).astimezone(IST).date()",
     "return (at if at.tzinfo else at.replace(tzinfo=IST)).astimezone(timezone.utc).date()"),
    # --- chain rules ---
    ("M-r3-04 refusal: terminal outcome no longer ends the chain", "samajh/ops/chain.py",
     "    if last.outcome not in RETRY_AFTER:\n        return (", "    if False:\n        return ("),
    ("M-r3-05 refusal: attempt limit off by one (>= -> >)", "samajh/ops/chain.py",
     "return len(chain) >= max_attempts", "return len(chain) > max_attempts"),
    ("M-r3-06 refusal: limit check removed", "samajh/ops/chain.py",
     "    if at_limit(chain, max_attempts):\n        return (", "    if False:\n        return ("),
    ("M-r3-07 refusal: same-moment call accepted (<= -> <)", "samajh/ops/chain.py",
     "if at <= last.at:", "if at < last.at:"),
    ("M-r3-08 sessions ignores the chain refusal", "samajh/ops/sessions.py",
     "if existing is None and (why := refusal(chain, at)):", "if False and (why := refusal(chain, at)):"),
    ("M-r3-09 next_number = len(chain)+1", "samajh/ops/chain.py",
     "return chain[-1].number + 1 if chain else 1", "return len(chain) + 1"),
    ("M-r3-10 next_number always 1", "samajh/ops/chain.py",
     "return chain[-1].number + 1 if chain else 1", "return 1"),
    # --- supersede ---
    ("M-r3-11 may_supersede: any outcome may be superseded", "samajh/ops/store.py",
     "        and existing.outcome is AttemptOutcome.completed_not_analysed\n", ""),
    ("M-r3-12 sessions._write: supersede branch removed", "samajh/ops/sessions.py",
     "    if call is not None and may_supersede(existing, superseding):", "    if False:"),
    ("M-r3-13 _same_call always True", "samajh/ops/sessions.py",
     '    if saved is None:\n        return False\n    if saved == fresh:', "    return True\n    if saved == fresh:"),
    # --- attempt limit in the simulator ---
    ("M-r3-14 simulator default limit MAX_ATTEMPTS + 1", "samajh/ops/simulate.py",
     "    max_attempts: int = MAX_ATTEMPTS,", "    max_attempts: int = MAX_ATTEMPTS + 1,"),
    ("M-r3-15 simulator: phone attempts not counted towards the scripted step", "samajh/ops/simulate.py",
     "scripted = sum(not isinstance(a.source, PhoneSession) for a in made)", "scripted = len(made)"),
    # --- window ---
    ("M-r3-16 completed on day 31 counted", "samajh/ops/batch.py",
     "in_window = 0 <= last.day_since_sale <= WINDOW_DAYS", "in_window = 0 <= last.day_since_sale <= WINDOW_DAYS + 1"),
    ("M-r3-17 completed before the sale counted", "samajh/ops/batch.py",
     "in_window = 0 <= last.day_since_sale <= WINDOW_DAYS", "in_window = last.day_since_sale <= WINDOW_DAYS"),
    ("M-r3-18 timing counts day 30 as after the window", "samajh/ops/report.py",
     "after = [a for a in attempts if a.day_since_sale > WINDOW_DAYS]",
     "after = [a for a in attempts if a.day_since_sale >= WINDOW_DAYS]"),
    ("M-r3-19 window_note says none by design whatever the count", "samajh/ops/wording.py",
     "    if not after:\n        return \"No attempt was made after day 30 from the sale.\"",
     "    if True:\n        return \"None by design: no attempt was made after day 30 from the sale.\""),
    ("M-r3-20 simulator allows day 31", "samajh/ops/simulate.py",
     "if (day - loan.sold_on).days > WINDOW_DAYS:", "if (day - loan.sold_on).days > WINDOW_DAYS + 1:"),
    # --- narrow threshold ---
    ("M-r3-21 NARROW_RATIO 1.25 -> 1.5", "samajh/ops/report.py", "NARROW_RATIO = 1.25", "NARROW_RATIO = 1.5"),
    ("M-r3-22 ratio <= NARROW_RATIO -> <", "samajh/ops/report.py",
     'return "narrow" if ratio is not None and ratio <= NARROW_RATIO else "wide"',
     'return "narrow" if ratio is not None and ratio < NARROW_RATIO else "wide"'),
    ("M-r3-23 intervals always shown", "samajh/ops/report.py",
     'intervals_shown=chances != "wide",', "intervals_shown=True,"),
    ("M-r3-24 share function ignores the withheld intervals", "samajh/ops/report.py",
     "share: Share = proportion if chosen.intervals_shown else plain_share", "share: Share = proportion"),
    # --- audio note ---
    ("M-r3-25 phone_note: mic-only counts sessions with both", "samajh/ops/wording.py",
     "mic = sum(a.mic > 0 and a.file == 0 for a in known)", "mic = sum(a.mic > 0 for a in known)"),
    ("M-r3-26 phone_note: unknown part dropped", "samajh/ops/wording.py",
     "    if unknown:\n        parts.append(", "    if False:\n        parts.append("),
    ("M-r3-27 phone_note: absent customer_audio counted as no audio", "samajh/ops/wording.py",
     "known = [s.customer_audio for s in sessions if s.customer_audio is not None]",
     "known = [s.customer_audio or __import__('samajh.ops.model', fromlist=['m']).CustomerAudio(mic=0, file=0, none=0) for s in sessions]"),
    # --- "finding" lint ---
    ("M-r3-28 'finding' removed from BANNED", "samajh/ops/wording.py",
     '    r"\\bfinding",  # a flag is evidence for review; the word reads as a conclusion about the sale\n', ""),
    ("M-r3-29 tier label 'No finding' back", "samajh/ops/wording.py", '"Nothing to refer"', '"No finding"'),
    ("M-r3-30 risk note says 'findings'", "samajh/ops/wording.py",
     '"Risk coverage is thin. One question', '"Risk findings are thin. One question'),
    # --- readings line ---
    ("M-r3-31 readings: closing pairs swapped (same/differ read back)", "samajh/ops/views.py",
     "    (True, \"read_back\"): wording.READINGS_SAME_READ_BACK,",
     "    (True, \"read_back\"): wording.READINGS_DIFFER_READ_BACK,"),
    ("M-r3-32 readings: null agreement called 'differ'", "samajh/ops/views.py",
     "    elif turn.agreed is None:\n        closing = wording.READINGS_NOT_COMPARED\n", ""),
    ("M-r3-33 readings: text shown though ok is false", "samajh/ops/views.py",
     "if reading.ok and reading.text:", "if reading.text:"),
    ("M-r3-34 readings: followed_by ignored", "samajh/ops/views.py",
     "closing = _CLOSING.get((turn.agreed, turn.followed_by), bare)", "closing = bare"),
    ("M-r3-35 readings: one-reading case says same amount", "samajh/ops/views.py",
     "        closing = wording.READINGS_ONE", "        closing = wording.READINGS_SAME"),
    ("M-r3-36 review.js: separator before closing changed", "web/review/review.js",
     "(i ? [\" · \", ...p] : p)), ` · ${r.closing}`);", "(i ? [\" · \", ...p] : p)), ` / ${r.closing}`);"),
    # --- sessions: dates and undrawn loans ---
    ("M-r3-37 undrawn loan with a book block skipped, not outside", "samajh/ops/sessions.py",
     "    if draw is None:\n        _as_outside(store, case, NOT_DRAWN, loan.record, at)\n        return \"outside\"",
     "    if draw is None:\n        raise _Skip(\"not drawn\")"),
    ("M-r3-38 call before the sale accepted", "samajh/ops/sessions.py",
     "    if day < 0:\n        raise _Skip(", "    if False:\n        raise _Skip("),
    ("M-r3-39 call before the draw accepted", "samajh/ops/sessions.py",
     "    if book.call_date < draw.as_of:\n        raise _Skip(", "    if False:\n        raise _Skip("),
    ("M-r3-40 day_since_sale mismatch accepted", "samajh/ops/sessions.py",
     "    if book.day_since_sale != day:\n        raise _Skip(", "    if False:\n        raise _Skip("),
    ("M-r3-41 sold_on mismatch accepted", "samajh/ops/sessions.py",
     "    if book.sold_on != loan.sold_on:\n        raise _Skip(", "    if False:\n        raise _Skip("),
    ("M-r3-42 draw_id mismatch accepted", "samajh/ops/sessions.py",
     "    if book.draw_id != draw.draw_id:\n        raise _Skip(", "    if False:\n        raise _Skip("),
    ("M-r3-43 batch_id mismatch accepted", "samajh/ops/sessions.py",
     "    if book.batch_id != batch.batch_id:\n        raise _Skip(", "    if False:\n        raise _Skip("),
    ("M-r3-44 record_id mismatch accepted", "samajh/ops/sessions.py",
     "    if case.record_id != case.loan_id:\n        raise _Skip(", "    if False:\n        raise _Skip("),
    # --- outcomes ---
    ("M-r3-45 FROM_DIALOGUE loses do_not_call", "samajh/ops/model.py",
     '    "do_not_call": AttemptOutcome.do_not_call,\n', ""),
    ("M-r3-46 do_not_call treated as a retry", "samajh/ops/model.py",
     "{AttemptOutcome.no_answer, AttemptOutcome.call_back_later, AttemptOutcome.language_switch}",
     "{AttemptOutcome.no_answer, AttemptOutcome.call_back_later, AttemptOutcome.language_switch, AttemptOutcome.do_not_call}"),
    ("M-r3-47 failed case file counted as completed", "samajh/ops/sessions.py",
     'if outcome is AttemptOutcome.completed and case.status != "ready":', "if False:"),
    # --- tiles ---
    ("M-r3-48 completed tile from right_party_confirmed", "samajh/ops/report.py",
     'completed=next(row.value.count for row in reach.stages if row.key == "completed"),',
     'completed=next(row.value.count for row in reach.stages if row.key == "right_party_confirmed"),'),
    ("M-r3-49 most common gap: last of a tie", "samajh/ops/report.py",
     "top = max(rules, key=lambda r: r.understanding_gap, default=None)",
     "top = max(reversed(rules), key=lambda r: r.understanding_gap, default=None)"),
    ("M-r3-50 sold tile counts sampled", "samajh/ops/report.py",
     "sold=chosen.sales_in_period,", "sold=chosen.eligible,"),
    # --- ingest summary / store hygiene ---
    ("M-r3-51 orphan session call files are kept", "samajh/ops/sessions.py",
     "        store.drop_unreferenced_session_calls()\n", ""),
    ("M-r3-52 ingest summary not saved", "samajh/ops/sessions.py",
     "        store.save_ingest_summary(found.summary())\n", ""),
]

for name, rel, old, new in MUTS:
    p = COPY / rel
    src = p.read_text()
    if src.count(old) != 1:
        print(f"{name}: SKIP (anchor found {src.count(old)} times)", flush=True)
        continue
    p.write_text(src.replace(old, new))
    try:
        r = subprocess.run(
            [PY, "-m", "pytest", "tests/ops", "-q", "-p", "no:cacheprovider", "-x"],
            cwd=COPY, capture_output=True, text=True, timeout=600,
            env={**os.environ, "PYTHONPATH": str(COPY), "SAMAJH_STATE_DIR": str(COPY / ".state")},
        )
        lines = r.stdout.strip().splitlines()
        last = lines[-1] if lines else r.stderr[-200:]
        failed = next((ln for ln in lines if ln.startswith("FAILED") or ln.startswith("ERROR")), "")
        print(f"{name}: {'CAUGHT' if r.returncode else 'SURVIVED'} | {last} | {failed[:160]}", flush=True)
    finally:
        p.write_text(src)
