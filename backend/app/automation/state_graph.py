import hashlib
import time
import uuid
from dataclasses import dataclass, field

from app.core.config import settings
from app.models.scan import ScanNode

_FINGERPRINT_JS = """
() => {
    const activeTab = document.querySelector('[role="tab"][aria-selected="true"]');
    const openDialog = document.querySelector('[role="dialog"], dialog[open]');
    return {
        activeTab: activeTab ? activeTab.textContent.trim().slice(0, 60) : '',
        hasOpenDialog: !!openDialog,
    };
}
"""


@dataclass
class GraphNode:
    id: uuid.UUID
    url: str
    label: str
    dom_signature: str
    parent_node_id: uuid.UUID | None = None
    reach_url: str = ""
    reach_selector: str | None = None
    tried_selectors: set[str] = field(default_factory=set)


class StateGraph:
    def __init__(self, scan_id: uuid.UUID) -> None:
        self.scan_id = scan_id
        self.nodes: dict[str, GraphNode] = {}
        self.queue: list[str] = []
        self.edges_count = 0
        self._start_time = time.monotonic()

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    def is_over_capacity(self) -> bool:
        if self.node_count >= settings.crawl_max_nodes:
            return True
        if time.monotonic() - self._start_time >= settings.crawl_max_duration_seconds:
            return True
        return False

    @staticmethod
    async def fingerprint(page) -> tuple[str, str]:
        """Returns (dom_signature, url) for the current page state.

        Keyed on the URL (ignoring hash/trailing slash) — that's the reliable
        signal. active-tab / open-dialog only differentiate distinct in-page
        states that share a URL (tabs, modals); both are binary/attribute-based
        so they don't race against animation or hydration timing the way text
        content would. Deliberately excludes heading text and raw element
        counts — both drift on sites with animations, chat widgets, or
        lazy-loaded content even with no real navigation, which previously
        caused false "new page" detections (the same URL kept fingerprinting
        differently run to run).
        """
        url = page.url
        normalized_url = url.split("#")[0].rstrip("/")
        try:
            data = await page.evaluate(_FINGERPRINT_JS)
        except Exception:
            data = {"activeTab": "", "hasOpenDialog": False}
        raw = (
            normalized_url + "|"
            + data.get("activeTab", "") + "|"
            + str(data.get("hasOpenDialog", False))
        )
        signature = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
        return signature, url

    def get_node(self, signature: str) -> GraphNode | None:
        return self.nodes.get(signature)

    def all_nodes(self) -> list[GraphNode]:
        return list(self.nodes.values())

    async def get_or_create_node(
        self,
        signature: str,
        url: str,
        label: str,
        parent_signature: str | None,
        reach_url: str,
        reach_selector: str | None,
        discovered_via: dict | None,
    ) -> tuple[GraphNode, bool]:
        if signature in self.nodes:
            return self.nodes[signature], False

        parent = self.nodes.get(parent_signature) if parent_signature else None
        node = GraphNode(
            id=uuid.uuid4(),
            url=url,
            label=label,
            dom_signature=signature,
            parent_node_id=parent.id if parent else None,
            reach_url=reach_url,
            reach_selector=reach_selector,
        )
        self.nodes[signature] = node
        await ScanNode(
            id=node.id,
            scan_id=self.scan_id,
            url=url,
            label=label,
            parent_node_id=node.parent_node_id,
            discovered_via=discovered_via,
            dom_signature=signature,
        ).insert()
        self.queue.append(signature)
        return node, True

    def mark_tried(self, node_signature: str, selector: str) -> None:
        node = self.nodes.get(node_signature)
        if node:
            node.tried_selectors.add(selector)

    def has_tried(self, node_signature: str, selector: str) -> bool:
        node = self.nodes.get(node_signature)
        return bool(node and selector in node.tried_selectors)

    def record_edge(self) -> None:
        self.edges_count += 1

    def pop_queue(self) -> str | None:
        if not self.queue:
            return None
        return self.queue.pop(0)
