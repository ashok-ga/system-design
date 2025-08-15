# Job Scheduler (cron + DAGs)

### 1. Problem Statement & Scope

Design a reliable, scalable job scheduling and orchestration platform for cron and DAG-based workflows (like Airflow/Prefect). The system must support complex dependencies, retries, monitoring, and high availability.

### 2. Requirements

- **Functional Requirements:**
    - Define workflows as DAGs (Directed Acyclic Graphs) of tasks.
    - Trigger jobs on schedule (cron) or manually.
    - Manage dependencies, retries, backoff, and failure handling.
    - UI/API for workflow management and monitoring.
- **Non-Functional Requirements:**
    - **Scalability:** 10k+ concurrent jobs.
    - **Reliability:** No job loss, strong guarantees.
    - **Extensibility:** Support custom operators, plugins.

### 3. Capacity Estimation

- **Workflows:** 10k active DAGs.
- **Tasks/DAG:** Avg 10.
- **Job Rate:** 1k/sec peak.

### 4. High-Level Architecture Diagram

Code snippet

`graph TD
    A[User/UI/API] --> B[Scheduler];
    B --> C[Metadata DB (Postgres)];
    B --> D[Message Queue (RabbitMQ/Kafka)];
    D --> E[Worker Fleet];
    E --> F[Object Storage];
    B --> G[Monitoring/Alerting];
    B --> H[UI/API];
`

### 5. Data Schema & API Design

- **API:**
    - `POST /v1/dags`: Create DAG.
    - `POST /v1/dags/{dag_id}/runs`: Trigger run.
    - `GET /v1/dags/{dag_id}/runs/{run_id}`: Get status.
- **Data Models:**
    - **DAG:** `dag_id, definition, schedule, owner, ...`
    - **DagRun:** `run_id, dag_id, status, start_time, end_time`
    - **TaskInstance:** `task_id, run_id, status, retries, logs`

### 6. Detailed Component Breakdown

- **Scheduler:** Core orchestrator. Evaluates schedules, triggers DAG runs, manages state.
- **Metadata DB:** Stores DAG definitions, run history, task state.
- **Message Queue:** Decouples scheduling from execution. Ensures reliable delivery of tasks to workers.
- **Worker Fleet:** Stateless workers execute tasks. Can autoscale.
- **Object Storage:** Stores logs, artifacts, and large outputs.
- **Monitoring/Alerting:** Tracks job status, failures, and metrics.
- **UI/API:** For workflow management and monitoring.

### 7. End-to-End Flow (DAG Run)

Code snippet

`sequenceDiagram
    participant User
    participant Scheduler
    participant DB
    participant Queue
    participant Worker
    participant Storage

    User->>Scheduler: Trigger DAG run
    Scheduler->>DB: Create DagRun
    Scheduler->>Queue: Enqueue tasks
    Queue->>Worker: Fetch task
    Worker->>Storage: Write logs/artifacts
    Worker->>DB: Update task status
    Scheduler->>User: Update status
`

### 8. Bottlenecks, Fault Tolerance, and Trade-offs

- **Bottleneck: Scheduler/Queue:**
    - Use active-passive HA for scheduler. Partition queues for scale.
- **Workers:**
    - Stateless, autoscale. Use heartbeat/zombie detector to handle failures.
- **Reliability:**
    - All state in DB. Queue is durable. Failed tasks retried with backoff.
- **Trade-offs:**
    - Strong guarantees add complexity. Eventual consistency is possible for non-critical metrics.

---

This design is used by modern workflow engines (Airflow, Prefect, Argo) for reliable, scalable job orchestration.
