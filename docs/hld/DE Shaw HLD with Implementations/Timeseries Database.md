---
# Timeseries Database (Downsampling + Retention)

## 1. Problem Statement & Requirements
Design a scalable, multi-tenant timeseries database (TSDB) for high write throughput, efficient range queries, retention, and downsampling.

**Functional Requirements:**
- Ingest high-frequency timeseries data (metrics, logs, IoT, etc.)
- Support multi-tenant isolation
- Range queries over time and labels
- Retention/TTL and automatic data expiry
- Downsampling/rollups for older data
- Support for tags/labels and flexible schema

**Non-Functional Requirements:**
- 1–10M datapoints/sec writes
- Query p95 < 500ms for recent data
- High availability, horizontal scalability

**Assumptions:**
- Data is append-only, immutable after ingest
- Hot/cold storage tiers for cost efficiency

---
## 2. High-Level Architecture

**Components:**
- **Ingest Tier:** Accepts writes, batches, and deduplicates
- **Write-Ahead Log (WAL):** Ensures durability before flush
- **Memtable:** In-memory buffer for fast ingest
- **Storage Engine:** Sharded, time-partitioned LSM/columnar store
- **Compactor:** Merges, downsample, and evicts old data
- **Query Engine:** Executes range, aggregation, and label queries
- **Retention Manager:** Enforces TTL and tiering

**Architecture Diagram:**
```
 [Ingest] -> [WAL] -> [Memtable] -> [Storage] -> [Compactor] -> [Query Engine]
```

---
## 3. Data Model & Partitioning

- **Timeseries:** { metric, labels, points[] }
- **Point:** { ts, value }
- **Labels:** { key: value, ... } for multi-dimensional queries
- **Sharding:** By tenant, metric, and time window

---
## 4. Key Workflows

### a) Write Path
1. Ingest tier receives batch of points
2. Appends to WAL for durability
3. Buffers in memtable (sorted by time)
4. On flush, writes to LSM/columnar storage

### b) Compaction & Downsampling
1. Compactor merges small files, removes duplicates
2. Downsamples old data (e.g., 1s→1m→1h)
3. Moves cold data to cheaper storage

### c) Query Path
1. Query engine parses range/label query
2. Reads from memtable, then storage (hot/cold)
3. Applies aggregation, downsampling as needed

### d) Retention & TTL
1. Retention manager scans for expired data
2. Deletes or moves to cold storage

---
## 5. Scaling & Reliability

- **Horizontal Scaling:** Shard by tenant/metric/time
- **Replication:** For HA and durability
- **Tiered Storage:** SSD for hot, object store for cold
- **Monitoring:** Ingest lag, compaction, query latency

---
## 6. Trade-offs & Alternatives

- **Write Amplification:** LSM/compaction increases writes, but enables fast ingest
- **Query Speed:** Columnar/LSM enables fast range queries, but may slow random access
- **Indexing:** Time-partitioned and label inverted indices for efficient queries

---
## 7. Best Practices & Extensions

- Use background rollups for downsampling
- Tiered storage for cost efficiency
- Support for schema evolution and label cardinality control
- Integrate with Prometheus/OTel for metrics ingest

---
## 8. Example Pseudocode (Downsampling)
```python
def downsample(points, interval):
    buckets = defaultdict(list)
    for p in points:
        bucket = p.ts // interval
        buckets[bucket].append(p.value)
    return [(bucket*interval, sum(vals)/len(vals)) for bucket, vals in buckets.items()]
```

---
## 9. References
- [LSM Trees](https://en.wikipedia.org/wiki/Log-structured_merge-tree)
- [Prometheus TSDB](https://prometheus.io/docs/prometheus/latest/storage/)
- [ClickHouse for Timeseries](https://clickhouse.com/docs/en/)
