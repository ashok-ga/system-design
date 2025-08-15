# Parking Lot

This problem requires designing a multi-floor parking lot system with spot types, allocation strategies, and billing.

### **1. System Overview & Scope Clarification**

We are designing a backend service to manage parking lots, spot allocation, and ticketing.

**Functional Requirements (FR):**
- Park/unpark vehicle; find nearest suitable spot.
- Track tickets and calculate fees.
- Support multiple floors and spot types (compact, large, handicapped).

**Non-Functional Requirements (NFR):**
- Real-time allocation and release.
- Scalable to large lots (1000+ spots).
- Accurate billing and ticket tracking.

**Assumptions:**
- Each spot has a unique ID and type.
- Pricing is based on duration and spot type.
- In-memory store for demo; DB in production.

---

### **2. Core Components and Class Design**

- **ParkingLot:** Main class managing floors and allocation.
- **Floor:** Contains spots.
- **Spot:** Represents a parking spot.
- **Vehicle:** Represents a vehicle.
- **Allocator:** Strategy for finding spots.
- **Ticket:** Tracks parking session.
- **Billing:** Calculates fees.

**Class Diagram (Textual Representation):**

```
+-------------+
| ParkingLot  |
+-------------+
| + park()    |
| + unpark()  |
+-------------+
      ^
      |
+-------------+
|   Floor     |
+-------------+
| + spots     |
+-------------+
      ^
      |
+-------------+
|   Spot      |
+-------------+
| id, type    |
| isFree      |
+-------------+
```

---

### **3. API Design (`ParkingLot`)**

Java

```java
class ParkingLot {
    Ticket park(Vehicle v);
    void unpark(Ticket t);
}
```

---

### **4. Key Workflows**

**a) Park Vehicle**
1. Find nearest suitable free spot (by type).
2. Mark spot as occupied.
3. Issue ticket with entry time and spot info.

**b) Unpark Vehicle**
1. Validate ticket.
2. Mark spot as free.
3. Calculate fee based on duration and spot type.
4. Close ticket.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;

class Spot {
    String id;
    SpotType type;
    boolean isFree = true;
    // ...constructors, getters, setters...
}

enum SpotType { COMPACT, LARGE, HANDICAPPED }

enum VehicleType { CAR, TRUCK, BIKE }

class Vehicle {
    String id;
    VehicleType type;
    // ...constructors, getters, setters...
}

class Ticket {
    String id;
    String spotId;
    long entryTime;
    long exitTime;
    double fee;
    // ...constructors, getters, setters...
}

class Floor {
    List<Spot> spots;
    // ...constructors, methods...
}

class ParkingLot {
    List<Floor> floors;
    Map<String, Ticket> activeTickets = new HashMap<>();
    public Ticket park(Vehicle v) {
        for (Floor f : floors) {
            for (Spot s : f.spots) {
                if (s.isFree && isSuitable(s, v)) {
                    s.isFree = false;
                    Ticket t = new Ticket();
                    t.id = UUID.randomUUID().toString();
                    t.spotId = s.id;
                    t.entryTime = System.currentTimeMillis();
                    activeTickets.put(t.id, t);
                    return t;
                }
            }
        }
        throw new RuntimeException("No spot available");
    }
    public void unpark(Ticket t) {
        t.exitTime = System.currentTimeMillis();
        t.fee = Billing.calculate(t);
        for (Floor f : floors) {
            for (Spot s : f.spots) {
                if (s.id.equals(t.spotId)) {
                    s.isFree = true;
                }
            }
        }
        activeTickets.remove(t.id);
    }
    private boolean isSuitable(Spot s, Vehicle v) {
        // Logic for spot suitability
        return true;
    }
}

class Billing {
    static double calculate(Ticket t) {
        long duration = t.exitTime - t.entryTime;
        return Math.ceil(duration / 3600000.0) * 10.0; // $10/hr
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class ParkingLotTest {
    @Test
    void testParkAndUnpark() {
        // Setup lot, floor, spots, vehicle
        // Park, unpark, assert fee
    }
}
```

---

### **7. Extensions and Edge Cases**
- Add reservations, overflow handling, lost ticket recovery.
- Support for different pricing models.
- Real-time spot availability dashboard.
