"""t333 + t338 (lot Scenario, A3 + A8, 29/10/2026) — changement FONCTIONNEL du Plateau 3D posé APRÈS L9 : previs
COLORÉE ET NOMMÉE, faisceaux exclus des captures, et COUVERTURE du plan (plan large, contre-champ, gros plan).

A3 : chaque instance prend la couleur de son entité de la bible ou de sa MATIÈRE (champ « ce que c'est » de la fiche) ;
la palette et la légende viennent du serveur (POST /api/scenes3d/{id}/palette — couleur stable, entités d'abord, voir
backend/app/services/previs_palette.py). Les FAISCEAUX (rôle « faisceau », ou un nom qui le dit) sont translucides à
l'écran et CACHÉS à chaque capture : un faisceau envoyé à un modèle devient un solide. La légende (« cylindres verts =
cyprès ») s'affiche à droite (section « Previs colorée ») et part dans la recette des captures et les prompts du plan.
A8 : « Générer la couverture » (section « Couverture ») : depuis la caméra du plan (son 1er keyframe, sinon la caméra
courante), plan large, contre-champ (règle des 180°, interlocuteur au choix ou d'office), gros plan (cible au choix) —
calculés par le serveur (POST …/couverture, scene3d_couverture.py), rangés dans la scène, chacun Voir / Capturer /
Nouveau plan (un plan neuf après le plan lié, sa scène posée sur la caméra) / Image du plan (la capture devient la
borne de début du plan lié, par vers-plan, avant / après puis confirmation armée). Aucun dialogue natif.
- plateau.js : import inchangé ; objetDe (matériau), listeInstances (pastille, faisceau exclu), fiche (rôle faisceau,
  matière), champ (matière), sauver (palette rafraîchie), rendreA (faisceaux cachés), capturer (scène affichée),
  ouvrir (couverture rangée) ; bloc neuf avant ouvrir() : couleurPrevis, materiauPrevis, basculerFaisceaux, recolorer,
  previsBientot, rafraichirPrevis, majLegende, champMatiere, etiquettePrevis, majSelectsCouverture, nomCamera,
  genererCouverture, majCouverture, actionCamera, previsOuvrir.
La table réversible L9 exige : source du poste == base 7f99c72c + éditions ; d'où cette saisie (comme t339, t340).
index.html n'est jamais réécrit par L9 : ses textes neufs sont traduits par la surcouche (entrées H).
GARDÉ : les valeurs envoyées au serveur (`partenaire_id`, `gros_plan_id`, `__auto` / `__aucun` comparés), les types
de plan renvoyés par le serveur (wide, close-up…), la légende anglaise et la phrase de prompt (contenu pour les
modèles, rendu tel quel), les noms d'instances saisis.
"""
from outils import S, H

PJ = "plateau/plateau.js"

BLOC = (
    "/* ───────── t333 + t338 (lot Scenario, A3 + A8) : previs colorée et nommée, couverture du plan ─────────\r\n"
    "   A3 : la couleur d'une instance = celle de son entité de la bible ou de sa MATIÈRE ; palette et légende viennent\r\n"
    "   du SERVEUR (POST /palette : couleur stable par empreinte, entités d'abord). Les FAISCEAUX sont translucides à\r\n"
    "   l'écran et CACHÉS à chaque capture (un faisceau envoyé à un modèle devient un solide).\r\n"
    "   A8 : depuis la caméra du plan, plan large, contre-champ (règle des 180°), gros plan — calculés par le serveur\r\n"
    "   (POST /couverture), rangés, capturables, envoyables en plan neuf ou en image du plan (vers-plan). */\r\n"
    "const COUL_FAISCEAU = \"#ffe8a3\";\r\n"
    "let tPrevis = 0, previsSeq = 0;\r\n"
    "function estFaisceauAffiche(i) {\r\n"
    "  return i.role === \"faisceau\" || !!(P.palette && P.palette.faisceaux.some((f) => f.id === i.id));\r\n"
    "}\r\n"
    "function couleurPrevis(i, defaut) {\r\n"
    "  if (estFaisceauAffiche(i)) return COUL_FAISCEAU;\r\n"
    "  return (P.palette && P.palette.couleurs[i.id]) || defaut;\r\n"
    "}\r\n"
    "function materiauPrevis(i, coul) {\r\n"
    "  return estFaisceauAffiche(i)\r\n"
    "    ? new THREE.MeshStandardMaterial({ color: COUL_FAISCEAU, emissive: COUL_FAISCEAU, emissiveIntensity: 0.5,\r\n"
    "        transparent: true, opacity: 0.22, depthWrite: false, roughness: 1, metalness: 0 })\r\n"
    "    : new THREE.MeshStandardMaterial({ color: coul, roughness: 0.8, metalness: 0 });\r\n"
    "}\r\n"
    "/* une capture ne rend JAMAIS un faisceau : caché le temps du rendu, rendu visible ensuite */\r\n"
    "function basculerFaisceaux(visible, vus) {\r\n"
    "  const out = [];\r\n"
    "  for (const i of P.scene.instances) {\r\n"
    "    const o = P.mesh.get(i.id);\r\n"
    "    if (!o || !estFaisceauAffiche(i)) continue;\r\n"
    "    if (visible) { if (!vus || vus.includes(o)) o.visible = true; }\r\n"
    "    else if (o.visible) { o.visible = false; out.push(o); }\r\n"
    "  }\r\n"
    "  return out;\r\n"
    "}\r\n"
    "/* la previs n'est jamais grise : proxys ET maillages prennent la couleur de la palette (matériau d'argile) */\r\n"
    "function recolorer() {\r\n"
    "  for (const i of P.scene.instances) {\r\n"
    "    const o = P.mesh.get(i.id);\r\n"
    "    if (!o) continue;\r\n"
    "    const f = estFaisceauAffiche(i), coul = couleurPrevis(i, i.role === \"sujet\" ? COUL_SUJET : i.couleur);\r\n"
    "    const voulu = f ? \"faisceau\" : \"couleur\";\r\n"
    "    o.traverse((m) => {\r\n"
    "      if (!m.isMesh) return;\r\n"
    "      if (m.userData.dzPrevis !== voulu) { m.material = materiauPrevis(i, coul); m.userData.dzPrevis = voulu; }\r\n"
    "      else if (!f) m.material.color.set(coul);\r\n"
    "    });\r\n"
    "  }\r\n"
    "}\r\n"
    "function previsBientot() { clearTimeout(tPrevis); tPrevis = setTimeout(rafraichirPrevis, 250); }\r\n"
    "async function rafraichirPrevis() {\r\n"
    "  if (!P.scene) return;\r\n"
    "  const n = ++previsSeq;\r\n"
    "  try {\r\n"
    "    const d = await send(`${API}/${P.scene.id}/palette`, \"POST\", { scene: sceneAffichée() });\r\n"
    "    if (n !== previsSeq) return;\r\n"
    "    P.palette = d;\r\n"
    "    recolorer(); listeInstances(); majLegende(); majSelectsCouverture();\r\n"
    "  } catch (e) { $(\"#legende\").innerHTML = `<li class=\"avert\">${esc(e.message)}</li>`; }\r\n"
    "}\r\n"
    "function majLegende() {\r\n"
    "  const d = P.palette, en = typeof dzLang === \"function\" && dzLang() === \"en\";\r\n"
    "  $(\"#legende\").innerHTML = d && d.table.length\r\n"
    "    ? d.table.map((e, k) => `<li><span class=\"pastille\" style=\"background:${esc(e.couleur)}\"></span>${esc((en ? d.legende.en : d.legende.fr)[k])}</li>`).join(\"\")\r\n"
    "    : `<li class=\"vide\">${dzT(\"plateau.t333_leg.vide\")}</li>`;\r\n"
    "  $(\"#faisceaux\").textContent = d && d.faisceaux.length\r\n"
    "    ? dzT(\"plateau.t333_leg.faisceaux\", { n: d.faisceaux.length, noms: d.faisceaux.map((f) => f.nom).join(\", \") }) : \"\";\r\n"
    "  $(\"#legPrompt\").textContent = d && d.prompt ? d.prompt : \"\";\r\n"
    "}\r\n"
    "function champMatiere(i) {\r\n"
    "  if (i.role === \"repere\") return \"\";\r\n"
    "  return `<div class=\"ligne\"><span>${dzT(\"plateau.t333_fiche.matiere\")}</span><input class=\"champ\" data-k=\"matiere\" value=\"${esc(i.matiere || \"\")}\" placeholder=\"${dzT(\"plateau.t333_fiche.matiere_ph\")}\" title=\"${dzT(\"plateau.t333_fiche.matiere_t\")}\"></div>`;\r\n"
    "}\r\n"
    "function etiquettePrevis(i) {\r\n"
    "  return estFaisceauAffiche(i) ? `<span class=\"exclu\" title=\"${dzT(\"plateau.t333_liste.exclu_t\")}\" aria-label=\"${dzT(\"plateau.t333_liste.exclu_t\")}\">${ico(\"dz-lab3d-lumiere\", 14)}</span>` : \"\";\r\n"
    "}\r\n"
    "/* la couverture : l'interlocuteur (d'office, aucun, ou une instance) et la cible du gros plan */\r\n"
    "function majSelectsCouverture() {\r\n"
    "  const autres = P.scene.instances.filter((i) => i.role !== \"sujet\" && i.role !== \"repere\" && !estFaisceauAffiche(i));\r\n"
    "  const sujet = P.scene.instances.find((i) => i.role === \"sujet\");\r\n"
    "  const opt = (v, l, sel) => `<option value=\"${esc(v)}\" ${sel ? \"selected\" : \"\"}>${esc(l)}</option>`;\r\n"
    "  const vp = $(\"#covPartenaire\").value || \"__auto\", vg = $(\"#covGrosPlan\").value || \"\";\r\n"
    "  $(\"#covPartenaire\").innerHTML = opt(\"__auto\", dzT(\"plateau.t338_cov.auto\"), vp === \"__auto\")\r\n"
    "    + opt(\"__aucun\", dzT(\"plateau.t338_cov.aucun\"), vp === \"__aucun\") + autres.map((i) => opt(i.id, i.nom, vp === i.id)).join(\"\");\r\n"
    "  $(\"#covGrosPlan\").innerHTML = (sujet ? opt(\"\", dzT(\"plateau.t338_cov.le_sujet\", { nom: sujet.nom }), !vg) : \"\")\r\n"
    "    + autres.map((i) => opt(i.id, i.nom, vg === i.id)).join(\"\");\r\n"
    "}\r\n"
    "const nomInst = (id) => ((P.scene.instances.find((i) => i.id === id) || {}).nom || id);\r\n"
    "function nomCamera(c) {\r\n"
    "  if (c.id === \"large\") return dzT(\"plateau.t338_cam.large\");\r\n"
    "  if (c.id === \"contrechamp\") return P.couverture && P.couverture.partenaire\r\n"
    "    ? dzT(\"plateau.t338_cam.contrechamp_de\", { nom: c.cible }) : dzT(\"plateau.t338_cam.contrechamp\");\r\n"
    "  return dzT(\"plateau.t338_cam.gros_plan_de\", { nom: c.cible });\r\n"
    "}\r\n"
    "async function genererCouverture() {\r\n"
    "  const b = $(\"#btnCouverture\");\r\n"
    "  b.disabled = true;\r\n"
    "  const corps = { scene: sceneAffichée(), enregistrer: true };\r\n"
    "  if (!P.scene.keyframes.length) corps.camera = caméraCourante();      // sans keyframe : la caméra courante\r\n"
    "  const vp = $(\"#covPartenaire\").value, vg = $(\"#covGrosPlan\").value;\r\n"
    "  if (vp === \"__aucun\") corps.partenaire_id = \"\";\r\n"
    "  else if (vp && vp !== \"__auto\") corps.partenaire_id = vp;\r\n"
    "  if (vg) corps.gros_plan_id = vg;\r\n"
    "  try {\r\n"
    "    clearTimeout(tSave);\r\n"
    "    await send(`${API}/${P.scene.id}`, \"PUT\", { instances: P.scene.instances, keyframes: P.scene.keyframes, camera: caméraCourante() });\r\n"
    "    P.couverture = await send(`${API}/${P.scene.id}/couverture`, \"POST\", corps);\r\n"
    "    majCouverture();\r\n"
    "    etat(dzT(\"plateau.t338_cov.faite\"));\r\n"
    "  } catch (e) { etat(dzT(\"plateau.t338_err.couverture\", { msg: e.message }), true); }\r\n"
    "  b.disabled = false;\r\n"
    "}\r\n"
    "function majCouverture() {\r\n"
    "  const cv = P.couverture, L = $(\"#cameras\"), av = $(\"#covAvert\");\r\n"
    "  if (!cv || !cv.cameras) { L.innerHTML = `<li class=\"vide\">${dzT(\"plateau.t338_cov.vide\")}</li>`; av.innerHTML = \"\"; return; }\r\n"
    "  const r = cv.regle_180 || {};\r\n"
    "  av.innerHTML = r.avertissement ? `<span class=\"avert\">${ico(\"dz-etat-avertissement\")} ${esc(dzT(\"plateau.t338_cov.sur_axe\"))}</span>`\r\n"
    "    : r.axe ? `${ico(\"dz-etat-succes\")} ${esc(dzT(\"plateau.t338_cov.axe_tenu\", { a: nomInst(r.axe[0]), b: nomInst(r.axe[1]) }))}`\r\n"
    "    : esc(dzT(\"plateau.t338_cov.sans_axe\"));\r\n"
    "  L.innerHTML = cv.cameras.map((c) => `<li data-cam=\"${esc(c.id)}\">\r\n"
    "    <div class=\"cam-tete\"><b>${esc(nomCamera(c))}</b><span class=\"sous\">${esc(c.shot_type)} · ${Math.round(c.focale_mm)} mm · h ${f2(c.h)}</span></div>\r\n"
    "    ${c.capture ? `<img src=\"/api/images/${encodeURIComponent(c.capture)}\" alt=\"${esc(nomCamera(c))}\">` : \"\"}\r\n"
    "    <div class=\"ligne\"><button class=\"btn\" data-act=\"voir\" title=\"${dzT(\"plateau.t338_cam.voir_t\")}\">${ico(\"dz-etat-visible\")} ${dzT(\"plateau.t338_cam.voir\")}</button>\r\n"
    "      <button class=\"btn\" data-act=\"capturer\" title=\"${dzT(\"plateau.t338_cam.capturer_t\")}\">${ico(\"dz-action-capturer\")} ${dzT(\"plateau.t338_cam.capturer\")}</button></div>\r\n"
    "    <div class=\"ligne\"><button class=\"btn\" data-act=\"plan\" ${P.plan ? \"\" : \"disabled\"} title=\"${dzT(\"plateau.t338_cam.plan_t\")}\">${ico(\"dz-action-nouveau\")} ${dzT(\"plateau.t338_cam.plan\")}</button>\r\n"
    "      <button class=\"btn\" data-act=\"image\" ${P.plan && c.capture ? \"\" : \"disabled\"} title=\"${dzT(\"plateau.t338_cam.image_t\")}\">${ico(\"dz-action-envoyer-vers\")} ${dzT(\"plateau.t338_cam.image\")}</button></div>\r\n"
    "    <div class=\"cam-retour\"></div></li>`).join(\"\");\r\n"
    "  L.querySelectorAll(\"[data-act]\").forEach((b) => b.addEventListener(\"click\", () => actionCamera(b.closest(\"li\").dataset.cam, b.dataset.act, b)));\r\n"
    "}\r\n"
    "/* Voir / Capturer / Nouveau plan / Image du plan : deux gestes écrivent, et chacun montre d'abord ce qu'il fera\r\n"
    "   (aperçu du plan neuf, avant / après de la borne) puis demande un second clic sur le bouton armé */\r\n"
    "async function actionCamera(id, act, b) {\r\n"
    "  const c = P.couverture.cameras.find((x) => x.id === id), z = b.closest(\"li\").querySelector(\".cam-retour\");\r\n"
    "  if (!c) return;\r\n"
    "  if (P.lecture) basculerLecture();\r\n"
    "  if (act === \"voir\") { poserCaméra(c.camera); majFocale(false); majGuides(); mesurerBientôt(); return; }\r\n"
    "  try {\r\n"
    "    if (act === \"capturer\") {\r\n"
    "      poserCaméra(c.camera); majFocale(false); majGuides();\r\n"
    "      const a = ASPECTS[P.scene.aspect];\r\n"
    "      const w = a >= 1 ? CAPTURE_PX : Math.round(CAPTURE_PX * a), h = a >= 1 ? Math.round(CAPTURE_PX / a) : CAPTURE_PX;\r\n"
    "      const image = rendreA(w, h);\r\n"
    "      const d = await send(`${API}/${P.scene.id}/capture`, \"POST\", { quand: \"camera\", camera_id: id, image_b64: image, scene: sceneAffichée() });\r\n"
    "      c.capture = d.filename;\r\n"
    "      majCouverture();\r\n"
    "      etat(dzT(\"plateau.t338_cam.capturee\", { nom: nomCamera(c) }));\r\n"
    "    } else if (act === \"plan\") {\r\n"
    "      const url = `${API}/${P.scene.id}/couverture/${encodeURIComponent(id)}/nouveau-plan`;\r\n"
    "      if (b.dataset.arm !== \"1\") {\r\n"
    "        const d = await send(url, \"POST\", {});\r\n"
    "        z.innerHTML = `<div class=\"k\">${esc(dzT(\"plateau.t338_cam.plan_apercu\", { n: d.plan.idx + 1, type: d.plan.shot_type }))}</div>`;\r\n"
    "        b.dataset.arm = \"1\";\r\n"
    "        b.innerHTML = `${ico(\"dz-action-nouveau\")} ${dzT(\"plateau.t338_cam.plan_confirmer\")}`;\r\n"
    "        return;\r\n"
    "      }\r\n"
    "      const d = await send(url, \"POST\", { confirmer: true });\r\n"
    "      b.dataset.arm = \"\"; b.disabled = true;\r\n"
    "      z.innerHTML = `<div>${esc(dzT(\"plateau.t338_cam.plan_cree\", { n: d.plan.idx + 1 }))} <a href=\"?scene=${encodeURIComponent(d.scene_id)}\">${dzT(\"plateau.t338_cam.ouvrir\")}</a></div>`;\r\n"
    "    } else if (act === \"image\") {\r\n"
    "      const ap = { keyframe_image: c.capture };\r\n"
    "      if (b.dataset.arm !== \"1\") {\r\n"
    "        const d = await send(`${API}/${P.scene.id}/vers-plan`, \"POST\", { appliquer: ap });\r\n"
    "        z.innerHTML = `<div class=\"k\">${esc(dzT(\"plateau.t338_cam.image_apercu\", { avant: d.avant.keyframe_image || \"—\", apres: d.apres.keyframe_image }))}</div>`;\r\n"
    "        if (!d.change.length) return;\r\n"
    "        b.dataset.arm = \"1\";\r\n"
    "        b.innerHTML = `${ico(\"dz-action-envoyer-vers\")} ${dzT(\"plateau.t338_cam.image_confirmer\")}`;\r\n"
    "        return;\r\n"
    "      }\r\n"
    "      await send(`${API}/${P.scene.id}/vers-plan`, \"POST\", { appliquer: ap, confirmer: true });\r\n"
    "      b.dataset.arm = \"\"; b.disabled = true;\r\n"
    "      P.plan.keyframe_image = c.capture;\r\n"
    "      z.innerHTML = `<div>${esc(dzT(\"plateau.t338_cam.image_faite\", { nom: nomCamera(c) }))}</div>`;\r\n"
    "    }\r\n"
    "  } catch (e) { z.innerHTML = `<div class=\"avert\">${esc(e.message)}</div>`; }\r\n"
    "}\r\n"
    "function previsOuvrir() {\r\n"
    "  P.couverture = P.scene.couverture || null;\r\n"
    "  majSelectsCouverture(); majCouverture(); rafraichirPrevis();\r\n"
    "}\r\n"
    "$(\"#btnCouverture\").addEventListener(\"click\", genererCouverture);\r\n"
    "\r\n"
)

D_BLOC = {
    "plateau.t333_leg.vide": ("Aucune forme à légender : posez des proxys ou des maillages.",
                              "No shape to label yet: add proxies or meshes."),
    "plateau.t333_leg.faisceaux": ("{n} faisceau(x) de lumière exclu(s) des captures et du GLB : {noms}",
                                   "{n} light beam(s) left out of captures and the GLB: {noms}"),
    "plateau.t333_fiche.matiere": ("Matière", "Material"),
    "plateau.t333_fiche.matiere_ph": ("ce que c'est : cyprès, ajoncs…", "what it is: cypress, gorse…"),
    "plateau.t333_fiche.matiere_t": ("Ce que représente la forme : nommée dans la légende et les prompts du plan "
                                     "(« cylindres verts = cyprès ») ; les formes de même matière partagent leur couleur",
                                     "What the shape stands for: named in the legend and the shot prompts (\"green "
                                     "cylinders = cypress\"); shapes of the same material share their colour"),
    "plateau.t333_liste.exclu_t": ("Volume de lumière : ni capturé, ni composé, ni légendé (il deviendrait un solide)",
                                   "Light volume: never captured, composed or labelled (it would turn into a solid)"),
    "plateau.t338_cov.auto": ("d'office (le plus proche)", "automatic (nearest)"),
    "plateau.t338_cov.aucun": ("aucun (180° autour du sujet)", "none (180° around the subject)"),
    "plateau.t338_cov.le_sujet": ("le sujet ({nom})", "the subject ({nom})"),
    "plateau.t338_cov.faite": ("couverture générée : 3 caméras rangées dans la scène",
                               "coverage generated: 3 cameras saved in the scene"),
    "plateau.t338_cov.vide": ("Aucune caméra de couverture : générez-la depuis la caméra du plan.",
                              "No coverage camera yet: generate it from the shot's camera."),
    "plateau.t338_cov.sur_axe": ("La caméra du plan est sur l'axe sujet ↔ interlocuteur : décalez-la d'un côté puis "
                                 "régénérez.", "The shot's camera sits on the subject ↔ other-character axis: move it "
                                 "to one side, then generate again."),
    "plateau.t338_cov.axe_tenu": ("Règle des 180° tenue : axe {a} ↔ {b}, contre-champ du même côté",
                                  "180° rule kept: axis {a} ↔ {b}, reverse shot on the same side"),
    "plateau.t338_cov.sans_axe": ("Sans interlocuteur : le contre-champ tourne de 180° autour du sujet.",
                                  "No other character: the reverse angle turns 180° around the subject."),
    "plateau.t338_err.couverture": ("couverture : {msg}", "coverage: {msg}"),
    "plateau.t338_cam.large": ("Plan large", "Wide shot"),
    "plateau.t338_cam.contrechamp": ("Contre-champ", "Reverse shot"),
    "plateau.t338_cam.contrechamp_de": ("Contre-champ — {nom}", "Reverse shot — {nom}"),
    "plateau.t338_cam.gros_plan_de": ("Gros plan — {nom}", "Close-up — {nom}"),
    "plateau.t338_cam.voir": ("Voir", "View"),
    "plateau.t338_cam.voir_t": ("Poser cette caméra dans le cadre", "Put this camera in the frame"),
    "plateau.t338_cam.capturer": ("Capturer", "Capture"),
    "plateau.t338_cam.capturer_t": ("Capturer ce cadre vers la Bibliothèque (Plateau 3D), faisceaux cachés",
                                    "Capture this frame to the Library (3D Stage), light beams hidden"),
    "plateau.t338_cam.capturee": ("{nom} capturé dans la Bibliothèque", "{nom} captured to the Library"),
    "plateau.t338_cam.plan": ("Nouveau plan", "New shot"),
    "plateau.t338_cam.plan_t": ("Créer un plan juste après le plan lié, avec sa scène posée sur cette caméra (un "
                                "second clic confirme)", "Create a shot right after the linked one, its scene set on "
                                "this camera (a second click confirms)"),
    "plateau.t338_cam.plan_apercu": ("Plan {n} · {type} · fixe — cliquez encore pour le créer",
                                     "Shot {n} · {type} · static — click again to create it"),
    "plateau.t338_cam.plan_confirmer": ("Créer le plan", "Create the shot"),
    "plateau.t338_cam.plan_cree": ("Plan {n} créé dans le storyboard.", "Shot {n} created in the storyboard."),
    "plateau.t338_cam.ouvrir": ("Ouvrir sa scène", "Open its scene"),
    "plateau.t338_cam.image": ("Image du plan", "Shot image"),
    "plateau.t338_cam.image_t": ("Faire de cette capture l'image de début du plan lié (avant / après, puis un second "
                                 "clic confirme)", "Make this capture the linked shot's start frame (before / after, "
                                 "then a second click confirms)"),
    "plateau.t338_cam.image_apercu": ("image de début : {avant} → {apres}", "start frame: {avant} → {apres}"),
    "plateau.t338_cam.image_confirmer": ("Écrire dans le plan", "Write to the shot"),
    "plateau.t338_cam.image_faite": ("{nom} est l'image de début du plan.", "{nom} is now the shot's start frame."),
}

ENTREES = [
    # l'aide de la previs : importée nulle part ailleurs, le bloc vit dans plateau.js (table réversible)
    S(PJ, 109, '  const coul = inst.role === "sujet" ? COUL_SUJET : inst.couleur;\r\n'
               '  const mat = new THREE.MeshStandardMaterial({ color: coul, roughness: 0.8, metalness: 0 });',
      '  const coul = couleurPrevis(inst, inst.role === "sujet" ? COUL_SUJET : inst.couleur);   // t333 : la palette\r\n'
      '  const mat = materiauPrevis(inst, coul);', {}),
    S(PJ, 153, 'style="background:${i.role === "sujet" ? COUL_SUJET : esc(i.couleur)}"></span>${esc(i.nom)}',
      'style="background:${esc(couleurPrevis(i, i.role === "sujet" ? COUL_SUJET : i.couleur))}"></span>${esc(i.nom)}'
      '${etiquettePrevis(i)}', {}),
    S(PJ, 163, '["sujet", "decor", "repere"].map(', '["sujet", "decor", "repere", "faisceau"].map(', {}),
    S(PJ, 165, '    <div class="xyz"><span>pos m</span>', '    ${champMatiere(i)}\r\n    <div class="xyz"><span>pos m</span>', {}),
    S(PJ, 183, '  if (k === "nom") i.nom = el.value.trim() || i.nom;',
      '  if (k === "nom") i.nom = el.value.trim() || i.nom;\r\n'
      '  else if (k === "matiere") i.matiere = el.value.trim() || null;          // t333 : la légende de la previs', {}),
    S(PJ, 244, '  P.dirty = true;', '  P.dirty = true;\r\n  previsBientot();                                   // t333 : palette et légende suivent', {}),
    S(PJ, 374, '  r.render(V.scene, c);', '  const vus = basculerFaisceaux(false);             // t333 : jamais de faisceau capturé\r\n'
                                         '  r.render(V.scene, c);', {}),
    S(PJ, 375, '  const url = r.domElement.toDataURL("image/png");',
      '  const url = r.domElement.toDataURL("image/png");\r\n  basculerFaisceaux(true, vus);', {}),
    S(PJ, 386, '{ quand, image_b64: b64 }', '{ quand, image_b64: b64, scene: sceneAffichée() }', {}),
    S(PJ, 469, '  listeInstances(); fiche(); majTimeline(); allerA(0);',
      '  listeInstances(); fiche(); majTimeline(); allerA(0);\r\n  previsOuvrir();                                    // t333 + t338', {}),
    S(PJ, 473, 'ouvrir();\r\n', BLOC + 'ouvrir();\r\n', D_BLOC),

    # index.html : sections « Previs colorée » et « Couverture » (traduites par la surcouche)
    H("plateau.t333_page.titre", "Previs colorée", "Coloured previs"),
    H("plateau.t333_page.aide", "Une couleur par entité de la bible ou matière ; la légende part dans les prompts du plan.",
      "One colour per bible entity or material; the legend goes into the shot prompts."),
    H("plateau.t333_page.prompt_t", "Phrase ajoutée aux prompts de Previs → plan et de l'image du plan",
      "Sentence added to the Previs → shot and shot image prompts"),
    H("plateau.t338_page.titre", "Couverture", "Coverage"),
    H("plateau.t338_page.interlocuteur", "Interlocuteur", "Other character"),
    H("plateau.t338_page.interlocuteur_a", "Interlocuteur : l'axe du contre-champ", "Other character: the reverse-shot axis"),
    H("plateau.t338_page.gros_plan", "Gros plan", "Close-up"),
    H("plateau.t338_page.gros_plan_a", "Cible du gros plan", "Close-up target"),
    H("plateau.t338_page.generer", "Générer la couverture", "Generate coverage"),
    H("plateau.t338_page.generer_t", "Plan large, contre-champ et gros plan depuis la caméra du plan (son premier "
      "keyframe, sinon la caméra courante) — gratuit, tout local",
      "Wide shot, reverse shot and close-up from the shot's camera (its first keyframe, otherwise the current "
      "camera) — free, all local"),
    H("plateau.t338_page.regle", "La règle des 180°", "The 180° rule"),
    H("plateau.t338_page.regle_txt", "L'axe d'action relie le sujet à son interlocuteur. Le contre-champ reste du même "
      "côté de cet axe que la caméra du plan : les regards restent raccord, l'un regarde à gauche, l'autre à droite.",
      "The axis of action links the subject to the other character. The reverse shot stays on the same side of that "
      "axis as the shot's camera, so eyelines match: one looks left, the other looks right."),
]
