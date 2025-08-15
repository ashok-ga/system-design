# Thread-Safe Limit Order Book (Equities)

This problem requires designing the core data structure of a financial exchange: the Limit Order Book (LOB). The design must support adding and canceling orders, matching trades according to strict price-time priority rules, and do so in a thread-safe, deterministic, and low-latency manner.

### **1. System Overview & Scope Clarification**

A Limit Order Book is a centralized record of all outstanding buy (bid) and sell (ask) limit orders for a specific financial instrument (e.g., stock in GOOGLE). Its job is to match incoming orders against resting orders to create trades.

**Core Principle: Price-Time Priority**
This is the non-negotiable rule for matching orders in most exchanges:

1. **Price Priority:** The highest-priced buy order (best bid) and the lowest-priced sell order (best ask) have the highest priority.
2. **Time Priority:** If multiple orders exist at the same best price, the one that was submitted earliest gets executed first (First-In, First-Out).

**Functional Requirements (FR):**

- **Add Limit Order:** Place a new buy or sell order onto the book with a specific price and quantity.
- **Cancel Order:** Remove an existing order from the book using its unique ID.
- **Order Matching:** When a new order's price "crosses the spread" (i.e., a buy order's price is >= the best sell price, or a sell order's price is <= the best buy price), it must be matched against resting orders according to price-time priority.
- **Query Book State:** Get the best bid and best ask prices and quantities.

**Non-Functional Requirements (NFR):**

- **Low Latency:** All operations (add, cancel, match) must be completed in microseconds.
- **Determinism:** For the same sequence of input commands, the system must produce the exact same sequence of output trades. This is critical for fairness and regulatory compliance.
- **High Throughput:** The system must handle tens of thousands to millions of commands per second.

**Concurrency Model: The Single Writer Principle**
To achieve determinism and avoid complex, slow locking, the standard industry pattern is to have a **single, dedicated thread** (the "matching engine") that processes all state-changing commands serially from a queue. Other threads (e.g., network threads handling client connections) act as producers, placing commands onto this queue. This is a Multiple-Producer, Single-Consumer (MPSC) model.

---

### **2. Core Components and Class Design**

The data structures are chosen for their performance characteristics in sorting and lookups.

- **`Order`:** A simple Plain Old Java Object (POJO) representing an order.
    - `long orderId`: Unique identifier.
    - `Side side`: An enum (`BUY`, `SELL`).
    - `long price`: The limit price (using `long` for fixed-point arithmetic, e.g., representing cents, is faster than `BigDecimal`).
    - `long quantity`: The number of shares.
    - `long timestamp`: Arrival time for time-priority.
    - `PriceLevel level`: A reference to the `PriceLevel` it belongs to, for fast cancellation.
- **`PriceLevel`:** Represents all orders at a single price point.
    - `long price`: The price of this level.
    - `long totalVolume`: The sum of quantities of all orders at this level.
    - `Deque<Order> orders`: A queue of orders, maintaining FIFO time priority. `ArrayDeque` is a good choice.
- **`OrderBook`:** The central data structure holding the two sides of the book.
    - `NavigableMap<Long, PriceLevel> bids`: A map of buy-side price levels, sorted from highest to lowest price. `TreeMap` with a reverse-order comparator is perfect.
    - `NavigableMap<Long, PriceLevel> asks`: A map of sell-side price levels, sorted from lowest to highest price. A standard `TreeMap` works here.
    - `Map<Long, Order> ordersById`: A `HashMap` for O(1) lookup of any order by its ID, essential for fast cancellations.
- **`MatchingEngine`**: The class that runs the single writer thread, consuming commands and operating on the `OrderBook`.

---

### **3. API Design (Commands and the Engine)**

The API is not a set of direct methods, but rather a set of command objects placed onto a queue.

```java
// Command interface
public sealed interface OrderBookCommand permits AddOrder, CancelOrder {}
public record AddOrder(Order order) implements OrderBookCommand {}
public record CancelOrder(long orderId) implements OrderBookCommand {}

public class MatchingEngine implements Runnable {
    private final BlockingQueue<OrderBookCommand> commandQueue;
    private final OrderBook orderBook;

    // The single thread runs this loop
    @Override
    public void run() {
        while (!Thread.currentThread().isInterrupted()) {
            try {
                OrderBookCommand command = commandQueue.take();
                processCommand(command);
            } catch (InterruptedException e) { /* ... */ }
        }
    }
    
    private void processCommand(OrderBookCommand command) {
        switch (command) {
            case AddOrder(var order) -> orderBook.addOrder(order);
            case CancelOrder(var id) -> orderBook.cancelOrder(id);
        }
    }
}
```

---

### **4. Key Workflows (executed by the single `MatchingEngine` thread)**

**a) `OrderBook.addOrder(Order newOrder)` Workflow**

1. **Match or Rest?**: The first step is to check if the incoming order is "marketable" (can be matched immediately).
    - If `newOrder` is a `BUY`: Check if the `asks` map is non-empty and `newOrder.price >= asks.firstKey()`.
    - If `newOrder` is a `SELL`: Check if the `bids` map is non-empty and `newOrder.price <= bids.firstKey()`.
2. **Matching Logic (if marketable):**
    a. Get the list of price levels from the opposite side (e.g., `asks.values()` for a buy order).
    b. Iterate through the price levels, starting from the best price.
    c. For each `PriceLevel`, iterate through its `Deque<Order>` (FIFO).
    d. Match `newOrder` against the resting order (`restingOrder`). The trade quantity is `min(newOrder.quantity, restingOrder.quantity)`.
    e. **Generate a `Trade` event (to be published to downstream systems).**
    f. Decrement quantities on both orders.
    g. If `restingOrder.quantity == 0`, remove it from its `PriceLevel`'s deque and the main `ordersById` map. If the `PriceLevel` becomes empty, remove it from its `TreeMap`.
    h. If `newOrder.quantity == 0`, the process is complete. Stop and return.
    i. If the price level is exhausted, move to the next best price level and repeat.
3. **Resting Logic (if not marketable or partially filled):**
    a. If `newOrder` still has quantity remaining, it must be placed on the book.
    b. Find the correct side (`bids` or `asks`).
    c. Use `map.computeIfAbsent(newOrder.price, ...)` to get or create the `PriceLevel`.
    d. Add the `newOrder` to the end of the `PriceLevel`'s `Deque`, update the level's total volume.
    e. Store the order in the `ordersById` map for future cancellation.

**b) `OrderBook.cancelOrder(long orderId)` Workflow**

1. Use the `ordersById` map to find the `Order` object in O(1) time. If it's not found, it was likely already filled; do nothing.
2. Get the `PriceLevel` from the `order.level` reference.
3. Remove the order from the `PriceLevel`'s `Deque`. This is O(N) on `ArrayDeque`. For extreme performance, a custom doubly-linked list implementation where the `Order` object itself is the node would make this O(1). For an interview, acknowledging this tradeoff is key.
4. Update the `PriceLevel`'s total volume.
5. If the `PriceLevel` is now empty, remove it from the `TreeMap` (`bids` or `asks`).
6. Finally, remove the order from the `ordersById` map.

---

### **5. Code Implementation (Java)**

This is a simplified implementation of the `OrderBook`'s core logic, assuming it's called by the single-threaded `MatchingEngine`.

```java
import java.util.*;

public enum Side { BUY, SELL }

// Simplified Order class for this example
public class Order {
    long orderId; Side side; long price; long quantity;
    public Order(long id, Side s, long p, long q) {
        this.orderId=id; this.side=s; this.price=p; this.quantity=q;
    }
    // ...getters and setters...
}

class PriceLevel {
    long totalVolume = 0;
    final Deque<Order> orders = new ArrayDeque<>();
}

public class OrderBook {
    private final NavigableMap<Long, PriceLevel> bids = new TreeMap<>(Collections.reverseOrder());
    private final NavigableMap<Long, PriceLevel> asks = new TreeMap<>();
    private final Map<Long, Order> ordersById = new HashMap<>(); // For fast cancellations

    public void addOrder(Order newOrder) {
        // For simplicity, we assume trade events are printed to console.
        if (newOrder.side == Side.BUY) {
            matchOrder(newOrder, asks);
        } else {
            matchOrder(newOrder, bids);
        }

        if (newOrder.quantity > 0) {
            restOrder(newOrder);
        }
    }

    private void matchOrder(Order newOrder, NavigableMap<Long, PriceLevel> oppositeSide) {
        Iterator<Map.Entry<Long, PriceLevel>> levelIterator = oppositeSide.entrySet().iterator();
        
        while (levelIterator.hasNext() && newOrder.quantity > 0) {
            Map.Entry<Long, PriceLevel> entry = levelIterator.next();
            long price = entry.getKey();
            PriceLevel level = entry.getValue();

            // Price check: can the new order be matched at this level?
            boolean priceMatch = (newOrder.side == Side.BUY && newOrder.price >= price) ||
                                 (newOrder.side == Side.SELL && newOrder.price <= price);
            if (!priceMatch) break;

            Iterator<Order> orderIterator = level.orders.iterator();
            while (orderIterator.hasNext() && newOrder.quantity > 0) {
                Order restingOrder = orderIterator.next();
                long tradeQty = Math.min(newOrder.quantity, restingOrder.quantity);
                
                System.out.printf("TRADE: %d shares at %d%n", tradeQty, restingOrder.price);

                newOrder.quantity -= tradeQty;
                restingOrder.quantity -= tradeQty;
                level.totalVolume -= tradeQty;

                if (restingOrder.quantity == 0) {
                    orderIterator.remove(); // Remove from Deque
                    ordersById.remove(restingOrder.orderId);
                }
            }

            if (level.orders.isEmpty()) {
                levelIterator.remove(); // Remove PriceLevel from TreeMap
            }
        }
    }

    private void restOrder(Order order) {
        NavigableMap<Long, PriceLevel> side = (order.side == Side.BUY) ? bids : asks;
        PriceLevel level = side.computeIfAbsent(order.price, k -> new PriceLevel());
        level.orders.addLast(order);
        level.totalVolume += order.quantity;
        ordersById.put(order.orderId, order);
    }
    
    // Cancellation logic would be here...
    public void cancelOrder(long orderId) { /* ... as described in workflow ... */ }
    
    // Public query methods
    public Optional<Long> getBestBid() { return Optional.ofNullable(bids.firstKey()); }
    public Optional<Long> getBestAsk() { return Optional.ofNullable(asks.firstKey()); }
}
```

---

### **6. Testing (Key Scenarios)**

- **Building the Book:** Add a series of non-crossing orders (`BUY 100 @ 99`, `BUY 50 @ 98`, `SELL 100 @ 101`, `SELL 50 @ 102`). Verify `getBestBid()` returns 99 and `getBestAsk()` returns 101.
- **Simple Cross:** With the book above, add `SELL 75 @ 99`. Verify a trade of 75 shares occurs, the original bid is now for 25 shares, and the sell order is gone.
- **Multi-Level Cross:** With the book above, add `SELL 200 @ 97`. Verify it first matches all 100 shares @ 99, then all 50 shares @ 98. The remaining 50 shares should rest on the book, making the new best ask 97.
- **Cancellation:** Add an order, then cancel it. Verify it's gone from all data structures.

---

### **7. Performance, Concurrency, and Extensions**

- **Concurrency:** The MPSC queue model is the key. It serializes all writes, making the core logic simple and lock-free. Reads (like providing a market data snapshot) are tricky; they either need to be queued as commands or use non-blocking techniques to read a potentially stale copy of the book state.
- **Performance Optimizations:**
    - **Cancellation:** As noted, O(N) removal from a `PriceLevel`'s `ArrayDeque` is a bottleneck. A custom `Order` class that is also a node in a doubly-linked list makes removal O(1).
    - **GC-Free:** For HFT, avoiding GC is critical. This involves object pooling (reusing `Order` objects instead of creating new ones) and avoiding any memory allocation on the critical path.
    - **Primitives:** Using `long` for price/quantity avoids `BigDecimal` object overhead.
- **Extensions:**
    - **Market Orders:** Add an `Order` type with no price. It matches against the best available prices until filled. In the `matchOrder` logic, a market order would simply not have the `priceMatch` condition.
    - **Other Order Types:** Implement Immediate-Or-Cancel (IOC) orders (match what you can immediately, cancel the rest) and Fill-Or-Kill (FOK) orders (execute the entire quantity immediately or cancel).
    - **Market Data Feeds:** The `OrderBook` should generate events for every state change (new order, cancel, trade, book update). These events are put onto outbound queues for market data publishers and other downstream systems. The matching engine thread should *not* be blocked by slow consumers of this data.
