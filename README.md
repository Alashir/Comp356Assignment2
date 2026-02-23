# Simplified ART Index for Integer Records

This repository demonstrates an **Adaptive Radix Tree (ART)**, a high-performance index structure often used in modern in-memory database engines.

## Why ART

Compared with a classic B+ tree, ART is commonly competitive or faster for in-memory point lookups because it:

- Navigates fixed-length key bytes directly (no binary search inside each node).
- Adapts node representations (4/16/48/256 children), reducing memory overhead for sparse nodes.
- Uses dense direct indexing in high-fanout areas (`node256`) for very fast child access.

In practice, ART is considered at least B+ tree class performance for many in-memory indexing workloads, with particularly strong point lookup throughput.

## Scope for this assignment

- Records are simplified to integers.
- Integer keys are encoded as fixed 8-byte big-endian values.
- Implemented API:
  - `insert(record: int)`
  - `bulk_insert(records: Iterable[int])`
  - `contains(record: int) -> bool`
  - `range_query(low: int, high: int) -> list[int]`

## Run demo

```bash
python art_index.py
```

## Run tests

```bash
python -m unittest -v
```
