// App.jsx — v1.8 Reef edition. Mounts the new DeepotusApp shell (Sidebar
// + Topbar + JobDock) at full viewport with the tokens.css design system.
// The legacy components (ImagePicker, GenerationForm, …) are still in
// `src/components/` if a hotfix needs them, but they're no longer routed.
import React, { useEffect } from "react";
import { ToastProvider } from "./components/Toast.jsx";
import { DeepotusApp } from "./studio/shell.jsx";

export default function App() {
  // The .deepotus root in tokens.css scopes the design tokens. Apply it
  // once to the body so background, font and focus tokens work everywhere.
  // Also restore the persisted Appearance prefs (Reduced motion / Halo)
  // so the toggles take effect on first paint, not after Settings is opened.
  useEffect(() => {
    document.body.classList.add("deepotus");
    document.body.classList.remove(
      "bg-deep-950",
      "text-slate-100",
      "antialiased"
    );
    document.body.style.margin = "0";
    document.body.style.minHeight = "100vh";
    const html = document.documentElement;
    if (localStorage.getItem("deepotus.motion.reduced") === "1") html.classList.add("no-motion");
    if (localStorage.getItem("deepotus.motion.halo") === "0") html.classList.add("no-halo");
    return () => {
      document.body.classList.remove("deepotus");
    };
  }, []);

  return (
    <ToastProvider>
      <div
        className="deepotus depth-bg"
        style={{ width: "100vw", height: "100vh", overflow: "hidden" }}
      >
        <DeepotusApp variant="reef" initialView="studio" />
      </div>
    </ToastProvider>
  );
}
