from datetime import datetime
from html import escape
from typing import List, Dict, Any, Optional
import numpy as np


def _fmt_ms(x: float) -> str:
    return f"{x:.2f} ms"


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.2f}%"


def _mini_table(rows: List[List[str]]) -> str:
    trs = []
    for r in rows:
        tds = "".join(f"<td>{escape(c)}</td>" for c in r)
        trs.append(f"<tr>{tds}</tr>")
    return "<table>" + "".join(trs) + "</table>"


def render_html_report(
    title: str,
    baseline: List[float],
    change: List[float],
    gate_result: Dict[str, Any],
    mode: str,
    equivalence: Optional[Dict[str, Any]] = None,
) -> str:
    a = np.array(baseline, dtype=float)
    b = np.array(change, dtype=float)
    d = b - a

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    passed = gate_result["passed"]
    status = "PASS ✅" if passed else "FAIL ❌"

    base_med = float(np.median(a))
    change_med = float(np.median(b))
    delta_med = float(np.median(d))
    base_p90 = float(np.quantile(a, 0.90))
    change_p90 = float(np.quantile(b, 0.90))
    delta_p90 = float(np.quantile(d, 0.90))
    pos_frac = float(np.mean(d > 0))

    summary_rows = [
        ["Mode", mode],
        ["Status", status],
        ["Samples (paired)", str(len(d))],
        ["Baseline median", _fmt_ms(base_med)],
        ["Change median", _fmt_ms(change_med)],
        ["Median delta", _fmt_ms(delta_med)],
        ["Baseline p90", _fmt_ms(base_p90)],
        ["Change p90", _fmt_ms(change_p90)],
        ["p90 delta", _fmt_ms(delta_p90)],
        ["Positive delta fraction", _fmt_pct(pos_frac)],
    ]

    details = gate_result.get("details", {})
    if "threshold_ms" in details:
        summary_rows.append(
            ["Gate threshold", _fmt_ms(details["threshold_ms"])]
        )

    wilcoxon = details.get("wilcoxon")
    wilcoxon_rows = []
    if wilcoxon:
        wilcoxon_rows = [
            ["n", str(wilcoxon["n"])],
            ["z", f'{wilcoxon["z"]:.3f}'],
            ["p(greater)", f'{wilcoxon["p_greater"]:.6f}'],
            ["p(two-sided)", f'{wilcoxon["p_two_sided"]:.6f}'],
        ]

    bootstrap = details.get("bootstrap_ci_median")
    bootstrap_rows = []
    if bootstrap:
        bootstrap_rows = [
            ["Confidence", f'{bootstrap["confidence"]*100:.1f}%'],
            ["CI low", _fmt_ms(bootstrap["low"])],
            ["CI high", _fmt_ms(bootstrap["high"])],
            ["Bootstrap samples", str(bootstrap["n_boot"])],
        ]

    eq_rows = []
    if equivalence:
        eq_rows = [
            ["Equivalent", "YES ✅" if equivalence["equivalent"] else "NO ❌"],
            ["Margin", _fmt_ms(equivalence["margin_ms"])],
            ["CI low", _fmt_ms(equivalence["ci_low"])],
            ["CI high", _fmt_ms(equivalence["ci_high"])],
        ]

    run_rows = []
    for i, (ai, bi, di) in enumerate(zip(a, b, d), start=1):
        run_rows.append([
            str(i),
            _fmt_ms(ai),
            _fmt_ms(bi),
            _fmt_ms(di),
        ])

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; margin: 24px; }}
    h1 {{ margin-bottom: 4px; }}
    .meta {{ color: #666; margin-bottom: 20px; }}
    .card {{ border: 1px solid #e5e5e5; border-radius: 12px; padding: 16px; margin: 16px 0; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td, th {{ border-bottom: 1px solid #eee; padding: 8px; text-align: left; }}
    th {{ background: #fafafa; }}
    .status {{ font-size: 20px; font-weight: 700; }}
    .pass {{ color: #137333; }}
    .fail {{ color: #b3261e; }}
  </style>
</head>
<body>

<h1>{escape(title)}</h1>
<div class="meta">Generated {escape(now)}</div>

<div class="card">
  <div class="status {'pass' if passed else 'fail'}">{status}</div>
  <div>{escape(gate_result["reason"])}</div>
</div>

<div class="card">
  <h3>Summary</h3>
  {_mini_table(summary_rows)}
</div>

{"<div class='card'><h3>Wilcoxon (paired)</h3>" + _mini_table(wilcoxon_rows) + "</div>" if wilcoxon_rows else ""}

{"<div class='card'><h3>Bootstrap CI (median delta)</h3>" + _mini_table(bootstrap_rows) + "</div>" if bootstrap_rows else ""}

{"<div class='card'><h3>Equivalence (release)</h3>" + _mini_table(eq_rows) + "</div>" if eq_rows else ""}

<div class="card">
  <h3>Per-run values</h3>
  <table>
    <tr><th>#</th><th>Baseline</th><th>Change</th><th>Delta</th></tr>
    {''.join('<tr>' + ''.join(f'<td>{escape(c)}</td>' for c in row) + '</tr>' for row in run_rows)}
  </table>
</div>

</body>
</html>
"""
