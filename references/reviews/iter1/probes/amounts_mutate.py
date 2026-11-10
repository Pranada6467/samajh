"""Mutation testing of samajh/audio and samajh/evalkit in a SCRATCH COPY of the repo, never the repo.

  python references/reviews/iter1/probes/amounts_mutate.py /path/to/scratch/repo [name ...]

The copy is made beforehand (rsync without .git, .samajh, .venv, .env). Each mutation is one exact
string replacement that must match once; the suite `pytest tests/audio tests/evalkit -q -x` runs with
the copy as the working directory, so the copy is what is imported (checked before every run); the
file is restored afterwards. No network: the suite is the offline one (`-m 'not live'` by default).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PYTHON = REPO / ".venv" / "bin" / "python"

# name, file, old, new
MUTATIONS: list[tuple[str, str, str, str]] = [
    (
        "snr-amplitude-as-power",
        "samajh/audio/steps.py",
        "gain = speech_rms / (noise_rms * 10 ** (snr_db / 20))",
        "gain = speech_rms / (noise_rms * 10 ** (snr_db / 10))",
    ),
    (
        "snr-one-db-off",
        "samajh/audio/steps.py",
        "gain = speech_rms / (noise_rms * 10 ** (snr_db / 20))",
        "gain = speech_rms / (noise_rms * 10 ** ((snr_db + 1) / 20))",
    ),
    (
        "snr-quarter-db-off",
        "samajh/audio/steps.py",
        "gain = speech_rms / (noise_rms * 10 ** (snr_db / 20))",
        "gain = speech_rms / (noise_rms * 10 ** ((snr_db + 0.25) / 20))",
    ),
    (
        "noise-same-for-every-clip",
        "samajh/audio/steps.py",
        "seed = _derive_seed(step.seed, hashlib.sha256(wav).hexdigest())",
        "seed = _derive_seed(step.seed)",
    ),
    (
        "mulaw-is-only-a-resample",
        "samajh/audio/steps.py",
        "            out = _mulaw(pcm)",
        "            out = _resample(pcm, 8000)",
    ),
    (
        "bandlimit-no-highpass",
        "samajh/audio/steps.py",
        'graph = f"highpass=f={low_hz},highpass=f={low_hz},lowpass=f={high_hz},lowpass=f={high_hz}"',
        'graph = f"lowpass=f={high_hz},lowpass=f={high_hz}"',
    ),
    (
        "bandlimit-edge-at-200-hz",
        "samajh/audio/steps.py",
        'graph = f"highpass=f={low_hz},highpass=f={low_hz},lowpass=f={high_hz},lowpass=f={high_hz}"',
        'graph = f"highpass=f={low_hz - 100},highpass=f={low_hz - 100},lowpass=f={high_hz},lowpass=f={high_hz}"',
    ),
    (
        "store-key-without-transform-version",
        "samajh/audio/steps.py",
        "payload = [TRANSFORM_VERSION, step.model_dump(mode=\"json\"), input_sha256]",
        "payload = [step.model_dump(mode=\"json\"), input_sha256]",
    ),
    (
        "store-key-without-input-hash",
        "samajh/audio/steps.py",
        "payload = [TRANSFORM_VERSION, step.model_dump(mode=\"json\"), input_sha256]",
        "payload = [TRANSFORM_VERSION, step.model_dump(mode=\"json\")]",
    ),
    (
        "wilson-wrong-variance-term",
        "samajh/evalkit/score.py",
        "half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator",
        "half = z * math.sqrt(p * (1 - p) / n + z * z / (2 * n * n)) / denominator",
    ),
    (
        "wilson-90-percent",
        "samajh/evalkit/score.py",
        "def wilson(correct: int, n: int, z: float = 1.959964)",
        "def wilson(correct: int, n: int, z: float = 1.644854)",
    ),
    (
        "mcnemar-one-sided",
        "samajh/evalkit/score.py",
        "return min(1.0, 2 * tail)",
        "return min(1.0, tail)",
    ),
    (
        "paired-swaps-nothing-but-drops-both-wrong",
        "samajh/evalkit/score.py",
        "{(True, True): 0, (True, False): 1, (False, True): 2, (False, False): 3}[left[key], right[key]]",
        "{(True, True): 0, (True, False): 2, (False, True): 1, (False, False): 3}[left[key], right[key]]",
    ),
    (
        "no-answer-counts-as-correct-when-gold-none",
        "samajh/evalkit/score.py",
        "correct=prediction.value is not None\n                        and type(prediction.value) is type(gold)",
        "correct=type(prediction.value) is type(gold)",
    ),
    (
        "bool-matches-int",
        "samajh/evalkit/score.py",
        "                        and type(prediction.value) is type(gold)\n",
        "",
    ),
    (
        "budget-guard-ignores-the-next-call",
        "samajh/evalkit/runner.py",
        "if summary.spent_credits + estimate > budget:",
        "if summary.spent_credits > budget:",
    ),
    (
        "no-budget-guard-on-stt",
        "samajh/evalkit/runner.py",
        "        guard(seconds * rates.stt_credits_per_second)\n",
        "",
    ),
    (
        "no-budget-guard-on-tts",
        "samajh/evalkit/runner.py",
        "        guard(len(job.item.text) * rates.tts_credits_per_char)\n",
        "",
    ),
    (
        "resume-does-not-skip-done",
        "samajh/evalkit/runner.py",
        "            if job.fingerprint in done:\n                summary.already_done += 1\n                continue\n",
        "",
    ),
    (
        "manifest-hash-not-checked",
        "samajh/evalkit/manifest.py",
        "    if actual != expect_sha256:",
        "    if False:",
    ),
    (
        "fingerprint-without-transform-version",
        "samajh/evalkit/runner.py",
        "        if steps and audio_steps.TRANSFORM_VERSION != 1\n",
        "        if False\n",
    ),
    (
        "torn-line-not-repaired",
        "samajh/evalkit/runner.py",
        'os.write(fd, b"\\n" + line if torn else line)',
        "os.write(fd, line)",
    ),
    (
        "no-store-lock",
        "samajh/evalkit/runner.py",
        "        lock.acquire()\n",
        "        pass\n",
    ),
    (
        "cache-hit-spend-not-recounted",
        "samajh/evalkit/runner.py",
        "            summary.spent_credits = run_spend(store, ledger)\n        else:",
        "            pass\n        else:",
    ),
    (
        "fingerprint-without-stt-format",
        "samajh/evalkit/runner.py",
        '                    stt=options.model_dump(mode="json"),',
        '                    stt={"model": options.model, "language": str(options.language)},',
    ),
    (
        "fingerprint-without-steps",
        "samajh/evalkit/runner.py",
        '                    steps=[step.model_dump(mode="json") for step in steps],',
        "                    steps=job_condition_name(cell),",
    ),
    (
        "stale-rows-are-scored",
        "samajh/evalkit/runner.py",
        "        job.cell.key: by_fingerprint[job.fingerprint] for job in planned if job.fingerprint in by_fingerprint\n    }",
        "        job.cell.key: by_fingerprint[job.fingerprint] for job in planned if job.fingerprint in by_fingerprint\n"
        "    } | {row.fingerprint: row for row in store.stt_rows()}",
    ),
    (
        "error-cells-not-retried",
        "samajh/evalkit/runner.py",
        "                summary.errors += 1\n                consecutive += 1\n",
        "                summary.errors += 1\n                consecutive += 1\n                done.add(job.fingerprint)\n",
    ),
    (
        "naive-ignores-the-unit-word",
        "samajh/evalkit/scorers.py",
        "            value *= size\n",
        "            pass\n",
    ),
    (
        "voice-seed-ignored",
        "samajh/evalkit/plan.py",
        'random.Random(f"{experiment.voice_seed}:{language}:{tag}").shuffle(members)',
        'random.Random(f"{language}:{tag}").shuffle(members)',
    ),
    (
        "run-spend-counts-every-gnani-row",
        "samajh/evalkit/runner.py",
        'if e.provider == "gnani" and e.cache_key in keys)',
        'if e.provider == "gnani")',
    ),
]


def main() -> int:
    copy = Path(sys.argv[1]).resolve()
    if copy == REPO or REPO in copy.parents or not (copy / "samajh").is_dir():
        print("refusing: the target must be a scratch copy outside the repository")
        return 2
    wanted = set(sys.argv[2:])
    where = subprocess.run(
        [str(PYTHON), "-c", "import samajh.evalkit.runner as r, samajh.audio.steps as s; print(r.__file__); print(s.__file__)"],
        cwd=copy, capture_output=True, text=True, check=True,
    ).stdout.split()
    assert all(Path(p).resolve().is_relative_to(copy) for p in where), where
    print("imported from:", where[0])
    for name, rel, old, new in MUTATIONS:
        if wanted and name not in wanted:
            continue
        path = copy / rel
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            print(f"{name}: SKIPPED, pattern found {original.count(old)} times in {rel}")
            continue
        if name == "fingerprint-without-steps":
            new = '                    steps=cell.condition,'
        path.write_text(original.replace(old, new), encoding="utf-8")
        try:
            done = subprocess.run(
                [str(PYTHON), "-m", "pytest", "tests/audio", "tests/evalkit", "-q", "-x", "-p", "no:cacheprovider"],
                cwd=copy, capture_output=True, text=True, check=False,
            )
        finally:
            path.write_text(original, encoding="utf-8")
        lines = [line for line in done.stdout.splitlines() if line.strip()]
        first_fail = next((line for line in lines if line.startswith("FAILED") or line.startswith("ERROR")), "")
        verdict = "KILLED" if done.returncode != 0 else "SURVIVED"
        print(f"{name}: {verdict} | {lines[-1] if lines else done.stderr[-200:]} | {first_fail[:160]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
