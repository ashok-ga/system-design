# Token-Bucket Rate Limiter (Multi-Tenant)

This problem involves designing a rate limiter that can enforce different request limits for multiple clients (or tenants) using the token bucket algorithm. This is a critical component for API gateways, microservices, and any system needing to control traffic flow.

### **1. System Overview & Scope Clarification**

We are building an in-memory, server-side rate limiting service. The goal is to control the frequency of operations on a per-client basis, identified by a unique key (e.g., user ID, API key, IP address).

**Algorithm Choice: Token Bucket**
The token bucket algorithm is ideal for this use case. It works as follows:

- A bucket has a maximum capacity of tokens.
- Tokens are added to the bucket at a fixed rate.
- If the bucket is full, new tokens are discarded.
- Each incoming request consumes one token. If the bucket is empty, the request is rejected.
This allows for **bursts of requests** up to the bucket's capacity, which is often desirable, while maintaining a constant average rate over time.

**Functional Requirements (FR):**

- **`isAllowed(key)`:** A method that returns `true` if a request for a given key should proceed, and `false` if it should be rate-limited.
- **Multi-Tenancy:** The system must support different rate limits and burst capacities for different keys.
- **Configuration:** Allow setting a default limit and tenant-specific overrides.

**Non-Functional Requirements (NFR):**

- **Performance:** The `isAllowed` check (the hot path) must be highly performant, ideally O(1).
- **Thread-Safety:** The limiter must handle concurrent requests for the same or different keys correctly.
- **Monotonic Clock:** The logic must use a monotonic clock (`System.nanoTime()`) to be immune to system time changes (e.g., NTP adjustments, daylight saving).

**Scope:**

- We will design a single-node, in-memory solution first.
- We will then discuss the necessary modifications to scale it to a distributed environment.

---

### **2. Core Components and Class Design**

The design will consist of a central manager class that holds a collection of individual token buckets.

- **`RateLimiterConfig`:** A simple data object (or Java Record) to hold the configuration for a bucket: its `capacity` (burst size) and `refillRateInTokensPerSecond`.
- **`TokenBucket`:** This class encapsulates the state and logic for a single client's bucket. It will contain the configuration, the current number of tokens, and the timestamp of the last refill. Its methods will be synchronized to ensure thread safety.
- **`MultiTenantRateLimiter`:** The main public class. It holds a `ConcurrentHashMap` mapping a client key (`String`) to their respective `TokenBucket`. It manages the creation of new buckets on-demand based on the provided configurations.

**Class Diagram (Textual Representation):**

`+---------------------------+
| MultiTenantRateLimiter    |
|---------------------------|
| - buckets: ConcurrentHashMap<String, TokenBucket> |
| - defaultConfig: RateLimiterConfig |
| - specificConfigs: Map<String, RateLimiterConfig> |
|---------------------------|
| + isAllowed(key): boolean |
+---------------------------+
          |
          | creates & manages
          v
+---------------------------+
|      TokenBucket          |
|---------------------------|
| - capacity: long          |
| - refillRatePerNano: double |
| - tokens: double          |
| - lastRefillNanos: long   |
|---------------------------|
| + allow(): boolean (sync) |
+---------------------------+`

---

### **3. API Design (`MultiTenantRateLimiter`)**

Java

```cpp
public class MultiTenantRateLimiter {

    // Constructor to define the default and specific rate limiting rules.
    public MultiTenantRateLimiter(RateLimiterConfig defaultConfig, Map<String, RateLimiterConfig> specificConfigs);

    /**
     * Determines if a request for the given key should be allowed.
     * This method is thread-safe and has O(1) complexity.
     * It lazily creates token buckets for new keys.
     * @param key The identifier for the client (e.g., userId, apiKey).
     * @return true if the request is within the limit, false otherwise.
     */
    public boolean isAllowed(String key);
}

// Configuration record
public record RateLimiterConfig(long capacity, double tokensPerSecond) {}
```

---

### **4. Key Workflows**

**`isAllowed(key)` Workflow:**

1. The `MultiTenantRateLimiter` receives a call to `isAllowed("some_user_id")`.
2. It uses `ConcurrentHashMap.computeIfAbsent()` to atomically get or create the `TokenBucket` for `"some_user_id"`.
    - **If bucket exists:** The existing instance is returned.
    - **If bucket does not exist (first request):**
    a. A lambda expression is executed to create the new bucket.
    b. It checks the `specificConfigs` map for `"some_user_id"`. If a config is found, it's used.
    c. Otherwise, the `defaultConfig` is used.
    d. A new `TokenBucket` is instantiated with the chosen config, starting with a full bucket of tokens.
    e. The new bucket is placed in the map and returned.
3. The method then calls the `allow()` method on the retrieved `TokenBucket`.
4. **Inside `TokenBucket.allow()` (a `synchronized` method):**
a. A private `refill()` method is called first.
b. `refill()` calculates the time delta in nanoseconds since the last refill (`System.nanoTime() - lastRefillNanos`).
c. It calculates tokens to add (`delta * refillRatePerNano`) and adds them to the current token count.
d. The token count is capped at the bucket's `capacity`.
e. The `lastRefillNanos` timestamp is updated to the current time.
f. After refilling, `allow()` checks if `tokens >= 1.0`.
g. If yes, it subtracts `1.0` from `tokens` and returns `true`.
h. If no, it returns `false`.

---

### **5. Code Implementation (Java)**

**`RateLimiterConfig.java`**

Java

```cpp
public record RateLimiterConfig(long capacity, double tokensPerSecond) {
    public RateLimiterConfig {
        if (capacity <= 0 || tokensPerSecond <= 0) {
            throw new IllegalArgumentException("Capacity and tokensPerSecond must be positive.");
        }
    }
}
```

**`TokenBucket.java`**

Java

```cpp
class TokenBucket {
    private final long capacity;
    private final double refillRatePerNano;
    private double tokens;
    private long lastRefillNanos;

    TokenBucket(RateLimiterConfig config) {
        this.capacity = config.capacity();
        this.refillRatePerNano = config.tokensPerSecond() / 1_000_000_000.0;
        this.tokens = config.capacity(); // Start with a full bucket
        this.lastRefillNanos = System.nanoTime();
    }

    private void refill() {
        long now = System.nanoTime();
        long nanosElapsed = now - lastRefillNanos;
        if (nanosElapsed > 0) {
            double tokensToAdd = nanosElapsed * refillRatePerNano;
            this.tokens = Math.min(capacity, this.tokens + tokensToAdd);
            this.lastRefillNanos = now;
        }
    }

    public synchronized boolean allow() {
        refill();
        if (this.tokens >= 1.0) {
            this.tokens -= 1.0;
            return true;
        }
        return false;
    }
}
```

**`MultiTenantRateLimiter.java`**

Java

```cpp
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class MultiTenantRateLimiter {
    private final ConcurrentHashMap<String, TokenBucket> buckets = new ConcurrentHashMap<>();
    private final RateLimiterConfig defaultConfig;
    private final Map<String, RateLimiterConfig> specificConfigs;

    public MultiTenantRateLimiter(RateLimiterConfig defaultConfig, Map<String, RateLimiterConfig> specificConfigs) {
        this.defaultConfig = defaultConfig;
        this.specificConfigs = specificConfigs;
    }

    public boolean isAllowed(String key) {
        TokenBucket bucket = buckets.computeIfAbsent(key, this::createBucket);
        return bucket.allow();
    }

    private TokenBucket createBucket(String key) {
        RateLimiterConfig config = specificConfigs.getOrDefault(key, defaultConfig);
        return new TokenBucket(config);
    }
}
```

---

### **6. Testing (JUnit 5)**

Java

```cpp
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

class MultiTenantRateLimiterTest {

    @Test
    void testAllowsBurstUpToCapacity() {
        RateLimiterConfig config = new RateLimiterConfig(5, 10);
        MultiTenantRateLimiter limiter = new MultiTenantRateLimiter(config, Map.of());
        
        for (int i = 0; i < 5; i++) {
            assertTrue(limiter.isAllowed("user1"), "Request " + (i+1) + " should be allowed");
        }
        assertFalse(limiter.isAllowed("user1"), "6th request should be denied");
    }

    @Test
    void testTokenRefill() throws InterruptedException {
        // 1 token per 100ms
        RateLimiterConfig config = new RateLimiterConfig(1, 10); 
        MultiTenantRateLimiter limiter = new MultiTenantRateLimiter(config, Map.of());

        assertTrue(limiter.isAllowed("user1")); // Consume the only token
        assertFalse(limiter.isAllowed("user1")); // Now it's empty

        Thread.sleep(110); // Wait for more than 100ms for a token to refill

        assertTrue(limiter.isAllowed("user1"), "Should be allowed after refill");
    }

    @Test
    void testMultiTenantSpecificConfigs() {
        RateLimiterConfig defaultConfig = new RateLimiterConfig(1, 10);
        RateLimiterConfig premiumConfig = new RateLimiterConfig(5, 100);
        MultiTenantRateLimiter limiter = new MultiTenantRateLimiter(
            defaultConfig, 
            Map.of("premiumUser", premiumConfig)
        );

        // Test default user
        assertTrue(limiter.isAllowed("defaultUser"));
        assertFalse(limiter.isAllowed("defaultUser"));
        
        // Test premium user
        for (int i = 0; i < 5; i++) {
            assertTrue(limiter.isAllowed("premiumUser"));
        }
        assertFalse(limiter.isAllowed("premiumUser"));
    }

    @Test
    void testConcurrencyForSingleKey() throws InterruptedException {
        RateLimiterConfig config = new RateLimiterConfig(20, 100);
        MultiTenantRateLimiter limiter = new MultiTenantRateLimiter(config, Map.of());
        ExecutorService executor = Executors.newFixedThreadPool(10);
        AtomicInteger allowedCount = new AtomicInteger(0);

        for (int i = 0; i < 50; i++) {
            executor.submit(() -> {
                if (limiter.isAllowed("concurrentUser")) {
                    allowedCount.incrementAndGet();
                }
            });
        }

        executor.shutdown();
        executor.awaitTermination(5, TimeUnit.SECONDS);

        // Initially, the burst capacity of 20 should be allowed.
        // A few more might get through depending on thread scheduling and refill, but it should be close to 20.
        assertTrue(allowedCount.get() >= 20 && allowedCount.get() < 25);
    }
}
```

---

### **7. Scalability & Extensions**

The current implementation is for a single application instance. In a distributed system with multiple instances, this design would lead to an effective rate limit of `(limit * N)` where `N` is the number of instances, which is incorrect.

**Distributed Rate Limiter using Redis**

To solve this, the state of each token bucket must be centralized in a fast, shared data store like **Redis**.

- **State Storage:** For each client key (e.g., `"ratelimit:user123"`), store a Redis Hash with two fields:
    - `tokens`: The current number of tokens.
    - `last_refill_ts`: The timestamp of the last refill (in microseconds or nanoseconds for precision).
- **Atomic Operations:** The read-modify-write cycle (refill tokens, check, consume) must be atomic to prevent race conditions between different application servers. This is a perfect use case for a **Redis Lua script**.
- **Lua Script Workflow:**
    1. **Input:** The script receives `KEYS[1]` (the Redis key), `ARGV[1]` (capacity), `ARGV[2]` (refill rate per second), and `ARGV[3]` (current timestamp).
    2. **Get State:** It retrieves the `tokens` and `last_refill_ts` from the Redis hash at `KEYS[1]`. If the hash doesn't exist, it initializes it to the full capacity.
    3. **Refill Logic:** It calculates the time delta and refills tokens, capping at the capacity, just like the in-memory version.
    4. **Check & Consume:** It checks if `tokens >= 1`. If so, it decrements the token count.
    5. **Update State:** It updates the hash in Redis with the new `tokens` and `last_refill_ts`.
    6. **Return:** It returns 1 if allowed, 0 if denied.
    
    Since Redis executes Lua scripts atomically, this guarantees consistency across all application instances.
    

**Other Extensions:**

- **Idle Bucket Eviction:** The `ConcurrentHashMap` will grow indefinitely as new keys make requests. In a long-running application, this is a memory leak. A production-grade solution would use a cache with an eviction policy (like `Caffeine` or `Guava Cache`) to remove buckets for clients that have been inactive for a certain period.
- **Sliding Window Log:** For more complex rate limiting scenarios (e.g., "100 requests per hour"), the Sliding Window Log algorithm, also implemented efficiently in Redis using sorted sets, can be a better fit than the token bucket.