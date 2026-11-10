"""Write a frozen amounts manifest.

python -m samajh.evalkit.amounts --out data/amounts                 # amounts-v1, the development set
python -m samajh.evalkit.amounts --set v2 --out data/amounts_v2     # amounts-v2, the held-out set
"""

import argparse
import hashlib
import sys
from pathlib import Path

from samajh.evalkit.amounts import heldout
from samajh.evalkit.amounts.grammar import generate, jsonl_bytes

SETS = {"v1": ("amounts-v1", generate), "v2": ("amounts-v2", heldout.generate)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--set", choices=sorted(SETS), default="v1", dest="which")
    parser.add_argument("--force", action="store_true", help="overwrite a manifest whose bytes differ")
    args = parser.parse_args(argv)
    name, make = SETS[args.which]
    data = jsonl_bytes(make())
    manifest = args.out / f"{name}.jsonl"
    if manifest.exists() and manifest.read_bytes() != data and not args.force:
        print(
            f"{manifest} exists and differs: the set is frozen. Pass --force to overwrite.", file=sys.stderr
        )
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    manifest.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    (args.out / f"{name}.sha256").write_text(f"{digest}  {manifest.name}\n", encoding="utf-8")
    print(f"{manifest}: {len(data.splitlines())} rows, sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
