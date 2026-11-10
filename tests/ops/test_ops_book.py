from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

from samajh.ops import book as books
from samajh.ops.model import RETRY_AFTER, Tier
from samajh.ops.simulate import script_call, scripted_analysis
from samajh.ops.store import CALL_ID
from samajh.ops.triage import triage
from samajh.types import Language

FILES = ("book.jsonl", "sim-customers.jsonl", "BOOK.json", "README.md")


@pytest.fixture(scope="module")
def generated():
    return books.generate_book(85)


def _written(directory: Path, seed: int) -> dict[str, bytes]:
    books.write_book(directory, *books.generate_book(seed))
    return {name: (directory / name).read_bytes() for name in FILES}


def test_the_same_seed_gives_the_same_files_byte_for_byte(tmp_path: Path) -> None:
    first, again, other = (
        _written(tmp_path / "a", 85),
        _written(tmp_path / "b", 85),
        _written(tmp_path / "c", 86),
    )
    assert first == again
    assert first["book.jsonl"] != other["book.jsonl"]


def test_the_book_in_the_repository_is_what_seed_85_generates(tmp_path: Path) -> None:
    fresh = _written(tmp_path, 85)
    assert {name: (books.DATA_DIR / name).read_bytes() for name in FILES} == fresh


def test_every_id_and_name_is_marked_synthetic_and_nothing_looks_like_a_real_identifier(generated) -> None:
    meta, loans, _ = generated
    assert meta.synthetic and meta.lender_name.endswith("(synthetic)")
    for loan in loans:
        record = loan.record
        assert re.fullmatch(r"SYN-(GL|PL)-\d{6}-\d{4}", record.loan_id)
        assert re.fullmatch(r"SYN-BR-0[1-6]", loan.branch)
        assert record.borrower.name.endswith("(synthetic)")
        assert all(p.provider.endswith("(synthetic)") for p in record.products)
        assert record.lender_type is meta.lender_type
        assert record.borrower.language in (Language.hi, Language.hi_en)
        assert meta.sold_from <= loan.sold_on <= meta.sold_to
    assert len({loan.record.loan_id for loan in loans}) == meta.loans == 200
    # No run of digits long enough to be a phone, account, Aadhaar or card number.
    assert not re.search(r"\d{8,}", books.jsonl(loans))


def test_every_loan_can_be_scripted_and_analysed_and_an_informed_customer_has_no_finding(generated) -> None:
    _, loans, customers = generated
    tiers: Counter = Counter()
    for loan, customer in zip(loans, customers, strict=True):
        call = script_call(loan, customer)
        assert call.transcript.loan_id == loan.record.loan_id
        assert call.transcript.language is loan.record.borrower.language
        assert CALL_ID.fullmatch(call.transcript.call_id)
        result, how = scripted_analysis(call, loan.record)
        assert how == "scripted extraction, no model"
        tier = triage(result).tier
        tiers[tier] += 1
        if customer.archetype == "informed_full":
            assert tier is Tier.clear, (loan.record.loan_id, result.all_flags(), result.all_gaps())
    assert set(tiers) == set(Tier)  # the mix exercises every tier


def test_most_sales_are_unproblematic_and_the_hot_branch_and_channel_carry_more_problems(generated) -> None:
    _, loans, customers = generated
    problem = [books.ARCHETYPES[c.archetype].problem for c in customers]
    assert sum(problem) < len(loans) / 2

    def share(inside: list[bool]) -> tuple[float, float]:
        hot = [p for p, here in zip(problem, inside, strict=True) if here]
        rest = [p for p, here in zip(problem, inside, strict=True) if not here]
        return sum(hot) / len(hot), sum(rest) / len(rest)

    hot, rest = share([loan.branch == books.HOT_BRANCH for loan in loans])
    assert hot > rest
    hot, rest = share([loan.channel is books.HOT_CHANNEL for loan in loans])
    assert hot > rest


def test_a_customers_attempts_end_at_the_first_outcome_that_is_not_retried(generated) -> None:
    _, _, customers = generated
    for customer in customers:
        assert 1 <= len(customer.attempts) <= books.MAX_STEPS
        assert all(step.outcome in RETRY_AFTER for step in customer.attempts[:-1])
        assert len(customer.attempts) == books.MAX_STEPS or customer.attempts[-1].outcome not in RETRY_AFTER


def test_the_book_loads_back_and_a_changed_file_is_refused(tmp_path: Path, generated) -> None:
    meta, loans, customers = generated
    books.write_book(tmp_path, meta, loans, customers)
    assert books.load_book(tmp_path) == (meta, loans)
    assert tuple(books.load_customers(tmp_path).values()) == customers
    path = tmp_path / "book.jsonl"
    path.write_text(path.read_text(encoding="utf-8").replace("SYN-BR-01", "SYN-BR-02", 1), encoding="utf-8")
    with pytest.raises(ValueError, match="sha256"):
        books.load_book(tmp_path)
