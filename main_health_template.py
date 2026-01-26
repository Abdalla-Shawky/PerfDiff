"""
HTML template for Main Branch Health Monitoring reports.

This module contains the HTML/CSS/JS template for generating
premium health monitoring reports with charts and quality assessment.
"""

from typing import List, Dict, Any, Optional


def render_health_template(
    series: List[float],
    report: Any,  # HealthReport
    overall_status: str,  # "ALERT" or "OK"
    regression_index: Optional[int],
    timestamp: str,
) -> str:
    """
    Render the main health monitoring HTML report.

    Args:
        series: Time-series data
        report: HealthReport object
        overall_status: "ALERT" or "OK"
        regression_index: Index where regression started (None if no regression)
        timestamp: Report generation timestamp
    """

    # Extract data from report
    control = report.control
    ewma = report.ewma
    stepfit = report.stepfit

    # Prepare series data for chart
    series_json = str(series)

    # Calculate quality score based on data characteristics
    quality_score, quality_verdict, quality_issues, outlier_indices = _assess_data_quality(series, report)

    # Prepare outlier indices for chart
    outlier_indices_json = str(outlier_indices)

    # Calculate trimmed mean (average excluding outliers)
    trimmed_mean = _calculate_trimmed_mean(series, outlier_indices)

    # Determine status colors
    if overall_status == "ALERT":
        status_color = "#FFFFFF"
        status_bg = "#ffebee"
        status_icon = "🚨"
    else:
        status_color = "#2e7d32"
        status_bg = "#e8f5e9"
        status_icon = "✅"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Main Branch Health Monitoring Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/hammerjs@2.0.8"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">

    <style>
        :root {{
            /* Premium Color Palette */
            --bg-primary: #f8f9fa;
            --bg-secondary: #ffffff;
            --bg-tertiary: #f1f3f5;
            --text-primary: #1a1a1a;
            --text-secondary: #6c757d;
            --accent-primary: #0066ff;
            --accent-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

            --success: #2e7d32;
            --success-bg: #e8f5e9;
            --success-text: #2e7d32;
            --danger: #d32f2f;
            --danger-bg: #ffebee;
            --danger-text: #d32f2f;
            --warning: #f57c00;
            --warning-bg: #fff3e0;
            --warning-text: #f57c00;
            --info: #0288d1;
            --info-bg: #e1f5fe;
            --info-text: #0288d1;

            /* Shadows */
            --shadow-sm: 0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1);
            --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
            --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1);

            /* Typography */
            --font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }}

        [data-theme="dark"] {{
            --bg-primary: #0f1419;
            --bg-secondary: #1a1f29;
            --bg-tertiary: #242b38;
            --text-primary: #e0e0e0;
            --text-secondary: #a0a0a0;

            /* Dark mode color adjustments - muted colors for better design */
            --success: #4caf50;
            --success-bg: #1b5e20;
            --success-text: #ffffff;
            --danger: #f44336;
            --danger-bg: #b71c1c;
            --danger-text: #ffffff;
            --warning: #ff9800;
            --warning-bg: #e65100;
            --warning-text: #ffffff;
            --info: #2196f3;
            --info-bg: #01579b;
            --info-text: #ffffff;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: var(--font-family);
            background: var(--bg-primary);
            color: var(--text-primary);
            padding: 20px;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: var(--bg-secondary);
            border-radius: 12px;
            box-shadow: var(--shadow-md);
        }}

        h1 {{
            font-size: 28px;
            font-weight: 700;
            letter-spacing: -0.5px;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }}

        .timestamp {{
            color: var(--text-secondary);
            font-size: 14px;
        }}

        .status-banner {{
            padding: 24px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: var(--shadow-sm);
        }}

        .status-banner.alert {{
            background: var(--danger-bg);
            border-left: 4px solid var(--danger);
        }}

        .status-banner.ok {{
            background: var(--success-bg);
            border-left: 4px solid var(--success);
        }}

        .status-banner.alert h2 {{
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 8px;
            color: var(--danger-text);
        }}

        .status-banner.ok h2 {{
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 8px;
            color: var(--success-text);
        }}

        .status-banner.alert p {{
            color: var(--danger-text);
            font-size: 16px;
        }}

        .status-banner.ok p {{
            color: var(--success-text);
            font-size: 16px;
        }}

        .card {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: var(--shadow-md);
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .card:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
        }}

        .card-title {{
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 16px;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .badge-success {{
            background: var(--success-bg);
            color: var(--success-text);
        }}

        .badge-danger {{
            background: var(--danger-bg);
            color: var(--danger-text);
        }}

        .badge-warning {{
            background: var(--warning-bg);
            color: var(--warning-text);
        }}

        .badge-info {{
            background: var(--info-bg);
            color: var(--info-text);
        }}

        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}

        .metric {{
            background: var(--bg-tertiary);
            padding: 16px;
            border-radius: 8px;
        }}

        .metric-label {{
            color: var(--text-secondary);
            font-size: 13px;
            margin-bottom: 4px;
        }}

        .metric-value {{
            font-size: 24px;
            font-weight: 700;
            color: var(--text-primary);
        }}

        .metric-unit {{
            font-size: 14px;
            font-weight: 400;
            color: var(--text-secondary);
        }}

        .regression-alert {{
            background: var(--warning-bg);
            border-left: 4px solid var(--warning);
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}

        .regression-alert h3 {{
            color: var(--warning);
            font-size: 18px;
            margin-bottom: 12px;
        }}

        .regression-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 12px;
            margin-top: 12px;
        }}

        .alert-reason-box {{
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid;
            font-size: 14px;
            line-height: 1.6;
        }}

        .alert-reason-box strong {{
            display: block;
            font-size: 15px;
            margin-bottom: 8px;
            font-weight: 700;
        }}

        .alert-reason-danger {{
            background: var(--danger-bg);
            border-left-color: var(--danger);
            color: var(--danger-text);
        }}

        .alert-reason-success {{
            background: var(--success-bg);
            border-left-color: var(--success);
            color: var(--success-text);
        }}

        .alert-reason-warning {{
            background: var(--warning-bg);
            border-left-color: var(--warning);
            color: var(--warning-text);
        }}

        .alert-reason-info {{
            background: var(--info-bg);
            border-left-color: var(--info);
            color: var(--info-text);
        }}

        .chart-container {{
            position: relative;
            height: 400px;
            margin: 20px 0;
        }}

        .chart-container canvas {{
            cursor: grab;
        }}

        .chart-container canvas:active {{
            cursor: grabbing;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
        }}

        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--bg-tertiary);
        }}

        th {{
            background: var(--bg-tertiary);
            font-weight: 600;
            color: var(--text-primary);
        }}

        td {{
            color: var(--text-primary);
        }}

        .progress-bar {{
            width: 100%;
            height: 24px;
            background: var(--bg-tertiary);
            border-radius: 12px;
            overflow: hidden;
            margin-top: 8px;
        }}

        .progress-fill {{
            height: 100%;
            background: var(--accent-gradient);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 12px;
            font-weight: 600;
            transition: width 0.3s ease;
        }}

        .dark-mode-toggle {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--bg-secondary);
            border: none;
            padding: 12px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 20px;
            box-shadow: var(--shadow-md);
            transition: transform 0.2s;
        }}

        .dark-mode-toggle:hover {{
            transform: scale(1.1);
        }}

        /* Zoom controls */
        .zoom-controls {{
            position: absolute;
            top: 10px;
            right: 10px;
            display: flex;
            gap: 8px;
            z-index: 10;
        }}

        .zoom-btn {{
            background: var(--bg-secondary);
            border: 1px solid var(--border, rgba(0,0,0,0.1));
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
            box-shadow: var(--shadow-sm);
            transition: all 0.2s;
            user-select: none;
        }}

        .zoom-btn:hover {{
            background: var(--bg-tertiary);
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
        }}

        .zoom-btn:active {{
            transform: translateY(0);
        }}

        /* Collapsible sections */
        details {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 0;
            margin-bottom: 24px;
            box-shadow: var(--shadow-md);
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        details:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
        }}

        details summary {{
            cursor: pointer;
            padding: 24px;
            font-size: 20px;
            font-weight: 600;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 8px;
            list-style: none;
            user-select: none;
        }}

        details summary::-webkit-details-marker {{
            display: none;
        }}

        details summary::before {{
            content: '▶';
            display: inline-block;
            width: 20px;
            transition: transform 0.2s;
            color: var(--text-secondary);
        }}

        details[open] summary::before {{
            transform: rotate(90deg);
        }}

        details .details-content {{
            padding: 0 24px 24px 24px;
        }}

        @media print {{
            .dark-mode-toggle {{ display: none; }}
        }}
    </style>
</head>
<body>
    <button class="dark-mode-toggle" onclick="toggleDarkMode()" title="Toggle Dark Mode">🌙</button>

    <div class="container">
        <header>
            <h1>Main Branch Health Monitoring</h1>
            <p class="timestamp">Generated: {timestamp}</p>
        </header>

        <div class="status-banner {'alert' if overall_status == 'ALERT' else 'ok'}">
            <h2>{status_icon} {overall_status}</h2>
            <p>
                {_get_status_message(overall_status, regression_index)}
            </p>
        </div>

        <!-- Quality Assessment -->
        <div class="card">
            <div class="card-title">
                🔬 Data Quality Assessment
                <span class="badge {'badge-success' if quality_score >= 80 else 'badge-warning' if quality_score >= 60 else 'badge-danger'}">{quality_verdict}</span>
            </div>

            <div class="metric-grid">
                <div class="metric">
                    <div class="metric-label">Quality Score</div>
                    <div class="metric-value">{quality_score}<span class="metric-unit">/100</span></div>
                </div>
                <div class="metric">
                    <div class="metric-label">Series Length</div>
                    <div class="metric-value">{len(series)}<span class="metric-unit"> points</span></div>
                </div>
                <div class="metric">
                    <div class="metric-label">Trimmed Mean</div>
                    <div class="metric-value">{trimmed_mean:.2f}<span class="metric-unit"> ms</span></div>
                </div>
            </div>

            {f'<p style="color: var(--text-secondary); font-size: 13px; margin-top: 8px;">💡 Trimmed Mean excludes {len(outlier_indices)} outlier(s) to show typical performance.</p>' if outlier_indices else ''}

            <div class="progress-bar">
                <div class="progress-fill" style="width: {quality_score}%">{quality_score}%</div>
            </div>

            {_render_quality_issues(quality_issues)}
        </div>

        <!-- Outlier Analysis (if outliers detected) -->
        {_render_outlier_section(outlier_indices, series) if outlier_indices else ''}

        <!-- Time Series Chart -->
        <div class="card">
            <div class="card-title">📈 Time Series Analysis</div>
            <div class="chart-container">
                <div class="zoom-controls">
                    <button class="zoom-btn" onclick="zoomIn()" title="Zoom In">🔍+</button>
                    <button class="zoom-btn" onclick="zoomOut()" title="Zoom Out">🔍−</button>
                    <button class="zoom-btn" onclick="resetZoom()" title="Reset Zoom">↺</button>
                </div>
                <canvas id="timeSeriesChart"></canvas>
            </div>
        </div>

        <!-- Regression Location (if found) -->
        {_render_regression_alert(regression_index, stepfit) if regression_index is not None else ''}

        <!-- EWMA Results -->
        {_render_ewma(ewma) if ewma else ''}

        <!-- Step-Fit Results -->
        {_render_stepfit(stepfit) if stepfit else ''}

        <!-- Control Chart Results -->
        {_render_control_chart(control) if control else ''}

        <!-- Configuration -->
        <div class="card">
            <div class="card-title">⚙️ Configuration</div>
            <table>
                <tr>
                    <th>Parameter</th>
                    <th>Value</th>
                    <th>Description</th>
                </tr>
                <tr>
                    <td>Window Size</td>
                    <td>{report.details.get('window', 'N/A')}</td>
                    <td>Baseline window for control chart</td>
                </tr>
                <tr>
                    <td>Absolute Floor</td>
                    <td>{report.details.get('abs_floor', 'N/A')} ms</td>
                    <td>Minimum absolute change threshold</td>
                </tr>
                <tr>
                    <td>Relative Floor</td>
                    <td>{report.details.get('pct_floor', 'N/A') * 100:.1f}%</td>
                    <td>Minimum relative change threshold</td>
                </tr>
                <tr>
                    <td>Control K</td>
                    <td>{report.details.get('k_mad', 'N/A')}</td>
                    <td>Sigma multiplier for control limits</td>
                </tr>
                <tr>
                    <td>EWMA Alpha</td>
                    <td>{report.details.get('ewma_alpha', 'N/A')}</td>
                    <td>Smoothing parameter for EWMA</td>
                </tr>
            </table>
        </div>
    </div>

    <script>
        // Dark mode toggle
        function toggleDarkMode() {{
            const body = document.body;
            const currentTheme = body.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            body.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        }}

        // Load saved theme
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.body.setAttribute('data-theme', savedTheme);

        // Chart
        const ctx = document.getElementById('timeSeriesChart').getContext('2d');
        const series = {series_json};
        const regressionIndex = {regression_index if regression_index is not None else 'null'};
        const outlierIndices = {outlier_indices_json};

        // Create datasets
        const datasets = [{{
            label: 'Measured Values',
            data: series.map((val, idx) => ({{x: idx, y: val}})),
            borderWidth: 2,
            pointRadius: (ctx) => outlierIndices.includes(ctx.dataIndex) ? 6 : 3,
            pointStyle: (ctx) => outlierIndices.includes(ctx.dataIndex) ? 'triangle' : 'circle',
            pointBackgroundColor: (ctx) => {{
                if (outlierIndices.includes(ctx.dataIndex)) return '#f57c00';  // Orange for outliers
                return '#0066ff';  // Blue for all other points
            }},
            pointHoverRadius: 5,
            tension: 0.1,
            fill: true,
            borderColor: '#0066ff',  // Keep line blue throughout
            backgroundColor: 'rgba(0, 102, 255, 0.1)'  // Keep fill blue throughout
        }}];

        {_render_chart_baseline(control, len(series))}

        // Horizontal crosshair plugin
        let mouseY = null;
        let isMouseInChart = false;
        let isDragging = false;

        const horizontalLinePlugin = {{
            id: 'horizontalLine',
            afterEvent(chart, args) {{
                const {{ inChartArea }} = args;
                const event = args.event;

                // Detect dragging/panning
                if (event.type === 'mousedown') {{
                    isDragging = true;
                }} else if (event.type === 'mouseup') {{
                    isDragging = false;
                }}

                // Only show crosshair when not dragging
                if (event.type === 'mousemove' && !isDragging) {{
                    if (inChartArea) {{
                        mouseY = event.y;
                        isMouseInChart = true;
                        // Use requestAnimationFrame to avoid blocking pan gestures
                        requestAnimationFrame(() => chart.draw());
                    }} else {{
                        isMouseInChart = false;
                        requestAnimationFrame(() => chart.draw());
                    }}
                }} else if (event.type === 'mouseout') {{
                    isMouseInChart = false;
                    isDragging = false;
                    requestAnimationFrame(() => chart.draw());
                }}
            }},
            afterDatasetsDraw(chart, args, options) {{
                // Don't show crosshair while dragging/panning
                if (!isMouseInChart || mouseY === null || isDragging) return;

                const {{ ctx, chartArea: {{ top, bottom, left, right }}, scales: {{ y }} }} = chart;

                // Check if mouseY is within chart area
                if (mouseY < top || mouseY > bottom) return;

                // Draw horizontal line
                ctx.save();
                ctx.beginPath();
                ctx.moveTo(left, mouseY);
                ctx.lineTo(right, mouseY);
                ctx.lineWidth = 1;
                ctx.strokeStyle = 'rgba(255, 99, 132, 0.8)';
                ctx.setLineDash([5, 5]);
                ctx.stroke();
                ctx.restore();

                // Convert pixel Y to data value
                const dataValue = y.getValueForPixel(mouseY);
                const label = dataValue.toFixed(2) + ' ms';

                // Draw value label on the right side
                ctx.save();
                ctx.font = 'bold 12px Arial';
                const textWidth = ctx.measureText(label).width;
                const padding = 4;

                // Draw background
                ctx.fillStyle = 'rgba(255, 99, 132, 0.9)';
                ctx.fillRect(right - textWidth - padding * 2 - 5, mouseY - 10, textWidth + padding * 2, 20);

                // Draw text
                ctx.fillStyle = '#fff';
                ctx.textAlign = 'left';
                ctx.textBaseline = 'middle';
                ctx.fillText(label, right - textWidth - padding - 5, mouseY);
                ctx.restore();
            }}
        }};

        const chart = new Chart(ctx, {{
            type: 'line',
            data: {{ datasets }},
            plugins: [horizontalLinePlugin],
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {{
                    mode: 'index',
                    intersect: false
                }},
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top'
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false
                    }},
                    annotation: regressionIndex !== null ? {{
                        annotations: {{
                            regressionLine: {{
                                type: 'line',
                                xMin: regressionIndex,
                                xMax: regressionIndex,
                                borderColor: '#d32f2f',
                                borderWidth: 2,
                                borderDash: [6, 6],
                                label: {{
                                    display: true,
                                    content: `Regression at ${{regressionIndex}}`,
                                    position: 'start',
                                    backgroundColor: 'rgba(211, 47, 47, 0.9)',
                                    color: '#fff',
                                    font: {{
                                        size: 11,
                                        weight: 'bold'
                                    }},
                                    padding: 4
                                }}
                            }}
                        }}
                    }} : {{}},
                    zoom: {{
                        pan: {{
                            enabled: true,
                            mode: 'x'
                        }},
                        zoom: {{
                            wheel: {{
                                enabled: true,
                                speed: 0.1
                            }},
                            pinch: {{
                                enabled: true
                            }},
                            mode: 'x'
                        }},
                        limits: {{
                            x: {{min: 0, max: series.length - 1}}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        type: 'linear',
                        title: {{
                            display: true,
                            text: 'Data Point Index'
                        }},
                        grid: {{
                            color: 'rgba(0, 0, 0, 0.05)'
                        }}
                    }},
                    y: {{
                        title: {{
                            display: true,
                            text: 'Value (ms)'
                        }},
                        grid: {{
                            color: 'rgba(0, 0, 0, 0.05)'
                        }}
                    }}
                }}
            }}
        }});

        // Zoom control functions
        function zoomIn() {{
            chart.zoom(1.2);
        }}

        function zoomOut() {{
            chart.zoom(0.8);
        }}

        function resetZoom() {{
            chart.resetZoom();
        }}
    </script>
</body>
</html>
"""


def _assess_data_quality(series: List[float], report: Any) -> tuple:
    """Assess data quality and return score, verdict, issues, and outlier indices."""
    import numpy as np
    from main_health import detect_outliers_rolling

    score = 100
    issues = []

    # Sample size check
    n = len(series)
    if n < 10:
        score -= 30
        issues.append(("Critical", f"Very small sample size (n={n}, need ≥10)"))
    elif n < 30:
        score -= 10
        issues.append(("Warning", f"Small sample size (n={n}, recommended ≥30)"))

    # Variance check
    if n >= 2:
        arr = np.array(series)
        mean = np.mean(arr)
        std = np.std(arr)
        cv = (std / mean * 100) if mean > 0 else 0

        if cv > 20:
            score -= 25
            issues.append(("Issue", f"High variability (CV={cv:.1f}%, threshold=20%)"))
        elif cv > 10:
            score -= 10
            issues.append(("Warning", f"Moderate variability (CV={cv:.1f}%)"))

    # Outlier detection
    outlier_indices = detect_outliers_rolling(series)
    num_outliers = len(outlier_indices)

    if num_outliers > 0:
        outlier_pct = (num_outliers / len(series)) * 100
        if outlier_pct > 20:
            score -= 20
            issues.append(("Issue", f"{num_outliers} outliers detected ({outlier_pct:.1f}%). Test environment may be unstable."))
        else:
            score -= 5
            issues.append(("Warning", f"{num_outliers} outlier(s) detected. May indicate measurement noise."))

    # Determine verdict
    if score >= 90:
        verdict = "Excellent"
    elif score >= 75:
        verdict = "Good"
    elif score >= 60:
        verdict = "Fair"
    else:
        verdict = "Poor"

    return max(0, score), verdict, issues, outlier_indices


def _calculate_trimmed_mean(series: List[float], outlier_indices: List[int]) -> float:
    """
    Calculate arithmetic mean after removing outliers.

    Args:
        series: Full time-series data
        outlier_indices: Indices of detected outliers

    Returns:
        Trimmed mean value (average excluding outliers)

    Example:
        >>> series = [100, 102, 200, 98, 101]
        >>> outlier_indices = [2]  # 200 is outlier
        >>> _calculate_trimmed_mean(series, outlier_indices)
        100.25  # mean of [100, 102, 98, 101]
    """
    import numpy as np

    # Create boolean mask for non-outlier indices
    outlier_set = set(outlier_indices)
    trimmed_values = [val for i, val in enumerate(series) if i not in outlier_set]

    # Handle edge case: all values are outliers
    if not trimmed_values:
        return float(np.mean(series))  # Fall back to full mean

    return float(np.mean(trimmed_values))


def _get_status_message(status: str, regression_index: Optional[int]) -> str:
    """Get status message."""
    if status == "ALERT":
        if regression_index is not None:
            return f"Performance regression detected at index {regression_index}"
        return "Performance regression detected in latest measurements"
    return "No performance regression detected - metrics are stable"


def _render_quality_issues(issues: List[tuple]) -> str:
    """Render quality issues."""
    if not issues:
        return '<p style="color: var(--success); margin-top: 12px;">✅ No quality issues detected</p>'

    html = '<div style="margin-top: 16px;">'
    for severity, message in issues:
        color = {
            "Critical": "var(--danger)",
            "Issue": "var(--warning)",
            "Warning": "var(--info)"
        }.get(severity, "var(--text-secondary)")

        html += f'<div style="color: {color}; margin: 8px 0;">⚠ {message}</div>'

    html += '</div>'
    return html


def _render_outlier_section(outlier_indices: List[int], series: List[float]) -> str:
    """Render outlier analysis section."""
    if not outlier_indices:
        return ""

    return f"""
    <details>
        <summary>
            ⚠️ Outlier Analysis
            <span class="badge badge-warning">{len(outlier_indices)} OUTLIER{'S' if len(outlier_indices) > 1 else ''}</span>
        </summary>

        <div class="details-content">
            <p>Detected {len(outlier_indices)} outlier(s) using rolling MAD method (time-series aware):</p>

            <table>
                <tr>
                    <th>Index</th>
                    <th>Value (ms)</th>
                    <th>Description</th>
                </tr>
                {_render_outlier_rows(outlier_indices, series)}
            </table>

            <p style="margin-top: 12px; color: var(--text-secondary); font-size: 14px;">
                💡 Note: Outliers are marked with orange triangles (▲) on the chart. These represent anomalies relative to recent baseline, not systematic changes.
            </p>
        </div>
    </details>
    """


def _render_outlier_rows(outlier_indices: List[int], series: List[float]) -> str:
    """Render outlier table rows."""
    rows = ""
    for idx in outlier_indices:
        rows += f"""
            <tr>
                <td>{idx}</td>
                <td>{series[idx]:.2f} ms</td>
                <td>Anomaly detected via rolling MAD (k=3.5)</td>
            </tr>
        """
    return rows


def _render_regression_alert(index: int, stepfit: Any) -> str:
    """Render regression alert box."""
    if stepfit and stepfit.found:
        before = stepfit.before_median
        after = stepfit.after_median
        delta = stepfit.delta
    else:
        before = after = delta = None

    return f"""
    <div class="regression-alert">
        <h3>⚠️ Regression Detected at Index {index}</h3>
        <p>A changepoint was detected at data point #{index + 1}</p>
        {f'''
        <div class="regression-details">
            <div class="metric">
                <div class="metric-label">Before Median</div>
                <div class="metric-value" style="font-size: 18px;">{before:.2f}<span class="metric-unit"> ms</span></div>
            </div>
            <div class="metric">
                <div class="metric-label">After Median</div>
                <div class="metric-value" style="font-size: 18px;">{after:.2f}<span class="metric-unit"> ms</span></div>
            </div>
            <div class="metric">
                <div class="metric-label">Delta</div>
                <div class="metric-value" style="font-size: 18px; color: var(--danger);">{delta:+.2f}<span class="metric-unit"> ms</span></div>
            </div>
        </div>
        ''' if before is not None else ''}
    </div>
    """


def _render_control_chart(control: Any) -> str:
    """Render control chart results."""
    alert_class = "badge-danger" if control.alert else "badge-success"
    alert_text = "ALERT" if control.alert else "OK"
    reason_class = "alert-reason-danger" if control.alert else "alert-reason-success"
    reason_title = "⚠️ Alert Reason" if control.alert else "✓ Status"

    return f"""
    <div class="card">
        <div class="card-title">
            📊 Control Chart (Spike Detection For The Last Build)
            <span class="badge {alert_class}">{alert_text}</span>
        </div>

        <p style="margin-bottom: 16px; color: var(--text-secondary); font-size: 13px; line-height: 1.5;">
            Detects sudden spikes by comparing the latest value against a baseline window (last 30 points).
            <strong>Delta</strong> is the absolute difference between current value and baseline median.
            Alerts when <strong>BOTH</strong> conditions are met:<br/>
            1. <strong>Practical threshold</strong>: Delta &gt; max(50ms, 5% of baseline)<br/>
            2. <strong>Statistical threshold</strong>: Delta exceeds ±4.0σ (robust sigma from MAD)
        </p>

        <div class="alert-reason-box {reason_class}">
            <strong>{reason_title}:</strong>
            {control.reason}
        </div>

        <div class="metric-grid">
            <div class="metric">
                <div class="metric-label">Baseline Median</div>
                <div class="metric-value">{control.baseline_median:.2f}<span class="metric-unit"> ms</span></div>
            </div>
            <div class="metric">
                <div class="metric-label">Current Value</div>
                <div class="metric-value">{control.value:.2f}<span class="metric-unit"> ms</span></div>
            </div>
            <div class="metric">
                <div class="metric-label">Delta (Difference)</div>
                <div class="metric-value">{abs(control.value - control.baseline_median):.2f}<span class="metric-unit"> ms</span></div>
            </div>
            <div class="metric">
                <div class="metric-label">Practical Threshold</div>
                <div class="metric-value">{max(50, 0.05 * control.baseline_median):.2f}<span class="metric-unit"> ms</span></div>
            </div>
        </div>

        <div style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin: 16px 0; font-size: 13px;">
            <strong style="color: var(--text-primary);">📋 Dual-Threshold Check:</strong>
            <div style="margin-top: 8px; color: var(--text-secondary); line-height: 1.6;">
                <div style="margin: 4px 0;">
                    ✓ <strong>Condition 1 (Practical):</strong> Delta ({abs(control.value - control.baseline_median):.2f}ms) {'>' if abs(control.value - control.baseline_median) > max(50, 0.05 * control.baseline_median) else '≤'} Practical threshold ({max(50, 0.05 * control.baseline_median):.2f}ms)
                    <span style="color: {'var(--success)' if abs(control.value - control.baseline_median) > max(50, 0.05 * control.baseline_median) else 'var(--danger)'}; font-weight: bold;">{'✓ PASS' if abs(control.value - control.baseline_median) > max(50, 0.05 * control.baseline_median) else '✗ FAIL'}</span>
                </div>
                <div style="margin: 4px 0;">
                    ✓ <strong>Condition 2 (Statistical):</strong> Z-score ({min(control.robust_z, 99.99):.2f}) {'>' if control.robust_z > 4.0 else '≤'} 4.0σ threshold
                    <span style="color: {'var(--success)' if control.robust_z > 4.0 else 'var(--danger)'}; font-weight: bold;">{'✓ PASS' if control.robust_z > 4.0 else '✗ FAIL'}</span>
                </div>
                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border); color: var(--text-primary);">
                    <strong>Result:</strong> {'Both conditions passed → ALERT 🚨' if control.alert else 'At least one condition failed → OK (no alert)'}
                </div>
            </div>
        </div>

        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Description</th>
            </tr>
            <tr>
                <td>Upper Bound (4.0σ)</td>
                <td>{control.upper_bound:.2f} ms</td>
                <td>Statistical upper limit</td>
            </tr>
            <tr>
                <td>Lower Bound (4.0σ)</td>
                <td>{control.lower_bound:.2f} ms</td>
                <td>Statistical lower limit</td>
            </tr>
            <tr>
                <td>Baseline MAD</td>
                <td>{control.baseline_mad:.2f} ms</td>
                <td>Median Absolute Deviation (spread measure)</td>
            </tr>
            <tr>
                <td>Robust Z-Score</td>
                <td>{min(control.robust_z, 99.99):.2f}</td>
                <td>How many σ from baseline (secondary metric)</td>
            </tr>
        </table>
    </div>
    """


def _render_ewma(ewma: Any) -> str:
    """Render EWMA results."""
    alert_class = "badge-danger" if ewma.alert else "badge-success"
    alert_text = "ALERT" if ewma.alert else "OK"
    reason_class = "alert-reason-danger" if ewma.alert else "alert-reason-success"
    reason_title = "⚠️ Alert Reason" if ewma.alert else "✓ Status"

    return f"""
    <div class="card">
        <div class="card-title">
            📉 EWMA (Trend Detection)
            <span class="badge {alert_class}">{alert_text}</span>
        </div>

        <p style="margin-bottom: 16px; color: var(--text-secondary); font-size: 13px; line-height: 1.5;">
            Detects gradual performance creep using exponentially weighted moving average (α=0.25).
            Alerts when EWMA exceeds <strong>±3.0σ</strong> bounds OR drifts <strong>≥15%</strong> from baseline median.
        </p>

        <div class="alert-reason-box {reason_class}">
            <strong>{reason_title}:</strong>
            {ewma.reason}
        </div>

        <div class="metric-grid">
            <div class="metric">
                <div class="metric-label">EWMA Value</div>
                <div class="metric-value">{ewma.ewma:.2f}<span class="metric-unit"> ms</span></div>
            </div>
            <div class="metric">
                <div class="metric-label">Current Value</div>
                <div class="metric-value">{ewma.value:.2f}<span class="metric-unit"> ms</span></div>
            </div>
            <div class="metric">
                <div class="metric-label">Upper Bound</div>
                <div class="metric-value">{ewma.upper_bound:.2f}<span class="metric-unit"> ms</span></div>
            </div>
            <div class="metric">
                <div class="metric-label">Lower Bound</div>
                <div class="metric-value">{ewma.lower_bound:.2f}<span class="metric-unit"> ms</span></div>
            </div>
        </div>
    </div>
    """


def _render_stepfit(stepfit: Any) -> str:
    """Render step-fit results."""
    if stepfit.found:
        alert_class = "badge-warning"
        alert_text = "CHANGEPOINT FOUND"
        reason_class = "alert-reason-danger"
        reason_title = "⚠️ Alert Reason"
    else:
        alert_class = "badge-info"
        alert_text = "NO CHANGEPOINT"
        reason_class = "alert-reason-success"
        reason_title = "✓ Status"

    content = ""
    if stepfit.found:
        content = f"""
        <div class="metric-grid">
            <div class="metric">
                <div class="metric-label">Change Index</div>
                <div class="metric-value">{stepfit.change_index}<span class="metric-unit"></span></div>
            </div>
            <div class="metric">
                <div class="metric-label">Before Median</div>
                <div class="metric-value">{stepfit.before_median:.2f}<span class="metric-unit"> ms</span></div>
            </div>
            <div class="metric">
                <div class="metric-label">After Median</div>
                <div class="metric-value">{stepfit.after_median:.2f}<span class="metric-unit"> ms</span></div>
            </div>
            <div class="metric">
                <div class="metric-label">Delta</div>
                <div class="metric-value" style="color: var(--danger);">{stepfit.delta:+.2f}<span class="metric-unit"> ms</span></div>
            </div>
            <div class="metric">
                <div class="metric-label">Score</div>
                <div class="metric-value">{min(stepfit.score, 9999.99):.2f}<span class="metric-unit"></span></div>
            </div>
        </div>
        """

    explanation = """
        <p style="margin-bottom: 16px; color: var(--text-secondary); font-size: 13px; line-height: 1.5;">
            Finds the exact commit where performance changed by testing every possible split point.
            Alerts when change score exceeds <strong>4.0σ</strong> OR percentage change is <strong>≥20%</strong>.
        </p>
    """

    return f"""
    <div class="card">
        <div class="card-title">
            🔍 Step-Fit (Changepoint Detection)
            <span class="badge {alert_class}">{alert_text}</span>
        </div>

        {explanation}

        <div class="alert-reason-box {reason_class}">
            <strong>{reason_title}:</strong>
            {stepfit.reason}
        </div>

        {content}
    </div>
    """


def _render_chart_baseline(control: Any, series_len: int) -> str:
    """Render baseline bounds on chart."""
    if control is None:
        return ""

    return f"""
    // Add baseline bounds
    datasets.push({{
        label: 'Upper Bound',
        data: Array({series_len}).fill({control.upper_bound}).map((val, idx) => ({{x: idx, y: val}})),
        borderColor: 'rgba(211, 47, 47, 0.5)',
        borderWidth: 1,
        borderDash: [5, 5],
        pointRadius: 0,
        fill: false
    }});

    datasets.push({{
        label: 'Lower Bound',
        data: Array({series_len}).fill({control.lower_bound}).map((val, idx) => ({{x: idx, y: val}})),
        borderColor: 'rgba(46, 125, 50, 0.5)',
        borderWidth: 1,
        borderDash: [5, 5],
        pointRadius: 0,
        fill: false
    }});

    datasets.push({{
        label: 'Baseline Median',
        data: Array({series_len}).fill({control.baseline_median}).map((val, idx) => ({{x: idx, y: val}})),
        borderColor: 'rgba(128, 128, 128, 0.5)',
        borderWidth: 1,
        borderDash: [2, 2],
        pointRadius: 0,
        fill: false
    }});
    """
