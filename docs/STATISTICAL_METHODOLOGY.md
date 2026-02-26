# Statistical Methodology

## What Makes This Tool Statistically Sound

### 1. One-Sided Mann-Whitney U Test

**Why one-sided?**
- We have a directional hypothesis: "Is target slower than baseline?"
- One-sided test has more statistical power for directional hypotheses
- Combined with direction checks (P(T>B) > 0.5 AND median_delta > 0)

**Result:** Never fails on performance improvements, maximum power for detecting regressions

### 2. Adaptive Tail Latency Metric

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

### 3. Practical Significance Override

**The problem:** Statistical significance != practical importance

**Example:**
```
Baseline: 2500ms
Target:   2502.5ms
Mann-Whitney p-value: 0.003 (statistically significant!)
Delta: 2.5ms (0.1%)
```

**Without override:** FAIL (statistically significant)  
**With override:** PASS (below practical threshold of 20ms)

**Dual-threshold check:**
- Override only applies if BOTH median AND tail deltas are negligible
- Prevents hiding tail regressions while allowing override on median

### 4. Multiple Testing (Documented, Not Inflated)

**Common concern:** Multiple tests -> inflated false positive rate?

**Reality:** Only 1 test uses p-values (Mann-Whitney)
- Median delta: Threshold comparison (not p-value)
- Tail latency: Threshold comparison (not p-value)
- Directionality: Informational only (not used for PASS/FAIL)

**Result:** Family-wise error rate ~= 0.05 (dominated by Mann-Whitney alone)

### 5. Direction Checks (No False Failures)

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
