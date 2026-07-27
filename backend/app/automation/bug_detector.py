import re
import uuid
from pathlib import Path
from urllib.parse import urljoin, urlparse

from app.core.config import settings
from app.core.enums import BugSeverity, ScanStatus


def _same_origin(base: str, target: str) -> bool:
    base_p = urlparse(base)
    target_p = urlparse(target)
    return base_p.netloc == target_p.netloc and base_p.scheme == target_p.scheme


_LEADING_TIMESTAMP_RE = re.compile(r"^\d{1,2}:\d{2}:\d{2}(:\d{1,3})?\s*")
_ISO_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?")


def _normalize_error_key(message: str) -> str:
    """Strip volatile bits (timestamps) so the same recurring error dedupes
    even though libraries like Agora's SDK prefix each log line with a
    wall-clock timestamp, making otherwise-identical messages look unique."""
    stripped = _LEADING_TIMESTAMP_RE.sub("", message)
    stripped = _ISO_TIMESTAMP_RE.sub("<timestamp>", stripped)
    return stripped.strip()


class BugDetector:
    def detect_console_errors(self, errors: list[str], page_url: str) -> list[dict]:
        counts: dict[str, int] = {}
        representative: dict[str, str] = {}
        order: list[str] = []
        for err in errors:
            key = _normalize_error_key(err)
            if key not in counts:
                order.append(key)
                representative[key] = err
            counts[key] = counts.get(key, 0) + 1

        bugs = []
        for key in order[:10]:
            count = counts[key]
            suffix = f" (occurred {count}x during the scan)" if count > 1 else ""
            bugs.append({
                "severity": BugSeverity.HIGH.value,
                "title": "JavaScript console error",
                "component": "Console",
                "description": representative[key][:500] + suffix,
                "selector": None,
                "page_url": page_url,
                "fix_suggestion": "Fix the JavaScript error in the browser console stack trace.",
            })
        return bugs

    def detect_missing_alt(self, images: list[dict], page_url: str) -> list[dict]:
        missing = [img for img in images if not img.get("alt")]
        if not missing:
            return []
        return [{
            "severity": BugSeverity.MEDIUM.value,
            "title": f"Images missing alt text ({len(missing)})",
            "component": "Image",
            "description": f"{len(missing)} image(s) lack alt attributes, failing accessibility checks.",
            "selector": "img:not([alt])",
            "page_url": page_url,
            "fix_suggestion": 'Add descriptive alt text: <img src="..." alt="Description" />',
        }]

    def detect_broken_links(self, links: list[dict], page_url: str) -> list[dict]:
        broken = [l for l in links if l.get("status", 200) >= 400]
        bugs = []
        for link in broken[:5]:
            bugs.append({
                "severity": BugSeverity.HIGH.value,
                "title": f"Broken link ({link.get('status')})",
                "component": "Anchor",
                "description": f"Link to {link.get('href')} returned HTTP {link.get('status')}.",
                "selector": link.get("selector"),
                "page_url": page_url,
                "fix_suggestion": "Verify the URL is correct and the resource is available.",
            })
        return bugs

    def detect_broken_images(self, images: list[dict], page_url: str) -> list[dict]:
        broken = [img for img in images if img.get("broken")]
        if not broken:
            return []
        return [{
            "severity": BugSeverity.HIGH.value,
            "title": f"Broken images ({len(broken)})",
            "component": "Image",
            "description": f"{len(broken)} image(s) failed to load on the page.",
            "selector": "img",
            "page_url": page_url,
            "fix_suggestion": "Check image URLs and ensure assets are deployed correctly.",
        }]

    def detect_missing_meta(self, page_url: str, has_title: bool, has_viewport: bool) -> list[dict]:
        bugs = []
        if not has_title:
            bugs.append({
                "severity": BugSeverity.MEDIUM.value,
                "title": "Missing page title",
                "component": "Head",
                "description": "Page is missing a <title> element.",
                "selector": "title",
                "page_url": page_url,
                "fix_suggestion": "<title>Your Page Title</title>",
            })
        if not has_viewport:
            bugs.append({
                "severity": BugSeverity.HIGH.value,
                "title": "Missing viewport meta tag",
                "component": "Head",
                "description": "No viewport meta tag found — mobile responsiveness may fail.",
                "selector": 'meta[name="viewport"]',
                "page_url": page_url,
                "fix_suggestion": '<meta name="viewport" content="width=device-width, initial-scale=1">',
            })
        return bugs

    def detect_contrast_issues(self, low_contrast: list[dict], page_url: str) -> list[dict]:
        if not low_contrast:
            return []
        worst = min(low_contrast, key=lambda x: x["ratio"])
        return [{
            "severity": BugSeverity.HIGH.value,
            "title": f"Low text contrast ({len(low_contrast)} element(s))",
            "component": "Typography",
            "description": (
                f"{len(low_contrast)} text element(s) fail WCAG AA contrast. Worst: "
                f'"{worst["text"]}" at {worst["ratio"]}:1 (needs {worst["required"]}:1).'
            ),
            "selector": None,
            "page_url": page_url,
            "fix_suggestion": "Increase text/background color contrast to meet WCAG 2.1 AA (4.5:1 normal text, 3:1 large text).",
        }]

    def detect_responsive_overflow(self, scroll_width: int, client_width: int, viewport: str, page_url: str) -> list[dict]:
        if scroll_width <= client_width + 1:
            return []
        return [{
            "severity": BugSeverity.HIGH.value,
            "title": f"Horizontal overflow on {viewport}",
            "component": "Layout",
            "description": f"Page content is {scroll_width}px wide but the {viewport} viewport is {client_width}px, causing horizontal scroll.",
            "selector": None,
            "page_url": page_url,
            "fix_suggestion": "Add `overflow-x: hidden` on the offending container or constrain child widths with max-width: 100%.",
        }]

    def detect_element_overlap(self, overlaps: list[dict], viewport: str, page_url: str) -> list[dict]:
        if not overlaps:
            return []
        sample = ", ".join(f'"{o["a"]}" over "{o["b"]}"' for o in overlaps[:3])
        return [{
            "severity": BugSeverity.HIGH.value,
            "title": f"Overlapping elements on {viewport} ({len(overlaps)})",
            "component": "Layout",
            "description": f"{len(overlaps)} pair(s) of elements visually overlap at the {viewport} viewport: {sample}.",
            "selector": None,
            "page_url": page_url,
            "fix_suggestion": "Check flex/grid sizing and absolute-positioned elements at this breakpoint; add spacing or wrap content.",
        }]

    def detect_offviewport_elements(self, count: int, viewport: str, page_url: str) -> list[dict]:
        if count <= 0:
            return []
        return [{
            "severity": BugSeverity.HIGH.value,
            "title": f"Interactive elements outside viewport on {viewport} ({count})",
            "component": "Layout",
            "description": f"{count} clickable element(s) render fully off-screen horizontally at the {viewport} viewport width and can't be reached without extra scrolling.",
            "selector": None,
            "page_url": page_url,
            "fix_suggestion": "Constrain the containing element's width or fix a wrapper that's wider than the viewport at this breakpoint.",
        }]

    def detect_clipped_text(self, count: int, viewport: str, page_url: str) -> list[dict]:
        if count <= 0:
            return []
        return [{
            "severity": BugSeverity.MEDIUM.value,
            "title": f"Clipped text on {viewport} ({count})",
            "component": "Layout",
            "description": f"{count} text element(s) are wider than their container and get cut off at the {viewport} viewport.",
            "selector": None,
            "page_url": page_url,
            "fix_suggestion": "Allow wrapping (white-space: normal), shrink font-size responsively, or widen the container at this breakpoint.",
        }]

    def detect_form_labels(self, total: int, unlabeled: int, page_url: str) -> list[dict]:
        if unlabeled <= 0:
            return []
        return [{
            "severity": BugSeverity.MEDIUM.value,
            "title": f"Form fields missing labels ({unlabeled}/{total})",
            "component": "Form",
            "description": f"{unlabeled} input/select/textarea element(s) have no associated <label>, aria-label, or aria-labelledby.",
            "selector": "input, select, textarea",
            "page_url": page_url,
            "fix_suggestion": '<label for="email">Email</label><input id="email" type="email" /> or aria-label="Email"',
        }]

    def detect_heading_structure(self, h1_count: int, skipped: bool, total: int, page_url: str) -> list[dict]:
        bugs = []
        if total > 0 and h1_count == 0:
            bugs.append({
                "severity": BugSeverity.MEDIUM.value,
                "title": "Missing <h1>",
                "component": "Heading",
                "description": "Page has headings but no <h1>, hurting document structure and SEO.",
                "selector": "h1",
                "page_url": page_url,
                "fix_suggestion": "Add exactly one <h1> describing the page's main content.",
            })
        elif h1_count > 1:
            bugs.append({
                "severity": BugSeverity.LOW.value,
                "title": f"Multiple <h1> elements ({h1_count})",
                "component": "Heading",
                "description": "More than one <h1> on the page dilutes document outline semantics.",
                "selector": "h1",
                "page_url": page_url,
                "fix_suggestion": "Use a single <h1> per page; demote the rest to <h2>/<h3>.",
            })
        if skipped:
            bugs.append({
                "severity": BugSeverity.LOW.value,
                "title": "Skipped heading level",
                "component": "Heading",
                "description": "Heading levels jump (e.g. h2 to h4) without an intermediate level, breaking the document outline.",
                "selector": "h1, h2, h3, h4, h5, h6",
                "page_url": page_url,
                "fix_suggestion": "Keep heading levels sequential; don't skip levels for visual styling alone.",
            })
        return bugs

    def detect_seo_issues(self, lang: str | None, meta_description: str | None, title_length: int, page_url: str) -> list[dict]:
        bugs = []
        if not lang:
            bugs.append({
                "severity": BugSeverity.MEDIUM.value,
                "title": "Missing lang attribute",
                "component": "Head",
                "description": "<html> has no lang attribute, hurting screen readers and SEO.",
                "selector": "html",
                "page_url": page_url,
                "fix_suggestion": '<html lang="en">',
            })
        if not meta_description:
            bugs.append({
                "severity": BugSeverity.LOW.value,
                "title": "Missing meta description",
                "component": "Head",
                "description": "No <meta name=\"description\"> found — hurts search result snippets.",
                "selector": 'meta[name="description"]',
                "page_url": page_url,
                "fix_suggestion": '<meta name="description" content="Concise page summary under 160 characters.">',
            })
        if title_length > 60:
            bugs.append({
                "severity": BugSeverity.LOW.value,
                "title": f"Page title too long ({title_length} chars)",
                "component": "Head",
                "description": "Titles over ~60 characters get truncated in search results.",
                "selector": "title",
                "page_url": page_url,
                "fix_suggestion": "Shorten the <title> to under 60 characters.",
            })
        return bugs

    def detect_mixed_content(self, count: int, page_url: str) -> list[dict]:
        if count <= 0:
            return []
        return [{
            "severity": BugSeverity.HIGH.value,
            "title": f"Mixed content ({count} resource(s))",
            "component": "Security",
            "description": f"{count} resource(s) load over http:// on an https:// page, which browsers may block.",
            "selector": None,
            "page_url": page_url,
            "fix_suggestion": "Serve all resources (images, scripts, styles, iframes) over https://.",
        }]

    def detect_duplicate_ids(self, duplicate_ids: list[str], page_url: str) -> list[dict]:
        if not duplicate_ids:
            return []
        return [{
            "severity": BugSeverity.MEDIUM.value,
            "title": f"Duplicate element IDs ({len(duplicate_ids)})",
            "component": "HTML",
            "description": f"Duplicate id attribute(s): {', '.join(duplicate_ids[:5])}. IDs must be unique per page.",
            "selector": None,
            "page_url": page_url,
            "fix_suggestion": "Ensure every id attribute value is unique within the document.",
        }]

    def detect_empty_links(self, count: int, page_url: str) -> list[dict]:
        if count <= 0:
            return []
        return [{
            "severity": BugSeverity.LOW.value,
            "title": f"Placeholder links ({count})",
            "component": "Anchor",
            "description": f'{count} link(s) use href="#" or href="" and go nowhere.',
            "selector": 'a[href="#"], a[href=""]',
            "page_url": page_url,
            "fix_suggestion": "Point the link at a real destination, or use a <button> if it only triggers JS behavior.",
        }]

    def detect_small_tap_targets(self, total: int, small: int, page_url: str) -> list[dict]:
        if small <= 0:
            return []
        return [{
            "severity": BugSeverity.MEDIUM.value,
            "title": f"Tap targets too small ({small})",
            "component": "Touch",
            "description": f"{small} of {total} interactive element(s) are smaller than the 44x44px minimum recommended tap target size.",
            "selector": "a, button",
            "page_url": page_url,
            "fix_suggestion": "Increase padding or min-width/min-height to at least 44x44px on mobile.",
        }]

    def detect_network_errors(self, failed_requests: list[dict], page_url: str) -> list[dict]:
        if not failed_requests:
            return []
        by_url: dict[str, int] = {}
        for req in failed_requests:
            by_url[req["url"]] = req["status"]
        worst_status = max(by_url.values())
        severity = BugSeverity.CRITICAL.value if worst_status >= 500 else BugSeverity.HIGH.value
        sample = list(by_url.items())[:5]
        return [{
            "severity": severity,
            "title": f"Failed network requests ({len(by_url)})",
            "component": "Network",
            "description": "Failed resource/API requests: " + ", ".join(f"{u} ({s})" for u, s in sample),
            "selector": None,
            "page_url": page_url,
            "fix_suggestion": "Check server logs for these endpoints; ensure assets and APIs return 2xx.",
        }]

    def detect_slow_requests(self, all_requests: list[dict], threshold_ms: int, page_url: str) -> list[dict]:
        slow = [r for r in all_requests if r.get("duration_ms") and r["duration_ms"] >= threshold_ms]
        if not slow:
            return []
        slow_sorted = sorted(slow, key=lambda r: -r["duration_ms"])[:5]
        sample = ", ".join(f"{r['url']} ({r['duration_ms']}ms)" for r in slow_sorted)
        return [{
            "severity": BugSeverity.MEDIUM.value,
            "title": f"Slow network requests ({len(slow)})",
            "component": "Performance",
            "description": f"{len(slow)} request(s) took over {threshold_ms}ms: {sample}",
            "selector": None,
            "page_url": page_url,
            "fix_suggestion": "Profile and optimize these endpoints/assets, or lazy-load non-critical resources.",
        }]

    def detect_duplicate_requests(self, all_requests: list[dict], page_url: str) -> list[dict]:
        counts: dict[str, int] = {}
        for req in all_requests:
            counts[req["url"]] = counts.get(req["url"], 0) + 1
        dupes = {url: count for url, count in counts.items() if count > 1}
        if not dupes:
            return []
        sample = ", ".join(f"{url} (x{count})" for url, count in list(dupes.items())[:5])
        return [{
            "severity": BugSeverity.LOW.value,
            "title": f"Duplicate network requests ({len(dupes)})",
            "component": "Performance",
            "description": f"{len(dupes)} distinct URL(s) were requested more than once during the scan: {sample}",
            "selector": None,
            "page_url": page_url,
            "fix_suggestion": "Cache or dedupe repeated fetches (e.g. via React Query/SWR, or HTTP caching headers).",
        }]

    _COUNT_SUFFIX_RE = re.compile(r"\s*\(.*\)\s*$")
    _SEVERITY_RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}

    def merge_recurring_bugs(self, bugs: list[dict]) -> list[dict]:
        """Site-wide issues (missing h1, low contrast, unlabeled buttons, etc.)
        get detected once per page they appear on, which floods the report with
        near-duplicates for what's really one underlying problem repeated across
        a shared layout/component. Group by (component, title-without-count) and
        collapse each group into a single entry listing the affected pages."""
        groups: dict[tuple[str, str], list[dict]] = {}
        order: list[tuple[str, str]] = []
        for bug in bugs:
            family_title = self._COUNT_SUFFIX_RE.sub("", bug.get("title", "")).strip()
            key = (bug.get("component", "Unknown"), family_title)
            if key not in groups:
                order.append(key)
                groups[key] = []
            groups[key].append(bug)

        merged = []
        for key in order:
            group = groups[key]
            if len(group) == 1:
                merged.append(group[0])
                continue

            component, family_title = key
            pages: list[str] = []
            for bug in group:
                url = bug.get("page_url")
                if url and url not in pages:
                    pages.append(url)
            descriptions: list[str] = []
            for bug in group:
                desc = bug.get("description", "")
                if desc and desc not in descriptions:
                    descriptions.append(desc)

            worst = max(group, key=lambda b: self._SEVERITY_RANK.get(b.get("severity", "medium"), 1))
            selector = next((b.get("selector") for b in group if b.get("selector")), None)
            fix_suggestion = next((b.get("fix_suggestion") for b in group if b.get("fix_suggestion")), None)
            node_id = next((b.get("_node_id") for b in group if b.get("_node_id")), None)

            shown = descriptions[:3]
            extra_note = f" (+{len(descriptions) - 3} more variant(s))" if len(descriptions) > 3 else ""
            page_note = f" Occurs on {len(pages)} pages." if len(pages) > 1 else ""
            merged_description = "; ".join(shown) + extra_note + page_note

            merged.append({
                "severity": worst["severity"],
                "title": f"{family_title} ({len(pages)} pages)" if len(pages) > 1 else group[0]["title"],
                "component": component,
                "description": merged_description,
                "selector": selector,
                "page_url": pages[0] if pages else group[0].get("page_url"),
                "fix_suggestion": fix_suggestion,
                "_node_id": node_id,
            })
        return merged

    def calculate_health_score(self, bugs: list[dict]) -> int:
        if not bugs:
            return 100
        penalty = 0
        for bug in bugs:
            sev = bug.get("severity", "medium")
            penalty += {"critical": 15, "high": 10, "medium": 5, "low": 2}.get(sev, 5)
        return max(0, min(100, 100 - penalty))
