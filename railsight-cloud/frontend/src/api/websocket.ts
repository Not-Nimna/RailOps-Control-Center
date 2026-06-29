import type { Alert, Asset } from "../types/railsight";

export type RailSightSocketMessage =
  | {
      type: "asset_update";
      asset: Asset;
    }
  | {
      type: "alert_created";
      alert: Alert;
    }
  | {
      type: "alert_acknowledged";
      alertId: string;
      acknowledgedAt: string;
    }
  | {
      type: "connected";
      message: string;
    };

export function createRailSightSocket(onMessage: (message: RailSightSocketMessage) => void, onOpen?: () => void, onClose?: () => void, onError?: (event: Event) => void): WebSocket {
  const socket = new WebSocket(import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/ws");

  socket.onopen = () => {
    onOpen?.();
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as RailSightSocketMessage;
      onMessage(data);
    } catch (error) {
      console.error("Invalid WebSocket message:", event.data, error);
    }
  };

  socket.onclose = () => {
    onClose?.();
  };

  socket.onerror = (event) => {
    onError?.(event);
  };

  return socket;
}
