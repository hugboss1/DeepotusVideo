"""t340 (lot Scenario, B1 + B2, 29/10/2026) — changement FONCTIONNEL du Spritelab posé APRÈS L9 : grille pixel
verrouillée (« sprite approuvé ») et préréglage « Boucle ».

B1 (Pixel Lock) : la grille (`target_px`) et la palette sont imposées par l'OUTIL, jamais par le modèle. « Approuver ce
sprite » (sortie, à droite) écrit l'approbation côté serveur (POST /assets/sprite/{job}/approuver) ; l'état verrouillé
se lit dans « Réglages de la planche › Pixel-art » (grille N px + palette X), les champs y sont figés, et chaque
génération envoie `pixel_verrou` : le serveur impose sa règle. La preuve de la grille (blocs unis, couleurs dans la
palette) vient du manifeste (`pixel_verif`).
B2 (« Boucle ») : onglet Image, préréglage Libre / Boucle. La pose choisie est la 1re ET la dernière image de la vidéo
(POST /assets/sprite/boucle, devis affiché AVANT, dialogue, `confirme_cout`), puis 1 image sur 2 ou 3 à l'extraction
(la dernière, identique à la première, retirée), re-pixelisées sur la grille verrouillée — feuille + GIF.
- spritelab.js : pixVerrou, animMode, uneSur, majVerrou, majAppro, approuverSprite, deverrouiller, verifierVerrou,
  majAnimMode, devisAnim, animerBoucle, boucleWire ; branchés dans animer, extract, generate, pixelOpts, showResult,
  les préférences et wire.
La table réversible L9 exige : source du poste == base 7f99c72c + éditions ; d'où cette saisie (comme t339).
index.html n'est jamais réécrit par L9 : ses textes neufs sont traduits par la surcouche (entrées H).
GARDÉ : les valeurs envoyées au serveur (`une_sur`, `pixel_verrou`, « libre » / « boucle » comparés).
"""
from outils import S, H

SL = "spritelab/spritelab.js"

BLOC = (
    "/* ───────── t340 (lot Scenario, B1 + B2) : sprite approuvé (Pixel Lock) et préréglage « Boucle » ─────────\r\n"
    "   Le VERROU vient du serveur (POST /assets/sprite/{job}/approuver -> approbation.json) : grille target_px et\r\n"
    "   palette figées ; chaque génération envoie `pixel_verrou` et le serveur impose sa règle, quoi que disent les\r\n"
    "   champs. La BOUCLE : la pose choisie est la 1re ET la dernière image de la vidéo (devis affiché, dialogue,\r\n"
    "   confirme_cout), puis 1 image sur 2 ou 3 à l'extraction, la dernière (= la 1re) retirée. */\r\n"
    "let pixVerrou = null, animMode = \"libre\", uneSur = 2, animDevis = null, animSeq = 0, busyAppro = false;\r\n"
    "const boucleCorps = () => (source && source.boucle ? { boucle: { une_sur: source.boucle.une_sur } } : {});\r\n"
    "\r\n"
    "function nomPaletteVerrou(v) {\r\n"
    "  const P = v && v.palette && window.DZ_PALETTES && window.DZ_PALETTES.palette_de(v.palette);\r\n"
    "  return P ? P.nom : dzT(\"sprites.t340_v.palette_sprite\");\r\n"
    "}\r\n"
    "\r\n"
    "/* l'état verrouillé, lisible dans Réglages de la planche › Pixel-art : les champs sont figés sur l'approbation */\r\n"
    "function majVerrou() {\r\n"
    "  const on = !!pixVerrou;\r\n"
    "  $(\"#pixVerrou\").classList.toggle(\"hidden\", !on);\r\n"
    "  if (on) {\r\n"
    "    $(\"#pixelOn\").checked = true;\r\n"
    "    $(\"#pixTarget\").value = pixVerrou.target_px;\r\n"
    "    $(\"#pixDither\").value = pixVerrou.dither || \"none\";\r\n"
    "    $(\"#pixVerrouTxt\").textContent = dzT(\"sprites.t340_v.etat\", { px: pixVerrou.target_px,\r\n"
    "      palette: nomPaletteVerrou(pixVerrou), n: (pixVerrou.palette_hex || []).length, job: pixVerrou.job });\r\n"
    "    $(\"#pixVerrouPal\").innerHTML = (pixVerrou.palette_hex || []).slice(0, 64)\r\n"
    "      .map((h) => `<i style=\"background:${escA(h)}\" title=\"${escA(h)}\"></i>`).join(\"\");\r\n"
    "  }\r\n"
    "  for (const id of [\"pixelOn\", \"pixTarget\", \"pixPalette\", \"pixColors\", \"pixDither\"]) $(\"#\" + id).disabled = on;\r\n"
    "  $(\".pixelset\").classList.toggle(\"verrou\", on);\r\n"
    "  syncPixelSet();\r\n"
    "  majAppro();\r\n"
    "}\r\n"
    "\r\n"
    "/* sortie : « Approuver ce sprite » et la PREUVE de la grille (manifeste pixel_verif), seulement en pixel-art */\r\n"
    "function majAppro() {\r\n"
    "  const box = $(\"#appro\"), m = sheet && sheet.manifest;\r\n"
    "  if (!box) return;\r\n"
    "  if (!m || !m.pixel || !m.grid) { box.classList.add(\"hidden\"); return; }\r\n"
    "  box.classList.remove(\"hidden\");\r\n"
    "  const v = m.pixel_verif, el = $(\"#approVerif\");\r\n"
    "  if (v) {\r\n"
    "    el.className = \"appro-verif \" + (v.ok ? \"ok\" : \"ko\");\r\n"
    "    const pal = v.palette != null ? dzT(\"sprites.t340_ap.dans_pal\", { p: v.palette }) : dzT(\"sprites.t340_ap.pal_adapt\");\r\n"
    "    el.innerHTML = dzIcone(v.ok ? \"dz-etat-succes\" : \"dz-etat-avertissement\", { taille: 16 }) + \" \" + esc(v.ok\r\n"
    "      ? dzT(\"sprites.t340_ap.verif_ok\", { bloc: v.bloc, n: v.frames, pal })\r\n"
    "      : dzT(\"sprites.t340_ap.verif_ko\", { blocs: v.blocs_non_unis, hors: v.hors_palette, alpha: v.alpha_partiel }));\r\n"
    "  } else { el.className = \"appro-verif\"; el.textContent = \"\"; }\r\n"
    "  const approuve = !!(pixVerrou && pixVerrou.job === sheet.short);\r\n"
    "  $(\"#approBtn\").disabled = approuve || busyAppro;\r\n"
    "  $(\"#approBtn\").innerHTML = dzIcone(approuve ? \"dz-etat-verrouille\" : \"dz-action-valider\", { taille: 16 }) + \" \"\r\n"
    "    + esc(approuve ? dzT(\"sprites.t340_ap.approuve\") : dzT(\"sprites.t340_ap.approuver\"));\r\n"
    "  $(\"#approEtat\").textContent = approuve ? dzT(\"sprites.t340_ap.etat_on\")\r\n"
    "    : (pixVerrou ? dzT(\"sprites.t340_ap.remplace\", { job: pixVerrou.job }) : dzT(\"sprites.t340_ap.etat_off\"));\r\n"
    "}\r\n"
    "\r\n"
    "async function approuverSprite() {\r\n"
    "  if (!sheet || busyAppro) return;\r\n"
    "  busyAppro = true; majAppro();\r\n"
    "  try {\r\n"
    "    pixVerrou = await api.send(\"POST\", `/assets/sprite/${sheet.short}/approuver`);\r\n"
    "    savePrefs();\r\n"
    "    toastOk(dzT(\"sprites.t340_ap.toast\", { px: pixVerrou.target_px, n: pixVerrou.palette_hex.length }));\r\n"
    "  } catch (e) {\r\n"
    "    toast(dzT(\"sprites.t340_ap.echec\", { msg: e.message }), true);\r\n"
    "  }\r\n"
    "  busyAppro = false; majVerrou(); devisAnim();\r\n"
    "}\r\n"
    "function deverrouiller() {\r\n"
    "  pixVerrou = null; majVerrou(); savePrefs(); devisAnim();\r\n"
    "  toast(dzT(\"sprites.t340_v.leve\"));\r\n"
    "}\r\n"
    "/* au chargement : le verrou des préférences est relu au serveur (un sprite supprimé lève le verrou) */\r\n"
    "async function verifierVerrou() {\r\n"
    "  if (pixVerrou && pixVerrou.job) {\r\n"
    "    try { pixVerrou = await api.get(`/assets/sprite/${pixVerrou.job}/approbation`); } catch (e) { pixVerrou = null; }\r\n"
    "  } else pixVerrou = null;\r\n"
    "  majVerrou();\r\n"
    "}\r\n"
    "\r\n"
    "function majAnimMode() {\r\n"
    "  const seg = (sel, on) => $$(sel).forEach((b) => { const x = on(b); b.classList.toggle(\"on\", x); b.setAttribute(\"aria-pressed\", x ? \"true\" : \"false\"); });\r\n"
    "  seg(\"#animMode .seg\", (b) => b.dataset.mode === animMode);\r\n"
    "  seg(\"#uneSur .seg\", (b) => +b.dataset.n === uneSur);\r\n"
    "  const boucle = animMode === \"boucle\";\r\n"
    "  $(\"#boucleOpts\").classList.toggle(\"hidden\", !boucle);\r\n"
    "  $(\"#animerBtn\").innerHTML = dzIcone(\"dz-media-generer-video\", { taille: 16 }) + \" \"\r\n"
    "    + esc(boucle ? dzT(\"sprites.t340_b.bt_boucle\") : dzT(\"sprites.t340_b.bt_libre\"));\r\n"
    "  $(\"#animerBtn\").title = boucle ? dzT(\"sprites.t340_b.bt_boucle_t\") : dzT(\"sprites.t340_b.bt_libre_t\");\r\n"
    "  $(\"#boucleVerrou\").textContent = pixVerrou ? dzT(\"sprites.t340_b.verrou_on\", { px: pixVerrou.target_px,\r\n"
    "    palette: nomPaletteVerrou(pixVerrou) }) : dzT(\"sprites.t340_b.verrou_off\");\r\n"
    "}\r\n"
    "\r\n"
    "/* le coût de la vidéo AVANT le clic (devis du serveur, aucune dépense) — même tarif en Libre et en Boucle */\r\n"
    "async function devisAnim() {\r\n"
    "  const el = $(\"#animCout\"), seq = ++animSeq;\r\n"
    "  if (!el) return;\r\n"
    "  majAnimMode();\r\n"
    "  if (!selImage) { animDevis = null; el.textContent = dzT(\"sprites.t340_c.choisis\"); return; }\r\n"
    "  try {\r\n"
    "    const d = await api.send(\"POST\", \"/assets/sprite/boucle/devis\", { image_filename: selImage,\r\n"
    "      duration_s: parseInt($(\"#animDur\").value, 10) || 5, aspect_ratio: $(\"#animRatio\").value, une_sur: uneSur,\r\n"
    "      ...(pixVerrou ? { pixel_verrou: pixVerrou.job } : {}) });\r\n"
    "    if (seq !== animSeq) return;\r\n"
    "    animDevis = d;\r\n"
    "    el.innerHTML = `${dzIcone(\"dz-action-cout\", { taille: 16 })} ${esc(dzT(\"sprites.t340_c.video\", { s: d.secondes, usd: (+d.usd).toFixed(3), modele: d.label }))}`;\r\n"
    "    if (d.cle_manquante) el.innerHTML += ` <span class=\"dir-cle\">${dzIcone(\"dz-etat-avertissement\", { taille: 16 })} ${esc(dzT(\"sprites.t340_c.cle\", { cle: d.cle_manquante }))}</span>`;\r\n"
    "  } catch (e) {\r\n"
    "    if (seq === animSeq) { animDevis = null; el.textContent = dzT(\"sprites.t340_c.indispo\", { msg: e.message }); }\r\n"
    "  }\r\n"
    "}\r\n"
    "\r\n"
    "async function animerBoucle() {\r\n"
    "  if (busyAnim) return;\r\n"
    "  if (!selImage) return toast(dzT(\"sprites.t340_b.choisis_pose\"), true);\r\n"
    "  const action = ($(\"#animPrompt\").value || \"\").trim();\r\n"
    "  if (!action) return toast(dzT(\"sprites.t340_b.decris\"), true);\r\n"
    "  const st = $(\"#animStatus\");\r\n"
    "  await devisAnim();                              // le devis À JOUR : c'est lui que le dialogue montre\r\n"
    "  const d = animDevis;\r\n"
    "  if (!d) return setStatus(st, dzT(\"sprites.t340_c.sans_devis\"), true);\r\n"
    "  const ok = window.__dzDialogue && await window.__dzDialogue.confirmer(\r\n"
    "    dzT(\"sprites.t340_conf.msg\", { s: d.secondes, modele: d.label, usd: (+d.usd).toFixed(3), n: uneSur }),\r\n"
    "    { ok: dzT(\"sprites.t340_conf.ok\") });\r\n"
    "  if (!ok) return;\r\n"
    "  busyAnim = true; $(\"#animerBtn\").disabled = true;\r\n"
    "  try {\r\n"
    "    setStatus(st, dzT(\"sprites.t340_b.lancement\"), false, 3);\r\n"
    "    const r = await api.send(\"POST\", \"/assets/sprite/boucle\", { image_filename: selImage, prompt: action,\r\n"
    "      duration_s: d.duration_s, aspect_ratio: d.aspect_ratio, une_sur: uneSur, confirme_cout: true,\r\n"
    "      ...(pixVerrou ? { pixel_verrou: pixVerrou.job } : {}) });\r\n"
    "    const j = await pollJob(r.job_id, (jj) => setStatus(st,\r\n"
    "      dzT(\"sprites.t340_b.etape\", { etape: jj.current_step || jj.status }), false, jj.progress || 5));\r\n"
    "    if (j.status !== \"done\") throw new Error(j.error || dzT(\"sprites.t340_b.echouee\"));\r\n"
    "    clearStatus(st);\r\n"
    "    // fond vert uni demandé au modèle : la clé chroma locale suffit (gratuite)\r\n"
    "    if (detourPayant()) { $(\"#removeBg\").value = \"local-chroma\"; detourMaj(); updateCost(); }\r\n"
    "    savePrefs();\r\n"
    "    toast(dzT(\"sprites.t340_b.prete\", { n: uneSur }));\r\n"
    "    setSource({ kind: \"job\", job_id: j.job_id, boucle: { une_sur: uneSur },\r\n"
    "      label: dzT(\"sprites.t340_b.label\", { t: j.title || j.job_id.slice(0, 8), n: uneSur }) });\r\n"
    "  } catch (e) {\r\n"
    "    setStatus(st, dzT(\"sprites.t340_b.echec\", { msg: e.message }), true);\r\n"
    "  }\r\n"
    "  busyAnim = false; $(\"#animerBtn\").disabled = false;\r\n"
    "}\r\n"
    "\r\n"
    "function boucleWire() {\r\n"
    "  $$(\"#animMode .seg\").forEach((b) => b.onclick = () => { animMode = b.dataset.mode === \"boucle\" ? \"boucle\" : \"libre\"; savePrefs(); devisAnim(); });\r\n"
    "  $$(\"#uneSur .seg\").forEach((b) => b.onclick = () => { uneSur = +b.dataset.n === 3 ? 3 : 2; savePrefs(); devisAnim(); });\r\n"
    "  for (const id of [\"animDur\", \"animRatio\"]) $(\"#\" + id).addEventListener(\"change\", devisAnim);\r\n"
    "  $(\"#approBtn\").onclick = approuverSprite;\r\n"
    "  $(\"#pixDeverrou\").onclick = deverrouiller;\r\n"
    "  document.addEventListener(\"dz-palettes\", () => majVerrou());   // le nom de la palette arrive avec le module\r\n"
    "  majAnimMode();\r\n"
    "}\r\n"
    "\r\n"
    "async function animer() {\r\n"
    "  if (animMode === \"boucle\") return animerBoucle();   // t340 : préréglage « Boucle »"
)

DICO = {
    "sprites.t340_v.palette_sprite": ("celle du sprite", "the sprite's own"),
    "sprites.t340_v.etat": ("Verrouillé sur le sprite {job} : grille {px} px · palette {palette} ({n} couleurs)",
                            "Locked to sprite {job}: {px} px grid · {palette} palette ({n} colours)"),
    "sprites.t340_v.leve": ("Verrou levé : les réglages Pixel-art redeviennent libres.",
                            "Lock lifted: the Pixel art settings are free again."),
    "sprites.t340_ap.dans_pal": ("toutes les couleurs dans la palette ({p})", "every colour in the palette ({p})"),
    "sprites.t340_ap.pal_adapt": ("palette adaptative", "adaptive palette"),
    "sprites.t340_ap.verif_ok": ("Grille vérifiée : blocs de {bloc} px tous unis sur {n} image(s), {pal}",
                                 "Grid checked: {bloc} px blocks all solid across {n} frame(s), {pal}"),
    "sprites.t340_ap.verif_ko": ("Grille à revoir : {blocs} bloc(s) non uni(s), {hors} couleur(s) hors palette, {alpha} "
                                 "pixel(s) semi-transparent(s) — une ombre ou un contour du post-traitement en ajoute",
                                 "Grid to review: {blocs} non-solid block(s), {hors} colour(s) off the palette, {alpha} "
                                 "semi-transparent pixel(s) — a post-processing shadow or outline adds them"),
    "sprites.t340_ap.approuver": ("Approuver ce sprite", "Approve this sprite"),
    "sprites.t340_ap.approuve": ("Sprite approuvé", "Sprite approved"),
    "sprites.t340_ap.etat_off": ("Fige sa grille et sa palette : les animations suivantes les reprennent.",
                                 "Freezes its grid and palette: the next animations reuse them."),
    "sprites.t340_ap.etat_on": ("Sa grille et sa palette sont imposées aux animations suivantes.",
                                "Its grid and palette are enforced on the next animations."),
    "sprites.t340_ap.remplace": ("Remplacera le verrou actuel (sprite {job}).", "Will replace the current lock (sprite {job})."),
    "sprites.t340_ap.toast": ("Sprite approuvé : grille {px} px et {n} couleurs verrouillées.",
                              "Sprite approved: {px} px grid and {n} colours locked."),
    "sprites.t340_ap.echec": ("Approbation refusée : {msg}", "Approval refused: {msg}"),
    "sprites.t340_b.bt_libre": ("Animer (Seedance, fond uni)", "Animate (Seedance, plain background)"),
    "sprites.t340_b.bt_libre_t": ("Lance une génération Seedance (coût selon les Réglages) puis enchaîne sur "
                                  "l'extraction des frames",
                                  "Starts a Seedance generation (cost per Settings), then goes on to extract the frames"),
    "sprites.t340_b.bt_boucle": ("Animer en boucle (Seedance)", "Animate as a loop (Seedance)"),
    "sprites.t340_b.bt_boucle_t": ("Génère une vidéo dont la 1re et la dernière image sont la pose choisie (devis "
                                   "affiché, confirmation demandée), puis en extrait la boucle",
                                   "Generates a video whose first and last frames are the chosen pose (quote shown, "
                                   "confirmation asked), then extracts the loop from it"),
    "sprites.t340_b.verrou_on": ("Re-pixelisée sur le sprite approuvé : grille {px} px · palette {palette}.",
                                 "Re-pixelated on the approved sprite: {px} px grid · {palette} palette."),
    "sprites.t340_b.verrou_off": ("Aucun sprite approuvé : la grille et la palette sont celles des réglages Pixel-art.",
                                  "No approved sprite: the grid and palette come from the Pixel art settings."),
    "sprites.t340_b.choisis_pose": ("Choisis d'abord la pose de départ dans la Library.",
                                    "Pick the starting pose in the Library first."),
    "sprites.t340_b.decris": ("Décris le mouvement à boucler (ex : walks in place).",
                              "Describe the motion to loop (e.g. walks in place)."),
    "sprites.t340_b.lancement": ("Lancement de la boucle…", "Starting the loop…"),
    "sprites.t340_b.etape": ("Boucle : {etape}…", "Loop: {etape}…"),
    "sprites.t340_b.echouee": ("génération de la boucle échouée", "loop generation failed"),
    "sprites.t340_b.prete": ("Boucle prête — extraction d'une image sur {n}…", "Loop ready — extracting one frame in {n}…"),
    "sprites.t340_b.label": ("boucle 1/{n} · {t}", "loop 1/{n} · {t}"),
    "sprites.t340_b.echec": ("Échec : {msg}", "Failed: {msg}"),
    "sprites.t340_c.choisis": ("choisis une pose pour voir le coût", "pick a pose to see the cost"),
    "sprites.t340_c.video": ("vidéo {s} s · ≈ ${usd} ({modele})", "{s} s video · ≈ ${usd} ({modele})"),
    "sprites.t340_c.cle": ("clé {cle} absente : ajoute-la dans Réglages", "{cle} key missing: add it in Settings"),
    "sprites.t340_c.indispo": ("devis indisponible : {msg}", "quote unavailable: {msg}"),
    "sprites.t340_c.sans_devis": ("Devis indisponible : rien n'est lancé.", "Quote unavailable: nothing was started."),
    "sprites.t340_conf.msg": ("Générer la boucle avec {modele} : une vidéo de {s} s, la pose en 1re et en dernière "
                              "image, ≈ ${usd}. Puis une image sur {n} est gardée et re-pixelisée (local, gratuit).",
                              "Generate the loop with {modele}: a {s} s video, the pose as first and last frame, "
                              "≈ ${usd}. Then one frame in {n} is kept and re-pixelated (local, free)."),
    "sprites.t340_conf.ok": ("Générer", "Generate"),
}

ENTREES = [
    S(SL, 153, "async function animer() {", BLOC, DICO),
    S(SL, 91, "  p.tagRows = JSON.stringify(tagRows);",
      "  p.tagRows = JSON.stringify(tagRows);\r\n"
      "  p.pixVerrou = pixVerrou ? JSON.stringify(pixVerrou) : \"\";   // t340 : le verrou (relu au serveur au chargement)\r\n"
      "  p.animMode = animMode; p.uneSur = uneSur;", {}),
    S(SL, 99, "  if (p.tagRows) { try {",
      "  if (p.pixVerrou) { try { pixVerrou = JSON.parse(p.pixVerrou); } catch (e) { pixVerrou = null; } }   // t340\r\n"
      "  if (p.animMode) animMode = p.animMode === \"boucle\" ? \"boucle\" : \"libre\";\r\n"
      "  if (p.uneSur) uneSur = +p.uneSur === 3 ? 3 : 2;\r\n"
      "  if (p.tagRows) { try {", {}),
    S(SL, 148, "    selImage = el.dataset.fn;",
      "    selImage = el.dataset.fn; devisAnim();      // t340 : le coût suit la pose", {}),
    S(SL, 263, "      remove_bg: \"none\", extract_only: true,",
      "      remove_bg: \"none\", extract_only: true, ...boucleCorps(),   // t340 : même échantillonnage que le tir", {}),
    S(SL, 329, "function pixelOpts() {\r\n  if (!$(\"#pixelOn\").checked) return undefined;",
      "function pixelOpts() {\r\n"
      "  // t340 : un sprite approuvé impose SA grille et SA palette (le serveur les reprend aussi par `pixel_verrou`)\r\n"
      "  if (pixVerrou) return { target_px: pixVerrou.target_px, dither: pixVerrou.dither || \"none\", palette_hex: pixVerrou.palette_hex.slice() };\r\n"
      "  if (!$(\"#pixelOn\").checked) return undefined;", {}),
    S(SL, 397, "    const px = pixelOpts(); if (px) body.pixel = px;",
      "    const px = pixelOpts(); if (px) body.pixel = px;\r\n"
      "    if (pixVerrou) body.pixel_verrou = pixVerrou.job;   // t340 : le serveur impose la grille et la palette approuvées\r\n"
      "    Object.assign(body, boucleCorps());                // t340 : 1 image sur N, boucle fermée (comme la sonde)", {}),
    S(SL, 451, "  $(\"#sheetImg\").src = ",
      "  majAppro();                           // t340 : « Approuver ce sprite » et la preuve de la grille\r\n"
      "  $(\"#sheetImg\").src = ", {}),
    S(SL, 1154, "function syncPixelSet() {",
      "function syncPixelSet() {\r\n  if (pixVerrou) $(\"#pixelOn\").checked = true;   // t340 : verrouillé = pixel-art", {}),
    S(SL, 1180, "  $(\"#animerBtn\").onclick = animer;",
      "  $(\"#animerBtn\").onclick = animer;\r\n  boucleWire();                          // t340", {}),
    S(SL, 1414, "  loadImages(); loadRenders();",
      "  verifierVerrou(); devisAnim();         // t340 : verrou relu au serveur, coût de l'animation\r\n"
      "  loadImages(); loadRenders();", {}),
    # ── index.html (surcouche) ──
    H("sprites.t340_h.prereglage", "Préréglage", "Preset"),
    H("sprites.t340_h.mode_aria", "Préréglage d'animation", "Animation preset"),
    H("sprites.t340_h.libre", "Sans boucle", "No loop"),
    H("sprites.t340_h.libre_t", "Sans boucle : la vidéo part de l'image choisie et va où le mouvement la mène",
      "No loop: the video starts from the chosen image and goes wherever the motion leads"),
    H("sprites.t340_h.boucle", "Boucle", "Loop"),
    H("sprites.t340_h.boucle_t", "Boucle : la même pose en première et en dernière image, une image sur 2 ou 3 gardée, "
      "re-pixelisée sur la grille verrouillée",
      "Loop: the same pose as first and last frame, one frame in 2 or 3 kept, re-pixelated on the locked grid"),
    H("sprites.t340_h.boucle_aide1", "La pose choisie est la", "The chosen pose is the"),
    H("sprites.t340_h.boucle_aide2", "1re et la dernière", "first and the last"),
    H("sprites.t340_h.boucle_aide3", "image de la vidéo. À l'extraction, la dernière (identique à la première) est "
      "retirée pour que la boucle ne bégaie pas, puis une image sur 2 ou 3 est gardée. Feuille + GIF.",
      "frame of the video. On extraction, the last one (identical to the first) is dropped so the loop does not "
      "stutter, then one frame in 2 or 3 is kept. Sheet + GIF."),
    H("sprites.t340_h.une_sur", "Garder une image sur", "Keep one frame in"),
    H("sprites.t340_h.une_sur_aria", "Garder une image sur N", "Keep one frame in N"),
    H("sprites.t340_h.une_sur2_t", "Une image sur deux (cycle plus fluide)", "One frame in two (smoother cycle)"),
    H("sprites.t340_h.une_sur3_t", "Une image sur trois (moins d'images, feuille plus légère)",
      "One frame in three (fewer frames, lighter sheet)"),
    H("sprites.t340_h.verrou_titre", "Grille et palette verrouillées", "Grid and palette locked"),
    H("sprites.t340_h.deverrouiller", "Déverrouiller", "Unlock"),
    H("sprites.t340_h.deverrouiller_t", "Lève le verrou : les champs Pixel-art redeviennent libres (le sprite reste "
      "approuvé, on peut le reprendre)",
      "Lifts the lock: the Pixel art fields are free again (the sprite stays approved and can be picked again)"),
    H("sprites.t340_h.verrou_aide", "Imposées par le serveur à chaque génération : les champs ci-dessus sont figés.",
      "Enforced by the server on every generation: the fields above are frozen."),
    H("sprites.t340_h.palette_aria", "Couleurs de la palette verrouillée", "Colours of the locked palette"),
    H("sprites.t340_h.appro_titre", "Pixel Lock", "Pixel Lock", contexte=True),
    H("sprites.t340_h.approuver_t", "Fige la grille et la palette de ce sprite : les animations suivantes les "
      "reprennent, imposées par le serveur (local, gratuit)",
      "Freezes this sprite's grid and palette: the next animations reuse them, enforced by the server (local, free)"),
]
