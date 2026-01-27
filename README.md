# Performance Regression Detection Tool

A production-ready statistical tool for detecting performance regressions with **premium UI**, **data quality gates**, and **intelligent analysis**. Features world-class HTML reports, interactive visualizations, and automatic reliability checks.

[![Tests](https://img.shields.io/badge/tests-24%2F24%20passing-success)](docs/TEST_REPORT.md)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)]()

---

## Quick Start

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install numpy scipy pytest
```

### Basic Usage

```bash
python perf_html_report.py \
  --baseline "[800,805,798,810,799,803,801,807,802,804]" \
  --target   "[845,850,838,860,842,848,844,855,849,847]" \
  --out performance_report.html
```

**Output:**
- 📄 `generated_reports/performance_report.html` - Interactive HTML report
- 🚦 Exit code 0 (pass) or 1 (fail) for CI/CD

**Note:** All HTML reports are automatically saved to the `generated_reports/` folder.

---

## What Does It Do?

This tool:
1. ✅ **Compares** baseline vs target performance measurements
2. 📊 **Detects** regressions using multiple statistical tests
3. 📈 **Generates** beautiful HTML reports with visualizations
4. 🤖 **Integrates** with CI/CD via exit codes

### Regression Checks

- **Median Delta**: Is the median change too large?
- **Tail Latency (p90)**: Did worst-case performance degrade?
- **Directionality**: Are too many runs slower?
- **Wilcoxon Test**: Is the difference statistically significant?
- **Bootstrap CI**: What's the confidence interval for the change?
- **Quality Gates**: Is the data reliable enough for analysis?

---

## ✨ Report Preview

The tool generates premium, interactive HTML reports with:

- **🎨 Modern Design** - Professional UI with gradient accents and smooth animations
- **📊 Interactive Charts** - Chart.js visualizations (histogram, line charts, statistical summary)
- **🌙 Dark Mode** - Beautiful dark theme toggle with localStorage persistence
- **📈 Quality Assessment** - Visual scoring and issue detection (0-100 scale)
- **⚙️ Configuration Display** - Transparent threshold and quality gate settings
- **📥 Export Options** - JSON, CSV, and print/PDF support

**Key Sections:**
1. **Executive Summary** - Large status indicator, before/after comparison, plain English verdict
2. **Interactive Charts** - Distribution histogram, run-by-run comparison, statistical summary
3. **Data Quality** - Quality scores, CV metrics, outlier detection, visual indicators
4. **Technical Details** - Wilcoxon test, bootstrap CI, quality gates configuration
5. **Raw Data** - Per-run breakdown with outlier marking

See [PREMIUM_UI_COMPLETE.md](docs/PREMIUM_UI_COMPLETE.md) for design details and screenshots.

---

## Use Cases

| Use Case | Mode | Example |
|----------|------|---------|
| 🚦 **PR Performance Gate** | `pr` | Block PRs with >5% regression |
| 🚀 **Release Validation** | `release` | Verify releases stay within ±30ms |
| 🔬 **A/B Testing** | `pr` | Compare two implementations |
| 📈 **Performance Tracking** | `pr` | Monitor trends over time |
| ⚡ **Optimization Verification** | `pr` | Confirm improvements worked |

---

## Features

### 🎨 Premium UI (NEW!)
- **World-class design** - Professional UI inspired by Stripe, Vercel, and Linear
- **Interactive Chart.js visualizations** - Histogram, line charts, statistical summaries
- **Dark mode** - Beautiful dark theme optimized for reduced eye strain
- **Smooth animations** - Polished micro-interactions and transitions
- **Responsive design** - Optimized for mobile, tablet, and desktop
- **Export functionality** - JSON, CSV, and print/PDF support

### 🔬 Data Quality Assessment (NEW!)
- **Quality scoring** - 0-100 score based on sample size, variance, outliers
- **Quality gates** - Automatic rejection of unreliable data (CV > 15%)
- **INCONCLUSIVE status** - Returns inconclusive instead of false positives/negatives
- **Visual indicators** - Color-coded quality badges and progress bars
- **Issue detection** - Identifies high variance, outliers, insufficient samples

### 🎯 Statistically Sound
- **Wilcoxon signed-rank test** - Proper z-scores for statistical significance
- **Bootstrap confidence intervals** - Default 95% CI for median delta
- **Paired sample comparisons** - Accounts for run-to-run correlation
- **Multi-check validation** - Median, tail, directionality, and statistical tests

### 🛡️ Quality Gates & Validation
- **Pre-flight checks** - Validates data quality before regression detection
- **CV threshold** - Rejects data with coefficient of variation > 15%
- **Sample size checks** - Requires minimum 10 samples for reliability
- **Adaptive thresholds** - Stricter thresholds for higher variance data
- **Transparent reporting** - Shows thresholds and observed values

### 📊 Adaptive Thresholds
- **Hybrid approach** - Combines absolute (ms) and relative (%) thresholds
- **CV-based multiplier** - Automatically adjusts strictness based on variance
- **Fast & slow operations** - Works for <100ms and >1s operations
- **Configurable** - Customize thresholds via CLI or constants.py
- **Example**: Fail if change > max(50ms, 5% of baseline) × cv_multiplier

### 🤖 CI/CD Ready
- **Exit codes** - 0 (pass), 1 (fail), 2 (error) for automation
- **JSON input support** - Parse arrays from JSON or CSV format
- **Reproducible results** - Fixed random seeds
- **Auto-folder creation** - Reports saved to `generated_reports/`
- **Modes**: PR (strict) vs Release (equivalence testing)

### 📈 Advanced Analytics
- **Outlier detection** - IQR-based outlier marking
- **Run-by-run analysis** - Paired delta visualization
- **Statistical summary** - Min, Q1, median, Q3, max, mean
- **Directionality check** - Ensures consistent improvement/regression
- **Tail latency (p90)** - Catches worst-case performance issues

---

## 🆕 Latest Updates

### Version 2.0 - Major UI & Quality Overhaul

**Premium UI Redesign** 🎨
- Complete visual overhaul with modern design system
- Inter font, gradient accents, layered shadows
- Enhanced hover states and micro-interactions
- Circular toggle icons, premium badges
- Optimized for both light and dark modes

**Data Quality Gates** 🔬
- Automatic detection of unreliable measurements
- INCONCLUSIVE status prevents false positives/negatives
- Quality scoring (0-100) with visual indicators
- Transparent threshold display with pass/fail status

**Improved Organization** 📁
- All reports auto-saved to `generated_reports/`
- Documentation organized in `docs/` folder
- Clean project structure with `.gitignore`
- Template separated into `perf_html_template.py`

**Enhanced Configuration** ⚙️
- All constants centralized in `constants.py`
- CV-based adaptive thresholds
- Quality gate configuration display
- Comprehensive documentation for every setting

See [PREMIUM_UI_COMPLETE.md](docs/PREMIUM_UI_COMPLETE.md) and [QUALITY_GATES_GUIDE.md](docs/QUALITY_GATES_GUIDE.md) for details.

---

## Examples

### Example 1: Basic Comparison

```bash
python perf_html_report.py \
  --baseline "[100,102,98,101,99]" \
  --target   "[110,112,108,111,109]" \
  --out report.html
```

### Example 2: Custom Thresholds

```bash
python perf_html_report.py \
  --baseline "[50,52,48,51,49]" \
  --target   "[60,62,58,61,59]" \
  --ms-floor 20.0 \
  --pct-floor 0.10 \
  --out custom_report.html
```

### Example 3: Release Mode (Equivalence Testing)

```bash
python perf_html_report.py \
  --baseline "[800,805,798,810,799]" \
  --target   "[802,807,800,812,801]" \
  --mode release \
  --equivalence-margin-ms 30.0 \
  --out release_report.html
```

### Example 4: CI/CD Integration

```bash
# Run benchmarks
./run_benchmarks.sh > baseline.txt
./run_benchmarks.sh > target.txt

# Check for regression
python perf_html_report.py \
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

## Configuration Options

### Quick Reference

| Option | Description | Default |
|--------|-------------|---------|
| `--baseline` | Baseline measurements (required) | - |
| `--target` | Target measurements (required) | - |
| `--out` | Output HTML file (required) | - |
| `--mode` | `pr` or `release` | `pr` |
| `--ms-floor` | Absolute threshold (ms) | `50.0` |
| `--pct-floor` | Relative threshold (fraction) | `0.05` (5%) |
| `--tail-ms-floor` | Tail absolute threshold | `75.0` |
| `--tail-pct-floor` | Tail relative threshold | `0.05` (5%) |
| `--directionality` | Max fraction slower | `0.70` (70%) |
| `--no-wilcoxon` | Disable Wilcoxon test | False |
| `--equivalence-margin-ms` | Release mode margin | `30.0` |
| `--seed` | Random seed | `0` |

### Full Options

See `--help` for all options:
```bash
python perf_html_report.py --help
```

---

## Running Tests

```bash
# Install test dependencies
pip install pytest

# Run all tests
python -m pytest test_commit_to_commit_comparison.py -v

# Expected output:
# 24 passed in ~1.3s
```

---

## Documentation

All documentation is located in the [`docs/`](docs/) folder.

### Core Guides

| Document | Description |
|----------|-------------|
| [USER_GUIDE.md](docs/USER_GUIDE.md) | 📖 Complete usage guide with examples |
| [TEST_REPORT.md](docs/TEST_REPORT.md) | 🧪 Comprehensive test results |
| [MEASUREMENT_GUIDE.md](docs/MEASUREMENT_GUIDE.md) | 📏 Best practices for measurement |

### Feature Documentation

| Document | Description |
|----------|-------------|
| [PREMIUM_UI_COMPLETE.md](docs/PREMIUM_UI_COMPLETE.md) | 🎨 Premium UI design details |
| [DATA_QUALITY_FEATURE.md](docs/DATA_QUALITY_FEATURE.md) | 🔬 Data quality assessment |
| [QUALITY_GATES_GUIDE.md](docs/QUALITY_GATES_GUIDE.md) | 🚦 Quality gates explained |
| [MODES_EXPLAINED.md](docs/MODES_EXPLAINED.md) | ⚙️ PR vs Release mode |
| [THRESHOLD_COMPUTATION_EXPLAINED.md](docs/THRESHOLD_COMPUTATION_EXPLAINED.md) | 📊 Threshold calculation |
| [WILCOXON_EXPLAINED.md](docs/WILCOXON_EXPLAINED.md) | 📈 Wilcoxon test details |

### Technical Documentation

| Document | Description |
|----------|-------------|
| [TEMPLATE_SPLIT_COMPLETE.md](docs/TEMPLATE_SPLIT_COMPLETE.md) | 🔧 Template architecture |
| [ARCHITECTURE_TEMPLATE_OPTIONS.md](docs/ARCHITECTURE_TEMPLATE_OPTIONS.md) | 🏗️ Architecture options |
| [FIXES_APPLIED.md](docs/FIXES_APPLIED.md) | ✅ Recent improvements & fixes |

---

## Project Structure

```
.
├── commit_to_commit_comparison.py          # Core regression detection logic
├── perf_html_report.py      # CLI and HTML report generation
├── perf_html_template.py    # HTML/CSS/JS template (separated)
├── constants.py             # Configuration constants
├── test_commit_to_commit_comparison.py     # Test suite (24 tests)
├── README.md                # This file
├── .gitignore               # Git ignore patterns
├── docs/                    # Documentation folder
│   ├── USER_GUIDE.md        # Complete usage guide
│   ├── TEST_REPORT.md       # Test validation report
│   ├── MEASUREMENT_GUIDE.md # Best practices for measurements
│   ├── QUALITY_GATES_GUIDE.md # Quality gates explained
│   ├── PREMIUM_UI_COMPLETE.md # Premium UI documentation
│   └── ... (20 documentation files)
└── generated_reports/       # Generated HTML reports (gitignored)
    └── README.md            # Reports folder documentation
```

---

## How It Works

### 1. Data Collection
You provide two sets of paired measurements:
- **Baseline**: Performance before changes
- **Target**: Performance after changes

### 2. Statistical Analysis

The tool performs multiple checks:

```
┌─────────────────────────────────────────┐
│ Median Delta Check                      │
│ Is median(target - baseline) too large? │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ Tail Check (p90)                        │
│ Did worst-case performance degrade?     │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ Directionality Check                    │
│ Are ≥70% of runs slower?                │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ Wilcoxon Test (Optional)                │
│ Is the difference statistically real?   │
└─────────────────────────────────────────┘
           ↓
      PASS or FAIL
```

### 3. Report Generation

Creates an HTML report with:
- ✅/❌ Overall status
- 📊 Summary statistics
- 📈 Bootstrap confidence intervals
- 📋 Per-run breakdown
- 🎯 Clear failure reasons

### 4. Exit Code

Returns exit code for automation:
- **0**: PASS (no regression)
- **1**: FAIL (regression detected)
- **2**: ERROR (invalid input)

---

## Real-World Example

### Scenario: API Endpoint Performance

You have an API endpoint and want to ensure a code change doesn't slow it down.

#### Step 1: Collect Baseline
```bash
# Run 10 times on current code
for i in {1..10}; do
  curl -w "%{time_total}\n" -o /dev/null -s https://api.example.com/endpoint
done > baseline.txt
```

#### Step 2: Apply Changes
```bash
git checkout feature-branch
# Deploy to test environment
```

#### Step 3: Collect New Measurements
```bash
for i in {1..10}; do
  curl -w "%{time_total}\n" -o /dev/null -s https://api.example.com/endpoint
done > target.txt
```

#### Step 4: Check for Regression
```bash
python perf_html_report.py \
  --baseline "$(cat baseline.txt | tr '\n' ',')" \
  --target "$(cat target.txt | tr '\n' ',')" \
  --out api_perf_report.html \
  --title "API Endpoint - Feature Branch"
```

#### Step 5: Review Results
- Open `api_perf_report.html`
- Check exit code: `echo $?`
- If exit code = 1, investigate regression
- If exit code = 0, safe to merge

---

## Requirements

- **Python**: 3.8+
- **Dependencies**:
  - `numpy` - Numerical computations
  - `scipy` - Statistical tests
  - `pytest` - Testing (optional, for development)

---

## Contributing

This tool has been thoroughly tested and validated:
- ✅ 24/24 tests passing
- ✅ All critical bugs fixed
- ✅ Comprehensive documentation
- ✅ Production-ready

For questions or issues, refer to the documentation in this repository.

---

## License

MIT License - Feel free to use in your projects!

---

## Quick Tips

### 💡 Choosing the Right Mode

**PR Mode** (`--mode pr`): Strict regression gate
- Use for: PRs, feature branches, continuous testing
- Goal: Catch any performance degradation
- Fails if: Median, tail, or directionality exceeds thresholds

**Release Mode** (`--mode release`): Equivalence testing
- Use for: Release validation, stable builds
- Goal: Ensure performance hasn't significantly changed
- Fails if: Bootstrap CI for median delta is outside margin

### 💡 Sample Size Guidelines

| Samples | Reliability | Use Case |
|---------|-------------|----------|
| 3-5 | Low | Quick checks only |
| 10-20 | Good | Most use cases ✅ |
| 30+ | Excellent | Critical paths, noisy environments |

### 💡 Understanding Thresholds

The tool uses `max(absolute, relative)`:

**Example**: `--ms-floor 50.0 --pct-floor 0.05`
- For baseline median = 100ms → threshold = max(50ms, 5ms) = **50ms**
- For baseline median = 2000ms → threshold = max(50ms, 100ms) = **100ms**

This adapts to both fast and slow operations!

---

## Support

📖 **Full Documentation**: See [USER_GUIDE.md](docs/USER_GUIDE.md)
🧪 **Test Results**: See [TEST_REPORT.md](docs/TEST_REPORT.md)
📊 **All Documentation**: Browse the [docs/](docs/) folder

---

## 🎯 Why This Tool?

This isn't just another performance testing tool. It's a **complete solution** built with:

✅ **Statistical Rigor** - Wilcoxon tests, bootstrap CI, multi-check validation
✅ **Data Quality Focus** - Automatic detection of unreliable measurements
✅ **Professional UI** - World-class design that stakeholders trust
✅ **Production Ready** - 24/24 tests passing, comprehensive documentation
✅ **CI/CD Friendly** - Exit codes, auto-folder creation, reproducible results
✅ **Transparent** - Shows all thresholds, configurations, and quality metrics

**Perfect for:**
- Performance engineers validating optimizations
- QA teams setting up performance gates
- Engineering teams tracking performance trends
- Platform teams monitoring system health

---

**Built with statistical rigor. Tested thoroughly. Production ready.** 🚀

**Version 2.0** - Premium UI · Quality Gates · Intelligent Analysis
