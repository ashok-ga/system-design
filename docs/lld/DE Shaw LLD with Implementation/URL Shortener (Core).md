# URL Shortener (Core)

This problem requires designing a scalable URL shortening service with support for custom codes and click tracking.

### **1. System Overview & Scope Clarification**

We are designing a backend service to shorten URLs, expand short codes, and track basic statistics.

**Functional Requirements (FR):**
- `shorten(url, custom?)`: Shorten a URL, optionally with a custom code.
- `expand(code)`: Retrieve the original URL.
- Basic stats: click count, creation time.
- Prevent malicious loops (no self-shortening).

**Non-Functional Requirements (NFR):**
- High availability and low latency.
- Unique, collision-free codes.
- Scalable to billions of URLs.
- Secure: prevent abuse and malicious links.

**Assumptions:**
- Codes are base62-encoded.
- Store is persistent (e.g., DB), but demo uses in-memory map.
- Caching is used for hot URLs.

---

### **2. Core Components and Class Design**

- **UrlShortenerService:** Main service for shortening and expanding URLs.
- **CodeGenerator:** Generates unique codes (counter or hash).
- **UrlMapping:** Stores mapping from code to long URL and metadata.
- **StatsService:** Tracks click stats.
- **Store:** Interface for persistence.

**Class Diagram (Textual Representation):**

```
+---------------------+
| UrlShortenerService |
+---------------------+
| + shorten()         |
| + expand()          |
| + getStats()        |
+---------------------+
        ^
        |
+---------------------+
|   CodeGenerator     |
+---------------------+
| + generate()        |
+---------------------+
        ^
        |
+---------------------+
|      Store          |
+---------------------+
| + save()            |
| + find()            |
+---------------------+
```

---

### **3. API Design (`UrlShortenerService`)**

Java

```java
class UrlShortenerService {
    String shorten(String url, String customCode);
    String expand(String code);
    UrlStats getStats(String code);
}
```

---

### **4. Key Workflows**

**a) Shorten URL**
1. Validate URL and custom code (if provided).
2. If custom code, check for collision.
3. If no custom code, generate unique code (base62 of counter).
4. Save mapping to store.
5. Return code.

**b) Expand URL**
1. Lookup code in store (cache first).
2. If found, increment click count.
3. Return long URL.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

class UrlMapping {
    String code;
    String longUrl;
    long createdAt;
    int clickCount;
    String owner;
    // ...constructors, getters, setters...
}

class CodeGenerator {
    private long counter = 1;
    public synchronized String generate() {
        return base62(counter++);
    }
    private String base62(long num) {
        String chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";
        StringBuilder sb = new StringBuilder();
        while (num > 0) {
            sb.append(chars.charAt((int)(num % 62)));
            num /= 62;
        }
        return sb.reverse().toString();
    }
}

class InMemoryStore {
    private final Map<String, UrlMapping> map = new ConcurrentHashMap<>();
    public void save(UrlMapping m) { map.put(m.code, m); }
    public UrlMapping find(String code) { return map.get(code); }
}

class UrlShortenerService {
    private final InMemoryStore store = new InMemoryStore();
    private final CodeGenerator codeGen = new CodeGenerator();
    public String shorten(String url, String customCode) {
        // Validate URL, check for loops, etc.
        String code = (customCode != null) ? customCode : codeGen.generate();
        if (store.find(code) != null) throw new RuntimeException("Code exists");
        UrlMapping m = new UrlMapping();
        m.code = code;
        m.longUrl = url;
        m.createdAt = System.currentTimeMillis();
        m.clickCount = 0;
        store.save(m);
        return code;
    }
    public String expand(String code) {
        UrlMapping m = store.find(code);
        if (m == null) throw new RuntimeException("Not found");
        m.clickCount++;
        return m.longUrl;
    }
    public int getStats(String code) {
        UrlMapping m = store.find(code);
        if (m == null) throw new RuntimeException("Not found");
        return m.clickCount;
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class UrlShortenerServiceTest {
    @Test
    void testShortenAndExpand() {
        UrlShortenerService svc = new UrlShortenerService();
        String code = svc.shorten("https://example.com", null);
        assertNotNull(code);
        String url = svc.expand(code);
        assertEquals("https://example.com", url);
    }
    @Test
    void testCustomCode() {
        UrlShortenerService svc = new UrlShortenerService();
        String code = svc.shorten("https://foo.com", "foo");
        assertEquals("foo", code);
        assertEquals("https://foo.com", svc.expand("foo"));
    }
}
```

---

### **7. Scalability, Security, and Extensions**
- Use distributed counter or sharded DB for code generation at scale.
- Add TTL for expired links.
- Validate and sanitize URLs.
- Add abuse detection and rate limiting.
