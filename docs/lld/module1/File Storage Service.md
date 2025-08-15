# Design a File Storage Service (Dropbox/Google Drive)

This problem requires designing a scalable file storage and sharing service like Dropbox or Google Drive.

### **1. System Overview & Scope Clarification**

We are designing a backend service to store, retrieve, and share files for users, supporting versioning and collaboration.

**Functional Requirements (FR):**
- Upload/download files and folders.
- Share files with users (read/write).
- Support file versioning and metadata.
- Directory structure and search.

**Non-Functional Requirements (NFR):**
- Scalable to billions of files.
- High durability and availability.
- Secure (auth, access control, encryption).

**Assumptions:**
- Object storage (e.g., S3) for file blobs.
- Metadata in DB; demo uses in-memory.

---

### **2. Core Components and Class Design**

- **FileService:** Main API for file ops.
- **File/Folder:** Represents files and directories.
- **User:** Represents users.
- **Share:** Access control.
- **Version:** File versioning.

**Class Diagram (Textual Representation):**

```
+-----------+      +--------+
| File      |<-----| Folder |
+-----------+      +--------+
| id, name  |      | files  |
| owner     |      | folders|
| versions  |      +--------+
+-----------+
      ^
      |
+-----------+
| FileService|
+-----------+
```

---

### **3. API Design (`FileService`)**

Java

```java
class FileService {
    void upload(String userId, String path, byte[] data);
    byte[] download(String userId, String path);
    void share(String path, String targetUser, String access);
    List<String> list(String userId, String path);
}
```

---

### **4. Key Workflows**

**a) Upload/Download**
1. User uploads file; service stores blob and metadata.
2. User downloads file; service fetches blob.

**b) Share**
1. Owner shares file/folder with another user.
2. Service updates access control.

---

### **5. Code Implementation (Java)**

```java
import java.util.*;

class File {
    String id;
    String name;
    String owner;
    List<Version> versions = new ArrayList<>();
    // ...constructors, getters...
}

class Version {
    int number;
    byte[] data;
    long ts;
}

class Folder {
    String name;
    Map<String, File> files = new HashMap<>();
    Map<String, Folder> folders = new HashMap<>();
}

class FileService {
    private final Map<String, Folder> userRoots = new HashMap<>();
    public void upload(String userId, String path, byte[] data) {
        // Simplified: store file at path for user
        Folder root = userRoots.computeIfAbsent(userId, k -> new Folder());
        File file = new File();
        file.id = UUID.randomUUID().toString();
        file.name = path;
        file.owner = userId;
        Version v = new Version();
        v.number = 1;
        v.data = data;
        v.ts = System.currentTimeMillis();
        file.versions.add(v);
        root.files.put(path, file);
    }
    public byte[] download(String userId, String path) {
        Folder root = userRoots.get(userId);
        if (root == null) return null;
        File file = root.files.get(path);
        if (file == null || file.versions.isEmpty()) return null;
        return file.versions.get(file.versions.size()-1).data;
    }
    public void share(String path, String targetUser, String access) {
        // For demo, just print share action
        System.out.println("Shared " + path + " with " + targetUser + " as " + access);
    }
    public List<String> list(String userId, String path) {
        Folder root = userRoots.get(userId);
        if (root == null) return List.of();
        return new ArrayList<>(root.files.keySet());
    }
}
```

---

### **6. Testing (JUnit 5)**

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

public class FileServiceTest {
    @Test
    void testUploadAndDownload() {
        // Setup users, upload/download, assert data
    }
}
```

---

### **7. Extensions and Edge Cases**
- Add deduplication, chunking, and sync.
- Support for trash, restore, and audit logs.
- Integrate with cloud storage APIs.
