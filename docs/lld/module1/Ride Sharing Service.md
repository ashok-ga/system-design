# Design a Ride-Sharing Matching Service (Uber)

This problem requires designing a real-time ride-matching service for a ride-sharing platform like Uber or Lyft.

### **1. System Overview & Scope Clarification**

We are designing a backend service to match riders and drivers in real time, supporting surge pricing and location-based matching.

**Functional Requirements (FR):**
- Register drivers/riders and update locations.
- Match riders to nearest available drivers.
- Support surge pricing and cancellations.
- Track trip state (requested, accepted, completed).

**Non-Functional Requirements (NFR):**
- Low latency (real-time matching).
- Scalable to millions of users.
- Fault-tolerant and highly available.

**Assumptions:**
- In-memory for demo; production uses distributed DB and geospatial index.

---

### **2. Core Components and Class Design**

- **RideService:** Main API for matching.
- **Driver/Rider:** Represents users.
- **Trip:** Represents a ride.
- **Location:** Geospatial data.
- **MatchingEngine:** Finds nearest driver.

**Class Diagram (Textual Representation):**

```
+-----------+      +--------+
| Driver    |      | Rider  |
+-----------+      +--------+
| id, loc   |      | id, loc|
+-----------+      +--------+
      ^
      |
+-----------+
| Matching  |
|  Engine   |
+-----------+
| + match() |
+-----------+
```

---

### **3. API Design (`RideService`)**

Java

```java
class RideService {
    void registerDriver(String id, Location loc);
    void registerRider(String id, Location loc);
    Trip requestRide(String riderId, Location dest);
    void updateLocation(String id, Location loc);
}
```

---

### **4. Key Workflows**

**a) Request Ride**
1. Rider requests ride; service finds nearest driver.
2. Assigns trip, updates state.

**b) Update Location**
1. Driver/rider updates location; service updates index.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;

class Location {
    double lat, lon;
}

class Driver {
    String id;
    Location loc;
    boolean available = true;
}

class Rider {
    String id;
    Location loc;
}

class Trip {
    String id;
    String driverId, riderId;
    Location from, to;
    String state;
}

class RideService {
    private final Map<String, Driver> drivers = new HashMap<>();
    private final Map<String, Rider> riders = new HashMap<>();
    public void registerDriver(String id, Location loc) {
        Driver d = new Driver();
        d.id = id; d.loc = loc; d.available = true;
        drivers.put(id, d);
    }
    public void registerRider(String id, Location loc) {
        Rider r = new Rider();
        r.id = id; r.loc = loc;
        riders.put(id, r);
    }
    public Trip requestRide(String riderId, Location dest) {
        Rider rider = riders.get(riderId);
        if (rider == null) return null;
        Driver nearest = null;
        double minDist = Double.MAX_VALUE;
        for (Driver d : drivers.values()) {
            if (!d.available) continue;
            double dist = Math.hypot(d.loc.lat - rider.loc.lat, d.loc.lon - rider.loc.lon);
            if (dist < minDist) {
                minDist = dist;
                nearest = d;
            }
        }
        if (nearest == null) return null;
        nearest.available = false;
        Trip trip = new Trip();
        trip.id = UUID.randomUUID().toString();
        trip.driverId = nearest.id;
        trip.riderId = riderId;
        trip.from = rider.loc;
        trip.to = dest;
        trip.state = "requested";
        return trip;
    }
    public void updateLocation(String id, Location loc) {
        if (drivers.containsKey(id)) drivers.get(id).loc = loc;
        if (riders.containsKey(id)) riders.get(id).loc = loc;
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class RideServiceTest {
    @Test
    void testRequestRide() {
        // Setup drivers/riders, request ride, assert trip
    }
}
```

---

### **7. Extensions and Edge Cases**
- Add geospatial index (e.g., k-d tree, R-tree).
- Handle surge pricing, cancellations, and no-shows.
- Add trip history and analytics.
