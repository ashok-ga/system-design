# Meeting Room Scheduler

This problem requires designing a meeting room booking system that avoids conflicts and supports search by capacity/resources.

### **1. System Overview & Scope Clarification**

We are designing a backend service to manage meeting rooms, bookings, and search for available slots.

**Functional Requirements (FR):**
- Create rooms with capacity and features.
- Book/cancel meetings.
- Search for free slots.
- Support recurring bookings.

**Non-Functional Requirements (NFR):**
- Conflict-free booking (no double-booking).
- Scalable to large offices (100+ rooms).
- Efficient search and conflict detection.

**Assumptions:**
- All state is in-memory for demo.
- Each room has a unique ID and features.

---

### **2. Core Components and Class Design**

- **Room:** Represents a meeting room.
- **Booking:** Represents a booking entry.
- **Scheduler:** Manages bookings and conflict checks.
- **Interval:** Represents a time interval.

**Class Diagram (Textual Representation):**

```
+--------+      +---------+
| Room   |<-----| Booking |
+--------+      +---------+
| id     |      | roomId  |
| cap    |      | interval|
| features|     | user    |
+--------+      +---------+
      ^
      |
+---------+
|Scheduler|
+---------+
```

---

### **3. API Design (`Scheduler`)**

Java

```java
class Scheduler {
    boolean book(String roomId, Interval interval, String user);
    void cancel(String bookingId);
    List<Interval> search(String roomId, ...);
}
```

---

### **4. Key Workflows**

**a) Book Room**
1. User calls `book(roomId, interval, user)`.
2. Scheduler checks for conflicts.
3. If free, creates booking.

**b) Search Free Slots**
1. User calls `search(roomId, ...)`.
2. Scheduler returns available intervals.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;

class Interval {
    long start;
    long end;
    // ...constructors, getters...
}

class Room {
    String id;
    int capacity;
    Set<String> features = new HashSet<>();
}

class Booking {
    String id;
    String roomId;
    Interval interval;
    String user;
}

class Scheduler {
    Map<String, List<Booking>> bookings = new HashMap<>();
    public boolean book(String roomId, Interval interval, String user) {
        List<Booking> roomBookings = bookings.getOrDefault(roomId, new ArrayList<>());
        for (Booking b : roomBookings) {
            if (overlaps(b.interval, interval)) return false;
        }
        Booking booking = new Booking();
        booking.id = UUID.randomUUID().toString();
        booking.roomId = roomId;
        booking.interval = interval;
        booking.user = user;
        roomBookings.add(booking);
        bookings.put(roomId, roomBookings);
        return true;
    }
    public void cancel(String bookingId) {
        for (List<Booking> roomBookings : bookings.values()) {
            roomBookings.removeIf(b -> b.id.equals(bookingId));
        }
    }
    public List<Interval> search(String roomId) {
        // Return free intervals (not implemented)
        return new ArrayList<>();
    }
    private boolean overlaps(Interval a, Interval b) {
        return a.start < b.end && b.start < a.end;
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class MeetingRoomSchedulerTest {
    @Test
    void testBookAndCancel() {
        // Setup rooms, scheduler, book/cancel, assert conflicts
    }
}
```

---

### **7. Extensions and Edge Cases**
- Add buffer times, recurring bookings, and advanced search.
- Handle overlapping/adjacent intervals.
- Add permissions and notifications.
