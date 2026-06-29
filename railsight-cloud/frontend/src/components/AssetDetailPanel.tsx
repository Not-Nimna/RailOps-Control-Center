import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import type { Alert, Asset, TelemetryPoint } from "../types/railsight";
import IncidentTimeline from "./IncidentTimeline";
import StatusBadge from "./StatusBadge";

interface AssetDetailPanelProps {
  asset: Asset | null;
  history: TelemetryPoint[];
  alerts: Alert[];
}

function isShadowInSync(lastSeen: string) {
  const lastSeenMs = new Date(lastSeen).getTime();
  const nowMs = Date.now();
  const secondsSinceLastSeen = (nowMs - lastSeenMs) / 1000;

  return secondsSinceLastSeen <= 30;
}

export default function AssetDetailPanel({ asset, history, alerts }: AssetDetailPanelProps) {
  if (!asset) {
    return (
      <div className="asset-detail-panel">
        <div className="empty-state">Select an asset to inspect telemetry.</div>
      </div>
    );
  }

  const shadowInSync = isShadowInSync(asset.lastSeen);
  const gps = asset.gps;

  const chartData = history
    .filter((point) => point.signalStrength !== undefined)
    .map((point) => ({
      time: new Date(point.timestamp).toLocaleTimeString(),
      signalStrength: point.signalStrength,
    }));

  return (
    <div className="asset-detail-panel">
      <div className="panel-header">
        <div>
          <h2>{asset.assetId}</h2>
          <p>{asset.type}</p>
        </div>

        <StatusBadge status={asset.status} />
      </div>

      <div className={`shadow-badge ${shadowInSync ? "in-sync" : "out-of-sync"}`}>{shadowInSync ? "Shadow in sync" : "Shadow stale"}</div>

      <div className="telemetry-grid">
        <div>
          <span>Speed</span>
          <strong>{asset.speed ?? "N/A"} km/h</strong>
        </div>

        <div>
          <span>Signal</span>
          <strong>{asset.signalStrength ?? "N/A"}%</strong>
        </div>

        <div>
          <span>GPS</span>
          <strong>{gps && gps.length >= 2 ? `${Number(gps[0]).toFixed(4)}, ${Number(gps[1]).toFixed(4)}` : "N/A"}</strong>
        </div>

        <div>
          <span>Battery</span>
          <strong>{asset.batteryLevel ?? "N/A"}%</strong>
        </div>

        <div>
          <span>Radio Channel</span>
          <strong>{asset.radioChannel ?? "N/A"}</strong>
        </div>

        <div>
          <span>Last Seen</span>
          <strong>{new Date(asset.lastSeen).toLocaleTimeString()}</strong>
        </div>
      </div>

      <section className="chart-section">
        <h3>Signal Strength</h3>

        <div className="chart-card">
          {chartData.length === 0 ? (
            <div className="empty-state">No signal history available.</div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Line type="monotone" dataKey="signalStrength" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>

      <IncidentTimeline asset={asset} history={history} alerts={alerts} />
    </div>
  );
}
