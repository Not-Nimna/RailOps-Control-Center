## Local Installation

```bash
cd railsight-cloud/edge-gateway
python3 -m venv .venv
source .venv/bin/activate
pip install awsiotsdk boto3
python3 -m pip install -r requirements.txt
```

# run the gateway from the project root:

cd railsight-cloud
python edge-gateway/edge_gateway.py

# Terminal 1:

cd railsight-cloud
source .venv/bin/activate
python edge-gateway/edge_gateway.py

# Stop these when not testing:

pkill -f edge_gateway.py
