
# Limit Order Book & Matching Engine — Deep Dive

## 1. Problem Statement & Scope
Design a high-performance, deterministic matching engine for a single financial instrument (e.g., AAPL stock). The engine must process new/cancel/modify orders, match trades using strict price-time priority, and ensure durability, auditability, and fault tolerance. The system should support high throughput (100k+ orders/sec), low latency (<1ms per match), and be the source of truth for all trades.

## 2. Functional & Non-Functional Requirements

### Functional Requirements
- Accept new limit and market orders (buy/sell)
- Accept order cancellation and modification requests
- Match orders using price-time priority (FIFO within price level)
- Support order types: Limit, Market, IOC (Immediate or Cancel), FOK (Fill or Kill)
- Generate trade execution reports and order status updates
- Support for partial fills, order expiry, and self-trade prevention
- Real-time order book snapshot API

### Non-Functional Requirements
- **Performance:** <1ms matching latency, 100k+ orders/sec
- **Determinism:** Same input sequence always produces same output
- **Durability:** No loss of orders/trades on crash (WAL, snapshots)
- **Availability:** 99.99% uptime, fast failover
- **Auditability:** Full replay and audit trail
- **Security:** Authenticated clients, encrypted channels

## 3. Capacity & Scale Estimation

- **Order Rate:** 100k orders/sec peak
- **Order Book Depth:** 10k price levels, 1M open orders
- **Trade Rate:** 10k trades/sec
- **Storage:** Each order ~200 bytes, 1M open orders = 200MB in-memory. WAL: 100k orders/sec * 200B = 20MB/sec, ~1.7TB/day
- **Snapshot Frequency:** Every 1s or 10k events

## 4. High-Level Architecture

```mermaid
graph TD
    Gateway[Client Gateway] --> Sequencer
    Sequencer --> MatchingEngine[Matching Engine (Single-threaded)]
    MatchingEngine --> WAL[WAL Persister]
    MatchingEngine --> Snapshotter
    MatchingEngine --> EventBus
    EventBus --> Downstream[Downstream Consumers (Analytics, Risk, UI)]
    WAL --> DurableStorage
    Snapshotter --> DurableStorage
    Sequencer --> OrderBookState
    MatchingEngine --> OrderBookState
    OrderBookState --> MatchingEngine
```

## 5. Data Model & API Design

### API Endpoints
- `POST /order`: New order (limit/market/IOC/FOK)
- `POST /cancel`: Cancel order
- `POST /replace`: Modify order
- `GET /orderbook`: Get current order book snapshot
- `GET /trades`: Get recent trades

### Data Models
- **Order:** {order_id, side, price, qty, type, tif, user_id, timestamp}
- **ExecutionReport:** {order_id, status, fill_qty, fill_price, ...}
- **Order Book:** Two price-ordered trees (bids, asks), each price → FIFO queue of orders
- **WAL (Write-Ahead Log):** Append-only log of all order events, persisted before ack

## 6. Detailed Component Breakdown

- **Client Gateway:** Authenticates clients, validates messages, and forwards to sequencer
- **Sequencer:** Assigns a global sequence number to all incoming messages, ensuring total ordering and preventing race conditions
- **Matching Engine:** Single-threaded for determinism. Maintains in-memory order book, processes events in order, matches trades, and generates execution reports
- **WAL Persister:** Writes every event to disk before ack. Enables crash recovery and replay
- **Snapshotter:** Periodically saves full in-memory state for fast recovery
- **Event Bus:** Publishes all events (order, trade, cancel) to downstream consumers (risk, analytics, UI)
- **Durable Storage:** Stores WAL and snapshots for audit and replay

## 7. End-to-End Workflows

### a) Order Submission & Matching
1. Trader submits new order via Gateway
2. Gateway authenticates, validates, and forwards to Sequencer
3. Sequencer assigns sequence number, forwards to Matching Engine
4. Matching Engine writes event to WAL, waits for ack
5. Matching Engine updates order book, matches trades, generates execution reports
6. Execution reports published to Event Bus and returned to client
7. Periodic snapshots taken for fast recovery

### b) Crash Recovery
1. On crash, engine loads last snapshot
2. Replays WAL from snapshot point to current
3. Resumes matching with no loss of state

### c) Failover
1. Hot standby replica replays WAL in real-time
2. On failover, standby takes over with minimal downtime

## 8. Scaling, Fault Tolerance, and Trade-offs

- **Scaling:**
    - Partition by instrument (one engine per symbol) for horizontal scale
    - Use sharded WAL and snapshot storage for throughput
- **Fault Tolerance:**
    - WAL + periodic snapshots for durability
    - Hot standby replica for fast failover
- **Trade-offs:**
    - Single-threaded = simple, deterministic, but not horizontally scalable for one instrument
    - WAL = strong durability, but adds write latency
    - Partitioning by instrument enables horizontal scale

## 9. Security & Operational Considerations

- **Security:**
    - Authenticate all clients, encrypt all channels
    - All actions logged for audit
- **Monitoring:**
    - Real-time dashboards for order flow, latency, and errors
- **Disaster Recovery:**
    - Regular backups of WAL and snapshots

## 10. Best Practices & Industry Insights

- Use single-threaded engine for determinism, partition by instrument for scale
- Always persist to WAL before ack
- Use periodic snapshots for fast recovery
- Integrate with risk and analytics systems via event bus
- Design for auditability and replay

---

This design is inspired by real-world exchanges (e.g., NASDAQ, NYSE, CME) and can be extended for multi-instrument, multi-market, and cross-venue matching.
