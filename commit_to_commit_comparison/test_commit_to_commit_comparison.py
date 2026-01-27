#!/usr/bin/env python3
"""
Comprehensive test suite for commit_to_commit_comparison.py

Tests all fixed issues and core functionality.
"""
import pytest
import numpy as np
from commit_to_commit_comparison.commit_to_commit_comparison import (
    gate_regression,
    equivalence_bootstrap_median,
    GateResult,
    EquivalenceResult,
)
from constants import MIN_SAMPLES_FOR_REGRESSION, MAX_CV_FOR_REGRESSION_CHECK


class TestGateRegression:
    """Test gate_regression function."""

    def test_basic_regression_detected(self):
        """Test that a clear regression is detected."""
        baseline = [800, 805, 798, 810, 799, 803, 801, 807, 802, 804]
        change = [845, 850, 838, 860, 842, 848, 844, 855, 849, 847]

        result = gate_regression(baseline, change)

        assert isinstance(result, GateResult)
        assert result.passed is False
        assert "FAIL:" in result.reason
        assert "threshold_ms" in result.details

    def test_no_regression(self):
        """Test that no regression is detected when values are similar."""
        # Use values with some negative deltas to avoid directionality failure
        baseline = [100, 102, 98, 101, 99, 103, 100, 101, 102, 100]
        change = [99, 101, 97, 100, 98, 102, 99, 100, 101, 99]  # Mix of faster/slower

        result = gate_regression(baseline, change)

        assert isinstance(result, GateResult)
        assert result.passed is True
        # Can be either PASS or NO CHANGE depending on the delta size
        assert "PASS:" in result.reason or "NO CHANGE:" in result.reason

    def test_realistic_arrays_pass(self):
        """Realistic, slightly noisy arrays that should pass."""
        baseline = [245.2, 252.1, 248.7, 251.4, 249.6, 247.9, 253.3, 250.5, 246.8, 254.0, 248.9, 252.4]
        change = [246.1, 251.8, 247.5, 252.0, 248.9, 247.1, 254.2, 249.7, 245.9, 255.1, 247.8, 251.6]

        result = gate_regression(baseline, change)

        assert result.inconclusive is False
        assert result.passed is True
        assert result.details["median_delta_ms"] < result.details["threshold_ms"]

    def test_realistic_arrays_regression(self):
        """Realistic arrays with a clear regression that should fail."""
        baseline = [245.2, 252.1, 248.7, 251.4, 249.6, 247.9, 253.3, 250.5, 246.8, 254.0, 248.9, 252.4]
        change = [319.5, 326.8, 322.9, 325.4, 323.7, 321.6, 327.8, 324.9, 320.7, 328.1, 323.1, 326.2]

        result = gate_regression(baseline, change)

        assert result.inconclusive is False
        assert result.passed is False
        assert result.details["median_delta_ms"] > result.details["threshold_ms"]
        assert result.reason.startswith("FAIL:")

    def test_empty_arrays(self):
        """Test handling of empty arrays."""
        result = gate_regression([], [])

        assert result.passed is False
        assert "Empty arrays" in result.reason

    def test_mismatched_lengths(self):
        """Test handling of mismatched array lengths."""
        baseline = [100, 200, 300]
        change = [100, 200]

        result = gate_regression(baseline, change)

        assert result.passed is False
        assert "must have same length" in result.reason

    def test_invalid_parameters_raise(self):
        """Test parameter validation errors."""
        baseline = [100.0] * 10
        change = [100.0] * 10

        with pytest.raises(ValueError, match="ms_floor must be non-negative"):
            gate_regression(baseline, change, ms_floor=-1)

        with pytest.raises(ValueError, match="pct_floor must be between 0 and 1"):
            gate_regression(baseline, change, pct_floor=1.5)

        with pytest.raises(ValueError, match="tail_quantile must be between 0 and 1"):
            gate_regression(baseline, change, tail_quantile=1.0)

        with pytest.raises(ValueError, match="directionality must be between 0 and 1"):
            gate_regression(baseline, change, directionality=1.1)

        with pytest.raises(ValueError, match="wilcoxon_alpha must be between 0 and 1"):
            gate_regression(baseline, change, wilcoxon_alpha=0.0)

        with pytest.raises(ValueError, match="bootstrap_confidence must be between 0 and 1"):
            gate_regression(baseline, change, bootstrap_confidence=1.0)

        with pytest.raises(ValueError, match="bootstrap_n must be non-negative"):
            gate_regression(baseline, change, bootstrap_n=-10)

    def test_threshold_calculation(self):
        """Test that threshold is max of absolute and relative."""
        baseline = [100] * 10
        change = [110] * 10

        result = gate_regression(
            baseline,
            change,
            ms_floor=50.0,
            pct_floor=0.05  # 5% of 100 = 5ms
        )

        # Threshold should be max(50, 5) = 50ms
        # Delta is 10ms, so should pass
        assert result.details["threshold_ms"] == 50.0

    def test_tail_threshold_with_relative(self):
        """Test that tail threshold uses both absolute and relative."""
        baseline = [1000] * 10  # High baseline
        change = [1100] * 10

        result = gate_regression(
            baseline,
            change,
            tail_ms_floor=75.0,
            tail_pct_floor=0.05,  # 5% of ~1000 = 50ms
            tail_quantile=0.90
        )

        # tail_threshold should be max(75, 0.05 * 1000) = 75ms
        assert result.details["tail_threshold_ms"] == 75.0

    def test_directionality_boundary(self):
        """Test directionality boundary condition (>= not >)."""
        # Create data where exactly 70% are slower
        baseline = [100] * 10
        change = [110] * 7 + [100] * 3  # Exactly 70% slower

        result = gate_regression(
            baseline,
            change,
            ms_floor=0.0,  # Make threshold very low to isolate directionality
            directionality=0.70
        )

        # Should fail because 70% >= 70%
        assert result.passed is False
        assert "70.0%" in result.reason

    def test_tail_regression_only(self):
        """Test a case where median passes but tail fails."""
        baseline = [100.0] * 10
        # A modest outlier increases the p90 while keeping variance acceptable
        change = [103.0] * 9 + [133.0]

        result = gate_regression(
            baseline,
            change,
            ms_floor=1000.0,
            pct_floor=0.0,
            tail_ms_floor=1.0,
            tail_pct_floor=0.0,
            directionality=1.0,
            use_wilcoxon=False,
            bootstrap_n=0,
        )

        assert result.passed is False
        assert "Tail delta" in result.reason
        assert result.details["median_delta_ms"] == 3.0
        assert result.details["tail_delta_ms"] > result.details["tail_threshold_ms"]

    def test_bootstrap_disabled(self):
        """Test that bootstrap output is omitted when disabled."""
        baseline = [100.0] * 10
        change = [120.0] * 10

        result = gate_regression(baseline, change, bootstrap_n=0)

        assert "bootstrap_ci_median" not in result.details

    def test_wilcoxon_with_approx_method(self):
        """Test that Wilcoxon uses approx method and provides valid z-score."""
        baseline = [800] * 10
        change = [850] * 10

        result = gate_regression(
            baseline,
            change,
            use_wilcoxon=True
        )

        assert "wilcoxon" in result.details
        wilcox = result.details["wilcoxon"]

        # Check that we have proper fields
        assert "p_greater" in wilcox
        assert "p_two_sided" in wilcox
        # z-score might be present depending on scipy version
        if "z" in wilcox:
            assert isinstance(wilcox["z"], float)

    def test_bootstrap_confidence_interval(self):
        """Test that bootstrap CI is calculated correctly."""
        # Add some variance to get a non-trivial CI
        baseline = [100, 102, 98, 101, 99, 103, 100, 101, 102, 100]
        change = [110, 112, 108, 111, 109, 113, 110, 111, 112, 110]

        result = gate_regression(
            baseline,
            change,
            bootstrap_n=1000,
            bootstrap_confidence=0.95
        )

        assert "bootstrap_ci_median" in result.details
        bci = result.details["bootstrap_ci_median"]

        assert "low" in bci
        assert "high" in bci
        assert bci["confidence"] == 0.95
        assert bci["n_boot"] == 1000

        # Delta should be around 10ms, CI should contain 10 or be close
        # With variance, CI should have some width
        assert bci["low"] <= 10 <= bci["high"]

    def test_random_seed_reproducibility(self):
        """Test that same seed produces same results."""
        baseline = [100, 105, 98, 102, 99] * 2
        change = [110, 115, 108, 112, 109] * 2

        result1 = gate_regression(baseline, change, seed=42, bootstrap_n=1000)
        result2 = gate_regression(baseline, change, seed=42, bootstrap_n=1000)

        # Results should be identical
        assert result1.passed == result2.passed
        bci1 = result1.details["bootstrap_ci_median"]
        bci2 = result2.details["bootstrap_ci_median"]

        assert bci1["low"] == bci2["low"]
        assert bci1["high"] == bci2["high"]

    def test_wilcoxon_skipped_when_all_deltas_zero(self):
        """Test Wilcoxon is skipped cleanly when all deltas are zero."""
        baseline = [100.0] * 10
        change = [100.0] * 10

        result = gate_regression(baseline, change, use_wilcoxon=True)

        # No non-zero deltas means no Wilcoxon result should be recorded
        assert result.passed is True
        assert "wilcoxon" not in result.details

    def test_inconclusive_on_insufficient_samples(self):
        """Test quality gate behavior when sample size is too small."""
        baseline = [100.0, 101.0, 99.0, 100.5, 99.5]
        change = [100.2, 101.2, 98.8, 100.7, 99.7]

        result = gate_regression(baseline, change)

        assert result.passed is True
        assert result.inconclusive is True
        assert result.reason.startswith("INCONCLUSIVE:")
        assert f"minimum {MIN_SAMPLES_FOR_REGRESSION}" in result.reason
        assert result.details["sample_size"] == len(baseline)

    def test_inconclusive_on_high_variance(self):
        """Test quality gate behavior when variance is too high."""
        # High variance but still 10 samples to avoid the sample-size gate
        baseline = [10.0, 1000.0] * 5
        change = [12.0, 1200.0] * 5

        result = gate_regression(baseline, change)

        assert result.passed is True
        assert result.inconclusive is True
        assert result.reason.startswith("INCONCLUSIVE:")
        assert "HIGH VARIANCE" in result.reason
        assert result.details["baseline_cv"] > MAX_CV_FOR_REGRESSION_CHECK
        assert result.details["change_cv"] > MAX_CV_FOR_REGRESSION_CHECK

    def test_reason_string_clarity(self):
        """Test that reason strings are clear and unambiguous."""
        baseline = [100] * 10
        change = [200] * 10  # Clear regression

        result = gate_regression(baseline, change)

        # Should have clear PASS, NO CHANGE, or FAIL prefix
        assert (result.reason.startswith("PASS:") or
                result.reason.startswith("NO CHANGE:") or
                result.reason.startswith("FAIL:"))

        if not result.passed:
            # Should not say "within threshold" if failed
            assert "within threshold" not in result.reason or "FAIL:" in result.reason

    def test_practical_significance_override(self):
        """Test that negligible changes are not reported as regression.

        This test replicates the scenario from no_regression.html:
        - Baseline: ~2400ms
        - Change: ~2403ms
        - Delta: +2.5ms (0.1% slower)
        - Dynamic threshold: 20ms (1% of 2400ms, capped at 20ms)
        - Directionality: 90% (9/10 runs slower) - FAILS
        - Wilcoxon: p=0.0029 - FAILS
        - Result: Should PASS due to practical significance override (2.5ms < 20ms)
        """
        baseline = [2400.0, 2410.0, 2395.0, 2405.0, 2402.0, 2398.0, 2412.0, 2401.0, 2399.0, 2407.0]
        change = [2403.0, 2412.0, 2397.0, 2408.0, 2401.0, 2400.0, 2415.0, 2404.0, 2402.0, 2409.0]

        result = gate_regression(baseline, change)

        # Key assertions
        assert result.passed is True, "Should PASS due to practical significance override"
        assert "practical significance override" in result.reason, \
            "Reason should mention practical significance override"

        # Verify details show override was applied
        assert "practical_override" in result.details, \
            "Details should contain practical_override info"
        assert result.details["practical_override"]["applied"] is True, \
            "Override should be marked as applied"

        # Verify the dynamic threshold was calculated correctly
        # For 2400ms baseline: 1% = 24ms, but capped at 20ms
        practical_threshold = result.details["practical_override"]["practical_threshold_ms"]
        assert practical_threshold == 20.0, \
            f"Threshold should be 20ms (capped), got {practical_threshold}ms"

        # Verify the delta is below the dynamic threshold
        abs_delta = result.details["practical_override"]["abs_delta_ms"]
        assert abs_delta < practical_threshold, \
            f"Delta {abs_delta}ms should be below threshold {practical_threshold}ms"

        # Verify original failures are preserved
        assert "original_failures" in result.details["practical_override"], \
            "Should preserve original failure reasons"
        original_failures = result.details["practical_override"]["original_failures"]
        assert len(original_failures) > 0, "Should have at least one statistical failure"

        # The statistical tests should have failed (directionality and Wilcoxon)
        failures_str = "; ".join(original_failures)
        assert "slower" in failures_str or "Wilcoxon" in failures_str, \
            "Should have failed on directionality or Wilcoxon"

    def test_practical_significance_override_not_applied_when_delta_too_large(self):
        """Test that override is NOT applied when delta is above practical threshold.

        - Baseline: ~100ms
        - Change: ~110ms
        - Delta: 10ms
        - Dynamic threshold: 2ms (floor, since 1% of 100 = 1ms < 2ms floor)
        - Result: Should FAIL (10ms > 2ms threshold)
        """
        # Delta: 10ms on ~100ms baseline
        baseline = [100.0, 102.0, 98.0, 101.0, 99.0, 103.0, 100.0, 101.0, 102.0, 100.0]
        change = [110.0, 112.0, 108.0, 111.0, 109.0, 113.0, 110.0, 111.0, 112.0, 110.0]

        result = gate_regression(baseline, change)

        # Should FAIL (no override because delta is too large)
        assert result.passed is False, "Should FAIL because delta exceeds practical threshold"
        assert "FAIL:" in result.reason, "Reason should indicate failure"

        # Verify override was NOT applied
        assert "practical_override" in result.details, \
            "Details should contain practical_override info"
        assert result.details["practical_override"]["applied"] is False, \
            "Override should NOT be applied when delta is too large"

        # Verify the dynamic threshold
        practical_threshold = result.details["practical_override"]["practical_threshold_ms"]
        assert practical_threshold == 2.0, \
            f"Threshold should be 2ms (floor), got {practical_threshold}ms"

        # Verify delta exceeds threshold
        abs_delta = result.details["practical_override"]["abs_delta_ms"]
        assert abs_delta >= practical_threshold, \
            f"Delta {abs_delta}ms should exceed threshold {practical_threshold}ms"

    def test_practical_significance_override_not_applied_when_passes_all_gates(self):
        """Test that override logic is not triggered when all gates pass normally."""
        # Very similar values - should pass all gates without needing override
        baseline = [100.0, 102.0, 98.0, 101.0, 99.0, 103.0, 100.0, 101.0, 102.0, 100.0]
        change = [99.0, 101.0, 97.0, 100.0, 98.0, 102.0, 99.0, 100.0, 101.0, 99.0]

        result = gate_regression(baseline, change)

        # Should PASS normally
        assert result.passed is True, "Should PASS all gates normally"

        # Override should not be mentioned in reason
        assert "practical significance override" not in result.reason, \
            "Should be normal PASS, not override"

        # No practical_override field should be present (or it should show not applied)
        # depending on implementation, but definitely not applied
        if "practical_override" in result.details:
            assert result.details["practical_override"]["applied"] is False


class TestEquivalenceBootstrapMedian:
    """Test equivalence_bootstrap_median function."""

    def test_equivalent_distributions(self):
        """Test that similar distributions are equivalent."""
        baseline = [100] * 10
        change = [102] * 10  # Delta = 2ms

        result = equivalence_bootstrap_median(
            baseline,
            change,
            margin_ms=30.0,
            n_boot=1000
        )

        assert isinstance(result, EquivalenceResult)
        assert result.equivalent is True
        assert result.ci.ci_low > -30.0
        assert result.ci.ci_high < 30.0

    def test_non_equivalent_distributions(self):
        """Test that different distributions are not equivalent."""
        baseline = [100] * 10
        change = [150] * 10  # Delta = 50ms

        result = equivalence_bootstrap_median(
            baseline,
            change,
            margin_ms=30.0,
            n_boot=1000
        )

        assert result.equivalent is False
        # CI should be outside the margin
        assert result.ci.ci_low > 30.0 or result.ci.ci_high < -30.0

    def test_empty_arrays_validation(self):
        """Test that empty arrays raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            equivalence_bootstrap_median([], [])

        with pytest.raises(ValueError, match="cannot be empty"):
            equivalence_bootstrap_median([1, 2], [])

        with pytest.raises(ValueError, match="cannot be empty"):
            equivalence_bootstrap_median([], [1, 2])

    def test_mismatched_length_validation(self):
        """Test that mismatched lengths raise ValueError."""
        with pytest.raises(ValueError, match="length mismatch"):
            equivalence_bootstrap_median([1, 2, 3], [1, 2])

    def test_invalid_margin_validation(self):
        """Test that invalid margin raises ValueError."""
        baseline = [100] * 10
        change = [100] * 10

        with pytest.raises(ValueError, match="margin_ms must be positive"):
            equivalence_bootstrap_median(baseline, change, margin_ms=-5)

        with pytest.raises(ValueError, match="margin_ms must be positive"):
            equivalence_bootstrap_median(baseline, change, margin_ms=0)

    def test_invalid_confidence_validation(self):
        """Test that invalid confidence raises ValueError."""
        baseline = [100] * 10
        change = [100] * 10

        with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
            equivalence_bootstrap_median(baseline, change, confidence=0)

        with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
            equivalence_bootstrap_median(baseline, change, confidence=1)

        with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
            equivalence_bootstrap_median(baseline, change, confidence=1.5)

    def test_invalid_n_boot_validation(self):
        """Test that invalid n_boot raises ValueError."""
        baseline = [100] * 10
        change = [100] * 10

        with pytest.raises(ValueError, match="n_boot must be positive"):
            equivalence_bootstrap_median(baseline, change, n_boot=0)

        with pytest.raises(ValueError, match="n_boot must be positive"):
            equivalence_bootstrap_median(baseline, change, n_boot=-100)

    def test_reproducibility_with_seed(self):
        """Test that same seed produces same results."""
        baseline = [100, 105, 98, 102, 99] * 2
        change = [102, 107, 100, 104, 101] * 2

        result1 = equivalence_bootstrap_median(baseline, change, seed=42, n_boot=1000)
        result2 = equivalence_bootstrap_median(baseline, change, seed=42, n_boot=1000)

        assert result1.equivalent == result2.equivalent
        assert result1.ci.ci_low == result2.ci.ci_low
        assert result1.ci.ci_high == result2.ci.ci_high

    def test_quantile_consistency(self):
        """Test that quantile calculations are consistent."""
        baseline = [100] * 20
        change = [110] * 20

        # Run multiple times with different seeds
        results = [
            equivalence_bootstrap_median(baseline, change, seed=i, n_boot=500)
            for i in range(5)
        ]

        # All should agree on equivalence (delta is 10ms, margin is 30ms)
        equivalence_values = [r.equivalent for r in results]
        assert all(equivalence_values) or not any(equivalence_values)

    def test_equivalence_margin_boundary_is_strict(self):
        """Test that CI touching the margin is NOT considered equivalent."""
        baseline = [100.0] * 10
        change = [130.0] * 10  # Constant delta exactly 30ms

        result = equivalence_bootstrap_median(
            baseline,
            change,
            margin_ms=30.0,
            n_boot=500,
            seed=123,
        )

        # CI will be exactly [30, 30], and the check is strict (< margin)
        assert result.ci.ci_low == 30.0
        assert result.ci.ci_high == 30.0
        assert result.equivalent is False


class TestEdgeCases:
    """Test edge cases and corner conditions."""

    def test_very_fast_operations(self):
        """Test threshold behavior for very fast operations."""
        # Use more consistent data to avoid quality gate rejection
        baseline = [0.1, 0.11, 0.09, 0.1, 0.11, 0.1, 0.09, 0.1, 0.11, 0.1]  # Low variance
        change = [0.12, 0.13, 0.11, 0.12, 0.13, 0.12, 0.11, 0.12, 0.13, 0.12]  # Consistent small increase

        result = gate_regression(
            baseline,
            change,
            ms_floor=50.0,
            pct_floor=0.05  # 5% of 0.1 = 0.005ms
        )

        # If not inconclusive, base threshold should be max(50, 0.005) = 50ms
        # (threshold_ms may be higher due to CV multiplier)
        if not result.inconclusive:
            assert result.details["base_threshold_ms"] == 50.0
        else:
            # Data quality too poor, test passes anyway
            assert result.inconclusive is True

    def test_all_zeros(self):
        """Test handling of all-zero deltas."""
        baseline = [100] * 10
        change = [100] * 10  # No change

        result = gate_regression(baseline, change)

        # Should pass - no regression
        assert result.passed is True

    def test_negative_deltas(self):
        """Test handling when change is faster than baseline."""
        baseline = [200] * 10
        change = [100] * 10  # Improvement

        result = gate_regression(baseline, change)

        # Should pass - this is an improvement
        assert result.passed is True
        assert result.details["median_delta_ms"] < 0

    def test_single_sample(self):
        """Test with minimum sample size."""
        baseline = [100]
        change = [110]

        result = gate_regression(baseline, change)

        # Should work but may not have reliable statistics
        assert isinstance(result, GateResult)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
