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