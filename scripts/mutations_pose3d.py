# -*- coding: utf-8 -*-
"""Mutations t376 (29/10/2026) : le choix de pose de la génération 3D (pose3d, asset3d_service, routes, maillon
patch_bundle_dzpose, /shared/dz-pose3d.js, dictionnaire pose3d.json, crochet L9 du 3D Studio). Chaque mutation doit
faire ÉCHOUER son banc : backend/tests/test_pose3d.py (serveur) ou backend/tests/test_pose3d_ecran.py (écran, qui
joue aussi frontend/shared/qa/pose3d.test.mjs). Les fichiers sont copiés AVANT, restaurés après chaque mutation et
comparés octet à octet à la fin (le bundle compris).
Run (depuis la racine) : & $PY scripts/mutations_pose3d.py"""
import filecmp, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[1]
SAUVE = pathlib.Path(tempfile.mkdtemp(prefix="mut_pose3d_"))
F = {"pose": RACINE / "backend/app/services/pose3d.py", "a3": RACINE / "backend/app/services/asset3d_service.py",
     "routes": RACINE / "backend/app/api/routes.py", "proutes": RACINE / "backend/app/api/pose3d_routes.py",
     "bundle": RACINE / "frontend/dist/assets/index-BEOJX8L5.js", "js": RACINE / "frontend/shared/dz-pose3d.js",
     "jsd": RACINE / "frontend/dist/shared/dz-pose3d.js", "dico": RACINE / "frontend/shared/i18n/pose3d.json",
     "aide": RACINE / "backend/tests/_i18n_l1_aide.py", "maillon": RACINE / "scripts/patch_bundle_dzpose.py",
     "sj": RACINE / "frontend/studio3d/studio3d.js", "s3html": RACINE / "frontend/studio3d/index.html"}
for k, p in F.items(): shutil.copy2(p, SAUVE / (k + ".orig"))
SERVEUR = [sys.executable, "backend/tests/test_pose3d.py"]
ECRAN = [sys.executable, "backend/tests/test_pose3d_ecran.py"]
M = [
 # ── serveur : détection D6 ──
 ("pose", SERVEUR, "    if any(_dans(m, PERSONNAGES) for m in mots):\r\n        return \"personnage\"\r\n    if any(_dans(m, DOUTES) for m in mots):",
  "    if any(_dans(m, DOUTES) for m in mots):\r\n        return \"doute\"\r\n    if any(_dans(m, PERSONNAGES) for m in mots):"),
 ("pose", SERVEUR, "    return \"doute\"\r\n\r\n\r\n# ── pose demandée", "    return \"objet\"\r\n\r\n\r\n# ── pose demandée"),
 ("pose", SERVEUR, "    if mot in lexique:\r\n        return True\r\n", "    if any(mot in x for x in lexique):\r\n        return True\r\n"),
 ("pose", SERVEUR, 'for fin in ("es", "s", "x"):', 'for fin in ():'),
 ("pose", SERVEUR, "_sans_accents(str(sujet or \"\")).lower()", "str(sujet or \"\").lower()"),
 # ── serveur : normalisation et modes ──
 ("pose", SERVEUR, '        return "t-pose" if payload.get("tpose") else ""', '        return "t-pose"'),
 ("pose", SERVEUR, '        if v in ("aucune", "none", "libre"):', '        if v in ("aucune",):'),
 ("pose", SERVEUR, 'MODES = {"rodin": "moteur", "tripo": "vues", "tripo-h3.1": "vues", "meshy": "moteur"}',
  'MODES = {"rodin": "moteur", "tripo": "vues", "tripo-h3.1": "vues", "meshy": "moteur", "trellis": "vues"}'),
 ("pose", SERVEUR, '    elif mode == "vues" and not multiview:', '    elif mode == "vues" and False:'),
 ("pose", SERVEUR, '    if "personnage" in classes:', '    if texte == "personnage":'),
 ("pose", SERVEUR, '"avertissement": "doute" if (not raison and s == "doute") else "",', '"avertissement": "",'),
 ("pose", SERVEUR, '    if e["raison"] == "objet":\r\n        raise', '    if False:\r\n        raise'),
 # ── serveur : vision ──
 ("pose", SERVEUR, '    if isinstance(connu, dict) and connu.get("classe"):', '    if False:'),
 ("pose", SERVEUR, "    if cout > mx + EPS_USD:", "    if False:"),
 ("pose", SERVEUR, "    await asyncio.to_thread(_ecrire_cache, cle, classe, modele or \"\")\r\n", ""),
 ("pose", SERVEUR, 'CATEGORIE = "moteurs3d"', 'CATEGORIE = "atelier"'),
 ("pose", SERVEUR, "        if mots and mots[0] == c:", "        if c in mots:"),
 ("proutes", SERVEUR, '    if P.classe_vision(image) is None and (body or {}).get("confirme_cout") is not True:',
  '    if False:'),
 # ── serveur : transmission ──
 ("a3", SERVEUR, '    angles = ["front view"] + _ANGLES[1:]', '    angles = _ANGLES'),
 ("a3", SERVEUR, '    return [f"{subj}, {a}, {ph + \', \' if ph else \'\'}{_CADRAGE}" for a in angles[:n]]',
  '    return [f"{subj}, {a}, {ph + \', \' if (ph and a == angles[0]) else \'\'}{_CADRAGE}" for a in angles[:n]]'),
 ("a3", SERVEUR, '            a["prompt"] = pose3d.phrase(pose)', '            a["prompt"] = pose3d.phrase("t-pose")'),
 ("a3", SERVEUR, '"TAPose": bool(pose), "use_original_alpha"', '"TAPose": bool(opts.get("tpose")), "use_original_alpha"'),
 ("a3", SERVEUR, 'enumerate(view_prompts(_nv, payload.get("subject", ""), pose_de(payload)), 1)',
  'enumerate(view_prompts(_nv, payload.get("subject", "")), 1)'),
 ("a3", SERVEUR, '        "pose": base_opts["pose"] or "",\r\n', ''),
 ("routes", SERVEUR, "    _pose_ou_400(body, engine)   # t376", "    pass   # t376"),
 ("routes", SERVEUR, '    _pose_ou_400({**body, "multiview": True}, engine)', '    pass'),
 ("routes", SERVEUR, '                    "pose": _pose3d.mode_moteur(eid),', ''),
 # ── écran : bundle ──
 ("bundle", ECRAN, 'var on=val===o[0],off=!actif&&o[0]!=="";', 'var on=val===o[0],off=!actif;'),
 ("bundle", ECRAN, 'onClick:function(){if(!off)set("pose",o[0])}', 'onClick:function(){set("pose",o[0])}'),
 ("bundle", ECRAN, 'title:off?tx.raison:o[2]', 'title:o[2]'),
 ("bundle", ECRAN, 'val=actif?(p.pose||""):"",', 'val=p.pose||"",'),
 ("bundle", ECRAN, 'color:(!tx.raison&&tx.avertissement)?"var(--amber)":"var(--ink-soft)"', 'color:"var(--ink-soft)"'),
 ("bundle", ECRAN, '(P&&e&&e.vision_proposee)?', '(P&&e)?'),
 ("bundle", ECRAN, 'onClick:function(){P.classer(q,maj)}', 'onClick:function(){P.classer({},maj)}'),
 ("bundle", ECRAN, 'body:JSON.stringify(window.__dzPose3d?window.__dzPose3d.corps(p):p)', 'body:JSON.stringify(p)'),
 ("bundle", ECRAN, 'textures:!0,pose:"",formats:["glb"]}),p=PP[0]', 'textures:!0,tpose:!1,formats:["glb"]}),p=PP[0]'),
 ("bundle", ECRAN, 'r.jsx(O,{label:dzT("pose3d.choix.champ"),', 'r.jsx(O,{label:"Pose",'),
 ("bundle", ECRAN, 'r.jsx("div",{role:"radiogroup","aria-label":dzT("pose3d.choix.champ")', 'r.jsx("div",{"aria-label":dzT("pose3d.choix.champ")'),
 # ── écran : module partagé ──
 ("js", ECRAN, "    if (!b.pose || !e || !e.actif) b.pose = \"\";", "    if (!b.pose) b.pose = \"\";"),
 ("js", ECRAN, "    delete b.tpose;\r\n", ""),
 ("js", ECRAN, "}, 250);", "}, 0);"),
 ("js", ECRAN, "    return exact ? null : (DERNIER[q.engine || \"\"] || null);", "    return DERNIER[q.engine || \"\"] || null;"),
 ("js", ECRAN, "          if (!oui) return null;", "          if (oui === 2) return null;"),
 ("js", ECRAN, "confirme_cout: true, max_usd: usd,", "confirme_cout: true, max_usd: 1,"),
 ("js", ECRAN, "      if (!e.actif) sel.value = \"\";", ""),
 ("js", ECRAN, "      sel.disabled = !e.actif;", "      sel.disabled = false;"),
 ("js", ECRAN, 'if (e.actif && e.mode === "moteur" && moteur === "rodin") o.precision', 'if (e.actif && e.mode === "moteur") o.precision'),
 ("jsd", ECRAN, "    delete b.tpose;\r\n", ""),
 # ── écran : dictionnaire, inverse, maillon, 3D Studio ──
 ("dico", ECRAN, '"en": "None"}', '"en": "Aucune"}'),
 ("dico", ECRAN, '  "pose3d.raison.vues"', '  "pose3d.raison.vuesX"'),
 ("aide", ECRAN, "    bundle = avant_dzpose(bundle)                # 29/10 (t376)", "    # 29/10 (t376)"),
 ("maillon", ECRAN, '("dzecartes", "/*dzecartes*/", 1),', '("dzcurseur", "/*dzcurseur*/", 1),'),
 ("sj", ECRAN, 'subject: c.source === "text" ? c.prompt : ""', 'subject: c.prompt'),
 ("sj", ECRAN, 'if (id === "preview" && window.__dzPose3d)', 'if (window.__dzPose3d)'),
 ("s3html", ECRAN, '<script src="/shared/dz-pose3d.js"></script>\r\n', ''),
]
tues = 0
try:
  for i, (k, banc, a, b) in enumerate(M, 1):
    p = F[k]; s = p.read_bytes().decode("utf-8")
    assert s.count(a) == 1, (i, a, s.count(a))
    p.write_bytes(s.replace(a, b).encode("utf-8"))
    r = subprocess.run(banc, cwd=RACINE / "backend" if banc is SERVEUR else RACINE, capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}) if banc is ECRAN else \
        subprocess.run([sys.executable, "tests/test_pose3d.py"], cwd=RACINE / "backend", capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    for k2, p2 in F.items(): shutil.copy2(SAUVE / (k2 + ".orig"), p2)
    ok = r.returncode != 0; tues += ok
    print(("TUÉE   " if ok else "SURVIT ") + f"M{i} {k}: {a[:70]!r}", flush=True)
finally:
  for k, p in F.items(): shutil.copy2(SAUVE / (k + ".orig"), p)
  print("restauré, identique :", all(filecmp.cmp(SAUVE / (k + ".orig"), p, shallow=False) for k, p in F.items()))
print(f"{tues}/{len(M)} mutations tuées")
sys.exit(0 if tues == len(M) else 1)
