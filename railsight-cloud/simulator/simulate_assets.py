import argparse
import json
import math
import os
import random
import socket
import threading
import time
from datetime import datetime, timezone

GATEWAY_HOST = os.getenv("GATEWAY_HOST", "127.0.0.1")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "9000"))

ASSET_TYPES = ["locomotive", "wayside_detector", "radio_tower", "track_sensor"]

CALGARY_LAT = 51.0447
CALGARY_LON = -114.0719

# Rough railway-ish corridor around Calgary.
# These are fake demo anchor points, not real track data.
ROUTES = {
    "west_corridor": [
        (51.0447, -114.0719),
        (51.0350, -114.1800),
        (51.0200, -114.3100),
        (51.0000, -114.4500),
        (50.9800, -114.6200),
    ],
    "east_corridor": [
        (51.0447, -114.0719),
        (51.0500, -113.9500),
        (51.0600, -113.8000),
        (51.0700, -113.6500),
        (51.0800, -113.5000),
    ],
    "north_corridor": [
        (51.0447, -114.0719),
        (51.1200, -114.0600),
        (51.2100, -114.0500),
        (51.3000, -114.0400),
        (51.3900, -114.0300),
    ],
    "south_corridor": [
        (51.0447, -114.0719),
        (50.9800, -114.0800),
        (50.9000, -114.0900),
        (50.8200, -114.1000),
        (50.7400, -114.1100),
    ],
}


def interpolate_route(route_points, progress):
    """
    Move smoothly along a polyline route.

    progress is between 0.0 and 1.0.
    """
    if progress <= 0:
        return route_points[0]

    if progress >= 1:
        return route_points[-1]

    segment_count = len(route_points) - 1
    scaled = progress * segment_count
    segment_index = int(scaled)
    segment_fraction = scaled - segment_index

    lat1, lon1 = route_points[segment_index]
    lat2, lon2 = route_points[segment_index + 1]

    lat = lat1 + (lat2 - lat1) * segment_fraction
    lon = lon1 + (lon2 - lon1) * segment_fraction

    return lat, lon


def add_small_gps_noise(lat, lon):
    """
    Add tiny noise so the movement looks natural without teleporting.
    About 5-20 meters of jitter.
    """
    return (
        lat + random.uniform(-0.00008, 0.00008),
        lon + random.uniform(-0.00008, 0.00008),
    )


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def get_status(signal, battery_level):
    if signal < 35 or battery_level < 20:
        return "critical"

    if signal < 60 or battery_level < 40:
        return "warning"

    return "healthy"


def simulate_asset(asset_id, asset_type, failure_rate, interval_seconds, force_fail_id, fail_type):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    seq = 0
    signal = random.uniform(75, 95)
    battery_level = random.uniform(85, 100)
    radio_channel = f"CH-{random.randint(1, 5)}"

    route_name = random.choice(list(ROUTES.keys()))
    route_points = ROUTES[route_name]

    # Each asset starts at a different point along its route.
    route_progress = random.uniform(0, 0.95)

    # Locomotives move. Fixed infrastructure stays fixed.
    if asset_type == "locomotive":
        speed = random.uniform(35, 75)
        route_step = random.uniform(0.002, 0.006)
    else:
        speed = 0
        route_step = 0

    lat, lon = interpolate_route(route_points, route_progress)

    while True:
        is_forced_failure = asset_id == force_fail_id

        # Signal changes gradually instead of jumping randomly.
        if is_forced_failure and fail_type == "signal_drop":
            signal -= random.uniform(8, 15)
        elif random.random() < failure_rate:
            signal -= random.uniform(4, 10)
        else:
            signal += random.uniform(-2, 3)

        signal = clamp(signal, 10, 95)

        # Battery drains slowly.
        battery_level -= random.uniform(0.01, 0.08)
        battery_level = clamp(battery_level, 5, 100)

        # Radio channel should not change constantly.
        # Rarely switch channels to simulate handoff/reconfiguration.
        if random.random() < 0.01:
            radio_channel = f"CH-{random.randint(1, 5)}"

        if asset_type == "locomotive":
            # Speed changes gradually.
            speed += random.uniform(-3, 3)
            speed = clamp(speed, 0, 90)

            # Unexpected stop failure.
            if is_forced_failure and fail_type == "unexpected_stop":
                speed = 0

            # Move forward along the route based on speed.
            # Faster speed = slightly larger progress step.
            route_progress += route_step * (speed / 60)

            # Loop back when reaching end of fake route.
            if route_progress >= 1:
                route_progress = 0

            lat, lon = interpolate_route(route_points, route_progress)
            lat, lon = add_small_gps_noise(lat, lon)

        else:
            # Wayside/radio/sensor assets are fixed infrastructure.
            # They should not move after startup.
            lat, lon = add_small_gps_noise(lat, lon)

        status = get_status(signal, battery_level)

        packet = {
            "assetId": asset_id,
            "type": asset_type,
            "status": status,
            "speed": round(speed, 1),
            "gps": [round(lat, 6), round(lon, 6)],
            "signalStrength": round(signal, 1),
            "batteryLevel": round(battery_level, 1),
            "sequenceNumber": seq,
            "radioChannel": radio_channel,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        sock.sendto(json.dumps(packet).encode(), (GATEWAY_HOST, GATEWAY_PORT))

        print(
            f"{asset_id} | {status.upper()} | "
            f"speed={packet['speed']} km/h | "
            f"signal={packet['signalStrength']}% | "
            f"gps={packet['gps']} | "
            f"battery={packet['batteryLevel']}%"
        )

        seq += 1
        time.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=int, default=30)
    parser.add_argument("--failure-rate", type=float, default=0.10)
    parser.add_argument(
        "--interval",
        type=float,
        default=10.0,
        help="Seconds between packets. Use 10+ for AWS mode/free-tier-friendly testing.",
    )
    parser.add_argument("--force-fail", type=str, help="Asset ID to force into failure")
    parser.add_argument(
        "--fail-type",
        type=str,
        default="signal_drop",
        choices=["signal_drop", "unexpected_stop"],
    )

    args = parser.parse_args()

    print(
        f"Starting {args.assets} assets | "
        f"interval={args.interval}s | "
        f"failure-rate={args.failure_rate}"
    )
    print(f"Estimated IoT Core messages/hour: {args.assets * (3600 / args.interval):.0f}")

    if args.force_fail:
        print(f"Forcing failure for {args.force_fail} | fail-type={args.fail_type}")

    threads = []

    for i in range(args.assets):
        asset_type = ASSET_TYPES[i % len(ASSET_TYPES)]
        asset_id = f"{asset_type.upper().replace('_', '-')}-{1000 + i}"

        thread = threading.Thread(
            target=simulate_asset,
            args=(
                asset_id,
                asset_type,
                args.failure_rate,
                args.interval,
                args.force_fail,
                args.fail_type,
            ),
        )

        thread.daemon = True
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()
