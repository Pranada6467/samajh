"""P3b round 3: every string a reviewer or reader sees, for several states, through the project's
banned-word lint and a wider list (claim 12).

Usage: uv run python references/reviews/iter2/probes/p3b_r3_wording.py <state dir> [<state dir> ...]
Reads the states; runs the CLI (`ingest`, `verify`, `report`) only against a copy under
<first state dir>/../wording_cli. Prints hits.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from samajh.ops import views  # noqa: E402
from samajh.ops.batch import load_batch  # noqa: E402
from samajh.ops.report import build_report  # noqa: E402
from samajh.ops.store import OpsStore  # noqa: E402
from samajh.ops.wording import banned_in  # noqa: E402

EXTRA = {
    "finding": r"(?i)\bfinding",
    "mis-selling as a result": r"(?i)mis[\s-]?sel",
    "refund / money back promise": r"(?i)\brefund|will (?:get|receive) (?:the |your )?money back|money will be returned|entitled to",
    "conclusion about a sale": r"(?i)\b(?:established|confirmed (?:that )?the sale|the sale was (?:wrong|improper|unfair)|wrongly sold|liable|penalt)",
    "flag as a conclusion": r"(?i)flag(?:s|ged)? (?:shows?|proves?|means?) ",
}


def strings(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield f"{path}.{k}#key", k
            yield from strings(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from strings(v, f"{path}[{i}]")
    elif isinstance(o, str):
        yield path, o


def scan(label: str, items) -> dict[str, set[str]]:
    hits: dict[str, set[str]] = {}
    for path, s in items:
        for b in banned_in(s):
            hits.setdefault(f"BANNED {b}", set()).add(f"{label}{path}: {s[:110]}")
        for name, pat in EXTRA.items():
            if re.search(pat, s):
                hits.setdefault(name, set()).add(f"{label}{path}: {s[:110]}")
    return hits


total: dict[str, set[str]] = {}
n_views = 0
for arg in sys.argv[1:]:
    st = Path(arg)
    store = OpsStore(st / "ops")
    batch = load_batch(store)
    docs = {
        "batch": views.batch_view(batch),
        "queue": views.queue_view(batch),
        "attempts": views.attempt_log_view(batch),
        "report": build_report(store),
    }
    for item in docs["queue"].items:
        docs[f"case:{item.case_id}"] = views.case_view(batch, item.case_id, st / "sessions")
    for name, doc in docs.items():
        n_views += 1
        for k, v in scan(f"[{st.name}/{name}]", strings(json.loads(doc.model_dump_json()))).items():
            total.setdefault(k, set()).update(v)
print(f"views scanned: {n_views} over {len(sys.argv) - 1} state(s)")

for p in sorted((REPO / "web" / "review").glob("*")):
    if p.suffix in (".js", ".html", ".css"):
        text = p.read_text()
        lits = re.findall(r"`([^`]*)`|\"([^\"\n]*)\"|'([^'\n]*)'|>([^<>{}\n]+)<", text)
        flat = [(f"[{p.name}]", "".join(x)) for x in lits]
        for k, v in scan("", flat).items():
            total.setdefault(k, set()).update(v)
readme = REPO / "data" / "loanbook" / "README.md"
for k, v in scan("[loanbook README]", [(f":{i}", line) for i, line in enumerate(readme.read_text().splitlines(), 1)]).items():
    total.setdefault(k, set()).update(v)

# the CLI, on a copy of the first state
first = Path(sys.argv[1])
cli = first.parent / "wording_cli"
shutil.rmtree(cli, ignore_errors=True)
shutil.copytree(first, cli)
outs = []
for cmd in (["ingest"], ["verify"], ["report"], ["ingest", "--sessions", str(cli / "no-such-dir")]):
    r = subprocess.run([sys.executable, "-m", "samajh.ops", *cmd, "--state", str(cli)], cwd=REPO, capture_output=True, text=True, timeout=600)
    outs.append((f"[cli {' '.join(cmd[:1])}]", r.stdout + r.stderr))
    if r.returncode not in (0,):
        print(f"cli {cmd}: exit {r.returncode}: {(r.stderr.strip().splitlines() or [''])[-1][:160]}")
for k, v in scan("", [(lab, line) for lab, out in outs for line in out.splitlines()]).items():
    total.setdefault(k, set()).update(v)

for k, v in sorted(total.items()):
    print(f"{k}: {len(v)}")
    for s in sorted(v)[:8]:
        print("   ", s)
print("DONE")
