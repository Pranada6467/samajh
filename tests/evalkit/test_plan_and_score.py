"""The manifest freeze, the plan, the scoring path and the statistics."""

from __future__ import annotations

from collections import Counter

import pytest
from evalkit_bench import ROWS, write_manifest
from pydantic import ValidationError

from samajh.evalkit.manifest import ManifestError, load_manifest
from samajh.evalkit.plan import SttSpec, assign_voices, load_experiment, plan
from samajh.evalkit.runner import SttRow, current_rows, jobs
from samajh.evalkit.score import (
    Hypothesis,
    Prediction,
    Scorer,
    aggregate,
    cell_text,
    mcnemar_exact,
    paired,
    pivot,
    score,
    wilson,
)
from samajh.evalkit.scorers import AMOUNT, naive_digits, parser
from samajh.types import Language

# ------------------------------------------------------------------ manifest


def test_a_manifest_that_is_not_the_frozen_file_is_refused(bench):
    bench.manifest.write_bytes(bench.manifest.read_bytes() + b"\n")
    with pytest.raises(ManifestError, match="froze"):
        load_manifest(bench.manifest, expect_sha256=bench.digest)


def test_duplicate_ids_and_bad_rows_are_refused(tmp_path):
    path = tmp_path / "m.jsonl"
    digest = write_manifest(path, [ROWS[0], ROWS[0]])
    with pytest.raises(ManifestError, match="duplicate"):
        load_manifest(path, expect_sha256=digest)
    digest = write_manifest(path, [{**ROWS[0], "language": "xx"}])
    with pytest.raises(ManifestError, match="m.jsonl:1"):
        load_manifest(path, expect_sha256=digest)


# ------------------------------------------------------------------ plan


def test_the_plan_is_the_union_of_the_arms_without_duplicates(bench):
    cells = plan(bench.items, bench.experiment)
    assert len(cells) == len({cell.key for cell in cells}) == 16 * 4 + 8
    babble = [cell for cell in cells if cell.condition == "babble10"]
    fold_0 = {row["id"] for row in ROWS if row["tags"]["fold"] == "0"}
    assert {cell.item_id for cell in babble} == fold_0
    assert {cell.stt.model for cell in babble} == {"prisma-v3.0"}


def test_voices_are_balanced_within_each_stratum_and_stable(bench):
    voices = assign_voices(bench.items, bench.experiment)
    assert voices == assign_voices(bench.items, bench.experiment)
    per_group = Counter((row["language"], row["tags"]["stratum"], voices[row["id"]].voice) for row in ROWS)
    assert set(per_group.values()) == {2}
    assert {voices[row["id"]].voice for row in ROWS if row["language"] == "ta"} == {"Lakshmi", "Asmita"}


def test_requests_follow_the_item_language(bench):
    by_id = {item.id: item for item in bench.items}
    for job in jobs(bench.items, bench.experiment):
        expected = {"hi": "hi-IN", "ta": "ta-IN"}[by_id[job.cell.item_id].language.value]
        assert job.options.language == job.timbre.language == expected
    assert SttSpec(model="prisma-v3.0", format="codemix", language="item+en").options(
        Language.hi_en
    ).language == ("hi-IN", "en-IN")
    assert (
        SttSpec(model="prisma-v3.0", format="verbatim", language="indic-auto").options(Language.kn).language
        == "indic-auto"
    )


@pytest.mark.parametrize(
    "spec",
    [
        {"model": "prisma-v2.5", "format": "codemix"},
        {"model": "prisma-v2.5", "format": "transcribe", "language": "indic-auto"},
    ],
)
def test_a_configuration_the_model_rejects_fails_when_the_experiment_is_read(bench, spec):
    bench.raw["arms"][0]["stt"] = [spec]
    with pytest.raises(ValidationError):
        _ = bench.experiment


def test_an_arm_naming_an_undefined_condition_or_voice_fails(bench):
    bench.raw["arms"][0]["conditions"] = ["nope"]
    with pytest.raises(ValidationError, match="undefined conditions"):
        _ = bench.experiment
    bench.raw["arms"][0]["conditions"] = ["phone"]
    bench.raw["voices"]["hi"] = [{"model": "timbre-v3.0", "voice": "Asmita"}]
    with pytest.raises(ValidationError, match="does not belong"):
        _ = bench.experiment


def test_an_experiment_file_loads_with_its_manifest_resolved(bench, tmp_path):
    path = tmp_path / "experiment.toml"
    path.write_text(
        f'''
name = "t"
manifest = "items.jsonl"
manifest_sha256 = "{bench.digest}"
scorer = "amount"
budget_credits = 5
[voices]
hi = [{{model = "timbre-v3.0", voice = "Shivani"}}]
[conditions]
clean16k = []
gsm = [{{kind = "resample", rate = 8000}}, {{kind = "bandlimit"}}, {{kind = "mulaw"}}]
[[arm]]
name = "a"
conditions = ["gsm"]
stt = [{{model = "prisma-v3.0", format = "verbatim", language = "indic-auto"}}]
where = {{language = "hi"}}
''',
        encoding="utf-8",
    )
    experiment = load_experiment(path)
    assert experiment.manifest == bench.manifest.resolve()
    assert [step.kind for step in experiment.conditions["gsm"]] == ["resample", "bandlimit", "mulaw"]
    items = load_manifest(experiment.manifest, expect_sha256=experiment.manifest_sha256)
    assert {cell.item_id[:2] for cell in plan(items, experiment)} == {"hi"}


# ------------------------------------------------------------------ scoring


def _stt_row(bench, text: str, literal: str | None = None, index: int = 0) -> SttRow:
    job = jobs(bench.items, bench.experiment)[index]
    return SttRow(
        fingerprint=job.fingerprint,
        item_id=job.item.id,
        language=job.item.language,
        voice=job.cell.voice,
        condition=job.cell.condition,
        steps=[],
        stt=job.cell.stt,
        request={},
        clip_sha256="c",
        audio_sha256="a",
        audio_seconds=1.0,
        text=text,
        literal=literal,
        detected_language=None,
        request_id=None,
        truncated=False,
        cache_key="k",
        cache_hit=False,
        est_credits=0.0,
        seconds=0.1,
        attempts=1,
        ts="t",
    )


def test_a_predictor_is_given_the_transcript_and_language_and_nothing_else(bench):
    seen = []

    def spy(hypothesis):
        seen.append(hypothesis)
        return Prediction(value=1000)

    rows = score(bench.items, [_stt_row(bench, "एक हज़ार रुपये")], Scorer("spy", "amount_inr", {"spy": spy}))
    assert seen == [Hypothesis(text="एक हज़ार रुपये", language=Language.hi)]
    assert set(Hypothesis.model_fields) == {"text", "language"}
    assert [(row.gold, row.predicted, row.correct) for row in rows] == [(1000, 1000, True)]


def test_correct_means_equal_to_gold_and_no_answer_is_wrong(bench):
    answers = {"right": 1000, "wrong": 999, "none": None, "bool": True, "text": "1000"}
    methods = {name: (lambda _h, value=value: Prediction(value=value)) for name, value in answers.items()}
    rows = score(bench.items, [_stt_row(bench, "x")], Scorer("s", "amount_inr", methods))
    assert {row.method: row.correct for row in rows} == {
        "right": True,
        "wrong": False,
        "none": False,
        "bool": False,
        "text": False,
    }


def test_the_literal_wording_is_scored_as_its_own_output(bench):
    rows = score(bench.items, [_stt_row(bench, "सवा 1,000", literal="एक हज़ार")], AMOUNT)
    got = {(row.output, row.method): (row.predicted, row.correct) for row in rows}
    assert got == {
        ("text", "naive"): (1000, True),
        ("text", "parser"): (1250, False),
        ("literal", "naive"): (None, False),
        ("literal", "parser"): (1000, True),
    }
    assert {row.transcript for row in rows if row.output == "literal"} == {"एक हज़ार"}


def test_only_the_planned_requests_are_scored(bench):
    bench.run()
    bench.raw["conditions"]["babble10"][0]["snr_db"] = 5
    current = current_rows(bench.store, jobs(bench.items, bench.experiment))
    assert len(current) == 16 * 4 and all(row.condition != "babble10" for row in current.values())


@pytest.mark.parametrize(
    ("text", "naive", "parsed"),
    [
        ("मेरे लोन से 52,000 रुपये कटे।", 52000, 52000),
        ("सवा 2,00,000 का लोन मिला।", 200000, 225000),
        ("2.25 लाख का लोन मिला।", 225000, 225000),
        ("साढ़े 3,000 की किस्त है।", 3000, 3500),
        ("पौने ₹2,00,000 जमा किए।", 200000, 175000),
        ("ஒன்றரை ₹1,00,000 பிரீமியம்.", 100000, 150000),
        ("cover 10 lakh rupees का बताया।", 1000000, 1000000),
        ("1.5 रुपये", None, None),
        ("बावन हज़ार रुपये कटे।", None, 52000),
        ("कुछ नहीं कटा।", None, None),
    ],
)
def test_naive_reading_and_the_parser_on_the_shapes_prisma_writes(text, naive, parsed):
    hypothesis = Hypothesis(text=text, language=Language.hi)
    assert naive_digits(hypothesis).value == naive
    assert parser(hypothesis).value == parsed


def test_no_answer_carries_its_reason():
    assert naive_digits(Hypothesis(text="बावन हज़ार", language=Language.hi)).note == "no_digits"
    assert parser(Hypothesis(text="कुछ नहीं", language=Language.hi)).note == "no_amount"
    note = parser(Hypothesis(text="50 से 60 हज़ार", language=Language.hi)).note
    assert note.startswith("ambiguous:multiple_amounts")


# ------------------------------------------------------------------ statistics


@pytest.mark.parametrize(
    ("correct", "n", "low", "high"),
    [
        # Reference values: Newcombe (1998), method 3, and the closed form at the edges.
        (81, 263, 0.2553, 0.3662),
        (15, 148, 0.0624, 0.1605),
        (0, 20, 0.0, 0.1611),
        (20, 20, 0.8389, 1.0),
        (1, 29, 0.0061, 0.1718),
    ],
)
def test_wilson_interval_matches_published_values(correct, n, low, high):
    got = wilson(correct, n)
    assert got == pytest.approx((low, high), abs=5e-4)


def test_wilson_with_no_data_says_nothing():
    assert wilson(0, 0) == (0.0, 1.0)


@pytest.mark.parametrize(
    ("only_a", "only_b", "p"), [(0, 0, 1.0), (5, 0, 0.0625), (0, 6, 0.03125), (3, 3, 1.0), (8, 1, 0.0390625)]
)
def test_exact_mcnemar(only_a, only_b, p):
    assert mcnemar_exact(only_a, only_b) == pytest.approx(p)


def test_aggregate_counts_each_group_and_pairs_line_up(bench):
    texts = ["1,000 रुपये", "सवा 1,000", "शून्य"]
    rows = score(bench.items, [_stt_row(bench, text, index=i) for i, text in enumerate(texts)], AMOUNT)
    summaries = {s.group["method"]: s for s in aggregate(rows, ["method"])}
    assert (summaries["naive"].correct, summaries["naive"].n) == (2, 3)
    assert (summaries["parser"].correct, summaries["parser"].n) == (1, 3)
    assert summaries["naive"].low == pytest.approx(wilson(2, 3)[0])
    assert cell_text(summaries["parser"]) == "1/3 (33%, 6-79)"
    naive = [row for row in rows if row.method == "naive"]
    parsed = [row for row in rows if row.method == "parser"]
    assert paired(naive, parsed, ["item_id", "condition", "stt"]) == (1, 1, 0, 1)
    table = pivot(rows, down=["language"], across="method")
    assert table.splitlines()[0] == "| language | naive | parser |"
    assert table.splitlines()[2] == "| hi | 2/3 (67%, 21-94) | 1/3 (33%, 6-79) |"
