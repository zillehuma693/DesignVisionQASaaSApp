"""Shared tree utilities over ScanNode's parent_node_id chain.

The crawl graph is a tree (each node has at most one parent_node_id), so
children/breadcrumb/siblings/paths are all fully determined by that single
field and can be computed at read time — no need to persist a children list
on the document (which would risk write-amplification/races on concurrent
inserts during a live crawl).
"""

from typing import Protocol
from uuid import UUID


class NodeLike(Protocol):
    id: UUID
    parent_node_id: UUID | None
    label: str
    url: str
    created_at: object


def build_children_map(nodes: list[NodeLike]) -> dict[UUID | None, list[NodeLike]]:
    """Group nodes by parent_node_id, each group ordered by created_at."""
    children: dict[UUID | None, list[NodeLike]] = {}
    for node in nodes:
        children.setdefault(node.parent_node_id, []).append(node)
    for siblings in children.values():
        siblings.sort(key=lambda n: n.created_at)
    return children


def build_node_index(nodes: list[NodeLike]) -> dict[UUID, NodeLike]:
    return {node.id: node for node in nodes}


def build_breadcrumb(
    node: NodeLike, node_by_id: dict[UUID, NodeLike], max_depth: int = 25
) -> list[dict]:
    """Ancestor chain from root to `node`, inclusive, root first."""
    trail: list[NodeLike] = [node]
    walk = node
    depth = 0
    while walk.parent_node_id and walk.parent_node_id in node_by_id and depth < max_depth:
        walk = node_by_id[walk.parent_node_id]
        trail.append(walk)
        depth += 1
    trail.reverse()
    return [{"id": n.id, "label": n.label, "url": n.url} for n in trail]


def sibling_index(
    node: NodeLike, children_map: dict[UUID | None, list[NodeLike]]
) -> tuple[int, int]:
    """(0-based index among siblings, total sibling count) for `node`."""
    siblings = children_map.get(node.parent_node_id, [])
    for i, sibling in enumerate(siblings):
        if sibling.id == node.id:
            return i, len(siblings)
    return 0, len(siblings) or 1


def enumerate_root_to_leaf_paths(
    nodes: list[NodeLike], max_depth: int = 25
) -> list[list[NodeLike]]:
    """Every path from a root node (no parent) to a leaf (no children).

    Paths reflect the tree's actual click-through structure, not discovery
    order — the crawl is BFS, so discovery order interleaves sibling
    branches and is not a valid sequential-journey signal.
    """
    children_map = build_children_map(nodes)
    roots = children_map.get(None, [])

    paths: list[list[NodeLike]] = []

    def walk(node: NodeLike, trail: list[NodeLike]) -> None:
        trail = trail + [node]
        kids = children_map.get(node.id, [])
        if not kids or len(trail) >= max_depth:
            paths.append(trail)
            return
        for child in kids:
            walk(child, trail)

    for root in roots:
        walk(root, [])

    return paths
