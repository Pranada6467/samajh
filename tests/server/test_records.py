"""The record book: strict loading, and demo records that are plainly synthetic."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from samajh.server.records import PACKAGED_DIR, RECORD_ID, RecordBook, default_book, load_book

BOOK = load_book(PACKAGED_DIR)
HERO = json.loads((PACKAGED_DIR / "hero.json").read_text(encoding="utf-8"))


def write(directory: Path, name: str, data: object) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_the_packaged_demo_records_load() -> None:
    assert BOOK.ids() == ["hero", "informed", "third-party"]
    for record_id in BOOK.ids():
        record = BOOK.get(record_id)
        assert record.id == record_id and re.fullmatch(RECORD_ID, record_id)
        assert len(record.record.products) == 1


def test_the_demo_records_are_plainly_synthetic() -> None:
    for path in sorted(PACKAGED_DIR.glob("*.json")):
        record = BOOK.get(path.stem)
        assert re.fullmatch(r"LN-DEMO-\d{4}", record.record.loan_id)
        assert record.record.borrower.name.split()[1] in ("Namoona", "Udaharan")  # "sample", "example"
        assert "नमूना" in record.lender_name
        assert all("(synthetic)" in product.provider for product in record.record.products)
        assert "Synthetic" in record.description
        # Nothing shaped like a phone, account, Aadhaar or card number, and no PAN.
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\d{8,}", text) and not re.search(r"\b[A-Z]{5}\d{4}[A-Z]\b", text)
    assert len({BOOK.get(record_id).record.loan_id for record_id in BOOK.ids()}) == 3


def test_the_demo_records_show_what_their_labels_promise() -> None:
    hero, informed, third = (BOOK.get(i).record for i in ("hero", "informed", "third-party"))
    assert hero.loan_kind == "gold" and hero.products[0].paid_from_loan and hero.products[0].consent is None
    assert informed.products[0].consent is not None and informed.products[0].provider_choice_offered
    assert third.borrower.name != hero.borrower.name


def test_the_listing_is_for_the_picker_and_holds_no_tested_value() -> None:
    listing = BOOK.listing()

    assert [row["id"] for row in listing] == BOOK.ids()
    assert listing[0] == {
        "id": "hero",
        "label": BOOK.get("hero").label,
        "description": BOOK.get("hero").description,
        "first_name": "Ramesh",
        "language": "hi",
    }
    for row in listing:
        product = BOOK.get(row["id"]).record.products[0]
        shown = " ".join(row.values()).casefold()
        named = ("insurance", "बीमा", "credit", "policy", "premium", "cover", "otp", "sign", product.provider)
        figures = (product.premium_inr, product.cover_inr, product.term_months, product.cancel_window_days)
        assert [word for word in named if word.casefold() in shown] == []
        assert [n for n in figures if n is not None and re.search(rf"(?<!\d){n}(?!\d)", shown)] == []
        assert BOOK.get(row["id"]).lender_name not in shown and "LN-" not in " ".join(row.values())


def test_an_unknown_id_is_a_key_error() -> None:
    with pytest.raises(KeyError):
        BOOK.get("nobody")


def test_records_from_several_directories_make_one_book(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write(tmp_path, "eval-0001.json", HERO | {"id": "eval-0001"})

    assert load_book(PACKAGED_DIR, tmp_path).ids() == ["eval-0001", "hero", "informed", "third-party"]
    monkeypatch.setenv("SAMAJH_RECORDS_DIR", str(tmp_path))
    assert default_book().get("eval-0001").record == BOOK.get("hero").record
    monkeypatch.delenv("SAMAJH_RECORDS_DIR")
    assert default_book().ids() == BOOK.ids()


def test_a_duplicate_id_is_refused(tmp_path: Path) -> None:
    shutil.copy(PACKAGED_DIR / "hero.json", tmp_path / "hero.json")

    with pytest.raises(ValueError, match="duplicate record id 'hero'"):
        load_book(PACKAGED_DIR, tmp_path)
    with pytest.raises(ValueError, match="duplicate"):
        RecordBook([BOOK.get("hero"), BOOK.get("hero")])


@pytest.mark.parametrize(
    ("name", "data"),
    [
        ("hero.json", "{not json"),
        ("hero.json", {k: v for k, v in HERO.items() if k != "lender_name"}),
        ("hero.json", HERO | {"premium_hint": "52000"}),
        ("hero.json", HERO | {"lender_name": "  "}),
        ("hero.json", HERO | {"record": HERO["record"] | {"products": "none"}}),
        ("hero.json", HERO | {"record": HERO["record"] | {"borrower": HERO["record"]["borrower"] | {"name": " "}}}),
        ("other.json", HERO),
        ("Hero.json", HERO | {"id": "Hero"}),
        ("a_b.json", HERO | {"id": "a_b"}),
        ("x" * 42 + ".json", HERO | {"id": "x" * 42}),
    ],
)
def test_a_malformed_file_is_refused_and_named(tmp_path: Path, name: str, data: object) -> None:
    path = write(tmp_path, name, data)

    with pytest.raises(ValueError, match=re.escape(str(path))):
        load_book(tmp_path)


def test_a_missing_directory_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not a directory"):
        load_book(tmp_path / "absent")


def test_a_written_record_reads_back(tmp_path: Path) -> None:
    record = BOOK.get("informed").model_copy(update={"id": "eval-0002"})
    write(tmp_path, "eval-0002.json", record.model_dump_json())

    assert load_book(tmp_path).get("eval-0002") == record
