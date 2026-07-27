import asyncio
from pathlib import Path

from playwright.async_api import Page

from app.core.config import settings
from app.core.enums import BugSeverity

_AXE_SOURCE = (Path(__file__).parent / "vendor" / "axe.min.js").read_text(encoding="utf-8")

_IMPACT_TO_SEVERITY = {
    "critical": BugSeverity.CRITICAL.value,
    "serious": BugSeverity.HIGH.value,
    "moderate": BugSeverity.MEDIUM.value,
    "minor": BugSeverity.LOW.value,
}

_RUN_AXE_JS = """async () => {
    return await axe.run(document, {
        resultTypes: ['violations'],
        runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'] },
    });
}"""


class AccessibilityEngine:
    """Runs the real axe-core WCAG ruleset against each page, replacing/
    augmenting the hand-rolled heuristic checks with an industry-standard
    accessibility audit (~90 rules covering ARIA, forms, contrast, landmarks,
    keyboard access, etc.)."""

    async def run(self, page: Page, page_url: str) -> list[dict]:
        try:
            await page.add_script_tag(content=_AXE_SOURCE)
            results = await asyncio.wait_for(
                page.evaluate(_RUN_AXE_JS),
                timeout=settings.axe_timeout_ms / 1000,
            )
        except Exception:
            return []

        return self._to_bugs(results.get("violations", []), page_url)

    def _to_bugs(self, violations: list[dict], page_url: str) -> list[dict]:
        bugs = []
        for violation in violations[:15]:
            nodes = violation.get("nodes", [])
            selector = None
            if nodes and nodes[0].get("target"):
                selector = ", ".join(nodes[0]["target"][:1])
            tags = [t for t in violation.get("tags", []) if t.startswith("wcag")][:3]
            wcag_note = f" ({', '.join(tags)})" if tags else ""

            bugs.append({
                "severity": _IMPACT_TO_SEVERITY.get(violation.get("impact"), BugSeverity.MEDIUM.value),
                "title": f"{violation.get('help', 'Accessibility issue')} ({len(nodes)})",
                "component": "Accessibility",
                "description": f"{violation.get('description', '')}{wcag_note}. Affects {len(nodes)} element(s).",
                "selector": selector,
                "page_url": page_url,
                "fix_suggestion": violation.get("helpUrl") or "See WCAG guidance for this rule.",
            })
        return bugs
