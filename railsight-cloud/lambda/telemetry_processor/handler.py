"""AWS Lambda handler for telemetry ingestion events."""


def handler(event, context):
    return {"statusCode": 200, "body": "telemetry processed"}

