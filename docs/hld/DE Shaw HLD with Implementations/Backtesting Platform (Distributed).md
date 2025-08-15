
# Backtesting Platform (Distributed)

### 1. Problem Statement & Scope

Design a distributed platform for quantitative analysts ("quants") to test their trading strategies against massive historical market data sets. The platform must be scalable to run hundreds of simulations concurrently and ensure that every backtest is perfectly reproducible.

### 2. Requirements

- **Functional Requirements:**
    - Users can submit a backtest job with parameters: strategy code, date range, symbols, etc.
    - The platform runs the strategy simulation over the specified historical data.
    - The system must produce detailed results: performance metrics (Sharpe ratio, drawdown), a list of simulated trades, and logs.
    - **Reproducibility:** A backtest run with the same code and data must produce the exact same result, bit for bit, every time.
- **Non-Functional Requirements:**
    - **Scalability:** Handle 10+ TB of historical data and run hundreds of concurrent backtest jobs.
    - **Performance:** A typical backtest of one strategy over one year of tick data should complete in a reasonable time (e.g., under 30 minutes).
    - **Isolation:** Jobs from different users must be isolated in terms of resources and security.
    - **Cost-Effectiveness:** Leverage cloud resources efficiently, potentially using cheaper spot instances for computation.

### 3. Capacity Estimation

- **Data Size:** 10 TB of tick data. A single year for a single stock can be 50-100 GB.
- **Concurrent Jobs:** 200.
- **Compute:** If each job needs 4 CPU cores, we need `200 * 4 = 800` cores available.
- **Data Access:** A single job might need to read 100 GB of data. At 200 concurrent jobs, the peak read throughput from storage could be significant, necessitating a high-performance storage solution.

### 4. High-Level Architecture Diagram

Code snippet

`graph TD
    subgraph "User Interface"
        A[Quant Analyst via UI/SDK] --> B[Job API Service];
    end

    subgraph "Control Plane"
        B --> C[Job Scheduler];
        C -- reads/writes --> D[Metadata DB (Postgres)];
    end

    subgraph "Execution Plane (e.g., on Kubernetes)"
        C -- creates Pod --> E{Backtest Runner Pod};
        subgraph E
            F[Containerized Strategy Code]
        end
        E --> G[Data Access Layer];
    end

    subgraph "Data & Storage"
        G --> H[Object Storage (S3)];
        H -- contains --> I[Historical Data (Parquet)];
        E -- writes logs/results --> J[Results Store (S3)];
        D -- stores --> K[Job Metadata];
        J -- triggers --> L[Results Analysis Service]
    end`

### 5. Data Schema & API Design

- **API:**
    - `POST /v1/jobs`: Submit a new backtest.
        - **Body:** `{"strategy_image": "docker.io/repo/my_strategy:v1.2", "start_date": "...", "end_date": "...", "params": {...}}`
    - `GET /v1/jobs/{job_id}`: Get the status and results of a job.
- **Data Models:**
    - **Metadata DB (Postgres):**
        - `jobs`: `job_id, user_id, status, docker_image_digest, submitted_at, results_path, ...`
    - **Storage (S3):**
        - **Historical Data:** Stored in Parquet format, partitioned by date and symbol. `s3://market-data/ticks/symbol=AAPL/date=2025-08-14/data.parquet`
        - **Results:** Each job writes its output to a dedicated path. `s3://backtest-results/{job_id}/trades.csv`, `s3://backtest-results/{job_id}/metrics.json`

### 6. Detailed Component Breakdown

- **Job API Service:** The entry point for users. It authenticates the request, validates the parameters, and creates a new job record in the **Metadata DB** with a `PENDING` status.
- **Job Scheduler:** The core of the control plane. It can be a custom service or built on a workflow orchestrator like Argo Workflows or a simple Kubernetes Operator. It polls the database for `PENDING` jobs and submits them to the compute cluster for execution.
- **Containerized Runner:** This is the key to reproducibility. The user's strategy code and all its dependencies (e.g., specific versions of pandas, numpy) are packaged into a **Docker image**. The scheduler runs this specific, immutable image. This eliminates "it works on my machine" problems and guarantees an identical execution environment every time.
- **Data Access Layer:** A library or sidecar container within the runner pod responsible for efficiently fetching data. It understands the partitioning scheme of the data in S3. To optimize performance, it can implement a **local cache on the worker node's SSD**, so if another job needs the same data, it can be read from the fast local disk instead of S3. The scheduler can be made "cache-aware" to try and place jobs on nodes that already have the data.
- **Object Storage (S3 + Parquet):**
    - **S3:** Provides a cheap, scalable, and durable way to store terabytes of data.
    - **Parquet:** A columnar storage format. This is extremely efficient for backtesting, as a strategy often only needs a few columns (e.g., `price`, `volume`) out of many. Columnar storage allows the runner to read only the data it needs, drastically reducing I/O.

### 7. End-to-End Flow (Submitting a Backtest)

Code snippet

`sequenceDiagram
    participant Analyst
    participant JobAPI
    participant Scheduler
    participant Kubernetes
    participant RunnerPod
    participant S3

    Analyst->>JobAPI: POST /jobs (strategy_image, params)
    JobAPI->>JobAPI: Create job record in DB (status=PENDING)
    JobAPI-->>Analyst: 202 Accepted (job_id)

    loop Scheduler Loop
        Scheduler->>Scheduler: Poll DB for PENDING jobs.
        Scheduler->>Kubernetes: Create Pod from docker_image for job_id.
    end

    Kubernetes->>RunnerPod: Start container.
    RunnerPod->>S3: Stream relevant Parquet data partitions.
    Note over RunnerPod: Execute strategy logic tick-by-tick...
    RunnerPod->>S3: Write trades.csv and metrics.json to results path.
    RunnerPod->>RunnerPod: Update job status to SUCCESS in DB.`

### 8. Bottlenecks, Fault Tolerance, and Trade-offs

- **Bottleneck: Data I/O:** Reading large volumes of data from S3 can be the slowest part.
    - **Mitigation:** The columnar Parquet format is the primary mitigation. The local SSD cache on worker nodes is another. Using a high-performance query engine like DuckDB within the runner can also speed up data processing.
- **Fault Tolerance:**
    - **Runner Failure:** The runner is a container. If it fails (e.g., out of memory), Kubernetes will automatically restart it based on the defined policy. Since the job is deterministic, it will restart from the beginning and produce the same result. The system can be enhanced with checkpointing for very long jobs.
- **Key Trade-offs:**
    - **Object Store (S3) vs. Distributed File System (HDFS):** S3 is easier to manage, more cost-effective, and offers infinite scalability (decoupled compute and storage). HDFS can offer better performance if data locality is critical but comes with significant operational overhead. For this use case, the flexibility of S3 is usually preferred.
    - **Cost (Spot vs. On-Demand Instances):** Backtesting jobs are often batch workloads that can tolerate interruption. Using cheaper EC2 Spot Instances can reduce compute costs by up to 90%. The trade-off is that a job might be preempted and need to be restarted, increasing its total wall-clock time.
