import os
import socket, json, logging
from datetime import datetime, timezone
from awsiot import mqtt_connection_builder
from awscrt import mqtt

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [GATEWAY] %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

IOT_ENDPOINT = os.getenv("IOT_ENDPOINT", "a16j74wv9e0nbe-ats.iot.ca-central-1.amazonaws.com")
REQUIRED_FIELDS = {"assetId", "type", "status", "signalStrength", "timestamp", "sequenceNumber"}
VALID_TYPES = {"locomotive", "wayside_detector", "radio_tower", "track_sensor"}

def validate(packet):
    missing = REQUIRED_FIELDS - set(packet.keys())
    if missing:
        return False, f"Missing fields: {missing}"
    if not 0 <= packet['signalStrength'] <= 100:
        return False, f"signalStrength out of range: {packet['signalStrength']}"
    if packet['type'] not in VALID_TYPES:
        return False, f"Unknown type: {packet['type']}"
    return True, "ok"

def run():
    mqtt_conn = mqtt_connection_builder.mtls_from_path(
        endpoint=IOT_ENDPOINT,
        cert_filepath="certs/edge-gateway.cert.pem",
        pri_key_filepath="certs/edge-gateway.private.key",
        ca_filepath="certs/root-CA.crt",
        client_id="railsight-edge-gateway"
    )
    mqtt_conn.connect().result()
    logger.info("Connected to AWS IoT Core")

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(('0.0.0.0', 9000))
    logger.info("Listening for UDP on :9000")

    seen_sequences = {}
    packets_forwarded = 0
    packets_rejected = 0

    while True:
        data, addr = udp_sock.recvfrom(4096)
        try:
            packet = json.loads(data.decode())
            valid, reason = validate(packet)

            if not valid:
                packets_rejected += 1
                logger.warning(f"REJECTED from {addr}: {reason}")
                continue

            asset_id = packet['assetId']
            seq = packet['sequenceNumber']
            is_duplicate = seq in seen_sequences.get(asset_id, set())

            if is_duplicate:
                logger.warning(f"DUPLICATE seq={seq} from {asset_id}")
                packet['_duplicate'] = True
            else:
                seen_sequences.setdefault(asset_id, set()).add(seq)

            topic = f"railsight/assets/{asset_id}/telemetry"
            mqtt_conn.publish(topic=topic, payload=json.dumps(packet),
                              qos=mqtt.QoS.AT_LEAST_ONCE)

            packets_forwarded += 1
            if packets_forwarded % 100 == 0:
                logger.info(f"Forwarded {packets_forwarded} packets | Rejected {packets_rejected}")

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error from {addr}: {e}")

if __name__ == "__main__":
    run()
