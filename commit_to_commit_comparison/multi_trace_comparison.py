"""Multi-trace performance comparison system.

This module provides functionality to compare multiple performance traces
between baseline and target commits, generating HTML reports for analysis.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from .commit_to_commit_comparison import gate_regression, GateResult


@dataclass
class TraceComparison:
    """Single trace comparison result."""
    name: str
    baseline_data: List[float]
    target_data: List[float]
    gate_result: GateResult

    def __post_init__(self):
        """Convert data to lists if they're numpy arrays for JSON serialization."""
        if isinstance(self.baseline_data, np.ndarray):
            self.baseline_data = self.baseline_data.tolist()
        if isinstance(self.target_data, np.ndarray):
            self.target_data = self.target_data.tolist()


@dataclass
class MultiTraceResult:
    """Results from comparing multiple traces."""
    comparisons: List[TraceComparison]
    warnings: List[str]
    baseline_file: str
    target_file: str
    timestamp: str

    def get_summary_stats(self) -> Dict[str, int]:
        """Calculate summary statistics for all comparisons."""
        stats = {
            'total': len(self.comparisons),
            'pass': 0,
            'fail': 0,
            'no_change': 0,
            'inconclusive': 0
        }

        for comparison in self.comparisons:
            result = comparison.gate_result
            if result.inconclusive:
                stats['inconclusive'] += 1
            elif result.no_change:
                stats['no_change'] += 1
            elif result.passed:
                stats['pass'] += 1
            else:
                stats['fail'] += 1

        return stats


def load_traces_from_json(json_path: str) -> Tuple[Dict[str, np.ndarray], dict]:
    """Load traces from JSON file.

    Expected format:
    {
      "commit": "abc123",
      "timestamp": "2026-01-27T10:00:00Z",
      "traces": [
        {"name": "api_login", "measurements": [100.0, 102.0, ...]},
        {"name": "ui_render", "measurements": [250.0, 255.0, ...]}
      ]
    }

    Args:
        json_path: Path to JSON file

    Returns:
        Tuple of (traces dict mapping name to np.ndarray, metadata dict)

    Raises:
        FileNotFoundError: If JSON file doesn't exist
        json.JSONDecodeError: If JSON is invalid
        KeyError: If required fields are missing
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    with open(path, 'r') as f:
        data = json.load(f)

    if 'traces' not in data:
        raise KeyError(f"JSON file must contain 'traces' field: {json_path}")

    traces = {}
    metadata = {
        'commit': data.get('commit', 'unknown'),
        'timestamp': data.get('timestamp', ''),
        'file': str(path)
    }

    for trace in data['traces']:
        if 'name' not in trace:
            continue  # Skip traces without names
        if 'measurements' not in trace:
            continue  # Skip traces without measurements

        name = trace['name']
        measurements = trace['measurements']

        if not measurements:
            continue  # Skip empty measurements

        traces[name] = np.array(measurements, dtype=float)

    return traces, metadata


def compare_traces(baseline_json: str, target_json: str) -> MultiTraceResult:
    """Compare all traces between baseline and target files.

    Steps:
    1. Load both JSON files
    2. Match traces by name
    3. Run gate_regression() on each matched pair
    4. Collect warnings for unmatched traces
    5. Return MultiTraceResult

    Args:
        baseline_json: Path to baseline JSON file
        target_json: Path to target JSON file

    Returns:
        MultiTraceResult containing all comparisons and warnings
    """
    # Load traces from both files
    baseline_traces, baseline_meta = load_traces_from_json(baseline_json)
    target_traces, target_meta = load_traces_from_json(target_json)

    comparisons = []
    warnings = []

    # Find matched traces
    baseline_names = set(baseline_traces.keys())
    target_names = set(target_traces.keys())
    matched_names = baseline_names & target_names

    # Warn about unmatched traces
    baseline_only = baseline_names - target_names
    target_only = target_names - baseline_names

    if baseline_only:
        warnings.append(
            f"⚠️ {len(baseline_only)} trace(s) only in baseline: {', '.join(sorted(baseline_only))}"
        )

    if target_only:
        warnings.append(
            f"⚠️ {len(target_only)} trace(s) only in target: {', '.join(sorted(target_only))}"
        )

    # Compare matched traces
    for name in sorted(matched_names):
        baseline_data = baseline_traces[name]
        target_data = target_traces[name]

        # Check if arrays have the same length
        if len(baseline_data) != len(target_data):
            warnings.append(
                f"⚠️ Skipping trace '{name}': mismatched lengths "
                f"(baseline: {len(baseline_data)}, target: {len(target_data)})"
            )
            continue

        # Run regression check
        try:
            result = gate_regression(baseline_data, target_data)
            comparisons.append(TraceComparison(
                name=name,
                baseline_data=baseline_data.tolist(),
                target_data=target_data.tolist(),
                gate_result=result
            ))
        except Exception as e:
            warnings.append(f"⚠️ Error comparing trace '{name}': {str(e)}")

    return MultiTraceResult(
        comparisons=comparisons,
        warnings=warnings,
        baseline_file=baseline_meta['file'],
        target_file=target_meta['file'],
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    )


def generate_comparison_html(result: MultiTraceResult, output_path: str = None) -> str:
    """Generate table view HTML showing all trace comparisons.

    Args:
        result: MultiTraceResult from compare_traces()
        output_path: Optional path to write HTML file

    Returns:
        HTML string
    """
    from .comparison_html_template import render_comparison_template

    html = render_comparison_template(result)

    if output_path:
        Path(output_path).write_text(html)

    return html


def generate_trace_detail_html(
    trace_name: str,
    comparison: TraceComparison,
    prev_trace: str = None,
    next_trace: str = None,
    comparison_page_url: str = "index.html",
    output_path: str = None
) -> str:
    """Generate detailed report HTML for a single trace.

    Args:
        trace_name: Name of the trace
        comparison: TraceComparison object
        prev_trace: Name of previous trace (for navigation)
        next_trace: Name of next trace (for navigation)
        comparison_page_url: URL to comparison page
        output_path: Optional path to write HTML file

    Returns:
        HTML string
    """
    from .trace_detail_html_template import render_trace_detail_template

    html = render_trace_detail_template(
        trace_name=trace_name,
        baseline=np.array(comparison.baseline_data),
        target=np.array(comparison.target_data),
        result=comparison.gate_result,
        prev_trace=prev_trace,
        next_trace=next_trace,
        comparison_page_url=comparison_page_url
    )

    if output_path:
        Path(output_path).write_text(html)

    return html


def main():
    """CLI entry point for multi-trace comparison."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Compare multiple performance traces between baseline and target commits'
    )
    parser.add_argument('baseline', help='Baseline JSON file path')
    parser.add_argument('target', help='Target JSON file path')
    parser.add_argument('--output-dir', default='output', help='Output directory (default: output)')

    args = parser.parse_args()

    # Run comparison
    print(f"📊 Comparing traces...")
    print(f"  Baseline: {args.baseline}")
    print(f"  Target: {args.target}")
    print()

    result = compare_traces(args.baseline, args.target)

    # Print summary
    stats = result.get_summary_stats()
    print(f"✅ Comparison complete!")
    print(f"  Total traces: {stats['total']}")
    print(f"  PASS: {stats['pass']}")
    print(f"  FAIL: {stats['fail']}")
    print(f"  NO CHANGE: {stats['no_change']}")
    print(f"  INCONCLUSIVE: {stats['inconclusive']}")

    if result.warnings:
        print(f"\n⚠️  {len(result.warnings)} warning(s):")
        for warning in result.warnings:
            print(f"  {warning}")

    print(f"\n📝 Generating HTML reports...")

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    # Generate comparison page
    comparison_html = generate_comparison_html(result)
    (output_dir / 'index.html').write_text(comparison_html)
    print(f"  ✓ index.html (Performance Comparison)")

    # Generate detail pages for each trace
    for i, comparison in enumerate(result.comparisons):
        prev_trace = result.comparisons[i-1].name if i > 0 else None
        next_trace = result.comparisons[i+1].name if i < len(result.comparisons)-1 else None

        detail_html = generate_trace_detail_html(
            comparison.name,
            comparison,
            prev_trace,
            next_trace
        )
        (output_dir / f'{comparison.name}.html').write_text(detail_html)
        print(f"  ✓ {comparison.name}.html")

    print(f"\n🎉 Done! Open {output_dir}/index.html to view the report")


if __name__ == '__main__':
    main()
