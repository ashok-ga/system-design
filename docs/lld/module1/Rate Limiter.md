# Design a Scalable Rate Limiter

This problem requires designing a distributed, scalable rate limiter (token bucket/leaky bucket) for APIs or services.

### **1. System Overview & Scope Clarification**

We are designing a backend service to limit the rate of requests per user, API key, or IP, supporting distributed deployments.

**Functional Requirements (FR):**
- Enforce rate limits (e.g., 100 req/min) per key.
- Support burst and steady rates (token bucket).
- Distributed: works across multiple servers.
- Configurable per user/API.

**Non-Functional Requirements (NFR):**
- Low latency (sub-ms per check).
- High throughput (10k+ req/sec).
- Fault-tolerant and consistent.

**Assumptions:**
- Redis or similar is available for distributed state.
- In-memory fallback for demo.

---

### **2. Core Components and Class Design**

- **RateLimiter:** Main API for checking/consuming tokens.
- **TokenBucket:** Per-key state (tokens, last refill).
- **Store:** Interface for state (in-memory/Redis).

**Class Diagram (Textual Representation):**

```
+-------------+
| RateLimiter |
+-------------+
| + allow()   |
| - store     |
+-------------+
        ^
        |
+-------------+
| TokenBucket |
+-------------+
| tokens      |
| lastRefill  |
+-------------+
```

---

### **3. API Design (`RateLimiter`)**

Java

```java
class RateLimiter {
    boolean allow(String key);
}
```

---

### **4. Key Workflows**

**a) Allow Request**
1. Fetch bucket for key.
2. Refill tokens if needed.
3. If tokens > 0, allow and decrement; else, reject.
4. Persist state.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

class TokenBucket {
    int tokens;
    long lastRefill;
    final int capacity;
    final int refillRate;
    TokenBucket(int capacity, int refillRate) {
        this.capacity = capacity;
        this.refillRate = refillRate;
        this.tokens = capacity;
        this.lastRefill = System.currentTimeMillis();
    }
}

class InMemoryStore {
    private final Map<String, TokenBucket> buckets = new ConcurrentHashMap<>();
    public TokenBucket get(String key) { return buckets.get(key); }
    public void put(String key, TokenBucket bucket) { buckets.put(key, bucket); }
}

class RateLimiter {
    private final InMemoryStore store = new InMemoryStore();
    public boolean allow(String key) {
        TokenBucket bucket = store.get(key);
        if (bucket == null) {
            bucket = new TokenBucket(100, 100); // 100 tokens/min
            store.put(key, bucket);
        }
        refill(bucket);
        if (bucket.tokens > 0) {
            bucket.tokens--;
            return true;
        }
        return false;
    }
    private void refill(TokenBucket bucket) {
        long now = System.currentTimeMillis();
        long elapsed = now - bucket.lastRefill;
        int tokensToAdd = (int)(elapsed / 600);
        if (tokensToAdd > 0) {
            bucket.tokens = Math.min(bucket.capacity, bucket.tokens + tokensToAdd);
            bucket.lastRefill = now;
        }
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class RateLimiterTest {
    @Test
    void testAllow() {
        RateLimiter rl = new RateLimiter();
        for (int i = 0; i < 100; i++) assertTrue(rl.allow("user1"));
        assertFalse(rl.allow("user1"));
    }
}
```

---

### **7. Extensions and Edge Cases**
- Use Redis for distributed buckets.
- Add leaky bucket, sliding window algorithms.
- Support for dynamic configs and quotas.
