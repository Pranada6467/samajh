"""P3b re-verification (round 2): the sampler and the 30-day edge on books and schedules the builder
never used. Offline, no network. Writes only under the directory given as the first argument.

Usage: uv run python references/reviews/iter2/probes/p3b_r2_sampler.py <scratch dir>

Checks, for every (seed, book size, schedule, rate):
  S1 no loan is eligible in two draws; S2 no loan is drawn twice; S3 drawn is a subset of eligible;
  S4 every eligible loan is 0..30 days from the sale on the draw day and sold after the previous draw;
  S5 completeness: every loan sold after the previous draw and 0..30 days old is eligible;
  S6 verify_draw recomputes every draw; S7 a tampered draw fails verification;
  S8 rate 1.0 on a covering schedule draws every loan exactly once (exhaustion);
  S9 never-eligible reasons sum to sales_in_period - eligible (through build_report).
Then the simulated calls on edge schedules: A1 no attempt after day 30; A2 the status of loans whose
retries were cut by the window; A3 attempt day equals the IST date of `at` minus the sale day.
Then the sampling statement with mixed rates, and the store's refusal of an overlapping draw.
"""

import itertools
import random
import sys
from collections import Counter
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

from samajh.ops import book as books
from samajh.ops import sampler
from samajh.ops.batch import load_batch
from samajh.ops.model import WINDOW_DAYS, AttemptOutcome, FinalStatus
from samajh.ops.report import build_report
from samajh.ops.simulate import run_draw, scripted_analysis
from samajh.ops.store import OpsStore

IST = timezone(timedelta(hours=5, minutes=30))
SCRATCH = Path(sys.argv[1])
fails: list[str] = []


def bad(msg: str) -> None:
    fails.append(msg)
    if len(fails) <= 40:
        print("FAIL", msg)


def schedules(start: date, end: date, rng: random.Random) -> dict[str, list[date]]:
    def every(k: int, first_offset: int = 7) -> list[date]:
        out, d = [], start + timedelta(days=first_offset)
        while d <= end + timedelta(days=40):
            out.append(d)
            d += timedelta(days=k)
        return out

    irregular, d = [], start + timedelta(days=rng.randrange(0, 10))
    while d <= end + timedelta(days=40):
        irregular.append(d)
        d += timedelta(days=rng.randrange(1, 41))
    return {
        "daily": every(1, 0),
        "weekly": every(7),
        "every30": every(30, 30),
        "every31": every(31, 31),
        "every45": every(45, 10),
        "irregular": irregular,
        "first_late": every(7, 50),  # first draw after day 30 of the earliest sales
    }


n_draws = n_cases = 0
for seed, size in itertools.product((1, 7, 2027, 31337), (1, 5, 37, 200, 600)):
    days = random.Random(seed).choice((10, 60, 181))
    meta, loans, _ = books.generate_book(seed, size, days=days)
    by_id = {l.record.loan_id: l for l in loans}
    rng = random.Random(f"sched|{seed}|{size}")
    for name, sched in schedules(meta.sold_from, meta.sold_to, rng).items():
        for rate in (0.05, 0.4, 1.0):
            n_cases += 1
            draws, prev = [], None
            for as_of in sched:
                d = sampler.draw(loans, meta, as_of, rate, seed, after=prev.as_of if prev else None)
                draws.append(d)
                n_draws += 1
                if not sampler.verify_draw(d, loans, prev):
                    bad(f"S6 verify {seed}/{size}/{name}/{rate} {d.draw_id}")
                el = set(d.eligible)
                if len(el) != len(d.eligible):
                    bad(f"S1 duplicate in eligible {d.draw_id}")
                ids = [x.loan_id for x in d.drawn]
                if len(set(ids)) != len(ids):
                    bad(f"S2 drawn twice within {d.draw_id}")
                if not set(ids) <= el:
                    bad(f"S3 drawn not eligible {d.draw_id}")
                for lid in el:
                    age = (as_of - by_id[lid].sold_on).days
                    if not (0 <= age <= WINDOW_DAYS) or (prev and by_id[lid].sold_on <= prev.as_of):
                        bad(f"S4 {lid} age {age} in {d.draw_id} after {prev.as_of if prev else None}")
                want = {
                    l.record.loan_id
                    for l in loans
                    if 0 <= (as_of - l.sold_on).days <= WINDOW_DAYS and (prev is None or l.sold_on > prev.as_of)
                }
                if want != el:
                    bad(f"S5 completeness {d.draw_id}: missing {sorted(want - el)[:3]} extra {sorted(el - want)[:3]}")
                for x in d.drawn:
                    if x.day_since_sale != (as_of - by_id[x.loan_id].sold_on).days:
                        bad(f"day_since_sale mismatch {x.loan_id}")
                if d.drawn:
                    t = d.model_copy(update={"drawn": d.drawn[1:] + d.drawn[:1]}) if len(d.drawn) > 1 else None
                    if t is not None and sampler.verify_draw(t, loans, prev):
                        bad(f"S7 reordered draw verified {d.draw_id}")
                    t2 = d.model_copy(update={"after": None}) if prev else None
                    if t2 is not None and sampler.verify_draw(t2, loans, prev):
                        bad(f"S7 unchained draw verified {d.draw_id}")
                prev = d
            elig_all = [lid for d in draws for lid in d.eligible]
            if len(elig_all) != len(set(elig_all)):
                c = Counter(elig_all)
                bad(f"S1 overlap {seed}/{size}/{name}/{rate}: {[k for k, v in c.items() if v > 1][:3]}")
            drawn_all = [x.loan_id for d in draws for x in d.drawn]
            if len(drawn_all) != len(set(drawn_all)):
                bad(f"S2 drawn twice across draws {seed}/{size}/{name}/{rate}")
            if rate == 1.0 and name in ("daily", "weekly") and sorted(drawn_all) != sorted(by_id):
                bad(f"S8 exhaustion {seed}/{size}/{name}: drew {len(drawn_all)} of {len(by_id)}")
print(f"sampler: {n_cases} (seed, size, schedule, rate) cases, {n_draws} draws")

# --- S9 and the 30-day edge through the store and the simulated calls ----------------------------
edge_cases = 0
attempts_seen = 0
cut_status: Counter[str] = Counter()
for seed, size, gap, rate in itertools.product((3, 85, 4242), (60, 300), (1, 7, 29, 30, 31, 33), (0.4, 1.0)):
    meta, loans, customers = books.generate_book(seed, size, days=45)
    root = SCRATCH / f"edge-{seed}-{size}-{gap}-{rate}"
    store = OpsStore(root / "ops")
    if not (root / "ops" / "batch.json").exists():
        store.init(meta, loans, date(2027, 1, 1), date(2027, 6, 30), datetime(2027, 1, 1, tzinfo=UTC))
    cust = {c.loan_id: c for c in customers}
    as_of, prev = meta.sold_from + timedelta(days=gap), None
    while as_of <= meta.sold_to + timedelta(days=WINDOW_DAYS + gap):
        if not any(d.as_of == as_of for d in store.draws()):
            d = sampler.draw(loans, meta, as_of, rate, seed, after=prev.as_of if prev else None)
            store.add_draw(d)
        prev = next(d for d in store.draws() if d.as_of == as_of)
        as_of += timedelta(days=gap)
    for d in store.draws():
        run_draw(store, d, cust, scripted_analysis)
    edge_cases += 1
    batch = load_batch(store)
    sold = {l.record.loan_id: l.sold_on for l in loans}
    for s in batch.sampled:
        for a in s.attempts:
            attempts_seen += 1
            if a.day_since_sale > WINDOW_DAYS:
                bad(f"A1 attempt after day 30: {a.attempt_id} day {a.day_since_sale}")
            ist_day = (a.at.astimezone(IST).date() - sold[a.loan_id]).days
            utc_day = (a.at.astimezone(UTC).date() - sold[a.loan_id]).days
            if ist_day != a.day_since_sale:
                bad(f"A3 IST day {ist_day} != logged {a.day_since_sale} {a.attempt_id}")
            if utc_day != ist_day:
                bad(f"A3 UTC and IST days differ {a.attempt_id}")
        c = cust[s.drawn.loan_id]
        scripted = len(c.attempts[:3])
        made = len(s.attempts)
        if made < scripted and s.attempts and s.attempts[-1].outcome in (
            AttemptOutcome.no_answer,
            AttemptOutcome.call_back_later,
            AttemptOutcome.language_switch,
        ):
            cut_status[s.status.value] += 1
            if s.status is not FinalStatus.not_reached_in_time:
                bad(f"A2 cut by window but status {s.status} {s.drawn.loan_id}")
        if s.status is FinalStatus.not_reached_in_time and s.attempts[-1].day_since_sale != WINDOW_DAYS:
            bad(f"A2 not_reached_in_time with last attempt on day {s.attempts[-1].day_since_sale}")
    rep = build_report(store)
    sm = rep.sampling
    if sum(r.count for r in sm.never_eligible) != sm.sales_in_period - sm.eligible:
        bad(f"S9 never-eligible sum {root.name}")
    if sm.eligible != len({lid for d in batch.draws for lid in d.eligible}):
        bad(f"S9 eligible count {root.name}: {sm.eligible}")
    if rep.timing.attempts_after_window.count:
        bad(f"A1 report counts {rep.timing.attempts_after_window.count} attempts after day 30 {root.name}")
    if gap > 30 and not sm.never_eligible:
        bad(f"S9 gap {gap} but no never-eligible sale {root.name}")
print(f"edge: {edge_cases} batches, {attempts_seen} attempts; retries cut by the window -> {dict(cut_status)}")

# --- the store refuses an overlapping draw; the CLI path refuses an earlier date ------------------
meta, loans, _ = books.generate_book(85)
store = OpsStore(SCRATCH / "overlap" / "ops")
if not (SCRATCH / "overlap" / "ops" / "batch.json").exists():
    store.init(meta, loans, date(2027, 1, 1), date(2027, 6, 30), datetime(2027, 1, 1, tzinfo=UTC))
d1 = sampler.draw(loans, meta, date(2027, 1, 20), 0.4, 85, after=None)
store.add_draw(d1)
overlap = sampler.draw(loans, meta, date(2027, 1, 27), 0.4, 85, after=None)  # window re-covers 4-20 Jan
try:
    store.add_draw(overlap)
    bad("store accepted a draw whose window overlaps the previous one")
except ValueError as e:
    print("store refuses overlapping draw:", e)
try:
    sampler.draw(loans, meta, date(2027, 1, 15), 0.4, 85, after=d1.as_of)
    bad("sampler accepted a draw dated before the previous draw")
except ValueError as e:
    print("sampler refuses an earlier date:", e)
# a forged draw: chained `after`, but its eligible list re-includes the previous draw's loans
forged = d1.model_copy(
    update={"draw_id": "D-2027-01-27", "as_of": date(2027, 1, 27), "after": d1.as_of}
)
store.add_draw(forged)
print("store accepts a chained forged draw (no recompute on write):", forged in store.draws())
print("load_batch.verified on the forged draw:", load_batch(store).verified)

# --- mixed rates and the equal-chance statement --------------------------------------------------
store = OpsStore(SCRATCH / "mixed" / "ops")
if not (SCRATCH / "mixed" / "ops" / "batch.json").exists():
    store.init(meta, loans, date(2027, 1, 1), date(2027, 6, 30), datetime(2027, 1, 1, tzinfo=UTC))
    prev = None
    for as_of, rate in ((date(2027, 1, 20), 1.0), (date(2027, 2, 10), 0.05), (date(2027, 3, 5), 0.4)):
        d = sampler.draw(loans, meta, as_of, rate, 85, after=prev.as_of if prev else None)
        store.add_draw(d)
        prev = d
rep = build_report(store)
print("mixed-rate inclusion:", [(d.draw_id, f"{d.inclusion:.3f}") for d in rep.draws])
print("mixed-rate statement:", rep.sampling.statement)
# small windows and rounding: daily draws at rate 0.4
store = OpsStore(SCRATCH / "daily" / "ops")
if not (SCRATCH / "daily" / "ops" / "batch.json").exists():
    store.init(meta, loans, date(2027, 1, 1), date(2027, 6, 30), datetime(2027, 1, 1, tzinfo=UTC))
    prev = None
    for k in range(70):
        d = sampler.draw(loans, meta, date(2027, 1, 4) + timedelta(days=k), 0.4, 85, after=prev.as_of if prev else None)
        store.add_draw(d)
        prev = d
rep = build_report(store)
print("daily-draw statement:", rep.sampling.statement)

print("FAILURES:", len(fails))
for f in fails[40:]:
    print("FAIL", f)
