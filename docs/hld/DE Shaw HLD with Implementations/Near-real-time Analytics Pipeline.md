# Near-real-time Analytics Pipeline (Clickstream)

## Requirements
- Sub-second ingest
- Minute-level aggregates
- Dashboards

## Scale
- 100–500k events/s

## Core Architecture
- Edge collectors
- Kafka
- Stream processor (Flink/Spark)
- OLAP (Pinot/Druid/ClickHouse)
- BI

## Storage
- Lake for raw
- OLAP for queries

## Flow
- Ingest → parse → sessionize → materialize rollups

## Bottlenecks & Mitigations
- Reprocessing & exactly-once; use transactional sinks

## Diagram
```
[Collector] -> [Kafka] -> [Stream Processor] -> [OLAP] -> [BI]
```

## Notes
- Use transactional sinks for exactly-once
- Sessionization for user analytics
