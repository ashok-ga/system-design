# In-Memory File System (Simplified)

This problem requires designing an in-memory file system supporting basic file and directory operations.

### **1. System Overview & Scope Clarification**

We are designing a backend service to support file and directory operations (mkdir, ls, create, read, write, move, delete) in memory.

**Functional Requirements (FR):**
- Support mkdir, ls, create, read, write, move, delete.
- Hierarchical directory structure.
- Path resolution (e.g., /a/b/c.txt).

**Non-Functional Requirements (NFR):**
- Fast (O(1) or O(logN) per op).
- Thread-safe for concurrent access.
- No persistence required (demo only).

**Assumptions:**
- All state is in-memory.
- No permissions or journaling for this round.

---

### **2. Core Components and Class Design**

- **Node:** Abstract base for File and Directory.
- **File:** Stores data and metadata.
- **Directory:** Contains children (files/directories).
- **FileSystem:** Main API for file ops and path resolution.

**Class Diagram (Textual Representation):**

```
+----------+      +----------+
|  Node    |<-----| Directory|
+----------+      +----------+
| name     |      | children |
+----------+      +----------+
      ^
      |
+----------+
|  File    |
+----------+
| data     |
| meta     |
+----------+
```

---

### **3. API Design (`FileSystem`)**

Java

```java
class FileSystem {
    void mkdir(String path);
    void create(String path);
    void write(String path, byte[] data);
    byte[] read(String path);
    void delete(String path);
    List<String> ls(String path);
}
```

---

### **4. Key Workflows**

**a) mkdir / create**
1. Parse path, traverse tree, create nodes as needed.

**b) read / write**
1. Resolve path to File node.
2. Read or write data.

**c) ls**
1. Resolve path to Directory node.
2. List children names.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;

abstract class Node {
    String name;
}

class File extends Node {
    byte[] data;
    Map<String, String> meta = new HashMap<>();
}

class Directory extends Node {
    Map<String, Node> children = new HashMap<>();
}

class FileSystem {
    private final Directory root = new Directory();
    public FileSystem() { root.name = "/"; }
    public void mkdir(String path) {
        resolveOrCreate(path, true);
    }
    public void create(String path) {
        String[] parts = path.split("/");
        Directory dir = (Directory)resolveOrCreate(String.join("/", Arrays.copyOf(parts, parts.length-1)), true);
        File file = new File();
        file.name = parts[parts.length-1];
        dir.children.put(file.name, file);
    }
    public void write(String path, byte[] data) {
        File file = (File)resolve(path);
        file.data = data;
    }
    public byte[] read(String path) {
        File file = (File)resolve(path);
        return file.data;
    }
    public void delete(String path) {
        String[] parts = path.split("/");
        Directory dir = (Directory)resolve(String.join("/", Arrays.copyOf(parts, parts.length-1)));
        dir.children.remove(parts[parts.length-1]);
    }
    public List<String> ls(String path) {
        Node node = resolve(path);
        if (node instanceof Directory) return new ArrayList<>(((Directory)node).children.keySet());
        else return List.of(node.name);
    }
    private Node resolve(String path) {
        String[] parts = path.split("/");
        Node curr = root;
        for (String p : parts) {
            if (p.isEmpty()) continue;
            if (!(curr instanceof Directory)) throw new RuntimeException("Not a directory");
            curr = ((Directory)curr).children.get(p);
            if (curr == null) throw new RuntimeException("Not found");
        }
        return curr;
    }
    private Node resolveOrCreate(String path, boolean isDir) {
        String[] parts = path.split("/");
        Node curr = root;
        for (String p : parts) {
            if (p.isEmpty()) continue;
            Directory dir = (Directory)curr;
            curr = dir.children.get(p);
            if (curr == null) {
                curr = isDir ? new Directory() : new File();
                curr.name = p;
                dir.children.put(p, curr);
            }
        }
        return curr;
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class FileSystemTest {
    @Test
    void testCreateAndRead() {
        FileSystem fs = new FileSystem();
        fs.mkdir("/a");
        fs.create("/a/b.txt");
        fs.write("/a/b.txt", "hello".getBytes());
        assertArrayEquals("hello".getBytes(), fs.read("/a/b.txt"));
    }
}
```

---

### **7. Extensions and Edge Cases**
- Add permissions, journaling, and persistence.
- Support for move/rename, symlinks, and quotas.
