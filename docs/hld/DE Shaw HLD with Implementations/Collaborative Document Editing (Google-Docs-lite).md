# Collaborative Document Editing (Google-Docs-lite)

## Requirements
- Real-time multi-user edits
- Presence
- Versioning

## Scale
- Docs with 10–100 concurrent editors
- p99 < 200ms convergence

## Core Architecture
- OT or CRDT engine
- Doc shard service
- Presence/pubsub
- Snapshot & compaction

## Storage
- Log of ops + periodic snapshots (RDBMS/Doc store)

## Flow
- Edit → transform/merge → broadcast; late join replay since snapshot

## Trade-offs
- OT easier server-centric; CRDT for P2P/offline

## Diagram
```
[Client] -> [OT/CRDT Engine] -> [Shard Service] -> [Broadcast/Presence]
```

## Notes
- Use operational transform for server-centric, CRDT for offline/P2P
- Snapshots for efficient late join
