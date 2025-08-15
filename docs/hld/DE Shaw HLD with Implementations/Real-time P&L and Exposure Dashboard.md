---
# Real-time P&L & Exposure Dashboard

## 1. Problem Statement & Requirements
Design a real-time dashboard for P&L and exposure, aggregating tick data and positions for books, traders, and desks.

**Functional Requirements:**
- Ingest tick updates and position changes
- Compute live P&L and exposures per book/trader
- Support drill-down and aggregation by hierarchy
- Serve data via API and websocket for dashboards
- Pre-materialize views for fast queries

**Non-Functional Requirements:**
- 100k updates/sec
- Fan-out to 1k+ users
- p99 < 100ms for dashboard queries
- High availability, auditability

**Assumptions:**
- Tick and position data are available in real time
- OLAP store for aggregates

---
## 2. High-Level Architecture

**Components:**
- **Tick Ingest:** Receives real-time price updates
- **Position Service:** Tracks positions per book/trader
- **Stream Processor:** Aggregates P&L and exposures (Flink/Spark)
- **Aggregation Cache:** OLAP DB (Pinot/ClickHouse) for pre-materialized views
- **API Service:** Serves queries and websocket updates
- **Websocket Gateway:** Pushes updates to dashboards

**Architecture Diagram:**
```
 [Tick Ingest] + [Position Service] -> [Stream Processor] -> [Aggregation Cache] -> [API/Websocket]
```

---
## 3. Data Model & Aggregation

- **Tick:** { symbol, price, ts }
- **Position:** { book_id, symbol, qty, ... }
- **P&L Aggregate:** { book_id, pnl, exposure, ts }

---
## 4. Key Workflows

### a) Real-time Aggregation
1. Tick and position updates ingested
2. Stream processor joins ticks with positions
3. Computes P&L and exposures per book/trader
4. Writes aggregates to OLAP cache
5. API/websocket serves pre-materialized views

### b) Drill-down & Query
1. User queries dashboard for book/trader
2. API fetches aggregates from OLAP
3. Websocket pushes updates for live view

---
## 5. Scaling & Reliability

- **Sharding:** By symbol/book for parallelism
- **Pre-materialization:** OLAP DB for low-latency queries
- **Websocket Fan-out:** Scalable push to 1k+ users
- **Monitoring:** Latency, update lag, user connections

---
## 6. Bottlenecks & Mitigations

- **Hot Symbols:** Shard and rebalance to avoid skew
- **OLAP Write Latency:** Use batch writes, partitioning
- **Websocket Scale:** Use pub/sub and connection pooling

---
## 7. Best Practices & Extensions

- Use time-windowed aggregations for P&L
- Audit logs for all updates
- Support for historical replay and what-if analysis
- Integrate with risk and trade capture systems

---
## 8. Example Pseudocode (Aggregation)
```python
def aggregate_pnl(ticks, positions):
    pnl = defaultdict(float)
    for tick in ticks:
        for pos in positions:
            if pos.symbol == tick.symbol:
                pnl[pos.book_id] += (tick.price - pos.entry_price) * pos.qty
    return pnl
```

---
## 9. References
- [OLAP for Real-time Analytics](https://clickhouse.com/docs/en/)
- [Streaming Aggregation](https://flink.apache.org/)
