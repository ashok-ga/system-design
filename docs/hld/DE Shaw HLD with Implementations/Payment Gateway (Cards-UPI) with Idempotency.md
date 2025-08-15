---
# Payment Gateway (Cards/UPI) with Idempotency

## 1. Problem Statement & Requirements
Design a highly available, idempotent payment gateway for cards and UPI, supporting retries, webhooks, and double-charge prevention.

**Functional Requirements:**
- Authorize, capture, refund, and void payments
- Support idempotency keys for all operations
- Retry and backoff on failures
- Webhook notifications for status changes
- Support multiple payment connectors (cards, UPI, wallets)

**Non-Functional Requirements:**
- 1–5k TPS
- Five-nines (99.999%) availability on core path
- PCI DSS compliance
- Low-latency (p99 < 200ms)

**Assumptions:**
- All payment operations are atomic and idempotent
- Outbox/event sourcing for reliable notifications

---
## 2. High-Level Architecture

**Components:**
- **API Gateway:** Receives payment requests, validates input
- **Idempotency Store:** Tracks idempotency keys and operation results
- **Orchestrator (State Machine):** Manages payment state transitions
- **Acquirer Connectors:** Integrates with card/UPI networks
- **Event Outbox:** Stores events for reliable webhook delivery
- **Webhook Dispatcher:** Sends notifications to clients
- **Storage:** Postgres (core), Redis (idempotency), S3 (receipts)

**Architecture Diagram:**
```
 [API] -> [Idempotency Store] -> [Orchestrator] -> [Acquirer] -> [Outbox] -> [Webhook]
```

---
## 3. Data Model & State Machine

- **Payment:** { id, amount, currency, status, idempotency_key, ... }
- **Idempotency Key:** { key, operation, result, expiry }
- **Event:** { id, type, payload, status }
- **State Machine:** States: INIT → AUTHORIZED → CAPTURED/VOIDED → REFUNDED

---
## 4. Key Workflows

### a) Payment Request
1. API receives request with idempotency key
2. Checks idempotency store; if present, returns stored result
3. If new, creates payment, stores key, starts orchestrator
4. Orchestrator transitions state (authorize, capture, etc.)
5. On each state change, writes event to outbox
6. Webhook dispatcher delivers notifications

### b) Retry & Backoff
1. On failure, orchestrator persists state and schedules retry
2. Idempotency key ensures no double-processing

### c) Webhook Delivery
1. Outbox stores events until acknowledged by client
2. Retries with exponential backoff

---
## 5. Scaling & Reliability

- **Stateless API:** Horizontally scalable
- **Idempotency Store:** Redis for low-latency lookups
- **Outbox Pattern:** Guarantees at-least-once delivery
- **Failover:** Use leader election for orchestrator
- **Monitoring:** Track double-charge, latency, webhook failures

---
## 6. Risk Points & Mitigations

- **Double-charge:** Idempotency key scoped to operation
- **Lost Webhooks:** Outbox with retries
- **Partial State:** Persist state transitions atomically

---
## 7. Best Practices & Extensions

- Use UUIDs for idempotency keys
- Encrypt sensitive data at rest and in transit
- PCI DSS compliance for card data
- Support for SCA (Strong Customer Authentication)
- Integrate with fraud detection

---
## 8. Example Pseudocode (Idempotency Check)
```python
def process_payment(request):
    key = request.idempotency_key
    result = idempotency_store.get(key)
    if result:
        return result
    # Process payment
    result = orchestrate_payment(request)
    idempotency_store.set(key, result)
    return result
```

---
## 9. References
- [Idempotency in Payments](https://stripe.com/docs/idempotency)
- [Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html)
