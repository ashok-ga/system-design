# Splitwise-like Expense Splitter

This problem requires designing a group expense tracker that simplifies debts and supports various expense types.

### **1. System Overview & Scope Clarification**

We are designing a backend service to track group expenses, calculate balances, and minimize cash flows for settlements.

**Functional Requirements (FR):**
- Add expenses (equal, unequal, percent split).
- Track balances per user.
- Settle up and simplify debt graph.

**Non-Functional Requirements (NFR):**
- Accurate calculations (handle rounding).
- Scalable to large groups (100+ users).
- Support multiple currencies (optional).

**Assumptions:**
- All state is in-memory for demo.
- Each group has a unique ID and list of users.

---

### **2. Core Components and Class Design**

- **User:** Represents a group member.
- **Group:** Holds users and expenses.
- **Expense:** Represents an expense entry.
- **BalanceSheet:** Tracks net balances.
- **SettlementEngine:** Minimizes cash flows.

**Class Diagram (Textual Representation):**

```
+--------+      +-------+
| User   |<-----| Group |
+--------+      +-------+
| id     |      | users |
| name   |      | expenses
+--------+      +-------+
      ^             |
      |             v
+--------+      +-------------+
|Expense |      |BalanceSheet |
+--------+      +-------------+
```

---

### **3. API Design (`SettlementEngine`)**

Java

```java
class SettlementEngine {
    List<Settlement> simplify(BalanceSheet sheet);
}
```

---

### **4. Key Workflows**

**a) Add Expense**
1. User adds expense (amount, split type).
2. Update balances for all users.

**b) Settle Up**
1. Run min-cash-flow algorithm to minimize transactions.
2. Output list of settlements.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;

class User {
    String id;
    String name;
}

class Expense {
    String id;
    String paidBy;
    double amount;
    Map<String, Double> splits;
    // ...constructors, getters...
}

class Group {
    String id;
    List<User> users = new ArrayList<>();
    List<Expense> expenses = new ArrayList<>();
}

class BalanceSheet {
    Map<String, Double> balances = new HashMap<>();
}

class Settlement {
    String from;
    String to;
    double amount;
}

class SettlementEngine {
    public List<Settlement> simplify(BalanceSheet sheet) {
        // Min-cash-flow algorithm
        List<Settlement> result = new ArrayList<>();
        // ...algorithm...
        return result;
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class SplitwiseTest {
    @Test
    void testAddExpenseAndSettle() {
        // Setup group, users, add expenses, run settlement
    }
}
```

---

### **7. Extensions and Edge Cases**
- Handle multiple currencies, rounding errors.
- Add recurring expenses, group management.
- Support for audit/history of transactions.
