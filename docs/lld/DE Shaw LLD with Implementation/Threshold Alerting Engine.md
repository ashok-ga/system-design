# Threshold Alerting Engine

This problem requires designing a time-series alerting engine that triggers alerts based on threshold rules over rolling windows.

### **1. System Overview & Scope Clarification**

We are designing a backend service to evaluate time-series data and trigger alerts when rules are met.

**Functional Requirements (FR):**
- Define rules per metric (e.g., CPU > 90% for 5m).
- Evaluate conditions over rolling time windows.
- Suppress duplicate alerts (debounce).

**Non-Functional Requirements (NFR):**
- Low-latency evaluation.
- Scalable to thousands of metrics/rules.
- Reliable alert delivery (email/webhook).

**Assumptions:**
- All state is in-memory for demo.
- Each rule is for a single metric.

---

### **2. Core Components and Class Design**

- **Rule:** Represents a threshold rule.
- **Evaluator:** Evaluates rules over time windows.
- **Notifier:** Sends alerts.
- **Debounce:** Suppresses duplicate alerts.

**Class Diagram (Textual Representation):**

```
+--------+      +----------+
| Rule   |<-----|Evaluator |
+--------+      +----------+
| metric |      | rules    |
| pred   |      | window   |
| window |      +----------+
+--------+      | Notifier |
               +----------+
```

---

### **3. API Design (`Evaluator`)**

Java

```java
class Evaluator {
    void addRule(Rule rule);
    void onMetric(String metric, double value, long ts);
}
```

---

### **4. Key Workflows**

**a) Add Rule**
1. User defines rule (metric, predicate, window, duration).
2. Evaluator stores rule.

**b) On Metric**
1. Evaluator receives metric value.
2. Updates rolling window.
3. Checks if rule is met for window.
4. If so, triggers alert (debounced).

---

### **5. Code Implementation (Java)**

```java
import java.util.*;
import java.util.function.Predicate;

class Rule {
    String metric;
    Predicate<Double> predicate;
    long window;
    long duration;
}

class Evaluator {
    Map<String, Rule> rules = new HashMap<>();
    Map<String, Deque<DataPoint>> windows = new HashMap<>();
    Notifier notifier = new Notifier();
    Map<String, Long> lastAlert = new HashMap<>();
    public void addRule(Rule rule) { rules.put(rule.metric, rule); }
    public void onMetric(String metric, double value, long ts) {
        Rule rule = rules.get(metric);
        if (rule == null) return;
        windows.computeIfAbsent(metric, k -> new ArrayDeque<>()).addLast(new DataPoint(ts, value));
        // Remove old points
        while (!windows.get(metric).isEmpty() && ts - windows.get(metric).peekFirst().ts > rule.window) {
            windows.get(metric).pollFirst();
        }
        // Check predicate
        boolean triggered = windows.get(metric).stream().allMatch(dp -> rule.predicate.test(dp.value));
        if (triggered && shouldAlert(metric, ts, rule)) {
            notifier.notify("Alert for " + metric);
            lastAlert.put(metric, ts);
        }
    }
    private boolean shouldAlert(String metric, long ts, Rule rule) {
        return !lastAlert.containsKey(metric) || ts - lastAlert.get(metric) > rule.duration;
    }
}

class DataPoint {
    long ts;
    double value;
    DataPoint(long ts, double value) { this.ts = ts; this.value = value; }
}

class Notifier {
    public void notify(String alert) {
        // Send email/webhook
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class ThresholdAlertingEngineTest {
    @Test
    void testAlertTrigger() {
        // Setup rule, evaluator, send metrics, assert alert
    }
}
```

---

### **7. Extensions and Edge Cases**
- Add support for multiple predicates, composite rules.
- Integrate with persistent storage and distributed evaluation.
- Add alert suppression and escalation policies.
