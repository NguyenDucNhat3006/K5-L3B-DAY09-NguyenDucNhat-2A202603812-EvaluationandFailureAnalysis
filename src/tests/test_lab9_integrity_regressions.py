import copy
import pytest

from lab9.gate import integrity_check


@pytest.mark.student
@pytest.mark.parametrize("change", ["duplicate", "relabel", "grader_failure"])
def test_invalid_rows_block_even_with_green_summary(change):
    baseline = {
        "manifest": {"items": 1, "seeds": [1, 2]},
        "rows": [{"item_id": "A", "seed": seed, "pass_rate": True, "slices": ["denial"]}
                 for seed in (1, 2)],
        "metrics": {"pass_rate": 1.0},
        "evaluator_failures": [],
    }
    report = copy.deepcopy(baseline)
    if change == "duplicate":
        report["rows"][1] = report["rows"][0]
    elif change == "relabel":
        report["rows"][0]["slices"] = []
    else:
        report["evaluator_failures"].append("grader crashed")
    spec = {"metrics": [{"id": "pass_rate"}]}
    assert integrity_check(report, baseline, spec)
