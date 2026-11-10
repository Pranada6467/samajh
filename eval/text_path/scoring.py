"""Score text-path runs against gold. Pure: no network, no LLM.

Units and gold standards:
  * field: one answer field of one product in one call, compared after `to_beliefs` (status,
    and for a stated answer its value: an enum, a bool, rupees, months or days). Gold is the
    hand-labelled extraction passed through the same `to_beliefs`. A field the call never asked
    is not counted (the rule engine turns an answer to an unasked question into `unclear`, so
    none can hide there). A call the extractor failed on counts every gold field as wrong.
    List fields (open recall, volunteered claims, sale concerns) count once per call and are
    right only when the whole set matches. A volunteered "it is a deposit" claim is ignored on
    both sides when the gold already has the customer calling that product a deposit: the
    rules read the same belief from the kind, so the repeat changes nothing.
  * flag: one (call, product, rule) triple. Gold is the rule engine run on the gold extraction,
    or the flags a scenario set states.
  * verdict: per product and per call, three-way.
  * false clear: a call whose gold verdict is flag_for_review or unclear_needs_human and whose
    pipeline verdict is clear. A call the extractor failed on has no verdict and is never clear.
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

from scenario import FlagKey, GoldLabels

from samajh.types import (
    Answer,
    Beliefs,
    CaseResult,
    FeatureClaim,
    KindClaim,
    ProductId,
    RuleId,
    Stated,
    Verdict,
)

ANSWER_FIELDS = (
    "kind", "premium_inr", "premium_readback", "payment_source", "required_for_loan",
    "provider_choice_offered", "cover_inr", "term_months", "cancel_allowed", "cancel_window_days",
    "feature_probe", "consent_given", "consent_method",
)  # fmt: skip
LIST_FIELDS = ("recall_items", "volunteered_claims", "sale_concerns")
LANGUAGES = ("hi", "hi-en", "ta", "kn")


def comparable(answer: Answer) -> tuple:
    """(status, value) with an order-free value, so two answers can be compared and printed."""
    if isinstance(answer, Stated):
        value = answer.value
        return ("stated", tuple(sorted(value)) if isinstance(value, tuple) else value)
    return (answer.status, None)


@dataclass(frozen=True)
class FieldScore:
    name: str
    gold: tuple
    got: tuple

    @property
    def ok(self) -> bool:
        return self.gold == self.got


@dataclass(frozen=True)
class CaseScore:
    id: str
    language: str
    gold_verdict: Verdict
    verdict: Verdict | None  # None: the extractor raised, so there is no verdict
    error: str | None = None
    fields: tuple[FieldScore, ...] = ()
    gold_flags: frozenset[FlagKey] = frozenset()
    flags: frozenset[FlagKey] = frozenset()
    product_verdicts: tuple[tuple[Verdict, Verdict | None], ...] = ()  # (gold, got) per product

    @property
    def false_clear(self) -> bool:
        return self.gold_verdict is not Verdict.clear and self.verdict is Verdict.clear


def _called_a_deposit(beliefs: Beliefs) -> set[ProductId]:
    """Products the customer calls a deposit in the kind answer or in open recall."""
    found = {i.product_id for i in beliefs.recall.items if i.product_id and i.kind is KindClaim.deposit}
    for product in beliefs.products:
        if isinstance(product.kind, Stated) and product.kind.value is KindClaim.deposit:
            found.add(product.product_id)
    return found


def _list_fields(beliefs: Beliefs, deposits: set[ProductId]) -> dict[str, tuple]:
    recall = Counter((i.product_id, i.kind) for i in beliefs.recall.items)
    claims = {
        (p.product_id, c.claim)
        for p in beliefs.products
        for c in p.volunteered_claims
        if not (c.claim is FeatureClaim.is_deposit and p.product_id in deposits)
    }
    concerns = {c.concern for c in beliefs.sale_concerns}

    def ordered(items: Iterable) -> tuple:
        return tuple(sorted(items, key=str))

    return {
        "recall_items": ordered(recall.items()),
        "volunteered_claims": ordered(claims),
        "sale_concerns": ordered(concerns),
    }


NO_EXTRACTION = ("no extraction", None)


def field_scores(gold: Beliefs, got: Beliefs | None) -> tuple[FieldScore, ...]:
    """`got` is None when the extractor raised: every gold field then counts as wrong."""
    scores: list[FieldScore] = []
    for gold_product in gold.products:
        got_product = got.for_product(gold_product.product_id) if got else None
        for name in ANSWER_FIELDS:
            wanted = comparable(getattr(gold_product, name))
            if wanted[0] != "not_asked":
                found = comparable(getattr(got_product, name)) if got_product else NO_EXTRACTION
                scores.append(FieldScore(name, wanted, found))
    deposits = _called_a_deposit(gold)
    gold_lists = _list_fields(gold, deposits)
    got_lists = _list_fields(got, deposits) if got else dict.fromkeys(LIST_FIELDS, NO_EXTRACTION)
    scores += [FieldScore(name, gold_lists[name], got_lists[name]) for name in LIST_FIELDS]
    return tuple(scores)


def score_case(
    id: str,
    language: str,
    gold: GoldLabels,
    gold_beliefs: Beliefs | None,
    got: CaseResult | None,
    got_beliefs: Beliefs | None,
    error: str | None = None,
) -> CaseScore:
    """`got` is None when the extractor raised: no verdict, and every gold field counts as wrong."""
    labels = GoldLabels.of(got) if got else None
    got_products = dict(labels.products) if labels else {}
    return CaseScore(
        id=id,
        language=language,
        gold_verdict=gold.verdict,
        verdict=labels.verdict if labels else None,
        error=error,
        fields=field_scores(gold_beliefs, got_beliefs) if gold_beliefs and (got_beliefs or error) else (),
        gold_flags=gold.flags,
        flags=labels.flags if labels else frozenset(),
        product_verdicts=tuple((verdict, got_products.get(pid)) for pid, verdict in gold.products),
    )


@dataclass
class Tally:
    """hits out of n. `rate` is None when n is 0: no data is not a score."""

    hits: int = 0
    n: int = 0

    def add(self, hit: bool) -> None:
        self.hits += hit
        self.n += 1

    @property
    def rate(self) -> float | None:
        return self.hits / self.n if self.n else None

    def __str__(self) -> str:
        return "n/a (n=0)" if not self.n else f"{100 * self.hits / self.n:.1f}% ({self.hits}/{self.n})"


@dataclass
class Summary:
    """Every headline number for one group of calls (all of them, or one language)."""

    cases: int = 0
    errors: int = 0
    false_clear: Tally = field(default_factory=Tally)  # n = calls whose gold is not clear
    false_alarm: Tally = field(default_factory=Tally)  # n = calls whose gold is clear
    case_verdict: Tally = field(default_factory=Tally)
    product_verdict: Tally = field(default_factory=Tally)
    all_fields: Tally = field(default_factory=Tally)
    by_field: dict[str, Tally] = field(default_factory=dict)
    flag_tp: Counter = field(default_factory=Counter)
    flag_fp: Counter = field(default_factory=Counter)
    flag_fn: Counter = field(default_factory=Counter)
    confusion: Counter = field(default_factory=Counter)  # (gold verdict, got verdict or "error")

    def precision(self, rule: RuleId | None = None) -> Tally:
        tp, fp = self._count(self.flag_tp, rule), self._count(self.flag_fp, rule)
        return Tally(tp, tp + fp)

    def recall(self, rule: RuleId | None = None) -> Tally:
        tp, fn = self._count(self.flag_tp, rule), self._count(self.flag_fn, rule)
        return Tally(tp, tp + fn)

    @staticmethod
    def _count(counter: Counter, rule: RuleId | None) -> int:
        return counter.total() if rule is None else counter[rule]


def summarise(scores: Iterable[CaseScore]) -> Summary:
    s = Summary()
    for c in scores:
        s.cases += 1
        s.errors += c.error is not None
        s.confusion[(c.gold_verdict.value, c.verdict.value if c.verdict else "error")] += 1
        if c.gold_verdict is Verdict.clear:
            s.false_alarm.add(c.verdict is not Verdict.clear)
        else:
            s.false_clear.add(c.false_clear)
        s.case_verdict.add(c.verdict is c.gold_verdict)
        for gold, got in c.product_verdicts:
            s.product_verdict.add(gold is got)
        for f in c.fields:
            s.all_fields.add(f.ok)
            s.by_field.setdefault(f.name, Tally()).add(f.ok)
        for _, rule in c.gold_flags & c.flags:
            s.flag_tp[rule] += 1
        for _, rule in c.flags - c.gold_flags:
            s.flag_fp[rule] += 1
        for _, rule in c.gold_flags - c.flags:
            s.flag_fn[rule] += 1
    return s


def by_language(scores: Iterable[CaseScore]) -> dict[str, Summary]:
    """'all' first, then each language that has at least one call."""
    scores = list(scores)
    groups = {"all": summarise(scores)}
    for language in LANGUAGES:
        own = [c for c in scores if c.language == language]
        if own:
            groups[language] = summarise(own)
    return groups
