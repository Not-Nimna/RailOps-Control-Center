````md
## Run the Backend Locally

From the project root:

```bash
cd railsight-cloud
source .venv/bin/activate
python3 -m pip install -r backend/requirements.txt
```
````

### Run from the project root

Use this if your current folder is:

```bash
railsight-cloud/
```

Run:

```bash
uvicorn backend.main:app --reload --port 8000
```

## Test the Backend

After the server starts, open these URLs in your browser:

```txt
http://localhost:8000/health
http://localhost:8000/assets
http://localhost:8000/assets/LOCO-5821/history
http://localhost:8000/alerts
```

Expected result:

- `/health` should confirm the API is running.
- `/assets` should return the current asset records.
- `/assets/LOCO-5821/history` should return telemetry history for asset `LOCO-5821`.
- `/alerts` should return current alert records.

```

```

## To Test WebSocket

Install wscat if you do not have it:

```bash
npm install -g wscat
```

Then run:

```bash
wscat -c ws://localhost:8000/ws
```
