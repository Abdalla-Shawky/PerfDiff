#!/usr/bin/env python3
"""
Performance Traces Dashboard - Flask Backend
Integrates with BigQuery and main_health algorithm
"""

from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS

try:
    from google.cloud import bigquery
    BQ_AVAILABLE = True
except Exception as e:
    print(f"⚠️  BigQuery import failed: {e}")
    print("Running in mock mode only")
    bigquery = None
    BQ_AVAILABLE = False

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from main_health import assess_main_health
except ImportError:
    print("Warning: main_health module not found. Using mock analysis.")
    assess_main_health = None

app = Flask(__name__)
CORS(app)

# Configuration
PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'your-project-id')
DATASET_ID = os.getenv('BQ_DATASET_ID', 'performance')
TABLE_ID = os.getenv('BQ_TABLE_ID', 'benchmark_results')
GITHUB_REPO_URL = os.getenv('GITHUB_REPO_URL', 'https://github.com/your-org/your-repo')

# Initialize BigQuery client
bq_client = None
if BQ_AVAILABLE:
    try:
        bq_client = bigquery.Client(project=PROJECT_ID)
        print(f"✅ BigQuery client initialized for project: {PROJECT_ID}")
    except Exception as e:
        print(f"⚠️  BigQuery client initialization failed: {e}")
        print("Running in mock mode - using generated data")
else:
    print("BigQuery not available - running in mock mode")


def _convert_medians_to_bq_format(
    medians: List[float],
    platform: str,
    trace_name: str,
    start_date: str,
    end_date: str
) -> List[Dict[str, Any]]:
    """
    Convert simplified median array to BigQuery format.

    Args:
        medians: List of median values (e.g., [250, 252, 351, 353])
        platform: Platform name ('ios' or 'android')
        trace_name: Trace name
        start_date: Start date string
        end_date: End date string

    Returns:
        List of BigQuery-formatted records
    """
    from datetime import timedelta

    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    total_days = (end - start).days

    # Calculate date spacing to distribute medians across date range
    if len(medians) > 1:
        day_step = max(1, total_days // (len(medians) - 1))
    else:
        day_step = 1

    records = []
    device_model = 'iPhone 14 Pro' if platform.lower() == 'ios' else 'Pixel 7'
    device_os = f'{platform} {"17" if platform.lower() == "ios" else "14"}'

    for i, median_value in enumerate(medians):
        # Generate date within range
        current_date = start + timedelta(days=min(i * day_step, total_days))

        # Generate runs around median (10 values)
        # Create realistic variance: ±5% around median
        import random
        variance = median_value * 0.05
        runs = []
        for _ in range(10):
            value = median_value + random.uniform(-variance, variance)
            runs.append(round(value, 2))
        runs.sort()

        # Ensure median is accurate
        actual_median = runs[len(runs) // 2]

        record = {
            'benchmarks': [{
                'className': 'PerformanceBenchmark',
                'name': f'{trace_name}_benchmark',
                'metrics': {
                    'runs': runs,
                    'median': actual_median,
                    'minimum': runs[0],
                    'maximum': runs[-1],
                    'metricName': trace_name
                }
            }],
            'build': {
                'model': device_model,
                'id': 1000 + i,
                'app_version': f'1.0.{i}',
                'commit_hash': f'mock{i:04d}',
                'device': device_os,
                'created_at': current_date.isoformat() + 'Z',
                'branch': 'main'
            }
        }
        records.append(record)

    return records


def load_mock_data_from_file(platform: str, start_date: str, end_date: str, trace_name: str) -> List[Dict[str, Any]]:
    """
    Load mock data from local JSON file.

    Supports two formats:
    1. Simplified format (array of medians): [250, 252, 351, 353, ...]
    2. BigQuery format (array of objects): [{benchmarks: [...], build: {...}}, ...]

    The simplified format is automatically converted to BigQuery format.
    """
    mock_file_path = os.path.join(os.path.dirname(__file__), 'mock_data.json')

    try:
        if os.path.exists(mock_file_path):
            with open(mock_file_path, 'r') as f:
                data = json.load(f)

            # Get data for specific trace and platform
            if 'traces' in data and trace_name in data['traces']:
                platform_key = platform.lower()
                if platform_key in data['traces'][trace_name]:
                    trace_data = data['traces'][trace_name][platform_key]

                    # Check if data exists
                    if trace_data:
                        # Detect format: simplified (array of numbers) or BigQuery (array of objects)
                        is_simplified_format = (
                            isinstance(trace_data, list) and
                            len(trace_data) > 0 and
                            isinstance(trace_data[0], (int, float))
                        )

                        if is_simplified_format:
                            # Convert simplified format to BigQuery format
                            print(f"✅ Loaded {len(trace_data)} medians from mock_data.json for {trace_name}/{platform} (simplified format)")
                            trace_data = _convert_medians_to_bq_format(
                                trace_data, platform, trace_name, start_date, end_date
                            )
                        else:
                            print(f"✅ Loaded {len(trace_data)} records from mock_data.json for {trace_name}/{platform} (BigQuery format)")

                        # Filter by date range (compare dates only, not times)
                        start = datetime.fromisoformat(start_date).date()
                        end = datetime.fromisoformat(end_date).date()

                        filtered_data = []
                        for record in trace_data:
                            record_date = datetime.fromisoformat(record['build']['created_at'].replace('Z', '+00:00')).date()
                            if start <= record_date <= end:
                                filtered_data.append(record)

                        if filtered_data:
                            print(f"✅ Filtered to {len(filtered_data)} records in date range {start_date} to {end_date}")
                            return filtered_data
                        else:
                            print(f"⚠️  No data in date range, falling back to generated data")
    except Exception as e:
        print(f"⚠️  Error reading mock_data.json: {e}")
        import traceback
        traceback.print_exc()

    return None


def query_bigquery(platform: str, start_date: str, end_date: str, trace_name: str) -> List[Dict[str, Any]]:
    """Query BigQuery for performance data."""

    if not bq_client:
        # Try to load from local file first
        file_data = load_mock_data_from_file(platform, start_date, end_date, trace_name)
        if file_data:
            return file_data

        # Fall back to generated mock data
        print("⚠️  Using auto-generated mock data")
        return generate_mock_data(platform, start_date, end_date, trace_name)

    query = f"""
    SELECT
        benchmarks,
        build
    FROM
        `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    WHERE
        DATE(build.created_at) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
        AND LOWER(build.device) LIKE LOWER('%{platform}%')
        AND EXISTS (
            SELECT 1 FROM UNNEST(benchmarks) AS b
            WHERE b.metrics.metricName = '{trace_name}'
        )
    ORDER BY
        build.created_at ASC
    """

    try:
        query_job = bq_client.query(query)
        results = []

        for row in query_job:
            results.append({
                'benchmarks': json.loads(row.benchmarks) if isinstance(row.benchmarks, str) else row.benchmarks,
                'build': json.loads(row.build) if isinstance(row.build, str) else row.build
            })

        return results

    except Exception as e:
        print(f"❌ BigQuery query failed: {e}")
        # Fallback to mock data
        return generate_mock_data(platform, start_date, end_date, trace_name)


def generate_mock_data(platform: str, start_date: str, end_date: str, trace_name: str) -> List[Dict[str, Any]]:
    """Generate mock data for testing."""
    import random
    from datetime import datetime, timedelta

    data = []
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    days = (end - start).days + 1

    for i in range(days):
        current_date = start + timedelta(days=i)

        # Simulate clear regression after day 10
        has_regression = i >= 10
        base_value = 250 if platform.lower() == 'ios' else 300

        # More dramatic regression for visibility
        if has_regression:
            # 40% increase for clear regression
            regression_multiplier = 1.4
        else:
            regression_multiplier = 1.0

        # Generate runs
        metric_base = base_value * regression_multiplier
        runs = []
        for _ in range(10):
            # Tighter variance for cleaner signal
            value = metric_base + random.uniform(-10, 10)
            runs.append(round(value, 2))

        runs.sort()
        median = runs[len(runs) // 2]

        data.append({
            'benchmarks': [{
                'className': 'PerformanceBenchmark',
                'name': f'{trace_name}_benchmark',
                'metrics': {
                    'runs': runs,
                    'median': median,
                    'minimum': runs[0],
                    'maximum': runs[-1],
                    'metricName': trace_name
                }
            }],
            'build': {
                'model': 'iPhone 14 Pro' if platform.lower() == 'ios' else 'Pixel 7',
                'id': 1000 + i,
                'app_version': f'1.0.{i}',
                'commit_hash': f'abc{i:04d}',
                'device': f'{platform} {"17" if platform.lower() == "ios" else "14"}',
                'created_at': current_date.isoformat() + 'Z',
                'branch': 'main'
            }
        })

    return data


def run_regression_analysis(data: List[Dict[str, Any]], trace_name: str) -> Dict[str, Any]:
    """Run main_health analysis on the data."""

    # Extract time series
    series = []
    dates = []

    for record in data:
        for benchmark in record['benchmarks']:
            if benchmark['metrics']['metricName'] == trace_name:
                series.append(benchmark['metrics']['median'])
                dates.append(record['build']['created_at'])

    if len(series) < 10:
        return {
            'alert': False,
            'reason': 'Insufficient data points for analysis',
            'delta': 0,
            'z_score': 0,
            'baseline_median': 0,
            'current_value': 0
        }

    # Use main_health algorithm if available
    if assess_main_health:
        try:
            report = assess_main_health(series)

            # Extract control chart results
            control = report.control if report else None
            stepfit = report.stepfit if report else None

            # Determine regression index and type
            regression_index = None
            regression_type = None
            regression_date = None
            regression_commit = None
            regression_commit_url = None

            if control and control.alert:
                # Check if step-fit found a changepoint
                if stepfit and stepfit.found:
                    regression_index = stepfit.change_index
                    regression_type = 'step'
                else:
                    # Use last point for spike detection
                    regression_index = len(series) - 1
                    regression_type = 'step'

                # Get commit information from the data
                if regression_index is not None and regression_index < len(data):
                    regression_date = dates[regression_index] if regression_index < len(dates) else None
                    build_info = data[regression_index].get('build', {})
                    regression_commit = build_info.get('commit_hash', 'unknown')

                    # Generate GitHub URL from configured repo
                    if regression_commit and regression_commit != 'unknown':
                        regression_commit_url = f"{GITHUB_REPO_URL}/commit/{regression_commit}"

                return {
                    'alert': True,
                    'reason': control.reason,
                    'delta': round(control.value - control.baseline_median, 2),
                    'z_score': round(control.robust_z, 2),
                    'baseline_median': round(control.baseline_median, 2),
                    'current_value': round(control.value, 2),
                    'regression_index': regression_index,
                    'regression_type': regression_type,
                    'regression_date': regression_date,
                    'regression_commit': regression_commit,
                    'regression_commit_url': regression_commit_url
                }
            else:
                return {
                    'alert': False,
                    'reason': 'No regression detected',
                    'delta': 0,
                    'z_score': 0,
                    'baseline_median': round(control.baseline_median, 2) if control else 0,
                    'current_value': round(control.value, 2) if control else 0
                }
        except Exception as e:
            print(f"⚠️  main_health analysis failed: {e}")

    # Fallback: Simple analysis
    # Use first 30% of data as baseline
    # Compare CURRENT value (last point) against baseline, like Control Chart does
    baseline_size = max(5, int(len(series) * 0.3))
    baseline = series[:baseline_size]

    baseline_median = sorted(baseline)[len(baseline) // 2]
    current_value = series[-1]
    delta = current_value - baseline_median

    # Simple threshold check
    practical_threshold = max(50, 0.05 * baseline_median)
    alert = delta > practical_threshold and delta > 0

    # Detect regression point and type
    regression_index = None
    regression_type = None
    regression_date = None
    regression_commit = None
    regression_commit_url = None

    if alert:
        # Find where regression started - look for step change
        for i in range(baseline_size, len(series)):
            if series[i] > baseline_median + practical_threshold:
                regression_index = i
                regression_date = dates[i] if i < len(dates) else None

                # Get commit information from the data
                if i < len(data):
                    build_info = data[i].get('build', {})
                    regression_commit = build_info.get('commit_hash', 'unknown')

                    # Generate GitHub URL from configured repo
                    if regression_commit and regression_commit != 'unknown':
                        regression_commit_url = f"{GITHUB_REPO_URL}/commit/{regression_commit}"

                # Determine if it's a step or creep
                # Step: sudden jump (next value is significantly higher)
                # Creep: gradual increase
                if i > 0:
                    jump = series[i] - series[i-1]
                    if jump > practical_threshold * 0.5:
                        regression_type = 'step'
                    else:
                        regression_type = 'creep'
                else:
                    regression_type = 'step'
                break

    return {
        'alert': alert,
        'reason': f'{"Step" if regression_type == "step" else "Creep"} regression detected: {delta:.2f}ms increase' if alert else 'No regression detected',
        'delta': round(delta, 2),
        'z_score': 0,
        'baseline_median': round(baseline_median, 2),
        'current_value': round(current_value, 2),
        'regression_index': regression_index,
        'regression_type': regression_type,
        'regression_date': regression_date,
        'regression_commit': regression_commit,
        'regression_commit_url': regression_commit_url
    }


@app.route('/')
def index():
    """Serve the main dashboard."""
    return render_template('dashboard_new.html')


@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'bigquery': 'connected' if bq_client else 'mock_mode',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/api/performance-data', methods=['POST'])
def get_performance_data():
    """Fetch performance data from BigQuery and run analysis."""

    try:
        # Parse request
        data = request.get_json()
        platform = data.get('platform', 'ios')
        start_date = data.get('startDate', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end_date = data.get('endDate', datetime.now().strftime('%Y-%m-%d'))
        trace_name = data.get('traceName', 'homeTabStartToInteractive')

        print(f"📊 Fetching data: platform={platform}, dates={start_date} to {end_date}, trace={trace_name}")

        # Query BigQuery
        bq_data = query_bigquery(platform, start_date, end_date, trace_name)

        print(f"✅ Retrieved {len(bq_data)} records")

        # Run regression analysis
        analysis = run_regression_analysis(bq_data, trace_name)

        # Prepare response
        response = {
            'data': bq_data,
            'analysis': analysis,
            'metadata': {
                'platform': platform,
                'startDate': start_date,
                'endDate': end_date,
                'traceName': trace_name,
                'recordCount': len(bq_data)
            }
        }

        return jsonify(response)

    except Exception as e:
        print(f"❌ Error in get_performance_data: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'error': str(e),
            'message': 'Failed to fetch performance data'
        }), 500


def _generate_commit_history_section(commits, regression_index, trace_name, platform):
    """Generate HTML section showing before/after commits."""

    if not commits or regression_index is None:
        return ""

    # Get 10 commits before and after regression point
    before_commits = commits[max(0, regression_index - 10):regression_index]
    after_commits = commits[regression_index:min(len(commits), regression_index + 10)]

    html = f"""
    <div style="margin: 40px; padding: 30px; background: rgba(26, 31, 41, 0.95); border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
        <h2 style="color: #e0e0e0; margin-bottom: 20px; font-size: 24px;">
            📋 Commit History - {trace_name} ({platform.upper()})
        </h2>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
            <!-- Before Regression -->
            <div>
                <h3 style="color: #4caf50; margin-bottom: 15px; font-size: 18px; display: flex; align-items: center; gap: 8px;">
                    <span>✅</span> Before Regression ({len(before_commits)} commits)
                </h3>
                <div style="background: rgba(36, 43, 56, 0.9); padding: 20px; border-radius: 8px; border-left: 4px solid #4caf50;">
    """

    for i, commit in enumerate(reversed(before_commits)):
        html += f"""
                    <div style="margin-bottom: 12px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 6px;">
                        <div style="color: #e0e0e0; font-weight: 600; margin-bottom: 4px;">
                            {commit['hash'][:8]} - {commit['app_version']}
                        </div>
                        <div style="color: #a0a0a0; font-size: 13px; display: flex; justify-content: space-between;">
                            <span>{commit['date'][:10]}</span>
                            <span style="color: #4caf50; font-weight: 600;">{commit['median']:.2f}ms</span>
                        </div>
                    </div>
        """

    html += f"""
                </div>
            </div>

            <!-- After Regression -->
            <div>
                <h3 style="color: #f44336; margin-bottom: 15px; font-size: 18px; display: flex; align-items: center; gap: 8px;">
                    <span>⚠️</span> After Regression ({len(after_commits)} commits)
                </h3>
                <div style="background: rgba(36, 43, 56, 0.9); padding: 20px; border-radius: 8px; border-left: 4px solid #f44336;">
    """

    for i, commit in enumerate(after_commits):
        is_first = (i == 0)
        highlight = "background: rgba(244, 67, 54, 0.2);" if is_first else ""
        html += f"""
                    <div style="margin-bottom: 12px; padding: 10px; {highlight} border-radius: 6px;">
                        <div style="color: #e0e0e0; font-weight: 600; margin-bottom: 4px;">
                            {commit['hash'][:8]} - {commit['app_version']}
                            {"<span style='color: #f44336; margin-left: 8px;'>← REGRESSION</span>" if is_first else ""}
                        </div>
                        <div style="color: #a0a0a0; font-size: 13px; display: flex; justify-content: space-between;">
                            <span>{commit['date'][:10]}</span>
                            <span style="color: #f44336; font-weight: 600;">{commit['median']:.2f}ms</span>
                        </div>
                    </div>
        """

    html += """
                </div>
            </div>
        </div>
    </div>
    """

    return html


@app.route('/api/detailed-report', methods=['POST'])
def generate_detailed_report():
    """Generate detailed main_health HTML report."""
    try:
        # Parse request (same as /api/performance-data)
        data = request.get_json()
        platform = data.get('platform', 'ios')
        start_date = data.get('startDate', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end_date = data.get('endDate', datetime.now().strftime('%Y-%m-%d'))
        trace_name = data.get('traceName', 'homeTabStartToInteractive')

        print(f"📊 Generating detailed report: platform={platform}, dates={start_date} to {end_date}, trace={trace_name}")

        # Query data (reuse existing function)
        bq_data = query_bigquery(platform, start_date, end_date, trace_name)

        if not bq_data or len(bq_data) < 10:
            return jsonify({
                'error': 'Insufficient data',
                'message': 'Need at least 10 data points for detailed analysis'
            }), 400

        # Extract time series (same as run_regression_analysis)
        series = []
        dates = []
        commits = []

        for record in bq_data:
            for benchmark in record['benchmarks']:
                if benchmark['metrics']['metricName'] == trace_name:
                    series.append(benchmark['metrics']['median'])
                    dates.append(record['build']['created_at'])
                    commits.append({
                        'hash': record['build'].get('commit_hash', 'unknown'),
                        'date': record['build']['created_at'],
                        'app_version': record['build'].get('app_version', 'N/A'),
                        'median': benchmark['metrics']['median']
                    })

        # Run main_health analysis
        if assess_main_health:
            report = assess_main_health(series)
            overall_status = "ALERT" if report.overall_alert else "OK"

            # Try to get regression index from step-fit first, then control chart
            regression_index = None
            if report.stepfit and report.stepfit.found:
                regression_index = report.stepfit.change_index
            elif report.control and report.control.alert:
                # For spike detection, regression is at the last point
                regression_index = len(series) - 1
        else:
            return jsonify({
                'error': 'main_health module not available',
                'message': 'Cannot generate detailed report without main_health'
            }), 500

        # Generate HTML using main_health_template
        try:
            from main_health_template import render_health_template
        except ImportError:
            return jsonify({
                'error': 'main_health_template module not available',
                'message': 'Cannot generate detailed report without main_health_template'
            }), 500

        html_content = render_health_template(
            series=series,
            report=report,
            overall_status=overall_status,
            regression_index=regression_index,
            timestamp=datetime.utcnow().isoformat(),
            trace_name=trace_name
        )

        # Add custom metadata section with commit history
        # Find "before" and "after" commits (10 each around regression point)
        commit_section = _generate_commit_history_section(
            commits, regression_index, trace_name, platform
        )

        # Inject commit section into HTML (before closing </body>)
        html_content = html_content.replace('</body>', f'{commit_section}</body>')

        # Save to file
        os.makedirs('generated_reports', exist_ok=True)
        filename = f"{trace_name}_{platform}_{start_date}_{end_date}.html"
        filepath = os.path.join('generated_reports', filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"✅ Generated report: {filepath}")

        return jsonify({
            'success': True,
            'report_filename': filename,
            'report_url': f'/api/reports/{filename}'
        })

    except Exception as e:
        print(f"❌ Error generating detailed report: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'message': 'Failed to generate detailed report'
        }), 500


@app.route('/api/reports/<filename>')
def serve_report(filename):
    """Serve generated HTML reports."""
    try:
        filepath = os.path.join('generated_reports', filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'Report not found'}), 404

        return send_file(filepath, mimetype='text/html')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/available-traces')
def get_available_traces():
    """Get list of available trace names."""
    traces = [
        'homeTabStartToInteractive',
        'pickupListStartToInteractive',
        'shopListStartToInteractive',
        'shopDetailStartToInteractive',
        'menuStartToInteractive',
        'cartStartToInteractive',
        'checkoutStartToInteractive',
        'orderTrackingStartToInteractive'
    ]

    return jsonify({'traces': traces})


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'

    print(f"""
    ╔══════════════════════════════════════════╗
    ║  Performance Traces Dashboard Server    ║
    ╠══════════════════════════════════════════╣
    ║  Running on: http://localhost:{port}      ║
    ║  Mode: {'Development' if debug else 'Production':30} ║
    ║  BigQuery: {'Connected' if bq_client else 'Mock Mode':29} ║
    ╚══════════════════════════════════════════╝
    """)

    app.run(host='0.0.0.0', port=port, debug=debug)
