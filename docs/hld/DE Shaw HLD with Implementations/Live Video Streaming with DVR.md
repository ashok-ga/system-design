---
# Live Video Streaming (WebRTC) with DVR (Seekable)

## 1. Problem Statement & Requirements
Design a scalable, low-latency live video streaming platform with DVR (seekable playback) and multi-camera support.

**Functional Requirements:**
- Ingest live video from publishers (WebRTC, RTMP)
- <500ms glass-to-glass latency for live
- DVR: Seekable playback (HLS/DASH fallback)
- Multi-camera support (switching, simulcast)
- Viewer authentication and access control
- Adaptive bitrate (ABR) streaming

**Non-Functional Requirements:**
- 1–10k concurrent viewers
- 100–500 publishers
- High availability, geo-distributed
- Scalable to spikes (e.g., events)

**Assumptions:**
- SFU (Selective Forwarding Unit) for WebRTC
- Object store for DVR segments

---
## 2. High-Level Architecture

**Components:**
- **Ingest Gateway:** Accepts WebRTC/RTMP streams from publishers
- **SFU:** Routes video/audio to viewers, supports simulcast
- **Transcoder:** Optional, for ABR and format conversion
- **Timeshift Buffer:** In-memory ring for short DVR, object store for long DVR
- **CDN:** Distributes HLS/DASH segments to viewers
- **Viewer Gateway:** Authenticates and manages viewer sessions
- **Segment Index:** Tracks available segments for DVR

**Architecture Diagram:**
```
 [Publisher] -> [Ingest] -> [SFU] -> [Transcoder] -> [Timeshift Buffer] -> [CDN] -> [Viewer]
```

---
## 3. Data Model & Segmentation

- **Segment:** { id, camera_id, start_ts, duration, url }
- **DVR Index:** Maps camera_id to list of segments
- **Viewer Session:** { id, user_id, camera_id, live/seek, ... }

---
## 4. Key Workflows

### a) Live Ingest & Routing
1. Publisher connects via WebRTC/RTMP
2. Ingest gateway authenticates and registers stream
3. SFU routes video/audio to viewers (simulcast for ABR)

### b) DVR Recording & Playback
1. Segments written to in-memory ring buffer (short-term)
2. Segments flushed to object store for long-term DVR
3. Segment index updated for seek/playback
4. Viewer requests live or past segment; CDN serves from buffer or object store

### c) Multi-camera & ABR
1. Publisher can switch cameras or simulcast
2. Viewer can select camera/bitrate

---
## 5. Scaling & Reliability

- **Horizontal Scaling:** Multiple ingest/SFU/CDN nodes
- **Geo-distribution:** Edge nodes for low-latency
- **Segment Index:** Distributed, consistent
- **Monitoring:** Latency, segment loss, viewer QoE

---
## 6. Bottlenecks & Mitigations

- **CPU on Transcode:** Use hardware encoders, ladder planning
- **Network Spikes:** CDN and edge cache
- **Segment Loss:** Redundant ingest, segment replication

---
## 7. Best Practices & Extensions

- Use CMAF for low-latency HLS/DASH
- Health checks for publisher streams
- Analytics for viewer engagement
- DRM for premium content

---
## 8. Example Pseudocode (Segment Index)
```python
class SegmentIndex:
    def __init__(self):
        self.index = defaultdict(list)
    def add_segment(self, camera_id, segment):
        self.index[camera_id].append(segment)
    def get_segments(self, camera_id, start, end):
        return [s for s in self.index[camera_id] if start <= s.start_ts < end]
```

---
## 9. References
- [WebRTC SFU](https://medooze.com/)
- [Low-latency HLS/DASH](https://developer.apple.com/documentation/http_live_streaming)
