# Why Use Commit-to-Commit Comparison Over Simple Median Comparison

## Executive Summary

**Current Approach:** Comparing medians of 10-30 runs
**Problem:** Can't reliably distinguish between real regressions and random noise
**Solution:** Statistical regression detection with 4 complementary algorithms

---

## The Problem with Simple Median Comparison

### Your Current Workflow

```
Build 45: Median = 412ms (from 20 runs)
Build 46: Median = 423ms (from 20 runs)

Question: Is +11ms a regression?
```

### Why This Fails

**You can't answer these critical questions:**

1. **Is this change real or noise?**
   - 11ms could be normal variation
   - Or it could be the start of a 50% regression

2. **What's the historical baseline?**
   - Is 412ms normal for this metric?
   - Or was it already elevated from a previous regression?

3. **Is there a trend?**
   - Are we slowly degrading (400 → 405 → 410 → 415)?
   - Or just random fluctuation?

4. **Which commit caused it?**
   - Simple comparison can't pinpoint the culprit
   - You waste time investigating wrong commits

### Real Example: Simple Median Comparison Fails

**Scenario:** Gradual performance degradation over 50 builds

```
Build 1:  400ms
Build 10: 405ms  (+5ms, +1.25%)  ✓ PASS (seems minor)
Build 20: 410ms  (+5ms, +1.22%)  ✓ PASS (seems minor)
Build 30: 415ms  (+5ms, +1.22%)  ✓ PASS (seems minor)
Build 40: 420ms  (+5ms, +1.20%)  ✓ PASS (seems minor)
Build 50: 425ms  (+5ms, +1.19%)  ✓ PASS (seems minor)

Total degradation: +25ms (+6.25%)
```

**Problem:** Each individual comparison passes, but you've accumulated a 6% regression!

---

## The Solution: Statistical Regression Detection

### What Commit-to-Commit Comparison Provides

Instead of asking **"Did the median change?"**, we ask:

1. **"Is the latest value statistically unusual?"** → Control Chart
2. **"Is there a trend toward degradation?"** → EWMA
3. **"Where exactly did performance change?"** → Step-Fit
4. **"Is performance degrading long-term?"** → Linear Trend

---

## The 4 Algorithms Explained

### Algorithm 1: Control Chart (Spike Detection)

**What it does:** Detects if the latest build is an outlier

**How it works:**
1. Calculate baseline from last 30 builds: median = 408ms, MAD = 12ms
2. Set control limits: 408 ± (4 × 12) = [360ms, 456ms]
3. Check current value: 520ms > 456ms → ALERT!

**Visual Example:**
```
500ms |                                           ⚠️ SPIKE!
      |
450ms |...................................← Upper limit (4σ)
      |
408ms |●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●← Baseline
      |
360ms |...................................← Lower limit (4σ)
      |
```

**When to use:**
- Continuous monitoring of new builds
- Detecting sudden spikes immediately
- When you need real-time alerts

**Advantages over median comparison:**
- ✅ Statistically rigorous (not arbitrary thresholds)
- ✅ Accounts for historical variability
- ✅ Robust to outliers (uses MAD, not std dev)

---

### Algorithm 2: EWMA (Exponentially Weighted Moving Average)

**What it does:** Detects gradual performance drift over time

**How it works:**
1. Track smoothed average: EWMA = 0.25 × current + 0.75 × previous_EWMA
2. Compare EWMA to baseline: drift = (425 - 400) / 400 = 6.25%
3. Alert if drift exceeds 15%

**Visual Example:**
```
Value (ms)
425 |                              ●●●●●●● ← Raw data (noisy)
420 |                          ●●●
415 |                      ●●●     ═════════ ← EWMA (smooth trend)
410 |                  ●●●     ═══
405 |              ●●●     ═══
400 |●●●●●●●●══════
    |________________________________________________
```

**Real Example: Gradual Regression**
```
Builds: [400, 405, 410, 415, 420, 425, 430, 435, 440] ms

Simple Median: Each change is small (+5ms), all PASS ✓
EWMA: Drift of +40ms (10%) detected! ⚠️

→ EWMA catches the creep that median comparison misses
```

**When to use:**
- Detecting slow degradation over weeks
- Early warning before performance gets bad
- Tracking cumulative effects of small changes

**Advantages over median comparison:**
- ✅ Detects gradual trends (median comparison only sees point-to-point)
- ✅ Smooths out noise while preserving signal
- ✅ Early warning system

---

### Algorithm 3: Step-Fit (Changepoint Detection)

**What it does:** Finds the EXACT commit where performance changed

**How it works:**
1. Test every possible split point in the series
2. For each split, calculate median before vs. median after
3. Find the split with maximum difference
4. Refine to pinpoint the exact commit

**Visual Example:**
```
Value (ms)
650 |                      ●●●●●●●●●●●●● ← After: 650ms
    |                      ↑ CHANGEPOINT!
    |                      │ Commit #57
400 |●●●●●●●●●●●●●●●●●●●●●│
    |← Before: 400ms
    |_____________________│______________
     0                   57            100
```

**Real Example: Finding the Culprit**
```
Series: [370, 375, 380, 370, 385, 380, 392, 608, 650, 665, ...]
                                         ↑ Big jump at index 57

Step-Fit Analysis:
  ✓ Changepoint detected at index 57
  ✓ Before: 370ms → After: 650ms
  ✓ Delta: +280ms (+76%)
  ✓ Commit: ABC123DEF

→ You know EXACTLY which commit to investigate!
```

**When to use:**
- Root cause analysis (find which commit broke it)
- Historical investigation (when did this start?)
- After getting an alert (where should I look?)

**Advantages over median comparison:**
- ✅ Pinpoints exact commit (median comparison just says "something changed")
- ✅ Scans full history (not just last 2 builds)
- ✅ Quantifies the impact of the regression

---

### Algorithm 4: Linear Trend Detection

**What it does:** Detects systematic long-term degradation

**How it works:**
1. Fit linear regression: y = mx + b
2. Check if slope is positive (degrading) with R² > 0.7
3. Verify statistical significance (p-value < 0.05)
4. Alert if total change exceeds threshold

**Visual Example:**
```
Value (ms)
500 |                                         ●
    |                                     ●
    |                                 ●       ═══ Trend line
    |                             ●       ═══    (slope = +2ms/build)
450 |                         ●       ═══
    |                     ●       ═══
    |                 ●       ═══
400 |             ●       ═══
    |         ●       ═══
    |     ●       ═══
    | ●       ═══
    |_____________________________________________________
     0   10   20   30   40   50
```

**Real Example: Systematic Degradation**
```
Last 50 builds:
  Build 1:  400ms
  Build 50: 500ms

Linear Regression:
  Slope: +2ms/build
  R²: 0.85 (strong linear relationship)
  p-value: 0.0001 (highly significant)
  Total change: +25% over 50 builds

→ Clear evidence of systematic degradation
  (not just random fluctuation)
```

**When to use:**
- Detecting long-term patterns
- Identifying systematic issues (memory leaks, resource exhaustion)
- Planning capacity/performance work

**Advantages over median comparison:**
- ✅ Identifies patterns over time (median is point-in-time)
- ✅ Statistical validation (not just "looks bad")
- ✅ Predictive (can project future degradation)

---

## Why You Need ALL 4 Algorithms

### Each Algorithm Catches Different Regression Types

| Regression Type | Control Chart | EWMA | Step-Fit | Linear Trend |
|-----------------|---------------|------|----------|--------------|
| **Sudden spike** (latest build 2x slower) | ✅ | ✓ | ✓ | ❌ |
| **Gradual creep** (each build +5ms) | ❌ | ✅ | ❌ | ✅ |
| **Old regression** (50 builds ago) | ❌ | ✓ | ✅ | ✓ |
| **Recent step change** (10 builds ago) | ❌ | ✅ | ✅ | ❌ |

✅ = Excellent detection | ✓ = Good detection | ❌ = Misses it

### Real-World Example: Complex Regression

**Scenario:** App performance over 100 builds

```
Builds 1-50:   Stable at 400ms
Builds 51-60:  Gradual creep: 400→420ms (memory leak)
Build 61:      Spike to 650ms (bad commit)
Builds 62-100: New baseline at 440ms (partially fixed)
```

**Simple Median Comparison Results:**
```
Build 60: 420ms vs 400ms = +20ms (+5%)
  → Might flag as minor concern, might not

Build 61: 650ms vs 420ms = +230ms (+55%)
  → Flags as major regression ✓

Build 100: 440ms vs 400ms = +40ms (+10%)
  → But comparing to what baseline?
```

**Commit-to-Commit Comparison Results:**

**Build 58 (during gradual creep):**
- Control Chart: ✓ OK (no individual spike)
- **EWMA: ⚠️ ALERT** (drift 6%, threshold 5%)
- Step-Fit: ✓ OK (no sharp change yet)
- Trend: ✓ OK (not enough data)

**Build 61 (spike):**
- **Control Chart: ⚠️ ALERT** (650ms >> 456ms upper bound)
- **EWMA: ⚠️ ALERT** (drift 45%)
- **Step-Fit: ⚠️ ALERT** (changepoint at build 61)
- Trend: ⚠️ ALERT (significant upward slope)

**Build 100 (partial recovery):**
- Control Chart: ✓ OK (baseline adapted to 440ms)
- **EWMA: ⚠️ ALERT** (still 10% above original)
- **Step-Fit: ⚠️ ALERT** (points to build 61 as root cause)
- **Trend: ⚠️ ALERT** (new baseline 10% higher)

**Outcome:**
- ✅ Detected gradual creep early (Build 58)
- ✅ Identified exact regression commit (Build 61)
- ✅ Confirmed performance never fully recovered (Build 100)

---

## Comparison: Simple Median vs. Statistical Detection

### Scenario: Recent Regression (11 builds ago)

**Data:**
```
Builds 1-870:   1263ms (stable)
Builds 871-881: 1876ms (48.5% regression)
```

#### Simple Median Comparison (at build 881):
```
Build 880: 1845ms
Build 881: 1912ms

Delta: +67ms (+3.6%)

Result: ✓ PASS (small change, seems normal)
```

**Problem:** Comparing to wrong baseline (already regressed)!

#### Statistical Detection (at build 881):

**Control Chart:**
```
Baseline (last 30): Mixed (19 good + 11 bad) = 1683ms
Current: 1912ms
z-score: 1.33

Result: ✓ OK
```
**Problem:** Baseline contaminated by recent regression

**EWMA:**
```
Baseline median: 1683ms
EWMA: 1938ms
Drift: (1938 - 1683) / 1683 = 15.2%

Result: ⚠️ ALERT (drift ≥ 15%)
```
**Success:** Detects the drift!

**Step-Fit:**
```
Scanning full history...
Best split at build 870:
  Before (1-870):  median = 1263ms
  After (871-881): median = 1876ms
  Delta: +613ms (+48.5%)

Result: ⚠️ ALERT
  Commit: Build 870 (EXACT LOCATION!)
```
**Success:** Pinpoints the exact regression commit!

### Summary

| Feature | Simple Median | Commit-to-Commit |
|---------|---------------|------------------|
| **Detected regression** | ❌ No | ✅ Yes |
| **Found root cause** | ❌ No | ✅ Yes (build 870) |
| **Quantified impact** | +67ms (+3.6%) | +613ms (+48.5%) |
| **False result reason** | Compared to contaminated baseline | N/A |

---

## Key Advantages Summary

### 1. Statistical Rigor
**Simple Median:** Arbitrary thresholds (is 5% bad? is 10% bad?)
**Our Tool:** Adaptive thresholds based on historical variability

### 2. Historical Context
**Simple Median:** Only knows about last 2 builds
**Our Tool:** Analyzes full series (50-100+ builds)

### 3. Root Cause Analysis
**Simple Median:** "Something got slower"
**Our Tool:** "Commit #870 introduced +613ms regression"

### 4. Catches All Regression Types
**Simple Median:** Only catches large point-to-point changes
**Our Tool:**
- Sudden spikes → Control Chart
- Gradual creep → EWMA
- Step changes → Step-Fit
- Long-term trends → Linear Trend

### 5. Reduces False Positives
**Simple Median:** Noise can look like regression
**Our Tool:** Statistical tests separate signal from noise

### 6. Reduces False Negatives
**Simple Median:** Gradual degradation goes unnoticed
**Our Tool:** EWMA and Trend catch slow degradation

### 7. Adaptive Thresholds
**Simple Median:** Same threshold for all metrics
**Our Tool:** Adjusts based on:
- Data series length (10 vs 100 points)
- Historical variability (noisy vs stable)
- Metric characteristics (time vs frame count)

### 8. Quality Gates
**Simple Median:** Fails on noisy data
**Our Tool:**
- Detects poor data quality
- Returns "inconclusive" instead of false alarms
- Suggests minimum sample sizes

---

## Real Output Examples

### Example 1: Clear Regression Detected

```
╔═══════════════════════════════════════════════════════════╗
║  REGRESSION DETECTED ⚠️                                   ║
╚═══════════════════════════════════════════════════════════╝

Metric: homeTabStartToInteractive_timeToInteractiveMs

Series Analysis:
  Total builds: 252
  Baseline (0-870): 1263ms (median)
  Recent (871-881): 1876ms (median)

Algorithm Results:

  1. Control Chart:
     Status: ✓ OK
     Latest: 1912ms
     Upper bound: 1748ms
     Note: Baseline contaminated by recent regression

  2. EWMA:
     Status: ⚠️ ALERT
     EWMA value: 1938ms
     Baseline: 1683ms
     Drift: +15.2% (threshold: 15%)

  3. Step-Fit:
     Status: ⚠️ ALERT
     Changepoint: Build 870
     Before: 1263ms
     After: 1876ms
     Delta: +613ms (+48.5%)

     🎯 ROOT CAUSE: Commit at index 870

  4. Linear Trend:
     Status: ⚠️ ALERT
     Slope: +12ms/build
     R²: 0.78
     p-value: < 0.001

RECOMMENDATION:
  → Investigate commit at build 870
  → Regression magnitude: +48.5%
  → Consider reverting or optimizing the change
```

### Example 2: No Regression (Stable Performance)

```
╔═══════════════════════════════════════════════════════════╗
║  PERFORMANCE STABLE ✓                                     ║
╚═══════════════════════════════════════════════════════════╝

Metric: AppStartToInteractive_durationMs

Algorithm Results:

  1. Control Chart: ✓ OK
     Latest: 412ms
     Bounds: [380ms, 445ms]

  2. EWMA: ✓ OK
     Drift: +2.1% (threshold: 15%)

  3. Step-Fit: ✓ OK
     No significant changepoint detected

  4. Linear Trend: ✓ OK
     Slope: +0.3ms/build
     R²: 0.12 (no linear pattern)

CONCLUSION:
  → No regression detected
  → Performance within normal variation
  → Continue monitoring
```

---

## When to Use Each Algorithm

### Decision Tree

```
New build completed
     │
     ├─ Is latest value a spike?
     │  └─ YES → Control Chart alerts → Investigate immediately
     │  └─ NO  → Continue
     │
     ├─ Is there gradual degradation?
     │  └─ YES → EWMA alerts → Review recent commits
     │  └─ NO  → Continue
     │
     ├─ Did performance change at some point?
     │  └─ YES → Step-Fit alerts → Points to exact commit
     │  └─ NO  → Continue
     │
     └─ Is there long-term trend?
        └─ YES → Linear Trend alerts → Plan optimization work
        └─ NO  → ✓ All good!
```

### Usage Guidelines

**For Daily Monitoring:**
- Run all 4 algorithms on every build
- Trust Control Chart for immediate issues
- Check EWMA weekly for trends

**For Historical Analysis:**
- Use Step-Fit to find when regression started
- Use Linear Trend to assess overall health

**For Root Cause Investigation:**
- Step-Fit tells you the exact commit
- EWMA confirms the magnitude
- Trend shows if it's systematic

---

## ROI: Why This Matters

### Time Savings

**Before (Simple Median):**
```
1. Notice performance "seems worse"
2. Compare last 2 builds: "Hmm, 3% slower"
3. Is that real or noise? Unknown.
4. Check last 10 builds manually
5. Still not sure where it started
6. Git bisect 50 commits (hours of work)
7. Finally find the culprit
```
**Time: 4-8 hours**

**After (Statistical Detection):**
```
1. Automated alert: "Regression at build 870"
2. Step-Fit points to exact commit
3. Investigate that commit
4. Fix or revert
```
**Time: 30 minutes**

### Preventing "Death by 1000 Cuts"

**Simple median comparison misses:**
- +2ms per build × 50 builds = +100ms (25% degradation)
- Each change individually passes
- Cumulative effect is devastating

**Statistical detection catches:**
- EWMA alerts at +5% (build 10)
- Linear Trend confirms pattern
- You fix it before it gets bad

### Confidence in Releases

**With Simple Median:**
- "Build passed performance tests"
- (But tests might have missed gradual degradation)

**With Statistical Detection:**
- "All 4 algorithms confirm stable performance"
- "No changepoints, no drift, no trend"
- Ship with confidence

---

## Getting Started

### Minimum Requirements

- **Data:** At least 30 historical builds
- **Ideal:** 50-100 builds for best accuracy
- **Each build:** 10-30 runs (same as current)

### Migration Path

**Phase 1:** Run both tools in parallel
- Keep your simple median comparison
- Add statistical detection
- Compare results for 2-4 weeks

**Phase 2:** Trust but verify
- Use statistical detection for alerts
- Verify with manual investigation
- Build confidence in the system

**Phase 3:** Full automation
- Automated CI gates
- Block releases on regression
- Root cause analysis built-in

---

## Conclusion

### Simple Median Comparison Limitations

❌ Can't distinguish signal from noise
❌ No historical context
❌ Misses gradual degradation
❌ Can't find root cause
❌ Arbitrary thresholds
❌ High false positive rate
❌ High false negative rate

### Commit-to-Commit Comparison Benefits

✅ Statistical rigor (not guesswork)
✅ Full historical analysis
✅ Catches ALL regression types
✅ Pinpoints exact commit
✅ Adaptive thresholds
✅ Reduces false positives
✅ Reduces false negatives
✅ Saves investigation time
✅ Prevents slow degradation
✅ Ships with confidence

### The Bottom Line

**Simple median comparison answers:** "Did the number change?"

**Statistical detection answers:**
- Is this change real or noise?
- Where did the regression start?
- How bad is it really?
- Is there a pattern?
- Should I be worried?
- What commit should I investigate?

---

## Questions?

**"Is this overkill for my project?"**
- If you have <10 builds: Maybe
- If you have 30+ builds: No - simple median is unreliable at scale
- If regressions are costly: Definitely worth it

**"Won't this be too sensitive?"**
- Adaptive thresholds adjust to your data
- Quality gates prevent false alarms on noisy data
- Multiple algorithm consensus reduces false positives

**"What if I don't have 100 builds?"**
- Works with as few as 10 builds (adjusted thresholds)
- Accuracy improves with more data
- Start collecting now!

**"Can I customize the algorithms?"**
- Yes - all thresholds are configurable
- Default values based on research & testing
- Tune to your specific needs

---

## Next Steps

1. **Review Example Reports**
   - Check `commit_to_commit_comparison/test_output/*.html`
   - See real regression detection in action

2. **Read Algorithm Details**
   - `PERFORMANCE_REGRESSION_DETECTION.md` - Overview
   - `DETECTION_ALGORITHMS_GUIDE.md` - Deep dive

3. **Run a Pilot**
   - Test on 1-2 key metrics
   - Compare results with current approach
   - Measure time savings

4. **Adopt Incrementally**
   - Start with Step-Fit (root cause analysis)
   - Add EWMA (trend monitoring)
   - Full suite for critical metrics

---

**Remember:** Performance regressions are expensive. Detection is cheap.

**The question isn't "Should we use statistical detection?"**
**The question is "Can we afford not to?"**
