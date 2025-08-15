# Basic Matching Engine (with Market Orders)

Here, we elevate the `OrderBook` data structure into a full-fledged `MatchingEngine`. The key changes are supporting more complex order types (specifically market orders), handling all outcomes like partial fills, and, most importantly, producing a stream of events that communicates every action to the outside world.

### **1. System Overview & Scope Clarification**

A Matching Engine is the active component that drives a market. It takes order submission and cancellation requests as inputs and produces trades and order status updates as outputs. We will extend our previous `OrderBook` by wrapping it in a class that understands different order types and communicates its actions via an event bus.

**Functional Requirements (FR):**

- **Support Limit Orders:** As per the previous design.
- **Support Market Orders:** A market order is an instruction to buy or sell a specified quantity at the best available price(s) on the opposite side of the book immediately. Market orders never rest on the book.
- **Generate Trade Events:** Whenever a match occurs, a `Trade` event must be published, detailing the price, quantity, and parties involved.
- **Generate Order Update Events:** Every order's lifecycle must be tracked and communicated. This includes events for acceptance (`ACK`), partial fills, full fills, and cancellations.
- **Event Bus:** Provide a mechanism for downstream systems (like risk management, position keeping, market data feeds) to subscribe to these events.

**Non-Functional Requirements & Design Notes:**

- **Maintain Determinism & Low Latency:** The single-threaded core model from the previous problem must be preserved.
- **Price Protection:** A crucial safety feature. The engine should reject market orders that would execute at a price drastically different from the last known market price (e.g., last trade price or a Volume-Weighted Average Price - VWAP). This prevents a single large order from causing a "flash crash".
- **Circuit Breakers:** The engine should have hooks to allow an external system to halt all trading activity if market volatility or technical issues are detected.

---

### **2. Core Components and Class Design**

We will reuse the `OrderBook` and its internal structures, but the logic will be orchestrated by the `MatchingEngine`, which also introduces an eventing system.

- **`Order` (Modified):** We add an `OrderType` enum.
    - `enum OrderType { LIMIT, MARKET }`
    - A `MARKET` order might have its `price` field set to 0 or a sentinel value.
- **`MarketEvent` (New Hierarchy):** A sealed interface to represent all possible outputs from the engine.

Java

```java
public sealed interface MarketEvent {
    long timestamp();
}
public record Trade(long timestamp, long price, long quantity, long aggressingOrderId, long restingOrderId, Side aggressingSide) implements MarketEvent {}
public record OrderUpdate(long timestamp, long orderId, OrderStatus status, long remainingQuantity) implements MarketEvent {}
public enum OrderStatus { ACCEPTED, PARTIALLY_FILLED, FILLED, CANCELLED, REJECTED }
```

- **`EventBus` (New):** An interface for publishing events. A simple implementation will use a `BlockingQueue` to hand off events to a publisher thread, ensuring the matching thread is never blocked.
- **`MatchingEngine` (New Wrapper):** The central component.
    - Contains an `OrderBook` instance.
    - Contains an `EventBus` instance.
    - Runs the single-threaded command processing loop.
    - Holds logic to handle different `OrderType`s.
    - Integrates checks for circuit breakers and price protection.

---

### **3. API Design (Command and Event-Driven)**

The interaction model remains the same: external threads submit commands to a queue, and the engine emits events. The `AddOrder` command is now richer as it includes the `OrderType`.

**Input:** `BlockingQueue<OrderBookCommand>`**Output:** `EventBus` publishing a stream of `MarketEvent`s

---

### **4. Key Workflows (Executed by the `MatchingEngine` thread)**

The main loop processes one command at a time. The `processAddOrder` logic becomes more sophisticated.

**`processAddOrder(Order newOrder)` Workflow:**

1. **Pre-flight Checks:**
a. Check if a **circuit breaker** is active. If so, reject the order (publish `OrderUpdate` with `REJECTED` status) and stop.
b. Perform basic validation (e.g., quantity > 0). If invalid, reject.
2. **Acknowledge Acceptance:** Publish an `OrderUpdate` event with status `ACCEPTED`. This confirms the order has been received and is being processed.
3. **Handle by Order Type:**
    - **If `newOrder.type == LIMIT`:**
    a. The logic is similar to before, but instead of printing trades, the `OrderBook`'s matching methods now return a `List<Trade>`.
    b. The `MatchingEngine` receives this list and publishes each `Trade` to the `EventBus`.
    c. For each trade, it also publishes `OrderUpdate` events for both the aggressing and resting orders involved (`PARTIALLY_FILLED` or `FILLED`).
    d. If the limit order is not fully filled, it rests on the book.
    - **If `newOrder.type == MARKET`:**
    a. **Price Protection Check:** Compare the best price on the opposite side of the book with a reference price. If the slippage is too high, reject the entire order by publishing an `OrderUpdate` with status `REJECTED` (e.g., "Market price protection trip").
    b. Begin matching against the opposite side of the book, starting from the best price.
    c. Consume all available quantity at the best price level, generating `Trade` and `OrderUpdate` events as you go.
    d. Move to the next-best price level and repeat until the market order is fully filled.
    e. **Outcome 1: Fully Filled.** The order's quantity becomes zero. Publish a final `OrderUpdate` for the market order with status `FILLED`.
    f. **Outcome 2: Partially Filled.** The order still has quantity, but the opposite side of the book is now empty. A market order cannot rest, so the remaining quantity is cancelled. Publish a final `OrderUpdate` for the market order with status `CANCELLED`.

---

### **5. Code Implementation (Java)**

This shows the new `MatchingEngine` class and the modifications to handle market orders.

**`Order` and `MarketEvent` definitions**

Java

```java
public enum OrderType { LIMIT, MARKET }
public enum OrderStatus { ACCEPTED, PARTIALLY_FILLED, FILLED, CANCELLED, REJECTED }

public class Order {
    long orderId; Side side; OrderType type; long price; long quantity;
    // ... constructor and getters ...
}

public sealed interface MarketEvent { long timestamp(); }
public record Trade(long timestamp, long price, long quantity, /*...other fields...*/) implements MarketEvent {}
public record OrderUpdate(long timestamp, long orderId, OrderStatus status, long remainingQuantity) implements MarketEvent {}

// Simple EventBus for decoupling
public interface EventBus { void publish(MarketEvent event); }
```

**`MatchingEngine.java` (Simplified Logic)**

Java

```java
import java.util.List;
import java.util.ArrayList;

public class MatchingEngine {
    private final OrderBook orderBook;
    private final EventBus eventBus;

    public MatchingEngine(EventBus eventBus) {
        this.orderBook = new OrderBook(); // Our data structure from the previous problem
        this.eventBus = eventBus;
    }

    public void processAddOrder(Order newOrder) {
        // Assume pre-flight checks (circuit breaker, etc.) pass
        eventBus.publish(new OrderUpdate(System.nanoTime(), newOrder.orderId, OrderStatus.ACCEPTED, newOrder.quantity));

        List<Trade> trades = new ArrayList<>();
        if (newOrder.type == OrderType.LIMIT) {
            trades = orderBook.matchLimitOrder(newOrder);
        } else if (newOrder.type == OrderType.MARKET) {
            // Price protection check would go here
            trades = orderBook.matchMarketOrder(newOrder);
        }

        // Publish all generated events
        for (Trade trade : trades) {
            eventBus.publish(trade);
            // Publish updates for resting orders that were hit
            eventBus.publish(createUpdateForRestingOrder(trade));
        }
        
        // Publish final status for the aggressing order
        if (newOrder.quantity == 0) {
            eventBus.publish(new OrderUpdate(System.nanoTime(), newOrder.orderId, OrderStatus.FILLED, 0));
        } else if (trades.isEmpty()) {
            // No trades occurred, order rests (only for LIMIT)
            if(newOrder.type == OrderType.LIMIT) orderBook.restOrder(newOrder);
        } else {
            // Partial fill
            eventBus.publish(new OrderUpdate(System.nanoTime(), newOrder.orderId, OrderStatus.PARTIALLY_FILLED, newOrder.quantity));
            if(newOrder.type == OrderType.LIMIT) orderBook.restOrder(newOrder);
            else { // Unfilled market order portion is cancelled
                 eventBus.publish(new OrderUpdate(System.nanoTime(), newOrder.orderId, OrderStatus.CANCELLED, 0));
            }
        }
    }
    
    private OrderUpdate createUpdateForRestingOrder(Trade trade) {
        // Logic to find the resting order from the trade, check its remaining quantity,
        // and create a FILLED or PARTIALLY_FILLED update.
        return null; // Placeholder
    }
    
    // The OrderBook's matching methods would now be modified to return List<Trade>
    // instead of printing to console.
}
```

---

### **6. Testing (Key Scenarios)**

Testing the matching engine is primarily about verifying the event stream.

- **Scenario: Market order partially fills and exhausts the book.**
    1. **Setup:** `SELL 100 @ 101`.
    2. **Action:** Submit `BUY MARKET 150`.
    3. **Expected Event Stream:**
        1. `OrderUpdate(marketBuyId, ACCEPTED, 150)`
        2. `Trade(price=101, qty=100, ...)`
        3. `OrderUpdate(restingSellId, FILLED, 0)`
        4. `OrderUpdate(marketBuyId, PARTIALLY_FILLED, 50)`
        5. `OrderUpdate(marketBuyId, CANCELLED, 0)` (because no more liquidity)
- **Scenario: Market order fills across multiple price levels.**
    1. **Setup:** `SELL 100 @ 101`, `SELL 100 @ 102`.
    2. **Action:** Submit `BUY MARKET 150`.
    3. **Expected Event Stream:**
        1. `OrderUpdate(marketBuyId, ACCEPTED, 150)`
        2. `Trade(price=101, qty=100, ...)`
        3. `OrderUpdate(restingSellId_1, FILLED, 0)`
        4. `OrderUpdate(marketBuyId, PARTIALLY_FILLED, 50)`
        5. `Trade(price=102, qty=50, ...)`
        6. `OrderUpdate(restingSellId_2, PARTIALLY_FILLED, 50)`
        7. `OrderUpdate(marketBuyId, FILLED, 0)`

---

### **7. Extensions and Real-World Considerations**

- **IOC and FOK Orders:**
    - **Immediate-Or-Cancel (IOC):** Behaves like a market or limit order, but any portion that does not fill immediately is cancelled instead of resting. The logic is similar to a market order, but it can have a limit price.
    - **Fill-Or-Kill (FOK):** The entire order must be filled immediately, otherwise the entire order is cancelled. This requires a "probing" step to check if enough volume is available before executing any trades.
- **Self-Trade Prevention (STP):** A crucial feature. Before matching two orders, the engine checks if they belong to the same client/trader. If they do, the exchange's rules determine what happens. Often, the incoming order is cancelled to prevent a "wash trade".
- **Sophisticated Price Protection:** Instead of a simple check, production systems use a reference price like the Volume-Weighted Average Price (VWAP) over a recent time window and define collars (e.g., +/- 5%) outside of which a market order will be rejected.
- **Low-Latency Eventing:** The `EventBus` is on the critical path for communicating what happened. High-performance implementations use things like shared memory (`Aeron`) or ring buffers (`Disruptor`) to pass events to other threads with minimal latency and no garbage generation.
