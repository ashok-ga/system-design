# Vector Search Service

### 1. Problem Statement & Scope

Design a scalable, low-latency vector search service for semantic search over 100M+ items using high-dimensional embeddings. The system must support fast k-NN queries, incremental updates, and metadata filtering, with high availability and horizontal scalability.

### 2. Requirements

- **Functional Requirements:**
    - Ingest and index high-dimensional vectors (e.g., 768D, 1536D).
    - Support k-NN search with optional metadata filters.
    - Incremental updates (add, delete, update vectors).
    - Return top-k most similar items for a query vector.
- **Non-Functional Requirements:**
    - **Latency:** <100ms/query for 100M+ items.
    - **Scalability:** Scale to billions of vectors via sharding.
    - **Availability:** 99.99% uptime.
    - **Consistency:** Eventual for index, strong for metadata.

### 3. Capacity Estimation

- **Corpus Size:** 100M vectors, 1536D, float32 = ~600MB/1M vectors, ~60GB total.
- **Query Rate:** 10k QPS.
- **Index Size:** With metadata, ~100GB total.

### 4. High-Level Architecture Diagram

Code snippet

`graph TD
    A[Client] --> B[API Gateway];
    B --> C[Embedding Model Service];
    B --> D[Query Router];
    D --> E[Shard 1 (Faiss/HNSW)];
    D --> F[Shard 2 (Faiss/HNSW)];
    D --> G[Shard N (Faiss/HNSW)];
    E --> H[Metadata Store];
    F --> H;
    G --> H;
    D --> I[Aggregator/Ranker];
    I --> J[Result];
`

### 5. Data Schema & API Design

- **API:**
    - `POST /v1/search`: `{query_vector, k, filters}`
    - `POST /v1/index`: `{item_id, vector, metadata}`
    - `DELETE /v1/index/{item_id}`
- **Data Models:**
    - **Vector Index:** HNSW/IVF-PQ, sharded by item_id hash.
    - **Metadata Store:** `item_id, metadata fields...`

### 6. Detailed Component Breakdown

- **Embedding Model Service:** Converts raw data (text, image) to vectors.
- **API Gateway:** Handles authentication, rate limiting, and forwards requests.
- **Query Router:** Routes search requests to relevant shards, aggregates results.
- **Shard (Faiss/HNSW):** In-memory or SSD-based vector index for fast k-NN search.
- **Metadata Store:** Stores item metadata for filtering and re-ranking.
- **Aggregator/Ranker:** Merges results from shards, applies filters, sorts by similarity.

### 7. End-to-End Flow (Search Query)

Code snippet

`sequenceDiagram
    participant Client
    participant APIGW
    participant Embed
    participant Router
    participant Shard1
    participant Shard2
    participant Agg

    Client->>APIGW: POST /v1/search
    APIGW->>Embed: Get query vector
    Embed-->>APIGW: Return vector
    APIGW->>Router: Forward search
    Router->>Shard1: k-NN search
    Router->>Shard2: k-NN search
    Shard1-->>Router: Top-k results
    Shard2-->>Router: Top-k results
    Router->>Agg: Aggregate, filter, rank
    Agg-->>APIGW: Final results
    APIGW-->>Client: Return top-k
`

### 8. Bottlenecks, Fault Tolerance, and Trade-offs

- **Bottleneck: Shard Memory/CPU:**
    - Use SSD-based indexes for larger-than-memory datasets. Horizontal sharding for scale.
- **Recall vs. Latency:**
    - HNSW/IVF-PQ trade off accuracy for speed. Tune parameters per use case.
- **Fault Tolerance:**
    - Replicate shards, use stateless routers. Failed shard = partial results, degrade gracefully.
- **Trade-offs:**
    - Eventual consistency for index updates. Strong consistency for metadata.
    - SSD-based search is slower but cheaper than RAM.

---

This design is used by modern semantic search engines (e.g., Pinecone, Weaviate, OpenAI) for large-scale vector search.
