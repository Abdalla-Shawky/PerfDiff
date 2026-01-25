#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np
from scipy import stats


@dataclass
class GateResult:
    """Result from gate_regression check."""
    passed: bool
    reason: str
    details: Dict[str, Any]


@dataclass
class BootstrapCI:
    """Bootstrap confidence interval."""
    ci_low: float
    ci_high: float


@dataclass
class EquivalenceResult:
    """Result from equivalence test."""
    equivalent: bool
    ci: BootstrapCI


def gate_regression(
    baseline: List[float],
    change: List[float],
    ms_floor: float = 50.0,
    pct_floor: float = 0.05,
    tail_quantile: float = 0.90,
    tail_ms_floor: float = 75.0,
    tail_pct_floor: float = 0.05,
    directionality: float = 0.70,
    use_wilcoxon: bool = True,
    wilcoxon_alpha: float = 0.05,
    bootstrap_confidence: float = 0.95,
    bootstrap_n: int = 5000,
    seed: int = 0,
) -> GateResult:
    """
    Gate regression check for performance testing.

    Args:
        baseline: Baseline measurements
        change: Change measurements
        ms_floor: Absolute threshold in milliseconds for median
        pct_floor: Relative threshold as fraction for median (e.g., 0.05 = 5%)
        tail_quantile: Quantile for tail check (e.g., 0.90 = p90)
        tail_ms_floor: Absolute threshold for tail in milliseconds
        tail_pct_floor: Relative threshold as fraction for tail (e.g., 0.05 = 5%)
        directionality: Fraction of positive deltas required (e.g., 0.70 = 70%)
        use_wilcoxon: Whether to use Wilcoxon signed-rank test
        wilcoxon_alpha: Significance level for Wilcoxon test
        bootstrap_confidence: Confidence level for bootstrap CI
        bootstrap_n: Number of bootstrap samples
        seed: Random seed for reproducibility

    Returns:
        GateResult with passed status, reason, and details
    """
    # Use modern numpy random Generator API for better isolation
    rng = np.random.default_rng(seed)

    a = np.array(baseline, dtype=float)
    b = np.array(change, dtype=float)

    if len(a) != len(b):
        return GateResult(
            passed=False,
            reason="Baseline and change arrays must have same length",
            details={}
        )

    if len(a) == 0:
        return GateResult(
            passed=False,
            reason="Empty arrays",
            details={}
        )

    delta = b - a
    median_delta = float(np.median(delta))
    baseline_median = float(np.median(a))

    # Calculate threshold (max of absolute and relative)
    # For very small baseline values (<< ms_floor), the relative threshold
    # (pct_floor * baseline_median) will be tiny, so ms_floor dominates.
    # This is intentional - we want a minimum absolute threshold even for
    # very fast operations to avoid flagging insignificant noise.
    threshold = max(ms_floor, pct_floor * baseline_median)

    # Collect failures
    failures = []
    passed = True

    # Check 1: Median delta vs threshold
    if median_delta > threshold:
        failures.append(f"Median delta {median_delta:.2f}ms exceeds threshold {threshold:.2f}ms")
        passed = False

    # Check 2: Tail (p90) check
    baseline_tail = float(np.quantile(a, tail_quantile, method="linear"))
    change_tail = float(np.quantile(b, tail_quantile, method="linear"))
    tail_delta = change_tail - baseline_tail

    # Calculate tail threshold (max of absolute and relative)
    # Similar to median threshold, uses max of absolute and relative to handle
    # both fast and slow operations appropriately
    tail_threshold = max(tail_ms_floor, tail_pct_floor * baseline_tail)

    if tail_delta > tail_threshold:
        failures.append(f"Tail delta {tail_delta:.2f}ms exceeds threshold {tail_threshold:.2f}ms")
        passed = False

    # Check 3: Directionality
    positive_fraction = float(np.mean(delta > 0))
    if positive_fraction >= directionality:
        failures.append(f"{positive_fraction*100:.1f}% of runs slower (>= {directionality*100:.1f}% threshold)")
        passed = False

    details: Dict[str, Any] = {
        "threshold_ms": threshold,
        "median_delta_ms": median_delta,
        "tail_threshold_ms": tail_threshold,
        "tail_delta_ms": tail_delta,
        "positive_fraction": positive_fraction,
    }

    # Wilcoxon signed-rank test
    if use_wilcoxon and len(delta) > 0:
        # Remove zeros for Wilcoxon test
        delta_nonzero = delta[delta != 0]
        if len(delta_nonzero) > 0:
            try:
                res = stats.wilcoxon(delta_nonzero, alternative='greater', method='approx')
                p_greater = res.pvalue
                # Use z-statistic from approx method if available
                z_score = res.zstatistic if hasattr(res, 'zstatistic') else None

                # Two-sided test
                res_two = stats.wilcoxon(delta_nonzero, alternative='two-sided', method='approx')
                p_two_sided = res_two.pvalue

                wilcox_data = {
                    "n": len(delta_nonzero),
                    "p_greater": float(p_greater),
                    "p_two_sided": float(p_two_sided),
                }
                if z_score is not None:
                    wilcox_data["z"] = float(z_score)

                details["wilcoxon"] = wilcox_data

                if p_greater < wilcoxon_alpha:
                    passed = False
                    failures.append(f"Wilcoxon test significant (p={p_greater:.4f} < {wilcoxon_alpha})")
            except Exception as e:
                details["wilcoxon_error"] = str(e)

    # Build final reason string
    if passed:
        reason = f"PASS: Median delta {median_delta:.2f}ms within threshold {threshold:.2f}ms"
    else:
        reason = "FAIL: " + "; ".join(failures)

    # Bootstrap CI for median delta
    if bootstrap_n > 0:
        boot_medians = []
        n = len(delta)
        for _ in range(bootstrap_n):
            indices = rng.choice(n, size=n, replace=True)
            boot_delta = delta[indices]
            boot_medians.append(np.median(boot_delta))

        boot_medians = np.array(boot_medians)
        alpha = 1 - bootstrap_confidence
        ci_low = float(np.quantile(boot_medians, alpha / 2, method="linear"))
        ci_high = float(np.quantile(boot_medians, 1 - alpha / 2, method="linear"))

        details["bootstrap_ci_median"] = {
            "confidence": bootstrap_confidence,
            "low": ci_low,
            "high": ci_high,
            "n_boot": bootstrap_n,
        }

    return GateResult(passed=passed, reason=reason, details=details)


def equivalence_bootstrap_median(
    baseline: List[float],
    change: List[float],
    margin_ms: float = 30.0,
    confidence: float = 0.95,
    n_boot: int = 5000,
    seed: int = 0,
) -> EquivalenceResult:
    """
    Test for equivalence using bootstrap CI on median delta.

    Two distributions are considered equivalent if the bootstrap confidence
    interval for the median delta falls entirely within [-margin_ms, margin_ms].

    Args:
        baseline: Baseline measurements
        change: Change measurements
        margin_ms: Equivalence margin in milliseconds
        confidence: Confidence level for bootstrap CI
        n_boot: Number of bootstrap samples
        seed: Random seed for reproducibility

    Returns:
        EquivalenceResult with equivalent status and CI

    Raises:
        ValueError: If arrays are empty, mismatched lengths, or invalid parameters
    """
    # Input validation
    if len(baseline) == 0 or len(change) == 0:
        raise ValueError("Baseline and change arrays cannot be empty")

    if len(baseline) != len(change):
        raise ValueError(f"Array length mismatch: baseline has {len(baseline)} elements, change has {len(change)} elements")

    if margin_ms <= 0:
        raise ValueError(f"margin_ms must be positive, got {margin_ms}")

    if not (0 < confidence < 1):
        raise ValueError(f"confidence must be between 0 and 1, got {confidence}")

    if n_boot <= 0:
        raise ValueError(f"n_boot must be positive, got {n_boot}")

    # Use modern numpy random Generator API for better isolation
    rng = np.random.default_rng(seed)

    a = np.array(baseline, dtype=float)
    b = np.array(change, dtype=float)
    delta = b - a

    # Bootstrap CI for median delta
    boot_medians = []
    n = len(delta)
    for _ in range(n_boot):
        indices = rng.choice(n, size=n, replace=True)
        boot_delta = delta[indices]
        boot_medians.append(np.median(boot_delta))

    boot_medians = np.array(boot_medians)
    alpha = 1 - confidence
    ci_low = float(np.quantile(boot_medians, alpha / 2, method="linear"))
    ci_high = float(np.quantile(boot_medians, 1 - alpha / 2, method="linear"))

    # Check if entire CI is within [-margin, margin]
    equivalent = (ci_low > -margin_ms) and (ci_high < margin_ms)

    return EquivalenceResult(
        equivalent=equivalent,
        ci=BootstrapCI(ci_low=ci_low, ci_high=ci_high)
    )
