# URL Shortener (Global)

### 1. Problem Statement & Scope

Design a global URL shortening service (like bit.ly or tinyurl.com) that generates short aliases for long URLs and provides fast, highly available redirection. The system must handle billions of URLs, massive read traffic, and provide analytics.

### 2. Requirements

- **Functional Requirements:**
    - Users can submit a long URL and receive a unique, short URL.
    - Optionally support custom aliases.
    - Accessing the short URL redirects to the original long URL.
    - Track click analytics (usage, geo, referrer).
- **Non-Functional Requirements:**
    - **Latency:** Redirects must be extremely fast (p99 < 30ms).
    - **Availability:** Five-nines (99.999%) for redirects.
    - **Scalability:** 50k QPS reads, billions of URLs.
    - **Durability:** No lost mappings.

### 3. Capacity Estimation

- **Write Rate:** 10 new URLs/sec.
- **Read Rate:** 50,000 redirects/sec (read/write = 5000:1).
- **Storage:** 10B URLs * 600B = 6TB (sharded DB).

### 4. High-Level Architecture Diagram

Code snippet

`graph TD
    subgraph "Write Path (Shorten)"
        A[User] --> B[API Service];
        B --> C[Code Generation Service];
        B --> D[Database (Sharded)];
    end
    subgraph "Read Path (Redirect)"
        E[User] --> F[Edge CDN/PoP];
        F --> G[Redirector Service];
        G --> H[Cache (Redis)];
        H --> D;
    end
    subgraph "Analytics Path (Async)"
        G -- fire-and-forget --> I[Message Bus (Kafka)];
        I --> J[Stream Processor];
        J --> K[Analytics DB (ClickHouse)];
    end
`

### 5. Data Schema & API Design

- **API:**
    - `POST /v1/shorten`: `{long_url, custom_alias?}` → `{short_url}`
    - `GET /{short_code}`: Redirect endpoint.
- **Data Models:**
    - **URLs Table:** `short_code, long_url, user_id, created_at, ...`
    - **Analytics Table:** `short_code, ts, ip, geo, referrer, ...`

### 6. Detailed Component Breakdown

- **API Service:** Handles URL shortening requests, validates input, and stores mappings.
- **Code Generation Service:** Generates unique short codes, checks for collisions, supports custom aliases.
- **Database (Sharded):** Stores mappings, sharded for scale.
- **Edge CDN/PoP:** Caches redirects close to users for low latency.
- **Redirector Service:** Looks up short code, issues HTTP 301/302 redirect.
- **Cache (Redis):** Caches hot mappings for fast lookup.
- **Message Bus (Kafka):** Streams click events for analytics.
- **Stream Processor:** Aggregates analytics, writes to analytics DB.
- **Analytics DB (ClickHouse):** Stores and serves analytics queries.

### 7. End-to-End Flow (Shorten & Redirect)

Code snippet

`sequenceDiagram
    participant User
    participant API
    participant CodeGen
    participant DB
    participant CDN
    participant Redirector
    participant Cache
    participant Kafka
    participant Analytics

    User->>API: POST /shorten
    API->>CodeGen: Generate code
    CodeGen->>DB: Store mapping
    DB-->>API: Ack
    API-->>User: Return short_url
    User->>CDN: GET /{short_code}
    CDN->>Redirector: Lookup
    Redirector->>Cache: Check cache
    alt Hit
        Cache-->>Redirector: Return long_url
    else Miss
        Redirector->>DB: Lookup
        DB-->>Redirector: Return long_url
        Redirector->>Cache: Set cache
    end
    Redirector-->>User: HTTP 301/302
    Redirector->>Kafka: Log click
    Kafka->>Analytics: Aggregate
`

### 8. Bottlenecks, Fault Tolerance, and Trade-offs

- **Bottleneck: DB/Cache:**
    - Use sharding and caching for scale. CDN for global low latency.
- **Code Generation:**
    - Ensure uniqueness, avoid collisions. Use random or hash-based codes.
- **Analytics:**
    - Async, eventual consistency. Use stream processing for scale.
- **Trade-offs:**
    - Write path can be eventually consistent. Read path must be highly available and fast.

---

This design is used by Bitly, TinyURL, and other global URL shorteners.
        - `short_code VARCHAR(8) PRIMARY KEY,`
        - `long_url TEXT,`
        - `created_at TIMESTAMP`
    - The choice of `short_code` as the primary key is perfect for a sharded system, as random-looking codes will distribute the load evenly.

### 6. Detailed Component Breakdown

- **API Service (Write Path):** Receives the long URL. It calls the **Code Generation Service** to get a unique short code, then writes the mapping (`short_code` -> `long_url`) to the database. If a custom alias is requested, it first checks the DB for its availability.
- **Code Generation Service:** This is a critical component that must produce unique short codes without being a bottleneck.
    - **Strategy 1 (Snowflake-style):** Use a distributed unique ID generator (like Twitter's Snowflake) to get a 64-bit integer. Then, **Base62-encode** this integer `[a-zA-Z0-9]`. This produces a ~7-character code, is guaranteed to be unique, and doesn't require a database check.
    - **Strategy 2 (Pre-generation):** Have a background job that generates millions of random, unused codes and stores them in a queue (e.g., in Redis). The API service just pops a code from this queue when needed.
- **Redirector Service (Read Path):** A fleet of lightweight, stateless servers deployed globally. Their only job is to handle `GET /{short_code}` requests.
    1. First, check a multi-layered **cache** (e.g., local in-memory, then a regional Redis cluster).
    2. If it's a cache miss, query the database to get the `long_url`.
    3. Populate the cache with the result.
    4. Return a `301` or `302` redirect.
    5. Asynchronously publish a click event to Kafka for analytics.
- **Cache:** The most important part of the read path. A very high cache hit rate (>99%) is expected. This shields the database from the massive read traffic. Caching can happen at multiple levels: browser, CDN edge, and the service's regional Redis cluster.
- **Analytics Pipeline:** A standard streaming pipeline. The fire-and-forget approach ensures that analytics processing adds zero latency to the user-facing redirect.

### 7. End-to-End Flow (Redirect)

Code snippet

`sequenceDiagram
    participant UserBrowser
    participant EdgeCDN
    participant RedirectorSvc
    participant RedisCache
    participant Database

    UserBrowser->>EdgeCDN: GET /aBcDeF
    Note over EdgeCDN: Cache MISS
    EdgeCDN->>RedirectorSvc: GET /aBcDeF
    
    RedirectorSvc->>RedisCache: GET short_code:aBcDeF
    Note over RedisCache: Cache MISS
    RedisCache-->>RedirectorSvc: nil
    
    RedirectorSvc->>Database: SELECT long_url WHERE short_code='aBcDeF'
    Database-->>RedirectorSvc: "http://very.long.url/..."
    
    RedirectorSvc->>RedisCache: SET short_code:aBcDeF "http://..."
    
    Note over RedirectorSvc: Asynchronously log click to Kafka
    RedirectorSvc-->>EdgeCDN: 302 Found, Location: "http://..."
    EdgeCDN-->>UserBrowser: 302 Found, Location: "http://..."`

### 8. Bottlenecks, Fault Tolerance, and Trade-offs

- **Bottleneck: Write Path Code Generation:** If we used a naive approach of generating a random code and checking the DB for uniqueness, we would face high latency and collisions at scale. The Snowflake/Base62 approach avoids this central contention.
- **Fault Tolerance:**
    - **Read Path:** The read path is highly resilient. If the database is temporarily unavailable, the system can continue to serve redirects for all cached entries, degrading gracefully.
    - **Write Path:** The write path is less critical. If it's down for a few minutes, users cannot create new short URLs, but existing ones continue to work.
- **Key Trade-offs:**
    - **Redirect Type (301 vs. 302):**
        - **`301 Moved Permanently`:** The browser caches this response aggressively. The next time the user clicks the link, the browser may go directly to the long URL without ever contacting our service again. This is great for reducing server load but terrible for analytics and makes it impossible to ever change the destination URL.
        - **`302 Found` (or `307 Temporary Redirect`):** The browser is instructed that this redirect is temporary and it should always check the short URL first. This ensures our service is hit every time, allowing for 100% accurate analytics and the ability to edit the destination. The trade-off is higher traffic to our servers. For most commercial shorteners, **302/307 is the correct choice.**
