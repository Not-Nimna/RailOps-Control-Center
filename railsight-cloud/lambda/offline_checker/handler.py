import boto3
import json
from datetime import datetime, timezone


REGION = "ca-central-1"

dynamodb = boto3.resource("dynamodb", region_name=REGION)

assets_table = dynamodb.Table("railsight-assets")
alerts_table = dynamodb.Table("railsight-alerts")

OFFLINE_THRESHOLD_SECONDS = 300  # 5 minutes


def lambda_handler(event, context):
    now = datetime.now(timezone.utc)

    checked_count = 0
    offline_count = 0
    skipped_duplicate_count = 0

    assets = scan_all_assets()

    for asset in assets:
        checked_count += 1

        asset_id = asset.get("assetId")
        last_seen_str = asset.get("lastSeen", "")

        if not asset_id or not last_seen_str:
            continue

        try:
            last_seen = datetime.fromisoformat(
                last_seen_str.replace("Z", "+00:00")
            )
        except ValueError:
            print(f"Invalid lastSeen timestamp for {asset_id}: {last_seen_str}")
            continue

        seconds_since = (now - last_seen).total_seconds()

        if seconds_since > OFFLINE_THRESHOLD_SECONDS:
            if unresolved_alert_exists(asset_id, "ASSET_OFFLINE"):
                skipped_duplicate_count += 1
                print(f"Skipping duplicate ASSET_OFFLINE alert for {asset_id}")
                continue

            create_alert(
                asset_id=asset_id,
                rule="ASSET_OFFLINE",
                severity="P1",
                suggested_action=(
                    f"No telemetry for {int(seconds_since)}s. "
                    "Check asset power, radio channel, antenna, and last known GPS position."
                ),
                now=now
            )

            offline_count += 1
            print(f"OFFLINE: {asset_id} — last seen {int(seconds_since)}s ago")

    response = {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Offline check completed",
            "checkedAssets": checked_count,
            "newOfflineAlerts": offline_count,
            "skippedDuplicateAlerts": skipped_duplicate_count,
            "checkedAt": now.isoformat()
        })
    }

    print(response)
    return response


def scan_all_assets():
    """
    DynamoDB scan only returns up to 1 MB per request.
    This function handles pagination so every asset is checked.
    """
    items = []

    response = assets_table.scan()
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = assets_table.scan(
            ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items.extend(response.get("Items", []))

    return items


def unresolved_alert_exists(asset_id, rule):
    """
    Prevents the offline checker from creating a new ASSET_OFFLINE alert
    every minute while the same asset remains offline.

    This uses a scan for simplicity.
    For a larger production system, use a GSI on assetId/rule/acknowledged.
    """
    response = alerts_table.scan(
        FilterExpression=(
            "assetId = :asset_id AND #rule = :rule AND acknowledged = :acknowledged"
        ),
        ExpressionAttributeNames={
            "#rule": "rule"
        },
        ExpressionAttributeValues={
            ":asset_id": asset_id,
            ":rule": rule,
            ":acknowledged": False
        }
    )

    return len(response.get("Items", [])) > 0


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