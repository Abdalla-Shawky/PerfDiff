# Performance Regression Detection Tool

A production-ready statistical tool for detecting performance regressions with **premium UI**, **data quality gates**, and **rigorous statistical methodology**. Features world-class HTML reports, interactive visualizations, and automatic reliability checks.

[![Tests](https://img.shields.io/badge/tests-52%2F52%20passing-success)](docs/TEST_REPORT.md)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Statistical](https://img.shields.io/badge/statistical-rigorous-purple)]()

---

## 📑 Table of Contents

- [🎯 Why This Tool Exists](#-why-this-tool-exists)
- [✅ What This Tool Does Differently](#-what-this-tool-does-differently)
- [🚀 Quick Start](#-quick-start)
- [📖 Regression Detection Gates](#-regression-detection-gates)
- [📊 Comparison Table](#-comparison-table)
- [💡 Usage Examples](#-usage-examples)
- [🧪 Running Tests](#-running-tests)
- [🎯 Who Is This Tool For?](#-who-is-this-tool-for)
- [🚦 Configuration Options](#-configuration-options)
- [💡 Quick Tips](#-quick-tips)
- [📊 Project Structure](#-project-structure)
- [🏆 Why This Tool?](#-why-this-tool)
- [📚 Documentation](#-documentation)
- [📄 License](#-license)

---

## 🎯 Why This Tool Exists

### The Performance Testing Problem

Every engineering team faces these challenges when testing performance:

| Problem | What Happens | Impact |
|---------|--------------|--------|
| **False Positives** | 2ms noise flagged as "regression" | ❌ Blocked PRs, wasted time |
| **False Negatives** | Real 50ms regression missed due to variance | ❌ Regressions reach production |
| **No Statistical Rigor** | "Is 5ms real or noise?" → Unknown | ❌ Guesswork, not data |
| **Poor Data Quality** | 5 runs with 40% variance = "valid" | ❌ Unreliable conclusions |
| **Tail Latency Ignored** | Median OK, but P90 +200ms | ❌ User pain not detected |
| **Arbitrary Thresholds** | Fixed 10ms threshold for all operations | ❌ Fails for fast ops, misses slow ops |

### What Teams Usually Do (Wrong)

```python
# ❌ The naive approach
baseline_median = median(baseline_runs)
target_median = median(target_runs)

if target_median > baseline_median:
    print("REGRESSION!")  # False positives everywhere
```

**Problems:**
- No confidence: Is the difference real or random noise?
- No quality check: Works with any garbage data
- No tail check: Misses worst-case performance
- No context: Same threshold for 10ms and 10s operations

---

## ✅ What This Tool Does Differently

This tool was built from the ground up with **statistical rigor** to solve real performance testing problems.

### 1. **Multi-Layered Defense Against False Results**

```
                    ┌──────────────────┐
                    │  Quality Gates   │  ← Reject bad data FIRST
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
       ┌──────▼──────┐ ┌────▼────┐ ┌──────▼──────┐
       │ Median      │ │ Tail    │ │ Direction   │
       │ Threshold   │ │ Latency │ │ Check       │
       └──────┬──────┘ └────┬────┘ └──────┬──────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────▼─────────┐
                    │ Mann-Whitney U   │ ← Statistical test
                    │ (One-sided)      │   (directional)
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ Practical        │ ← Prevent false
                    │ Significance     │   positives on
                    │ Override         │   tiny changes
                    └──────────────────┘
```

**Why this matters:**
- **Quality gates** prevent garbage-in-garbage-out
- **Multiple checks** catch different types of regressions
- **Statistical test** provides confidence (p-value)
- **Practical override** prevents false positives on negligible changes

### 2. **Statistical Rigor (Not Guesswork)**

| What It Does | Why It Matters | Example |
|--------------|----------------|---------|
| **Mann-Whitney U Test** (one-sided) | Proves difference is real, not noise | p=0.003 → 99.7% confident target is slower |
| **Bootstrap CI** | Quantifies uncertainty | 95% CI: [8ms, 22ms] → won't include 0 if real |
| **Direction Checks** | Never fails on improvements | P(T>B) > 50% AND median_delta > 0 AND p < 0.05 |
| **Adaptive Tail Metric** | Stable with small samples | Mean of worst k samples (k adaptive) |
| **Quality Gates** | Rejects unreliable data | CV > 15% → INCONCLUSIVE (not false result) |

### 3. **Solves Real Problems**

**Problem 1: False Positive on Noise**
```
Baseline: 2400ms, Target: 2402.5ms
Simple median: "REGRESSION!" ❌
This tool: "PASS - below practical threshold (20ms)" ✅
```

**Problem 2: Missed Tail Regression**
```
Baseline: Median 101ms, Tail 150ms
Target:   Median 101ms, Tail 350ms
Simple median: "No change" ❌
This tool: "FAIL - Tail delta 200ms exceeds threshold" ✅
```

**Problem 3: Garbage Data**
```
Runs: [100, 95, 180, 90, 85]  # One wild outlier
CV = 34.5%
Simple median: "Valid result" ❌
This tool: "INCONCLUSIVE - CV 34.5% > 15% max" ✅
```

**Problem 4: False Failure on Improvement**
```
Target is 20ms faster (improvement!)
Old tools: Could fail due to statistical significance
This tool: "PASS" (direction check prevents false failures) ✅
```

---

## 🚀 Quick Start

### Installation

```bash
# Method 1: Install from GitHub (recommended)
pip install git+https://github.com/Abdalla-Shawky/PerfDiff.git@v1.0.0

# Method 2: Local development installation
git clone https://github.com/Abdalla-Shawky/PerfDiff.git
cd PerfDiff
pip install -e .

# Verify installation
perfdiff --help
```

**Dependencies (auto-installed):**
- `numpy` (≥1.20.0) - Numerical computing
- `scipy` (≥1.7.0) - Statistical functions (Mann-Whitney U test)

### Try It Now (Mock Data)

```bash
# Using CLI command
perfdiff \
    commit2commit/mock_data/baseline_traces.json \
    commit2commit/mock_data/target_traces.json \
    --output-dir ./test_output

# Or using module directly
python -m commit2commit.multi_trace_comparison \
    commit2commit/mock_data/baseline_traces.json \
    commit2commit/mock_data/target_traces.json \
    --output-dir ./test_output

# View results
open test_output/index.html
```

**Output:**
- 📊 `test_output/index.html` - Summary of all traces
- 📄 `test_output/[trace_name].html` - Detailed report per trace
- 🚦 Exit code: 0 (PASS) or 1 (FAIL with regressions)

---

## 📖 Regression Detection Gates

The tool performs checks in this order:

### 1. Quality Gates (Pre-check)
**Purpose:** Reject unreliable data before analysis
- Sample size: n ≥ 10 required
- Coefficient of variation: CV ≤ 15% required
- **Result:** PASS/INCONCLUSIVE (never FAIL on quality alone)

### 2. Median Delta Check
**Purpose:** Detect median performance change
- Threshold: max(5ms, 3% of baseline)
- No CV adjustment (CV > 15% → INCONCLUSIVE instead)
- **Result:** PASS/FAIL

### 3. Tail Latency Check
**Purpose:** Detect worst-case performance degradation
- Metric: Adaptive trimmed mean of worst k samples (k = 2 to 5)
- Threshold: max(75ms, 5% of baseline tail)
- No CV adjustment (CV > 15% → INCONCLUSIVE instead)
- **Result:** PASS/FAIL

### 4. Directionality (Informational)
**Purpose:** Screening metric only
- Metric: Fraction of target samples > baseline median
- Stored in details, NOT used for PASS/FAIL
- Mann-Whitney P(T>B) is the confirmatory test

### 5. Mann-Whitney U Test (One-sided)
**Purpose:** Statistical significance test
- Test: One-sided, alternative='greater'
- Alpha: 0.05 (5% significance level)
- **Direction check:** p < 0.05 AND P(T>B) >= 0.55
- **Note:** Removed `median_delta > 0` to catch tail-only regressions
- **Result:** PASS/FAIL

### 6. Practical Significance Override (Post-check)
**Purpose:** Prevent false positives on negligible changes
- **Dual threshold:** median_delta < threshold AND tail_delta < tail_threshold
- Overrides statistical failures when changes are negligible
- **Result:** Can convert FAIL → PASS (with explanation)

---

## 📊 Comparison Table

| Aspect | Simple Median | This Tool |
|--------|---------------|-----------|
| **Data quality check** | None | Quality gates (CV ≤ 15%, n ≥ 10) |
| **Threshold type** | Fixed or relative only | Adaptive (max of absolute + relative) |
| **Tail latency** | Not checked | Adaptive trimmed mean (k scales with n) |
| **Consistency check** | None | Directionality (informational) |
| **Statistical test** | None | One-sided Mann-Whitney U test |
| **Direction check** | None | Triple condition (prevents false failures) |
| **False positives** | High (2ms noise = "regression") | Low (practical significance override) |
| **False negatives** | High (noise hides real issues) | Low (multiple detection layers) |
| **Uncertainty** | Unknown | Bootstrap confidence intervals |
| **Result types** | Pass/Fail | Pass/Fail/Inconclusive/No Change |
| **Small sample handling** | Unreliable | Adaptive tail metric (stable with n=12) |
| **Multiple testing** | Not addressed | Documented (only 1 p-value test) |

---

## 💡 Usage Examples

### CLI Usage

```bash
# Production use
perfdiff baseline.json target.json --output-dir ./reports
```

### Programmatic Usage

```python
from commit2commit.trace_to_trace import gate_regression
import numpy as np

baseline = np.array([100, 102, 98, 101, 99, 103, 97, 100, 102, 101])
target = np.array([110, 112, 108, 111, 109, 113, 107, 110, 112, 111])

result = gate_regression(baseline, target)

if not result.passed:
    print(f"❌ {result.reason}")
    print(f"Δ median: {result.details['median_delta_ms']}ms")
    print(f"p-value: {result.details['mann_whitney_p']:.4f}")
```

### CI/CD Integration

```bash
pip install git+https://github.com/Abdalla-Shawky/PerfDiff.git@v1.0.0
perfdiff baseline.json target.json --output-dir ./reports
[ $? -eq 1 ] && echo "❌ Regressions detected" && exit 1
```

---

## 🧪 Running Tests

```bash
# Install test dependencies
pip install pytest

# Run all tests
cd commit2commit
python -m pytest test_trace_to_trace.py -v

# Expected output:
# ========================= 52 passed in ~5.0s =========================
```

---

## 🎯 Who Is This Tool For?

**Perfect for:**
- 🔧 **Performance Engineers** - Validating optimizations with statistical rigor
- ✅ **QA Teams** - Setting up reliable performance gates
- 👥 **Engineering Teams** - Tracking performance trends over time
- 🏗️ **Platform Teams** - Monitoring system health
- 🔬 **Data Scientists** - Anyone who values statistical correctness

**Not just another perf tool. This is:**
- ✅ Statistically rigorous (Mann-Whitney U, Bootstrap CI)
- ✅ Battle-tested (52/52 tests passing)
- ✅ Production-ready (comprehensive documentation)
- ✅ Professional UI (stakeholders trust it)
- ✅ False-positive resistant (practical significance override)
- ✅ False-negative resistant (multiple detection layers)

---

## 🚦 Configuration Options

### Quick Reference

| Option | Description | Default |
|--------|-------------|---------|
| `--baseline` | Baseline measurements (required) | - |
| `--target` | Target measurements (required) | - |
| `--out` | Output HTML file (required) | - |
| `--mode` | `pr` or `release` | `pr` |
| `--ms-floor` | Absolute threshold (ms) | `5.0` |
| `--pct-floor` | Relative threshold (fraction) | `0.03` (3%) |
| `--tail-ms-floor` | Tail absolute threshold | `75.0` |
| `--tail-pct-floor` | Tail relative threshold | `0.05` (5%) |
| `--directionality` | Max fraction slower (informational) | `0.70` (70%) |
| `--no-mann-whitney` | Disable Mann-Whitney U test | False |
| `--mann-whitney-alpha` | Significance level | `0.05` |
| `--seed` | Random seed | `0` |

See `--help` for all options.

---

## 💡 Quick Tips

### Choosing the Right Mode

**PR Mode** (`--mode pr`): Strict regression gate
- Use for: PRs, feature branches, continuous testing
- Goal: Catch any performance degradation
- Fails if: Median, tail, or Mann-Whitney exceeds thresholds

**Release Mode** (`--mode release`): Equivalence testing
- Use for: Release validation, stable builds
- Goal: Ensure performance hasn't significantly changed
- Fails if: Bootstrap CI for median delta is outside margin

### Sample Size Guidelines

| Samples | Reliability | Use Case |
|---------|-------------|----------|
| 3-5 | Low | Quick checks only |
| 10-20 | Good | Most use cases ✅ |
| 30+ | Excellent | Critical paths, noisy environments |

### Sequential Testing Methodology

✅ **Correct (AAA BBB):**
```bash
# Run all baseline measurements
for i in {1..10}; do measure_baseline; done
# Then run all target measurements
for i in {1..10}; do measure_target; done
```

❌ **Incorrect (interleaved):**
```bash
# Don't interleave measurements
for i in {1..10}; do
  measure_baseline
  measure_target
done
```

**Why?** The tool uses independent samples testing (Mann-Whitney U), which assumes samples are collected independently.

---

## 📊 Project Structure

```
PerfDiff/
├── commit2commit/                          # Main package
│   ├── trace_to_trace.py                  # Core: Single trace statistical analysis
│   ├── multi_trace_comparison.py          # Orchestrator: Multi-trace + CLI entry point
│   ├── constants.py                       # Configuration thresholds
│   │
│   ├── perf_html_report.py                # HTML report generator
│   ├── perf_html_template.py              # Premium UI template
│   ├── comparison_html_template.py        # Summary table template
│   ├── trace_detail_html_template.py      # Individual trace template
│   ├── timeline_html_template.py          # Timeline visualization
│   │
│   ├── test_trace_to_trace.py             # Test suite (52 tests passing)
│   ├── mock_data/                         # Sample traces for testing
│   │   ├── baseline_traces.json
│   │   └── target_traces.json
│   └── __init__.py
│
├── setup.py                                # pip installation config
├── requirements.txt                        # Python dependencies
├── run_comparison.sh                       # Quick test script
│
├── README.md                               # This file
├── STATISTICAL_FIXES_SUMMARY.md           # Statistical methodology
├── TOOL_TECHNICAL_SUMMARY.md              # Technical details
├── EXECUTIVE_SUMMARY.md                   # High-level overview
│
└── docs/                                   # Detailed documentation
    ├── USER_GUIDE.md
    ├── TEST_REPORT.md
    └── ... (20+ documentation files)
```

**Key Modules:**

| Module | Purpose |
|--------|---------|
| `trace_to_trace.py` | Core statistical engine - compares one trace pair |
| `multi_trace_comparison.py` | CLI tool - compares multiple traces, generates reports |
| `constants.py` | All thresholds (MS_FLOOR, PCT_FLOOR, CV limits, etc.) |
| `perf_html_*.py` | HTML report generation with interactive charts |

---
## 📚 Documentation

📖 **Full User Guide**: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
📊 **Technical Summary**: [TOOL_TECHNICAL_SUMMARY.md](TOOL_TECHNICAL_SUMMARY.md)
📊 **Statistical Details**: [STATISTICAL_FIXES_SUMMARY.md](STATISTICAL_FIXES_SUMMARY.md)
🧪 **Test Results**: [docs/TEST_REPORT.md](docs/TEST_REPORT.md)
📋 **Executive Summary**: [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)

**Version:** 1.0.0
**Author:** Shawky
**Repository:** [github.com/Abdalla-Shawky/PerfDiff](https://github.com/Abdalla-Shawky/PerfDiff)

---

## 📄 License

MIT License - Feel free to use in your projects!

