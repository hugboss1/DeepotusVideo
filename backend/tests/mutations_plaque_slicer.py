"""Banc de mutations de la plaque façon slicer : casser → rouge → remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance À LA MAIN, depuis backend/ :

    python tests/mutations_plaque_slicer.py          # toutes
    python tests/mutations_plaque_slicer.py 3 17     # celles-là

Il MUTE les sources du dépôt une à une et les REMET à l'octet près (assertion),
donc il ne se lance pas pendant qu'un autre banc lit ces fichiers. La liste est
l'argument de la revue : chaque mutation nomme le test qu'elle fait rougir, et
une « VERTE » est une assertion qui manque — c'est ainsi que la ligne morte du
pivot, le trou de l'origine des règles et le mutant faible du libellé ont été
trouvés.

Chaque mutation : (fichier, ancien, nouveau, tests attendus rouges).
Le script VÉRIFIE que la mutation a bien été appliquée (l'ancien texte existe,
une fois), lance le banc ciblé, lit les noms des tests rouges, et remet le
fichier à l'octet près. Une mutation « verte » est signalée.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
BANC = "tests/test_etabli_canevas.py"

M = [
    # ── plaque.js ────────────────────────────────────────────────────────────
    ("frontend/lib3d/plaque.js",
     "  const cote = pas ? cases * pas : brut;",
     "  const cote = brut;",
     ["nombre_entier_de_PAS"]),
    ("frontend/lib3d/plaque.js",
     "  const grille = new THREE.GridHelper(cote, g.cases, 0x5b636f, 0x333941);",
     "  const grille = new THREE.GridHelper(cote, 24, 0x5b636f, 0x333941);",
     ["nombre_entier_de_PAS"]),
    ("frontend/lib3d/plaque.js",
     "  const pas = pasGradue(brut);",
     "  const pas = pasGradue(brut * 2);",
     ["nombre_entier_de_PAS"]),
    ("frontend/lib3d/plaque.js",
     "  e.decalage[g.u] += du;\n  e.decalage[g.v] += dv;\n  e.berceau.position.copy(versLocal(e.parent, e.decalage));",
     "  e.decalage[g.u] += du;\n  e.decalage[g.v] += dv;\n  e.berceau.position.copy(versLocal(e.parent, e.decalage));\n  e.piece.position.x += 1e-3;",
     ["DEPLACE_par_le_BERCEAU"]),
    ("frontend/lib3d/plaque.js",
     "  e.decalage[g.u] += du;\n  e.decalage[g.v] += dv;",
     "  e.decalage[g.u] += du;\n  e.decalage[g.v] += du;",
     ["DEPLACE_par_le_BERCEAU"]),
    ("frontend/lib3d/plaque.js",
     "  e.pivot.matrix.copy(Mi).multiply(Tc).multiply(R).multiply(Tmc).multiply(M);",
     "  e.pivot.matrix.copy(Mi).multiply(R).multiply(M);",
     ["ROTATION_tourne"]),
    ("frontend/lib3d/plaque.js",
     "  const R = new THREE.Matrix4().makeRotationAxis(n, (e.rot * Math.PI) / 180);",
     "  const R = new THREE.Matrix4().makeRotationAxis(n, (-e.rot * Math.PI) / 180);",
     ["ROTATION_tourne"]),
    ("frontend/lib3d/plaque.js",
     "  let r = ((d % 360) + 360) % 360;\n  if (r > 180) r -= 360;",
     "  let r = d;",
     ["ROTATION_tourne"]),
    ("frontend/lib3d/plaque.js",
     "    if (pose) {\n      d[u] = Number(pose.dx) || 0;\n      d[v] = Number(pose.dy) || 0;\n    }",
     "",
     ["applique_le_PLAN", "ROTATION_tourne"]),
    ("frontend/lib3d/plaque.js",
     "  const planApplique = !!(plan && plan.axe === mise.axe\n                          && Array.isArray(plan.pieces));",
     "  const planApplique = !!(plan && Array.isArray(plan.pieces));",
     ["applique_le_PLAN"]),
    ("frontend/lib3d/plaque.js",
     "    if (pose && Number.isFinite(Number(pose.rot)) && Number(pose.rot) !== 0) {\n      e.rot = Number(pose.rot);\n      poserPivot(e, mise.axe);\n    }",
     "",
     ["applique_le_PLAN", "ROTATION_tourne"]),
    ("frontend/lib3d/plaque.js",
     "  const signe = axe === \"y\" ? -1 : 1;",
     "  const signe = 1;",
     ["ANNEAU"]),
    ("frontend/lib3d/plaque.js",
     "  return origine + Math.round((valeur - origine) / pas) * pas;",
     "  return valeur;",
     ["AIMANTATION"]),
    ("frontend/lib3d/plaque.js",
     "    if (!e.piece.visible) continue;",
     "",
     ["ANNEAU"]),
    ("frontend/lib3d/plaque.js",
     "  if (h.axe === d.axe) {\n    const autre = d.axe === u ? v : u;\n    h = { axe: autre, signe: Math.sign(haut[autre]) || 1 };\n  }",
     "",
     ["FLECHES"]),
    ("frontend/lib3d/plaque.js",
     "  const droite = { x: elements[0], y: elements[1], z: elements[2] };\n  const haut = { x: elements[4], y: elements[5], z: elements[6] };",
     "  const droite = { x: elements[4], y: elements[5], z: elements[6] };\n  const haut = { x: elements[0], y: elements[1], z: elements[2] };",
     ["FLECHES"]),
    ("frontend/lib3d/plaque.js",
     "  for (const groupe of [etat.plateau, etat.poignee]) {",
     "  for (const groupe of [etat.plateau]) {",
     ["REPERE_ORTHONORME", "SANS_RECHARGER"]),
    ("frontend/lib3d/plaque.js",
     "      index: e.cle, dx: e.decalage[g.u], dy: e.decalage[g.v], rot: e.rot })),",
     "      index: e.cle, dx: e.decalage[g.v], dy: e.decalage[g.u], rot: e.rot })),",
     ["DEPLACE_par_le_BERCEAU", "ROTATION_tourne"]),
    # ── viewer.js ────────────────────────────────────────────────────────────
    ("frontend/lib3d/viewer.js",
     "  const n = Math.floor(cote / pas + 1e-9);",
     "  const n = Math.floor(cote / pas + 1e-9) - 1;",
     ["REGLES_sont", "nombre_entier_de_PAS"]),
    ("frontend/lib3d/viewer.js",
     "    ctx.fillText(l.texte, x, cv.height / 2);",
     "    ctx.fillText(l.texte.replace(/[^0-9.,]/g, \"\"), x, cv.height / 2);",
     ["REGLES_sont"]),
    ("frontend/lib3d/viewer.js",
     "  if (e && e.cle === cle) return e;",
     "  if (false) return e;",
     ["REGLES_sont"]),
    ("frontend/lib3d/viewer.js",
     "      if (o.material.map) o.material.map.dispose();",
     "",
     ["REGLES_sont"]),
    ("frontend/lib3d/viewer.js",
     "  const origine = new THREE.Vector3(g.coin.x, g.coin.y, g.coin.z);",
     "  const origine = new THREE.Vector3(); origine[g.u] = -g.cote / 2; origine[g.v] = -g.cote / 2;",
     ["REGLES_sont"]),
    ("frontend/lib3d/plaque.js",
     "  coin[u] = (-sens.u * cote) / 2;\n  coin[v] = (-sens.v * cote) / 2;",
     "  coin[u] = -cote / 2;\n  coin[v] = -cote / 2;",
     ["nombre_entier_de_PAS", "REGLES_sont"]),
    ("frontend/lib3d/viewer.js",
     "  const sensDe = (a) => (Math.abs(droite[a]) >= Math.abs(h[a])\n    ? Math.sign(droite[a]) || 1 : Math.sign(h[a]) || 1);",
     "  const sensDe = (a) => 1;",
     ["REGLES_sont", "nombre_entier_de_PAS"]),
    ("frontend/lib3d/viewer.js",
     "    seg(pu, pu.clone().addScaledVector(av, -long));",
     "    seg(pu, pu.clone().addScaledVector(av, long));",
     ["REGLES_sont"]),
    ("frontend/lib3d/viewer.js",
     "  libelles.push({ fraction: (g.cote + 0.6 * g.pas) / longueur,\n                  texte: String(unite ?? \"\") });",
     "",
     ["REGLES_sont", "PAS_DU_PLATEAU"]),
    ("frontend/lib3d/viewer.js",
     "  api.scene.add(groupe);\n  e = { groupe, cle, origine, sens, valeurs, textes, traits,",
     "  e = { groupe, cle, origine, sens, valeurs, textes, traits,",
     ["REPERE_ORTHONORME", "PAS_DU_PLATEAU"]),
    ("frontend/lib3d/viewer.js",
     "  const y = new THREE.Vector3().crossVectors(normale, dir);",
     "  const y = new THREE.Vector3().crossVectors(dir, normale);",
     ["REGLES_sont"]),
    # ── etabli.js ────────────────────────────────────────────────────────────
    ("frontend/etabli/etabli.js",
     "  PLQ.repereAvant = montrerRepere(S.vueA, false);",
     "  PLQ.repereAvant = true; montrerRepere(S.vueA, false);",
     ["REPERE_ORTHONORME"]),
    ("frontend/etabli/etabli.js",
     "  montrerRepere(S.vueA, PLQ.repereAvant);\n  PLQ.active = false;",
     "  montrerRepere(S.vueA, true);\n  PLQ.active = false;",
     ["REPERE_ORTHONORME"]),
    ("frontend/etabli/etabli.js",
     "  envoyerPlan();\n  effacerRegles(S.vueA);",
     "  effacerRegles(S.vueA);",
     ["REPERE_ORTHONORME", "PREMIERE_RETOUCHE"]),
    ("frontend/etabli/etabli.js",
     "  effacerRegles(S.vueA);\n  marquerPiece(S.vueA, null);",
     "  marquerPiece(S.vueA, null);",
     ["REPERE_ORTHONORME"]),
    ("frontend/etabli/etabli.js",
     "  const pasVu = PLQ.active ? PLQ.pas : REP.pas;",
     "  const pasVu = REP.pas;",
     ["PAS_DU_PLATEAU"]),
    ("frontend/etabli/etabli.js",
     "  graduerPlateau();\n\n  const m = mesurerRetenus();",
     "\n  const m = mesurerRetenus();",
     ["REGLES_sont", "PAS_DU_PLATEAU"]),
    ("frontend/etabli/etabli.js",
     "                 fmtMesure, uniteCourante());",
     "                 (v) => String(v), uniteCourante());",
     ["REGLES_sont", "PAS_DU_PLATEAU"]),
    ("frontend/etabli/etabli.js",
     "      if (!ev.shiftKey) {\n        u = aimanter(u, g.coin[g.u], g.pas);\n        v = aimanter(v, g.coin[g.v], g.pas);\n      }",
     "",
     ["AIMANTATION"]),
    ("frontend/etabli/etabli.js",
     "      if (ev.shiftKey) rot = Math.round(rot / PAS_ROTATION) * PAS_ROTATION;",
     "",
     ["ANNEAU"]),
    ("frontend/etabli/etabli.js",
     "    api.controls.enabled = false;\n    if (canvas.setPointerCapture)",
     "    if (canvas.setPointerCapture)",
     ["AIMANTATION"]),
    ("frontend/etabli/etabli.js",
     "    geste = null;\n    GESTE.enCours = null;\n    api.controls.enabled = true;",
     "    geste = null;\n    GESTE.enCours = null;",
     ["AIMANTATION"]),
    ("frontend/etabli/etabli.js",
     "      if (Math.hypot(ev.clientX - geste.x0, ev.clientY - geste.y0)\n          <= TOLERANCE_CLIC) return;",
     "",
     ["AIMANTATION"]),
    ("frontend/etabli/etabli.js",
     "    if (!cible) return;\n    const point = pointSurPlateau(api, ndc);",
     "    const point = pointSurPlateau(api, ndc);",
     ["AIMANTATION"]),
    ("frontend/etabli/etabli.js",
     "  const pas = g.pas * (ev.altKey ? 0.1 : ev.ctrlKey ? 10 : 1);",
     "  const pas = g.pas;",
     ["FLECHES"]),
    # ancrée sur la garde de la plaque : depuis le lot B, le clavier des
    # outils (toucheClavierOutils) garde les champs par les deux mêmes lignes
    ("frontend/etabli/etabli.js",
     "  if (!PLQ.active || PLQ.courante === null || !S.vueA) return false;\n  const t = ev.target;\n  if (t && (t.isContentEditable\n            || /^(INPUT|TEXTAREA|SELECT)$/i.test(t.tagName || \"\"))) return false;",
     "  if (!PLQ.active || PLQ.courante === null || !S.vueA) return false;\n  const t = ev.target;",
     ["FLECHES"]),
    ("frontend/etabli/etabli.js",
     "  const dir = axesEcran(S.vueA.camera.matrixWorld.elements, g.axe)[f[0]];",
     "  const dir = f[0] === \"droite\" ? { axe: g.u, signe: 1 } : { axe: g.v, signe: 1 };",
     ["FLECHES"]),
    # ancree sur noterPlan() : depuis le lot B, toucheClavierOutils finit par
    # les deux memes lignes
    ("frontend/etabli/etabli.js",
     "  noterPlan();\n  if (ev.preventDefault) ev.preventDefault();\n  return true;",
     "  noterPlan();\n  return true;",
     ["FLECHES"]),
    ("frontend/etabli/etabli.js",
     "  PLQ.aEnvoyer = { job: S.a.job, version: S.a.version, ...plan };\n  if (!_envoiPlan) _envoiPlan = setTimeout(envoyerPlan, DELAI_PLAN_MS);",
     "  PLQ.aEnvoyer = { job: S.a.job, version: S.a.version, ...plan };\n  _envoiPlan = setTimeout(envoyerPlan, DELAI_PLAN_MS);",
     ["PREMIERE_RETOUCHE"]),
    ("frontend/etabli/etabli.js",
     "  const corps = PLQ.aEnvoyer;\n  PLQ.aEnvoyer = null;\n  if (!corps) return;\n  _envoisEnVol++;",
     "  const corps = { job: S.a.job, version: S.a.version, ...dispositionDe(S.vueA) };\n  PLQ.aEnvoyer = null;\n  if (!corps) return;\n  _envoisEnVol++;",
     ["PREMIERE_RETOUCHE"]),
    ("frontend/etabli/etabli.js",
     "  const etalement = etaler(S.vueA, plan);\n  if (!etalement) {\n    direRefus(\"aucune pièce mesurable",
     "  const etalement = etaler(S.vueA, plan);\n  noterPlan();\n  if (!etalement) {\n    direRefus(\"aucune pièce mesurable",
     ["PREMIERE_RETOUCHE"]),
    ("frontend/etabli/etabli.js",
     "  if (r.status === 404) return null;\n  if (!r.ok) throw",
     "  if (!r.ok) return null;\n  if (!r.ok) throw",
     ["PREMIERE_RETOUCHE"]),
    ("frontend/etabli/etabli.js",
     "  glisserSurPlaque(S.vueA, $(\"#vueA canvas\"));\n});",
     "});",
     ["AIMANTATION"]),
    # ── second tour : la lecture d'une pièce tournée, le retour, le coin ─────
    ("frontend/lib3d/plaque.js",
     "    .multiply(new THREE.Matrix4().makeRotationAxis(n, (-e.rot * Math.PI) / 180))\n",
     "",
     ["TOURNEE_et_ASYMETRIQUE"]),
    ("frontend/lib3d/plaque.js",
     "    .multiply(new THREE.Matrix4().makeTranslation(-d.x, -d.y, -d.z));",
     ";",
     ["TOURNEE_et_ASYMETRIQUE"]),
    ("frontend/lib3d/plaque.js",
     "  const rayon = (e.demiDiagonale || g.pas || 1) * MARGE_POIGNEE;",
     "  const emp = empreinteDe(api, e.cle);\n  const rayon = (Math.hypot(emp.l, emp.p) / 2) * MARGE_POIGNEE;",
     ["ANNEAU"]),
    ("frontend/lib3d/viewer.js",
     "  poserBande(bandeV, origine, av, au, normale, longueur, largeur, espace);",
     "  poserBande(bandeV, origine, av, au, normale, longueur, largeur, -espace - largeur);",
     ["REGLES_sont"]),
    ("frontend/lib3d/viewer.js",
     "    const demi = ctx.measureText(l.texte).width / 2;",
     "    const demi = 0;",
     ["REGLES_sont"]),
    ("frontend/etabli/etabli.js",
     "    const lu = boiteModele(S.vueA, o);",
     "    const lu = { boite: new THREE.Box3().setFromObject(o), etale: false };",
     ["TOURNEE_et_ASYMETRIQUE", "POSITION_lue"]),
    ("frontend/etabli/etabli.js",
     "  if (_envoiPlan || PLQ.aEnvoyer || _envoisEnVol) {\n    envoyerPlan();\n    direRefus(\"disposition de la plaque en cours d'enregistrement — un \"\n      + \"instant, puis revenez au 3D Studio\");\n    return;\n  }\n",
     "",
     ["PREMIERE_RETOUCHE"]),
    ("frontend/etabli/etabli.js",
     "  if (_envoiPlan || PLQ.aEnvoyer || _envoisEnVol) {\n    envoyerPlan();",
     "  if (_envoiPlan || PLQ.aEnvoyer || _envoisEnVol) {",
     ["PREMIERE_RETOUCHE"]),
    ("frontend/etabli/etabli.js",
     "  fetch(ROUTE_PLAQUE, { method: \"POST\", keepalive: true,",
     "  fetch(ROUTE_PLAQUE, { method: \"POST\",",
     ["PREMIERE_RETOUCHE"]),
    ("frontend/etabli/etabli.js",
     "  const tour = _envoiChaine.then(async () => {",
     "  const tour = Promise.resolve().then(async () => {",
     ["PREMIERE_RETOUCHE"]),
    ("frontend/etabli/etabli.js",
     "    } finally {\n      _envoisEnVol--;\n    }",
     "    } finally {\n    }",
     ["PREMIERE_RETOUCHE"]),
    ("frontend/etabli/etabli.js",
     "      if (GESTE.enCours && GESTE.enCours.quoi === \"poignee\") return;\n",
     "",
     ["ANNEAU"]),
    ("frontend/etabli/etabli.js",
     "      if (!masquee && cle === PLQ.courante) {\n        PLQ.courante = null;\n        marquerPiece(S.vueA, null);\n      }\n",
     "",
     ["ANNEAU"]),
    ("backend/app/api/routes.py",
     "    if not isinstance(job, str):\n        raise HTTPException(400, f\"plan de plaque : job « {job} » — le nom du \"\n                                 \"dossier de job est attendu\")\n",
     "",
     ["PLAN_DE_PLAQUE"]),
    ("backend/app/api/routes.py",
     "    if version < 1:\n        raise HTTPException(400, f\"plan de plaque : version {version} — les \"\n                                 \"versions sont numérotées à partir de 1\")\n    p = _etabli_plaque_cible(job, version)\n    if not p.is_file():",
     "    p = _etabli_plaque_cible(job, version)\n    if not p.is_file():",
     ["PLAN_DE_PLAQUE"]),
    ("backend/app/api/routes.py",
     "           \"repere\": \"monde\", \"pieces\": propres}",
     "           \"pieces\": propres}",
     ["PLAN_DE_PLAQUE"]),
    # ── la 77e, du relecteur : le glisser branché AVANT le sélecteur au clic.
    #    Deux remplacements (la liste), parce qu'on DÉPLACE l'appel : le relever
    #    du sélecteur ne voit plus `_gestePlaque`, un clic sur l'anneau relâche.
    ("frontend/etabli/etabli.js",
     [("  _clicBranche = true;\n  designerAuClic(S.vueA, $(\"#vueA canvas\"), (obj, touche) => {",
       "  _clicBranche = true;\n  glisserSurPlaque(S.vueA, $(\"#vueA canvas\"));\n  designerAuClic(S.vueA, $(\"#vueA canvas\"), (obj, touche) => {"),
      ("  glisserSurPlaque(S.vueA, $(\"#vueA canvas\"));\n});",
       "});")],
     None,
     ["ANNEAU"]),
    # ── routes.py ────────────────────────────────────────────────────────────
    # ancree sur le refus du plan : depuis le lot B, _etabli_glb_cible porte
    # la meme garde de version
    ("backend/app/api/routes.py",
     "    if not _etabli_entier(version) or version < 1:\n        raise HTTPException(400, f\"plan de plaque : version « {version} » — \"",
     "    if not isinstance(version, (int, float)) or version < 1:\n        raise HTTPException(400, f\"plan de plaque : version « {version} » — \"",
     ["PLAN_DE_PLAQUE"]),
    ("backend/app/api/routes.py",
     "    if axe not in _ETABLI_AXES:",
     "    if axe is not None and axe not in _ETABLI_AXES:",
     ["PLAN_DE_PLAQUE"]),
    ("backend/app/api/routes.py",
     "    if not _etabli_nombre(pas) or pas <= 0:",
     "    if not _etabli_nombre(pas) or pas < 0:",
     ["PLAN_DE_PLAQUE"]),
    ("backend/app/api/routes.py",
     "        if index in vus:",
     "        if False:",
     ["PLAN_DE_PLAQUE"]),
    ("backend/app/api/routes.py",
     "        if not _etabli_entier(index) or index < 0:",
     "        if not _etabli_entier(index):",
     ["PLAN_DE_PLAQUE"]),
    ("backend/app/api/routes.py",
     "    return (isinstance(v, (int, float)) and not isinstance(v, bool)",
     "    return (isinstance(v, (int, float))",
     ["PLAN_DE_PLAQUE"]),
    ("backend/app/api/routes.py",
     "    if not glb.is_file():\n        raise HTTPException(404, f\"plan de plaque",
     "    if False:\n        raise HTTPException(404, f\"plan de plaque",
     ["PLAN_DE_PLAQUE"]),
    ("backend/app/api/routes.py",
     "    tmp = d / f\"{p.name}.tmp\"\n    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1),\n                   encoding=\"utf-8\")\n    tmp.replace(p)",
     "    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1),\n                 encoding=\"utf-8\")",
     ["PLAN_DE_PLAQUE"]),
    ("backend/app/api/routes.py",
     "    return _etabli_cible_sous_jobs(job, lambda j: _etabli_plaque_path(j, v),\n                                   \"plan de plaque\")",
     "    return _etabli_plaque_path(job, v)",
     ["PLAN_DE_PLAQUE"]),
]


def rouges(k):
    """Les tests rouges du banc ciblé — et si RIEN n'a tourné, on le dit.

    pytest sort 0 (tout vert) ou 1 (des rouges) quand il a tourné ; 2, 3, 4
    ou 5 quand la COLLECTE a cassé (une erreur de syntaxe dans routes.py, un
    import qui lève) ou qu'aucun test ne correspond. Lue comme « aucun
    FAILED », une collecte cassée passerait pour une mutation VERTE alors
    que rien n'a été mesuré. On lit donc le code de sortie et les lignes
    `ERROR`, et l'on rend un troisième état.
    """
    r = subprocess.run([PY, "-m", "pytest", BANC, "-q", "--no-header",
                        "-p", "no:warnings", "-k", k],
                       capture_output=True, cwd=R / "backend", timeout=900)
    txt = r.stdout.decode("utf-8", "replace")
    erreur = (r.returncode not in (0, 1)
              or bool(re.search(r"^ERROR ", txt, re.M)))
    return set(re.findall(r"^FAILED [^:]+::(\w+)", txt, re.M)), txt, erreur


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (rel, old, new, attendus) in enumerate(M):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        src = p.read_bytes()
        brut = src.decode("utf-8")
        # les fichiers de l'arbre sont en CRLF (autocrlf) : on apparie en LF et
        # l'on reecrit avec la fin de ligne du fichier ; la remise se fait a
        # l'octet pres depuis `src`.
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        # une mutation est UN remplacement, ou une LISTE de remplacements
        # appliqués dans l'ordre (quand on déplace un appel, il faut l'ôter
        # d'un endroit et le poser à un autre)
        paires = old if isinstance(old, list) else [(old, new)]
        for o, n_ in paires:
            assert txt.count(o) == 1, (i, rel, txt.count(o), o[:60])
            txt = txt.replace(o, n_)
        sha_avant = hashlib.sha256(src).hexdigest()
        p.write_bytes(txt.replace("\n", eol).encode("utf-8"))
        try:
            k = " or ".join(attendus) if attendus else \
                "AIMANTATION or FLECHES or DEPLACE_par or ROTATION_tourne or applique_le_PLAN"
            rg, sortie, erreur = rouges(k)
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        manquants = [a for a in attendus if not any(a in n for n in rg)]
        if erreur:
            verdict = "ERREUR(collecte)"
            print(sortie[-1200:], file=sys.stderr)
        elif attendus:
            verdict = "ROUGE" if not manquants else ("VERTE" if not rg else "ROUGE(autres)")
        else:
            verdict = "VERTE(attendue)" if not rg else "ROUGE(inattendu)"
        bilan.append((i, rel, verdict, sorted(rg), manquants))
        apercu = paires[0][0].strip()[:50]
        print(f"[{i:2d}] {verdict:16s} {rel:30s} {apercu!r} -> {sorted(rg)}"
              f"  sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
    print(json.dumps([b[:3] for b in bilan], ensure_ascii=False))


if __name__ == "__main__":
    main()
