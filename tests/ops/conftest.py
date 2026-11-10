from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))  # serverkit.FakeSpeech

from samajh.ops.__main__ import main
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
