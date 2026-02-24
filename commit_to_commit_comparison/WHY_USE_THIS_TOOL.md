# Why Upgrade Your Performance Regression Detection?

## A Case for Statistical Rigor in Performance Testing

---

## The Problem with Simple Median Comparison

### What Your Team Currently Does:
```
baseline_median = median(10-30 runs of commit A)
target_median = median(10-30 runs of commit B)

if target_median > baseline_median:
    flag_as_regression()
```

### Why This Approach Fails:

| Problem | Example | Result |
|---------|---------|--------|
| **High False Positive Rate** | Baseline: 100ms, Target: 102ms (2ms noise) | Flagged as regression |
| **High False Negative Rate** | High variance hides real 50ms regression | Missed regression |
| **No Statistical Confidence** | Is 5ms difference real or random? | Unknown |
| **Ignores Data Quality** | 5 runs with 40% variance | "Valid" result |
| **No Tail Latency Check** | Median same, but p90 +200ms | Missed regression |

---

## What This Tool Does Better

### Multi-Layered Defense Against False Results

```
                    +------------------+
                    |  Quality Gates   |  <-- Reject bad data FIRST
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
       +------v------+ +-----v-----+ +------v------+
       | Threshold   | | Tail      | | Direction   |
       | Check       | | Check     | | Check       |
       +------+------+ +-----+-----+ +------+------+
              |              |              |
              +--------------+--------------+
                             |
                    +--------v---------+
                    | Wilcoxon Test    |
                    +--------+---------+
                             |
                    +--------v---------+
                    | Practical        |
                    | Significance     |
                    +--------+---------+
                             |
                    +--------v---------+
                    | Bootstrap CI     |
                    +------------------+
```

---

## Algorithm 1: Quality Gates (The Guardian)

### What It Does:
Rejects data that's too noisy or too small to make reliable conclusions.

### Why You Need It:
| Without Quality Gates | With Quality Gates |
|----------------------|-------------------|
| 5 runs flagged as "regression" | "INCONCLUSIVE: 5 samples too few" |
| 40% variance = "valid" result | "INCONCLUSIVE: CV 40% > 15% max" |
| Random noise = "regression" | "Cannot determine - collect more data" |

### Checks:
1. **Minimum Sample Size**: n >= 10 required
2. **Coefficient of Variation (CV)**: CV <= 15% required

### The Math:
```
CV = (standard_deviation / mean) * 100

Example:
  Runs: [100, 95, 180, 90, 85]  # One outlier
  Mean: 110ms
  StdDev: 38ms
  CV = 38/110 * 100 = 34.5%  --> REJECTED (> 15%)
```

### Why 15% CV Threshold?
- CV > 15% means your measurements have too much noise
- A 50ms "regression" in 15% noise data could easily be random variance
- Forces teams to fix measurement methodology before trusting results

---

## Algorithm 2: Dynamic Threshold Check

### What It Does:
Uses both absolute AND relative thresholds, whichever is stricter.

### Why You Need It:

| Baseline | Simple 5% Check | Dynamic Threshold | Better Choice |
|----------|-----------------|-------------------|---------------|
| 20ms | 1ms (too sensitive!) | 50ms (MS_FLOOR) | Absolute |
| 2000ms | 100ms | 100ms | Relative |
| 50ms | 2.5ms | 50ms (MS_FLOOR) | Absolute |

### The Math:
```
threshold = max(MS_FLOOR, PCT_FLOOR * baseline_median)

Where:
  MS_FLOOR = 50ms (absolute minimum)
  PCT_FLOOR = 5% (relative)

Example 1: Baseline 100ms
  threshold = max(50, 0.05 * 100) = max(50, 5) = 50ms

Example 2: Baseline 2000ms
  threshold = max(50, 0.05 * 2000) = max(50, 100) = 100ms
```

### Adaptive Scaling with Variance:
When data has elevated (but acceptable) variance, thresholds automatically widen:
```
effective_threshold = base_threshold * (1 + 0.5 * CV/100)

Example: CV = 10%, base = 50ms
  effective = 50 * (1 + 0.5 * 0.10) = 52.5ms
```

---

## Algorithm 3: Tail Latency Check (p90)

### What It Does:
Checks the 90th percentile, not just the median.

### Why You Need It:

```
Scenario: Median looks fine, but worst-case degraded

Baseline:  [100, 102, 98, 105, 101, 99, 103, 100, 104, 150]
           Median: 101ms, P90: 150ms

Target:    [100, 103, 99, 102, 101, 100, 104, 101, 102, 350]
           Median: 101ms, P90: 350ms

Simple median comparison: "No regression!" (101ms = 101ms)
This tool: "FAIL: Tail delta 200ms exceeds threshold 75ms"
```

### Why P90?
- User experience is defined by worst-case, not average
- 10% of users seeing 2x slower response = bad UX
- SLOs/SLAs often defined on P95/P99

### The Math:
```
tail_threshold = max(TAIL_MS_FLOOR, TAIL_PCT_FLOOR * baseline_p90)

Where:
  TAIL_MS_FLOOR = 75ms
  TAIL_PCT_FLOOR = 5%
```

---

## Algorithm 4: Directionality Check

### What It Does:
Checks if a consistent majority of runs are slower.

### Why You Need It:

```
Scenario: Median similar, but target consistently slower

Baseline samples: [100, 98, 102, 101, 99, 103, 100, 97, 101, 102] (median = 100.5ms)
Target samples:   [108, 105, 110, 109, 106, 107, 104, 108, 109, 95]  (median = 107.5ms)

Median difference: 7ms (below 50ms threshold)
But: 9/10 target samples > baseline median (100.5ms)
Directionality: 90% of target samples slower!
```

### The Math:
```
baseline_median = median(baseline)
positive_fraction = count(target > baseline_median) / len(target)

if positive_fraction >= 0.70:  # 70% threshold
    flag_regression()

Example: 9/10 = 90% target samples above baseline median --> FLAGGED
```

### Why 70%?
- 50% would be random chance
- 70% indicates a consistent pattern
- Catches "death by a thousand cuts" regressions

---

## Algorithm 5: Mann-Whitney U Test

### What It Does:
Statistical test that detects if target distribution is stochastically greater than baseline distribution (for independent samples).

### Why You Need It:

| Simple Approach | Mann-Whitney U Test |
|-----------------|---------------------|
| "Is median different?" | "Is target distribution shifted higher?" |
| No p-value | p-value for confidence |
| Binary yes/no | Statistical significance |

### The Math:
```
1. Combine all observations from both groups
2. Rank all observations together
3. Calculate U statistic based on ranks in each group
4. Compare to expected distribution under null hypothesis
5. Output: p-value

if p_value < 0.05:  # 95% confidence
    "Statistically significant performance change"
```

### Why Mann-Whitney U (for independent samples)?
- **Non-parametric**: No assumption of normal distribution
- **Robust to outliers**: Uses ranks, not raw values
- **Independent samples design**: Proper for sequential testing (AAA BBB)
- **Unequal sample sizes**: Works with different baseline/target sizes
- **Performance data is rarely normal**: Often skewed

---

## Algorithm 6: Practical Significance Override

### What It Does:
Prevents flagging statistically significant but negligible changes.

### Why You Need It:

```
Scenario: Statistically significant but who cares?

Baseline: [100.0, 100.1, 100.0, 100.2, 100.1] (very consistent)
Target:   [102.0, 102.1, 102.0, 102.2, 102.1] (also consistent)

Mann-Whitney U p-value: 0.003 (highly significant!)
Median difference: 2ms (0.002%)

Without override: "FAIL: Mann-Whitney U test significant (p=0.003)"
With override:    "PASS: 2ms difference below practical threshold (2ms)"
```

### The Math:
```
# Dynamic practical threshold
practical_threshold = baseline_median * 0.01  # 1% of baseline
practical_threshold = clamp(practical_threshold, 2ms, 20ms)

if abs(median_delta) < practical_threshold:
    override_to_pass()

Examples:
  Baseline 100ms:  threshold = max(2, min(20, 1)) = 2ms
  Baseline 500ms:  threshold = max(2, min(20, 5)) = 5ms
  Baseline 5000ms: threshold = max(2, min(20, 50)) = 20ms (capped)
```

### Why This Matters:
- Users don't notice 2ms changes
- CI shouldn't block on irrelevant noise
- Focuses attention on real issues

---

## Algorithm 7: Bootstrap Confidence Intervals

### What It Does:
Provides confidence intervals for the median delta.

### Why You Need It:

| Point Estimate Only | With Bootstrap CI |
|--------------------|-------------------|
| "Delta is 15ms" | "Delta is 15ms (95% CI: 8ms to 22ms)" |
| No uncertainty measure | Know the range of likely values |
| "Is 15ms significant?" | "CI doesn't include 0, it's real" |

### The Math:
```
1. Resample baseline and target arrays independently (5000 times each)
2. Calculate median difference for each resample pair
3. Take 2.5th and 97.5th percentile of bootstrap median differences
4. Output: [CI_low, CI_high]

Example:
  Original median difference: 15ms
  Bootstrap median differences: [12, 18, 14, 16, 13, 19, 15, ...]
  95% CI: [8ms, 22ms]

Interpretation:
  - CI doesn't include 0 --> real regression
  - CI includes 0 --> might be noise
```

### Why Bootstrap?
- Works with any distribution
- No assumptions required
- Intuitive interpretation
- Industry standard for uncertainty quantification

---

## Equivalence Testing: Proving "No Change"

### The Problem:
"Not detecting a regression" != "Proving no regression"

| Scenario | Traditional Testing | Equivalence Testing |
|----------|--------------------|--------------------|
| No data | "No regression" | "Cannot determine" |
| Noisy data | "No regression" | "Cannot determine" |
| Truly equivalent | "No regression" | "Equivalent (proven)" |

### The Math:
```
# Equivalence margin: 30ms (imperceptible to users)

if CI_low > -30ms AND CI_high < 30ms:
    "EQUIVALENT: Performance unchanged"
else:
    "Cannot prove equivalence"

Example 1: CI = [-5ms, +10ms]
  -30 < -5 AND 10 < 30 --> EQUIVALENT

Example 2: CI = [-45ms, +20ms]
  -45 < -30 is FALSE --> Cannot prove equivalence
```

---

## Summary: Simple vs. This Tool

| Aspect | Simple Median | This Tool |
|--------|---------------|-----------|
| **Data quality check** | None | Quality gates (CV, sample size) |
| **Threshold type** | Fixed or relative only | Adaptive (absolute + relative) |
| **Tail latency** | Not checked | P90 check included |
| **Consistency check** | None | Directionality (70% rule) |
| **Statistical test** | None | Wilcoxon signed-rank |
| **False positives** | High (2ms noise = "regression") | Low (practical significance override) |
| **False negatives** | High (noise hides real issues) | Low (multiple detection layers) |
| **Uncertainty** | Unknown | Bootstrap confidence intervals |
| **Equivalence proof** | Cannot prove | Equivalence testing |
| **Result types** | Pass/Fail | Pass/Fail/Inconclusive/No Change |

---

## Decision Flow

```
                         START
                           |
                  +--------v--------+
                  | Quality Gates   |
                  | (CV < 15%,      |
                  |  n >= 10)       |
                  +--------+--------+
                           |
              +------------+------------+
              | FAIL                    | PASS
              v                         v
    +------------------+      +---------+---------+
    | INCONCLUSIVE     |      | Run All Checks    |
    | "Data too noisy" |      | (5 checks)        |
    +------------------+      +---------+---------+
                                        |
                         +--------------+--------------+
                         | Any check fails?            |
                         |                             |
                   +-----+-----+                 +-----+-----+
                   | YES       |                 | NO        |
                   v           |                 v           |
          +--------+-------+   |     +-----------+----------+
          | Practical      |   |     | Check practical      |
          | Significance?  |   |     | significance         |
          +--------+-------+   |     +-----------+----------+
                   |           |                 |
         +---------+---------+ |     +-----------+----------+
         | YES     | NO      | |     | Delta < threshold    |
         v         v         | |     v                      v
     +------+  +-------+     | |  +----------+        +------+
     | PASS |  | FAIL  |     | |  | NO CHANGE|        | PASS |
     +------+  +-------+     | |  +----------+        +------+
                             | |
                             +-+
```

---

## Real-World Impact

### Case Study: The 2.5ms Trap

**Without This Tool:**
```
Commit A: median 2500ms
Commit B: median 2502.5ms (0.1% increase)
Wilcoxon p-value: 0.003

Result: BUILD FAILED
Team wastes 2 hours investigating
Finding: "It's just noise"
```

**With This Tool:**
```
Result: PASS (practical significance override)
Reason: 2.5ms (0.1%) below practical threshold (20ms)
Team continues working
```

### Case Study: The Hidden P90 Regression

**Without This Tool:**
```
Median: 100ms (unchanged)
Result: BUILD PASSED
```

**With This Tool:**
```
Median: 100ms (OK)
P90: +200ms regression detected
Result: BUILD FAILED
Reason: Tail delta 200ms exceeds threshold 75ms
Team catches issue before production
```

### Case Study: The Noisy Data Trap

**Without This Tool:**
```
Data CV: 35% (very noisy)
Median delta: -50ms (looks like improvement!)
Result: "IMPROVEMENT!"
Reality: Random noise, no real change
```

**With This Tool:**
```
Data CV: 35% exceeds 15% maximum
Result: INCONCLUSIVE
Reason: "Measurements too noisy for reliable detection"
Action: Fix measurement methodology
```

---

## Recommendations

### When to Use This Tool:
1. **CI/CD pipelines**: Gate deployments on real regressions
2. **A/B testing**: Statistically validate performance changes
3. **Release validation**: Prove no regression before shipping
4. **Investigation**: Quantify impact of code changes

### Best Practices:
1. **Collect sufficient samples**: Minimum 10 per group, prefer 30+
2. **Control variance**: Target CV < 15% for reliable results
3. **Check tail latency**: P90 matters for user experience
4. **Trust the tool**: Inconclusive means improve your test environment
5. **Sequential collection**: Run all baseline, then all target (AAA BBB)

---

## Getting Started

```python
from commit_to_commit_comparison import gate_regression

result = gate_regression(
    baseline=[...],  # Your baseline measurements
    target=[...],    # Your target measurements
)

if result.passed:
    if result.no_change:
        print("No meaningful performance difference")
    else:
        print("No regression detected")
elif result.inconclusive:
    print("Data quality insufficient - collect more data")
else:
    print(f"Regression detected: {result.reason}")
```

---

## Questions?

### Key Takeaways:
1. Simple median comparison has high false positive AND false negative rates
2. Quality gates prevent conclusions from noisy data
3. Multiple detection layers catch different types of regressions
4. Practical significance prevents blocking on irrelevant changes
5. Statistical confidence quantifies uncertainty

### The Bottom Line:
**Stop guessing. Start measuring with statistical rigor.**
