# Short-video Feed (TikTok-style)

### 1. Problem Statement & Scope

Design a scalable backend for a short-video mobile app (like TikTok) that delivers a personalized, infinite feed. The system must support low-latency video delivery, real-time user interactions, and high availability for millions of users.

### 2. Requirements

- **Functional Requirements:**
    - Generate personalized, infinite video feeds per user.
    - Support user interactions: like, comment, share, follow.
    - Real-time event ingestion for engagement signals.
    - Low TTFB (time to first byte) for video playback.
- **Non-Functional Requirements:**
    - **Scalability:** 100M+ users, 1M QPS.
    - **Low Latency:** <100ms feed load, <1s video start.
    - **Availability:** 99.99% uptime.

### 3. Capacity Estimation

- **Users:** 100M.
- **Videos:** 1B+.
- **Feed Requests:** 1M QPS.
- **Video Size:** 5MB avg, 5PB total.

### 4. High-Level Architecture Diagram

Code snippet

`graph TD
    A[User] --> B[API Gateway];
    B --> C[Feed Orchestrator];
    C --> D[Candidate Generators];
    C --> E[Feature Service];
    C --> F[Ranker];
    F --> G[Filtering/Composition];
    G --> H[CDN (Video Assets)];
    C --> I[Event Ingestion];
    I --> J[Analytics/ML];
`

### 5. Data Schema & API Design

- **API:**
    - `GET /v1/feed`: Fetch personalized feed.
    - `POST /v1/videos/{video_id}/like`: Like a video.
    - `POST /v1/videos/{video_id}/comment`: Comment on a video.
- **Data Models:**
    - **Videos:** `video_id, uploader_id, url, metadata, features`
    - **Users:** `user_id, profile, preferences, history`
    - **Events:** `event_id, user_id, video_id, type, ts`

### 6. Detailed Component Breakdown

- **Feed Orchestrator:** Entry point for feed requests. Coordinates candidate generation, ranking, and filtering.
- **Candidate Generators:** Generate a pool of potential videos (fresh, trending, followed, etc.).
- **Feature Service:** Computes user/video features for ranking (e.g., embeddings, engagement).
- **Ranker:** ML model ranks candidates for personalization.
- **Filtering/Composition:** Removes seen/ineligible videos, composes final feed.
- **CDN:** Delivers video assets with low latency.
- **Event Ingestion:** Streams user interactions to analytics/ML for feedback loop.

### 7. End-to-End Flow (Feed Generation)

Code snippet

`sequenceDiagram
    participant User
    participant APIGW
    participant Orchestrator
    participant CandidateGen
    participant FeatureSvc
    participant Ranker
    participant Filter
    participant CDN

    User->>APIGW: GET /feed
    APIGW->>Orchestrator: Forward request
    Orchestrator->>CandidateGen: Get candidates
    CandidateGen-->>Orchestrator: Candidate list
    Orchestrator->>FeatureSvc: Get features
    FeatureSvc-->>Orchestrator: Features
    Orchestrator->>Ranker: Rank candidates
    Ranker-->>Orchestrator: Ranked list
    Orchestrator->>Filter: Filter/compose
    Filter-->>Orchestrator: Final feed
    Orchestrator->>APIGW: Return feed
    APIGW->>User: Show feed
    User->>CDN: Fetch video asset
    CDN-->>User: Stream video
`

### 8. Bottlenecks, Fault Tolerance, and Trade-offs

- **Bottleneck: Feed Generation:**
    - Use precomputed feeds for cold start, real-time for active users.
- **Video Delivery:**
    - CDN ensures low-latency, global delivery. Multi-CDN for redundancy.
- **Personalization:**
    - ML ranking is compute-intensive. Use feature stores and caching.
- **Trade-offs:**
    - Real-time feeds are more personalized but costlier. Precomputed feeds are faster but less fresh.

---

This design is used by TikTok, Instagram Reels, and YouTube Shorts for scalable, personalized video feeds.
