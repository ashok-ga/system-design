# Rolling Time-Window Aggregator (VWAP EMA)

This problem involves designing a rolling time-window aggregator for financial data, specifically to compute metrics like Volume Weighted Average Price (VWAP) and Exponential Moving Average (EMA) over a sliding window. This is a common requirement in trading systems, analytics, and real-time dashboards.

---

### **1. System Overview & Scope Clarification**

- **Input:** A stream of trade events (price, volume, timestamp).
- **Output:** For each new event, compute the VWAP and EMA over the last N seconds/minutes (rolling window).
- **Requirements:**
    - **Low Latency:** Must update metrics in real-time as new events arrive.
    - **Configurable Window:** Support arbitrary window sizes (e.g., 1 minute, 5 minutes).
    - **Thread-Safety:** Safe for concurrent updates and reads.
    - **Memory Efficiency:** Only store events within the current window.

---

### **2. Core Components and Class Design**

- **TradeEvent:** Represents a single trade (price, volume, timestamp).
- **RollingWindowAggregator:** Maintains a time-ordered queue of events and computes VWAP/EMA as new events arrive and old ones expire.
- **Eviction Policy:** As new events arrive, remove events older than the window size.
- **EMA Calculation:** Use the standard EMA formula with a configurable smoothing factor.

---

### **3. API Design**

```java
public class TradeEvent {
    public final double price;
    public final double volume;
    public final long timestamp; // epoch millis
    public TradeEvent(double price, double volume, long timestamp) {
        this.price = price; this.volume = volume; this.timestamp = timestamp;
    }
}

public class RollingWindowAggregator {
    public RollingWindowAggregator(long windowMillis, double emaAlpha);
    public void onTrade(TradeEvent event);
    public double getVWAP();
    public double getEMA();
}
```

---

### **4. Key Workflows**

**a) Adding a Trade Event**
- Add the event to a time-ordered queue (e.g., LinkedList or ArrayDeque).
- Remove events from the head of the queue if they are older than (current time - windowMillis).
- Update running totals for VWAP (sum of price*volume, sum of volume).
- Update EMA using the formula: `EMA_new = alpha * price + (1 - alpha) * EMA_prev`.

**b) Querying VWAP and EMA**
- VWAP: `sum(price * volume) / sum(volume)` over the current window.
- EMA: The latest computed value.

---

### **5. Code Implementation (Java, Simplified)**

```java
import java.util.*;

public class TradeEvent {
    public final double price;
    public final double volume;
    public final long timestamp;
    public TradeEvent(double price, double volume, long timestamp) {
        this.price = price; this.volume = volume; this.timestamp = timestamp;
    }
}

public class RollingWindowAggregator {
    private final long windowMillis;
    private final double alpha;
    private final Deque<TradeEvent> window = new ArrayDeque<>();
    private double vwapNumerator = 0.0;
    private double vwapDenominator = 0.0;
    private double ema = Double.NaN;

    public RollingWindowAggregator(long windowMillis, double emaAlpha) {
        this.windowMillis = windowMillis;
        this.alpha = emaAlpha;
    }

    public synchronized void onTrade(TradeEvent event) {
        window.addLast(event);
        vwapNumerator += event.price * event.volume;
        vwapDenominator += event.volume;
        if (Double.isNaN(ema)) {
            ema = event.price;
        } else {
            ema = alpha * event.price + (1 - alpha) * ema;
        }
        evictOldEvents(event.timestamp);
    }

    private void evictOldEvents(long now) {
        while (!window.isEmpty() && window.peekFirst().timestamp < now - windowMillis) {
            TradeEvent old = window.removeFirst();
            vwapNumerator -= old.price * old.volume;
            vwapDenominator -= old.volume;
        }
    }

    public synchronized double getVWAP() {
        return vwapDenominator == 0.0 ? Double.NaN : vwapNumerator / vwapDenominator;
    }

    public synchronized double getEMA() {
        return ema;
    }
}
```

---

### **6. Testing and Extensions**

- **Testing:**
    - Feed a sequence of trades and verify VWAP/EMA match expected values.
    - Test with trades arriving out of order or with gaps.
    - Test with different window sizes and alpha values.
- **Extensions:**
    - Support for multiple symbols (map symbol to aggregator).
    - Add support for other metrics (e.g., simple moving average, max/min price).
    - Use a more efficient data structure for very high-frequency data (e.g., segment tree, skip list).
    - Add snapshotting for fast recovery after restart.
