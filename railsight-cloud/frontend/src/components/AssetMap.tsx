import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import L from "leaflet";
import type { Asset, AssetStatus, AssetType } from "../types/railsight";
import "leaflet/dist/leaflet.css";

interface AssetMapProps {
  assets: Asset[];
  selectedAssetId: string | null;
  onSelectAsset: (assetId: string) => void;
}

const CALGARY_POSITION: [number, number] = [51.0447, -114.0719];

function getStatusColor(status: AssetStatus) {
  switch (status) {
    case "healthy":
      return "#22c55e";
    case "warning":
      return "#eab308";
    case "critical":
      return "#ef4444";
    case "offline":
      return "#6b7280";
    default:
      return "#6b7280";
  }
}

function getAssetIcon(type: AssetType) {
  switch (type) {
    case "locomotive":
      return "🚆";
    case "radio_tower":
      return "📡";
    case "wayside_detector":
      return "🛤️";
    case "track_sensor":
      return "📍";
    default:
      return "●";
  }
}

function createAssetMarker(asset: Asset, isSelected: boolean) {
  const color = getStatusColor(asset.status);
  const icon = getAssetIcon(asset.type);

  return L.divIcon({
    className: "",
    html: `
      <div style="
        width: ${isSelected ? "42px" : "34px"};
        height: ${isSelected ? "42px" : "34px"};
        border-radius: 999px;
        background: ${color};
        border: 3px solid white;
        box-shadow: 0 6px 16px rgba(0,0,0,0.35);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: ${isSelected ? "22px" : "18px"};
      ">
        ${icon}
      </div>
    `,
    iconSize: isSelected ? [42, 42] : [34, 34],
    iconAnchor: isSelected ? [21, 21] : [17, 17],
  });
}

export default function AssetMap({ assets, selectedAssetId, onSelectAsset }: AssetMapProps) {
  return (
    <MapContainer center={CALGARY_POSITION} zoom={10} className="asset-map">
      <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

      {assets.map((asset) => {
        const gps = asset.gps;

        if (!gps || gps.length < 2) {
          return null;
        }

        const isSelected = asset.assetId === selectedAssetId;

        return (
          <Marker
            key={asset.assetId}
            position={[gps[0], gps[1]]}
            icon={createAssetMarker(asset, isSelected)}
            eventHandlers={{
              click: () => onSelectAsset(asset.assetId),
            }}>
            <Popup>
              <strong>{asset.assetId}</strong>
              <br />
              Type: {asset.type}
              <br />
              Status: {asset.status}
              <br />
              Signal: {asset.signalStrength ?? "N/A"}%
            </Popup>
          </Marker>
        );
      })}
    </MapContainer>
  );
}
