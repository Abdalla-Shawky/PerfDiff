#!/bin/bash
#
# Interleaved Performance Testing Script
#
# This script runs baseline and change measurements in an interleaved fashion
# to minimize systematic bias from thermal throttling, background load, etc.
#
# Usage:
#   ./interleaved_test_example.sh <baseline_commit> <change_commit> <num_pairs>
#
# Example:
#   ./interleaved_test_example.sh abc123 def456 15
#

set -e

BASELINE_COMMIT=${1:-HEAD}
CHANGE_COMMIT=${2:-HEAD}
NUM_PAIRS=${3:-15}

echo "╔════════════════════════════════════════════════════════════╗"
echo "║       Interleaved Performance Testing                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Baseline commit: $BASELINE_COMMIT"
echo "Change commit:   $CHANGE_COMMIT"
echo "Number of pairs: $NUM_PAIRS"
echo ""

# Function to run a single performance measurement
# REPLACE THIS with your actual performance test command
run_perf_test() {
    local commit=$1
    local iteration=$2

    # Example: Android app startup time
    # REPLACE with your actual test command
    # adb shell am start-activity -W -n com.example.app/.MainActivity | \
    #     grep "TotalTime" | awk '{print $2}'

    # For demonstration, simulate measurement with some noise
    # DELETE THIS and use your real test
    echo "scale=2; 2000 + $RANDOM % 500" | bc
}

# Arrays to store results
declare -a BASELINE_RESULTS
declare -a CHANGE_RESULTS

echo "Running interleaved measurements..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Warmup phase (optional but recommended)
echo "Warmup (discarding first 3 measurements)..."
for i in {1..3}; do
    run_perf_test "$BASELINE_COMMIT" "warmup-$i" > /dev/null
    sleep 1
done
echo "✓ Warmup complete"
echo ""

# Interleaved measurement loop
for i in $(seq 1 $NUM_PAIRS); do
    printf "Pair %2d/%2d: " "$i" "$NUM_PAIRS"

    # Randomly alternate order to avoid position bias
    if [ $((RANDOM % 2)) -eq 0 ]; then
        # Baseline first
        baseline_val=$(run_perf_test "$BASELINE_COMMIT" "$i")
        sleep 1  # Small delay between measurements
        change_val=$(run_perf_test "$CHANGE_COMMIT" "$i")
        order="B→C"
    else
        # Change first
        change_val=$(run_perf_test "$CHANGE_COMMIT" "$i")
        sleep 1
        baseline_val=$(run_perf_test "$BASELINE_COMMIT" "$i")
        order="C→B"
    fi

    BASELINE_RESULTS+=("$baseline_val")
    CHANGE_RESULTS+=("$change_val")

    delta=$(echo "scale=2; $change_val - $baseline_val" | bc)
    printf "Baseline=%6.1fms, Change=%6.1fms, Delta=%+7.1fms [%s]\n" \
        "$baseline_val" "$change_val" "$delta" "$order"

    # Optional: Add cooldown every 5 pairs to prevent thermal buildup
    if [ $((i % 5)) -eq 0 ] && [ $i -lt $NUM_PAIRS ]; then
        echo "   → Cooldown (5s)..."
        sleep 5
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Measurements complete!"
echo ""

# Format results as JSON arrays
BASELINE_JSON=$(IFS=,; echo "${BASELINE_RESULTS[*]}")
CHANGE_JSON=$(IFS=,; echo "${CHANGE_RESULTS[*]}")

# Calculate quick stats
BASELINE_MEDIAN=$(echo "${BASELINE_RESULTS[@]}" | tr ' ' '\n' | sort -n | awk '{a[NR]=$1} END{print (NR%2==1)?a[(NR+1)/2]:(a[NR/2]+a[NR/2+1])/2}')
CHANGE_MEDIAN=$(echo "${CHANGE_RESULTS[@]}" | tr ' ' '\n' | sort -n | awk '{a[NR]=$1} END{print (NR%2==1)?a[(NR+1)/2]:(a[NR/2]+a[NR/2+1])/2}')
DELTA=$(echo "scale=2; $CHANGE_MEDIAN - $BASELINE_MEDIAN" | bc)
PCT=$(echo "scale=1; ($DELTA / $BASELINE_MEDIAN) * 100" | bc)

echo "Quick Statistics:"
echo "  Baseline median: ${BASELINE_MEDIAN}ms"
echo "  Change median:   ${CHANGE_MEDIAN}ms"
echo "  Delta:           ${DELTA}ms (${PCT}%)"
echo ""

# Generate HTML report
OUTPUT_FILE="interleaved_report_$(date +%Y%m%d_%H%M%S).html"

python3 perf_html_report.py \
    --baseline "[$BASELINE_JSON]" \
    --change "[$CHANGE_JSON]" \
    --out "$OUTPUT_FILE" \
    --title "Interleaved Performance Test: $BASELINE_COMMIT vs $CHANGE_COMMIT"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ HTML report generated: $OUTPUT_FILE"
echo ""

# Provide interpretation
if [ "$BASELINE_COMMIT" = "$CHANGE_COMMIT" ]; then
    echo "⚠️  SAME COMMIT TEST - Checking measurement stability"
    echo ""
    if (( $(echo "$PCT < -3 || $PCT > 3" | bc -l) )); then
        echo "❌ WARNING: >3% difference on same commit!"
        echo "   Your measurements are UNSTABLE. Possible causes:"
        echo "   - Thermal throttling"
        echo "   - Background processes"
        echo "   - Insufficient warmup"
        echo "   - Need more controlled environment"
    else
        echo "✓ Good! <3% difference indicates stable measurements"
    fi
fi

echo ""
echo "Open the report: open $OUTPUT_FILE"
