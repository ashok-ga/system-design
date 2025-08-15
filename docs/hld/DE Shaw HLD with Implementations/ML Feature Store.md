# ML Feature Store (Online + Offline)

## Requirements
- Point-in-time correctness
- Online/serving parity
- Backfills

## Scale
- 10k QPS feature reads
- 100k QPS writes

## Core Architecture
- Offline store (Parquet/Iceberg) + online KV (Redis/Cassandra)
- Registry
- Materialization jobs

## Storage
- As above; TTLs for online

## Flow
- Write events → batch compute → push to online; join at inference

## Trade-offs
- Latency vs consistency; late-arriving data

## Diagram
```
[Event] -> [Batch Compute] -> [Offline Store] -> [Materialization] -> [Online Store] -> [Serving]
```

## Notes
- TTLs for online features
- Registry for schema/versioning
