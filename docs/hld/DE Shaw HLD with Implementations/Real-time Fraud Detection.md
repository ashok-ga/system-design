---
# Real-time Fraud Detection (Rules + ML)

## 1. Problem Statement & Requirements
Design a real-time fraud detection system for financial transactions, combining rules and ML models, with async review and high throughput.

**Functional Requirements:**
- Score transactions inline (real-time)
- Combine rules engine and ML model for decisioning
- Support async review queue for flagged cases
- Integrate with feature store for real-time features
- Emit decisions to downstream systems (Kafka, logs)

**Non-Functional Requirements:**
- 5–10k TPS online scoring
- p99 < 50ms latency
- High availability, explainability, auditability

**Assumptions:**
- Features are precomputed and available in online store
- Model serving supports A/B testing and versioning

---
## 2. High-Level Architecture

**Components:**
- **Transaction Ingest:** Receives and validates transactions
- **Feature Fetcher:** Retrieves features from online store (Redis/Scylla)
- **Rules Engine:** Applies business rules (e.g., velocity, blacklists)
- **Model Serving:** Scores transaction using ML model (A/B, canary)
- **Decision Engine:** Combines rules/model, makes allow/challenge/deny decision
- **Case Service:** Queues flagged cases for manual review
- **Event Emitter:** Publishes results to Kafka/logs
- **Storage:** Online (Redis/Scylla), offline (Parquet/warehouse)

**Architecture Diagram:**
```
 [Tx] -> [Feature Fetch] -> [Rules Engine] -> [Model] -> [Decision] -> [Case/Log]
```

---
## 3. Data Model & Feature Store

- **Transaction:** { id, user_id, amount, ts, ... }
- **Feature Vector:** { user_id, avg_txn_amt, velocity, ... }
- **Decision:** { tx_id, score, action, reason, model_version }
- **Case:** { tx_id, features, decision, status }

---
## 4. Key Workflows

### a) Real-time Scoring
1. Transaction arrives at ingest
2. Feature fetcher retrieves features
3. Rules engine applies business logic
4. Model serving scores transaction
5. Decision engine combines results
6. If flagged, case is queued for review
7. Emit decision to Kafka/logs

### b) Async Review
1. Analyst reviews flagged cases in case service
2. Updates status, triggers notifications

### c) Model A/B Testing
1. Model serving supports multiple versions
2. Traffic split for A/B or canary
3. Metrics collected for evaluation

---
## 5. Scaling & Reliability

- **Horizontal Scaling:** Stateless services, scale by QPS
- **Feature Store:** Redis/Scylla for low-latency fetch
- **Model Serving:** Containerized, autoscaled
- **Monitoring:** Latency, false positive/negative rates, model drift

---
## 6. Trade-offs & Alternatives

- **Consistency:** Point-in-time correctness for features
- **Latency vs Accuracy:** More features/models = higher latency
- **Explainability:** Rules are explainable, models less so

---
## 7. Best Practices & Extensions

- Use feature store for online/offline parity
- Audit logs for all decisions
- Support for real-time and batch scoring
- Integrate with feedback loop for model retraining
- Add explainability and reason codes

---
## 8. Example Pseudocode (Decision Engine)
```python
def score_transaction(tx):
    features = fetch_features(tx.user_id)
    rule_result = rules_engine(tx, features)
    model_score = model_serve(tx, features)
    if rule_result == 'deny' or model_score < 0.2:
        action = 'deny'
    elif rule_result == 'challenge' or model_score < 0.5:
        action = 'challenge'
    else:
        action = 'allow'
    return action
```

---
## 9. References
- [Feature Store](https://feast.dev/)
- [Fraud Detection at Scale](https://stripe.com/blog/real-time-fraud-detection)
