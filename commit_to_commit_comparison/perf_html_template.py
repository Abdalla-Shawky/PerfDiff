#!/usr/bin/env python3
"""
HTML Template for Performance Regression Reports

This module contains the HTML/CSS/JavaScript template used by perf_html_report.py
to generate interactive performance regression reports.
"""

from html import escape
from constants import (
    ENABLE_QUALITY_GATES, MAX_CV_FOR_REGRESSION_CHECK, MIN_SAMPLES_FOR_REGRESSION,
    CV_THRESHOLD_MULTIPLIER, MS_FLOOR, PCT_FLOOR, TAIL_MS_FLOOR, TAIL_PCT_FLOOR,
    DIRECTIONALITY, MANN_WHITNEY_ALPHA, CHARTJS_CDN_URL,
    ANIMATION_DURATION_FAST, ANIMATION_DURATION_NORMAL, ANIMATION_DURATION_SLOW,
    CHART_COLOR_BASELINE, CHART_COLOR_TARGET_IMPROVEMENT, CHART_COLOR_TARGET_REGRESSION,
    CHART_COLOR_NEUTRAL, LIGHT_BG_PRIMARY, LIGHT_BG_SECONDARY, LIGHT_BG_TERTIARY,
    LIGHT_TEXT_PRIMARY, LIGHT_TEXT_SECONDARY, LIGHT_BORDER,
    DARK_BG_PRIMARY, DARK_BG_SECONDARY, DARK_BG_TERTIARY,
    DARK_TEXT_PRIMARY, DARK_TEXT_SECONDARY, DARK_BORDER,
)


def render_template(**context) -> str:
    """Render HTML performance regression report from template variables."""
    # Make context variables available as local variables for f-string
    # This allows using {title} instead of {context['title']} in the template
    title = context['title']
    passed = context['passed']
    inconclusive = context['inconclusive']
    status = context['status']
    status_color = context['status_color']
    now = context['now']
    base_med = context['base_med']
    target_med = context['target_med']
    delta_med = context['delta_med']
    base_p90 = context['base_p90']
    target_p90 = context['target_p90']
    delta_p90 = context['delta_p90']
    pos_frac = context['pos_frac']
    pct_change = context['pct_change']
    simple_verdict = context['simple_verdict']
    recommendation = context['recommendation']
    change_icon = context['change_icon']
    change_color = context['change_color']
    a = context['a']
    b = context['b']
    d = context['d']
    baseline_quality = context['baseline_quality']
    target_quality = context['target_quality']
    overall_quality_score = context['overall_quality_score']
    overall_quality_verdict = context['overall_quality_verdict']
    overall_quality_class = context['overall_quality_class']
    result = context['result']
    _fmt_ms = context['_fmt_ms']
    _mini_table = context['_mini_table']
    bar = context['bar']
    escape = context['escape']
    np = context['np']
    summary_rows = context['summary_rows']
    runs_rows = context['runs_rows']
    wil_rows = context['wil_rows']
    bci_rows = context['bci_rows']
    bci_interpretation = context.get('bci_interpretation', '')
    eq_rows = context['eq_rows']
    eq = context['eq']
    mode = context['mode']
    max_run = context['max_run']
    baseline_data_json = context['baseline_data_json']
    target_data_json = context['target_data_json']
    delta_data_json = context['delta_data_json']
    export_data_json = context['export_data_json']
    chart_target_color = context['chart_target_color']
    practical_impact = context.get('practical_impact', {})

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{escape(title)} - Perf Report</title>

  <!-- Chart.js for interactive visualizations -->
  <script src="{CHARTJS_CDN_URL}" crossorigin="anonymous"></script>

  <style>
    /* ============================================================================
       CSS CUSTOM PROPERTIES (CSS Variables) FOR THEMING
       ============================================================================ */
    :root {{
      /* Emerge Tools Dark Theme */
      --bg-primary: rgba(15, 20, 25, 0.85);
      --bg-secondary: rgba(26, 31, 41, 0.95);
      --bg-tertiary: rgba(36, 43, 56, 0.9);
      --text-primary: #e0e0e0;
      --text-secondary: #a0a0a0;
      --border-color: rgba(255, 255, 255, 0.1);
      --card-bg: rgba(26, 31, 41, 0.8);
      --accent-primary: #0066ff;
      --accent-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

      /* Status colors for dark theme */
      --color-success: #4caf50;
      --color-success-bg: rgba(27, 94, 32, 0.8);
      --color-error: #f44336;
      --color-error-bg: rgba(183, 28, 28, 0.8);
      --color-warning: #ff9800;
      --color-warning-bg: rgba(230, 81, 0, 0.8);
      --color-info: #2196f3;
      --color-info-bg: rgba(1, 87, 155, 0.8);

      /* Chart colors */
      --chart-baseline: {CHART_COLOR_BASELINE};
      --chart-improvement: {CHART_COLOR_TARGET_IMPROVEMENT};
      --chart-regression: {CHART_COLOR_TARGET_REGRESSION};

      /* Animation durations */
      --anim-fast: {ANIMATION_DURATION_FAST}ms;
      --anim-normal: {ANIMATION_DURATION_NORMAL}ms;
      --anim-slow: {ANIMATION_DURATION_SLOW}ms;

      /* Shadows with glow for dark theme */
      --shadow-xs: 0 1px 2px 0 rgba(0,0,0,0.3);
      --shadow-sm: 0 1px 3px 0 rgba(0,0,0,0.3), 0 0 10px rgba(120, 119, 198, 0.1);
      --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.4), 0 0 15px rgba(120, 119, 198, 0.15);
      --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.5), 0 0 20px rgba(120, 119, 198, 0.2);
      --shadow-xl: 0 20px 25px -5px rgba(0,0,0,0.5), 0 0 25px rgba(120, 119, 198, 0.25);

      /* Spacing scale */
      --space-1: 4px;
      --space-2: 8px;
      --space-3: 12px;
      --space-4: 16px;
      --space-6: 24px;
      --space-8: 32px;

      /* Border radius scale */
      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 14px;
      --radius-xl: 20px;
    }}


    /* Smooth transitions for theme changes */
    * {{
      transition: background-color var(--anim-normal) ease,
                  color var(--anim-normal) ease,
                  border-color var(--anim-normal) ease,
                  box-shadow var(--anim-normal) ease;
    }}

    /* Disable transitions for immediate feedback on clicks */
    *, *::before, *::after {{
      transition-property: background-color, color, border-color, box-shadow, transform, opacity;
    }}

    /* Base styles with premium typography */
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      margin: 0;
      padding: 0;
      background: #000000;  /* Emerge Tools style - pure black background */
      color: var(--text-primary);
      line-height: 1.6;
      font-size: 15px;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      position: relative;
      overflow-x: hidden;
    }}

    /* Import Inter font for premium typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Premium Header */
    .header {{
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border-color);
      padding: 20px 32px;
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: var(--shadow-md);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 20px;
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
    }}

    .header-left {{
      flex: 1;
      min-width: 200px;
    }}

    .header-right {{
      display: flex;
      gap: 12px;
      align-items: center;
    }}

    h1 {{
      margin: 0;
      font-size: 26px;
      font-weight: 700;
      color: var(--text-primary);
      letter-spacing: -0.5px;
      background: var(--accent-gradient);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }}

    [data-theme="dark"] h1 {{
      background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }}

    .meta {{
      color: var(--text-secondary);
      font-size: 13px;
      margin-top: 6px;
      font-weight: 500;
      letter-spacing: 0.3px;
    }}

    .container {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }}

    /* Premium Control Buttons */
    .control-btn {{
      background: var(--bg-tertiary);
      border: 1px solid var(--border-color);
      color: var(--text-primary);
      padding: 10px 18px;
      border-radius: var(--radius-md);
      cursor: pointer;
      font-size: 14px;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all var(--anim-fast) cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: var(--shadow-xs);
    }}

    .control-btn:hover {{
      transform: translateY(-2px);
      box-shadow: var(--shadow-lg);
      background: var(--bg-secondary);
      border-color: var(--accent-primary);
    }}

    .control-btn:active {{
      transform: translateY(0);
      box-shadow: var(--shadow-sm);
    }}

    .icon-btn {{
      background: var(--bg-tertiary);
      border: 1px solid var(--border-color);
      padding: 10px;
      cursor: pointer;
      font-size: 20px;
      border-radius: var(--radius-md);
      width: 42px;
      height: 42px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      transition: all var(--anim-fast) cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: var(--shadow-xs);
    }}

    .icon-btn:hover {{
      background: var(--bg-secondary);
      transform: translateY(-2px);
      box-shadow: var(--shadow-lg);
      border-color: var(--accent-primary);
    }}

    .icon-btn:active {{
      transform: scale(0.95);
    }}

    /* Export dropdown */
    .export-dropdown {{
      position: relative;
      display: inline-block;
    }}

    .export-menu {{
      display: none;
      position: absolute;
      right: 0;
      top: 100%;
      margin-top: 4px;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      box-shadow: var(--shadow-lg);
      min-width: 160px;
      z-index: 1000;
    }}

    .export-dropdown.active .export-menu {{
      display: block;
      animation: fadeIn var(--anim-fast) ease;
    }}

    .export-menu button {{
      width: 100%;
      padding: 10px 16px;
      border: none;
      background: transparent;
      text-align: left;
      cursor: pointer;
      font-size: 14px;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 8px;
      transition: background-color var(--anim-fast) ease;
    }}

    .export-menu button:hover {{
      background: var(--bg-tertiary);
    }}

    .export-menu button:first-child {{
      border-radius: 8px 8px 0 0;
    }}

    .export-menu button:last-child {{
      border-radius: 0 0 8px 8px;
    }}

    /* Premium Executive Summary */
    .executive-summary {{
      background: var(--bg-secondary);
      border-radius: var(--radius-xl);
      padding: 48px;
      margin-bottom: 32px;
      box-shadow: var(--shadow-xl);
      animation: slideUp var(--anim-slow) ease;
      border: 1px solid var(--border-color);
      position: relative;
      overflow: hidden;
    }}

    .executive-summary::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 4px;
      background: var(--accent-gradient);
    }}

    .big-status {{
      font-size: 56px;
      font-weight: 800;
      margin-bottom: 20px;
      text-align: center;
      animation: scaleIn var(--anim-normal) ease;
      letter-spacing: -1px;
      text-transform: uppercase;
    }}

    .big-status.pass {{
      color: var(--color-success);
      text-shadow: 0 2px 10px rgba(16, 185, 129, 0.3);
    }}
    .big-status.fail {{
      color: var(--color-error);
      text-shadow: 0 2px 10px rgba(239, 68, 68, 0.3);
    }}
    .big-status.inconclusive {{
      color: var(--color-warning);
      text-shadow: 0 2px 10px rgba(245, 158, 11, 0.3);
    }}
    .big-status.no-change {{
      color: var(--color-info);
      text-shadow: 0 2px 10px rgba(33, 150, 243, 0.3);
    }}

    .verdict {{
      font-size: 24px;
      font-weight: 700;
      margin-bottom: 24px;
      text-align: center;
      color: var(--text-primary);
      letter-spacing: -0.3px;
    }}

    .recommendation {{
      font-size: 16px;
      padding: 24px 28px;
      background: var(--bg-tertiary);
      border-radius: var(--radius-lg);
      margin: 32px 0;
      text-align: center;
      line-height: 1.8;
      border: 1px solid var(--border-color);
      box-shadow: var(--shadow-sm);
      font-weight: 500;
    }}

    .comparison {{
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      gap: 24px;
      align-items: center;
      margin: 32px 0;
    }}

    .comparison-item {{
      text-align: center;
      padding: 32px 24px;
      background: var(--bg-tertiary);
      border-radius: var(--radius-lg);
      border: 2px solid var(--border-color);
      transition: all var(--anim-fast) cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
      overflow: hidden;
    }}

    .comparison-item::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: var(--accent-gradient);
      opacity: 0;
      transition: opacity var(--anim-fast) ease;
    }}

    .comparison-item:hover {{
      transform: translateY(-4px);
      box-shadow: var(--shadow-xl);
      border-color: var(--accent-primary);
    }}

    .comparison-item:hover::before {{
      opacity: 1;
    }}

    .comparison-label {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--text-secondary);
      margin-bottom: 12px;
      font-weight: 700;
    }}

    .comparison-value {{
      font-size: 40px;
      font-weight: 800;
      color: var(--text-primary);
      margin: 12px 0;
      letter-spacing: -1px;
    }}

    .comparison-arrow {{
      font-size: 48px;
      color: {change_color};
      opacity: 0.9;
      filter: drop-shadow(0 2px 8px {change_color}40);
    }}

    /* Premium Collapsible Sections */
    .section {{
      background: var(--bg-secondary);
      border-radius: var(--radius-lg);
      padding: 28px;
      margin-bottom: 20px;
      box-shadow: var(--shadow-md);
      border: 1px solid var(--border-color);
      animation: fadeIn var(--anim-normal) ease;
      transition: all var(--anim-fast) ease;
    }}

    .section:hover {{
      box-shadow: var(--shadow-lg);
    }}

    .section-header {{
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      user-select: none;
      padding: 12px;
      margin: -12px;
      border-radius: var(--radius-md);
      transition: all var(--anim-fast) ease;
    }}

    .section-header:hover {{
      background: var(--bg-tertiary);
    }}

    .section-title {{
      font-size: 20px;
      font-weight: 700;
      color: var(--text-primary);
      margin: 0;
      letter-spacing: -0.3px;
    }}

    .section-subtitle {{
      font-size: 14px;
      color: var(--text-secondary);
      margin-top: 6px;
      font-weight: 500;
    }}

    .toggle-icon {{
      font-size: 24px;
      color: var(--text-secondary);
      transition: transform var(--anim-normal) cubic-bezier(0.4, 0, 0.2, 1);
      background: var(--bg-tertiary);
      width: 32px;
      height: 32px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
    }}

    .section-content {{
      margin-top: 24px;
      max-height: 0;
      overflow: hidden;
      opacity: 0;
      transition: max-height var(--anim-normal) ease, opacity var(--anim-normal) ease;
    }}

    .section-content.show {{
      max-height: 10000px;
      opacity: 1;
    }}

    .section.expanded .toggle-icon {{
      transform: rotate(180deg);
      background: var(--accent-primary);
      color: white;
    }}

    /* Charts container */
    .chart-container {{
      position: relative;
      height: 350px;
      margin: 20px 0;
    }}

    .chart-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 24px;
      margin: 20px 0;
    }}

    /* Premium Tables */
    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 16px 0;
      border-radius: var(--radius-md);
      overflow: hidden;
      box-shadow: var(--shadow-xs);
    }}

    td, th {{
      border-bottom: 1px solid var(--border-color);
      padding: 14px 16px;
      text-align: left;
      font-size: 14px;
    }}

    th {{
      font-weight: 700;
      background: var(--bg-tertiary);
      color: var(--text-primary);
      text-transform: uppercase;
      font-size: 12px;
      letter-spacing: 0.5px;
      border-bottom: 2px solid var(--border-color);
    }}

    tr {{
      transition: background-color var(--anim-fast) ease;
    }}

    tr:hover {{
      background: var(--bg-tertiary);
    }}

    tbody tr:last-child td {{
      border-bottom: none;
    }}

    /* Premium Cards and Grid */
    .card {{
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 24px;
      margin: 16px 0;
      background: var(--bg-secondary);
      box-shadow: var(--shadow-sm);
      transition: all var(--anim-fast) ease;
    }}

    .card:hover {{
      box-shadow: var(--shadow-md);
      transform: translateY(-2px);
    }}

    .grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }}

    .card h3 {{
      margin-top: 0;
      margin-bottom: 20px;
      font-size: 18px;
      font-weight: 700;
      color: var(--text-primary);
      letter-spacing: -0.3px;
      padding-bottom: 12px;
      border-bottom: 2px solid var(--border-color);
    }}

    /* Enhanced Progress Bars with Gradients */
    .bar {{
      background: var(--bg-tertiary);
      border-radius: 8px;
      height: 12px;
      overflow: hidden;
      position: relative;
    }}

    .barfill {{
      height: 12px;
      border-radius: 8px;
      background: linear-gradient(90deg, var(--chart-baseline), {CHART_COLOR_NEUTRAL});
      transition: width var(--anim-slow) cubic-bezier(0.4, 0, 0.2, 1);
      animation: barGrow var(--anim-slow) ease;
    }}

    .barfill.improvement {{
      background: linear-gradient(90deg, var(--chart-improvement), #4caf50);
    }}

    .barfill.regression {{
      background: linear-gradient(90deg, var(--chart-regression), #f44336);
    }}

    /* Premium Badges */
    .small {{
      color: var(--text-secondary);
      font-size: 13px;
      font-weight: 500;
    }}

    .badge {{
      display: inline-block;
      padding: 6px 14px;
      border-radius: var(--radius-md);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.3px;
      box-shadow: var(--shadow-xs);
    }}

    .badge-info {{
      background: var(--color-info-bg);
      color: var(--color-info);
      border: 1px solid var(--color-info);
    }}

    .outlier-badge {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: var(--radius-sm);
      font-size: 11px;
      background: var(--color-warning-bg);
      color: var(--color-warning);
      margin-left: 6px;
      font-weight: 700;
      box-shadow: var(--shadow-xs);
      border: 1px solid var(--color-warning);
    }}

    /* Hint / explanation panels - use theme-aware colors for readable contrast */
    .hint-box {{
      margin-top: 16px;
      padding: 12px;
      background: var(--bg-tertiary);
      color: var(--text-primary);
      border-radius: 6px;
      border: 1px solid var(--border-color);
      line-height: 1.7;
    }}

    .hint-box.info {{
      border-left: 4px solid var(--color-info);
    }}

    .hint-box.warning {{
      border-left: 4px solid var(--color-warning);
    }}

    .hint-box.neutral {{
      border-left: 4px solid var(--accent-primary);
    }}

    .hint-box strong {{
      color: var(--text-primary);
    }}

    .hint-box ul {{
      margin: 8px 0;
      padding-left: 20px;
      font-size: 14px;
      color: var(--text-primary);
    }}

    .quality-badge {{
      display: inline-block;
      padding: 14px 24px;
      border-radius: var(--radius-lg);
      font-weight: 800;
      font-size: 16px;
      animation: pulse 2s ease infinite;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      box-shadow: var(--shadow-md);
    }}

    .quality-good {{
      background: var(--bg-tertiary);
      color: var(--text-primary);
      border: 2px solid var(--color-success);
    }}

    .quality-warning {{
      background: var(--bg-tertiary);
      color: var(--text-primary);
      border: 2px solid var(--color-warning);
    }}

    .quality-poor {{
      background: var(--bg-tertiary);
      color: var(--text-primary);
      border: 2px solid var(--color-error);
    }}

    /* Premium Data Quality Grid */
    .data-quality-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin: 20px 0;
    }}

    .quality-item {{
      padding: 24px;
      background: var(--bg-tertiary);
      border-radius: var(--radius-lg);
      border-left: 4px solid var(--border-color);
      transition: all var(--anim-fast) cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: var(--shadow-sm);
    }}

    .quality-item:hover {{
      transform: translateX(6px);
      box-shadow: var(--shadow-lg);
      border-left-width: 6px;
    }}

    .quality-item.excellent {{
      border-left-color: var(--color-success);
      background: var(--bg-tertiary);
    }}
    .quality-item.good {{
      border-left-color: var(--color-success);
      background: var(--bg-tertiary);
    }}
    .quality-item.fair {{
      border-left-color: var(--color-warning);
      background: var(--bg-tertiary);
    }}
    .quality-item.poor {{
      border-left-color: var(--color-error);
      background: var(--bg-tertiary);
    }}

    .issue-list {{
      margin: 12px 0;
      padding-left: 24px;
    }}

    .issue-list li {{
      margin: 8px 0;
      color: var(--text-secondary);
      font-size: 14px;
      line-height: 1.6;
    }}

    /* Premium Info Boxes */
    .info-box {{
      margin: 20px 0;
      padding: 20px 24px;
      background: var(--color-info-bg);
      border-left: 4px solid var(--color-info);
      border-radius: var(--radius-lg);
      font-size: 14px;
      line-height: 1.8;
      box-shadow: var(--shadow-sm);
    }}

    .warning-box {{
      margin: 20px 0;
      padding: 20px 24px;
      background: var(--color-warning-bg);
      border-left: 4px solid var(--color-warning);
      border-radius: var(--radius-lg);
      font-size: 14px;
      line-height: 1.8;
      box-shadow: var(--shadow-sm);
    }}

    /* Premium Scroll to Top Button */
    .scroll-top-btn {{
      position: fixed;
      bottom: 32px;
      right: 32px;
      background: var(--accent-primary);
      border: none;
      color: white;
      width: 56px;
      height: 56px;
      border-radius: 50%;
      cursor: pointer;
      font-size: 24px;
      display: none;
      align-items: center;
      justify-content: center;
      box-shadow: var(--shadow-xl);
      transition: all var(--anim-fast) cubic-bezier(0.4, 0, 0.2, 1);
      z-index: 999;
    }}

    .scroll-top-btn:hover {{
      transform: translateY(-6px) scale(1.1);
      box-shadow: 0 12px 32px rgba(0, 102, 255, 0.4);
    }}

    .scroll-top-btn:active {{
      transform: translateY(-2px) scale(1.05);
    }}

    .scroll-top-btn.visible {{
      display: flex;
      animation: fadeIn var(--anim-normal) ease, bounce 2s ease-in-out infinite;
    }}

    @keyframes bounce {{
      0%, 100% {{ transform: translateY(0); }}
      50% {{ transform: translateY(-8px); }}
    }}

    /* Animations */
    @keyframes fadeIn {{
      from {{ opacity: 0; }}
      to {{ opacity: 1; }}
    }}

    @keyframes slideUp {{
      from {{
        opacity: 0;
        transform: translateY(20px);
      }}
      to {{
        opacity: 1;
        transform: translateY(0);
      }}
    }}

    @keyframes scaleIn {{
      from {{
        opacity: 0;
        transform: scale(0.9);
      }}
      to {{
        opacity: 1;
        transform: scale(1);
      }}
    }}

    @keyframes barGrow {{
      from {{ width: 0; }}
    }}

    @keyframes pulse {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.8; }}
    }}

    /* Premium Responsive Design */
    @media (max-width: 900px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .comparison {{ grid-template-columns: 1fr; gap: 16px; }}
      .comparison-arrow {{ transform: rotate(90deg); font-size: 36px; }}
      .data-quality-grid {{ grid-template-columns: 1fr; }}
      .header {{ flex-direction: column; align-items: flex-start; padding: 16px 20px; }}
      .header-right {{ width: 100%; justify-content: flex-end; }}
      .scroll-top-btn {{ bottom: 20px; right: 20px; width: 48px; height: 48px; }}
      .section {{ padding: 20px; }}
      .executive-summary {{ padding: 32px 24px; }}
    }}

    @media (max-width: 600px) {{
      .container {{ padding: 16px; }}
      .executive-summary {{ padding: 24px 20px; }}
      .big-status {{ font-size: 40px; }}
      .verdict {{ font-size: 20px; }}
      .comparison-value {{ font-size: 32px; }}
      .comparison-item {{ padding: 24px 16px; }}
      h1 {{ font-size: 22px; }}
      .section-title {{ font-size: 18px; }}
      .card {{ padding: 16px; }}
      .quality-badge {{ font-size: 14px; padding: 12px 20px; }}
      .scroll-top-btn {{ bottom: 16px; right: 16px; width: 44px; height: 44px; }}
    }}

    /* =========================
       Animated Background (Emerge Tools Style)
       ========================= */
    #meteor-canvas {{
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      z-index: -1;
      pointer-events: none;
    }}

    .gradient-overlay {{
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      z-index: -1;
      pointer-events: none;
      background:
        radial-gradient(ellipse 80% 50% at 50% -20%, rgba(120, 119, 198, 0.3), transparent),
        radial-gradient(ellipse 60% 80% at 80% 50%, rgba(157, 78, 221, 0.2), transparent);
    }}

    /* Glass morphism effect on sections */
    .section, .executive-summary, .header {{
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.1);
    }}

    /* Print styles */
    @media print {{
      .header-right, .scroll-top-btn, .section-header, #meteor-canvas, .gradient-overlay {{
        display: none !important;
      }}
      .section-content {{
        max-height: none !important;
        opacity: 1 !important;
        display: block !important;
      }}
      body {{
        background: white;
        color: black;
      }}
      .section, .executive-summary {{
        page-break-inside: avoid;
        box-shadow: none;
        border: 1px solid #ccc;
      }}
    }}
  </style>
</head>
<body>
  <!-- Animated Background Canvas (Emerge Tools Style) -->
  <canvas id="meteor-canvas"></canvas>
  <div class="gradient-overlay"></div>

  <!-- Sticky Header with Controls -->
  <div class="header">
    <div class="header-left">
      <h1>{escape(title)}</h1>
      <div class="meta">Generated: {escape(now)} | Mode: {mode.upper()}</div>
    </div>
    <div class="header-right">
      <!-- Export Dropdown -->
      <div class="export-dropdown" id="export-dropdown">
        <button class="control-btn" onclick="toggleExportMenu()">
          📥 Export ▼
        </button>
        <div class="export-menu">
          <button onclick="exportJSON()">📄 Export JSON</button>
          <button onclick="exportCSV()">📊 Export CSV</button>
          <button onclick="window.print()">🖨️ Print / PDF</button>
        </div>
      </div>
    </div>
  </div>

  <div class="container">
    <!-- EXECUTIVE SUMMARY - Simple & Clear for Everyone -->
    <div class="executive-summary">
      <div class="big-status {'inconclusive' if inconclusive else ('no-change' if result.get('no_change', False) else ('pass' if passed else 'fail'))}">{status}</div>
      <div class="verdict">{escape(simple_verdict)}</div>

      <div class="comparison">
        <div class="comparison-item">
          <div class="comparison-label">Before (Baseline)</div>
          <div class="comparison-value">{_fmt_ms(base_med)}</div>
          <div class="small">{len(a)} measurements</div>
        </div>
        <div class="comparison-arrow">{change_icon}</div>
        <div class="comparison-item">
          <div class="comparison-label">After (Target)</div>
          <div class="comparison-value">{_fmt_ms(target_med)}</div>
          <div class="small">{len(b)} measurements</div>
        </div>
      </div>

      <div class="recommendation">{escape(recommendation)}</div>

      {f'''
      <div class="hint-box {practical_impact.get('severity', 'info')}" style="margin-top: 24px; padding: 16px; border-left: 4px solid {practical_impact.get('color', '#2196f3')};">
        <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">
          {practical_impact['icon']} {practical_impact['title']}
        </div>
        <div style="margin-bottom: 12px; color: var(--text-secondary);">
          {practical_impact['description']}
        </div>
        <ul style="margin: 8px 0 0 0; padding-left: 20px; list-style-type: disc;">
          {''.join(f"<li style='margin: 4px 0;'>{bullet}</li>" for bullet in practical_impact.get('bullets', []))}
        </ul>
      </div>
      ''' if practical_impact and practical_impact.get('bullets') else ''}

      <div class="small" style="text-align: center; margin-top: 16px; color: var(--text-secondary);">
        💡 Scroll down for detailed technical analysis
      </div>
    </div>

    <!-- INTERACTIVE CHARTS - Visual Data Exploration -->
    <div class="section">
      <div class="section-header" onclick="toggleSection('charts')">
        <div>
          <h2 class="section-title">📊 Interactive Charts</h2>
          <div class="section-subtitle">Visual comparison of performance distributions</div>
        </div>
        <span class="toggle-icon">▼</span>
      </div>
      <div id="charts" class="section-content">
        <div class="chart-grid">
          <!-- Histogram Comparison Chart -->
          <div>
            <h3 style="margin-top: 0; font-size: 16px; color: var(--text-primary);">Distribution Histogram</h3>
            <p style="font-size: 13px; color: var(--text-secondary); margin: 8px 0 16px 0;">
              Compare the distribution of measurements between baseline and target. Overlapping peaks indicate similar performance.
            </p>
            <div class="chart-container">
              <canvas id="histogramChart"></canvas>
            </div>
          </div>

          <!-- Run-by-Run Line Chart -->
          <div>
            <h3 style="margin-top: 0; font-size: 16px; color: var(--text-primary);">Run-by-Run Comparison</h3>
            <p style="font-size: 13px; color: var(--text-secondary); margin: 8px 0 16px 0;">
              Track how each paired measurement compares. The gap between lines shows performance delta.
            </p>
            <div class="chart-container">
              <canvas id="lineChart"></canvas>
            </div>
          </div>

          <!-- Statistical Summary Comparison -->
          <div>
            <h3 style="margin-top: 0; font-size: 16px; color: var(--text-primary);">Statistical Summary</h3>
            <p style="font-size: 13px; color: var(--text-secondary); margin: 8px 0 16px 0;">
              Compare key statistics: min, quartiles (Q1/Q3), median, mean, and max values side-by-side.
            </p>
            <div class="chart-container">
              <canvas id="boxPlotChart"></canvas>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- DATA QUALITY ASSESSMENT -->
    <div class="section">
      <div class="section-header" onclick="toggleSection('data-quality')">
        <div>
          <h2 class="section-title">🔬 Data Quality Assessment</h2>
          <div class="section-subtitle">How reliable are these measurements?</div>
        </div>
        <span class="toggle-icon">▼</span>
      </div>
      <div id="data-quality" class="section-content">
        <div style="text-align: center; margin-bottom: 20px;">
          <span class="quality-badge quality-{overall_quality_class}">{escape(overall_quality_verdict)}</span>
        </div>

        <div class="data-quality-grid">
          <!-- Baseline Quality -->
          <div class="quality-item {baseline_quality['verdict'].lower()}">
            <h3 style="margin: 0 0 8px 0; font-size: 16px;">
              {baseline_quality['verdict_icon']} Baseline Data: {baseline_quality['verdict']}
              <span style="float: right; font-size: 14px; font-weight: 600; color: var(--text-secondary);">
                Score: {baseline_quality['score']}/100
              </span>
            </h3>
            <p style="margin: 8px 0; color: var(--text-secondary); font-size: 14px;">{escape(baseline_quality['verdict_desc'])}</p>
            <div style="margin: 12px 0;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-size: 12px; font-weight: 600; color: var(--text-secondary);">Quality Score</span>
                <span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">{baseline_quality['score']}/100</span>
              </div>
              <div class="bar" style="height: 8px;">
                <div class="barfill" style="width: {baseline_quality['score']}%; background: linear-gradient(90deg, var(--accent-primary), {baseline_quality['verdict_color']}80);"></div>
              </div>
            </div>
            <table style="font-size: 13px; margin-top: 12px;">
              <tr><td>Samples:</td><td><strong>{baseline_quality['n']}</strong></td></tr>
              <tr><td>Median:</td><td><strong>{_fmt_ms(baseline_quality['median'])}</strong></td></tr>
              <tr><td>Variability (CV):</td><td><strong>{baseline_quality['cv']:.1f}%</strong></td></tr>
              <tr><td>Range:</td><td>{_fmt_ms(baseline_quality['min'])} - {_fmt_ms(baseline_quality['max'])}</td></tr>
              <tr><td>Outliers:</td><td>{baseline_quality['num_outliers']}</td></tr>
            </table>
            {"<div style='margin-top: 12px;'><strong style='color: #b3261e;'>⚠️ Issues:</strong><ul class='issue-list'>" + "".join(f"<li>{escape(issue)}</li>" for issue in baseline_quality['issues']) + "</ul></div>" if baseline_quality['issues'] else ""}
            {"<div style='margin-top: 12px;'><strong style='color: #f57c00;'>⚡ Warnings:</strong><ul class='issue-list'>" + "".join(f"<li>{escape(warning)}</li>" for warning in baseline_quality['warnings']) + "</ul></div>" if baseline_quality['warnings'] else ""}
          </div>

          <!-- Target Quality -->
          <div class="quality-item {target_quality['verdict'].lower()}">
            <h3 style="margin: 0 0 8px 0; font-size: 16px;">
              {target_quality['verdict_icon']} Target Data: {target_quality['verdict']}
              <span style="float: right; font-size: 14px; font-weight: 600; color: var(--text-secondary);">
                Score: {target_quality['score']}/100
              </span>
            </h3>
            <p style="margin: 8px 0; color: var(--text-secondary); font-size: 14px;">{escape(target_quality['verdict_desc'])}</p>
            <div style="margin: 12px 0;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-size: 12px; font-weight: 600; color: var(--text-secondary);">Quality Score</span>
                <span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">{target_quality['score']}/100</span>
              </div>
              <div class="bar" style="height: 8px;">
                <div class="barfill" style="width: {target_quality['score']}%; background: linear-gradient(90deg, var(--accent-primary), {target_quality['verdict_color']}80);"></div>
              </div>
            </div>
            <table style="font-size: 13px; margin-top: 12px;">
              <tr><td>Samples:</td><td><strong>{target_quality['n']}</strong></td></tr>
              <tr><td>Median:</td><td><strong>{_fmt_ms(target_quality['median'])}</strong></td></tr>
              <tr><td>Variability (CV):</td><td><strong>{target_quality['cv']:.1f}%</strong></td></tr>
              <tr><td>Range:</td><td>{_fmt_ms(target_quality['min'])} - {_fmt_ms(target_quality['max'])}</td></tr>
              <tr><td>Outliers:</td><td>{target_quality['num_outliers']}</td></tr>
            </table>
            {"<div style='margin-top: 12px;'><strong style='color: #b3261e;'>⚠️ Issues:</strong><ul class='issue-list'>" + "".join(f"<li>{escape(issue)}</li>" for issue in target_quality['issues']) + "</ul></div>" if target_quality['issues'] else ""}
            {"<div style='margin-top: 12px;'><strong style='color: #f57c00;'>⚡ Warnings:</strong><ul class='issue-list'>" + "".join(f"<li>{escape(warning)}</li>" for warning in target_quality['warnings']) + "</ul></div>" if target_quality['warnings'] else ""}
          </div>
        </div>

        <div class="hint-box info">
          <strong>💡 What does this mean?</strong><br/>
          <ul>
            <li><strong>Quality Score:</strong> Starts at 100, penalties applied for issues. ≥90 = Excellent, ≥75 = Good, ≥60 = Fair, <60 = Poor.</li>
            <li><strong>Samples:</strong> More samples = more reliable results. Aim for 10-20.</li>
            <li><strong>Variability (CV):</strong> Lower is better. <5% is excellent, >20% is problematic.</li>
            <li><strong>Outliers:</strong> Unusual measurements that may indicate instability.</li>
          </ul>
          If data quality is poor, consider re-running tests in a more stable environment or with more samples.
        </div>
      </div>
    </div>

    <!-- TECHNICAL DETAILS - Collapsible Sections -->

    <!-- Quick Statistics -->
    <div class="section">
      <div class="section-header" onclick="toggleSection('quick-stats')">
        <div>
          <h2 class="section-title">📊 Quick Statistics</h2>
          <div class="section-subtitle">Key numbers at a glance</div>
        </div>
        <span class="toggle-icon">▼</span>
      </div>
      <div id="quick-stats" class="section-content">
        <div class="grid">
          <div class="card">
            <h3>Summary</h3>
            {_mini_table(summary_rows)}
          </div>
          <div class="card">
            <h3>Run distribution (relative)</h3>
            <table>
              <tr><th>Baseline max</th><td>{_fmt_ms(float(np.max(a)))}</td></tr>
              <tr><th>Target max</th><td>{_fmt_ms(float(np.max(b)))}</td></tr>
              <tr><th>Baseline bars</th><td>{bar(float(np.median(a)), max_run)} <span class="small">median</span></td></tr>
              <tr><th>Target bars</th><td>{bar(float(np.median(b)), max_run)} <span class="small">median</span></td></tr>
            </table>
            <div class="small">Bars are scaled relative to the max single-run value across both sets.</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Why Did This Pass/Fail? -->
    <div class="section">
      <div class="section-header" onclick="toggleSection('explanation')">
        <div>
          <h2 class="section-title">🔍 Why Did This {
            'Result Is Inconclusive' if inconclusive else
            ('Show No Change' if result.get('no_change', False) else
             ('Pass' if passed else 'Fail'))
          }?</h2>
          <div class="section-subtitle">Technical explanation of the decision</div>
        </div>
        <span class="toggle-icon">▼</span>
      </div>
      <div id="explanation" class="section-content">
        <div class="hint-box neutral" style="padding: 16px;">
          <strong>Decision Reason:</strong><br/>
          {escape(result.get("reason", ""))}
        </div>
        <div class="hint-box warning">
          <strong>💡 What this means:</strong><br/>
          {(
            'Data quality gates failed, so the result is inconclusive. ' if inconclusive else
            ('All checks passed and the change is within practical thresholds (no meaningful change). ' if result.get('no_change', False) else
             ('The performance test passed all checks. ' if passed else 'The performance test failed one or more checks. '))
          )}
          The tool checks multiple factors: median change, worst-case (p90) latency, consistency across runs, and statistical significance.
        </div>
      </div>
    </div>

    <!-- Quality Gates Configuration -->
    <div class="section">
      <div class="section-header" onclick="toggleSection('quality-gates-config')">
        <div>
          <h2 class="section-title">⚙️ Quality Gate Configuration</h2>
          <div class="section-subtitle">Data quality thresholds applied before regression detection</div>
        </div>
        <span class="toggle-icon">▼</span>
      </div>
      <div id="quality-gates-config" class="section-content">
        <table>
          <tr>
            <th>Setting</th>
            <th>Threshold</th>
            <th>Observed</th>
            <th>Status</th>
          </tr>
          <tr>
            <td><strong>Quality Gates Enabled</strong></td>
            <td>{'✅ Yes' if ENABLE_QUALITY_GATES else '❌ No (permissive mode)'}</td>
            <td>—</td>
            <td>—</td>
          </tr>
          <tr>
            <td><strong>Minimum Sample Size</strong></td>
            <td>≥ {MIN_SAMPLES_FOR_REGRESSION} measurements</td>
            <td>{len(a)} measurements</td>
            <td>{'✅ PASS' if len(a) >= MIN_SAMPLES_FOR_REGRESSION else '❌ FAIL'}</td>
          </tr>
          <tr>
            <td><strong>Maximum CV (Variability)</strong></td>
            <td>≤ {MAX_CV_FOR_REGRESSION_CHECK}%</td>
            <td>Baseline: {result['details'].get('baseline_cv', 0):.1f}%, Target: {result['details'].get('target_cv', 0):.1f}%</td>
            <td>{'✅ PASS' if max(result['details'].get('baseline_cv', 0), result['details'].get('target_cv', 0)) <= MAX_CV_FOR_REGRESSION_CHECK else '❌ FAIL'}</td>
          </tr>
          <tr>
            <td><strong>CV Threshold Multiplier</strong></td>
            <td>{CV_THRESHOLD_MULTIPLIER}× (adaptive strictness)</td>
            <td>Applied multiplier: {result['details'].get('cv_multiplier', 1.0):.3f}×</td>
            <td>—</td>
          </tr>
        </table>

        <div style="margin-top: 20px; margin-bottom: 12px; font-weight: 600; color: var(--text-primary);">
          📊 Regression Detection Thresholds
        </div>
        <table>
          <tr>
            <th>Check</th>
            <th>Base Threshold Formula</th>
            <th>Computed Value → Effective (After CV Multiplier)</th>
            <th>Description</th>
          </tr>
          <tr>
            <td><strong>Median Delta</strong></td>
            <td>max({MS_FLOOR}ms, {PCT_FLOOR*100:.0f}% of baseline)</td>
            <td><strong>{result['details'].get('base_threshold_ms', MS_FLOOR):.1f}ms</strong> → <strong style="color: var(--color-info);">{result['details'].get('threshold_ms', MS_FLOOR):.1f}ms</strong></td>
            <td>Absolute or relative threshold, whichever is larger</td>
          </tr>
          <tr>
            <td><strong>Tail (p90) Delta</strong></td>
            <td>max({TAIL_MS_FLOOR}ms, {TAIL_PCT_FLOOR*100:.0f}% of baseline)</td>
            <td><strong>{result['details'].get('base_tail_threshold_ms', TAIL_MS_FLOOR):.1f}ms</strong> → <strong style="color: var(--color-info);">{result['details'].get('tail_threshold_ms', TAIL_MS_FLOOR):.1f}ms</strong></td>
            <td>Catches worst-case latency regressions</td>
          </tr>
          <tr>
            <td><strong>Directionality</strong></td>
            <td>≤ {DIRECTIONALITY*100:.0f}% slower runs</td>
            <td>{DIRECTIONALITY*100:.0f}% (not affected by CV)</td>
            <td>Max fraction of runs that can be slower</td>
          </tr>
          <tr>
            <td><strong>Mann-Whitney U p-value</strong></td>
            <td>≥ {MANN_WHITNEY_ALPHA} (significance level)</td>
            <td>{MANN_WHITNEY_ALPHA} (not affected by CV)</td>
            <td>Statistical significance threshold</td>
          </tr>
        </table>

        <div class="hint-box {'warning' if inconclusive else 'info'}">
          <strong>💡 What are Quality Gates?</strong><br/>
          Quality gates validate data quality <em>before</em> checking for regressions. If data is too noisy (high CV) or insufficient (too few samples), the test returns <strong>INCONCLUSIVE</strong> instead of PASS/FAIL. This prevents false positives/negatives from unreliable measurements.
          <br/><br/>
          <strong>CV-based Adaptive Thresholds:</strong> When variance is elevated (but acceptable), regression thresholds become stricter proportionally. Formula: effective_threshold = base_threshold × cv_multiplier
          <br/><br/>
          {'<span style="color: #d32f2f;">⚠️ <strong>Quality gate failed!</strong> Data rejected as too unreliable. Fix measurement methodology and re-test. See MEASUREMENT_GUIDE.md</span>' if inconclusive else '<span style="color: #2e7d32;">✅ <strong>Quality gates passed.</strong> Data quality is acceptable for regression detection.</span>'}
        </div>
      </div>
    </div>

    {"<div class='section'><div class='section-header' onclick='toggleSection(\"mann_whitney\")'><div><h2 class='section-title'>📈 Mann-Whitney U Test</h2><div class='section-subtitle'>Tests if the target distribution is stochastically greater than baseline (for independent samples)</div></div><span class='toggle-icon'>▼</span></div><div id='mann_whitney' class='section-content'>" + _mini_table(wil_rows) + "<div class='hint-box neutral'><strong>Understanding Mann-Whitney U Test Results:</strong><ul style='margin: 8px 0; padding-left: 20px;'><li><strong>P(Target > Baseline):</strong> The probability that a randomly selected target sample is slower than a randomly selected baseline sample. Values close to 50% indicate no difference; values above 70% indicate substantial performance degradation.</li><li><strong>Effect Size:</strong> Interpretation of the magnitude of difference:<ul style='margin-top: 4px;'><li>Negligible (&lt;55%): No meaningful difference</li><li>Small (55-64%): Slight degradation</li><li>Medium (64-71%): Moderate degradation</li><li>Large (71-86%): Substantial degradation</li><li>Very Large (&gt;86%): Severe degradation</li></ul></li><li><strong>p-value:</strong> Tests whether the difference is statistically significant (not random chance). p &lt; 0.05 means the difference is real with 95% confidence. <strong>Direction Check:</strong> The test only fails if p &lt; 0.05 <em>AND</em> P(Target > Baseline) > 50% <em>AND</em> median delta > 0, ensuring we never fail on performance improvements.</li></ul><strong>Note:</strong> P(Target > Baseline) tells you <em>how much worse</em> target is, while p-value tells you <em>if it's real or noise</em>. Both are needed for complete understanding.<br/><br/><strong>📊 Multiple Testing:</strong> Only Mann-Whitney uses p-value hypothesis testing (α=0.05). Other gates (median delta, tail latency, directionality) use threshold comparisons, not p-values. This limits multiple testing inflation - the family-wise error rate is dominated by the single Mann-Whitney test, not compounded across all gates.</div></div></div>" if wil_rows else ""}

    {"<div class='section'><div class='section-header' onclick='toggleSection(\"bootstrap\")'><div><h2 class='section-title'>🎯 Bootstrap Confidence Interval</h2><div class='section-subtitle'>Quantifies uncertainty in the median performance difference using resampling</div></div><span class='toggle-icon'>▼</span></div><div id='bootstrap' class='section-content'>" + _mini_table(bci_rows) + (f"<div class='hint-box info' style='margin-top: 16px; padding: 12px; background: rgba(33, 150, 243, 0.1); border-left: 4px solid #2196f3;'>{bci_interpretation}</div>" if bci_interpretation else "") + "<div class='hint-box neutral'><strong>📊 Understanding Bootstrap Confidence Intervals:</strong><ul style='margin: 8px 0; padding-left: 20px;'><li><strong>What it means:</strong> We are 95% confident that the TRUE population median difference lies between the CI low and CI high values. This accounts for sampling variability and measurement uncertainty.</li><li><strong>How it works:</strong> The bootstrap method resamples the data 5,000 times (with replacement), calculates the median difference for each resample, then takes the 2.5th and 97.5th percentiles of these differences to form the confidence interval.</li><li><strong>Statistical significance:</strong> If the CI does NOT include 0, the difference is statistically significant at the 95% confidence level (equivalent to p < 0.05). If the CI includes 0, the difference may be due to random variation.</li><li><strong>General interpretation examples:</strong><ul style='margin-top: 4px;'><li>CI = [5ms, 12ms]: Clear regression (significant, entire interval positive)</li><li>CI = [-2ms, 8ms]: Inconclusive (includes 0, not statistically significant)</li><li>CI = [-15ms, -3ms]: Clear improvement (significant, entire interval negative)</li></ul></li></ul><strong>Note:</strong> This CI is for informational purposes and debugging. The actual PASS/FAIL decision uses the gate checks (median delta, tail latency, Mann-Whitney U, etc.). In <strong>release mode</strong>, the bootstrap CI is used for equivalence testing to determine if the entire CI falls within an acceptable margin.</div></div></div>" if bci_rows else ""}

    {"<div class='section'><div class='section-header' onclick='toggleSection(\"equivalence\")'><div><h2 class='section-title'>⚖️ Equivalence Test (Release Mode)</h2><div class='section-subtitle'>Checks if performance is 'close enough' to baseline</div></div><span class='toggle-icon'>▼</span></div><div id='equivalence' class='section-content'>" + _mini_table(eq_rows) + "<div class='hint-box neutral'><strong>What is this?</strong> In release mode, we test if the new version is equivalent to the old (within a margin). This is more permissive than regression testing.</div></div></div>" if eq_rows else ""}

    <!-- Raw Data -->
    <div class="section">
      <div class="section-header" onclick="toggleSection('raw-data')">
        <div>
          <h2 class="section-title">📋 Raw Measurement Data</h2>
          <div class="section-subtitle">Every individual measurement, side-by-side</div>
        </div>
        <span class="toggle-icon">▼</span>
      </div>
      <div id="raw-data" class="section-content">
        <table>
          <tr><th>#</th><th>Baseline</th><th>Target</th><th>Delta</th></tr>
          {''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>' for row in runs_rows)}
        </table>
        <div class="small" style="margin-top: 12px;">
          <strong>Note:</strong> Each row shows a paired measurement. Delta = Target - Baseline.
          Negative delta means faster (improvement), positive means slower (regression).
          Outliers (detected using IQR method) are marked with <span class="outlier-badge">⚠️</span>
        </div>
      </div>
    </div>

    <div style="text-align: center; margin: 32px 0; padding: 16px; color: var(--text-secondary); font-size: 12px;">
      Generated by Performance Regression Detection Tool 🚀
    </div>

  </div>

  <!-- Scroll to Top Button -->
  <button class="scroll-top-btn" id="scrollTopBtn" onclick="scrollToTop()" aria-label="Scroll to top">
    ↑
  </button>

  <script>
    // ==========================================
    // Animated Meteor Background (Emerge Tools Style)
    // ==========================================
    (function initMeteorCanvas() {{
      const canvas = document.getElementById('meteor-canvas');
      if (!canvas) return;

      const ctx = canvas.getContext('2d');
      let width = window.innerWidth;
      let height = window.innerHeight;

      canvas.width = width;
      canvas.height = height;

      // Meteor particles
      const meteors = [];
      const stars = [];

      // Create background stars
      function createStars() {{
        for (let i = 0; i < 150; i++) {{
          stars.push({{
            x: Math.random() * width,
            y: Math.random() * height,
            size: Math.random() * 1.5,
            opacity: Math.random() * 0.5 + 0.3,
            twinkleSpeed: Math.random() * 0.02
          }});
        }}
      }}

      // Meteor class
      class Meteor {{
        constructor() {{
          this.reset();
        }}

        reset() {{
          // Start from random position in top-left area
          this.x = Math.random() * width - 200;
          this.y = Math.random() * height * 0.3 - 200;

          // Angle roughly towards bottom-right (like Emerge Tools)
          const angle = Math.random() * 0.3 + 0.3; // 0.3 to 0.6 radians (~17-34 degrees)
          this.speedX = Math.cos(angle) * (Math.random() * 3 + 3);
          this.speedY = Math.sin(angle) * (Math.random() * 3 + 3);

          this.length = Math.random() * 80 + 60;
          this.opacity = Math.random() * 0.5 + 0.5;
          this.thickness = Math.random() * 2 + 1;

          this.life = 1;
          this.decay = Math.random() * 0.005 + 0.005;
        }}

        update() {{
          this.x += this.speedX;
          this.y += this.speedY;
          this.life -= this.decay;

          // Reset if dead or off-screen
          if (this.life <= 0 || this.x > width + 100 || this.y > height + 100) {{
            this.reset();
          }}
        }}

        draw() {{
          ctx.save();

          const grad = ctx.createLinearGradient(
            this.x, this.y,
            this.x - this.length * Math.cos(0.4),
            this.y - this.length * Math.sin(0.4)
          );

          grad.addColorStop(0, `rgba(255, 255, 255, ${{this.opacity * this.life}})`);
          grad.addColorStop(0.5, `rgba(200, 180, 255, ${{this.opacity * this.life * 0.5}})`);
          grad.addColorStop(1, 'rgba(255, 255, 255, 0)');

          ctx.strokeStyle = grad;
          ctx.lineWidth = this.thickness;
          ctx.lineCap = 'round';

          ctx.beginPath();
          ctx.moveTo(this.x, this.y);
          ctx.lineTo(
            this.x - this.length * Math.cos(0.4),
            this.y - this.length * Math.sin(0.4)
          );
          ctx.stroke();

          ctx.restore();
        }}
      }}

      // Initialize
      createStars();
      for (let i = 0; i < 8; i++) {{
        meteors.push(new Meteor());
      }}

      // Animation loop
      function animate() {{
        // Clear with black background
        ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
        ctx.fillRect(0, 0, width, height);

        // Draw stars
        stars.forEach((star, i) => {{
          star.opacity += Math.sin(Date.now() * star.twinkleSpeed + i) * 0.01;
          star.opacity = Math.max(0.1, Math.min(0.8, star.opacity));

          ctx.fillStyle = `rgba(255, 255, 255, ${{star.opacity}})`;
          ctx.beginPath();
          ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
          ctx.fill();
        }});

        // Update and draw meteors
        meteors.forEach(meteor => {{
          meteor.update();
          meteor.draw();
        }});

        requestAnimationFrame(animate);
      }}

      // Handle resize
      window.addEventListener('resize', () => {{
        width = window.innerWidth;
        height = window.innerHeight;
        canvas.width = width;
        canvas.height = height;
        stars.length = 0;
        createStars();
      }});

      // Start animation
      animate();
    }})();

    // ============================================================================
    // DATA PREPARATION FOR CHARTS
    // ============================================================================
    const baselineData = {baseline_data_json};
    const targetData = {target_data_json};
    const deltaData = {delta_data_json};
    const exportData = {export_data_json};

    // Chart colors
    const CHART_COLORS = {{
      baseline: '{CHART_COLOR_BASELINE}',
      target: '{chart_target_color}',
      neutral: '{CHART_COLOR_NEUTRAL}',
    }};

    // ============================================================================
    // EXPORT FUNCTIONALITY
    // ============================================================================
    function toggleExportMenu() {{
      const dropdown = document.getElementById('export-dropdown');
      dropdown.classList.toggle('active');
    }}

    // Close dropdown when clicking outside
    document.addEventListener('click', function(event) {{
      const dropdown = document.getElementById('export-dropdown');
      if (!dropdown.contains(event.target)) {{
        dropdown.classList.remove('active');
      }}
    }});

    function exportJSON() {{
      const dataStr = JSON.stringify(exportData, null, 2);
      const blob = new Blob([dataStr], {{ type: 'application/json' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'perf-report-data.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      document.getElementById('export-dropdown').classList.remove('active');
      showToast('JSON exported successfully');
    }}

    function exportCSV() {{
      const rows = [
        ['Run', 'Baseline (ms)', 'Target (ms)', 'Delta (ms)']
      ];

      for (let i = 0; i < baselineData.length; i++) {{
        rows.push([
          i + 1,
          baselineData[i].toFixed(2),
          targetData[i].toFixed(2),
          deltaData[i].toFixed(2)
        ]);
      }}

      const csvContent = rows.map(row => row.join(',')).join('\\n');
      const blob = new Blob([csvContent], {{ type: 'text/csv' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'perf-report-measurements.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      document.getElementById('export-dropdown').classList.remove('active');
      showToast('CSV exported successfully');
    }}

    function showToast(message) {{
      const toast = document.createElement('div');
      toast.textContent = message;
      toast.style.cssText = `
        position: fixed;
        bottom: 80px;
        right: 32px;
        background: var(--bg-secondary);
        color: var(--text-primary);
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: var(--shadow-lg);
        z-index: 10000;
        animation: fadeIn 0.3s ease;
        border: 1px solid var(--border-color);
      `;
      document.body.appendChild(toast);
      setTimeout(() => {{
        toast.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => document.body.removeChild(toast), 300);
      }}, 2000);
    }}

    // ============================================================================
    // SECTION TOGGLE ENHANCEMENT
    // ============================================================================
    let chartsInitialized = false;

    function toggleSection(id) {{
      const content = document.getElementById(id);
      const section = content.parentElement;
      content.classList.toggle('show');
      section.classList.toggle('expanded');

      // Lazy load charts when Interactive Charts section is first opened
      if (id === 'charts' && content.classList.contains('show') && !chartsInitialized) {{
        chartsInitialized = true;
        initializeCharts();
      }}
    }}

    // ============================================================================
    // SCROLL TO TOP BUTTON
    // ============================================================================
    const scrollTopBtn = document.getElementById('scrollTopBtn');

    window.addEventListener('scroll', () => {{
      if (window.pageYOffset > 300) {{
        scrollTopBtn.classList.add('visible');
      }} else {{
        scrollTopBtn.classList.remove('visible');
      }}
    }});

    function scrollToTop() {{
      window.scrollTo({{
        top: 0,
        behavior: 'smooth'
      }});
    }}

    // ============================================================================
    // CHART.JS INITIALIZATION
    // ============================================================================
    window.charts = {{}};

    function getChartColors() {{
      const theme = document.documentElement.getAttribute('data-theme');
      return {{
        gridColor: theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
        textColor: theme === 'dark' ? '#e0e0e0' : '#333',
      }};
    }}

    function initializeCharts() {{
      const colors = getChartColors();

      // 1. HISTOGRAM - Distribution comparison
      const histCtx = document.getElementById('histogramChart');
      if (histCtx) {{
        // Calculate histogram bins
        const allData = [...baselineData, ...targetData];
        const min = Math.min(...allData);
        const max = Math.max(...allData);
        const numBins = Math.min(20, Math.max(10, Math.floor(Math.sqrt(baselineData.length))));
        const binWidth = (max - min) / numBins;

        const bins = Array.from({{ length: numBins }}, (_, i) => min + i * binWidth);

        function calculateHistogram(data) {{
          const counts = new Array(numBins).fill(0);
          data.forEach(val => {{
            const binIndex = Math.min(numBins - 1, Math.floor((val - min) / binWidth));
            counts[binIndex]++;
          }});
          return counts;
        }}

        const baselineHist = calculateHistogram(baselineData);
        const targetHist = calculateHistogram(targetData);

        window.charts.histogram = new Chart(histCtx, {{
          type: 'bar',
          data: {{
            labels: bins.map(b => b.toFixed(1)),
            datasets: [
              {{
                label: 'Baseline',
                data: baselineHist,
                backgroundColor: CHART_COLORS.baseline + '80',
                borderColor: CHART_COLORS.baseline,
                borderWidth: 1.5,
              }},
              {{
                label: 'Target',
                data: targetHist,
                backgroundColor: CHART_COLORS.target + '80',
                borderColor: CHART_COLORS.target,
                borderWidth: 1.5,
              }}
            ]
          }},
          options: {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{
              mode: 'index',
              intersect: false,
            }},
            plugins: {{
              legend: {{
                labels: {{ color: colors.textColor }}
              }},
              tooltip: {{
                callbacks: {{
                  title: (items) => `Range: ${{items[0].label}}ms`,
                  label: (item) => `${{item.dataset.label}}: ${{item.parsed.y}} measurements`
                }}
              }}
            }},
            scales: {{
              x: {{
                title: {{
                  display: true,
                  text: 'Performance (ms)',
                  color: colors.textColor
                }},
                grid: {{ color: colors.gridColor }},
                ticks: {{ color: colors.textColor }}
              }},
              y: {{
                title: {{
                  display: true,
                  text: 'Count',
                  color: colors.textColor
                }},
                grid: {{ color: colors.gridColor }},
                ticks: {{ color: colors.textColor, precision: 0 }}
              }}
            }}
          }}
        }});
      }}

      // 2. LINE CHART - Run-by-run comparison
      const lineCtx = document.getElementById('lineChart');
      if (lineCtx) {{
        const runLabels = Array.from({{ length: baselineData.length }}, (_, i) => (i + 1).toString());

        window.charts.line = new Chart(lineCtx, {{
          type: 'line',
          data: {{
            labels: runLabels,
            datasets: [
              {{
                label: 'Baseline',
                data: baselineData,
                borderColor: CHART_COLORS.baseline,
                backgroundColor: CHART_COLORS.baseline + '20',
                borderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                tension: 0.3,
                fill: true,
              }},
              {{
                label: 'Target',
                data: targetData,
                borderColor: CHART_COLORS.target,
                backgroundColor: CHART_COLORS.target + '20',
                borderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                tension: 0.3,
                fill: true,
              }}
            ]
          }},
          options: {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{
              mode: 'index',
              intersect: false,
            }},
            plugins: {{
              legend: {{
                labels: {{ color: colors.textColor }}
              }},
              tooltip: {{
                callbacks: {{
                  title: (items) => `Run #${{items[0].label}}`,
                  afterLabel: (item) => {{
                    const delta = targetData[item.dataIndex] - baselineData[item.dataIndex];
                    return `Delta: ${{delta.toFixed(2)}}ms (${{delta > 0 ? '+' : ''}}${{((delta / baselineData[item.dataIndex]) * 100).toFixed(1)}}%)`;
                  }}
                }}
              }}
            }},
            scales: {{
              x: {{
                title: {{
                  display: true,
                  text: 'Run Number',
                  color: colors.textColor
                }},
                grid: {{ color: colors.gridColor }},
                ticks: {{ color: colors.textColor }}
              }},
              y: {{
                title: {{
                  display: true,
                  text: 'Performance (ms)',
                  color: colors.textColor
                }},
                grid: {{ color: colors.gridColor }},
                ticks: {{ color: colors.textColor }}
              }}
            }}
          }}
        }});
      }}

      // 3. STATISTICAL SUMMARY - Bar chart comparison
      const boxCtx = document.getElementById('boxPlotChart');
      if (boxCtx) {{
        function calculateStats(data) {{
          const sorted = [...data].sort((a, b) => a - b);
          const min = sorted[0];
          const max = sorted[sorted.length - 1];
          const q1 = sorted[Math.floor(sorted.length * 0.25)];
          const median = sorted[Math.floor(sorted.length * 0.5)];
          const q3 = sorted[Math.floor(sorted.length * 0.75)];
          const mean = data.reduce((a, b) => a + b, 0) / data.length;

          return {{ min, q1, median, q3, max, mean }};
        }}

        const baselineStats = calculateStats(baselineData);
        const targetStats = calculateStats(targetData);

        window.charts.boxplot = new Chart(boxCtx, {{
          type: 'bar',
          data: {{
            labels: ['Min', 'Q1 (25%)', 'Median', 'Mean', 'Q3 (75%)', 'Max'],
            datasets: [
              {{
                label: 'Baseline',
                data: [
                  baselineStats.min,
                  baselineStats.q1,
                  baselineStats.median,
                  baselineStats.mean,
                  baselineStats.q3,
                  baselineStats.max
                ],
                backgroundColor: CHART_COLORS.baseline + '80',
                borderColor: CHART_COLORS.baseline,
                borderWidth: 2,
              }},
              {{
                label: 'Target',
                data: [
                  targetStats.min,
                  targetStats.q1,
                  targetStats.median,
                  targetStats.mean,
                  targetStats.q3,
                  targetStats.max
                ],
                backgroundColor: CHART_COLORS.target + '80',
                borderColor: CHART_COLORS.target,
                borderWidth: 2,
              }}
            ]
          }},
          options: {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{
              mode: 'index',
              intersect: false,
            }},
            plugins: {{
              legend: {{
                labels: {{ color: colors.textColor }}
              }},
              tooltip: {{
                callbacks: {{
                  label: (item) => `${{item.dataset.label}}: ${{item.parsed.y.toFixed(2)}}ms`
                }}
              }}
            }},
            scales: {{
              x: {{
                grid: {{ color: colors.gridColor }},
                ticks: {{ color: colors.textColor }}
              }},
              y: {{
                title: {{
                  display: true,
                  text: 'Performance (ms)',
                  color: colors.textColor
                }},
                grid: {{ color: colors.gridColor }},
                ticks: {{ color: colors.textColor }}
              }}
            }}
          }}
        }});
      }}
    }}

    // ============================================================================
    // INITIALIZATION ON PAGE LOAD
    // ============================================================================
    document.addEventListener('DOMContentLoaded', function() {{
      // Charts are lazy-loaded when the section is first opened
    }});
  </script>
</body>
</html>
"""
