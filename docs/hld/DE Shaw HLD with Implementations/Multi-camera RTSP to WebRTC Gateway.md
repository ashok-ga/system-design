---
# Multi-camera RTSP → WebRTC Gateway

## 1. Problem Statement & Requirements
Design a gateway to ingest multiple RTSP (CCTV) feeds, transcode/mux, and serve via WebRTC with per-camera auth and monitoring.

**Functional Requirements:**
- Pull RTSP feeds from cameras (hundreds of sources)
- Transcode/mux to WebRTC-compatible format
- Serve to viewers via WebRTC (1–100 per feed)
- Per-camera authentication and access control
- Health checks and auto-restart for dead feeds
- Metrics and monitoring for all streams

**Non-Functional Requirements:**
- Low-latency (sub-second)
- High reliability, auto-recovery
- Scalable to hundreds of feeds

**Assumptions:**
- GStreamer/NVENC for decode/encode
- SFU for WebRTC fan-out

---
## 2. High-Level Architecture

**Components:**
- **RTSP Puller:** Connects to camera, pulls RTSP stream
- **Decoder/Encoder:** Transcodes to WebRTC format (H.264/Opus)
- **SFU:** Routes streams to viewers
- **Access Control Service:** Authenticates viewers per camera
- **Metrics Service:** Collects stream health, viewer stats
- **Health Checker:** Monitors and restarts dead feeds
- **Storage:** Short buffer (tmpfs), S3 for recordings

**Architecture Diagram:**
```
 [RTSP Puller] -> [Decoder/Encoder] -> [SFU] -> [WebRTC] -> [Viewer]
                                 |
                                 v
                            [Metrics/Health]
```

---
## 3. Data Model & Stream Management

- **Camera:** { id, url, auth, ... }
- **Stream:** { camera_id, status, viewers, bitrate, ... }
- **Viewer:** { id, camera_id, session, ... }

---
## 4. Key Workflows

### a) Feed Ingest & Transcode
1. RTSP Puller connects to camera
2. Decoder/Encoder transcodes to H.264/Opus
3. SFU routes to viewers

### b) Viewer Connect & Auth
1. Viewer requests stream, authenticates
2. Access control checks permissions
3. SFU adds viewer to stream

### c) Health Check & Recovery
1. Health checker monitors stream status
2. On failure, restarts RTSP puller/decoder

---
## 5. Scaling & Reliability

- **Horizontal Scaling:** Multiple pullers/encoders/SFU nodes
- **Auto-recovery:** Health checks and restart logic
- **Metrics:** Per-stream and per-viewer stats

---
## 6. Trade-offs & Alternatives

- **Passthrough vs Re-encode:** Passthrough is lower latency, re-encode allows ABR and format conversion
- **Buffering:** Short buffer for jitter, S3 for long-term recording

---
## 7. Best Practices & Extensions

- Use NVENC for efficient encoding
- Per-camera access control and audit
- Analytics for viewer engagement
- Integrate with VMS (video management system)

---
## 8. Example Pseudocode (Health Checker)
```python
class HealthChecker:
    def __init__(self, streams):
        self.streams = streams
    def check(self):
        for s in self.streams:
            if not s.is_alive():
                s.restart()
```

---
## 9. References
- [GStreamer](https://gstreamer.freedesktop.org/)
- [WebRTC SFU](https://medooze.com/)
