"""The review export (references/pilots/P2-lines-for-review.md) covers every bot line and is current."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "probes"))

import export_lines

from samajh.dialogue import LINES, load_prompts
from samajh.types import Language


def test_every_line_has_a_meaning_and_a_moment():
    assert export_lines.MEANINGS.keys() == LINES.keys()


def test_the_exported_file_holds_every_current_line():
    text = export_lines.OUT.read_text(encoding="utf-8")
    for language in (Language.hi, Language.hi_en):
        for key, template in load_prompts(language).templates.items():
            assert export_lines._cell(template) in text, (language, key)
