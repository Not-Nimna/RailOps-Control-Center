# RailSight Cloud — Single Pane of Glass for Railway Field Asset Operations

**A portfolio project built to match the CPKC Analyst Software Developer role.**
**Architecture: Hybrid UDP Edge Gateway → AWS IoT Core → Serverless Backend → React Dashboard**

---

## The One-Line Pitch

RailSight Cloud simulates railway field assets (locomotives, wayside detectors, radios) sending UDP telemetry to a Python edge gateway, which validates and republishes events to AWS IoT Core over MQTT; cloud-side IoT Rules route data to Lambda, DynamoDB, and Timestream, while a FastAPI WebSocket backend serves a live React dashboard with AI-assisted incident troubleshooting from CloudWatch logs and S3 runbooks.

---

## Why the Hybrid Architecture

Pure MQTT simulators are common in AWS tutorials. Pure UDP-to-local-API is what most monitoring demos do. This project does both, for a reason you can explain:

> "Real railway field assets — locomotives, wayside detectors — speak industrial protocols like UDP and serial. They don't talk directly to the cloud. In the real world, a gateway device sits at the edge, collects that raw telemetry, validates it, and republishes it upstream. That's what the edge gateway component does here."

That explanation alone distinguishes you from candidates who just did the AWS IoT getting-started tutorial.

The hybrid also means you cover every CPKC keyword in one project: **UDP**, **TCP/IP**, **Python**, **Bash**, **cloud tools**, **real-time monitoring**, **automation**, and **Generative AI**.

---

## Full Architecture

```
[Python Asset Simulator]
        |
        |  UDP packets every 2-5 seconds to localhost:9000
        v
[Python Edge Gateway]         ← validates, converts, republishes
        |
        |  MQTT over TLS (port 8883)
        v
[AWS IoT Core]
        |
        |  IoT Rule: SELECT * FROM 'railsight/assets/+/telemetry'
        v
   ┌────┴──────────────────────────────────────────────┐
   ↓                        ↓                          ↓
[Lambda:               [Timestream:              [S3:
 Telemetry Processor]   telemetry history]        raw event archive]
   |
   |  upserts asset state, runs alert rules, updates Device Shadows
   ↓
[DynamoDB:             [DynamoDB:
 railsight-assets]      railsight-alerts]
        |
        v
[FastAPI Backend]      ← reads DynamoDB + Timestream, serves WebSocket
        |
        |  WebSocket (real-time push to dashboard)
        v
[React Dashboard]
        |
        v
[Lambda: AI Assistant] ← CloudWatch Logs + Timestream + S3 Runbooks
```

### Why each AWS service

| Service              | What It Replaces              | Why It's the Right Tool                                                                          |
| -------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------ |
| AWS IoT Core         | Raw UDP listener in FastAPI   | Built for field-device telemetry ingestion at scale; Device Shadow state management included     |
| IoT Rules            | Manual routing code           | Declarative SQL-style rules that fan out to multiple targets without code                        |
| Lambda (processor)   | FastAPI background alert loop | Event-driven; fires immediately on every packet, not on a 30-second poll                         |
| Lambda (EventBridge) | Asyncio scheduled task        | Detects _absence_ of packets (ASSET_OFFLINE rule) on a 1-minute cron                             |
| DynamoDB             | PostgreSQL                    | No server to manage; millisecond reads for WebSocket push; free tier covers the whole project    |
| Timestream           | PostgreSQL asset_events table | Purpose-built time-series DB; native Grafana/QuickSight integration for the analytics page       |
| S3                   | PostgreSQL runbooks table     | Correct place for documents; easy to add/update runbooks without a DB migration                  |
| CloudWatch Logs      | Local OpenSearch              | Lambda logs go here automatically; Log Insights queries match the "Elastic/Dynatrace" JD mention |
| Device Shadows       | assets.current_state column   | IoT-native last-known-state store; survives reconnects and gaps in telemetry                     |

---

## Tech Stack (with JD keyword alignment)

| What You Build            | Technology                              | JD Keyword It Covers                       |
| ------------------------- | --------------------------------------- | ------------------------------------------ |
| Asset simulator           | Python (UDP sockets)                    | Python, UDP, field systems                 |
| Edge gateway              | Python (AWS IoT Device SDK, MQTT)       | Python, TCP/IP, MQTT, networking protocols |
| Cloud telemetry ingestion | AWS IoT Core                            | Cloud tools, field systems, networking     |
| Alert engine              | Python Lambda + EventBridge             | Python, automation, monitoring             |
| Asset state store         | DynamoDB                                | Data platforms, cloud                      |
| Telemetry history         | Timestream                              | Time-series, data platforms                |
| Structured logging        | CloudWatch Logs + Log Insights          | Elastic, Dynatrace, monitoring             |
| Raw archive               | S3                                      | Cloud storage                              |
| REST + WebSocket API      | Python FastAPI                          | Python, real-time monitoring               |
| Frontend dashboard        | React + TypeScript + Recharts + Leaflet | Single pane of glass                       |
| AI assistant              | Claude API (RAG over logs + runbooks)   | Generative AI, decision-making             |
| Health-check automation   | Bash + AWS CLI                          | Bash, Python, automation, ITIL             |
| Local orchestration       | Docker Compose                          | Modern dev practices                       |

---

## MQTT Topic Structure

All assets publish under a consistent topic hierarchy:

```
railsight/assets/{assetId}/telemetry     ← live telemetry packets
railsight/assets/{assetId}/alerts        ← alert notifications (Lambda publishes back)
railsight/system/health                  ← edge gateway heartbeat
```

AWS Device Shadow (managed by IoT Core automatically):

```
$aws/things/{assetId}/shadow/update      ← last known state, survives gaps
```

---

## Telemetry Packet Format

Every asset sends this exact schema. Consistent across simulator, gateway, Lambda, and dashboard:

```json
{
  "assetId": "LOCO-5821",
  "type": "locomotive",
  "status": "warning",
  "speed": 62,
  "gps": [51.0447, -114.0719],
  "signalStrength": 71,
  "batteryLevel": 88,
  "sequenceNumber": 4821,
  "radioChannel": "CH-3",
  "timestamp": "2026-06-28T14:32:00Z"
}
```

Asset types: `locomotive`, `wayside_detector`, `radio_tower`, `track_sensor`

---

## AWS Infrastructure (Set Up Before Writing Code)

Create these manually in the AWS Console or with a setup script before Phase 1.
Region: `ca-central-1` (Calgary — aligns with the CPKC role location).

**IoT Core**

- Thing Type: `railway-asset`
- Things: Create one per asset type for the demo (LOCO-5821, WAYSIDE-104, etc.)
- Certificate: One certificate for the edge gateway (not per-device, to keep setup simple)
- IoT Rule: `RailSightTelemetryRule`

```sql
  SELECT * FROM 'railsight/assets/+/telemetry'
```

Actions: → Lambda (processor), → Timestream (telemetry table), → S3 (raw archive)

**DynamoDB**

- Table `railsight-assets`: partition key = `assetId` (String)
- Table `railsight-alerts`: partition key = `alertId` (String), sort key = `timestamp` (String)
- Enable DynamoDB Streams on `railsight-alerts` (for future WebSocket push)
  **Timestream**
- Database: `railsight`
- Table: `telemetry`
  - Memory store retention: 1 day
  - Magnetic store retention: 7 days
  - Dimensions: `assetId`, `type`, `radioChannel`
  - Measures: `speed`, `signalStrength`, `batteryLevel`, `latitude`, `longitude`
    **S3**
- Bucket: `railsight-runbooks` — stores JSON runbook files
- Bucket: `railsight-events` — IoT Rule writes raw telemetry here (one JSON per event)
  **Lambda**
- Function `railsight-telemetry-processor`: Python 3.12, triggered by IoT Rule
- Function `railsight-offline-checker`: Python 3.12, triggered by EventBridge every 60 seconds
- Function `railsight-ai-assistant`: Python 3.12, triggered by FastAPI HTTP call
  **IAM**
- Lambda execution role: DynamoDB read/write, Timestream write, IoT publish, S3 read, CloudWatch Logs write

---

## Build Plan — 4 Phases

### Phase 1 — Telemetry Core (Days 1–7)

Build the data pipeline end to end. Nothing visual yet.

**Day 1–2: AWS setup**
Complete the infrastructure above. Verify IoT Core is receiving test messages using the MQTT test client in the AWS Console before writing any application code. This step is non-negotiable — debugging AWS config inside your application code is painful.

**Day 2–3: UDP Asset Simulator (`simulate_assets.py`)**

```python
import socket, json, random, time, threading, argparse

ASSET_TYPES = ['locomotive', 'wayside_detector', 'radio_tower', 'track_sensor']
GATEWAY_HOST = '127.0.0.1'
GATEWAY_PORT = 9000

def simulate_asset(asset_id, asset_type, failure_rate):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    seq = 0
    signal = 85.0
    speed = random.uniform(40, 80) if asset_type == 'locomotive' else 0

    while True:
        # Inject failure scenarios
        if random.random() < failure_rate:
            signal = max(10, signal - random.uniform(15, 30))  # signal drop
        else:
            signal = min(95, signal + random.uniform(0, 5))   # recovery

        packet = {
            "assetId": asset_id,
            "type": asset_type,
            "status": "healthy" if signal > 60 else ("warning" if signal > 35 else "critical"),
            "speed": round(speed + random.uniform(-2, 2), 1) if asset_type == 'locomotive' else 0,
            "gps": [51.0447 + random.uniform(-0.5, 0.5), -114.0719 + random.uniform(-2, 2)],
            "signalStrength": round(signal, 1),
            "batteryLevel": random.uniform(70, 100),
            "sequenceNumber": seq,
            "radioChannel": f"CH-{random.randint(1, 5)}",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        sock.sendto(json.dumps(packet).encode(), (GATEWAY_HOST, GATEWAY_PORT))
        seq += 1
        time.sleep(random.uniform(2, 5))
```

Run with: `python simulate_assets.py --assets 30 --failure-rate 0.10`

Also support: `python simulate_assets.py --force-fail LOCO-5821 --type signal_drop`

**Day 3–4: Python Edge Gateway (`edge_gateway.py`)**

This is the most architecturally interesting piece. It's a small but real piece of systems design.

```python
import socket, json, logging
from awsiot import mqtt_connection_builder
from awscrt import mqtt

IOT_ENDPOINT = "your-endpoint.iot.ca-central-1.amazonaws.com"
REQUIRED_FIELDS = {"assetId", "type", "status", "signalStrength", "timestamp", "sequenceNumber"}

def validate_packet(packet: dict) -> tuple[bool, str]:
    missing = REQUIRED_FIELDS - set(packet.keys())
    if missing:
        return False, f"Missing fields: {missing}"
    if packet['signalStrength'] < 0 or packet['signalStrength'] > 100:
        return False, "signalStrength out of range"
    if packet['type'] not in VALID_ASSET_TYPES:
        return False, f"Unknown asset type: {packet['type']}"
    return True, "ok"

def run_gateway():
    # MQTT connection to IoT Core
    mqtt_conn = mqtt_connection_builder.mtls_from_path(
        endpoint=IOT_ENDPOINT,
        cert_filepath="certs/edge-gateway.cert.pem",
        pri_key_filepath="certs/edge-gateway.private.key",
        ca_filepath="certs/root-CA.crt",
        client_id="railsight-edge-gateway"
    )
    mqtt_conn.connect().result()
    logger.info("Edge gateway connected to AWS IoT Core")

    # UDP socket for receiving from simulator
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(('0.0.0.0', 9000))
    logger.info("Listening for UDP telemetry on :9000")

    seen_sequences = {}   # for duplicate detection

    while True:
        data, addr = udp_sock.recvfrom(4096)
        try:
            packet = json.loads(data.decode())
            valid, reason = validate_packet(packet)

            if not valid:
                logger.warning(f"Malformed packet from {addr}: {reason} | raw: {data[:100]}")
                continue

            # Duplicate sequence check
            asset_id = packet['assetId']
            seq = packet['sequenceNumber']
            if asset_id in seen_sequences and seq in seen_sequences[asset_id]:
                logger.warning(f"Duplicate sequence {seq} from {asset_id}")
                # Still publish but tag it
                packet['_duplicate'] = True
            else:
                seen_sequences.setdefault(asset_id, set()).add(seq)

            topic = f"railsight/assets/{asset_id}/telemetry"
            mqtt_conn.publish(
                topic=topic,
                payload=json.dumps(packet),
                qos=mqtt.QoS.AT_LEAST_ONCE
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error from {addr}: {e}")
```

**Day 4–5: Lambda Telemetry Processor**

Triggered by the IoT Rule on every valid telemetry packet:

```python
import boto3, json
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
iot_data = boto3.client('iot-data', region_name='ca-central-1')

assets_table = dynamodb.Table('railsight-assets')
alerts_table = dynamodb.Table('railsight-alerts')

def handler(event, context):
    asset_id = event['assetId']

    # 1. Upsert current asset state in DynamoDB
    assets_table.put_item(Item={
        'assetId': asset_id,
        'type': event['type'],
        'status': event['status'],
        'speed': str(event.get('speed', 0)),
        'gps': event.get('gps', []),
        'signalStrength': str(event['signalStrength']),
        'batteryLevel': str(event.get('batteryLevel', 100)),
        'radioChannel': event.get('radioChannel', 'unknown'),
        'lastSeen': event['timestamp'],
        'sequenceNumber': event['sequenceNumber'],
        'updatedAt': datetime.now(timezone.utc).isoformat()
    })

    # 2. Run alert rules
    run_alert_rules(event)

    # 3. Update Device Shadow (last known good state)
    iot_data.update_thing_shadow(
        thingName=asset_id,
        payload=json.dumps({
            "state": {
                "reported": {
                    "status": event['status'],
                    "signalStrength": event['signalStrength'],
                    "gps": event.get('gps'),
                    "lastSeen": event['timestamp']
                }
            }
        })
    )

def run_alert_rules(event):
    asset_id = event['assetId']
    signal = float(event['signalStrength'])
    speed = float(event.get('speed', 0))

    if signal < 40:
        create_alert(asset_id, "LOW_SIGNAL", "P1" if signal < 20 else "P2",
                     f"Signal at {signal}%. Verify radio channel and antenna.")

    if event['type'] == 'locomotive' and speed == 0:
        # Check if speed was > 0 in previous packet
        prev = assets_table.get_item(Key={'assetId': asset_id}).get('Item', {})
        if float(prev.get('speed', 0)) > 5:
            create_alert(asset_id, "UNEXPECTED_STOP", "P1",
                         "Locomotive stopped unexpectedly. Contact engineer.")

    if event.get('_duplicate'):
        create_alert(asset_id, "DUPLICATE_TELEMETRY", "P3",
                     f"Duplicate sequence {event['sequenceNumber']} received.")

def create_alert(asset_id, rule, severity, suggested_action):
    alert_id = f"{asset_id}-{rule}-{int(datetime.now().timestamp())}"
    alerts_table.put_item(Item={
        'alertId': alert_id,
        'assetId': asset_id,
        'rule': rule,
        'severity': severity,
        'suggestedAction': suggested_action,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'acknowledged': False,
        'resolvedAt': None
    })
```

**Day 5–7: Lambda Offline Checker (EventBridge every 60s)**

The LOW_SIGNAL and UNEXPECTED_STOP rules fire when a packet _arrives_. But ASSET_OFFLINE fires when packets _stop_. This requires a separate scheduled checker:

```python
def handler(event, context):
    now = datetime.now(timezone.utc)
    assets = assets_table.scan()['Items']

    for asset in assets:
        last_seen = datetime.fromisoformat(asset['lastSeen'].replace('Z', '+00:00'))
        seconds_since = (now - last_seen).total_seconds()

        if seconds_since > 300:   # 5 minutes
            create_alert(
                asset['assetId'],
                "ASSET_OFFLINE",
                "P1",
                f"No telemetry for {int(seconds_since)}s. Check power and connectivity."
            )
```

**Goal for Phase 1:** Simulator → gateway → IoT Core → Lambda → DynamoDB/Timestream. Verify in DynamoDB console (items appearing), Timestream query editor (data rows), and S3 bucket (raw JSON files). Device shadows updating. No frontend yet.

---

### Phase 2 — FastAPI Backend + WebSocket Streaming (Days 8–13)

FastAPI no longer touches a database directly. It reads from DynamoDB and Timestream and broadcasts to the React frontend via WebSocket.

**REST endpoints**

```python
@app.get("/assets")
async def get_assets():
    # Scan DynamoDB railsight-assets
    return dynamodb.Table('railsight-assets').scan()['Items']

@app.get("/assets/{asset_id}/history")
async def get_asset_history(asset_id: str, hours: int = 6):
    # Query Timestream for the last N hours of telemetry for this asset
    query = f"""
        SELECT time, signalStrength, speed, batteryLevel
        FROM "railsight"."telemetry"
        WHERE assetId = '{asset_id}'
        AND time > ago({hours}h)
        ORDER BY time ASC
    """
    return timestream_query.query(QueryString=query)['Rows']

@app.get("/alerts")
async def get_alerts(severity: str = None, acknowledged: bool = None):
    # Query DynamoDB railsight-alerts with optional filters
    ...

@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    alerts_table.update_item(
        Key={'alertId': alert_id},
        UpdateExpression='SET acknowledged = :val',
        ExpressionAttributeValues={':val': True}
    )
```

**WebSocket endpoint**

FastAPI polls DynamoDB every 3 seconds and pushes any changes to all connected clients:

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            assets = await fetch_current_assets()
            alerts = await fetch_active_alerts()
            await websocket.send_json({
                "type": "state_update",
                "assets": assets,
                "alerts": alerts,
                "timestamp": datetime.utcnow().isoformat()
            })
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

**Goal for Phase 2:** All REST endpoints return live data from DynamoDB/Timestream. WebSocket connection pushes updates every 3 seconds. Test with `wscat -c ws://localhost:8000/ws`.

---

### Phase 3 — React Dashboard (Days 14–22)

This is what the recruiter sees. Invest time here.

**Asset Map (Leaflet)**

- Plot all assets on a map of the Canadian prairies (centre on Calgary)
- Color-coded markers: Green (healthy), Yellow (warning), Red (critical), Grey (offline)
- Marker icon changes based on asset type: train icon for locomotive, antenna for radio, etc.
- Click a marker → open asset detail panel on the right
  **Alert Feed (right sidebar)**
- Live list of active alerts from the WebSocket state update, ordered by severity
- P1 = red badge, P2 = orange badge, P3 = yellow badge
- Acknowledge button per alert (calls `POST /alerts/{id}/acknowledge`)
- Filters: All / P1 only / Unacknowledged / By asset type
  **Asset Detail Panel**
- Current telemetry from DynamoDB: speed, signal strength, GPS, battery, radio channel
- Signal strength over time: line chart (Recharts) from Timestream `/history` endpoint
- Device Shadow status badge: "Shadow in sync" or "Shadow stale"
- Incident timeline (see below)
  **Incident Timeline (per asset)**

Built from a `GET /assets/{id}/events` endpoint that queries both DynamoDB alert history and Timestream telemetry transitions. Display as a vertical timeline:

```
● 14:01  Signal strength dropped below 50% (74% → 38%)
● 14:03  Missed 2 consecutive telemetry packets
● 14:05  Status changed: healthy → warning
● 14:08  Status changed: warning → critical
● 14:09  Alert P1 created: LOW_SIGNAL
● 14:11  Alert acknowledged by operator
```

**Analytics Page (PowerBI-style)**

Reads from Timestream for all charts. Four panels:

- Asset health breakdown: donut chart (Green/Yellow/Red/Grey counts from DynamoDB scan)
- Alert volume last 24h: bar chart by hour (Timestream aggregation query)
- Top 5 most-alerted assets last 24h: ranked list with bar indicators
- Network signal health trend: line chart of average `signalStrength` across all assets over time
  Add a CloudWatch Log Insights query result as a fifth "system log" panel — paste in a screenshot if live embedding is complex. This is the "Elastic/Dynatrace" analog that proves you know operational dashboarding.

**Goal for Phase 3:** Full dashboard live. Run the simulator, watch assets appear on the map, trigger a force-fail, watch the alert sidebar update within 3 seconds, open the incident timeline, verify the analytics page shows the spike.

---

### Phase 4 — AI Assistant + Automation Scripts (Days 23–30)

**AI Troubleshooting Assistant (Lambda)**

When an operator asks `"Why is LOCO-5821 in critical status?"`, the Lambda function:

1. Queries Timestream: last 20 telemetry records for LOCO-5821
2. Queries DynamoDB: all active alerts for LOCO-5821
3. Fetches matching runbook from S3: `s3://railsight-runbooks/LOW_SIGNAL.json`
4. Fetches recent Lambda logs from CloudWatch Log Insights for LOCO-5821
   Then sends everything to the Claude API:

```python
def build_context(asset_id, telemetry_rows, alerts, runbook, logs):
    return f"""
ASSET: {asset_id}

RECENT TELEMETRY (last 20 readings):
{format_telemetry(telemetry_rows)}

ACTIVE ALERTS:
{format_alerts(alerts)}

RUNBOOK PROCEDURES:
{json.dumps(runbook, indent=2)}

SYSTEM LOG ENTRIES:
{logs}
"""

def handler(event, context):
    asset_id = event['assetId']
    question = event['question']

    ctx = build_context(
        asset_id,
        get_telemetry(asset_id),
        get_alerts(asset_id),
        get_runbook(asset_id),
        get_cloudwatch_logs(asset_id)
    )

    response = anthropic.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system="""You are an operations assistant for a railway field asset monitoring system.
You will be given recent telemetry, active alerts, runbook procedures, and system logs for an asset.
Answer the operator's question clearly and concisely. Suggest one specific next action.
Do not speculate beyond what the data shows. Keep responses under 150 words.""",
        messages=[
            {"role": "user", "content": f"Context:\n{ctx}\n\nQuestion: {question}"}
        ]
    )

    return {"answer": response.content[0].text}
```

S3 runbook files (`LOW_SIGNAL.json`, `ASSET_OFFLINE.json`, `UNEXPECTED_STOP.json`):

```json
{
  "alertType": "LOW_SIGNAL",
  "severity": "P1 if < 20%, P2 if < 40%",
  "immediateActions": ["Verify radio channel assignment matches expected corridor plan", "Check antenna connection at nearest tower (RADIO-TOWER-09 for this zone)", "Confirm asset GPS position — signal issues can indicate zone boundary"],
  "escalationPath": "If unresolved after 15 minutes, escalate to field crew in zone",
  "relatedAlerts": ["ASSET_OFFLINE", "DUPLICATE_TELEMETRY"]
}
```

**Bash Health-Check Script (`health_check.sh`)**

```bash
#!/bin/bash
echo "=== RailSight Cloud Health Check ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# Local services
echo "[LOCAL]"
echo "  Edge Gateway:     $(pgrep -f edge_gateway.py > /dev/null && echo running || echo STOPPED)"
echo "  Simulator:        $(pgrep -f simulate_assets.py > /dev/null && echo running || echo stopped)"
echo "  FastAPI Backend:  $(curl -sf http://localhost:8000/health | jq -r .status 2>/dev/null || echo DOWN)"
echo "  WebSocket:        $(wscat -c ws://localhost:8000/ws --wait 1 > /dev/null 2>&1 && echo active || echo DOWN)"
echo ""

# AWS services
echo "[AWS ca-central-1]"
echo "  IoT Core:         $(aws iot describe-endpoint --endpoint-type iot:Data-ATS --query endpointAddress --output text 2>/dev/null | head -c 30)..."
echo "  DynamoDB Assets:  $(aws dynamodb describe-table --table-name railsight-assets --query 'Table.TableStatus' --output text 2>/dev/null)"
echo "  DynamoDB Alerts:  $(aws dynamodb describe-table --table-name railsight-alerts --query 'Table.TableStatus' --output text 2>/dev/null)"
echo "  Lambda Processor: $(aws lambda get-function-configuration --function-name railsight-telemetry-processor --query 'State' --output text 2>/dev/null)"
echo "  Lambda Checker:   $(aws lambda get-function-configuration --function-name railsight-offline-checker --query 'State' --output text 2>/dev/null)"
echo "  Lambda AI:        $(aws lambda get-function-configuration --function-name railsight-ai-assistant --query 'State' --output text 2>/dev/null)"
echo ""

# Operational status
echo "[OPERATIONS]"
ASSETS_ONLINE=$(aws dynamodb scan --table-name railsight-assets \
  --filter-expression "#s <> :offline" \
  --expression-attribute-names '{"#s":"status"}' \
  --expression-attribute-values '{":offline":{"S":"offline"}}' \
  --select COUNT --query Count --output text 2>/dev/null)
P1_ALERTS=$(aws dynamodb scan --table-name railsight-alerts \
  --filter-expression "severity = :s AND acknowledged = :a" \
  --expression-attribute-values '{":s":{"S":"P1"},":a":{"BOOL":false}}' \
  --select COUNT --query Count --output text 2>/dev/null)
echo "  Assets Online:    ${ASSETS_ONLINE:-unknown}"
echo "  Active P1 Alerts: ${P1_ALERTS:-unknown}"
```

**Goal for Phase 4:** AI assistant gives grounded, data-backed responses. Health script runs in under 5 seconds. All components verified in one terminal window.

---

## Docker Compose (Local Orchestration)

AWS services run in the cloud. Docker Compose only handles what runs locally:

```yaml
services:
  edge-gateway:
    build: ./edge-gateway
    ports:
      - "9000:9000/udp" # receives UDP from simulator
    environment:
      - IOT_ENDPOINT=${IOT_ENDPOINT}
      - AWS_REGION=ca-central-1
    volumes:
      - ./certs:/app/certs:ro
    restart: unless-stopped

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - AWS_REGION=ca-central-1
      - DYNAMODB_ASSETS_TABLE=railsight-assets
      - DYNAMODB_ALERTS_TABLE=railsight-alerts
      - TIMESTREAM_DATABASE=railsight
      - TIMESTREAM_TABLE=telemetry
    depends_on:
      - edge-gateway

  simulator:
    build: ./simulator
    command: python simulate_assets.py --assets 30 --failure-rate 0.10
    depends_on:
      - edge-gateway

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
      - REACT_APP_WS_URL=ws://localhost:8000/ws
```

One command: `docker compose up`. Simulator runs, gateway connects to IoT Core, backend serves the dashboard.

Note in your README: AWS credentials must be configured in the host environment (`aws configure`). IoT certificates must be in `./certs/`.

---

## Repository Structure

```
railsight-cloud/
├── simulator/
│   ├── simulate_assets.py
│   └── Dockerfile
├── edge-gateway/
│   ├── edge_gateway.py       ← the architectural star of the project
│   ├── requirements.txt      ← awsiotsdk, paho-mqtt
│   └── Dockerfile
├── backend/
│   ├── main.py               ← FastAPI app
│   ├── dynamodb_client.py
│   ├── timestream_client.py
│   ├── websocket_manager.py
│   └── Dockerfile
├── lambda/
│   ├── telemetry_processor/
│   │   └── handler.py
│   ├── offline_checker/
│   │   └── handler.py
│   └── ai_assistant/
│       └── handler.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AssetMap.tsx
│   │   │   ├── AlertFeed.tsx
│   │   │   ├── AssetDetail.tsx
│   │   │   ├── IncidentTimeline.tsx
│   │   │   ├── AnalyticsPage.tsx
│   │   │   └── AIAssistant.tsx
│   │   └── App.tsx
│   └── Dockerfile
├── runbooks/                 ← JSON files, uploaded to S3
│   ├── LOW_SIGNAL.json
│   ├── ASSET_OFFLINE.json
│   ├── UNEXPECTED_STOP.json
│   └── DUPLICATE_TELEMETRY.json
├── scripts/
│   └── health_check.sh
├── infra/
│   └── setup_aws.md          ← manual AWS setup steps
├── certs/                    ← gitignored
│   ├── edge-gateway.cert.pem
│   ├── edge-gateway.private.key
│   └── root-CA.crt
├── docker-compose.yml
└── README.md
```

---

## GitHub README Structure

```markdown
# RailSight Cloud

Real-Time Railway Field Asset Monitoring with AWS IoT Core

[dashboard screenshot — most important thing in the README]

## Architecture

[ASCII diagram]

## What It Does

3 sentences. Plain English. No jargon.

## Why the Hybrid Design

UDP at the edge, MQTT to the cloud — the same pattern used in
real industrial IoT deployments where field devices speak legacy
protocols and a gateway bridges them to cloud infrastructure.

## Quick Start

# Prerequisites: AWS credentials configured, IoT certs in ./certs/

docker compose up

## Triggering a Failure (Demo Mode)

python simulate_assets.py --force-fail LOCO-5821 --type signal_drop

## AWS Infrastructure

See infra/setup_aws.md for the manual setup steps.
Services used: IoT Core, Lambda, DynamoDB, Timestream, S3, CloudWatch

## Tech Stack

[table]

## Running the Health Check

./scripts/health_check.sh
```

---

## 60-Second Recruiter Demo Script

1. Terminal A: `docker compose up`. Edge gateway connects to IoT Core. Simulator starts.
2. Open dashboard at `localhost:3000`. 30 assets appear on the Alberta map, mostly green.
3. Terminal B: `python simulate_assets.py --force-fail LOCO-5821 --type signal_drop`
4. On the map, LOCO-5821 turns yellow then red within one WebSocket cycle (≤3 seconds).
5. P1 alert appears in the sidebar: "LOW_SIGNAL — Signal at 18%."
6. Click LOCO-5821. Show the incident timeline — exact sequence of telemetry events.
7. Show the signal strength chart: Recharts line dropping from 74 to 18 over 5 readings.
8. Type in the AI chat: `"What happened to LOCO-5821?"`
9. AI responds with signal drop sequence, Timestream data points, and runbook action.
10. Terminal B: `./scripts/health_check.sh`. All green except "Active P1 Alerts: 1".
11. Click Acknowledge in the dashboard. Alert moves to resolved.
12. Optional: Open AWS Console → IoT Core → MQTT Test Client → subscribe to `railsight/assets/LOCO-5821/telemetry`. Show raw packets arriving. This one moment proves the whole cloud pipeline is real.

---

## Resume Bullets (Use One)

**Concise:**

> Built RailSight Cloud, a hybrid railway asset monitoring platform where simulated field assets send UDP telemetry to a Python edge gateway that republishes to AWS IoT Core over MQTT; implemented IoT Rules, Lambda-based alert engines, DynamoDB/Timestream persistence, a FastAPI WebSocket backend, React dashboard, and AI-assisted troubleshooting from CloudWatch logs and S3 runbooks.

**Stronger:**

> Designed and built a "single pane of glass" railway field asset monitoring system using a hybrid IoT architecture: UDP telemetry from simulated locomotives, wayside detectors, and radio towers flows through a Python edge gateway to AWS IoT Core, where Lambda functions enforce P1/P2/P3 alert rules, Timestream stores time-series telemetry, and a React dashboard surfaces live asset status, incident timelines, and GenAI-assisted troubleshooting recommendations.

**With scale:**

> Architected RailSight Cloud, a full-stack real-time monitoring platform simulating 50+ railway field assets across four asset types; edge gateway bridges UDP telemetry to AWS IoT Core over MQTT, IoT Rules fan out to Lambda (alert engine), Timestream (history), and DynamoDB (state); React dashboard provides live status map, incident reconstruction, and AI troubleshooting aligned with ITIL P1/P2/P3 severity model.

---

## What to Say in the Interview

> "The core architectural decision was the edge gateway. I could have just had the simulator publish MQTT directly to IoT Core, but that wouldn't reflect how real railway field systems actually work — those assets use legacy protocols like UDP and serial, not MQTT. So I added a gateway layer that bridges UDP to MQTT before it hits the cloud. That decision gave me a natural place to do schema validation, duplicate detection, and malformed-packet logging before anything reaches AWS, which is exactly the kind of concern you'd have in a mission-critical system. The Rover project I built during school used the same pattern — we transmitted sensor data over UDP to a local receiver, and I basically extended that idea to the cloud here."

That answer shows systems design reasoning, domain awareness, and a direct connection to your own prior work. That combination is hard to fake and hard to forget.

---

## Optional Enhancements After MVP

- **SNMP trap simulation** — add a separate thread in the simulator that emits SNMP traps (using pysnmp) when an asset goes offline. One bullet in the README, one mention in the interview. Covers CPKC's explicit SNMP requirement.
- **AMQP/RabbitMQ** — add a RabbitMQ container between the edge gateway and the simulator to buffer UDP bursts before publishing to IoT Core. Covers the AMQP requirement.
- **PTC/ETC zone labels** — add a `ptcZone` or `etcCorridor` field to telemetry packets and display it on the map. No real implementation needed — just naming conventions that show you read the JD.
- **Loom walkthrough** — 3 minutes, link at the top of the README. Most portfolio reviewers watch before they read. Record it last, once everything works cleanly.
- **AWS CDK or CloudFormation template** — replace `infra/setup_aws.md` with an actual IaC script. Shows modern DevOps awareness and makes the project reproducible.
