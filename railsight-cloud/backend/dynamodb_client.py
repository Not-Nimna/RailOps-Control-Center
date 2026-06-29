from decimal import Decimal
import json
import os

import boto3

REGION = os.getenv("AWS_REGION", "ca-central-1")

dynamodb = boto3.resource("dynamodb", region_name=REGION)

assets_table = dynamodb.Table(os.getenv("DYNAMODB_ASSETS_TABLE", "railsight-assets"))
telemetry_table = dynamodb.Table(os.getenv("DYNAMODB_TELEMETRY_TABLE", "railsight-telemetry"))
alerts_table = dynamodb.Table(os.getenv("DYNAMODB_ALERTS_TABLE", "railsight-alerts"))


def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def dynamodb_to_json(data):
    return json.loads(json.dumps(data, default=decimal_to_float))
