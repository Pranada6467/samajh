import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for _p in (_ROOT / "eval" / "acq", _ROOT / "eval" / "p5"):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))
