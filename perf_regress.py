#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np
from scipy import stats

from constants import (
    MS_FLOOR,
    PCT_FLOOR,
    TAIL_QUANTILE,
    TAIL_MS_FLOOR,
    TAIL_PCT_FLOOR,
    DIRECTIONALITY,
    USE_WILCOXON,
    WILCOXON_ALPHA,
    BOOTSTRAP_CONFIDENCE,
    BOOTSTRAP_N,
    SEED,
    EQUIVALENCE_MARGIN_MS,
    TWO_SIDED_TEST_DIVISOR,
    ENABLE_QUALITY_GATES,
    MAX_CV_FOR_REGRESSION_CHECK,
    MIN_QUALITY_SCORE_FOR_REGRESSION,
    CV_THRESHOLD_MULTIPLIER,
    MIN_SAMPLES_FOR_REGRESSION,
    PCT_CONVERSION_FACTOR,
)


@dataclass
class GateResult:
    """Result from gate_regression check.

    Attributes:
        passed: True if no regression detected, False if regression detected
        reason: Human-readable explanation of the result
        details: Dictionary containing all metrics and analysis details
        inconclusive: True if data quality is too poor to make a reliable determination
    """
    passed: bool
    reason: str
    details: Dict[str, Any]
    inconclusive: bool = False  # New field for quality gate failures


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


def _calculate_cv(data: np.ndarray) -> float:
    """
    Calculate coefficient of variation (CV) as percentage.

    CV = (std_dev / mean) * 100

    Args:
        data: Array of measurements

    Returns:
        CV as percentage (e.g., 15.5 for 15.5%)
    """
    mean_val = np.mean(data)
    if mean_val == 0:
        return 0.0
    std_val = np.std(data, ddof=1)  # Sample std dev
    return float((std_val / mean_val) * PCT_CONVERSION_FACTOR)


def _check_quality_gates(
    baseline: np.ndarray,
    change: np.ndarray,
    enable_gates: bool = ENABLE_QUALITY_GATES,
    max_cv: float = MAX_CV_FOR_REGRESSION_CHECK,
    min_samples: int = MIN_SAMPLES_FOR_REGRESSION,
) -> Optional[str]:
    """
    Check if data quality is sufficient for regression detection.

    Args:
        baseline: Baseline measurements
        change: Change measurements
        enable_gates: Whether to enforce quality gates
        max_cv: Maximum allowed coefficient of variation (%)
        min_samples: Minimum required sample size

    Returns:
        None if quality is acceptable, otherwise error message explaining why data is rejected
    """
    if not enable_gates:
        return None

    n = len(baseline)

    # Gate 1: Sample size
    if n < min_samples:
        return (
            f"INSUFFICIENT SAMPLES: Only {n} measurements (minimum {min_samples} required). "
            f"Results would be unreliable. Collect more data and re-run."
        )

    # Gate 2: Coefficient of variation
    baseline_cv = _calculate_cv(baseline)
    change_cv = _calculate_cv(change)
    max_observed_cv = max(baseline_cv, change_cv)

    if max_observed_cv > max_cv:
        return (
            f"HIGH VARIANCE: CV = {max_observed_cv:.1f}% exceeds maximum {max_cv:.1f}%. "
            f"Measurements are too noisy for reliable regression detection. "
            f"Use interleaved testing and control environment (see MEASUREMENT_GUIDE.md). "
            f"Target: CV < {max_cv:.1f}%"
        )

    return None


def gate_regression(
    baseline: List[float],
    change: List[float],
    ms_floor: float = MS_FLOOR,
    pct_floor: float = PCT_FLOOR,
    tail_quantile: float = TAIL_QUANTILE,
    tail_ms_floor: float = TAIL_MS_FLOOR,
    tail_pct_floor: float = TAIL_PCT_FLOOR,
    directionality: float = DIRECTIONALITY,
    use_wilcoxon: bool = USE_WILCOXON,
    wilcoxon_alpha: float = WILCOXON_ALPHA,
    bootstrap_confidence: float = BOOTSTRAP_CONFIDENCE,
    bootstrap_n: int = BOOTSTRAP_N,
    seed: int = SEED,
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
            details={},
            inconclusive=False
        )

    if len(a) == 0:
        return GateResult(
            passed=False,
            reason="Empty arrays",
            details={},
            inconclusive=False
        )

    # Check quality gates FIRST - reject if data quality is too poor
    quality_gate_error = _check_quality_gates(a, b)
    if quality_gate_error:
        return GateResult(
            passed=True,  # Don't fail the build - data is inconclusive
            reason=f"INCONCLUSIVE: {quality_gate_error}",
            details={
                "baseline_cv": _calculate_cv(a),
                "change_cv": _calculate_cv(b),
                "sample_size": len(a),
            },
            inconclusive=True
        )

    delta = b - a
    median_delta = float(np.median(delta))
    baseline_median = float(np.median(a))

    # Calculate CV for adaptive thresholds
    baseline_cv = _calculate_cv(a)
    change_cv = _calculate_cv(b)
    max_cv = max(baseline_cv, change_cv)

    # Apply CV-based threshold multiplier
    # When variance is elevated (but acceptable), be more conservative
    # Formula: effective_threshold = base_threshold * (1 + CV_THRESHOLD_MULTIPLIER * CV/100)
    cv_multiplier = 1.0 + (CV_THRESHOLD_MULTIPLIER * max_cv / PCT_CONVERSION_FACTOR)

    # Calculate threshold (max of absolute and relative)
    # For very small baseline values (<< ms_floor), the relative threshold
    # (pct_floor * baseline_median) will be tiny, so ms_floor dominates.
    # This is intentional - we want a minimum absolute threshold even for
    # very fast operations to avoid flagging insignificant noise.
    # NOW: Apply CV multiplier to make threshold stricter when variance is high
    base_threshold = max(ms_floor, pct_floor * baseline_median)
    threshold = base_threshold * cv_multiplier

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
    # Apply same CV multiplier to make tail check consistent with median
    base_tail_threshold = max(tail_ms_floor, tail_pct_floor * baseline_tail)
    tail_threshold = base_tail_threshold * cv_multiplier

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
        "base_threshold_ms": base_threshold,
        "median_delta_ms": median_delta,
        "tail_threshold_ms": tail_threshold,
        "base_tail_threshold_ms": base_tail_threshold,
        "tail_delta_ms": tail_delta,
        "positive_fraction": positive_fraction,
        "baseline_cv": baseline_cv,
        "change_cv": change_cv,
        "cv_multiplier": cv_multiplier,
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
        ci_low = float(np.quantile(boot_medians, alpha / TWO_SIDED_TEST_DIVISOR, method="linear"))
        ci_high = float(np.quantile(boot_medians, 1 - alpha / TWO_SIDED_TEST_DIVISOR, method="linear"))

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
    margin_ms: float = EQUIVALENCE_MARGIN_MS,
    confidence: float = BOOTSTRAP_CONFIDENCE,
    n_boot: int = BOOTSTRAP_N,
    seed: int = SEED,
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
