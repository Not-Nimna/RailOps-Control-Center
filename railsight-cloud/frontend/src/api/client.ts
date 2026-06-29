import type { Alert, Asset, TelemetryPoint } from "../types/railsight";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export function getAssets(): Promise<Asset[]> {
  return request<Asset[]>("/assets");
}

export function getAssetHistory(assetId: string): Promise<TelemetryPoint[]> {
  return request<TelemetryPoint[]>(`/assets/${assetId}/history`);
}

export function getAlerts(): Promise<Alert[]> {
  return request<Alert[]>("/alerts");
}
