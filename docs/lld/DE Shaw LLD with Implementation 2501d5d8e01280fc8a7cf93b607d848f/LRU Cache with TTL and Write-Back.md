# LRU Cache with TTL and Write-Back

This problem requires designing a high-performance, thread-safe, in-memory cache that evicts items based on a Least Recently Used (LRU) policy, supports Time-To-Live (TTL) expiration, and provides an optional, asynchronous write-back mechanism to a backing store.

### **1. System Overview & Scope Clarification**

We are building a generic, in-memory key-value cache. It's a fundamental component in many systems for reducing latency and load on slower backend services like databases.

**Functional Requirements (FR):**

- **`get(key)`:** Retrieve a value. If the item has expired, it should be treated as a miss.
- **`put(key, value, ttl)`:** Insert or update a key-value pair with an optional TTL.
- **`delete(key)`:** Explicitly remove an item from the cache.
- **LRU Eviction:** When the cache reaches its capacity, the least recently used item must be removed to make space.
- **TTL Expiration:** Items with a TTL should become inaccessible after the duration has passed. Expiration should be checked lazily on access.
- **Write-Back Caching:** When a "dirty" item (one that has been `put` or modified) is evicted or deleted, it should be asynchronously written to a persistent backing store.

**Non-Functional Requirements (NFR):**

- **Performance:** `get` and `put` operations should be O(1) on average.
- **Thread-Safety:** The cache must be safe to use from multiple concurrent threads.

**Assumptions:**

- The `BackingStore` (e.g., a database client) will be provided via an interface.
- The cache will handle its own background thread management for the write-back process.
- We will use a "write-through" approach conceptually, where a `put` makes an entry "dirty," and the write to the backing store is deferred until eviction.

---

### **2. Core Components and Class Design**

The classic implementation for an LRU cache uses a combination of a `HashMap` for fast O(1) lookups and a doubly linked list to maintain the O(1) ordering of items by recency.

- **`LRUCacheWithWriteBack<K, V>`:** The main public class. It encapsulates all logic, including the data structures, locking, and the write-back worker.
- **`Node<K, V>`:** A private inner class representing an entry in the cache. It holds the key, value, expiration time, a `dirty` flag for the write-back logic, and pointers (`prev`, `next`) for the doubly linked list.
- **`BackingStore<K, V>`:** An interface that the user of our cache must implement. This decouples the cache from any specific database or storage technology. It will have a `write(key, value)` and `delete(key)` method.
- **Write-Back Mechanism:** This will be implemented using a `java.util.concurrent.BlockingQueue` to hold evicted dirty nodes and a dedicated `ExecutorService` (a single background thread) to consume from the queue and interact with the `BackingStore`.

**Class Diagram (Textual Representation):**

`+--------------------------------+
|  LRUCacheWithWriteBack<K, V>   |
|--------------------------------|
| - capacity: int                |
| - lock: ReentrantLock          |
| - map: HashMap<K, Node<K, V>>  |
| - head, tail: Node<K, V>       |
| - backingStore: BackingStore   |
| - writeBackQueue: BlockingQueue|
| - writerExecutor: ExecutorSvc  |
|--------------------------------|
| + get(key): V                  |
| + put(key, value, ttl, unit)   |
| + delete(key): void            |
| + shutdown(): void             |
+--------------------------------+
          |
          | contains
          v
+--------------------------------+
|      <<private inner>>         |
|         Node<K, V>             |
|--------------------------------|
| - key: K                       |
| - value: V                     |
| - expireAtNanos: long          |
| - dirty: boolean               |
| - prev, next: Node<K, V>       |
+--------------------------------+
          |
          | uses
          v
+-----------------------------+
|      <<interface>>          |
|     BackingStore<K, V>      |
|-----------------------------|
| + write(key, value): void   |
| + delete(key): void         |
+-----------------------------+`

---

### **3. API Design (`LRUCacheWithWriteBack`)**

Java

`public class LRUCacheWithWriteBack<K, V> {
    
    // Constructor to initialize capacity and backing store.
    public LRUCacheWithWriteBack(int capacity, BackingStore<K, V> backingStore);

    // Get a value from the cache. Returns null if not found or expired.
    public V get(K key);

    // Put a value with a specific TTL. Marks the entry as dirty for write-back.
    public void put(K key, V value, long ttl, TimeUnit unit);

    // Put a value with no expiration.
    public void put(K key, V value);

    // Remove a value from the cache. If the item was dirty, it's queued for deletion from the backing store.
    public void delete(K key);

    // Shuts down the write-back worker thread gracefully.
    public void shutdown();
}`

---

### **4. Key Workflows**

**a) `get(key)` Workflow**

1. Acquire the global `ReentrantLock`.
2. Look up the `Node` in the `HashMap`. If not found, release the lock and return `null`.
3. Check if the node is expired (`System.nanoTime() > node.expireAtNanos`).
    - If expired, call a private `removeNode()` helper. This helper will remove it from the list and map. **Crucially, expired items are NOT written back as their data is considered stale.**
    - Release lock and return `null`.
4. If the node is valid, move it to the front of the doubly linked list (marking it as most recently used).
5. Release the lock and return the node's value.

**b) `put(key, value, ttl)` Workflow**

1. Acquire the global `ReentrantLock`.
2. Check if the key already exists in the `HashMap`.
    - **If it exists:** Update the node's value, set its `dirty` flag to `true`, update its `expireAtNanos`, and move it to the front of the list.
    - **If it's new:**
    a. Check if the cache is at capacity (`map.size() >= capacity`).
    b. If so, evict the LRU item (the node just before `tail`). Call `removeNode()` on it.
    c. Inside `removeNode()`, if the evicted node was `dirty`, add it to the `writeBackQueue`.
    d. Create a new `Node` with the key, value, expiration, and `dirty = true`.
    e. Add the new node to the `HashMap` and insert it at the front of the list.
3. Release the lock.

**c) Write-Back Worker (Background Thread)**

1. The worker thread runs in a loop, calling `writeBackQueue.take()`. This call blocks until an item is available.
2. When a `Node` is dequeued, the worker calls the appropriate `BackingStore` method. We can add a special marker for deletion vs. update. A simple way is to check if the `value` is null.
3. It calls `backingStore.write(node.key, node.value)` or `backingStore.delete(node.key)`.
4. This loop is wrapped in a `try-catch` block to handle exceptions from the `BackingStore` (e.g., database connection issues), allowing the worker to log the error and continue processing other items. A retry mechanism could be added here.

---

### **5. Code Implementation (Java)**

Java

```cpp
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.*;
import java.util.concurrent.locks.ReentrantLock;

public class LRUCacheWithWriteBack<K, V> {

    // Interface for the backing store
    public interface BackingStore<K, V> {
        void write(K key, V value);
        void delete(K key);
    }

    private static class Node<K, V> {
        final K key;
        V value;
        long expireAtNanos;
        boolean dirty;
        Node<K, V> prev, next;

        Node(K key, V value, long expireAtNanos) {
            this.key = key;
            this.value = value;
            this.expireAtNanos = expireAtNanos;
            this.dirty = false;
        }
    }

    private final int capacity;
    private final BackingStore<K, V> backingStore;
    private final Map<K, Node<K, V>> map;
    private final Node<K, V> head, tail;
    private final ReentrantLock lock = new ReentrantLock();

    private final BlockingQueue<Node<K, V>> writeBackQueue;
    private final ExecutorService writerExecutor;
    private static final Node DELETED_MARKER = new Node<>(null, null, 0);

    public LRUCacheWithWriteBack(int capacity, BackingStore<K, V> backingStore) {
        this.capacity = capacity;
        this.backingStore = backingStore;
        this.map = new HashMap<>(capacity);
        this.head = new Node<>(null, null, 0);
        this.tail = new Node<>(null, null, 0);
        head.next = tail;
        tail.prev = head;

        if (backingStore != null) {
            this.writeBackQueue = new LinkedBlockingQueue<>();
            this.writerExecutor = Executors.newSingleThreadExecutor(r -> {
                Thread t = new Thread(r, "cache-writer-thread");
                t.setDaemon(true);
                return t;
            });
            this.writerExecutor.submit(this::writeBackProcessor);
        } else {
            this.writeBackQueue = null;
            this.writerExecutor = null;
        }
    }

    public V get(K key) {
        lock.lock();
        try {
            Node<K, V> node = map.get(key);
            if (node == null) {
                return null; // Cache miss
            }
            if (isExpired(node)) {
                removeNode(node); // Lazy expiration
                // Expired nodes are NOT written back
                return null;
            }
            moveToFront(node);
            return node.value;
        } finally {
            lock.unlock();
        }
    }

    public void put(K key, V value, long ttl, TimeUnit unit) {
        long expireAtNanos = (ttl > 0) ? System.nanoTime() + unit.toNanos(ttl) : -1L;
        lock.lock();
        try {
            Node<K, V> node = map.get(key);
            if (node != null) { // Update existing node
                node.value = value;
                node.expireAtNanos = expireAtNanos;
                node.dirty = true;
                moveToFront(node);
            } else { // Add new node
                if (map.size() >= capacity) {
                    evictLru();
                }
                Node<K, V> newNode = new Node<>(key, value, expireAtNanos);
                newNode.dirty = true;
                map.put(key, newNode);
                addToFront(newNode);
            }
        } finally {
            lock.unlock();
        }
    }
    
    public void put(K key, V value) {
        put(key, value, -1, TimeUnit.SECONDS);
    }
    
    public void delete(K key) {
        lock.lock();
        try {
            Node<K, V> node = map.remove(key);
            if (node != null) {
                removeNode(node);
                if (backingStore != null && node.dirty) {
                    // Create a special marker for deletion
                     Node<K, V> deleteMarker = new Node<>(node.key, null, 0);
                    writeBackQueue.offer(deleteMarker);
                }
            }
        } finally {
            lock.unlock();
        }
    }
    
    public void shutdown() {
        if (writerExecutor != null) {
            writerExecutor.shutdown();
            try {
                if (!writerExecutor.awaitTermination(5, TimeUnit.SECONDS)) {
                    writerExecutor.shutdownNow();
                }
            } catch (InterruptedException e) {
                writerExecutor.shutdownNow();
            }
        }
    }

    // --- Private helper methods ---

    private void evictLru() {
        Node<K, V> lruNode = tail.prev;
        if (lruNode != head) {
            removeNode(lruNode);
            map.remove(lruNode.key);
            if (backingStore != null && lruNode.dirty) {
                writeBackQueue.offer(lruNode);
            }
        }
    }
    
    private void writeBackProcessor() {
        while (!Thread.currentThread().isInterrupted()) {
            try {
                Node<K, V> node = writeBackQueue.take();
                if (node.value == null) { // This is our deletion marker
                    backingStore.delete(node.key);
                } else {
                    backingStore.write(node.key, node.value);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            } catch (Exception e) {
                // Log exception from backing store
                System.err.println("Error writing back to store: " + e.getMessage());
            }
        }
    }

    private boolean isExpired(Node<K, V> node) {
        return node.expireAtNanos > 0 && System.nanoTime() > node.expireAtNanos;
    }

    private void moveToFront(Node<K, V> node) {
        removeNode(node);
        addToFront(node);
    }

    private void removeNode(Node<K, V> node) {
        node.prev.next = node.next;
        node.next.prev = node.prev;
    }

    private void addToFront(Node<K, V> node) {
        node.next = head.next;
        node.prev = head;
        head.next.prev = node;
        head.next = node;
    }
}
```

---

### **6. Testing (JUnit 5)**

We'll use a mock `BackingStore` to verify the write-back logic.

Java

```cpp
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

class LRUCacheWithWriteBackTest {

    // A mock backing store for testing
    static class MockBackingStore implements LRUCacheWithWriteBack.BackingStore<String, String> {
        final Map<String, String> store = new ConcurrentHashMap<>();
        @Override public void write(String key, String value) { store.put(key, value); }
        @Override public void delete(String key) { store.remove(key); }
    }
    
    private LRUCacheWithWriteBack<String, String> cache;
    private MockBackingStore mockStore;

    @BeforeEach
    void setUp() {
        mockStore = new MockBackingStore();
        cache = new LRUCacheWithWriteBack<>(3, mockStore);
    }
    
    @AfterEach
    void tearDown() {
        cache.shutdown();
    }

    @Test
    void testBasicGetAndPut() {
        cache.put("k1", "v1");
        assertEquals("v1", cache.get("k1"));
        assertNull(cache.get("k2"));
    }

    @Test
    void testLruEviction() {
        cache.put("k1", "v1");
        cache.put("k2", "v2");
        cache.put("k3", "v3");
        cache.get("k1"); // k1 is now most recent
        cache.put("k4", "v4"); // k2 should be evicted
        
        assertNull(cache.get("k2"));
        assertNotNull(cache.get("k1"));
        assertNotNull(cache.get("k3"));
        assertNotNull(cache.get("k4"));
    }

    @Test
    void testTtlExpiration() throws InterruptedException {
        cache.put("k1", "v1", 100, TimeUnit.MILLISECONDS);
        assertNotNull(cache.get("k1"));
        Thread.sleep(150);
        assertNull(cache.get("k1")); // Should be expired
    }
    
    @Test
    void testWriteBackOnEviction() throws InterruptedException {
        cache.put("k1", "v1");
        cache.put("k2", "v2");
        cache.put("k3", "v3");
        cache.put("k4", "v4"); // Evicts k1

        // Give the writer thread a moment to process
        Thread.sleep(50); 
        
        assertEquals("v1", mockStore.store.get("k1"));
        assertNull(mockStore.store.get("k4")); // k4 is in cache, not written back yet
    }

    @Test
    void testNoWriteBackForCleanOrExpiredItems() throws InterruptedException {
        cache.put("k1", "v1", 50, TimeUnit.MILLISECONDS);
        Thread.sleep(100);
        cache.get("k1"); // Triggers lazy expiration
        
        cache.put("k2", "v2");
        cache.put("k3", "v3");
        cache.put("k4", "v4"); // Evicts k2
        
        Thread.sleep(50);
        
        assertNull(mockStore.store.get("k1")); // Expired items are not written
    }
    
    @Test
    void testWriteBackOnDelete() throws InterruptedException {
        cache.put("k1", "v1");
        cache.delete("k1");
        
        Thread.sleep(50);
        
        assertNull(cache.get("k1"));
        assertFalse(mockStore.store.containsKey("k1")); // Should be deleted from backing store
    }
}
```

---

### **7. Concurrency, Performance, and Extensions**

- **Concurrency:** The use of a single `ReentrantLock` makes the design simple and correct, but it serializes all access. For highly concurrent workloads with many CPU cores, this could become a bottleneck. A more advanced design might use **segmented locking**, where the cache is divided into several segments, each with its own lock, similar to how `ConcurrentHashMap` works. This increases complexity but improves throughput.
- **Performance:** All core operations (`get`, `put`, `delete`) are O(1) because they rely on `HashMap` lookups and simple pointer manipulations in the doubly linked list, all of which are constant time operations. The write-back mechanism operates on a separate thread, so it doesn't add latency to the cache operations themselves.
- **Extensions:**
    - **Proactive Expiration:** A dedicated "sweeper" thread could periodically scan the cache to remove expired items. This prevents the cache from holding onto a large number of expired-but-never-accessed items, which would otherwise waste memory.
    - **Read-Through Cache:** The `get` method could be extended. If an item is not in the cache (a miss), the cache could then try to load it from the `BackingStore`, insert it into the cache, and then return it to the caller.
    - **Cache Statistics:** The cache could be instrumented to expose metrics like hit rate, miss rate, eviction count, and the current size of the write-back queue. This is invaluable for monitoring and tuning performance.
    - **Graceful Shutdown:** The `shutdown()` method is essential to ensure that on application exit, any pending writes in the queue are flushed to the backing store, preventing data loss.