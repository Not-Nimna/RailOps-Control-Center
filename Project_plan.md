# RailSight Cloud — Single Pane of Glass for Railway Field Asset Operations

**A portfolio project built to match the CPKC Analyst Software Developer role.**
**Architecture: Hybrid UDP Edge Gateway → AWS IoT Core → Serverless Backend → React Dashboard**
**Runs entirely within the AWS Free Tier.**

---

## AWS Free Tier — What You're Using and Why It's Safe

Before anything else, here is exactly what this project uses and why each service stays free:

| Service         | Free Tier Limit                     | This Project's Usage                                | Safe?                                             |
| --------------- | ----------------------------------- | --------------------------------------------------- | ------------------------------------------------- |
| Lambda          | 1M requests/month, always free      | ~1 invocation per telemetry packet                  | ✅ Yes                                            |
| DynamoDB        | 25 WCU / 25 RCU / 25GB, always free | 3 tables, ~3 writes/second during demos             | ✅ Yes                                            |
| IoT Core        | 250K messages/month (12 months)     | ~65K messages per demo hour at recommended settings | ✅ Yes if you follow the simulator settings below |
| S3              | 5GB / 2,000 PUTs/month (12 months)  | Runbooks only — 5–10 PUTs ever, done manually       | ✅ Yes                                            |
| CloudWatch Logs | 5GB ingestion/month, always free    | Lambda logs only                                    | ✅ Yes                                            |
| EventBridge     | 14M events/month, always free       | 1 event/minute for offline checker                  | ✅ Yes                                            |

**What was removed and why:**

- **Timestream** — no free tier at all. Charges per write, per query, and per GB stored. Replaced with a DynamoDB telemetry table using TTL (auto-expiry after 24 hours). Same data, zero cost.
- **S3 events bucket** — the IoT Rule would write one file per telemetry packet. At 30 assets running for 2 hours, that's ~21,600 PUTs. Free tier only gives 2,000 per month. Removed. Raw event archiving is handled by CloudWatch Logs via Lambda instead.

**One critical simulator setting for IoT Core free tier:**

In AWS mode, the simulator must send every **10 seconds**, not every 2–5 seconds. At 10 seconds:

```
30 assets × 6 packets/minute = 180 packets/minute
180 × 60 minutes × ~8 hours of demo time/month = ~86,400 messages
```

That's well under the 250K monthly free limit. For local UDP testing before AWS is involved, 2–5 seconds is fine.

---

## The One-Line Pitch

RailSight Cloud simulates railway field assets sending UDP telemetry to a Python edge gateway, which validates and republishes to AWS IoT Core over MQTT; IoT Rules route data to Lambda and DynamoDB, a FastAPI WebSocket backend serves a live React dashboard, and an AI assistant provides grounded troubleshooting recommendations from CloudWatch logs and S3 runbooks — all within the AWS free tier.

---

## Why the Hybrid Architecture

Pure MQTT simulators are common in AWS tutorials. Pure UDP-to-local-API is what most monitoring demos do. This project does both, for a reason you can explain:

> "Real railway field assets — locomotives, wayside detectors — speak industrial protocols like UDP and serial. They don't talk directly to the cloud. In the real world, a gateway device sits at the edge, collects raw telemetry, validates it, and republishes it upstream. That's what the edge gateway does here."

That explanation distinguishes you from candidates who just followed the AWS IoT getting-started tutorial.

---

## Full Architecture

```
[Python Asset Simulator]
        |
        |  UDP packets every 10 seconds (AWS mode)
        v
[Python Edge Gateway]         ← validates, converts UDP → MQTT
        |
        |  MQTT over TLS (port 8883)
        v
[AWS IoT Core]
        |
        |  IoT Rule: SELECT * FROM 'railsight/assets/+/telemetry'
        v
[Lambda: Telemetry Processor]
        |
   ┌────┴──────────────────────────────────┐
   ↓                                       ↓
[DynamoDB: railsight-assets]    [DynamoDB: railsight-telemetry]
 current state per asset         every packet, TTL = 24 hours

[DynamoDB: railsight-alerts]    [S3: railsight-runbooks]
 active + resolved alerts        JSON runbook files (manual upload)

[Lambda: Offline Checker]       ← EventBridge every 60 seconds
        |
        v
[FastAPI Backend]               ← reads DynamoDB, serves WebSocket + REST
        |
        |  WebSocket
        v
[React Dashboard]
        |
        v
[Lambda: AI Assistant]          ← CloudWatch Logs + DynamoDB + S3 runbooks
```

---

## Tech Stack (with JD keyword alignment)

| What You Build            | Technology                              | JD Keyword It Covers                       |
| ------------------------- | --------------------------------------- | ------------------------------------------ |
| Asset simulator           | Python (UDP sockets)                    | Python, UDP, field systems                 |
| Edge gateway              | Python (AWS IoT Device SDK, MQTT)       | Python, TCP/IP, MQTT, networking protocols |
| Cloud telemetry ingestion | AWS IoT Core                            | Cloud tools, field systems                 |
| Alert engine              | Python Lambda + EventBridge             | Python, automation, monitoring             |
| Asset state store         | DynamoDB (`railsight-assets`)           | Data platforms, cloud                      |
| Telemetry history         | DynamoDB (`railsight-telemetry`) + TTL  | Time-series, data platforms                |
| Structured logging        | CloudWatch Logs + Log Insights          | Elastic, Dynatrace, monitoring             |
| Runbook store             | S3 (`railsight-runbooks`)               | Cloud storage                              |
| REST + WebSocket API      | Python FastAPI                          | Python, real-time monitoring               |
| Frontend dashboard        | React + TypeScript + Recharts + Leaflet | Single pane of glass                       |
| AI assistant              | Claude API (RAG over logs + runbooks)   | Generative AI, decision-making             |
| Health-check automation   | Bash + AWS CLI                          | Bash, Python, automation, ITIL             |
| Local orchestration       | Docker Compose                          | Modern dev practices                       |

---

## MQTT Topic Structure

```
railsight/assets/{assetId}/telemetry     ← live telemetry from edge gateway
railsight/assets/{assetId}/alerts        ← Lambda publishes alerts back to IoT Core
railsight/system/health                  ← edge gateway heartbeat

$aws/things/{assetId}/shadow/update      ← Device Shadow (last known state)
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

## AWS Infrastructure Setup (Do This First, Before Writing Code)

Region: `ca-central-1`. Do this in order.

**Step 1 — DynamoDB tables**

Create three tables with default settings (provisioned, 5 RCU / 5 WCU each — all within free tier):

`railsight-assets`

- Partition key: `assetId` (String)
- Stores current state — one row per asset, upserted on every packet

`railsight-telemetry`

- Partition key: `assetId` (String)
- Sort key: `timestamp` (String)
- Enable TTL on attribute `expiresAt` (Number)
- This replaces Timestream — stores every telemetry packet, auto-deleted after 24 hours

`railsight-alerts`

- Partition key: `alertId` (String)
- Sort key: `timestamp` (String)

**Step 2 — S3 bucket (runbooks only)**

Create one bucket: `railsight-runbooks-{yourname}-2026`

This bucket only ever receives ~5–10 manual PUTs (one per runbook file you upload). No IoT Rule writes to it. Well within free tier.

Keep all defaults from the S3 creation screen — SSE-S3 encryption, ACLs disabled, block all public access.

**Step 3 — AWS IoT Core**

- Create a Thing Type called `railway-asset`
- Create one certificate for the edge gateway (not per-device)
- Download: `edge-gateway.cert.pem`, `edge-gateway.private.key`, `root-CA.crt`
- Attach a policy to the certificate that allows:
  ```json
  {
    "Effect": "Allow",
    "Action": ["iot:Publish", "iot:Connect"],
    "Resource": "arn:aws:iot:ca-central-1:*:topic/railsight/*"
  }
  ```
- Create IoT Rule `RailSightTelemetryRule`:
  ```sql
  SELECT * FROM 'railsight/assets/+/telemetry'
  ```
  One action: → Lambda (`railsight-telemetry-processor`)
  When prompted, let the console create a new IAM role — it auto-generates the correct permissions.

**Step 4 — Lambda functions**

Create three functions (Python 3.12):

- `railsight-telemetry-processor` — triggered by IoT Rule
- `railsight-offline-checker` — triggered by EventBridge (rate: 1 minute)
- `railsight-ai-assistant` — triggered by FastAPI HTTP call (URL not needed; invoke via boto3)

IAM role for all Lambda functions needs:

- `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:Query`, `dynamodb:UpdateItem`, `dynamodb:Scan` on all three tables
- `s3:GetObject` on `railsight-runbooks-*`
- `iot:Publish` on `railsight/*`
- `logs:CreateLogGroup`, `logs:CreateLogDelivery`, `logs:PutLogEvents` (CloudWatch — auto-added by Lambda console)
- `iot:UpdateThingShadow` on all things

**Step 5 — EventBridge rule**

Create a rule with a schedule: `rate(1 minute)`. Target: `railsight-offline-checker` Lambda.

**Verify before writing any application code:**

Go to IoT Core → MQTT test client → subscribe to `railsight/assets/#`. Publish a manual test message to `railsight/assets/LOCO-5821/telemetry`. Check the Lambda CloudWatch logs confirm the function was invoked. Check DynamoDB `railsight-assets` shows a row for `LOCO-5821`. If this works, your cloud pipeline is confirmed.

---

## Build Plan — 4 Phases

### Phase 1 — Telemetry Core (Days 1–7)

Build the data pipeline end to end. Nothing visual yet.

**UDP Asset Simulator (`simulate_assets.py`)**

```python
import socket, json, random, time, threading, argparse
from datetime import datetime, timezone

GATEWAY_HOST = '127.0.0.1'
GATEWAY_PORT = 9000
ASSET_TYPES = ['locomotive', 'wayside_detector', 'radio_tower', 'track_sensor']

def simulate_asset(asset_id, asset_type, failure_rate, interval_seconds):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    seq = 0
    signal = 85.0
    speed = random.uniform(40, 80) if asset_type == 'locomotive' else 0

    while True:
        if random.random() < failure_rate:
            signal = max(10, signal - random.uniform(15, 30))
        else:
            signal = min(95, signal + random.uniform(0, 5))

        packet = {
            "assetId": asset_id,
            "type": asset_type,
            "status": "healthy" if signal > 60 else ("warning" if signal > 35 else "critical"),
            "speed": round(speed + random.uniform(-2, 2), 1) if asset_type == 'locomotive' else 0,
            "gps": [51.0447 + random.uniform(-0.5, 0.5), -114.0719 + random.uniform(-2, 2)],
            "signalStrength": round(signal, 1),
            "batteryLevel": round(random.uniform(70, 100), 1),
            "sequenceNumber": seq,
            "radioChannel": f"CH-{random.randint(1, 5)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        sock.sendto(json.dumps(packet).encode(), (GATEWAY_HOST, GATEWAY_PORT))
        seq += 1
        time.sleep(interval_seconds)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--assets', type=int, default=30)
    parser.add_argument('--failure-rate', type=float, default=0.10)
    parser.add_argument('--interval', type=float, default=10.0,
                        help='Seconds between packets. Use 10+ for AWS mode (free tier).')
    parser.add_argument('--force-fail', type=str, help='Asset ID to force into failure')
    parser.add_argument('--fail-type', type=str, default='signal_drop')
    args = parser.parse_args()

    print(f"Starting {args.assets} assets | interval={args.interval}s | failure-rate={args.failure_rate}")
    print(f"Estimated IoT Core messages/hour: {args.assets * (3600 / args.interval):.0f}")

    threads = []
    for i in range(args.assets):
        asset_type = ASSET_TYPES[i % len(ASSET_TYPES)]
        asset_id = f"{asset_type.upper().replace('_','-')}-{1000 + i}"
        t = threading.Thread(target=simulate_asset,
                             args=(asset_id, asset_type, args.failure_rate, args.interval))
        t.daemon = True
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
```

Usage:

```bash
# AWS mode (free tier safe)
python simulate_assets.py --assets 30 --failure-rate 0.10 --interval 10

# Local testing (fast, no AWS)
python simulate_assets.py --assets 30 --failure-rate 0.10 --interval 2

# Force a failure for demo
python simulate_assets.py --force-fail LOCO-1000 --fail-type signal_drop --interval 10
```

**Python Edge Gateway (`edge_gateway.py`)**

```python
import socket, json, logging
from datetime import datetime, timezone
from awsiot import mqtt_connection_builder
from awscrt import mqtt

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [GATEWAY] %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

IOT_ENDPOINT = "your-endpoint.iot.ca-central-1.amazonaws.com"
REQUIRED_FIELDS = {"assetId", "type", "status", "signalStrength", "timestamp", "sequenceNumber"}
VALID_TYPES = {"locomotive", "wayside_detector", "radio_tower", "track_sensor"}

def validate(packet):
    missing = REQUIRED_FIELDS - set(packet.keys())
    if missing:
        return False, f"Missing fields: {missing}"
    if not 0 <= packet['signalStrength'] <= 100:
        return False, f"signalStrength out of range: {packet['signalStrength']}"
    if packet['type'] not in VALID_TYPES:
        return False, f"Unknown type: {packet['type']}"
    return True, "ok"

def run():
    mqtt_conn = mqtt_connection_builder.mtls_from_path(
        endpoint=IOT_ENDPOINT,
        cert_filepath="certs/edge-gateway.cert.pem",
        pri_key_filepath="certs/edge-gateway.private.key",
        ca_filepath="certs/root-CA.crt",
        client_id="railsight-edge-gateway"
    )
    mqtt_conn.connect().result()
    logger.info("Connected to AWS IoT Core")

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(('0.0.0.0', 9000))
    logger.info("Listening for UDP on :9000")

    seen_sequences = {}
    packets_forwarded = 0
    packets_rejected = 0

    while True:
        data, addr = udp_sock.recvfrom(4096)
        try:
            packet = json.loads(data.decode())
            valid, reason = validate(packet)

            if not valid:
                packets_rejected += 1
                logger.warning(f"REJECTED from {addr}: {reason}")
                continue

            asset_id = packet['assetId']
            seq = packet['sequenceNumber']
            is_duplicate = seq in seen_sequences.get(asset_id, set())

            if is_duplicate:
                logger.warning(f"DUPLICATE seq={seq} from {asset_id}")
                packet['_duplicate'] = True
            else:
                seen_sequences.setdefault(asset_id, set()).add(seq)

            topic = f"railsight/assets/{asset_id}/telemetry"
            mqtt_conn.publish(topic=topic, payload=json.dumps(packet),
                              qos=mqtt.QoS.AT_LEAST_ONCE)

            packets_forwarded += 1
            if packets_forwarded % 100 == 0:
                logger.info(f"Forwarded {packets_forwarded} packets | Rejected {packets_rejected}")

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error from {addr}: {e}")

if __name__ == "__main__":
    run()
```

**Lambda: Telemetry Processor**

This is the core of the cloud pipeline. Triggered by IoT Rule on every valid packet:

```python
import boto3, json, os
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb', region_name='ca-central-1')
iot_data = boto3.client('iot-data', region_name='ca-central-1')

assets_table = dynamodb.Table('railsight-assets')
telemetry_table = dynamodb.Table('railsight-telemetry')
alerts_table = dynamodb.Table('railsight-alerts')

TTL_SECONDS = 86400   # 24 hours — keeps DynamoDB small and free

def handler(event, context):
    asset_id = event['assetId']
    now = datetime.now(timezone.utc)
    expires_at = int(now.timestamp()) + TTL_SECONDS

    # 1. Upsert current state
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
        'updatedAt': now.isoformat()
    })

    # 2. Write to telemetry history (replaces Timestream)
    #    TTL auto-deletes after 24 hours — keeps DynamoDB usage minimal
    telemetry_table.put_item(Item={
        'assetId': asset_id,
        'timestamp': event['timestamp'],
        'status': event['status'],
        'speed': str(event.get('speed', 0)),
        'signalStrength': str(event['signalStrength']),
        'batteryLevel': str(event.get('batteryLevel', 100)),
        'latitude': str(event['gps'][0]) if event.get('gps') else '0',
        'longitude': str(event['gps'][1]) if event.get('gps') else '0',
        'expiresAt': expires_at    # DynamoDB TTL attribute
    })

    # 3. Run alert rules
    run_alert_rules(event, now)

    # 4. Update Device Shadow
    try:
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
    except Exception as e:
        print(f"Shadow update failed for {asset_id}: {e}")

def run_alert_rules(event, now):
    asset_id = event['assetId']
    signal = float(event['signalStrength'])
    speed = float(event.get('speed', 0))

    if signal < 40:
        severity = "P1" if signal < 20 else "P2"
        create_alert(asset_id, "LOW_SIGNAL", severity,
                     f"Signal at {signal}%. Verify radio channel and antenna.", now)

    if event['type'] == 'locomotive' and speed == 0:
        prev = assets_table.get_item(Key={'assetId': asset_id}).get('Item', {})
        if float(prev.get('speed', 0)) > 5:
            create_alert(asset_id, "UNEXPECTED_STOP", "P1",
                         "Locomotive stopped unexpectedly. Contact engineer directly.", now)

    if event.get('_duplicate'):
        create_alert(asset_id, "DUPLICATE_TELEMETRY", "P3",
                     f"Duplicate sequence {event['sequenceNumber']} from {asset_id}.", now)

def create_alert(asset_id, rule, severity, suggested_action, now):
    alert_id = f"{asset_id}-{rule}-{int(now.timestamp())}"
    alerts_table.put_item(Item={
        'alertId': alert_id,
        'assetId': asset_id,
        'rule': rule,
        'severity': severity,
        'suggestedAction': suggested_action,
        'timestamp': now.isoformat(),
        'acknowledged': False,
        'resolvedAt': None
    })
    print(f"ALERT created: {severity} {rule} for {asset_id}")
```

**Lambda: Offline Checker (EventBridge every 60s)**

```python
from datetime import datetime, timezone
import boto3

dynamodb = boto3.resource('dynamodb', region_name='ca-central-1')
assets_table = dynamodb.Table('railsight-assets')

def handler(event, context):
    now = datetime.now(timezone.utc)
    assets = assets_table.scan()['Items']

    for asset in assets:
        last_seen_str = asset.get('lastSeen', '')
        if not last_seen_str:
            continue
        last_seen = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
        seconds_since = (now - last_seen).total_seconds()

        if seconds_since > 300:    # 5 minutes
            create_alert(
                asset['assetId'], "ASSET_OFFLINE", "P1",
                f"No telemetry for {int(seconds_since)}s. Check power, radio, and last GPS position.",
                now
            )
            print(f"OFFLINE: {asset['assetId']} — last seen {int(seconds_since)}s ago")
```

**Goal for Phase 1:** Simulator → gateway → IoT Core → Lambda. Verify in DynamoDB console: rows in `railsight-assets` and `railsight-telemetry`. Check CloudWatch Logs for Lambda to confirm invocations. No frontend yet.

---

### Phase 2 — FastAPI Backend + WebSocket Streaming (Days 8–13)

FastAPI reads from DynamoDB. All history that previously came from Timestream now comes from `railsight-telemetry`.

**Telemetry history endpoint (replaces Timestream query)**

```python
from boto3.dynamodb.conditions import Key
from decimal import Decimal
import json

def decimal_to_float(obj):
    """DynamoDB returns Decimals — convert for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

@app.get("/assets/{asset_id}/history")
async def get_asset_history(asset_id: str, limit: int = 20):
    response = telemetry_table.query(
        KeyConditionExpression=Key('assetId').eq(asset_id),
        ScanIndexForward=False,   # newest first
        Limit=limit
    )
    return json.loads(json.dumps(response['Items'], default=decimal_to_float))
```

**REST endpoints**

```python
@app.get("/assets")
async def get_assets():
    items = assets_table.scan()['Items']
    return json.loads(json.dumps(items, default=decimal_to_float))

@app.get("/assets/{asset_id}/history")
async def get_asset_history(asset_id: str, limit: int = 20):
    # Query railsight-telemetry, sorted newest-first
    ...

@app.get("/alerts")
async def get_alerts(severity: str = None, acknowledged: bool = None):
    # Scan railsight-alerts with optional filter expression
    ...

@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, timestamp: str):
    alerts_table.update_item(
        Key={'alertId': alert_id, 'timestamp': timestamp},
        UpdateExpression='SET acknowledged = :val',
        ExpressionAttributeValues={':val': True}
    )

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
```

**WebSocket — polls DynamoDB every 3 seconds**

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            assets = assets_table.scan()['Items']
            alerts = alerts_table.scan(
                FilterExpression=Attr('acknowledged').eq(False)
            )['Items']
            await websocket.send_json({
                "type": "state_update",
                "assets": json.loads(json.dumps(assets, default=decimal_to_float)),
                "alerts": json.loads(json.dumps(alerts, default=decimal_to_float)),
                "timestamp": datetime.utcnow().isoformat()
            })
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

**Goal for Phase 2:** All endpoints return live DynamoDB data. WebSocket pushes updates. Test with `wscat -c ws://localhost:8000/ws` and watch JSON arrive every 3 seconds.

---

### Phase 3 — React Dashboard (Days 14–22)

**Asset Map (Leaflet)**

- Plot all assets on a map centred on Calgary (51.0447, -114.0719)
- Color-coded markers: Green (healthy), Yellow (warning), Red (critical), Grey (offline)
- Different icons per asset type — train for locomotive, antenna for radio tower, sensor for wayside
- Click marker → asset detail panel opens on the right

**Alert Feed (right sidebar)**

- Live alert list from WebSocket, ordered P1 → P2 → P3
- P1 = red badge, P2 = orange, P3 = yellow
- Acknowledge button per alert
- Filter bar: All / P1 only / Unacknowledged / By type

**Asset Detail Panel**

- Current telemetry from DynamoDB: speed, signal strength, GPS, battery, radio channel
- Device Shadow badge: "Shadow in sync" if `lastSeen` within last 30 seconds
- Signal strength line chart (Recharts) from `/assets/{id}/history` endpoint
- Incident timeline below the chart

**Incident Timeline**

Constructed in the frontend by combining alert history and telemetry status changes:

```
● 14:01  Signal dropped below 50% (74% → 38%)
● 14:03  Status changed: healthy → warning
● 14:08  Status changed: warning → critical
● 14:09  P1 Alert created: LOW_SIGNAL
● 14:11  Alert acknowledged by operator
```

**Analytics Page (aggregation done in FastAPI, not a database)**

Because Timestream is gone, aggregations are computed in Python using the DynamoDB telemetry scan. For 30 assets, this is fast enough for a portfolio project:

```python
@app.get("/analytics/summary")
async def get_analytics_summary():
    # Asset health breakdown
    assets = assets_table.scan()['Items']
    status_counts = {"healthy": 0, "warning": 0, "critical": 0, "offline": 0}
    for a in assets:
        status_counts[a.get('status', 'offline')] += 1

    # Average signal strength (from recent telemetry across all assets)
    all_telemetry = telemetry_table.scan(Limit=500)['Items']
    avg_signal = sum(float(t['signalStrength']) for t in all_telemetry) / max(len(all_telemetry), 1)

    # Top 5 most-alerted assets (last 24h)
    all_alerts = alerts_table.scan()['Items']
    from collections import Counter
    alert_counts = Counter(a['assetId'] for a in all_alerts)
    top_alerted = alert_counts.most_common(5)

    return {
        "statusCounts": status_counts,
        "averageSignalStrength": round(avg_signal, 1),
        "topAlertedAssets": [{"assetId": k, "count": v} for k, v in top_alerted],
        "totalActiveAlerts": sum(1 for a in all_alerts if not a.get('acknowledged'))
    }
```

Four dashboard panels using this endpoint:

- Donut chart: asset health breakdown
- Bar chart: alert counts per asset (top 5)
- Stat card: average signal strength across fleet
- Stat card: total active P1 alerts

This directly demonstrates the "Elastic / Dynatrace / PowerBI" monitoring awareness from the JD.

**Goal for Phase 3:** Full dashboard live and updating in real time. Run the force-fail command and watch the map, alert feed, and timeline all update within one WebSocket cycle.

---

### Phase 4 — AI Assistant + Automation Scripts (Days 23–30)

**AI Troubleshooting Assistant (Lambda)**

```python
import boto3, json, anthropic
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='ca-central-1')
s3 = boto3.client('s3', region_name='ca-central-1')
logs_client = boto3.client('logs', region_name='ca-central-1')
anthropic_client = anthropic.Anthropic()

RUNBOOKS_BUCKET = 'railsight-runbooks-yourname-2026'

def handler(event, context):
    asset_id = event['assetId']
    question = event['question']

    # 1. Last 20 telemetry readings from DynamoDB
    telemetry = dynamodb.Table('railsight-telemetry').query(
        KeyConditionExpression=Key('assetId').eq(asset_id),
        ScanIndexForward=False, Limit=20
    )['Items']

    # 2. Active alerts for this asset
    alerts = dynamodb.Table('railsight-alerts').scan(
        FilterExpression='assetId = :id AND acknowledged = :a',
        ExpressionAttributeValues={':id': asset_id, ':a': False}
    )['Items']

    # 3. Runbooks matching active alert types
    runbooks = []
    for alert in alerts:
        try:
            obj = s3.get_object(Bucket=RUNBOOKS_BUCKET, Key=f"{alert['rule']}.json")
            runbooks.append(json.loads(obj['Body'].read()))
        except Exception:
            pass

    # 4. Recent Lambda log entries mentioning this asset
    logs = get_recent_logs(asset_id)

    # 5. Build context and call Claude
    context_text = f"""
ASSET: {asset_id}

RECENT TELEMETRY (newest first):
{json.dumps([{k: float(v) if isinstance(v, Decimal) else v for k, v in t.items()
              if k not in ('expiresAt',)} for t in telemetry], indent=2)}

ACTIVE ALERTS:
{json.dumps(alerts, indent=2, default=str)}

RUNBOOK PROCEDURES:
{json.dumps(runbooks, indent=2)}

SYSTEM LOG ENTRIES:
{logs}
"""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system="""You are an operations assistant for a railway field asset monitoring system.
You are given recent telemetry, active alerts, runbook procedures, and system logs for an asset.
Answer the operator's question clearly. Suggest one specific next action.
Do not speculate beyond what the data shows. Keep responses under 150 words.""",
        messages=[{"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {question}"}]
    )

    return {"answer": response.content[0].text, "assetId": asset_id}

def get_recent_logs(asset_id):
    try:
        response = logs_client.filter_log_events(
            logGroupName='/aws/lambda/railsight-telemetry-processor',
            filterPattern=asset_id,
            limit=20
        )
        return '\n'.join(e['message'] for e in response['events'])
    except Exception:
        return "No recent log entries found."
```

S3 runbook files — upload these manually to your runbooks bucket:

`LOW_SIGNAL.json`

```json
{
  "alertType": "LOW_SIGNAL",
  "immediateActions": ["Verify radio channel assignment matches corridor plan", "Check antenna connection at nearest tower", "Confirm asset GPS position — signal issues can indicate zone boundary crossing"],
  "escalation": "If unresolved after 15 minutes, dispatch field crew to last known GPS position."
}
```

`ASSET_OFFLINE.json`

```json
{
  "alertType": "ASSET_OFFLINE",
  "immediateActions": ["Attempt radio contact on backup channel", "Check last known GPS position in dashboard", "Verify power status with dispatch"],
  "escalation": "If no contact after 15 minutes, escalate to field supervisor and mark corridor for manual inspection."
}
```

`UNEXPECTED_STOP.json`

```json
{
  "alertType": "UNEXPECTED_STOP",
  "immediateActions": ["Contact locomotive engineer directly via radio", "Check track obstruction reports for that corridor", "Review preceding 10 speed telemetry readings for anomaly pattern"],
  "escalation": "If engineer unreachable, initiate emergency response protocol and notify operations centre."
}
```

**Bash Health-Check Script (`scripts/health_check.sh`)**

```bash
#!/bin/bash
echo "=== RailSight Cloud Health Check ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

echo "[LOCAL SERVICES]"
echo "  Edge Gateway:    $(pgrep -f edge_gateway.py > /dev/null && echo running || echo STOPPED)"
echo "  Simulator:       $(pgrep -f simulate_assets.py > /dev/null && echo running || echo stopped)"
echo "  FastAPI Backend: $(curl -sf http://localhost:8000/health | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo DOWN)"
echo "  WebSocket:       $(wscat -c ws://localhost:8000/ws --wait 1 > /dev/null 2>&1 && echo active || echo DOWN)"
echo ""

echo "[AWS SERVICES — ca-central-1]"
echo "  DynamoDB Assets:     $(aws dynamodb describe-table --table-name railsight-assets --query 'Table.TableStatus' --output text 2>/dev/null || echo ERROR)"
echo "  DynamoDB Telemetry:  $(aws dynamodb describe-table --table-name railsight-telemetry --query 'Table.TableStatus' --output text 2>/dev/null || echo ERROR)"
echo "  DynamoDB Alerts:     $(aws dynamodb describe-table --table-name railsight-alerts --query 'Table.TableStatus' --output text 2>/dev/null || echo ERROR)"
echo "  Lambda Processor:    $(aws lambda get-function-configuration --function-name railsight-telemetry-processor --query 'State' --output text 2>/dev/null || echo ERROR)"
echo "  Lambda Checker:      $(aws lambda get-function-configuration --function-name railsight-offline-checker --query 'State' --output text 2>/dev/null || echo ERROR)"
echo "  Lambda AI:           $(aws lambda get-function-configuration --function-name railsight-ai-assistant --query 'State' --output text 2>/dev/null || echo ERROR)"
echo "  S3 Runbooks:         $(aws s3 ls s3://railsight-runbooks-yourname-2026/ 2>/dev/null | wc -l | tr -d ' ') runbook files"
echo ""

echo "[OPERATIONAL STATUS]"
ASSETS_ONLINE=$(aws dynamodb scan --table-name railsight-assets \
  --filter-expression "#s <> :offline" \
  --expression-attribute-names '{"#s":"status"}' \
  --expression-attribute-values '{":offline":{"S":"offline"}}' \
  --select COUNT --query Count --output text 2>/dev/null || echo "?")
TOTAL_ASSETS=$(aws dynamodb scan --table-name railsight-assets \
  --select COUNT --query Count --output text 2>/dev/null || echo "?")
P1_ALERTS=$(aws dynamodb scan --table-name railsight-alerts \
  --filter-expression "severity = :s AND acknowledged = :a" \
  --expression-attribute-values '{":s":{"S":"P1"},":a":{"BOOL":false}}' \
  --select COUNT --query Count --output text 2>/dev/null || echo "?")
TELEMETRY_EVENTS=$(aws dynamodb scan --table-name railsight-telemetry \
  --select COUNT --query Count --output text 2>/dev/null || echo "?")

echo "  Assets Online:       ${ASSETS_ONLINE} / ${TOTAL_ASSETS}"
echo "  Active P1 Alerts:    ${P1_ALERTS}"
echo "  Telemetry Records:   ${TELEMETRY_EVENTS} (last 24h, TTL auto-expires older)"
echo ""
echo "=== Done ==="
```

**Goal for Phase 4:** AI assistant gives grounded responses from actual DynamoDB and S3 data. Health script passes cleanly. Everything starts with `docker compose up`.

---

## Docker Compose

```yaml
services:
  edge-gateway:
    build: ./edge-gateway
    ports:
      - "9000:9000/udp"
    environment:
      - IOT_ENDPOINT=${IOT_ENDPOINT}
      - AWS_REGION=ca-central-1
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
    volumes:
      - ./certs:/app/certs:ro
    restart: unless-stopped

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - AWS_REGION=ca-central-1
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - DYNAMODB_ASSETS_TABLE=railsight-assets
      - DYNAMODB_TELEMETRY_TABLE=railsight-telemetry
      - DYNAMODB_ALERTS_TABLE=railsight-alerts
      - RUNBOOKS_BUCKET=railsight-runbooks-yourname-2026
    depends_on:
      - edge-gateway

  simulator:
    build: ./simulator
    command: python simulate_assets.py --assets 30 --failure-rate 0.10 --interval 10
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

AWS credentials come from a `.env` file (gitignored). IoT certificates are mounted read-only from `./certs/`.

---

## Repository Structure

```
railsight-cloud/
├── simulator/
│   ├── simulate_assets.py
│   └── Dockerfile
├── edge-gateway/
│   ├── edge_gateway.py
│   ├── requirements.txt        ← awsiotsdk, paho-mqtt
│   └── Dockerfile
├── backend/
│   ├── main.py                 ← FastAPI app
│   ├── dynamodb_client.py
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
│   └── src/
│       ├── components/
│       │   ├── AssetMap.tsx
│       │   ├── AlertFeed.tsx
│       │   ├── AssetDetail.tsx
│       │   ├── IncidentTimeline.tsx
│       │   ├── AnalyticsPage.tsx
│       │   └── AIAssistant.tsx
│       └── App.tsx
├── runbooks/                   ← upload to S3 manually
│   ├── LOW_SIGNAL.json
│   ├── ASSET_OFFLINE.json
│   ├── UNEXPECTED_STOP.json
│   └── DUPLICATE_TELEMETRY.json
├── scripts/
│   └── health_check.sh
├── infra/
│   └── setup_aws.md
├── certs/                      ← gitignored
├── .env                        ← gitignored
├── docker-compose.yml
└── README.md
```

---

## 60-Second Recruiter Demo Script

1. Terminal A: `docker compose up` — edge gateway connects, simulator starts at 10s intervals.
2. Open `localhost:3000`. 30 assets appear on the Alberta map, mostly green.
3. Terminal B: `python simulate_assets.py --force-fail LOCO-1000 --fail-type signal_drop --interval 10`
4. Watch LOCO-1000 turn yellow then red on the map within one WebSocket cycle.
5. P1 alert appears in the sidebar: "LOW_SIGNAL — Signal at 18%."
6. Click LOCO-1000. Show the incident timeline and signal strength chart.
7. Type in the AI chat: `"What happened to LOCO-1000 and what should I do?"`
8. AI responds with signal drop sequence from DynamoDB and the runbook action from S3.
9. Terminal B: `./scripts/health_check.sh`. All green except "Active P1 Alerts: 1."
10. Acknowledge the alert in the dashboard.
11. Optional: Open AWS Console → IoT Core → MQTT Test Client → subscribe to `railsight/assets/#`. Show live packets arriving. This proves the cloud pipeline is real, not simulated locally.

---

## Resume Bullets

**Concise:**

> Built RailSight Cloud, a hybrid railway field asset monitoring platform where simulated locomotives, wayside detectors, and radio towers send UDP telemetry to a Python edge gateway that republishes to AWS IoT Core over MQTT; IoT Rules trigger Lambda for alert processing, DynamoDB stores asset state and time-series telemetry with 24-hour TTL, and a FastAPI WebSocket backend serves a React dashboard with AI-assisted troubleshooting from CloudWatch logs and S3 runbooks.

**Stronger:**

> Designed a "single pane of glass" railway monitoring platform using a hybrid IoT architecture: simulated field assets transmit UDP telemetry to a Python edge gateway, which bridges to AWS IoT Core over MQTT; Lambda functions enforce P1/P2/P3 alert rules, DynamoDB persists asset state and rolling telemetry history, and a React dashboard surfaces live status maps, incident timelines, and GenAI troubleshooting grounded in structured logs and operational runbooks — deployed entirely within the AWS free tier.

---

## What to Say in the Interview

> "The core architectural decision was the edge gateway. I could have had the simulator publish MQTT directly to IoT Core, but that wouldn't reflect how real field systems work — those assets speak UDP and serial, not MQTT. So I added a gateway that bridges UDP to MQTT and handles validation before anything touches AWS. The other decision I'm proud of is replacing Timestream with a DynamoDB table using TTL. Timestream has no free tier and I wanted the project to be fully reproducible by anyone, so I used DynamoDB's auto-expiry feature to get the same rolling 24-hour telemetry window at zero cost. That tradeoff — choosing the right tool within real constraints — is something I'd be making constantly in this role."

That answer shows systems thinking, cost awareness, and practical engineering judgment. It's hard to fake and hard to forget.
