import { useRef, useState } from "react";
import { api } from "../api/client.js";
import { useToast } from "./Toast.jsx";

/**
 * PhotoAvatarUpload — creates a custom HeyGen photo avatar from a local image.
 *
 * Flow:
 *  1. User picks/drops a PNG/JPG/WEBP
 *  2. Upload as multipart to /api/heygen/photo-avatar/create
 *  3. Backend uploads to HeyGen, creates group, adds photo, polls until ready
 *  4. On success: callback parent (onCreated) so it can refresh avatar list
 */
export function PhotoAvatarUpload({ onCreated }) {
  const toast = useToast();
  const fileInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [avatarName, setAvatarName] = useState("Deepotus custom");
  const [groupName, setGroupName] = useState("");
  const [doTrain, setDoTrain] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [stage, setStage] = useState(""); // visual progress hint
  const [dragOver, setDragOver] = useState(false);

  function handleFileChosen(f) {
    if (!f) return;
    const allowed = ["image/png", "image/jpeg", "image/webp"];
    if (!allowed.includes(f.type)) {
      toast.error("File must be PNG, JPG, or WEBP");
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      toast.error("File must be under 10 MB");
      return;
    }
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
  }

  async function submit() {
    if (!file) {
      toast.error("Pick a file first");
      return;
    }
    setUploading(true);
    setStage("Uploading to HeyGen...");
    const fd = new FormData();
    fd.append("file", file);
    fd.append("avatar_name", avatarName || "Deepotus custom");
    if (groupName) fd.append("group_name", groupName);
    fd.append("do_train", doTrain ? "true" : "false");

    try {
      setStage("Creating avatar group + polling (10-30s)...");
      const result = await api.createPhotoAvatar(fd);
      toast.success(`Avatar created: ${result.avatar_name}`);
      setStage("");
      setFile(null);
      setPreviewUrl(null);
      if (onCreated) onCreated(result);
    } catch (e) {
      toast.error(`Upload failed: ${e.message}`);
      setStage("");
    } finally {
      setUploading(false);
    }
  }

  function onDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFileChosen(f);
  }

  return (
    <div className="panel space-y-3 border-bio-violet/30">
      <div className="panel-title flex items-center justify-between mb-0">
        <span>Photo Avatar</span>
        <span className="badge bg-bio-violet/20 border-bio-violet/40 text-bio-violet text-[9px]">
          v1.5
        </span>
      </div>
      <div className="text-[10px] text-slate-400 -mt-1">
        Upload a photo → HeyGen creates a custom talking avatar.
        Best: face centered, well-lit, neutral background.
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-lg p-4 cursor-pointer transition-all
          ${dragOver ? "border-bio-cyan bg-bio-cyan/10" : "border-deep-700 hover:border-bio-violet/50"}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          className="hidden"
          onChange={(e) => handleFileChosen(e.target.files?.[0])}
        />
        {previewUrl ? (
          <div className="flex items-center gap-3">
            <img src={previewUrl} alt="preview"
                 className="w-16 h-16 object-cover rounded border border-deep-700" />
            <div className="flex-1 text-xs">
              <div className="font-mono truncate text-bio-cyan">{file?.name}</div>
              <div className="text-slate-500">{(file?.size / 1024).toFixed(0)} KB</div>
            </div>
          </div>
        ) : (
          <div className="text-center text-xs text-slate-400">
            <div className="text-2xl mb-1">📸</div>
            Drop image or click to pick<br/>
            <span className="text-[10px] text-slate-500">PNG / JPG / WEBP, max 10 MB</span>
          </div>
        )}
      </div>

      <label className="block">
        <div className="text-[10px] uppercase tracking-wider text-slate-400 font-mono mb-1">
          Avatar name
        </div>
        <input
          type="text"
          className="input text-xs"
          value={avatarName}
          onChange={(e) => setAvatarName(e.target.value)}
          maxLength={60}
          placeholder="Deepotus custom"
        />
      </label>

      <label className="flex items-center gap-2 text-xs">
        <input
          type="checkbox"
          checked={doTrain}
          onChange={(e) => setDoTrain(e.target.checked)}
          className="accent-bio-violet"
        />
        Train the group (better consistency across regenerations)
      </label>

      {stage && (
        <div className="text-xs text-bio-cyan bg-bio-cyan/5 border border-bio-cyan/30 rounded p-2 animate-pulse">
          ⏳ {stage}
        </div>
      )}

      <button
        onClick={submit}
        disabled={!file || uploading}
        className="btn-primary w-full"
      >
        {uploading ? "Creating..." : "📸 Create avatar"}
      </button>

      <div className="text-[9px] text-slate-500 italic leading-tight">
        Cost: ~$0.20 in HeyGen credits to create. The avatar persists on your account
        and can be reused for unlimited videos.
      </div>
    </div>
  );
}
