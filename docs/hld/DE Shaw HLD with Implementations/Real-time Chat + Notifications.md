# Real-time Chat + Notifications

### 1. Problem Statement & Scope

Design a scalable, low-latency chat platform supporting 1:1 and group messaging, user presence, read receipts, and push notifications. The system must handle millions of concurrent users, guarantee message delivery, and provide a seamless experience across devices.

### 2. Requirements

- **Functional Requirements:**
    - Send/receive messages in real time (1:1, group).
    - Show user presence (online/offline/away).
    - Read receipts and typing indicators.
    - Persist chat history and support search.
    - Push notifications for offline users.
- **Non-Functional Requirements:**
    - **Scalability:** Millions of concurrent users, 100k+ QPS.
    - **Low Latency:** <100ms end-to-end delivery.
    - **Reliability:** No message loss, at-least-once delivery.
    - **Security:** End-to-end encryption (optional).

### 3. Capacity Estimation

- **Concurrent Users:** 10M.
- **Message Rate:** 100k/sec peak.
- **Storage:** 1B messages/day, 1KB/message = 1TB/day.

### 4. High-Level Architecture Diagram

Code snippet

`graph TD
    A[Client] --> B[WebSocket Gateway];
    B --> C[Presence Service];
    B --> D[Chat Service];
    D --> E[Message Store (Cassandra/ScyllaDB)];
    D --> F[Kafka/Event Bus];
    F --> G[Fan-out Service];
    G --> H[Push Notification Service];
    D --> I[Search Service];
    C --> J[Presence DB/Cache];
`

### 5. Data Schema & API Design

- **API:**
    - WebSocket: `send_message`, `receive_message`, `presence_update`, `typing`, etc.
    - REST: `GET /v1/conversations`, `GET /v1/messages`, etc.
- **Data Models:**
    - **Messages:** `message_id, conversation_id, sender_id, content, timestamp, status`
    - **Conversations:** `conversation_id, participants, last_message_id, ...`
    - **Presence:** `user_id, status, last_seen`

### 6. Detailed Component Breakdown

- **WebSocket Gateway:** Maintains persistent connections, authenticates users, routes messages to Chat Service.
- **Presence Service:** Tracks user status, updates presence in real time, and notifies interested clients.
- **Chat Service:** Core logic for message delivery, persistence, and fan-out. Handles message ordering and deduplication.
- **Message Store:** Scalable NoSQL DB (Cassandra/ScyllaDB) for chat history.
- **Kafka/Event Bus:** Decouples message ingestion from fan-out and notification.
- **Fan-out Service:** Delivers messages to all recipients (online/offline), triggers push notifications as needed.
- **Push Notification Service:** Integrates with APNs/FCM for mobile push.
- **Search Service:** Indexes messages for fast retrieval.

### 7. End-to-End Flow (Message Send & Delivery)

Code snippet

`sequenceDiagram
    participant UserA
    participant Gateway
    participant ChatSvc
    participant MessageStore
    participant Kafka
    participant Fanout
    participant PushSvc
    participant UserB

    UserA->>Gateway: send_message
    Gateway->>ChatSvc: Forward message
    ChatSvc->>MessageStore: Persist message
    ChatSvc->>Kafka: Publish event
    Kafka->>Fanout: Consume event
    Fanout->>UserB: Deliver message (if online)
    Fanout->>PushSvc: Push notification (if offline)
    PushSvc-->>UserB: Mobile push
    UserB->>Gateway: ack/read_receipt
    Gateway->>ChatSvc: Update status
`

### 8. Bottlenecks, Fault Tolerance, and Trade-offs

- **Bottleneck: WebSocket Gateway:**
    - Horizontally scalable, stateless. Use sticky sessions or consistent hashing.
- **Message Store:**
    - NoSQL DB for high write throughput. Partition by conversation_id.
- **Fan-out:**
    - Kafka decouples ingestion from delivery. Enables retries and at-least-once delivery.
- **Trade-offs:**
    - Eventual consistency for presence/read receipts. Strong consistency for message delivery.
    - Push notifications may be delayed by mobile OS.

---

This architecture is used by leading chat apps (WhatsApp, Slack, Messenger) for reliability and scale.
