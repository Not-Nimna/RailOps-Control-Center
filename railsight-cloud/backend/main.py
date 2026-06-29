from datetime import datetime
import asyncio

from boto3.dynamodb.conditions import Key, Attr
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.dynamodb_client import (
    assets_table,
    telemetry_table,
    alerts_table,
    dynamodb_to_json,
)
from backend.websocket_manager import WebSocketManager

app = FastAPI(title="RailSight Cloud API")

manager = WebSocketManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/assets")
async def get_assets():
    response = assets_table.scan()
    return dynamodb_to_json(response.get("Items", []))


@app.get("/assets/{asset_id}/history")
async def get_asset_history(asset_id: str, limit: int = 20):
    response = telemetry_table.query(
        KeyConditionExpression=Key("assetId").eq(asset_id),
        ScanIndexForward=False,
        Limit=limit
    )
    return dynamodb_to_json(response.get("Items", []))


@app.get("/alerts")
async def get_alerts(severity: str | None = None, acknowledged: bool | None = None):
    filter_expr = None

    if severity is not None:
        filter_expr = Attr("severity").eq(severity)

    if acknowledged is not None:
        ack_expr = Attr("acknowledged").eq(acknowledged)
        filter_expr = ack_expr if filter_expr is None else filter_expr & ack_expr

    if filter_expr is not None:
        response = alerts_table.scan(FilterExpression=filter_expr)
    else:
        response = alerts_table.scan()

    return dynamodb_to_json(response.get("Items", []))


@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, timestamp: str):
    alerts_table.update_item(
        Key={
            "alertId": alert_id,
            "timestamp": timestamp
        },
        UpdateExpression="SET acknowledged = :val",
        ExpressionAttributeValues={
            ":val": True
        }
    )

    return {
        "message": "Alert acknowledged",
        "alertId": alert_id
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            assets = assets_table.scan().get("Items", [])
            alerts = alerts_table.scan(
                FilterExpression=Attr("acknowledged").eq(False)
            ).get("Items", [])

            await websocket.send_json({
                "type": "state_update",
                "assets": dynamodb_to_json(assets),
                "alerts": dynamodb_to_json(alerts),
                "timestamp": datetime.utcnow().isoformat()
            })

            await asyncio.sleep(3)

    except WebSocketDisconnect:
        manager.disconnect(websocket)