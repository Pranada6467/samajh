"""Turn a scenario into its two scripted calls.

The teach-back call follows DESIGN.md section 5 plus the money-back probe. The customer's line for
each step is chosen from the phrase bank by what the customer believes, so the script and the
belief cannot disagree. The extraction returned with the call is what a perfect extractor would
produce: every answer quotes the customer's whole turn.

The yes/no call asks five closed questions about the same record. A truthful customer answers
each by their belief; an acquiescent or coached customer says yes to all of them.
"""

import hashlib
from dataclasses import dataclass, field

from samajh.amounts import format_inr, spoken_amount
from samajh.scenarios.model import (
    DONT_KNOW,
    EVASIVE,
    DepositWord,
    ProductBelief,
    Recall,
    Scenario,
    TeachBackCall,
    YesNoAnswer,
    YesNoCall,
    YesNoDisposition,
    YesNoOutcome,
    YesNoQuestion,
    YesNoReply,
)
from samajh.scenarios.phrases import BANKS, PhraseBank
from samajh.types import (
    Answer,
    CallStep,
    ClaimEvidence,
    ConcernEvidence,
    DontKnow,
    Evidence,
    FeatureClaim,
    GapReason,
    KindClaim,
    PaymentSource,
    Product,
    Question,
    RawExtraction,
    RawOpenRecall,
    RawProductAnswers,
    RawRecallItem,
    SaleConcern,
    Speaker,
    Stated,
    Transcript,
    Turn,
    TurnId,
    Unclear,
)

YES_NO_PREMIUM_TOLERANCE = 0.05  # a truthful customer accepts a stated premium within 5% of what they recall
_UNEXPLAINED = frozenset({SaleConcern.learned_after_sale})
_THING = {  # how the customer names the product, for the consent phrase
    KindClaim.insurance: "insurance",
    KindClaim.investment: "investment",
    DepositWord.fd: "fd",
    DepositWord.security_deposit: "security_deposit",
}
_MONEY_BACK_KEY: dict[frozenset[FeatureClaim], str] = {
    frozenset({FeatureClaim.is_deposit, FeatureClaim.refundable_anytime}): "feat.fd_anytime",
    frozenset({FeatureClaim.is_deposit, FeatureClaim.withdrawable_after_period}): "feat.deposit_after",
    frozenset({FeatureClaim.withdrawable_after_period}): "feat.after",
    frozenset({FeatureClaim.guaranteed_return}): "feat.guaranteed",
}


def _pick(variants: tuple[str, ...], scenario_id: str, slot: str) -> str:
    """A variant chosen by a hash of the scenario and the slot: stable across runs and machines."""
    digest = hashlib.sha256(f"{scenario_id}|{slot}".encode()).digest()
    return variants[int.from_bytes(digest[:4], "big") % len(variants)]


@dataclass
class _Call:
    """Accumulates the turns of one call."""

    scenario: Scenario
    bank: PhraseBank
    turns: list[Turn] = field(default_factory=list)
    evasions: int = 0

    def bot(
        self, step: CallStep, key: str, asks: Question | None = None, product: Product | None = None, **slots
    ) -> None:
        text = self.bank.bot[key].format(**slots)
        product_id = product.id if product is not None else None
        self._add(Speaker.bot, step, text, asks, product_id)

    def customer(self, step: CallStep, key: str, slot: str | None = None, **slots) -> Evidence:
        """Say the line for `key`. `slot` names the place in the call, for the variant choice."""
        return self.say(step, self.line(key, slot, **slots))

    def say(self, step: CallStep, text: str) -> Evidence:
        turn_id = self._add(Speaker.customer, step, text, None, None)
        return Evidence(quote=text, turn_id=turn_id)

    def line(self, key: str, slot: str | None = None, **slots) -> str:
        variants = self.bank.customer[key]
        if key.startswith("evasive"):  # walk the pool so a customer who dodges every question does not repeat one line
            start = int.from_bytes(hashlib.sha256(self.scenario.id.encode()).digest()[:4], "big")
            self.evasions += 1
            return variants[(start + self.evasions) % len(variants)]
        return _pick(variants, self.scenario.id, slot or key).format(**slots)

    def _add(self, speaker, step, text, asks, product_id) -> TurnId:
        turn_id = TurnId(len(self.turns) + 1)
        self.turns.append(
            Turn(id=turn_id, speaker=speaker, step=step, text=text, asks=asks, product_id=product_id)
        )
        return turn_id

    def transcript(self, suffix: str) -> Transcript:
        return Transcript(
            call_id=f"TEST-CALL-{self.scenario.id}-{suffix}",
            loan_id=self.scenario.record.loan_id,
            language=self.scenario.language,
            turns=tuple(self.turns),
        )

    def opening(self, intro_key: str) -> None:
        """Right-party check, disclosure, year of birth and context: the same in both call styles."""
        s, bank = self.scenario, self.bank
        loan = bank.loan[s.record.loan_kind]
        lender = bank.lender[s.record.lender_type]
        self.bot(CallStep.right_party_check, "rp", name=bank.first_name)
        self.customer(CallStep.right_party_check, "rp")
        self.bot(CallStep.disclosure, intro_key, lender=lender, loan=loan)
        self.customer(CallStep.disclosure, "disc")
        self.bot(CallStep.second_check, "yob")
        self.customer(CallStep.second_check, "yob", yob=bank.years[s.record.borrower.dob.year])
        self.bot(CallStep.context, "ctx", loan=loan)
        self.customer(CallStep.context, f"ctx.{s.record.loan_kind.value}")


def _answer(value, evidence: Evidence) -> Answer:
    """A belief value as an extracted answer: stated, don't know, or no usable answer."""
    if value == DONT_KNOW:
        return DontKnow(evidence=evidence)
    if value == EVASIVE:
        return Unclear(reason=GapReason.no_usable_answer, evidence=evidence)
    return Stated(value=value, evidence=evidence)


def _keyed(
    call: _Call, step: CallStep, value, known_key: str, prefix: str, slot: str, *, closed: bool = False, **slots
) -> Evidence:
    """Say the dont-know line, an evasive line, or the line for a known value.

    `closed` marks a question a bare yes would answer. An evasive customer deflects it with a line
    that has no yes or no in it, so the reply cannot be read as an answer.
    """
    if value == DONT_KNOW:
        return call.customer(step, f"{prefix}.dont_know", slot)
    if value == EVASIVE:
        return call.customer(step, "evasive.closed" if closed else "evasive", slot)
    return call.customer(step, known_key, slot, **slots)


def _recall(call: _Call, belief: ProductBelief) -> RawOpenRecall:
    bank = call.bank
    call.bot(CallStep.open_recall, "recall")
    if belief.recall is not Recall.named:
        evidence = call.customer(CallStep.open_recall, f"recall.{belief.recall.value}")
        return RawOpenRecall(asked=True, answer=evidence)
    assert isinstance(belief.kind, KindClaim), "a named product has a believed kind"
    amount = bank.amounts[belief.premium_inr] if isinstance(belief.premium_inr, int) else None
    if belief.consent_given is False:
        key = "recall.insurance_added"
    elif belief.deposit_word is not None:
        key = f"recall.{belief.deposit_word.value}"
    elif amount is None:
        key = "recall.insurance_noamt"
    else:
        key = f"recall.{belief.kind.value}"
    evidence = call.customer(CallStep.open_recall, key, premium=amount)
    item = RawRecallItem(evidence=evidence, kind=belief.kind, amount_text=amount, product_id=belief.product_id)
    return RawOpenRecall(asked=True, answer=evidence, items=(item,))


def _consent_key(belief: ProductBelief) -> str:
    if belief.consent_given is False:
        return "consent.no"
    if belief.consent_method == DONT_KNOW:
        return "consent.no_method"
    thing = _THING[belief.deposit_word or belief.kind]
    return f"consent.{thing}.{belief.consent_method.value}"


def teach_back(scenario: Scenario) -> TeachBackCall:
    """The scripted Samajh call for one scenario, with the perfect extraction of it."""
    bank = BANKS[scenario.language]
    call = _Call(scenario, bank)
    step = CallStep.teach_back
    call.opening("disc")

    (product,) = scenario.record.products  # v1 scenarios carry one product
    belief = scenario.belief(product.id)
    recall = _recall(call, belief)
    answers: dict[str, Answer] = {}
    claims: list[ClaimEvidence] = []

    call.bot(step, "kind", Question.kind, product)
    kind_key = f"kind.{(belief.deposit_word or belief.kind).value}" if isinstance(belief.kind, KindClaim) else ""
    answers["kind"] = _answer(belief.kind, _keyed(call, step, belief.kind, kind_key, "kind", "kind"))

    call.bot(step, "premium", Question.premium, product)
    premium_said = isinstance(belief.premium_inr, int)
    premium_words = bank.amounts[belief.premium_inr] if premium_said else None
    if belief.one_time_claim:
        premium_key = "premium.once"
    else:
        premium_key = "premium.taken" if belief.consent_given is False else "premium.say"
    if belief.premium_inr == DONT_KNOW and belief.recall is Recall.named:
        evidence = call.customer(step, "premium.forgot")  # knows the product, forgot the figure
    else:
        evidence = _keyed(
            call, step, belief.premium_inr, premium_key, "premium", "premium", premium=premium_words
        )
    answers["premium"] = _answer(premium_words if premium_said else belief.premium_inr, evidence)
    if belief.one_time_claim:
        claims.append(ClaimEvidence(claim=FeatureClaim.one_time_payment, evidence=evidence))

    call.bot(step, "pay", Question.payment_source, product)
    debited = belief.consent_given is False and not product.paid_from_loan
    pay_key = "pay.separately_debited" if debited else f"pay.{belief.payment_source}"
    answers["payment_source"] = _answer(
        belief.payment_source, _keyed(call, step, belief.payment_source, pay_key, "pay", "pay")
    )

    call.bot(step, "req", Question.required_for_loan, product)
    if belief.required_for_loan is True:
        req_key = "req.yes"
    elif belief.consent_given is False:
        req_key = "req.no_plain"
    else:
        req_key = "req.no_soft" if belief.required_said_softly else "req.no"
    answers["required_for_loan"] = _answer(
        belief.required_for_loan,
        _keyed(call, step, belief.required_for_loan, req_key, "req", "req", closed=True),
    )

    if belief.provider_choice_offered is not None:
        call.bot(step, "choice", Question.provider_choice, product)
        choice_key = "choice.yes" if belief.provider_choice_offered is True else "choice.no"
        answers["provider_choice_offered"] = _answer(
            belief.provider_choice_offered,
            _keyed(call, step, belief.provider_choice_offered, choice_key, "choice", "choice", closed=True),
        )

    call.bot(step, "cover", Question.cover, product)
    cover_said = isinstance(belief.cover_inr, int)
    cover_words = bank.amounts[belief.cover_inr] if cover_said else None
    evidence = _keyed(call, step, belief.cover_inr, "cover.say", "cover", "cover", cover=cover_words)
    answers["cover"] = _answer(cover_words if cover_said else belief.cover_inr, evidence)

    call.bot(step, "term", Question.term, product)
    term_said = isinstance(belief.term_months, int)
    term_words = bank.durations[belief.term_months] if term_said else None
    evidence = _keyed(call, step, belief.term_months, "term.say", "term", "term", term=term_words)
    answers["term"] = _answer(term_words if term_said else belief.term_months, evidence)

    call.bot(step, "cancel", Question.cancel_window, product)
    if belief.cancel_allowed is True:
        window = bank.windows[belief.cancel_window_days]
        evidence = call.customer(step, "cancel.say", window=window)
        answers["cancel_window"] = Stated(value=window, evidence=evidence)
    else:
        evidence = _keyed(call, step, belief.cancel_allowed, "cancel.not_told", "cancel", "cancel", closed=True)
        if belief.cancel_allowed == EVASIVE:
            answers["cancel_window"] = _answer(EVASIVE, evidence)
    answers["cancel_allowed"] = _answer(belief.cancel_allowed, evidence)

    call.bot(step, "feat", Question.features, product)
    if isinstance(belief.money_back, tuple):
        if belief.money_back:
            feat_key = _MONEY_BACK_KEY[frozenset(belief.money_back)]
        else:
            feat_key = "feat.none_window" if belief.money_back_mentions_window else "feat.none"
        evidence = call.customer(
            step,
            feat_key,
            period=bank.durations.get(belief.money_back_period_months),
            window=bank.windows.get(product.cancel_window_days),
        )
    else:
        evidence = _keyed(call, step, belief.money_back, "", "feat", "feat", closed=True)
    answers["feature_probe"] = _answer(belief.money_back, evidence)

    call.bot(CallStep.consent_check, "consent", Question.consent)
    concern_lines = [(c, call.line(f"concern.{c.value}")) for c in scenario.concerns]
    if belief.consent_given in (DONT_KNOW, EVASIVE):
        key = "consent.dont_know" if belief.consent_given == DONT_KNOW else "evasive"
        consent_line = call.line(key, "consent")
    else:
        consent_line = call.line(_consent_key(belief), "consent")
    evidence = call.say(CallStep.consent_check, " ".join([consent_line, *(line for _, line in concern_lines)]))
    answers["consent_given"] = _answer(belief.consent_given, evidence)
    if belief.consent_given is True or belief.consent_given in (DONT_KNOW, EVASIVE):
        method = belief.consent_method if belief.consent_given is True else belief.consent_given
        answers["consent_method"] = _answer(method, evidence)
    concerns = tuple(
        ConcernEvidence(concern=c, evidence=Evidence(quote=line, turn_id=evidence.turn_id))
        for c, line in concern_lines
    )

    if premium_said:
        call.bot(
            CallStep.read_back,
            "readback",
            Question.premium,
            product,
            canon=spoken_amount(belief.premium_inr, scenario.language),
            inr=format_inr(belief.premium_inr),
        )
        answers["premium_readback"] = Stated(value=True, evidence=call.customer(CallStep.read_back, "readback.yes"))

    call.bot(CallStep.close, "close")
    call.customer(CallStep.close, "close")

    transcript = call.transcript("tb")
    extraction = RawExtraction(
        call_id=transcript.call_id,
        recall=recall,
        products=(
            RawProductAnswers(product_id=product.id, volunteered_claims=tuple(claims), **answers),
        ),
        sale_concerns=concerns,
    )
    return TeachBackCall(transcript=transcript, extraction=extraction)


def _yes_no_answer(question: YesNoQuestion, scenario: Scenario, product: Product) -> tuple[YesNoAnswer, str]:
    """The reply to one closed question and the phrase key that says it."""
    yes = (YesNoAnswer.yes, "yn.yes")
    if scenario.yes_no is not YesNoDisposition.truthful:
        return yes
    belief = scenario.belief(product.id)
    name = question.value
    if question is YesNoQuestion.bought:
        if belief.consent_given is False:
            return YesNoAnswer.no, "yn.bought.no_consent"
        if belief.kind == KindClaim.insurance:
            return yes
        if isinstance(belief.kind, KindClaim):
            return YesNoAnswer.no, f"yn.bought.no_{(belief.deposit_word or belief.kind).value}"
    elif question is YesNoQuestion.premium:
        if isinstance(belief.premium_inr, int):
            close = abs(belief.premium_inr - product.premium_inr) <= YES_NO_PREMIUM_TOLERANCE * product.premium_inr
            return yes if close else (YesNoAnswer.no, "yn.premium.no")
    elif question is YesNoQuestion.payment:
        on_record = PaymentSource.from_loan if product.paid_from_loan else PaymentSource.separately
        if belief.payment_source == on_record:
            return yes
        if isinstance(belief.payment_source, PaymentSource):
            return YesNoAnswer.no, f"yn.payment.no_{belief.payment_source.value}"
    elif question is YesNoQuestion.consent:
        if belief.consent_given is True:
            return yes
        if belief.consent_given is False:
            return YesNoAnswer.no, "yn.consent.no"
    elif question is YesNoQuestion.explained:
        if _UNEXPLAINED & set(scenario.concerns):
            return YesNoAnswer.no, "yn.explained.no"
        if belief.kind != DONT_KNOW:
            return yes
    return YesNoAnswer.unsure, f"yn.{name}.unsure"


def yes_no(scenario: Scenario) -> YesNoCall:
    """The scripted confirmation call for one scenario: five closed questions about the record."""
    bank = BANKS[scenario.language]
    call = _Call(scenario, bank)
    step = CallStep.teach_back  # CallStep has no step for a closed confirmation question
    call.opening("yn.intro")
    (product,) = scenario.record.products

    questions = (
        (YesNoQuestion.bought, "yn.bought", Question.kind, product),
        (YesNoQuestion.premium, "yn.premium", Question.premium, product),
        (
            YesNoQuestion.payment,
            "yn.payment.from_loan" if product.paid_from_loan else "yn.payment.separately",
            Question.payment_source,
            product,
        ),
        (YesNoQuestion.consent, "yn.consent", Question.consent, None),
        (YesNoQuestion.explained, "yn.explained", None, None),
    )
    replies: list[YesNoReply] = []
    for question, bot_key, asks, about in questions:
        call.bot(
            step,
            bot_key,
            asks,
            about,
            provider=bank.provider,
            canon=spoken_amount(product.premium_inr, scenario.language),
        )
        answer, key = _yes_no_answer(question, scenario, product)
        evidence = call.customer(step, key, f"yn.{question.value}")
        replies.append(YesNoReply(question=question, answer=answer, turn_id=evidence.turn_id))
    call.bot(CallStep.close, "yn.close")

    confirmed = all(r.answer is YesNoAnswer.yes for r in replies)
    return YesNoCall(
        transcript=call.transcript("yn"),
        replies=tuple(replies),
        outcome=YesNoOutcome.confirmed if confirmed else YesNoOutcome.not_confirmed,
    )
