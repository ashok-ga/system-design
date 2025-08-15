# Design a Thread-Safe LRU Cache

This problem requires designing a thread-safe Least Recently Used (LRU) cache with O(1) operations.

### **1. System Overview & Scope Clarification**

We are designing a backend component to cache key-value pairs with LRU eviction and thread safety.

**Functional Requirements (FR):**
- O(1) get/put/evict operations.
- Thread-safe for concurrent access.
- Configurable capacity.

**Non-Functional Requirements (NFR):**
- High throughput (10k+ ops/sec).
- Low latency (sub-ms per op).

**Assumptions:**
- In-memory only for this round.

---

### **2. Core Components and Class Design**

- **LRUCache:** Main API for get/put.
- **Node:** Doubly-linked list node for order.
- **Map:** Key to node mapping.

**Class Diagram (Textual Representation):**

```
+---------+
| LRUCache|
+---------+
| + get() |
| + put() |
| - map   |
| - head  |
| - tail  |
+---------+
```

---

### **3. API Design (`LRUCache`)**

Java

```java
class LRUCache<K,V> {
    V get(K key);
    void put(K key, V value);
}
```

---

### **4. Key Workflows**

**a) Get**
1. Lookup node in map.
2. Move node to head.
3. Return value.

**b) Put**
1. If key exists, update value and move to head.
2. Else, add new node at head.
3. If over capacity, evict tail.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;
import java.util.concurrent.locks.*;

class Node<K,V> {
    K key;
    V value;
    Node<K,V> prev, next;
}

class LRUCache<K,V> {
    private final int capacity;
    private final Map<K, Node<K,V>> map = new HashMap<>();
    private Node<K,V> head, tail;
    private final ReentrantLock lock = new ReentrantLock();
    public LRUCache(int capacity) { this.capacity = capacity; }
    public V get(K key) {
        lock.lock();
        try {
            Node<K,V> node = map.get(key);
            if (node == null) return null;
            moveToHead(node);
            return node.value;
        } finally { lock.unlock(); }
    }
    public void put(K key, V value) {
        lock.lock();
        try {
            Node<K,V> node = map.get(key);
            if (node != null) {
                node.value = value;
                moveToHead(node);
            } else {
                node = new Node<>();
                node.key = key; node.value = value;
                map.put(key, node);
                addToHead(node);
                if (map.size() > capacity) {
                    map.remove(tail.key);
                    removeTail();
                }
            }
        } finally { lock.unlock(); }
    }
    private void moveToHead(Node<K,V> node) {
        if (node == head) return;
        remove(node); addToHead(node);
    }
    private void addToHead(Node<K,V> node) {
        node.next = head; node.prev = null;
        if (head != null) head.prev = node;
        head = node;
        if (tail == null) tail = node;
    }
    private void remove(Node<K,V> node) {
        if (node.prev != null) node.prev.next = node.next;
        else head = node.next;
        if (node.next != null) node.next.prev = node.prev;
        else tail = node.prev;
    }
    private void removeTail() { remove(tail); }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class LRUCacheTest {
    @Test
    void testPutAndGet() {
        LRUCache<Integer, String> cache = new LRUCache<>(2);
        cache.put(1, "a");
        cache.put(2, "b");
        assertEquals("a", cache.get(1));
        cache.put(3, "c");
        assertNull(cache.get(2));
    }
}
```

---

### **7. Extensions and Edge Cases**
- Add TTL, write-back, and metrics.
- Support for distributed cache (e.g., Redis LRU).
