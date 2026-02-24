# Performance Regression Detection Tool

A production-ready statistical tool for detecting performance regressions with **premium UI**, **data quality gates**, and **rigorous statistical methodology**. Features world-class HTML reports, interactive visualizations, and automatic reliability checks.

[![Tests](https://img.shields.io/badge/tests-52%2F52%20passing-success)](docs/TEST_REPORT.md)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Statistical](https://img.shields.io/badge/statistical-rigorous-purple)]()

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
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install numpy scipy pytest
```

### Try It Now (Mock Data)

```bash
./run_comparison.sh \
    commit_to_commit_comparison/mock_data/baseline_traces.json \
    commit_to_commit_comparison/mock_data/target_traces.json \
    commit_to_commit_comparison/test_output

# View results
open commit_to_commit_comparison/test_output/index.html
```

This will:
- ✅ Process 10 sample traces with various scenarios
- ✅ Generate HTML reports with interactive charts
- ✅ Demonstrate all regression detection features
- ✅ Show exit code 0 (success) or 1 (regression detected)

### Basic Usage

```bash
python commit_to_commit_comparison/perf_html_report.py \
  --baseline "[800,805,798,810,799,803,801,807,802,804]" \
  --target   "[845,850,838,860,842,848,844,855,849,847]" \
  --out performance_report.html
```

**Output:**
- 📄 `generated_reports/performance_report.html` - Interactive HTML report
- 🚦 Exit code 0 (pass) or 1 (fail) for CI/CD

---

## 🔬 Statistical Methodology

### What Makes This Tool Statistically Sound

#### 1. One-Sided Mann-Whitney U Test ✅

**Why one-sided?**
- We have a directional hypothesis: "Is target slower than baseline?"
- One-sided test has more statistical power for directional hypotheses
- Combined with direction checks (P(T>B) > 0.5 AND median_delta > 0)

**Result:** Never fails on performance improvements, maximum power for detecting regressions

#### 2. Adaptive Tail Latency Metric ✅

**Problem with P90:** With n=12, P90 is position 10.9/12 (near-maximum, extremely jumpy)

**Our solution:** Adaptive trimmed mean of worst k samples
```
k = min(MAX_TAIL_METRIC_K, max(MIN_TAIL_METRIC_K, ceil(n * TAIL_METRIC_K_PCT)))

Examples:
  n=10:  k=2 (mean of worst 2 samples - 20% of data)
  n=12:  k=2 (mean of worst 2 samples - 17% of data)
  n=30:  k=3 (mean of worst 3 samples - 10% of data)
  n=50:  k=5 (mean of worst 5 samples - 10% of data)
  n=100: k=5 (mean of worst 5 samples - 5% of data, capped)
```

**Benefits:**
- More stable than single percentile with small samples
- Automatically scales with sample size
- Less sensitive to individual outliers
- Uses at least 2 samples (MIN_TAIL_METRIC_K), at most 5 (MAX_TAIL_METRIC_K)
- Uses ceil() to round up for proper tail coverage

#### 3. Practical Significance Override ✅

**The problem:** Statistical significance ≠ practical importance

**Example:**
```
Baseline: 2500ms
Target:   2502.5ms
Mann-Whitney p-value: 0.003 (statistically significant!)
Delta: 2.5ms (0.1%)
```

**Without override:** FAIL ❌ (statistically significant)
**With override:** PASS ✅ (below practical threshold of 20ms)

**Dual-threshold check:**
- Override only applies if BOTH median AND tail deltas are negligible
- Prevents hiding tail regressions while allowing override on median

#### 4. Multiple Testing (Documented, Not Inflated)

**Common concern:** Multiple tests → inflated false positive rate?

**Reality:** Only 1 test uses p-values (Mann-Whitney)
- Median delta: Threshold comparison (not p-value)
- Tail latency: Threshold comparison (not p-value)
- Directionality: Informational only (not used for PASS/FAIL)

**Result:** Family-wise error rate ≈ 0.05 (dominated by Mann-Whitney alone)

#### 5. Direction Checks (No False Failures)

**Dual condition for Mann-Whitney failure:**
```python
if p_greater < 0.05 AND prob_target_greater >= 0.55:
    FAIL  # Both conditions must be met
```

**Why P(T>B) >= 0.55?**
- Mild effect size filter (55% threshold)
- Ensures target is stochastically worse, not just different
- Removed `median_delta > 0` check to catch tail-only regressions

**Result:** Never fails on performance improvements, catches tail-only regressions

---

## 📊 Key Features

### 🎨 Premium UI
- **World-class design** - Professional UI inspired by Stripe, Vercel, and Linear
- **Interactive Chart.js visualizations** - Histogram, line charts, statistical summaries
- **Dark mode** - Beautiful dark theme optimized for reduced eye strain
- **Smooth animations** - Polished micro-interactions and transitions
- **Responsive design** - Optimized for mobile, tablet, and desktop
- **Export functionality** - JSON, CSV, and print/PDF support

### 🔬 Data Quality Assessment
- **Quality scoring** - 0-100 score based on sample size, variance, outliers
- **Quality gates** - Automatic rejection of unreliable data (CV > 15%)
- **INCONCLUSIVE status** - Returns inconclusive instead of false positives/negatives
- **Visual indicators** - Color-coded quality badges and progress bars
- **Issue detection** - Identifies high variance, outliers, insufficient samples

### 🎯 Statistically Rigorous
- **One-sided Mann-Whitney U test** - Directional hypothesis testing
- **Bootstrap confidence intervals** - Default 95% CI for median delta
- **Independent sample comparisons** - Proper for sequential testing (AAA BBB)
- **Multi-check validation** - Median, tail, directionality, and statistical tests
- **Direction checks** - Never fails on improvements (P(T>B) >= 0.55)

### 🛡️ Quality Gates & Validation
- **Pre-flight checks** - Validates data quality before regression detection
- **CV threshold** - Rejects data with coefficient of variation > 15%
- **Sample size checks** - Requires minimum 10 samples for reliability
- **INCONCLUSIVE handling** - High variance → INCONCLUSIVE (not stricter thresholds)
- **Transparent reporting** - Shows thresholds and observed values

### 📊 Adaptive Thresholds
- **Hybrid approach** - Combines absolute (ms) and relative (%) thresholds
- **Fast & slow operations** - Works for <100ms and >1s operations
- **Configurable** - Customize thresholds via CLI or constants.py
- **Example**: Fail if change > max(5ms, 3% of baseline)
- **No CV multiplier** - Quality gates handle variance (CV > 15% → INCONCLUSIVE)

### 🤖 CI/CD Ready
- **Exit codes** - 0 (pass), 1 (fail), 2 (error) for automation
- **JSON input support** - Parse arrays from JSON or CSV format
- **Reproducible results** - Fixed random seeds
- **Auto-folder creation** - Reports saved to `generated_reports/`
- **Modes**: PR (strict) vs Release (equivalence testing)

---

## 🆕 Latest Updates

### Version 4.0 - Critical Fixes & Statistical Rigor (February 2026)

**Critical Bug Fixes** 🐛
- **MS_FLOOR threshold**: Fixed absurd 50ms → **5ms** (10x stricter, matches typical latency ranges)
- **PCT_FLOOR threshold**: Fixed 5% → **3%** (more appropriate for typical operations)
- **CV multiplier removed**: Eliminated contradictory logic (made thresholds MORE permissive when variance high)
- **Mann-Whitney direction check**: Removed `median_delta > 0` check to catch tail-only regressions
- **Mann-Whitney threshold**: Changed P(T>B) > 0.5 → **P(T>B) >= 0.55** (mild effect size filter)
- **Practical override**: Now directional (no abs()), only applies to regressions
- **Tail metric k**: Changed MIN from 3 → **2**, added MAX cap at **5**, uses ceil() not int()

**Statistical Improvements** 📊
- **Explicit one-sided test**: Mann-Whitney now explicitly one-sided with documented rationale
- **MWU U-statistic documentation**: Comprehensive documentation of probability calculation and tie handling
- **Multiple testing documentation**: Clarified that only 1 gate uses p-values (limited inflation)
- **Adaptive k calculation**: Tail metric uses k = min(5, max(2, ceil(n * 0.10))) for optimal stability

**Impact:**
- ✅ Appropriate thresholds (5ms floor, 3% relative)
- ✅ No contradictory CV logic
- ✅ Catches tail-only regressions
- ✅ Never false-fails on improvements
- ✅ Never hides tail regressions
- ✅ More stable tail metrics with small samples
- ✅ Better statistical transparency

**Test Coverage:**
- 52/52 tests passing (up from 45, +7 new tests)
- All critical fixes validated
- Full regression suite passing

See [TOOL_TECHNICAL_SUMMARY.md](TOOL_TECHNICAL_SUMMARY.md) for complete technical details.

### Version 3.0 - Independent Samples Support

**Independent Samples Testing** 🔬
- Converted from paired samples (ABA BAB) to independent samples (AAA BBB)
- Replaced Wilcoxon signed-rank test with Mann-Whitney U test
- Arrays can now have different lengths
- Proper sequential testing methodology

**Breaking Changes** 🚨
- `--no-wilcoxon` → `--no-mann-whitney`
- `--wilcoxon-alpha` → `--mann-whitney-alpha`
- `use_wilcoxon` parameter → `use_mann_whitney`

### Version 2.0 - Major UI & Quality Overhaul

**Premium UI Redesign** 🎨
- Complete visual overhaul with modern design system
- Enhanced hover states and micro-interactions
- Optimized for both light and dark modes

**Data Quality Gates** 🔬
- Automatic detection of unreliable measurements
- INCONCLUSIVE status prevents false positives/negatives
- Quality scoring (0-100) with visual indicators

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

## 💡 Examples

### Example 1: Multi-Trace Comparison

```bash
./run_comparison.sh \
    commit_to_commit_comparison/mock_data/baseline_traces.json \
    commit_to_commit_comparison/mock_data/target_traces.json \
    commit_to_commit_comparison/test_output

open commit_to_commit_comparison/test_output/index.html
```

### Example 2: Basic Comparison

```bash
python commit_to_commit_comparison/perf_html_report.py \
  --baseline "[100,102,98,101,99]" \
  --target   "[110,112,108,111,109]" \
  --out report.html
```

### Example 3: CI/CD Integration

```bash
# Run benchmarks (sequential testing - AAA BBB)
./run_benchmarks.sh > baseline.txt
./run_benchmarks.sh > target.txt

# Check for regression
python commit_to_commit_comparison/perf_html_report.py \
  --baseline "$(cat baseline.txt)" \
  --target "$(cat target.txt)" \
  --out report.html

# Exit code will be 1 if regression detected
if [ $? -ne 0 ]; then
  echo "❌ Performance regression detected!"
  exit 1
fi
```

---

## 🧪 Running Tests

```bash
# Install test dependencies
pip install pytest

# Run all tests
cd commit_to_commit_comparison
python -m pytest test_commit_to_commit_comparison.py -v

# Expected output:
# ========================= 52 passed in ~5.0s =========================
```

---

## 📚 Documentation

All documentation is located in the [`docs/`](docs/) folder.

### Core Guides

| Document | Description |
|----------|-------------|
| [TOOL_TECHNICAL_SUMMARY.md](TOOL_TECHNICAL_SUMMARY.md) | 📊 **NEW!** Complete technical summary (Version 2.0) |
| [STATISTICAL_FIXES_SUMMARY.md](STATISTICAL_FIXES_SUMMARY.md) | 📊 Original statistical fixes documentation (Version 1.0) |
| [USER_GUIDE.md](docs/USER_GUIDE.md) | 📖 Complete usage guide with examples |
| [TEST_REPORT.md](docs/TEST_REPORT.md) | 🧪 Comprehensive test results (52/52 passing) |
| [MEASUREMENT_GUIDE.md](docs/MEASUREMENT_GUIDE.md) | 📏 Best practices for measurement |

### Feature Documentation

| Document | Description |
|----------|-------------|
| [PREMIUM_UI_COMPLETE.md](docs/PREMIUM_UI_COMPLETE.md) | 🎨 Premium UI design details |
| [DATA_QUALITY_FEATURE.md](docs/DATA_QUALITY_FEATURE.md) | 🔬 Data quality assessment |
| [QUALITY_GATES_GUIDE.md](docs/QUALITY_GATES_GUIDE.md) | 🚦 Quality gates explained |
| [MODES_EXPLAINED.md](docs/MODES_EXPLAINED.md) | ⚙️ PR vs Release mode |
| [THRESHOLD_COMPUTATION_EXPLAINED.md](docs/THRESHOLD_COMPUTATION_EXPLAINED.md) | 📊 Threshold calculation |

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
.
├── commit_to_commit_comparison/
│   ├── commit_to_commit_comparison.py  # Core regression detection logic
│   ├── perf_html_report.py             # CLI and HTML report generation
│   ├── perf_html_template.py           # HTML/CSS/JS template
│   ├── multi_trace_comparison.py       # Multi-trace comparison
│   ├── test_commit_to_commit_comparison.py  # Test suite (52 tests)
│   ├── mock_data/                      # Sample test data
│   └── test_output/                    # Generated test reports
├── constants.py                        # Configuration constants
├── STATISTICAL_FIXES_SUMMARY.md        # Statistical fixes documentation
├── README.md                           # This file
├── docs/                               # Documentation folder (20+ files)
└── generated_reports/                  # Generated HTML reports (gitignored)
```

---

## 🏆 Why This Tool?

This isn't just another performance testing tool. It's a **complete solution** built with:

✅ **Statistical Rigor** - One-sided Mann-Whitney U, bootstrap CI, direction checks
✅ **Data Quality Focus** - Automatic detection of unreliable measurements
✅ **Professional UI** - World-class design that stakeholders trust
✅ **Production Ready** - 52/52 tests passing, comprehensive documentation
✅ **CI/CD Friendly** - Exit codes, auto-folder creation, reproducible results
✅ **Transparent** - Shows all thresholds, configurations, and quality metrics
✅ **No False Failures** - Direction checks prevent failures on improvements
✅ **No Hidden Regressions** - Dual-threshold override respects tail latency

**Stop guessing. Start measuring with statistical rigor.** 📊

---

## 📄 License

MIT License - Feel free to use in your projects!

---

## 🚀 Support

📖 **Full Documentation**: See [USER_GUIDE.md](docs/USER_GUIDE.md)
📊 **Technical Summary**: See [TOOL_TECHNICAL_SUMMARY.md](TOOL_TECHNICAL_SUMMARY.md)
📊 **Statistical Details**: See [STATISTICAL_FIXES_SUMMARY.md](STATISTICAL_FIXES_SUMMARY.md)
🧪 **Test Results**: See [TEST_REPORT.md](docs/TEST_REPORT.md)
🚀 **Quick Start**: Try `./run_comparison.sh` with mock data

---

**Built with statistical rigor. Tested thoroughly. Production ready.** 🚀

**Version 4.0** - Critical Fixes · Appropriate Thresholds · No CV Contradictions · Tail-Only Regression Detection · 52/52 Tests Passing
