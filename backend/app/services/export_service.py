import uuid
from pathlib import Path

from fastapi import HTTPException, status

from app.automation.graph_utils import build_breadcrumb, build_node_index
from app.core.config import settings
from app.models.bug import Bug
from app.models.scan import Scan, ScanNode, Screenshot
from app.models.user import User


def _fmt_ms(value: int | None) -> str:
    return f"{value}ms" if value is not None else "—"


def _fmt_cls(value: float | None) -> str:
    return f"{value}" if value is not None else "—"


class ExportService:
    async def generate_html_report(self, user: User, scan_id: uuid.UUID) -> str:
        scan = await Scan.find_one(Scan.id == scan_id, Scan.user_id == user.id)
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

        bugs = await Bug.find(Bug.scan_id == scan.id).sort("-severity").to_list()
        screenshots = await Screenshot.find(Screenshot.scan_id == scan.id).to_list()
        nodes = await ScanNode.find(ScanNode.scan_id == scan.id).to_list()

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        bugs.sort(key=lambda b: severity_order.get(b.severity, 4))

        bug_rows = ""
        for bug in bugs:
            bug_rows += f"""
            <tr>
              <td><span class="sev {bug.severity}">{bug.severity}</span></td>
              <td>{bug.title}</td>
              <td>{bug.component}</td>
              <td>{bug.description[:220]}</td>
              <td class="muted">{bug.page_url or "—"}</td>
            </tr>"""

        node_by_id = build_node_index(nodes)
        node_rows = ""
        for node in nodes:
            depth = len(build_breadcrumb(node, node_by_id, max_depth=10)) - 1
            indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * depth
            node_rows += f"""
            <tr>
              <td>{indent}{node.label}</td>
              <td class="muted">{node.url}</td>
              <td>{_fmt_ms(node.lcp_ms)}</td>
              <td>{_fmt_cls(node.cls)}</td>
              <td>{_fmt_ms(node.ttfb_ms)}</td>
            </tr>"""

        screenshots_by_node: dict[uuid.UUID | None, list[Screenshot]] = {}
        for ss in screenshots:
            screenshots_by_node.setdefault(ss.node_id, []).append(ss)

        screenshot_section = ""
        for node in nodes:
            shots = screenshots_by_node.get(node.id, [])
            if not shots:
                continue
            thumbs = "".join(
                f'<div class="ss"><p>{ss.viewport}</p>'
                f'<img src="/api/v1/scans/screenshots/{Path(ss.file_path).name}" alt="{node.label} · {ss.viewport}"/></div>'
                for ss in shots
            )
            screenshot_section += f'<h3>{node.label}</h3><p class="muted">{node.url}</p><div class="ss-row">{thumbs}</div>'

        critical_count = sum(1 for b in bugs if b.severity == "critical")
        high_count = sum(1 for b in bugs if b.severity == "high")

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>VisionQA Report - {scan.url}</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 1000px; margin: 2rem auto; padding: 0 1rem; }}
h1 {{ color: #1e40af; }} h2 {{ margin-top: 2.5rem; }} .score {{ font-size: 3rem; font-weight: bold; }}
.sev {{ padding: 2px 8px; border-radius: 4px; font-size: 12px; text-transform: uppercase; }}
.critical {{ background: #fecaca; color: #991b1b; }} .high {{ background: #fed7aa; color: #9a3412; }}
.medium {{ background: #fef08a; color: #854d0e; }} .low {{ background: #bfdbfe; color: #1e40af; }}
table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
th, td {{ border: 1px solid #e5e7eb; padding: 8px; text-align: left; font-size: 14px; }}
th {{ background: #f3f4f6; }} .muted {{ color: #6b7280; font-size: 12px; }}
.ss-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 1rem; }}
.ss {{ width: 220px; }} .ss img {{ max-width: 100%; border: 1px solid #e5e7eb; border-radius: 8px; }}
.ss p {{ font-size: 12px; color: #6b7280; margin: 4px 0; }}
.summary {{ background: #f0f9ff; padding: 1rem; border-radius: 8px; margin: 1rem 0; }}
.stats {{ display: flex; gap: 2rem; margin: 1rem 0; }}
.stat {{ text-align: center; }} .stat .n {{ font-size: 1.5rem; font-weight: bold; }} .stat .l {{ font-size: 12px; color: #6b7280; }}
</style></head><body>
<h1>VisionQA Scan Report</h1>
<p><strong>URL:</strong> {scan.url}</p>
<p><strong>Date:</strong> {scan.completed_at or scan.created_at}</p>
<p class="score">Health Score: {scan.health_score or 0}/100</p>

<div class="stats">
  <div class="stat"><div class="n">{scan.nodes_discovered}</div><div class="l">Pages discovered</div></div>
  <div class="stat"><div class="n">{scan.edges_discovered}</div><div class="l">Interactions explored</div></div>
  <div class="stat"><div class="n">{len(bugs)}</div><div class="l">Total issues</div></div>
  <div class="stat"><div class="n">{critical_count}</div><div class="l">Critical</div></div>
  <div class="stat"><div class="n">{high_count}</div><div class="l">High</div></div>
</div>

<div class="summary"><strong>AI Summary</strong><p>{scan.ai_summary or "No summary available."}</p></div>

<h2>Pages Discovered</h2>
<table><thead><tr><th>Page</th><th>URL</th><th>LCP</th><th>CLS</th><th>TTFB</th></tr></thead>
<tbody>{node_rows or "<tr><td colspan=5>No pages recorded</td></tr>"}</tbody></table>

<h2>Issues ({len(bugs)})</h2>
<table><thead><tr><th>Severity</th><th>Title</th><th>Component</th><th>Description</th><th>Page</th></tr></thead>
<tbody>{bug_rows or "<tr><td colspan=5>No issues found</td></tr>"}</tbody></table>

<h2>Screenshots</h2>
{screenshot_section or "<p>No screenshots</p>"}

<p style="margin-top:2rem;color:#6b7280;font-size:12px;">Generated by VisionQA</p>
</body></html>"""

        Path(settings.reports_path).mkdir(parents=True, exist_ok=True)
        report_path = Path(settings.reports_path) / f"report_{scan.id}.html"
        report_path.write_text(html, encoding="utf-8")
        return html


export_service = ExportService()
