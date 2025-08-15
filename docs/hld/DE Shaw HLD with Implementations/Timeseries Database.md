# Timeseries Database (Downsampling + Retention)

## Requirements
- Write heavy
- Multi-tenant
- Queries over ranges
- Retention/TTL
- Downsample

## Scale
- 1–10M datapoints/s writes
- Query p95 < 500ms for recent data

## Core Architecture
- Ingest tier
- Sharded time-partitioned storage (LSM/columnar)
- Query engine
- Compactor

## Storage
- LSM-based TSDB or ClickHouse/Pinot
- Tiered (hot/cold)

## Flow
- Append to WAL → memtable → flush → compact; background rollups (1s→1m→1h)

## Trade-offs
- Write amplification vs query speed; index choices (time-partition, label inverted index)

## Diagram
```
[Ingest] -> [WAL] -> [Memtable] -> [Storage] -> [Compactor] -> [Query Engine]
```

## Notes
- Use background rollups for downsampling
- Tiered storage for cost efficiency
