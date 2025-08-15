# Distributed ID Generator (Snowflake-like)

This problem requires designing a distributed, sortable 64-bit ID generator (like Twitter Snowflake) that works across datacenters and workers.

### **1. System Overview & Scope Clarification**

We are designing a backend service to generate unique, time-sortable IDs for distributed systems.

**Functional Requirements (FR):**
- Generate 64-bit IDs composed of timestamp, datacenter, worker, and sequence.
- Ensure uniqueness and monotonicity within a millisecond.
- Handle clock skew and rollover.
- Thread-safe for concurrent requests.

**Non-Functional Requirements (NFR):**
- High throughput (10k+ IDs/sec per node).
- Low latency (sub-millisecond per call).
- Fault-tolerant: no duplicate IDs on restart.
- Scalable: support for many datacenters and workers.

**Assumptions:**
- Each instance is assigned a unique datacenter and worker ID.
- System clock is NTP-synchronized.
- State can be persisted locally (for last timestamp).

---

### **2. Core Components and Class Design**

- **IdGenerator:** Main class for generating IDs.
- **Clock:** Abstraction for time (for testing/skew handling).
- **Persistence:** Interface to persist last timestamp (optional for in-memory demo).

**Class Diagram (Textual Representation):**

```
+-------------------+
|   IdGenerator     |
+-------------------+
| + nextId()        |
| - lastTimestamp   |
| - sequence        |
| - workerId        |
| - datacenterId    |
+-------------------+
        ^
        |
+-------------------+
|     Clock         |
+-------------------+
| + now()           |
+-------------------+
```

---

### **3. API Design (`IdGenerator`)**

Java

```java
class IdGenerator {
    long nextId();
}
```

---

### **4. Key Workflows**

**a) ID Generation**
1. Get current timestamp (ms).
2. If timestamp < lastTimestamp: wait until lastTimestamp or throw error.
3. If timestamp == lastTimestamp: increment sequence; if sequence overflows, wait for next ms.
4. If timestamp > lastTimestamp: reset sequence to 0.
5. Compose ID: `(timestamp << 22) | (datacenterId << 17) | (workerId << 12) | sequence`.
6. Persist lastTimestamp.

---

### **5. Code Implementation (Java)**

```java
public class IdGenerator {
    private final long workerId;
    private final long datacenterId;
    private long sequence = 0L;
    private long lastTimestamp = -1L;
    private static final long EPOCH = 1609459200000L; // 2021-01-01
    private static final long WORKER_ID_BITS = 5L;
    private static final long DATACENTER_ID_BITS = 5L;
    private static final long SEQUENCE_BITS = 12L;
    private static final long MAX_WORKER_ID = ~(-1L << WORKER_ID_BITS);
    private static final long MAX_DATACENTER_ID = ~(-1L << DATACENTER_ID_BITS);
    private static final long SEQUENCE_MASK = ~(-1L << SEQUENCE_BITS);
    public IdGenerator(long workerId, long datacenterId) {
        if (workerId > MAX_WORKER_ID || workerId < 0) throw new IllegalArgumentException();
        if (datacenterId > MAX_DATACENTER_ID || datacenterId < 0) throw new IllegalArgumentException();
        this.workerId = workerId;
        this.datacenterId = datacenterId;
    }
    public synchronized long nextId() {
        long timestamp = System.currentTimeMillis();
        if (timestamp < lastTimestamp) {
            throw new RuntimeException("Clock moved backwards");
        }
        if (timestamp == lastTimestamp) {
            sequence = (sequence + 1) & SEQUENCE_MASK;
            if (sequence == 0) {
                // Sequence overflow, wait for next ms
                while ((timestamp = System.currentTimeMillis()) <= lastTimestamp) {}
            }
        } else {
            sequence = 0L;
        }
        lastTimestamp = timestamp;
        return ((timestamp - EPOCH) << 22)
            | (datacenterId << 17)
            | (workerId << 12)
            | sequence;
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class IdGeneratorTest {
    @Test
    void testMonotonicity() {
        IdGenerator gen = new IdGenerator(1, 1);
        long prev = gen.nextId();
        for (int i = 0; i < 1000; i++) {
            long id = gen.nextId();
            assertTrue(id > prev);
            prev = id;
        }
    }
}
```

---

### **7. Concurrency, Fault Tolerance, and Scalability**
- Use `synchronized` for thread safety.
- Persist lastTimestamp to disk for crash recovery.
- Assign worker/datacenter IDs via config or coordination service (e.g., Zookeeper).
- Use NTP for clock sync; monitor for skew.
