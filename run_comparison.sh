#!/bin/bash
# Multi-Trace Performance Comparison Runner
# Usage: ./run_comparison.sh baseline.json target.json [output_dir]

if [ $# -lt 2 ]; then
    echo "Usage: $0 <baseline.json> <target.json> [output_dir]"
    echo ""
    echo "Example:"
    echo "  $0 commit_to_commit_comparison/mock_data/baseline_traces.json \\"
    echo "     commit_to_commit_comparison/mock_data/target_traces.json \\"
    echo "     reports"
    exit 1
fi

BASELINE="$1"
TARGET="$2"
OUTPUT_DIR="${3:-output}"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory to ensure correct Python path
cd "$SCRIPT_DIR"

# Run the comparison
python3 -m commit_to_commit_comparison.multi_trace_comparison \
    "$BASELINE" \
    "$TARGET" \
    --output-dir "$OUTPUT_DIR"

# Check if successful
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Reports generated successfully!"
    echo "📂 Output directory: $OUTPUT_DIR"
    echo "🌐 Open $OUTPUT_DIR/index.html to view"
else
    echo ""
    echo "❌ Error generating reports"
    exit 1
fi
