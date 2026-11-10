"""Verifier probe for P6: recompute the amounts_v2 numbers from cached transcripts, offline.

Independent of eval/amounts_v2/analyze.py and samajh/evalkit: exports samajh/amounts AND
samajh/types.py at commit 59c12d9 into a scratch directory under fresh names, reads the stored
STT rows directly, and computes outcomes, Wilson intervals and exact McNemar tests itself.

  uv run python references/reviews/iter2/probes/p6_recompute.py tts
  uv run python references/reviews/iter2/probes/p6_recompute.py realvoice

Never prints real-voice transcript text: only ids, amounts and counts.
"""

from __future__ import annotations

import hashlib
import importlib
import io
import json
import math
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
COMMIT = "59c12d9"
PKG = "vp6_amounts"
TYPES = "vp6_types"


def load_parser():
    scratch = Path(tempfile.mkdtemp(prefix="vp6-"))
    tar_bytes = subprocess.run(
        ["git", "-C", str(REPO), "archive", "--format=tar", COMMIT, "samajh/amounts", "samajh/types.py"],
        check=True, capture_output=True,
    ).stdout
    (scratch / PKG).mkdir()
    digest = hashlib.sha256()
    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar:
        members = sorted((m for m in tar.getmembers() if m.isfile() and m.name.endswith(".py")), key=lambda m: m.name)
        for m in members:
            src = tar.extractfile(m).read().decode()
            if m.name.startswith("samajh/amounts/"):
                digest.update(Path(m.name).name.encode() + b"\0" + src.encode())  # same fingerprint rule as builder, pre-rewrite
            src = src.replace("samajh.amounts", PKG).replace("samajh.types", TYPES)
            if m.name == "samajh/types.py":
                (scratch / f"{TYPES}.py").write_text(src)
            else:
                (scratch / PKG / Path(m.name).name).write_text(src)
    sys.path.insert(0, str(scratch))
    return importlib.import_module(PKG), digest.hexdigest()


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def fmt(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({100 * k / n if n else 0:.0f}%, {100 * lo:.0f}-{100 * hi:.0f})"


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


R = ("T3", "V3", "T25", "L25")
SRC = {("prisma-v3.0", "transcribe"): "T3", ("prisma-v3.0", "verbatim"): "V3", ("prisma-v2.5", "transcribe"): "T25"}


def main(which: str) -> None:
    amounts, fp = load_parser()
    print(f"parser {COMMIT} fingerprint {fp[:16]} (builder reports ea36a203a54a85af)")
    if which == "tts":
        manifest = REPO / "data/amounts_v2/amounts-v2.jsonl"
        stt = REPO / "eval/amounts_v2/run/stt.jsonl"
        conditions = ("clean16k", "phone")
    else:
        manifest = REPO / "data/amounts_v2/realvoice-v1.jsonl"
        stt = REPO / ".samajh-realvoice/run/stt.jsonl"
        conditions = ("native16k", "phone")
    print("manifest sha256", hashlib.sha256(manifest.read_bytes()).hexdigest()[:16])
    items = {r["id"]: r for r in map(json.loads, manifest.read_text().splitlines())}

    texts: dict[tuple[str, str], dict[str, str | None]] = defaultdict(dict)
    seen = Counter()
    for row in map(json.loads, stt.read_text().splitlines()):
        key = SRC[(row["stt"]["model"], row["stt"]["format"])]
        seen[(row["item_id"], row["condition"], key)] += 1
        texts[(row["item_id"], row["condition"])][key] = row["text"]
        if key == "T25":
            texts[(row["item_id"], row["condition"])]["L25"] = row["literal"]
    print("duplicate stt rows:", sum(v > 1 for v in seen.values()))

    def read(text):
        if text is None:
            return "missing"
        res = amounts.parse_amount(text)
        return res.rupees if isinstance(res, amounts.Parsed) else None

    for cond in conditions:
        clips = []
        for (iid, c), t in texts.items():
            if c != cond or set(t) != set(R):
                continue
            gold = items[iid]["gold"]["amount_inr"]
            vals = {r: read(t[r]) for r in R}
            clips.append((iid, items[iid]["tags"], gold, vals, t))
        n = len(clips)
        print(f"\n===== {which} / {cond}: clips {n} (manifest {len(items)}; missing {sorted(set(items) - {c[0] for c in clips})})")

        def out(cl, r):
            ok = sum(v[r] == g for _, _, g, v, _ in cl)
            ref = sum(v[r] is None for _, _, g, v, _ in cl)
            wr = sum(v[r] is not None and v[r] != g for _, _, g, v, _ in cl)
            return ok, ref, wr

        groups = [("all", clips), ("retail", [c for c in clips if c[1].get("band") == "retail"])]
        if which == "tts":
            for s in ("skipped", "control", "general", "fraction", "large"):
                groups.append((s, [c for c in clips if c[1].get("stratum") == s]))
        else:
            for s in ("skipped", "multi", "single"):
                groups.append((s, [c for c in clips if c[1].get("shape") == s]))
            groups.append((">=1000", [c for c in clips if c[2] >= 1000]))
            groups.append(("<1000", [c for c in clips if c[2] < 1000]))
        for name, cl in groups:
            for r in R:
                ok, ref, wr = out(cl, r)
                print(f"  {name:8s} {r:4s} n={len(cl):3d} correct {fmt(ok, len(cl))}  refused {ref}  wrong {fmt(wr, len(cl))}")

        # McNemar between models
        def only(a, b):
            return sum(v[a] is not None and v[a] != g and not (v[b] is not None and v[b] != g) for _, _, g, v, _ in clips)
        a, b = only("T3", "T25"), only("T25", "T3")
        print(f"  McNemar wrong T3-only {a} vs T25-only {b}: p={mcnemar_exact(a, b):.3g}")

        if which == "tts":
            pairs = defaultdict(dict)
            for cl in clips:
                if "pair" in cl[1]:
                    pairs[cl[1]["pair"]][cl[1]["stratum"]] = cl
            so = co = both = 0
            same_voice = same_carrier = 0
            for p in pairs.values():
                s, c = p["skipped"], p["control"]
                sw = s[3]["T3"] is not None and s[3]["T3"] != s[2]
                cw = c[3]["T3"] is not None and c[3]["T3"] != c[2]
                so += sw and not cw
                co += cw and not sw
                both += sw and cw
                same_carrier += s[1]["carrier"] == c[1]["carrier"]
            print(f"  pairs {len(pairs)}; T3 wrong skipped-only {so} control-only {co} both {both}; McNemar p={mcnemar_exact(so, co):.3g}; same carrier {same_carrier}")
            # unpaired comparison for context (Fisher exact, two-sided, via hypergeometric)
            k1, n1, k2, n2 = so + both, len(pairs), co + both, len(pairs)
            print(f"  (unpaired) skipped wrong {k1}/{n1}, control wrong {k2}/{n2}; Fisher p={fisher(k1, n1, k2, n2):.3g}")
            all_wrong_t3 = [c for c in clips if c[3]["T3"] is not None and c[3]["T3"] != c[2]]
            print("  T3 wrong strata:", Counter(c[1]["stratum"] for c in all_wrong_t3))

        # mechanism
        dw = [c for c in clips if c[3]["T3"] is not None and c[3]["T3"] != c[2]]
        vr = sum(c[3]["V3"] == c[2] for c in dw)
        print(f"  mechanism: T3 wrong {len(dw)}, V3 right on {fmt(vr, len(dw)) if dw else '0'}")

        # agreement schemes
        def scheme(rs):
            acc = [c for c in clips if c[3][rs[0]] is not None and all(c[3][r] == c[3][rs[0]] for r in rs)]
            wr = sum(c[3][rs[0]] != c[2] for c in acc)
            return acc, wr
        for rs in (("T3",), ("T25",), ("T25", "L25"), ("T3", "T25"), ("T3", "L25"), ("T3", "V3"), ("V3", "L25")):
            acc, wr = scheme(rs)
            right = len(acc) - wr
            print(f"  accept {'='.join(rs):10s} coverage {fmt(len(acc), n)}  wrong accepted {wr}  P(correct|acc) {fmt(right, len(acc)) if acc else '-'}")
            if rs == ("T3", "T25") and which == "realvoice":
                big = [c for c in acc if c[2] >= 1000]
                print(f"    of accepted, gold>=1000: {fmt(sum(c[3]['T3'] == c[2] for c in big), len(big))}; all-clips gold>=1000 {sum(c[2] >= 1000 for c in clips)}")
        # disagreement T3 vs T25
        acc, _ = scheme(("T3", "T25"))
        accid = {c[0] for c in acc}
        dis = [c for c in clips if c[0] not in accid]
        two = sum(c[3]["T3"] is not None and c[3]["T25"] is not None for c in dis)
        one = sum((c[3]["T3"] is None) != (c[3]["T25"] is None) for c in dis)
        t3r = sum(c[3]["T3"] == c[2] for c in dis)
        t25r = sum(c[3]["T25"] == c[2] for c in dis)
        neither = sum(c[3]["T3"] != c[2] and c[3]["T25"] != c[2] for c in dis)
        print(f"  disagreement {len(dis)}: two amounts {two}, one refused {one}, T3 right {t3r}, T25 right {t25r}, neither {neither}")

        if which == "realvoice":
            golds = sorted(c[2] for c in clips)
            print("  gold distribution:", Counter(_bucket(g) for g in golds))
            print("  round (multiple of 100):", sum(g % 100 == 0 for g in golds), "of", len(golds))
            print("  T3 wrong:", [(c[0], c[2], c[3]["T3"], c[3]["V3"]) for c in dw])
            print("  T25 wrong:", [(c[0], c[2], c[3]["T25"]) for c in clips if c[3]["T25"] is not None and c[3]["T25"] != c[2]])
        else:
            print("  T3 wrong list (id, gold, T3, V3):")
            for c in sorted(dw):
                print("   ", c[0], c[2], c[3]["T3"], c[3]["V3"], c[1]["shape"])


def _bucket(g: int) -> str:
    for lim, name in ((100, "<100"), (1000, "100-999"), (10000, "1k-9.9k"), (100000, "10k-99.9k"), (10**7, "1L-99L")):
        if g < lim:
            return name
    return ">=1Cr"


def fisher(k1, n1, k2, n2):
    K, N = k1 + k2, n1 + n2

    def pmf(x):
        return math.comb(n1, x) * math.comb(n2, K - x) / math.comb(N, K)
    p0 = pmf(k1)
    return min(1.0, sum(pmf(x) for x in range(max(0, K - n2), min(K, n1) + 1) if pmf(x) <= p0 * (1 + 1e-9)))


if __name__ == "__main__":
    main(sys.argv[1])
