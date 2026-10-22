"""In-memory property graph with the C2 labels, types and properties (PHASE-3.md 7.1.2).

Every detector has a reference candidate step that runs on this graph. Unit tests use it, so they
need no database, and the parity test (M3.2) compares it with the Cypher candidate step on the same
records loaded into Neo4j. Nodes and relationships carry exactly the C2 properties, and every
listing is in id order, so results never depend on insertion order.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Node:
    id: str
    labels: frozenset[str]
    props: Mapping[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.props.get(key, default)

    @property
    def synthetic(self) -> bool:
        return bool(self.props.get("synthetic", False))


@dataclass(frozen=True, slots=True)
class Rel:
    id: str
    type: str
    source: str
    target: str
    props: Mapping[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.props.get(key, default)

    @property
    def synthetic(self) -> bool:
        return bool(self.props.get("synthetic", False))


class MemGraph:
    """Nodes by id, relationships by id, adjacency by (node, type)."""

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._rels: dict[str, Rel] = {}
        self._out: dict[tuple[str, str], list[Rel]] = defaultdict(list)
        self._in: dict[tuple[str, str], list[Rel]] = defaultdict(list)
        self._by_label: dict[str, list[str]] = defaultdict(list)
        self._by_type: dict[str, list[str]] = defaultdict(list)
        self._dirty = False

    def add_node(self, node_id: str, labels: Iterable[str], props: Mapping[str, Any]) -> None:
        if node_id in self._nodes:
            raise ValueError(f"duplicate node id {node_id}")
        node = Node(node_id, frozenset(labels), dict(props, id=node_id))
        self._nodes[node_id] = node
        for label in node.labels:
            self._by_label[label].append(node_id)
        self._dirty = True

    def add_rel(
        self, rel_id: str, rel_type: str, source: str, target: str, props: Mapping[str, Any]
    ) -> None:
        if rel_id in self._rels:
            raise ValueError(f"duplicate relationship id {rel_id}")
        if source not in self._nodes or target not in self._nodes:
            raise KeyError(f"relationship {rel_id} has an end that is not a node")
        rel = Rel(rel_id, rel_type, source, target, dict(props, id=rel_id))
        self._rels[rel_id] = rel
        self._out[(source, rel_type)].append(rel)
        self._in[(target, rel_type)].append(rel)
        self._by_type[rel_type].append(rel_id)
        self._dirty = True

    def _sort(self) -> None:
        if not self._dirty:
            return
        for ids in self._by_label.values():
            ids.sort()
        for ids in self._by_type.values():
            ids.sort()
        for rels in self._out.values():
            rels.sort(key=lambda r: r.id)
        for rels in self._in.values():
            rels.sort(key=lambda r: r.id)
        self._dirty = False

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def node(self, node_id: str) -> Node:
        return self._nodes[node_id]

    def rel(self, rel_id: str) -> Rel:
        return self._rels[rel_id]

    def nodes(self, label: str | None = None) -> list[Node]:
        self._sort()
        if label is None:
            return [self._nodes[i] for i in sorted(self._nodes)]
        return [self._nodes[i] for i in self._by_label.get(label, [])]

    def rels(self, rel_type: str) -> list[Rel]:
        self._sort()
        return [self._rels[i] for i in self._by_type.get(rel_type, [])]

    def out_rels(self, node_id: str, *types: str) -> list[Rel]:
        self._sort()
        found = [r for t in types for r in self._out.get((node_id, t), [])]
        return sorted(found, key=lambda r: r.id) if len(types) > 1 else found

    def in_rels(self, node_id: str, *types: str) -> list[Rel]:
        self._sort()
        found = [r for t in types for r in self._in.get((node_id, t), [])]
        return sorted(found, key=lambda r: r.id) if len(types) > 1 else found

    def holders(self, account_id: str) -> list[Node]:
        """The sources of HOLDS_ACCOUNT into an account, in id order."""
        return sorted(
            (self._nodes[r.source] for r in self.in_rels(account_id, "HOLDS_ACCOUNT")),
            key=lambda n: n.id,
        )

    def accounts(self, holder_id: str) -> list[Node]:
        """The accounts a legal entity holds, in id order."""
        return sorted(
            (self._nodes[r.target] for r in self.out_rels(holder_id, "HOLDS_ACCOUNT")),
            key=lambda n: n.id,
        )

    def counts(self) -> dict[str, int]:
        return {"nodes": len(self._nodes), "relationships": len(self._rels)}
