# Performance Regression Detection Algorithms: Complete Guide

## Table of Contents
1. [Overview: Why Multiple Algorithms?](#overview)
2. [Control Chart (Spike Detection)](#control-chart)
3. [EWMA (Trend Detection)](#ewma)
4. [Step-Fit (Changepoint Detection)](#step-fit)
5. [Comparison & When to Use Each](#comparison)
6. [Real-World Examples](#real-world-examples)

---

## Overview: Why Multiple Algorithms?

Performance regressions happen in different ways:

1. **Sudden Spikes**: Latest build suddenly 2x slower
2. **Gradual Drift**: Performance slowly degrades over weeks
3. **Step Changes**: Single commit causes permanent degradation

**No single algorithm detects all types.** That's why we use three complementary methods:

| Algorithm | Detects | Time Horizon | Best For |
|-----------|---------|--------------|----------|
| Control Chart | Sudden spikes | Recent (last 30 points) | "Is NOW unusual?" |
| EWMA | Gradual drift | Full series with recency bias | "Is there a trend?" |
| Step-Fit | Permanent shifts | Full series history | "Where did it break?" |

---

## Control Chart (Spike Detection)

### What It Does

Detects if the **latest value** is unusually high/low compared to **recent performance**.

**Question it answers**: *"Is the most recent measurement a spike?"*

### How It Works

**Step 1: Define Baseline**
- Take the last 30 measurements (excluding the latest)
- This is your "normal" reference

**Step 2: Compute Robust Statistics**
```
Baseline median = median of last 30 points
MAD = Median Absolute Deviation (robust measure of spread)
Robust sigma = 1.4826 × MAD  (converts MAD to standard deviation equivalent)
```

**Step 3: Set Control Limits**
```
Upper bound = baseline_median + k × robust_sigma
Lower bound = baseline_median - k × robust_sigma

(k = 4.0 by default, allowing ±4 standard deviations)
```

**Step 4: Check Current Value**
```
z-score = (current_value - baseline_median) / robust_sigma

If z-score > k AND exceeds practical threshold:
    ALERT: Spike detected!
Else:
    OK: Normal variation
```

**Step 5: Practical Threshold** (prevents false alarms on small absolute changes)
```
practical_threshold = max(50ms, 5% of baseline_median)

Example:
- If baseline = 1000ms, practical = max(50, 50) = 50ms
- If baseline = 100ms, practical = max(50, 5) = 50ms
```

### Mathematical Example

**Data**: Last 31 measurements (indices 0-30)
```
Baseline (0-29): [100, 102, 98, 101, 99, 103, 97, 100, 102, 98, 
                  100, 101, 99, 100, 102, 98, 101, 100, 99, 103,
                  98, 100, 102, 101, 99, 100, 98, 102, 101, 100]
Current (30):    [250]  ← Is this a spike?
```

**Step 1: Baseline Median**
```
median([100, 102, 98, ..., 101, 100]) = 100ms
```

**Step 2: MAD (Median Absolute Deviation)**
```
Deviations from median:
[0, 2, -2, 1, -1, 3, -3, 0, 2, -2, ...]

Absolute deviations:
[0, 2, 2, 1, 1, 3, 3, 0, 2, 2, ...]

MAD = median([0, 2, 2, 1, 1, 3, ...]) = 2.0
```

**Step 3: Robust Sigma**
```
sigma = 1.4826 × 2.0 = 2.97
```

**Step 4: Control Limits** (k=4.0)
```
Upper bound = 100 + (4.0 × 2.97) = 111.88ms
Lower bound = 100 - (4.0 × 2.97) = 88.12ms
```

**Step 5: Check Current Value**
```
# Step A: Calculate delta (difference from baseline)
Delta = current_value - baseline_median
Delta = 250 - 100 = 150ms

# Step B: Check practical threshold (prevents false alarms on small absolute changes)
practical_threshold = max(50ms, 5% of baseline_median)
practical_threshold = max(50, 0.05 × 100) = 50ms
Exceeds practical? Delta (150ms) > practical_threshold (50ms) ✓

# Step C: Calculate statistical z-score (measures how unusual the spike is)
z-score = Delta / robust_sigma
z-score = 150 / 2.97 = 50.5

# Step D: Dual-condition check
Statistical check: z-score (50.5) > k (4.0) ✓
Practical check:   Delta (150ms) > practical_threshold (50ms) ✓

Result: BOTH conditions met → ALERT: Spike detected! 🚨

Note: Both conditions must be satisfied to trigger an alert:
  1. Statistical: z-score > 4.0σ (large enough deviation from normal variation)
  2. Practical: delta > 50ms AND > 5% (meaningful absolute and relative change)
```

### Visual Representation

```
Value (ms)
300 |
    |
250 |                                              ⚠️  ← Spike!
    |
200 |
    |
150 |
    |
112 |...................................................← Upper bound (4σ)
100 |●●●●●●●●●●●●●●●●●●●●●●●●●●●●●● ← Baseline median
 88 |...................................................← Lower bound (4σ)
    |
    |
  0 |________________________________________________
     0  2  4  6  8 10 12 14 16 18 20 22 24 26 28 30
     ←──────── Baseline (30 points) ──────────→  Current
```

### Why We Use MAD Instead of Standard Deviation

**Standard Deviation** is sensitive to outliers:
```
Data: [100, 100, 100, 100, 100, 100, 100, 100, 100, 10000]
Mean = 1090, Std Dev = 2970 (skewed by one outlier!)
```

**MAD (Median Absolute Deviation)** is robust:
```
Same data: [100, 100, 100, 100, 100, 100, 100, 100, 100, 10000]
Median = 100, MAD = 0 (outlier doesn't affect it)
```

### Strengths

✅ **Fast**: Only looks at last 30 points  
✅ **Robust**: MAD-based statistics ignore outliers  
✅ **Real-time**: Detects problems immediately  
✅ **Simple**: Easy to understand and interpret  

### Limitations

❌ **Recency bias**: Only knows about last 30 measurements  
❌ **Misses old regressions**: If regression happened >30 points ago, baseline adapts  
❌ **Contamination**: Recent regressions (within 30 points) contaminate baseline  
❌ **No root cause**: Doesn't tell you WHERE the problem started  

### When to Use

- **Continuous monitoring**: Check each new build for spikes
- **After the fact**: When regression is already >30 points old
- **Noise filtering**: When data has many measurement outliers

---

## EWMA (Trend Detection)

### What It Does

Detects **gradual performance drift** over time using exponentially weighted moving average.

**Question it answers**: *"Is there a trend toward degradation?"*

### How It Works

**Step 1: Initialize**
```
baseline = last 30 points (excluding current)
baseline_median = median(baseline)
baseline_MAD = MAD(baseline)
sigma = 1.4826 × baseline_MAD
```

**Step 2: Detect Outliers in Full Series**
```
For each point i in full series:
    rolling_baseline = window of 30 points before i
    If point i is outlier relative to rolling_baseline:
        Mark as outlier (exclude from EWMA)
```

**Step 3: Compute EWMA Over Full Series**
```
EWMA[0] = baseline_median  (initialize)

For i = 1 to N:
    If point[i] is NOT an outlier:
        EWMA[i] = α × point[i] + (1 - α) × EWMA[i-1]
    Else:
        EWMA[i] = EWMA[i-1]  (skip outliers)

(α = 0.25 by default, giving 75% weight to history)
```

**Step 4: Set Bounds** (based on baseline, NOT EWMA variance)
```
Upper bound = baseline_median + 3.0 × sigma
Lower bound = baseline_median - 3.0 × sigma
```

**Step 5: Dual-Threshold Detection**
```
Statistical alarm:
    EWMA outside bounds [lower, upper]
    
Practical drift alarm:
    abs(EWMA - baseline_median) / baseline_median ≥ 15%

Alert if EITHER condition is true
```

### Mathematical Example

**Data**: 100 points showing gradual degradation
```
Points 0-49:   100ms each (stable)
Points 50-99:  100 + (i-49)×2 = 100, 102, 104, ..., 198ms (gradual increase)
```

**Step 1: Initialize** (baseline = last 30 points before current)
```
baseline = points[69:99] = [140, 142, 144, ..., 196]
baseline_median = 168ms
MAD = 15
sigma = 1.4826 × 15 = 22.2ms
```

**Step 2: Compute EWMA** (α=0.25, skipping outliers)
```
EWMA[0] = 168  (initialize with baseline median)

EWMA[1] = 0.25 × 100 + 0.75 × 168 = 25 + 126 = 151
EWMA[2] = 0.25 × 100 + 0.75 × 151 = 25 + 113.25 = 138.25
EWMA[3] = 0.25 × 100 + 0.75 × 138.25 = 25 + 103.69 = 128.69
...
EWMA[50] = 0.25 × 100 + 0.75 × EWMA[49] = ~100 (converged)
EWMA[51] = 0.25 × 102 + 0.75 × 100 = 25.5 + 75 = 100.5
EWMA[52] = 0.25 × 104 + 0.75 × 100.5 = 26 + 75.375 = 101.375
...
EWMA[99] = ~185ms (tracking the upward trend)
```

**Step 3: Check Bounds**
```
Upper bound = 168 + (3.0 × 22.2) = 234.6ms
Lower bound = 168 - (3.0 × 22.2) = 101.4ms

EWMA[99] = 185ms → Within bounds [101.4, 234.6] ✓
```

**Step 4: Check Drift**
```
Drift = abs(185 - 168) / 168 × 100% = 10.1%

10.1% < 15% threshold → No drift alarm
```

**Result**: OK (in this example, drift hasn't exceeded 15% yet)

### Visual Representation

```
Value (ms)
200 |                                       ●●●●●●●●● ← Raw data
    |                                    ●●●
    |                                 ●●●
180 |                              ●●●
    |                           ●●●
    |                        ●●●     ═════════ ← EWMA (smoothed)
160 |                     ●●●     ═══
    |                  ●●●     ═══
    |               ●●●     ═══
140 |            ●●●     ═══
    |         ●●●     ═══
    |      ●●●     ═══
120 |   ●●●     ═══
    |●●●     ═══
100 |●●●══════  ← Stable phase
    |
  0 |_________________________________________________
     0      20      40      60      80      100

     ←── Stable ──→←───── Gradual Degradation ─────→
```

**Key Insight**: EWMA smooths out noise and tracks the underlying trend!

### Exponential Weighting Explained

**Alpha (α) = 0.25** means:
- **25% weight** to current value
- **75% weight** to historical EWMA

**Effective window**:
```
Effective N = 2/α - 1 = 2/0.25 - 1 = 7 points

This means EWMA gives significant weight to ~last 7 values
```

**Why exponential?** Older data has exponentially decreasing influence:
```
Current value:     25% weight
1 point ago:       75% × 25% = 18.75% weight
2 points ago:      75% × 18.75% = 14.06% weight
3 points ago:      75% × 14.06% = 10.55% weight
...
10 points ago:     ~5.6% weight
20 points ago:     ~0.3% weight
```

### Strengths

✅ **Trend detection**: Catches gradual drift that Control Chart misses  
✅ **Noise smoothing**: Exponential weighting filters out random spikes  
✅ **Full series**: Now computes over entire history (after recent improvement!)  
✅ **Outlier robust**: Filters outliers before computing EWMA  
✅ **Dual thresholds**: Both statistical (3σ) and practical (15% drift)  

### Limitations

❌ **Lagging**: EWMA lags behind sudden changes (by design)  
❌ **No pinpoint**: Doesn't tell you exact commit where regression started  
❌ **Parameter sensitive**: Alpha choice affects responsiveness  
❌ **Complex interpretation**: Less intuitive than Control Chart  

### When to Use

- **Gradual degradation**: Performance slowly getting worse over weeks/months
- **Creeping regressions**: Multiple small changes accumulating
- **Long-term monitoring**: Tracking performance trends over time
- **After Control Chart is OK**: Validates that there's no hidden drift

---

## Step-Fit (Changepoint Detection)

### What It Does

Finds the **exact commit** where performance permanently changed by testing every possible split point.

**Question it answers**: *"Where did the performance level shift?"*

### How It Works

**Step 1: Scan Window**
```
If scan_back = None:
    Scan entire series (0 to N)
Else:
    Scan last scan_back points only
```

**Step 2: Compute Global Statistics**
```
sigma = robust_sigma_from_mad(MAD(entire_scan_window))
This is used to normalize all change scores
```

**Step 3: Test Every Possible Split Point**
```
For each candidate split t (must leave min_segment points on each side):
    
    before = data[0:t]
    after = data[t:N]
    
    median_before = median(before)
    median_after = median(after)
    
    delta = median_after - median_before
    
    # Check if change exceeds practical threshold
    practical = max(50ms, 5% of median_before)
    if abs(delta) <= practical:
        continue  # Too small to matter
    
    # Compute score (normalized by global sigma)
    score = abs(delta) / sigma
    
    # Track best split
    if score > best_score:
        best_score = score
        best_t = t
```

**Step 4: Dual-Threshold Detection**
```
Statistical alarm: best_score ≥ 4.0σ
Practical alarm: percentage_change ≥ 20%

Alert if EITHER condition is true
```

### Mathematical Example

**Data**: 100 points with step change at index 50
```
Points 0-49:   100ms each (before)
Points 50-99:  160ms each (after)
```

**Step 1: Global Statistics**
```
All data = [100, 100, ..., 100, 160, 160, ..., 160]
Median = 130ms (midpoint)
MAD = median(abs([100-130, 100-130, ..., 160-130, ...]))
    = median([30, 30, ..., 30, ..., 30, 30])
    = 30ms
sigma = 1.4826 × 30 = 44.5ms
```

**Step 2: Test Split at t=50**
```
before = [100, 100, ..., 100]  (50 points)
after = [160, 160, ..., 160]   (50 points)

median_before = 100ms
median_after = 160ms
delta = 160 - 100 = 60ms

practical = max(50, 0.05 × 100) = 50ms
abs(delta) = 60 > 50 ✓ (exceeds practical threshold)

score = 60 / 44.5 = 1.35
percentage_change = 60 / 100 × 100% = 60%
```

**Step 3: Test Other Splits** (examples)
```
Split at t=25:
    before median = 100, after median = 130
    delta = 30, score = 30/44.5 = 0.67
    
Split at t=75:
    before median = 130, after median = 160
    delta = 30, score = 30/44.5 = 0.67
```

**Step 4: Choose Best Split**
```
best_t = 50 (highest score)
best_score = 1.35
percentage_change = 60%

Statistical alarm: 1.35 < 4.0 → NO
Practical alarm: 60% ≥ 20% → YES

Result: CHANGEPOINT FOUND at index 50! ⚠️
Reason: Percentage change (60%) exceeds 20% threshold
```

### Visual Representation

```
Value (ms)
200 |
    |
180 |
    |
160 |                      ●●●●●●●●●●●●●●●●●●●●●●●●●
    |                      ← After: median=160ms
140 |                      
    |                      
120 |                     ↑ CHANGEPOINT DETECTED
    |                     │ Index 50
100 |●●●●●●●●●●●●●●●●●●●●●│
    |← Before: median=100ms
 80 |                     
    |                     
  0 |_____________________│_________________________
     0   10   20   30   40  50  60   70   80   90  100
     
     ←───── Before ─────→ ←────── After ──────→
     Median: 100ms         Median: 160ms
                          Delta: +60ms (60%)
```

**How Step-Fit Scans**:
```
Test split at t=10:  score = 0.2 (low)
Test split at t=20:  score = 0.4 (low)
Test split at t=30:  score = 0.6 (low)
Test split at t=40:  score = 0.9 (low)
Test split at t=50:  score = 1.35 (BEST!) ← Found it!
Test split at t=60:  score = 0.9 (lower)
Test split at t=70:  score = 0.6 (lower)
...
```

### Why It Works

**Key Insight**: The correct changepoint creates the **maximum difference** between before/after medians.

**Robustness**: Uses median (not mean), so outliers don't create false changepoints.

**Global normalization**: All scores normalized by same sigma, making them comparable.

### Strengths

✅ **Exact location**: Pinpoints the commit where regression started  
✅ **Historical**: Scans full series, finds old regressions  
✅ **Root cause**: Gives you the index to investigate  
✅ **Robust**: Median-based, ignores outliers  
✅ **Dual thresholds**: Statistical (4σ) + practical (20%)  
✅ **No blind spots**: Tests every possible split point  

### Limitations

❌ **Computationally expensive**: Tests N splits (can be slow for large N)  
❌ **One changepoint**: Finds best split, but assumes single step change  
❌ **Not real-time**: Needs full series, can't detect ongoing issues  
❌ **Gradual changes**: May not detect smooth trends (EWMA is better)  

### When to Use

- **Root cause analysis**: Find which commit caused regression
- **Historical investigation**: Understand when performance degraded
- **After ALERT**: Step-Fit tells you WHERE the problem started
- **Batch analysis**: Analyzing collected data after-the-fact

---

## Comparison & When to Use Each

### Quick Decision Matrix

| Scenario | Use This | Why |
|----------|----------|-----|
| Latest build suddenly slow | **Control Chart** | Detects spikes in current data |
| Performance degrading over weeks | **EWMA** | Tracks gradual drift |
| Need to find which commit broke it | **Step-Fit** | Pinpoints exact location |
| Monitoring live builds | **Control Chart + EWMA** | Real-time detection |
| Analyzing historical data | **Step-Fit** | Find when regression started |
| Noisy data with outliers | **All three** | Robust to outliers |

### Complementary Strengths

```
Timeline of a Regression:

Day 1:  Commit X introduces 40% slowdown
        └─ Step-Fit: "Changepoint at commit X" ✓
        └─ EWMA: "15% drift detected" (starting to notice)
        └─ Control Chart: "OK" (only 1 point, too early)

Day 5:  5 commits since regression
        └─ Step-Fit: "Changepoint at commit X" ✓
        └─ EWMA: "20% drift detected" ✓
        └─ Control Chart: "OK" (baseline adapting)

Day 30: 30 commits since regression
        └─ Step-Fit: "Changepoint at commit X" ✓
        └─ EWMA: "25% drift detected" ✓
        └─ Control Chart: "OK" (baseline fully adapted)

Day 31: New spike (2x slower than degraded baseline)
        └─ Step-Fit: "Changepoint at commit X" (old news)
        └─ EWMA: "30% drift detected" ✓
        └─ Control Chart: "SPIKE!" ✓ (detects new issue)
```

**Lesson**: Each algorithm has a time horizon where it excels!

### Detection Coverage

```
Type of Change     | Control Chart | EWMA | Step-Fit |
-------------------|---------------|------|----------|
Sudden spike       |      ✓✓✓      |  ✓   |    ✓     |
Gradual drift      |       ✗       | ✓✓✓  |    ✗     |
Old step change    |       ✗       |  ✓   |   ✓✓✓    |
Recent step change |       ✗*      | ✓✓   |   ✓✓✓    |
Multiple changes   |       ✓       |  ✓   |    ✗**   |

✓✓✓ = Excellent    ✓✓ = Good    ✓ = Fair    ✗ = Poor

*Control Chart misses recent changes due to baseline contamination
**Step-Fit finds best single changepoint, may miss multiple
```

---

## Real-World Examples

### Example 1: Sudden Spike (Control Chart Detects)

**Scenario**: Latest build has a memory leak causing GC pauses

**Data**:
```
Last 31 builds: [200, 198, 202, 201, 199, 200, 198, 202, 201, 200,
                 199, 201, 200, 198, 202, 199, 201, 200, 198, 202,
                 201, 199, 200, 202, 198, 201, 200, 199, 202, 201,
                 1500]  ← Latest: 1500ms (7.5x spike!)
```

**Control Chart**:
```
Baseline median = 200ms
MAD = 1.5ms
sigma = 2.2ms
Upper bound = 200 + (4.0 × 2.2) = 208.8ms

Current = 1500ms
z-score = (1500 - 200) / 2.2 = 590.9

Result: ALERT! 🚨 (z-score 590.9 >> 4.0)
```

**EWMA**:
```
EWMA ≈ 200ms (stable for long time)
Current spike affects it slightly, but within bounds
Result: OK or minor alert
```

**Step-Fit**:
```
Best split at index 30 (last point)
Before median = 200ms, After median = 1500ms
Score = high, percentage = 650%
Result: CHANGEPOINT at index 30
```

**Winner**: Control Chart (immediate detection of spike)

---

### Example 2: Gradual Drift (EWMA Detects)

**Scenario**: Memory usage slowly increasing due to small leaks

**Data** (60 builds):
```
Builds 1-20:   200ms each
Builds 21-40:  200 + (i-20)×3 = 203, 206, 209, ..., 257ms
Builds 41-60:  260 + (i-40)×2 = 262, 264, 266, ..., 298ms
```

**Control Chart** (at build 60):
```
Baseline (last 30) = builds 31-60, median ≈ 280ms
Current = 298ms
Difference = 18ms (6.4%)
Result: OK (within normal variation)
```

**EWMA** (at build 60):
```
EWMA tracks upward trend
Baseline median (from early history) = 200ms
EWMA value ≈ 275ms
Drift = (275 - 200) / 200 × 100% = 37.5%

Result: ALERT! 🚨 (drift 37.5% >> 15%)
```

**Step-Fit** (at build 60):
```
Tests all splits, but no single clear changepoint
Gradual changes don't create strong step signal
Result: WEAK or no changepoint
```

**Winner**: EWMA (designed for gradual trends)

---

### Example 3: Old Step Change (Step-Fit Detects)

**Scenario**: Commit at build 50 (out of 200 total) introduced inefficient algorithm

**Data**:
```
Builds 1-49:    100ms each (fast algorithm)
Builds 50-200:  180ms each (slow algorithm)
```

**Control Chart** (at build 200):
```
Baseline = builds 171-200, all ≈180ms
Current = 180ms
Result: OK (entire baseline is post-regression)
```

**EWMA** (at build 200):
```
Baseline = builds 171-200, median = 180ms
EWMA has fully adapted to 180ms
Drift = 0%
Result: OK
```

**Step-Fit** (at build 200):
```
Scans full series (builds 1-200)
Best split at build 50:
    Before (1-49): median = 100ms
    After (50-200): median = 180ms
    Delta = 80ms (80% regression)

Result: CHANGEPOINT at build 50! 🚨
```

**Winner**: Step-Fit (only one that remembers old baseline)

---

### Example 4: Recent Regression (Step-Fit + EWMA Detect)

**Scenario**: Regression 11 commits ago (homeTabStartToInteractive case)

**Data**:
```
Commits 1-870:  1263ms median (stable)
Commits 871-881: 1876ms median (48.5% regression)
```

**Control Chart** (at commit 881):
```
Baseline = commits 852-881 (last 30)
  - 19 commits before regression (852-870): ~1559ms
  - 11 commits after regression (871-881): ~1876ms
  - Combined median: 1683ms (contaminated!)
  
Current = 2176ms
Difference = (2176 - 1683) / 1683 = 29%
z-score = 1.33

Result: OK (baseline contaminated, can't detect)
```

**EWMA** (at commit 881):
```
Baseline median = 1683ms (from last 30)
EWMA = 1938ms (tracking upward trend)
Drift = (1938 - 1683) / 1683 × 100% = 15.2%

Result: ALERT! 🚨 (drift 15.2% ≥ 15%)
```

**Step-Fit** (at commit 881):
```
Best split at commit 870:
    Before (1-870): median = 1263ms
    After (871-881): median = 1876ms
    Delta = 613ms (48.5% regression)

Result: CHANGEPOINT at commit 870! 🚨
```

**Winners**: EWMA + Step-Fit (Control Chart fooled by contamination)

---

## Why We Need All Three

### The Complete Detection System

**Phase 1: Real-Time Monitoring** (every new build)
```
1. Run Control Chart
   - Quick check: "Is this build a spike?"
   - If ALERT → Investigate immediately

2. Run EWMA  
   - Trend check: "Is there gradual drift?"
   - If ALERT → Review recent commits

3. Run Step-Fit
   - Historical check: "Where did performance change?"
   - If ALERT → Pinpoint exact commit
```

**Phase 2: Triage**
```
If any alert:
    1. Step-Fit → Find regression commit (index X)
    2. EWMA → Confirm drift magnitude
    3. Control Chart → Verify if still spiking
    
    Action: git bisect from commit X, revert if needed
```

**Phase 3: Prevention**
```
Monitor trends:
    - EWMA trending up? → Code review for inefficiencies
    - Repeated Control Chart spikes? → Investigate infrastructure
    - Step-Fit shows regression? → Add performance test at commit X
```

### Coverage Matrix

```
Question                              | Control | EWMA | Step-Fit |
--------------------------------------|---------|------|----------|
"Is the latest build slow?"           |   ✓✓✓   |  ✓   |    ✓     |
"Is performance drifting?"            |    ✗    | ✓✓✓  |    ✗     |
"Which commit caused regression?"     |    ✗    |  ✗   |   ✓✓✓    |
"Is there a spike right now?"         |   ✓✓✓   |  ✓   |    ✓     |
"When did degradation start?"         |    ✗    |  ✓   |   ✓✓✓    |
"Is performance stable?"              |    ✓    | ✓✓   |    ✓     |
"Should I revert the latest commit?"  |   ✓✓    |  ✓   |    ✓     |
"What's the historical baseline?"     |    ✗    |  ✗   |   ✓✓✓    |
```

### Real-World Workflow

```
┌─────────────────────────────────────────┐
│  New Build Completes                     │
│  Performance: 250ms                      │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Control Chart: SPIKE! z=12.5           │ ← First Line of Defense
│  → Immediate alert to team              │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  EWMA: Drift = 18%                      │ ← Confirms Trend
│  → Yes, there's a pattern               │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Step-Fit: Changepoint at commit #1245  │ ← Root Cause
│  → That's the PR that added caching!    │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Action: Investigate commit #1245       │
│  Found bug: Cache lookup O(n) not O(1)  │
│  Fix applied, performance restored      │
└─────────────────────────────────────────┘
```

---

## Summary Table

| Feature | Control Chart | EWMA | Step-Fit |
|---------|--------------|------|----------|
| **Purpose** | Spike detection | Trend detection | Changepoint detection |
| **Window** | Last 30 points | Full series (weighted) | Full series |
| **Complexity** | O(1) | O(N) | O(N²) or O(N log N) |
| **Real-time** | ✓ Yes | ✓ Yes | ✗ Batch only |
| **Historical** | ✗ No (30 points) | ✓ Weighted | ✓ Full history |
| **Pinpoint location** | ✗ No | ✗ No | ✓ Exact commit |
| **Outlier robust** | ✓ MAD-based | ✓ Filters outliers | ✓ Median-based |
| **Best for** | Recent spikes | Gradual drift | Root cause |
| **Limitation** | Recency bias | Lagging | Single changepoint |
| **Alert threshold** | 4.0σ + practical | 3.0σ OR 15% drift | 4.0σ OR 20% change |

---

## Conclusion

**No single algorithm is perfect.** Each has strengths and blind spots.

**The three-method approach provides:**
- **Immediate detection** (Control Chart)
- **Trend awareness** (EWMA)
- **Root cause analysis** (Step-Fit)

**Together**, they create a comprehensive performance regression detection system that catches all types of problems:
- Sudden spikes → Control Chart catches it
- Gradual drift → EWMA catches it  
- Historical step changes → Step-Fit catches it
- Recent regressions → EWMA + Step-Fit catch it

**Best practice**: Use all three, trust the one that's designed for the problem type you're investigating.

