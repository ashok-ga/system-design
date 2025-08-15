---
# Trade Capture & Reconciliation

## 1. Problem Statement & Requirements
Design a robust trade capture and reconciliation system to ingest, deduplicate, persist, and reconcile trade executions with custodians.

**Functional Requirements:**
- Ingest executions from multiple venues
- Deduplicate and canonicalize trades
- Persist all trades with audit trail
- End-of-day reconciliation with custodian/counterparty
- Exception workflow for mismatches

**Non-Functional Requirements:**
- 100–500k messages/day
- Correctness > performance
- High auditability, schema evolution support

**Assumptions:**
- All venues provide unique trade IDs or can be canonicalized
- Reconciliation is batch (EOD)

---
## 2. High-Level Architecture

**Components:**
- **Venue Ingest:** Receives and parses trade executions
- **Canonicalizer:** Normalizes trade format, deduplicates
- **Idempotency Layer:** Ensures no double-inserts
- **Durable Log:** Write-ahead log for all trades
- **Reconciliation Job:** Compares internal and custodian records
- **Exception Workflow:** Handles mismatches, manual review
- **Storage:** RDBMS (audit), data lake (raw)

**Architecture Diagram:**
```
 [Venue Ingest] -> [Canonicalizer] -> [Idempotency] -> [Durable Log] -> [Reconciliation] -> [Exception Workflow]
```

---
## 3. Data Model & Canonicalization

- **Trade:** { id, venue, symbol, qty, price, ts, ... }
- **Canonical Trade:** Normalized, deduped trade record
- **Reconciliation Record:** { trade_id, status, details }

---
## 4. Key Workflows

### a) Trade Ingestion
1. Venue Ingest receives trade execution
2. Canonicalizer normalizes and deduplicates
3. Idempotency layer checks for duplicates
4. Trade written to durable log and RDBMS

### b) End-of-day Reconciliation
1. Reconciliation job fetches internal and custodian trades
2. Compares by trade ID, symbol, qty, price
3. Matches marked as reconciled; mismatches to exception workflow

### c) Exception Handling
1. Mismatches queued for manual review
2. Analyst resolves, updates status

---
## 5. Scaling & Reliability

- **Batch Processing:** EOD jobs for reconciliation
- **Idempotency:** Versioned upserts for deduplication
- **Schema Evolution:** Use CDC and schema registry
- **Audit Trail:** All changes logged

---
## 6. Trade-offs & Alternatives

- **Strict Schema vs Flexibility:** Use schema registry for evolution
- **Batch vs Real-time Reconciliation:** Batch is simpler, real-time is possible but complex

---
## 7. Best Practices & Extensions

- Use versioned upserts for idempotency
- CDC for schema evolution
- Exception workflow for all mismatches
- Integrate with downstream reporting and analytics

---
## 8. Example Pseudocode (Reconciliation)
```python
def reconcile(internal_trades, custodian_trades):
    matched, mismatched = [], []
    custodian_map = {t.id: t for t in custodian_trades}
    for t in internal_trades:
        if t.id in custodian_map and t == custodian_map[t.id]:
            matched.append(t)
        else:
            mismatched.append(t)
    return matched, mismatched
```

---
## 9. References
- [Trade Reconciliation](https://en.wikipedia.org/wiki/Trade_reconciliation)
- [CDC & Schema Registry](https://debezium.io/)
