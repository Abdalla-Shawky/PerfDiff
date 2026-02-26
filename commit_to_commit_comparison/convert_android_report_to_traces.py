#!/usr/bin/env python3
"""Convert Android performance report JSON into PerfDiff traces JSON format."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _coerce_numeric_runs(runs: List[Any], metric_name: str) -> Tuple[List[float | int], List[str]]:
    """Convert run values to numeric values while preserving integers when possible."""
    converted: List[float | int] = []
    warnings: List[str] = []

    for i, value in enumerate(runs):
        if isinstance(value, bool):
            warnings.append(f"{metric_name}: run[{i}] is bool and was skipped")
            continue

        if isinstance(value, (int, float)):
            converted.append(value)
            continue

        if isinstance(value, str):
            try:
                numeric = float(value)
                converted.append(int(numeric) if numeric.is_integer() else numeric)
            except ValueError:
                warnings.append(f"{metric_name}: run[{i}]='{value}' is not numeric and was skipped")
            continue

        warnings.append(
            f"{metric_name}: run[{i}] has unsupported type {type(value).__name__} and was skipped"
        )

    return converted, warnings


def convert_report_to_traces(report: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Map Android report schema into commit_to_commit comparison trace schema."""
    if not isinstance(report, dict):
        raise ValueError("Input report must be a JSON object")

    build = report.get("build")
    benchmarks = report.get("benchmarks")
    if not isinstance(build, dict):
        raise ValueError("Input report missing required 'build' object")
    if not isinstance(benchmarks, list):
        raise ValueError("Input report missing required 'benchmarks' array")

    traces: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for benchmark_index, benchmark in enumerate(benchmarks):
        if not isinstance(benchmark, dict):
            warnings.append(f"benchmarks[{benchmark_index}] is not an object and was skipped")
            continue

        metrics = benchmark.get("metrics", [])
        if not isinstance(metrics, list):
            warnings.append(f"benchmarks[{benchmark_index}].metrics is not an array and was skipped")
            continue

        for metric_index, metric in enumerate(metrics):
            if not isinstance(metric, dict):
                warnings.append(
                    f"benchmarks[{benchmark_index}].metrics[{metric_index}] is not an object and was skipped"
                )
                continue

            metric_name = metric.get("metricName")
            runs = metric.get("runs")

            if not isinstance(metric_name, str) or not metric_name.strip():
                warnings.append(
                    f"benchmarks[{benchmark_index}].metrics[{metric_index}] has invalid metricName and was skipped"
                )
                continue

            if not isinstance(runs, list):
                warnings.append(f"{metric_name}: runs is not an array and was skipped")
                continue

            measurements, run_warnings = _coerce_numeric_runs(runs, metric_name)
            warnings.extend(run_warnings)

            traces.append(
                {
                    "name": metric_name,
                    "measurements": measurements,
                }
            )

    mapped = {
        "commit": str(build.get("commit_hash", "unknown")),
        "timestamp": str(build.get("created_at", "")),
        "traces": traces,
    }
    return mapped, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Convert Android macrobenchmark performance report JSON (metrics[].runs) "
            "to commit_to_commit_comparison traces JSON."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to android *-performance-report.txt JSON file",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to output traces JSON file (e.g. baseline_traces.json)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any mapping warnings are detected",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indent for output (default: 2)",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.exists():
        print(f"Error: input file does not exist: {input_path}", file=sys.stderr)
        return 2

    try:
        with input_path.open("r", encoding="utf-8") as f:
            report = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: failed to parse JSON from {input_path}: {e}", file=sys.stderr)
        return 2

    try:
        mapped, warnings = convert_report_to_traces(report)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    if warnings:
        for warning in warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        if args.strict:
            print("Error: strict mode enabled and warnings were found", file=sys.stderr)
            return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(mapped, f, indent=args.indent)
        f.write("\n")

    print(f"Wrote {len(mapped['traces'])} traces to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
