# RailSight — Single Pane of Glass for Railway Field Asset Operations

**A portfolio project built to match the CPKC Analyst Software Developer role.**

---

## The One-Line Pitch

RailSight is a real-time monitoring and incident management platform that streams live telemetry from simulated railway field assets — locomotives, wayside detectors, and radios — over UDP and WebSockets, surfaces failures through an automated alert engine, and responds to operator queries using an AI troubleshooting assistant trained on structured logs and runbooks.

---

## Why This Project Works for You Specifically

Three things from your background map perfectly to this role:

1. **Rover UDP telemetry** — you already transmitted sensor data over UDP from hardware to a laptop. RailSight does exactly the same thing at a larger scale. You can say this directly to the recruiter.
2. **TC Energy** — you've worked in a regulated, mission-critical operations environment. CPKC is the same culture. The words "field assets," "24/7 support," and "on-call rotation" are familiar to you.
3. **Cloud/capstone background** — Docker, cloud deployment, and structured logging are things you can implement and explain confidently.

This project isn't a stretch. It's a direct continuation of work you've already done.

---

## Tech Stack (with JD keyword alignment)

| What You Build | Technology | JD Keyword It Covers |
|---|---|---|
| Telemetry simulator | Python (UDP sockets) | Python, UDP, TCP/IP, field systems |
| Backend API | Python FastAPI | Python, .NET-style REST patterns |
| Real-time streaming | WebSockets | Real-time monitoring, networking |
| Asset state database | PostgreSQL | Data platforms, persistence |
| Alert engine | Python rules engine | Automation, monitoring, troubleshooting |
| Structured logging | JSON logs → OpenSearch (local) | Elastic, structured logging |
| Frontend dashboard | React + TypeScript + Recharts + Leaflet | Single pane of glass |
| AI assistant | Claude API (RAG over logs) | Generative AI, decision-making |
| Health-check automation | Bash + Python scripts | Bash, Python, automation, ITIL |
| Deployment | Docker Compose | Cloud tools, modern dev practices |

**Do not use more than this.** Complexity without purpose looks like padding.

---

## Architecture in Plain English

```
[Python UDP Telemetry Simulator]
        |  UDP packets every 2-5 seconds
        v
[FastAPI Backend]  ←→  [PostgreSQL]
        |
    WebSocket
        |
[React Dashboard]
        |
   [AI Assistant]  ←  [Structured JSON Logs + Runbook Store]
        |
[Bash Health-Check Scripts]
```

The simulator sends fake asset telemetry over UDP to the FastAPI backend, which validates it, writes it to Postgres, and broadcasts updates to the React frontend via WebSocket. The alert engine runs as a background job checking for failures. The AI assistant queries recent logs and runbooks to answer operator questions.

---

## Telemetry Packet Format

Keep this consistent across the whole project. Every asset sends:

```json
{
  "assetId": "LOCO-5821",
  "type": "locomotive",
  "status": "warning",
  "speed": 62,
  "gps": [51.0447, -114.0719],
  "signalStrength": 71,
  "batteryLevel": 88,
  "lastSeen": "2026-06-28T14:32:00Z",
  "sequenceNumber": 4821,
  "radioChannel": "CH-3"
}
```

Asset types to simulate: `locomotive`, `wayside_detector`, `radio_tower`, `track_sensor`

---

## Build Plan — 4 Phases

### Phase 1 — Telemetry Core (Days 1–5)

Build the foundation first. Nothing visible yet, just working data flow.

**UDP Telemetry Simulator (`simulate_assets.py`)**
- Spawn N fake assets as threads
- Each asset sends a UDP packet every 2–5 seconds to `localhost:9000`
- Inject failures randomly: signal drop, missed packets, GPS drift, duplicate sequence numbers
- Command: `python simulate_assets.py --assets 30 --failure-rate 0.10`

**FastAPI UDP Listener + REST API**
- `udp_listener.py` runs a UDP socket server, receives packets, validates schema
- On valid packet: write to PostgreSQL `asset_events` table, update `assets` table (current state)
- On invalid packet: log to `malformed_events` table with reason
- Expose REST endpoints: `GET /assets`, `GET /assets/{id}/history`, `GET /alerts`

**PostgreSQL schema (keep it simple)**
- `assets` — current state of each asset (one row per asset, upserted on each packet)
- `asset_events` — every telemetry packet received (time-series log)
- `alerts` — active and resolved alerts with severity and timestamps
- `runbooks` — static table of runbook entries for AI context

**Goal for Phase 1:** Running `python simulate_assets.py` and `python main.py` produces live data in Postgres. Verify with `psql` queries. No frontend yet.

---

### Phase 2 — Alert Engine + WebSocket Streaming (Days 6–10)

**Alert Engine (Python background task)**

Run as an `asyncio` loop every 30 seconds. Check these rules:

```python
# Rule 1: Asset not seen in 5 minutes
if (now - asset.last_seen).seconds > 300:
    create_alert(asset, "ASSET_OFFLINE", severity="P1")

# Rule 2: Signal strength below threshold
if asset.signal_strength < 40:
    create_alert(asset, "LOW_SIGNAL", severity="P2")

# Rule 3: Locomotive speed is 0 and was >0 in last packet (unexpected stop)
if asset.type == "locomotive" and asset.speed == 0 and prev_speed > 5:
    create_alert(asset, "UNEXPECTED_STOP", severity="P1")

# Rule 4: Duplicate sequence number received
if packet.sequence_number in seen_sequences[asset_id]:
    create_alert(asset, "DUPLICATE_TELEMETRY", severity="P3")
```

Each alert stores: asset ID, rule triggered, severity (P1/P2/P3), timestamp, suggested action, acknowledged status.

**WebSocket endpoint**
- FastAPI WebSocket at `/ws`
- Backend pushes asset state + alert changes to all connected clients in real time
- Payload: `{ "type": "asset_update" | "alert_created" | "alert_resolved", "data": {...} }`

**Goal for Phase 2:** Alerts appear in Postgres. WebSocket connection works (test with `wscat`).

---

### Phase 3 — React Dashboard (Days 11–18)

This is what the recruiter sees. Invest time here.

**Asset Map (Leaflet)**
- Plot all assets on a map of the Canadian prairies
- Color-coded markers: Green (healthy), Yellow (warning), Red (critical), Grey (offline)
- Click a marker → open asset detail panel

**Alert Feed (right sidebar)**
- Live list of active alerts ordered by severity
- P1 = red badge, P2 = orange badge, P3 = yellow badge
- Acknowledge button per alert
- Filters: All / P1 only / By asset type

**Asset Detail Panel**
- Current telemetry (speed, signal, GPS, battery)
- Signal strength over time (line chart, Recharts)
- Incident timeline (see below)

**Incident Timeline (per asset)**

Show this as a vertical timeline component:

```
● 14:01  Signal strength dropped below 50% (74% → 38%)
● 14:03  Missed 2 consecutive telemetry packets
● 14:05  Status changed: healthy → warning
● 14:08  Status changed: warning → critical
● 14:09  Alert P1 created: LOW_SIGNAL
● 14:11  Alert acknowledged by operator
```

**Analytics Page (PowerBI-style)**
- Asset health breakdown: pie chart of Green/Yellow/Red/Grey counts
- Alert volume over last 24h: bar chart
- Top 5 most-alerted assets: ranked list
- Average signal strength trend: line chart

This page alone covers the "Elastic / Dynatrace / PowerBI" requirement from the JD.

**Goal for Phase 3:** The full dashboard is live. Run the simulator, watch assets appear, trigger a failure, watch the alert appear and the timeline update in real time.

---

### Phase 4 — AI Assistant + Automation Scripts (Days 19–25)

**AI Troubleshooting Assistant**

This is the most impressive feature. Build it properly.

Operator types: `"Why is LOCO-5821 in critical status?"`

Your backend:
1. Fetches the last 20 events for LOCO-5821 from `asset_events`
2. Fetches active alerts for LOCO-5821 from `alerts`
3. Looks up matching runbook entries from `runbooks` (keyword match on alert type)
4. Sends all of this as context to the Claude API with a system prompt like:

```
You are an operations assistant for a railway field asset monitoring system.
You will be given recent telemetry events, active alerts, and runbook procedures
for a specific asset. Answer the operator's question clearly and concisely.
Suggest a specific next action. Do not speculate beyond the data provided.
```

5. Returns the AI response to the frontend chat panel

The runbook table should have entries like:
- `LOW_SIGNAL` → "Verify radio channel assignment. Check antenna connection at tower. Confirm asset is within expected coverage zone."
- `ASSET_OFFLINE` → "Attempt radio contact on backup channel. Check last known GPS position. Escalate to field crew if no response within 15 minutes."
- `UNEXPECTED_STOP` → "Check track obstruction reports for that corridor. Contact locomotive engineer directly. Review preceding speed telemetry for anomaly."

**Bash Health-Check Script (`health_check.sh`)**

```bash
#!/bin/bash
echo "=== RailSight Health Check ==="
echo "API:              $(curl -s http://localhost:8000/health | jq -r .status)"
echo "Database:         $(psql -U railsight -c 'SELECT 1' > /dev/null 2>&1 && echo healthy || echo DOWN)"
echo "WebSocket:        $(wscat -c ws://localhost:8000/ws --wait 1 > /dev/null 2>&1 && echo active || echo DOWN)"
echo "Simulator:        $(pgrep -f simulate_assets.py > /dev/null && echo running || echo stopped)"
echo "Active P1 Alerts: $(psql -U railsight -t -c "SELECT COUNT(*) FROM alerts WHERE severity='P1' AND resolved_at IS NULL")"
echo "Assets Online:    $(psql -U railsight -t -c "SELECT COUNT(*) FROM assets WHERE status != 'offline'")"
echo "Total Events 1h:  $(psql -U railsight -t -c "SELECT COUNT(*) FROM asset_events WHERE created_at > NOW() - INTERVAL '1 hour'")"
```

This runs in seconds, looks highly operational, and maps directly to "Bash scripting for automation and system reliability" in the JD.

**Goal for Phase 4:** AI assistant gives useful, context-grounded answers. Health script runs clean. Docker Compose starts everything with one command.

---

## Docker Compose (Final Setup)

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: railsight
      POSTGRES_USER: railsight
      POSTGRES_PASSWORD: railsight
  
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - db
  
  simulator:
    build: ./simulator
    command: python simulate_assets.py --assets 30 --failure-rate 0.10
    depends_on:
      - backend
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
```

One command: `docker compose up`. That's what a recruiter runs in their terminal.

---

## GitHub README Structure

```
# RailSight
Real-Time Field Asset Monitoring and AI-Assisted Troubleshooting for Railway Operations

[screenshot of dashboard here]

## What It Does
[3 sentences, plain English]

## Why I Built It
[1 sentence connecting to your background — mention UDP from Rover]

## Quick Start
docker compose up

## Features
- Live asset map with status color-coding
- Real-time alert engine (P1/P2/P3 severity)
- Incident timeline per asset
- AI troubleshooting assistant over structured logs and runbooks
- Bash health-check automation script
- Analytics dashboard

## Architecture
[paste the ASCII diagram from above]

## Tech Stack
[table]

## Running the Simulator
python simulate_assets.py --assets 30 --failure-rate 0.10

## Triggering a Failure (Demo)
python simulate_assets.py --force-fail LOCO-5821 --type signal_drop
```

---

## 60-Second Recruiter Demo Script

1. Open terminal. Run `docker compose up`. Everything starts.
2. Open the dashboard. 30 assets appear on the map, most green.
3. Run `python simulate_assets.py --force-fail LOCO-5821 --type signal_drop`
4. Watch LOCO-5821 turn yellow, then red in real time on the map.
5. A P1 alert appears in the right sidebar.
6. Click LOCO-5821. Show the incident timeline — the exact sequence of events.
7. Type in the AI chat: `"What happened to LOCO-5821 and what should I do?"`
8. The assistant responds with the signal drop log, missed packets, and the runbook action.
9. Switch to terminal. Run `./health_check.sh`. Output shows everything healthy except 1 P1 alert.
10. Acknowledge the alert in the dashboard. It moves to resolved.

That demo proves: real-time monitoring, alert management, AI integration, scripting, and operational thinking. In 60 seconds.

---

## Resume Bullets (Use One)

**Concise:**
> Built RailSight, a real-time railway field asset monitoring platform streaming simulated locomotive and wayside telemetry over UDP and WebSockets; implemented a Python alert engine with P1/P2/P3 severity rules, an AI troubleshooting assistant over structured logs and runbooks, and Bash health-check automation.

**Stronger (references CPKC language directly):**
> Developed a "single pane of glass" monitoring platform for simulated railway field assets, ingesting live telemetry via UDP into a FastAPI/PostgreSQL backend, surfacing failures through a rule-based alert engine, and providing AI-generated troubleshooting guidance from structured logs and operational runbooks.

**If you want to mention scale:**
> Designed and built a full-stack real-time monitoring system simulating 50+ railway assets across locomotive, wayside detector, radio, and track sensor types; features include live status mapping, incident timeline reconstruction, GenAI-assisted fault diagnosis, and operational health-check scripts aligned with ITIL incident management principles.

---

## Things That Would Make It Even Better (Optional, After MVP)

- **SNMP trap simulation** — add a simple SNMP trap emitter to the simulator. One line in the README explaining it maps directly to CPKC's SNMP requirement.
- **AMQP message queue** — swap direct UDP → FastAPI for UDP → RabbitMQ → FastAPI. Shows you understand messaging protocols.
- **PTC/ETC terminology in the UI** — label things with "Positive Train Control corridor" or "ETC zone" even if simulated. Shows you read the JD carefully.
- **Loom walkthrough video** — 3 minutes. Link it at the top of the README. Most portfolio reviewers watch before they read.

---

## What to Say in the Interview

When asked about this project, use this structure:

*"I built it to understand the operational environment CPKC works in. The core insight from reading the JD was that this team monitors physical field assets in real time, so I needed to simulate that data layer first — which I did using UDP sockets, the same protocol I used for my Rover telemetry project. From there I built the alert engine, the dashboard, and finally the AI assistant that gives operators grounded troubleshooting recommendations from actual event logs rather than generic advice. The thing I'm most proud of is the incident timeline — it reconstructs exactly what happened to an asset and in what order, which I think is what an on-call engineer actually needs at 2am."*

That answer shows systems thinking, not just coding ability.
