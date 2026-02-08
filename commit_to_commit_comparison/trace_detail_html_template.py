"""HTML template for individual trace detail pages.

This template wraps the existing perf_html_report with navigation.
"""

import numpy as np
import json
from html import escape
from typing import List, Dict, Optional

from .perf_html_report import render_html_report
from .commit_to_commit_comparison import GateResult


def render_trace_detail_template(
    trace_name: str,
    baseline: np.ndarray,
    target: np.ndarray,
    result: GateResult,
    prev_trace: str = None,
    next_trace: str = None,
    comparison_page_url: str = "index.html",
    baseline_device_metrics: Optional[List[Dict]] = None,
    target_device_metrics: Optional[List[Dict]] = None
) -> str:
    """Render detail page with navigation and device metrics.

    Args:
        trace_name: Name of the trace
        baseline: Baseline measurements array
        target: Target measurements array
        result: GateResult from gate_regression()
        prev_trace: Name of previous trace (for navigation)
        next_trace: Name of next trace (for navigation)
        comparison_page_url: URL to return to comparison page
        baseline_device_metrics: Optional device metrics for baseline runs
        target_device_metrics: Optional device metrics for target runs

    Returns:
        Complete HTML string for the detail page
    """
    # Convert GateResult to dictionary format expected by render_html_report
    result_dict = {
        'passed': result.passed,
        'reason': result.reason,
        'inconclusive': result.inconclusive,
        'no_change': result.no_change,
        'details': result.details
    }

    # Generate the base performance report HTML
    base_html = render_html_report(
        title="PerfDiff",
        baseline=baseline.tolist(),
        target=target.tolist(),
        result=result_dict,
        mode="pr"  # PR mode for regression detection
    )

    # Create navigation bar HTML
    prev_link = ""
    if prev_trace:
        prev_link = f'<a href="{escape(prev_trace)}.html" class="nav-btn">← Previous</a>'

    next_link = ""
    if next_trace:
        next_link = f'<a href="{escape(next_trace)}.html" class="nav-btn">Next →</a>'

    nav_bar_html = f"""
  <!-- Navigation Bar -->
  <div class="nav-bar">
    <div class="nav-left">
      <a href="{escape(comparison_page_url)}" class="nav-back">← Back to Comparison</a>
    </div>
    <div class="nav-center">
      <span class="nav-trace-name">{escape(trace_name)}</span>
    </div>
    <div class="nav-right">
      {prev_link}
      {next_link}
    </div>
  </div>
"""

    # Add CSS for navigation bar
    nav_styles = """
  <style>
    /* Navigation bar */
    .nav-bar {
      position: sticky;
      top: 0;
      z-index: 101;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 20px;
      background: rgba(26, 31, 41, 0.98);
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      backdrop-filter: blur(10px);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }

    .nav-left, .nav-center, .nav-right {
      flex: 1;
      display: flex;
      align-items: center;
    }

    .nav-left {
      justify-content: flex-start;
    }

    .nav-center {
      justify-content: center;
    }

    .nav-right {
      justify-content: flex-end;
      gap: 12px;
    }

    .nav-back {
      color: #0066ff;
      text-decoration: none;
      font-weight: 600;
      font-size: 14px;
      transition: color 0.2s ease;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .nav-back:hover {
      color: #4dabf7;
    }

    .nav-trace-name {
      font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
      font-size: 15px;
      font-weight: 600;
      color: #f5f9ff;
      padding: 6px 12px;
      background: rgba(0, 102, 255, 0.25);
      border-radius: 6px;
      border: 1px solid rgba(0, 102, 255, 0.6);
      box-shadow: 0 0 12px rgba(0, 102, 255, 0.35);
    }

    .nav-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 14px;
      background: rgba(0, 102, 255, 0.1);
      color: #0066ff;
      text-decoration: none;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      border: 1px solid rgba(0, 102, 255, 0.3);
      transition: all 0.2s ease;
    }

    .nav-btn:hover {
      background: rgba(0, 102, 255, 0.2);
      border-color: rgba(0, 102, 255, 0.5);
      transform: translateY(-1px);
    }

    /* Responsive navigation */
    @media (max-width: 900px) {
      .nav-bar {
        flex-wrap: wrap;
        gap: 12px;
      }

      .nav-left, .nav-center, .nav-right {
        flex: auto;
      }

      .nav-center {
        order: -1;
        flex-basis: 100%;
        justify-content: center;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      }
    }

    @media (max-width: 600px) {
      .nav-bar {
        padding: 10px 12px;
      }

      .nav-trace-name {
        font-size: 13px;
        padding: 4px 10px;
      }

      .nav-btn {
        font-size: 12px;
        padding: 6px 10px;
      }
    }
  </style>
"""

    # Generate device metrics section if available
    device_metrics_html = ""
    if baseline_device_metrics or target_device_metrics:
        device_metrics_html = _render_device_metrics_section(
            baseline_device_metrics,
            target_device_metrics,
            baseline.tolist(),
            target.tolist()
        )

    # Add device metrics styles
    device_metrics_styles = """
  <style>
    /* Device Metrics Table */
    .device-metrics-table-container {
      margin: 0 0 32px 0;
    }

    .device-metrics-table-container h3 {
      font-size: 18px;
      font-weight: 600;
      color: #f5f9ff;
      margin: 0 0 16px 0;
    }

    .device-metrics-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      margin-bottom: 24px;
    }

    .device-metrics-table thead {
      background: rgba(0, 102, 255, 0.1);
    }

    .device-metrics-table th {
      padding: 12px 16px;
      text-align: left;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.9);
      border-bottom: 2px solid rgba(0, 102, 255, 0.3);
      white-space: nowrap;
    }

    .device-metrics-table td {
      padding: 10px 16px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      color: rgba(255, 255, 255, 0.8);
    }

    .device-metrics-table tbody tr:hover {
      background: rgba(0, 102, 255, 0.05);
    }

    .device-metrics-table tbody tr:last-child td {
      border-bottom: none;
    }

    /* Thermal State Indicators */
    .thermal-nominal {
      color: #4caf50;
      font-weight: 600;
    }

    .thermal-fair {
      color: #ff9800;
      font-weight: 600;
    }

    .thermal-serious {
      color: #ff5722;
      font-weight: 600;
    }

    .thermal-critical {
      color: #f44336;
      font-weight: 700;
      text-transform: uppercase;
    }

    /* Correlation Charts */
    .device-correlation-charts {
      margin: 0;
    }

    .device-correlation-charts h3 {
      font-size: 18px;
      font-weight: 600;
      color: #f5f9ff;
      margin: 0 0 16px 0;
    }

    .charts-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
      gap: 24px;
    }

    .chart-container {
      background: rgba(26, 31, 41, 0.5);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      padding: 20px;
      min-height: 300px;
    }

    .chart-container canvas {
      max-height: 350px;
    }

    /* Responsive Design */
    @media (max-width: 900px) {
      .charts-grid {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 600px) {
      .device-metrics-table {
        font-size: 11px;
      }

      .device-metrics-table th,
      .device-metrics-table td {
        padding: 8px 10px;
      }

      .chart-container {
        padding: 16px;
      }
    }
  </style>
"""

    # Insert navigation bar and styles into the base HTML
    # Find the closing </head> tag and insert nav styles before it
    html_with_nav_styles = base_html.replace('</head>', f'{nav_styles}\n{device_metrics_styles}\n</head>')

    # Find the opening <body> tag and insert nav bar after it
    html_with_nav = html_with_nav_styles.replace('<body>', f'<body>\n{nav_bar_html}')

    # Insert device metrics before the footer (inside main container)
    if device_metrics_html:
        # Find the "Generated by" footer and insert device metrics before it
        footer_marker = 'Generated by Performance Regression Detection Tool'
        if footer_marker in html_with_nav:
            html_with_content = html_with_nav.replace(
                f'    <div style="text-align: center; margin: 32px 0; padding: 16px; color: var(--text-secondary); font-size: 12px;">\n      {footer_marker}',
                f'{device_metrics_html}\n\n    <div style="text-align: center; margin: 32px 0; padding: 16px; color: var(--text-secondary); font-size: 12px;">\n      {footer_marker}'
            )
        else:
            # Fallback: insert before closing body tag
            html_with_content = html_with_nav.replace('</body>', f'\n{device_metrics_html}\n</body>')
    else:
        html_with_content = html_with_nav

    return html_with_content


def _calculate_device_stats(metrics: List[Dict]) -> Optional[Dict]:
    """Calculate aggregate device statistics.

    Args:
        metrics: List of device metrics per run

    Returns:
        Dictionary with aggregate statistics or None if no metrics
    """
    if not metrics:
        return None

    # Extract values, filtering out invalid ones
    cpu_values = [m['cpu_usage_percent'] for m in metrics if 'cpu_usage_percent' in m]
    memory_used_values = [m['memory_used_mb'] for m in metrics if 'memory_used_mb' in m]
    memory_available_values = [m['memory_available_mb'] for m in metrics if 'memory_available_mb' in m]
    battery_values = [m['battery_level_percent'] for m in metrics
                     if 'battery_level_percent' in m and m['battery_level_percent'] > 0]

    # Count thermal states
    thermal_distribution = {}
    for m in metrics:
        if 'thermal_state' in m:
            state = m['thermal_state']
            thermal_distribution[state] = thermal_distribution.get(state, 0) + 1

    # Count low power mode
    low_power_count = sum(1 for m in metrics if m.get('low_power_mode', False))

    return {
        'avg_cpu': np.mean(cpu_values) if cpu_values else None,
        'avg_memory_used': np.mean(memory_used_values) if memory_used_values else None,
        'avg_memory_available': np.mean(memory_available_values) if memory_available_values else None,
        'thermal_distribution': thermal_distribution,
        'battery_avg': np.mean(battery_values) if battery_values else None,
        'low_power_mode_count': low_power_count,
        'total_runs': len(metrics)
    }


def _render_device_overview_cards(baseline_stats: Optional[Dict], target_stats: Optional[Dict]) -> str:
    """Generate overview comparison cards for device metrics.

    Args:
        baseline_stats: Baseline device statistics
        target_stats: Target device statistics

    Returns:
        HTML string with comparison cards
    """
    if not baseline_stats and not target_stats:
        return ""

    # Helper function to format thermal distribution
    def get_thermal_summary(distribution):
        if not distribution:
            return "N/A"
        total = sum(distribution.values())
        # Get most common thermal state
        most_common = max(distribution.items(), key=lambda x: x[1])
        percentage = (most_common[1] / total) * 100
        return f"Mostly {most_common[0].title()} ({percentage:.0f}%)"

    # Helper function to get delta class
    def get_delta_class(value):
        if value is None or value == 0:
            return "neutral"
        return "positive" if value > 0 else "negative"

    cards_html = '<div class="device-overview-grid">\n'

    # CPU Usage Card
    if baseline_stats and target_stats:
        cpu_delta = (target_stats.get('avg_cpu') or 0) - (baseline_stats.get('avg_cpu') or 0)
        cards_html += f'''
      <div class="device-card">
        <h4>CPU Usage</h4>
        <div class="metric-comparison">
          <span class="baseline-value">{baseline_stats.get('avg_cpu', 0):.1f}%</span>
          <span class="arrow">→</span>
          <span class="target-value">{target_stats.get('avg_cpu', 0):.1f}%</span>
          <span class="delta {get_delta_class(cpu_delta)}">{cpu_delta:+.1f}%</span>
        </div>
      </div>
    '''

    # Memory Used Card
    if baseline_stats and target_stats:
        memory_delta = (target_stats.get('avg_memory_used') or 0) - (baseline_stats.get('avg_memory_used') or 0)
        cards_html += f'''
      <div class="device-card">
        <h4>Memory Used</h4>
        <div class="metric-comparison">
          <span class="baseline-value">{baseline_stats.get('avg_memory_used', 0):.1f} MB</span>
          <span class="arrow">→</span>
          <span class="target-value">{target_stats.get('avg_memory_used', 0):.1f} MB</span>
          <span class="delta {get_delta_class(memory_delta)}">{memory_delta:+.1f} MB</span>
        </div>
      </div>
    '''

    # Thermal State Card
    if baseline_stats and target_stats:
        baseline_thermal = get_thermal_summary(baseline_stats.get('thermal_distribution', {}))
        target_thermal = get_thermal_summary(target_stats.get('thermal_distribution', {}))
        cards_html += f'''
      <div class="device-card">
        <h4>Thermal State</h4>
        <div class="metric-comparison">
          <span class="baseline-value">{baseline_thermal}</span>
          <span class="arrow">→</span>
          <span class="target-value">{target_thermal}</span>
        </div>
      </div>
    '''

    # Battery Card
    if baseline_stats and target_stats:
        baseline_battery = baseline_stats.get('battery_avg')
        target_battery = target_stats.get('battery_avg')
        if baseline_battery is not None and target_battery is not None:
            battery_delta = target_battery - baseline_battery
            cards_html += f'''
      <div class="device-card">
        <h4>Battery Level</h4>
        <div class="metric-comparison">
          <span class="baseline-value">{baseline_battery:.0f}%</span>
          <span class="arrow">→</span>
          <span class="target-value">{target_battery:.0f}%</span>
          <span class="delta {get_delta_class(battery_delta)}">{battery_delta:+.0f}%</span>
        </div>
      </div>
    '''

    cards_html += '    </div>\n'
    return cards_html


def _render_device_metrics_table(
    baseline_metrics: Optional[List[Dict]],
    target_metrics: Optional[List[Dict]],
    baseline_measurements: List[float],
    target_measurements: List[float]
) -> str:
    """Generate per-run device metrics tables (Baseline and Target stacked vertically).

    Args:
        baseline_metrics: Baseline device metrics per run
        target_metrics: Target device metrics per run
        baseline_measurements: Baseline performance measurements
        target_measurements: Target performance measurements

    Returns:
        HTML string with two separate device metrics tables
    """
    if not baseline_metrics and not target_metrics:
        return ""

    # Helper function to get thermal state class
    def get_thermal_class(state):
        if not state:
            return ""
        state_lower = state.lower()
        if state_lower == "nominal":
            return "thermal-nominal"
        elif state_lower == "fair":
            return "thermal-fair"
        elif state_lower == "serious":
            return "thermal-serious"
        elif state_lower == "critical":
            return "thermal-critical"
        return ""

    # Helper function to render a single table
    def render_table(title, metrics, measurements):
        if not metrics:
            return ""

        html = f'''
        <h3>{title}</h3>
        <table class="device-metrics-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Value (ms)</th>
              <th>Thermal State</th>
              <th>CPU %</th>
              <th>Memory (MB)</th>
              <th>Battery %</th>
              <th>Low Power</th>
            </tr>
          </thead>
          <tbody>
        '''

        for i, metric in enumerate(metrics):
            run_idx = metric.get('run_index', i + 1)
            value = measurements[i] if i < len(measurements) else None
            value_str = f"{value:.2f}" if value is not None else 'N/A'

            thermal = escape(metric.get('thermal_state', 'N/A'))
            cpu = f"{metric.get('cpu_usage_percent', 0):.1f}" if 'cpu_usage_percent' in metric else 'N/A'
            memory = f"{metric.get('memory_used_mb', 0):.1f}" if 'memory_used_mb' in metric else 'N/A'
            battery = metric.get('battery_level_percent', -1)
            battery_str = f"{battery:.0f}" if battery > 0 else 'N/A'
            low_power = "Yes" if metric.get('low_power_mode', False) else "No"

            html += f'''
            <tr>
              <td>{run_idx}</td>
              <td>{value_str}</td>
              <td><span class="{get_thermal_class(thermal)}">{thermal}</span></td>
              <td>{cpu}</td>
              <td>{memory}</td>
              <td>{battery_str}</td>
              <td>{low_power}</td>
            </tr>
            '''

        html += '''
          </tbody>
        </table>
        '''
        return html

    table_html = '<div class="device-metrics-table-container">\n'

    # Render Baseline table
    if baseline_metrics:
        table_html += render_table("Baseline Device Metrics", baseline_metrics, baseline_measurements)

    # Render Target table
    if target_metrics:
        table_html += render_table("Target Device Metrics", target_metrics, target_measurements)

    table_html += '</div>\n'

    return table_html


def _render_device_correlation_charts(
    baseline_metrics: Optional[List[Dict]],
    target_metrics: Optional[List[Dict]],
    baseline_measurements: List[float],
    target_measurements: List[float]
) -> str:
    """Generate Chart.js correlation charts.

    Args:
        baseline_metrics: Baseline device metrics per run
        target_metrics: Target device metrics per run
        baseline_measurements: Baseline performance measurements
        target_measurements: Target performance measurements

    Returns:
        HTML string with correlation charts
    """
    if not baseline_metrics and not target_metrics:
        return ""

    # Prepare data for CPU correlation chart
    baseline_cpu_data = []
    if baseline_metrics and baseline_measurements:
        for i, metric in enumerate(baseline_metrics):
            if i < len(baseline_measurements) and 'cpu_usage_percent' in metric:
                baseline_cpu_data.append({
                    'x': metric['cpu_usage_percent'],
                    'y': baseline_measurements[i]
                })

    target_cpu_data = []
    if target_metrics and target_measurements:
        for i, metric in enumerate(target_metrics):
            if i < len(target_measurements) and 'cpu_usage_percent' in metric:
                target_cpu_data.append({
                    'x': metric['cpu_usage_percent'],
                    'y': target_measurements[i]
                })

    # Prepare data for memory correlation chart
    baseline_memory_data = []
    if baseline_metrics and baseline_measurements:
        for i, metric in enumerate(baseline_metrics):
            if i < len(baseline_measurements) and 'memory_used_mb' in metric:
                baseline_memory_data.append({
                    'x': metric['memory_used_mb'],
                    'y': baseline_measurements[i]
                })

    target_memory_data = []
    if target_metrics and target_measurements:
        for i, metric in enumerate(target_metrics):
            if i < len(target_measurements) and 'memory_used_mb' in metric:
                target_memory_data.append({
                    'x': metric['memory_used_mb'],
                    'y': target_measurements[i]
                })

    # Prepare data for thermal state correlation chart
    # Map thermal states to numeric values
    thermal_state_map = {
        'nominal': 0,
        'fair': 1,
        'serious': 2,
        'critical': 3
    }

    baseline_thermal_data = []
    if baseline_metrics and baseline_measurements:
        for i, metric in enumerate(baseline_metrics):
            if i < len(baseline_measurements) and 'thermal_state' in metric:
                state = metric['thermal_state'].lower()
                if state in thermal_state_map:
                    baseline_thermal_data.append({
                        'x': thermal_state_map[state],
                        'y': baseline_measurements[i]
                    })

    target_thermal_data = []
    if target_metrics and target_measurements:
        for i, metric in enumerate(target_metrics):
            if i < len(target_measurements) and 'thermal_state' in metric:
                state = metric['thermal_state'].lower()
                if state in thermal_state_map:
                    target_thermal_data.append({
                        'x': thermal_state_map[state],
                        'y': target_measurements[i]
                    })

    charts_html = f'''
    <div class="device-correlation-charts">
      <h3>Device Metrics Correlation</h3>
      <div class="charts-grid">
        <div class="chart-container">
          <canvas id="deviceThermalChart"></canvas>
        </div>
        <div class="chart-container">
          <canvas id="deviceCpuChart"></canvas>
        </div>
        <div class="chart-container">
          <canvas id="deviceMemoryChart"></canvas>
        </div>
      </div>
    </div>

    <script>
      // Thermal State Correlation Chart
      new Chart(document.getElementById('deviceThermalChart'), {{
        type: 'scatter',
        data: {{
          datasets: [{{
            label: 'Baseline',
            data: {json.dumps(baseline_thermal_data)},
            backgroundColor: 'rgba(25, 118, 210, 0.6)',
            borderColor: 'rgba(25, 118, 210, 1)',
            borderWidth: 1
          }}, {{
            label: 'Target',
            data: {json.dumps(target_thermal_data)},
            backgroundColor: 'rgba(211, 47, 47, 0.6)',
            borderColor: 'rgba(211, 47, 47, 1)',
            borderWidth: 1
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: true,
          plugins: {{
            title: {{
              display: true,
              text: 'Performance vs Thermal State',
              color: '#e0e0e0'
            }},
            legend: {{
              labels: {{
                color: '#e0e0e0'
              }}
            }}
          }},
          scales: {{
            x: {{
              title: {{
                display: true,
                text: 'Thermal State',
                color: '#e0e0e0'
              }},
              ticks: {{
                color: '#e0e0e0',
                stepSize: 1,
                autoSkip: false,
                callback: function(value) {{
                  const labels = {{
                    0: 'Nominal',
                    1: 'Fair',
                    2: 'Serious',
                    3: 'Critical'
                  }};
                  return labels[value] !== undefined ? labels[value] : '';
                }}
              }},
              grid: {{
                color: 'rgba(255, 255, 255, 0.1)'
              }},
              min: 0,
              max: 3
            }},
            y: {{
              title: {{
                display: true,
                text: 'Performance (ms)',
                color: '#e0e0e0'
              }},
              ticks: {{
                color: '#e0e0e0'
              }},
              grid: {{
                color: 'rgba(255, 255, 255, 0.1)'
              }}
            }}
          }}
        }}
      }});

      // CPU Correlation Chart
      new Chart(document.getElementById('deviceCpuChart'), {{
        type: 'scatter',
        data: {{
          datasets: [{{
            label: 'Baseline',
            data: {json.dumps(baseline_cpu_data)},
            backgroundColor: 'rgba(25, 118, 210, 0.6)',
            borderColor: 'rgba(25, 118, 210, 1)',
            borderWidth: 1
          }}, {{
            label: 'Target',
            data: {json.dumps(target_cpu_data)},
            backgroundColor: 'rgba(211, 47, 47, 0.6)',
            borderColor: 'rgba(211, 47, 47, 1)',
            borderWidth: 1
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: true,
          plugins: {{
            title: {{
              display: true,
              text: 'Performance vs CPU Usage',
              color: '#e0e0e0'
            }},
            legend: {{
              labels: {{
                color: '#e0e0e0'
              }}
            }}
          }},
          scales: {{
            x: {{
              title: {{
                display: true,
                text: 'CPU Usage (%)',
                color: '#e0e0e0'
              }},
              ticks: {{
                color: '#e0e0e0'
              }},
              grid: {{
                color: 'rgba(255, 255, 255, 0.1)'
              }}
            }},
            y: {{
              title: {{
                display: true,
                text: 'Performance (ms)',
                color: '#e0e0e0'
              }},
              ticks: {{
                color: '#e0e0e0'
              }},
              grid: {{
                color: 'rgba(255, 255, 255, 0.1)'
              }}
            }}
          }}
        }}
      }});

      // Memory Correlation Chart
      new Chart(document.getElementById('deviceMemoryChart'), {{
        type: 'scatter',
        data: {{
          datasets: [{{
            label: 'Baseline',
            data: {json.dumps(baseline_memory_data)},
            backgroundColor: 'rgba(25, 118, 210, 0.6)',
            borderColor: 'rgba(25, 118, 210, 1)',
            borderWidth: 1
          }}, {{
            label: 'Target',
            data: {json.dumps(target_memory_data)},
            backgroundColor: 'rgba(211, 47, 47, 0.6)',
            borderColor: 'rgba(211, 47, 47, 1)',
            borderWidth: 1
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: true,
          plugins: {{
            title: {{
              display: true,
              text: 'Performance vs Memory Usage',
              color: '#e0e0e0'
            }},
            legend: {{
              labels: {{
                color: '#e0e0e0'
              }}
            }}
          }},
          scales: {{
            x: {{
              title: {{
                display: true,
                text: 'Memory Used (MB)',
                color: '#e0e0e0'
              }},
              ticks: {{
                color: '#e0e0e0'
              }},
              grid: {{
                color: 'rgba(255, 255, 255, 0.1)'
              }}
            }},
            y: {{
              title: {{
                display: true,
                text: 'Performance (ms)',
                color: '#e0e0e0'
              }},
              ticks: {{
                color: '#e0e0e0'
              }},
              grid: {{
                color: 'rgba(255, 255, 255, 0.1)'
              }}
            }}
          }}
        }}
      }});
    </script>
    '''

    return charts_html


def _render_device_metrics_section(
    baseline_metrics: Optional[List[Dict]],
    target_metrics: Optional[List[Dict]],
    baseline_measurements: List[float],
    target_measurements: List[float]
) -> str:
    """Render complete device metrics section.

    Args:
        baseline_metrics: Baseline device metrics per run
        target_metrics: Target device metrics per run
        baseline_measurements: Baseline performance measurements
        target_measurements: Target performance measurements

    Returns:
        HTML string with complete device metrics section
    """
    if not baseline_metrics and not target_metrics:
        return ""

    # Generate components (skip overview cards)
    table_html = _render_device_metrics_table(
        baseline_metrics,
        target_metrics,
        baseline_measurements,
        target_measurements
    )
    charts_html = _render_device_correlation_charts(
        baseline_metrics,
        target_metrics,
        baseline_measurements,
        target_measurements
    )

    # Combine into collapsible section matching Raw Measurement style
    section_html = f'''
    <div class="section">
      <div class="section-header" onclick="toggleSection('device-metrics')">
        <div>
          <h2 class="section-title">📱 Device Performance Metrics</h2>
          <div class="section-subtitle">Device conditions during test execution</div>
        </div>
        <span class="toggle-icon">▼</span>
      </div>
      <div id="device-metrics" class="section-content">
        {table_html}
        {charts_html}
      </div>
    </div>
    '''

    return section_html
