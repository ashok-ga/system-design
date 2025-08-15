# Metrics Store (Append-only + Compaction)

## Problem Statement
In-process time-series store with write/fetch and periodic compaction.

## Functional Requirements
- `put(metric, ts, value)`, `rangeQuery(metric, from, to)`
- Compaction to downsample older data (1s→1m)

## Core Concepts
- `Segment` (append log), `Index`, `Compactor`
- Memory-mapped segments (optional)
- Read path merges raw+compact

## High-Level Design
- **Segments:**
    - Append-only log per metric
    - Index for fast lookup
- **Compaction:**
    - Downsample old data (e.g., 1s → 1m)
    - Merge segments
- **API:**
    - put, rangeQuery
- **Edge Cases:**
    - Out-of-order writes
    - Query across raw+compact

## Step-by-Step Solution
1. **Define Segment, Index, Compactor classes**
2. **Write path:** append to segment
3. **Compaction:** periodic downsampling
4. **API:** put, rangeQuery

## Edge Cases
- Data loss on crash (in-memory)
- Compaction lag
