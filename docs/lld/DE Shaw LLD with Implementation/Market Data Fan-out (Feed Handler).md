# Market Data Fan-out (Feed Handler)

This problem involves designing a high-performance, low-latency market data fan-out service (feed handler) for a trading system. The service must ingest a stream of market data updates (e.g., order book changes, trades) and efficiently distribute them to many downstream consumers (e.g., trading algorithms, GUIs, risk systems) with minimal latency and high throughput.

---

### **1. System Overview & Scope Clarification**

- **Input:** A single, high-volume stream of market data updates (e.g., from an exchange or internal matching engine).
- **Output:** Each update must be delivered to all registered consumers (subscribers) as quickly as possible.
- **Requirements:**
    - **Low Latency:** Updates must be fanned out to all consumers with minimal delay (microseconds to low milliseconds).
    - **High Throughput:** Must support thousands to millions of updates per second.
    - **Backpressure Handling:** Slow consumers must not block or degrade the performance for fast consumers.
    - **Reliability:** No update should be lost for any consumer unless explicitly dropped due to backpressure policy.
    - **Thread-Safety:** The system must be safe for concurrent use by multiple producers and consumers.

---

### **2. Core Components and Class Design**

- **FeedHandler:** The main orchestrator. Receives updates and distributes them to all consumers.
- **Consumer (Subscriber):** An interface implemented by downstream systems. Each consumer gets its own queue/buffer.
- **RingBuffer/Queue:** Each consumer is assigned a bounded, lock-free queue (e.g., Disruptor RingBuffer or ArrayBlockingQueue) to decouple producer and consumer speeds.
- **Backpressure Policy:** If a consumer's queue is full, the system can either drop updates for that consumer, block the producer, or disconnect the slow consumer.
- **Thread Model:**
    - **Single Producer, Multiple Consumers:** The feed handler thread reads updates and enqueues them to each consumer's buffer.
    - **Each Consumer:** Runs in its own thread, reading from its buffer and processing updates at its own pace.

---

### **3. API Design**

```java
public interface MarketDataConsumer {
    void onMarketData(MarketDataUpdate update);
}

public class MarketDataUpdate {
    // e.g., order book snapshot, trade, etc.
    // Fields: symbol, price, size, type, timestamp, etc.
}

public class FeedHandler {
    public void registerConsumer(MarketDataConsumer consumer);
    public void unregisterConsumer(MarketDataConsumer consumer);
    public void onMarketData(MarketDataUpdate update); // Called by producer
}
```

---

### **4. Key Workflows**

**a) Registering a Consumer**
- FeedHandler creates a bounded queue for the consumer and starts a thread to deliver updates from the queue to the consumer's `onMarketData` method.

**b) Receiving an Update**
- FeedHandler receives a `MarketDataUpdate` from the producer.
- For each registered consumer, it enqueues the update into the consumer's queue.
- If the queue is full, apply the backpressure policy (e.g., drop, block, or disconnect).

**c) Consumer Processing**
- Each consumer thread dequeues updates and processes them independently.
- If a consumer is slow, its queue fills up, and backpressure policy is triggered.

---

### **5. Code Implementation (Java, Simplified)**

```java
import java.util.concurrent.*;
import java.util.*;

public interface MarketDataConsumer {
    void onMarketData(MarketDataUpdate update);
}

public class MarketDataUpdate {
    public final String symbol;
    public final double price;
    public final int size;
    public final String type; // e.g., "TRADE", "BOOK"
    public final long timestamp;
    public MarketDataUpdate(String symbol, double price, int size, String type, long timestamp) {
        this.symbol = symbol; this.price = price; this.size = size; this.type = type; this.timestamp = timestamp;
    }
}

public class FeedHandler {
    private final Map<MarketDataConsumer, BlockingQueue<MarketDataUpdate>> consumerQueues = new ConcurrentHashMap<>();
    private final int queueCapacity = 1024; // Tune as needed
    private final ExecutorService consumerThreads = Executors.newCachedThreadPool();

    public void registerConsumer(MarketDataConsumer consumer) {
        BlockingQueue<MarketDataUpdate> queue = new ArrayBlockingQueue<>(queueCapacity);
        consumerQueues.put(consumer, queue);
        consumerThreads.submit(() -> {
            try {
                while (true) {
                    MarketDataUpdate update = queue.take();
                    consumer.onMarketData(update);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        });
    }

    public void unregisterConsumer(MarketDataConsumer consumer) {
        consumerQueues.remove(consumer);
        // Optionally interrupt the consumer thread
    }

    public void onMarketData(MarketDataUpdate update) {
        for (BlockingQueue<MarketDataUpdate> queue : consumerQueues.values()) {
            // Backpressure policy: drop if full
            queue.offer(update);
        }
    }
}
```

---

### **6. Testing and Extensions**

- **Testing:**
    - Simulate multiple consumers with different speeds.
    - Verify that fast consumers get all updates, slow consumers may drop updates if their queue is full.
    - Measure end-to-end latency.
- **Extensions:**
    - Use a high-performance ring buffer (e.g., LMAX Disruptor) for even lower latency.
    - Add metrics for dropped updates, queue sizes, and consumer lag.
    - Support for consumer-specific filtering (e.g., only certain symbols).
    - Add replay/buffering for late-joining consumers.
    - Support for multiple producers (requires more advanced concurrency control).
