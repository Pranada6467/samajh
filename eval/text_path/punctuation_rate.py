"""How often does the text the extractor reads lack a clause break? Read-only, offline, no network.

    uv run python eval/text_path/punctuation_rate.py

"Clause break" is counted the way the extractor counts it: `Reply(text).clauses()` in
`samajh/extract/_ground.py` (two or more clauses that hold a word). The change check used to run
only on such replies; since P3a round 4 it also runs on a one-clause reply that holds a marker word
(`Reply.has_change_marker`), so the last column is the one-clause replies that now get a check.

Two sources, Hindi and Hinglish only:
1. Stored Prisma responses of the evaluations (`.samajh/cache/gnani/`, matched to model, format and
   language through each evaluation's `run/stt.jsonl`; a response is counted once per cache key).
   Amounts sets v1 and v2 are Timbre TTS; `.samajh-realvoice/` is public real-voice clips
   (IndicVoices, Kathbath), present only on the machine that holds them. No transcript text is printed.
2. The customer turns of Samajh-dialogue sessions (`.samajh/sessions/*/session.json`, plus any
   `references/pilots/p1-artifacts/*/case.json` whose session is not there). The stored turn text is
   what the dialogue acted on and what the case file's extraction reads; `acted_on` names the reading
   that supplied it. Every customer turn so far is Timbre audio (played from a file or through a
   headless browser as the microphone); no person has used the phone.
"""

import json
from collections import defaultdict
from pathlib import Path

from samajh.extract._ground import Reply

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".samajh" / "cache" / "gnani"
RUNS = {
    "Timbre TTS (amounts v1)": ROOT / "eval" / "amounts" / "run" / "stt.jsonl",
    "Timbre TTS (amounts v2)": ROOT / "eval" / "amounts_v2" / "run" / "stt.jsonl",
    "public real voice": ROOT / ".samajh-realvoice" / "run" / "stt.jsonl",
}
SESSIONS = ROOT / ".samajh" / "sessions"
P1 = ROOT / "references" / "pilots" / "p1-artifacts"
LANGUAGES = {"hi", "hi-en", "hi-IN"}
SHORT = 6  # words, as the extractor counts them


class Row:
    def __init__(self) -> None:
        self.n = self.many = self.marked_one = self.bare = self.blank = 0

    def add(self, text: str) -> None:
        reply = Reply(text)
        if reply.blank:
            self.blank += 1
            return
        self.n += 1
        if len(reply.clauses()) >= 2:
            self.many += 1
        else:
            self.marked_one += reply.has_change_marker()
            # One clause and no clause-end mark anywhere, not even a final "।" or ".".
            self.bare += not any(ch in text for ch in "।॥;!?…,.\n")


def _cached_text(key: str) -> str | None:
    body = CACHE / key[:2] / f"{key}.bin"
    if not body.exists():
        return None
    return json.loads(body.read_bytes()).get("transcript")


def evaluation_rows() -> tuple[dict[tuple, Row], int]:
    rows: dict[tuple, Row] = defaultdict(Row)
    missing = 0
    for audio, path in RUNS.items():
        if not path.exists():
            continue
        seen: set[str] = set()
        for line in path.read_text().splitlines():
            run = json.loads(line)
            key = run.get("cache_key")
            if run["language"] not in LANGUAGES or not key or key in seen:
                continue
            seen.add(key)
            text = _cached_text(key)
            if text is None:
                missing += 1
                continue
            words = Reply(text).word_count
            stt = run["stt"]
            group = (
                audio.split(" (")[0],
                f"{stt['model']} {stt['format']}",
                "≤6" if words <= SHORT else ">6",
            )
            rows[group].add(text)
    return rows, missing


def _session_turns() -> list[tuple[str, dict, list[dict]]]:
    """(session id, the turn's record, its readings) for every customer turn that was read."""
    found: list[tuple[str, dict, list[dict]]] = []
    seen: set[str] = set()
    for path in sorted(SESSIONS.glob("*/session.json")):
        log = json.loads(path.read_text())
        if log.get("dialogue") != "samajh" or log.get("params", {}).get("language", "hi") not in LANGUAGES:
            continue
        seen.add(log["session_id"])
        for event in log["events"]:
            if event["type"] != "customer" or event.get("superseded") or not event.get("readings"):
                continue
            readings = event["readings"]
            # Logs written before `acted_on` existed read each turn once.
            acted = event.get("acted_on") or (readings[0]["role"] if len(readings) == 1 else None)
            if acted:
                found.append((log["session_id"], event | {"acted_on": acted}, readings))
    for path in sorted(P1.glob("*/case.json")):
        case = json.loads(path.read_text())
        if case.get("session_id") in seen or case.get("language", "hi") not in LANGUAGES:
            continue
        for turn in case.get("turns", []):
            readings = turn.get("readings", [])
            acted = next((r["role"] for r in readings if r.get("ok") and r.get("text") == turn["text"]), None)
            if acted:
                found.append((case["session_id"], {"transcript": turn["text"], "acted_on": acted}, readings))
    return found


def session_rows() -> tuple[dict[tuple, Row], int, int]:
    """Counted once per distinct (stored text, reading): replays of one persona repeat its audio."""
    rows: dict[tuple, Row] = defaultdict(Row)
    sessions = set()
    seen: set[tuple[str, str]] = set()
    turns = _session_turns()
    for session, event, readings in turns:
        sessions.add(session)
        by_role = {r["role"]: r for r in readings}
        model = by_role[event["acted_on"]]["model"]
        read_twice = "second" in by_role
        turn = "figure turn" if read_twice else "other turn"
        source = f"{model} {by_role[event['acted_on']]['params'].get('format', '?')} ({turn})"
        if (event["transcript"], source) in seen:
            continue
        seen.add((event["transcript"], source))
        words = Reply(event["transcript"]).word_count
        rows[("Timbre TTS (session)", source, "≤6" if words <= SHORT else ">6")].add(event["transcript"])
    return rows, len(sessions), len(turns)


def gold_clause_rows() -> list[str]:
    """TTS only: of the sentences whose written text has two or more clauses, how many transcripts kept them."""
    gold: dict[str, str] = {}
    for path in (
        ROOT / "data" / "amounts" / "amounts-v1.jsonl",
        ROOT / "data" / "amounts_v2" / "amounts-v2.jsonl",
    ):
        for line in path.read_text().splitlines():
            item = json.loads(line)
            gold[item["id"]] = item["text"]
    kept: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for audio, path in RUNS.items():
        if not audio.startswith("Timbre") or not path.exists():
            continue
        seen: set[str] = set()
        for line in path.read_text().splitlines():
            run = json.loads(line)
            key, item = run.get("cache_key"), run["item_id"]
            if run["language"] not in LANGUAGES or not key or key in seen or item not in gold:
                continue
            seen.add(key)
            if len(Reply(gold[item]).clauses()) < 2:
                continue
            text = _cached_text(key)
            if text is None:
                continue
            row = kept[f"{run['stt']['model']} {run['stt']['format']}"]
            row[0] += 1
            row[1] += len(Reply(text).clauses()) >= 2
    out = ["| reading | n (written text has ≥2 clauses) | transcript has ≥2 clauses |", "|---|---|---|"]
    out += [f"| {name} | {n} | {k} |" for name, (n, k) in sorted(kept.items())]
    return out


def table(rows: dict[tuple, Row]) -> list[str]:
    out = [
        "| audio | reading | words | n | ≥2 clauses | 1 clause | 1 clause, no mark at all | 1 clause with a marker word |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for (audio, reading, words), r in sorted(rows.items()):
        one = r.n - r.many
        out.append(
            f"| {audio} | {reading} | {words} | {r.n} | {r.many} | {one} | {r.bare} | {r.marked_one} |"
        )
    return out


def main() -> None:
    evaluation, missing = evaluation_rows()
    sessions, n_sessions, n_turns = session_rows()
    print("## Evaluation responses (Hindi and Hinglish; one per cache key)\n")
    print("\n".join(table(evaluation)))
    print(f"\nRun rows whose response is not in the cache: {missing}.")
    print("\n## Timbre TTS: does the transcript keep a clause break the written sentence has?\n")
    print("\n".join(gold_clause_rows()))
    print(
        f"\n## Customer turns of Samajh-dialogue sessions ({n_sessions} sessions, {n_turns} turns read; "
        "each distinct text counted once)\n"
    )
    print("\n".join(table(sessions)))
    print(
        "\n'figure turn': read twice (premium or cover question, read-back, restate); the stored text is "
        "v2.5 when it has text, unless only v3.0 held a figure or a stop signal."
    )


if __name__ == "__main__":
    main()
