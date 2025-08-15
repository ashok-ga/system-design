# Design a Notification/Observer System

This problem requires designing a notification system using the Observer pattern, supporting multiple channels and subscribers.

### **1. System Overview & Scope Clarification**

We are designing a backend service to send notifications to users via multiple channels (email, SMS, push), supporting subscriptions and event-driven delivery.

**Functional Requirements (FR):**
- Subscribe/unsubscribe to topics/events.
- Notify all subscribers on event.
- Support multiple channels (email, SMS, push).
- Delivery guarantees (at-least-once).

**Non-Functional Requirements (NFR):**
- Low latency (real-time delivery).
- Scalable to millions of users/events.
- Extensible for new channels.

**Assumptions:**
- In-memory for demo; production uses message queues.

---

### **2. Core Components and Class Design**

- **NotificationService:** Main API for subscribe/notify.
- **Subscriber:** Interface for notification channels.
- **Event:** Represents an event/topic.

**Class Diagram (Textual Representation):**

```
+---------------------+
| NotificationService |
+---------------------+
| + subscribe()       |
| + unsubscribe()     |
| + notify()          |
+---------------------+
        ^
        |
+---------------------+
|   Subscriber        |
+---------------------+
| + notify()          |
+---------------------+
```

---

### **3. API Design (`NotificationService`)**

Java

```java
class NotificationService {
    void subscribe(String event, Subscriber s);
    void unsubscribe(String event, Subscriber s);
    void notify(String event, String message);
}
```

---

### **4. Key Workflows**

**a) Subscribe/Unsubscribe**
1. User subscribes/unsubscribes to event/topic.
2. Service updates subscriber list.

**b) Notify**
1. Event occurs; service notifies all subscribers.
2. Each subscriber receives message via their channel.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;

interface Subscriber {
    void notify(String message);
}

class NotificationService {
    private final Map<String, List<Subscriber>> subs = new HashMap<>();
    public void subscribe(String event, Subscriber s) {
        subs.computeIfAbsent(event, k -> new ArrayList<>()).add(s);
    }
    public void unsubscribe(String event, Subscriber s) {
        List<Subscriber> list = subs.get(event);
        if (list != null) list.remove(s);
    }
    public void notify(String event, String message) {
        List<Subscriber> list = subs.get(event);
        if (list != null) for (Subscriber s : list) s.notify(message);
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class NotificationServiceTest {
    @Test
    void testSubscribeAndNotify() {
        NotificationService svc = new NotificationService();
        List<String> received = new ArrayList<>();
        Subscriber s = received::add;
        svc.subscribe("event1", s);
        svc.notify("event1", "msg");
        assertEquals(List.of("msg"), received);
    }
}
```

---

### **7. Extensions and Edge Cases**
- Add message queues for reliability.
- Support for retries, dead-letter queues.
- Add filtering and batching.
