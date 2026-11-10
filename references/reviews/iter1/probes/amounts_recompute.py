"""Independent recomputation of eval/amounts/REPORT.md headline cells. Offline: reads JSONL only.

BEFORE = the saved per-item scores in eval/amounts/run/scores.jsonl (parser as of the evaluation).
AFTER  = the saved transcripts in eval/amounts/run/stt.jsonl rescored with today's samajh.amounts.

Uses no samajh.evalkit code for counting or statistics (own Wilson, own McNemar). It imports
samajh.amounts.parse_amount and samajh.evalkit.scorers.naive_digits only for the AFTER rescoring
and for checking that the saved naive scores are regenerable.

  uv run python references/reviews/iter1/probes/amounts_recompute.py
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "eval" / "amounts" / "run"


def jl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def w(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({100 * k / n:.0f}%, {100 * lo:.0f}-{100 * hi:.0f})"


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2**n)


def mcnemar_midp(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, mcnemar_exact(b, c) - math.comb(n, min(b, c)) / 2**n)


def mcnemar_chi2_cc(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    stat = (abs(b - c) - 1) ** 2 / n
    return math.erfc(math.sqrt(stat / 2))  # chi-square, 1 df, upper tail


def label(stt: dict) -> str:
    return f"{stt['model'].removeprefix('prisma-')} {stt['format']} {stt['language']}"


V25, V30 = "v2.5 transcribe item", "v3.0 transcribe item"


def main() -> None:
    manifest = jl(ROOT / "data" / "amounts" / "amounts-v1.jsonl")
    items = {row["id"]: row for row in manifest}
    stt = jl(RUN / "stt.jsonl")
    scores = jl(RUN / "scores.jsonl")
    print(f"manifest {len(manifest)}, stt rows {len(stt)}, score rows {len(scores)}")

    # --- integrity of the saved scores against the saved transcripts -------------------------
    stt_by = {(r["item_id"], r["condition"], label(r["stt"])): r for r in stt}
    assert len(stt_by) == len(stt), "duplicate (item, condition, stt) cells in stt.jsonl"
    seen = Counter()
    bad_transcript = bad_gold = bad_correct = 0
    for s in scores:
        key = (s["item_id"], s["condition"], label(s["stt"]))
        seen[key + (s["output"], s["method"])] += 1
        src = stt_by[key]
        want = src["text"] if s["output"] == "text" else src["literal"]
        bad_transcript += s["transcript"] != want
        gold = items[s["item_id"]]["gold"]["amount_inr"]
        bad_gold += s["gold"] != gold
        truth = isinstance(s["predicted"], int) and not isinstance(s["predicted"], bool) and s["predicted"] == gold
        bad_correct += s["correct"] != truth
    print(
        f"scores.jsonl: duplicates {sum(v > 1 for v in seen.values())}, transcript != stt.jsonl {bad_transcript}, "
        f"gold != manifest {bad_gold}, correct flag != (predicted == gold) {bad_correct}"
    )
    expect = sum(2 * (2 if r["literal"] is not None else 1) for r in stt)
    print(f"score rows expected from stt.jsonl (2 methods x text[+literal]) {expect}, found {len(scores)}")

    # --- BEFORE: index of the saved scores ---------------------------------------------------
    def index(rows: list[dict]) -> dict:
        return {
            (r["item_id"], r["condition"], label(r["stt"]), r["output"], r["method"]): r for r in rows
        }

    before = index(scores)

    # --- AFTER: rescore with today's parser ---------------------------------------------------
    from samajh.amounts import Ambiguous, Parsed, parse_amount  # noqa: PLC0415
    from samajh.evalkit.score import Hypothesis  # noqa: PLC0415
    from samajh.evalkit.scorers import naive_digits  # noqa: PLC0415

    after_rows = []
    naive_moved = parser_moved = 0
    for s in scores:
        r = dict(s)
        if s["method"] == "parser":
            res = parse_amount(s["transcript"])
            pred = res.rupees if isinstance(res, Parsed) else None
            note = "" if isinstance(res, Parsed) else ("ambiguous" if isinstance(res, Ambiguous) else "no_amount")
            parser_moved += pred != s["predicted"]
            r["predicted"], r["note"] = pred, note
        else:
            pred = naive_digits(Hypothesis(text=s["transcript"], language=s["language"])).value
            naive_moved += pred != s["predicted"]
            r["predicted"] = pred
        r["correct"] = r["predicted"] is not None and r["predicted"] == s["gold"]
        after_rows.append(r)
    after = index(after_rows)
    print(f"rescoring today: naive predictions that differ from saved {naive_moved}; parser predictions that differ {parser_moved}")
    files = sorted((ROOT / "samajh" / "amounts").glob("*.py"))
    print("parser hash today:", hashlib.sha256(b"".join(p.read_bytes() for p in files)).hexdigest()[:16], "(report: efbd312d3bc7c33e)")

    def cell(ix, cond, stt_label, output="text", method="parser", ids=None):
        return {
            k[0]: r
            for k, r in ix.items()
            if k[1] == cond and k[2] == stt_label and k[3] == output and k[4] == method and (ids is None or k[0] in ids)
        }

    def ok(c):
        return sum(r["correct"] for r in c.values())

    def paired(a, b):
        keys = a.keys() & b.keys()
        only_a = sum(a[k]["correct"] and not b[k]["correct"] for k in keys)
        only_b = sum(b[k]["correct"] and not a[k]["correct"] for k in keys)
        return len(keys), only_a, only_b

    def skips(rupees: int) -> bool:
        crore, rest = divmod(rupees, 10_000_000)
        lakh, rest = divmod(rest, 100_000)
        thousand, rest = divmod(rest, 1_000)
        hundred, below = divmod(rest, 100)
        used = [bool(x) for x in (crore, lakh, thousand, hundred, below)]
        first = used.index(True)
        last = len(used) - 1 - used[::-1].index(True)
        return not all(used[first : last + 1])

    for name, ix in (("BEFORE (saved scores.jsonl)", before), ("AFTER (today's parser on saved transcripts)", after)):
        print(f"\n================ {name} ================")
        for stt_label in (V25, V30):
            for cond in ("clean16k", "phone"):
                p, n = cell(ix, cond, stt_label), cell(ix, cond, stt_label, method="naive")
                _, only_p, only_n = paired(p, n)
                wrong = sum(1 for r in p.values() if not r["correct"] and r["predicted"] is not None)
                none = sum(1 for r in p.values() if r["predicted"] is None)
                print(
                    f"{stt_label:22s} {cond:9s} parser {w(ok(p), len(p))}  naive {w(ok(n), len(n))}  "
                    f"parser-only {only_p} naive-only {only_n} p={mcnemar_exact(only_p, only_n):.2g}  "
                    f"failures {len(p) - ok(p)} = wrong {wrong} + no-answer {none}"
                )
        lit = cell(ix, "phone", V25, "literal")
        print(f"v2.5 literal phone parser {w(ok(lit), len(lit))}")

        # fraction recoveries
        p, n = cell(ix, "phone", V25), cell(ix, "phone", V25, method="naive")
        rec = [k for k in p if p[k]["correct"] and not n[k]["correct"]]
        print(f"v2.5 phone: parser recovers {len(rec)}, of them fraction stratum {sum(items[k]['tags']['stratum'] == 'fraction' for k in rec)}")
        for stt_label in (V25, V30):
            frac = {k for k, v in items.items() if v["tags"]["stratum"] == "fraction"}
            nf, pf = cell(ix, "phone", stt_label, method="naive", ids=frac), cell(ix, "phone", stt_label, ids=frac)
            print(f"  fraction sentences, phone, {stt_label}: naive {w(ok(nf), len(nf))}, parser {w(ok(pf), len(pf))}")

        # model gap and phone vs clean
        a, b = cell(ix, "phone", V30), cell(ix, "phone", V25)
        n_, oa, ob = paired(a, b)
        print(
            f"v3.0 vs v2.5 phone: n={n_} v3-only {oa} v2.5-only {ob}  exact p={mcnemar_exact(oa, ob):.3f} "
            f"mid-p={mcnemar_midp(oa, ob):.3f} chi2-cc p={mcnemar_chi2_cc(oa, ob):.3f}"
        )
        a, b = cell(ix, "clean16k", V30), cell(ix, "clean16k", V25)
        n_, oa, ob = paired(a, b)
        print(f"v3.0 vs v2.5 clean: v3-only {oa} v2.5-only {ob} exact p={mcnemar_exact(oa, ob):.3f}")
        for stt_label in (V25, V30):
            a, b = cell(ix, "phone", stt_label), cell(ix, "clean16k", stt_label)
            n_, oa, ob = paired(a, b)
            print(f"phone vs clean {stt_label}: {ok(a)} vs {ok(b)}; phone-only {oa} clean-only {ob} p={mcnemar_exact(oa, ob):.2g}")

        # skipped groups
        for stt_label in (V25, V30):
            p = cell(ix, "phone", stt_label)
            tally = defaultdict(lambda: [0, 0])
            for k, r in p.items():
                if items[k]["tags"]["stratum"] == "fraction":
                    continue
                t = tally[skips(items[k]["gold"]["amount_inr"])]
                t[0] += 1
                t[1] += r["correct"]
            print(f"skipped group {stt_label}: yes {w(tally[True][1], tally[True][0])}; no {w(tally[False][1], tally[False][0])}")

        # agreement
        a, b = cell(ix, "phone", V25), cell(ix, "phone", V30)
        agree = [k for k in a if a[k]["predicted"] is not None and a[k]["predicted"] == b[k]["predicted"]]
        differ = [k for k in a if k not in agree]
        right = sum(a[k]["correct"] for k in agree)
        one = sum(a[k]["correct"] or b[k]["correct"] for k in differ)
        neither_none = sum(a[k]["predicted"] is None and b[k]["predicted"] is None for k in differ)
        print(
            f"agreement v2.5/v3.0 phone: same amount {len(agree)}, right {w(right, len(agree))}; other {len(differ)}, "
            f"at least one right {one}; both no-answer {neither_none}; agree-wrong items "
            f"{[k for k in agree if not a[k]['correct']]}"
        )
        a, b = cell(ix, "phone", V25), cell(ix, "phone", V25, "literal")
        agree = [k for k in a if a[k]["predicted"] is not None and a[k]["predicted"] == b[k]["predicted"]]
        print(f"agreement v2.5 text/literal phone: same {len(agree)}, right {sum(a[k]['correct'] for k in agree)}; other {len(a) - len(agree)}, "
              f"one right {sum(a[k]['correct'] or b[k]['correct'] for k in a if k not in agree)}")

        # noise table
        print("noise table (parser): condition | this cond | phone same sentences | phone-only | cond-only | exact p | mid-p | chi2cc p")
        ps = []
        for stt_label in (V25, V30):
            ph = cell(ix, "phone", stt_label)
            for cond in ("narrowband", "street10", "street5", "babble10", "babble5"):
                c = cell(ix, cond, stt_label)
                n_, only_ph, only_c = paired(ph, c)
                phs = sum(ph[k]["correct"] for k in c)
                p_ = mcnemar_exact(only_ph, only_c)
                ps.append((p_, stt_label, cond))
                print(
                    f"  {stt_label} {cond:10s} {w(ok(c), len(c))} | {w(phs, n_)} | {only_ph} | {only_c} | "
                    f"{p_:.3f} | {mcnemar_midp(only_ph, only_c):.3f} | {mcnemar_chi2_cc(only_ph, only_c):.3f}"
                )
        m = len(ps)
        ps.sort()
        print(f"  comparisons in the table: {m}; smallest p {ps[0][0]:.4f} ({ps[0][1]} {ps[0][2]}); "
              f"Bonferroni {min(1, ps[0][0] * m):.3f}; Holm threshold for it {0.05 / m:.4f}")

        # formats on fold 0
        f0 = {k for k, v in items.items() if v["tags"]["fold"] == "0"}
        for lab in ("v3.0 codemix item", "v3.0 verbatim item", "v3.0 transcribe indic-auto"):
            a, b = cell(ix, "phone", lab), cell(ix, "phone", V30, ids=f0)
            n_, oa, ob = paired(a, b)
            print(f"{lab}: {w(ok(a), len(a))} vs v3.0 transcribe {w(ok(b), len(b))}; only {oa}/{ob} p={mcnemar_exact(oa, ob):.2g}")

    # --- things that do not depend on the parser ------------------------------------------------
    print("\n================ parser-independent ================")
    cells = Counter((r["condition"], label(r["stt"])) for r in stt)
    for k, v in sorted(cells.items()):
        print(f"  cells {k[0]:10s} {k[1]:28s} {v}")
    print("per model calls:", Counter(r["stt"]["model"] for r in stt))
    print("distinct fingerprints", len({r["fingerprint"] for r in stt}), "cache keys", len({r["cache_key"] for r in stt}),
          "(audio, request) pairs", len({(r["audio_sha256"], json.dumps(r["request"], sort_keys=True)) for r in stt}))
    mismatch = [
        r["item_id"] for r in stt
        if r["request"]["model"] != r["stt"]["model"] or r["request"]["format"] != r["stt"]["format"]
    ]
    print("rows whose request model/format differs from the label:", len(mismatch))
    print("request language by (item language, stt.language):", dict(Counter(
        (r["language"], r["stt"]["language"], str(r["request"]["language"])) for r in stt)))
    print("cache_hit rows:", sum(r["cache_hit"] for r in stt), "truncated:", sum(r["truncated"] for r in stt),
          "empty text:", sum(not r["text"].strip() for r in stt))

    def sq(t: str) -> str:
        return "".join(ch for ch in t if unicodedata.category(ch)[0] in "LMN")

    verb = {r["item_id"]: r["text"] for r in stt if label(r["stt"]) == "v2.5 verbatim item"}
    same = diff = exact = 0
    for r in stt:
        if label(r["stt"]) == V25 and r["condition"] == "phone" and r["item_id"] in verb:
            same += sq(r["literal"] or "") == sq(verb[r["item_id"]])
            diff += sq(r["literal"] or "") != sq(verb[r["item_id"]])
            exact += (r["literal"] or "") == verb[r["item_id"]]
    print(f"literal == verbatim ignoring punctuation/space: {same} of {same + diff}; byte-identical {exact}")

    for model in ("prisma-v2.5", "prisma-v3.0"):
        rows = [r for r in stt if r["stt"]["model"] == model]
        vals = sorted(r["seconds"] for r in rows if not r["cache_hit"])
        retried = [r for r in rows if r["attempts"] > 1]
        print(
            f"{model}: calls {len(rows)}, median {statistics.median(vals):.3f}s, p95(index) {vals[int(0.95 * (len(vals) - 1))]:.3f}s, "
            f"max {vals[-1]:.1f}s, attempts>1 {len(retried)}, by language {dict(Counter(r['language'] for r in retried))}, "
            f"attempt counts {dict(Counter(r['attempts'] for r in retried))}"
        )
        lat = sorted(r["seconds"] for r in retried)
        if lat:
            print(f"   retried-call wall seconds: min {lat[0]:.1f} median {statistics.median(lat):.1f} max {lat[-1]:.1f}")

    voice = jl(RUN / "voice.jsonl")
    print(f"voice rows {len(voice)}; chars {sum(v['chars'] for v in voice)}; audio s {sum(v['audio_seconds'] for v in voice):.1f}; "
          f"tts est {sum(v['est_credits'] for v in voice):.2f}; stt audio s {sum(r['audio_seconds'] for r in stt):.1f}; "
          f"stt est {sum(r['est_credits'] for r in stt):.2f}; total {sum(v['est_credits'] for v in voice) + sum(r['est_credits'] for r in stt):.2f}")
    print("voices:", len({(v['voice']['model'], v['voice']['voice']) for v in voice}),
          dict(Counter(v['voice']['model'] for v in voice)))
    print("wilson spot checks:", w(221, 240), w(214, 240), w(156, 240), w(220, 240), w(6, 16), w(161, 164), w(199, 200), w(15, 16))


if __name__ == "__main__":
    main()
