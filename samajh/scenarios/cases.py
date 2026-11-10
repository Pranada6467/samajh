"""The base scenarios and their gold verdicts, written by hand.

Gold follows DESIGN.md section 6 as a person reading it would apply it, plus the coordinator's
decisions of 2026-11-10 (the money-back probe is part of the call; a product not named in open
recall is a low flag; a customer who cannot say how they agreed is unclear). The rule engine is
never called here. `data/scenarios/README.md` lists the reading used for each rule, and
`data/scenarios/CHANGELOG.md` lists every change made to gold after the first freeze.

Every party, id and figure is invented. Where a case is templated on a public award, `Template`
says what was taken from the award and what the scenario changes.
"""

from datetime import date

from samajh.scenarios.model import (
    DONT_KNOW,
    EVASIVE,
    BaseCase,
    CustomerState,
    DepositWord,
    Gold,
    ProductBelief,
    ProductGold,
    Recall,
    RecordFacts,
    Remedy,
    ScenarioClass,
    Template,
    YesNoDisposition,
)
from samajh.types import (
    Consent,
    ConsentMethod,
    FeatureClaim,
    KindClaim,
    LenderType,
    LoanKind,
    PaymentSource,
    Product,
    ProductId,
    ProductKind,
    RuleId,
    SaleConcern,
    Verdict,
)

P1 = ProductId("P1")
PROVIDER = "Namoona Life (synthetic)"
SALE_DAY = date(2027, 1, 11)
ONE_TIME = frozenset({FeatureClaim.one_time_payment})
REGULAR_PREMIUM: frozenset[FeatureClaim] = frozenset()

BANK, NBFC = LenderType.bank, LenderType.nbfc
GOLD_LOAN, PERSONAL = LoanKind.gold, LoanKind.personal
FROM_LOAN, SEPARATELY = PaymentSource.from_loan, PaymentSource.separately
INSURANCE, DEPOSIT, INVESTMENT = KindClaim.insurance, KindClaim.deposit, KindClaim.investment
CLEAR, FLAGGED, UNCLEAR = Verdict.clear, Verdict.flag_for_review, Verdict.unclear_needs_human
VIOLATING, COMPLIANT, NEAR_MISS = ScenarioClass.violating, ScenarioClass.compliant, ScenarioClass.near_miss
TRUTHFUL, ACQUIESCENT, COACHED = (
    YesNoDisposition.truthful,
    YesNoDisposition.acquiescent,
    YesNoDisposition.coached,
)
INFORMED, MISLED, UNAWARE, DID_NOT_AGREE = (
    CustomerState.informed,
    CustomerState.misled,
    CustomerState.unaware,
    CustomerState.did_not_agree,
)

R = RuleId
IS_DEPOSIT = FeatureClaim.is_deposit
ANYTIME = FeatureClaim.refundable_anytime
AFTER_PERIOD = FeatureClaim.withdrawable_after_period
GUARANTEED = FeatureClaim.guaranteed_return

SCRIPT_COVERS = "The confirmation script asks nothing about this, so a truthful customer says yes throughout."
ANSWERS_BY_BELIEF = "Answers each closed question by what they believe."


def _consent(method: ConsentMethod) -> Consent:
    return Consent(method=method, at=SALE_DAY)


def _product(**changes) -> Product:
    base = {
        "id": P1,
        "kind": ProductKind.credit_life,
        "provider": PROVIDER,
        "premium_inr": 12_500,
        "cover_inr": 250_000,
        "term_months": 24,
        "paid_from_loan": True,
        "required_for_loan": False,
        "risk_mitigant": True,
        "provider_choice_offered": True,
        "cancel_window_days": 30,
        "features": ONE_TIME,
        "consent": _consent(ConsentMethod.otp),
    }
    return Product(**(base | changes))


def _record(
    product: Product, lender: LenderType, loan: LoanKind, sanctioned: int, birth_year: int = 1985
) -> RecordFacts:
    deducted = product.premium_inr if product.paid_from_loan else 0
    return RecordFacts(
        lender_type=lender,
        loan_kind=loan,
        sanctioned_inr=sanctioned,
        disbursed_inr=sanctioned - deducted,
        disbursed_on=SALE_DAY,
        birth_year=birth_year,
        products=(product,),
    )


def _informed(product: Product, **changes) -> ProductBelief:
    """Beliefs that match the record in every field. A record without consent needs `consent_*` passed in."""
    base = {
        "product_id": product.id,
        "recall": Recall.named,
        "kind": INSURANCE,
        "premium_inr": product.premium_inr,
        "payment_source": FROM_LOAN if product.paid_from_loan else SEPARATELY,
        "required_for_loan": product.required_for_loan,
        "provider_choice_offered": product.provider_choice_offered if product.required_for_loan else None,
        "cover_inr": product.cover_inr,
        "term_months": product.term_months,
        "cancel_allowed": product.cancel_window_days is not None,
        "cancel_window_days": product.cancel_window_days,
        "money_back": (),
    }
    if product.consent is not None:
        base |= {"consent_given": True, "consent_method": product.consent.method}
    return ProductBelief(**(base | changes))


def _gold(
    verdict: Verdict,
    rationale: str,
    flags: tuple[RuleId, ...] = (),
    unclear: tuple[RuleId, ...] = (),
    case_flags: tuple[RuleId, ...] = (),
) -> Gold:
    product_verdict = FLAGGED if flags else UNCLEAR if unclear else CLEAR
    return Gold(
        verdict=verdict,
        products=(
            ProductGold(
                product_id=P1,
                verdict=product_verdict,
                flags=tuple(sorted(flags)),
                unclear=tuple(sorted(unclear)),
            ),
        ),
        case_flags=tuple(sorted(case_flags)),
        rationale=rationale,
    )


def _cases() -> tuple[BaseCase, ...]:
    cases: list[BaseCase] = []

    # ---- U: understanding of what was bought (85Y / 101Y) -------------------------------------

    p = _product()
    cases.append(
        BaseCase(
            id="U01",
            title="Informed customer, premium deducted from a gold loan with an OTP consent",
            target_rule=R.kind,
            scenario_class=COMPLIANT,
            record=_record(p, BANK, GOLD_LOAN, 250_000),
            told="Told it is loan insurance, a single payment of 12,500 taken out of the loan, optional, "
            "30 days to cancel. Gave an OTP for it.",
            beliefs=(_informed(p, one_time_claim=True),),
            customer_state=INFORMED,
            yes_no=TRUTHFUL,
            yes_no_basis=ANSWERS_BY_BELIEF,
            gold=_gold(
                CLEAR,
                "Names the insurance unprompted. Kind, premium (confirmed at read-back), payment from the "
                "loan, cover, term and the 30-day window all match the record. Says it was optional. Makes "
                "no money-back claim. Describes the OTP consent on record. The remark that it is paid only "
                "once is true of this product.",
            ),
            tags=("loan-funded-with-consent",),
        )
    )

    p = _product(premium_inr=52_000, cover_inr=500_000, term_months=36, consent=None)
    cases.append(
        BaseCase(
            id="U02",
            title="Credit-life premium deducted from a gold loan and described as an FD for loan security",
            target_rule=R.kind,
            scenario_class=VIOLATING,
            record=_record(p, BANK, GOLD_LOAN, 500_000),
            told="Told that 52,000 would be kept as a fixed deposit, as security for the gold loan, and "
            "could be taken out whenever needed. Signed the loan papers.",
            beliefs=(
                _informed(
                    p,
                    kind=DEPOSIT,
                    deposit_word=DepositWord.fd,
                    required_for_loan=True,
                    provider_choice_offered=False,
                    cover_inr=DONT_KNOW,
                    term_months=DONT_KNOW,
                    cancel_allowed=False,
                    cancel_window_days=None,
                    money_back=(IS_DEPOSIT, ANYTIME),
                    consent_given=True,
                    consent_method=ConsentMethod.signed_form,
                ),
            ),
            customer_state=MISLED,
            yes_no=ACQUIESCENT,
            yes_no_basis="Our assumption, taken from the demo line in DESIGN.md section 10 (the customer "
            "says yes when asked whether they took a policy). The award discusses no call.",
            gold=_gold(
                FLAGGED,
                "Calls the product an FD: kind differs from the record, and the belief that it is a "
                "deposit that can be broken at any time contradicts the product (belief_mismatch). The "
                "record holds no consent, which flags consent on the record alone and, with the premium "
                "taken from the loan, loan_funded. The customer says it was needed for the loan and that "
                "no other provider was mentioned (bundling). Does not know the cover or the term and was "
                "not told about cancelling although the record shows 30 days.",
                flags=(
                    R.kind,
                    R.belief_mismatch,
                    R.consent,
                    R.loan_funded,
                    R.bundling,
                    R.cover,
                    R.term,
                    R.cancel_window,
                ),
            ),
            template=Template(
                case="BHP-L-021-1617-0529",
                ledger="B1",
                taken="Rs 52,000 deducted from a gold-loan amount and described by the bank as a fixed "
                "deposit for loan security; it was a life-insurance policy.",
                changed="The loan size, the consent gap and every answer in the call are ours. The award "
                "states only the Rs 52,000 and discusses no verification call.",
                remedy=Remedy.refund,
                remedy_note="Insurer directed to cancel the policy and refund Rs 52,000. The Forum's own "
                "finding is that cancellation was sought within two months.",
            ),
            tags=("sold-as-fd", "loan-funded-without-consent"),
        )
    )

    p = _product(
        premium_inr=52_000, cover_inr=500_000, term_months=36, consent=_consent(ConsentMethod.signed_form)
    )
    cases.append(
        BaseCase(
            id="U03",
            title="Customer believes the premium was 40,000; the record says 52,000",
            target_rule=R.premium,
            scenario_class=VIOLATING,
            record=_record(p, BANK, PERSONAL, 500_000, 1990),
            told="Told the loan insurance would cost about forty thousand. Signed the insurance form.",
            beliefs=(_informed(p, premium_inr=40_000),),
            customer_state=MISLED,
            yes_no=TRUTHFUL,
            yes_no_basis="Hears 52,000 in the premium question and says it was not that much.",
            gold=_gold(
                FLAGGED,
                "States 40,000 and confirms it at read-back; the record says 52,000, a 23% difference, "
                "far outside the 1% tolerance. Everything else matches the record.",
                flags=(R.premium,),
            ),
        )
    )

    p = _product(premium_inr=12_400)
    cases.append(
        BaseCase(
            id="U04",
            title="Premium rounded to a fraction word, inside the 1% tolerance",
            target_rule=R.premium,
            scenario_class=NEAR_MISS,
            record=_record(p, NBFC, GOLD_LOAN, 250_000, 1978),
            told="Told the loan insurance costs 12,400, taken from the loan. Gave an OTP.",
            beliefs=(_informed(p, premium_inr=12_500),),
            customer_state=INFORMED,
            yes_no=TRUTHFUL,
            yes_no_basis="Hears 12,400 and accepts it as the amount they remember as twelve and a half thousand.",
            gold=_gold(
                CLEAR,
                "Says twelve and a half thousand (12,500) for a premium of 12,400: 100 rupees off, 0.81% "
                "of the record, inside the 1% tolerance. Everything else matches.",
            ),
            tags=("premium-within-tolerance",),
        )
    )

    p = _product(premium_inr=12_350)
    cases.append(
        BaseCase(
            id="U05",
            title="Premium rounded to a fraction word, just outside the 1% tolerance",
            target_rule=R.premium,
            scenario_class=VIOLATING,
            record=_record(p, NBFC, GOLD_LOAN, 250_000),
            told="Told the loan insurance costs 12,350, taken from the loan. Gave an OTP.",
            beliefs=(_informed(p, premium_inr=12_500),),
            customer_state=INFORMED,
            yes_no=TRUTHFUL,
            yes_no_basis="Hears 12,350 and accepts it as the amount they remember as twelve and a half thousand.",
            gold=_gold(
                FLAGGED,
                "Says twelve and a half thousand (12,500) for a premium of 12,350: 150 rupees off, 1.21% "
                "of the record, outside the 1% tolerance, so the premium rule flags. The customer is not "
                "misled; this is the rule's known cost at the boundary.",
                flags=(R.premium,),
            ),
            tags=("premium-just-outside-tolerance", "flag-on-informed-customer"),
        )
    )

    p = _product(
        premium_inr=18_000, cover_inr=300_000, term_months=36, consent=_consent(ConsentMethod.signed_form)
    )
    cases.append(
        BaseCase(
            id="U06",
            title="Customer believes the cover is ten lakh and does not know the term",
            target_rule=R.cover,
            scenario_class=VIOLATING,
            record=_record(p, BANK, PERSONAL, 300_000, 1990),
            told="Told the loan insurance gives a cover of ten lakh. The term was not mentioned.",
            beliefs=(_informed(p, cover_inr=1_000_000, term_months=DONT_KNOW),),
            customer_state=MISLED,
            yes_no=TRUTHFUL,
            yes_no_basis=SCRIPT_COVERS,
            gold=_gold(
                FLAGGED,
                "States a cover of 10,00,000 where the record says 3,00,000 (wrong) and does not know the "
                "term (unaware). Both are lower-severity understanding flags. Kind, premium, payment and "
                "consent match.",
                flags=(R.cover, R.term),
            ),
        )
    )

    p = _product(premium_inr=18_000, cover_inr=300_000, term_months=36)
    cases.append(
        BaseCase(
            id="U07",
            title="Customer was told 15 days to cancel; the record says 30",
            target_rule=R.cancel_window,
            scenario_class=VIOLATING,
            record=_record(p, NBFC, PERSONAL, 300_000, 1978),
            told="Told the cover can be cancelled within 15 days.",
            beliefs=(_informed(p, cancel_window_days=15),),
            customer_state=MISLED,
            yes_no=TRUTHFUL,
            yes_no_basis=SCRIPT_COVERS,
            gold=_gold(
                FLAGGED,
                "Says the cover can be cancelled within 15 days; the record shows 30. A wrong window is a "
                "lower-severity flag. Everything else matches.",
                flags=(R.cancel_window,),
            ),
        )
    )

    p = _product(premium_inr=25_000, cover_inr=300_000, term_months=36)
    cases.append(
        BaseCase(
            id="U08",
            title="Customer believes the cover is an investment plan that grows",
            target_rule=R.kind,
            scenario_class=VIOLATING,
            record=_record(p, BANK, PERSONAL, 300_000),
            told="Told it is an investment plan: 25,000 goes in and comes back bigger after three years, "
            "guaranteed. Gave an OTP for 'the plan'.",
            beliefs=(
                _informed(p, kind=INVESTMENT, cover_inr=DONT_KNOW, money_back=(GUARANTEED,)),
            ),
            customer_state=MISLED,
            yes_no=TRUTHFUL,
            yes_no_basis="Asked whether they took an insurance policy, says it is an investment plan.",
            gold=_gold(
                FLAGGED,
                "Calls the product an investment plan (kind) and says the money comes back grown and "
                "guaranteed, which contradicts a pure credit-life cover (belief_mismatch). Does not know "
                "the cover. The customer recognises giving an OTP for this purchase, so consent is not "
                "flagged: the misdescription is carried by kind and belief_mismatch.",
                flags=(R.kind, R.belief_mismatch, R.cover),
            ),
        )
    )

    p = _product()
    cases.append(
        BaseCase(
            id="U09",
            title="Informed customer who cannot remember the amount",
            target_rule=R.premium,
            scenario_class=NEAR_MISS,
            record=_record(p, BANK, GOLD_LOAN, 250_000, 1990),
            told="Told everything correctly. Does not remember the figure a few weeks later.",
            beliefs=(_informed(p, premium_inr=DONT_KNOW),),
            customer_state=INFORMED,
            yes_no=TRUTHFUL,
            yes_no_basis="Cannot confirm a figure they do not remember.",
            gold=_gold(
                UNCLEAR,
                "Does not state the premium. DESIGN.md section 6: premium not stated is unclear, not a "
                "flag. Every other answer matches, so the case goes to a human with no flag.",
                unclear=(R.premium,),
            ),
            tags=("dont-know",),
        )
    )

    p = _product(
        premium_inr=7_500, cover_inr=150_000, term_months=12, consent=_consent(ConsentMethod.digital_click)
    )
    cases.append(
        BaseCase(
            id="U10",
            title="Customer who answers 'I don't know' to almost everything",
            target_rule=R.cover,
            scenario_class=VIOLATING,
            record=_record(p, NBFC, PERSONAL, 150_000, 1978),
            told="Was handed a phone to tap through the loan screens. Nobody mentioned insurance.",
            beliefs=(
                ProductBelief(
                    product_id=P1,
                    recall=Recall.dont_know,
                    kind=DONT_KNOW,
                    premium_inr=DONT_KNOW,
                    payment_source=DONT_KNOW,
                    required_for_loan=DONT_KNOW,
                    provider_choice_offered=None,
                    cover_inr=DONT_KNOW,
                    term_months=DONT_KNOW,
                    cancel_allowed=DONT_KNOW,
                    money_back=DONT_KNOW,
                    consent_given=DONT_KNOW,
                    consent_method=None,
                ),
            ),
            customer_state=UNAWARE,
            yes_no=TRUTHFUL,
            yes_no_basis="Says they are not sure to each closed question.",
            gold=_gold(
                FLAGGED,
                "Names nothing in open recall (recall). Unaware of the cover, the term and whether it can "
                "be cancelled: section 6 flags each. The premium came out of the loan and the customer "
                "did not know how it was paid (loan_funded). The customer does not know what they agreed "
                "to buy, which section 6 flags under consent, and answers 'I don't know' to the money-back "
                "probe, which section 6 flags under belief_mismatch. Not knowing what the product is flags "
                "kind: section 6 is silent on that answer, and this is our reading, by analogy with the "
                "other understanding rules. Section 6 says a premium 'not stated' is unclear, and not "
                "knowing whether the product was required is unclear.",
                flags=(
                    R.recall,
                    R.kind,
                    R.cover,
                    R.term,
                    R.cancel_window,
                    R.loan_funded,
                    R.consent,
                    R.belief_mismatch,
                ),
                unclear=(R.premium, R.bundling),
            ),
            tags=("dont-know",),
        )
    )

    # ---- G: consent (85G / 101G) --------------------------------------------------------------

    p = _product(
        premium_inr=200_000,
        cover_inr=2_000_000,
        term_months=60,
        paid_from_loan=False,
        cancel_window_days=None,
        features=REGULAR_PREMIUM,
        consent=None,
    )
    cases.append(
        BaseCase(
            id="G01",
            title="Two lakh debited from the borrower's account for a policy, no consent on record",
            target_rule=R.consent,
            scenario_class=VIOLATING,
            record=_record(p, BANK, PERSONAL, 2_000_000),
            told="Told nothing. Saw a debit of two lakh for insurance in the savings-account passbook.",
            beliefs=(
                _informed(
                    p,
                    cover_inr=DONT_KNOW,
                    term_months=DONT_KNOW,
                    money_back=DONT_KNOW,
                    consent_given=False,
                    consent_method=None,
                ),
            ),
            concerns=(SaleConcern.learned_after_sale,),
            customer_state=DID_NOT_AGREE,
            yes_no=TRUTHFUL,
            yes_no_basis="Denies having taken the policy and denies consenting.",
            gold=_gold(
                FLAGGED,
                "The record holds no consent and the customer says they agreed only to the loan "
                "(consent). They say they learned of the policy afterwards, which is a sale-conduct "
                "concern at case level. They do not know the cover or the term, and do not know whether "
                "the money can be got back, which section 6 flags (low) under belief_mismatch. The premium "
                "was paid from the savings account, as the record says, so loan_funded does not apply. The "
                "record shows no cancellation window and the customer was told of none, which is consistent.",
                flags=(R.consent, R.cover, R.term, R.belief_mismatch),
                case_flags=(R.sale_conduct,),
            ),
            template=Template(
                case="Baramulla DCDRC CC 33/2025",
                ledger="B7",
                taken="Rs 2,00,000 debited from a borrower's account for a life policy without knowledge "
                "or consent.",
                changed="The order concerns a cash-credit loan; the scenario uses a personal loan because "
                "the record type has no cash-credit kind. The order discusses no call. It was passed ex "
                "parte, and our copy is a scan hosted by a news site.",
                remedy=Remedy.refund,
                remedy_note="Policy cancelled; refund of Rs 2,00,000 with 8% interest, Rs 50,000 "
                "compensation and Rs 10,000 litigation charges.",
            ),
        )
    )

    p = _product(
        premium_inr=18_000, cover_inr=300_000, term_months=36, consent=_consent(ConsentMethod.signed_form)
    )
    cases.append(
        BaseCase(
            id="G02",
            title="Signed consent on file; the customer says they agreed only to the loan",
            target_rule=R.consent,
            scenario_class=VIOLATING,
            record=_record(p, NBFC, PERSONAL, 300_000, 1990),
            told="While filling the loan form the officer described a loan insurance: its cost, cover, "
            "term and the 30 days to cancel. He never asked whether the customer wanted it. A stack of "
            "papers was then signed with no word on which was which.",
            beliefs=(_informed(p, consent_given=False, consent_method=None),),
            concerns=(SaleConcern.signed_without_explanation,),
            customer_state=DID_NOT_AGREE,
            yes_no=TRUTHFUL,
            yes_no_basis="Denies having taken the policy and denies consenting. The terms were described, "
            "so says yes to that question.",
            gold=_gold(
                FLAGGED,
                "A signed form is on file, but the customer's own account of what they agreed to buy "
                "leaves the insurance out: a consent record the customer does not recognise flags consent. "
                "Signing without explanation is a sale-conduct concern at case level. The facts of the "
                "product are known to the customer and match. loan_funded is not flagged on the letter of "
                "section 6: the record holds a consent and the customer knows the premium came out of the "
                "loan.",
                flags=(R.consent,),
                case_flags=(R.sale_conduct,),
            ),
            template=Template(
                case="PUN-L-041-1617-0649",
                ledger="B-N11",
                taken="A group policy issued with a loan that the borrower says was issued without his consent.",
                changed="The award concerns a housing loan and discusses no consent record, and the "
                "borrower received the policy terms only after repaying the loan. The scenario uses a "
                "personal loan, puts a signed form on file, and has the officer describe the cover "
                "without asking for agreement.",
                remedy=Remedy.other,
                remedy_note="Insurer directed to pay the difference in one-time premium between the "
                "original term and the term availed. The amount is not printed.",
            ),
            tags=("consent-on-file-customer-unaware", "loan-funded-with-consent"),
        )
    )

    p = _product()
    cases.append(
        BaseCase(
            id="G03",
            title="Record says OTP; the customer says they signed a form and no OTP came",
            target_rule=R.consent,
            scenario_class=VIOLATING,
            record=_record(p, BANK, GOLD_LOAN, 250_000, 1978),
            told="Agreed to the insurance and signed a paper form at the branch. Received no OTP.",
            beliefs=(_informed(p, consent_method=ConsentMethod.signed_form),),
            customer_state=INFORMED,
            yes_no=TRUTHFUL,
            yes_no_basis="Asked only whether they consented, says yes; the method is not asked.",
            gold=_gold(
                FLAGGED,
                "The customer agreed to the insurance but describes a signed form, and the record shows an "
                "OTP: they do not recognise the consent on record. Everything else matches.",
                flags=(R.consent,),
            ),
        )
    )

    p = _product(
        premium_inr=7_500,
        cover_inr=150_000,
        term_months=12,
        cancel_window_days=15,
        consent=_consent(ConsentMethod.digital_click),
    )
    cases.append(
        BaseCase(
            id="G04",
            title="Voluntary add-on accepted in the app, which the customer describes",
            target_rule=R.consent,
            scenario_class=COMPLIANT,
            record=_record(p, NBFC, PERSONAL, 150_000),
            told="Chose the loan insurance in the lender's app and ticked the box for it. Told 15 days to cancel.",
            beliefs=(_informed(p),),
            customer_state=INFORMED,
            yes_no=TRUTHFUL,
            yes_no_basis=ANSWERS_BY_BELIEF,
            gold=_gold(
                CLEAR,
                "Describes accepting the insurance in the app, which is the consent on record. All other "
                "answers match, including the 15-day window.",
            ),
            tags=("loan-funded-with-consent",),
        )
    )

    p = _product(
        premium_inr=18_000, cover_inr=300_000, term_months=36, consent=_consent(ConsentMethod.signed_form)
    )
    cases.append(
        BaseCase(
            id="G05",
            title="Customer agreed to the insurance but cannot say how",
            target_rule=R.consent,
            scenario_class=NEAR_MISS,
            record=_record(p, BANK, PERSONAL, 300_000, 1990),
            told="Agreed to the insurance at the branch. Does not remember what was signed or tapped.",
            beliefs=(_informed(p, consent_method=DONT_KNOW),),
            customer_state=INFORMED,
            yes_no=TRUTHFUL,
            yes_no_basis=ANSWERS_BY_BELIEF,
            gold=_gold(
                UNCLEAR,
                "Says they agreed to both the loan and the insurance but cannot say how. Coordinator "
                "decision 3 of 2026-11-10: that is unclear, for a human, and not a flag.",
                unclear=(R.consent,),
            ),
            tags=("dont-know",),
        )
    )

    p = _product(consent=_consent(ConsentMethod.recorded_call))
    cases.append(
        BaseCase(
            id="G06",
            title="Consent by recorded call, which the customer describes",
            target_rule=R.consent,
            scenario_class=NEAR_MISS,
            record=_record(p, BANK, GOLD_LOAN, 250_000, 1978),
            told="Got a call that said it was being recorded and asked whether they wanted the insurance. Said yes.",
            beliefs=(_informed(p),),
            customer_state=INFORMED,
            yes_no=TRUTHFUL,
            yes_no_basis=ANSWERS_BY_BELIEF,
            gold=_gold(
                CLEAR,
                "Describes saying yes on a recorded phone call, which is the method on record and not a "
                "bare word-of-mouth yes. All other answers match.",
            ),
        )
    )

    # ---- V: bundling (85V / 101V) -------------------------------------------------------------

    p = _product(
        premium_inr=18_000,
        cover_inr=500_000,
        term_months=36,
        required_for_loan=True,
        consent=_consent(ConsentMethod.signed_form),
    )
    cases.append(
        BaseCase(
            id="V01",
            title="Cover required as a risk mitigant, with a choice of provider the customer confirms",
            target_rule=R.bundling,
            scenario_class=NEAR_MISS,
            record=_record(p, BANK, PERSONAL, 500_000),
            told="Told the loan needs a life cover and that a policy from any insurer would do. Chose the "
            "one offered at the branch.",
            beliefs=(_informed(p),),
            customer_state=INFORMED,
            yes_no=TRUTHFUL,
            yes_no_basis=ANSWERS_BY_BELIEF,
            gold=_gold(
                CLEAR,
                "The cover was required for the loan, it is a risk mitigant on the record, and both the "
                "record and the customer say a choice of provider was offered. 85V allows this; it must "
                "not flag. All other answers match.",
            ),
            tags=("risk-mitigant-with-choice",),
        )
    )

    p = _product(
        premium_inr=18_000,
        cover_inr=500_000,
        term_months=36,
        required_for_loan=True,
        provider_choice_offered=False,
        consent=_consent(ConsentMethod.signed_form),
    )
    cases.append(
        BaseCase(
            id="V02",
            title="Cover required as a risk mitigant, no choice of provider on record or in the customer's account",
            target_rule=R.bundling,
            scenario_class=VIOLATING,
            record=_record(p, BANK, PERSONAL, 500_000, 1990),
            told="Told the loan needs this insurance and it has to be this company's.",
            beliefs=(_informed(p),),
            customer_state=INFORMED,
            yes_no=TRUTHFUL,
            yes_no_basis=SCRIPT_COVERS,
            gold=_gold(
                FLAGGED,
                "Required for the loan, and neither the record nor the customer shows a choice of "
                "provider. Everything else matches.",
                flags=(R.bundling,),
            ),
        )
    )

    p = _product(
        premium_inr=18_000,
        cover_inr=500_000,
        term_months=36,
        required_for_loan=True,
        consent=_consent(ConsentMethod.signed_form),
    )
    cases.append(
        BaseCase(
            id="V03",
            title="Record says a choice of provider was offered; the customer says it was not",
            target_rule=R.bundling,
            scenario_class=VIOLATING,
            record=_record(p, NBFC, PERSONAL, 500_000, 1978),
            told="Told the loan needs this insurance. No other company was mentioned.",
            beliefs=(_informed(p, provider_choice_offered=False),),
            customer_state=INFORMED,
            yes_no=TRUTHFUL,
            yes_no_basis=SCRIPT_COVERS,
            gold=_gold(
                FLAGGED,
                "Required for the loan. The record says a choice of provider was offered, but the customer "
                "says none was mentioned: section 6 flags a missing choice per the record or the customer.",
                flags=(R.bundling,),
            ),
        )
    )

    p = _product(
        premium_inr=100_000,
        cover_inr=1_000_000,
        term_months=60,
        paid_from_loan=False,
        required_for_loan=True,
        risk_mitigant=False,
        provider_choice_offered=False,
        features=REGULAR_PREMIUM,
        consent=_consent(ConsentMethod.signed_form),
    )
    cases.append(
        BaseCase(
            id="V04",
            title="Savings policy required for the loan and described as a security deposit",
            target_rule=R.bundling,
            scenario_class=VIOLATING,
            record=_record(p, BANK, PERSONAL, 1_000_000),
            told="Told to pay one lakh as a security deposit for the loan facility, to be paid back after "
            "one year. Signed several forms for it.",
            beliefs=(
                _informed(
                    p,
                    kind=DEPOSIT,
                    deposit_word=DepositWord.security_deposit,
                    cover_inr=DONT_KNOW,
                    term_months=12,
                    cancel_allowed=False,
                    cancel_window_days=None,
                    money_back=(IS_DEPOSIT, AFTER_PERIOD),
                    money_back_period_months=12,
                ),
            ),
            customer_state=MISLED,
            yes_no=TRUTHFUL,
            yes_no_basis="Asked whether they took an insurance policy, says it was a security deposit.",
            gold=_gold(
                FLAGGED,
                "A savings-type policy the record marks as required and not a risk mitigant, with no "
                "choice of provider: bundling, on the record alone. The customer calls it a security "
                "deposit (kind) that comes back after a year (belief_mismatch), gives one year for a "
                "five-year term, does not know the cover, and was not told about cancelling. The customer "
                "recognises signing for this purchase, so consent is not flagged. The record's product "
                "kind reads credit_life only because the type has one kind in v1.",
                flags=(R.bundling, R.kind, R.belief_mismatch, R.cover, R.term, R.cancel_window),
            ),
            template=Template(
                case="BNG-L-033-1617-0600",
                ledger="B5",
                taken="Rs 1,00,000 paid for a policy 'as a requirement of a security deposit' for a bank "
                "facility, with a promise that it would be paid back after one year.",
                changed="The award concerns an overdraft; the scenario uses a personal loan. The cover, "
                "term and call answers are ours. The award discusses no verification call.",
                remedy=Remedy.conversion,
                remedy_note="Policy converted into a one-time-premium policy for the minimum term. No refund.",
            ),
            tags=("sold-as-security-deposit",),
        )
    )

    p = _product(
        premium_inr=3_500, cover_inr=125_000, term_months=12, consent=_consent(ConsentMethod.signed_form)
    )
    cases.append(
        BaseCase(
            id="V05",
            title="Voluntary cover; the customer says the officer only suggested it",
            target_rule=R.bundling,
            scenario_class=NEAR_MISS,
            record=_record(p, NBFC, GOLD_LOAN, 125_000, 1990),
            told="The officer said the cover is optional and a good idea. Agreed and signed the form.",
            beliefs=(_informed(p, required_said_softly=True),),
            customer_state=INFORMED,
            yes_no=TRUTHFUL,
            yes_no_basis=ANSWERS_BY_BELIEF,
            gold=_gold(
                CLEAR,
                "Not required per the record, and the customer says it was a suggestion, not a condition. "
                "A voluntary product is not bundling. All other answers match.",
            ),
        )
    )

    p = _product(
        premium_inr=100_000,
        cover_inr=1_000_000,
        term_months=60,
        paid_from_loan=False,
        features=REGULAR_PREMIUM,
    )
    cases.append(
        BaseCase(
            id="V06",
            title="Record says voluntary; the customer says an FD was demanded to get the loan",
            target_rule=R.bundling,
            scenario_class=VIOLATING,
            record=_record(p, NBFC, PERSONAL, 1_000_000, 1978),
            told="Told to deposit one lakh as a fixed deposit, or the loan would not be sanctioned. Gave "
            "an OTP 'for the FD'.",
            beliefs=(
                _informed(
                    p,
                    kind=DEPOSIT,
                    deposit_word=DepositWord.fd,
                    required_for_loan=True,
                    provider_choice_offered=False,
                    cover_inr=DONT_KNOW,
                    cancel_allowed=False,
                    cancel_window_days=None,
                    money_back=(IS_DEPOSIT, ANYTIME),
                ),
            ),
            customer_state=MISLED,
            yes_no=TRUTHFUL,
            yes_no_basis="Asked whether they took an insurance policy, says they made an FD.",
            gold=_gold(
                FLAGGED,
                "The record shows a voluntary product with a choice of provider, but the customer says it "
                "was demanded for the loan and no other provider was mentioned: section 6 takes 'required' "
                "and 'no choice' from the record or the customer (bundling). They call it an FD (kind) "
                "that can be broken at any time (belief_mismatch), do not know the cover, and were not "
                "told about cancelling. The five-year term they give matches. They recognise giving an "
                "OTP for this purchase, so consent is not flagged.",
                flags=(R.bundling, R.kind, R.belief_mismatch, R.cover, R.cancel_window),
            ),
            template=Template(
                case="BHP-L-013-1617-0436",
                ledger="B-N9",
                taken="A housing-finance applicant asked to 'deposit Rs 1.00 lac as an Fixed Deposit to "
                "get the housing loan'; a policy was issued.",
                changed="The award concerns a housing loan from a housing-finance company; the scenario "
                "uses an NBFC personal loan (HFCs follow the NBFC paragraphs). The lender's record and the "
                "call answers are ours.",
                remedy=Remedy.conversion,
                remedy_note="Policy converted to a single-premium policy from the date of application. No refund.",
            ),
            tags=("sold-as-fd",),
        )
    )

    # ---- W: premium funded from the loan (85W / 101W) -----------------------------------------

    p = _product(consent=None)
    cases.append(
        BaseCase(
            id="W01",
            title="Premium deducted from the loan with no consent on record; the customer is informed",
            target_rule=R.loan_funded,
            scenario_class=VIOLATING,
            record=_record(p, BANK, GOLD_LOAN, 250_000),
            told="Told everything correctly and said yes across the desk. Nothing was signed or tapped for the insurance.",
            beliefs=(_informed(p, consent_given=True, consent_method=ConsentMethod.verbal),),
            customer_state=INFORMED,
            yes_no=TRUTHFUL,
            yes_no_basis=ANSWERS_BY_BELIEF,
            gold=_gold(
                FLAGGED,
                "The premium came out of the loan and the record holds no consent: loan_funded and consent "
                "both flag on the record alone, whatever the customer says. The customer understands the "
                "product and says they agreed by word of mouth.",
                flags=(R.loan_funded, R.consent),
            ),
            tags=("loan-funded-without-consent",),
        )
    )

    p = _product(premium_inr=18_000, cover_inr=300_000, term_months=36)
    cases.append(
        BaseCase(
            id="W02",
            title="Premium deducted from the loan; the customer believes they paid it separately",
            target_rule=R.loan_funded,
            scenario_class=VIOLATING,
            record=_record(p, NBFC, PERSONAL, 300_000, 1990),
            told="Agreed to the insurance by OTP. Believes the premium was among the fees paid at the "
            "counter and that the full loan amount was credited.",
            beliefs=(_informed(p, payment_source=SEPARATELY),),
            customer_state=MISLED,
            yes_no=TRUTHFUL,
            yes_no_basis="Told the premium was deducted from the loan, says no, it was paid separately.",
            gold=_gold(
                FLAGGED,
                "The record shows the premium taken from the loan and the customer says it was paid "
                "separately. Consent is on record and recognised. Everything else matches.",
                flags=(R.loan_funded,),
            ),
        )
    )

    p = _product()
    cases.append(
        BaseCase(
            id="W03",
            title="Premium deducted from the loan; the customer does not know how it was paid",
            target_rule=R.loan_funded,
            scenario_class=VIOLATING,
            record=_record(p, BANK, GOLD_LOAN, 250_000, 1978),
            told="Agreed to the insurance by OTP. Nobody said where the premium would come from.",
            beliefs=(_informed(p, payment_source=DONT_KNOW),),
            customer_state=UNAWARE,
            yes_no=TRUTHFUL,
            yes_no_basis="Cannot confirm how the premium was paid.",
            gold=_gold(
                FLAGGED,
                "The record shows the premium taken from the loan and the customer does not know how it "
                "was paid: section 6 flags 'paid separately / didn't know'. Everything else matches.",
                flags=(R.loan_funded,),
            ),
            tags=("dont-know",),
        )
    )

    p = _product(
        premium_inr=3_500, cover_inr=125_000, term_months=12, consent=_consent(ConsentMethod.signed_form)
    )
    cases.append(
        BaseCase(
            id="W04",
            title="Premium deducted from the loan with a signed consent the customer describes",
            target_rule=R.loan_funded,
            scenario_class=COMPLIANT,
            record=_record(p, NBFC, GOLD_LOAN, 125_000),
            told="Told the premium of 3,500 would be taken out of the loan. Signed the insurance form.",
            beliefs=(_informed(p),),
            customer_state=INFORMED,
            yes_no=TRUTHFUL,
            yes_no_basis=ANSWERS_BY_BELIEF,
            gold=_gold(
                CLEAR,
                "Funded from the loan with a signed consent on record, and the customer knows both. All "
                "other answers match.",
            ),
            tags=("loan-funded-with-consent",),
        )
    )

    p = _product(
        premium_inr=7_500, cover_inr=175_000, paid_from_loan=False, cancel_window_days=None
    )
    cases.append(
        BaseCase(
            id="W05",
            title="Premium paid separately; no cancellation window on record and none was mentioned",
            target_rule=R.loan_funded,
            scenario_class=COMPLIANT,
            record=_record(p, BANK, PERSONAL, 175_000, 1990),
            told="Paid the premium from their own account. Nothing was said about cancelling.",
            beliefs=(_informed(p),),
            customer_state=INFORMED,
            yes_no=TRUTHFUL,
            yes_no_basis=ANSWERS_BY_BELIEF,
            gold=_gold(
                CLEAR,
                "Paid separately, as the record says. The record shows no cancellation window and the "
                "customer says none was mentioned, which is consistent. All other answers match.",
            ),
        )
    )

    p = _product(premium_inr=7_500, cover_inr=175_000, paid_from_loan=False)
    cases.append(
        BaseCase(
            id="W06",
            title="Premium paid separately on record; the customer does not know how it was paid",
            target_rule=R.loan_funded,
            scenario_class=NEAR_MISS,
            record=_record(p, BANK, PERSONAL, 175_000, 1978),
            told="A relative handled the payment at the branch.",
            beliefs=(_informed(p, payment_source=DONT_KNOW),),
            customer_state=UNAWARE,
            yes_no=TRUTHFUL,
            yes_no_basis="Cannot confirm how the premium was paid.",
            gold=_gold(
                UNCLEAR,
                "The record says the premium was paid separately, so the loan_funded flag has no ground. "
                "The customer cannot say how it was paid, so the answer cannot be compared: unclear, for a "
                "human, not a flag.",
                unclear=(R.loan_funded,),
            ),
            tags=("dont-know",),
        )
    )

    # ---- B: belief contradicts the product (4(20A)(ii) / 6(9A)(ii)) ---------------------------

    p = _product(premium_inr=52_000, cover_inr=500_000, term_months=36)
    cases.append(
        BaseCase(
            id="B01",
            title="Knows it is a policy; believes the money can be withdrawn after one year",
            target_rule=R.belief_mismatch,
            scenario_class=VIOLATING,
            record=_record(p, BANK, PERSONAL, 500_000),
            told="The banker said the policy could be cancelled and the money withdrawn any time after one year.",
            beliefs=(
                _informed(
                    p,
                    cancel_allowed=False,
                    cancel_window_days=None,
                    money_back=(AFTER_PERIOD,),
                    money_back_period_months=12,
                ),
            ),
            customer_state=MISLED,
            yes_no=TRUTHFUL,
            yes_no_basis="Confirms taking the policy and its terms. In the award the insurer submitted a "
            "recorded call to show the complainant had confirmed the policy. The script does not ask what "
            "happens to the money.",
            gold=_gold(
                FLAGGED,
                "Kind, premium, payment and consent match. At the money-back probe the customer says the "
                "money can be withdrawn after a year, which is not a feature of the product "
                "(belief_mismatch). Asked about cancelling, they say no window was mentioned, and the "
                "record shows 30 days (cancel_window).",
                flags=(R.belief_mismatch, R.cancel_window),
            ),
            template=Template(
                case="BNG-L-041-1617-0797",
                ledger="B2",
                taken="The banker assured the customer the policy could be cancelled and the money "
                "withdrawn after one year; the insurer's recorded call showed the customer confirming the policy.",
                changed="The award is not about a loan; the scenario attaches the same belief to a "
                "credit-life cover sold with a personal loan.",
                remedy=Remedy.conversion,
                remedy_note="Premium put into a one-time-premium policy for the minimum period. No refund.",
            ),
        )
    )

    p = _product(premium_inr=25_000, cover_inr=300_000, term_months=36)
    cases.append(
        BaseCase(
            id="B02",
            title="Knows it is insurance; believes the premium comes back grown, guaranteed",
            target_rule=R.belief_mismatch,
            scenario_class=VIOLATING,
            record=_record(p, NBFC, PERSONAL, 300_000, 1990),
            told="Told it is insurance for the loan and that after three years the money comes back with "
            "a guaranteed gain.",
            beliefs=(_informed(p, money_back=(GUARANTEED,)),),
            customer_state=MISLED,
            yes_no=TRUTHFUL,
            yes_no_basis=SCRIPT_COVERS,
            gold=_gold(
                FLAGGED,
                "Every recorded fact is answered correctly. At the money-back probe the customer says the "
                "money returns grown and guaranteed, which a pure credit-life cover does not do.",
                flags=(R.belief_mismatch,),
            ),
            template=Template(
                case="PUN-L-036-1617-0228",
                ledger="B-N2",
                taken="A recorded call that was clear on the policy terms while the benefit the customer "
                "expected was never explained.",
                changed="The award's promised money-back figures are replaced by a belief in a guaranteed "
                "return on a credit-life cover sold with a loan.",
                remedy=Remedy.refund,
                remedy_note="Premium refunded by cancelling the policy. The refunded sum is not printed.",
            ),
        )
    )

    p = _product(premium_inr=52_000, cover_inr=500_000, term_months=36, features=REGULAR_PREMIUM)
    cases.append(
        BaseCase(
            id="B03",
            title="Believes the premium is paid only once; the record shows a regular-premium product",
            target_rule=R.belief_mismatch,
            scenario_class=VIOLATING,
            record=_record(p, BANK, GOLD_LOAN, 500_000, 1978),
            told="Told it is a single-premium policy: pay 52,000 once and nothing after.",
            beliefs=(_informed(p, one_time_claim=True),),
            customer_state=MISLED,
            yes_no=TRUTHFUL,
            yes_no_basis=SCRIPT_COVERS,
            gold=_gold(
                FLAGGED,
                "At the premium question the customer adds that it is paid only once. The record does not "
                "list one-time payment among the product's features, so the claim contradicts the product. "
                "The amount itself and every other answer match.",
                flags=(R.belief_mismatch,),
            ),
            template=Template(
                case="BHP-L-021-1617-0456",
                ledger="B-N10",
                taken="A regular-premium policy issued 'on pretext of single premium policy like FD for 5 years'.",
                changed="The award is not about a loan; the scenario keeps the one-time-payment belief and "
                "drops the FD comparison.",
                remedy=Remedy.conversion,
                remedy_note="Policy converted to a single-premium policy; the insurer agreed at the hearing.",
            ),
        )
    )

    p = _product()
    cases.append(
        BaseCase(
            id="B04",
            title="Says the money does not come back, except by cancelling inside the window",
            target_rule=R.belief_mismatch,
            scenario_class=NEAR_MISS,
            record=_record(p, BANK, GOLD_LOAN, 250_000),
            told="Told it is pure insurance with a 30-day cancellation window.",
            beliefs=(_informed(p, money_back_mentions_window=True),),
            customer_state=INFORMED,
            yes_no=TRUTHFUL,
            yes_no_basis=ANSWERS_BY_BELIEF,
            gold=_gold(
                CLEAR,
                "The customer mentions getting money back, but only by cancelling within the 30 days on "
                "record. That is the cancellation window, not a claim that the money is refundable. No "
                "belief contradicts the product.",
            ),
        )
    )

    # ---- C: customers told how to answer the verification call --------------------------------

    p = _product(premium_inr=25_000, cover_inr=300_000, term_months=36, consent=None)
    cases.append(
        BaseCase(
            id="C01",
            title="Coached to say yes; believes it is an FD and tells the bot about the coaching",
            target_rule=R.sale_conduct,
            scenario_class=VIOLATING,
            record=_record(p, NBFC, PERSONAL, 300_000),
            told="Told 25,000 would sit in an FD needed for the loan, and that a verification call would "
            "come and every answer should be yes.",
            beliefs=(
                _informed(
                    p,
                    kind=DEPOSIT,
                    deposit_word=DepositWord.fd,
                    required_for_loan=True,
                    provider_choice_offered=False,
                    cover_inr=DONT_KNOW,
                    term_months=DONT_KNOW,
                    cancel_allowed=False,
                    cancel_window_days=None,
                    money_back=(IS_DEPOSIT, ANYTIME),
                    consent_given=True,
                    consent_method=ConsentMethod.signed_form,
                ),
            ),
            concerns=(SaleConcern.coached_answers,),
            customer_state=MISLED,
            yes_no=COACHED,
            yes_no_basis="Told to answer the verification call 'in positive' (the complainant's account in the award).",
            gold=_gold(
                FLAGGED,
                "The customer says the agent told them to answer yes to everything: a sale-conduct concern "
                "at case level. Open questions still bring out the belief: an FD (kind) that can be broken "
                "at any time (belief_mismatch), needed for the loan with no other provider mentioned "
                "(bundling). The record holds no consent and the premium came from the loan (consent, "
                "loan_funded). Cover and term unknown; not told about cancelling.",
                flags=(
                    R.kind,
                    R.belief_mismatch,
                    R.bundling,
                    R.consent,
                    R.loan_funded,
                    R.cover,
                    R.term,
                    R.cancel_window,
                ),
                case_flags=(R.sale_conduct,),
            ),
            template=Template(
                case="AHD-L-001-1617-0203",
                ledger="B4",
                taken="The complainant's account that she was told 'there would be a verification call and "
                "in reply she had to answer everything in positive'.",
                changed="The award is a loan-bait sale by telephone and records no verification-call "
                "recording. The scenario attaches the coaching to a cover sold with a loan as an FD.",
                remedy=Remedy.refund,
                remedy_note="Complaint allowed for Rs 50,000 plus 12% interest.",
            ),
            tags=("coached", "sold-as-fd", "loan-funded-without-consent"),
        )
    )

    p = _product(
        premium_inr=100_000,
        cover_inr=1_000_000,
        term_months=60,
        paid_from_loan=False,
        features=REGULAR_PREMIUM,
        consent=_consent(ConsentMethod.signed_form),
    )
    cases.append(
        BaseCase(
            id="C02",
            title="Coached to say yes; believes it is a security for the loan and does not mention the coaching",
            target_rule=R.kind,
            scenario_class=VIOLATING,
            record=_record(p, BANK, PERSONAL, 1_000_000, 1990),
            told="Told one lakh was a security to obtain the loan, returned when the five years are up, "
            "and guided on how to answer the verification call.",
            beliefs=(
                _informed(
                    p,
                    kind=DEPOSIT,
                    deposit_word=DepositWord.security_deposit,
                    required_for_loan=True,
                    provider_choice_offered=False,
                    cover_inr=DONT_KNOW,
                    cancel_allowed=False,
                    cancel_window_days=None,
                    money_back=(IS_DEPOSIT, AFTER_PERIOD),
                    money_back_period_months=60,
                ),
            ),
            customer_state=MISLED,
            yes_no=COACHED,
            yes_no_basis="'Responded as was guided' (the Ombudsman's observation in the award).",
            gold=_gold(
                FLAGGED,
                "The customer never mentions the coaching, so there is no sale-conduct flag. The open "
                "questions bring out the belief anyway: a security deposit (kind) returned after five "
                "years (belief_mismatch), needed for the loan with no other provider mentioned (bundling, "
                "on the customer's account; the record says voluntary). Cover unknown; not told about "
                "cancelling. The five-year term matches, and the customer recognises signing for this "
                "purchase.",
                flags=(R.kind, R.belief_mismatch, R.bundling, R.cover, R.cancel_window),
            ),
            template=Template(
                case="CHD-L-019-1718-1436",
                ledger="B-N6",
                taken="A policy sold 'as a security to obtain a loan'; on the verification call the "
                "customer 'responded as was guided'.",
                changed="In the award the promised loan never came; in the scenario the loan exists. The "
                "premium, cover and term are ours.",
                remedy=Remedy.refund,
                remedy_note="Policy cancelled from inception and premiums refunded without interest or deduction.",
            ),
            tags=("coached", "sold-as-security-deposit"),
        )
    )

    p = _product()
    cases.append(
        BaseCase(
            id="C03",
            title="Coached to say yes; answers every open question with 'yes, all fine'",
            target_rule=R.recall,
            scenario_class=VIOLATING,
            record=_record(p, BANK, GOLD_LOAN, 250_000, 1978),
            told="Told a verification call would come and to agree to all the terms. Believes the premium "
            "comes back in full after two years.",
            beliefs=(
                ProductBelief(
                    product_id=P1,
                    recall=Recall.evasive,
                    kind=EVASIVE,
                    premium_inr=EVASIVE,
                    payment_source=EVASIVE,
                    required_for_loan=EVASIVE,
                    provider_choice_offered=None,
                    cover_inr=EVASIVE,
                    term_months=EVASIVE,
                    cancel_allowed=EVASIVE,
                    money_back=EVASIVE,
                    consent_given=EVASIVE,
                    consent_method=None,
                ),
            ),
            customer_state=MISLED,
            yes_no=COACHED,
            yes_no_basis="'Instructed to agree to all the terms and conditions during the verification "
            "calls' (the complainant's account in the award).",
            gold=_gold(
                FLAGGED,
                "The customer answers the open questions with 'yes, all fine' and deflects the ones a yes "
                "could answer with 'whatever the bank did'. They name no product in open recall (recall, "
                "low severity) and give no usable answer to any teach-back question, so every other rule "
                "is unclear. The case goes to a human; it is never clear.",
                flags=(R.recall,),
                unclear=(
                    R.kind,
                    R.premium,
                    R.cover,
                    R.term,
                    R.cancel_window,
                    R.consent,
                    R.loan_funded,
                    R.bundling,
                    R.belief_mismatch,
                ),
            ),
            template=Template(
                case="PUN-L-009-1617-0009",
                ledger="B-N17",
                taken="The complainant's account that he was 'instructed to agree to all the terms and "
                "conditions during the verification calls'; the insurer's recording showed no concerns raised.",
                changed="The award is not about a loan. The scenario shows a coached customer who stays "
                "on the yes script when asked open questions.",
                remedy=Remedy.partial_refund,
                remedy_note="Relief on one of three policies only: cancel and refund Rs 29,100.",
            ),
            tags=("coached",),
        )
    )

    # ---- R: unprompted recall -----------------------------------------------------------------

    p = _product(
        premium_inr=18_000, cover_inr=300_000, term_months=18, consent=_consent(ConsentMethod.signed_form)
    )
    cases.append(
        BaseCase(
            id="R01",
            title="Informed customer who does not mention the insurance until asked about it",
            target_rule=R.recall,
            scenario_class=VIOLATING,
            record=_record(p, BANK, PERSONAL, 300_000),
            told="Told everything correctly. Thinks of the insurance as part of the loan.",
            beliefs=(_informed(p, recall=Recall.not_named),),
            customer_state=INFORMED,
            yes_no=TRUTHFUL,
            yes_no_basis=ANSWERS_BY_BELIEF,
            gold=_gold(
                FLAGGED,
                "Asked what they took with the loan, the customer says only the loan. Coordinator decision "
                "2 of 2026-11-10: a product on record that is not named in open recall is a low-severity "
                "flag. Every prompted answer matches the record, so this is the only flag.",
                flags=(R.recall,),
            ),
            tags=("low-severity-only", "flag-on-informed-customer"),
        )
    )

    return tuple(cases)


BASE_CASES: tuple[BaseCase, ...] = _cases()
