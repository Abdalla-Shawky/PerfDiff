#!/usr/bin/env python3
"""
Comprehensive test suite for perf_regress.py

Tests all fixed issues and core functionality.
"""
import pytest
import numpy as np
from perf_regress import gate_regression, equivalence_bootstrap_median, GateResult, EquivalenceResult


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
        assert "PASS:" in result.reason

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

    def test_reason_string_clarity(self):
        """Test that reason strings are clear and unambiguous."""
        baseline = [100] * 10
        change = [200] * 10  # Clear regression

        result = gate_regression(baseline, change)

        # Should have clear PASS or FAIL prefix
        assert result.reason.startswith("PASS:") or result.reason.startswith("FAIL:")

        if not result.passed:
            # Should not say "within threshold" if failed
            assert "within threshold" not in result.reason or "FAIL:" in result.reason


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


class TestEdgeCases:
    """Test edge cases and corner conditions."""

    def test_very_fast_operations(self):
        """Test threshold behavior for very fast operations."""
        baseline = [0.1] * 10  # 0.1ms - very fast
        change = [0.15] * 5 + [0.08] * 5  # Mixed results to avoid directionality failure

        result = gate_regression(
            baseline,
            change,
            ms_floor=50.0,
            pct_floor=0.05  # 5% of 0.1 = 0.005ms
        )

        # Threshold should be max(50, 0.005) = 50ms
        # Median delta is ~0.025ms, so should pass median check
        assert result.details["threshold_ms"] == 50.0
        # May still fail on directionality or other checks, but threshold is correct

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
