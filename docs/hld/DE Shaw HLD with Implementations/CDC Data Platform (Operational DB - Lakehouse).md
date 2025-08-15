# CDC Data Platform (Operational DB -> Lakehouse)

### 1. Problem Statement & Scope

Design a real-time Change Data Capture (CDC) platform to stream all changes from operational databases (e.g., Postgres, MySQL) into a central lakehouse (e.g., Iceberg, Delta Lake). The system must support high throughput, schema evolution, and strong delivery guarantees.

### 2. Requirements

- **Functional Requirements:**
    - Capture all inserts, updates, deletes from source DBs.
    - Deliver changes to the lakehouse with at-least-once or exactly-once semantics.
    - Handle schema evolution and DDL changes.
    - Support multiple source DBs and tables.
- **Non-Functional Requirements:**
    - **Scalability:** 100MB+/sec ingest, 1000+ tables.
    - **Reliability:** No data loss, strong delivery guarantees.
    - **Extensibility:** Add new sources/sinks easily.

### 3. Capacity Estimation

- **Source DBs:** 10, each 1TB, 100GB/day change rate.
- **Change Rate:** 10MB/sec per DB, 100MB/sec total.
- **Lakehouse Storage:** 10TB+.

### 4. High-Level Architecture Diagram

Code snippet

`graph TD
    A[Source DB (Postgres/MySQL)] --> B[Debezium Connector];
    B --> C[Kafka (CDC Topics)];
    C --> D[Stream Processor (Flink/Spark)] ;
    D --> E[Lakehouse (Iceberg/Delta)];
    D --> F[Monitoring/Alerting];
    C --> G[Schema Registry];
`

### 5. Data Schema & API Design

- **CDC Event (Debezium):** `{table, op (insert/update/delete), before, after, ts, schema_version}`
- **Kafka Topic:** Partitioned by table, Avro/JSON encoding.
- **Lakehouse Table:** SCD2 (slowly changing dimension) or append-only, partitioned by date/table.

### 6. Detailed Component Breakdown

- **Debezium Connector:** Reads DB logs, emits CDC events to Kafka. Handles schema changes.
- **Kafka:** Durable, scalable event bus. Buffers CDC events, supports replay.
- **Stream Processor (Flink/Spark):** Consumes CDC events, applies transformations, merges, and writes to lakehouse. Handles exactly-once via checkpointing.
- **Lakehouse (Iceberg/Delta):** Stores raw and processed data, supports ACID, schema evolution, and time travel.
- **Schema Registry:** Tracks schema versions for compatibility.
- **Monitoring/Alerting:** Tracks lag, failures, and data quality.

### 7. End-to-End Flow (CDC Ingest)

Code snippet

`sequenceDiagram
    participant SourceDB
    participant Debezium
    participant Kafka
    participant Flink
    participant Lakehouse

    SourceDB->>Debezium: Write to binlog/WAL
    Debezium->>Kafka: Emit CDC event
    Kafka->>Flink: Stream event
    Flink->>Lakehouse: Write/merge data
    Flink->>Kafka: Commit offset (checkpoint)
    Lakehouse-->>Flink: Ack
`

### 8. Bottlenecks, Fault Tolerance, and Trade-offs

- **Bottleneck: Stream Processor:**
    - Scale out Flink/Spark for high ingest. Use partitioned topics.
- **Delivery Guarantees:**
    - At-least-once is simpler, exactly-once requires checkpointing and idempotent writes.
- **Schema Evolution:**
    - Use schema registry, support backward/forward compatibility.
- **Trade-offs:**
    - Micro-batch merges are efficient but add latency. Row-by-row upserts are slower but more real-time.

---

This architecture is used by modern data platforms (e.g., Netflix, Uber) for real-time analytics and data lake ingestion.
