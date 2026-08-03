import { useEffect, useState, useCallback } from "react";
import { api } from "../api/client.js";
import { useToast } from "./Toast.jsx";

export function TemplateList({ refreshKey, currentId, onPick }) {
  const toast = useToast();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.listLayoutTemplates();
      setItems(r.templates || []);
    } catch (e) {
      toast.error(`Load templates failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  async function remove(e, id) {
    e.stopPropagation();
    if (!confirm(`Delete template "${id}"? This cannot be undone.`)) return;
    try {
      await api.deleteLayoutTemplate(id);
      toast.success("Template deleted.");
      load();
    } catch (err) {
      toast.error(`Delete failed: ${err.message}`);
    }
  }

  return (
    <div className="panel space-y-2">
      <div className="flex items-center justify-between">
        <div className="panel-title">Templates</div>
        <button className="btn-ghost text-xs px-2 py-1" onClick={load}>
          {loading ? "…" : "↻"}
        </button>
      </div>
      <div className="space-y-1.5 max-h-[420px] overflow-auto pr-1">
        {items.length === 0 && (
          <div className="text-sm text-slate-500 italic">
            {loading ? "Loading…" : "No templates."}
          </div>
        )}
        {items.map((t) => (
          <div
            key={t.id}
            onClick={() => onPick(t)}
            className={`rounded-md border px-3 py-2 cursor-pointer transition-all
              ${
                currentId === t.id
                  ? "bg-bio-cyan/15 border-bio-cyan/40"
                  : "border-deep-700/50 hover:border-deep-600"
              }`}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="text-sm font-medium truncate">{t.name}</div>
              {t._builtin ? (
                <span className="badge text-[9px]">built-in</span>
              ) : (
                <button
                  className="text-[10px] text-red-300 hover:text-red-200"
                  onClick={(e) => remove(e, t.id)}
                  title="Delete user template"
                >
                  delete
                </button>
              )}
            </div>
            <div className="text-[10px] text-slate-500 font-mono truncate">
              {t.id} · {(t.regions || []).length} regions
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
