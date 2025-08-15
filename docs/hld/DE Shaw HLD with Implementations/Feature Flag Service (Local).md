# Feature Flag Service (Local)

### 1. Problem Statement & Scope

Design a local feature flag service to enable/disable features for users or groups without redeploying code. The system must support targeting by user, group, or percentage, and provide low-latency flag evaluation in the app.

### 2. Requirements

- **Functional Requirements:**
    - Create, update, delete feature flags.
    - Target flags by user, group, or percentage rollout.
    - Evaluate flags in the app (SDK or API).
- **Non-Functional Requirements:**
    - **Low Latency:** <5ms flag evaluation.
    - **Reliability:** No flag loss, safe rollbacks.
    - **Consistency:** Eventual consistency for local cache.

### 3. Capacity Estimation

- **Flags:** 10k.
- **Users:** 1M.
- **QPS:** 10k/sec flag evaluations.

### 4. High-Level Architecture Diagram

Code snippet

`graph TD
    A[Admin UI] --> B[FeatureFlag Service];
    B --> C[Flag Store (DB)];
    B --> D[SDK Client];
    D --> E[App];
    B --> F[Cache];
`

### 5. Data Schema & API Design

- **API:**
    - `POST /v1/flags`: Create flag.
    - `GET /v1/flags/{flag_id}`: Get flag.
    - `PUT /v1/flags/{flag_id}`: Update flag.
    - `DELETE /v1/flags/{flag_id}`: Delete flag.
- **Data Models:**
    - **Flag:** `flag_id, name, enabled, targeting_rules, rollout_percentage, updated_at`
    - **TargetingRule:** `rule_id, flag_id, user_id/group_id, condition, value`

### 6. Detailed Component Breakdown

- **FeatureFlag Service:** CRUD for flags, manages targeting rules, exposes API for SDKs.
- **Flag Store (DB):** Persistent storage for flags and rules.
- **SDK Client:** Fetches and caches flags locally, evaluates for user/group.
- **Cache:** In-memory cache for fast evaluation, supports TTL and refresh.
- **Admin UI:** For flag management and monitoring.

### 7. End-to-End Flow (Flag Evaluation)

Code snippet

`sequenceDiagram
    participant Admin
    participant FlagSvc
    participant DB
    participant SDK
    participant App

    Admin->>FlagSvc: Create/Update flag
    FlagSvc->>DB: Persist flag
    SDK->>FlagSvc: Fetch flags
    FlagSvc-->>SDK: Return flags
    SDK->>App: Evaluate flag for user
    App-->>SDK: Use feature
`

### 8. Bottlenecks, Fault Tolerance, and Trade-offs

- **Bottleneck: Cache Staleness:**
    - Use TTL and background refresh. Accept brief staleness for performance.
- **Rollbacks:**
    - Support instant disable/rollback. Use versioning for safe updates.
- **Trade-offs:**
    - Local cache is fast but may be stale. Centralized API is slower but always fresh.

---

This design is used by LaunchDarkly, Unleash, and other feature flag platforms for local, low-latency flag evaluation.
