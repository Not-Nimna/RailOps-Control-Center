import { useMemo, useState } from "react";
import type { Alert } from "../types/railsight";

interface AlertFeedProps {
  alerts: Alert[];
  onAcknowledge: (alertId: string) => void;
}

type AlertFilter = "all" | "p1" | "unacknowledged" | "type";

function getSeverityClass(severity: Alert["severity"]) {
  switch (severity) {
    case "P1":
      return "priority-p1";
    case "P2":
      return "priority-p2";
    case "P3":
      return "priority-p3";
    default:
      return "";
  }
}

export default function AlertFeed({ alerts, onAcknowledge }: AlertFeedProps) {
  const [filter, setFilter] = useState<AlertFilter>("all");
  const [typeFilter, setTypeFilter] = useState("");

  const alertRules = useMemo(() => {
    return Array.from(new Set(alerts.map((alert) => alert.rule))).sort();
  }, [alerts]);

  const filteredAlerts = useMemo(() => {
    if (filter === "p1") {
      return alerts.filter((alert) => alert.severity === "P1");
    }

    if (filter === "unacknowledged") {
      return alerts.filter((alert) => !alert.acknowledged);
    }

    if (filter === "type" && typeFilter) {
      return alerts.filter((alert) => alert.rule === typeFilter);
    }

    return alerts;
  }, [alerts, filter, typeFilter]);

  return (
    <div className="alert-feed">
      <div className="panel-header">
        <h2>Alert Feed</h2>
        <span>{filteredAlerts.length}</span>
      </div>

      <div className="filter-bar">
        <button onClick={() => setFilter("all")} className={filter === "all" ? "active" : ""}>
          All
        </button>

        <button onClick={() => setFilter("p1")} className={filter === "p1" ? "active" : ""}>
          P1 only
        </button>

        <button onClick={() => setFilter("unacknowledged")} className={filter === "unacknowledged" ? "active" : ""}>
          Unacknowledged
        </button>

        <button onClick={() => setFilter("type")} className={filter === "type" ? "active" : ""}>
          By type
        </button>
      </div>

      {filter === "type" && (
        <select className="type-select" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
          <option value="">Select alert type</option>
          {alertRules.map((rule) => (
            <option key={rule} value={rule}>
              {rule}
            </option>
          ))}
        </select>
      )}

      <div className="alert-list">
        {filteredAlerts.length === 0 && <div className="empty-state">No alerts match the current filter.</div>}

        {filteredAlerts.map((alert) => (
          <article key={alert.alertId} className="alert-card">
            <div className="alert-card-top">
              <span className={`priority-badge ${getSeverityClass(alert.severity)}`}>{alert.severity}</span>

              <span className="alert-type">{alert.rule}</span>
            </div>

            <p className="alert-message">{alert.suggestedAction}</p>

            <div className="alert-meta">
              <span>{alert.assetId}</span>
              <span>{new Date(alert.timestamp).toLocaleTimeString()}</span>
            </div>

            {alert.acknowledged ? (
              <div className="acknowledged-label">Acknowledged</div>
            ) : (
              <button className="ack-button" onClick={() => onAcknowledge(alert.alertId)}>
                Acknowledge
              </button>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
