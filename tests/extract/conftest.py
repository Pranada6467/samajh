import sys
from pathlib import Path

import pytest

# The evaluation scripts are run as scripts, so their folder is not a package.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "eval" / "text_path"))

from extractkit import FakeLlm, recorded_outputs


@pytest.fixture
def llm() -> FakeLlm:
    """Replays the model outputs recorded for the development set."""
    return FakeLlm(recorded_outputs())
