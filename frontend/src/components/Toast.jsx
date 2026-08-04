import { createContext, useContext, useState, useCallback } from "react";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const show = useCallback((message, type = "info", duration = 3500) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, message, type }]);
    setTimeout(() => {
      setToasts((t) => t.filter((x) => x.id !== id));
    }, duration);
  }, []);

  const value = {
    success: (m) => show(m, "success"),
    error: (m) => show(m, "error", 6000),
    info: (m) => show(m, "info"),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed top-4 right-4 z-50 space-y-2 pointer-events-none">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto px-4 py-3 rounded-lg shadow-lg backdrop-blur-md border text-sm max-w-sm animate-slidein
              ${t.type === "success" ? "bg-green-500/20 border-green-500/40 text-green-200" : ""}
              ${t.type === "error" ? "bg-red-500/20 border-red-500/40 text-red-200" : ""}
              ${t.type === "info" ? "bg-deep-800/80 border-bio-cyan/40 text-slate-200" : ""}
            `}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be inside ToastProvider");
  return ctx;
}
