"""One markdown report over a day of sessions: per-session rows against card gold, counts per 100
by kind of customer, void rate, latency, STT health, pauses, talk-over and the two readings."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from samajh.human.sessions import Session
from samajh.human.stats import NOT_LOGGED, per100, spread_cell
from samajh.types import RuleId

RULE_IDS = frozenset(r.value for r in RuleId)
BUCKETS = [(200, 400), (400, 600), (600, 800), (800, 1000), (1000, 1500), (1500, None)]
CLASSES = ["problem", "knowledge_gap_only", "no_problem", "procedural"]


def _g(d: Any, *path: str) -> Any:
    for p in path:
        if not isinstance(d, dict):
            return None
        d = d.get(p)
    return d


def flags_and_gaps(case: dict | None) -> tuple[list[dict], list[dict]]:
    result = (case or {}).get("result") or {}
    flags = list(result.get("case_flags") or [])
    gaps = list(result.get("case_gaps") or [])
    for p in result.get("products") or []:
        flags += p.get("flags") or []
        gaps += p.get("gaps") or []
    return flags, gaps


def _rules(gold: dict, key: str) -> list[str]:
    """The gold rules under `key`, each once, in order."""
    return list(dict.fromkeys(g.get("rule") if isinstance(g, dict) else g for g in gold.get(key) or []))


def grounds(s: Session) -> dict[str, Any]:
    """Gold grounds against the case's flag and gap rule ids (a rule listed twice counts once)."""
    flags, gaps = flags_and_gaps(s.case)
    flag_ids = {f.get("rule_id") for f in flags}
    any_ids = flag_ids | {g.get("rule_id") for g in gaps}
    gold = s.gold or {}
    matched, missing, unmappable = [], [], []
    for key, pool in (("refer_grounds_from_call", flag_ids), ("gap_grounds", any_ids)):
        for rule in _rules(gold, key):
            if rule not in RULE_IDS:
                unmappable.append(rule)
            else:
                (matched if rule in pool else missing).append(rule)
    record = [r for r in _rules(gold, "refer_grounds_from_record") if r in RULE_IDS]
    gold_rules = {
        r
        for k in ("refer_grounds_from_call", "refer_grounds_from_record", "gap_grounds")
        for r in _rules(gold, k)
    }
    return {
        "matched": matched,
        "n": len(matched) + len(missing),
        "missing": missing,
        "unmappable": list(dict.fromkeys(unmappable)),
        "extra": sorted(r for r in flag_ids - gold_rules if r),
        "record_matched": [r for r in record if r in flag_ids],
        "record_n": len(record),
    }


def match(s: Session) -> bool | None:
    if not s.gold:
        return None
    ok = s.outcome() == s.gold.get("expected_outcome")
    if s.gold.get("expected_tier") is not None:
        ok = ok and s.tier() == s.gold["expected_tier"]
    return ok


def _yn(v: bool | None) -> str:
    return "n/a" if v is None else ("yes" if v else "no")


def session_rows(sessions: list[Session]) -> list[str]:
    out = [
        (
            "| session | card | lang | audio | outcome | tier | expected outcome / tier | match | void "
            "| grounds (call, gap) | missing | unmappable | record grounds | extra flags | loan named |"
        ),
        "|" + "---|" * 15,
    ]
    for s in sessions:
        gold = s.gold or {}
        gr = grounds(s) if s.gold else None
        wrong = gold.get("expected_outcome") == "wrong_party"
        out.append(
            "| "
            + " | ".join(
                [
                    s.id,
                    (s.card or "") if s.gold else "no card",
                    str(_g(s.log, "params", "language") or ""),
                    s.source(),
                    str(s.outcome() or NOT_LOGGED),
                    s.tier(),
                    f"{gold.get('expected_outcome')} / {gold.get('expected_tier') or '-'}" if s.gold else "",
                    _yn(match(s)),
                    _yn(s.void()),
                    f"{len(gr['matched'])} of {gr['n']}" if gr else "",
                    ", ".join(gr["missing"]) if gr else "",
                    ", ".join(gr["unmappable"]) if gr else "",
                    f"{len(gr['record_matched'])} of {gr['record_n']}" if gr else "",
                    ", ".join(gr["extra"]) if gr else "",
                    _yn(s.loan_named()) if wrong else "",
                ]
            )
            + " |"
        )
    return out


MAIN_TIER = {"problem": "refer", "knowledge_gap_only": "understanding_gap", "no_problem": "clear"}


def ended_early(s: Session) -> bool:
    """Not a miss: the call did not end `completed`, or it has no case (as eval/p5/score.py `state`)."""
    return s.outcome() != "completed" or s.tier() == "no case"


def _class_metrics(cls: str, ss: list[Session]) -> list[tuple[str, int]]:
    """For the three tier classes the rows add up to n."""
    if cls == "procedural":
        reached = sum(s.outcome() == (s.gold or {}).get("expected_outcome") for s in ss)
        return [("expected outcome reached", reached), ("loan named", sum(s.loan_named() for s in ss))]
    done = [s.tier() for s in ss if not ended_early(s)]
    main, early = MAIN_TIER[cls], len(ss) - len(done)
    if cls == "problem":
        rows = [
            ("referred (completed)", done.count("refer")),
            ("missed (completed, tier not refer)", len(done) - done.count("refer")),
        ]
    else:
        rows = [
            (f"{main} (completed)", done.count(main)),
            ("referred (completed)", done.count("refer")),
            ("completed, other tier", len(done) - done.count(main) - done.count("refer")),
        ]
    return [*rows, ("ended early or no case", early)]


def class_tables(sessions: list[Session]) -> list[str]:
    counted = [s for s in sessions if s.gold and not s.void()]
    void = [s for s in sessions if s.gold and s.void()]
    out = [
        "## Counts per 100 by kind of customer",
        "",
        (
            f"Void sessions excluded ({len(void)} with a card, counted on their own below). "
            "No rate is pooled across classes."
        ),
        "",
        "| class | n | measure | per 100 (k/n; 95% Wilson) |",
        "|---|---|---|---|",
    ]
    by_class: dict[str, list[Session]] = defaultdict(list)
    for s in counted:
        by_class[s.gold.get("class")].append(s)
    for cls in CLASSES + sorted(c for c in by_class if c not in CLASSES):
        ss = by_class.get(cls, [])
        for name, k in _class_metrics(cls, ss) if cls in CLASSES else []:
            out.append(f"| {cls} | {len(ss)} | {name} | {per100(k, len(ss))} |")
    out += ["", "By gold kind:", "", "| kind | class | n | measure | per 100 |", "|---|---|---|---|---|"]
    by_kind: dict[tuple, list[Session]] = defaultdict(list)
    for s in counted:
        by_kind[(s.gold.get("kind"), s.gold.get("class"))].append(s)
    for (kind, cls), ss in sorted(by_kind.items(), key=lambda kv: (str(kv[0][1]), str(kv[0][0]))):
        for name, k in _class_metrics(cls, ss) if cls in CLASSES else []:
            out.append(f"| {kind} | {cls} | {len(ss)} | {name} | {per100(k, len(ss))} |")
    return out


SOURCES = ("mic", "file")


def _num(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _label(c: dict) -> str:
    label = _g(c, "classifier", "label")
    if label is None:
        return "(no label, degraded)" if _g(c, "classifier", "degraded") else "(no label)"
    return str(label)


WAIT = "classifier wait added to the turn (wait_ms)"
BEGIN = (
    "classifier begin to answer (latency_ms; upper bound on the LLM's own time, includes the "
    "second-reading wait when prefetched)"
)


def latency(sessions: list[Session]) -> list[str]:
    """Every row split by the audio source of the customer turn (a bot event: of the turn it answers)."""
    vals: dict[tuple[str, str], list[float]] = defaultdict(list)
    classifier_seen = False
    labels: Counter = Counter()
    labels_degraded = 0
    tts_count: Counter = Counter()

    def add(name: str, src: str, v: Any) -> None:
        if (x := _num(v)) is not None:
            vals[(name, src)].append(x)

    for s in sessions:
        for c in s.customers():
            src = c.get("source") or "none"
            eos = _g(c, "browser", "eos_wait_ms")
            add("bot_start_ms (browser)", src, _g(s.reply(c), "browser", "bot_start_ms"))
            add("eos_wait_ms", src, eos if eos is not None else _g(c, "latency", "eos_wait_ms"))
            add("STT primary (stt_ms)", src, _g(c, "latency", "stt_ms"))
            if len(c.get("readings") or []) >= 2:
                add("STT second (second_stt_ms)", src, _g(c, "latency", "second_stt_ms"))
            add("dialogue_ms", src, _g(c, "latency", "dialogue_ms"))
            add("server_ms", src, _g(c, "latency", "server_ms"))
            if _g(c, "classifier", "ran"):
                classifier_seen = True
                labels[_label(c)] += 1
                labels_degraded += bool(_g(c, "classifier", "degraded"))
                add(WAIT, src, _g(c, "classifier", "wait_ms"))
                add(BEGIN, src, _g(c, "classifier", "latency_ms"))
        for b in s.bots():
            prev = s.event((b.get("seq") or 0) - 1) or {}
            src = prev.get("source") if prev.get("type") == "customer" else None
            src = src or "none (opening)"
            add("bot event synth_ms", src, b.get("synth_ms"))
            for ln in b.get("lines") or []:
                tts = ln.get("tts") or {}
                if not tts:
                    continue
                which = "pre-made (cache hit)" if tts.get("cache_hit") else "synthesised during the call"
                tts_count[which] += 1
                add(f"TTS line synth_ms, {which}", src, tts.get("synth_ms"))
    names = [
        "bot_start_ms (browser)",
        "eos_wait_ms",
        "STT primary (stt_ms)",
        "STT second (second_stt_ms)",
        WAIT,
        BEGIN,
        "dialogue_ms",
        "server_ms",
        "TTS line synth_ms, pre-made (cache hit)",
        "TTS line synth_ms, synthesised during the call",
        "bot event synth_ms",
    ]
    srcs = [*SOURCES, *sorted({k[1] for k in vals} - set(SOURCES))]
    out = [
        "## Latency (ms; p90 nearest-rank; counted turns, void sessions included)",
        "",
        (
            "Split by audio source: mic turns are human, file turns are TTS audio. A bot row takes the source "
            "of the customer turn it answers."
        ),
        "",
        "| stage | source | median | p90 | max | n |",
        "|---|---|---|---|---|---|",
    ]
    for name in names:
        for src in srcs:
            if name in (WAIT, BEGIN) and not classifier_seen:
                if src == SOURCES[0]:
                    out.append(f"| {name} | all | {NOT_LOGGED}: see dialogue_ms | | | 0 |")
                continue
            if src not in SOURCES and not vals[(name, src)]:
                continue
            out.append(f"| {name} | {src} | {spread_cell(vals[(name, src)])} |")
    out += [
        "",
        (
            f"TTS lines: {tts_count['pre-made (cache hit)']} pre-made, "
            f"{tts_count['synthesised during the call']} synthesised during the call."
        ),
        "Classifier labels (turns where it ran): "
        + (", ".join(f"{k}: {v}" for k, v in sorted(labels.items())) or NOT_LOGGED)
        + f"; degraded: {labels_degraded}.",
    ]
    return out


def _ts(text: str | None) -> datetime | None:
    try:
        t = datetime.fromisoformat(str(text))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def read_ledger(path: Path | None) -> list[dict] | None:
    if path is None or not path.is_file():
        return None
    rows = []
    for line in path.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return [
        r
        for r in rows
        if r.get("provider") == "gnani" and r.get("kind") == "stt" and r.get("status") != "cache_hit"
    ]


def _status(r: dict) -> str:
    if "http_status" not in r:
        return "not logged"
    if r["http_status"] is not None:
        return str(r["http_status"])
    if r.get("ok") is False:
        return "failed, no status"
    return "cache hit" if r.get("cache_hit") else "no status"


def _window(s: Session) -> tuple[datetime, datetime] | None:
    start = _ts(s.log.get("created_at"))
    if start is None:
        return None
    last = max((e.get("at") or 0.0 for e in s.events), default=0.0)
    return start, start + timedelta(seconds=last + 120)


def _tally(c: Counter) -> str:
    return ", ".join(f"{k}: {v}" for k, v in sorted(c.items())) or "none"


def stt_health(sessions: list[Session], ledger: list[dict] | None) -> list[str]:
    readings = [r for s in sessions for c in s.customers(counted=False) for r in c.get("readings") or []]
    retried = sum((r.get("attempts") or 0) > 1 for r in readings)
    failed = Counter(r.get("error") or "unknown" for r in readings if r.get("ok") is False)
    status: dict[str, Counter] = defaultdict(Counter)
    for r in readings:
        status[r.get("model") or "?"][_status(r)] += 1
    out = [
        "## STT health (every take, superseded included)",
        "",
        f"Readings: {len(readings)}; with attempts > 1: {retried}; failed: {sum(failed.values())}"
        + (f" ({_tally(failed)})" if failed else ""),
        "",
    ]
    for model, cnt in sorted(status.items()):
        out.append(f"- {model} http_status: {_tally(cnt)}")
    if ledger is None:
        return [*out, "", f"Ledger: {NOT_LOGGED} (no ledger file)."]
    joined_tally, window_tally, keys_retried, joined = Counter(), Counter(), 0, 0
    for s in sessions:
        win = _window(s)
        if win is None:
            continue
        keys = {r.get("cache_key") for c in s.customers(counted=False) for r in c.get("readings") or []}
        keys.discard(None)
        per_key: Counter = Counter()
        for row in ledger:
            t = _ts(row.get("ts"))
            if t is None or not win[0] <= t <= win[1]:
                continue
            window_tally[str(row.get("status"))] += 1
            if row.get("cache_key") in keys:
                joined_tally[str(row.get("status"))] += 1
                per_key[row["cache_key"]] += 1
        joined += len(per_key)
        keys_retried += sum(v > 1 for v in per_key.values())
    out += [
        "",
        (
            f"Ledger join by cache_key: {joined} readings found, {keys_retried} with more than one "
            f"HTTP attempt; attempt statuses: {_tally(joined_tally)}"
        ),
        (
            f"All Gnani STT HTTP attempts inside the sessions' time windows (created_at to last event + 120 s), "
            f"by status: {_tally(window_tally)}. This includes failed readings (no cache_key) and any other "
            "process using the account in that window; overlapping windows count a row once per session."
        ),
    ]
    if not any(r.get("cache_key") for r in readings):
        out.append(f"(cache_key {NOT_LOGGED} in these sessions.)")
    return out


def failed_steps(sessions: list[Session]) -> list[str]:
    overall: Counter = Counter()
    out = ["## Failed steps (error events)", ""]
    per = []
    for s in sessions:
        errs = [e for e in s.events if e.get("type") == "error"]
        c = Counter(f"{e.get('stage')} / {e.get('code')} / {e.get('status')}" for e in errs)
        overall.update(c)
        if errs:
            per.append(f"- {s.id}: {len(errs)} ({_tally(c)})")
    out.append(
        f"Error events (stage / code / HTTP status to the phone): {sum(overall.values())}; {_tally(overall)}."
    )
    return out + per


def _bucket(ms: float) -> str | None:
    for lo, hi in BUCKETS:
        if ms >= lo and (hi is None or ms < hi):
            return f"{lo}-{hi}" if hi else f">={lo}"
    return None


def _split(s: Session, c: dict) -> bool:
    if (_g(c, "browser", "takes") or 1) > 1:
        return True
    return any(
        e.get("superseded") and e.get("reply_to") == c.get("reply_to") and e.get("seq") != c.get("seq")
        for e in s.customers(counted=False)
    )


def pauses(sessions: list[Session], cuts: dict[str, float]) -> list[str]:
    hist: dict[str, Counter] = defaultdict(Counter)
    per_kind: dict[str, Counter] = defaultdict(Counter)
    logged = 0
    for s in sessions:
        for c in s.customers():
            p = _g(c, "pauses", "pauses_ms")
            src = c.get("source")
            kind = (s.asked(c) or {}).get("listen") or "open"
            k = per_kind[kind]
            k["turns"] += 1
            k["observed splits"] += _split(s, c)
            k["grace_used"] += bool(_g(c, "browser", "grace_used"))
            if p is None:
                continue
            logged += 1
            for ms in p:
                b = _bucket(ms)
                if b:
                    hist[src][b] += 1
            if kind in cuts and any(ms >= cuts[kind] for ms in p):
                k["would have been split"] += 1
    labels = [f"{lo}-{hi}" if hi else f">={lo}" for lo, hi in BUCKETS]
    out = [
        "## Pauses inside customer turns (counted turns; file turns are TTS audio, mic turns human)",
        "",
        f"Turns with pause stats: {logged}. Pauses under 200 ms are not measured.",
        "",
        "| source | " + " | ".join(labels) + " |",
        "|---|" + "---|" * len(labels),
    ]
    for src in ("mic", "file"):
        out.append(f"| {src} | " + " | ".join(str(hist[src][b]) for b in labels) + " |")
    out += [
        "",
        (
            "| listen kind | cut_ms | turns | pause >= cut (would have been split) | observed splits "
            "| grace_used |"
        ),
        "|---|---|---|---|---|---|",
    ]
    for kind, k in sorted(per_kind.items()):
        out.append(
            f"| {kind} | {cuts.get(kind, 'n/a')} | {k['turns']} | {k['would have been split']} "
            f"| {k['observed splits']} | {k['grace_used']} |"
        )
    return out


def talk_over(sessions: list[Session]) -> list[str]:
    with_data = runs = prompts = 0
    total = 0.0
    for s in sessions:
        for b in s.bots():
            br = b.get("browser")
            if not br:
                continue
            with_data += 1
            to = br.get("talk_over") or []
            prompts += bool(to)
            runs += len(to)
            total += sum(t.get("ms") or 0 for t in to)
    return [
        "## Talk-over",
        "",
        (
            f"Bot prompts with browser data: {with_data}; with >= 1 talk-over run: {prompts}; runs: {runs}; "
            f"total {total:.0f} ms."
        ),
        (
            "Caveat: measured on the mic with echo cancellation on; residual bot echo can count, so this is "
            "speech heard during bot audio, not proof the customer spoke."
        ),
    ]


def two_readings(sessions: list[Session]) -> list[str]:
    """Four disjoint counts on turns with two readings."""
    counts, missing, n = Counter(), Counter(), 0
    for s in sessions:
        for c in s.customers():
            rs = c.get("readings") or []
            if len(rs) < 2:
                continue
            n += 1
            bad = [r for r in rs[1:] if r.get("ok") is False]
            if bad:
                counts["missing"] += 1
                missing.update(r.get("error") or "unknown" for r in bad)
            elif c.get("readings_agreed") is True:
                counts["agreed"] += 1
            elif c.get("readings_agreed") is False:
                counts["differed"] += 1
            else:
                counts["null"] += 1
    return [
        "## Two readings on figure turns",
        "",
        f"Turns with two readings: {n}; both read and agreed: {counts['agreed']}; both read and differed: "
        f"{counts['differed']}; second reading missing: {counts['missing']}"
        + (f" ({_tally(missing)})" if missing else "")
        + f"; null (no figure in either reading): {counts['null']}.",
    ]


def report(
    sessions: list[Session], inputs: list[str], cuts: dict[str, float], ledger: list[dict] | None
) -> str:
    void = [s for s in sessions if s.void()]
    turns = [c for s in sessions for c in s.customers()]
    mic = sum(c.get("source") == "mic" for c in turns)
    files = sum(c.get("source") == "file" for c in turns)
    browser = sum(any(e.get("browser") for e in s.events) for s in sessions)
    lines = [
        "# Human-call scoring report",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M UTC}. Inputs: {', '.join(inputs)}.",
        "",
        (
            f"Sessions: {len(sessions)}; counted customer turns: {len(turns)}; void sessions: {len(void)}; "
            f"sessions with browser data: {browser}."
        ),
        (
            f"Audio: {mic} mic turns (human speech) and {files} file turns (TTS audio, not human). "
            "Numbers from file turns say nothing about human callers."
        ),
        "",
        "## Sessions",
        "",
        *session_rows(sessions),
        "",
        *class_tables(sessions),
        "",
        "## Void rate",
        "",
        f"Void sessions: {per100(len(void), len(sessions))}. Ids: {', '.join(s.id for s in void) or 'none'}.",
        "",
        *latency(sessions),
        "",
        *stt_health(sessions, ledger),
        "",
        *failed_steps(sessions),
        "",
        *pauses(sessions, cuts),
        "",
        *talk_over(sessions),
        "",
        *two_readings(sessions),
        "",
    ]
    return "\n".join(lines)
