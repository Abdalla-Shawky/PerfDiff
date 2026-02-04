"""HTML template for timeline visualization view.

This module generates the Firebase Performance-style timeline view
showing traces chronologically with side-by-side baseline/target comparison.
"""

from typing import TYPE_CHECKING, List, Dict
from html import escape
import numpy as np

if TYPE_CHECKING:
    from multi_trace_comparison import MultiTraceResult, TraceComparison


# SVG layout constants
SVG_WIDTH = 1200
SVG_LEFT_MARGIN = 320  # Space for trace names
SVG_RIGHT_MARGIN = 80
CHART_WIDTH = SVG_WIDTH - SVG_LEFT_MARGIN - SVG_RIGHT_MARGIN
BAR_HEIGHT = 28
BAR_SPACING = 8
TOP_MARGIN = 60


def calculate_timeline_layout(comparisons: List['TraceComparison'],
                              timeline_type: str) -> dict:
    """Calculate SVG coordinates for timeline bars.

    Args:
        comparisons: List of TraceComparison objects
        timeline_type: 'baseline' or 'target'

    Returns:
        dict with layout info: {
            'max_time': float,
            'traces': [...],
            'svg_height': int
        }
    """
    # Filter traces with timing info
    timed_traces = []
    for comp in comparisons:
        if timeline_type == 'baseline':
            start = comp.baseline_start_time
            duration = comp.baseline_duration
        else:
            start = comp.target_start_time
            duration = comp.target_duration

        if start is not None and duration is not None:
            timed_traces.append({
                'name': comp.name,
                'start_ms': start,
                'duration_ms': duration,
                'comparison': comp
            })

    # If no traces have timing info, return empty layout
    if not timed_traces:
        return {
            'max_time': 1000,
            'traces': [],
            'svg_height': 200
        }

    # Sort chronologically by start time
    timed_traces.sort(key=lambda t: t['start_ms'])

    # Calculate max time for scale
    max_time = max(
        (t['start_ms'] + t['duration_ms'] for t in timed_traces),
        default=1000
    )

    # Add 10% padding to the right
    max_time = max_time * 1.1

    # Calculate coordinates for each trace
    traces_layout = []
    for i, trace in enumerate(timed_traces):
        # X position (time scale)
        x = SVG_LEFT_MARGIN + (trace['start_ms'] / max_time) * CHART_WIDTH
        width = (trace['duration_ms'] / max_time) * CHART_WIDTH

        # Y position (stacked vertically)
        y = TOP_MARGIN + i * (BAR_HEIGHT + BAR_SPACING)

        # Determine status from gate result
        result = trace['comparison'].gate_result
        if result.inconclusive:
            status = 'inconclusive'
        elif result.no_change:
            status = 'no-change'
        elif result.passed:
            status = 'pass'
        else:
            status = 'fail'

        traces_layout.append({
            'name': trace['name'],
            'start_ms': trace['start_ms'],
            'duration_ms': trace['duration_ms'],
            'x': x,
            'width': max(width, 5),  # Minimum width for visibility
            'y': y,
            'status': status
        })

    svg_height = TOP_MARGIN + len(timed_traces) * (BAR_HEIGHT + BAR_SPACING) + 40

    return {
        'max_time': max_time,
        'traces': traces_layout,
        'svg_height': svg_height
    }


def render_time_axis(max_time: float) -> str:
    """Generate SVG markup for time axis.

    Args:
        max_time: Maximum time value in milliseconds

    Returns:
        SVG markup for time axis
    """
    # Calculate appropriate tick interval
    if max_time <= 1000:
        interval = 100  # 100ms ticks
    elif max_time <= 5000:
        interval = 500  # 500ms ticks
    elif max_time <= 10000:
        interval = 1000  # 1s ticks
    else:
        interval = 2000  # 2s ticks

    ticks = []
    current = 0
    while current <= max_time:
        # Calculate x position
        x = SVG_LEFT_MARGIN + (current / max_time) * CHART_WIDTH

        # Format label
        if current >= 1000:
            label = f"{current/1000:.1f}s"
        else:
            label = f"{int(current)}ms"

        # Create tick mark and label
        tick_svg = f'''
        <line x1="{x}" y1="{TOP_MARGIN - 10}"
              x2="{x}" y2="{TOP_MARGIN - 5}"
              stroke="rgba(255,255,255,0.3)" stroke-width="1"/>
        <text x="{x}" y="{TOP_MARGIN - 15}"
              fill="rgba(255,255,255,0.6)"
              font-size="11"
              text-anchor="middle">{label}</text>
        '''
        ticks.append(tick_svg)
        current += interval

    # Horizontal axis line
    axis_line = f'''
    <line x1="{SVG_LEFT_MARGIN}" y1="{TOP_MARGIN}"
          x2="{SVG_LEFT_MARGIN + CHART_WIDTH}" y2="{TOP_MARGIN}"
          stroke="rgba(255,255,255,0.2)" stroke-width="2"/>
    '''

    return f'<g class="time-axis">{axis_line}{"".join(ticks)}</g>'


def render_timeline_svg(layout: dict, timeline_type: str, comparisons: List['TraceComparison']) -> str:
    """Generate SVG markup for timeline.

    Args:
        layout: Layout dict from calculate_timeline_layout()
        timeline_type: 'baseline' or 'target'
        comparisons: List of all comparisons for lookup

    Returns:
        SVG markup string
    """
    if not layout['traces']:
        return ''

    # Create comparison lookup
    comp_lookup = {c.name: c for c in comparisons}

    traces_svg = []
    for trace in layout['traces']:
        # Get comparison for this trace
        comp = comp_lookup.get(trace['name'])

        # Background bar (track)
        bg_rect = f'''
        <rect class="bar-bg"
              x="{trace['x']}"
              y="{trace['y']}"
              width="{trace['width']}"
              height="{BAR_HEIGHT}"
              fill="rgba(255,255,255,0.05)"
              rx="4" ry="4"/>
        '''

        # Get baseline and target data for tooltip
        if comp:
            baseline_median = np.median(comp.baseline_data) if comp.baseline_data else 0
            target_median = np.median(comp.target_data) if comp.target_data else 0
            delta = target_median - baseline_median
            delta_str = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
        else:
            baseline_median = 0
            target_median = 0
            delta_str = "0.0"

        # Filled bar (actual duration with status color)
        fill_rect = f'''
        <rect class="bar-fill status-{trace['status']}"
              x="{trace['x']}"
              y="{trace['y']}"
              width="{trace['width']}"
              height="{BAR_HEIGHT}"
              data-trace="{escape(trace['name'])}"
              data-start="{trace['start_ms']:.1f}"
              data-duration="{trace['duration_ms']:.1f}"
              data-baseline="{baseline_median:.1f}"
              data-target="{target_median:.1f}"
              data-delta="{delta_str}"
              data-status="{trace['status'].upper()}"
              rx="4" ry="4"/>
        '''

        # Label (trace name) - truncate if too long
        display_name = trace['name']
        if len(display_name) > 40:
            display_name = display_name[:37] + "..."

        label_text = f'''
        <text class="bar-label"
              x="{SVG_LEFT_MARGIN - 10}"
              y="{trace['y'] + BAR_HEIGHT/2 + 5}"
              text-anchor="end">{escape(display_name)}</text>
        '''

        traces_svg.append(f'<g class="trace-bar">{bg_rect}{fill_rect}{label_text}</g>')

    # Time axis
    axis_svg = render_time_axis(layout['max_time'])

    svg = f'''
    <svg class="timeline-svg"
         width="100%"
         height="{layout['svg_height']}"
         viewBox="0 0 {SVG_WIDTH} {layout['svg_height']}"
         preserveAspectRatio="xMidYMid meet">
      {axis_svg}
      <g class="trace-bars">
        {"".join(traces_svg)}
      </g>
    </svg>
    '''

    return svg


def render_timeline_interactivity() -> str:
    """Generate JavaScript for timeline interactions.

    Returns:
        JavaScript code string
    """
    return '''
// Timeline tooltip
const tooltip = document.createElement('div');
tooltip.className = 'timeline-tooltip';
tooltip.style.cssText = `
  position: absolute;
  display: none;
  background: rgba(26, 31, 41, 0.98);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  padding: 12px 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.6);
  pointer-events: none;
  z-index: 1000;
  font-size: 13px;
  max-width: 320px;
  line-height: 1.5;
`;
document.body.appendChild(tooltip);

// Helper to get status color
function getStatusColor(status) {
  const colors = {
    'PASS': '#4caf50',
    'FAIL': '#f44336',
    'NO-CHANGE': '#2196f3',
    'INCONCLUSIVE': '#ff9800'
  };
  return colors[status] || '#888';
}

// Attach hover listeners to all trace bars
document.querySelectorAll('.bar-fill').forEach(bar => {
  bar.addEventListener('mouseenter', (e) => {
    const traceName = bar.dataset.trace;
    const startTime = bar.dataset.start;
    const duration = bar.dataset.duration;
    const status = bar.dataset.status;
    const baseline = bar.dataset.baseline;
    const target = bar.dataset.target;
    const delta = bar.dataset.delta;

    const statusColor = getStatusColor(status);
    const deltaColor = delta.startsWith('+') ? '#f44336' : (delta.startsWith('-') ? '#4caf50' : '#888');

    tooltip.innerHTML = `
      <div style="font-weight: 700; margin-bottom: 8px; color: #f5f9ff; font-size: 14px;">
        ${escapeHtml(traceName)}
      </div>
      <div style="color: #b0b0b0; font-size: 12px;">
        <div style="margin-bottom: 4px;"><strong>Start:</strong> ${startTime}ms</div>
        <div style="margin-bottom: 4px;"><strong>Duration:</strong> ${duration}ms</div>
        <div style="margin-bottom: 8px;"><strong>Status:</strong> <span style="color: ${statusColor}; font-weight: 600;">${status}</span></div>
        <div style="padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.1);">
          <div style="margin-bottom: 3px;"><strong>Baseline:</strong> ${baseline}ms</div>
          <div style="margin-bottom: 3px;"><strong>Target:</strong> ${target}ms</div>
          <div><strong>Delta:</strong> <span style="color: ${deltaColor}; font-weight: 600;">${delta}ms</span></div>
        </div>
      </div>
    `;

    tooltip.style.display = 'block';
  });

  bar.addEventListener('mousemove', (e) => {
    tooltip.style.left = (e.pageX + 15) + 'px';
    tooltip.style.top = (e.pageY + 15) + 'px';
  });

  bar.addEventListener('mouseleave', () => {
    tooltip.style.display = 'none';
  });

  // Click to navigate to detail page
  bar.addEventListener('click', () => {
    const traceName = bar.dataset.trace;
    window.location.href = `${traceName}.html`;
  });

  // Visual feedback
  bar.style.cursor = 'pointer';
});

// HTML escape helper
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
'''


def render_timeline_section(result: 'MultiTraceResult') -> str:
    """Render timeline view HTML section.

    Args:
        result: MultiTraceResult from compare_traces()

    Returns:
        HTML string for timeline section
    """
    # Calculate layouts
    baseline_layout = calculate_timeline_layout(result.comparisons, 'baseline')
    target_layout = calculate_timeline_layout(result.comparisons, 'target')

    # Check if any traces have timing info
    if not baseline_layout['traces'] and not target_layout['traces']:
        return '''
        <div class="timeline-empty">
          <div class="empty-icon">📊</div>
          <div class="empty-title">No Timeline Data Available</div>
          <div class="empty-message">
            The timeline view requires traces with <code>startTime</code> metadata.
            <br><br>
            Switch to the <a href="#" onclick="switchView('table'); return false;" style="color: #0066ff; text-decoration: none; font-weight: 600;">Table View</a> to see all traces.
          </div>
        </div>
        '''

    # Generate SVGs
    baseline_svg = render_timeline_svg(baseline_layout, 'baseline', result.comparisons)
    target_svg = render_timeline_svg(target_layout, 'target', result.comparisons)

    # Extract commit info from file paths
    baseline_commit = result.baseline_file.split('/')[-1].replace('.json', '').replace('_traces', '')
    target_commit = result.target_file.split('/')[-1].replace('.json', '').replace('_traces', '')

    # Count traces with timing data
    baseline_count = len(baseline_layout['traces'])
    target_count = len(target_layout['traces'])
    total_count = len(result.comparisons)

    html = f'''
    <div class="timeline-container">
      <div class="timeline-info">
        <div class="timeline-info-text">
          Showing {max(baseline_count, target_count)} of {total_count} traces with timing data
        </div>
      </div>

      <!-- Baseline Timeline -->
      <div class="timeline-section">
        <h3 class="timeline-title">
          <span class="timeline-label">Baseline Timeline</span>
          <span class="timeline-commit">{escape(baseline_commit)}</span>
        </h3>
        <div class="timeline-chart">
          {baseline_svg if baseline_svg else '<div class="timeline-empty-section">No timing data for baseline traces</div>'}
        </div>
        <div class="timeline-legend">
          <span class="legend-item">
            <span class="legend-dot status-pass"></span> Pass
          </span>
          <span class="legend-item">
            <span class="legend-dot status-fail"></span> Fail
          </span>
          <span class="legend-item">
            <span class="legend-dot status-no-change"></span> No Change
          </span>
          <span class="legend-item">
            <span class="legend-dot status-inconclusive"></span> Inconclusive
          </span>
        </div>
      </div>

      <!-- Target Timeline -->
      <div class="timeline-section">
        <h3 class="timeline-title">
          <span class="timeline-label">Target Timeline</span>
          <span class="timeline-commit">{escape(target_commit)}</span>
        </h3>
        <div class="timeline-chart">
          {target_svg if target_svg else '<div class="timeline-empty-section">No timing data for target traces</div>'}
        </div>
        <div class="timeline-legend">
          <span class="legend-item">
            <span class="legend-dot status-pass"></span> Pass
          </span>
          <span class="legend-item">
            <span class="legend-dot status-fail"></span> Fail
          </span>
          <span class="legend-item">
            <span class="legend-dot status-no-change"></span> No Change
          </span>
          <span class="legend-item">
            <span class="legend-dot status-inconclusive"></span> Inconclusive
          </span>
        </div>
      </div>
    </div>

    <script>
      {render_timeline_interactivity()}
    </script>
    '''

    return html
