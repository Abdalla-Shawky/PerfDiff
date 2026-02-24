#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, UTC
from html import escape
from typing import List, Any, Dict, Optional

import numpy as np

# ---- Import from your module (the one I gave you earlier) ----
# If commit_to_commit_comparison.py is in the same package, import via package:
from commit_to_commit_comparison.commit_to_commit_comparison import gate_regression, equivalence_bootstrap_median
try:
    from perf_html_template import render_template
except ImportError:
    from .perf_html_template import render_template

from constants import (
    MS_FLOOR,
    PCT_FLOOR,
    TAIL_QUANTILE,
    TAIL_MS_FLOOR,
    TAIL_PCT_FLOOR,
    DIRECTIONALITY,
    WILCOXON_ALPHA,
    BOOTSTRAP_CONFIDENCE,
    BOOTSTRAP_N,
    SEED,
    EQUIVALENCE_MARGIN_MS,
    MIN_SAMPLE_CRITICAL,
    MIN_SAMPLE_WARNING,
    CV_HIGH_THRESHOLD,
    CV_MODERATE_THRESHOLD,
    CV_SOME_THRESHOLD,
    IQR_OUTLIER_MULTIPLIER,
    OUTLIER_PCT_ISSUE,
    INITIAL_QUALITY_SCORE,
    PENALTY_SAMPLE_CRITICAL,
    PENALTY_SAMPLE_WARNING,
    PENALTY_CV_HIGH,
    PENALTY_CV_MODERATE,
    PENALTY_CV_SOME,
    PENALTY_OUTLIER_ISSUE,
    PENALTY_OUTLIER_WARNING,
    QUALITY_EXCELLENT_THRESHOLD,
    QUALITY_GOOD_THRESHOLD,
    QUALITY_FAIR_THRESHOLD,
    OVERALL_HIGH_CONFIDENCE,
    OVERALL_MODERATE_CONFIDENCE,
    Q1_QUANTILE,
    Q3_QUANTILE,
    P90_QUANTILE,
    PCT_CONVERSION_FACTOR,
    BAR_MAX_WIDTH_PCT,
    EXIT_SUCCESS,
    EXIT_FAILURE,
    EXIT_PARSE_ERROR,
    # Quality Gate Constants
    ENABLE_QUALITY_GATES,
    MAX_CV_FOR_REGRESSION_CHECK,
    MIN_SAMPLES_FOR_REGRESSION,
    CV_THRESHOLD_MULTIPLIER,
    # UI Constants
    CHARTJS_CDN_URL,
    CHARTJS_CDN_SRI,
    ANIMATION_DURATION_FAST,
    ANIMATION_DURATION_NORMAL,
    ANIMATION_DURATION_SLOW,
    CHART_COLOR_BASELINE,
    CHART_COLOR_TARGET_IMPROVEMENT,
    CHART_COLOR_TARGET_REGRESSION,
    CHART_COLOR_NEUTRAL,
    DARK_BG_PRIMARY,
    DARK_BG_SECONDARY,
    DARK_BG_TERTIARY,
    DARK_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY,
    DARK_BORDER,
    LIGHT_BG_PRIMARY,
    LIGHT_BG_SECONDARY,
    LIGHT_BG_TERTIARY,
    LIGHT_TEXT_PRIMARY,
    LIGHT_TEXT_SECONDARY,
    LIGHT_BORDER,
)


def _parse_array(s: str) -> List[float]:
    """
    Accepts:
      - JSON array string: "[1,2,3]"
      - Comma-separated: "1,2,3"
    """
    s = s.strip()
    if not s:
        raise ValueError("Empty array input")

    if s[0] == "[":
        arr = json.loads(s)
        if not isinstance(arr, list):
            raise ValueError("JSON input must be a list")
        return [float(x) for x in arr]

    # comma-separated
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if not parts:
        raise ValueError("No numbers found in input")
    return [float(p) for p in parts]


def _fmt_ms(x: float) -> str:
    return f"{x:.2f} ms"


def _fmt_pct(x: float) -> str:
    return f"{x*PCT_CONVERSION_FACTOR:.2f}%"


def _mini_table(rows: List[List[str]]) -> str:
    trs = []
    for r in rows:
        tds = "".join(f"<td>{escape(c)}</td>" for c in r)
        trs.append(f"<tr>{tds}</tr>")
    return "<table>" + "".join(trs) + "</table>"


def render_html_report(
    title: str,
    baseline: List[float],
    target: List[float],
    result: Dict[str, Any],
    mode: str,
    eq: Optional[Dict[str, Any]] = None,
) -> str:
    a = np.array(baseline, dtype=float)
    b = np.array(target, dtype=float)
    d = b - a

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    passed = result.get("passed", False)
    inconclusive = result.get("inconclusive", False)

    if inconclusive:
        status = "INCONCLUSIVE ⚠️"
        status_color = "#ff9800"  # Orange for warning
    elif result.get("no_change", False):
        status = "NO CHANGE ⚖️"
        status_color = "#2196f3"  # Blue for info
    elif passed:
        status = "PASS ✅"
        status_color = "#4caf50"  # Green
    else:
        status = "FAIL ❌"
        status_color = "#f44336"  # Red

    base_med = float(np.median(a))
    target_med = float(np.median(b))
    delta_med = float(np.median(d))
    base_p90 = float(np.quantile(a, P90_QUANTILE, method="linear"))
    target_p90 = float(np.quantile(b, P90_QUANTILE, method="linear"))
    delta_p90 = float(np.quantile(d, P90_QUANTILE, method="linear"))
    pos_frac = float(np.mean(d > 0))

    # Calculate percentage change for plain English
    pct_change = ((target_med - base_med) / base_med * PCT_CONVERSION_FACTOR) if base_med > 0 else 0

    # Determine plain English explanation
    if inconclusive:
        simple_verdict = "Data quality too poor for reliable regression detection"
        recommendation = (
            "⚠️ Cannot determine if performance changed. Measurements are too noisy/inconsistent. "
            "Fix data quality issues and re-test with interleaved measurements."
        )
    elif result.get("no_change", False):
        simple_verdict = f"No performance change detected (delta: {delta_med:.1f}ms, {abs(pct_change):.1f}%)"
        recommendation = "⚖️ This change has no measurable performance impact. Safe to deploy."
    elif passed:
        if delta_med < 0:
            simple_verdict = f"Performance IMPROVED by {abs(delta_med):.1f}ms ({abs(pct_change):.1f}% faster)"
            recommendation = "✅ This change is safe to deploy. Performance has improved."
        else:
            simple_verdict = f"Performance change is within acceptable limits (+{delta_med:.1f}ms, +{pct_change:.1f}%)"
            recommendation = "✅ This change is safe to deploy. The small performance impact is acceptable."
    else:
        simple_verdict = f"Performance REGRESSED by {delta_med:.1f}ms ({pct_change:.1f}% slower)"
        recommendation = "❌ This change should be reviewed before deployment. Performance has degraded."

    # Simple comparison for non-technical users
    if result.get("no_change", False):
        change_icon = "⚖️"  # Balance/scale
        change_color = "#2196f3"  # Blue
    elif delta_med < 0:
        change_icon = "📈"  # Improvement
        change_color = "#137333"  # Green
    elif delta_med > 0:
        change_icon = "📉"  # Regression
        change_color = "#b3261e"  # Red
    else:
        change_icon = "➡️"  # No change
        change_color = "#666"  # Gray

    # Data Quality Assessment
    def assess_data_quality(data: np.ndarray, name: str) -> Dict[str, Any]:
        """Assess the quality and reliability of measurement data."""
        n = len(data)
        median = float(np.median(data))
        mean = float(np.mean(data))
        std = float(np.std(data))
        cv = (std / mean * PCT_CONVERSION_FACTOR) if mean > 0 else 0  # Coefficient of variation
        min_val = float(np.min(data))
        max_val = float(np.max(data))
        range_val = max_val - min_val
        iqr = float(np.quantile(data, Q3_QUANTILE, method="linear") - np.quantile(data, Q1_QUANTILE, method="linear"))

        # Detect outliers using IQR method
        q1 = float(np.quantile(data, Q1_QUANTILE, method="linear"))
        q3 = float(np.quantile(data, Q3_QUANTILE, method="linear"))
        iqr_threshold = IQR_OUTLIER_MULTIPLIER * iqr
        outliers = data[(data < q1 - iqr_threshold) | (data > q3 + iqr_threshold)]
        num_outliers = len(outliers)

        # Assessment criteria
        issues = []
        warnings = []
        score = INITIAL_QUALITY_SCORE  # Start with perfect score

        # Sample size check
        if n < MIN_SAMPLE_CRITICAL:
            issues.append(f"Very few samples ({n}). Recommend at least 10 samples for reliable results.")
            score -= PENALTY_SAMPLE_CRITICAL
        elif n < MIN_SAMPLE_WARNING:
            warnings.append(f"Small sample size ({n}). Consider 10+ samples for better confidence.")
            score -= PENALTY_SAMPLE_WARNING

        # Variability check (CV = coefficient of variation)
        if cv > CV_HIGH_THRESHOLD:
            issues.append(f"High variability (CV={cv:.1f}%). Data is inconsistent - check test environment.")
            score -= PENALTY_CV_HIGH
        elif cv > CV_MODERATE_THRESHOLD:
            warnings.append(f"Moderate variability (CV={cv:.1f}%). Results may be noisy.")
            score -= PENALTY_CV_MODERATE
        elif cv > CV_SOME_THRESHOLD:
            warnings.append(f"Some variability (CV={cv:.1f}%). This is normal for most systems.")
            score -= PENALTY_CV_SOME

        # Outlier check
        if num_outliers > 0:
            outlier_pct = num_outliers / n * PCT_CONVERSION_FACTOR
            if outlier_pct > OUTLIER_PCT_ISSUE:
                issues.append(f"{num_outliers} outliers detected ({outlier_pct:.0f}% of data). Test environment may be unstable.")
                score -= PENALTY_OUTLIER_ISSUE
            else:
                warnings.append(f"{num_outliers} outlier(s) detected. May indicate measurement noise.")
                score -= PENALTY_OUTLIER_WARNING

        # Determine overall verdict
        if score >= QUALITY_EXCELLENT_THRESHOLD:
            verdict = "Excellent"
            verdict_icon = "🟢"
            verdict_color = "#137333"
            verdict_desc = "Data quality is excellent. Results are highly reliable."
        elif score >= QUALITY_GOOD_THRESHOLD:
            verdict = "Good"
            verdict_icon = "🟡"
            verdict_color = "#f9ab00"
            verdict_desc = "Data quality is good. Results are reliable with minor caveats."
        elif score >= QUALITY_FAIR_THRESHOLD:
            verdict = "Fair"
            verdict_icon = "🟠"
            verdict_color = "#f57c00"
            verdict_desc = "Data quality is fair. Results may have some uncertainty."
        else:
            verdict = "Poor"
            verdict_icon = "🔴"
            verdict_color = "#b3261e"
            verdict_desc = "Data quality is poor. Consider re-running tests in a more stable environment."

        return {
            "name": name,
            "n": n,
            "median": median,
            "mean": mean,
            "std": std,
            "cv": cv,
            "min": min_val,
            "max": max_val,
            "range": range_val,
            "iqr": iqr,
            "num_outliers": num_outliers,
            "issues": issues,
            "warnings": warnings,
            "score": score,
            "verdict": verdict,
            "verdict_icon": verdict_icon,
            "verdict_color": verdict_color,
            "verdict_desc": verdict_desc,
        }

    baseline_quality = assess_data_quality(a, "Baseline")
    target_quality = assess_data_quality(b, "Target")

    # Overall data quality verdict
    overall_quality_score = (baseline_quality["score"] + target_quality["score"]) / 2
    if overall_quality_score >= OVERALL_HIGH_CONFIDENCE:
        overall_quality_verdict = "✅ High confidence in results"
        overall_quality_class = "good"
    elif overall_quality_score >= OVERALL_MODERATE_CONFIDENCE:
        overall_quality_verdict = "⚠️ Moderate confidence - see data quality notes"
        overall_quality_class = "warning"
    else:
        overall_quality_verdict = "⚠️ Low confidence - recommend re-running tests"
        overall_quality_class = "poor"

    # Simple sparkline-like bars (no external deps)
    def bar(value: float, maxv: float) -> str:
        if maxv <= 0:
            return ""
        w = max(0.0, min(BAR_MAX_WIDTH_PCT, BAR_MAX_WIDTH_PCT * value / maxv))
        return f'<div class="bar"><div class="barfill" style="width:{w:.1f}%"></div></div>'

    # Detect outliers using IQR method (same as data quality assessment)
    def detect_outliers(data: np.ndarray) -> set:
        """Returns a set of outlier values using IQR method."""
        if len(data) < 4:  # Need at least 4 points for IQR
            return set()
        q1 = float(np.quantile(data, Q1_QUANTILE, method="linear"))
        q3 = float(np.quantile(data, Q3_QUANTILE, method="linear"))
        iqr = q3 - q1
        iqr_threshold = IQR_OUTLIER_MULTIPLIER * iqr
        lower_bound = q1 - iqr_threshold
        upper_bound = q3 + iqr_threshold
        outliers = data[(data < lower_bound) | (data > upper_bound)]
        return set(outliers.tolist())

    max_run = float(max(np.max(a), np.max(b)))

    # Detect outliers in baseline and target
    baseline_outliers = detect_outliers(a)
    target_outliers = detect_outliers(b)

    runs_rows = []
    for i, (ai, bi, di) in enumerate(zip(a.tolist(), b.tolist(), d.tolist()), start=1):
        # Mark outliers with a badge
        baseline_val = _fmt_ms(ai)
        target_val = _fmt_ms(bi)

        if ai in baseline_outliers:
            baseline_val = f'{_fmt_ms(ai)} <span class="outlier-badge">⚠️</span>'
        if bi in target_outliers:
            target_val = f'{_fmt_ms(bi)} <span class="outlier-badge">⚠️</span>'

        runs_rows.append([
            str(i),
            baseline_val,
            target_val,
            _fmt_ms(di),
        ])

    summary_rows = [
        ["Mode", mode],
        ["Status", status],
        ["N (paired)", str(len(d))],
        ["Baseline median", _fmt_ms(base_med)],
        ["Target median", _fmt_ms(target_med)],
        ["Median delta (target-baseline)", _fmt_ms(delta_med)],
        ["Baseline p90", _fmt_ms(base_p90)],
        ["Target p90", _fmt_ms(target_p90)],
        ["p90 delta", _fmt_ms(delta_p90)],
        ["Positive delta fraction", _fmt_pct(pos_frac)],
    ]

    # Gate thresholds (if present)
    details = result.get("details", {})
    if "threshold_ms" in details:
        summary_rows.append(["Gate threshold", _fmt_ms(float(details["threshold_ms"]))])

    # Mann-Whitney U test (if present) - check both old and new key names for compatibility
    mw = details.get("mann_whitney") or details.get("wilcoxon")
    mw_rows = []
    if isinstance(mw, dict):
        # Mann-Whitney U test format (independent samples)
        if "u_statistic" in mw:
            mw_rows = [
                ["Mann-Whitney n (baseline)", str(mw.get("n_baseline", ""))],
                ["Mann-Whitney n (target)", str(mw.get("n_target", ""))],
                ["Mann-Whitney U", f'{mw.get("u_statistic", 0.0):.1f}'],
                ["Mann-Whitney p(greater)", f'{mw.get("p_greater", 1.0):.6f}'],
                ["Mann-Whitney p(two-sided)", f'{mw.get("p_two_sided", 1.0):.6f}'],
            ]
        # Legacy Wilcoxon format (backward compatibility)
        else:
            mw_rows = [
                ["Wilcoxon n", str(mw.get("n", ""))],
                ["Wilcoxon z", f'{mw.get("z", 0.0):.3f}'],
                ["Wilcoxon p(greater)", f'{mw.get("p_greater", 1.0):.6f}'],
                ["Wilcoxon p(two-sided)", f'{mw.get("p_two_sided", 1.0):.6f}'],
            ]
    wil_rows = mw_rows  # Keep variable name for backward compatibility below

    # Bootstrap CI (if present)
    bci = details.get("bootstrap_ci_median")
    bci_rows = []
    if isinstance(bci, dict):
        bci_rows = [
            ["Bootstrap confidence", f'{float(bci.get("confidence", 0.95))*100:.1f}%'],
            ["Median delta CI low", _fmt_ms(float(bci.get("low", 0.0)))],
            ["Median delta CI high", _fmt_ms(float(bci.get("high", 0.0)))],
            ["Bootstrap samples", str(bci.get("n_boot", ""))],
        ]

    # Equivalence (for release mode)
    eq_rows = []
    if isinstance(eq, dict):
        eq_rows = [
            ["Equivalence", "EQUIVALENT ✅" if eq.get("equivalent") else "NOT EQUIVALENT ❌"],
            ["Margin", _fmt_ms(float(eq.get("margin_ms", 0.0)))],
            ["Median delta CI low", _fmt_ms(float(eq.get("ci_low", 0.0)))],
            ["Median delta CI high", _fmt_ms(float(eq.get("ci_high", 0.0)))],
            ["Confidence", f'{float(eq.get("confidence", 0.95))*100:.1f}%'],
        ]

    # Prepare data for charts and exports (as JSON)
    baseline_data_json = json.dumps(a.tolist())
    target_data_json = json.dumps(b.tolist())
    delta_data_json = json.dumps(d.tolist())

    # Prepare full data export
    export_data = {
        "title": title,
        "mode": mode,
        "generated": now,
        "status": {"passed": passed, "reason": result.get("reason", "")},
        "measurements": {
            "baseline": a.tolist(),
            "target": b.tolist(),
            "delta": d.tolist(),
        },
        "statistics": {
            "baseline_median": base_med,
            "target_median": target_med,
            "median_delta": delta_med,
            "baseline_p90": base_p90,
            "target_p90": target_p90,
            "p90_delta": delta_p90,
            "positive_fraction": pos_frac,
        },
        "data_quality": {
            "baseline": {
                "score": baseline_quality["score"],
                "verdict": baseline_quality["verdict"],
                "n": baseline_quality["n"],
                "cv": baseline_quality["cv"],
                "outliers": baseline_quality["num_outliers"],
            },
            "target": {
                "score": target_quality["score"],
                "verdict": target_quality["verdict"],
                "n": target_quality["n"],
                "cv": target_quality["cv"],
                "outliers": target_quality["num_outliers"],
            },
        },
        "details": details,
    }
    if eq:
        export_data["equivalence"] = eq

    export_data_json = json.dumps(export_data, indent=2)

    # Determine chart color for target data (regression vs improvement)
    chart_target_color = CHART_COLOR_TARGET_REGRESSION if delta_med > 0 else CHART_COLOR_TARGET_IMPROVEMENT

    # Pass all local variables plus module-level helper functions to template
    template_context = locals()
    template_context['_fmt_ms'] = _fmt_ms
    template_context['_mini_table'] = _mini_table
    template_context['escape'] = escape
    template_context['np'] = np

    return render_template(**template_context)




def main() -> int:
    p = argparse.ArgumentParser(
        description="Generate an HTML perf regression report from paired baseline/target arrays."
    )
    p.add_argument("--baseline", required=True, help='Baseline array: JSON "[...]" or "1,2,3"')
    p.add_argument("--target", required=False, help='Target array: JSON "[...]" or "1,2,3"')
    p.add_argument(
        "--change",
        required=False,
        help='[DEPRECATED] Use --target instead. Change array: JSON "[...]" or "1,2,3"',
    )
    p.add_argument("--out", required=True, help="Output HTML file path, e.g. report.html")
    p.add_argument("--title", default="Performance Regression Report", help="Report title")

    # Gate config (PR-style)
    p.add_argument("--ms-floor", type=float, default=MS_FLOOR)
    p.add_argument("--pct-floor", type=float, default=PCT_FLOOR)
    p.add_argument("--tail-ms-floor", type=float, default=TAIL_MS_FLOOR)
    p.add_argument("--tail-pct-floor", type=float, default=TAIL_PCT_FLOOR)
    p.add_argument("--tail-quantile", type=float, default=TAIL_QUANTILE)
    p.add_argument("--directionality", type=float, default=DIRECTIONALITY)
    p.add_argument("--no-wilcoxon", action="store_true")
    p.add_argument("--wilcoxon-alpha", type=float, default=WILCOXON_ALPHA)
    p.add_argument("--bootstrap-confidence", type=float, default=BOOTSTRAP_CONFIDENCE)
    p.add_argument("--bootstrap-n", type=int, default=BOOTSTRAP_N)
    p.add_argument("--seed", type=int, default=SEED)

    # Release equivalence mode (optional)
    p.add_argument("--mode", choices=["pr", "release"], default="pr")
    p.add_argument("--equivalence-margin-ms", type=float, default=EQUIVALENCE_MARGIN_MS, help="Used only in --mode release")

    args = p.parse_args()

    if args.target and args.change:
        print("Error: Use only one of --target or --change (deprecated).", file=sys.stderr)
        return EXIT_PARSE_ERROR
    if not args.target and args.change:
        args.target = args.change
        print("Warning: --change is deprecated. Use --target instead.", file=sys.stderr)
    if not args.target:
        print("Error: --target is required.", file=sys.stderr)
        return EXIT_PARSE_ERROR

    try:
        baseline = _parse_array(args.baseline)
        target = _parse_array(args.target)
    except Exception as e:
        print(f"Error parsing arrays: {e}", file=sys.stderr)
        return EXIT_PARSE_ERROR

    # Run the PR-style gate always (even for release, useful signal)
    gate = gate_regression(
        baseline=baseline,
        target=target,
        ms_floor=args.ms_floor,
        pct_floor=args.pct_floor,
        tail_quantile=args.tail_quantile,
        tail_ms_floor=args.tail_ms_floor,
        tail_pct_floor=args.tail_pct_floor,
        directionality=args.directionality,
        use_wilcoxon=not args.no_wilcoxon,
        wilcoxon_alpha=args.wilcoxon_alpha,
        bootstrap_confidence=args.bootstrap_confidence,
        bootstrap_n=args.bootstrap_n,
        seed=args.seed,
    )

    eq_payload = None
    if args.mode == "release":
        eq = equivalence_bootstrap_median(
            baseline=baseline,
            target=target,
            margin_ms=args.equivalence_margin_ms,
            confidence=args.bootstrap_confidence,
            n_boot=args.bootstrap_n,
            seed=args.seed,
        )
        eq_payload = {
            "equivalent": eq.equivalent,
            "margin_ms": args.equivalence_margin_ms,
            "confidence": args.bootstrap_confidence,
            "ci_low": eq.ci.ci_low,
            "ci_high": eq.ci.ci_high,
        }

    report = render_html_report(
        title=args.title,
        baseline=baseline,
        target=target,
        result={
            "passed": gate.passed,
            "reason": gate.reason,
            "details": gate.details,
            "inconclusive": gate.inconclusive,
        },
        mode=args.mode,
        eq=eq_payload,
    )

    # Create generated_reports folder if it doesn't exist
    output_dir = "generated_reports"
    os.makedirs(output_dir, exist_ok=True)

    # Prepend folder to output path (unless user already included a path)
    if os.path.dirname(args.out):
        # User specified a path like "foo/bar.html" - use as-is
        output_path = args.out
    else:
        # User specified just a filename like "report.html" - put in generated_reports/
        output_path = os.path.join(output_dir, args.out)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Wrote HTML report to: {output_path}")

    # Exit code logic:
    # - PR mode: Exit 0 if gate check passed, exit 1 if regression detected
    # - Release mode: Exit 0 if equivalent, exit 1 if NOT equivalent
    #
    # Note: In release mode, we only check equivalence, not the gate result.
    # This means a release can pass even if it would fail the PR gate,
    # as long as the change is within the equivalence margin.
    if args.mode == "release":
        # Fail if NOT equivalent
        return EXIT_SUCCESS if (eq_payload and eq_payload["equivalent"]) else EXIT_FAILURE

    # PR mode: fail if gate check failed
    return EXIT_SUCCESS if gate.passed else EXIT_FAILURE


if __name__ == "__main__":
    raise SystemExit(main())
