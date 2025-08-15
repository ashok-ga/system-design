# Elevator Controller (N Elevators)

This problem requires designing a multi-elevator controller to efficiently schedule elevator cars and minimize wait times.

### **1. System Overview & Scope Clarification**

We are designing a backend service to manage N elevators in a building, handling hall and cab calls, and optimizing scheduling.

**Functional Requirements (FR):**
- Handle hall (up/down) and cab (floor) calls.
- Support multiple elevator states: IDLE, MOVING, DOOR_OPEN.
- Assign calls to elevators using a scheduling algorithm.
- Support group control and peak modes.

**Non-Functional Requirements (NFR):**
- Real-time responsiveness.
- Scalable to large buildings (10+ elevators, 100+ floors).
- Safety: door interlocks, overload protection.

**Assumptions:**
- Each elevator has a unique ID and state.
- All state is in-memory for demo; production would use distributed state.

---

### **2. Core Components and Class Design**

- **Elevator:** Represents an elevator car.
- **Scheduler:** Assigns calls to elevators.
- **Call:** Represents a hall or cab call.
- **ElevatorState:** Enum for IDLE, MOVING, DOOR_OPEN.

**Class Diagram (Textual Representation):**

```
+-----------+      +-----------+
| Elevator  |<-----| Scheduler |
+-----------+      +-----------+
| id        |      | assign()  |
| current   |      +-----------+
| direction |
| queue     |
| state     |
+-----------+
```

---

### **3. API Design (`Scheduler`)**

Java

```java
class Scheduler {
    void assign(Call call);
}
```

---

### **4. Key Workflows**

**a) Assign Call**
1. Receive call (hall/cab).
2. Find best elevator (nearest, least busy, etc.).
3. Add call to elevator's queue.
4. Update elevator state.

**b) Elevator Movement**
1. Elevator processes queue.
2. Moves to next floor, opens door, handles passengers.
3. Updates state.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;

enum ElevatorState { IDLE, MOVING, DOOR_OPEN }
enum Direction { UP, DOWN, NONE }

class Call {
    int floor;
    Direction direction;
    boolean isHallCall;
    // ...constructors, getters...
}

class Elevator {
    int id;
    int currentFloor;
    Direction direction = Direction.NONE;
    Queue<Integer> queue = new LinkedList<>();
    ElevatorState state = ElevatorState.IDLE;
    // ...constructors, methods...
}

class Scheduler {
    List<Elevator> elevators;
    public void assign(Call call) {
        // Find best elevator (nearest, idle, etc.)
        Elevator best = null;
        int minDist = Integer.MAX_VALUE;
        for (Elevator e : elevators) {
            int dist = Math.abs(e.currentFloor - call.floor);
            if (dist < minDist && (e.state == ElevatorState.IDLE || e.direction == call.direction)) {
                minDist = dist;
                best = e;
            }
        }
        if (best != null) best.queue.add(call.floor);
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class ElevatorControllerTest {
    @Test
    void testAssignCall() {
        // Setup elevators, scheduler, calls
        // Assign call, assert queue
    }
}
```

---

### **7. Extensions and Edge Cases**
- Add Look/SCAN algorithm for better scheduling.
- Handle peak/idle modes, group control.
- Add safety checks for doors, overload, etc.
