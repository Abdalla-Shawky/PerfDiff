#!/usr/bin/env python3
"""
Performance Traces Dashboard - Flask Backend
Integrates with BigQuery and main_health algorithm
"""

from flask import Flask, render_template, jsonify, request
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


def load_mock_data_from_file(platform: str, start_date: str, end_date: str, trace_name: str) -> List[Dict[str, Any]]:
    """Load mock data from local JSON file."""
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

                    # Filter by date range if data exists
                    if trace_data:
                        print(f"✅ Loaded {len(trace_data)} records from mock_data.json for {trace_name}/{platform}")

                        # Filter by date range
                        start = datetime.fromisoformat(start_date)
                        end = datetime.fromisoformat(end_date)

                        filtered_data = []
                        for record in trace_data:
                            record_date = datetime.fromisoformat(record['build']['created_at'].replace('Z', '+00:00'))
                            if start <= record_date <= end:
                                filtered_data.append(record)

                        if filtered_data:
                            print(f"✅ Filtered to {len(filtered_data)} records in date range {start_date} to {end_date}")
                            return filtered_data
                        else:
                            print(f"⚠️  No data in date range, falling back to generated data")
    except Exception as e:
        print(f"⚠️  Error reading mock_data.json: {e}")

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

            if control and control.alert:
                return {
                    'alert': True,
                    'reason': control.reason,
                    'delta': round(control.value - control.baseline_median, 2),
                    'z_score': round(control.robust_z, 2),
                    'baseline_median': round(control.baseline_median, 2),
                    'current_value': round(control.value, 2)
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
    # Use first 30% of data as baseline, last 30% as recent
    baseline_size = max(5, int(len(series) * 0.3))
    baseline = series[:baseline_size]
    recent = series[-baseline_size:]

    baseline_median = sorted(baseline)[len(baseline) // 2]
    recent_median = sorted(recent)[len(recent) // 2]
    current_value = recent[-1]
    delta = recent_median - baseline_median

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
