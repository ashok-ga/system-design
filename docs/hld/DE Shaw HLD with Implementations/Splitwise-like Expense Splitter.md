# Splitwise-like Expense Splitter

### 1. Problem Statement & Scope

Design a system to track group expenses, balances, and simplify debt among users (like Splitwise). The system must support adding expenses, calculating balances, and settling up efficiently, even for large groups and multiple currencies.

### 2. Requirements

- **Functional Requirements:**
    - Add expenses (equal, unequal, percent split).
    - Track balances per user and group.
    - Simplify debts (minimize cash flow between users).
    - Settle up (record payments, mark debts as settled).
- **Non-Functional Requirements:**
    - **Scalability:** 1M+ users, 100k+ groups.
    - **Accuracy:** Handle rounding, currency conversion.
    - **Reliability:** No lost transactions.

### 3. Capacity Estimation

- **Users:** 1M.
- **Groups:** 100k.
- **Expenses:** 10M/month.
- **Storage:** Each expense ~200B, 10M = 2GB/month.

### 4. High-Level Architecture Diagram

Code snippet

`graph TD
    A[User App] --> B[API Gateway];
    B --> C[Expense Service];
    C --> D[Balance Service];
    C --> E[Settlement Engine];
    C --> F[Notification Service];
    D --> G[User DB];
    C --> H[Group DB];
    C --> I[Expense DB];
    E --> J[Payment Service];
`

### 5. Data Schema & API Design

- **API:**
    - `POST /v1/groups/{group_id}/expenses`: Add expense.
    - `GET /v1/groups/{group_id}/balances`: Get balances.
    - `POST /v1/groups/{group_id}/settle`: Settle up.
- **Data Models:**
    - **User:** `user_id, name, email, ...`
    - **Group:** `group_id, name, members, ...`
    - **Expense:** `expense_id, group_id, paid_by, amount, split, currency, ts`
    - **BalanceSheet:** `group_id, user_id, balance`
    - **Settlement:** `settlement_id, group_id, from_user, to_user, amount, ts`

### 6. Detailed Component Breakdown

- **Expense Service:** Handles adding expenses, validates splits, updates balances.
- **Balance Service:** Calculates and stores per-user balances for each group.
- **Settlement Engine:** Runs min-cash-flow algorithm to minimize number of payments needed to settle all debts.
- **Notification Service:** Notifies users of new expenses, settlements, or reminders.
- **User/Group/Expense DBs:** Store all persistent data.
- **Payment Service:** (Optional) Integrates with payment gateways for real money settlements.

### 7. End-to-End Flow (Add Expense & Settle Up)

Code snippet

`sequenceDiagram
    participant User
    participant API
    participant ExpenseSvc
    participant BalanceSvc
    participant SettlementEng
    participant Notification

    User->>API: Add expense
    API->>ExpenseSvc: Validate & record
    ExpenseSvc->>BalanceSvc: Update balances
    ExpenseSvc->>Notification: Notify group
    User->>API: Settle up
    API->>SettlementEng: Run min-cash-flow
    SettlementEng->>BalanceSvc: Update balances
    SettlementEng->>Notification: Notify users
`

### 8. Bottlenecks, Fault Tolerance, and Trade-offs

- **Bottleneck: Settlement Algorithm:**
    - Min-cash-flow is O(N^2) for large groups. Use heuristics or batch settlements for scale.
- **Accuracy:**
    - Rounding and currency conversion can cause small errors. Use high-precision types and audit logs.
- **Reliability:**
    - All transactions are persisted. Use idempotency keys for safe retries.
- **Trade-offs:**
    - Simpler algorithms are faster but may not minimize payments. More complex ones are optimal but slower.

---

This design is used by Splitwise and similar apps for group expense management and debt simplification.
