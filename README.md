# RailSight

Real-Time Field Asset Monitoring and AI-Assisted Troubleshooting for Railway Operations

<img width="2556" height="1317" alt="RailSight dashboard screenshot" src="https://github.com/user-attachments/assets/74813046-eac4-4560-8232-f1ffc497b8f8" />

## What It Does

Simulates railway field assets such as locomotives, wayside detectors, radios, and track sensors sending UDP telemetry to a Python edge gateway.

The gateway validates each packet, converts UDP telemetry into MQTT messages, and republishes them to AWS IoT Core. Cloud-side IoT Rules route telemetry into Lambda and DynamoDB, while a FastAPI WebSocket backend serves a live React dashboard with AI-assisted incident troubleshooting from CloudWatch logs and S3 runbooks.

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

<img width="1376" height="768" alt="architechture" src="https://github.com/user-attachments/assets/970cde58-0862-4874-9401-251c5b759210" />

## Tech Stack
| Layer                    | Technology                                | Role in RailSight Cloud                                                                    |
| ------------------------ | ----------------------------------------- | ------------------------------------------------------------------------------------------ |
| **Asset Simulator**      | Python UDP sockets, threading             | Spawns 30 simulated field assets sending telemetry packets every 10 seconds                |
| **Edge Gateway**         | Python, AWS IoT Device SDK, MQTT over TLS | Receives UDP packets, validates schema, and republishes telemetry to AWS IoT Core          |
| **Cloud Ingestion**      | AWS IoT Core                              | Receives MQTT telemetry and routes events using IoT Rules                                  |
| **Alert Engine**         | Python Lambda, EventBridge Scheduler      | Fires on every packet for signal and speed rules, plus every 60 seconds for offline checks |
| **Asset State**          | DynamoDB `railsight-assets`               | Stores the latest known state for each asset                                               |
| **Telemetry History**    | DynamoDB `railsight-telemetry` with TTL   | Stores rolling 24-hour telemetry history                                                   |
| **Alerts Store**         | DynamoDB `railsight-alerts`               | Stores P1/P2/P3 alerts with acknowledged and resolved states                               |
| **Device State**         | AWS IoT Device Shadows                    | Stores last known good state per asset                                                     |
| **Runbooks**             | S3 `railsight-runbooks`                   | Stores JSON troubleshooting procedures for AI context                                      |
| **Logging**              | CloudWatch Logs, Log Insights             | Makes Lambda logs queryable by asset ID                                                    |
| **REST + WebSocket API** | Python FastAPI                            | Reads DynamoDB and pushes live dashboard updates every 3 seconds                           |
| **Frontend**             | React, TypeScript                         | Provides a single-pane-of-glass dashboard                                                  |
| **Asset Map**            | Leaflet.js                                | Displays a live color-coded asset map centered on Alberta                                  |
| **Charts**               | Recharts                                  | Displays signal history and analytics views                                                |
| **AI Assistant**         | Claude API                                | RAG over DynamoDB telemetry, CloudWatch logs, and S3 runbooks under development            |
| **Health Automation**    | Bash, AWS CLI                             | Checks local and AWS services in one script under development                              |
| **Local Orchestration**  | Docker Compose                            | Starts gateway, simulator, backend, and frontend with one command                          |
| **Region**               | `ca-central-1`                            | Canada Central AWS region                                                                  |

## Running the Simulator
python simulate_assets.py --assets 30 --failure-rate 0.10

## Triggering a Failure
python simulate_assets.py --force-fail LOCO-5821 --type signal_drop
