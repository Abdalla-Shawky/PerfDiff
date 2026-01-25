#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, UTC
from html import escape
from typing import List, Any, Dict, Optional

import numpy as np

# ---- Import from your module (the one I gave you earlier) ----
# If perf_regress.py is in the same folder, this works:
from perf_regress import gate_regression, equivalence_bootstrap_median

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
    # UI Constants
    CHARTJS_CDN_URL,
    CHARTJS_CDN_SRI,
    ANIMATION_DURATION_FAST,
    ANIMATION_DURATION_NORMAL,
    ANIMATION_DURATION_SLOW,
    CHART_COLOR_BASELINE,
    CHART_COLOR_CHANGE_IMPROVEMENT,
    CHART_COLOR_CHANGE_REGRESSION,
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
    change: List[float],
    result: Dict[str, Any],
    mode: str,
    eq: Optional[Dict[str, Any]] = None,
) -> str:
    a = np.array(baseline, dtype=float)
    b = np.array(change, dtype=float)
    d = b - a

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    passed = result.get("passed", False)
    status = "PASS ✅" if passed else "FAIL ❌"

    base_med = float(np.median(a))
    change_med = float(np.median(b))
    delta_med = float(np.median(d))
    base_p90 = float(np.quantile(a, P90_QUANTILE, method="linear"))
    change_p90 = float(np.quantile(b, P90_QUANTILE, method="linear"))
    delta_p90 = float(np.quantile(d, P90_QUANTILE, method="linear"))
    pos_frac = float(np.mean(d > 0))

    # Calculate percentage change for plain English
    pct_change = ((change_med - base_med) / base_med * PCT_CONVERSION_FACTOR) if base_med > 0 else 0

    # Determine plain English explanation
    if passed:
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
    if delta_med < 0:
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
    change_quality = assess_data_quality(b, "Change")

    # Overall data quality verdict
    overall_quality_score = (baseline_quality["score"] + change_quality["score"]) / 2
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

    # Detect outliers in baseline and change
    baseline_outliers = detect_outliers(a)
    change_outliers = detect_outliers(b)

    runs_rows = []
    for i, (ai, bi, di) in enumerate(zip(a.tolist(), b.tolist(), d.tolist()), start=1):
        # Mark outliers with a badge
        baseline_val = _fmt_ms(ai)
        change_val = _fmt_ms(bi)

        if ai in baseline_outliers:
            baseline_val = f'{_fmt_ms(ai)} <span class="outlier-badge">⚠️</span>'
        if bi in change_outliers:
            change_val = f'{_fmt_ms(bi)} <span class="outlier-badge">⚠️</span>'

        runs_rows.append([
            str(i),
            baseline_val,
            change_val,
            _fmt_ms(di),
        ])

    summary_rows = [
        ["Mode", mode],
        ["Status", status],
        ["N (paired)", str(len(d))],
        ["Baseline median", _fmt_ms(base_med)],
        ["Change median", _fmt_ms(change_med)],
        ["Median delta (change-baseline)", _fmt_ms(delta_med)],
        ["Baseline p90", _fmt_ms(base_p90)],
        ["Change p90", _fmt_ms(change_p90)],
        ["p90 delta", _fmt_ms(delta_p90)],
        ["Positive delta fraction", _fmt_pct(pos_frac)],
    ]

    # Gate thresholds (if present)
    details = result.get("details", {})
    if "threshold_ms" in details:
        summary_rows.append(["Gate threshold", _fmt_ms(float(details["threshold_ms"]))])

    # Wilcoxon (if present)
    wil = details.get("wilcoxon")
    wil_rows = []
    if isinstance(wil, dict):
        wil_rows = [
            ["Wilcoxon n", str(wil.get("n", ""))],
            ["Wilcoxon z", f'{wil.get("z", 0.0):.3f}'],
            ["Wilcoxon p(greater)", f'{wil.get("p_greater", 1.0):.6f}'],
            ["Wilcoxon p(two-sided)", f'{wil.get("p_two_sided", 1.0):.6f}'],
        ]

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
    change_data_json = json.dumps(b.tolist())
    delta_data_json = json.dumps(d.tolist())

    # Prepare full data export
    export_data = {
        "title": title,
        "mode": mode,
        "generated": now,
        "status": {"passed": passed, "reason": result.get("reason", "")},
        "measurements": {
            "baseline": a.tolist(),
            "change": b.tolist(),
            "delta": d.tolist(),
        },
        "statistics": {
            "baseline_median": base_med,
            "change_median": change_med,
            "median_delta": delta_med,
            "baseline_p90": base_p90,
            "change_p90": change_p90,
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
            "change": {
                "score": change_quality["score"],
                "verdict": change_quality["verdict"],
                "n": change_quality["n"],
                "cv": change_quality["cv"],
                "outliers": change_quality["num_outliers"],
            },
        },
        "details": details,
    }
    if eq:
        export_data["equivalence"] = eq

    export_data_json = json.dumps(export_data, indent=2)

    # Determine chart color for change data (regression vs improvement)
    chart_change_color = CHART_COLOR_CHANGE_REGRESSION if delta_med > 0 else CHART_COLOR_CHANGE_IMPROVEMENT

    html = f"""<!doctype html>
<html data-theme="light">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{escape(title)} - Perf Report</title>

  <!-- Chart.js for interactive visualizations -->
  <script src="{CHARTJS_CDN_URL}" crossorigin="anonymous"></script>

  <style>
    /* ============================================================================
       CSS CUSTOM PROPERTIES (CSS Variables) FOR THEMING
       ============================================================================ */
    :root {{
      /* Light mode colors (default) */
      --bg-primary: {LIGHT_BG_PRIMARY};
      --bg-secondary: {LIGHT_BG_SECONDARY};
      --bg-tertiary: {LIGHT_BG_TERTIARY};
      --text-primary: {LIGHT_TEXT_PRIMARY};
      --text-secondary: {LIGHT_TEXT_SECONDARY};
      --border-color: {LIGHT_BORDER};

      /* Status colors (same in both themes) */
      --color-success: #137333;
      --color-error: #b3261e;
      --color-warning: #f57c00;
      --color-info: #1976d2;

      /* Chart colors */
      --chart-baseline: {CHART_COLOR_BASELINE};
      --chart-improvement: {CHART_COLOR_CHANGE_IMPROVEMENT};
      --chart-regression: {CHART_COLOR_CHANGE_REGRESSION};

      /* Animation durations */
      --anim-fast: {ANIMATION_DURATION_FAST}ms;
      --anim-normal: {ANIMATION_DURATION_NORMAL}ms;
      --anim-slow: {ANIMATION_DURATION_SLOW}ms;

      /* Shadows */
      --shadow-sm: 0 1px 3px rgba(0,0,0,0.12);
      --shadow-md: 0 2px 8px rgba(0,0,0,0.08);
      --shadow-lg: 0 4px 16px rgba(0,0,0,0.12);
    }}

    /* Dark mode color overrides */
    [data-theme="dark"] {{
      --bg-primary: {DARK_BG_PRIMARY};
      --bg-secondary: {DARK_BG_SECONDARY};
      --bg-tertiary: {DARK_BG_TERTIARY};
      --text-primary: {DARK_TEXT_PRIMARY};
      --text-secondary: {DARK_TEXT_SECONDARY};
      --border-color: {DARK_BORDER};
      --shadow-sm: 0 1px 3px rgba(0,0,0,0.3);
      --shadow-md: 0 2px 8px rgba(0,0,0,0.25);
      --shadow-lg: 0 4px 16px rgba(0,0,0,0.35);
    }}

    /* Smooth transitions for theme changes */
    * {{
      transition: background-color var(--anim-normal) ease,
                  color var(--anim-normal) ease,
                  border-color var(--anim-normal) ease,
                  box-shadow var(--anim-normal) ease;
    }}

    /* Disable transitions for immediate feedback on clicks */
    *, *::before, *::after {{
      transition-property: background-color, color, border-color, box-shadow, transform, opacity;
    }}

    /* Base styles */
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      margin: 0;
      padding: 0;
      background: var(--bg-primary);
      color: var(--text-primary);
      line-height: 1.6;
    }}

    /* Header with controls */
    .header {{
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border-color);
      padding: 16px 24px;
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: var(--shadow-sm);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }}

    .header-left {{
      flex: 1;
      min-width: 200px;
    }}

    .header-right {{
      display: flex;
      gap: 12px;
      align-items: center;
    }}

    h1 {{
      margin: 0;
      font-size: 24px;
      font-weight: 600;
      color: var(--text-primary);
    }}

    .meta {{
      color: var(--text-secondary);
      font-size: 13px;
      margin-top: 4px;
    }}

    .container {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }}

    /* Control buttons (theme toggle, export) */
    .control-btn {{
      background: var(--bg-tertiary);
      border: 1px solid var(--border-color);
      color: var(--text-primary);
      padding: 8px 16px;
      border-radius: 8px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all var(--anim-fast) cubic-bezier(0.4, 0, 0.2, 1);
    }}

    .control-btn:hover {{
      transform: translateY(-1px);
      box-shadow: var(--shadow-md);
      background: var(--bg-secondary);
    }}

    .control-btn:active {{
      transform: translateY(0);
    }}

    .icon-btn {{
      background: transparent;
      border: none;
      padding: 8px;
      cursor: pointer;
      font-size: 20px;
      border-radius: 50%;
      width: 36px;
      height: 36px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      transition: all var(--anim-fast) ease;
    }}

    .icon-btn:hover {{
      background: var(--bg-tertiary);
    }}

    /* Export dropdown */
    .export-dropdown {{
      position: relative;
      display: inline-block;
    }}

    .export-menu {{
      display: none;
      position: absolute;
      right: 0;
      top: 100%;
      margin-top: 4px;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      box-shadow: var(--shadow-lg);
      min-width: 160px;
      z-index: 1000;
    }}

    .export-dropdown.active .export-menu {{
      display: block;
      animation: fadeIn var(--anim-fast) ease;
    }}

    .export-menu button {{
      width: 100%;
      padding: 10px 16px;
      border: none;
      background: transparent;
      text-align: left;
      cursor: pointer;
      font-size: 14px;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 8px;
      transition: background-color var(--anim-fast) ease;
    }}

    .export-menu button:hover {{
      background: var(--bg-tertiary);
    }}

    .export-menu button:first-child {{
      border-radius: 8px 8px 0 0;
    }}

    .export-menu button:last-child {{
      border-radius: 0 0 8px 8px;
    }}

    /* Executive Summary */
    .executive-summary {{
      background: var(--bg-secondary);
      border-radius: 16px;
      padding: 32px;
      margin-bottom: 24px;
      box-shadow: var(--shadow-md);
      animation: slideUp var(--anim-slow) ease;
    }}

    .big-status {{
      font-size: 48px;
      font-weight: 700;
      margin-bottom: 16px;
      text-align: center;
      animation: scaleIn var(--anim-normal) ease;
    }}

    .big-status.pass {{ color: var(--color-success); }}
    .big-status.fail {{ color: var(--color-error); }}

    .verdict {{
      font-size: 22px;
      font-weight: 600;
      margin-bottom: 16px;
      text-align: center;
      color: var(--text-primary);
    }}

    .recommendation {{
      font-size: 16px;
      padding: 20px;
      background: var(--bg-tertiary);
      border-radius: 12px;
      margin: 24px 0;
      text-align: center;
      line-height: 1.7;
      border: 1px solid var(--border-color);
    }}

    .comparison {{
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      gap: 16px;
      align-items: center;
      margin: 24px 0;
    }}

    .comparison-item {{
      text-align: center;
      padding: 24px;
      background: var(--bg-tertiary);
      border-radius: 12px;
      border: 1px solid var(--border-color);
      transition: all var(--anim-fast) ease;
    }}

    .comparison-item:hover {{
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }}

    .comparison-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-secondary);
      margin-bottom: 8px;
      font-weight: 600;
    }}

    .comparison-value {{
      font-size: 32px;
      font-weight: 700;
      color: var(--text-primary);
      margin: 8px 0;
    }}

    .comparison-arrow {{
      font-size: 40px;
      color: {change_color};
      opacity: 0.8;
    }}

    /* Collapsible Sections */
    .section {{
      background: var(--bg-secondary);
      border-radius: 16px;
      padding: 24px;
      margin-bottom: 16px;
      box-shadow: var(--shadow-md);
      border: 1px solid var(--border-color);
      animation: fadeIn var(--anim-normal) ease;
    }}

    .section-header {{
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      user-select: none;
      padding: 8px;
      margin: -8px;
      border-radius: 8px;
      transition: background-color var(--anim-fast) ease;
    }}

    .section-header:hover {{
      background: var(--bg-tertiary);
    }}

    .section-title {{
      font-size: 19px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0;
    }}

    .section-subtitle {{
      font-size: 13px;
      color: var(--text-secondary);
      margin-top: 4px;
    }}

    .toggle-icon {{
      font-size: 20px;
      color: var(--text-secondary);
      transition: transform var(--anim-normal) cubic-bezier(0.4, 0, 0.2, 1);
    }}

    .section-content {{
      margin-top: 20px;
      max-height: 0;
      overflow: hidden;
      opacity: 0;
      transition: max-height var(--anim-normal) ease, opacity var(--anim-normal) ease;
    }}

    .section-content.show {{
      max-height: 10000px;
      opacity: 1;
    }}

    .section.expanded .toggle-icon {{
      transform: rotate(180deg);
    }}

    /* Charts container */
    .chart-container {{
      position: relative;
      height: 350px;
      margin: 20px 0;
    }}

    .chart-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 24px;
      margin: 20px 0;
    }}

    /* Tables */
    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 12px 0;
    }}

    td, th {{
      border-bottom: 1px solid var(--border-color);
      padding: 12px;
      text-align: left;
      font-size: 14px;
    }}

    th {{
      font-weight: 600;
      background: var(--bg-tertiary);
      color: var(--text-primary);
    }}

    tr:hover {{
      background: var(--bg-tertiary);
    }}

    /* Cards and Grid */
    .card {{
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 20px;
      margin: 14px 0;
      background: var(--bg-secondary);
    }}

    .grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }}

    .card h3 {{
      margin-top: 0;
      margin-bottom: 16px;
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
    }}

    /* Enhanced Progress Bars with Gradients */
    .bar {{
      background: var(--bg-tertiary);
      border-radius: 8px;
      height: 12px;
      overflow: hidden;
      position: relative;
    }}

    .barfill {{
      height: 12px;
      border-radius: 8px;
      background: linear-gradient(90deg, var(--chart-baseline), {CHART_COLOR_NEUTRAL});
      transition: width var(--anim-slow) cubic-bezier(0.4, 0, 0.2, 1);
      animation: barGrow var(--anim-slow) ease;
    }}

    .barfill.improvement {{
      background: linear-gradient(90deg, var(--chart-improvement), #4caf50);
    }}

    .barfill.regression {{
      background: linear-gradient(90deg, var(--chart-regression), #f44336);
    }}

    /* Badges */
    .small {{
      color: var(--text-secondary);
      font-size: 12px;
    }}

    .badge {{
      display: inline-block;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
    }}

    .badge-info {{
      background: #e3f2fd;
      color: var(--color-info);
    }}

    .outlier-badge {{
      display: inline-block;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 10px;
      background: #fff3cd;
      color: #856404;
      margin-left: 4px;
      font-weight: 600;
    }}

    .quality-badge {{
      display: inline-block;
      padding: 10px 18px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 14px;
      animation: pulse 2s ease infinite;
    }}

    .quality-good {{
      background: #e8f5e9;
      color: #2e7d32;
    }}

    .quality-warning {{
      background: #fff3cd;
      color: #856404;
    }}

    .quality-poor {{
      background: #f8d7da;
      color: #721c24;
    }}

    /* Data Quality Grid */
    .data-quality-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin: 16px 0;
    }}

    .quality-item {{
      padding: 20px;
      background: var(--bg-tertiary);
      border-radius: 12px;
      border-left: 4px solid var(--border-color);
      transition: all var(--anim-fast) ease;
    }}

    .quality-item:hover {{
      transform: translateX(4px);
      box-shadow: var(--shadow-md);
    }}

    .quality-item.excellent {{ border-left-color: var(--color-success); }}
    .quality-item.good {{ border-left-color: #f9ab00; }}
    .quality-item.fair {{ border-left-color: var(--color-warning); }}
    .quality-item.poor {{ border-left-color: var(--color-error); }}

    .issue-list {{
      margin: 8px 0;
      padding-left: 20px;
    }}

    .issue-list li {{
      margin: 6px 0;
      color: var(--text-secondary);
    }}

    /* Info boxes */
    .info-box {{
      margin: 16px 0;
      padding: 16px;
      background: var(--bg-tertiary);
      border-left: 4px solid var(--color-info);
      border-radius: 8px;
      font-size: 14px;
      line-height: 1.6;
    }}

    .warning-box {{
      margin: 16px 0;
      padding: 16px;
      background: #fff3cd;
      border-left: 4px solid #ffc107;
      border-radius: 8px;
      font-size: 14px;
      line-height: 1.6;
    }}

    /* Scroll to top button */
    .scroll-top-btn {{
      position: fixed;
      bottom: 32px;
      right: 32px;
      background: var(--bg-secondary);
      border: 2px solid var(--border-color);
      color: var(--text-primary);
      width: 48px;
      height: 48px;
      border-radius: 50%;
      cursor: pointer;
      font-size: 24px;
      display: none;
      align-items: center;
      justify-content: center;
      box-shadow: var(--shadow-lg);
      transition: all var(--anim-fast) ease;
      z-index: 999;
    }}

    .scroll-top-btn:hover {{
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.2);
    }}

    .scroll-top-btn.visible {{
      display: flex;
      animation: fadeIn var(--anim-normal) ease;
    }}

    /* Animations */
    @keyframes fadeIn {{
      from {{ opacity: 0; }}
      to {{ opacity: 1; }}
    }}

    @keyframes slideUp {{
      from {{
        opacity: 0;
        transform: translateY(20px);
      }}
      to {{
        opacity: 1;
        transform: translateY(0);
      }}
    }}

    @keyframes scaleIn {{
      from {{
        opacity: 0;
        transform: scale(0.9);
      }}
      to {{
        opacity: 1;
        transform: scale(1);
      }}
    }}

    @keyframes barGrow {{
      from {{ width: 0; }}
    }}

    @keyframes pulse {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.8; }}
    }}

    /* Responsive Design */
    @media (max-width: 900px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .comparison {{ grid-template-columns: 1fr; }}
      .comparison-arrow {{ transform: rotate(90deg); }}
      .data-quality-grid {{ grid-template-columns: 1fr; }}
      .header {{ flex-direction: column; align-items: flex-start; }}
      .header-right {{ width: 100%; justify-content: flex-end; }}
      .scroll-top-btn {{ bottom: 16px; right: 16px; }}
    }}

    @media (max-width: 600px) {{
      .container {{ padding: 16px; }}
      .executive-summary {{ padding: 20px; }}
      .big-status {{ font-size: 36px; }}
      .comparison-value {{ font-size: 24px; }}
      h1 {{ font-size: 20px; }}
    }}

    /* Print styles */
    @media print {{
      .header-right, .scroll-top-btn, .section-header {{
        display: none !important;
      }}
      .section-content {{
        max-height: none !important;
        opacity: 1 !important;
        display: block !important;
      }}
      body {{
        background: white;
        color: black;
      }}
      .section, .executive-summary {{
        page-break-inside: avoid;
        box-shadow: none;
        border: 1px solid #ccc;
      }}
    }}
  </style>
</head>
<body>
  <!-- Sticky Header with Controls -->
  <div class="header">
    <div class="header-left">
      <h1>{escape(title)}</h1>
      <div class="meta">Generated: {escape(now)} | Mode: {mode.upper()}</div>
    </div>
    <div class="header-right">
      <!-- Theme Toggle -->
      <button class="icon-btn" onclick="toggleTheme()" aria-label="Toggle dark mode" title="Toggle dark mode">
        <span id="theme-icon">🌙</span>
      </button>

      <!-- Export Dropdown -->
      <div class="export-dropdown" id="export-dropdown">
        <button class="control-btn" onclick="toggleExportMenu()">
          📥 Export ▼
        </button>
        <div class="export-menu">
          <button onclick="exportJSON()">📄 Export JSON</button>
          <button onclick="exportCSV()">📊 Export CSV</button>
          <button onclick="window.print()">🖨️ Print / PDF</button>
        </div>
      </div>
    </div>
  </div>

  <div class="container">
    <!-- EXECUTIVE SUMMARY - Simple & Clear for Everyone -->
    <div class="executive-summary">
      <div class="big-status {'pass' if passed else 'fail'}">{status}</div>
      <div class="verdict">{escape(simple_verdict)}</div>

      <div class="comparison">
        <div class="comparison-item">
          <div class="comparison-label">Before (Baseline)</div>
          <div class="comparison-value">{_fmt_ms(base_med)}</div>
          <div class="small">{len(a)} measurements</div>
        </div>
        <div class="comparison-arrow">{change_icon}</div>
        <div class="comparison-item">
          <div class="comparison-label">After (Change)</div>
          <div class="comparison-value">{_fmt_ms(change_med)}</div>
          <div class="small">{len(b)} measurements</div>
        </div>
      </div>

      <div class="recommendation">{escape(recommendation)}</div>

      <div class="small" style="text-align: center; margin-top: 16px; color: var(--text-secondary);">
        💡 Scroll down for detailed technical analysis
      </div>
    </div>

    <!-- INTERACTIVE CHARTS - Visual Data Exploration -->
    <div class="section">
      <div class="section-header" onclick="toggleSection('charts')">
        <div>
          <h2 class="section-title">📊 Interactive Charts</h2>
          <div class="section-subtitle">Visual comparison of performance distributions</div>
        </div>
        <span class="toggle-icon">▼</span>
      </div>
      <div id="charts" class="section-content">
        <div class="chart-grid">
          <!-- Histogram Comparison Chart -->
          <div>
            <h3 style="margin-top: 0; font-size: 16px; color: var(--text-primary);">Distribution Histogram</h3>
            <p style="font-size: 13px; color: var(--text-secondary); margin: 8px 0 16px 0;">
              Compare the distribution of measurements between baseline and change. Overlapping peaks indicate similar performance.
            </p>
            <div class="chart-container">
              <canvas id="histogramChart"></canvas>
            </div>
          </div>

          <!-- Run-by-Run Line Chart -->
          <div>
            <h3 style="margin-top: 0; font-size: 16px; color: var(--text-primary);">Run-by-Run Comparison</h3>
            <p style="font-size: 13px; color: var(--text-secondary); margin: 8px 0 16px 0;">
              Track how each paired measurement compares. The gap between lines shows performance delta.
            </p>
            <div class="chart-container">
              <canvas id="lineChart"></canvas>
            </div>
          </div>

          <!-- Statistical Summary Comparison -->
          <div>
            <h3 style="margin-top: 0; font-size: 16px; color: var(--text-primary);">Statistical Summary</h3>
            <p style="font-size: 13px; color: var(--text-secondary); margin: 8px 0 16px 0;">
              Compare key statistics: min, quartiles (Q1/Q3), median, mean, and max values side-by-side.
            </p>
            <div class="chart-container">
              <canvas id="boxPlotChart"></canvas>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- DATA QUALITY ASSESSMENT -->
    <div class="section">
      <div class="section-header" onclick="toggleSection('data-quality')">
        <div>
          <h2 class="section-title">🔬 Data Quality Assessment</h2>
          <div class="section-subtitle">How reliable are these measurements?</div>
        </div>
        <span class="toggle-icon">▼</span>
      </div>
      <div id="data-quality" class="section-content">
        <div style="text-align: center; margin-bottom: 20px;">
          <span class="quality-badge quality-{overall_quality_class}">{escape(overall_quality_verdict)}</span>
        </div>

        <div class="data-quality-grid">
          <!-- Baseline Quality -->
          <div class="quality-item {baseline_quality['verdict'].lower()}">
            <h3 style="margin: 0 0 8px 0; font-size: 16px;">
              {baseline_quality['verdict_icon']} Baseline Data: {baseline_quality['verdict']}
            </h3>
            <p style="margin: 8px 0; color: #666; font-size: 14px;">{escape(baseline_quality['verdict_desc'])}</p>
            <table style="font-size: 13px; margin-top: 12px;">
              <tr><td>Samples:</td><td><strong>{baseline_quality['n']}</strong></td></tr>
              <tr><td>Median:</td><td><strong>{_fmt_ms(baseline_quality['median'])}</strong></td></tr>
              <tr><td>Variability (CV):</td><td><strong>{baseline_quality['cv']:.1f}%</strong></td></tr>
              <tr><td>Range:</td><td>{_fmt_ms(baseline_quality['min'])} - {_fmt_ms(baseline_quality['max'])}</td></tr>
              <tr><td>Outliers:</td><td>{baseline_quality['num_outliers']}</td></tr>
            </table>
            {"<div style='margin-top: 12px;'><strong style='color: #b3261e;'>⚠️ Issues:</strong><ul class='issue-list'>" + "".join(f"<li>{escape(issue)}</li>" for issue in baseline_quality['issues']) + "</ul></div>" if baseline_quality['issues'] else ""}
            {"<div style='margin-top: 12px;'><strong style='color: #f57c00;'>⚡ Warnings:</strong><ul class='issue-list'>" + "".join(f"<li>{escape(warning)}</li>" for warning in baseline_quality['warnings']) + "</ul></div>" if baseline_quality['warnings'] else ""}
          </div>

          <!-- Change Quality -->
          <div class="quality-item {change_quality['verdict'].lower()}">
            <h3 style="margin: 0 0 8px 0; font-size: 16px;">
              {change_quality['verdict_icon']} Change Data: {change_quality['verdict']}
            </h3>
            <p style="margin: 8px 0; color: #666; font-size: 14px;">{escape(change_quality['verdict_desc'])}</p>
            <table style="font-size: 13px; margin-top: 12px;">
              <tr><td>Samples:</td><td><strong>{change_quality['n']}</strong></td></tr>
              <tr><td>Median:</td><td><strong>{_fmt_ms(change_quality['median'])}</strong></td></tr>
              <tr><td>Variability (CV):</td><td><strong>{change_quality['cv']:.1f}%</strong></td></tr>
              <tr><td>Range:</td><td>{_fmt_ms(change_quality['min'])} - {_fmt_ms(change_quality['max'])}</td></tr>
              <tr><td>Outliers:</td><td>{change_quality['num_outliers']}</td></tr>
            </table>
            {"<div style='margin-top: 12px;'><strong style='color: #b3261e;'>⚠️ Issues:</strong><ul class='issue-list'>" + "".join(f"<li>{escape(issue)}</li>" for issue in change_quality['issues']) + "</ul></div>" if change_quality['issues'] else ""}
            {"<div style='margin-top: 12px;'><strong style='color: #f57c00;'>⚡ Warnings:</strong><ul class='issue-list'>" + "".join(f"<li>{escape(warning)}</li>" for warning in change_quality['warnings']) + "</ul></div>" if change_quality['warnings'] else ""}
          </div>
        </div>

        <div style="margin-top: 16px; padding: 12px; background: #e3f2fd; border-left: 4px solid #1976d2; border-radius: 4px;">
          <strong>💡 What does this mean?</strong><br/>
          <ul style="margin: 8px 0; padding-left: 20px; font-size: 14px;">
            <li><strong>Samples:</strong> More samples = more reliable results. Aim for 10-20.</li>
            <li><strong>Variability (CV):</strong> Lower is better. <5% is excellent, >20% is problematic.</li>
            <li><strong>Outliers:</strong> Unusual measurements that may indicate instability.</li>
          </ul>
          If data quality is poor, consider re-running tests in a more stable environment or with more samples.
        </div>
      </div>
    </div>

    <!-- TECHNICAL DETAILS - Collapsible Sections -->

    <!-- Quick Statistics -->
    <div class="section">
      <div class="section-header" onclick="toggleSection('quick-stats')">
        <div>
          <h2 class="section-title">📊 Quick Statistics</h2>
          <div class="section-subtitle">Key numbers at a glance</div>
        </div>
        <span class="toggle-icon">▼</span>
      </div>
      <div id="quick-stats" class="section-content">
        <div class="grid">
          <div class="card">
            <h3>Summary</h3>
            {_mini_table(summary_rows)}
          </div>
          <div class="card">
            <h3>Run distribution (relative)</h3>
            <table>
              <tr><th>Baseline max</th><td>{_fmt_ms(float(np.max(a)))}</td></tr>
              <tr><th>Change max</th><td>{_fmt_ms(float(np.max(b)))}</td></tr>
              <tr><th>Baseline bars</th><td>{bar(float(np.median(a)), max_run)} <span class="small">median</span></td></tr>
              <tr><th>Change bars</th><td>{bar(float(np.median(b)), max_run)} <span class="small">median</span></td></tr>
            </table>
            <div class="small">Bars are scaled relative to the max single-run value across both sets.</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Why Did This Pass/Fail? -->
    <div class="section">
      <div class="section-header" onclick="toggleSection('explanation')">
        <div>
          <h2 class="section-title">🔍 Why Did This {'Pass' if passed else 'Fail'}?</h2>
          <div class="section-subtitle">Technical explanation of the decision</div>
        </div>
        <span class="toggle-icon">▼</span>
      </div>
      <div id="explanation" class="section-content">
        <div style="padding: 16px; background: #f8f9fa; border-radius: 8px; line-height: 1.8;">
          <strong>Decision Reason:</strong><br/>
          {escape(result.get("reason", ""))}
        </div>
        <div style="margin-top: 16px; padding: 12px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px;">
          <strong>💡 What this means:</strong><br/>
          {'The performance test passed all checks. ' if passed else 'The performance test failed one or more checks. '}
          The tool checks multiple factors: median change, worst-case (p90) latency, consistency across runs, and statistical significance.
        </div>
      </div>
    </div>

    {"<div class='section'><div class='section-header' onclick='toggleSection(\"wilcoxon\")'><div><h2 class='section-title'>📈 Wilcoxon Statistical Test</h2><div class='section-subtitle'>Tests if the difference is statistically significant (not just random noise)</div></div><span class='toggle-icon'>▼</span></div><div id='wilcoxon' class='section-content'>" + _mini_table(wil_rows) + "<div class='small' style='margin-top: 12px; padding: 12px; background: #f8f9fa; border-radius: 8px;'><strong>What is this?</strong> The Wilcoxon test checks if the performance difference is real or could be random variation. A p-value < 0.05 means the difference is statistically significant.</div></div></div>" if wil_rows else ""}

    {"<div class='section'><div class='section-header' onclick='toggleSection(\"bootstrap\")'><div><h2 class='section-title'>🎯 Bootstrap Confidence Interval</h2><div class='section-subtitle'>Range of uncertainty for the median performance change</div></div><span class='toggle-icon'>▼</span></div><div id='bootstrap' class='section-content'>" + _mini_table(bci_rows) + "<div class='small' style='margin-top: 12px; padding: 12px; background: #f8f9fa; border-radius: 8px;'><strong>What is this?</strong> We're 95% confident the true median change is between the CI low and high values. This accounts for measurement uncertainty.</div></div></div>" if bci_rows else ""}

    {"<div class='section'><div class='section-header' onclick='toggleSection(\"equivalence\")'><div><h2 class='section-title'>⚖️ Equivalence Test (Release Mode)</h2><div class='section-subtitle'>Checks if performance is 'close enough' to baseline</div></div><span class='toggle-icon'>▼</span></div><div id='equivalence' class='section-content'>" + _mini_table(eq_rows) + "<div class='small' style='margin-top: 12px; padding: 12px; background: #f8f9fa; border-radius: 8px;'><strong>What is this?</strong> In release mode, we test if the new version is equivalent to the old (within a margin). This is more permissive than regression testing.</div></div></div>" if eq_rows else ""}

    <!-- Raw Data -->
    <div class="section">
      <div class="section-header" onclick="toggleSection('raw-data')">
        <div>
          <h2 class="section-title">📋 Raw Measurement Data</h2>
          <div class="section-subtitle">Every individual measurement, side-by-side</div>
        </div>
        <span class="toggle-icon">▼</span>
      </div>
      <div id="raw-data" class="section-content">
        <table>
          <tr><th>#</th><th>Baseline</th><th>Change</th><th>Delta</th></tr>
          {''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>' for row in runs_rows)}
        </table>
        <div class="small" style="margin-top: 12px;">
          <strong>Note:</strong> Each row shows a paired measurement. Delta = Change - Baseline.
          Negative delta means faster (improvement), positive means slower (regression).
          Outliers (detected using IQR method) are marked with <span class="outlier-badge">⚠️</span>
        </div>
      </div>
    </div>

    <div style="text-align: center; margin: 32px 0; padding: 16px; color: var(--text-secondary); font-size: 12px;">
      Generated by Performance Regression Detection Tool 🚀
    </div>

  </div>

  <!-- Scroll to Top Button -->
  <button class="scroll-top-btn" id="scrollTopBtn" onclick="scrollToTop()" aria-label="Scroll to top">
    ↑
  </button>

  <script>
    // ============================================================================
    // DATA PREPARATION FOR CHARTS
    // ============================================================================
    const baselineData = {baseline_data_json};
    const changeData = {change_data_json};
    const deltaData = {delta_data_json};
    const exportData = {export_data_json};

    // Chart colors
    const CHART_COLORS = {{
      baseline: '{CHART_COLOR_BASELINE}',
      change: '{chart_change_color}',
      neutral: '{CHART_COLOR_NEUTRAL}',
    }};

    // ============================================================================
    // THEME TOGGLE (DARK MODE)
    // ============================================================================
    function toggleTheme() {{
      const html = document.documentElement;
      const currentTheme = html.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      const icon = document.getElementById('theme-icon');

      html.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      icon.textContent = newTheme === 'dark' ? '☀️' : '🌙';

      // Update chart colors for dark mode (only if charts are already initialized)
      if (chartsInitialized && window.charts) {{
        Object.values(window.charts).forEach(chart => {{
          if (chart) chart.destroy();
        }});
        initializeCharts();
      }}
    }}

    // Initialize theme from localStorage or system preference
    function initializeTheme() {{
      const savedTheme = localStorage.getItem('theme');
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      const theme = savedTheme || (prefersDark ? 'dark' : 'light');

      document.documentElement.setAttribute('data-theme', theme);
      document.getElementById('theme-icon').textContent = theme === 'dark' ? '☀️' : '🌙';
    }}

    // ============================================================================
    // EXPORT FUNCTIONALITY
    // ============================================================================
    function toggleExportMenu() {{
      const dropdown = document.getElementById('export-dropdown');
      dropdown.classList.toggle('active');
    }}

    // Close dropdown when clicking outside
    document.addEventListener('click', function(event) {{
      const dropdown = document.getElementById('export-dropdown');
      if (!dropdown.contains(event.target)) {{
        dropdown.classList.remove('active');
      }}
    }});

    function exportJSON() {{
      const dataStr = JSON.stringify(exportData, null, 2);
      const blob = new Blob([dataStr], {{ type: 'application/json' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'perf-report-data.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      document.getElementById('export-dropdown').classList.remove('active');
      showToast('JSON exported successfully');
    }}

    function exportCSV() {{
      const rows = [
        ['Run', 'Baseline (ms)', 'Change (ms)', 'Delta (ms)']
      ];

      for (let i = 0; i < baselineData.length; i++) {{
        rows.push([
          i + 1,
          baselineData[i].toFixed(2),
          changeData[i].toFixed(2),
          deltaData[i].toFixed(2)
        ]);
      }}

      const csvContent = rows.map(row => row.join(',')).join('\\n');
      const blob = new Blob([csvContent], {{ type: 'text/csv' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'perf-report-measurements.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      document.getElementById('export-dropdown').classList.remove('active');
      showToast('CSV exported successfully');
    }}

    function showToast(message) {{
      const toast = document.createElement('div');
      toast.textContent = message;
      toast.style.cssText = `
        position: fixed;
        bottom: 80px;
        right: 32px;
        background: var(--bg-secondary);
        color: var(--text-primary);
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: var(--shadow-lg);
        z-index: 10000;
        animation: fadeIn 0.3s ease;
        border: 1px solid var(--border-color);
      `;
      document.body.appendChild(toast);
      setTimeout(() => {{
        toast.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => document.body.removeChild(toast), 300);
      }}, 2000);
    }}

    // ============================================================================
    // SECTION TOGGLE ENHANCEMENT
    // ============================================================================
    let chartsInitialized = false;

    function toggleSection(id) {{
      const content = document.getElementById(id);
      const section = content.parentElement;
      content.classList.toggle('show');
      section.classList.toggle('expanded');

      // Lazy load charts when Interactive Charts section is first opened
      if (id === 'charts' && content.classList.contains('show') && !chartsInitialized) {{
        chartsInitialized = true;
        initializeCharts();
      }}
    }}

    // ============================================================================
    // SCROLL TO TOP BUTTON
    // ============================================================================
    const scrollTopBtn = document.getElementById('scrollTopBtn');

    window.addEventListener('scroll', () => {{
      if (window.pageYOffset > 300) {{
        scrollTopBtn.classList.add('visible');
      }} else {{
        scrollTopBtn.classList.remove('visible');
      }}
    }});

    function scrollToTop() {{
      window.scrollTo({{
        top: 0,
        behavior: 'smooth'
      }});
    }}

    // ============================================================================
    // CHART.JS INITIALIZATION
    // ============================================================================
    window.charts = {{}};

    function getChartColors() {{
      const theme = document.documentElement.getAttribute('data-theme');
      return {{
        gridColor: theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
        textColor: theme === 'dark' ? '#e0e0e0' : '#333',
      }};
    }}

    function initializeCharts() {{
      const colors = getChartColors();

      // 1. HISTOGRAM - Distribution comparison
      const histCtx = document.getElementById('histogramChart');
      if (histCtx) {{
        // Calculate histogram bins
        const allData = [...baselineData, ...changeData];
        const min = Math.min(...allData);
        const max = Math.max(...allData);
        const numBins = Math.min(20, Math.max(10, Math.floor(Math.sqrt(baselineData.length))));
        const binWidth = (max - min) / numBins;

        const bins = Array.from({{ length: numBins }}, (_, i) => min + i * binWidth);

        function calculateHistogram(data) {{
          const counts = new Array(numBins).fill(0);
          data.forEach(val => {{
            const binIndex = Math.min(numBins - 1, Math.floor((val - min) / binWidth));
            counts[binIndex]++;
          }});
          return counts;
        }}

        const baselineHist = calculateHistogram(baselineData);
        const changeHist = calculateHistogram(changeData);

        window.charts.histogram = new Chart(histCtx, {{
          type: 'bar',
          data: {{
            labels: bins.map(b => b.toFixed(1)),
            datasets: [
              {{
                label: 'Baseline',
                data: baselineHist,
                backgroundColor: CHART_COLORS.baseline + '80',
                borderColor: CHART_COLORS.baseline,
                borderWidth: 1.5,
              }},
              {{
                label: 'Change',
                data: changeHist,
                backgroundColor: CHART_COLORS.change + '80',
                borderColor: CHART_COLORS.change,
                borderWidth: 1.5,
              }}
            ]
          }},
          options: {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{
              mode: 'index',
              intersect: false,
            }},
            plugins: {{
              legend: {{
                labels: {{ color: colors.textColor }}
              }},
              tooltip: {{
                callbacks: {{
                  title: (items) => `Range: ${{items[0].label}}ms`,
                  label: (item) => `${{item.dataset.label}}: ${{item.parsed.y}} measurements`
                }}
              }}
            }},
            scales: {{
              x: {{
                title: {{
                  display: true,
                  text: 'Performance (ms)',
                  color: colors.textColor
                }},
                grid: {{ color: colors.gridColor }},
                ticks: {{ color: colors.textColor }}
              }},
              y: {{
                title: {{
                  display: true,
                  text: 'Count',
                  color: colors.textColor
                }},
                grid: {{ color: colors.gridColor }},
                ticks: {{ color: colors.textColor, precision: 0 }}
              }}
            }}
          }}
        }});
      }}

      // 2. LINE CHART - Run-by-run comparison
      const lineCtx = document.getElementById('lineChart');
      if (lineCtx) {{
        const runLabels = Array.from({{ length: baselineData.length }}, (_, i) => (i + 1).toString());

        window.charts.line = new Chart(lineCtx, {{
          type: 'line',
          data: {{
            labels: runLabels,
            datasets: [
              {{
                label: 'Baseline',
                data: baselineData,
                borderColor: CHART_COLORS.baseline,
                backgroundColor: CHART_COLORS.baseline + '20',
                borderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                tension: 0.3,
                fill: true,
              }},
              {{
                label: 'Change',
                data: changeData,
                borderColor: CHART_COLORS.change,
                backgroundColor: CHART_COLORS.change + '20',
                borderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                tension: 0.3,
                fill: true,
              }}
            ]
          }},
          options: {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{
              mode: 'index',
              intersect: false,
            }},
            plugins: {{
              legend: {{
                labels: {{ color: colors.textColor }}
              }},
              tooltip: {{
                callbacks: {{
                  title: (items) => `Run #${{items[0].label}}`,
                  afterLabel: (item) => {{
                    const delta = changeData[item.dataIndex] - baselineData[item.dataIndex];
                    return `Delta: ${{delta.toFixed(2)}}ms (${{delta > 0 ? '+' : ''}}${{((delta / baselineData[item.dataIndex]) * 100).toFixed(1)}}%)`;
                  }}
                }}
              }}
            }},
            scales: {{
              x: {{
                title: {{
                  display: true,
                  text: 'Run Number',
                  color: colors.textColor
                }},
                grid: {{ color: colors.gridColor }},
                ticks: {{ color: colors.textColor }}
              }},
              y: {{
                title: {{
                  display: true,
                  text: 'Performance (ms)',
                  color: colors.textColor
                }},
                grid: {{ color: colors.gridColor }},
                ticks: {{ color: colors.textColor }}
              }}
            }}
          }}
        }});
      }}

      // 3. STATISTICAL SUMMARY - Bar chart comparison
      const boxCtx = document.getElementById('boxPlotChart');
      if (boxCtx) {{
        function calculateStats(data) {{
          const sorted = [...data].sort((a, b) => a - b);
          const min = sorted[0];
          const max = sorted[sorted.length - 1];
          const q1 = sorted[Math.floor(sorted.length * 0.25)];
          const median = sorted[Math.floor(sorted.length * 0.5)];
          const q3 = sorted[Math.floor(sorted.length * 0.75)];
          const mean = data.reduce((a, b) => a + b, 0) / data.length;

          return {{ min, q1, median, q3, max, mean }};
        }}

        const baselineStats = calculateStats(baselineData);
        const changeStats = calculateStats(changeData);

        window.charts.boxplot = new Chart(boxCtx, {{
          type: 'bar',
          data: {{
            labels: ['Min', 'Q1 (25%)', 'Median', 'Mean', 'Q3 (75%)', 'Max'],
            datasets: [
              {{
                label: 'Baseline',
                data: [
                  baselineStats.min,
                  baselineStats.q1,
                  baselineStats.median,
                  baselineStats.mean,
                  baselineStats.q3,
                  baselineStats.max
                ],
                backgroundColor: CHART_COLORS.baseline + '80',
                borderColor: CHART_COLORS.baseline,
                borderWidth: 2,
              }},
              {{
                label: 'Change',
                data: [
                  changeStats.min,
                  changeStats.q1,
                  changeStats.median,
                  changeStats.mean,
                  changeStats.q3,
                  changeStats.max
                ],
                backgroundColor: CHART_COLORS.change + '80',
                borderColor: CHART_COLORS.change,
                borderWidth: 2,
              }}
            ]
          }},
          options: {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{
              mode: 'index',
              intersect: false,
            }},
            plugins: {{
              legend: {{
                labels: {{ color: colors.textColor }}
              }},
              tooltip: {{
                callbacks: {{
                  label: (item) => `${{item.dataset.label}}: ${{item.parsed.y.toFixed(2)}}ms`
                }}
              }}
            }},
            scales: {{
              x: {{
                grid: {{ color: colors.gridColor }},
                ticks: {{ color: colors.textColor }}
              }},
              y: {{
                title: {{
                  display: true,
                  text: 'Performance (ms)',
                  color: colors.textColor
                }},
                grid: {{ color: colors.gridColor }},
                ticks: {{ color: colors.textColor }}
              }}
            }}
          }}
        }});
      }}
    }}

    // ============================================================================
    // INITIALIZATION ON PAGE LOAD
    // ============================================================================
    document.addEventListener('DOMContentLoaded', function() {{
      initializeTheme();
      // Charts are lazy-loaded when the section is first opened
    }});
  </script>
</body>
</html>
"""
    return html


def main() -> int:
    p = argparse.ArgumentParser(
        description="Generate an HTML perf regression report from paired baseline/change arrays."
    )
    p.add_argument("--baseline", required=True, help='Baseline array: JSON "[...]" or "1,2,3"')
    p.add_argument("--change", required=True, help='Change array: JSON "[...]" or "1,2,3"')
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

    try:
        baseline = _parse_array(args.baseline)
        change = _parse_array(args.change)
    except Exception as e:
        print(f"Error parsing arrays: {e}", file=sys.stderr)
        return EXIT_PARSE_ERROR

    # Run the PR-style gate always (even for release, useful signal)
    gate = gate_regression(
        baseline=baseline,
        change=change,
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
            change=change,
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
        change=change,
        result={"passed": gate.passed, "reason": gate.reason, "details": gate.details},
        mode=args.mode,
        eq=eq_payload,
    )

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Wrote HTML report to: {args.out}")

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
