# E-commerce Checkout

### 1. Problem Statement & Scope

Design a robust, reliable, and scalable checkout system for an e-commerce platform. The system must handle order creation, inventory reservation, payment processing, and confirmation, ensuring no overselling or double-charging, even under failures or retries.

### 2. Requirements

- **Functional Requirements:**
    - Create an order from a user's cart.
    - Reserve inventory for each item.
    - Process payment (credit card, wallet, etc.).
    - Confirm order and notify user.
    - Rollback all steps if any sub-step fails (distributed transaction).
- **Non-Functional Requirements:**
    - **Reliability:** No double-charging, no overselling.
    - **Idempotency:** Safe to retry any step.
    - **Scalability:** Handle 10k+ checkouts/minute.
    - **Consistency:** Strong consistency for inventory and payment.
    - **Observability:** Trace each order's status.

### 3. Capacity Estimation

- **Peak Checkouts:** 10k/minute (167/sec).
- **Inventory Items/Order:** Avg 3.
- **Payment Failures:** 1%.
- **Storage:** Orders table grows by 10M/year.

### 4. High-Level Architecture Diagram

Code snippet

`graph TD
    A[User] --> B[API Gateway];
    B --> C[Order Service (Saga Orchestrator)];
    C --> D[Inventory Service];
    C --> E[Payment Service];
    C --> F[Notification Service];
    C --> G[Outbox/Event Bus];
    D --> H[Inventory DB];
    E --> I[Payment Gateway];
    F --> J[Email/SMS];
    G --> K[Order Analytics];
`

### 5. Data Schema & API Design

- **API:**
    - `POST /v1/checkout`: `{cart_id, payment_method, shipping_address, ...}`
    - `GET /v1/orders/{order_id}`: Get order status.
- **Data Models:**
    - **Orders:** `order_id, user_id, status, total, created_at, ...`
    - **OrderItems:** `order_id, item_id, qty, price`
    - **Inventory:** `item_id, available_qty`
    - **Payments:** `payment_id, order_id, status, amount, ...`
    - **Idempotency Key:** For safe retries.

### 6. Detailed Component Breakdown

- **Order Service (Saga Orchestrator):** Coordinates the distributed transaction. Starts the saga, tracks progress, and rolls back on failure.
- **Inventory Service:** Checks and reserves inventory. Supports compensation (release) on rollback.
- **Payment Service:** Processes payment. Supports refund on rollback.
- **Notification Service:** Sends order confirmation or failure notifications.
- **Outbox/Event Bus:** Ensures reliable event publishing for downstream consumers (analytics, fulfillment).

### 7. End-to-End Flow (Checkout Saga)

Code snippet

`sequenceDiagram
    participant User
    participant API
    participant OrderSvc
    participant InventorySvc
    participant PaymentSvc
    participant NotificationSvc
    participant Outbox

    User->>API: POST /checkout
    API->>OrderSvc: Create order (PENDING)
    OrderSvc->>InventorySvc: Reserve items
    InventorySvc-->>OrderSvc: Success/Fail
    OrderSvc->>PaymentSvc: Charge payment
    PaymentSvc-->>OrderSvc: Success/Fail
    alt All succeed
        OrderSvc->>OrderSvc: Mark order CONFIRMED
        OrderSvc->>NotificationSvc: Send confirmation
        OrderSvc->>Outbox: Publish event
    else Any fail
        OrderSvc->>InventorySvc: Release items (compensate)
        OrderSvc->>PaymentSvc: Refund (if needed)
        OrderSvc->>OrderSvc: Mark order FAILED
        OrderSvc->>NotificationSvc: Send failure
    end
`

### 8. Bottlenecks, Fault Tolerance, and Trade-offs

- **Bottleneck: Inventory/Payment:**
    - Both must be strongly consistent. Use row-level locks or atomic DB ops for inventory. Payment must be idempotent.
- **Saga Pattern:**
    - Enables distributed rollback. Each step has a compensating action.
- **Outbox Pattern:**
    - Ensures events are reliably published even if the service crashes after DB commit.
- **Trade-offs:**
    - Strong consistency adds latency. Eventual consistency is possible for non-critical steps (e.g., notifications).
    - Sagas are more complex than monolithic transactions but scale better and avoid distributed locks.

---

This design is used by leading e-commerce platforms to ensure reliability and scalability in the checkout process.
