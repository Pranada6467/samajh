"""Run the text path over a scenario set and report how the extractor did.

    uv run python eval/text_path/run.py --set dev
    uv run python eval/text_path/run.py --set dev --model google/gemini-2.5-flash-lite --model openai/gpt-4.1-nano
    uv run python eval/text_path/run.py --set frozen

Rerunnable: every LLM call goes through `LlmClient`, so a second run is all cache hits and costs
nothing. Cost and latency in the report are those of the first, uncached call of each request,
kept in `runs/calls.jsonl`. Reports are written to `eval/text_path/runs/` and printed.
"""

import argparse
import json
import statistics
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import devset
import e1
import scenario_sets
import triage
from scenario import Scenario
from scoring import ANSWER_FIELDS, LIST_FIELDS, CaseScore, Summary, by_language, score_case

from samajh.amounts import format_inr, spoken_amount
from samajh.clients.errors import ClientError
from samajh.clients.llm import LlmClient
from samajh.extract import ExtractionFailed, Llm, SlotKind, SlotTrace, slots
from samajh.extract._ground import comparison_form
from samajh.pipeline import TextRun, WithoutTemperature, run_text, takes_temperature
from samajh.rules import to_beliefs
from samajh.rules.summary import summarise as summarise_case
from samajh.types import Beliefs, CallStep, GapReason, RuleId, Speaker, Verdict

RUNS = Path(__file__).parent / "runs"
CALLS = RUNS / "calls.jsonl"

# Which replies to print next to a wrong field.
_ASKED_BY: dict[str, tuple[SlotKind, ...]] = {
    "kind": (SlotKind.kind,),
    "premium_inr": (SlotKind.premium, SlotKind.readback),
    "premium_readback": (SlotKind.readback,),
    "payment_source": (SlotKind.payment_source,),
    "payment_frequency": (SlotKind.payment_frequency,),
    "required_for_loan": (SlotKind.required_for_loan,),
    "provider_choice_offered": (SlotKind.provider_choice,),
    "cover_inr": (SlotKind.cover,),
    "term_months": (SlotKind.term,),
    "cancel_allowed": (SlotKind.cancel_window,),
    "cancel_window_days": (SlotKind.cancel_window,),
    "feature_probe": (SlotKind.features,),
    "consent_given": (SlotKind.consent,),
    "consent_method": (SlotKind.consent,),
    "recall_items": (SlotKind.recall,),
}


@dataclass(frozen=True)
class CaseRun:
    scenario: Scenario
    run: TextRun | None
    error: str | None
    score: CaseScore


@dataclass(frozen=True)
class Call:
    """Cost and latency of one LLM request when it was first made. None when that was not recorded."""

    usd: float | None
    seconds: float | None
    cache_hit: bool


def _first_made() -> dict[str, dict]:
    if not CALLS.exists():
        return {}
    rows = [json.loads(line) for line in CALLS.read_text().splitlines() if line.strip()]
    return {row["generation_id"]: row for row in rows}


def _record_calls(traces: list[SlotTrace]) -> list[Call]:
    """Append this run's uncached calls to `calls.jsonl` and price the cached ones from it."""
    known = _first_made()
    fresh = [
        {
            "generation_id": t.generation_id, "model": t.model, "usd": t.usd, "seconds": round(t.seconds, 3),
            "prompt_tokens": t.prompt_tokens, "completion_tokens": t.completion_tokens,
        }
        for t in traces
        if not t.cache_hit and t.generation_id and t.generation_id not in known
    ]  # fmt: skip
    if fresh:
        RUNS.mkdir(parents=True, exist_ok=True)
        with CALLS.open("a") as out:
            out.writelines(json.dumps(row) + "\n" for row in fresh)
        known |= {row["generation_id"]: row for row in fresh}
    calls = []
    for t in traces:
        first = known.get(t.generation_id or "")
        if not t.cache_hit:
            calls.append(Call(t.usd, t.seconds, False))
        else:
            calls.append(Call(first["usd"] if first else None, first["seconds"] if first else None, True))
    return calls


def run_case(scenario: Scenario, llm: Llm, model: str) -> CaseRun:
    gold_beliefs = (
        to_beliefs(scenario.gold_raw, scenario.record, scenario.transcript) if scenario.gold_raw else None
    )
    run: TextRun | None = None
    error = None
    try:
        run = run_text(scenario.transcript, scenario.record, llm, model=model)
    except (ExtractionFailed, ClientError, ValueError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    score = score_case(
        scenario.id,
        scenario.language.value,
        scenario.gold,
        gold_beliefs,
        run.result if run else None,
        run.beliefs if run else None,
        error,
    )
    return CaseRun(scenario, run, error, score)


# --- report ----------------------------------------------------------------------------------


def _table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def _replies(scenario: Scenario, kinds: tuple[SlotKind, ...]) -> list[str]:
    found = [s for s in slots(scenario.transcript, scenario.record) if s.kind in kinds]
    return [f'turn {s.turn.id} [{s.kind.value}] bot: "{s.question}" customer: "{s.turn.text}"' for s in found]


def _kept(beliefs: Beliefs, name: str) -> str:
    """The quote the pipeline kept for a field, to show next to a failure."""
    if name == "recall_items":
        return (
            "; ".join(f'{i.kind}:"{i.evidence.quote}"->{i.product_id}' for i in beliefs.recall.items) or "-"
        )
    if name == "sale_concerns":
        return "; ".join(f'{c.concern.value}:"{c.evidence.quote}"' for c in beliefs.sale_concerns) or "-"
    quotes = []
    for product in beliefs.products:
        if name == "volunteered_claims":
            quotes += [f'{c.claim.value}:"{c.evidence.quote}"' for c in product.volunteered_claims]
        else:
            evidence = getattr(getattr(product, name), "evidence", None)
            quotes += [f'"{evidence.quote}" (turn {evidence.turn_id})'] if evidence else []
    return "; ".join(quotes) or "-"


def _failures(runs: list[CaseRun]) -> str:
    lines: list[str] = []
    for r in runs:
        s = r.score
        wrong = [f for f in s.fields if not f.ok]
        missed, extra = s.gold_flags - s.flags, s.flags - s.gold_flags
        if not (wrong or missed or extra or r.error or s.verdict is not s.gold_verdict):
            continue
        got = s.verdict.value if s.verdict else "no verdict"
        tier = s.tier.value if s.tier else "no result"
        mark = " **FALSE CLEAR**" if s.false_clear else ""
        lines.append(
            f"\n### {s.id} ({s.language}): gold `{s.gold_verdict.value}`, pipeline `{got}`, tier `{tier}`{mark}"
        )
        if r.scenario.note:
            lines.append(f"Scenario: {r.scenario.note}")
        if r.error:
            lines.append(f"- extractor error: `{r.error}`")
        for f in wrong:
            lines.append(f"- field `{f.name}`: gold `{f.gold}`, pipeline `{f.got}`")
            lines += [f"  - {line}" for line in _replies(r.scenario, _ASKED_BY.get(f.name, ()))]
            if r.run:
                lines.append(f"  - pipeline kept: {_kept(r.run.beliefs, f.name)}")
                if f.name in ("volunteered_claims", "sale_concerns") and r.scenario.gold_raw:
                    gold_beliefs = to_beliefs(r.scenario.gold_raw, r.scenario.record, r.scenario.transcript)
                    lines.append(f"  - gold has: {_kept(gold_beliefs, f.name)}")
        for product, rule in sorted(missed, key=str):
            lines.append(f"- missed flag: `{rule.value}` on {product or 'the call'}")
        for product, rule in sorted(extra, key=str):
            flags = [f for f in r.run.result.all_flags() if (f.product_id, f.rule_id) == (product, rule)]
            said = "; ".join(f'{f.heard} | quote: "{f.quote}"' for f in flags)
            lines.append(f"- flag not in gold: `{rule.value}` on {product or 'the call'}: {said}")
    return "\n".join(lines) if lines else "\nNone."


def _call_name(trace: SlotTrace) -> str:
    return f"{trace.kind.value}/screen" if trace.screen else trace.kind.value


def _share(part: int, whole: int) -> str:
    return f"{part} of {whole} ({100 * part / whole:.2f}%)" if whole else f"{part} of 0"


def _span_stats(runs: list[CaseRun]) -> str:
    traces = [t for r in runs if r.run for t in r.run.extraction.slots]
    not_in_reply = Counter(f"{_call_name(t)}.{name}" for t in traces for name in t.not_in_reply)
    bad_pointers = Counter(f"{_call_name(t)}.{name}" for t in traces for name in t.bad_pointers)
    inconsistent = Counter(f"{_call_name(t)}.{name}" for t in traces for name in t.inconsistent)
    gaps = Counter(g.reason for r in runs if r.run for g in r.run.result.all_gaps())
    gold_gaps = Counter(g.reason for r in runs if r.scenario.perfect for g in r.scenario.perfect.all_gaps())
    ungrounded, unparsed = GapReason.quote_not_grounded, GapReason.value_not_parsed
    return "\n".join(
        [
            (
                "- Spans the model copied (amounts, durations, recall items, claims, concerns) that were not "
                f"in the reply: {_share(not_in_reply.total(), sum(t.spans for t in traces))}. "
                f"By field: {dict(not_in_reply) or 'none'}."
            ),
            (
                "- Answers whose clause numbers were missing or out of range: "
                f"{_share(bad_pointers.total(), sum(t.pointers for t in traces))}. "
                f"By field: {dict(bad_pointers) or 'none'}."
            ),
            (
                "- Both kinds are dropped to `unclear` (answers) or left for the rule engine to record as an "
                "evidence gap (recall items, claims, concerns). None is kept as an answer."
            ),
            (
                f"- Answers marked stated with no value or no span, kept as unclear: {inconsistent.total()}. "
                f"By field: {dict(inconsistent) or 'none'}."
            ),
            (
                f"- Gaps the rule engine raised with reason `quote_not_grounded`: {gaps[ungrounded]} "
                f"(with the gold extraction: {gold_gaps[ungrounded]})."
            ),
            (
                f"- Gaps with reason `value_not_parsed`: {gaps[unparsed]} "
                f"(with the gold extraction: {gold_gaps[unparsed]})."
            ),
        ]
    )


def record_values_shown(scenario: Scenario) -> Counter:
    """Values of the lender's record that appear, as text, in a bot turn the model is shown.

    Keyed by (what the bot turn asks, which record value). A lexical check: amounts as digits,
    grouped digits and in the spoken form of the call's language, plus the provider's name.
    """
    record, product = scenario.record, scenario.record.products[0]
    amounts = {
        "premium": product.premium_inr, "cover": product.cover_inr,
        "sanctioned": record.sanctioned_inr, "disbursed": record.disbursed_inr,
    }  # fmt: skip
    forms = {product.provider: "provider"}
    for label, rupees in amounts.items():
        for form in (
            str(rupees),
            format_inr(rupees),
            f"{rupees:,}",
            spoken_amount(rupees, scenario.language),
        ):
            forms[form] = label
    shown: Counter = Counter()
    for slot in slots(scenario.transcript, record):
        if slot.step in (CallStep.right_party_check, CallStep.second_check):
            continue  # never sent to the model
        for label in {label for form, label in forms.items() if form in slot.question}:
            shown[(slot.kind.value, label)] += 1
    return shown


def _leaks(runs: list[CaseRun]) -> str:
    shown: Counter = Counter()
    for r in runs:
        shown += record_values_shown(r.scenario)
    found = ", ".join(f"{label} in a `{kind}` question: {n}" for (kind, label), n in sorted(shown.items()))
    return (
        f"- Record values found in bot turns shown to the model: {found or 'none'}. A lexical check of "
        "the premium, cover, sanctioned and disbursed amounts (digits and spoken form) and the "
        "provider name. A read-back repeats the amount the customer said, so it shows the record's "
        "premium whenever the customer's amount equals it. The two identity checks are never sent."
    )


def _dev_overlap(runs: list[CaseRun]) -> str:
    """How much of this set the prompt was tuned on: replies that are word for word in the dev set."""
    dev = {
        comparison_form(t.text)
        for scenario in devset.scenarios()
        for t in scenario.transcript.turns
        if t.speaker is Speaker.customer
    } - {""}
    asked = [
        comparison_form(slot.turn.text)
        for r in runs
        for slot in slots(r.scenario.transcript, r.scenario.record)
        if slot.kind is not SlotKind.other
    ]
    shared = [text for text in asked if text in dev]
    longer = sum(len(text.split()) > 3 for text in shared)
    return (
        f"- Replies to a checked question that are word for word a reply of the development set: "
        f"{_share(len(shared), len(asked))}; {longer} of them longer than three words. The prompt was "
        "iterated on the development set, so the model's reading of these replies is in-sample."
    )


def _clusters(runs: list[CaseRun]) -> str:
    """The four languages share a base case, so errors are also counted per base case."""
    bases = {r.scenario.base for r in runs}

    def count(wrong: list[CaseRun]) -> str:
        names = sorted({r.scenario.base for r in wrong})
        return f"{len(wrong)} calls in {len(names)} of {len(bases)} base cases" + (
            f" ({', '.join(names)})" if names else ""
        )

    not_clear = [r for r in runs if r.score.gold_verdict is not Verdict.clear]
    clear = [r for r in runs if r.score.gold_verdict is Verdict.clear]
    lines = [
        f"- False clears: {count([r for r in not_clear if r.score.false_clear])}.",
        (
            f"- False alarms: {count([r for r in clear if r.score.verdict is not Verdict.clear])}; "
            f"gold-clear base cases: {len({r.scenario.base for r in clear})}."
        ),
        f"- Any wrong call verdict: {count([r for r in runs if r.score.verdict is not r.score.gold_verdict])}.",
        f"- Any wrong field: {count([r for r in runs if any(not f.ok for f in r.score.fields)])}.",
    ]
    reading = [
        f for r in runs if r.scenario.consent_reading for f in r.score.fields if f.name == "consent_given"
    ]
    others = [
        f for r in runs if not r.scenario.consent_reading for f in r.score.fields if f.name == "consent_given"
    ]
    if reading:
        lines.append(
            "- `consent_given` where the customer agreed to a misdescribed product "
            f"({', '.join(sorted(scenario_sets.CONSENT_READING))}; the set expects true and calls false a "
            f"defensible reading): {sum(f.ok for f in reading)}/{len(reading)} match the set. "
            f"All other calls: {sum(f.ok for f in others)}/{len(others)}."
        )
    return "\n".join(lines)


def triage_rows(runs: list[CaseRun]) -> list[triage.TriageRow]:
    return [
        triage.TriageRow(
            id=r.scenario.id,
            base=r.scenario.base,
            language=r.score.language,
            group=triage.group(r.scenario.customer_state, r.score.gold_verdict is Verdict.clear),
            tier=r.score.tier,
            ceiling=r.scenario.perfect.tier if r.scenario.perfect else None,
        )
        for r in runs
    ]


def _issue_lines(r: CaseRun) -> list[str]:
    """The reviewer's summary of one call, so a miss or a false referral can be read in place."""
    if r.run is None:
        return [f"  - no result: `{r.error}`"]
    summary = summarise_case(r.scenario.record, r.run.result)
    return [
        f"  - {line.tier.value}: {line.title} | record: {line.record_value} | quote: \"{line.quote}\""
        for line in summary.lines
    ]


def _triage(runs: list[CaseRun]) -> str:
    rows = triage_rows(runs)
    by_id = {r.scenario.id: r for r in runs}
    lines = [triage.table(rows), ""]
    for title, found in (
        ("Misses (a customer with a problem ends `clear` or `understanding_gap`)", triage.misses(rows)),
        ("False referrals (an informed customer on a compliant record ends `refer`)", triage.false_referrals(rows)),
    ):
        lines.append(f"{title}: {len(found)}.")
        for row in found:
            lines.append(f"- {row.id}: tier `{row.tier.value}`")
            lines += _issue_lines(by_id[row.id])
        lines.append("")
    lines.append(
        "A miss is counted only for customers the set labels misled, unaware or did not agree. "
        "`incomplete` is not a miss and not a referral: the call did not yield enough to decide. "
        "The last column runs the rule engine on the set's own extraction, so a miss there is the "
        "rules', not the extractor's. Base cases, not calls, are the independent unit."
    )
    return "\n".join(lines)


def _e1(runs: list[CaseRun]) -> str:
    rows = [
        e1.E1Row(
            base=r.scenario.base or r.scenario.id,
            stratum=r.scenario.yes_no.stratum,
            gold_clear=r.score.gold_verdict is Verdict.clear,
            yes_no_caught=not r.scenario.yes_no.confirmed,
            teach_back_caught=r.score.verdict is not Verdict.clear,
            target_flagged=any(rule is r.scenario.yes_no.target_rule for _, rule in r.score.flags),
            ceiling_caught=r.scenario.perfect is not None and r.scenario.perfect.verdict is not Verdict.clear,
        )
        for r in runs
        if r.scenario.yes_no
    ]
    return e1.table(rows)


@dataclass(frozen=True)
class Cost:
    calls: int
    cached: int
    spent_now: float
    first_usd: float | None  # None when some first-made cost is unknown
    median_s: float | None
    p90_s: float | None
    cases: int

    @property
    def per_case(self) -> float | None:
        return self.first_usd / self.cases if self.first_usd is not None and self.cases else None

    @property
    def per_call(self) -> float | None:
        return self.first_usd / self.calls if self.first_usd is not None and self.calls else None


def cost_of(runs: list[CaseRun]) -> Cost:
    traces = [t for r in runs if r.run for t in r.run.extraction.slots]
    calls = _record_calls(traces)
    seconds = sorted(c.seconds for c in calls if c.seconds is not None)
    known = all(c.usd is not None for c in calls)
    return Cost(
        calls=len(calls),
        cached=sum(c.cache_hit for c in calls),
        spent_now=sum(t.usd for t in traces),
        first_usd=sum(c.usd for c in calls) if known else None,
        median_s=statistics.median(seconds) if seconds else None,
        p90_s=seconds[int(0.9 * (len(seconds) - 1))] if seconds else None,
        cases=sum(r.run is not None for r in runs),
    )


def _usd(value: float | None) -> str:
    return "unknown" if value is None else f"${value:.5f}"


def _secs(value: float | None) -> str:
    return "unknown" if value is None else f"{value:.2f} s"


def report(set_name: str, note: str, model: str, runs: list[CaseRun], cost: Cost) -> str:
    groups = by_language([r.score for r in runs])
    names = list(groups)
    everything: Summary = groups["all"]
    # The same rules on the gold extraction: what a perfect extractor would score against this gold.
    ceiling = by_language(
        score_case(r.scenario.id, r.scenario.language.value, r.scenario.gold, None, r.scenario.perfect, None)
        for r in runs
        if r.scenario.perfect
    )["all"]
    rows = [
        [name, str(g.cases), str(g.false_clear), str(g.false_alarm), str(g.case_verdict),
         str(g.product_verdict), str(g.all_fields)]
        for name, g in groups.items()
    ]  # fmt: skip
    rows.append(
        ["gold extraction, no LLM", str(ceiling.cases), str(ceiling.false_clear), str(ceiling.false_alarm),
         str(ceiling.case_verdict), str(ceiling.product_verdict), "-"]
    )  # fmt: skip
    head = [
        f"# Text path on the `{set_name}` set, model `{model}`",
        "",
        f"Run at {datetime.now(UTC).isoformat(timespec='seconds')}. {note}",
        "",
        "## Headline",
        "",
        _table(
            ["group", "calls", "false clear", "false alarm", "call verdict", "product verdict", "fields"],
            rows,
        ),
        "",
        (
            "False clear: gold is flag_for_review or unclear_needs_human and the pipeline says clear "
            "(n = calls whose gold is not clear). False alarm: gold is clear and the pipeline does not "
            f"say clear (n = calls whose gold is clear). Extractor errors: {everything.errors}. "
            "Last row: the rule engine on the set's gold extraction, so any miss there is not the "
            "extractor's."
        ),
        "",
        "## Triage: where each kind of customer ended up",
        "",
        _triage(runs),
        "",
        "## Verdicts, gold against pipeline (all calls)",
        "",
        _table(
            ["gold", "pipeline", "calls"],
            [[gold, got, str(n)] for (gold, got), n in sorted(everything.confusion.items())],
        ),
        "",
        "## Tiers by gold verdict (all calls)",
        "",
        _table(
            ["gold verdict", "pipeline tier", "calls"],
            [[gold, got, str(n)] for (gold, got), n in sorted(everything.tiers.items())],
        ),
        "",
        "## Extraction accuracy per field",
        "",
        _table(
            ["field", *names],
            [
                [name, *(str(groups[g].by_field.get(name, "n/a (n=0)")) for g in names)]
                for name in (*ANSWER_FIELDS, *LIST_FIELDS)
                if name in everything.by_field
            ],
        ),
        "",
        "## Flags per rule: precision and recall",
        "",
        _table(
            ["rule", *(f"{g} P" for g in names), *(f"{g} R" for g in names)],
            [
                [
                    rule.value,
                    *(str(groups[g].precision(rule)) for g in names),
                    *(str(groups[g].recall(rule)) for g in names),
                ]
                for rule in RuleId
                if everything.precision(rule).n or everything.recall(rule).n
            ]
            + [
                [
                    "all rules",
                    *(str(groups[g].precision()) for g in names),
                    *(str(groups[g].recall()) for g in names),
                ]
            ],
        ),
        "",
        "## Spans and grounding",
        "",
        _span_stats(runs),
        _leaks(runs),
        "",
        "## Cost and latency",
        "",
        f"- LLM calls: {cost.calls} for {cost.cases} calls ({cost.cached} served from the cache in this run).",
        f"- Spent in this run: {_usd(cost.spent_now)}.",
        (
            f"- Cost of these calls with nothing cached: {_usd(cost.first_usd)} "
            f"({_usd(cost.per_case)} per transcript, {_usd(cost.per_call)} per LLM call)."
        ),
        (
            f"- Latency per LLM call when first made: median {_secs(cost.median_s)}, "
            f"p90 {_secs(cost.p90_s)} (wall time of the client call, retries included, one network)."
        ),
        "",
    ]
    if any(r.scenario.base for r in runs):
        head += ["## By base case", "", _clusters(runs), _dev_overlap(runs), ""]
    if any(r.scenario.yes_no for r in runs):
        head += [
            "## E1: teach-back call against the yes/no call, by stratum",
            "",
            _e1(runs),
            "",
            (
                "Caught: the call did not end as a pass (yes/no: not confirmed; teach-back: verdict not "
                "clear, which includes unclear and an extractor error). The yes/no arm is the set's "
                "scripted outcome with no LLM; coached and acquiescent customers say yes to it by "
                "assumption, and never_asked is the coverage of a five-question script. The strata are "
                "the set author's mix, so no pooled rate is given. For a clear-gold row, caught is a "
                "false alarm."
            ),
            "",
        ]
    head += ["## Failures", _failures(runs), ""]
    return "\n".join(head)


def comparison(set_name: str, rows: list[tuple[str, Summary, Cost]]) -> str:
    table = _table(
        ["model", "false clear", "false alarm", "call verdict", "fields", "flag P", "flag R", "errors",
         "$ / transcript", "$ / LLM call", "median s / LLM call"],
        [
            [f"`{model}`", str(s.false_clear), str(s.false_alarm), str(s.case_verdict), str(s.all_fields),
             str(s.precision()), str(s.recall()), str(s.errors), _usd(c.per_case), _usd(c.per_call),
             _secs(c.median_s)]
            for model, s, c in rows
        ],
    )  # fmt: skip
    return f"# Model comparison on the `{set_name}` set\n\n{table}\n"


def _slug(model: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in model)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", default="dev", choices=["dev", "frozen"])
    parser.add_argument("--model", action="append", help="OpenRouter model id; repeat to compare models")
    parser.add_argument("--workers", type=int, default=8, help="transcripts run at the same time")
    parser.add_argument("--usd-cap", type=float, default=0.5, help="spend cap per model for this run")
    args = parser.parse_args()

    loaded = scenario_sets.load(args.set)
    if loaded is None:
        print(f"The {args.set} set is not available: {scenario_sets.FROZEN} does not exist.")
        return 2
    note, scenarios = loaded
    default_model = LlmClient.from_env(usd_cap=0.0)._model  # the configured default, read the client's way
    rows = []
    for model in args.model or [default_model]:
        client = LlmClient.from_env(model=model, usd_cap=args.usd_cap)
        llm: Llm = client if takes_temperature(model) else WithoutTemperature(client)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            runs = list(pool.map(lambda s: run_case(s, llm, model), scenarios))  # noqa: B023
        cost = cost_of(runs)
        text = report(args.set, note, model, runs, cost)
        RUNS.mkdir(parents=True, exist_ok=True)
        (RUNS / f"{args.set}__{_slug(model)}.md").write_text(text)
        print(text)
        rows.append((model, by_language([r.score for r in runs])["all"], cost))
    if len(rows) > 1:
        text = comparison(args.set, rows)
        (RUNS / f"{args.set}__comparison.md").write_text(text)
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
