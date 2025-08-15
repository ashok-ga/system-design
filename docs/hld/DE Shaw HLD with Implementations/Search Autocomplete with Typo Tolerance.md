---
# Search Autocomplete with Typo Tolerance

## 1. Problem Statement & Requirements
Design a high-performance, typo-tolerant search autocomplete system for a web-scale consumer application (e.g., e-commerce, search engine).

**Functional Requirements:**
- Suggest completions for user input in real time (sub-50ms latency)
- Support prefix and fuzzy (typo-tolerant) matching
- Rank suggestions by popularity, recency, and context
- Handle large vocabularies (1–10M+ tokens)
- Support multi-language and Unicode

**Non-Functional Requirements:**
- 10–50k QPS sustained
- High availability (99.99%)
- Horizontal scalability
- Low memory footprint per node

**Assumptions:**
- Data is periodically rebuilt offline and loaded into memory
- Popularity/CTR stats are updated asynchronously

---
## 2. High-Level Architecture

**Components:**
- **Frontend API:** Receives user queries, returns suggestions
- **Autocomplete Engine:** Performs prefix/fuzzy lookup and ranking
- **Index Builder:** Offline job to build DAWG/Trie and BK-tree
- **Popularity Service:** Tracks CTR, updates ranking weights
- **Cache Layer:** Hot cache for most frequent queries
- **Data Store:** Stores raw tokens, stats, and index snapshots

**Architecture Diagram:**
```
        +-----------+         +-------------------+         +-----------------+
User -> | Frontend  | <-----> | Autocomplete API  | <-----> | Autocomplete    |
        +-----------+         +-------------------+         | Engine (Trie/   |
                                                           | BK-tree/Ranker) |
                                                           +-----------------+
                                                                 ^
                                                                 |
        +-------------------+         +-----------------+        |
        | Popularity/CTR    | <-----> | Index Builder   | <------+
        | Stats Service     |         +-----------------+
        +-------------------+
```

---
## 3. Data Model & Indexing

- **Trie/DAWG:** For fast prefix search; each node stores child pointers, end-of-word, and popularity counters.
- **BK-tree:** For fuzzy/typo-tolerant search (edit distance ≤ 2); each node stores a word and children by edit distance.
- **Popularity Table:** Maps tokens to CTR, last access, and context features.
- **Cache:** LRU or LFU for hot queries and results.

---
## 4. Key Workflows

### a) Query Handling
1. User types query; API receives partial input.
2. Check hot cache for query; if hit, return suggestions.
3. If miss, perform prefix search in Trie/DAWG.
4. If not enough results, expand with fuzzy search (BK-tree, edit distance ≤ 2).
5. Rank results by popularity, recency, and context.
6. Return top-N suggestions (e.g., 10).

### b) Index Build & Refresh
1. Offline job ingests new tokens, builds Trie/DAWG and BK-tree.
2. Serializes index to disk; API nodes reload on update.
3. Popularity stats merged from logs/analytics.

### c) Popularity/CTR Update
1. User selects a suggestion; event sent to Popularity Service.
2. CTR and recency stats updated asynchronously.
3. Periodic batch jobs update ranking weights in index.

---
## 5. Scaling & Reliability

- **Sharding:** Partition index by first character or hash for horizontal scaling.
- **Replication:** Multiple API nodes for HA; index reload on failover.
- **Cache:** Multi-level (local LRU, distributed Redis/Memcached for hot queries).
- **Bulk Rebuild:** Blue/green index deployment to avoid downtime.
- **Monitoring:** Latency, QPS, cache hit rate, memory usage.

---
## 6. Trade-offs & Alternatives

- **Memory vs Recall:** Larger index = more recall, but higher memory. Use pruning and compression.
- **Prefix vs Fuzzy:** Fuzzy search is slower; limit edit distance and result count.
- **Popularity Lag:** CTR updates are eventually consistent; may lag real-time.
- **Offline vs Online Indexing:** Offline is faster and safer; online allows instant updates but is complex.

---
## 7. Best Practices & Extensions

- Use DAWG for minimal memory prefix index; BK-tree for fuzzy.
- Precompute and cache top queries.
- Use async logging for CTR updates.
- Support language-specific tokenization and normalization.
- Integrate with analytics for query trends.
- Add abuse prevention (rate limits, spam filtering).

---
## 8. Example Pseudocode (Trie Node)
```python
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False
        self.popularity = 0

def insert(root, word, popularity):
    node = root
    for c in word:
        if c not in node.children:
            node.children[c] = TrieNode()
        node = node.children[c]
    node.is_end = True
    node.popularity = popularity

def search_prefix(root, prefix):
    node = root
    for c in prefix:
        if c not in node.children:
            return []
        node = node.children[c]
    return collect_words(node, prefix)

def collect_words(node, prefix):
    results = []
    if node.is_end:
        results.append((prefix, node.popularity))
    for c, child in node.children.items():
        results.extend(collect_words(child, prefix + c))
    return results
```

---
## 9. References
- [DAWG/Trie](https://en.wikipedia.org/wiki/Deterministic_acyclic_finite_state_automaton)
- [BK-tree](https://en.wikipedia.org/wiki/BK-tree)
- [Autocomplete at Scale](https://blog.twitter.com/engineering/en_us/a/2015/real-time-autocomplete-search)
