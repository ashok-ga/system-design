---
# Real-time Market Data Fan-out (Ticks → Thousands of Clients)

## 1. Problem Statement & Requirements
Design a real-time market data fan-out system to ingest, normalize, and distribute high-frequency financial tick data to thousands of downstream clients and services.

**Functional Requirements:**
- Ingest vendor UDP/TCP feeds (multiple formats)
- Normalize and partition by symbol/instrument
- Multicast to internal services and external clients (websockets, APIs)
- Per-symbol and per-client filtering
- Handle slow consumers gracefully (drop, backpressure)
- Hot/cold storage for ticks

**Non-Functional Requirements:**
- 1–5M messages/sec ingress
- 1–10k downstream clients
- p99 < 5–20ms end-to-end latency
- High availability, zero data loss on core path

**Assumptions:**
- Kernel bypass (DPDK/XDP) optional for ultra-low latency
- Internal network is high-throughput, low-latency

---
## 2. High-Level Architecture

**Components:**
- **Feed Handler:** Parses vendor UDP/TCP feeds, normalizes to internal format
- **Normalizer:** Cleanses, enriches, and partitions data by symbol
- **Broker:** High-throughput message bus (Kafka/Pulsar/Disruptor)
- **Fan-out Hubs:** Per-client or per-group ring buffers for downstream consumers
- **Websocket/API Edge:** Exposes data to external clients
- **Slow Consumer Handler:** Monitors lag, applies drop/backpressure
- **Storage:** Hot cache (Redis/Memcached), cold store (Parquet+S3/Iceberg, ClickHouse/Pinot)

**Architecture Diagram:**
```
 [Feed Handler] -> [Normalizer] -> [Broker] -> [Fan-out Hubs] -> [WS/API Edge]
                                             |
                                             v
                                         [Storage]
```

---
## 3. Data Model & Partitioning

- **Tick Message:** { symbol, price, size, ts, ... }
- **Partitioning:** By symbol (topic/partition in broker)
- **Per-client Buffer:** Ring buffer or queue for each client/consumer group

---
## 4. Key Workflows

### a) Ingestion & Normalization
1. Feed Handler receives UDP/TCP packets
2. Parses and normalizes to internal tick format
3. Passes to Normalizer for cleansing, enrichment
4. Publishes to Broker (partitioned by symbol)

### b) Fan-out to Clients
1. Fan-out Hub subscribes to relevant partitions/topics
2. Maintains per-client ring buffer (fixed size)
3. Applies per-symbol and per-client filters
4. Sends to client via websocket/API
5. If client lags, applies drop policy or disconnects

### c) Storage
1. Hot ticks cached in Redis/Mem for fast access
2. Cold ticks written to Parquet+S3/Iceberg or OLAP DB

---
## 5. Scaling & Reliability

- **Horizontal Scaling:** Multiple Feed Handlers, Normalizers, Fan-out Hubs
- **Partitioning:** By symbol for parallelism
- **Backpressure:** Broker and ring buffers apply backpressure to slow consumers
- **Zero-copy:** Use direct buffers, kernel bypass for low latency
- **Monitoring:** Track lag, dropped messages, latency, throughput

---
## 6. Bottlenecks & Mitigations

- **GC Pauses:** Use off-heap buffers, fixed pools
- **Buffer Bloat:** Fixed-size ring buffers, drop policy
- **Nagle/Coalesce:** Disable Nagle, tune kernel net (RPS/RFS)
- **Slow Consumers:** Drop or disconnect laggards

---
## 7. Best Practices & Extensions

- Use blue/green deployment for zero downtime
- Partition by symbol for scalability
- Kernel bypass (DPDK/XDP) for ultra-low latency
- Per-client metrics and alerting
- Integrate with risk/analytics systems

---
## 8. Example Pseudocode (Fan-out Hub)
```python
class FanoutHub:
    def __init__(self):
        self.clients = {}
    def subscribe(self, client, symbols):
        self.clients[client] = {'symbols': set(symbols), 'buffer': RingBuffer(1000)}
    def on_tick(self, tick):
        for client, info in self.clients.items():
            if tick.symbol in info['symbols']:
                if not info['buffer'].full():
                    info['buffer'].push(tick)
                else:
                    # Drop or disconnect
                    pass
```

---
## 9. References
- [Kafka for Market Data](https://www.confluent.io/blog/kafka-fastest-messaging-system/)
- [Zero-Copy Networking](https://lwn.net/Articles/193769/)
