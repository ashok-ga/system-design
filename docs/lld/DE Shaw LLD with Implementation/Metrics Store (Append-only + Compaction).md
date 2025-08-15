# Metrics Store (Append-only + Compaction)

This problem requires designing an in-process time-series metrics store with append-only writes and periodic compaction.

### **1. System Overview & Scope Clarification**

We are designing a backend service to store, fetch, and compact time-series metrics efficiently.

**Functional Requirements (FR):**
- `put(metric, ts, value)`: Write a data point.
- `rangeQuery(metric, from, to)`: Fetch data points in a range.
- Compaction: Downsample older data (e.g., 1s → 1m).

**Non-Functional Requirements (NFR):**
- High write throughput.
- Efficient range queries.
- Scalable to millions of points.

**Assumptions:**
- All state is in-memory for demo.
- Compaction runs periodically.

---

### **2. Core Components and Class Design**

- **Segment:** Append-only log of data points.
- **Index:** Maps metric to segments.
- **Compactor:** Merges/rolls up old data.
- **MetricsStore:** Main API for put/query.

**Class Diagram (Textual Representation):**

```
+-----------+      +-----------+
| Segment   |<-----| Index     |
+-----------+      +-----------+
| points    |      | metricMap |
+-----------+      +-----------+
      ^
      |
+-----------+
|Compactor  |
+-----------+
```

---

### **3. API Design (`MetricsStore`)**

Java

```java
class MetricsStore {
    void put(String metric, long ts, double value);
    List<DataPoint> rangeQuery(String metric, long from, long to);
}
```

---

### **4. Key Workflows**

**a) Put Data Point**
1. Append data point to segment for metric.
2. Update index.

**b) Range Query**
1. Fetch segments for metric.
2. Merge raw and compacted data.

**c) Compaction**
1. Periodically merge old data into downsampled segments.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;

class DataPoint {
    long ts;
    double value;
    DataPoint(long ts, double value) { this.ts = ts; this.value = value; }
}

class Segment {
    List<DataPoint> points = new ArrayList<>();
}

class Index {
    Map<String, List<Segment>> metricMap = new HashMap<>();
}

class Compactor {
    void compact(List<Segment> segments) {
        // Downsample logic (not implemented)
    }
}

class MetricsStore {
    Index index = new Index();
    public void put(String metric, long ts, double value) {
        List<Segment> segs = index.metricMap.computeIfAbsent(metric, k -> new ArrayList<>());
        if (segs.isEmpty()) segs.add(new Segment());
        segs.get(segs.size()-1).points.add(new DataPoint(ts, value));
    }
    public List<DataPoint> rangeQuery(String metric, long from, long to) {
        List<DataPoint> result = new ArrayList<>();
        List<Segment> segs = index.metricMap.getOrDefault(metric, List.of());
        for (Segment s : segs) {
            for (DataPoint dp : s.points) {
                if (dp.ts >= from && dp.ts <= to) result.add(dp);
            }
        }
        return result;
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class MetricsStoreTest {
    @Test
    void testPutAndQuery() {
        MetricsStore store = new MetricsStore();
        store.put("cpu", 1, 0.5);
        store.put("cpu", 2, 0.6);
        List<DataPoint> points = store.rangeQuery("cpu", 1, 2);
        assertEquals(2, points.size());
    }
}
```

---

### **7. Extensions and Edge Cases**
- Add persistent storage, WAL, and sharding.
- Support for tags, labels, and advanced queries.
- Implement compaction and retention policies.
