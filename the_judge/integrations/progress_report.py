"""
Progress Report — Human-Readable Improvement Journey for The Judge.

Generates a complete record of the multi-round improvement process,
showing not just score changes but evidence, contradictions, weaknesses,
and exactly why each round was considered an improvement.

For visual projects: includes screenshots per round.
For non-visual projects: shows the appropriate evidence instead.
"""

import os
import time
from typing import Any

from the_judge.integrations.audit_trail import AuditTrail, RoundRecord


def generate_progress_report(
    audit_trail: AuditTrail,
    workspace: str,
    outcome: str,
    output_dir: str,
    is_visual: bool = False,
) -> str:
    """Generate a human-readable HTML progress report.

    Args:
        audit_trail: Completed AuditTrail from the improvement loop.
        workspace: Path to the workspace (for labelling).
        outcome: Final loop outcome string (PASS, MAX_ROUNDS_EXCEEDED, etc.)
        output_dir: Directory to write the report into.
        is_visual: Whether the project has visual components.

    Returns:
        Absolute path to the generated report file.
    """
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, "improvement_report.html")

    history = audit_trail.get_history()
    initial = audit_trail.initial_score()
    final = audit_trail.final_score()
    delta = audit_trail.total_score_delta()
    delta_str = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
    ws_name = os.path.basename(workspace.rstrip("/\\")) or workspace
    generated_at = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    # Build score-bar HTML for each round
    round_blocks = []
    for r in history:
        round_blocks.append(_render_round(r, is_visual, output_dir))

    # Unresolved findings section
    unresolved = audit_trail.get_unresolved_findings()
    unresolved_html = _render_unresolved(unresolved)

    # Screenshots strip (visual only)
    screenshots_html = ""
    if is_visual:
        shots = audit_trail.screenshots()
        if shots:
            screenshots_html = _render_screenshot_strip(shots, output_dir)

    outcome_colour = {
        "PASS": "#10b981",
        "MAX_ROUNDS_EXCEEDED": "#f59e0b",
        "ABORTED": "#ef4444",
        "NO_MEANINGFUL_IMPROVEMENT": "#6b7280",
    }.get(outcome, "#6b7280")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The Judge — Improvement Report: {ws_name}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: #0f172a;
      color: #e2e8f0;
      margin: 0;
      padding: 24px;
      line-height: 1.6;
    }}
    h1, h2, h3 {{ margin: 0 0 8px; }}
    .header {{
      border-bottom: 1px solid #1e293b;
      padding-bottom: 20px;
      margin-bottom: 28px;
    }}
    .header h1 {{ font-size: 1.5rem; color: #f8fafc; }}
    .header .meta {{ font-size: 0.85rem; color: #64748b; }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
      margin-bottom: 32px;
    }}
    .stat-card {{
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 10px;
      padding: 16px;
      text-align: center;
    }}
    .stat-card .value {{
      font-size: 1.6rem;
      font-weight: 700;
      color: #38bdf8;
    }}
    .stat-card .label {{
      font-size: 0.75rem;
      color: #94a3b8;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .outcome-badge {{
      display: inline-block;
      padding: 4px 14px;
      border-radius: 20px;
      font-weight: 600;
      font-size: 0.9rem;
      background: {outcome_colour}22;
      color: {outcome_colour};
      border: 1px solid {outcome_colour}55;
    }}
    .round-card {{
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 20px 24px;
      margin-bottom: 20px;
      position: relative;
    }}
    .round-card h3 {{
      font-size: 1rem;
      color: #f8fafc;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .round-badge {{
      background: #0f172a;
      border: 1px solid #475569;
      border-radius: 6px;
      padding: 2px 10px;
      font-size: 0.8rem;
      color: #94a3b8;
    }}
    .score-bar-wrap {{
      background: #0f172a;
      border-radius: 6px;
      height: 8px;
      margin: 10px 0 16px;
      overflow: hidden;
    }}
    .score-bar {{
      height: 100%;
      border-radius: 6px;
      background: linear-gradient(90deg, #38bdf8, #818cf8);
      transition: width 0.4s ease;
    }}
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
      margin-right: 4px;
    }}
    .badge-ev-backed   {{ background: #ef444422; color: #f87171; border: 1px solid #ef444433; }}
    .badge-observed    {{ background: #f59e0b22; color: #fbbf24; border: 1px solid #f59e0b33; }}
    .badge-assumption  {{ background: #8b5cf622; color: #a78bfa; border: 1px solid #8b5cf633; }}
    .badge-claim       {{ background: #6b728022; color: #9ca3af; border: 1px solid #6b728033; }}
    .badge-contradicted {{ background: #dc262622; color: #f87171; border: 1px solid #dc262633; }}
    .badge-critical {{ background: #dc262622; color: #fca5a5; border: 1px solid #dc262633; }}
    .badge-high     {{ background: #ea580c22; color: #fdba74; border: 1px solid #ea580c33; }}
    .badge-medium   {{ background: #d9770622; color: #fcd34d; border: 1px solid #d9770633; }}
    .badge-low      {{ background: #15803d22; color: #86efac; border: 1px solid #15803d33; }}
    .badge-resolved {{ background: #10b98122; color: #6ee7b7; border: 1px solid #10b98133; }}
    .badge-blocker  {{ background: #dc262622; color: #f87171; border: 1px solid #dc262633; }}
    .finding-row {{
      display: flex;
      gap: 8px;
      align-items: flex-start;
      padding: 6px 0;
      border-bottom: 1px solid #0f172a;
      font-size: 0.85rem;
    }}
    .finding-row:last-child {{ border-bottom: none; }}
    .finding-desc {{ flex: 1; color: #cbd5e1; }}
    .action-list li {{ color: #94a3b8; font-size: 0.85rem; margin: 4px 0; }}
    .contradiction-box {{
      background: #dc262608;
      border: 1px solid #dc262633;
      border-radius: 8px;
      padding: 12px 16px;
      margin: 10px 0;
      font-size: 0.85rem;
    }}
    .contradiction-box .claim {{ color: #94a3b8; font-style: italic; }}
    .contradiction-box .desc  {{ color: #fca5a5; }}
    .screenshot-strip {{
      display: flex;
      gap: 16px;
      overflow-x: auto;
      padding: 12px 0;
      margin-bottom: 24px;
    }}
    .screenshot-frame {{
      flex-shrink: 0;
      text-align: center;
    }}
    .screenshot-frame img {{
      width: 240px;
      height: 150px;
      object-fit: cover;
      border-radius: 8px;
      border: 2px solid #334155;
    }}
    .screenshot-frame p {{ font-size: 0.75rem; color: #64748b; margin: 4px 0 0; }}
    section h2 {{
      font-size: 1.1rem;
      color: #94a3b8;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 16px;
      padding-bottom: 8px;
      border-bottom: 1px solid #1e293b;
    }}
    .unresolved-item {{
      display: flex;
      gap: 8px;
      align-items: flex-start;
      padding: 8px 0;
      border-bottom: 1px solid #1e293b;
      font-size: 0.85rem;
    }}
    .skeptic {{
      background: #1e293b;
      border-left: 3px solid #38bdf8;
      padding: 10px 16px;
      border-radius: 0 8px 8px 0;
      font-style: italic;
      color: #cbd5e1;
      font-size: 0.9rem;
      margin: 10px 0;
    }}
    .footer {{
      margin-top: 40px;
      padding-top: 16px;
      border-top: 1px solid #1e293b;
      font-size: 0.75rem;
      color: #475569;
      text-align: center;
    }}
  </style>
</head>
<body>

<div class="header">
  <h1>🔍 The Judge — Improvement Report</h1>
  <div class="meta">
    Workspace: <strong>{ws_name}</strong> &nbsp;|&nbsp;
    Generated: {generated_at} &nbsp;|&nbsp;
    Outcome: <span class="outcome-badge">{outcome}</span>
  </div>
</div>

<div class="summary-grid">
  <div class="stat-card">
    <div class="value">{len(history)}</div>
    <div class="label">Rounds</div>
  </div>
  <div class="stat-card">
    <div class="value">{initial:.0f}</div>
    <div class="label">Initial Score</div>
  </div>
  <div class="stat-card">
    <div class="value">{final:.0f}</div>
    <div class="label">Final Score</div>
  </div>
  <div class="stat-card">
    <div class="value" style="color: {"#10b981" if delta >= 0 else "#ef4444"}">{delta_str}</div>
    <div class="label">Score Delta</div>
  </div>
  <div class="stat-card">
    <div class="value">{len(unresolved)}</div>
    <div class="label">Unresolved Findings</div>
  </div>
</div>

{screenshots_html}

<section>
  <h2>Round-by-Round Journey</h2>
  {"".join(round_blocks)}
</section>

{unresolved_html}

<div class="footer">
  The Judge adversarial improvement engine &mdash; Don't trust, investigate, challenge, improve, verify, repeat.
</div>

</body>
</html>"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    return report_path


# ---------------------------------------------------------------------------
# Internal Rendering Helpers
# ---------------------------------------------------------------------------


def _render_round(r: RoundRecord, is_visual: bool, output_dir: str) -> str:
    score_pct = min(100.0, max(0.0, r.new_score))
    delta_str = f"+{r.score_delta:.1f}" if r.score_delta >= 0 else f"{r.score_delta:.1f}"
    delta_colour = "#10b981" if r.score_delta >= 0 else "#ef4444"

    # Findings table
    findings_html = ""
    if r.critique_findings:
        rows = []
        for f in r.critique_findings[:8]:
            ev = f.get("evidence_level", "")
            sev = f.get("severity", "")
            desc = f.get("description", "")[:120]
            blocker = (
                " <span class='badge badge-blocker'>BLOCKER</span>" if f.get("is_blocker") else ""
            )
            ev_badge = f"<span class='badge badge-{ev.replace('_', '-')}'>{ev.replace('_', ' ').upper()}</span>"
            sev_badge = f"<span class='badge badge-{sev}'>{sev.upper()}</span>"
            rows.append(
                f"<div class='finding-row'>{ev_badge}{sev_badge}"
                f"<span class='finding-desc'>{_esc(desc)}{blocker}</span></div>"
            )
        findings_html = f"<div style='margin:10px 0'>{''.join(rows)}</div>"

    # Contradictions
    contra_html = ""
    if r.contradictions:
        items = []
        for c in r.contradictions[:3]:
            claim = _esc(c.get("claim", "")[:80])
            desc = _esc(c.get("description", "")[:120])
            items.append(
                f"<div class='contradiction-box'>"
                f"<div class='claim'>Claim: {claim}</div>"
                f"<div class='desc'>↳ {desc}</div>"
                f"</div>"
            )
        contra_html = "".join(items)

    # Resolved findings
    resolved_html = ""
    if r.resolved_finding_ids:
        badges = " ".join(
            f"<span class='badge badge-resolved'>{_esc(fid)}</span>"
            for fid in r.resolved_finding_ids[:6]
        )
        resolved_html = f"<div style='margin-top:8px'><strong style='color:#94a3b8;font-size:.8rem'>Resolved this round:</strong> {badges}</div>"

    # Improvements
    actions_html = ""
    if r.improvement_actions:
        items_li = "".join(f"<li>{_esc(a[:120])}</li>" for a in r.improvement_actions[:5])
        actions_html = f"<ul class='action-list'>{items_li}</ul>"

    # Skeptic summary
    skeptic_html = ""
    if r.skeptic_summary:
        skeptic_html = f"<div class='skeptic'>{_esc(r.skeptic_summary)}</div>"

    # Screenshot
    screenshot_html = ""
    if is_visual and r.screenshot_path and os.path.exists(r.screenshot_path):
        rel = os.path.relpath(r.screenshot_path, output_dir)
        screenshot_html = (
            f"<div style='margin:12px 0'>"
            f"<img src='{rel}' style='max-width:300px;border-radius:8px;border:1px solid #334155' "
            f"alt='Round {r.round_number} screenshot'>"
            f"</div>"
        )

    return f"""
<div class="round-card">
  <h3>
    <span class="round-badge">Round {r.round_number}</span>
    Decision: <strong style="color: {"#10b981" if r.decision == "PASS" else "#f87171"}">{r.decision}</strong>
    &nbsp;&nbsp;
    Score: <strong>{r.previous_score:.1f} → {r.new_score:.1f}</strong>
    <span style="color:{delta_colour};font-size:0.9rem">({delta_str})</span>
    &nbsp;
    Evidence: <strong style="color:{"#10b981" if r.evidence_sufficiency == "sufficient" else "#f59e0b"}">{r.evidence_sufficiency}</strong>
    {('<span class="badge badge-blocker">BLOCKERS</span>' if r.has_blockers else "")}
  </h3>
  <div class="score-bar-wrap">
    <div class="score-bar" style="width:{score_pct:.1f}%"></div>
  </div>
  {skeptic_html}
  {contra_html}
  {findings_html}
  {actions_html}
  {resolved_html}
  {screenshot_html}
  <div style="font-size:0.75rem;color:#475569;margin-top:8px">
    {r.timestamp} &nbsp;|&nbsp; Loop: {r.loop_decision.upper()}
    {("&nbsp;— " + _esc(r.stop_reason)) if r.stop_reason else ""}
  </div>
</div>"""


def _render_screenshot_strip(shots: list[str], output_dir: str) -> str:
    if not shots:
        return ""
    frames = []
    for i, path in enumerate(shots, 1):
        if not os.path.exists(path):
            continue
        rel = os.path.relpath(path, output_dir)
        frames.append(
            f"<div class='screenshot-frame'><img src='{rel}' alt='Round {i}'><p>Round {i}</p></div>"
        )
    if not frames:
        return ""
    return (
        "<section><h2>Visual Progression</h2>"
        f"<div class='screenshot-strip'>{''.join(frames)}</div></section>"
    )


def _render_unresolved(unresolved: list[dict[str, Any]]) -> str:
    if not unresolved:
        return (
            "<section><h2>Remaining Findings</h2>"
            "<p style='color:#10b981'>✓ No unresolved findings remaining.</p></section>"
        )
    rows = []
    for f in unresolved:
        ev = f.get("evidence_level", "")
        sev = f.get("severity", "")
        desc = _esc(f.get("description", "")[:140])
        ev_b = f"<span class='badge badge-{ev.replace('_', '-')}'>{ev.replace('_', ' ').upper()}</span>"
        sev_b = f"<span class='badge badge-{sev}'>{sev.upper()}</span>"
        blocker = " <span class='badge badge-blocker'>BLOCKER</span>" if f.get("is_blocker") else ""
        rows.append(
            f"<div class='unresolved-item'>{ev_b}{sev_b}"
            f"<span class='finding-desc'>{desc}{blocker}</span></div>"
        )
    return "<section><h2>Remaining Findings</h2>" + "".join(rows) + "</section>"


def _esc(text: str) -> str:
    """Minimal HTML escaping."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
