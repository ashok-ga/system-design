# Design a Payment Wallet System

This problem requires designing a digital payment wallet supporting balance management, transfers, and transaction history.

### **1. System Overview & Scope Clarification**

We are designing a backend service to manage user balances, transfers, and transaction records securely.

**Functional Requirements (FR):**
- Add/withdraw funds.
- Transfer funds between users.
- Track transaction history.
- Support for refunds and reversals.

**Non-Functional Requirements (NFR):**
- Secure and auditable.
- Scalable to millions of users/transactions.
- Low latency for transfers.

**Assumptions:**
- In-memory for demo; production uses DB and payment gateway.

---

### **2. Core Components and Class Design**

- **WalletService:** Main API for wallet ops.
- **User/Wallet:** Represents users and balances.
- **Transaction:** Represents a transfer or operation.

**Class Diagram (Textual Representation):**

```
+--------+      +--------+
| User   |<-----| Wallet |
+--------+      +--------+
| id     |      | id     |
| name   |      | balance|
+--------+      +--------+
      ^
      |
+--------------+
|Transaction   |
+--------------+
| id, from, to |
| amount, ts   |
+--------------+
```

---

### **3. API Design (`WalletService`)**

Java

```java
class WalletService {
    void addFunds(String userId, double amount);
    void transfer(String fromUser, String toUser, double amount);
    List<Transaction> getHistory(String userId);
}
```

---

### **4. Key Workflows**

**a) Add/Withdraw Funds**
1. User adds/withdraws funds; service updates balance and records transaction.

**b) Transfer**
1. User transfers funds; service checks balance, updates both wallets, records transaction.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;

class Wallet {
    String id;
    double balance;
}

class Transaction {
    String id;
    String from, to;
    double amount;
    long ts;
}

class User {
    String id;
    String name;
    Wallet wallet = new Wallet();
    List<Transaction> history = new ArrayList<>();
}

class WalletService {
    private final Map<String, User> users = new HashMap<>();
    public void addFunds(String userId, double amount) {
        User user = users.computeIfAbsent(userId, k -> new User());
        user.wallet.id = userId;
        user.wallet.balance += amount;
        Transaction t = new Transaction();
        t.id = UUID.randomUUID().toString();
        t.from = "external";
        t.to = userId;
        t.amount = amount;
        t.ts = System.currentTimeMillis();
        user.history.add(t);
    }
    public void transfer(String fromUser, String toUser, double amount) {
        User from = users.get(fromUser);
        User to = users.get(toUser);
        if (from == null || to == null) throw new RuntimeException("User not found");
        if (from.wallet.balance < amount) throw new RuntimeException("Insufficient funds");
        from.wallet.balance -= amount;
        to.wallet.balance += amount;
        Transaction t = new Transaction();
        t.id = UUID.randomUUID().toString();
        t.from = fromUser;
        t.to = toUser;
        t.amount = amount;
        t.ts = System.currentTimeMillis();
        from.history.add(t);
        to.history.add(t);
    }
    public List<Transaction> getHistory(String userId) {
        User user = users.get(userId);
        if (user == null) return List.of();
        return user.history;
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class WalletServiceTest {
    @Test
    void testAddFundsAndTransfer() {
        // Setup users, add/transfer funds, assert balances
    }
}
```

---

### **7. Extensions and Edge Cases**
- Add fraud detection, KYC, and compliance.
- Support for multiple currencies and wallets.
- Integrate with payment gateways and banks.
