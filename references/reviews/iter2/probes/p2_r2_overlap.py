"""Exact-duplicate check of the p2_r2 inputs against every string in the builder's and the old verifier's sets.

Run: uv run python references/reviews/iter2/probes/p2_r2_overlap.py  -> prints and writes p2_r2_overlap.json
"""
import ast, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[4]
HERE = pathlib.Path(__file__).parent


def norm(s):
    return re.sub(r"[\s।.,?!]+", " ", s).strip().casefold()


def strings_from(path):
    out = set()
    if path.suffix == ".py":
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                out.add(node.value)
    else:
        text = path.read_text()
        for line in text.splitlines():
            try:
                obj = json.loads(line)
            except Exception:
                continue
            stack = [obj]
            while stack:
                o = stack.pop()
                if isinstance(o, str):
                    out.add(o)
                elif isinstance(o, dict):
                    stack.extend(o.values())
                elif isinstance(o, list):
                    stack.extend(o)
        if path.suffix == ".json":
            try:
                stack = [json.loads(text)]
                while stack:
                    o = stack.pop()
                    if isinstance(o, str):
                        out.add(o)
                    elif isinstance(o, dict):
                        stack.extend(o.values())
                    elif isinstance(o, list):
                        stack.extend(o)
            except Exception:
                pass
    return out


sources = {
    "builder": [p for p in (ROOT / "tests/dialogue").rglob("*") if p.suffix in (".py", ".jsonl", ".json")],
    "old_verifier": [p for p in (ROOT / "references/reviews/iter2/probes").glob("p2_*")
                     if not p.name.startswith("p2_r2_") and p.suffix in (".py", ".jsonl", ".json")],
}
mine = []
for c in json.loads((HERE / "p2_r2_inputs.json").read_text()):
    for i, t in enumerate(c["turns"]):
        mine.append((c["id"], i, t))
for p in json.loads((HERE / "p2_r2_personas.json").read_text()):
    for m in (p["replies"], p.get("then") or {}):
        for k, v in m.items():
            for t in (v if isinstance(v, list) else [v]):
                mine.append((p["id"], k, t))
report = {}
for name, files in sources.items():
    pool = {}
    for f in files:
        for s in strings_from(f):
            pool.setdefault(norm(s), str(f.relative_to(ROOT)))
    hits = [(cid, pos, t, pool[norm(t)]) for cid, pos, t in mine if norm(t) and norm(t) in pool]
    report[name] = {"files": len(files), "hits": hits}
    print(f"{name}: {len(files)} files; {len(hits)} of {len(mine)} input strings are exact duplicates")
    for h in hits:
        print("   ", h)
(HERE / "p2_r2_overlap.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
