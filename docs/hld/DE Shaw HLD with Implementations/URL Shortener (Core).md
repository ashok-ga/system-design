# URL Shortener (Core)

## Problem Statement
Shorten URLs, expand codes, and track clicks. Prevent malicious loops.

## Functional Requirements
- `shorten(url, custom?)`, `expand(code)`, basic stats
- Prevent malicious loops

## Core Concepts
- `CodeGenerator` (base62 of counter or hash+collision)
- `UrlMapping(code, longUrl, createdAt, owner)`
- `Store`, `StatsService`

## High-Level Design
- **Shortening:**
    - Generate code (base62 of counter or hash)
    - Store mapping in DB (code → longUrl)
    - Support custom aliases (check for collision)
- **Expanding:**
    - Lookup code in DB, return longUrl
    - Track click stats (increment counter)
- **Malicious Loops:**
    - Validate longUrl is not a shortener domain
- **Caching:**
    - Cache code→longUrl for fast redirects
    - TTL for dead links

## Step-by-Step Solution
1. **CodeGenerator**: base62 encode counter/hash
2. **Store**: mapping and stats
3. **API**: shorten, expand, stats endpoints
4. **Validation**: check for loops, dead links

## Edge Cases
- Custom alias collision
- Expired/deleted links
- Invalid URLs
