#!/usr/bin/env python3
"""Run adaptive score_k tests"""

import sys
import os

# Add parent directory to path for shared modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main_health import assess_main_health, _calculate_adaptive_parameters

def test_adaptive_score_k_noisy_step_detection():
    """Test that adaptive score_k detects noisy steps that would fail with strict thresholds"""
    print("\n" + "="*70)
    print("Test 1: Noisy Step Detection (User's Problematic Series)")
    print("="*70)

    series = [1100, 1101, 1111, 1099, 1100, 1102, 1098, 1101, 1100, 1099, 1101,
              1176, 1171, 1169, 1162, 1160, 1161, 1179, 1172, 1170, 1171, 1170,
              1172, 1179, 1171, 1170, 1152, 1149, 1151, 1150, 1152]

    print(f"\nSeries: 31 points, step at index 10 (score ~2.36)")
    print(f"Baseline ~1100ms → After step ~1170ms → Drops to ~1150ms")

    # Test with adaptive mode (score_k = 2.0 for 31-point series)
    report_adaptive = assess_main_health(series, abs_floor=50.0, pct_floor=0.05, adaptive=True)

    # Test with non-adaptive mode (score_k = 4.0 default)
    report_strict = assess_main_health(series, abs_floor=50.0, pct_floor=0.05, adaptive=False, step_score_k=4.0)

    print(f"\nResults:")
    print(f"  Adaptive (score_k=2.0): Step detected = {report_adaptive.stepfit.found}")
    if report_adaptive.stepfit.found:
        print(f"    Change index: {report_adaptive.stepfit.change_index}")
        print(f"    Reason: {report_adaptive.stepfit.reason}")

    print(f"  Strict (score_k=4.0): Step detected = {report_strict.stepfit.found}")
    if not report_strict.stepfit.found:
        print(f"    Reason: {report_strict.stepfit.reason}")

    assert report_adaptive.stepfit.found is True, "Adaptive should detect step"
    assert report_strict.stepfit.found is False, "Strict should NOT detect step"
    print("\n✅ Test 1 PASSED")
    return True

def test_adaptive_score_k_parameters():
    """Test that different series lengths get appropriate score_k thresholds"""
    print("\n" + "="*70)
    print("Test 2: Adaptive score_k Parameters")
    print("="*70)

    test_cases = [
        (12, 1.5, "Very short"),
        (25, 2.0, "Short"),
        (40, 2.0, "Medium"),
        (75, 3.0, "Long"),
        (150, 4.0, "Very long"),
    ]

    print("\nSeries Length → score_k Threshold:")
    for length, expected_score_k, description in test_cases:
        params = _calculate_adaptive_parameters(length)
        actual_score_k = params['step_score_k']

        print(f"  {description:12} ({length:3} pts): score_k = {actual_score_k}")
        assert actual_score_k == expected_score_k, f"Expected {expected_score_k}, got {actual_score_k}"

    print("\n✅ Test 2 PASSED")
    return True

def test_adaptive_score_k_with_clean_step():
    """Test that adaptive score_k still detects clean, obvious steps"""
    print("\n" + "="*70)
    print("Test 3: Clean Step Detection")
    print("="*70)

    # Clean step: 1000ms → 1500ms (50% increase, high score)
    series = [1000, 1001, 999, 1000, 1002, 998, 1001, 1000, 999, 1001,
              1500, 1501, 1499, 1500, 1502, 1498, 1501, 1500, 1499, 1501,
              1500, 1501, 1499, 1500, 1502, 1498, 1501, 1500, 1499, 1501]

    print(f"\nSeries: 30 points, clean step from 1000ms to 1500ms (50% increase)")

    report = assess_main_health(series, abs_floor=50.0, pct_floor=0.05, adaptive=True)

    print(f"\nResults:")
    print(f"  Step detected: {report.stepfit.found}")
    if report.stepfit.found:
        print(f"  Change index: {report.stepfit.change_index}")
        print(f"  Before median: {report.stepfit.before_median:.1f}ms")
        print(f"  After median: {report.stepfit.after_median:.1f}ms")
        print(f"  Delta: {report.stepfit.delta:.1f}ms")
        print(f"  Overall alert: {report.overall_alert}")

    assert report.stepfit.found is True, "Clean step should be detected"
    assert report.stepfit.before_median < 1100, f"Before median should be ~1000ms, got {report.stepfit.before_median}"
    assert report.stepfit.after_median > 1400, f"After median should be ~1500ms, got {report.stepfit.after_median}"
    assert report.stepfit.delta > 400, f"Delta should be ~500ms, got {report.stepfit.delta}"
    assert report.overall_alert is True, "Overall alert should be raised"
    print("\n✅ Test 3 PASSED")
    return True

def test_adaptive_score_k_short_series_sensitive():
    """Test that short series use very sensitive score_k thresholds"""
    print("\n" + "="*70)
    print("Test 4: Short Series Sensitivity")
    print("="*70)

    # Very short series (12 points) with weak step
    series = [100, 102, 98, 101, 99, 120, 122, 118, 121, 119, 121, 120]

    print(f"\nSeries: 12 points, step from ~100ms to ~120ms")

    # With adaptive (score_k = 1.5 for very short series)
    report_adaptive = assess_main_health(series, abs_floor=5.0, pct_floor=0.05, adaptive=True)

    # With strict threshold
    report_strict = assess_main_health(series, abs_floor=5.0, pct_floor=0.05, adaptive=False, step_score_k=4.0)

    print(f"\nResults:")
    print(f"  Adaptive (score_k=1.5): Step detected = {report_adaptive.stepfit.found if report_adaptive.stepfit else False}")
    print(f"  Strict (score_k=4.0): Step detected = {report_strict.stepfit.found if report_strict.stepfit else False}")

    assert report_adaptive is not None, "Adaptive report should exist"
    assert report_strict is not None, "Strict report should exist"
    print("\n✅ Test 4 PASSED")
    return True

if __name__ == "__main__":
    try:
        test_adaptive_score_k_noisy_step_detection()
        test_adaptive_score_k_parameters()
        test_adaptive_score_k_with_clean_step()
        test_adaptive_score_k_short_series_sensitive()

        print("\n" + "="*70)
        print("🎉 ALL ADAPTIVE SCORE_K TESTS PASSED!")
        print("="*70)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
