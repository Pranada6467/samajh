"""The P5 customer voice rule (eval/p5/RUNNER-PLAN.md Part 1, "Voices"). Pure; no network.

Shivani is the bot. For each gender, sort the customer ids, shuffle them with
`random.Random("samajh-p5-2026-11-10:voice:" + gender)` and give `pool[rank % 6]`. The gender is
`speaker.gender` in `customers.jsonl` (for a third party, the person who answers). The rule runs over
all 60 customers whatever subset a run voices, so a customer has the same voice in every run.
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from typing import Any

SEED = "samajh-p5-2026-11-10:voice:"
POOLS: dict[str, tuple[str, ...]] = {
    "f": ("Lakshmi", "Kalpana", "Chetana", "Vasudha", "Riyaa", "Tarika"),
    "m": ("Avinash", "Shubham", "Prakash", "Devansh", "Yashraj", "Harshad"),
}
# The Timbre language a customer reply is voiced in: the code the server uses for the call language
# (samajh.server.samajh_dialogue.TTS_LANGUAGE; a test pins that the two agree).
TTS_LANGUAGE: dict[str, str] = {"hi": "hi-IN", "hi-en": "hi-en"}


def assign_voices(customers: Mapping[str, Any]) -> dict[str, str]:
    """customer id -> Timbre v3.0 voice, for every customer in `customers` (id -> bank.Customer)."""
    out: dict[str, str] = {}
    for gender, pool in POOLS.items():
        ids = sorted(cid for cid, c in customers.items() if c.speaker["gender"] == gender)
        random.Random(SEED + gender).shuffle(ids)
        for rank, cid in enumerate(ids):
            out[cid] = pool[rank % len(pool)]
    missing = sorted(set(customers) - set(out))
    if missing:
        raise ValueError(f"no voice for {missing}: speaker.gender is not 'f' or 'm'")
    return out
