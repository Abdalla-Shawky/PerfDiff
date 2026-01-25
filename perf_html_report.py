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
    return f"{x*100:.2f}%"


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
    base_p90 = float(np.quantile(a, 0.90, method="linear"))
    change_p90 = float(np.quantile(b, 0.90, method="linear"))
    delta_p90 = float(np.quantile(d, 0.90, method="linear"))
    pos_frac = float(np.mean(d > 0))

    # Calculate percentage change for plain English
    pct_change = ((change_med - base_med) / base_med * 100) if base_med > 0 else 0

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
        cv = (std / mean * 100) if mean > 0 else 0  # Coefficient of variation
        min_val = float(np.min(data))
        max_val = float(np.max(data))
        range_val = max_val - min_val
        iqr = float(np.quantile(data, 0.75, method="linear") - np.quantile(data, 0.25, method="linear"))

        # Detect outliers using IQR method
        q1 = float(np.quantile(data, 0.25, method="linear"))
        q3 = float(np.quantile(data, 0.75, method="linear"))
        iqr_threshold = 1.5 * iqr
        outliers = data[(data < q1 - iqr_threshold) | (data > q3 + iqr_threshold)]
        num_outliers = len(outliers)

        # Assessment criteria
        issues = []
        warnings = []
        score = 100  # Start with perfect score

        # Sample size check
        if n < 5:
            issues.append(f"Very few samples ({n}). Recommend at least 10 samples for reliable results.")
            score -= 30
        elif n < 10:
            warnings.append(f"Small sample size ({n}). Consider 10+ samples for better confidence.")
            score -= 10

        # Variability check (CV = coefficient of variation)
        if cv > 20:
            issues.append(f"High variability (CV={cv:.1f}%). Data is inconsistent - check test environment.")
            score -= 25
        elif cv > 10:
            warnings.append(f"Moderate variability (CV={cv:.1f}%). Results may be noisy.")
            score -= 10
        elif cv > 5:
            warnings.append(f"Some variability (CV={cv:.1f}%). This is normal for most systems.")
            score -= 5

        # Outlier check
        if num_outliers > 0:
            outlier_pct = num_outliers / n * 100
            if outlier_pct > 20:
                issues.append(f"{num_outliers} outliers detected ({outlier_pct:.0f}% of data). Test environment may be unstable.")
                score -= 20
            else:
                warnings.append(f"{num_outliers} outlier(s) detected. May indicate measurement noise.")
                score -= 5

        # Determine overall verdict
        if score >= 90:
            verdict = "Excellent"
            verdict_icon = "🟢"
            verdict_color = "#137333"
            verdict_desc = "Data quality is excellent. Results are highly reliable."
        elif score >= 75:
            verdict = "Good"
            verdict_icon = "🟡"
            verdict_color = "#f9ab00"
            verdict_desc = "Data quality is good. Results are reliable with minor caveats."
        elif score >= 60:
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
    if overall_quality_score >= 85:
        overall_quality_verdict = "✅ High confidence in results"
        overall_quality_class = "good"
    elif overall_quality_score >= 70:
        overall_quality_verdict = "⚠️ Moderate confidence - see data quality notes"
        overall_quality_class = "warning"
    else:
        overall_quality_verdict = "⚠️ Low confidence - recommend re-running tests"
        overall_quality_class = "poor"

    # Simple sparkline-like bars (no external deps)
    def bar(value: float, maxv: float) -> str:
        if maxv <= 0:
            return ""
        w = max(0.0, min(100.0, 100.0 * value / maxv))
        return f'<div class="bar"><div class="barfill" style="width:{w:.1f}%"></div></div>'

    # Detect outliers using IQR method (same as data quality assessment)
    def detect_outliers(data: np.ndarray) -> set:
        """Returns a set of outlier values using IQR method."""
        if len(data) < 4:  # Need at least 4 points for IQR
            return set()
        q1 = float(np.quantile(data, 0.25, method="linear"))
        q3 = float(np.quantile(data, 0.75, method="linear"))
        iqr = q3 - q1
        iqr_threshold = 1.5 * iqr
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

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{escape(title)} - Perf Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; margin: 0; padding: 0; background: #f8f9fa; }}
    .container {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
    h1 {{ margin: 0 0 8px 0; font-size: 28px; }}
    .meta {{ color: #666; margin-bottom: 24px; font-size: 14px; }}

    /* Executive Summary - Simple & Clear */
    .executive-summary {{ background: white; border-radius: 16px; padding: 32px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
    .big-status {{ font-size: 48px; font-weight: 700; margin-bottom: 16px; text-align: center; }}
    .big-status.pass {{ color: #137333; }}
    .big-status.fail {{ color: #b3261e; }}
    .verdict {{ font-size: 24px; font-weight: 600; margin-bottom: 16px; text-align: center; color: #333; }}
    .recommendation {{ font-size: 18px; padding: 20px; background: #f8f9fa; border-radius: 12px; margin: 24px 0; text-align: center; line-height: 1.6; }}

    .comparison {{ display: grid; grid-template-columns: 1fr auto 1fr; gap: 16px; align-items: center; margin: 24px 0; }}
    .comparison-item {{ text-align: center; padding: 20px; background: #f8f9fa; border-radius: 12px; }}
    .comparison-label {{ font-size: 12px; text-transform: uppercase; color: #666; margin-bottom: 8px; font-weight: 600; }}
    .comparison-value {{ font-size: 32px; font-weight: 700; color: #333; }}
    .comparison-arrow {{ font-size: 48px; color: {change_color}; }}

    /* Collapsible Sections */
    .section {{ background: white; border-radius: 16px; padding: 24px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
    .section-header {{ cursor: pointer; display: flex; justify-content: space-between; align-items: center; user-select: none; }}
    .section-header:hover {{ background: #f8f9fa; margin: -8px; padding: 8px; border-radius: 8px; }}
    .section-title {{ font-size: 20px; font-weight: 600; color: #333; margin: 0; }}
    .section-subtitle {{ font-size: 14px; color: #666; margin-top: 4px; }}
    .toggle-icon {{ font-size: 24px; color: #666; transition: transform 0.3s; }}
    .section-content {{ margin-top: 20px; display: none; }}
    .section-content.show {{ display: block; }}
    .section.expanded .toggle-icon {{ transform: rotate(180deg); }}

    /* Tables */
    table {{ border-collapse: collapse; width: 100%; }}
    td, th {{ border-bottom: 1px solid #e5e5e5; padding: 12px; text-align: left; font-size: 14px; }}
    th {{ font-weight: 600; background: #f8f9fa; }}

    /* Misc */
    .card {{ border: 1px solid #e5e5e5; border-radius: 12px; padding: 16px; margin: 14px 0; background: white; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .bar {{ background:#f0f0f0; border-radius: 8px; height: 10px; overflow:hidden; }}
    .barfill {{ background:#999; height:10px; }}
    .small {{ color:#666; font-size: 12px; }}
    .badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
    .badge-info {{ background: #e3f2fd; color: #1976d2; }}
    .outlier-badge {{ display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 11px; background: #fff3cd; color: #856404; margin-left: 4px; font-weight: 600; }}
    .quality-badge {{ display: inline-block; padding: 8px 16px; border-radius: 8px; font-weight: 600; font-size: 14px; }}
    .quality-good {{ background: #e8f5e9; color: #2e7d32; }}
    .quality-warning {{ background: #fff3cd; color: #856404; }}
    .quality-poor {{ background: #f8d7da; color: #721c24; }}
    .data-quality-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 16px 0; }}
    .quality-item {{ padding: 16px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #ccc; }}
    .quality-item.excellent {{ border-left-color: #137333; }}
    .quality-item.good {{ border-left-color: #f9ab00; }}
    .quality-item.fair {{ border-left-color: #f57c00; }}
    .quality-item.poor {{ border-left-color: #b3261e; }}
    .issue-list {{ margin: 8px 0; padding-left: 20px; }}
    .issue-list li {{ margin: 4px 0; color: #666; }}

    @media (max-width: 900px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .comparison {{ grid-template-columns: 1fr; }}
      .comparison-arrow {{ transform: rotate(90deg); }}
    }}
  </style>
  <script>
    function toggleSection(id) {{
      const content = document.getElementById(id);
      const section = content.parentElement;
      content.classList.toggle('show');
      section.classList.toggle('expanded');
    }}
  </script>
</head>
<body>
  <div class="container">
    <h1>{escape(title)}</h1>
    <div class="meta">Generated: {escape(now)}</div>

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

      <div class="small" style="text-align: center; margin-top: 16px; color: #999;">
        💡 Scroll down for detailed technical analysis
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

    <div style="text-align: center; margin: 32px 0; padding: 16px; color: #999; font-size: 12px;">
      Generated by Performance Regression Detection Tool
    </div>

  </div>
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
    p.add_argument("--ms-floor", type=float, default=50.0)
    p.add_argument("--pct-floor", type=float, default=0.05)
    p.add_argument("--tail-ms-floor", type=float, default=75.0)
    p.add_argument("--tail-pct-floor", type=float, default=0.05)
    p.add_argument("--tail-quantile", type=float, default=0.90)
    p.add_argument("--directionality", type=float, default=0.70)
    p.add_argument("--no-wilcoxon", action="store_true")
    p.add_argument("--wilcoxon-alpha", type=float, default=0.05)
    p.add_argument("--bootstrap-confidence", type=float, default=0.95)
    p.add_argument("--bootstrap-n", type=int, default=5000)
    p.add_argument("--seed", type=int, default=0)

    # Release equivalence mode (optional)
    p.add_argument("--mode", choices=["pr", "release"], default="pr")
    p.add_argument("--equivalence-margin-ms", type=float, default=30.0, help="Used only in --mode release")

    args = p.parse_args()

    try:
        baseline = _parse_array(args.baseline)
        change = _parse_array(args.change)
    except Exception as e:
        print(f"Error parsing arrays: {e}", file=sys.stderr)
        return 2

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
        return 0 if (eq_payload and eq_payload["equivalent"]) else 1

    # PR mode: fail if gate check failed
    return 0 if gate.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
