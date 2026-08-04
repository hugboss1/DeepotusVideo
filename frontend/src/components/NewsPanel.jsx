import { useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";
import { useToast } from "./Toast.jsx";

const VOICE_MODES = ["", "oracle", "alpha", "zen", "memer"];

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="text-[10px] uppercase tracking-wide text-slate-500">
        {label}
      </span>
      {children}
    </label>
  );
}

export function NewsPanel() {
  const toast = useToast();
  const [sources, setSources] = useState([]);
  const [items, setItems] = useState([]);
  const [fetchedAt, setFetchedAt] = useState(null);
  const [errors, setErrors] = useState([]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState({}); // id -> item
  const [busy, setBusy] = useState(false);

  // add-source form
  const [newUrl, setNewUrl] = useState("");
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("rss");

  // script
  const [voiceMode, setVoiceMode] = useState("");
  const [language, setLanguage] = useState("EN");
  const [maxWords, setMaxWords] = useState(800);
  const [summaryWords, setSummaryWords] = useState(200);
  const [angle, setAngle] = useState("");
  const [script, setScript] = useState("");
  const [caption, setCaption] = useState("");
  const [readArticles, setReadArticles] = useState(true);
  const [newsImages, setNewsImages] = useState([]);
  const [sourcesRead, setSourcesRead] = useState(0);
  const [essences, setEssences] = useState([]);

  // illustration
  const [perCard, setPerCard] = useState(3.5);
  const [illJob, setIllJob] = useState(null);
  const pollRef = useRef(null);

  // build post (avatar + reel composed via tpl_news_reel)
  const [avatars, setAvatars] = useState([]);
  const [voices, setVoices] = useState([]);
  const [avatarQuery, setAvatarQuery] = useState("");
  const [avatarId, setAvatarId] = useState("");
  const [avatarType, setAvatarType] = useState("avatar");
  const [voiceId, setVoiceId] = useState("");
  const [postJob, setPostJob] = useState(null);
  const [postStage, setPostStage] = useState("");

  async function loadSources() {
    try {
      const r = await api.listNewsSources();
      setSources(r.sources || []);
    } catch (e) {
      toast.error(`Sources: ${e.message}`);
    }
  }
  async function loadItems() {
    try {
      const r = await api.listNewsItems();
      setItems(r.items || []);
      setFetchedAt(r.fetched_at || null);
      setErrors(r.errors || []);
    } catch (e) {
      toast.error(`Items: ${e.message}`);
    }
  }
  useEffect(() => {
    loadSources();
    loadItems();
    api.listHeygenAvatars().then((r) => setAvatars(r.avatars || [])).catch(() => {});
    api.listHeygenVoices().then((r) => setVoices(r.voices || [])).catch(() => {});
    return () => clearInterval(pollRef.current);
  }, []);

  function sleep(ms) {
    return new Promise((res) => setTimeout(res, ms));
  }
  async function waitJob(id, onTick, maxMs = 600000) {
    const t0 = Date.now();
    while (Date.now() - t0 < maxMs) {
      let j;
      try {
        j = await api.getJob(id);
      } catch {
        await sleep(2500);
        continue;
      }
      onTick && onTick(j);
      if (j.status === "done" || j.status === "failed") return j;
      await sleep(2500);
    }
    return { status: "failed", error: "timed out waiting for job" };
  }

  async function addSource() {
    if (!newUrl.trim()) return;
    try {
      await api.addNewsSource(newUrl.trim(), newName.trim(), newType);
      setNewUrl("");
      setNewName("");
      toast.success("Source added.");
      loadSources();
    } catch (e) {
      toast.error(`Add failed: ${e.message}`);
    }
  }
  async function loadCuratedPack() {
    try {
      const r = await api.seedDefaultNewsSources();
      toast.success(
        `Curated pack: +${r.added}` +
          (r.removed ? `, -${r.removed} Google News` : "") +
          ` (total ${r.total}).`
      );
      loadSources();
    } catch (e) {
      toast.error(`Curated pack failed: ${e.message}`);
    }
  }
  async function delSource(id) {
    try {
      await api.deleteNewsSource(id);
      loadSources();
    } catch (e) {
      toast.error(e.message);
    }
  }
  async function toggleSource(id, enabled) {
    try {
      await api.toggleNewsSource(id, enabled);
      loadSources();
    } catch (e) {
      toast.error(e.message);
    }
  }
  async function refresh() {
    setBusy(true);
    try {
      const r = await api.refreshNews();
      toast.success(`Fetched ${r.item_count} items.`);
      await loadItems();
    } catch (e) {
      toast.error(`Refresh failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }

  function toggleItem(it) {
    setSelected((s) => {
      const n = { ...s };
      if (n[it.id]) delete n[it.id];
      else n[it.id] = it;
      return n;
    });
  }
  const selList = Object.values(selected);

  const q = query.trim().toLowerCase();
  const shown = q
    ? items.filter((it) =>
        `${it.title} ${it.source_name}`.toLowerCase().includes(q)
      )
    : items;

  async function genScript() {
    if (selList.length === 0) {
      toast.error("Select at least one news item.");
      return;
    }
    setBusy(true);
    try {
      const r = await api.newsScript({
        items: selList.map((it) => ({
          title: it.title,
          summary: it.summary || "",
          source_name: it.source_name || "",
          link: it.link || "",
        })),
        voice_mode: voiceMode || null,
        language,
        max_words: Number(maxWords),
        summary_words: Number(summaryWords),
        angle: angle.trim() || null,
        read_articles: readArticles,
      });
      setScript(r.script);
      setCaption(r.suggested_caption);
      setNewsImages(r.images || []);
      setSourcesRead(r.sources_read || 0);
      setEssences(r.essences || []);
      toast.success(
        `Script ready (${r.word_count} words` +
          (r.sources_read ? `, ${r.sources_read} articles read` : "") +
          (r.images?.length ? `, ${r.images.length} images` : "") +
          ").");
    } catch (e) {
      toast.error(`Script failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }

  function pollJob(id) {
    clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const j = await api.getJob(id);
        setIllJob(j);
        if (j.status === "done" || j.status === "failed") {
          clearInterval(pollRef.current);
          if (j.status === "done") toast.success("Illustration ready.");
          else toast.error(`Illustration failed: ${j.error || "unknown"}`);
        }
      } catch {
        /* keep polling */
      }
    }, 2000);
  }

  async function genIllustration() {
    if (selList.length === 0) {
      toast.error("Select at least one news item.");
      return;
    }
    setIllJob(null);
    try {
      const r = await api.newsIllustration({
        items: selList.map((it) => ({
          title: it.title,
          summary: it.summary || "",
          source_name: it.source_name || "",
          link: it.link || "",
        })),
        per_card_s: Number(perCard),
        engine: "ffmpeg",
      });
      toast.success("Illustration queued.");
      setIllJob({ job_id: r.job_id, status: "queued", progress: 0 });
      pollJob(r.job_id);
    } catch (e) {
      toast.error(`Illustration failed: ${e.message}`);
    }
  }

  async function buildPost() {
    if (!script.trim()) {
      toast.error("Generate a script first.");
      return;
    }
    if (selList.length === 0) {
      toast.error("Select at least one news item.");
      return;
    }
    if (!avatarId || !voiceId) {
      toast.error("Pick a HeyGen avatar and voice for the post.");
      return;
    }
    const itemsPayload = selList.map((it) => ({
      title: it.title,
      summary: it.summary || "",
      source_name: it.source_name || "",
      link: it.link || "",
    }));
    setPostJob(null);
    try {
      // 1. Render the news illustration reel
      setPostStage("Rendering news reel…");
      const ill = await api.newsIllustration({
        items: itemsPayload,
        per_card_s: Number(perCard),
        engine: "ffmpeg",
      });
      const reelDone = await waitJob(ill.job_id, (j) =>
        setPostStage(`News reel… ${j.progress ?? 0}%`)
      );
      if (reelDone.status !== "done") {
        toast.error(`Reel failed: ${reelDone.error || "unknown"}`);
        setPostStage("");
        return;
      }
      // 2. Compose reel + avatar(script) via the built-in news template
      setPostStage("Composing avatar + reel…");
      const r = await api.renderLayoutTemplate(
        "tpl_news_reel",
        {
          reel: { source_kind: "job", job_id: ill.job_id },
          avatar: {
            source_kind: "heygen",
            heygen: {
              avatar_id: avatarId,
              avatar_type: avatarType,
              voice_id: voiceId,
              script: script,
            },
          },
        },
        voiceMode || null
      );
      const fin = await waitJob(r.job_id, (j) => {
        setPostJob(j);
        setPostStage(`Composing… ${j.status} ${j.progress ?? 0}%`);
      });
      setPostJob(fin);
      if (fin.status === "done") {
        setPostStage("Done");
        toast.success("Post ready.");
      } else {
        setPostStage("");
        toast.error(`Compose failed: ${fin.error || "unknown"}`);
      }
    } catch (e) {
      setPostStage("");
      toast.error(`Build post failed: ${e.message}`);
    }
  }

  const avMatches = avatarQuery.trim()
    ? avatars.filter((a) =>
        `${a.name || ""} ${a.avatar_name || ""} ${a.avatar_id || ""}`
          .toLowerCase()
          .includes(avatarQuery.trim().toLowerCase())
      )
    : avatars;

  function copy(text) {
    navigator.clipboard?.writeText(text).then(
      () => toast.success("Copied."),
      () => toast.error("Copy failed.")
    );
  }

  return (
    <div className="col-span-12 grid grid-cols-12 gap-4">
      {/* Sources */}
      <div className="col-span-12 lg:col-span-3 space-y-4">
        <div className="panel space-y-3">
          <div className="panel-title">Sources</div>
          <Field label="Feed or article URL">
            <input
              className="input w-full"
              placeholder="https://feeds.bbci.co.uk/news/world/rss.xml"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
            />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Name (optional)">
              <input
                className="input w-full"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </Field>
            <Field label="Type">
              <select
                className="input w-full"
                value={newType}
                onChange={(e) => setNewType(e.target.value)}
              >
                <option value="rss">RSS/Atom</option>
                <option value="article">Article URL</option>
              </select>
            </Field>
          </div>
          <div className="flex gap-2">
            <button
              className="btn-ghost flex-1 text-sm"
              onClick={addSource}
            >
              + Add source
            </button>
            <button
              className="btn-ghost flex-1 text-sm"
              onClick={loadCuratedPack}
            >
              Load curated pack
            </button>
          </div>
          <div className="space-y-1.5 max-h-64 overflow-auto pr-1">
            {sources.length === 0 && (
              <div className="text-xs text-slate-500 italic">
                No sources yet. Add an RSS feed (e.g. Google News RSS,
                a crypto site feed) or a single article URL.
              </div>
            )}
            {sources.map((s) => (
              <div
                key={s.id}
                className="flex items-center gap-2 text-xs border border-deep-700/50 rounded px-2 py-1.5"
              >
                <input
                  type="checkbox"
                  checked={s.enabled}
                  onChange={(e) => toggleSource(s.id, e.target.checked)}
                  title="Enabled"
                />
                <div className="flex-1 min-w-0">
                  <div className="truncate">{s.name}</div>
                  <div className="text-[9px] text-slate-500 font-mono truncate">
                    {s.type} · {s.url}
                  </div>
                </div>
                <button
                  className="text-red-300 hover:text-red-200"
                  onClick={() => delSource(s.id)}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
          <button
            className="btn-primary w-full text-sm"
            onClick={refresh}
            disabled={busy}
          >
            {busy ? "Working…" : "↻ Refresh feeds"}
          </button>
          <div className="text-[10px] text-slate-500">
            {fetchedAt
              ? `Last fetched: ${fetchedAt.replace("T", " ")}`
              : "Never fetched"}
            {" · auto-refreshes daily while the app runs"}
          </div>
          {errors.length > 0 && (
            <div className="text-[10px] text-amber-300">
              {errors.length} source error(s): {errors[0].error?.slice(0, 80)}
            </div>
          )}
        </div>
      </div>

      {/* Items */}
      <div className="col-span-12 lg:col-span-6">
        <div className="panel space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div className="panel-title">
              News ({selList.length}/{items.length} selected)
            </div>
            <button
              className="btn-ghost text-xs px-2 py-1"
              onClick={() => setSelected({})}
            >
              Clear
            </button>
          </div>
          <input
            className="input w-full"
            placeholder="Filter headlines…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div className="space-y-1.5 max-h-[560px] overflow-auto pr-1">
            {shown.length === 0 && (
              <div className="text-sm text-slate-500 italic">
                No items. Add sources and hit Refresh.
              </div>
            )}
            {shown.map((it) => (
              <label
                key={it.id}
                className={`block border rounded-md px-3 py-2 cursor-pointer transition-all ${
                  selected[it.id]
                    ? "bg-bio-cyan/15 border-bio-cyan/40"
                    : "border-deep-700/50 hover:border-deep-600"
                }`}
              >
                <div className="flex gap-2">
                  <input
                    type="checkbox"
                    checked={!!selected[it.id]}
                    onChange={() => toggleItem(it)}
                    className="mt-1"
                  />
                  <div className="min-w-0">
                    <div className="text-sm font-medium leading-snug">
                      {it.link ? (
                        <a
                          href={it.link}
                          target="_blank"
                          rel="noreferrer"
                          className="hover:text-bio-cyan underline decoration-dotted"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {it.title} <span className="text-[10px]">↗</span>
                        </a>
                      ) : (
                        it.title
                      )}
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono">
                      {it.link ? (
                        <a
                          href={it.link}
                          target="_blank"
                          rel="noreferrer"
                          className="hover:text-bio-cyan"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {it.source_name}
                        </a>
                      ) : (
                        it.source_name
                      )}
                      {it.published
                        ? ` · ${it.published.slice(0, 16).replace("T", " ")}`
                        : ""}
                    </div>
                    {it.summary && (
                      <div className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                        {it.summary.slice(0, 180)}
                      </div>
                    )}
                  </div>
                </div>
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="col-span-12 lg:col-span-3 space-y-4">
        <div className="panel space-y-3">
          <div className="panel-title">Script</div>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Voice mode">
              <select
                className="input w-full"
                value={voiceMode}
                onChange={(e) => setVoiceMode(e.target.value)}
              >
                {VOICE_MODES.map((m) => (
                  <option key={m} value={m}>
                    {m || "(none)"}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Language">
              <select
                className="input w-full"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
              >
                <option value="EN">EN</option>
                <option value="FR">FR</option>
              </select>
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Summary words / article">
              <input
                type="number"
                className="input w-full"
                min={40}
                max={2000}
                step={50}
                value={summaryWords}
                onChange={(e) => setSummaryWords(e.target.value)}
              />
            </Field>
            <Field label="Script max words">
              <input
                type="number"
                className="input w-full"
                min={20}
                max={6000}
                step={50}
                value={maxWords}
                onChange={(e) => setMaxWords(e.target.value)}
              />
            </Field>
          </div>
          <Field label="Angle (optional)">
            <input
              className="input w-full"
              placeholder="bullish, skeptical…"
              value={angle}
              onChange={(e) => setAngle(e.target.value)}
            />
          </Field>
          <div className="text-[10px] text-slate-500">
            Long-form: set Summary words high (e.g. 600+) and Script max
            words ≥ summary × number of selected articles so the prophet
            script keeps the full length.
          </div>
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={readArticles}
              onChange={(e) => setReadArticles(e.target.checked)}
            />
            <span>
              Read full articles → prophet summary + extract images
            </span>
          </label>
          <button
            className="btn-primary w-full"
            onClick={genScript}
            disabled={busy}
          >
            {busy
              ? "Working…"
              : readArticles
              ? "Read articles + generate script"
              : "Generate script"}
          </button>
          {script && (
            <>
              {essences.length > 0 && (
                <div className="space-y-2">
                  <div className="text-[10px] uppercase tracking-wide text-slate-500">
                    Article summaries ({essences.length})
                  </div>
                  <div className="space-y-1.5 max-h-60 overflow-auto pr-1">
                    {essences.map((e, i) => (
                      <div
                        key={i}
                        className="border border-deep-700/50 rounded-md p-2 text-xs"
                      >
                        <div className="flex items-start gap-2">
                          {e.image && (
                            <img
                              src={api.imageUrl(e.image)}
                              alt=""
                              className="w-12 h-12 object-cover rounded shrink-0"
                            />
                          )}
                          <div className="min-w-0">
                            {e.link ? (
                              <a
                                href={e.link}
                                target="_blank"
                                rel="noreferrer"
                                className="font-medium hover:text-bio-cyan underline decoration-dotted"
                              >
                                {e.title || e.link} ↗
                              </a>
                            ) : (
                              <span className="font-medium">{e.title}</span>
                            )}
                            <span
                              className={`ml-1 text-[9px] font-mono ${
                                /rss|blocked|error|empty/.test(e.status)
                                  ? "text-amber-400"
                                  : "text-green-400"
                              }`}
                            >
                              [{e.status || "?"}]
                            </span>
                            <div className="text-slate-400 mt-1">
                              {e.essence || "(no summary extracted)"}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="text-[9px] text-slate-500">
                    Status green = real article body · amber = fell back to
                    the RSS snippet (paywall / hard block / Google wrapper).
                  </div>
                </div>
              )}
              <Field label="Script (editable, → HeyGen)">
                <textarea
                  className="input w-full h-28"
                  value={script}
                  onChange={(e) => setScript(e.target.value)}
                />
              </Field>
              <textarea
                className="input w-full h-16 text-xs"
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
              />
              <div className="flex gap-2">
                <button
                  className="btn-ghost flex-1 text-xs"
                  onClick={() => copy(script)}
                >
                  Copy script
                </button>
                <button
                  className="btn-ghost flex-1 text-xs"
                  onClick={() => copy(caption)}
                >
                  Copy caption
                </button>
              </div>
              {sourcesRead > 0 && (
                <div className="text-[10px] text-slate-500">
                  {sourcesRead} article(s) read · prophet (cynical/humorous)
                  tone applied.
                </div>
              )}
              {newsImages.length > 0 && (
                <div className="space-y-1">
                  <div className="text-[10px] uppercase tracking-wide text-slate-500">
                    Extracted illustrations ({newsImages.length}) — saved to
                    assets/images, ready for Seedance
                  </div>
                  <div className="grid grid-cols-3 gap-1">
                    {newsImages.map((fn) => (
                      <a
                        key={fn}
                        href={api.imageUrl(fn)}
                        target="_blank"
                        rel="noreferrer"
                        title={fn}
                      >
                        <img
                          src={api.imageUrl(fn)}
                          alt={fn}
                          className="w-full h-16 object-cover rounded border border-deep-700/50"
                        />
                      </a>
                    ))}
                  </div>
                </div>
              )}
              <div className="text-[10px] text-slate-500">
                Paste the script into the 🎤 HeyGen tab (avatar + voice), or
                use “🐙 Build post” below. Extracted images appear in the
                Seedance image picker.
              </div>
            </>
          )}
        </div>

        <div className="panel space-y-3">
          <div className="panel-title">Illustration reel</div>
          <Field label={`Seconds per headline (${perCard}s)`}>
            <input
              type="range"
              className="w-full"
              min={2}
              max={8}
              step={0.5}
              value={perCard}
              onChange={(e) => setPerCard(e.target.value)}
            />
          </Field>
          <button
            className="btn-primary w-full"
            onClick={genIllustration}
            disabled={!!illJob && illJob.status !== "done" && illJob.status !== "failed"}
          >
            Generate news reel
          </button>
          {illJob && (
            <div className="rounded-md border border-deep-700/50 p-2 space-y-2">
              <div className="text-[11px] font-mono text-slate-400">
                {illJob.job_id?.slice(0, 12)} · {illJob.status} ·{" "}
                {illJob.progress ?? 0}%
              </div>
              {illJob.status === "done" && (
                <>
                  <video
                    key={illJob.job_id}
                    className="w-full rounded bg-black"
                    src={api.jobVideoUrl(illJob.job_id)}
                    controls
                  />
                  <a
                    className="btn-ghost block text-center text-xs"
                    href={api.jobVideoUrl(illJob.job_id)}
                    download
                  >
                    Download MP4
                  </a>
                  <div className="text-[10px] text-slate-500">
                    Reusable in any 🎨 Template slot via the “existing”
                    source (it’s in the job queue).
                  </div>
                </>
              )}
              {illJob.status === "failed" && (
                <div className="text-xs text-red-300">{illJob.error}</div>
              )}
            </div>
          )}
        </div>

        <div className="panel space-y-3">
          <div className="panel-title">Build post (one click)</div>
          <div className="text-[10px] text-slate-500">
            Reel + avatar reading the script, composed via the built-in
            <span className="font-mono"> tpl_news_reel </span> template.
          </div>
          <Field label={`Avatar (search ${avatars.length})`}>
            <input
              className="input w-full mb-1"
              placeholder="filter avatars…"
              value={avatarQuery}
              onChange={(e) => setAvatarQuery(e.target.value)}
            />
            <select
              className="input w-full"
              value={avatarId}
              onChange={(e) => {
                setAvatarId(e.target.value);
                const a = avatars.find((x) => x.avatar_id === e.target.value);
                setAvatarType(a?.avatar_type || "avatar");
              }}
            >
              <option value="">— pick avatar —</option>
              {avMatches.slice(0, 200).map((a) => (
                <option key={a.avatar_id} value={a.avatar_id}>
                  {(a.name || a.avatar_name || a.avatar_id) +
                    (a.avatar_type === "talking_photo" ? " (photo)" : "")}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Voice">
            <select
              className="input w-full"
              value={voiceId}
              onChange={(e) => setVoiceId(e.target.value)}
            >
              <option value="">— pick voice —</option>
              {voices.slice(0, 300).map((v) => (
                <option key={v.voice_id} value={v.voice_id}>
                  {v.name || v.voice_id}
                </option>
              ))}
            </select>
          </Field>
          <button
            className="btn-primary w-full"
            onClick={buildPost}
            disabled={!!postStage && postStage !== "Done" && !postJob}
          >
            🐙 Build post
          </button>
          {postStage && (
            <div className="text-[11px] font-mono text-slate-400">
              {postStage}
            </div>
          )}
          {postJob && postJob.status === "done" && (
            <div className="space-y-2">
              <video
                key={postJob.job_id}
                className="w-full rounded bg-black"
                src={api.jobVideoUrl(postJob.job_id)}
                controls
                autoPlay
              />
              <a
                className="btn-primary block text-center text-sm"
                href={api.jobVideoUrl(postJob.job_id)}
                download
              >
                Download post MP4
              </a>
              {caption && (
                <button
                  className="btn-ghost w-full text-xs"
                  onClick={() => copy(caption)}
                >
                  Copy caption for IG / X
                </button>
              )}
            </div>
          )}
          {postJob && postJob.status === "failed" && (
            <div className="text-xs text-red-300">{postJob.error}</div>
          )}
        </div>
      </div>
    </div>
  );
}
