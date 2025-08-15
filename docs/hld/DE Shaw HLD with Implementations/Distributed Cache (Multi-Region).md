# Distributed Cache (Multi-Region)

### 1. Problem Statement & Scope

Design a highly available, low-latency, multi-region distributed cache to accelerate database reads for global applications. The system must support strong or eventual consistency, explicit invalidation, and seamless failover across regions.

### 2. Requirements

- **Functional Requirements:**
    - Store key-value data with TTL.
    - Support read-through and write-through patterns.
    - Explicit cache invalidation (by key, by pattern).
    - Multi-region deployments with data locality.
- **Non-Functional Requirements:**
    - **Low Latency:** <10ms for local reads.
    - **High Availability:** Survive region failures.
    - **Consistency:** Configurable (eventual/strong).
    - **Scalability:** 1M+ QPS, 10TB+ data.

### 3. Capacity Estimation

- **Cache Size:** 10TB total, 5 regions, 2TB/region.
- **QPS:** 1M/sec global, 200k/sec/region.
- **Key Size:** 64B avg, Value Size: 1KB avg.

### 4. High-Level Architecture Diagram

Code snippet

`graph TD
    A[App Server (Region 1)] --> B[Cache Cluster (Region 1)];
    A2[App Server (Region 2)] --> C[Cache Cluster (Region 2)];
    B <--> D[Global Invalidation Bus (Kafka)];
    C <--> D;
    B --> E[Primary DB (Region 1)];
    C --> F[DB Replica (Region 2)];
    D --> B;
    D --> C;
`

### 5. Data Schema & API Design

- **API:**
    - `GET /cache/{key}`
    - `SET /cache/{key}`
    - `DEL /cache/{key}`
    - `INVALIDATE /cache/{pattern}`
- **Data Model:**
    - **Cache Entry:** `{key, value, version, timestamp, ttl}`
    - **Invalidation Event:** `{key/pattern, version, region, timestamp}`

### 6. Detailed Component Breakdown

- **Regional Cache Cluster:** Redis/Memcached cluster per region. Handles local traffic for low latency.
- **Global Invalidation Bus:** Kafka or similar pub/sub for propagating invalidation events across regions.
- **Primary DB + Replicas:** Source of truth. Cache misses/read-throughs go here.
- **Consistency Controller:** Ensures strong/eventual consistency as configured.

### 7. End-to-End Flow (Cache Read/Write/Invalidate)

Code snippet

`sequenceDiagram
    participant App
    participant Cache
    participant DB
    participant InvalidationBus

    App->>Cache: GET key
    alt Hit
        Cache-->>App: Return value
    else Miss
        Cache->>DB: Fetch value
        DB-->>Cache: Return value
        Cache-->>App: Return value
        Cache->>Cache: SET key
    end
    App->>Cache: SET/DEL key
    Cache->>InvalidationBus: Publish invalidation
    InvalidationBus->>Cache: Invalidate key in all regions
`

### 8. Bottlenecks, Fault Tolerance, and Trade-offs

- **Bottleneck: Invalidation Propagation:**
    - Use async pub/sub for scale. Accept brief staleness for performance.
- **Consistency:**
    - Eventual consistency is fast, but may serve stale data. Strong consistency is slower, requires cross-region coordination.
- **Availability:**
    - Each region is independent. If one fails, others continue serving.
- **Trade-offs:**
    - Eventual consistency is simpler and faster. Strong consistency is needed for critical data but adds latency.

---

This design is used by global-scale apps (e.g., Netflix, AWS ElastiCache Global Datastore) for low-latency, highly available caching.
