import sys
from pathlib import Path

# Appended, not prepended: tests/extract puts eval/text_path first, and its `run.py` must keep the name
# `run`. The P5 modules have names nothing else uses; eval/p5/run.py is loaded by path where a test needs it.
P5_CODE = Path(__file__).resolve().parents[2] / "eval" / "p5"
if str(P5_CODE) not in sys.path:
    sys.path.append(str(P5_CODE))
