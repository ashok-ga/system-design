# Chat (1:1 + Typing + Read Receipts)

This problem requires designing a simple, in-memory chat service supporting 1:1 messaging, typing indicators, and read/delivery receipts.

### **1. System Overview & Scope Clarification**

We are designing a backend service for real-time chat between two users, with ephemeral state (no persistence required for this round).

**Functional Requirements (FR):**
- Send message between two users.
- Delivery and read receipts per message.
- Typing indicator (user is typing).
- Idempotent resend support.

**Non-Functional Requirements (NFR):**
- Low latency (real-time experience).
- In-memory only (stateless, for demo).
- Thread-safe for concurrent users.

**Assumptions:**
- All state is in-memory (e.g., for interview/demo).
- No authentication or persistence required.
- Each conversation is between two users.

---

### **2. Core Components and Class Design**

- **User:** Represents a chat user.
- **Conversation:** Holds participants and messages.
- **Message:** Represents a chat message and its state.
- **ChatService:** Main API for sending messages, typing, and receipts.
- **PresenceService:** Tracks typing/read status (in-memory).
- **Delivery:** Observer for delivery/read events.

**Class Diagram (Textual Representation):**

```
+-------------+      +--------------+
|   User      |      | Conversation |
+-------------+      +--------------+
| id, name    |      | id           |
+-------------+      | participants |
                     | messages     |
                     +--------------+
                            ^
                            |
                     +--------------+
                     |   Message    |
                     +--------------+
                     | id, text     |
                     | senderId     |
                     | ts           |
                     | deliveredTo  |
                     | readBy       |
                     +--------------+
```

---

### **3. API Design (`ChatService`)**

Java

```java
class ChatService {
    void sendMessage(String convId, String senderId, String text);
    void typing(String convId, String userId);
    void markDelivered(String convId, String msgId, String userId);
    void markRead(String convId, String msgId, String userId);
}
```

---

### **4. Key Workflows**

**a) Send Message**
1. User calls `sendMessage(convId, senderId, text)`.
2. Service creates a new Message, adds to Conversation.
3. Notifies recipient (observer pattern).

**b) Typing Indicator**
1. User calls `typing(convId, userId)`.
2. PresenceService updates typing state.
3. Notifies other participant.

**c) Delivery/Read Receipts**
1. Recipient client calls `markDelivered`/`markRead`.
2. Message state updated; sender notified.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

class User {
    String id;
    String name;
}

class Message {
    String id;
    String text;
    String senderId;
    long ts;
    Set<String> deliveredTo = new HashSet<>();
    Set<String> readBy = new HashSet<>();
    // ...constructors, getters, setters...
}

class Conversation {
    String id;
    List<User> participants = new ArrayList<>();
    List<Message> messages = new ArrayList<>();
}

class PresenceService {
    private final Map<String, Set<String>> typing = new ConcurrentHashMap<>();
    public void setTyping(String convId, String userId) {
        typing.computeIfAbsent(convId, k -> new HashSet<>()).add(userId);
    }
    public Set<String> getTyping(String convId) {
        return typing.getOrDefault(convId, Collections.emptySet());
    }
}

interface DeliveryObserver {
    void onDelivered(String convId, String msgId, String userId);
    void onRead(String convId, String msgId, String userId);
}

class ChatService {
    private final Map<String, Conversation> conversations = new ConcurrentHashMap<>();
    private final PresenceService presence = new PresenceService();
    private final List<DeliveryObserver> observers = new ArrayList<>();
    public void sendMessage(String convId, String senderId, String text) {
        Conversation conv = conversations.get(convId);
        if (conv == null) throw new RuntimeException("No conversation");
        Message msg = new Message();
        msg.id = UUID.randomUUID().toString();
        msg.text = text;
        msg.senderId = senderId;
        msg.ts = System.currentTimeMillis();
        conv.messages.add(msg);
        // Notify observers (delivery)
        for (DeliveryObserver o : observers) o.onDelivered(convId, msg.id, senderId);
    }
    public void typing(String convId, String userId) {
        presence.setTyping(convId, userId);
        // Notify other participant (not shown)
    }
    public void markDelivered(String convId, String msgId, String userId) {
        Conversation conv = conversations.get(convId);
        for (Message m : conv.messages) {
            if (m.id.equals(msgId)) m.deliveredTo.add(userId);
        }
        for (DeliveryObserver o : observers) o.onDelivered(convId, msgId, userId);
    }
    public void markRead(String convId, String msgId, String userId) {
        Conversation conv = conversations.get(convId);
        for (Message m : conv.messages) {
            if (m.id.equals(msgId)) m.readBy.add(userId);
        }
        for (DeliveryObserver o : observers) o.onRead(convId, msgId, userId);
    }
    public void addObserver(DeliveryObserver o) { observers.add(o); }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class ChatServiceTest {
    @Test
    void testSendAndDeliver() {
        // Setup users, conversation, service
        // Send message, mark delivered/read, assert state
    }
}
```

---

### **7. Extensions and Edge Cases**
- Add group chat, message ordering, and persistence.
- Handle duplicate message delivery (idempotency).
- Add authentication and security for production.
