# Design a Calendar/Meeting Scheduler

This problem requires designing a calendar/meeting scheduler supporting event creation, conflict checks, and recurring events.

### **1. System Overview & Scope Clarification**

We are designing a backend service to manage user calendars, events, and meeting scheduling with conflict detection.

**Functional Requirements (FR):**
- Create, update, delete events.
- Check for conflicts and suggest free slots.
- Support recurring and group events.

**Non-Functional Requirements (NFR):**
- Scalable to millions of users/events.
- Low latency for scheduling and search.

**Assumptions:**
- In-memory for demo; production uses DB and cache.

---

### **2. Core Components and Class Design**

- **CalendarService:** Main API for event ops.
- **User/Event:** Represents users and events.
- **Interval:** Time interval for events.

**Class Diagram (Textual Representation):**

```
+--------+      +--------+
| User   |<-----| Event  |
+--------+      +--------+
| id     |      | id     |
| name   |      | interval|
+--------+      | users  |
               +--------+
      ^
      |
+--------------+
|CalendarService|
+--------------+
```

---

### **3. API Design (`CalendarService`)**

Java

```java
class CalendarService {
    void createEvent(String userId, Interval interval, List<String> users);
    List<Interval> getFreeSlots(String userId, long day);
    void deleteEvent(String eventId);
}
```

---

### **4. Key Workflows**

**a) Create Event**
1. User creates event; service checks for conflicts.
2. Adds event to calendars.

**b) Get Free Slots**
1. Service finds gaps in user's calendar for a day.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;

class Interval {
    long start, end;
}

class Event {
    String id;
    Interval interval;
    List<String> users = new ArrayList<>();
}

class User {
    String id;
    String name;
    List<Event> events = new ArrayList<>();
}

class CalendarService {
    private final Map<String, User> users = new HashMap<>();
    public void createEvent(String userId, Interval interval, List<String> usersList) {
        User user = users.computeIfAbsent(userId, k -> new User());
        for (Event e : user.events) {
            if (!(interval.end <= e.interval.start || interval.start >= e.interval.end)) {
                throw new RuntimeException("Conflict");
            }
        }
        Event event = new Event();
        event.id = UUID.randomUUID().toString();
        event.interval = interval;
        event.users = usersList;
        user.events.add(event);
    }
    public List<Interval> getFreeSlots(String userId, long day) {
        User user = users.get(userId);
        if (user == null) return List.of();
        List<Interval> busy = new ArrayList<>();
        for (Event e : user.events) {
            if (e.interval.start/86400000 == day/86400000) busy.add(e.interval);
        }
        busy.sort(Comparator.comparingLong(i -> i.start));
        List<Interval> free = new ArrayList<>();
        long prev = day;
        for (Interval i : busy) {
            if (i.start > prev) free.add(new Interval(){ {start=prev; end=i.start;} });
            prev = i.end;
        }
        if (prev < day+86400000) free.add(new Interval(){ {start=prev; end=day+86400000;} });
        return free;
    }
    public void deleteEvent(String eventId) {
        for (User user : users.values()) {
            user.events.removeIf(e -> e.id.equals(eventId));
        }
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class CalendarServiceTest {
    @Test
    void testCreateAndDeleteEvent() {
        // Setup users, create/delete event, assert conflicts
    }
}
```

---

### **7. Extensions and Edge Cases**
- Add notifications, reminders, and recurring events.
- Support for time zones and shared calendars.
- Integrate with external calendar APIs.
