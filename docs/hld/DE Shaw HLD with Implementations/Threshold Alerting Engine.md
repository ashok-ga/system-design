# Threshold Alerting Engine

## Problem Statement
On time-series inputs, trigger alerts (e.g., CPU>90% for 5m) with debounce.

## Functional Requirements
- Rules per metric
- Conditions across time windows
- Suppress duplicates (debounce)

## Core Concepts
- `Rule(metric, predicate, window, duration)`
- `Evaluator` keeps rolling window
- `Notifier` (email/webhook)
- Debounce logic

## High-Level Design
- **Rules:**
    - Each rule: metric, predicate, window, duration
- **Evaluator:**
    - Maintains rolling window of values
    - Triggers alert if condition met for duration
- **Notifier:**
    - Sends alert (email/webhook)
    - Debounce to suppress duplicates

## Step-by-Step Solution
1. **Define Rule, Evaluator, Notifier classes**
2. **Evaluator:** rolling window logic
3. **Debounce:** suppress duplicate alerts
4. **API:** add rule, ingest metric, get alerts

## Edge Cases
- Flapping metrics
- Overlapping rules
- Missed alerts on downtime
