# AWS mode (free tier safe)

python simulate_assets.py --assets 30 --failure-rate 0.10 --interval 10

# Local testing (fast, no AWS)

python simulate_assets.py --assets 30 --failure-rate 0.10 --interval 2

# Force a failure for demo

python simulate_assets.py --force-fail LOCO-1000 --fail-type signal_drop --interval 10
