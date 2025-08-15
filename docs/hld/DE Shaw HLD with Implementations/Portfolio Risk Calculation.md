---
# Portfolio Risk Calculation (Intraday VaR/Greeks)

## 1. Problem Statement & Requirements
Design a scalable, low-latency system to compute portfolio risk metrics (VaR, Greeks) in real time as market data updates.

**Functional Requirements:**
- Recalculate Greeks/VaR on market updates
- Support portfolio hierarchies (accounts, desks, books)
- SLAs per desk (customizable latency/accuracy)
- Expose risk metrics via API/UI
- Support ad-hoc and scheduled risk runs

**Non-Functional Requirements:**
- 10–100k positions per run
- 10–100 updates/sec
- p99 < 1–2s for risk recompute
- High availability, auditability

**Assumptions:**
- Positions and market data are available in real time
- Compute grid is available for parallelization

---
## 2. High-Level Architecture

**Components:**
- **Market Data Feed:** Real-time price updates
- **Change Data Subscription:** Triggers risk recompute on price/position change
- **Dependency Graph Engine:** Tracks which portfolios/positions are affected
- **Sensitivity Engine:** Computes Greeks, VaR, and other risk metrics
- **Compute Grid:** Parallelizes risk calculations
- **Result Cache:** Stores latest risk results for fast queries
- **API/UI:** Exposes risk metrics to users
- **Storage:** RDBMS for positions, Redis/Pinot for results, S3 for artifacts

**Architecture Diagram:**
```
 [Market Data] -> [Dependency Graph] -> [Sensitivity Engine] -> [Compute Grid] -> [Result Cache/API]
```

---
## 3. Data Model & Dependency Management

- **Position:** { id, portfolio_id, instrument, qty, ... }
- **Portfolio:** { id, parent_id, ... }
- **Dependency Graph:** Maps which positions/portfolios are affected by a price change
- **Risk Result:** { portfolio_id, VaR, Greeks, timestamp, ... }

---
## 4. Key Workflows

### a) Real-time Risk Recompute
1. Market data update triggers change-data event
2. Dependency graph engine determines affected portfolios/positions
3. Sensitivity engine computes new risk metrics (VaR, Greeks)
4. Results cached and published to API/UI

### b) Ad-hoc/Scheduled Risk Run
1. User/API requests risk run for a portfolio or desk
2. System fetches latest positions and market data
3. Runs sensitivity engine, caches and returns results

### c) Result Storage & Audit
1. Results written to Redis/Pinot for fast queries
2. Artifacts (full risk reports) archived to S3

---
## 5. Scaling & Reliability

- **Parallelization:** Use compute grid (Kubernetes, Spark, Ray) for large portfolios
- **DAG Scheduling:** Only recompute affected nodes in dependency graph
- **Memoization:** Cache intermediate results to avoid redundant computation
- **Monitoring:** Track latency, error rates, compute utilization

---
## 6. Bottlenecks & Mitigations

- **Fan-out Recompute:** Use DAG to minimize recompute scope
- **Data Staleness:** Use event-driven updates for freshness
- **Compute Spikes:** Autoscale compute grid

---
## 7. Best Practices & Extensions

- Use vectorized math libraries for speed
- Audit logs for all risk runs
- Support what-if scenarios and stress tests
- Integrate with trade capture and P&L systems

---
## 8. Example Pseudocode (Dependency Graph)
```python
class DependencyGraph:
    def __init__(self):
        self.edges = defaultdict(set)  # symbol -> set(portfolio_ids)
    def add_dependency(self, symbol, portfolio_id):
        self.edges[symbol].add(portfolio_id)
    def get_affected(self, symbol):
        return self.edges.get(symbol, set())
```

---
## 9. References
- [VaR Calculation](https://en.wikipedia.org/wiki/Value_at_risk)
- [DAG Scheduling](https://en.wikipedia.org/wiki/Directed_acyclic_graph)
