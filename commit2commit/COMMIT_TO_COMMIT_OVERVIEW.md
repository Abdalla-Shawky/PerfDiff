# Commit-to-Commit Comparison Overview

This module detects performance regressions between a **baseline** build and a **target** build using independent samples. It goes beyond comparing two medians by incorporating data-quality checks, tail latency, directionality, and statistical tests to reduce false positives/negatives in noisy environments.

---

## What It Does (High-Level)

Given two arrays of independent measurements:
- **Baseline**: performance before the change (collected sequentially)
- **Target**: performance after the change (collected sequentially)

The system:
1. Validates data quality (sample size + variance gates for each array)
2. Computes median difference (target median - baseline median)
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

2) **Median Difference Computation**
- Compares medians directly: `median_delta = median(target) - median(baseline)`
- Arrays can have different lengths (independent samples).

Example:
- Baseline: [100, 102, 98, 105, 103] (5 samples), Target: [108, 110, 107] (3 samples)\n
- median(baseline) = 102ms, median(target) = 108ms → median_delta = +6ms\n
Why: Robust central tendency comparison for independent samples.

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
- Checks what fraction of target samples exceed baseline median.
- If this fraction exceeds a threshold (e.g., 70%), indicates consistent slowdown.

Example:
- Baseline: [100, 100, 100, 100, 100], median = 100ms\n
- Target:   [101, 102, 103, 101, 104, 102, 103, 101, 102, 101] (10 samples)\n
- 10/10 target samples > 100ms → Directionality = 100% ≥ 70% → **FAIL**\n
Why needed: Detects when target distribution is consistently slower than baseline.

6) **Mann-Whitney U Test (optional)**
- Non-parametric test for independent samples.
- Tests whether target distribution is stochastically greater than baseline.
- Adds statistical confidence for detecting distributional shifts.

Example:
- Baseline: [100, 101, 99, 100, 101], Target: [108, 109, 107, 108, 109]\n
- Median difference = +8ms, p-value = 0.01 (< 0.05) → statistically significant slowdown\n
Why needed: Detects real distributional shifts even when there's overlap.

7) **Bootstrap Confidence Interval**
- Computes CI on median difference by resampling baseline and target independently.
- Shows uncertainty and confidence in the median difference estimate.

Example:
- Baseline: [100, 100, 101, 99, 100], Target: [104, 105, 103, 104, 106]\n
- 95% CI for median difference = [+2ms, +12ms] → suggests consistent regression\n
Why needed: Quantifies uncertainty and avoids overconfidence from point estimates.

8) **Practical Significance Rules**
- If the delta is below a dynamic practical threshold, the tool:
  - Marks **NO CHANGE** (if otherwise passing), or
  - Overrides FAIL into PASS (if statistically significant but trivial)

Why: Avoids blocking on tiny, statistically-significant but practically irrelevant changes.

Example:
- Baseline: [1490, 1505, 1510, 1498, 1502], Target: [1491, 1506, 1511, 1499, 1503]\n
- Median difference = +1.5ms on 1500ms baseline; practical threshold = 5ms\n
- Mann-Whitney U says significant, but delta is negligible → **PASS (override)**\n
Why needed: Prevents CI failures for changes users can't perceive.

---

## Verdict States

- **PASS**: No regression detected.
- **FAIL**: Regression detected (median/tail/directionality/Mann-Whitney U exceeded thresholds).
- **NO CHANGE**: Difference is within practical significance bounds.
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

- `commit2commit/trace_to_trace.py`
  - Core regression gate logic (single trace comparison)
- `commit2commit/multi_trace_comparison.py`
  - Orchestrator for comparing multiple traces + CLI
- `commit2commit/perf_html_report.py`
  - HTML report generation (single trace)
- `commit2commit/perf_html_template.py`
  - UI template for reports

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
combines robust checks (median, tail, directionality, Mann-Whitney U, bootstrap CI)
with quality gates and practical significance to avoid false positives and
false negatives that a naive median-only comparison would miss.
