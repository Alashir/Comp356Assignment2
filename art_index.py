"""Simplified Adaptive Radix Tree (ART) for integer record keys.

Why ART for indexing:
- Uses trie-like navigation over key bytes, so lookups are O(key_length)
  instead of O(log n) node traversals in B+ trees.
- Adapts node representation (small to dense) to minimize memory overhead
  while keeping very fast child access.

This implementation keeps the interface intentionally small:
- insert(record_id)
- contains(record_id)
- range_query(low, high)

Records are simplified to integers, and the integer itself is used as key/value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

KEY_BYTES = 8  # fixed width so integer ordering aligns with lexicographic bytes


def _int_to_key(value: int) -> bytes:
    if value < 0:
        raise ValueError("Only non-negative integers are supported")
    return value.to_bytes(KEY_BYTES, "big", signed=False)


def _key_to_int(key: bytes) -> int:
    return int.from_bytes(key, "big", signed=False)


class ArtNode:
    """Adaptive node that upgrades representation as fanout grows.

    Kinds:
    - node4/node16: dictionary (compact for small fanout)
    - node48:      sparse index table + compact child array
    - node256:     direct 256-slot array
    """

    __slots__ = ("kind", "children", "index", "leaf")

    def __init__(self) -> None:
        self.kind: str = "node4"
        self.children: Dict[int, ArtNode] | List[Optional[ArtNode]] = {}
        self.index: Optional[List[int]] = None
        self.leaf: bool = False

    def _fanout(self) -> int:
        if self.kind in {"node4", "node16"}:
            return len(self.children)  # type: ignore[arg-type]
        if self.kind == "node48":
            return len(self.children)  # type: ignore[arg-type]
        return sum(1 for child in self.children if child is not None)  # type: ignore[union-attr]

    def _upgrade(self) -> None:
        """Upgrade to the next node type when thresholds are exceeded."""
        if self.kind == "node4":
            self.kind = "node16"
            return

        if self.kind == "node16":
            # node48: index[byte] -> slot in compact child array, -1 means absent
            old = self.children  # type: ignore[assignment]
            self.kind = "node48"
            self.index = [-1] * 256
            compact: List[ArtNode] = []
            for key_byte, child in old.items():
                self.index[key_byte] = len(compact)
                compact.append(child)
            self.children = compact
            return

        if self.kind == "node48":
            # node256: direct access array for maximal lookup speed
            compact = self.children  # type: ignore[assignment]
            idx = self.index
            direct: List[Optional[ArtNode]] = [None] * 256
            for key_byte in range(256):
                slot = idx[key_byte]  # type: ignore[index]
                if slot != -1:
                    direct[key_byte] = compact[slot]  # type: ignore[index]
            self.kind = "node256"
            self.children = direct
            self.index = None

    def get_child(self, key_byte: int) -> Optional["ArtNode"]:
        if self.kind in {"node4", "node16"}:
            return self.children.get(key_byte)  # type: ignore[union-attr]
        if self.kind == "node48":
            slot = self.index[key_byte]  # type: ignore[index]
            if slot == -1:
                return None
            return self.children[slot]  # type: ignore[index]
        return self.children[key_byte]  # type: ignore[index]

    def set_child(self, key_byte: int, node: "ArtNode") -> None:
        if self.kind in {"node4", "node16"}:
            children = self.children  # type: ignore[assignment]
            children[key_byte] = node
            if self.kind == "node4" and len(children) > 4:
                self._upgrade()
            elif self.kind == "node16" and len(children) > 16:
                self._upgrade()
            return

        if self.kind == "node48":
            slot = self.index[key_byte]  # type: ignore[index]
            if slot == -1:
                self.index[key_byte] = len(self.children)  # type: ignore[index]
                self.children.append(node)  # type: ignore[union-attr]
                if len(self.children) > 48:  # type: ignore[arg-type]
                    self._upgrade()
            else:
                self.children[slot] = node  # type: ignore[index]
            return

        # node256
        self.children[key_byte] = node  # type: ignore[index]


@dataclass
class AdaptiveRadixTree:
    root: ArtNode = field(default_factory=ArtNode)

    def insert(self, record: int) -> None:
        key = _int_to_key(record)
        current = self.root
        for key_byte in key:
            child = current.get_child(key_byte)
            if child is None:
                child = ArtNode()
                current.set_child(key_byte, child)
            current = child
        current.leaf = True

    def bulk_insert(self, records: Iterable[int]) -> None:
        for value in records:
            self.insert(value)

    def contains(self, record: int) -> bool:
        key = _int_to_key(record)
        current = self.root
        for key_byte in key:
            current = current.get_child(key_byte)
            if current is None:
                return False
        return current.leaf

    def range_query(self, low: int, high: int) -> List[int]:
        if low > high:
            return []

        result: List[int] = []
        low_key = _int_to_key(low)
        high_key = _int_to_key(high)

        def walk(node: ArtNode, depth: int, prefix: bytearray) -> None:
            if depth == KEY_BYTES:
                if node.leaf:
                    value = _key_to_int(bytes(prefix))
                    if low <= value <= high:
                        result.append(value)
                return

            for b, child in _iter_children(node):
                # pruning via lexicographic bounds
                if b < low_key[depth] and prefix == low_key[:depth]:
                    continue
                if b > high_key[depth] and prefix == high_key[:depth]:
                    continue

                prefix.append(b)
                walk(child, depth + 1, prefix)
                prefix.pop()

        walk(self.root, 0, bytearray())
        return result


def _iter_children(node: ArtNode) -> List[Tuple[int, ArtNode]]:
    if node.kind in {"node4", "node16"}:
        children = node.children  # type: ignore[assignment]
        return sorted(children.items(), key=lambda kv: kv[0])

    if node.kind == "node48":
        out: List[Tuple[int, ArtNode]] = []
        for b in range(256):
            slot = node.index[b]  # type: ignore[index]
            if slot != -1:
                out.append((b, node.children[slot]))  # type: ignore[index]
        return out

    out256: List[Tuple[int, ArtNode]] = []
    for b, child in enumerate(node.children):  # type: ignore[arg-type]
        if child is not None:
            out256.append((b, child))
    return out256


if __name__ == "__main__":
    # Small usage demo
    idx = AdaptiveRadixTree()
    idx.bulk_insert([10, 3, 200, 150, 10_000])

    print("contains(200):", idx.contains(200))
    print("contains(999):", idx.contains(999))
    print("range_query(5, 300):", idx.range_query(5, 300))
