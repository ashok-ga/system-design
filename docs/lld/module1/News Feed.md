# Design a News Feed System (Facebook/Twitter)

This problem requires designing a scalable news feed system for a social network.

### **1. System Overview & Scope Clarification**

We are designing a backend service to generate personalized news feeds for users, supporting ranking and filtering.

**Functional Requirements (FR):**
- Post, like, comment, and follow users.
- Generate personalized feed per user.
- Support ranking, filtering, and pagination.

**Non-Functional Requirements (NFR):**
- Scalable to millions of users/posts.
- Low latency feed generation.
- Extensible for new features.

**Assumptions:**
- In-memory for demo; production uses DB and cache.

---

### **2. Core Components and Class Design**

- **FeedService:** Main API for feed ops.
- **User/Post:** Represents users and posts.
- **Feed:** List of posts per user.
- **RankingEngine:** Ranks posts.

**Class Diagram (Textual Representation):**

```
+-----------+      +--------+
| User      |      | Post   |
+-----------+      +--------+
| id, name  |      | id, ...|
+-----------+      +--------+
      ^
      |
+-----------+
| Feed      |
| Service   |
+-----------+
| + getFeed()|
+-----------+
```

---

### **3. API Design (`FeedService`)**

Java

```java
class FeedService {
    void post(String userId, String content);
    List<Post> getFeed(String userId);
}
```

---

### **4. Key Workflows**

**a) Post**
1. User posts content; service stores post.
2. Updates followers' feeds.

**b) Get Feed**
1. Service fetches posts for user, ranks and filters.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;

class Post {
    String id;
    String userId;
    String content;
    long ts;
}

class User {
    String id;
    String name;
    Set<String> following = new HashSet<>();
}

class FeedService {
    private final Map<String, User> users = new HashMap<>();
    private final Map<String, List<Post>> posts = new HashMap<>();
    public void post(String userId, String content) {
        Post p = new Post();
        p.id = UUID.randomUUID().toString();
        p.userId = userId;
        p.content = content;
        p.ts = System.currentTimeMillis();
        posts.computeIfAbsent(userId, k -> new ArrayList<>()).add(p);
    }
    public List<Post> getFeed(String userId) {
        User user = users.get(userId);
        List<Post> feed = new ArrayList<>();
        for (String followee : user.following) {
            feed.addAll(posts.getOrDefault(followee, List.of()));
        }
        feed.sort(Comparator.comparingLong(p -> -p.ts));
        return feed;
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class FeedServiceTest {
    @Test
    void testPostAndFeed() {
        // Setup users, post, get feed, assert order
    }
}
```

---

### **7. Extensions and Edge Cases**
- Add feed ranking, filtering, and pagination.
- Support for comments, likes, and notifications.
- Integrate with recommendation engine.
