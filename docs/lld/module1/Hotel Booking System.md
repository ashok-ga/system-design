# Design a Hotel Booking System

This problem requires designing a scalable hotel booking system supporting room search, booking, and cancellation.

### **1. System Overview & Scope Clarification**

We are designing a backend service to manage hotels, rooms, availability, and reservations for users.

**Functional Requirements (FR):**
- Search hotels/rooms by location, date, and features.
- Book/cancel rooms.
- Track availability and prevent double-booking.
- Support for pricing, offers, and user accounts.

**Non-Functional Requirements (NFR):**
- Scalable to thousands of hotels and users.
- Consistent and reliable booking.
- Low latency for search and booking.

**Assumptions:**
- In-memory for demo; production uses DB and cache.

---

### **2. Core Components and Class Design**

- **HotelService:** Main API for search/book.
- **Hotel/Room:** Represents hotels and rooms.
- **Booking:** Represents a reservation.
- **User:** Represents users.

**Class Diagram (Textual Representation):**

```
+--------+      +-------+
| Hotel  |<-----| Room  |
+--------+      +-------+
| id     |      | id    |
| name   |      | type  |
| loc    |      | avail |
+--------+      +-------+
      ^             |
      |             v
+--------+      +---------+
|Booking |      |User     |
+--------+      +---------+
```

---

### **3. API Design (`HotelService`)**

Java

```java
class HotelService {
    List<Room> search(String location, long from, long to);
    Booking book(String userId, String roomId, long from, long to);
    void cancel(String bookingId);
}
```

---

### **4. Key Workflows**

**a) Search**
1. User searches for rooms by location and date.
2. Service filters available rooms.

**b) Book**
1. User books room; service checks availability and creates booking.
2. Updates room availability.

**c) Cancel**
1. User cancels booking; service updates availability.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;

class Hotel {
    String id;
    String name;
    String location;
    List<Room> rooms = new ArrayList<>();
}

class Room {
    String id;
    String type;
    List<Booking> bookings = new ArrayList<>();
}

class Booking {
    String id;
    String userId;
    String roomId;
    long from, to;
}

class HotelService {
    private final Map<String, Hotel> hotels = new HashMap<>();
    public List<Room> search(String location, long from, long to) {
        List<Room> availableRooms = new ArrayList<>();
        for (Hotel hotel : hotels.values()) {
            if (!hotel.location.equalsIgnoreCase(location)) continue;
            for (Room room : hotel.rooms) {
                boolean isAvailable = true;
                for (Booking booking : room.bookings) {
                    if (!(to <= booking.from || from >= booking.to)) {
                        isAvailable = false;
                        break;
                    }
                }
                if (isAvailable) availableRooms.add(room);
            }
        }
        return availableRooms;
    }
    public Booking book(String userId, String roomId, long from, long to) {
        for (Hotel hotel : hotels.values()) {
            for (Room room : hotel.rooms) {
                if (room.id.equals(roomId)) {
                    for (Booking booking : room.bookings) {
                        if (!(to <= booking.from || from >= booking.to)) {
                            return null; // Not available
                        }
                    }
                    Booking newBooking = new Booking();
                    newBooking.id = UUID.randomUUID().toString();
                    newBooking.userId = userId;
                    newBooking.roomId = roomId;
                    newBooking.from = from;
                    newBooking.to = to;
                    room.bookings.add(newBooking);
                    return newBooking;
                }
            }
        }
        return null;
    }
    public void cancel(String bookingId) {
        for (Hotel hotel : hotels.values()) {
            for (Room room : hotel.rooms) {
                Iterator<Booking> it = room.bookings.iterator();
                while (it.hasNext()) {
                    Booking booking = it.next();
                    if (booking.id.equals(bookingId)) {
                        it.remove();
                        return;
                    }
                }
            }
        }
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class HotelServiceTest {
    @Test
    void testBookAndCancel() {
        // Setup hotels, rooms, book/cancel, assert availability
    }
}
```

---

### **7. Extensions and Edge Cases**
- Add payment, offers, and loyalty programs.
- Handle overbooking, waitlists, and notifications.
- Integrate with third-party hotel APIs.
