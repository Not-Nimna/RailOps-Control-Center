 # RailSight
Real-Time Field Asset Monitoring and AI-Assisted Troubleshooting for Railway Operations

<img width="2556" height="1317" alt="Screenshot 2026-06-29 at 11 46 45 AM" src="https://github.com/user-attachments/assets/74813046-eac4-4560-8232-f1ffc497b8f8" />




## What It Does
Simulates railway field assets (locomotives, wayside detectors, radios) sending UDP telemetry to a Python edge gateway, which validates and republishes events to AWS IoT Core over MQTT; cloud-side IoT Rules route data to Lambda, DynamoDB, and Timestream, while a FastAPI WebSocket backend serves a live React dashboard with AI-assisted incident troubleshooting from CloudWatch logs and S3 runbooks.


## Why I Built It
I wanted to build something that reflected how railway field systems actually work: telemetry at the edge, protocol translation through a gateway, cloud-based monitoring, and operator-focused troubleshooting.

## Quick Start

```bash
docker compose up --build
```

## Features
- Live asset map with status color-coding
- Real-time alert engine (P1/P2/P3 severity)
- Incident timeline per asset
- AI troubleshooting assistant over structured logs and runbooks ( under development)
- Bash health-check automation script ( under development)
- Analytics dashboard ( under development)

## Architecture
[ ASCII diagram ]

## Tech Stack
| Layer | Technology | Role in RailSight Cloud |
|---|---|---|---|
| **Asset Simulator** | Python (UDP sockets, threading) | Spawns 30 fake field assets sending telemetry packets every 10s  |
| **Edge Gateway** | Python + AWS IoT Device SDK (MQTT over TLS) | Receives UDP, validates schema, republishes to IoT Core |
| **Cloud Ingestion** | AWS IoT Core | Receives MQTT telemetry, routes via IoT Rules |
| **Alert Engine** | Python Lambda + EventBridge Scheduler | Fires on every packet (signal/speed rules) and every 60s (offline rule)|
| **Asset State** | DynamoDB (`railsight-assets`) | One row per asset, upserted on every packet  |
| **Telemetry History** | DynamoDB (`railsight-telemetry`) + TTL | Rolling 24h of all packets, auto-expired |
| **Alerts Store** | DynamoDB (`railsight-alerts`) | P1/P2/P3 alerts with acknowledged/resolved state |
| **Device State** | AWS IoT Device Shadows | Last known good state per asset, survives gaps |
| **Runbooks** | S3 (`railsight-runbooks`) | JSON troubleshooting procedures for AI context |
| **Logging** | CloudWatch Logs + Log Insights | Lambda logs queryable by asset ID  |
| **REST + WebSocket API** | Python FastAPI | Reads DynamoDB, pushes live updates to dashboard every 3s |
| **Frontend** | React + TypeScript | Single pane of glass dashboard  |
| **Asset Map** | Leaflet.js | Live color-coded asset map centred on Alberta  |
| **Charts** | Recharts | Signal strength history, analytics page  |
| **AI Assistant** | Claude API (claude-sonnet-4-6) | RAG over DynamoDB telemetry + CloudWatch logs + S3 runbooks ( under development) |
| **Health Automation** | Bash + AWS CLI | Checks all local and AWS services in one script ( under development) |
| **Local Orchestration** | Docker Compose | One command starts gateway, simulator, backend, frontend |
| **Region** | `ca-central-1` (Canada Central) | — |

## Running the Simulator
python simulate_assets.py --assets 30 --failure-rate 0.10

## Triggering a Failure
python simulate_assets.py --force-fail LOCO-5821 --type signal_drop
