"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations
import numpy as np
from math import comb
from scipy.stats import bootstrap
from collections.abc import Sequence

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    # TODO M2
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}

    for actual, predicted in zip(human, judge, strict=True):
        if actual == POS and predicted == POS:
            counts["tp"] += 1
        elif actual == POS:
            counts["fn"] += 1
        elif predicted == POS:
            counts["fp"] += 1
        else:
            counts["tn"] += 1

    return counts

def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    # TODO M2: precision = tp/(tp+fp), recall = tp/(tp+fn); return 0.0 when the denominator is 0
    counts = confusion(human, judge)

    True_positives = counts["tp"]
    predicted_failures = True_positives + counts["fp"]
    actual_failures = True_positives + counts["fn"]

    precision = True_positives / predicted_failures if predicted_failures else 0.0
    recall = True_positives / actual_failures if actual_failures else 0.0

    return precision, recall

def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    # TODO M2
    counts = confusion(human, judge)
    n = sum(counts.values())
    if n == 0:
        raise ValueError("Kappa requires at least one pair of labels")

    tp, fp = counts["tp"], counts["fp"]
    fn, tn = counts["fn"], counts["tn"]

    # Số cặp nhãn mà người chấm và judge đồng ý.
    agreed = tp + tn

    # Xác suất đồng ý ngẫu nhiên là expected_pairs / n².
    expected_pairs = (tp + fn) * (tp + fp) + (tn + fp) * (tn + fn)
    denominator = n * n - expected_pairs
    if denominator == 0:
        raise ValueError("Kappa is undefined when chance agreement is 1")

    return (n * agreed - expected_pairs) / denominator


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    # TODO M2: (p_obs + spec - 1) / (sens + spec - 1)
    denominator = sensitivity + specificity - 1
    if denominator == 0:
        raise ValueError("Failure rate cannot be estimated from this judge")

    corrected_rate = (observed_rate + specificity - 1) / denominator
    return max(0.0, min(1.0, corrected_rate))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    # TODO M4
    if len(a) != len(b) or len(a) == 0:
        raise ValueError("Expected two non-empty samples of equal length")

    pr = np.asarray(a, dtype=float)
    baseline = np.asarray(b, dtype=float)
    if np.array_equal(pr, baseline):
        return 0.0, 0.0, 0.0

    def mean_difference(x, y):
        return np.mean(x - y)

    result = bootstrap(
        (pr, baseline),
        mean_difference,
        paired=True,
        vectorized=False,
        method="percentile",
        n_resamples=n_resamples,
        confidence_level=confidence,
        rng=np.random.default_rng(rng),
    )

    delta = mean_difference(pr, baseline)
    interval = result.confidence_interval
    return float(delta), float(interval.low), float(interval.high)


def _validate_pass_args(n: int, c: int, k: int) -> None:
    if not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError("Expected 0 <= c <= n and 1 <= k <= n")


def pass_at_k(n: int, c: int, k: int) -> float:
    """Xác suất ít nhất một trong k lượt được chọn đạt."""
    _validate_pass_args(n, c, k)
    total = comb(n, k)
    all_failed = comb(n - c, k)
    return (total - all_failed) / total


def pass_hat_k(n: int, c: int, k: int) -> float:
    """Xác suất cả k lượt được chọn đều đạt."""
    _validate_pass_args(n, c, k)
    return comb(c, k) / comb(n, k)
