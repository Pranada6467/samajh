"""W7 Part A: the amount finding against open models and a closed reference, offline.

    uv run python eval/openbench/part_a.py

Reads the stored Prisma rows exactly as P6 scored them (`eval/amounts_v2/analyze.py`: same experiments,
same `current_rows`, the frozen parser at 59c12d9) and the W7 transcript rows of each other system, and
writes `eval/openbench/tables-amounts.md` and `eval/openbench/results-a.json`. Makes no API call.
Real-voice output holds ids and amounts only, never words. "gemini-3-flash" is a closed reference, not an open
baseline.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "eval" / "amounts_v2"))

import store  # noqa: E402
from frozen_parser import COMMIT, load  # noqa: E402

from samajh.evalkit.manifest import load_manifest  # noqa: E402
from samajh.evalkit.plan import load_experiment  # noqa: E402
from samajh.evalkit.runner import RunStore, current_rows, jobs  # noqa: E402
from samajh.evalkit.score import mcnemar_exact, wilson  # noqa: E402

T3, V3, T25, L25 = "v3.0 transcribe", "v3.0 verbatim", "v2.5 transcribe", "v2.5 literal"
PRISMA = (T3, V3, T25, L25)
LABELS = {"v3.0 transcribe item": T3, "v3.0 verbatim item": V3, "v2.5 transcribe item": T25}
OPEN = ("whisper-large-v3", "indicwhisper-hi")
PRIMARY = "indicwhisper-hi"  # the primary third reading for the product question
CLOSED = ("gemini-3-flash",)
PARTIAL = "gemini-3.1-pro-partial"  # stopped run: outcome table only, never in tests or schemes
OTHERS = OPEN + CLOSED
OUTCOMES = ("right", "wrong", "no amount", "ambiguous", "missing")

SETS = {
    "amounts-v2": (HERE.parent / "amounts_v2" / "experiment.toml", HERE.parent / "amounts_v2" / "run", ("phone", "clean16k")),
    "realvoice": (HERE.parent / "amounts_v2" / "realvoice.toml", REPO / ".samajh-realvoice" / "run", ("phone", "native16k")),
}
WORDS_ALLOWED = {"amounts-v2"}  # synthetic TTS text is ours; dataset words never leave the machine


def label(system: str, n: int | None = None) -> str:
    if system == PARTIAL:
        return f"{system} (closed reference, partial: {n} clips, not used in schemes)"
    return f"{system} (closed reference)" if system in CLOSED else system


# ---------------------------------------------------------------- reading and outcome


@dataclass(frozen=True)
class Reading:
    outcome: str  # one of OUTCOMES
    amount: int | None  # parsed rupees when the parser gave an amount
    text: str | None = None


def classify(parsed: object, gold: int, amounts) -> tuple[str, int | None]:
    if isinstance(parsed, amounts.Parsed):
        value = parsed.rupees
        return ("right" if type(value) is type(gold) and value == gold else "wrong"), value
    if isinstance(parsed, amounts.Ambiguous):
        return "ambiguous", None
    return "no amount", None


def read(text: str | None, gold: int, amounts) -> Reading:
    """`text` None means no row or an error row."""
    if text is None:
        return Reading("missing", None)
    outcome, value = classify(amounts.parse_amount(text), gold, amounts)
    return Reading(outcome, value, text)


@dataclass(frozen=True)
class Clip:
    item_id: str
    condition: str
    gold: int
    tags: Mapping[str, str]
    audio_sha256: str
    readings: dict[str, Reading]
    gold_text: str = ""


# ---------------------------------------------------------------- schemes (PLAN.md Part A)


def amount(clip: Clip, system: str) -> int | None:
    r = clip.readings.get(system)
    return r.amount if r is not None and r.outcome in ("right", "wrong") else None


def _all_equal(values: Sequence[int | None]) -> int | None:
    if values[0] is None or any(v != values[0] for v in values[1:]):
        return None
    return values[0]


def _majority(values: Sequence[int | None]) -> int | None:
    for v in values:
        if v is not None and sum(w == v for w in values) >= 2:
            return v
    return None


def schemes(other: str, shown: str | None = None) -> dict[str, Callable[[Clip], int | None]]:
    """The four schemes with `other` as the third reading; `shown` names it in the scheme names."""
    o = shown or other
    return {
        "1 reference: v3.0 T = v2.5 T": lambda c: _all_equal([amount(c, T3), amount(c, T25)]),
        f"2 unanimous: v3.0 T = v2.5 T = {o}": lambda c: _all_equal([amount(c, T3), amount(c, T25), amount(c, other)]),
        f"3 majority of v3.0 T, v2.5 T, {o}": lambda c: _majority([amount(c, T3), amount(c, T25), amount(c, other)]),
        f"4 swap: {o} = v2.5 T": lambda c: _all_equal([amount(c, other), amount(c, T25)]),
    }


@dataclass(frozen=True)
class Acceptance:
    n: int
    accepted: int
    wrong: int

    @property
    def reasks(self) -> int:
        return self.n - self.accepted


def accept(clips: Sequence[Clip], rule: Callable[[Clip], int | None]) -> Acceptance:
    got = [(rule(c), c.gold) for c in clips]
    acc = [(v, g) for v, g in got if v is not None]
    return Acceptance(n=len(clips), accepted=len(acc), wrong=sum(v != g for v, g in acc))


# ---------------------------------------------------------------- loading


def prisma_clips(set_name: str, amounts) -> list[Clip]:
    experiment_path, store_path, _ = SETS[set_name]
    experiment = load_experiment(experiment_path)
    items = load_manifest(experiment.manifest, expect_sha256=experiment.manifest_sha256)
    by_id = {item.id: item for item in items}
    rows = list(current_rows(RunStore(store_path), jobs(items, experiment)).values())
    grouped: dict[tuple[str, str], dict[str, Reading]] = {}
    sha: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        name = LABELS.get(row.stt.label)
        if name is None:
            continue
        key = (row.item_id, row.condition)
        gold = by_id[row.item_id].gold["amount_inr"]
        grouped.setdefault(key, {})[name] = read(row.text, gold, amounts)
        if name == T25 and row.literal is not None:
            grouped[key][L25] = read(row.literal, gold, amounts)
        sha.setdefault(key, set()).add(row.audio_sha256)
    out = []
    for (item_id, condition), readings in grouped.items():
        if set(readings) != set(PRISMA):
            continue
        assert len(sha[(item_id, condition)]) == 1, f"Prisma readings of {item_id}/{condition} differ in audio"
        item = by_id[item_id]
        out.append(Clip(item_id, condition, item.gold["amount_inr"], item.tags, sha[(item_id, condition)].pop(), readings,
                        item.text))
    return sorted(out, key=lambda c: (c.condition, c.item_id))


def attach(set_name: str, clips: Sequence[Clip], amounts) -> dict[str, int]:
    """Add each other system's reading to every clip; return rows found per system."""
    found = {}
    for system in OTHERS + (PARTIAL,):
        # The LAST row per (item_id, condition) wins (store.latest): a restart may append duplicates.
        rows = store.latest(store.read_jsonl(store.transcripts_path(set_name, system)))
        found[system] = len(rows)
        for clip in clips:
            row = rows.get((clip.item_id, clip.condition))
            if row is not None:
                assert row["audio_sha256"] == clip.audio_sha256, (
                    f"{system} {clip.item_id}/{clip.condition}: audio differs from what Prisma read"
                )
            text = None if row is None or row.get("error") is not None else row["text"]
            clip.readings[system] = read(text, clip.gold, amounts)
    return found


# ---------------------------------------------------------------- tables


def pct(k: int, n: int) -> str:
    if n == 0:
        return "0/0"
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({100 * k / n:.0f}%, {100 * lo:.0f}-{100 * hi:.0f})"


def tally(clips: Sequence[Clip], system: str) -> dict[str, int]:
    out = dict.fromkeys(OUTCOMES, 0)
    for c in clips:
        out[c.readings[system].outcome] += 1
    return out


def md_table(head: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def subsets(set_name: str, clips: Sequence[Clip]) -> list[tuple[str, list[Clip]]]:
    if set_name == "amounts-v2":
        return [
            ("skipped", [c for c in clips if c.tags.get("stratum") == "skipped"]),
            ("control", [c for c in clips if c.tags.get("stratum") == "control"]),
            ("all", list(clips)),
        ]
    return [("all", list(clips)), ("skipped", [c for c in clips if c.tags.get("shape") == "skipped"])]


def pairs(clips: Sequence[Clip]) -> list[tuple[Clip, Clip]]:
    by_pair: dict[str, dict[str, Clip]] = {}
    for c in clips:
        if c.tags.get("stratum") in ("skipped", "control"):
            by_pair.setdefault(c.tags["pair"], {})[c.tags["stratum"]] = c
    return [(p["skipped"], p["control"]) for p in by_pair.values() if len(p) == 2]


def discordant(clips: Sequence[Clip], a: str, b: str, outcome: str) -> tuple[int, int]:
    only_a = sum(c.readings[a].outcome == outcome and c.readings[b].outcome != outcome for c in clips)
    only_b = sum(c.readings[b].outcome == outcome and c.readings[a].outcome != outcome for c in clips)
    return only_a, only_b


def present(clips: Sequence[Clip], system: str) -> bool:
    return any(c.readings[system].outcome != "missing" for c in clips)


def analyse(set_name: str, clips: Sequence[Clip], condition: str, amounts=None) -> tuple[str, dict]:
    cc = [c for c in clips if c.condition == condition]
    systems = list(PRISMA) + [s for s in OTHERS if present(cc, s)]
    others = [s for s in OTHERS if present(cc, s)]
    shown = systems + ([PARTIAL] if present(cc, PARTIAL) else [])
    res: dict = {"n": len(cc), "outcomes": {}, "pair_test": {}, "vs_prisma": {}, "schemes": {}, "wrong": []}
    md = [f"\n## {set_name}, condition `{condition}` (n = {len(cc)} clips)\n"]

    md.append("\n### (a) Outcomes per system\n")
    rows = []
    for sub, part in subsets(set_name, cc):
        for s in shown:
            t = tally(part, s)
            res["outcomes"].setdefault(sub, {})[s] = {**t, "n": len(part)}
            n_s = sum(c.readings[s].outcome != "missing" for c in cc)
            rows.append([sub, label(s, n_s), pct(t["right"], len(part)), pct(t["wrong"], len(part)),
                         t["no amount"], t["ambiguous"], t["missing"]])
    md.append(md_table(["subset", "system", "right", "wrong", "no amount", "ambiguous", "missing"], rows))

    if set_name == "amounts-v2":
        md.append("\n### (b) Skipped vs matched control, exact McNemar on `wrong` over the pairs\n")
        ps = pairs(cc)
        rows = []
        for s in systems:
            only_s = sum(a.readings[s].outcome == "wrong" and b.readings[s].outcome != "wrong" for a, b in ps)
            only_c = sum(b.readings[s].outcome == "wrong" and a.readings[s].outcome != "wrong" for a, b in ps)
            p = mcnemar_exact(only_s, only_c)
            res["pair_test"][s] = {"pairs": len(ps), "skipped_only_wrong": only_s, "control_only_wrong": only_c, "p": p}
            rows.append([label(s), len(ps), only_s, only_c, f"{p:.2g}"])
        md.append(md_table(["system", "pairs", "wrong on skipped only", "wrong on control only", "exact p"], rows))

    md.append("\n### (c) Each other system vs Prisma `transcribe`, exact McNemar on `right`\n")
    rows = []
    for sub, part in subsets(set_name, cc):
        if set_name == "amounts-v2" and sub != "skipped":
            continue
        for s in others:
            for prisma in (T3, T25):
                a, b = discordant(part, s, prisma, "right")
                p = mcnemar_exact(a, b)
                res["vs_prisma"].setdefault(sub, {}).setdefault(s, {})[prisma] = {
                    "n": len(part), "system_only_right": a, "prisma_only_right": b, "p": p}
                rows.append([sub, label(s), prisma, len(part), a, b, f"{p:.2g}"])
    md.append(md_table(["subset", "system", "vs", "n", "system only right", "Prisma only right", "exact p"], rows)
              if rows else "No other system has rows here.\n")

    md.append("\n### (d) Acceptance schemes (a third reading)\n")
    rows = []
    for sub, part in subsets(set_name, cc):
        if sub == "control":
            continue
        if not others:
            a = accept(part, schemes("-")["1 reference: v3.0 T = v2.5 T"])
            res["schemes"].setdefault(sub, {})["reference"] = vars(a) | {"reasks": a.reasks}
            rows.append([sub, "1 reference: v3.0 T = v2.5 T", a.n, a.accepted, a.wrong, a.reasks])
        for s in others:
            for name, rule in schemes(s, label(s)).items():
                a = accept(part, rule)
                res["schemes"].setdefault(sub, {}).setdefault(s, {})[name] = {
                    "n": a.n, "accepted": a.accepted, "wrong_accepted": a.wrong, "reasks": a.reasks}
                rows.append([sub, name, a.n, a.accepted, a.wrong, a.reasks])
    md.append(md_table(["subset", "scheme", "n", "accepted", "wrong accepted", "re-asks"], rows))

    md.append("\n### (e) Every wrong amount from an open system or the closed reference\n")
    rows = []
    for s in others:
        for c in cc:
            r = c.readings[s]
            if r.outcome != "wrong":
                continue
            entry = {"system": s, "item_id": c.item_id, "gold": c.gold, "amount": r.amount}
            row = [label(s), c.item_id, c.gold, r.amount]
            if set_name in WORDS_ALLOWED:
                entry["text"] = r.text
                row.append(r.text)
            res["wrong"].append(entry)
            rows.append(row)
    head = ["system", "item", "gold", "amount given"] + (["text"] if set_name in WORDS_ALLOWED else [])
    md.append(md_table(head, rows) if rows else "None.\n")
    return "".join(md), res


# ---------------------------------------------------------------- self-check


def self_check(clips: dict[str, list[Clip]]) -> list[str]:
    """P6's published figures must reproduce, or nothing here is comparable."""
    phone = [c for c in clips["amounts-v2"] if c.condition == "phone"]
    skipped = [c for c in phone if c.tags.get("stratum") == "skipped"]
    control = [c for c in phone if c.tags.get("stratum") == "control"]
    ref = schemes("-")["1 reference: v3.0 T = v2.5 T"]
    rv = [c for c in clips["realvoice"] if c.condition == "phone"]
    a_tts, a_rv = accept(phone, ref), accept(rv, ref)
    got = {
        "amounts-v2 phone clips": (len(phone), 280),
        "v3.0 T wrong on skipped": (tally(skipped, T3)["wrong"], 40),
        "skipped n": (len(skipped), 68),
        "v3.0 T wrong on controls": (tally(control, T3)["wrong"], 0),
        "controls n": (len(control), 68),
        "reference accepted (amounts-v2)": (a_tts.accepted, 224),
        "reference wrong accepted (amounts-v2)": (a_tts.wrong, 0),
        "realvoice phone clips": (len(rv), 124),
        "reference accepted (realvoice)": (a_rv.accepted, 113),
        "reference wrong accepted (realvoice)": (a_rv.wrong, 0),
    }
    lines = [f"{k}: {v} (P6 {e}) {'ok' if v == e else 'MISMATCH'}" for k, (v, e) in got.items()]
    for line in lines:
        print(line)
    assert all(v == e for v, e in got.values()), "P6 figures do not reproduce"
    return lines


def main() -> int:
    amounts = load()
    clips = {name: prisma_clips(name, amounts) for name in SETS}
    check = self_check(clips)
    rows_found = {name: attach(name, clips[name], amounts) for name in SETS}
    items_rv = {c.item_id for c in clips["realvoice"]}
    md = [
        "# W7 Part A: the amount finding against open models and a closed reference\n\n",
        "Written by `uv run python eval/openbench/part_a.py` (offline). Prisma rows are P6's, read as "
        f"`eval/amounts_v2/analyze.py` reads them; every text is parsed by `samajh.amounts` at {COMMIT} "
        "(`eval/amounts_v2/frozen_parser.py`). Outcomes: right, wrong (an amount that is not gold), no amount, "
        "ambiguous, missing (no row or an error row). Rates: count/n (percent, Wilson 95%). `gemini-3-flash` is a "
        "closed reference, not an open baseline. All amounts-v2 audio is TTS; real-voice tables hold ids and "
        "amounts only. `indicwhisper-hi` (AI4Bharat IndicWhisper, Vistaar Hindi Whisper-medium) is trained on "
        "Vistaar data, which includes Kathbath, so its figures on the Kathbath train clips among the 124 public "
        "clips are probably in-sample for it. Primary third reading for the product question: `indicwhisper-hi`. "
        "IndicConformer was not run (gated model).\n\n"
        "Self-check against P6:\n\n" + "".join(f"- {line}\n" for line in check),
        "\nRows found per system: " + "; ".join(
            f"{s}: " + ", ".join(f"{k} {v}" for k, v in f.items()) for s, f in rows_found.items()) + "\n",
        f"\nReal-voice clips with all Prisma readings: {len(items_rv)} items.\n",
    ]
    results: dict = {"parser_commit": COMMIT, "self_check": check, "rows_found": rows_found, "sets": {}, "clips": {}}
    for name, (_, _, conditions) in SETS.items():
        for condition in conditions:
            text, res = analyse(name, clips[name], condition, amounts)
            md.append(text)
            results["sets"].setdefault(name, {})[condition] = res
        results["clips"][name] = {
            f"{c.condition}/{c.item_id}": {
                "gold": c.gold, "audio_sha256": c.audio_sha256, "tags": dict(c.tags),
                "readings": {s: {"outcome": r.outcome, "amount": r.amount}
                             | ({"text": r.text} if name in WORDS_ALLOWED and s not in PRISMA else {})
                             for s, r in c.readings.items() if s in PRISMA + OTHERS + (PARTIAL,)},
            }
            for c in clips[name]
        }
    (HERE / "tables-amounts.md").write_text("".join(md), encoding="utf-8")
    (HERE / "results-a.json").write_text(json.dumps(results, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                         encoding="utf-8")
    print("wrote eval/openbench/tables-amounts.md and eval/openbench/results-a.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
