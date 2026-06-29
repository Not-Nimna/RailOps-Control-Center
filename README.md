 # RailSight
Real-Time Field Asset Monitoring and AI-Assisted Troubleshooting for Railway Operations

[screenshot of dashboard]



## What It Does
Simulates railway field assets (locomotives, wayside detectors, radios) sending UDP telemetry to a Python edge gateway, which validates and republishes events to AWS IoT Core over MQTT; cloud-side IoT Rules route data to Lambda, DynamoDB, and Timestream, while a FastAPI WebSocket backend serves a live React dashboard with AI-assisted incident troubleshooting from CloudWatch logs and S3 runbooks.


## Why I Built It
I wanted to build something that reflected how railway field systems actually work: telemetry at the edge, protocol translation through a gateway, cloud-based monitoring, and operator-focused troubleshooting.

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
[ ASCII diagram ]

## Tech Stack
[table]

## Running the Simulator
python simulate_assets.py --assets 30 --failure-rate 0.10

## Triggering a Failure (Demo)
python simulate_assets.py --force-fail LOCO-5821 --type signal_drop
