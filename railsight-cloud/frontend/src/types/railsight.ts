export type AssetStatus = "healthy" | "warning" | "critical" | "offline";

export type AssetType = "locomotive" | "wayside_detector" | "radio_tower" | "track_sensor";

export type AlertSeverity = "P1" | "P2" | "P3";

export interface Asset {
  assetId: string;
  type: AssetType;
  status: AssetStatus;
  lastSeen: string;

  speed?: number;
  gps?: [number, number];
  signalStrength?: number;
  batteryLevel?: number;
  radioChannel?: string;
  sequenceNumber?: number;
  updatedAt?: string;
}

export interface TelemetryPoint {
  assetId: string;
  timestamp: string;
  status?: AssetStatus;

  speed?: number;
  signalStrength?: number;
  batteryLevel?: number;
  latitude?: number;
  longitude?: number;
  expiresAt?: number;
}

export interface Alert {
  alertId: string;
  assetId: string;
  rule: string;
  severity: AlertSeverity;
  suggestedAction: string;
  timestamp: string;
  acknowledged?: boolean;
  resolvedAt?: string | null;
}
