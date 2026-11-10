from __future__ import annotations

import shutil
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))  # serverkit.FakeSpeech

from samajh.ops import book as books
from samajh.ops import sampler
from samajh.ops.__main__ import main
from samajh.ops.simulate import run_draw, scripted_analysis
from samajh.ops.store import OpsStore


@pytest.fixture(scope="session")
def demo_state(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The scripted demo batch (200 loans, four draws of 20). Read-only: copy it before writing."""
    state = tmp_path_factory.mktemp("demo")
    assert main(["demo", "--state", str(state)]) == 0
    return state


@pytest.fixture
def state(demo_state: Path, tmp_path: Path) -> Path:
    """A private copy of the demo batch's state directory."""
    return Path(shutil.copytree(demo_state, tmp_path / "state"))


@pytest.fixture
def store(state: Path) -> OpsStore:
    return OpsStore(state / "ops")


MIXED_DRAWS = ((date(2027, 1, 20), 1.0), (date(2027, 2, 10), 0.05), (date(2027, 3, 5), 0.4))


@pytest.fixture(scope="session")
def mixed_state(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The seed-85 book drawn at three different rates (1.0, 0.05, 0.4), every call scripted and
    analysed: the chances of being drawn differ far more than `report.NARROW_RATIO`. Read-only."""
    state = tmp_path_factory.mktemp("mixed")
    meta, loans, customers = books.generate_book(85)
    store = OpsStore(state / "ops")
    store.init(meta, loans, date(2027, 1, 1), date(2027, 6, 30), datetime(2027, 1, 1, tzinfo=UTC))
    previous = None
    for as_of, rate in MIXED_DRAWS:
        drawn = sampler.draw(loans, meta, as_of, rate, 85, after=previous)
        store.add_draw(drawn)
        previous = as_of
    by_loan = {c.loan_id: c for c in customers}
    for drawn in store.draws():
        run_draw(store, drawn, by_loan, scripted_analysis)
    return state
