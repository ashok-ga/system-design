# Model Serving Platform (AB Tests + Canary)

## Requirements
- Deploy models
- Traffic splits
- Versioned
- Logging/metrics

## Scale
- 5–20k QPS
- p99 < 50ms

## Core Architecture
- Gateway
- Router
- Model containers (GPU/CPU)
- Feature fetch
- Result
- Control plane for versions/allocations

## Storage
- Model registry (S3 + DB)
- Logs in OLAP

## Flow
- Request → fetch features → call model → log; shadow/canary options

## Bottlenecks & Mitigations
- Cold starts; fix with warm pools & autoscaling

## Diagram
```
[Gateway] -> [Router] -> [Model Container] -> [Result] -> [Log]
```

## Notes
- Use shadow/canary for safe rollout
- Warm pools for low latency
