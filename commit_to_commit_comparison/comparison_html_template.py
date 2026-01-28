"""HTML template for the Performance Comparison table page.

This template displays all trace comparisons in a table view with search functionality.
"""

import numpy as np
from html import escape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from multi_trace_comparison import MultiTraceResult


def _fmt_ms(value: float) -> str:
    """Format milliseconds with appropriate precision."""
    if abs(value) < 1:
        return f"{value:.2f}ms"
    elif abs(value) < 10:
        return f"{value:.1f}ms"
    else:
        return f"{value:.0f}ms"


def render_comparison_template(result: 'MultiTraceResult') -> str:
    """Render the comparison table HTML page.

    Args:
        result: MultiTraceResult from compare_traces()

    Returns:
        Complete HTML string for the comparison page
    """
    # Calculate summary stats
    stats = result.get_summary_stats()

    # Build warning banner HTML
    warning_html = ""
    if result.warnings:
        warning_items = "\n".join([f"<li>{escape(w)}</li>" for w in result.warnings])
        warning_html = f"""
        <details class="warning-banner">
          <summary class="warning-summary">
            <span class="warning-icon">⚠️</span>
            <span class="warning-title">Warnings</span>
            <span class="warning-count">{len(result.warnings)}</span>
          </summary>
          <div class="warning-content">
            <ul class="warning-list">
              {warning_items}
            </ul>
          </div>
        </details>
        """

    # Build table rows
    table_rows = []
    for comparison in result.comparisons:
        name = comparison.name
        result_obj = comparison.gate_result
        baseline_arr = np.array(comparison.baseline_data)
        target_arr = np.array(comparison.target_data)

        baseline_median = float(np.median(baseline_arr))
        target_median = float(np.median(target_arr))
        delta = target_median - baseline_median

        # Determine status
        if result_obj.inconclusive:
            status = "INCONCLUSIVE ⚠️"
            status_class = "inconclusive"
        elif result_obj.no_change:
            status = "NO CHANGE ⚖️"
            status_class = "no-change"
        elif result_obj.passed:
            status = "PASS ✅"
            status_class = "pass"
        else:
            status = "FAIL ❌"
            status_class = "fail"

        # Format delta with sign and color
        delta_sign = "+" if delta >= 0 else ""
        delta_formatted = f"{delta_sign}{_fmt_ms(delta)}"
        delta_class = "positive" if delta > 0 else "negative" if delta < 0 else "neutral"

        row_html = f"""
        <tr class="trace-row" data-trace-name="{escape(name)}">
          <td class="trace-name-cell">
            <span class="trace-name">{escape(name)}</span>
          </td>
          <td class="status-cell">
            <span class="status-badge {status_class}">{status}</span>
          </td>
          <td class="numeric-cell">{_fmt_ms(baseline_median)}</td>
          <td class="numeric-cell">{_fmt_ms(target_median)}</td>
          <td class="numeric-cell delta-{delta_class}">{delta_formatted}</td>
          <td class="action-cell">
            <a href="{escape(name)}.html" class="view-details-btn">View Details</a>
          </td>
        </tr>
        """
        table_rows.append(row_html)

    table_body = "\n".join(table_rows)

    # Build complete HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Performance Comparison - Multi-Trace Report</title>
  <style>
    /* Reset and base styles */
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}

    /* CSS Variables - matching perf_html_template.py theme */
    :root {{
      /* Dark Theme (Emerge Tools style) */
      --bg-primary: rgba(15, 20, 25, 0.85);
      --bg-secondary: rgba(26, 31, 41, 0.95);
      --bg-tertiary: rgba(36, 43, 56, 0.9);
      --text-primary: #e0e0e0;
      --text-secondary: #a0a0a0;
      --border-color: rgba(255, 255, 255, 0.1);
      --card-bg: rgba(26, 31, 41, 0.8);

      /* Accent & Gradients */
      --accent-primary: #0066ff;
      --accent-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

      /* Status Colors */
      --color-success: #4caf50;
      --color-error: #f44336;
      --color-warning: #ff9800;
      --color-info: #2196f3;

      /* Shadows */
      --shadow-xs: 0 1px 2px 0 rgba(0,0,0,0.3);
      --shadow-sm: 0 1px 3px 0 rgba(0,0,0,0.3), 0 0 10px rgba(120, 119, 198, 0.1);
      --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.4), 0 0 15px rgba(120, 119, 198, 0.15);
      --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.5), 0 0 20px rgba(120, 119, 198, 0.2);

      /* Spacing scale */
      --space-1: 4px;
      --space-2: 8px;
      --space-3: 12px;
      --space-4: 16px;
      --space-5: 20px;
      --space-6: 24px;

      /* Border radius */
      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 14px;
      --radius-xl: 20px;

      /* Animation */
      --anim-fast: 150ms;
      --anim-normal: 250ms;
      --anim-slow: 400ms;
    }}

    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');

    body {{
      font-family: "Space Grotesk", "Sora", "Avenir Next", "Helvetica Neue", sans-serif;
      background: #0a0e12;
      color: var(--text-primary);
      line-height: 1.6;
      min-height: 100vh;
      position: relative;
      overflow-x: hidden;
    }}

    /* Animated background */
    #bg-canvas {{
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      z-index: 0;
      opacity: 0.8;
    }}

    /* Glow effects */
    @keyframes glow {{
      0%, 100% {{ box-shadow: 0 0 5px rgba(102, 126, 234, 0.3), 0 0 10px rgba(102, 126, 234, 0.2); }}
      50% {{ box-shadow: 0 0 20px rgba(102, 126, 234, 0.5), 0 0 30px rgba(102, 126, 234, 0.3); }}
    }}

    /* Header */
    .header {{
      position: sticky;
      top: 0;
      z-index: 100;
      background:
        radial-gradient(1200px 200px at 10% -50%, rgba(255, 152, 0, 0.18), transparent 60%),
        radial-gradient(900px 200px at 90% -40%, rgba(0, 200, 180, 0.18), transparent 55%),
        linear-gradient(180deg, rgba(16, 20, 26, 0.98), rgba(12, 16, 22, 0.96));
      backdrop-filter: blur(10px);
      border-bottom: 1px solid var(--border-color);
      padding: var(--space-4) var(--space-5);
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.35), 0 0 28px rgba(0, 200, 180, 0.12);
    }}

    .header::before {{
      content: "";
      position: absolute;
      inset: 0 0 auto 0;
      height: 2px;
      background: linear-gradient(90deg, rgba(255, 152, 0, 0.9), rgba(0, 200, 180, 0.9), rgba(255, 152, 0, 0.9));
    }}

    .header-content {{
      max-width: 1400px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: var(--space-4);
    }}

    .header-left {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .header-kicker {{
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--text-muted);
    }}

    .header-title {{
      font-size: 30px;
      font-weight: 700;
      color: #f4f8ff;
      text-shadow: 0 2px 16px rgba(0, 200, 180, 0.25);
    }}

    .header-subtitle {{
      font-size: 14px;
      color: var(--text-secondary);
      margin-top: 2px;
    }}

    .header-right {{
      display: flex;
      align-items: center;
      gap: var(--space-3);
    }}

    .header-chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      border-radius: 999px;
      background: rgba(0, 200, 180, 0.12);
      border: 1px solid rgba(0, 200, 180, 0.45);
      color: #d8fff7;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      box-shadow: 0 0 18px rgba(0, 200, 180, 0.18);
    }}

    .header-meta {{
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 6px 12px;
      border-radius: 12px;
      background: rgba(255, 152, 0, 0.12);
      border: 1px solid rgba(255, 152, 0, 0.45);
      color: #ffe1b8;
      font-size: 12px;
      font-weight: 600;
    }}

    /* Container */
    .container {{
      position: relative;
      z-index: 1;
      max-width: 1400px;
      margin: 0 auto;
      padding: var(--space-6);
    }}

    /* Warning banner */
    .warning-banner {{
      background: rgba(255, 152, 0, 0.1);
      border: 1px solid rgba(255, 152, 0, 0.3);
      border-radius: var(--radius-lg);
      padding: var(--space-3) var(--space-4);
      margin-bottom: var(--space-6);
      box-shadow: 0 0 15px rgba(255, 152, 0, 0.2);
    }}

    .warning-summary {{
      list-style: none;
      display: flex;
      align-items: center;
      gap: var(--space-3);
      cursor: pointer;
      user-select: none;
    }}

    .warning-summary::-webkit-details-marker {{
      display: none;
    }}

    .warning-summary::after {{
      content: "▾";
      margin-left: auto;
      color: var(--color-warning);
      font-size: 14px;
      transition: transform var(--anim-fast) ease;
    }}

    details[open] > .warning-summary::after {{
      transform: rotate(180deg);
    }}

    .warning-count {{
      font-size: 12px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 999px;
      background: rgba(255, 152, 0, 0.2);
      color: var(--color-warning);
    }}

    .warning-content {{
      margin-top: var(--space-3);
      padding-left: 34px;
    }}

    .warning-icon {{
      font-size: 20px;
      flex-shrink: 0;
    }}

    .warning-title {{
      font-weight: 600;
      font-size: 16px;
      color: var(--color-warning);
    }}

    .warning-list {{
      list-style: none;
      color: var(--text-secondary);
      font-size: 14px;
    }}

    .warning-list li {{
      margin-bottom: var(--space-1);
    }}

    .warning-banner[open] {{
      box-shadow: 0 0 18px rgba(255, 152, 0, 0.28);
    }}

    /* Summary stats */
    .summary-stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: var(--space-4);
      margin-bottom: var(--space-6);
    }}

    .stat-card {{
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: var(--space-5);
      text-align: center;
      transition: transform var(--anim-normal) ease, box-shadow var(--anim-normal) ease;
      box-shadow: 0 0 10px rgba(102, 126, 234, 0.1);
    }}

    .stat-card:hover {{
      transform: translateY(-4px);
      box-shadow: 0 0 20px rgba(102, 126, 234, 0.3), 0 4px 12px rgba(0, 0, 0, 0.4);
      animation: glow 2s ease-in-out infinite;
    }}

    .stat-value {{
      font-size: 36px;
      font-weight: 700;
      margin-bottom: var(--space-2);
    }}

    .stat-value.total {{ color: var(--text-primary); }}
    .stat-value.pass {{ color: var(--color-success); }}
    .stat-value.fail {{ color: var(--color-error); }}
    .stat-value.no-change {{ color: var(--color-info); }}
    .stat-value.inconclusive {{ color: var(--color-warning); }}

    .stat-label {{
      font-size: 14px;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    /* Search box */
    .search-container {{
      margin-bottom: var(--space-5);
    }}

    .search-box {{
      width: 100%;
      max-width: 500px;
      padding: var(--space-3) var(--space-4);
      background: var(--bg-tertiary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      color: var(--text-primary);
      font-size: 15px;
      transition: border-color var(--anim-normal) ease, box-shadow var(--anim-normal) ease;
      box-shadow: 0 0 10px rgba(102, 126, 234, 0.1);
    }}

    .search-box:focus {{
      outline: none;
      border-color: var(--accent-primary);
      box-shadow: 0 0 0 3px rgba(0, 102, 255, 0.2), 0 0 20px rgba(102, 126, 234, 0.4);
    }}

    .search-box::placeholder {{
      color: var(--text-secondary);
    }}

    /* Table */
    .table-container {{
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      overflow: hidden;
      box-shadow: var(--shadow-lg), 0 0 30px rgba(102, 126, 234, 0.15);
    }}

    .comparison-table {{
      width: 100%;
      border-collapse: collapse;
    }}

    .comparison-table th {{
      background: var(--bg-tertiary);
      padding: var(--space-4);
      text-align: left;
      font-weight: 600;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-secondary);
      border-bottom: 2px solid var(--border-color);
    }}

    .comparison-table td {{
      padding: var(--space-3) var(--space-4);
      border-bottom: 1px solid var(--border-color);
    }}

    .trace-row {{
      transition: background-color var(--anim-fast) ease;
    }}

    .trace-row:hover {{
      background: rgba(255, 255, 255, 0.03);
    }}

    .trace-row:last-child td {{
      border-bottom: none;
    }}

    .trace-name {{
      font-weight: 500;
      font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
      font-size: 14px;
    }}

    .numeric-cell {{
      font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
      font-size: 14px;
    }}

    .delta-positive {{ color: var(--color-error); }}
    .delta-negative {{ color: var(--color-success); }}
    .delta-neutral {{ color: var(--text-secondary); }}

    /* Status badge */
    .status-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border-radius: var(--radius-sm);
      font-size: 13px;
      font-weight: 600;
      white-space: nowrap;
    }}

    .status-badge.pass {{
      background: rgba(76, 175, 80, 0.15);
      color: var(--color-success);
      box-shadow: 0 0 10px rgba(76, 175, 80, 0.2);
    }}

    .status-badge.fail {{
      background: rgba(244, 67, 54, 0.15);
      color: var(--color-error);
      box-shadow: 0 0 10px rgba(244, 67, 54, 0.2);
    }}

    .status-badge.no-change {{
      background: rgba(33, 150, 243, 0.15);
      color: var(--color-info);
      box-shadow: 0 0 10px rgba(33, 150, 243, 0.2);
    }}

    .status-badge.inconclusive {{
      background: rgba(255, 152, 0, 0.15);
      color: var(--color-warning);
      box-shadow: 0 0 10px rgba(255, 152, 0, 0.2);
    }}

    /* View details button */
    .view-details-btn {{
      display: inline-block;
      padding: 8px 16px;
      background: var(--accent-primary);
      color: white;
      text-decoration: none;
      border-radius: var(--radius-sm);
      font-size: 13px;
      font-weight: 600;
      transition: all var(--anim-normal) ease;
      border: none;
      cursor: pointer;
    }}

    .view-details-btn:hover {{
      background: #0052cc;
      transform: translateY(-2px);
      box-shadow: 0 0 20px rgba(0, 102, 255, 0.6), 0 4px 12px rgba(0, 0, 0, 0.4);
    }}

    /* Responsive design */
    @media (max-width: 900px) {{
      .header-content {{
        flex-direction: column;
        align-items: flex-start;
      }}

      .summary-stats {{
        grid-template-columns: repeat(2, 1fr);
      }}

      .comparison-table {{
        font-size: 13px;
      }}

      .comparison-table th,
      .comparison-table td {{
        padding: var(--space-2) var(--space-3);
      }}
    }}

    @media (max-width: 600px) {{
      .container {{
        padding: var(--space-4);
      }}

      .summary-stats {{
        grid-template-columns: 1fr;
      }}

      .stat-value {{
        font-size: 28px;
      }}
    }}
  </style>
</head>
<body>
  <!-- Animated background canvas -->
  <canvas id="bg-canvas"></canvas>

  <!-- Header -->
  <div class="header">
    <div class="header-content">
      <div class="header-left">
        <div class="header-kicker">Performance Intelligence</div>
        <h1 class="header-title">CompaX</h1>
        <div class="header-subtitle">Multi-Trace Regression Report</div>
      </div>
      <div class="header-right">
        <div class="header-chip">Live Report</div>
        <div class="header-meta">Updated {escape(result.timestamp)}</div>
      </div>
    </div>
  </div>

  <!-- Main content -->
  <div class="container">
    {warning_html}

    <!-- Summary statistics -->
    <div class="summary-stats">
      <div class="stat-card">
        <div class="stat-value total">{stats['total']}</div>
        <div class="stat-label">Total Traces</div>
      </div>
      <div class="stat-card">
        <div class="stat-value pass">{stats['pass']}</div>
        <div class="stat-label">Pass</div>
      </div>
      <div class="stat-card">
        <div class="stat-value fail">{stats['fail']}</div>
        <div class="stat-label">Fail</div>
      </div>
      <div class="stat-card">
        <div class="stat-value no-change">{stats['no_change']}</div>
        <div class="stat-label">No Change</div>
      </div>
      <div class="stat-card">
        <div class="stat-value inconclusive">{stats['inconclusive']}</div>
        <div class="stat-label">Inconclusive</div>
      </div>
    </div>

    <!-- Search box -->
    <div class="search-container">
      <input
        type="text"
        id="trace-search"
        class="search-box"
        placeholder="🔍 Search traces by name..."
        oninput="filterTraces()"
      />
    </div>

    <!-- Comparison table -->
    <div class="table-container">
      <table class="comparison-table">
        <thead>
          <tr>
            <th>Trace Name</th>
            <th>Status</th>
            <th>Baseline Median</th>
            <th>Target Median</th>
            <th>Delta (Δ)</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {table_body}
        </tbody>
      </table>
    </div>
  </div>

  <script>
    // Search/filter functionality
    function filterTraces() {{
      const searchTerm = document.getElementById('trace-search').value.toLowerCase();
      const rows = document.querySelectorAll('.trace-row');

      rows.forEach(row => {{
        const traceName = row.dataset.traceName.toLowerCase();
        row.style.display = traceName.includes(searchTerm) ? '' : 'none';
      }});
    }}

    // Animated background (stars and meteors)
    const canvas = document.getElementById('bg-canvas');
    const ctx = canvas.getContext('2d');

    function resizeCanvas() {{
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }}

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Stars - many more for a richer background
    const stars = [];
    for (let i = 0; i < 250; i++) {{
      stars.push({{
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        radius: Math.random() * 2,
        opacity: Math.random() * 0.8 + 0.2,
        twinkleSpeed: Math.random() * 0.03 + 0.01
      }});
    }}

    // Meteors
    const meteors = [];
    function createMeteor() {{
      meteors.push({{
        x: Math.random() * canvas.width,
        y: -10,
        length: Math.random() * 80 + 20,
        speed: Math.random() * 3 + 2,
        opacity: Math.random() * 0.5 + 0.5
      }});
    }}

    setInterval(createMeteor, 3000);

    function animate() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw stars with enhanced twinkle
      stars.forEach(star => {{
        // Add subtle glow to brighter stars
        if (star.opacity > 0.7) {{
          ctx.shadowBlur = 3;
          ctx.shadowColor = `rgba(200, 200, 255, ${{star.opacity * 0.5}})`;
        }} else {{
          ctx.shadowBlur = 0;
        }}

        ctx.fillStyle = `rgba(255, 255, 255, ${{star.opacity}})`;
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
        ctx.fill();

        // Enhanced twinkle effect
        star.opacity += (Math.random() - 0.5) * star.twinkleSpeed;
        star.opacity = Math.max(0.2, Math.min(1, star.opacity));
      }});

      ctx.shadowBlur = 0;

      // Draw meteors
      meteors.forEach((meteor, index) => {{
        const gradient = ctx.createLinearGradient(
          meteor.x, meteor.y,
          meteor.x + meteor.length * 0.5, meteor.y + meteor.length * 0.5
        );
        gradient.addColorStop(0, `rgba(120, 119, 198, ${{meteor.opacity}})`);
        gradient.addColorStop(1, 'rgba(120, 119, 198, 0)');

        ctx.strokeStyle = gradient;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(meteor.x, meteor.y);
        ctx.lineTo(meteor.x + meteor.length * 0.5, meteor.y + meteor.length * 0.5);
        ctx.stroke();

        meteor.y += meteor.speed;
        meteor.x += meteor.speed * 0.5;

        // Remove meteors that are off-screen
        if (meteor.y > canvas.height + 100) {{
          meteors.splice(index, 1);
        }}
      }});

      requestAnimationFrame(animate);
    }}

    animate();
  </script>
</body>
</html>
"""

    return html
