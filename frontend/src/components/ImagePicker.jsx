import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { useToast } from "./Toast.jsx";

/**
 * Mode "start": clicking selects start image
 * Mode "end": clicking selects end image (for first-last frame transition)
 */
export function ImagePicker({ startImage, endImage, onSelectStart, onSelectEnd }) {
  const [images, setImages] = useState([]);
  const [folder, setFolder] = useState("");
  const [warning, setWarning] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pickMode, setPickMode] = useState("start");
  const toast = useToast();

  async function refresh() {
    setLoading(true);
    try {
      const data = await api.listImages();
      setImages(data.images || []);
      setFolder(data.folder || "");
      setWarning(data.warning || null);
    } catch (e) {
      setWarning(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    const i = setInterval(refresh, 5000);
    return () => clearInterval(i);
  }, []);

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await api.uploadImage(file);
      toast.success(`Uploaded: ${file.name}`);
      await refresh();
    } catch (err) {
      toast.error(`Upload failed: ${err.message}`);
    }
  }

  function handlePick(filename) {
    if (pickMode === "start") {
      onSelectStart(filename);
    } else {
      // Don't allow end == start
      if (filename === startImage) {
        toast.error("End image must differ from start");
        return;
      }
      onSelectEnd(filename);
    }
  }

  return (
    <div className="panel">
      <div className="flex items-center justify-between mb-3">
        <div className="panel-title mb-0">Source Images</div>
        <label className="btn-ghost cursor-pointer text-xs">
          + Upload
          <input type="file" accept="image/*" className="hidden" onChange={handleUpload} />
        </label>
      </div>

      {/* Pick mode toggle */}
      <div className="flex gap-1 mb-3 p-1 bg-deep-950/60 rounded-lg">
        <button
          onClick={() => setPickMode("start")}
          className={`flex-1 text-xs py-1.5 rounded-md transition-colors ${
            pickMode === "start"
              ? "bg-bio-cyan/20 text-bio-cyan border border-bio-cyan/40"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          Set Start
        </button>
        <button
          onClick={() => setPickMode("end")}
          className={`flex-1 text-xs py-1.5 rounded-md transition-colors ${
            pickMode === "end"
              ? "bg-bio-violet/20 text-bio-violet border border-bio-violet/40"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          Set End (transition)
        </button>
      </div>

      <div className="text-xs text-slate-500 font-mono mb-2 truncate" title={folder}>
        📁 {folder}
      </div>

      {/* Selected indicators */}
      <div className="grid grid-cols-2 gap-2 mb-3 text-[10px]">
        <div className="p-1.5 rounded border border-bio-cyan/30 bg-bio-cyan/5">
          <span className="text-bio-cyan/80 uppercase tracking-wider">Start</span>
          <div className="truncate text-slate-300 font-mono mt-0.5" title={startImage}>
            {startImage || "—"}
          </div>
        </div>
        <div className="p-1.5 rounded border border-bio-violet/30 bg-bio-violet/5">
          <div className="flex items-center justify-between">
            <span className="text-bio-violet/80 uppercase tracking-wider">End</span>
            {endImage && (
              <button
                onClick={() => onSelectEnd(null)}
                className="text-slate-500 hover:text-red-400 text-[10px]"
                title="Remove end image"
              >
                ✕
              </button>
            )}
          </div>
          <div className="truncate text-slate-300 font-mono mt-0.5" title={endImage}>
            {endImage || "(optional)"}
          </div>
        </div>
      </div>

      {warning && (
        <div className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded p-2 mb-3">
          ⚠️ {warning}
        </div>
      )}
      {images.length === 0 && !loading && (
        <div className="text-sm text-slate-500 text-center py-8">
          Aucune image. Drop tes PNG/JPG dans le dossier ci-dessus, ou Upload.
        </div>
      )}

      <div className="grid grid-cols-3 gap-2 max-h-[420px] overflow-y-auto pr-1">
        {images.map((img) => {
          const isStart = startImage === img.filename;
          const isEnd = endImage === img.filename;
          return (
            <button
              key={img.filename}
              onClick={() => handlePick(img.filename)}
              className={`relative aspect-square rounded-lg overflow-hidden border-2 transition-all
                ${isStart ? "border-bio-cyan shadow-glow" : ""}
                ${isEnd ? "border-bio-violet shadow-glow-violet" : ""}
                ${!isStart && !isEnd ? "border-deep-700 hover:border-bio-cyan/50" : ""}
              `}
              title={`${img.filename} — ${img.width}×${img.height} — ${img.size_kb}KB`}
            >
              <img
                src={api.imageUrl(img.filename)}
                alt={img.filename}
                className="w-full h-full object-cover"
                loading="lazy"
              />
              {(isStart || isEnd) && (
                <div className="absolute inset-0 flex items-end p-1.5">
                  <span className={`badge font-bold ${
                    isStart ? "bg-bio-cyan text-deep-950 border-bio-cyan" :
                    "bg-bio-violet text-white border-bio-violet"
                  }`}>
                    {isStart ? "START" : "END"}
                  </span>
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
