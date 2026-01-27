# Performance Regression Detection Algorithms

**A comprehensive guide to understanding the statistical algorithms in `main_health.py`**

---

## Table of Contents

1. [Overview](#overview)
2. [Core Statistical Concepts](#core-statistical-concepts)
3. [Algorithm 1: Control Chart (Spike Detection)](#algorithm-1-control-chart-spike-detection)
4. [Algorithm 2: EWMA (Trend Detection)](#algorithm-2-ewma-trend-detection)
5. [Algorithm 3: Step-Fit (Changepoint Detection)](#algorithm-3-step-fit-changepoint-detection)
6. [Algorithm 4: Outlier Detection](#algorithm-4-outlier-detection)
7. [Dual-Threshold Detection](#dual-threshold-detection)
8. [How They Work Together](#how-they-work-together)
9. [Practical Examples](#practical-examples)
10. [Choosing the Right Settings](#choosing-the-right-settings)

---

## Overview

The performance monitoring system uses **three complementary detection algorithms** to catch different types of performance regressions:

| Algorithm | Detects | Best For | Example |
|-----------|---------|----------|---------|
| **Control Chart** | Sudden spikes | Single outlier values | One test runs at 2000ms when baseline is 100ms |
| **EWMA** | Gradual trends | Slow performance creep | Performance slowly increases from 100ms to 150ms over 50 runs |
| **Step-Fit** | Abrupt changes | Finding exact commit that broke performance | Performance jumps from 100ms to 200ms at commit #47 |

**Why three algorithms?**
- Different regression patterns require different detection methods
- Using all three ensures comprehensive coverage
- Minimizes both false positives and false negatives

---

## Core Statistical Concepts

Before diving into the algorithms, let's understand the key statistical concepts used.

### 1. Median vs. Mean

**Median**: The middle value when data is sorted
- **Robust** to outliers
- Better for noisy performance data

```
Data: [100, 102, 98, 101, 9999]
Mean:   2080  ← Skewed by outlier
Median:  101  ← Not affected ✓
```

### 2. MAD (Median Absolute Deviation)

**Definition**: Robust measure of variability (like standard deviation, but resistant to outliers)

**Formula**:
```
MAD = median(|x_i - median(x)|)
```

**Example**:
```python
Data: [100, 105, 95, 102, 98, 103]

Step 1: Calculate median
median = 101

Step 2: Calculate absolute deviations
|100 - 101| = 1
|105 - 101| = 4
|95 - 101| = 6
|102 - 101| = 1
|98 - 101| = 3
|103 - 101| = 2

Step 3: Take median of deviations
MAD = median([1, 4, 6, 1, 3, 2]) = 2.5
```

### 3. Robust Sigma

**Definition**: Convert MAD to a standard deviation-equivalent for normal distributions

**Formula**:
```
robust_sigma = 1.4826 × MAD
```

**Why 1.4826?** This scaling factor makes robust_sigma approximately equal to standard deviation when data is normally distributed.

**Example**:
```python
MAD = 2.5
robust_sigma = 1.4826 × 2.5 = 3.71

# Now we can use it like standard deviation:
# 3-sigma rule: ~99.7% of data within 3×sigma
```

### 4. Control Limits

**Definition**: Boundaries that define "normal" behavior

**Formula**:
```
Upper Control Limit (UCL) = median + k × robust_sigma
Lower Control Limit (LCL) = median - k × robust_sigma
```

**Typical values**:
- k = 3: 99.7% confidence (conservative, fewer false alarms)
- k = 2: 95% confidence (more sensitive)

---

## Algorithm 1: Control Chart (Spike Detection)

### What It Does

Detects **sudden spikes or drops** in performance by comparing the latest value against baseline bounds.

### How It Works

1. **Establish Baseline**: Use last N points (e.g., 50) to calculate median and MAD
2. **Calculate Bounds**:
   - Upper limit = baseline_median + 3×robust_sigma
   - Lower limit = baseline_median - 3×robust_sigma
3. **Check Latest Value**: Alert if latest value exceeds bounds

### Visual Example

```
Performance (ms)
300 |                                                    ⚠️ 280ms (ALERT!)
    |                                                   /
200 |                                                  /
    | ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ UCL (183ms) ─ ─ ─ ─ ─ /
    |                                                /
150 |                                               /
    |
100 | ━━━━━━━━━━━━━━━━━━ Median (100ms) ━━━━━━━━━━━━
    |
 50 |
    | ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ LCL (17ms) ─ ─ ─ ─ ─ ─
    |
  0 |________________________________________________
       0    10   20   30   40   50   51 (latest)
                    Baseline Window
```

### Code Example

```python
# Your data
series = [100, 102, 98, 105, 99, 101, 97, 103, ..., 280]  # Last value is spike

# Control Chart Analysis
result = control_chart_median_mad(
    series,
    window=50,      # Use last 50 points as baseline
    k=3.0,          # 3-sigma bounds
    abs_floor=10.0, # Minimum 10ms change required
    pct_floor=0.05  # Minimum 5% change required
)

# Result
result.alert = True
result.reason = "ALERT: value=280 > UCL=183"
result.value = 280
result.baseline_median = 100
result.upper_bound = 183
result.robust_z_score = 6.5  # Very high!
```

### When to Use

✅ **Good for:**
- Detecting sudden performance spikes
- Catching one-off failures
- Quick sanity checks

❌ **Not good for:**
- Gradual performance degradation
- Finding when regression started
- Noisy data (too many false positives)

---

## Algorithm 2: EWMA (Trend Detection)

### What It Does

Detects **gradual trends** by smoothing the data and checking if the smoothed trend drifts away from baseline.

### How It Works

**EWMA (Exponentially Weighted Moving Average)** gives more weight to recent values:

**Formula**:
```
EWMA_t = α × value_t + (1-α) × EWMA_(t-1)
```

Where:
- α (alpha) = smoothing parameter (0 < α < 1)
- α = 0.3 (default): Smooths over ~7 points
- α = 0.1: Smooths over ~20 points (more aggressive smoothing)

**Then check if EWMA exceeds bounds**:
```
Alert if: EWMA > baseline_median + k×robust_sigma
```

### Visual Example

```
Performance (ms)
200 |                                        ⚠️ EWMA drift alert!
    |                                       ╱
180 |                                     ╱
    | ─ ─ ─ ─ ─ ─ ─ ─ UCL (165ms) ─ ─ ─╱─ ─ ─ ─ ─
160 |                                 ╱
    |                               ╱  EWMA (smoothed)
140 |                             ╱
    |                           ╱
120 |                         ╱
    |          ╭─────────────╯
100 | ━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━ Baseline (100ms)
    |    Actual values (noisy)
 80 | ●  ●   ●  ●  ●   ● ● ●  ●  ●   ●
    |
  0 |________________________________________________
       0    10   20   30   40   50   60   70   80
       └─ Baseline ──┘   └─── Gradual drift ───┘
```

### Step-by-Step Calculation

```python
# Example data showing gradual drift
series = [100, 102, 98, 105, 99, 101, 110, 115, 120, 125, 130]
alpha = 0.3

# Initialize EWMA with first value
EWMA_0 = 100

# Calculate EWMA for each point
EWMA_1 = 0.3×102 + 0.7×100 = 100.6
EWMA_2 = 0.3×98  + 0.7×100.6 = 99.8
EWMA_3 = 0.3×105 + 0.7×99.8 = 101.4
EWMA_4 = 0.3×99  + 0.7×101.4 = 100.7
EWMA_5 = 0.3×101 + 0.7×100.7 = 100.8
EWMA_6 = 0.3×110 + 0.7×100.8 = 103.6  ← Starting to rise
EWMA_7 = 0.3×115 + 0.7×103.6 = 107.0
EWMA_8 = 0.3×120 + 0.7×107.0 = 110.9
EWMA_9 = 0.3×125 + 0.7×110.9 = 115.1
EWMA_10 = 0.3×130 + 0.7×115.1 = 119.6  ← Significantly above baseline

# Check against bounds
baseline_median = 100
robust_sigma = 5
UCL = 100 + 3×5 = 115

# Alert! EWMA_10 (119.6) > UCL (115)
```

### Dual-Threshold Detection

EWMA uses **two criteria** (either triggers alert):

#### 1. Statistical Threshold (Sigma-Based)
```
Alert if: EWMA > baseline_median + k×robust_sigma
```

#### 2. Percentage Drift Threshold (Practical)
```
drift_pct = |EWMA - baseline_median| / baseline_median × 100
Alert if: drift_pct >= 15%  (default)
```

**Example**:
```python
baseline_median = 1000ms
EWMA = 1160ms
robust_sigma = 200ms (high variability)

# Statistical check
UCL = 1000 + 3×200 = 1600ms
1160 < 1600  ✗ No alert (statistical)

# Percentage drift check
drift = |1160 - 1000| / 1000 × 100 = 16%
16% >= 15%  ✓ ALERT! (percentage)

# Result: ALERT (because percentage threshold met)
```

### When to Use

✅ **Good for:**
- Detecting gradual performance degradation
- Catching slow memory leaks
- Smoothing out noisy data

❌ **Not good for:**
- Sudden spikes (use Control Chart)
- Finding exact regression point (use Step-Fit)

---

## Algorithm 3: Step-Fit (Changepoint Detection)

### What It Does

Finds the **exact point** where performance changed (e.g., which commit caused the regression).

### How It Works

1. **Scan the series**: Try splitting the data at every possible point
2. **For each split**: Calculate median before and median after
3. **Score each split**: How significant is the difference?
4. **Return best split**: The point with the highest score that meets thresholds

### The Scoring Formula

```
score = |median_after - median_before| / robust_sigma

Where:
  robust_sigma = 1.4826 × MAD(entire_scan_window)
```

**Interpretation**:
- Score ≥ 4.0: Very significant change (default threshold)
- Score 2-4: Moderate change
- Score < 2: Weak change

### Visual Example

```
Performance (ms)
200 |                                    ████████████████
    |                                    ████████████████
    |                                    ████████████████
150 |                                    ████████████████
    |                                    ████ After ████
    |                                    ████ (180ms)████
100 | ████████████████████████████████   ████████████████
    | ████████████████████████████████
    | ███████ Before (100ms) ██████████
 50 | ████████████████████████████████
    |
  0 |________________________________________________
       0              50           100  ↑  150         200
                                        |
                                   Changepoint!
                                   (index 100)
```

### Step-by-Step Example

```python
# Example: Performance doubled at index 50
series = [100]*50 + [200]*50  # 100 points total

# Algorithm tries every split:

# Split at index 10:
before = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100]  # 10 points
after = [100, 100, ..., 200, 200, ..., 200]  # 90 points
before_median = 100
after_median = 188  # Mix of 100s and 200s
delta = 88
score = 88 / robust_sigma = 88/3 = 29.3

# Split at index 50:
before = [100, 100, ..., 100]  # 50 points
after = [200, 200, ..., 200]   # 50 points
before_median = 100
after_median = 200
delta = 100
score = 100 / robust_sigma = 100/3 = 33.3  ← HIGHEST SCORE!

# Split at index 80:
before = [100, 100, ..., 200, 200, ...]  # 80 points (mix)
after = [200, 200, ..., 200]             # 20 points
before_median = 150
after_median = 200
delta = 50
score = 50 / robust_sigma = 50/3 = 16.7

# Result: Best changepoint is at index 50
```

### Dual-Threshold Detection

Step-Fit uses **two criteria** (either triggers alert):

#### 1. Statistical Threshold (Score-Based)
```
Alert if: score >= 4.0  (default)
```

#### 2. Percentage Change Threshold
```
pct_change = |after_median - before_median| / before_median × 100
Alert if: pct_change >= 20%  (default)
```

**Example (High Variability Data)**:
```python
# homeTab data at index 156
before_median = 930ms
after_median = 1680ms
robust_sigma = 280ms  (high variability!)

# Statistical check
delta = 1680 - 930 = 750ms
score = 750 / 280 = 2.68
2.68 < 4.0  ✗ No alert (statistical)

# Percentage check
pct_change = 750 / 930 × 100 = 80.6%
80.6% >= 20%  ✓ ALERT! (percentage)

# Result: ALERT at index 156 (found the exact commit!)
```

### Dynamic Scan Window

**Default**: `scan_back = None` (scans entire series)

```python
# Your 376-point series
series = [data from 376 test runs]

# With scan_back=None (default):
# Scans from index 0 to 375
# Finds regression at index 156 ✓

# With scan_back=120 (old behavior):
# Scans from index 256 to 375 (last 120 points only)
# Misses regression at index 156 ✗
```

**When to limit scan window**:
```python
# For very large datasets (>1000 points), you can limit:
--step-scan-back 500  # Scan last 500 points only (faster)
```

### When to Use

✅ **Good for:**
- Finding which commit broke performance
- Pinpointing exact regression location
- Historical analysis

❌ **Not good for:**
- Real-time monitoring (use Control Chart)
- Very noisy data with many false steps

---

## Algorithm 4: Outlier Detection

### What It Does

Identifies **individual outlier values** using a time-series aware rolling window approach.

### How It Works

**Rolling Window Approach**:
1. For each point i, look at the last N points before it (baseline)
2. Calculate baseline median and MAD
3. Compute robust z-score for point i
4. If z-score > threshold (default: 3.5), mark as outlier

**Formula**:
```
z_score = |value_i - baseline_median| / robust_sigma

Outlier if: z_score > 3.5
```

### Why Rolling Window?

**Traditional IQR Method** (static):
```python
# Uses entire dataset
Q1 = 25th percentile of ALL data
Q3 = 75th percentile of ALL data
IQR = Q3 - Q1
Outlier if: value < Q1 - 1.5×IQR or value > Q3 + 1.5×IQR

❌ Problem: Doesn't adapt to changing baselines
```

**Rolling MAD Method** (time-series aware):
```python
# Adapts to recent history
for each point i:
    baseline = last 50 points before i
    baseline_median = median(baseline)
    baseline_MAD = MAD(baseline)
    z_score = |value_i - baseline_median| / robust_sigma
    if z_score > 3.5:
        mark as outlier

✓ Advantage: Adapts to changing performance levels
```

### Visual Example

```
Performance (ms)
3000 |                    ⚠️ Outlier!
     |                    ●
2000 |
     |
1000 | ●  ●   ●  ● ●  ●  ●  ●  ● ● ●   ●  ●
     |           Normal values
  0  |________________________________________________
        0    10   20   30   40   50   60   70   80

Analysis at index 25 (3000ms):
  baseline = values[0:25] = [100, 102, 98, ..., 105]
  baseline_median = 100
  baseline_MAD = 3
  robust_sigma = 1.4826 × 3 = 4.45
  z_score = |3000 - 100| / 4.45 = 651.7
  651.7 > 3.5  ✓ OUTLIER!
```

### Adaptive to Changing Baselines

```
Performance (ms)
200 |                                    ●  ●   ●  ●
    |                                    Normal (new baseline)
150 |                              ╱
    |                            ╱
100 | ●  ●   ●  ● ●  ●  ●  ●  ●╱
    | Normal (old baseline)
 50 |
    |
  0 |________________________________________________
       0    10   20   30   40   50   60   70   80
       └─ Phase 1 ─┘  └─ Transition ─┘ └─ Phase 2 ─┘

# At index 70:
baseline = values[20:70] = [transitioning from 100 to 200]
baseline_median = 150  ← Adapted!
value_70 = 195
z_score = |195 - 150| / robust_sigma = 45/10 = 4.5
4.5 > 3.5  ✗ Not an outlier (within new baseline)

# Static IQR would incorrectly flag values in Phase 2 as outliers!
```

### Impact on Analysis

**Trimmed Mean Calculation**:
```python
series = [100, 102, 98, 3000, 105, 99, 101, 97]
outliers = [index 3]  # 3000ms is outlier

# Without outlier removal:
mean = (100+102+98+3000+105+99+101+97) / 8 = 462.75ms  ← Skewed!

# With outlier removal (trimmed mean):
trimmed_mean = (100+102+98+105+99+101+97) / 7 = 100.29ms  ← Accurate!
```

**Quality Score Penalty**:
```python
outlier_pct = num_outliers / total_points × 100

if outlier_pct > 20%:
    quality_score -= 20  # Severe penalty
elif outlier_pct > 0:
    quality_score -= 5   # Minor penalty
```

### Configuration

```python
# constants.py
HEALTH_OUTLIER_DETECTION_ENABLED = True  # Enable/disable
HEALTH_OUTLIER_K = 3.5  # Z-score threshold (higher = less sensitive)
HEALTH_WINDOW = 50      # Rolling window size
```

### When to Use

✅ **Enable when:**
- Test environment has occasional noise
- Want accurate trimmed mean
- Quality assessment is important

❌ **Disable when:**
- Data is very clean (no outliers expected)
- Want faster analysis
- Working with small datasets (<50 points)

---

## Dual-Threshold Detection

### The Problem

**High-variability data** makes statistical thresholds too conservative:

```
Example: homeTab data
  Median = 1000ms
  MAD = 200ms (20% coefficient of variation)
  robust_sigma = 296ms

  Statistical threshold (3-sigma):
  UCL = 1000 + 3×296 = 1888ms

  A jump from 1000ms to 1500ms (+50%!) doesn't trigger alert:
  1500 < 1888  ✗ No alert

  But 50% slower IS a regression! ✓
```

### The Solution

Use **two independent criteria** - alert if **EITHER** is met:

```
ALERT = (statistical_threshold OR percentage_threshold)
```

### Applied to Step-Fit

```python
# Statistical criterion
score = |after_median - before_median| / robust_sigma
statistical_alert = (score >= 4.0)

# Percentage criterion
pct_change = |after_median - before_median| / before_median × 100
percentage_alert = (pct_change >= 20.0%)

# Dual threshold
trigger_alert = statistical_alert OR percentage_alert
```

**Example**:
```python
before = 1000ms
after = 1300ms
robust_sigma = 250ms (high variability)

# Statistical check
score = 300 / 250 = 1.2
1.2 < 4.0  ✗ Fail

# Percentage check
pct = 300 / 1000 × 100 = 30%
30% >= 20%  ✓ Pass

# Result: ALERT (percentage threshold met)
```

### Applied to EWMA

```python
# Statistical criterion
statistical_alert = (EWMA > baseline_median + k×robust_sigma)

# Percentage drift criterion
drift_pct = |EWMA - baseline_median| / baseline_median × 100
drift_alert = (drift_pct >= 15.0%)

# Dual threshold
trigger_alert = statistical_alert OR drift_alert
```

**Example**:
```python
baseline_median = 1000ms
EWMA = 1160ms
robust_sigma = 200ms

# Statistical check
UCL = 1000 + 3×200 = 1600ms
1160 < 1600  ✗ Fail

# Drift check
drift = (160 / 1000) × 100 = 16%
16% >= 15%  ✓ Pass

# Result: ALERT (drift threshold met)
```

### Configuration

```python
# constants.py

# Step-Fit percentage threshold
HEALTH_STEP_PCT_THRESHOLD = 20.0  # 20% change triggers alert
# Set to None to disable percentage-based detection

# EWMA drift percentage threshold
HEALTH_EWMA_PCT_THRESHOLD = 15.0  # 15% drift triggers alert
# Set to None to disable drift-based detection
```

### CLI Override

```bash
# More sensitive (detect smaller changes)
python3 main_health.py --series "[...]" \
  --step-pct-threshold 10.0 \
  --ewma-pct-threshold 10.0

# Less sensitive (only major regressions)
python3 main_health.py --series "[...]" \
  --step-pct-threshold 50.0 \
  --ewma-pct-threshold 30.0

# Disable percentage detection (statistical only)
python3 main_health.py --series "[...]" \
  --step-pct-threshold 999999 \
  --ewma-pct-threshold 999999
```

### When to Use

✅ **Use dual-threshold when:**
- Data has high variability (CV > 20%)
- Want to catch practically significant changes
- Performance SLAs are percentage-based

❌ **Use statistical-only when:**
- Data is very clean (low noise)
- Want maximum rigor (fewer false positives)
- Working with research/academic analysis

---

## How They Work Together

The three algorithms complement each other:

```
┌─────────────────────────────────────────────────────────┐
│                    Your Time Series                     │
│   [1000, 1020, 980, 1010, ..., 3000, ..., 1800, ...]   │
└─────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌───────────────┐              ┌────────────────┐
│ Control Chart │              │  Step-Fit      │
│ (Spike Check) │              │ (Changepoint)  │
└───────────────┘              └────────────────┘
        │                               │
        ▼                               ▼
  ✓ Spike at                     ✓ Regression at
    index 50                        index 100
    (3000ms)                        (jumped to 1800ms)
        │                               │
        │       ┌────────────┐          │
        └──────>│    EWMA    │<─────────┘
                │ (Trend)    │
                └────────────┘
                      │
                      ▼
               ✓ Gradual drift
                 detected after
                 index 100
```

### Decision Flow

```
1. Run all three algorithms in parallel

2. Check results:
   ┌─> Control Chart alert?  ──> Yes ──> SPIKE DETECTED
   │
   ├─> EWMA alert?           ──> Yes ──> TREND DETECTED
   │
   └─> Step-Fit found change? ──> Yes ──> REGRESSION at index X

3. Overall status:
   ALERT = (Control OR EWMA OR Step-Fit)

4. For the report:
   - Show which algorithm(s) triggered
   - Show the regression index (from Step-Fit)
   - Display all detection details
```

### Example Scenario

**Your homeTab Data**:
```python
Series: 376 points
Pattern: Baseline ~1000ms, jump to ~1680ms at index 156

# Control Chart (last value check)
Latest value: 1807ms
UCL: ~2500ms (high variability)
Result: ✗ No alert (within bounds)

# EWMA (trend check)
EWMA value: 1617ms
Baseline: 1000ms
Drift: 61.7% > 15%
Result: ✓ ALERT! (drift threshold)

# Step-Fit (changepoint)
Best split: index 156
Before: 1013ms, After: 1569ms
Change: +54.8% > 20%
Result: ✓ ALERT! (percentage threshold)

# Overall
Status: 🚨 ALERT
Reason: EWMA drift + Step-Fit changepoint
Regression started at: index 156 ← YOUR EXACT COMMIT!
```

---

## Practical Examples

### Example 1: Sudden Spike

**Scenario**: One test run is extremely slow

```
Data: [100, 102, 98, 101, 99, 2500, 103, 97, 101]
                              ↑
                           Spike!
```

**Results**:
```
Control Chart: ✓ ALERT
  - value=2500 >> UCL=115
  - Robust z-score: 64.3

EWMA: ✗ OK
  - Spike doesn't affect smoothed trend much
  - EWMA rises to ~150, still within bounds

Step-Fit: ✗ No changepoint found
  - Single spike doesn't create sustained change
  - Before median = 100, After median = 100
  - Not a true regression

Overall Status: ⚠️ ALERT (spike detected)
Recommendation: Investigate index 5, likely transient issue
```

---

### Example 2: Gradual Performance Degradation

**Scenario**: Memory leak causing slow creep

```
Data: [100, 102, 105, 108, 112, 117, 123, 130, 138, 147]
       └─────────────── Gradual increase ──────────────┘
```

**Results**:
```
Control Chart: ✗ OK
  - Latest value 147 is only slightly above baseline 100
  - Within 3-sigma bounds (~145)

EWMA: ✓ ALERT
  - EWMA smoothly tracks the increase: 100 → 110 → 125 → 140
  - Drift: 40% >> 15% threshold
  - Reason: "EWMA drifted 40% from baseline"

Step-Fit: ✗ No clear changepoint
  - Change is gradual, not abrupt
  - No single point where median jumps

Overall Status: ⚠️ ALERT (trend detected)
Recommendation: Memory leak or resource exhaustion likely
```

---

### Example 3: Exact Commit Regression

**Scenario**: Code change broke performance at specific commit

```
Data: [100, 98, 102, 99, 101, ...(45 more)..., 101, 199, 201, 198, 202, ...(45 more)..., 200]
       └────────── Before (100ms) ──────────┘           └────────── After (200ms) ──────────┘
                                            ↑
                                       Commit #50
```

**Results**:
```
Control Chart: ✓ ALERT (on first occurrence)
  - value=199 >> UCL=115

EWMA: ✓ ALERT
  - EWMA rises from 100 to ~180
  - Drift: 80% >> 15%

Step-Fit: ✓ CHANGEPOINT at index 50
  - Before median: 100ms
  - After median: 200ms
  - Change: +100% >> 20%
  - Score: 33.3 >> 4.0

Overall Status: 🚨 ALERT (regression at index 50)
Recommendation: Review commit #50 for performance issues
```

---

### Example 4: High Variability Data (homeTab)

**Scenario**: Real homeTab data with 30% variability

```
Data: 376 points
  - Baseline (0-155): median=1013ms, high variance
  - After (156-375): median=1569ms, high variance
  - CV (coefficient of variation): 30.3%
```

**Results WITHOUT Dual-Threshold**:
```
Step-Fit (statistical only):
  - Score = 555 / 281 = 1.97
  - 1.97 < 4.0  ✗ No alert
  - STATUS: FALSE NEGATIVE ❌

Problem: High variance inflates robust_sigma, making detection too conservative
```

**Results WITH Dual-Threshold**:
```
Step-Fit (dual):
  - Statistical: score=1.97 < 4.0  ✗
  - Percentage: 54.8% > 20%  ✓
  - STATUS: ALERT ✓

EWMA (dual):
  - Statistical: within bounds  ✗
  - Drift: 16% > 15%  ✓
  - STATUS: ALERT ✓

Overall Status: 🚨 ALERT at index 156
Recommendation: This is a REAL regression caught by percentage thresholds
```

---

## Choosing the Right Settings

### Quick Reference Table

| Parameter | Default | Conservative | Aggressive | Use Case |
|-----------|---------|--------------|------------|----------|
| `HEALTH_WINDOW` | 50 | 100 | 30 | Baseline window size |
| `HEALTH_CONTROL_K` | 3.0 | 4.0 | 2.0 | Control chart sensitivity |
| `HEALTH_EWMA_ALPHA` | 0.3 | 0.1 | 0.5 | EWMA smoothing |
| `HEALTH_EWMA_K` | 3.0 | 4.0 | 2.0 | EWMA bounds |
| `HEALTH_STEP_SCORE_K` | 4.0 | 6.0 | 2.0 | Step-Fit score threshold |
| `HEALTH_STEP_PCT_THRESHOLD` | 20% | 50% | 10% | Step-Fit percentage |
| `HEALTH_EWMA_PCT_THRESHOLD` | 15% | 30% | 10% | EWMA drift percentage |
| `HEALTH_OUTLIER_K` | 3.5 | 5.0 | 3.0 | Outlier z-score |

### Tuning Guidelines

#### 1. For Clean, Stable Data
```python
# constants.py
HEALTH_CONTROL_K = 2.0        # More sensitive
HEALTH_EWMA_K = 2.0           # More sensitive
HEALTH_STEP_SCORE_K = 3.0     # Lower threshold
HEALTH_STEP_PCT_THRESHOLD = None  # Disable (rely on statistical)
HEALTH_EWMA_PCT_THRESHOLD = None  # Disable (rely on statistical)
```

#### 2. For Noisy, Variable Data
```python
# constants.py
HEALTH_CONTROL_K = 4.0        # Less sensitive (avoid false alarms)
HEALTH_STEP_SCORE_K = 6.0     # Higher threshold
HEALTH_STEP_PCT_THRESHOLD = 20.0  # Enable percentage detection
HEALTH_EWMA_PCT_THRESHOLD = 15.0  # Enable drift detection
HEALTH_OUTLIER_DETECTION_ENABLED = True  # Clean the data
```

#### 3. For Finding Exact Commits
```python
# CLI
python3 main_health.py \
  --series "[...]" \
  --step-scan-back None \      # Scan entire series
  --step-pct-threshold 15.0    # Catch smaller regressions
```

#### 4. For Continuous Monitoring (CI/CD)
```python
# CLI
python3 main_health.py \
  --series "[...]" \
  --step-scan-back 120 \       # Recent changes only (faster)
  --step-pct-threshold 25.0    # Only major regressions
```

### Performance SLA Examples

#### SLA: "No more than 20% slower than baseline"
```python
HEALTH_STEP_PCT_THRESHOLD = 20.0
HEALTH_EWMA_PCT_THRESHOLD = 15.0  # Slightly lower for early warning
```

#### SLA: "P99 must stay under 2000ms" (absolute threshold)
```python
# Use abs_floor parameter
python3 main_health.py \
  --series "[...]" \
  --abs-floor 2000  # Alert if any detection exceeds baseline + 2000ms
```

---

## Summary

### Key Takeaways

1. **Three Algorithms, Three Purposes**:
   - Control Chart → Spikes
   - EWMA → Trends
   - Step-Fit → Exact commit

2. **Dual-Threshold is Essential** for high-variability data:
   - Statistical threshold: Rigor
   - Percentage threshold: Practicality

3. **Scan Entire Series** for exact commit detection:
   - `scan_back=None` (default)
   - Catches regressions anywhere in history

4. **Outlier Detection** improves accuracy:
   - Trimmed mean more accurate
   - Quality assessment more meaningful

5. **Tune for Your Environment**:
   - Clean data → Aggressive settings
   - Noisy data → Conservative + Percentage thresholds

### Decision Tree

```
Start: Do I have a performance regression?
│
├─> Need to find WHICH COMMIT caused it?
│   └─> Use Step-Fit with scan_back=None
│       └─> Returns exact index (commit number)
│
├─> Want to catch it in REAL-TIME (CI/CD)?
│   └─> Use Control Chart + EWMA
│       └─> Fast, catches both spikes and trends
│
└─> Data is NOISY (high variability)?
    └─> Enable dual-threshold detection
        └─> Percentage thresholds catch practical regressions
```

### Further Reading

- **Files**:
  - `main_health.py` - Algorithm implementations
  - `constants.py` - All tunable parameters
  - `test_main_health.py` - Test examples
  - `MODES_EXPLAINED.md` - Usage modes

- **Papers** (for deeper understanding):
  - Robust Statistics: Huber, P. J. (1981). *Robust Statistics*
  - EWMA Control Charts: Roberts, S. W. (1959). *Control Chart Tests*
  - Changepoint Detection: Killick, R. et al. (2012). *Optimal Detection*

---

**Document Version**: 1.0
**Last Updated**: 2026-01-25
**Author**: Performance Monitoring System
