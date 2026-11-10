"""Mutants for P2 round 3, applied to copies under a scratch dir (never the repo). usage: p2_r3_mutate.py SCRATCH_MUT_DIR"""
import shutil, subprocess, sys, json
from pathlib import Path
M = {
 "M0_control_unmutated": ("machine.py", "", "", 0),
 "M1_year_off_by_one": ("machine.py", "year == known or (short >= 10 and year == short)", "abs(year - known) <= 1 or (short >= 10 and year == short)", 1),
 "M2_two_years_accepted": ("machine.py", "if not heard.two_years and matches(heard.year):", "if matches(heard.year):", 1),
 "M3_takeover_check_off": ("machine.py", "if heard.possible_takeover and isinstance(position, _QUESTION_POSITIONS):", "if False and heard.possible_takeover:", 1),
 "M4_who_check_resumes_on_takeover": ("machine.py", "if heard.intent is Intent.yes and not heard.possible_takeover:", "if heard.intent is Intent.yes:", 1),
 "M5_two_reading_stop_ignored": ("machine.py", "if _protects_more(other, heard):", "if False:", 1),
 "M6_readback_repeat_not_confirm": ("machine.py", "if heard.intent is Intent.yes or (figure is not None and heard.only_amount and figure.about == read.about):", "if heard.intent is Intent.yes:", 1),
 "M7_recall_dontknow_to_nothing": ("machine.py", "heard.intent in (Intent.took_nothing, Intent.no, Intent.dont_know) and not heard.names_something\n    ):\n        return _say(state, AtRecallFollowUp())", "heard.intent in (Intent.took_nothing, Intent.no, Intent.dont_know)\n    ):\n        return _say(state, AtRecallFollowUp())", 1),
 "M8_now_at_callback_ignored": ("machine.py", "if position.resume is not None and means_now(customer_text, state.language):", "if False:", 1),
}
root = Path(sys.argv[1]); base = root / "base"; py = "/Users/masterpanda/projects/gnani-voice-ai-challenge/.venv/bin/python"
procs = {}
for name, (f, old, new, n) in M.items():
    d = root / name
    if d.exists(): shutil.rmtree(d)
    shutil.copytree(base, d, symlinks=True)
    p = d / "samajh/dialogue" / f
    s = p.read_text()
    if n:
        assert s.count(old) >= 1, name
        p.write_text(s.replace(old, new, n))
    procs[name] = subprocess.Popen([py, "-m", "pytest", "tests/dialogue", "-x", "-q", "-p", "no:cacheprovider", "--deselect", "tests/dialogue/test_export_lines.py::test_the_exported_file_holds_every_current_line"], cwd=d,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
res = {}
for name, pr in procs.items():
    out = pr.communicate()[0]
    last = [l for l in out.splitlines() if l.strip()][-1]
    fails = [l for l in out.splitlines() if l.startswith("FAILED")]
    res[name] = dict(killed=pr.returncode != 0, summary=last, first_failure=fails[:1])
    print(name, "KILLED" if pr.returncode else "SURVIVED", "|", last, "|", fails[:1])
(Path(__file__).with_name("p2_r3_mutate.json")).write_text(json.dumps(res, indent=1))
