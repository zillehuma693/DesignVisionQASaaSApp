import uuid
from typing import Awaitable, Callable

from playwright.async_api import Page

from app.automation.navigation_discovery import NavigationDiscovery
from app.automation.state_graph import GraphNode, StateGraph
from app.core.config import settings

OnNodeVisited = Callable[[Page, GraphNode], Awaitable[None]]
OnLog = Callable[[str, str, str], Awaitable[None]]


def _origin(url: str) -> str:
    return url.split("#")[0]


class CrawlerEngine:
    def __init__(self, scan_id: uuid.UUID) -> None:
        self.graph = StateGraph(scan_id)
        self.nav = NavigationDiscovery()

    async def run(self, page: Page, on_node_visited: OnNodeVisited, on_log: OnLog) -> StateGraph:
        root_signature, root_url = await self.graph.fingerprint(page)
        await self.graph.get_or_create_node(
            signature=root_signature,
            url=root_url,
            label="Home",
            parent_signature=None,
            reach_url=root_url,
            reach_selector=None,
            discovered_via=None,
        )
        await on_log("info", f"Root page discovered: {root_url}", "crawl")

        while True:
            if self.graph.is_over_capacity():
                await on_log("warn", "Crawl limit reached (max pages or time); stopping exploration.", "crawl")
                break

            node_signature = self.graph.pop_queue()
            if node_signature is None:
                break

            node = self.graph.get_node(node_signature)
            if node is None:
                continue

            if node_signature != root_signature:
                reached = await self.reach_node(page, node)
                if not reached:
                    await on_log("warn", f'Could not reach discovered page "{node.label}"', "crawl")
                    continue

            await on_node_visited(page, node)
            await self._explore_node(page, node, node_signature, on_log)

        return self.graph

    async def reach_node(self, page: Page, node: GraphNode) -> bool:
        """Navigate the page back to a previously-discovered node's state.
        Public so callers (e.g. the multi-viewport responsive pass) can replay
        a node after the crawl itself has finished."""
        try:
            if _origin(page.url) != _origin(node.reach_url):
                await page.goto(node.reach_url, wait_until="domcontentloaded", timeout=15000)
            if node.reach_selector:
                await page.click(node.reach_selector, timeout=5000)
                await page.wait_for_timeout(400)
            return True
        except Exception:
            return False

    async def _explore_node(self, page: Page, node: GraphNode, node_signature: str, on_log: OnLog) -> None:
        elements = await self.nav.find_actionable_elements(page)
        actions_tried = 0

        for element in elements:
            if actions_tried >= settings.crawl_max_actions_per_node:
                break
            if self.graph.has_tried(node_signature, element.selector):
                continue
            self.graph.mark_tried(node_signature, element.selector)

            if element.is_destructive:
                await on_log("info", f'Skipped destructive action: "{element.text}"', "crawl")
                continue

            actions_tried += 1

            try:
                await page.click(element.selector, timeout=5000)
                await page.wait_for_timeout(500)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=3000)
                except Exception:
                    pass
            except Exception:
                continue

            new_signature, new_url = await self.graph.fingerprint(page)
            if new_signature == node_signature:
                continue

            navigated = _origin(new_url) != _origin(node.url)
            new_node, is_new = await self.graph.get_or_create_node(
                signature=new_signature,
                url=new_url,
                label=element.text or element.kind,
                parent_signature=node_signature,
                reach_url=new_url if navigated else node.url,
                reach_selector=None if navigated else element.selector,
                discovered_via={"selector": element.selector, "text": element.text, "kind": element.kind},
            )
            self.graph.record_edge()
            if is_new:
                await on_log("info", f'Discovered page via {element.kind} "{element.text}": {new_url}', "crawl")

            restored = await self._return_to(page, node, navigated)
            if not restored:
                await on_log(
                    "warn",
                    f'Could not return to "{node.label}" after clicking "{element.text}"; moving on',
                    "crawl",
                )
                break

    async def _return_to(self, page: Page, node: GraphNode, navigated: bool) -> bool:
        try:
            if navigated:
                await page.go_back(wait_until="domcontentloaded", timeout=10000)
            else:
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(300)
            current_signature, _ = await self.graph.fingerprint(page)
            return current_signature == node.dom_signature
        except Exception:
            return False
