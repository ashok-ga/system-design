# How to Approach a System Design Interview

This guide provides a repeatable, industry-grade script for tackling any system design interview. Use it to structure your 45–60 minute discussion and demonstrate both depth and breadth in your thinking.

---

## 1. Lock the Scope (Clarify Requirements)
- **Ask clarifying questions:** What is the core use case? What is out of scope? Who are the users? What are the must-have vs. nice-to-have features?
- **Write down requirements:** Separate functional (what the system does) and non-functional (scale, latency, availability, etc.).
- **Confirm with interviewer:** "Just to confirm, for this session, we are focusing on X, Y, and Z, and not A or B. Is that correct?"

## 2. Capacity Planning (Back-of-the-Envelope Estimation)
- **Estimate scale:** Users, QPS, data size, growth rate, peak vs. average load.
- **Do quick math:** E.g., "If we expect 10M users, and each generates 100 requests/day, that's ~115 QPS."
- **Document assumptions:** State them clearly so you can adjust if the interviewer pushes back.

## 3. API & Data Model Design
- **Define core APIs:** REST/gRPC endpoints, request/response schemas, error handling, idempotency.
- **Sketch data models:** Tables, indexes, key fields, relationships. Consider partitioning and sharding keys.
- **Discuss trade-offs:** E.g., SQL vs. NoSQL, denormalization, consistency needs.

## 4. High-Level Architecture (Boxes & Arrows)
- **Draw the big picture:** Major components (clients, API gateway, services, DBs, caches, queues, etc.).
- **Show data flow:** How does a request travel through the system?
- **Call out key patterns:** E.g., load balancers, CDN, microservices, event-driven, etc.

## 5. Hot Path Deep Dive
- **Pick a critical flow:** E.g., "Let's walk through a user posting a message."
- **Sequence diagram:** Step-by-step, from client to DB and back.
- **Discuss latency, consistency, and failure points at each step.**

## 6. Failure & Consistency
- **Identify failure modes:** What if a DB is down? What if a message is lost?
- **Mitigations:** Retries, timeouts, circuit breakers, replication, backups.
- **Consistency model:** Strong, eventual, read-your-writes, etc. How do you guarantee it?

## 7. Bottlenecks & Mitigations
- **Find the limits:** What will break first as you scale? (DB, cache, network, etc.)
- **Mitigation strategies:** Caching, sharding, partitioning, async processing, rate limiting.
- **Trade-offs:** Simplicity vs. scalability, cost vs. performance.

## 8. Evolution (Future Improvements)
- **What would you do next?** E.g., "If we need to support 10x more users, I'd add X."
- **Discuss extensibility:** How would you add new features or support new use cases?
- **Tech debt:** What shortcuts did you take, and how would you address them later?

---

**Tips:**
- Always state your assumptions.
- Use diagrams liberally (sequence, architecture, data model).
- Prioritize clarity and structure over covering every possible detail.
- If stuck, narrate your thought process and ask for hints.

**Example:** See the main README or HLDs in this repo for detailed, step-by-step examples following this script.
