"""
Performance Regression Detection Tool - Constants Configuration

This module centralizes all configuration constants used throughout the tool.
Each constant is documented with its purpose and acceptable value ranges.
"""

# ==============================================================================
# REGRESSION DETECTION THRESHOLDS
# ==============================================================================

# Absolute median threshold in milliseconds
# Regression is flagged if median change exceeds this value
# Used to detect regressions in slower operations (>1000ms)
MS_FLOOR = 50.0

# Relative median threshold as a fraction (0.0 - 1.0)
# Regression is flagged if median change exceeds this percentage
# 0.05 = 5% increase. Used for faster operations where absolute thresholds may be too lenient
PCT_FLOOR = 0.05

# Practical significance override thresholds
# Even if statistical tests fail (directionality, Wilcoxon), override to PASS
# if the delta is below these practical significance minimums.
# This prevents false positives on statistically significant but negligible changes.
# Example: 2.5ms delta (0.1%) with p=0.003 is statistically significant but not practically meaningful.
#
# Dynamic threshold calculation: practical_threshold = baseline * PRACTICAL_DELTA_PCT
# With min/max bounds to handle very fast and very slow operations.
#
# Examples:
#   - 100ms baseline: 1% = 1ms, but floor is 2ms → threshold = 2ms (2%)
#   - 500ms baseline: 1% = 5ms → threshold = 5ms (1%)
#   - 2000ms baseline: 1% = 20ms → threshold = 20ms (1%)
#   - 5000ms baseline: 1% = 50ms, but ceiling is 20ms → threshold = 20ms (0.4%)
MIN_PRACTICAL_DELTA_ABS_MS = 2.0  # Absolute minimum (never go below 2ms)
MAX_PRACTICAL_DELTA_ABS_MS = 20.0  # Absolute maximum (never go above 20ms)
PRACTICAL_DELTA_PCT = 0.01  # Base percentage (1% of baseline)

# Tail latency percentile for tail performance analysis (0.0 - 1.0)
# 0.90 = 90th percentile (p90). Measures worst-case performance
TAIL_QUANTILE = 0.90

# Absolute tail threshold in milliseconds
# Regression is flagged if tail latency (p90) change exceeds this value
TAIL_MS_FLOOR = 75.0

# Relative tail threshold as a fraction (0.0 - 1.0)
# Regression is flagged if tail latency (p90) change exceeds this percentage
# 0.05 = 5% increase at the tail
TAIL_PCT_FLOOR = 0.05


# ==============================================================================
# DIRECTIONALITY CHECK
# ==============================================================================

# Maximum allowed fraction of "slower" runs (0.0 - 1.0)
# If more than this fraction of target runs are slower than baseline median,
# it indicates a consistent performance degradation
# 0.70 = 70% of runs can be slower before flagging as regression
DIRECTIONALITY = 0.70


# ==============================================================================
# STATISTICAL TEST PARAMETERS
# ==============================================================================

# Enable/disable Wilcoxon signed-rank test
# This non-parametric test detects distributional shifts
USE_WILCOXON = True

# Significance level (alpha) for Wilcoxon test (0.0 - 1.0)
# 0.05 = 5% significance level (95% confidence)
# Lower values make the test more conservative
WILCOXON_ALPHA = 0.05

# Confidence level for bootstrap confidence intervals (0.0 - 1.0)
# 0.95 = 95% confidence interval
# Higher values produce wider intervals (more conservative)
BOOTSTRAP_CONFIDENCE = 0.95

# Number of bootstrap resampling iterations
# More iterations = more accurate but slower
# 5000 is a good balance between accuracy and performance
BOOTSTRAP_N = 5000

# Random seed for reproducibility
# Set to 0 or any integer for deterministic results
# Set to None for non-deterministic (different results each run)
SEED = 0


# ==============================================================================
# EQUIVALENCE TEST PARAMETERS
# ==============================================================================

# Equivalence margin in milliseconds for equivalence testing
# If the confidence interval falls within [-margin, +margin],
# the performance is considered equivalent (no significant change)
# 30ms is typically imperceptible to users
EQUIVALENCE_MARGIN_MS = 30.0


# ==============================================================================
# DATA QUALITY ASSESSMENT - SAMPLE SIZE THRESHOLDS
# ==============================================================================

# Minimum sample size before flagging as "very few samples" issue
# n < 5 is insufficient for reliable statistical analysis
MIN_SAMPLE_CRITICAL = 5

# Minimum sample size before flagging as "small sample" warning
# n < 10 has limited statistical power
MIN_SAMPLE_WARNING = 10


# ==============================================================================
# DATA QUALITY ASSESSMENT - VARIABILITY THRESHOLDS
# ==============================================================================

# Coefficient of variation (CV) percentage thresholds
# CV = (std_dev / mean) * 100

# High variability threshold (%)
# CV > 20% indicates inconsistent performance (issue)
CV_HIGH_THRESHOLD = 20

# Moderate variability threshold (%)
# CV > 10% indicates some inconsistency (warning)
CV_MODERATE_THRESHOLD = 10

# Low variability threshold (%)
# CV > 5% indicates minor inconsistency (warning)
CV_SOME_THRESHOLD = 5


# ==============================================================================
# DATA QUALITY ASSESSMENT - OUTLIER DETECTION
# ==============================================================================

# IQR multiplier for outlier detection using Tukey's method
# Outliers are values outside [Q1 - k*IQR, Q3 + k*IQR]
# 1.5 is the standard multiplier (classic definition)
IQR_OUTLIER_MULTIPLIER = 1.5

# Outlier percentage threshold for flagging as issue (%)
# If > 20% of samples are outliers, data quality is concerning
OUTLIER_PCT_ISSUE = 20


# ==============================================================================
# DATA QUALITY ASSESSMENT - SCORING SYSTEM
# ==============================================================================

# Initial quality score (before applying penalties)
# Starts at 100 (perfect), penalties are subtracted
INITIAL_QUALITY_SCORE = 100

# Penalty for critical sample size issue (n < 5)
PENALTY_SAMPLE_CRITICAL = 30

# Penalty for small sample warning (n < 10)
PENALTY_SAMPLE_WARNING = 10

# Penalty for high variability (CV > 20%)
PENALTY_CV_HIGH = 25

# Penalty for moderate variability (CV > 10%)
PENALTY_CV_MODERATE = 10

# Penalty for some variability (CV > 5%)
PENALTY_CV_SOME = 5

# Penalty for high outlier percentage (> 20%)
PENALTY_OUTLIER_ISSUE = 20

# Penalty for any detected outliers
PENALTY_OUTLIER_WARNING = 5


# ==============================================================================
# DATA QUALITY ASSESSMENT - VERDICT THRESHOLDS
# ==============================================================================

# Score threshold for "Excellent" verdict
# Score >= 90 indicates high-quality data
QUALITY_EXCELLENT_THRESHOLD = 90

# Score threshold for "Good" verdict
# Score >= 75 indicates acceptable data quality
QUALITY_GOOD_THRESHOLD = 75

# Score threshold for "Fair" verdict
# Score >= 60 indicates marginal data quality
QUALITY_FAIR_THRESHOLD = 60

# Scores < 60 result in "Poor" verdict


# ==============================================================================
# OVERALL CONFIDENCE THRESHOLDS
# ==============================================================================

# Overall quality score threshold for "High confidence"
# Average score >= 85 across all metrics
OVERALL_HIGH_CONFIDENCE = 85

# Overall quality score threshold for "Moderate confidence"
# Average score >= 70 across all metrics
OVERALL_MODERATE_CONFIDENCE = 70

# Scores < 70 result in "Low confidence"


# ==============================================================================
# DATA QUALITY GATES FOR REGRESSION DETECTION
# ==============================================================================

# Enable strict quality gates to prevent false positives/negatives
# When enabled, regression detection is blocked if data quality is too poor
ENABLE_QUALITY_GATES = True

# Maximum coefficient of variation (%) allowed for regression detection
# If CV exceeds this, regression check will return INCONCLUSIVE
# Set to 15% - data with CV > 15% is too noisy for reliable conclusions
# Your 28% same-commit variance had CV of 17-18%, which would be rejected
MAX_CV_FOR_REGRESSION_CHECK = 15.0

# Minimum quality score required for regression detection
# If quality score < this threshold, regression check will return INCONCLUSIVE
# Set to 70 - ensures at least "Fair" quality before making conclusions
MIN_QUALITY_SCORE_FOR_REGRESSION = 70

# CV-based threshold multiplier
# When CV is high (but below MAX_CV), increase detection thresholds proportionally
# This makes the test more conservative when variance is elevated
# Formula: effective_threshold = base_threshold * (1 + CV_THRESHOLD_MULTIPLIER * CV/100)
# Example: With CV=10%, MS_FLOOR=50ms, multiplier=0.5:
#   effective_threshold = 50 * (1 + 0.5 * 0.10) = 52.5ms
CV_THRESHOLD_MULTIPLIER = 0.5

# Minimum sample size required for regression detection
# If n < this value, regression check will return INCONCLUSIVE
# Set to 10 - fewer samples have insufficient statistical power
MIN_SAMPLES_FOR_REGRESSION = 10


# ==============================================================================
# QUANTILE DEFINITIONS
# ==============================================================================

# First quartile (Q1) - 25th percentile
# Used for IQR calculation: IQR = Q3 - Q1
Q1_QUANTILE = 0.25

# Third quartile (Q3) - 75th percentile
# Used for IQR calculation: IQR = Q3 - Q1
Q3_QUANTILE = 0.75

# 90th percentile for tail latency analysis
# Same as TAIL_QUANTILE, defined here for consistency
P90_QUANTILE = 0.90


# ==============================================================================
# MATHEMATICAL CONSTANTS
# ==============================================================================

# Conversion factor from fraction to percentage
# Multiply by 100 to convert 0.05 -> 5%
PCT_CONVERSION_FACTOR = 100

# Divisor for two-sided statistical tests
# Divide alpha by 2 for two-tailed tests
TWO_SIDED_TEST_DIVISOR = 2


# ==============================================================================
# UI/HTML REPORT CONSTANTS
# ==============================================================================

# Maximum width for progress bars in HTML report (%)
BAR_MAX_WIDTH_PCT = 100.0

# Chart.js CDN version for interactive charts
CHARTJS_CDN_VERSION = "4.4.1"

# Chart.js CDN URL with SRI hash for security
CHARTJS_CDN_URL = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"

# Chart.js CDN SRI hash for integrity verification
CHARTJS_CDN_SRI = "sha384-5PiDZVYBsJ4dB1mKiMnRYqHdkf7VUYauvBZ0LCJWi7YwJKHbPH8JLH0P1WXwTQ6p"

# Animation durations in milliseconds
ANIMATION_DURATION_FAST = 200      # Quick transitions (hover effects)
ANIMATION_DURATION_NORMAL = 300    # Standard transitions (section expand)
ANIMATION_DURATION_SLOW = 500      # Slow transitions (scroll animations)

# Chart color palette
CHART_COLOR_BASELINE = "#1976d2"            # Blue - baseline measurements
CHART_COLOR_TARGET_IMPROVEMENT = "#2e7d32"  # Green - performance improvement
CHART_COLOR_TARGET_REGRESSION = "#d32f2f"   # Red - performance regression
CHART_COLOR_NEUTRAL = "#f57c00"             # Orange - neutral/warning

# Dark mode colors
DARK_BG_PRIMARY = "#1a1a1a"       # Main background
DARK_BG_SECONDARY = "#2d2d2d"     # Cards and sections
DARK_BG_TERTIARY = "#3a3a3a"      # Nested elements
DARK_TEXT_PRIMARY = "#e0e0e0"     # Main text
DARK_TEXT_SECONDARY = "#a0a0a0"   # Secondary text
DARK_BORDER = "#404040"           # Border color

# Light mode colors (default)
LIGHT_BG_PRIMARY = "#f8f9fa"      # Main background
LIGHT_BG_SECONDARY = "#ffffff"    # Cards and sections
LIGHT_BG_TERTIARY = "#f0f0f0"     # Nested elements
LIGHT_TEXT_PRIMARY = "#333333"    # Main text
LIGHT_TEXT_SECONDARY = "#666666"  # Secondary text
LIGHT_BORDER = "#e5e5e5"          # Border color


# ==============================================================================
# MAIN BRANCH HEALTH MONITORING (main_health.py)
# ==============================================================================

# Control Chart Parameters
# Baseline window size for computing median and MAD
# Uses last N points (excluding latest) as baseline for control limits
HEALTH_WINDOW = 10

# Number of robust standard deviations (sigma) for control chart bounds
# control_limit = baseline_median ± k * robust_sigma
# 4.0 is conservative (wider bounds, fewer false positives)
HEALTH_CONTROL_K = 4.0

# Minimum MAD value to prevent division by zero
# When data has zero variance, this floor prevents numerical issues
HEALTH_MIN_MAD = 1e-9

# Default direction for control chart monitoring
# "regression" = only alert on increases (performance degradation)
# "both" = alert on increases or decreases (any significant change)
HEALTH_DIRECTION = "regression"

# EWMA (Exponentially Weighted Moving Average) Parameters
# Smoothing parameter for EWMA (0 < alpha <= 1)
# Higher alpha = more weight on recent observations (more responsive)
# Lower alpha = more smoothing (less responsive to noise)
# 0.25 is a good balance for detecting sustained trends
HEALTH_EWMA_ALPHA = 0.25

# Number of robust standard deviations for EWMA bounds
# 3.0 is more sensitive than control chart (detects smaller sustained shifts)
HEALTH_EWMA_K = 3.0

# Step-Fit (Changepoint Detection) Parameters
# Number of recent points to scan for changepoint
# Set to None to automatically scan the entire series (recommended for finding exact commit)
# Set to a number (e.g., 120) to scan only the last N points (faster for large datasets)
HEALTH_STEP_SCAN_BACK = None  # None = scan entire series dynamically

# Minimum segment size on each side of changepoint
# Ensures sufficient data before/after split for reliable median estimation
HEALTH_STEP_MIN_SEGMENT = 10

# Minimum score threshold for changepoint detection
# score = |median_after - median_before| / robust_sigma
# 4.0 is conservative (avoids false positives in noisy data)
HEALTH_STEP_SCORE_K = 4.0

# Percentage-based thresholds for practical significance
# These provide dual-threshold detection: statistical (sigma-based) OR percentage-based
# Useful for detecting practically significant changes in high-variability data
# Set to None to disable percentage-based detection

# Step change percentage threshold
# Triggers alert if change ≥ this percentage, even if statistical score is low
# Example: 20.0 means ≥20% performance degradation triggers alert
HEALTH_STEP_PCT_THRESHOLD = 20.0

# EWMA drift percentage threshold
# Triggers alert if EWMA drifts ≥ this percentage from baseline median
# Example: 15.0 means ≥15% drift from baseline triggers alert
HEALTH_EWMA_PCT_THRESHOLD = 15.0

# Robust Statistics Constants
# Scaling factor for converting MAD to robust standard deviation
# For normally distributed data, robust_sigma = 1.4826 * MAD
# This constant makes MAD comparable to standard deviation
MAD_TO_SIGMA_SCALE = 1.4826

# Outlier Detection Parameters
# Enable/disable outlier detection and trimmed mean calculation
# Set to False to disable outlier detection, visual marking, and quality penalties
# When disabled, trimmed mean = regular mean (no outlier exclusion)
HEALTH_OUTLIER_DETECTION_ENABLED = False

# Sigma multiplier for rolling MAD outlier detection
# 3.5 is more lenient than control chart (k=4.0) to avoid over-flagging
# Used for visual marking and quality scoring, NOT for exclusion
HEALTH_OUTLIER_K = 3.5


# ==============================================================================
# EXIT CODES
# ==============================================================================

# Exit code for successful execution (no regression detected)
EXIT_SUCCESS = 0

# Exit code for regression detected
EXIT_FAILURE = 1

# Exit code for parsing/input errors
EXIT_PARSE_ERROR = 2
