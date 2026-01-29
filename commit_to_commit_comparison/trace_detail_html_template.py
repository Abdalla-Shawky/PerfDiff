"""HTML template for individual trace detail pages.

This template wraps the existing perf_html_report with navigation.
"""

import numpy as np
from html import escape

from .perf_html_report import render_html_report
from .commit_to_commit_comparison import GateResult


def render_trace_detail_template(
    trace_name: str,
    baseline: np.ndarray,
    target: np.ndarray,
    result: GateResult,
    prev_trace: str = None,
    next_trace: str = None,
    comparison_page_url: str = "index.html"
) -> str:
    """Render detail page with navigation.

    Args:
        trace_name: Name of the trace
        baseline: Baseline measurements array
        target: Target measurements array
        result: GateResult from gate_regression()
        prev_trace: Name of previous trace (for navigation)
        next_trace: Name of next trace (for navigation)
        comparison_page_url: URL to return to comparison page

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
        title="TrustTrace",
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

    nav_bar = f"""
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

    # Insert navigation bar and styles into the base HTML
    # Find the closing </head> tag and insert nav styles before it
    html_with_nav_styles = base_html.replace('</head>', f'{nav_styles}\n</head>')

    # Find the opening <body> tag and insert nav bar after it
    html_with_nav = html_with_nav_styles.replace('<body>', f'<body>\n{nav_bar}')

    return html_with_nav
