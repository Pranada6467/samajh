"""One loan's chain of attempts: the rule both writers follow (`simulate.run_draw` and
`sessions.ingest`), so a loan's attempts read the same whichever wrote them, in whichever order.

A loan's attempts are numbered 1, 2, ... in time order. A new attempt goes at the end: it takes
the next number, and it must be later than the last attempt. An attempt whose outcome is not in
`RETRY_AFTER` ends the chain: nothing is added after it. No attempt already logged is ever moved,
renumbered or dropped. A loan gets at most `MAX_ATTEMPTS` attempts, counted over every effective
logged attempt of any kind (a superseded log line and the line that supersedes it are one attempt).
"""

from collections.abc import Iterable, Sequence
from datetime import date, datetime, timedelta, timezone

from samajh.ops.model import MAX_ATTEMPTS, RETRY_AFTER, Attempt

IST = timezone(timedelta(hours=5, minutes=30))


def india_day(at: datetime) -> date:
    """The India-time date of a moment; a naive time is taken as India time."""
    return (at if at.tzinfo else at.replace(tzinfo=IST)).astimezone(IST).date()


def chain_of(attempts: Iterable[Attempt], loan_id: str) -> list[Attempt]:
    """The loan's effective attempts, in number order."""
    return sorted((a for a in attempts if a.loan_id == loan_id), key=lambda a: a.number)


def next_number(chain: Sequence[Attempt]) -> int:
    return chain[-1].number + 1 if chain else 1


def at_limit(chain: Sequence[Attempt], max_attempts: int = MAX_ATTEMPTS) -> bool:
    """The loan has had its `max_attempts` attempts: no further one is made or accepted."""
    return len(chain) >= max_attempts


def refusal(chain: Sequence[Attempt], at: datetime, max_attempts: int = MAX_ATTEMPTS) -> str | None:
    """Why an attempt at `at` cannot go at the end of `chain`, in words; None when it can."""
    if not chain:
        return None
    last = chain[-1]
    if last.outcome not in RETRY_AFTER:
        return (
            f"the loan's attempts had already ended: attempt {last.number}, on day "
            f"{last.day_since_sale} from the sale, ended as {last.outcome.value}"
        )
    if at_limit(chain, max_attempts):
        return (
            f"the loan already has {len(chain)} logged attempts, the most a loan gets ({max_attempts}); "
            "no further attempt is taken in"
        )
    if at <= last.at:
        return (
            f"the call is dated {at.isoformat()}, not after the loan's last logged attempt "
            f"(attempt {last.number}, {last.at.isoformat()}); it cannot be put before it without renumbering"
        )
    return None
