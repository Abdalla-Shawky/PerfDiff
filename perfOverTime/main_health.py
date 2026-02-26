#!/usr/bin/env python3
from __future__ import annotations

import sys
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

import numpy as np

# Add parent directory to path for shared modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import (
    MS_FLOOR,
    PCT_FLOOR,
    HEALTH_WINDOW,
    HEALTH_CONTROL_K,
    HEALTH_MIN_MAD,
    HEALTH_DIRECTION,
    HEALTH_EWMA_ALPHA,
    HEALTH_EWMA_K,
    HEALTH_STEP_SCAN_BACK,
    HEALTH_STEP_MIN_SEGMENT,
    HEALTH_STEP_SCORE_K,
    HEALTH_STEP_PCT_THRESHOLD,
    HEALTH_EWMA_PCT_THRESHOLD,
    MAD_TO_SIGMA_SCALE,
    HEALTH_OUTLIER_DETECTION_ENABLED,
    HEALTH_OUTLIER_K,
)


# -----------------------------
# Helpers (robust stats)
# -----------------------------

def quantile_linear(x: np.ndarray, q: float) -> float:
    return float(np.quantile(x, q, method="linear"))


def rolling_median(x: np.ndarray) -> float:
    return float(np.median(x))


def mad(x: np.ndarray) -> float:
    """
    Median Absolute Deviation (MAD), unscaled.
    Robust scale estimate is ~ 1.4826 * MAD for normal data.
    """
    med = np.median(x)
    return float(np.median(np.abs(x - med)))


def robust_sigma_from_mad(mad_val: float) -> float:
    return MAD_TO_SIGMA_SCALE * mad_val


def detect_outliers_rolling(
    series: List[float],
    window: int = HEALTH_WINDOW,
    k_outlier: float = HEALTH_OUTLIER_K,
    min_mad: float = HEALTH_MIN_MAD,
) -> List[int]:
    """
    Detect outliers in time series using rolling window + MAD.

    This uses a time-series aware approach that adapts to changing baselines,
    unlike static IQR which would mark post-regression values as outliers.

    For each point i, we look at the last 'window' points before it as baseline,
    then check if point i is an outlier relative to that baseline using MAD.

    Args:
        series: Time-series data (e.g., daily P50 metrics)
        window: Rolling window size for baseline (default: HEALTH_WINDOW)
        k_outlier: Sigma multiplier for outlier threshold (default: 3.5, more lenient than control chart k=4.0)
        min_mad: Minimum MAD to prevent division by zero (default: HEALTH_MIN_MAD)

    Returns:
        List of indices where outliers detected (e.g., [30, 45] means points at index 30 and 45 are outliers)

    Example:
        >>> series = [100]*30 + [200] + [100]*20  # Spike at index 30
        >>> outliers = detect_outliers_rolling(series)
        >>> outliers
        [30]  # Only the spike is marked as outlier
    """
    # Check if outlier detection is disabled
    if not HEALTH_OUTLIER_DETECTION_ENABLED:
        return []

    if len(series) < window:
        return []

    x = np.asarray(series, dtype=float)
    outlier_indices = []

    for i in range(window, len(x)):
        # Use last 'window' points before i as baseline
        baseline = x[i - window:i]
        base_med = float(np.median(baseline))
        base_mad = max(mad(baseline), min_mad)
        sigma = robust_sigma_from_mad(base_mad)

        # Check if current point is outlier
        z_score = abs(x[i] - base_med) / sigma if sigma > 0 else 0
        if z_score > k_outlier:
            outlier_indices.append(i)

    return outlier_indices


def detect_outliers_in_window(
    window_data: np.ndarray,
    k_outlier: float = HEALTH_OUTLIER_K,
    min_mad: float = HEALTH_MIN_MAD,
) -> List[int]:
    """
    Detect outliers within a single window of data.

    Args:
        window_data: Array of values within the window
        k_outlier: Sigma multiplier for outlier threshold
        min_mad: Minimum MAD to prevent division by zero

    Returns:
        List of indices (within the window) that are outliers

    Example:
        >>> window = np.array([100, 100, 500, 100, 100])
        >>> outliers = detect_outliers_in_window(window)
        >>> outliers
        [2]  # Index 2 (value 500) is an outlier
    """
    if not HEALTH_OUTLIER_DETECTION_ENABLED or len(window_data) < 3:
        return []

    window_median = float(np.median(window_data))
    window_mad = max(mad(window_data), min_mad)
    sigma = robust_sigma_from_mad(window_mad)

    outlier_indices = []
    for i, val in enumerate(window_data):
        z_score = abs(val - window_median) / sigma if sigma > 0 else 0
        if z_score > k_outlier:
            outlier_indices.append(i)

    return outlier_indices


# -----------------------------
# Models
# -----------------------------

@dataclass(frozen=True)
class ControlChartResult:
    alert: bool
    reason: str
    baseline_median: float
    baseline_mad: float
    robust_sigma: float
    upper_bound: float
    lower_bound: float
    value: float
    robust_z: float


@dataclass(frozen=True)
class EwmaResult:
    alert: bool
    reason: str
    ewma: float
    upper_bound: float
    lower_bound: float
    value: float


@dataclass(frozen=True)
class StepFitResult:
    found: bool
    reason: str
    change_index: Optional[int]          # index in the *series* where step occurs
    before_median: Optional[float]
    after_median: Optional[float]
    delta: Optional[float]
    score: Optional[float]              # larger is stronger
    window: Tuple[int, int]             # [start, end) scan region used


@dataclass(frozen=True)
class LinearTrendResult:
    alert: bool
    reason: str
    slope: float                        # ms per data point
    slope_pct_per_point: float          # percentage increase per point
    total_change_pct: float             # total percentage change across series
    r_squared: float                    # goodness of fit (0-1)
    p_value: float                      # statistical significance


@dataclass(frozen=True)
class HealthReport:
    control: Optional[ControlChartResult]
    ewma: Optional[EwmaResult]
    stepfit: Optional[StepFitResult]
    trend: Optional[LinearTrendResult]
    overall_alert: bool
    details: Dict[str, Any]


# -----------------------------
# Control chart (median + MAD)
# -----------------------------

def control_chart_median_mad(
    series: List[float],
    window: int = HEALTH_WINDOW,
    k: float = HEALTH_CONTROL_K,
    abs_floor: float = MS_FLOOR,
    pct_floor: float = PCT_FLOOR,
    min_mad: float = HEALTH_MIN_MAD,
    direction: str = HEALTH_DIRECTION,
) -> Optional[ControlChartResult]:
    """
    Median-only robust control chart.
    Alerts if latest point exceeds baseline by:
      - robust z > k (based on MAD)
      - AND exceeds absolute/percent floor (practical significance)
    """
    # Parameter validation
    if window < 5:
        raise ValueError("window must be >= 5")
    if k <= 0:
        raise ValueError("k must be positive")
    if abs_floor < 0:
        raise ValueError("abs_floor must be non-negative")
    if not (0 < pct_floor < 1):
        raise ValueError("pct_floor must be in (0, 1)")
    if min_mad <= 0:
        raise ValueError("min_mad must be positive")
    if direction not in ("regression", "both"):
        raise ValueError("direction must be 'regression' or 'both'")

    if len(series) < window + 1:
        return None

    x = np.asarray(series, dtype=float)
    if np.any(~np.isfinite(x)):
        raise ValueError("series contains non-finite values")

    value = float(x[-1])
    baseline = x[-(window + 1):-1]  # exclude latest
    base_med = rolling_median(baseline)
    base_mad = max(mad(baseline), min_mad)
    sigma = robust_sigma_from_mad(base_mad)

    # Bounds
    upper = base_med + k * sigma
    lower = base_med - k * sigma

    # Robust z
    robust_z = (value - base_med) / sigma if sigma > 0 else 0.0

    # Practical threshold (absolute + relative)
    practical = max(abs_floor, pct_floor * base_med)
    exceeds_practical = (value - base_med) > practical

    if direction == "regression":
        exceeds_stat = value > upper
        alert = exceeds_stat and exceeds_practical
    elif direction == "both":
        exceeds_stat = (value > upper) or (value < lower)
        # Practical check should follow sign
        alert = exceeds_stat and (abs(value - base_med) > practical)
    else:
        raise ValueError("direction must be 'regression' or 'both'")

    reason = (
        f"{'ALERT' if alert else 'OK'}: value={value:.2f}, "
        f"baseline_median={base_med:.2f}, MAD={base_mad:.2f}, "
        f"sigma={sigma:.2f}, z={robust_z:.2f}, "
        f"bounds=[{lower:.2f}, {upper:.2f}], practical>{practical:.2f}"
    )

    return ControlChartResult(
        alert=alert,
        reason=reason,
        baseline_median=base_med,
        baseline_mad=base_mad,
        robust_sigma=sigma,
        upper_bound=upper,
        lower_bound=lower,
        value=value,
        robust_z=float(robust_z),
    )


# -----------------------------
# EWMA (creep detector)
# -----------------------------

def ewma_monitor(
    series: List[float],
    window: int = HEALTH_WINDOW,
    alpha: float = HEALTH_EWMA_ALPHA,
    k: float = HEALTH_EWMA_K,
    abs_floor: float = MS_FLOOR,
    pct_floor: float = PCT_FLOOR,
    min_mad: float = HEALTH_MIN_MAD,
    direction: str = HEALTH_DIRECTION,
    ewma_pct_threshold: Optional[float] = HEALTH_EWMA_PCT_THRESHOLD,
) -> Optional[EwmaResult]:
    """
    EWMA on the median-only series with outlier filtering.

    Uses baseline median/MAD from last window points (excluding latest) to set bounds,
    detects outliers across the full series using rolling window approach, then
    computes EWMA through the entire series while skipping detected outliers.

    Outliers are detected using MAD-based z-score (k=3.5σ) and excluded from the
    exponential smoothing to prevent skewed trend detection.

    This is a practical EWMA; it uses sigma from robust MAD, not classic EWMA variance.
    """
    # Parameter validation
    if not (0 < alpha <= 1.0):
        raise ValueError("alpha must be in (0, 1]")
    if window < 5:
        raise ValueError("window must be >= 5")
    if k <= 0:
        raise ValueError("k must be positive")
    if abs_floor < 0:
        raise ValueError("abs_floor must be non-negative")
    if not (0 < pct_floor < 1):
        raise ValueError("pct_floor must be in (0, 1)")
    if min_mad <= 0:
        raise ValueError("min_mad must be positive")
    if direction not in ("regression", "both"):
        raise ValueError("direction must be 'regression' or 'both'")

    if len(series) < window + 2:
        return None

    x = np.asarray(series, dtype=float)
    if np.any(~np.isfinite(x)):
        raise ValueError("series contains non-finite values")

    value = float(x[-1])
    baseline = x[-(window + 1):-1]
    base_med = float(np.median(baseline))
    base_mad = max(mad(baseline), min_mad)
    sigma = robust_sigma_from_mad(base_mad)

    # Detect outliers in the full series using rolling window approach
    # This catches outliers after the initial window period
    outlier_indices_rolling = detect_outliers_rolling(
        series, window=window, k_outlier=HEALTH_OUTLIER_K, min_mad=min_mad
    )

    # Also detect outliers within the baseline window itself
    # This catches outliers in the early part where rolling detection doesn't reach
    outlier_indices_baseline = detect_outliers_in_window(baseline)
    # Convert baseline indices to full series indices
    baseline_start = len(x) - window - 1
    outlier_indices_baseline_adjusted = [baseline_start + i for i in outlier_indices_baseline]

    # Combine both outlier sets
    outlier_set = set(outlier_indices_rolling) | set(outlier_indices_baseline_adjusted)

    # Compute EWMA over the full series (skipping outliers)
    # Initialize with baseline median for stability
    s = base_med
    for i, v in enumerate(x):
        # Skip outliers when computing EWMA to avoid skewing the trend
        if i not in outlier_set:
            s = alpha * float(v) + (1.0 - alpha) * s

    # Bounds around baseline median (robust)
    upper = base_med + k * sigma
    lower = base_med - k * sigma

    practical = max(abs_floor, pct_floor * base_med)

    # Calculate EWMA drift percentage from baseline for dual-threshold detection
    ewma_drift_pct = abs(s - base_med) / abs(base_med) * 100 if base_med != 0 else 0

    # Statistical alarm (existing logic)
    if direction == "regression":
        statistical_alarm = (s > upper) and ((s - base_med) > practical)
    elif direction == "both":
        statistical_alarm = ((s > upper) or (s < lower)) and (abs(s - base_med) > practical)
    else:
        raise ValueError("direction must be 'regression' or 'both'")

    # Practical drift alarm (percentage-based, only upward for regression)
    drift_alarm = (ewma_pct_threshold is not None and
                  ewma_drift_pct >= ewma_pct_threshold and
                  s > base_med)

    # Dual criteria: trigger if EITHER condition met
    alert = statistical_alarm or drift_alarm

    # Build reason string showing which threshold(s) triggered
    if alert:
        reason = f"ALERT: ewma={s:.2f}, baseline_median={base_med:.2f}"
        if statistical_alarm:
            reason += f" (exceeds bounds=[{lower:.2f}, {upper:.2f}])"
        if drift_alarm:
            reason += f" (drift={ewma_drift_pct:.1f}%≥{ewma_pct_threshold}%)"
    else:
        reason = (
            f"OK: ewma={s:.2f}, value={value:.2f}, "
            f"baseline_median={base_med:.2f}, sigma={sigma:.2f}, "
            f"bounds=[{lower:.2f}, {upper:.2f}], drift={ewma_drift_pct:.1f}%"
        )

    return EwmaResult(
        alert=alert,
        reason=reason,
        ewma=float(s),
        upper_bound=float(upper),
        lower_bound=float(lower),
        value=value,
    )


# -----------------------------
# Step-fit (simple, median-only)
# -----------------------------

def _refine_changepoint_to_largest_jump(
    series: List[float],
    statistical_index: int,
    search_radius: int = 10,
) -> int:
    """
    Refine a statistical changepoint to find the actual regression commit.

    The step_fit algorithm finds the best statistical split (maximizes median difference),
    but this may be a few points away from the actual commit that caused the regression.

    This function scans a window around the statistical split to find the index
    with the largest consecutive point-to-point jump, which is the actual commit
    that introduced the regression.

    Args:
        series: Full time series
        statistical_index: Initial changepoint from step_fit
        search_radius: How many points to search before/after the statistical index

    Returns:
        Refined index pointing to the CAUSING commit (where the regression was introduced)
    """
    n = len(series)

    # Define search window
    start = max(0, statistical_index - search_radius)
    end = min(n - 1, statistical_index + search_radius + 1)

    if end - start < 2:
        return statistical_index  # Not enough data to refine

    # Find the largest consecutive jump in the search window
    max_jump = 0.0
    max_jump_index = statistical_index

    for i in range(start, end - 1):
        jump = abs(series[i + 1] - series[i])
        if jump > max_jump:
            max_jump = jump
            max_jump_index = i + 1  # Return the CAUSING commit (where the regression was introduced)

    return max_jump_index


def step_fit(
    series: List[float],
    scan_back: Optional[int] = HEALTH_STEP_SCAN_BACK,
    min_segment: int = HEALTH_STEP_MIN_SEGMENT,
    abs_floor: float = MS_FLOOR,
    pct_floor: float = PCT_FLOOR,
    score_k: float = HEALTH_STEP_SCORE_K,
    min_mad: float = HEALTH_MIN_MAD,
    step_pct_threshold: Optional[float] = HEALTH_STEP_PCT_THRESHOLD,
    refine_to_largest_jump: bool = True,  # NEW: Enable changepoint refinement
) -> Optional[StepFitResult]:
    """
    Simple step-fit for median-only data.
    Scans candidate split points t and scores:
      score = |median(after) - median(before)| / robust_sigma(all)
    where sigma is from MAD of the scan window.

    Returns best change point if it exceeds:
      - abs + pct floors
      - score >= score_k

    Args:
      scan_back: Number of recent points to scan. None = scan entire series (recommended for exact commit detection)
      min_mad: Minimum MAD to prevent division by zero
      step_pct_threshold: Percentage change threshold for practical alarm (e.g., 20.0 for 20%)
      refine_to_largest_jump: If True, refine changepoint to the largest consecutive jump (actual regression commit)
    """
    # Parameter validation
    if scan_back is not None and scan_back <= 0:
        raise ValueError("scan_back must be positive or None")
    if min_segment <= 0:
        raise ValueError("min_segment must be positive")
    if abs_floor < 0:
        raise ValueError("abs_floor must be non-negative")
    if not (0 < pct_floor < 1):
        raise ValueError("pct_floor must be in (0, 1)")
    if score_k <= 0:
        raise ValueError("score_k must be positive")

    n = len(series)
    if n < (2 * min_segment + 1):
        return None

    x_full = np.asarray(series, dtype=float)
    if np.any(~np.isfinite(x_full)):
        raise ValueError("series contains non-finite values")

    # If scan_back is None, scan the entire series
    end = n
    start = 0 if scan_back is None else max(0, end - scan_back)
    x = x_full[start:end]
    m = x.size

    if m < (2 * min_segment + 1):
        return None

    # Robust sigma across scan window
    sigma = robust_sigma_from_mad(max(mad(x), min_mad))
    base_med = float(np.median(x))

    best_score = -1.0
    best_t = None
    best_before = None
    best_after = None
    best_delta = None

    # Candidate split positions in scan window coordinates
    for t in range(min_segment, m - min_segment):
        before = x[:t]
        after = x[t:]

        med_b = float(np.median(before))
        med_a = float(np.median(after))
        delta = med_a - med_b

        # Practical threshold based on local baseline (use median of before)
        practical = max(abs_floor, pct_floor * med_b)

        if abs(delta) <= practical:
            continue

        score = abs(delta) / sigma if sigma > 0 else 0.0
        if score > best_score:
            best_score = score
            best_t = t
            best_before = med_b
            best_after = med_a
            best_delta = delta

    if best_t is None:
        return StepFitResult(
            found=False,
            reason="No step found exceeding floors.",
            change_index=None,
            before_median=None,
            after_median=None,
            delta=None,
            score=None,
            window=(start, end),
        )

    # Calculate percentage change for dual-threshold detection
    pct_change = abs(best_delta) / abs(best_before) * 100 if best_before != 0 else 0

    # Dual criteria: statistical (score-based) OR practical (percentage-based)
    statistical_alarm = best_score >= score_k
    practical_alarm = (step_pct_threshold is not None and
                      pct_change >= step_pct_threshold)

    found = statistical_alarm or practical_alarm

    # Calculate initial change_index (statistical split)
    initial_change_index = int(start + best_t)

    # Refine changepoint to largest jump if requested
    if found and refine_to_largest_jump:
        refined_index = _refine_changepoint_to_largest_jump(
            series=list(x_full),
            statistical_index=initial_change_index,
            search_radius=10
        )
        change_index = refined_index

        # Add refinement info to reason if the index changed
        if refined_index != initial_change_index:
            refinement_note = f" → refined to idx={refined_index} (largest jump)"
        else:
            refinement_note = ""
    else:
        change_index = initial_change_index
        refinement_note = ""

    # Build reason string showing which threshold(s) triggered
    if found:
        reason = f"FOUND step: idx={change_index}, before={best_before:.2f}, after={best_after:.2f}, delta={best_delta:.2f}"
        if statistical_alarm:
            reason += f" (score={best_score:.2f}≥{score_k})"
        if practical_alarm:
            reason += f" ({pct_change:.1f}%≥{step_pct_threshold}%)"
        reason += f", scan_window=[{start},{end}){refinement_note}"
    else:
        reason = (
            f"WEAK step: idx={initial_change_index}, "
            f"before={best_before:.2f}, after={best_after:.2f}, "
            f"delta={best_delta:.2f}, score={best_score:.2f}, "
            f"scan_window=[{start},{end})"
        )

    return StepFitResult(
        found=found,
        reason=reason,
        change_index=change_index,
        before_median=float(best_before),
        after_median=float(best_after),
        delta=float(best_delta),
        score=float(best_score),
        window=(start, end),
    )


# -----------------------------
# Linear trend detection
# -----------------------------

def detect_linear_trend(
    series: List[float],
    slope_pct_threshold: float = 3.0,    # % increase per point
    total_pct_threshold: float = 5.0,    # total % increase threshold
    min_r_squared: float = 0.7,          # minimum goodness of fit
    p_value_threshold: float = 0.05,     # significance level
) -> LinearTrendResult:
    """
    Detect gradual linear trends using linear regression.

    This complements EWMA/Control Chart by detecting gradual creep patterns
    that don't trigger threshold-based alerts.

    Args:
        series: Time series data
        slope_pct_threshold: Alert if slope exceeds this % per point
        total_pct_threshold: Alert if total change exceeds this %
        min_r_squared: Minimum R² for good linear fit (0-1)
        p_value_threshold: Maximum p-value for statistical significance

    Returns:
        LinearTrendResult with alert status and statistics
    """
    from scipy import stats

    if len(series) < 3:
        return LinearTrendResult(
            alert=False,
            reason="Insufficient data for trend detection (n<3)",
            slope=0.0,
            slope_pct_per_point=0.0,
            total_change_pct=0.0,
            r_squared=0.0,
            p_value=1.0,
        )

    # Perform linear regression
    x = np.arange(len(series))
    y = np.array(series)
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    # Calculate statistics
    r_squared = r_value ** 2
    first_value = series[0]
    last_value = series[-1]

    # Slope as percentage per point
    slope_pct_per_point = (slope / first_value * 100) if first_value != 0 else 0

    # Total change percentage
    total_change_pct = ((last_value - first_value) / first_value * 100) if first_value != 0 else 0

    # Determine if alert should be raised
    alert = False
    reason_parts = []

    # Check if slope is positive and significant
    if slope > 0:
        # Check statistical significance
        if p_value > p_value_threshold:
            reason_parts.append(f"not significant (p={p_value:.4f})")

        # Check goodness of fit
        if r_squared < min_r_squared:
            reason_parts.append(f"poor fit (R²={r_squared:.3f})")

        # Check slope threshold
        if abs(slope_pct_per_point) >= slope_pct_threshold:
            reason_parts.append(f"slope {slope_pct_per_point:.2f}%/pt ≥ {slope_pct_threshold}%")
            if p_value <= p_value_threshold and r_squared >= min_r_squared:
                alert = True

        # Check total change threshold
        if total_change_pct >= total_pct_threshold:
            reason_parts.append(f"total Δ {total_change_pct:.1f}% ≥ {total_pct_threshold}%")
            if p_value <= p_value_threshold and r_squared >= min_r_squared:
                alert = True
    else:
        reason_parts.append(f"negative/flat slope ({slope:.4f} ms/pt)")

    # Build reason string
    if alert:
        reason = f"TREND DETECTED: {', '.join(reason_parts)}"
    else:
        if not reason_parts:
            reason = "OK: no significant upward trend"
        else:
            reason = f"OK: {', '.join(reason_parts)}"

    return LinearTrendResult(
        alert=alert,
        reason=reason,
        slope=float(slope),
        slope_pct_per_point=float(slope_pct_per_point),
        total_change_pct=float(total_change_pct),
        r_squared=float(r_squared),
        p_value=float(p_value),
    )


# -----------------------------
# Combined "main health" report
# -----------------------------

def _calculate_adaptive_parameters(series_length: int) -> dict:
    """
    Calculate adaptive parameters based on series length.

    For short series: Use smaller windows and lower thresholds
    For long series: Use standard parameters

    Args:
        series_length: Number of data points in the series

    Returns:
        Dictionary with optimal window, ewma_pct_threshold, and step_min_segment
    """
    if series_length < 15:
        # Very short series (10-14 points)
        # Challenge: Almost no stable baseline possible
        # Note: window must be >= 5 due to control_chart_median_mad constraint
        return {
            'window': 5,
            'ewma_pct_threshold': 3.0,  # 3% drift
            'step_min_segment': 3,
            'step_score_k': 1.5,  # Very low threshold for noisy short series
            'trend_total_pct_threshold': 2.0,  # 2% total change
            'trend_slope_pct_threshold': 1.5,  # 1.5%/point
            'description': 'Very short series - aggressive detection'
        }
    elif series_length < 30:
        # Short series (15-29 points)
        return {
            'window': 5,
            'ewma_pct_threshold': 5.0,  # 5% drift
            'step_min_segment': 4,
            'step_score_k': 2.0,  # Lower threshold for short series
            'trend_total_pct_threshold': 2.5,  # 2.5% total change
            'trend_slope_pct_threshold': 1.0,  # 1.0%/point
            'description': 'Short series - sensitive detection'
        }
    elif series_length < 50:
        # Medium series (30-49 points)
        return {
            'window': 10,
            'ewma_pct_threshold': 8.0,  # 8% drift
            'step_min_segment': 5,
            'step_score_k': 2.0,  # Lower threshold for potentially noisy data
            'trend_total_pct_threshold': 1.0,  # 1.0% total change (lowered for subtle noisy creep)
            'trend_slope_pct_threshold': 0.3,  # 0.3%/point (lowered for subtle creep)
            'description': 'Medium series - balanced detection'
        }
    elif series_length < 100:
        # Long series (50-99 points)
        return {
            'window': 20,
            'ewma_pct_threshold': 12.0,  # 12% drift
            'step_min_segment': 8,
            'step_score_k': 3.0,  # Moderate threshold
            'trend_total_pct_threshold': 3.0,  # 3.0% total change
            'trend_slope_pct_threshold': 1.5,  # 1.5%/point
            'description': 'Long series - standard detection'
        }
    else:
        # Very long series (100+ points)
        return {
            'window': 30,
            'ewma_pct_threshold': 15.0,  # Default
            'step_min_segment': 10,
            'step_score_k': 1.2,  # Lowered from 4.0 to catch steps in noisy data
            'trend_total_pct_threshold': 5.0,  # 5.0% total change (default)
            'trend_slope_pct_threshold': 3.0,  # 3.0%/point (default)
            'description': 'Very long series - balanced detection'
        }


def assess_main_health(
    series: List[float],
    window: Optional[int] = None,
    abs_floor: float = MS_FLOOR,
    pct_floor: float = PCT_FLOOR,
    k_mad: float = HEALTH_CONTROL_K,
    ewma_alpha: float = HEALTH_EWMA_ALPHA,
    ewma_k: float = HEALTH_EWMA_K,
    ewma_pct_threshold: Optional[float] = None,
    step_scan_back: Optional[int] = HEALTH_STEP_SCAN_BACK,
    step_min_segment: Optional[int] = None,
    step_score_k: Optional[float] = None,
    step_pct_threshold: Optional[float] = HEALTH_STEP_PCT_THRESHOLD,
    trend_total_pct_threshold: Optional[float] = None,
    trend_slope_pct_threshold: Optional[float] = None,
    adaptive: bool = True,
) -> HealthReport:
    """
    Runs:
      - control_chart_median_mad
      - ewma_monitor
      - step_fit (only to help triage; run always if enough data)
    and produces a unified report.

    Args:
      window: Baseline window size. If None and adaptive=True, calculated automatically.
      ewma_pct_threshold: EWMA drift percentage threshold (e.g., 15.0 for 15%).
                         If None and adaptive=True, calculated automatically.
      step_min_segment: Minimum segment size for step detection.
                       If None and adaptive=True, calculated automatically.
      step_score_k: Changepoint score threshold. If None and adaptive=True, calculated automatically.
                   Lower values = more sensitive (may detect noisier steps).
      step_pct_threshold: Step change percentage threshold (e.g., 20.0 for 20%)
      adaptive: If True (default), automatically calculates window, ewma_pct_threshold,
               step_min_segment, and step_score_k based on series length. Set to False to use
               explicit parameter values or constants from constants.py.
    """
    # Apply adaptive parameters if enabled
    if adaptive:
        adaptive_params = _calculate_adaptive_parameters(len(series))

        # Override with adaptive values if not explicitly provided
        if window is None:
            window = adaptive_params['window']
        if ewma_pct_threshold is None:
            ewma_pct_threshold = adaptive_params['ewma_pct_threshold']
        if step_min_segment is None:
            step_min_segment = adaptive_params['step_min_segment']
        if step_score_k is None:
            step_score_k = adaptive_params['step_score_k']
        if trend_total_pct_threshold is None:
            trend_total_pct_threshold = adaptive_params['trend_total_pct_threshold']
        if trend_slope_pct_threshold is None:
            trend_slope_pct_threshold = adaptive_params['trend_slope_pct_threshold']

        print(f"📊 Adaptive mode: {adaptive_params['description']}")
        print(f"   Series length: {len(series)}, Window: {window}, "
              f"EWMA threshold: {ewma_pct_threshold}%, Min segment: {step_min_segment}")
        print(f"   Step score threshold: {step_score_k}")
        print(f"   Trend thresholds: total={trend_total_pct_threshold}%, slope={trend_slope_pct_threshold}%/pt")
    else:
        # Non-adaptive mode: use defaults from constants if not provided
        if window is None:
            window = HEALTH_WINDOW
        if ewma_pct_threshold is None:
            ewma_pct_threshold = HEALTH_EWMA_PCT_THRESHOLD
        if step_min_segment is None:
            step_min_segment = HEALTH_STEP_MIN_SEGMENT
        if step_score_k is None:
            step_score_k = HEALTH_STEP_SCORE_K
        if trend_total_pct_threshold is None:
            trend_total_pct_threshold = 5.0  # Default
        if trend_slope_pct_threshold is None:
            trend_slope_pct_threshold = 3.0  # Default

    control = control_chart_median_mad(
        series, window=window, k=k_mad,
        abs_floor=abs_floor, pct_floor=pct_floor
    )

    ewma = ewma_monitor(
        series, window=window, alpha=ewma_alpha, k=ewma_k,
        abs_floor=abs_floor, pct_floor=pct_floor,
        ewma_pct_threshold=ewma_pct_threshold
    )

    step = step_fit(
        series, scan_back=step_scan_back, min_segment=step_min_segment,
        abs_floor=abs_floor, pct_floor=pct_floor, score_k=step_score_k,
        step_pct_threshold=step_pct_threshold
    )

    # Detect linear trends (gradual creep)
    trend = detect_linear_trend(
        series,
        total_pct_threshold=trend_total_pct_threshold,
        slope_pct_threshold=trend_slope_pct_threshold
    )

    overall_alert = bool(
        (control and control.alert) or
        (ewma and ewma.alert) or
        (step and step.found) or
        (trend and trend.alert)
    )

    details: Dict[str, Any] = {
        "n_points": len(series),
        "window": window,
        "abs_floor": abs_floor,
        "pct_floor": pct_floor,
        "k_mad": k_mad,
        "ewma_alpha": ewma_alpha,
        "ewma_k": ewma_k,
        "step_scan_back": step_scan_back,
        "step_min_segment": step_min_segment,
        "step_score_k": step_score_k,
    }

    return HealthReport(
        control=control,
        ewma=ewma,
        stepfit=step,
        trend=trend,
        overall_alert=overall_alert,
        details=details
    )


# -----------------------------
# CLI Interface
# -----------------------------

def main():
    """Command-line interface for main health monitoring."""
    import argparse
    import json
    import sys
    import os
    from datetime import datetime, UTC

    parser = argparse.ArgumentParser(
        description="Main Branch Health Monitoring - Detect regressions in time-series metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate HTML report with spike detection
  python3 main_health.py --series "[100,102,98,101,99,100,103,97,101,100,102,99,100,101,98,100,102,101,99,100,103,98,101,100,99,102,100,101,98,100,200]" --out health_report.html

  # Generate report with step change detection
  python3 main_health.py --series "[100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150,150]" --out step_report.html --abs-floor 10

  # Print to console (no HTML)
  python3 main_health.py --series "[100,102,98,101,...]"
        """
    )

    parser.add_argument(
        "--series",
        type=str,
        required=True,
        help="Time-series data as JSON array (e.g., '[100,102,98,101,...]')"
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output HTML file (e.g., 'health_report.html'). If not provided, prints to console."
    )
    parser.add_argument(
        "--window",
        type=int,
        default=HEALTH_WINDOW,
        help=f"Baseline window size (default: {HEALTH_WINDOW})"
    )
    parser.add_argument(
        "--abs-floor",
        type=float,
        default=MS_FLOOR,
        help=f"Absolute threshold in ms (default: {MS_FLOOR})"
    )
    parser.add_argument(
        "--pct-floor",
        type=float,
        default=PCT_FLOOR,
        help=f"Relative threshold as fraction (default: {PCT_FLOOR})"
    )
    parser.add_argument(
        "--direction",
        type=str,
        default=HEALTH_DIRECTION,
        choices=["regression", "both"],
        help=f"Alert direction: 'regression' (increases only) or 'both' (default: {HEALTH_DIRECTION})"
    )
    parser.add_argument(
        "--step-pct-threshold",
        type=float,
        default=None,
        help=f"Step change percentage threshold (e.g., 20.0 for 20%%). Set to override HEALTH_STEP_PCT_THRESHOLD (current: {HEALTH_STEP_PCT_THRESHOLD})"
    )
    parser.add_argument(
        "--ewma-pct-threshold",
        type=float,
        default=None,
        help=f"EWMA drift percentage threshold (e.g., 15.0 for 15%%). Set to override HEALTH_EWMA_PCT_THRESHOLD (current: {HEALTH_EWMA_PCT_THRESHOLD})"
    )
    parser.add_argument(
        "--step-scan-back",
        type=int,
        default=HEALTH_STEP_SCAN_BACK,
        help=f"Number of recent points to scan for changepoint. Default is None (scans entire series for exact commit detection). Set to a number (e.g., 120) to scan only recent points for faster analysis of large datasets."
    )

    args = parser.parse_args()

    # Parse series
    try:
        series = json.loads(args.series)
        if not isinstance(series, list):
            print("Error: --series must be a JSON array", file=sys.stderr)
            sys.exit(2)
        series = [float(x) for x in series]
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error parsing --series: {e}", file=sys.stderr)
        sys.exit(2)

    # Run health assessment with optional threshold overrides
    try:
        report = assess_main_health(
            series,
            window=args.window,
            abs_floor=args.abs_floor,
            pct_floor=args.pct_floor,
            step_scan_back=args.step_scan_back,
            ewma_pct_threshold=args.ewma_pct_threshold if args.ewma_pct_threshold is not None else HEALTH_EWMA_PCT_THRESHOLD,
            step_pct_threshold=args.step_pct_threshold if args.step_pct_threshold is not None else HEALTH_STEP_PCT_THRESHOLD,
        )
    except Exception as e:
        print(f"Error running health assessment: {e}", file=sys.stderr)
        sys.exit(2)

    # Determine overall status and regression index
    overall_status = "ALERT" if report.overall_alert else "OK"
    regression_index = report.stepfit.change_index if (report.stepfit and report.stepfit.found) else None

    # If --out specified, generate HTML report
    if args.out:
        from main_health_template import render_health_template

        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

        html_report = render_health_template(
            series=series,
            report=report,
            overall_status=overall_status,
            regression_index=regression_index,
            timestamp=timestamp,
        )

        # Create generated_reports folder if needed
        output_dir = "generated_reports"
        os.makedirs(output_dir, exist_ok=True)

        # Determine output path
        if os.path.dirname(args.out):
            output_path = args.out
        else:
            output_path = os.path.join(output_dir, args.out)

        # Write HTML report
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_report)

        print(f"✅ HTML report generated: {output_path}")
        print(f"   Status: {overall_status}")
        if regression_index is not None:
            print(f"   Regression started at index: {regression_index}")

        sys.exit(1 if report.overall_alert else 0)

    # Otherwise, print to console (backward compatibility)
    print("=" * 70)
    print("MAIN BRANCH HEALTH MONITORING REPORT")
    print("=" * 70)
    print()

    # Overall status
    if report.overall_alert:
        print("🚨 ALERT: Performance regression detected!")
    else:
        print("✅ OK: No performance regression detected")
    print()

    # Series info
    print(f"Series length: {len(series)} points")
    print(f"Latest value: {series[-1]:.2f}")
    if len(series) >= 2:
        print(f"Previous value: {series[-2]:.2f}")
    print()

    # Control Chart
    if report.control:
        print("--- Control Chart (Spike Detection) ---")
        print(f"Alert: {'YES' if report.control.alert else 'NO'}")
        print(f"Baseline median: {report.control.baseline_median:.2f}")
        print(f"Baseline MAD: {report.control.baseline_mad:.2f}")
        print(f"Robust z-score: {report.control.robust_z:.2f}")
        print(f"Bounds: [{report.control.lower_bound:.2f}, {report.control.upper_bound:.2f}]")
        print(f"Details: {report.control.reason}")
        print()

    # EWMA
    if report.ewma:
        print("--- EWMA (Trend Detection) ---")
        print(f"Alert: {'YES' if report.ewma.alert else 'NO'}")
        print(f"EWMA value: {report.ewma.ewma:.2f}")
        print(f"Bounds: [{report.ewma.lower_bound:.2f}, {report.ewma.upper_bound:.2f}]")
        print(f"Details: {report.ewma.reason}")
        print()

    # Step-Fit
    if report.stepfit:
        print("--- Step-Fit (Changepoint Detection) ---")
        if report.stepfit.found:
            print(f"⚠️  CHANGEPOINT DETECTED at index {report.stepfit.change_index}")
            print(f"   Before median: {report.stepfit.before_median:.2f}")
            print(f"   After median: {report.stepfit.after_median:.2f}")
            print(f"   Delta: {report.stepfit.delta:+.2f}")
            print(f"   Score: {report.stepfit.score:.2f}")
            print(f"   Scan window: {report.stepfit.window}")
        else:
            print("No changepoint detected")
        print(f"Details: {report.stepfit.reason}")
        print()

    # Summary
    print("=" * 70)
    if report.stepfit and report.stepfit.found:
        print(f"📍 REGRESSION STARTED AT: Index {report.stepfit.change_index}")
        print(f"   (This is data point #{report.stepfit.change_index + 1} in your series)")
    elif report.overall_alert:
        print("📍 REGRESSION LOCATION: Latest data point (spike detected)")
    else:
        print("📍 NO REGRESSION: Series is stable")
    print("=" * 70)

    # Exit code
    sys.exit(1 if report.overall_alert else 0)


if __name__ == "__main__":
    main()
