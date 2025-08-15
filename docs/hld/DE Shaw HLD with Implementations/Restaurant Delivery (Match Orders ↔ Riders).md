# Restaurant Delivery (Match Orders ↔ Riders)

### 1. Problem Statement & Scope

Design a scalable backend for a food delivery platform that matches orders with available riders in real time. The system must optimize for fast delivery, live tracking, dynamic pricing, and high availability during peak demand.

### 2. Requirements

- **Functional Requirements:**
    - Ingest real-time rider locations (GPS updates).
    - Accept and manage new food orders.
    - Assign best rider to each order using a scoring model (ETA, proximity, load).
    - Live tracking for users and restaurants.
    - Dynamic/surge pricing based on demand.
- **Non-Functional Requirements:**
    - **Scalability:** 1M+ orders/day, 100k+ concurrent riders.
    - **Low Latency:** <1s for assignment.
    - **Reliability:** No lost orders, high uptime.

### 3. Capacity Estimation

- **Orders:** 1M/day (~12/sec avg, 1k/sec peak).
- **Riders:** 100k active.
- **Location Updates:** 1/min/rider = 100k/min.

### 4. High-Level Architecture Diagram

Code snippet

`graph TD
    A[User App] --> B[Order Service];
    C[Rider App] --> D[Telemetry Service];
    B --> E[Assignment/Dispatch Service];
    D --> E;
    E --> F[Geo-Index Service];
    E --> G[ETA Service];
    E --> H[Pricing Service];
    E --> I[Orders DB];
    E --> J[Rider Profile DB];
    E --> K[Notification Service];
`

### 5. Data Schema & API Design

- **API:**
    - `POST /v1/orders`: Place new order.
    - `POST /v1/riders/location`: Update rider location.
    - `GET /v1/orders/{order_id}/status`: Track order.
- **Data Models:**
    - **Orders:** `order_id, user_id, restaurant_id, status, assigned_rider, ...`
    - **Riders:** `rider_id, location, status, capacity, ...`
    - **Geo-Index:** Spatial index for fast proximity search.

### 6. Detailed Component Breakdown

- **Order Service:** Handles order creation, status, and user notifications.
- **Telemetry Service:** Ingests and stores real-time rider locations.
- **Assignment/Dispatch Service:** Runs matching algorithm, assigns riders, and triggers notifications.
- **Geo-Index Service:** Maintains spatial index for fast nearest-neighbor queries.
- **ETA Service:** Estimates delivery times using traffic, distance, and rider load.
- **Pricing Service:** Calculates dynamic pricing based on demand/supply.
- **Notification Service:** Sends updates to users, riders, and restaurants.

### 7. End-to-End Flow (Order Assignment)

Code snippet

`sequenceDiagram
    participant User
    participant OrderSvc
    participant Telemetry
    participant Dispatch
    participant GeoIndex
    participant Rider
    participant Notification

    User->>OrderSvc: Place order
    OrderSvc->>Dispatch: New order event
    Telemetry->>Dispatch: Rider location update
    Dispatch->>GeoIndex: Find nearby riders
    GeoIndex-->>Dispatch: Candidate riders
    Dispatch->>Dispatch: Score & select best rider
    Dispatch->>Rider: Assign order
    Dispatch->>OrderSvc: Update order status
    Dispatch->>Notification: Notify user/restaurant
    Rider->>OrderSvc: Accept/reject
    OrderSvc->>Dispatch: Update status
`

### 8. Bottlenecks, Fault Tolerance, and Trade-offs

- **Bottleneck: Geo-Index:**
    - Use in-memory spatial index (e.g., Redis Geo) for fast lookups. Partition by city/region.
- **Assignment Algorithm:**
    - Greedy (fast) vs. batch (optimal). Greedy is simple, batch is more efficient but adds latency.
- **Reliability:**
    - All state changes are persisted. Use retries and dead-letter queues for failed assignments.
- **Trade-offs:**
    - Greedy matching is fast but may be suboptimal. Batch matching is optimal but slower.
    - Real-time tracking is resource-intensive but improves user experience.

---

This design is used by Uber Eats, DoorDash, and Swiggy for real-time order-to-rider matching.
