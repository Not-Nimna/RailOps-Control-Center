# AWS mode (free tier safe)

python simulate_assets.py --assets 30 --failure-rate 0.10 --interval 10

# Local testing (fast, no AWS)

python simulate_assets.py --assets 30 --failure-rate 0.10 --interval 2

# Force a failure for demo

python simulate_assets.py --force-fail LOCO-1000 --fail-type signal_drop --interval 10

# Terminal 2:

cd railsight-cloud
source .venv/bin/activate
python simulator/simulate_assets.py --assets 5 --failure-rate 0.10 --interval 10

# Stop these when not testing:

pkill -f simulate_assets.py
