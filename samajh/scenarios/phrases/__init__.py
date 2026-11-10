"""Phrase banks: what the customer and the bot say, per call language.

Each customer key names one answer (for example `kind.fd`: "it is an FD"). The key fixes the
meaning, so the scripted utterance and the scenario's belief cannot drift apart. Variants of a
key say the same thing in other words. All four banks have the same keys.

Hindi and Hinglish text is model-written and model-reviewed. Tamil and Kannada text is not
human-reviewed.
"""

from dataclasses import dataclass

from samajh.scenarios.phrases import hi, hi_en, kn, ta
from samajh.types import Language, LenderType, LoanKind


@dataclass(frozen=True)
class PhraseBank:
    """One language's wording. Amounts, durations and years are keyed by their value."""

    customer: dict[str, tuple[str, ...]]
    bot: dict[str, str]
    amounts: dict[int, str]  # rupees -> how a customer says it (fraction words where natural)
    durations: dict[int, str]  # months -> spoken term
    windows: dict[int, str]  # days -> spoken cancellation window
    years: dict[int, str]  # year of birth -> spoken
    first_name: str  # spoken form of the synthetic borrower's first name
    borrower: str  # name on the synthetic record
    lender: dict[LenderType, str]
    loan: dict[LoanKind, str]
    provider: str  # spoken form of the synthetic insurer's name


def _bank(module) -> PhraseBank:
    return PhraseBank(
        customer=module.CUSTOMER,
        bot=module.BOT,
        amounts=module.AMOUNTS,
        durations=module.DURATIONS,
        windows=module.WINDOWS,
        years=module.YEARS,
        first_name=module.FIRST_NAME,
        borrower=module.BORROWER,
        lender=module.LENDER,
        loan=module.LOAN,
        provider=module.PROVIDER,
    )


BANKS: dict[Language, PhraseBank] = {
    Language.hi: _bank(hi),
    Language.hi_en: _bank(hi_en),
    Language.ta: _bank(ta),
    Language.kn: _bank(kn),
}
