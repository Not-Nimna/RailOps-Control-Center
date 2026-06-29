import type { Alert, Asset, TelemetryPoint } from "../types/railsight";

interface IncidentTimelineProps {
  asset: Asset;
  history: TelemetryPoint[];
  alerts: Alert[];
}

interface TimelineEvent {
  id: string;
  timestamp: string;
  message: string;
}

function getSignalDropEvents(history: TelemetryPoint[]): TimelineEvent[] {
  const events: TimelineEvent[] = [];

  for (let i = 1; i < history.length; i++) {
    const previous = history[i - 1];
    const current = history[i];

    if (previous.signalStrength !== undefined && current.signalStrength !== undefined && previous.signalStrength >= 50 && current.signalStrength < 50) {
      events.push({
        id: `signal-drop-${current.timestamp}`,
        timestamp: current.timestamp,
        message: `Signal dropped below 50% (${previous.signalStrength}% → ${current.signalStrength}%)`,
      });
    }
  }

  return events;
}

function getStatusChangeEvents(history: TelemetryPoint[]): TimelineEvent[] {
  const events: TimelineEvent[] = [];

  for (let i = 1; i < history.length; i++) {
    const previous = history[i - 1];
    const current = history[i];

    if (previous.status && current.status && previous.status !== current.status) {
      events.push({
        id: `status-change-${current.timestamp}`,
        timestamp: current.timestamp,
        message: `Status changed: ${previous.status} → ${current.status}`,
      });
    }
  }

  return events;
}

function getAlertEvents(alerts: Alert[]): TimelineEvent[] {
  const createdEvents = alerts.map((alert) => ({
    id: `alert-created-${alert.alertId}`,
    timestamp: alert.timestamp,
    message: `${alert.severity} Alert created: ${alert.rule}`,
  }));

  return createdEvents;
}

export default function IncidentTimeline({ history, alerts }: IncidentTimelineProps) {
  const events = [...getSignalDropEvents(history), ...getStatusChangeEvents(history), ...getAlertEvents(alerts)].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  return (
    <section className="timeline-section">
      <h3>Incident Timeline</h3>

      {events.length === 0 ? (
        <div className="empty-state">No incidents detected for this asset.</div>
      ) : (
        <ol className="timeline-list">
          {events.map((event) => (
            <li key={event.id}>
              <span className="timeline-dot" />
              <time>{new Date(event.timestamp).toLocaleTimeString()}</time>
              <p>{event.message}</p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
