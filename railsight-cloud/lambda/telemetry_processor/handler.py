import boto3
import json
from datetime import datetime, timezone
from decimal import Decimal


REGION = "ca-central-1"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
iot_data = boto3.client("iot-data", region_name=REGION)

assets_table = dynamodb.Table("railsight-assets")
telemetry_table = dynamodb.Table("railsight-telemetry")
alerts_table = dynamodb.Table("railsight-alerts")

TTL_SECONDS = 86400  # 24 hours


def to_decimal(value):
    """
    DynamoDB does not accept regular Python floats.
    Convert numeric values to Decimal safely.
    """
    return Decimal(str(value))


def lambda_handler(event, context):
    print("Received telemetry event:")
    print(json.dumps(event))

    asset_id = event["assetId"]
    now = datetime.now(timezone.utc)
    expires_at = int(now.timestamp()) + TTL_SECONDS

    gps = event.get("gps", [0, 0])

    if not gps or len(gps) < 2:
        gps = [0, 0]

    # Get previous state before overwriting current state.
    previous_asset = assets_table.get_item(
        Key={"assetId": asset_id}
    ).get("Item", {})

    # 1. Update current asset state.
    assets_table.put_item(Item={
        "assetId": asset_id,
        "type": event["type"],
        "status": event["status"],
        "speed": to_decimal(event.get("speed", 0)),
        "gps": [
            to_decimal(gps[0]),
            to_decimal(gps[1])
        ],
        "signalStrength": to_decimal(event["signalStrength"]),
        "batteryLevel": to_decimal(event.get("batteryLevel", 100)),
        "radioChannel": event.get("radioChannel", "unknown"),
        "lastSeen": event["timestamp"],
        "sequenceNumber": int(event["sequenceNumber"]),
        "updatedAt": now.isoformat()
    })

    # 2. Write telemetry history.
    # expiresAt is the DynamoDB TTL attribute.
    telemetry_table.put_item(Item={
        "assetId": asset_id,
        "timestamp": event["timestamp"],
        "status": event["status"],
        "speed": to_decimal(event.get("speed", 0)),
        "signalStrength": to_decimal(event["signalStrength"]),
        "batteryLevel": to_decimal(event.get("batteryLevel", 100)),
        "latitude": to_decimal(gps[0]),
        "longitude": to_decimal(gps[1]),
        "expiresAt": expires_at
    })

    # 3. Run alert rules.
    run_alert_rules(event, previous_asset, now)

    # 4. Update AWS IoT Device Shadow.
    update_device_shadow(event, gps)

    print(f"Processed telemetry for {asset_id}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Telemetry processed",
            "assetId": asset_id
        })
    }


def run_alert_rules(event, previous_asset, now):
    asset_id = event["assetId"]
    signal = float(event["signalStrength"])
    current_speed = float(event.get("speed", 0))

    # Rule 1: Low signal strength.
    if signal < 40:
        severity = "P1" if signal < 20 else "P2"

        create_alert(
            asset_id=asset_id,
            rule="LOW_SIGNAL",
            severity=severity,
            suggested_action=(
                f"Signal at {signal}%. "
                "Verify radio channel, antenna, and field connectivity."
            ),
            now=now
        )

    # Rule 2: Unexpected locomotive stop.
    if event["type"] == "locomotive" and current_speed == 0:
        previous_speed = float(previous_asset.get("speed", 0))

        if previous_speed > 5:
            create_alert(
                asset_id=asset_id,
                rule="UNEXPECTED_STOP",
                severity="P1",
                suggested_action=(
                    "Locomotive stopped unexpectedly after previous movement. "
                    "Check train status, operator report, and nearby signal conditions."
                ),
                now=now
            )

    # Rule 3: Duplicate telemetry.
    if event.get("_duplicate"):
        create_alert(
            asset_id=asset_id,
            rule="DUPLICATE_TELEMETRY",
            severity="P3",
            suggested_action=(
                f"Duplicate sequence {event['sequenceNumber']} received from {asset_id}. "
                "Check edge gateway deduplication and asset sequence counter."
            ),
            now=now
        )


def create_alert(asset_id, rule, severity, suggested_action, now):
    alert_id = f"{asset_id}-{rule}-{int(now.timestamp())}"

    alerts_table.put_item(Item={
        "alertId": alert_id,
        "assetId": asset_id,
        "rule": rule,
        "severity": severity,
        "suggestedAction": suggested_action,
        "timestamp": now.isoformat(),
        "acknowledged": False,
        "resolvedAt": None
    })

    print(f"ALERT created: {severity} {rule} for {asset_id}")


def update_device_shadow(event, gps):
    asset_id = event["assetId"]

    shadow_payload = {
        "state": {
            "reported": {
                "status": event["status"],
                "speed": event.get("speed", 0),
                "signalStrength": event["signalStrength"],
                "batteryLevel": event.get("batteryLevel", 100),
                "gps": gps,
                "lastSeen": event["timestamp"]
            }
        }
    }

    try:
        iot_data.update_thing_shadow(
            thingName=asset_id,
            payload=json.dumps(shadow_payload)
        )

        print(f"Updated IoT Device Shadow for {asset_id}")

    except Exception as error:
        print(f"Shadow update failed for {asset_id}: {error}")