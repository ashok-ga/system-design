# Limit Order Book & Matching Engine

### 1. Problem Statement & Scope

Design a high-performance, deterministic matching engine for a single financial instrument (e.g., AAPL stock). The engine must process new/cancel orders, match trades using strict price-time priority, and ensure durability and fault tolerance. The system should support high throughput (100k+ orders/sec), low latency (<1ms per match), and be the source of truth for all trades.

### 2. Requirements

- **Functional Requirements:**
    - Accept new limit and market orders (buy/sell).
    - Accept order cancellation and modification requests.
    - Match orders using price-time priority (FIFO within price level).
    - Support order types: Limit, Market, IOC (Immediate or Cancel), FOK (Fill or Kill).
    - Generate trade execution reports and order status updates.
- **Non-Functional Requirements:**
    - **Performance:** <1ms matching latency, 100k+ orders/sec.
    - **Determinism:** Same input sequence always produces same output.
    - **Durability:** No loss of orders/trades on crash (WAL, snapshots).
    - **Availability:** 99.99% uptime, fast failover.
    - **Auditability:** Full replay and audit trail.

### 3. Capacity Estimation

- **Order Rate:** 100k orders/sec peak.
- **Order Book Depth:** 10k price levels, 1M open orders.
- **Trade Rate:** 10k trades/sec.
- **Storage:** Each order ~200 bytes, 1M open orders = 200MB in-memory. WAL: 100k orders/sec * 200B = 20MB/sec, ~1.7TB/day.

### 4. High-Level Architecture Diagram

Code snippet

`graph TD
    A[Client Gateway] --> B[Sequencer];
    B --> C[Matching Engine (Single-threaded)];
    C --> D[WAL Persister];
    C --> E[Snapshotter];
    C --> F[Event Bus];
    F --> G[Downstream Consumers (Analytics, Risk, UI)];
    D --> H[Durable Storage];
    E --> H;
    B --> I[Order Book State];
    C --> I;
    I --> C;
`

### 5. Data Schema & API Design

- **API:**
    - `NewOrderSingle`: `{order_id, side, price, qty, type, tif, user_id}`
    - `OrderCancelRequest`: `{order_id, user_id}`
    - `OrderReplaceRequest`: `{order_id, new_qty, new_price}`
    - `ExecutionReport`: `{order_id, status, fill_qty, fill_price, ...}`
- **Order Book:**
    - Two price-ordered trees (bids, asks), each price → FIFO queue of orders.
    - In-memory, with periodic snapshots and WAL for durability.
- **WAL (Write-Ahead Log):**
    - Append-only log of all order events, persisted before ack.

### 6. Detailed Component Breakdown

- **Client Gateway:** Authenticates clients, validates messages, and forwards to sequencer.
- **Sequencer:** Assigns a global sequence number to all incoming messages, ensuring total ordering and preventing race conditions.
- **Matching Engine:** Single-threaded for determinism. Maintains in-memory order book, processes events in order, matches trades, and generates execution reports.
- **WAL Persister:** Writes every event to disk before ack. Enables crash recovery and replay.
- **Snapshotter:** Periodically saves full in-memory state for fast recovery.
- **Event Bus:** Publishes all events (order, trade, cancel) to downstream consumers (risk, analytics, UI).
- **Durable Storage:** Stores WAL and snapshots for audit and replay.

### 7. End-to-End Flow (Order Submission & Matching)

Code snippet

`sequenceDiagram
    participant Trader
    participant Gateway
    participant Sequencer
    participant MatchingEngine
    participant WAL
    participant Snapshotter
    participant EventBus

    Trader->>Gateway: NewOrderSingle
    Gateway->>Sequencer: Validate & Forward
    Sequencer->>MatchingEngine: Assign sequence, forward event
    MatchingEngine->>WAL: Write event to WAL
    WAL-->>MatchingEngine: Ack
    MatchingEngine->>MatchingEngine: Update order book, match trades
    MatchingEngine->>Snapshotter: Periodic snapshot
    MatchingEngine->>EventBus: Publish ExecutionReport
    EventBus-->>Trader: ExecutionReport
`

### 8. Bottlenecks, Fault Tolerance, and Trade-offs

- **Bottleneck: Single-threaded Engine:**
    - Ensures determinism but limits vertical scaling. Mitigation: Partition by instrument (one engine per symbol).
- **Durability:**
    - WAL + periodic snapshots. On crash, replay WAL from last snapshot.
- **Availability:**
    - Hot standby replica can replay WAL in real-time for fast failover.
- **Trade-offs:**
    - Single-threaded = simple, deterministic, but not horizontally scalable for one instrument.
    - WAL = strong durability, but adds write latency.
    - Partitioning by instrument enables horizontal scale.

---

This design is used in real-world exchanges (e.g., NASDAQ, NYSE) for its determinism, auditability, and performance.
