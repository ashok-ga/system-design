# Design a Distributed Lock Service

This problem requires designing a distributed lock service for synchronizing access to shared resources across systems.

### **1. System Overview & Scope Clarification**

We are designing a backend service to provide distributed, fault-tolerant locks for clients in a distributed system.

**Functional Requirements (FR):**
- Acquire/release locks by key.
- Support lock timeouts and renewal.
- Ensure mutual exclusion and avoid deadlocks.

**Non-Functional Requirements (NFR):**
- High availability and fault tolerance.
- Low latency for lock ops.
- Scalable to thousands of clients.

**Assumptions:**
- Redis/ZooKeeper/etcd available for coordination.
- In-memory for demo.

---

### **2. Core Components and Class Design**

- **LockService:** Main API for lock ops.
- **Lock:** Represents a lock state.
- **Client:** Represents lock holders.

**Class Diagram (Textual Representation):**

```
+--------+      +--------+
| Lock   |<-----| Client |
+--------+      +--------+
| key    |      | id     |
| owner  |      +--------+
| expiry |
+--------+
      ^
      |
+--------------+
|LockService   |
+--------------+
| + acquire()  |
| + release()  |
+--------------+
```

---

### **3. API Design (`LockService`)**

Java

```java
class LockService {
    boolean acquire(String key, String clientId, long timeoutMs);
    void release(String key, String clientId);
}
```

---

### **4. Key Workflows**

**a) Acquire Lock**
1. Client requests lock; service checks if free or expired.
2. If so, assigns lock to client with expiry.

**b) Release Lock**
1. Client releases lock; service removes ownership.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;

class Lock {
    String key;
    String owner;
    long expiry;
}

class LockService {
    private final Map<String, Lock> locks = new HashMap<>();
    public synchronized boolean acquire(String key, String clientId, long timeoutMs) {
        Lock lock = locks.get(key);
        long now = System.currentTimeMillis();
        if (lock == null || lock.expiry < now) {
            lock = new Lock();
            lock.key = key;
            lock.owner = clientId;
            lock.expiry = now + timeoutMs;
            locks.put(key, lock);
            return true;
        }
        return false;
    }
    public synchronized void release(String key, String clientId) {
        Lock lock = locks.get(key);
        if (lock != null && lock.owner.equals(clientId)) {
            locks.remove(key);
        }
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class LockServiceTest {
    @Test
    void testAcquireAndRelease() {
        LockService svc = new LockService();
        assertTrue(svc.acquire("res1", "c1", 1000));
        assertFalse(svc.acquire("res1", "c2", 1000));
        svc.release("res1", "c1");
        assertTrue(svc.acquire("res1", "c2", 1000));
    }
}
```

---

### **7. Extensions and Edge Cases**
- Add fencing tokens, renewal, and failover.
- Integrate with Redis/ZooKeeper for production.
- Handle client crashes and lock expiry.
