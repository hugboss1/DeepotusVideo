/* Directions et prompt — t111 (plan-sprites T9-T11, partie écran). Module PUR : tables, corps de requête, prompt ;
   spritelab.js ne fait que câbler, et `<model-viewer>` capture. Les routes sont celles de #237 :
   POST /assets/sprite/from-board (T9, la planche découpée) et POST /assets/sprite/capture (T10, une vue déposée).
   Banc : qa/directions.test.mjs (les noms des directions y sont lus dans sprite_directions.py). */

/* Un azimut par direction, élévation fixe. Le modèle glTF regarde +Z ; model-viewer pose la caméra en
   x = r·sinφ·sinθ, z = r·sinφ·cosθ : θ = 0° fait face au modèle (« sud »), θ = 90° le montre de profil, nez à
   GAUCHE du cadre (« ouest », le profil « left » de la planche). L'ordre est celui de sprite_directions.HUIT —
   sinon les tags de la feuille mentiraient. */
export const ORBITES = [["south", 0], ["southwest", 45], ["west", 90], ["northwest", 135],
                        ["north", 180], ["northeast", 225], ["east", 270], ["southeast", 315]];
export const ELEVATION = 78;
export const orbite = (theta) => `${theta}deg ${ELEVATION}deg auto`;

/* Les kinds dont la planche est composée en colonnes face / profils / dos (board_service : « compose: character ») :
   le backend refuse de découper les autres, la liste ne les propose donc pas. */
export const KINDS_PLANCHE = ["character"];

export function entitesDecoupables(entites, q) {
  const f = String(q || "").trim().toLowerCase();
  return (entites || []).filter((e) => e && e.ref_image && KINDS_PLANCHE.includes(e.kind)
    && (!f || String(e.name || "").toLowerCase().includes(f)));
}

/* T0 + T11 : la source a deux formes (un job vidéo, ou des images de la Library). UNE fonction les rend, appelée par
   l'extraction ET la génération — deux copies dériveraient (et la source « images » partait en `job_id: undefined`). */
export function sourceBody(source) {
  if (!source) return null;
  return source.kind === "images"
    ? { kind: "images", filenames: source.filenames.slice() }
    : { kind: source.kind, job_id: source.job_id };
}

export function hex8(alea = Math.random) {
  let s = "";
  for (let i = 0; i < 8; i++) s += "0123456789abcdef"[Math.min(15, Math.floor(alea() * 16))];
  return s;
}

/* Les 8 vues déposées -> le corps de /assets/sprite. La MESURE de l'alpha (réponse de /capture) décide du détourage :
   rendu déjà transparent, on n'y touche pas ; une seule vue opaque, la clé chroma locale (gratuite) passe. */
export function corpsOrbites(noms, sansAlpha, o) {
  if (!Array.isArray(noms) || noms.length !== ORBITES.length)
    throw new Error(__dzT9("sprites.sp2_dir.vues", "{n} vues attendues, {recu} reçues", { n: ORBITES.length, recu: Array.isArray(noms) ? noms.length : 0 }));
  const opts = o || {};
  const b = {
    source: { kind: "images", filenames: noms.slice() },
    remove_bg: (sansAlpha || []).length ? "chroma" : "none",
    max_frames: ORBITES.length,           // le défaut serveur échantillonnerait — 8 vues, 8 cases
    columns: 4,
    anim: { tags: ORBITES.map(([n], i) => ({ name: n, from: i, to: i, direction: "forward" })) },
    title: "Sprites · 8 directions · " + (opts.titre || ""),
  };
  if (opts.cell) b.cell = opts.cell;
  if (opts.pixel) b.pixel = opts.pixel;
  if (opts.post) b.post = opts.post;
  return b;
}

/* T11 — prompt -> image -> pipeline pixel local. Le style est porté par des DESCRIPTEURS (palette, grille, contour)
   et par les mots-clés de la persona, jamais par un nom d'artiste : les générateurs refusent ou pastichent, et
   aucun `style` n'est passé à /images/generate, donc c'est l'écran qui tient la règle (le banc la vérifie). */
export const PIXEL_SUFFIX = "pixel art sprite, chunky readable pixels, limited flat palette, crisp 1px dark outline, "
  + "no anti-aliasing, plain solid green background, full body in frame, centered, no text, no watermark";

export function promptFinal(sujet, puces) {
  const s = String(sujet || "").trim();
  if (!s) return "";
  return [s, ...(puces || []), PIXEL_SUFFIX].filter(Boolean).join(", ");
}

export function corpsPrompt(sujet, puces, n, size) {
  return { prompt: promptFinal(sujet, puces), n: Math.max(1, Math.min(4, parseInt(n, 10) || 1)), size,
           source: "sprites" };
}

/* les puces de la persona : 12 mots-clés au plus, puis une par couleur de marque */
export function puces(persona) {
  const p = persona || {};
  return (p.vibe_keywords || []).slice(0, 12).map((m) => ({ v: String(m), libelle: String(m), couleur: false }))
    .concat(Object.values(p.brand_colors || {}).map((c) => ({ v: "palette accent " + c, libelle: String(c), couleur: true })));
}
// t149 (traduction L9) : dzT dans la page, le français sous node (bancs)
function __dzT9(k, fr, v) { return typeof globalThis.dzT === "function" ? globalThis.dzT(k, v) : String(fr).replace(/\{(\w+)\}/g, (m, n) => (v && v[n] != null ? String(v[n]) : m)); }
