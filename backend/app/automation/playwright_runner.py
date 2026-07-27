import asyncio
import json
import subprocess
import sys
import time
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, async_playwright

from app.automation.accessibility_engine import AccessibilityEngine
from app.automation.bug_detector import BugDetector
from app.automation.crawler_engine import CrawlerEngine
from app.automation.interaction_engine import InteractionEngine
from app.automation.navigation import friendly_navigation_error, goto_with_retries
from app.automation.performance_engine import INIT_SCRIPT as PERFORMANCE_INIT_SCRIPT
from app.automation.performance_engine import PerformanceEngine
from app.automation.responsive_engine import ResponsiveEngine
from app.automation.state_graph import GraphNode
from app.automation.viewports import VIEWPORTS
from app.core.config import settings
from app.core.crypto import decrypt_text
from app.core.enums import BugSeverity, ProjectStatus, ScanStatus
from app.core.logging import get_logger
from app.models.auth_profile import AuthProfile
from app.models.bug import Bug
from app.models.project import Project
from app.models.scan import Scan, ScanLog, ScanNode, Screenshot
from app.services.ai.provider import FallbackAIProvider, get_ai_provider

logger = get_logger(__name__)


class PlaywrightRunner:
    def __init__(self) -> None:
        self.detector = BugDetector()

    async def _log(self, scan_id: uuid.UUID, level: str, message: str, source: str = "system") -> None:
        await ScanLog(scan_id=scan_id, level=level, message=message, source=source).insert()

    async def _update_scan(self, scan: Scan, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(scan, key, value)
        await scan.save()

    async def _analyze_page(self, page: Page, viewport_name: str, page_url: str) -> list[dict]:
        bugs: list[dict] = []

        images = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('img')).map((img, i) => ({
                alt: img.getAttribute('alt'),
                src: img.src,
                broken: img.naturalWidth === 0 && img.complete,
                selector: 'img:nth-of-type(' + (i+1) + ')',
            }));
        }""")

        link_elements = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a[href]')).slice(0, 20).map((a, i) => ({
                href: a.href,
                selector: 'a:nth-of-type(' + (i+1) + ')',
            }));
        }""")

        links = []
        for link in link_elements[:10]:
            try:
                resp = await page.request.head(link["href"], timeout=10000)
                links.append({**link, "status": resp.status})
            except Exception:
                links.append({**link, "status": 0})

        meta = await page.evaluate("""() => ({
            hasTitle: !!document.title,
            hasViewport: !!document.querySelector('meta[name="viewport"]'),
        })""")

        layout = await page.evaluate("""() => ({
            scrollWidth: document.documentElement.scrollWidth,
            clientWidth: document.documentElement.clientWidth,
        })""")

        page_audit = await page.evaluate("""() => {
            const heads = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6')).map(h => parseInt(h.tagName[1]));
            let skipped = false;
            for (let i = 1; i < heads.length; i++) {
                if (heads[i] - heads[i - 1] > 1) { skipped = true; break; }
            }

            const fields = Array.from(document.querySelectorAll('input, select, textarea'))
                .filter(el => !['hidden', 'submit', 'button', 'image'].includes(el.type));
            const unlabeled = fields.filter(el => {
                if (el.getAttribute('aria-label') || el.getAttribute('aria-labelledby')) return false;
                if (el.id && document.querySelector('label[for="' + CSS.escape(el.id) + '"]')) return false;
                if (el.closest('label')) return false;
                return true;
            }).length;

            const ids = Array.from(document.querySelectorAll('[id]')).map(el => el.id);
            const seen = new Set(); const dupes = new Set();
            for (const id of ids) { if (seen.has(id)) dupes.add(id); seen.add(id); }

            const emptyLinks = Array.from(document.querySelectorAll('a')).filter(a => {
                const href = a.getAttribute('href');
                return href === '#' || href === '';
            }).length;

            const clickable = Array.from(document.querySelectorAll('a, button, input[type=button], input[type=submit], [role=button]'));
            let small = 0;
            for (const el of clickable) {
                const r = el.getBoundingClientRect();
                if (r.width > 0 && r.height > 0 && (r.width < 44 || r.height < 44)) small++;
            }

            const desc = document.querySelector('meta[name="description"]');
            const mixedContentCount = location.protocol === 'https:'
                ? Array.from(document.querySelectorAll('img[src], script[src], link[href], iframe[src]'))
                    .filter(el => (el.src || el.href || '').startsWith('http://')).length
                : 0;

            const buttonsNoLabel = Array.from(document.querySelectorAll('button')).filter(b =>
                !b.textContent?.trim() && !b.getAttribute('aria-label')
            ).length;

            return {
                heading: { h1Count: heads.filter(l => l === 1).length, skipped, total: heads.length },
                forms: { total: fields.length, unlabeled },
                duplicateIds: Array.from(dupes).slice(0, 10),
                emptyLinks,
                tapTargets: { total: clickable.length, small },
                seo: {
                    lang: document.documentElement.getAttribute('lang'),
                    metaDescription: desc ? desc.getAttribute('content') : null,
                    titleLength: document.title.length,
                },
                mixedContentCount,
                buttonsNoLabel,
            };
        }""")

        contrast_issues = await page.evaluate("""() => {
            function luminance(r, g, b) {
                const a = [r, g, b].map(v => {
                    v /= 255;
                    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
                });
                return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
            }
            function parseColor(str) {
                const m = str.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([\\d.]+))?\\)/);
                if (!m) return null;
                return { r: +m[1], g: +m[2], b: +m[3], a: m[4] !== undefined ? +m[4] : 1 };
            }
            function effectiveBg(el) {
                let node = el;
                while (node) {
                    const c = parseColor(getComputedStyle(node).backgroundColor);
                    if (c && c.a > 0) return c;
                    node = node.parentElement;
                }
                return { r: 255, g: 255, b: 255, a: 1 };
            }
            const els = Array.from(document.querySelectorAll('body *')).filter(el => {
                const style = getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden') return false;
                return Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim().length > 0);
            }).slice(0, 150);
            const results = [];
            for (const el of els) {
                const style = getComputedStyle(el);
                const fg = parseColor(style.color);
                if (!fg) continue;
                const bg = effectiveBg(el);
                const l1 = luminance(fg.r, fg.g, fg.b) + 0.05;
                const l2 = luminance(bg.r, bg.g, bg.b) + 0.05;
                const ratio = l1 > l2 ? l1 / l2 : l2 / l1;
                const fontSize = parseFloat(style.fontSize);
                const fontWeight = parseInt(style.fontWeight) || 400;
                const isLarge = fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700);
                const minRatio = isLarge ? 3 : 4.5;
                if (ratio < minRatio) {
                    results.push({ ratio: Math.round(ratio * 100) / 100, required: minRatio, text: el.textContent.trim().slice(0, 40) });
                }
            }
            return results.slice(0, 20);
        }""")

        bugs.extend(self.detector.detect_missing_alt(images, page_url))
        bugs.extend(self.detector.detect_broken_links(links, page_url))
        bugs.extend(self.detector.detect_broken_images(images, page_url))
        bugs.extend(self.detector.detect_missing_meta(page_url, meta["hasTitle"], meta["hasViewport"]))
        bugs.extend(self.detector.detect_contrast_issues(contrast_issues, page_url))
        bugs.extend(self.detector.detect_responsive_overflow(
            layout["scrollWidth"], layout["clientWidth"], viewport_name, page_url,
        ))
        bugs.extend(self.detector.detect_form_labels(
            page_audit["forms"]["total"], page_audit["forms"]["unlabeled"], page_url,
        ))
        bugs.extend(self.detector.detect_heading_structure(
            page_audit["heading"]["h1Count"], page_audit["heading"]["skipped"], page_audit["heading"]["total"], page_url,
        ))
        bugs.extend(self.detector.detect_seo_issues(
            page_audit["seo"]["lang"], page_audit["seo"]["metaDescription"], page_audit["seo"]["titleLength"], page_url,
        ))
        bugs.extend(self.detector.detect_mixed_content(page_audit["mixedContentCount"], page_url))
        bugs.extend(self.detector.detect_duplicate_ids(page_audit["duplicateIds"], page_url))
        bugs.extend(self.detector.detect_empty_links(page_audit["emptyLinks"], page_url))
        if viewport_name == "mobile":
            bugs.extend(self.detector.detect_small_tap_targets(
                page_audit["tapTargets"]["total"], page_audit["tapTargets"]["small"], page_url,
            ))
        if page_audit["buttonsNoLabel"] > 0:
            bugs.append({
                "severity": BugSeverity.MEDIUM.value,
                "title": f"Buttons missing accessible labels ({page_audit['buttonsNoLabel']})",
                "component": "Button",
                "description": f"{page_audit['buttonsNoLabel']} button(s) have no text or aria-label.",
                "selector": "button",
                "page_url": page_url,
                "fix_suggestion": 'Add aria-label="Action name" or visible text to buttons.',
            })

        return bugs

    async def run_scan(self, scan_id: uuid.UUID) -> None:
        scan = await Scan.get(scan_id)
        if not scan:
            return

        Path(settings.screenshots_path).mkdir(parents=True, exist_ok=True)
        start = time.time()
        all_bugs: list[dict] = []
        console_errors: list[str] = []
        failed_requests: list[dict] = []
        all_requests: list[dict] = []
        request_start_times: dict[str, float] = {}
        screenshot_index = 0
        interaction_engine = InteractionEngine()
        interaction_state = {"nodes_done": 0, "start": time.time()}
        accessibility_engine = AccessibilityEngine()
        accessibility_nodes_done = 0
        performance_engine = PerformanceEngine()

        try:
            await self._update_scan(
                scan,
                status=ScanStatus.RUNNING.value,
                started_at=datetime.now(UTC),
                progress=5,
                current_phase="Launching browser",
            )
            await self._log(scan.id, "info", "Launching Playwright browser", "system")

            storage_state = None
            if scan.auth_profile_id:
                profile = await AuthProfile.get(scan.auth_profile_id)
                if profile and profile.user_id == scan.user_id:
                    storage_state = json.loads(decrypt_text(profile.storage_state_encrypted))
                    await self._log(scan.id, "info", "Using saved login session", "system")
                else:
                    await self._log(scan.id, "warn", "Saved login session not found; scanning without it", "system")

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=settings.playwright_headless)
                viewport = VIEWPORTS.get(scan.viewport, VIEWPORTS["desktop"])
                context = await browser.new_context(viewport=viewport, storage_state=storage_state)
                await context.add_init_script(PERFORMANCE_INIT_SCRIPT)
                page = await context.new_page()

                def _on_request(req) -> None:
                    request_start_times[req.url] = time.monotonic()

                def _on_response(resp) -> None:
                    started_at = request_start_times.get(resp.url)
                    duration_ms = int((time.monotonic() - started_at) * 1000) if started_at else None
                    all_requests.append({"url": resp.url, "status": resp.status, "duration_ms": duration_ms})
                    if resp.status >= 400:
                        failed_requests.append({"url": resp.url, "status": resp.status})

                page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
                page.on("request", _on_request)
                page.on("response", _on_response)

                await self._update_scan(scan, progress=15, current_phase="Loading page")
                await self._log(scan.id, "info", f"Navigating to {scan.url}", "network")

                try:
                    response = await goto_with_retries(
                        page,
                        scan.url,
                        timeout_ms=settings.scan_timeout_ms,
                        attempts=3,
                    )
                except PlaywrightError as exc:
                    raise RuntimeError(friendly_navigation_error(scan.url, exc)) from exc

                if not response or response.status >= 400:
                    all_bugs.append({
                        "severity": BugSeverity.CRITICAL.value,
                        "title": f"Page returned HTTP {response.status if response else 'error'}",
                        "component": "Page",
                        "description": f"Failed to load {scan.url} successfully.",
                        "selector": None,
                        "page_url": scan.url,
                        "fix_suggestion": "Verify the URL is accessible and returns a 2xx status.",
                    })

                await self._update_scan(scan, progress=30, current_phase="Capturing screenshots")

                async def on_node_visited(node_page: Page, node: GraphNode) -> None:
                    nonlocal screenshot_index, accessibility_nodes_done
                    screenshot_index += 1
                    is_first = screenshot_index == 1
                    shot_path = Path(settings.screenshots_path) / f"{scan.id}_node_{screenshot_index}.png"

                    # Dashboards commonly render a loading skeleton first and swap in
                    # real content once their own data fetches resolve; without this,
                    # screenshots (and the DOM analysis below) capture the skeleton
                    # instead of the actual page.
                    try:
                        await node_page.wait_for_load_state("networkidle", timeout=4000)
                    except Exception:
                        pass
                    await node_page.wait_for_timeout(400)

                    try:
                        await node_page.screenshot(path=str(shot_path), full_page=True)
                        await Screenshot(
                            scan_id=scan.id,
                            node_id=node.id,
                            file_path=str(shot_path),
                            page_url=node.url,
                            viewport=scan.viewport,
                            label="Initial page load" if is_first else node.label,
                        ).insert()
                    except Exception as exc:
                        await self._log(scan.id, "warn", f'Could not screenshot "{node.label}": {exc}', "crawl")

                    try:
                        page_bugs = await self._analyze_page(node_page, scan.viewport, node.url)
                        for bug in page_bugs:
                            bug["_node_id"] = node.id
                        all_bugs.extend(page_bugs)
                    except Exception as exc:
                        await self._log(scan.id, "warn", f'Could not analyze "{node.label}": {exc}', "crawl")

                    if accessibility_nodes_done < settings.axe_max_nodes:
                        accessibility_nodes_done += 1
                        try:
                            axe_bugs = await accessibility_engine.run(node_page, node.url)
                            for bug in axe_bugs:
                                bug["_node_id"] = node.id
                            all_bugs.extend(axe_bugs)
                        except Exception as exc:
                            await self._log(scan.id, "warn", f'Accessibility audit failed on "{node.label}": {exc}', "a11y")

                    try:
                        metrics = await performance_engine.measure(node_page)
                        perf_bugs = performance_engine.to_bugs(metrics, node.url)
                        for bug in perf_bugs:
                            bug["_node_id"] = node.id
                        all_bugs.extend(perf_bugs)

                        scan_node_doc = await ScanNode.get(node.id)
                        if scan_node_doc:
                            scan_node_doc.lcp_ms = metrics.get("lcp")
                            scan_node_doc.cls = metrics.get("cls")
                            scan_node_doc.ttfb_ms = metrics.get("ttfb")
                            scan_node_doc.load_time_ms = metrics.get("loadTime")
                            await scan_node_doc.save()
                    except Exception as exc:
                        await self._log(scan.id, "warn", f'Performance measurement failed on "{node.label}": {exc}', "performance")

                    within_cap = (
                        interaction_state["nodes_done"] < settings.fill_forms_max_nodes
                        and time.time() - interaction_state["start"] < settings.fill_forms_max_duration_seconds
                    )
                    if within_cap:
                        interaction_state["nodes_done"] += 1
                        try:
                            form_results, form_bugs = await interaction_engine.run(node_page, node.url, scan.fill_forms)
                            for bug in form_bugs:
                                bug["_node_id"] = node.id
                            all_bugs.extend(form_bugs)
                            for result in form_results:
                                await self._log(
                                    scan.id, "info",
                                    f'Form "{result.form_label}": filled {result.fields_filled}/{result.fields_total} '
                                    f"field(s) — {result.outcome}",
                                    "forms",
                                )
                        except Exception as exc:
                            await self._log(scan.id, "warn", f'Form interaction failed on "{node.label}": {exc}', "forms")

                async def on_log(level: str, message: str, source: str) -> None:
                    await self._log(scan.id, level, message, source)

                crawler = CrawlerEngine(scan.id)
                graph = await crawler.run(page, on_node_visited, on_log)

                await self._update_scan(scan, progress=65, current_phase="Testing responsive layouts")
                responsive = ResponsiveEngine(scan.id, scan.viewport)
                all_bugs.extend(await responsive.run(page, crawler, on_log))

                await self._update_scan(scan, progress=80, current_phase="Analyzing DOM")
                all_bugs.extend(self.detector.detect_network_errors(failed_requests, scan.url))
                all_bugs.extend(self.detector.detect_console_errors(console_errors, scan.url))
                all_bugs.extend(self.detector.detect_slow_requests(all_requests, settings.perf_slow_request_ms, scan.url))
                all_bugs.extend(self.detector.detect_duplicate_requests(all_requests, scan.url))

                await browser.close()

            all_bugs = self.detector.merge_recurring_bugs(all_bugs)

            await self._update_scan(scan, progress=90, current_phase="AI analysis")
            ai = get_ai_provider()
            bug_dicts_for_ai = all_bugs[:20]
            try:
                summary = await ai.analyze_scan(scan.url, bug_dicts_for_ai)
            except Exception as exc:
                logger.warning("AI analysis failed: %s", exc)
                summary = await FallbackAIProvider().analyze_scan(scan.url, bug_dicts_for_ai)

            for bug_data in all_bugs:
                try:
                    explanation, fix = await ai.analyze_bug(bug_data)
                    if not bug_data.get("fix_suggestion"):
                        bug_data["fix_suggestion"] = fix
                    bug_data["ai_explanation"] = explanation
                except Exception:
                    bug_data["ai_explanation"] = bug_data.get("description", "")

                await Bug(
                    scan_id=scan.id,
                    node_id=bug_data.get("_node_id"),
                    severity=bug_data["severity"],
                    title=bug_data["title"],
                    component=bug_data["component"],
                    description=bug_data["description"],
                    selector=bug_data.get("selector"),
                    page_url=bug_data.get("page_url"),
                    ai_explanation=bug_data.get("ai_explanation"),
                    fix_suggestion=bug_data.get("fix_suggestion"),
                ).insert()

            health = self.detector.calculate_health_score(all_bugs)
            duration = int(time.time() - start)

            await self._update_scan(
                scan,
                status=ScanStatus.COMPLETED.value,
                health_score=health,
                pages_discovered=graph.node_count,
                nodes_discovered=graph.node_count,
                edges_discovered=graph.edges_count,
                bugs_count=len(all_bugs),
                duration_seconds=duration,
                ai_summary=summary,
                progress=100,
                current_phase="Complete",
                completed_at=datetime.now(UTC),
            )
            await self._log(
                scan.id, "info",
                f"Scan complete: {len(all_bugs)} bugs across {graph.node_count} pages "
                f"({graph.edges_count} interactions explored), score {health}",
                "system",
            )

            if scan.project_id:
                project = await Project.get(scan.project_id)
                if project:
                    if health >= 90:
                        project.status = ProjectStatus.PASSING.value
                    elif health >= 70:
                        project.status = ProjectStatus.WARNING.value
                    else:
                        project.status = ProjectStatus.FAILING.value
                    await project.save()

        except Exception as exc:
            logger.exception("Scan %s failed", scan_id)
            message = str(exc).strip() or f"{type(exc).__name__} (see traceback)"
            # Prefer a short operator-facing message; keep full traceback in server logs only
            # unless it is not a known navigation/network failure.
            log_traceback = not message.startswith("Could not resolve hostname") and "Failed to load" not in message
            await self._update_scan(
                scan,
                status=ScanStatus.FAILED.value,
                error_message=message[:1000],
                progress=100,
                current_phase="Failed",
                completed_at=datetime.now(UTC),
            )
            await self._log(scan.id, "error", message[:500], "system")
            if log_traceback:
                await self._log(scan.id, "error", traceback.format_exc()[:2000], "traceback")


async def run_scan_background(scan_id: uuid.UUID) -> None:
    if _event_loop_supports_playwright():
        await PlaywrightRunner().run_scan(scan_id)
        return

    # Windows + uvicorn --reload uses SelectorEventLoop, which cannot spawn
    # Playwright's driver. Run the scan in a child process with its own loop.
    logger.warning(
        "Event loop cannot spawn subprocesses; running scan %s in a worker process",
        scan_id,
    )
    await asyncio.to_thread(_run_scan_in_subprocess, scan_id)


def _event_loop_supports_playwright() -> bool:
    if sys.platform != "win32":
        return True
    loop = asyncio.get_running_loop()
    return isinstance(loop, asyncio.ProactorEventLoop)


def _run_scan_in_subprocess(scan_id: uuid.UUID) -> None:
    backend_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "app.automation.scan_worker", str(scan_id)],
        cwd=backend_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip() or (result.stdout or "").strip()
        logger.error("Scan worker for %s exited %s: %s", scan_id, result.returncode, stderr[:2000])
        raise RuntimeError(f"Scan worker failed (exit {result.returncode})")
