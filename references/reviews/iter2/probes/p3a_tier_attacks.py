"""P3a verifier probe: fresh Beliefs against the tier logic. Pure, no network.

    uv run python references/reviews/iter2/probes/p3a_tier_attacks.py

Each case starts from an informed customer on a compliant record (tier must be `clear`) and
changes one or two things. `want` is the set of tiers the verifier accepts, written before running.
A row is printed BAD when the engine's tier is outside `want`. Also checks for every case that
the tier equals tier_of(flags, gaps) recomputed here from the flag reasons and gap rules only.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "iter1" / "probes"))
from engine_adversarial import DK, EV, NA, UN, beliefs, informed, named, product, record, st  # noqa: E402

from samajh.rules import evaluate  # noqa: E402
from samajh.rules.summary import summarise  # noqa: E402
from samajh.types import (  # noqa: E402
    AnswerConflict,
    ClaimEvidence,
    ConcernEvidence,
    Evidence,
    FeatureClaim,
    KindClaim,
    OpenRecall,
    PaymentFrequency,
    PaymentSource,
    Question,
    SaleConcern,
    Stated,
    Tier,
    Unclear,
)

R_, I_, G_, C_ = Tier.refer, Tier.incomplete, Tier.understanding_gap, Tier.clear
NOT_MISSED = {R_, I_}
E2 = Evidence(quote="y", turn_id=9)


def approx(value, low=None, hedged=True):
    return Stated(value=value, evidence=EV, hedged=hedged, approximate=True, low=low)


def hedge(value):
    return Stated(value=value, evidence=EV, hedged=True)


CASES = []


def case(name, want, rec, b):
    CASES.append((name, set(want), rec, b))


P = product()  # credit_life, 41,300 premium, from loan, OTP consent, not required, mitigant, choice, 30d
R = record(P)
B = lambda **o: beliefs(R, [informed(P, **o)])  # noqa: E731

case("baseline informed", {C_}, R, B())
# --- real problems ---------------------------------------------------------------------
case("wrong kind (FD), hedged", NOT_MISSED, R, B(kind=hedge(KindClaim.deposit)))
case("wrong kind only in recall", NOT_MISSED, R,
     beliefs(R, [informed(P)], items=(named(P, kind=KindClaim.deposit),)))
P_nc = product(consent=None)
R_nc = record(P_nc)
case("funded from loan, no consent on record", NOT_MISSED, R_nc,
     beliefs(R_nc, [informed(P_nc, consent_given=st(True), consent_method=NA)]))
case("customer says separately, record from loan", NOT_MISSED, R, B(payment_source=hedge(PaymentSource.separately)))
case("consent not recognised", NOT_MISSED, R, B(consent_given=st(False)))
P_req = product(required_for_loan=True, risk_mitigant=False)
R_req = record(P_req)
case("required, not a risk mitigant", NOT_MISSED, R_req, beliefs(R_req, [informed(P_req)]))
case("contradicted belief (guaranteed return), hedged", NOT_MISSED, R,
     B(feature_probe=hedge((FeatureClaim.guaranteed_return,))))
case("contradicted belief volunteered", NOT_MISSED, R,
     B(volunteered_claims=(ClaimEvidence(claim=FeatureClaim.refundable_anytime, evidence=EV),)))
case("paid once on a regular product", NOT_MISSED, R, B(payment_frequency=st(PaymentFrequency.one_time)))
case("took nothing, record has product", NOT_MISSED, R,
     beliefs(R, [informed(P, kind=NA)], items=()).model_copy(
         update={"recall": OpenRecall(asked=True, answer=EV, items=(), denial=EV)}))
case("took nothing, then names insurance at kind question", NOT_MISSED, R,
     beliefs(R, [informed(P)], items=()).model_copy(
         update={"recall": OpenRecall(asked=True, answer=EV, items=(), denial=EV)}))
case("took nothing, then kind unclear", NOT_MISSED, R,
     beliefs(R, [informed(P, kind=UN)], items=()).model_copy(
         update={"recall": OpenRecall(asked=True, answer=EV, items=(), denial=EV)}))
case("conflict on kind (FD then insurance)", {R_}, R,
     B(conflicts=(AnswerConflict(question=Question.kind, answers=(EV, E2)),)))
case("conflict on payment source", {R_}, R,
     B(conflicts=(AnswerConflict(question=Question.payment_source, answers=(EV, E2)),)))
case("conflict on consent", {R_}, R,
     B(conflicts=(AnswerConflict(question=Question.consent, answers=(EV, E2)),)))
case("conflict on payment_frequency", {R_}, R,
     B(conflicts=(AnswerConflict(question=Question.payment_frequency, answers=(EV, E2)),)))
case("conflict on cover only", {G_}, R,
     B(conflicts=(AnswerConflict(question=Question.cover, answers=(EV, E2)),)))
case("sale concern", NOT_MISSED, R,
     beliefs(R, [informed(P)], concerns=(ConcernEvidence(concern=SaleConcern.coached_answers, evidence=EV),)))
case("off-record deposit named in recall", NOT_MISSED, R,
     beliefs(R, [informed(P)], items=(named(P), named(P, kind=KindClaim.deposit).model_copy(update={"product_id": None}))))
case("wrong cover confidently (10 lakh vs 3.5)", {G_}, R, B(cover_inr=st(1000000)))
case("wrong window confidently (15 vs 30)", {G_}, R, B(cancel_window_days=st(15)))
case("not told can cancel", {G_}, R, B(cancel_allowed=st(False)))
# --- hedges and approximations must not upgrade a wrong answer -------------------------
case("about 50k vs 52k record, confirmed", {G_}, record(product(premium_inr=52000)),
     beliefs(record(product(premium_inr=52000)), [informed(product(premium_inr=52000), premium_inr=approx(50000))]))
P80 = product(premium_inr=80000)
R80 = record(P80)
case("about 50k vs 80k record, confirmed", {R_}, R80, beliefs(R80, [informed(P80, premium_inr=approx(50000))]))
case("about 50k vs 80k record, NOT confirmed", NOT_MISSED, R80,
     beliefs(R80, [informed(P80, premium_inr=approx(50000), premium_readback=NA)]))
case("range 50-52k vs 80k, confirmed", {R_}, R80, beliefs(R80, [informed(P80, premium_inr=approx(52000, 50000))]))
P52 = product(premium_inr=52000)
R52 = record(P52)
case("range 25k-50k (2x) vs 52k, confirmed", {R_, I_, G_}, R52,
     beliefs(R52, [informed(P52, premium_inr=approx(50000, 25000))]))
case("range 25k-50k (2x) vs 23k, confirmed", {R_, I_, G_}, record(product(premium_inr=23000)),
     beliefs(record(product(premium_inr=23000)), [informed(product(premium_inr=23000), premium_inr=approx(50000, 25000))]))
case("range 1-5 lakh (5x, should never parse) vs 3 lakh, confirmed", {R_, I_}, record(product(premium_inr=300000)),
     beliefs(record(product(premium_inr=300000)), [informed(product(premium_inr=300000), premium_inr=approx(500000, 100000))]))
case("exact 52k on 52k record, flagged approximate by hedge only (hedged=True, approximate=False)", {C_}, R52,
     beliefs(R52, [informed(P52, premium_inr=Stated(value=52000, evidence=EV, hedged=True))]))
case("approximate but NOT confirmed, near", {I_}, R52,
     beliefs(R52, [informed(P52, premium_inr=approx(50000), premium_readback=NA)]))
case("cover range 2x straddling record passes outright", {C_, G_}, R,
     B(cover_inr=approx(500000, 250000)))
case("hedged kind 'maybe insurance' on insurance", {C_}, R, B(kind=hedge(KindClaim.insurance)))
# --- ordinary informed customer on a compliant record --------------------------------
case("informed, does not know cancel window", {G_}, R, B(cancel_window_days=DK))
case("informed, does not know cover or term or window", {G_}, R,
     B(cover_inr=DK, term_months=DK, cancel_window_days=DK))
case("informed, premium approximate confirmed + window DK", {G_}, R52,
     beliefs(R52, [informed(P52, premium_inr=approx(52000, 50000), cancel_window_days=DK)]))
case("informed, product not named unprompted", {G_}, R, beliefs(R, [informed(P)], items=()))
case("informed, consent method differs (OTP vs click)", {R_, I_, G_}, R,
     B(consent_method=st(__import__("samajh.types", fromlist=["ConsentMethod"]).ConsentMethod.digital_click)))
# --- silence ----------------------------------------------------------------------------
for f in ("kind", "premium_inr", "premium_readback", "payment_source", "consent_given", "consent_method",
          "required_for_loan", "feature_probe"):
    case(f"{f} unclear (refer-tier silence)", {I_}, R,
         beliefs(R, [informed(P, **{f: Unclear()})], items=() if f == "kind" else None))
case("payment_frequency unclear", {I_}, R, B(payment_frequency=Unclear()))


def main() -> int:
    bad = 0
    for name, want, rec, b in CASES:
        res = evaluate(rec, b)
        flags, gaps = res.all_flags(), res.all_gaps()
        # recompute from data: worst of flag tiers and gap tiers
        order = list(Tier)
        tiers = {f.tier for f in flags} | {g.tier for g in gaps}
        derived = next((t for t in order if t in tiers), Tier.clear)
        ok = res.tier in want and derived is res.tier
        bad += not ok
        reasons = sorted({f"{f.rule_id}:{f.reason}" for f in flags} | {f"gap {g.rule_id}:{g.reason}" for g in gaps})
        print(f"{'ok ' if ok else 'BAD'} {res.tier.value:18} want {sorted(t.value for t in want)} | {name} | {reasons}")
        if name.startswith("took nothing, then names"):
            for line in summarise(rec, res).lines:
                print("      summary:", line.tier.value, "|", line.title, "|", line.quote)
    print(f"\n{len(CASES)} cases, {bad} outside the verifier's reading")
    return 0


if __name__ == "__main__":
    sys.exit(main())
