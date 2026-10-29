/* t344 (29/10/2026) — ce que MONTRE chaque nœud du graphe Meshy, sans DOM ni three.js (banc qa/graphe_vues.test.mjs).

   Un nœud montre le résultat de SA phase : la tâche Meshy de la série en cours (par son taskId) relue au journal
   persistant (fichiers rapatriés, même origine : on peut les rendre en vignette), à défaut ce que la série tient en
   mémoire ; hors série, la dernière tâche réussie de cette phase au journal. Une série en cours ne montre JAMAIS le
   reliquat d'une autre série : une phase pas encore partie est « en attente ». */
"use strict";

const ETATS = { SUCCEEDED: "pret", IN_PROGRESS: "en_cours", PENDING: "attente", FAILED: "echec", CANCELED: "echec",
  SKIPPED: "saute" };

export function glbDe(fichiers) {
  if (!fichiers) return null;
  if (fichiers.glb) return fichiers.glb;
  const v = Object.values(fichiers).find((u) => /\.glb(\?|$)/i.test(String(u || "")));
  return v || null;
}

/* la tâche du journal qui porte cette phase, ou null */
export function tacheDe(phase, S) {
  const journal = S.persisted || [];
  const ph = S.run && (S.run.phases || []).find((p) => p.id === phase);
  if (S.run) {
    if (!ph || !ph.taskId) return null;
    return journal.find((t) => t.id === ph.taskId) || null;
  }
  return journal.find((t) => t.phase === phase && t.status === "SUCCEEDED") || null;
}

/* {etat, img, glb, texte} d'un nœud ; `etabli` : la vignette de la dernière production de l'Établi */
export function resultatNoeud(n, S, etabli) {
  const c = S.cfg || {};
  if (n.id === "prompt") {
    const t = String(c.prompt || "").trim();
    return { etat: t ? "pret" : "attente", texte: t || null, img: null, glb: null };
  }
  if (n.id === "ref") {
    const img = c.imageUrl || null;
    return { etat: img ? "pret" : "attente", img, glb: null, texte: null };
  }
  if (n.door) return { etat: etabli ? "pret" : "attente", img: etabli || null, glb: null, texte: null };
  const ph = S.run && (S.run.phases || []).find((p) => p.id === n.phase);
  let etat = S.run ? (ETATS[(ph && ph.status) || "PENDING"] || "attente") : "attente";
  /* image-to-3d texture en UNE passe : le nœud « texture » montre la tâche du maillage */
  const phaseLue = n.phase === "texture" && c.source === "image" ? "preview" : n.phase;
  const t = tacheDe(phaseLue, S);
  if (!S.run && t) etat = "pret";
  let img = t ? ((t.local_files && t.local_files.thumbnail) || t.thumbnail_url || null) : null;
  let glb = t ? glbDe(t.local_files) : null;
  if (S.run && etat === "pret" && !glb) {        // la série tient le fichier en mémoire, le journal pas encore
    const o = S.run.outputs || {};
    if (n.phase === "rig") glb = (o.rigged && (o.rigged.rigged_character_glb_url || o.rigged.rigged_model_url)) || null;
    else if (n.phase === "animate") {
      const a = (o.animations || []).filter((x) => x && x.animation_glb_url);
      glb = a.length ? a[a.length - 1].animation_glb_url : null;
    } else glb = (o.modelUrls && o.modelUrls.glb) || null;
    img = img || o.thumbnail || null;
  }
  if (etat !== "pret") { img = null; glb = null; }
  return { etat, img, glb, texte: null };
}

/* un instantané se fait seulement d'un fichier de MÊME origine (rapatrié) : un GLB du CDN du fournisseur serait
   refusé à la lecture du canevas (CORS) — on montre alors l'image d'aperçu du fournisseur */
export function rendable(url) {
  return typeof url === "string" && url.startsWith("/");
}
