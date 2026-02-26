#!/bin/bash
#
# Performance Regression Comparison Script
# Usage: ./run_comparison.sh <baseline_json> <target_json> <output_dir>
#

set -e  # Exit on error

# Check arguments
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <baseline_json> <target_json> <output_dir>"
    echo ""
    echo "Example:"
    echo "  $0 commit2commit/mock_data/baseline_traces.json \\"
    echo "     commit2commit/mock_data/target_traces.json \\"
    echo "     commit2commit/test_output"
    exit 1
fi

BASELINE_JSON="$1"
TARGET_JSON="$2"
OUTPUT_DIR="$3"

# Validate input files exist
if [ ! -f "$BASELINE_JSON" ]; then
    echo "Error: Baseline file not found: $BASELINE_JSON"
    exit 1
fi

if [ ! -f "$TARGET_JSON" ]; then
    echo "Error: Target file not found: $TARGET_JSON"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

echo "======================================"
echo "Performance Regression Comparison"
echo "======================================"
echo "Baseline: $BASELINE_JSON"
echo "Target:   $TARGET_JSON"
echo "Output:   $OUTPUT_DIR"
echo ""

# Path to the Python source (in PerfDiff directory)
SCRIPT_DIR="/Users/abdalla.ahmed/Documents/PerfDiff"

# Change to PerfDiff directory to run as module
cd "$SCRIPT_DIR"

# Run the multi-trace comparison as a Python module
python3 -m commit2commit.analyzer \
    "$OLDPWD/$BASELINE_JSON" \
    "$OLDPWD/$TARGET_JSON" \
    --output-dir "$OLDPWD/$OUTPUT_DIR"

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ PASS: No performance regressions detected"
    echo ""
    echo "View the report:"
    echo "  open $OUTPUT_DIR/index.html"
else
    echo "❌ FAIL: Performance regression detected (exit code: $EXIT_CODE)"
    echo ""
    echo "View the report for details:"
    echo "  open $OUTPUT_DIR/index.html"
fi

exit $EXIT_CODE
