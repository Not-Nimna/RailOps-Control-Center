import AIAssistant from "./components/AIAssistant";
import AlertFeed from "./components/AlertFeed";
import AnalyticsPage from "./components/AnalyticsPage";
import AssetDetail from "./components/AssetDetail";
import AssetMap from "./components/AssetMap";
import IncidentTimeline from "./components/IncidentTimeline";

export default function App() {
  return (
    <main>
      <AssetMap />
      <AlertFeed />
      <AssetDetail />
      <IncidentTimeline />
      <AnalyticsPage />
      <AIAssistant />
    </main>
  );
}
