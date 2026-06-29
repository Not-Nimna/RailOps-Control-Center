import socket, json, random, time, threading, argparse
from datetime import datetime, timezone

GATEWAY_HOST = '127.0.0.1'
GATEWAY_PORT = 9000
ASSET_TYPES = ['locomotive', 'wayside_detector', 'radio_tower', 'track_sensor']

def simulate_asset(asset_id, asset_type, failure_rate, interval_seconds):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    seq = 0
    signal = 85.0
    speed = random.uniform(40, 80) if asset_type == 'locomotive' else 0

    while True:
        if random.random() < failure_rate:
            signal = max(10, signal - random.uniform(15, 30))
        else:
            signal = min(95, signal + random.uniform(0, 5))

        packet = {
            "assetId": asset_id,
            "type": asset_type,
            "status": "healthy" if signal > 60 else ("warning" if signal > 35 else "critical"),
            "speed": round(speed + random.uniform(-2, 2), 1) if asset_type == 'locomotive' else 0,
            "gps": [51.0447 + random.uniform(-0.5, 0.5), -114.0719 + random.uniform(-2, 2)],
            "signalStrength": round(signal, 1),
            "batteryLevel": round(random.uniform(70, 100), 1),
            "sequenceNumber": seq,
            "radioChannel": f"CH-{random.randint(1, 5)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        sock.sendto(json.dumps(packet).encode(), (GATEWAY_HOST, GATEWAY_PORT))
        seq += 1
        time.sleep(interval_seconds)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--assets', type=int, default=30)
    parser.add_argument('--failure-rate', type=float, default=0.10)
    parser.add_argument('--interval', type=float, default=10.0,
                        help='Seconds between packets. Use 10+ for AWS mode (free tier).')
    parser.add_argument('--force-fail', type=str, help='Asset ID to force into failure')
    parser.add_argument('--fail-type', type=str, default='signal_drop')
    args = parser.parse_args()

    print(f"Starting {args.assets} assets | interval={args.interval}s | failure-rate={args.failure_rate}")
    print(f"Estimated IoT Core messages/hour: {args.assets * (3600 / args.interval):.0f}")

    threads = []
    for i in range(args.assets):
        asset_type = ASSET_TYPES[i % len(ASSET_TYPES)]
        asset_id = f"{asset_type.upper().replace('_','-')}-{1000 + i}"
        t = threading.Thread(target=simulate_asset,
                             args=(asset_id, asset_type, args.failure_rate, args.interval))
        t.daemon = True
        t.start()
        threads.append(t)

    for t in threads:
        t.join()