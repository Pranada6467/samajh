"""`uv run python -m samajh.server [--host 127.0.0.1] [--port 8085] [--state DIR] [--clips DIR] [--allow-host NAME]`"""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from samajh.server.app import LOCAL_HOSTS, create_app


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m samajh.server", description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8085)
    parser.add_argument(
        "--state",
        type=Path,
        default=None,
        help=(
            "where sessions and the review batch (<state>/ops, from `python -m samajh.ops`) live; "
            "default .samajh. The Gnani lock, cache and ledger stay in .samajh either way"
        ),
    )
    parser.add_argument("--clips", type=Path, default=None, help="directory of prepared turn audio")
    parser.add_argument(
        "--allow-host",
        action="append",
        default=[],
        metavar="NAME",
        help="another host name or address browsers may use for this server (for a phone on the LAN)",
    )
    args = parser.parse_args()
    app = create_app(state=args.state, clips_dir=args.clips, allowed_hosts=(*LOCAL_HOSTS, *args.allow_host))
    # Each open request may hold a 6 MiB upload; past this many, uvicorn answers 503 at once.
    uvicorn.run(app, host=args.host, port=args.port, limit_concurrency=32)


if __name__ == "__main__":
    main()
