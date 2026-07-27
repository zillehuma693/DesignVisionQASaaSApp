from playwright.async_api import Page

from app.core.config import settings
from app.core.enums import BugSeverity

# LCP and layout-shift entries aren't reliably retrievable after the fact via
# getEntriesByType() — Chromium only buffers them for an observer that was
# listening from the start of the page's lifecycle. Installed once per
# browser context via add_init_script() so it re-runs on every navigation
# (including cross-origin ones during the crawl) before any page script runs.
INIT_SCRIPT = """
(() => {
    window.__visionqaPerf = { lcp: null, cls: 0 };
    try {
        new PerformanceObserver((list) => {
            const entries = list.getEntries();
            const last = entries[entries.length - 1];
            if (last) window.__visionqaPerf.lcp = Math.round(last.startTime);
        }).observe({ type: 'largest-contentful-paint', buffered: true });
    } catch (e) {}
    try {
        new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
                if (!entry.hadRecentInput) window.__visionqaPerf.cls += entry.value;
            }
        }).observe({ type: 'layout-shift', buffered: true });
    } catch (e) {}
})();
"""

_METRICS_JS = """() => {
    const nav = performance.getEntriesByType('navigation')[0];
    const ttfb = nav ? Math.round(nav.responseStart) : null;
    const loadTime = nav ? Math.round(nav.loadEventEnd) : null;
    const perf = window.__visionqaPerf || {};
    return {
        ttfb,
        loadTime,
        lcp: perf.lcp != null ? perf.lcp : null,
        cls: perf.cls != null ? Math.round(perf.cls * 1000) / 1000 : null,
    };
}"""


class PerformanceEngine:
    """Captures Core-Web-Vitals-style metrics per page. Requires INIT_SCRIPT
    to be installed on the browser context (see playwright_runner.py) before
    any navigation happens."""

    async def measure(self, page: Page) -> dict:
        try:
            return await page.evaluate(_METRICS_JS)
        except Exception:
            return {}

    def to_bugs(self, metrics: dict, page_url: str) -> list[dict]:
        bugs = []
        lcp = metrics.get("lcp")
        cls = metrics.get("cls")
        ttfb = metrics.get("ttfb")

        if lcp is not None:
            if lcp >= settings.perf_lcp_bad_ms:
                bugs.append(self._bug(BugSeverity.HIGH.value, "Slow Largest Contentful Paint",
                                       f"LCP is {lcp}ms (target: under {settings.perf_lcp_warn_ms}ms).",
                                       page_url, "Optimize the largest above-the-fold image/text block: compress images, "
                                       "preload critical assets, remove render-blocking resources."))
            elif lcp >= settings.perf_lcp_warn_ms:
                bugs.append(self._bug(BugSeverity.MEDIUM.value, "Largest Contentful Paint needs improvement",
                                       f"LCP is {lcp}ms (target: under {settings.perf_lcp_warn_ms}ms).",
                                       page_url, "Optimize the largest above-the-fold image/text block."))

        if cls is not None:
            if cls >= settings.perf_cls_bad:
                bugs.append(self._bug(BugSeverity.HIGH.value, "High Cumulative Layout Shift",
                                       f"CLS is {cls} (target: under {settings.perf_cls_warn}).",
                                       page_url, "Reserve space for images/ads/embeds with explicit width/height, "
                                       "avoid inserting content above existing content after load."))
            elif cls >= settings.perf_cls_warn:
                bugs.append(self._bug(BugSeverity.MEDIUM.value, "Layout shift needs improvement",
                                       f"CLS is {cls} (target: under {settings.perf_cls_warn}).",
                                       page_url, "Reserve space for dynamically-loaded content."))

        if ttfb is not None and ttfb >= settings.perf_ttfb_warn_ms:
            bugs.append(self._bug(BugSeverity.MEDIUM.value, "Slow server response",
                                   f"Time to First Byte is {ttfb}ms (target: under {settings.perf_ttfb_warn_ms}ms).",
                                   page_url, "Investigate backend/API latency, add caching, or use a CDN."))

        return bugs

    def _bug(self, severity: str, title: str, description: str, page_url: str, fix: str) -> dict:
        return {
            "severity": severity,
            "title": title,
            "component": "Performance",
            "description": description,
            "selector": None,
            "page_url": page_url,
            "fix_suggestion": fix,
        }
