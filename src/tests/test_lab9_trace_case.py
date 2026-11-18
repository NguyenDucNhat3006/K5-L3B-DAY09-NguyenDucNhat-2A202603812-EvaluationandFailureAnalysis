import pytest

from lab9.trace_case import investigate


@pytest.mark.student
@pytest.mark.parametrize("shape, should_match", [("fixed", True), ("seeded_regression", False)])
def test_c002_uses_order_delay(shape, should_match):
    case = investigate(shape, "C-002", 11)
    trial, label = case["trial"], case["label"]
    actual = (trial["result"]["status"], trial["snapshot"]["refund_count"], trial["snapshot"]["refund_vnd"])
    expected = (label["status"], label["refund_count"], label["refund_vnd"])
    assert (actual == expected) == should_match
