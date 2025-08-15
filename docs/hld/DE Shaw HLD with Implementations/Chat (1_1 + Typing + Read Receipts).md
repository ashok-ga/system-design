# Chat (1_1 + Typing + Read Receipts)
## Problem Statement
Design a real-time chat system supporting 1:1 messaging, typing indicators, and read receipts. The system must provide low-latency delivery, message persistence, and seamless experience across devices.
## Functional Requirements
- 1:1 chat between users.
- Typing indicators (show when the other user is typing).
- Read receipts (show when a message is read).
- Message history and offline delivery.
## Non-Functional Requirements
- **Scalability:** 10M+ users, 100k QPS.
- **Low Latency:** <100ms message delivery.
- **Reliability:** No message loss.
## Capacity Estimation
- **Users:** 10M.
- **Message Rate:** 100k/sec peak.
- **Storage:** 1B messages/day, 1KB/message = 1TB/day.
## High-Level Architecture Diagram
Code snippet

`graph TD
    A[Client] --> B[WebSocket Gateway];
    B --> C[Chat Service];
    C --> D[Message Store (NoSQL)];
    C --> E[Presence Service];
    C --> F[Typing Indicator Service];
    C --> G[Read Receipt Service];
    D --> H[Search Service];
`
## Data Schema & API Design
- **API:**
    - WebSocket: `send_message`, `typing`, `read_receipt`, etc.
    - REST: `GET /v1/messages`, `GET /v1/conversations`, etc.
- **Data Models:**
    - **Messages:** `message_id, sender_id, receiver_id, content, ts, status`
    - **Conversations:** `conversation_id, participants, last_message_id, ...`
    - **Presence:** `user_id, status, last_seen`
    - **Typing:** `conversation_id, user_id, is_typing, ts`
    - **ReadReceipt:** `message_id, user_id, read_at`
## Detailed Component Breakdown
- **WebSocket Gateway:** Maintains persistent connections, authenticates users, routes messages.
- **Chat Service:** Core logic for message delivery, persistence, and fan-out.
- **Message Store (NoSQL):** Stores chat history, supports search and offline delivery.
- **Presence Service:** Tracks user status (online/offline).
- **Typing Indicator Service:** Publishes typing events to the other user.
- **Read Receipt Service:** Tracks and notifies when messages are read.
- **Search Service:** Indexes messages for fast retrieval.
## End-to-End Flow (Message Send & Read Receipt)
Code snippet

`sequenceDiagram
    participant UserA
    participant Gateway
    participant ChatSvc
    participant MessageStore
    participant TypingSvc
    participant ReadReceiptSvc
    participant UserB

    UserA->>Gateway: send_message
    Gateway->>ChatSvc: Forward message
    ChatSvc->>MessageStore: Persist message
    ChatSvc->>UserB: Deliver message
    UserB->>Gateway: typing
    Gateway->>TypingSvc: Publish typing
    TypingSvc->>UserA: Show typing
    UserB->>Gateway: read_receipt
    Gateway->>ReadReceiptSvc: Record read
    ReadReceiptSvc->>UserA: Notify read
`
## Bottlenecks, Fault Tolerance, and Trade-offs
- **Bottleneck: WebSocket Gateway:**
    - Horizontally scalable, stateless. Use sticky sessions or consistent hashing.
- **Message Store:**
    - NoSQL DB for high write throughput. Partition by conversation_id.
- **Typing/Read Receipts:**
    - Pub-sub for real-time updates. Eventual consistency is acceptable.
- **Trade-offs:**
    - Eventual consistency for presence/typing/read receipts. Strong consistency for message delivery.

---

This design is used by WhatsApp, Messenger, and other chat apps for real-time 1:1 messaging.
# Chat (1:1 + Typing + Read Receipts)

## Problem Statement
Design a simple chat service (no persistence required for LLD round). Support 1:1 chat, typing, and read receipts.

## Functional Requirements
- Send message
- Delivery receipt
- Read receipt
- Typing indicator

## Core Concepts
- `User`, `Conversation`, `Message`, `ChatService`
- `PresenceService` (in-memory), `Delivery` (Observer)

## High-Level Design
- **Conversations:**
    - Each conversation between two users
    - Messages sent, delivered, read
- **Presence:**
    - Track online/offline status
    - Typing indicator via in-memory pub/sub
- **Delivery:**
    - Observer pattern for delivery/read receipts
- **Edge Cases:**
    - Ordering per conversation
    - Idempotent resend

## Step-by-Step Solution
1. **Define classes:** User, Conversation, Message, ChatService
2. **PresenceService:** in-memory status
3. **Delivery:** observer for receipts
4. **API:** send, typing, read

## Edge Cases
- Out-of-order delivery
- Duplicate messages
- User disconnects
