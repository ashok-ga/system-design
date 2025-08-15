# Distributed ID Generator (Snowflake-like)

### 1. Problem Statement & Scope

Design a distributed ID generator that produces unique, sortable 64-bit IDs across multiple data centers and workers, similar to Twitter Snowflake. The system must handle clock skew, sequence rollover, and be highly available.

### 2. Requirements

- **Functional Requirements:**
    - Generate unique 64-bit IDs: `timestamp | datacenter | worker | sequence`.
    - IDs must be sortable by time.
    - Handle clock skew, sequence rollover, and thread safety.
- **Non-Functional Requirements:**
    - **Low Latency:** <1ms per ID generation.
    - **High Availability:** No duplicate IDs, even on failover.
    - **Scalability:** 10k+ QPS per node, 1000+ nodes.

### 3. Capacity Estimation

- **Nodes:** 1000 (workers across DCs).
- **QPS:** 10k/node = 10M QPS global.
- **ID Space:** 64 bits, 41b timestamp, 5b DC, 5b worker, 12b sequence.

### 4. High-Level Architecture Diagram

Code snippet

`graph TD
    A[Client] --> B[ID Generator Node];
    B --> C[Clock/Time Source];
    B --> D[Persistence (optional)];
    B --> E[Monitoring];
    B --> F[Cluster Coordination (optional)];
`

### 5. Data Schema & API Design

- **API:**
    - `GET /v1/next_id`: Returns next unique ID.
- **ID Layout:**
    - 41 bits: timestamp (ms since custom epoch)
    - 5 bits: datacenter ID
    - 5 bits: worker ID
    - 12 bits: sequence (per ms)

### 6. Detailed Component Breakdown

- **ID Generator Node:** Implements the ID generation logic, maintains local state (last timestamp, sequence), and exposes API.
- **Clock/Time Source:** Uses system clock. If clock moves backward, node waits until safe.
- **Persistence (optional):** Stores last timestamp for crash recovery.
- **Cluster Coordination (optional):** Assigns unique worker/datacenter IDs, prevents collisions.
- **Monitoring:** Tracks QPS, errors, clock skew events.

### 7. End-to-End Flow (ID Generation)

Code snippet

`sequenceDiagram
    participant Client
    participant IDGen
    participant Clock
    participant Persist

    Client->>IDGen: Request next_id
    IDGen->>Clock: Get current timestamp
    alt Same ms as last
        IDGen->>IDGen: Increment sequence
        alt Sequence overflow
            IDGen->>Clock: Wait for next ms
        end
    else Clock moved backward
        IDGen->>Clock: Wait until safe
    end
    IDGen->>Persist: (Optional) Store last timestamp
    IDGen-->>Client: Return ID
`

### 8. Bottlenecks, Fault Tolerance, and Trade-offs

- **Bottleneck: Sequence Overflow:**
    - 12 bits = 4096 IDs/ms/node. If exceeded, must wait for next ms.
- **Clock Skew:**
    - If clock moves backward, node must wait. Use NTP and monotonic clocks.
- **Worker/DC ID Collisions:**
    - Use static config or coordination service (e.g., Zookeeper) to assign unique IDs.
- **Persistence:**
    - Optional for crash recovery. If not used, may generate duplicate IDs after crash.
- **Trade-offs:**
    - Simpler design is stateless but risks duplicates on crash. Persistent design is safer but slower.

---

This design is used by Twitter, Instagram, and many distributed systems for unique, sortable ID generation.
