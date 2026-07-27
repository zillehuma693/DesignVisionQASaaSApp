import time
import uuid
from pathlib import Path
from typing import Awaitable, Callable

from playwright.async_api import Page

from app.automation.bug_detector import BugDetector
from app.automation.crawler_engine import CrawlerEngine
from app.automation.state_graph import GraphNode
from app.automation.viewports import VIEWPORTS as RESPONSIVE_VIEWPORTS
from app.core.config import settings
from app.models.scan import Screenshot

OnLog = Callable[[str, str, str], Awaitable[None]]

_LAYOUT_JS = """() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
})"""

_OVERLAP_JS = """() => {
    const els = Array.from(document.querySelectorAll(
        'button, a, input, select, textarea, [role="button"], h1, h2, h3, p, img, label'
    )).filter(el => {
        const r = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return r.width > 4 && r.height > 4 && style.display !== 'none' && style.visibility !== 'hidden'
            && parseFloat(style.opacity) > 0;
    }).slice(0, 200);

    const rects = els.map(el => ({ el, r: el.getBoundingClientRect() }));
    const overlaps = [];
    for (let i = 0; i < rects.length && overlaps.length < 10; i++) {
        for (let j = i + 1; j < rects.length && overlaps.length < 10; j++) {
            const { el: elA, r: a } = rects[i];
            const { el: elB, r: b } = rects[j];
            if (elA.contains(elB) || elB.contains(elA)) continue;
            const overlapX = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
            const overlapY = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
            const overlapArea = overlapX * overlapY;
            const minArea = Math.min(a.width * a.height, b.width * b.height);
            if (minArea > 0 && overlapArea / minArea > 0.35) {
                overlaps.push({
                    a: elA.tagName + ':' + (elA.textContent || '').trim().slice(0, 24),
                    b: elB.tagName + ':' + (elB.textContent || '').trim().slice(0, 24),
                });
            }
        }
    }
    return overlaps;
}"""

_OFFVIEWPORT_JS = """() => {
    function isScreenReaderOnly(el) {
        const r = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return (r.width <= 1 && r.height <= 1) || style.clip === 'rect(0px, 0px, 0px, 0px)'
            || /sr-only|visually-hidden|screen-reader/i.test(el.className || '');
    }
    const els = Array.from(document.querySelectorAll('a[href], button, input, [role="button"]'));
    let count = 0;
    for (const el of els) {
        const style = getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity) === 0) continue;
        if (isScreenReaderOnly(el)) continue;
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        if (r.right <= 0 || r.left >= window.innerWidth) count++;
    }
    return count;
}"""

_CLIPPED_TEXT_JS = """() => {
    const els = Array.from(document.querySelectorAll('p, span, h1, h2, h3, h4, button, a, label'))
        .filter(el => {
            const style = getComputedStyle(el);
            const overflowsX = el.scrollWidth > el.clientWidth + 2;
            const hidesOverflow = style.overflowX === 'hidden' || style.whiteSpace === 'nowrap';
            return overflowsX && hidesOverflow && (el.textContent || '').trim().length > 0;
        });
    return els.length;
}"""


class ResponsiveEngine:
    """Replays already-discovered pages at additional viewport sizes and
    checks for layout breakage — the visual/responsive counterpart to the
    crawler's structural exploration."""

    def __init__(self, scan_id: uuid.UUID, primary_viewport: str) -> None:
        self.scan_id = scan_id
        self.primary_viewport = primary_viewport if primary_viewport in RESPONSIVE_VIEWPORTS else "desktop"
        self.detector = BugDetector()

    async def run(self, page: Page, crawler: CrawlerEngine, on_log: OnLog) -> list[dict]:
        bugs: list[dict] = []
        extra_viewports = [v for v in RESPONSIVE_VIEWPORTS if v != self.primary_viewport]
        nodes = crawler.graph.all_nodes()[: settings.responsive_max_nodes]
        start = time.monotonic()

        for node in nodes:
            if time.monotonic() - start > settings.responsive_max_duration_seconds:
                await on_log("warn", "Responsive QA pass time limit reached; stopping early.", "responsive")
                break

            for viewport_name in extra_viewports:
                try:
                    await page.set_viewport_size(RESPONSIVE_VIEWPORTS[viewport_name])
                    reached = await crawler.reach_node(page, node)
                except Exception:
                    reached = False

                if not reached:
                    await on_log(
                        "warn",
                        f'Could not reach "{node.label}" at {viewport_name} (navigation may differ at this size)',
                        "responsive",
                    )
                    continue

                await page.wait_for_timeout(350)

                shot_path = Path(settings.screenshots_path) / f"{self.scan_id}_node_{node.id}_{viewport_name}.png"
                try:
                    await page.screenshot(path=str(shot_path), full_page=True)
                    await Screenshot(
                        scan_id=self.scan_id,
                        node_id=node.id,
                        file_path=str(shot_path),
                        page_url=node.url,
                        viewport=viewport_name,
                        label=f"{node.label} · {viewport_name}",
                    ).insert()
                except Exception as exc:
                    await on_log("warn", f'Could not screenshot "{node.label}" at {viewport_name}: {exc}', "responsive")

                try:
                    node_bugs = await self._analyze_viewport(page, node, viewport_name)
                    for bug in node_bugs:
                        bug["_node_id"] = node.id
                    bugs.extend(node_bugs)
                except Exception as exc:
                    await on_log("warn", f'Responsive check failed for "{node.label}" at {viewport_name}: {exc}', "responsive")

            try:
                await page.set_viewport_size(RESPONSIVE_VIEWPORTS[self.primary_viewport])
            except Exception:
                pass

        return bugs

    async def _analyze_viewport(self, page: Page, node: GraphNode, viewport_name: str) -> list[dict]:
        bugs: list[dict] = []

        layout = await page.evaluate(_LAYOUT_JS)
        bugs.extend(self.detector.detect_responsive_overflow(
            layout["scrollWidth"], layout["clientWidth"], viewport_name, node.url,
        ))

        overlaps = await page.evaluate(_OVERLAP_JS)
        bugs.extend(self.detector.detect_element_overlap(overlaps, viewport_name, node.url))

        offviewport_count = await page.evaluate(_OFFVIEWPORT_JS)
        bugs.extend(self.detector.detect_offviewport_elements(offviewport_count, viewport_name, node.url))

        clipped_count = await page.evaluate(_CLIPPED_TEXT_JS)
        bugs.extend(self.detector.detect_clipped_text(clipped_count, viewport_name, node.url))

        return bugs
