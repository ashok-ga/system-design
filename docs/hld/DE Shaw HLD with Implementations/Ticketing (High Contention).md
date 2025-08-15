# Ticketing (High Contention)

### 1. Problem Statement & Scope

Design a ticketing system for high-demand events (e.g., concerts, sports) that can handle massive traffic spikes, prevent overselling, and ensure fairness. The system must support temporary seat holds, payment, and confirmation, with strong consistency and resilience to failures.

### 2. Requirements

- **Functional Requirements:**
    - Users can view available seats in real time.
    - Place temporary holds on seats (cart/hold window).
    - Confirm purchase after payment.
    - Release holds on timeout or user abandon.
    - Waitlist/queue for overflow demand.
- **Non-Functional Requirements:**
    - **Scalability:** Handle 1M+ concurrent users during peak.
    - **Fairness:** Prevent bots, ensure first-come-first-served.
    - **Consistency:** No overselling, strong seat allocation.
    - **Availability:** Survive flash crowds, DDoS.

### 3. Capacity Estimation

- **Peak Users:** 1M concurrent.
- **Seats/Event:** 50k.
- **Hold Window:** 5 minutes.
- **Purchase Rate:** 10k/sec peak.

### 4. High-Level Architecture Diagram

Code snippet

`graph TD
    A[User] --> B[CDN/WAF];
    B --> C[Virtual Waiting Room];
    C --> D[Ticket Service];
    D --> E[Redis (Seat Holds)];
    D --> F[Postgres (Durable State)];
    D --> G[Payment Service];
    D --> H[Notification Service];
    D --> I[Queue/Waitlist Service];
`

### 5. Data Schema & API Design

- **API:**
    - `GET /v1/events/{event_id}/seats`: View seat map.
    - `POST /v1/events/{event_id}/hold`: Place hold.
    - `POST /v1/events/{event_id}/purchase`: Confirm purchase.
- **Data Models:**
    - **Seats:** `seat_id, event_id, status (available/held/sold), hold_expiry, user_id`
    - **Holds (Redis):** `hold_id, seat_ids, user_id, expires_at`
    - **Orders (Postgres):** `order_id, user_id, seat_ids, status, payment_id`

### 6. Detailed Component Breakdown

- **CDN/WAF:** Absorbs DDoS, caches static content.
- **Virtual Waiting Room:** Throttles entry, prevents overload, enforces fairness.
- **Ticket Service:** Core logic for seat holds, purchase, and release. Uses Redis for fast holds, Postgres for durability.
- **Redis (Seat Holds):** In-memory, expiring keys for temporary holds.
- **Postgres (Durable State):** Source of truth for sold seats and orders.
- **Payment Service:** Handles payment and refunds.
- **Notification Service:** Sends confirmation, reminders, or waitlist updates.
- **Queue/Waitlist Service:** Manages overflow demand.

### 7. End-to-End Flow (Seat Hold & Purchase)

Code snippet

`sequenceDiagram
    participant User
    participant WaitingRoom
    participant TicketSvc
    participant Redis
    participant Postgres
    participant Payment
    participant Notification

    User->>WaitingRoom: Enter event
    WaitingRoom->>TicketSvc: Allow entry
    TicketSvc->>Redis: Place seat hold
    Redis-->>TicketSvc: Hold confirmed
    TicketSvc->>User: Show hold, start timer
    User->>TicketSvc: Purchase
    TicketSvc->>Payment: Process payment
    Payment-->>TicketSvc: Success/Fail
    alt Success
        TicketSvc->>Postgres: Mark seat(s) sold
        TicketSvc->>Redis: Remove hold
        TicketSvc->>Notification: Send confirmation
    else Fail
        TicketSvc->>Redis: Release hold
        TicketSvc->>User: Show error
    end
`

### 8. Bottlenecks, Fault Tolerance, and Trade-offs

- **Bottleneck: Redis/DB:**
    - Redis for speed, Postgres for durability. Use optimistic locking for seat updates.
- **Fairness:**
    - Virtual waiting room and rate limiting prevent unfair access.
- **Consistency:**
    - Optimistic locking ensures no double-sell. Redis expiry releases abandoned holds.
- **Trade-offs:**
    - Speed vs. consistency. Strong consistency for seat allocation, eventual for notifications.
    - In-memory holds are fast but require careful expiry handling.

---

This design is used by major ticketing platforms to handle flash sales and high contention events.
