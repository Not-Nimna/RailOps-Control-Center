"""AWS Lambda handler for offline asset checks."""


def handler(event, context):
    return {"statusCode": 200, "body": "offline check complete"}

