import { useEffect, useMemo, useState } from "react";
import { getAlerts, getAssetHistory, getAssets } from "./api/client";
import { createRailSightSocket } from "./api/websocket";
import AssetMap from "./components/AssetMap";
import AlertFeed from "./components/AlertFeed";
import AssetDetailPanel from "./components/AssetDetailPanel";
import type { Alert, Asset, TelemetryPoint } from "./types/railsight";
import "./index.css";

const DASHBOARD_POLL_INTERVAL_MS = 5000;
const HISTORY_POLL_INTERVAL_MS = 5000;

function sortAlerts(alerts: Alert[]) {
  const priorityRank = {
    P1: 1,
    P2: 2,
    P3: 3,
  };

  return [...alerts].sort((a, b) => {
    const priorityDiff = priorityRank[a.severity] - priorityRank[b.severity];

    if (priorityDiff !== 0) {
      return priorityDiff;
    }

    return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
  });
}

export default function App() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);

  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const savedTheme = window.localStorage.getItem("railsight-theme");
    return savedTheme === "dark" ? "dark" : "light";
  });

  const [assetHistoryState, setAssetHistoryState] = useState<{
    assetId: string | null;
    history: TelemetryPoint[];
  }>({
    assetId: null,
    history: [],
  });

  const [socketStatus, setSocketStatus] = useState<"connected" | "disconnected">("disconnected");

  const selectedAsset = useMemo(() => {
    return assets.find((asset) => asset.assetId === selectedAssetId) ?? null;
  }, [assets, selectedAssetId]);

  const selectedAssetHistory = useMemo(() => {
    if (!selectedAssetId) {
      return [];
    }

    if (assetHistoryState.assetId !== selectedAssetId) {
      return [];
    }

    return assetHistoryState.history;
  }, [assetHistoryState, selectedAssetId]);

  const selectedAssetAlerts = useMemo(() => {
    if (!selectedAsset) {
      return [];
    }

    return alerts.filter((alert) => alert.assetId === selectedAsset.assetId);
  }, [alerts, selectedAsset]);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboardData() {
      try {
        const [assetData, alertData] = await Promise.all([getAssets(), getAlerts()]);

        if (cancelled) {
          return;
        }

        setAssets(assetData);
        setAlerts(sortAlerts(alertData));

        setSelectedAssetId((currentSelectedAssetId) => {
          if (currentSelectedAssetId) {
            return currentSelectedAssetId;
          }

          return assetData.length > 0 ? assetData[0].assetId : null;
        });
      } catch (error) {
        console.error("Failed to load dashboard data:", error);
      }
    }

    loadDashboardData();

    const intervalId = window.setInterval(() => {
      loadDashboardData();
    }, DASHBOARD_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    window.localStorage.setItem("railsight-theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!selectedAssetId) {
      return;
    }

    const assetId = selectedAssetId;
    let cancelled = false;

    async function loadHistory() {
      try {
        const history = await getAssetHistory(assetId);

        if (cancelled) {
          return;
        }

        setAssetHistoryState({
          assetId,
          history,
        });
      } catch (error) {
        console.error("Failed to load asset history:", error);
      }
    }

    loadHistory();

    const intervalId = window.setInterval(() => {
      loadHistory();
    }, HISTORY_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [selectedAssetId]);

  useEffect(() => {
    const socket = createRailSightSocket(
      (message) => {
        if (message.type === "asset_update") {
          setAssets((current) => {
            const exists = current.some((asset) => asset.assetId === message.asset.assetId);

            if (!exists) {
              return [...current, message.asset];
            }

            return current.map((asset) => (asset.assetId === message.asset.assetId ? message.asset : asset));
          });
        }

        if (message.type === "alert_created") {
          setAlerts((current) => sortAlerts([message.alert, ...current]));
        }

        if (message.type === "alert_acknowledged") {
          setAlerts((current) =>
            current.map((alert) =>
              alert.alertId === message.alertId
                ? {
                    ...alert,
                    acknowledged: true,
                    acknowledgedAt: message.acknowledgedAt,
                  }
                : alert,
            ),
          );
        }
      },
      () => setSocketStatus("connected"),
      () => setSocketStatus("disconnected"),
      (event) => console.error("WebSocket error:", event),
    );

    return () => {
      socket.close();
    };
  }, []);

  function acknowledgeAlert(alertId: string) {
    const acknowledgedAt = new Date().toISOString();

    setAlerts((current) =>
      current.map((alert) =>
        alert.alertId === alertId
          ? {
              ...alert,
              acknowledged: true,
              acknowledgedAt,
            }
          : alert,
      ),
    );

    // Later: replace this with POST /alerts/{alertId}/ack
  }

  return (
    <div className="app-shell" data-theme={theme}>
      <header className="top-bar">
        <div>
          <h1>RailSight Cloud</h1>
          <p>Real-time railway telemetry and alert monitoring</p>
        </div>

        <div className="top-bar-actions">
          <button type="button" className="theme-toggle" aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`} aria-pressed={theme === "dark"} onClick={() => setTheme((currentTheme) => (currentTheme === "light" ? "dark" : "light"))}>
            <span className="theme-toggle__icon" aria-hidden="true">
              {theme === "light" ? "☾" : "☀"}
            </span>
            <span>{theme === "light" ? "Dark" : "Light"}</span>
          </button>

          <div className={`socket-pill ${socketStatus}`}>WebSocket: {socketStatus}</div>
        </div>
      </header>

      <main className="dashboard-grid">
        <section className="map-panel">
          <AssetMap assets={assets} selectedAssetId={selectedAssetId} onSelectAsset={setSelectedAssetId} />
        </section>

        <section className="detail-panel">
          <AssetDetailPanel asset={selectedAsset} history={selectedAssetHistory} alerts={selectedAssetAlerts} />
        </section>

        <aside className="alert-sidebar">
          <AlertFeed alerts={alerts} onAcknowledge={acknowledgeAlert} />
        </aside>
      </main>
    </div>
  );
}
