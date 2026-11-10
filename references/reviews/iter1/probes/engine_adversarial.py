"""Verifier probe: fresh adversarial Beliefs against the rule engine. Pure, no network.

    uv run python references/reviews/iter1/probes/engine_adversarial.py

Each case starts from a customer who answers every question exactly as the record has it
(verdict must be `clear`) and changes one or two things. `want` is the verifier's reading of
DESIGN.md section 6, written before running. A row marked FALSE CLEAR / FALSE FLAG is a
disagreement between the engine and that reading.
"""

from datetime import date

from samajh.rules import evaluate
from samajh.types import (
    Beliefs,
    Borrower,
    ClaimEvidence,
    ConcernEvidence,
    Consent,
    ConsentMethod,
    DontKnow,
    Evidence,
    FeatureClaim,
    KindClaim,
    Language,
    LoanRecord,
    NotAsked,
    OpenRecall,
    PaymentSource,
    Product,
    ProductBeliefs,
    RecallItem,
    SaleConcern,
    Stated,
    Unclear,
)

EV = Evidence(quote="x", turn_id=1)


def st(value):
    return Stated(value=value, evidence=EV)


DK = DontKnow(evidence=EV)
UN = Unclear()
NA = NotAsked()


def product(pid="P1", **over) -> Product:
    base = dict(
        id=pid, kind="credit_life", provider="Nakli Life", premium_inr=41300, cover_inr=350000,
        term_months=36, paid_from_loan=True, required_for_loan=False, risk_mitigant=True,
        provider_choice_offered=True, cancel_window_days=30, features=frozenset(),
        consent=Consent(method=ConsentMethod.otp, at=date(2026, 10, 1)),
    )
    return Product(**{**base, **over})


def record(*products: Product) -> LoanRecord:
    return LoanRecord(
        loan_id="L-FAKE-0001", lender_type="bank",
        borrower=Borrower(name="Nakli Naam", dob=date(1990, 1, 1), language=Language.hi),
        loan_kind="personal", sanctioned_inr=350000, disbursed_inr=308700, disbursed_on=date(2026, 10, 1),
        products=products or (product(),),
    )


def informed(p: Product, **over) -> ProductBeliefs:
    base = dict(
        product_id=p.id, kind=st(KindClaim.insurance), premium_inr=st(p.premium_inr), premium_readback=st(True),
        payment_source=st(PaymentSource.from_loan if p.paid_from_loan else PaymentSource.separately),
        required_for_loan=st(p.required_for_loan), provider_choice_offered=st(p.provider_choice_offered),
        cover_inr=st(p.cover_inr), term_months=st(p.term_months),
        cancel_allowed=st(p.cancel_window_days is not None),
        cancel_window_days=st(p.cancel_window_days) if p.cancel_window_days else NA,
        consent_given=st(True), consent_method=st(p.consent.method) if p.consent else NA,
        feature_probe=st(()),
    )
    return ProductBeliefs(**{**base, **over})


def named(p: Product, kind=KindClaim.insurance, amount=None) -> RecallItem:
    return RecallItem(evidence=EV, kind=kind, amount_inr=amount, product_id=p.id)


def beliefs(rec: LoanRecord, products, items=None, asked=True, concerns=(), ungrounded=()) -> Beliefs:
    if items is None:
        items = tuple(named(p) for p in rec.products)
    return Beliefs(
        call_id="c", loan_id=rec.loan_id, language=Language.hi,
        recall=OpenRecall(asked=asked, answer=EV if asked else None, items=tuple(items)),
        products=tuple(products), sale_concerns=tuple(concerns), ungrounded=tuple(ungrounded),
    )


CASES = []


def case(group, name, want, rec, b):
    CASES.append((group, name, want, rec, b))


P = product()
R = record(P)

# --- baseline -------------------------------------------------------------------------------
case("base", "informed customer, clean record", "clear", R, beliefs(R, [informed(P)]))

# --- missing answers ------------------------------------------------------------------------
for field in ("kind", "premium_inr", "premium_readback", "payment_source", "required_for_loan",
              "cover_inr", "term_months", "cancel_allowed", "cancel_window_days", "consent_given",
              "consent_method", "feature_probe"):
    for label, value in (("not asked", NA), ("unclear", UN)):
        want = "unclear_needs_human"
        items = None
        if field == "kind":
            items = ()  # with no recall naming either, nothing says what the customer thinks it is
            want = "flag_for_review"  # recall low flag (not named)
        case("missing", f"{field} {label}" + (" and not named in recall" if field == "kind" else ""),
             want, R, beliefs(R, [informed(P, **{field: value})], items=items))
case("missing", "kind not asked, but named correctly in open recall", "clear", R,
     beliefs(R, [informed(P, kind=NA)]))
case("missing", "kind asked and unclear, though named correctly in recall", "unclear_needs_human", R,
     beliefs(R, [informed(P, kind=UN)]))
case("missing", "open recall never asked", "unclear_needs_human", R, beliefs(R, [informed(P)], items=(), asked=False))
case("missing", "provider_choice not asked (product not required, customer agrees)", "clear", R,
     beliefs(R, [informed(P, provider_choice_offered=NA)]))
case("missing", "beliefs carry no entry for the product at all", "unclear_needs_human", R, beliefs(R, []))

# --- don't-knows ----------------------------------------------------------------------------
for field, want in (("kind", "flag_for_review"), ("premium_inr", "flag_for_review"), ("cover_inr", "flag_for_review"),
                    ("term_months", "flag_for_review"), ("cancel_allowed", "flag_for_review"),
                    ("cancel_window_days", "flag_for_review"), ("consent_given", "flag_for_review"),
                    ("consent_method", "unclear_needs_human"), ("payment_source", "flag_for_review"),
                    ("required_for_loan", "unclear_needs_human"), ("feature_probe", "flag_for_review"),
                    ("premium_readback", "unclear_needs_human")):
    case("dont_know", f"{field} = I don't know", want, R, beliefs(R, [informed(P, **{field: DK})]))
P_sep = product(paid_from_loan=False)
case("dont_know", "paid separately on record, customer does not know how it was paid", "unclear_needs_human",
     record(P_sep), beliefs(record(P_sep), [informed(P_sep, payment_source=DK)]))
P_nowin = product(cancel_window_days=None)
case("dont_know", "no cancel window on record, customer does not know if cancellable", "clear",
     record(P_nowin), beliefs(record(P_nowin), [informed(P_nowin, cancel_allowed=DK)]))
P_req = product(required_for_loan=True)
case("dont_know", "required mitigant with choice on record; customer does not know if told of choice",
     "unclear_needs_human", record(P_req), beliefs(record(P_req), [informed(P_req, provider_choice_offered=DK)]))
case("dont_know", "every answer is I don't know", "flag_for_review", R,
     beliefs(R, [ProductBeliefs(product_id="P1", **{f: DK for f in (
         "kind", "premium_inr", "payment_source", "required_for_loan", "provider_choice_offered", "cover_inr",
         "term_months", "cancel_allowed", "consent_given", "feature_probe")})], items=()))

# --- contradictions -------------------------------------------------------------------------
case("contradiction", "kind question: insurance; open recall called the same product an FD", "flag_for_review", R,
     beliefs(R, [informed(P)], items=[named(P, KindClaim.deposit)]))
case("contradiction", "money-back probe: no claims; but volunteered 'can take it back any time' earlier",
     "flag_for_review", R,
     beliefs(R, [informed(P, volunteered_claims=(ClaimEvidence(claim=FeatureClaim.refundable_anytime, evidence=EV),))]))
case("contradiction", "premium right and confirmed; open recall gave a very different amount for it (20,000)",
     "flag_for_review", R, beliefs(R, [informed(P)], items=[named(P, amount=20000)]))
case("contradiction", "says they agreed by OTP (matches record) and also says they were told what to answer",
     "flag_for_review", R,
     beliefs(R, [informed(P)], concerns=[ConcernEvidence(concern=SaleConcern.coached_answers, evidence=EV)]))
case("contradiction", "told they can cancel = no, yet gives the right 30-day window", "flag_for_review", R,
     beliefs(R, [informed(P, cancel_allowed=st(False))]))
case("contradiction", "premium stated right, read-back answered 'no, wrong'", "unclear_needs_human", R,
     beliefs(R, [informed(P, premium_readback=st(False))]))
case("contradiction", "premium stated WRONG (30,000), read-back answered 'no, wrong'", "unclear_needs_human", R,
     beliefs(R, [informed(P, premium_inr=st(30000), premium_readback=st(False))]))
case("contradiction", "premium stated wrong (30,000) and never read back", "flag_for_review", R,
     beliefs(R, [informed(P, premium_inr=st(30000), premium_readback=NA)]))
case("contradiction", "customer says not required; record says required (mitigant, choice offered and confirmed)",
     "clear", record(P_req), beliefs(record(P_req), [informed(P_req, required_for_loan=st(False))]))
case("contradiction", "record says NOT required; customer says they were told it was compulsory (mitigant, choice confirmed)",
     "flag_for_review", R, beliefs(R, [informed(P, required_for_loan=st(True))]))

# --- consent on file, unaware customer ------------------------------------------------------
case("consent", "consent on file; customer says they agreed only to the loan", "flag_for_review", R,
     beliefs(R, [informed(P, consent_given=st(False), consent_method=UN)]))
case("consent", "consent on file (OTP); customer says they signed a form", "flag_for_review", R,
     beliefs(R, [informed(P, consent_method=st(ConsentMethod.signed_form))]))
case("consent", "consent on file; consent question never asked", "unclear_needs_human", R,
     beliefs(R, [informed(P, consent_given=NA, consent_method=NA)]))
case("consent", "consent on file; customer recognises it but does not know what the product is", "flag_for_review", R,
     beliefs(R, [informed(P, kind=DK)], items=()))
case("consent", "consent on file and matched; customer 'learned of the product only after the sale'",
     "flag_for_review", R,
     beliefs(R, [informed(P)], concerns=[ConcernEvidence(concern=SaleConcern.learned_after_sale, evidence=EV)]))
P_nc = product(consent=None, paid_from_loan=False)
case("consent", "no consent on record, paid separately, customer fully informed", "flag_for_review",
     record(P_nc), beliefs(record(P_nc), [informed(P_nc, consent_method=st(ConsentMethod.otp))]))

# --- required-but-risk-mitigant -------------------------------------------------------------
case("bundling", "required, mitigant, choice offered; customer confirms both", "clear", record(P_req),
     beliefs(record(P_req), [informed(P_req)]))
case("bundling", "required, mitigant, choice on record; customer says nobody told them of a choice",
     "flag_for_review", record(P_req), beliefs(record(P_req), [informed(P_req, provider_choice_offered=st(False))]))
case("bundling", "required, mitigant, choice on record; choice question never asked", "unclear_needs_human",
     record(P_req), beliefs(record(P_req), [informed(P_req, provider_choice_offered=NA)]))
case("bundling", "required, mitigant, choice on record; 'was it required' never asked, choice confirmed",
     "unclear_needs_human", record(P_req), beliefs(record(P_req), [informed(P_req, required_for_loan=NA)]))
case("bundling", "required, mitigant, choice on record; customer calls it a security deposit (volunteered)",
     "flag_for_review", record(P_req),
     beliefs(record(P_req), [informed(P_req, volunteered_claims=(ClaimEvidence(claim=FeatureClaim.is_deposit, evidence=EV),))]))
P_req_nochoice = product(required_for_loan=True, provider_choice_offered=False)
case("bundling", "required, mitigant, NO choice on record; customer (wrongly) says they were told of a choice",
     "flag_for_review", record(P_req_nochoice),
     beliefs(record(P_req_nochoice), [informed(P_req_nochoice, provider_choice_offered=st(True))]))
P_req_notmit = product(required_for_loan=True, risk_mitigant=False)
case("bundling", "required and not a risk mitigant on record; customer happy with everything", "flag_for_review",
     record(P_req_notmit), beliefs(record(P_req_notmit), [informed(P_req_notmit)]))
P_notmit = product(risk_mitigant=False)
case("bundling", "not required, not a mitigant on record; customer says it was compulsory", "flag_for_review",
     record(P_notmit), beliefs(record(P_notmit), [informed(P_notmit, required_for_loan=st(True))]))

# --- multi-product: one clean product must not launder the other ----------------------------
P2 = product("P2", premium_inr=18000, cover_inr=200000)
R2 = record(P, P2)
case("multi", "two products, both fully and rightly answered", "clear", R2,
     beliefs(R2, [informed(P), informed(P2)]))
case("multi", "P1 clean; P2 never covered by the call (no beliefs, not named)", "flag_for_review", R2,
     beliefs(R2, [informed(P)], items=[named(P)]))
case("multi", "P1 clean; P2 answered but called an FD", "flag_for_review", R2,
     beliefs(R2, [informed(P), informed(P2, kind=st(KindClaim.deposit))]))
case("multi", "P1 clean; P2 answers all present but money-back probe missing", "unclear_needs_human", R2,
     beliefs(R2, [informed(P), informed(P2, feature_probe=NA)]))
case("multi", "P1 clean; P2 answered right but customer named only one insurance in recall", "flag_for_review", R2,
     beliefs(R2, [informed(P), informed(P2)], items=[named(P)]))
case("multi", "P1 clean; P2 consent not recognised", "flag_for_review", R2,
     beliefs(R2, [informed(P), informed(P2, consent_given=st(False), consent_method=UN)]))
case("multi", "both answered right; customer also names an FD that is on no record", "flag_for_review", R2,
     beliefs(R2, [informed(P), informed(P2)],
             items=[named(P), named(P2), RecallItem(evidence=EV, kind=KindClaim.deposit)]))
case("multi", "both answered right; customer names a third thing extraction could not classify",
     "unclear_needs_human", R2,
     beliefs(R2, [informed(P), informed(P2)], items=[named(P), named(P2), RecallItem(evidence=EV, kind=None)]))
# P2's premium answer equals P1's premium (customer mixes them up)
case("multi", "customer gives P1's premium for P2 and confirms it", "flag_for_review", R2,
     beliefs(R2, [informed(P), informed(P2, premium_inr=st(P.premium_inr))]))

# --- read-back never confirmed --------------------------------------------------------------
for label, rb in (("never read back", NA), ("read back, reply unusable", UN), ("read back, 'I don't know'", DK),
                  ("read back, rejected", st(False))):
    case("readback", f"premium matches the record; {label}", "unclear_needs_human", R,
         beliefs(R, [informed(P, premium_readback=rb)]))

# --- evidence -------------------------------------------------------------------------------
case("evidence", "everything right, one ungrounded quote on the product", "unclear_needs_human", R,
     beliefs(R, [informed(P, ungrounded=(EV,))]))
case("evidence", "everything right, one ungrounded case-level quote", "unclear_needs_human", R,
     beliefs(R, [informed(P)], ungrounded=[EV]))

# --- tolerance edges ------------------------------------------------------------------------
case("edge", "premium 1.0% high (41,713 vs 41,300), confirmed", "clear", R,
     beliefs(R, [informed(P, premium_inr=st(41713))]))
case("edge", "premium 1.02% high (41,720 vs 41,300), confirmed", "flag_for_review", R,
     beliefs(R, [informed(P, premium_inr=st(41720))]))
case("edge", "premium rounded 'about 41,000' (0.7% low)", "clear", R,
     beliefs(R, [informed(P, premium_inr=st(41000))]))
case("edge", "premium rounded 'about 40,000' (3.1% low) by an otherwise informed customer", "flag_for_review", R,
     beliefs(R, [informed(P, premium_inr=st(40000))]))
case("edge", "term 35 months against 36", "flag_for_review", R, beliefs(R, [informed(P, term_months=st(35))]))
case("edge", "cancel window 31 days against 30", "clear", R, beliefs(R, [informed(P, cancel_window_days=st(31))]))
case("edge", "cancel window 15 days against 30", "flag_for_review", R,
     beliefs(R, [informed(P, cancel_window_days=st(15))]))
case("edge", "cover 1 lakh against 3.5 lakh", "flag_for_review", R, beliefs(R, [informed(P, cover_inr=st(100000))]))
P_feat = product(features=frozenset({FeatureClaim.one_time_payment}))
case("edge", "single-premium product; customer says it is paid once", "clear", record(P_feat),
     beliefs(record(P_feat), [informed(P_feat, feature_probe=st((FeatureClaim.one_time_payment,)))]))
case("edge", "regular-premium product; customer believes paid once but never says so (no question asks)",
     "flag_for_review", R, beliefs(R, [informed(P)]))
R0 = record()
R_empty = LoanRecord(**{**R0.model_dump(), "products": ()})
case("edge", "record with no product at all; open recall answered 'only the loan'", "clear", R_empty,
     beliefs(R_empty, [], items=()))

# --- compliant customers who might be flagged (false-flag hunt) -----------------------------
case("compliant", "informed; leaves the product out of open recall ('just the loan')", "flag_for_review", R,
     beliefs(R, [informed(P)], items=()))
case("compliant", "informed; also mentions the processing fee in recall", "clear", R,
     beliefs(R, [informed(P)], items=[named(P), RecallItem(evidence=EV, kind=KindClaim.fee)]))
case("compliant", "informed; mentions an older policy of their own that is not on this loan", "clear", R,
     beliefs(R, [informed(P)], items=[named(P), RecallItem(evidence=EV, kind=KindClaim.insurance)]))
case("compliant", "informed; record has no cancel window; customer says 'yes it can be cancelled'", "flag_for_review",
     record(P_nowin), beliefs(record(P_nowin), [informed(P_nowin, cancel_allowed=st(True))]))
case("compliant", "informed; record digital_click, customer says OTP (one digital journey)", "flag_for_review",
     record(product(consent=Consent(method=ConsentMethod.digital_click, at=date(2026, 10, 1)))),
     beliefs(record(product(consent=Consent(method=ConsentMethod.digital_click, at=date(2026, 10, 1)))),
             [informed(P, consent_method=st(ConsentMethod.otp))]))
case("compliant", "informed; paid separately on record; says 'paid separately'", "clear", record(P_sep),
     beliefs(record(P_sep), [informed(P_sep)]))
case("compliant", "informed; gives term as 3 years (36)", "clear", R, beliefs(R, [informed(P)]))
case("compliant", "informed; knows the cover is 'the loan amount' but extraction got no number", "unclear_needs_human",
     R, beliefs(R, [informed(P, cover_inr=UN)]))


def main() -> int:
    bad = 0
    for group, name, want, rec, b in CASES:
        try:
            result = evaluate(rec, b)
            got = result.verdict.value
            detail = "; ".join(f"{f.rule_id.value}:{f.severity.value}" for f in result.all_flags())
            gaps = "; ".join(f"{g.rule_id.value}:{g.reason.value}" for g in result.all_gaps())
        except Exception as exc:  # noqa: BLE001
            got, detail, gaps = f"ERROR {type(exc).__name__}", str(exc)[:80], ""
        mark = ""
        if got != want:
            bad += 1
            mark = "  <== FALSE CLEAR" if got == "clear" else ("  <== FALSE FLAG" if want == "clear" else "  <== differs")
        print(f"[{group}] {name}\n      want {want}; got {got}{mark}\n      flags: {detail or '-'} | gaps: {gaps or '-'}")
    print(f"\n{len(CASES)} cases; {bad} differ from the verifier's reading")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
