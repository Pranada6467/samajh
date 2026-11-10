from __future__ import annotations

from pathlib import Path

import pytest
from serverkit import FakeSpeech


@pytest.fixture
def fake() -> FakeSpeech:
    return FakeSpeech(["पचास हज़ार", "दो हज़ार", "बीमा"])


@pytest.fixture
def state(tmp_path: Path) -> Path:
    return tmp_path / "state"
