from pathlib import Path

import pytest
from evalkit_bench import Bench


@pytest.fixture
def bench(tmp_path: Path) -> Bench:
    return Bench(tmp_path)
