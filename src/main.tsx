import { createRoot } from "react-dom/client";

import App from "./app/App.tsx";
import { AppProviders } from "./providers/AppProviders.tsx";
import "./styles/index.css";

createRoot(document.getElementById("root")!).render(
  <AppProviders>
    <App />
  </AppProviders>,
);