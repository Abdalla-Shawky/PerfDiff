# Commit-to-Commit Comparison Overview

This module detects performance regressions between a **baseline** build and a **target** build using paired measurements. It goes beyond comparing two medians by incorporating data-quality checks, tail latency, directionality, and statistical tests to reduce false positives/negatives in noisy environments.

---

## What It Does (High-Level)

Given two equal-length arrays of paired measurements:
- **Baseline**: performance before the change
- **Target**: performance after the change

The system:
1. Validates data quality (sample size + variance gates)
2. Computes paired deltas (target - baseline)
3. Evaluates regression signals (median, tail, directionality, statistics)
4. Applies practical significance rules
5. Produces a clear verdict (PASS / FAIL / NO CHANGE / INCONCLUSIVE)
6. Generates HTML reports (single-trace and multi-trace)

---

## Core Algorithms and Checks (With Examples)

1) **Data Quality Gates (pre-check)**
- **Minimum sample size**: Rejects too-small datasets.
- **Variance gate (CV)**: Rejects datasets with high coefficient of variation.
- If quality is too poor, the result is **INCONCLUSIVE** (does not fail CI).

Why: Unreliable data should not produce a false PASS or FAIL.

Example:
- Baseline: [120, 98, 105, 140, 110], Target: [95, 130, 90, 150, 85]\n
- Baseline CV = 22%, Target CV = 19% (both above threshold) → **INCONCLUSIVE**\n
Why needed: High variance can flip medians and p-values randomly between runs.

2) **Paired Delta Computation**
- For each run: `delta_i = target_i - baseline_i`
- Uses paired deltas to remove run-to-run noise.

Example:
- Baseline: [100, 102, 98], Target: [103, 101, 99] → Deltas: [3, -1, 1]\n
Why needed: Pairing removes environmental drift (e.g., thermal or background load).

3) **Median Delta Threshold**
- Compares median delta to an **adaptive threshold**:
  - `max(ms_floor, pct_floor * baseline_median)`
  - Scaled by a **CV-based multiplier** to be more conservative when variance is high.

Example:
- Baseline: [980, 1000, 1010], Target: [1040, 1055, 1035]\n
- Baseline median = 1000ms, pct_floor = 5%, ms_floor = 50ms → base threshold = 50ms\n
- If CV is elevated, threshold increases (stricter) → reduces false FAILs.

4) **Tail Latency (p90)**
- Compares p90 delta to a tail threshold using the same adaptive logic.

Why: Median alone can miss regressions in worst-case performance.

Example:
- Baseline: [90, 100, 95, 98, 120], Target: [92, 101, 96, 99, 200]\n
- Median delta = +1ms (looks fine), but p90 delta ≈ +80ms (bad) → **FAIL**\n
Why needed: Users feel tail regressions even when median looks stable.

5) **Directionality Check**
- If the fraction of positive deltas exceeds a threshold (e.g., 70%),
  it indicates consistent slowdown even if the median is near the threshold.

Example:
- Baseline: [100, 100, 100, 100, 100, 100, 100, 100, 100, 100]\n
- Target:   [101, 102, 100, 101, 103, 101, 100, 102, 101, 101] → 9/10 slower\n
- Directionality = 90% ≥ 70% → **FAIL**\n
Why needed: Consistent small slowdowns can be real even if median is borderline.

6) **Wilcoxon Signed-Rank Test (optional)**
- Tests whether target is significantly slower than baseline.
- Adds statistical confidence for small effect sizes.

Example:
- Baseline: [100, 101, 99, 100, 101], Target: [108, 109, 107, 108, 109]\n
- Median delta = +8ms, p-value = 0.01 (< 0.05) → statistically significant slowdown\n
Why needed: Detects real shifts when distributions overlap.

7) **Bootstrap Confidence Interval**
- Computes CI on median delta to show uncertainty and confidence.

Example:
- Baseline: [100, 100, 101, 99, 100], Target: [104, 105, 103, 104, 106]\n
- 95% CI for median delta = [+2ms, +12ms] → suggests consistent regression\n
Why needed: Shows uncertainty and avoids overconfidence from single point estimates.

8) **Practical Significance Rules**
- If the delta is below a dynamic practical threshold, the tool:
  - Marks **NO CHANGE** (if otherwise passing), or
  - Overrides FAIL into PASS (if statistically significant but trivial)

Why: Avoids blocking on tiny, statistically-significant but practically irrelevant changes.

Example:
- Baseline: [1490, 1505, 1510, 1498, 1502], Target: [1491, 1506, 1511, 1499, 1503]\n
- Median delta = +1.5ms on 1500ms baseline; practical threshold = 5ms\n
- Wilcoxon says significant, but delta is negligible → **PASS (override)**\n
Why needed: Prevents CI failures for changes users can’t perceive.

---

## Verdict States

- **PASS**: No regression detected.
- **FAIL**: Regression detected (median/tail/directionality/Wilcoxon exceeded thresholds).
- **NO CHANGE**: Delta is within practical significance bounds.
- **INCONCLUSIVE**: Data quality too poor to decide.

---

## Multi-Trace Flow (commit_to_commit_comparison/multi_trace_comparison.py)

1. Load baseline and target JSON files with trace lists.
2. Match traces by name.
3. For each matched trace, run `gate_regression`.
4. Render:
   - `index.html` summary
   - Per-trace detail pages

Unmatched traces are reported as warnings.

---

## Why This Beats Comparing Two Medians

A simple "median vs median" check can be misleading:

- **Noisy data** can create false regressions or hide real ones.
- **Tail regressions** (p90) may not appear in the median.
- **Directional slowdowns** can be consistent even if medians overlap.
- **Statistical significance** matters when deltas are small.
- **Practical significance** matters when deltas are negligible.

This system combines multiple signals, adapts thresholds to variance, and uses
statistical methods to make decisions that are robust to noise.

---

## Key Files

- `commit_to_commit_comparison/commit_to_commit_comparison.py`
  - Core regression gate logic
- `commit_to_commit_comparison/perf_html_report.py`
  - HTML report generation (single trace)
- `commit_to_commit_comparison/perf_html_template.py`
  - UI template for reports
- `commit_to_commit_comparison/multi_trace_comparison.py`
  - Multi-trace comparison and HTML summary

---

## Feature Review (Quick Pass)

No critical correctness issues found in the current implementation.

Notable considerations:
- **CLI compatibility**: `--change` is supported as a deprecated alias for `--target` (warns on use).
- **Inconclusive behavior**: Quality gates intentionally return PASS with `inconclusive=True` to avoid failing CI on bad data.
- **Practical override**: Statistical failures can be overridden if deltas are below practical thresholds; this is intended and should be communicated to stakeholders.

Potential enhancements (optional):
- Add a deprecated `--change` alias in `perf_html_report.py` for backward compatibility.
- Emit a warning if `--change` is used (if alias added).

---

## Summary

This tool is a statistically aware, production-ready regression gate. It
combines robust checks (median, tail, directionality, Wilcoxon, bootstrap CI)
with quality gates and practical significance to avoid false positives and
false negatives that a naive median-only comparison would miss.
