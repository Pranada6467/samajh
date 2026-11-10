"""Verifier probe: mutation check of the in-scope tests. Never touches the repo.

    uv run python references/reviews/iter1/probes/mutate.py <scratch-dir>

Copies samajh/, tests/, eval/, data/ and pyproject.toml into <scratch-dir>, then for each
mutation below breaks one behaviour in the copy, runs tests/core, tests/scenarios and
tests/extract there, and reports how many tests failed. A mutation that no test notices is
printed as SURVIVED.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TESTS = ["tests/core", "tests/scenarios", "tests/extract"]

# (name, behaviour, file, old, new)
MUTATIONS = [
    ("M01", "a gap blocks `clear`",
     "samajh/types.py", "return Verdict.unclear_needs_human if gaps else Verdict.clear", "return Verdict.clear"),
    ("M01b", "a gap blocks `clear` (engine side too)",
     "samajh/rules/engine.py", "verdict = Verdict.unclear_needs_human", "verdict = Verdict.clear"),
    ("M02", "a matching premium passes only after a confirmed read-back",
     "samajh/rules/checks.py", "        if confirmed:\n            return _passed(rule, p.id)", "        if True:\n            return _passed(rule, p.id)"),
    ("M03", "a customer who does not recognise the product is a consent flag",
     "samajh/rules/checks.py", "return (_flag(rule, p.id, Why.consent_not_recognised, expected, heard, a.evidence),)", "return _passed(rule, p.id)"),
    ("M03b", "a different consent method is a flag",
     "samajh/rules/checks.py", "if method.value is on_record:", "if True:"),
    ("M04", "a kind that differs from the record is a flag",
     "samajh/rules/checks.py", "    if differing:\n        return tuple(", "    if False:\n        return tuple("),
    ("M05", "premium from the loan with no consent record is a flag",
     "samajh/rules/checks.py", "if p.paid_from_loan and p.consent is None:", "if False:"),
    ("M06", "required + customer not told of a choice of provider is a flag",
     "samajh/rules/checks.py", "if isinstance(choice, Stated) and not choice.value:\n        heard = f\"{how}; customer says", "if False:\n        heard = f\"{how}; customer says"),
    ("M06b", "required + not a risk mitigant is a flag",
     "samajh/rules/checks.py", "    if not p.risk_mitigant:\n        heard", "    if False:\n        heard"),
    ("M07", "a belief the product does not have is a flag",
     "samajh/rules/checks.py", "if claim not in p.features:", "if False:"),
    ("M08", "an answer counts only in a reply to its own question",
     "samajh/rules/normalise.py", "if reply and reply.asked & accepted:", "if reply:"),
    ("M09", "an answer's quote must be whole clauses (no negation-truncated quote)",
     "samajh/rules/normalise.py", "reply = _said(ev, replies, whole_clauses=True)", "reply = _said(ev, replies, whole_clauses=False)"),
    ("M10", "a read-back 'yes' confirms only the amount that was read back",
     "samajh/rules/normalise.py", "            or _rupees(read_back_turn.text, False) != premium.value\n", ""),
    ("M10b", "a read-back 'yes' given before the amount confirms nothing",
     "samajh/rules/normalise.py", "readback.evidence.turn_id <= premium.evidence.turn_id", "False"),
    ("M11", "the LLM's amount span must agree with the parser's reading of the whole reply",
     "samajh/rules/normalise.py", "if heard is None or heard != read(span, True):", "if heard is None:"),
    ("M12", "premium tolerance is 1%",
     "samajh/rules/checks.py", "> on_record * AMOUNT_TOLERANCE_PERCENT", "> on_record * 10"),
    ("M13", "two different amounts in one text are refused",
     "samajh/amounts/_parse.py", "        if len({p.rupees for p in strong_ok}) > 1:", "        if False:"),
    ("M14", "a negated or compared amount is refused",
     "samajh/amounts/_parse.py", "if run.hedged or (strong and _hedged_in_clause(text, toks, run.start, run.end)):", "if False:"),
    ("M15", "an enum answer needs an in-range clause pointer",
     "samajh/extract/_extract.py", "if self.reply.cover(clauses) is None:", "if False:"),
    ("M16", "the identity checks are never sent to the model",
     "samajh/extract/_extract.py", "if slot.step in _IDENTITY:", "if slot.step in ():"),
    ("M17", "a volunteered claim from the screening call reaches the rules",
     "samajh/extract/_extract.py", "        for claim in wire.claims:\n            found = g.find(\"claims\"", "        for claim in ():\n            found = g.find(\"claims\""),
    ("M18", "a later unusable answer does not replace an earlier usable one",
     "samajh/extract/_extract.py", "if replace or old is None or _usable(answer) or not _usable(old):", "if True:"),
    ("M19", "a product the customer does not name in open recall is a flag",
     "samajh/rules/checks.py", "    if _matched(p, beliefs):\n        return _passed(rule, p.id)\n    return (\n        _flag(\n            rule,\n            p.id,\n            Why.recall_not_named", "    if True:\n        return _passed(rule, p.id)\n    return (\n        _flag(\n            rule,\n            p.id,\n            Why.recall_not_named"),
    ("M20", "a customer not told they can cancel is a flag",
     "samajh/rules/checks.py", "            return (_flag(rule, p.id, Why.cancel_unaware, expected, heard, a.evidence),)", "            return _passed(rule, p.id)"),
    ("M21", "a sale concern is a flag",
     "samajh/rules/checks.py", "        for c in beliefs.sale_concerns\n    )\n    return flags or _passed(rule, None)", "        for c in ()\n    )\n    return flags or _passed(rule, None)"),
    ("M22", "an ungrounded quote is an evidence gap",
     "samajh/rules/checks.py", "    return gaps or _passed(rule, p.id)", "    return _passed(rule, p.id)"),
    ("M23", "a fraction word before a number changes it (paune, sawa, saadhe)",
     "samajh/amounts/_grammar.py", "            coef += pre", "            coef += 0"),
    ("M24", "'I do not know' is a flag, not a pass",
     "samajh/rules/checks.py", "        return (_flag(rule, product_id, dont_know, expected, DONT_KNOW, answer.evidence),)", "        return _passed(rule, product_id)"),
    ("M25", "a span the model returns must be in the reply",
     "samajh/extract/_ground.py", "            if forms[k : k + len(wanted)] == wanted:", "            if forms[k : k + len(wanted)] == wanted or k == 0:"),
    ("M26", "premium paid from the loan and the customer says 'separately' is a flag",
     "samajh/rules/checks.py", "        return (_flag(rule, p.id, other, expected, heard, a.evidence),)", "        return _passed(rule, p.id)"),
    ("M27", "a recall item counts only when said in reply to the open-recall question",
     "samajh/rules/normalise.py", "return recall_asked and reply is not None and reply.is_open_recall()", "return recall_asked and reply is not None"),
    ("M28", "the model is never shown the lender's record (prompt takes question and reply only)",
     "samajh/extract/_prompt.py", '        f"Assistant\'s question: <<<{question}>>>\\n"', '        f"Assistant\'s question: <<<{question}>>> (premium on record 52000)\\n"'),
]


def main() -> int:
    scratch = Path(sys.argv[1]).resolve()
    if ROOT in scratch.parents or scratch == ROOT:
        raise SystemExit("the scratch directory must be outside the repo")
    work = scratch / "mutants"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    for name in ("samajh", "tests", "eval", "data"):
        shutil.copytree(ROOT / name, work / name, ignore=shutil.ignore_patterns("__pycache__", "*.wav"))
    shutil.copy(ROOT / "pyproject.toml", work / "pyproject.toml")
    for name in ("DESIGN.md", "README.md", "CLAUDE.md", "ORCHESTRATION.md"):
        shutil.copy(ROOT / name, work / name)
    (work / "references" / "pilots").mkdir(parents=True)
    shutil.copy(ROOT / "references/pilots/results.json", work / "references/pilots/results.json")
    python = ROOT / ".venv" / "bin" / "python"
    env = {**os.environ, "PYTHONPATH": str(work), "PYTHONDONTWRITEBYTECODE": "1"}

    def run() -> tuple[int, int, str]:
        out = subprocess.run(
            [str(python), "-m", "pytest", *TESTS, "-q", "-p", "no:cacheprovider"],
            cwd=work, env=env, capture_output=True, text=True,
        ).stdout
        tail = out.strip().splitlines()[-1] if out.strip() else "(no output)"
        failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", tail)) else 0
        errors = int(m.group(1)) if (m := re.search(r"(\d+) error", tail)) else 0
        files = sorted({line.split("::")[0].removeprefix("FAILED ").removeprefix("ERROR ")
                        for line in out.splitlines() if line.startswith(("FAILED", "ERROR"))})
        return failed, errors, tail + " | " + ", ".join(files)

    where = subprocess.run([str(python), "-c", "import samajh; print(samajh.__file__)"],
                           cwd=work, env=env, capture_output=True, text=True).stdout.strip()
    print("mutants import samajh from:", where)
    failed, errors, tail = run()
    print("baseline:", tail)
    if failed or errors or "passed" not in tail:
        raise SystemExit("the unmutated copy does not pass: results would mean nothing")
    for name, behaviour, file, old, new in MUTATIONS:
        path = work / file
        original = path.read_text()
        if original.count(old) != 1:
            print(f"{name} NOT APPLIED ({original.count(old)} matches): {behaviour}")
            continue
        path.write_text(original.replace(old, new))
        failed, errors, tail = run()
        path.write_text(original)
        verdict = "killed" if failed or errors else "SURVIVED"
        print(f"{name} {verdict}: {behaviour} -> {tail}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
