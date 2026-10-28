"""t339 (lot Scenario, B3, 28/10/2026) — changement FONCTIONNEL du Spritelab posé APRÈS L9 : 4 ou 8 directions.

L'onglet Bible choisit 4 ou 8 directions. 8 = 5 dessinées (S, E, N découpées dans la planche ; SE, NE générées) + 3
miroirs (SO, O, NO) cochés par défaut, décochables pour générer (SO, NO) ou découper (O) vraiment la vue. La case
« objet tenu asymétrique » décoche et grise les miroirs et montre le rappel « ne pas miroiter » (l'est est alors
généré lui aussi). La rose des 8 directions et le coût (nombre de générations, $) viennent du devis du serveur
(POST /assets/sprite/from-board/devis, aucune dépense) ; le tir passe par le dialogue maison puis `confirme_cout`.
- directions.js : MIROIRS, ROSE, miroirsEffectifs, corpsDirections, rose, abrev, libelleSource (module pur, banc
  qa/directions.test.mjs) ;
- spritelab.js : majDir (appelé par majBible), devisDir, lancerDirections, dirWire.
La table réversible L9 exige : source du poste == base 7f99c72c + éditions ; d'où cette saisie (comme t183, t186).
index.html n'est jamais réécrit par L9 : ses textes neufs sont traduits par la surcouche (entrées H).
GARDÉ : les noms de directions envoyés au serveur (south, southwest…), valeurs du corps, jamais affichées seules.
"""
from outils import S, H

SL = "spritelab/spritelab.js"
SD = "spritelab/directions.js"

DIRECTIONS_JS = (
    "/* t339 (lot Scenario, B3) — 4 ou 8 directions depuis la planche. Le PLAN (d'où vient chaque direction) et le coût\r\n"
    "   viennent du serveur (POST /assets/sprite/from-board/devis, sprite_directions.plan_huit) : l'écran ne le recalcule\r\n"
    "   pas, il le dessine. Convention : 5 dessinées (S, SE, E, NE, N), 3 en miroir (SO <- SE, O <- E, NO <- NE). */\r\n"
    "export const MIROIRS = { southwest: \"southeast\", west: \"east\", northwest: \"northeast\" };\r\n"
    "/* la rose vue du dessus, nord en haut : 3 × 3, le centre est le personnage */\r\n"
    "export const ROSE = [[\"northwest\", \"north\", \"northeast\"], [\"west\", null, \"east\"], [\"southwest\", \"south\", \"southeast\"]];\r\n"
    "\r\n"
    "/* « objet tenu asymétrique » : AUCUN miroir (le serveur refuse en 400 sinon) — la case l'emporte sur les cases */\r\n"
    "export function miroirsEffectifs(coches, asymetrique) {\r\n"
    "  return asymetrique ? [] : Object.keys(MIROIRS).filter((d) => (coches || []).includes(d));\r\n"
    "}\r\n"
    "\r\n"
    "/* le corps de /assets/sprite/from-board (et de son /devis) ; `confirme` seulement après le dialogue du devis */\r\n"
    "export function corpsDirections(n, coches, asymetrique, o) {\r\n"
    "  const opts = o || {}, b = { directions: n === 8 ? 8 : 4 };\r\n"
    "  if (b.directions === 8) { b.miroirs = miroirsEffectifs(coches, asymetrique); b.objet_asymetrique = !!asymetrique; }\r\n"
    "  if (opts.entity_id) b.entity_id = opts.entity_id;\r\n"
    "  for (const k of [\"cell\", \"trim\", \"pixel\", \"post\"]) if (opts[k]) b[k] = opts[k];\r\n"
    "  if (opts.confirme) b.confirme_cout = true;\r\n"
    "  return b;\r\n"
    "}\r\n"
    "\r\n"
    "/* le plan du devis posé sur la rose : 3 × 3 de {direction, source, de} (null au centre ou si absente) */\r\n"
    "export function rose(plan) {\r\n"
    "  const par = Object.fromEntries((plan || []).map((p) => [p.direction, p]));\r\n"
    "  return ROSE.map((ligne) => ligne.map((d) => (d && par[d]) || null));\r\n"
    "}\r\n"
    "\r\n"
    "const ABREV = { south: () => dzT(\"sprites.t339_dir.s\"), southwest: () => dzT(\"sprites.t339_dir.so\"),\r\n"
    "  west: () => dzT(\"sprites.t339_dir.o\"), northwest: () => dzT(\"sprites.t339_dir.no\"),\r\n"
    "  north: () => dzT(\"sprites.t339_dir.n\"), northeast: () => dzT(\"sprites.t339_dir.ne\"),\r\n"
    "  east: () => dzT(\"sprites.t339_dir.e\"), southeast: () => dzT(\"sprites.t339_dir.se\") };\r\n"
    "export function abrev(direction) { return ABREV[direction] ? ABREV[direction]() : String(direction || \"\"); }\r\n"
    "\r\n"
    "/* ce que dit une case de la rose : découpée (gratuit), générée (payant), miroir de… */\r\n"
    "export function libelleSource(p) {\r\n"
    "  if (!p) return \"\";\r\n"
    "  if (p.source === \"planche\") return dzT(\"sprites.t339_src.planche\");\r\n"
    "  if (p.source === \"generee\") return dzT(\"sprites.t339_src.generee\");\r\n"
    "  return dzT(\"sprites.t339_src.miroir\", { d: abrev(p.de) });\r\n"
    "}\r\n"
    "\r\n"
    "/* les puces de la persona : 12 mots-clés au plus, puis une par couleur de marque */"
)

SPRITELAB_JS = (
    "/* ───────── t339 (lot Scenario, B3) : 4 ou 8 directions depuis la planche ─────────\r\n"
    "   « 4 » découpe la planche (gratuit, inchangé). « 8 » : 5 dessinées (S, E, N découpées ; SE, NE générées) + 3\r\n"
    "   miroirs cochés par défaut (décochés : SO, NO générés, O découpé). « Objet tenu asymétrique » : aucun miroir, et\r\n"
    "   l'est est généré (celui de la planche est le miroir du profil gauche). La rose et le coût viennent du DEVIS du\r\n"
    "   serveur (aucune dépense) ; le tir passe par le dialogue maison puis `confirme_cout` (409 sans lui). */\r\n"
    "let dirN = 4, dirDevis = null, dirSeq = 0;\r\n"
    "const dirMiroirsCoches = () => $$(\"#dirMiroirs input[type=checkbox]\").filter((c) => c.checked).map((c) => c.value);\r\n"
    "const dirAsym = () => !!$(\"#dirAsym\").checked;\r\n"
    "\r\n"
    "function majDir() {\r\n"
    "  const huit = dirN === 8, asym = dirAsym();\r\n"
    "  $$(\"#dirN .seg\").forEach((b) => { const on = +b.dataset.n === dirN; b.classList.toggle(\"on\", on); b.setAttribute(\"aria-pressed\", on ? \"true\" : \"false\"); });\r\n"
    "  $(\"#dirHuit\").classList.toggle(\"hidden\", !huit);\r\n"
    "  $$(\"#dirMiroirs input[type=checkbox]\").forEach((c) => { if (asym) c.checked = false; c.disabled = asym; });\r\n"
    "  $(\"#dirMiroirs\").classList.toggle(\"off\", asym);\r\n"
    "  $(\"#dirAsymRappel\").classList.toggle(\"hidden\", !(huit && asym));\r\n"
    "  $(\"#bibleCut\").innerHTML = dzIcone(\"dz-edit-directions\", { taille: 16 }) + \" \"\r\n"
    "    + esc(huit ? dzT(\"sprites.t339_bt.huit\") : dzT(\"sprites.t339_bt.quatre\"));\r\n"
    "  $(\"#bibleCut\").title = huit ? dzT(\"sprites.t339_bt.huit_t\") : dzT(\"sprites.t339_bt.quatre_t\");\r\n"
    "}\r\n"
    "\r\n"
    "/* le devis du serveur : la rose (d'où vient chaque direction) et le coût AVANT le clic */\r\n"
    "async function devisDir() {\r\n"
    "  await SLD_PRET;\r\n"
    "  const seq = ++dirSeq, el = $(\"#dirCout\");\r\n"
    "  if (dirN !== 8) { dirDevis = null; el.innerHTML = esc(dzT(\"sprites.t339_cout.gratuit4\")); return; }\r\n"
    "  try {\r\n"
    "    const d = await api.send(\"POST\", \"/assets/sprite/from-board/devis\", window.SLD.corpsDirections(8, dirMiroirsCoches(), dirAsym(), {}));\r\n"
    "    if (seq !== dirSeq) return;\r\n"
    "    dirDevis = d;\r\n"
    "    $(\"#dirRose\").innerHTML = window.SLD.rose(d.plan).map((ligne) => ligne.map((p) => p\r\n"
    "      ? `<div class=\"dir-case ${escA(p.source)}\" title=\"${escA(window.SLD.libelleSource(p))}\"><b>${esc(window.SLD.abrev(p.direction))}</b><span>${esc(window.SLD.libelleSource(p))}</span></div>`\r\n"
    "      : `<div class=\"dir-case centre\" aria-hidden=\"true\">${dzIcone(\"dz-nav-bible\", { taille: 16 })}</div>`).join(\"\")).join(\"\");\r\n"
    "    el.innerHTML = d.generations\r\n"
    "      ? `${dzIcone(\"dz-action-cout\", { taille: 16 })} ${esc(dzT(\"sprites.t339_cout.payant\", { n: d.generations, usd: (+d.usd).toFixed(3), modele: d.provider }))}`\r\n"
    "      : esc(dzT(\"sprites.t339_cout.gratuit8\"));\r\n"
    "    if (d.cle_manquante) el.innerHTML += ` <span class=\"dir-cle\">${dzIcone(\"dz-etat-avertissement\", { taille: 16 })} ${esc(dzT(\"sprites.t339_cout.cle\", { cle: d.cle_manquante }))}</span>`;\r\n"
    "  } catch (e) {\r\n"
    "    if (seq === dirSeq) { dirDevis = null; el.textContent = dzT(\"sprites.t339_cout.indispo\", { msg: e.message }); }\r\n"
    "  }\r\n"
    "}\r\n"
    "\r\n"
    "async function lancerDirections() {\r\n"
    "  if (dirN !== 8) return cutFromBible();\r\n"
    "  const e = selEnt();\r\n"
    "  if (!e || busyBible) return;\r\n"
    "  const st = $(\"#bibleStatus\");\r\n"
    "  await devisDir();                              // le devis À JOUR : c'est lui que le dialogue montre\r\n"
    "  const d = dirDevis;\r\n"
    "  if (!d) return setStatus(st, dzT(\"sprites.t339_cout.sans_devis\"), true);\r\n"
    "  if (d.generations) {\r\n"
    "    const ok = window.__dzDialogue && await window.__dzDialogue.confirmer(\r\n"
    "      dzT(\"sprites.t339_conf.msg\", { n: d.generations, usd: (+d.usd).toFixed(3), modele: d.provider }),\r\n"
    "      { ok: dzT(\"sprites.t339_conf.ok\") });\r\n"
    "    if (!ok) return;\r\n"
    "  }\r\n"
    "  busyBible = true; majBible();\r\n"
    "  try {\r\n"
    "    setStatus(st, d.generations ? dzT(\"sprites.t339_st.generation\", { n: d.generations }) : dzT(\"sprites.t339_st.decoupe\"), false, 5);\r\n"
    "    const body = window.SLD.corpsDirections(8, dirMiroirsCoches(), dirAsym(), { entity_id: e.id, cell: cellOpts(),\r\n"
    "      trim: $(\"#trim\").value, pixel: pixelOpts(), post: postOpts(), confirme: d.generations > 0 });\r\n"
    "    const r = await api.send(\"POST\", \"/assets/sprite/from-board\", body);\r\n"
    "    await finirFeuille(r.job_id, st, [dzT(\"sprites.t339_st.faite\"),\r\n"
    "      d.generations ? dzT(\"sprites.t339_st.faite_payant\", { n: d.generations }) : dzT(\"sprites.t339_st.faite_gratuit\")]);\r\n"
    "  } catch (err) {\r\n"
    "    setStatus(st, dzT(\"sprites.t339_st.echec\", { msg: err.message }), true);\r\n"
    "  }\r\n"
    "  busyBible = false; majBible();\r\n"
    "}\r\n"
    "\r\n"
    "function dirWire() {\r\n"
    "  $$(\"#dirN .seg\").forEach((b) => b.onclick = () => { dirN = +b.dataset.n === 8 ? 8 : 4; majDir(); devisDir(); });\r\n"
    "  $$(\"#dirMiroirs input[type=checkbox]\").forEach((c) => c.onchange = () => { majDir(); devisDir(); });\r\n"
    "  $(\"#dirAsym\").onchange = () => { majDir(); devisDir(); };\r\n"
    "  majDir(); devisDir();\r\n"
    "}\r\n"
    "\r\n"
    "function bibleWire() {"
)

ENTREES = [
    S(SD, 77, "/* les puces de la persona : 12 mots-clés au plus, puis une par couleur de marque */", DIRECTIONS_JS,
      {"sprites.t339_dir.s": ("S", "S", "contexte"), "sprites.t339_dir.so": ("SO", "SW", "contexte"), "sprites.t339_dir.o": ("O", "W", "contexte"),
       "sprites.t339_dir.no": ("NO", "NW", "contexte"), "sprites.t339_dir.n": ("N", "N", "contexte"), "sprites.t339_dir.ne": ("NE", "NE", "contexte"),
       "sprites.t339_dir.e": ("E", "E", "contexte"), "sprites.t339_dir.se": ("SE", "SE", "contexte"),
       "sprites.t339_src.planche": ("découpée", "cut", "contexte"),
       "sprites.t339_src.generee": ("générée", "generated"),
       "sprites.t339_src.miroir": ("miroir · {d}", "mirror · {d}")}),
    S(SL, 919, '  $("#bibleCut").disabled = !e || busyBible;',
      '  $("#bibleCut").disabled = !e || busyBible;\r\n  majDir();                                        // t339 : libellé 4 / 8 du bouton', {}),
    S(SL, 1057, "function bibleWire() {", SPRITELAB_JS,
      {"sprites.t339_bt.quatre": ("4 directions (planche)", "4 directions (sheet)"),
       "sprites.t339_bt.huit": ("8 directions (planche)", "8 directions (sheet)"),
       "sprites.t339_bt.quatre_t": ("Découpe la planche en 4 directions et assemble la feuille (local, gratuit)",
                                    "Cuts the sheet into 4 directions and assembles the sprite sheet (local, free)"),
       "sprites.t339_bt.huit_t": ("Assemble 8 directions : découpe la planche, génère les vues manquantes (devis "
                                  "affiché, confirmation demandée), tire les miroirs cochés",
                                  "Assembles 8 directions: cuts the sheet, generates the missing views (quote shown, "
                                  "confirmation asked), draws the ticked mirrors"),
       "sprites.t339_cout.gratuit4": ("gratuit — 4 vues découpées, aucune génération",
                                      "free — 4 cut views, no generation"),
       "sprites.t339_cout.gratuit8": ("gratuit — aucune vue à générer", "free — no view to generate"),
       "sprites.t339_cout.payant": ("{n} génération(s) · ≈ ${usd} ({modele})", "{n} generation(s) · ≈ ${usd} ({modele})"),
       "sprites.t339_cout.cle": ("clé {cle} absente : ajoute-la dans Réglages", "{cle} key missing: add it in Settings"),
       "sprites.t339_cout.indispo": ("devis indisponible : {msg}", "quote unavailable: {msg}"),
       "sprites.t339_cout.sans_devis": ("Devis indisponible : rien n'est lancé.", "Quote unavailable: nothing was started."),
       "sprites.t339_conf.msg": ("Générer {n} vue(s) de direction avec {modele} : ≈ ${usd}. Les autres directions sont "
                                 "découpées dans la planche ou tirées en miroir (gratuit).",
                                 "Generate {n} direction view(s) with {modele}: ≈ ${usd}. The other directions are cut "
                                 "from the sheet or mirrored (free)."),
       "sprites.t339_conf.ok": ("Générer", "Generate"),
       "sprites.t339_st.generation": ("Génération de {n} vue(s) puis assemblage…", "Generating {n} view(s), then assembling…"),
       "sprites.t339_st.decoupe": ("Découpe de la planche et miroirs…", "Cutting the sheet and mirroring…"),
       "sprites.t339_st.faite": ("8 directions depuis la planche", "8 directions from the sheet"),
       "sprites.t339_st.faite_payant": (" — {n} vue(s) générée(s), le reste découpé ou en miroir",
                                        " — {n} view(s) generated, the rest cut or mirrored"),
       "sprites.t339_st.faite_gratuit": (" — gratuit, local", " — free, local"),
       "sprites.t339_st.echec": ("Échec : {msg}", "Failed: {msg}")}),
    S(SL, 1059, '  $("#bibleCut").onclick = cutFromBible;',
      '  $("#bibleCut").onclick = lancerDirections;       // t339 : 4 = cutFromBible, 8 = devis puis tir\r\n  dirWire();', {}),
    # ── index.html (surcouche) ──
    H("sprites.t339_h.directions", "Directions", "Directions"),
    H("sprites.t339_h.n_titre", "Nombre de directions de la feuille", "Number of directions in the sheet"),
    H("sprites.t339_h.quatre_titre", "4 directions découpées dans la planche (gratuit)",
      "4 directions cut from the sheet (free)"),
    H("sprites.t339_h.huit_titre", "8 directions : 5 dessinées + 3 en miroir (les diagonales sont générées, payant)",
      "8 directions: 5 drawn + 3 mirrored (the diagonals are generated, paid)"),
    H("sprites.t339_h.rose", "Rose des 8 directions : d'où vient chaque vue", "8-direction rose: where each view comes from"),
    H("sprites.t339_h.aide8a", "5 directions dessinées : S, E et N sont", "5 drawn directions: S, E and N are"),
    H("sprites.t339_h.aide8b", "dans la planche, SE et NE", "from the sheet, SE and NE are"),
    H("sprites.t339_h.generees", "générées", "generated"),
    H("sprites.t339_h.aide8c", ". Les 3 autres se tirent en miroir — décoche un miroir pour avoir la vraie vue.",
      ". The other 3 are mirrored — untick a mirror to get the real view."),
    H("sprites.t339_h.miroirs", "Miroirs", "Mirrors"),
    H("sprites.t339_h.m_so", "SO, miroir du SE", "SW, mirror of SE"),
    H("sprites.t339_h.m_o", "O, miroir de l'E", "W, mirror of E"),
    H("sprites.t339_h.m_no", "NO, miroir du NE", "NW, mirror of NE"),
    H("sprites.t339_h.m_so_t", "Décoché : le sud-ouest est généré (payant)", "Unticked: south-west is generated (paid)"),
    H("sprites.t339_h.m_o_t", "Décoché : l'ouest est découpé dans la planche (profil gauche, gratuit)",
      "Unticked: west is cut from the sheet (left profile, free)"),
    H("sprites.t339_h.m_no_t", "Décoché : le nord-ouest est généré (payant)", "Unticked: north-west is generated (paid)"),
    H("sprites.t339_h.asym", "Le personnage tient un objet asymétrique (épée, bouclier, sac en bandoulière…)",
      "The character holds an asymmetric object (sword, shield, shoulder bag…)"),
    H("sprites.t339_h.asym_titre", "Coché : aucun miroir — un miroir changerait l'objet de main",
      "Ticked: no mirror — a mirror would switch the object to the other hand"),
    H("sprites.t339_h.rappel_t", "Objet tenu asymétrique : ne pas miroiter.", "Asymmetric held object: do not mirror."),
    H("sprites.t339_h.rappel", "Un miroir changerait l'objet de main : les 3 miroirs et l'est (miroir du profil gauche "
      "sur la planche) sont générés.",
      "A mirror would switch the object to the other hand: the 3 mirrors and east (a mirror of the left profile on "
      "the sheet) are generated."),
]
