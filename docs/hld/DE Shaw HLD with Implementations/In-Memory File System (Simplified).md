# In-Memory File System (Simplified)

### 1. Problem Statement & Scope

Design an in-memory file system supporting mkdir, ls, create, read, write, move, and delete operations. The system should mimic a real file system's API and structure, with fast, thread-safe operations and extensibility for future features (permissions, journaling).

### 2. Requirements

- **Functional Requirements:**
    - Create/delete directories and files.
    - List directory contents (ls).
    - Read/write file data.
    - Move/rename files and directories.
    - Path resolution (absolute/relative).
- **Non-Functional Requirements:**
    - **Low Latency:** All operations in-memory, <1ms.
    - **Thread Safety:** Support concurrent access.
    - **Extensibility:** Permissions, journaling (future).

### 3. Capacity Estimation

- **Files/Dirs:** 1M nodes.
- **File Size:** Up to 10MB/file.
- **RAM:** 10GB+ for large trees.

### 4. High-Level Architecture Diagram

Code snippet

`graph TD
    A[User/API] --> B[FileSystem];
    B --> C[Path Resolver];
    B --> D[Root Directory];
    D --> E[Directory/File Nodes];
    B --> F[Lock Manager];
    B --> G[Future: Journal/Log];
`

### 5. Data Schema & API Design

- **API:**
    - `mkdir(path)`
    - `ls(path)`
    - `create(path, data)`
    - `read(path)`
    - `write(path, data)`
    - `move(src, dst)`
    - `delete(path)`
- **Data Models:**
    - **Node:** `name, type (file/dir), parent, metadata`
    - **File:** `name, data, size, created_at, updated_at`
    - **Directory:** `name, children (map)`

### 6. Detailed Component Breakdown

- **FileSystem:** Main API, manages root, path resolution, and delegates to nodes.
- **Path Resolver:** Parses and resolves absolute/relative paths.
- **Directory Node:** Holds children (files/dirs) in a map for fast lookup.
- **File Node:** Stores file data and metadata.
- **Lock Manager:** Ensures thread safety for concurrent ops.
- **Journal/Log (Future):** For durability and crash recovery.

### 7. End-to-End Flow (File Create & Move)

Code snippet

`sequenceDiagram
    participant User
    participant FS
    participant PathRes
    participant Dir
    participant File

    User->>FS: create(/foo/bar.txt, data)
    FS->>PathRes: Resolve /foo
    PathRes-->>FS: Directory node
    FS->>Dir: Add File node
    Dir->>File: Store data
    User->>FS: move(/foo/bar.txt, /baz/bar.txt)
    FS->>PathRes: Resolve /foo/bar.txt, /baz
    PathRes-->>FS: Source file, dest dir
    FS->>Dir: Remove from /foo, add to /baz
`

### 8. Bottlenecks, Fault Tolerance, and Trade-offs

- **Bottleneck: Path Resolution:**
    - Use trie/map for fast lookup. Cache resolved paths.
- **Thread Safety:**
    - Use fine-grained locks or lock-free structures for concurrency.
- **Durability:**
    - In-memory only; add journaling for persistence.
- **Trade-offs:**
    - In-memory is fast but volatile. Adding journaling increases durability but adds latency.

---

This design is used in interview questions and as a basis for real file system implementations.
