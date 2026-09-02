"""Banc de mutations du lot B de la plaque façon slicer — l'assise et le couteau.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance À LA MAIN, depuis backend/ :

    python tests/mutations_assise_couteau.py          # toutes
    python tests/mutations_assise_couteau.py 3 17     # celles-là

Même modèle que mutations_plaque_slicer.py (le lot A), avec une colonne de
plus : le BANC visé — la géométrie (assise, couteau, routes) vit dans
test_etabli_socle.py, la page dans test_etabli_canevas.py, et les deux ne se
lancent jamais dans le même processus (run-tests.ps1 dit pourquoi : chaque
banc fige `app.config` avec son propre environnement).

Il MUTE les sources du dépôt une à une et les REMET à l'octet près (assertion
sur le sha256, journalisé), donc il ne se lance pas pendant qu'un autre banc
lit ces fichiers. Chaque mutation nomme les tests qu'elle doit faire rougir ;
une « VERTE » est une assertion qui manque, un « ERREUR(collecte) » un banc qui
n'a pas tourné (code de sortie 2 à 5, ou une ligne ERROR).

Chaque mutation : (fichier, ancien, nouveau, banc, tests attendus rouges).
`ancien` peut être une LISTE de (ancien, nouveau) appliqués dans l'ordre.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
SOCLE = "tests/test_etabli_socle.py"
CANEVAS = "tests/test_etabli_canevas.py"
ME = "backend/app/services/mesh_edit.py"
RT = "backend/app/api/routes.py"
JS = "frontend/etabli/etabli.js"

M = [
    # ── mesh_edit : le capuchon ──────────────────────────────────────────────
    # 0. le capuchon du côté a n'est plus retourné : ses arêtes vont dans le
    #    même sens que la paroi, la moitié n'est plus fermée
    (ME, "            if inverser:\n                j, k = k, j\n", "",
     SOCLE, ["FERMEES"]),
    # 1. « oublie le capuchon » : les triangles ne sont jamais ajoutés
    (ME, "            if tris_cap:\n                base = [c0.sommet_neuf([",
     "            if False:\n                base = [c0.sommet_neuf([",
     SOCLE, ["FERMEES", "garder_a_ou_b"]),
    # 2. l'interpolation repart de l'index et non de la position : la section
    #    ne se recoud plus à travers les coutures UV
    (ME, "            i0, j0 = (cle if pos[cle[0]] <= pos[cle[1]] else (cle[1], cle[0]))",
     "            i0, j0 = cle",
     SOCLE, ["FERMEES"]),
    # 3. la normale du plan est « tournée » au lieu d'être transposée : faux
    #    sous l'échelle non uniforme de la boîte
    (ME, "    nl = tuple(m[c * 4] * normale[0] + m[c * 4 + 1] * normale[1]\n"
         "               + m[c * 4 + 2] * normale[2] for c in range(3))",
     "    nl = tuple(normale)",
     SOCLE, ["FERMEES"]),
    # 4. l'orientation du capuchon jugée constante
    (ME, "    inverser = (vers[0] * n_unit[0] + vers[1] * n_unit[1]\n"
         "                + vers[2] * n_unit[2]) < 0",
     "    inverser = False",
     SOCLE, ["FERMEES"]),
    # 5. une oreille plate ne pose plus son triangle : jonction en T
    (ME, "        tris.append((ip, i, inx))\n        del idx[k]",
     "        if abs(croix(ip, i, inx)) > eps:\n            tris.append((ip, i, inx))\n        del idx[k]",
     SOCLE, ["triangulation_par_oreilles"]),
    # 6. les boucles imbriquées ne sont plus vues : le trou serait bouché
    (ME, "            if i != j and _dedans_polygone(bj[0], bi):", "            if False:",
     SOCLE, ["boucles_imbriquees"]),
    # 7. un plan qui ne traverse rien écrit quand même une version
    (ME, "    if not traversee:\n        raise ValueError(\"le plan ne traverse aucune des pièces retenues — \"\n"
         "                         \"rien à couper\")\n", "",
     SOCLE, ["ne_sait_pas_couper", "route_couper"]),
    # 8. une pièce entière du côté écarté est gardée quand même
    (ME, "            produits[i] = [i] if garde else []", "            produits[i] = [i]",
     SOCLE, ["ne_sait_pas_couper"]),
    # ── mesh_edit : l'assise ────────────────────────────────────────────────
    # 9. pas de translation de contact
    (ME, "    t[1] -= ymin\n", "", SOCLE, ["assise_pose_la_face", "deux_assises_EMPILENT", "route_assise"]),
    # 10. pas de pivot : la rotation se fait autour de l'origine
    (ME, "    t = [c[0] - rc[0], c[1] - rc[1], c[2] - rc[2]]", "    t = [0.0, 0.0, 0.0]",
     SOCLE, ["assise_pose_la_face"]),
    # 11. deux vecteurs opposés rendent l'identité
    (ME, "        if c > 0:\n            return _I3\n", "        return _I3\n",
     SOCLE, ["rodrigues"]),
    # ── routes ───────────────────────────────────────────────────────────────
    # 12. la version n'est plus jugée : « 1 » (chaîne) fait un 500
    (RT, "    if not _etabli_entier(version) or version < 1:\n"
         "        raise HTTPException(400, f\"{quoi} : version « {version} » — un entier \"\n"
         "                                 \"à partir de 1\")\n", "",
     SOCLE, ["route_assise", "route_couper"]),
    # 13. les deux gardes de chemin sautent : « .. » n'est plus un 400
    (RT, "    p = _etabli_cible_sous_jobs(\n        job, lambda j: mesh_report.job_dir(Path(str(j)).name) / nom, quoi)",
     "    p = mesh_report.job_dir(Path(str(job)).name) / nom",
     SOCLE, ["route_assise", "route_couper"]),
    # 14. une normale nulle n'est plus refusée par la route (le socle la
    #     refuse encore, mais avec son propre mot)
    (RT, "    if direction and all(c == 0 for c in v):", "    if False:",
     SOCLE, ["route_couper"]),
    # 15. le compte rendu du couteau n'est plus écrit dans la fiche
    (RT, "    return _etabli_ecrire(job, sortie, \"couper\", rapport)",
     "    return _etabli_ecrire(job, sortie, \"couper\", {})",
     SOCLE, ["route_couper"]),
    # ── etabli.js : le propriétaire du pointeur ─────────────────────────────
    # 16. quitter le couteau ne le range plus
    (JS, "  if (GESTE.mode === \"couteau\" && mode !== \"couteau\") rangerCouteau();\n", "",
     CANEVAS, ["UN_SEUL_proprietaire"]),
    # 17. le clic désigne encore sous le couteau
    (JS, "    if (GESTE.mode === \"couteau\") return;\n    if (GESTE.mode === \"assise\") { poserSurFace(obj, touche); return; }\n",
     "    if (GESTE.mode === \"assise\") { poserSurFace(obj, touche); return; }\n",
     CANEVAS, ["UN_SEUL_proprietaire"]),
    # 18. le geste en cours survit au changement de mode
    (JS, "  GESTE.mode = mode;\n  GESTE.enCours = null;", "  GESTE.mode = mode;",
     CANEVAS, ["UN_SEUL_proprietaire"]),
    # 19. le glisser saisit sans consulter le propriétaire
    (JS, "    if (ev.button !== 0 || GESTE.mode !== \"glisser\") return;",
     "    if (ev.button !== 0) return;",
     CANEVAS, ["UN_SEUL_proprietaire"]),
    # 20. le gizmo met le plan de coupe en file comme un nœud
    (JS, "      if (o && o === COUTEAU.plan) { majApercuCoupe(); return; }\n", "",
     CANEVAS, ["UN_SEUL_proprietaire"]),
    # 21. la plaque n'annonce plus qu'elle prend le pointeur
    (JS, "  armerGeste(\"glisser\");\n  PLQ.pieces = etalement.pieces;", "  PLQ.pieces = etalement.pieces;",
     CANEVAS, ["UN_SEUL_proprietaire"]),
    # ── etabli.js : l'assise ────────────────────────────────────────────────
    # 22. l'assise passe AVANT le déplacement : elle lirait une géométrie que
    #     transformer va déplacer (revue : min Y = +0,508)
    (JS, "const ORDRE_ECRITURE = [\"transformer\", \"assise\", \"reparer\", \"extraire\", \"couper\"];",
     "const ORDRE_ECRITURE = [\"assise\", \"transformer\", \"reparer\", \"extraire\", \"couper\"];",
     CANEVAS, ["MET_EN_ATTENTE", "AU_SOL"]),
    # 23. le mode ne retombe pas après la face cliquée
    (JS, "  noterAttente(\"assise\", { normale: [n.x, n.y, n.z], point: [p.x, p.y, p.z] });\n  armerGeste(\"selection\");\n",
     "  noterAttente(\"assise\", { normale: [n.x, n.y, n.z], point: [p.x, p.y, p.z] });\n",
     CANEVAS, ["MET_EN_ATTENTE"]),
    # 24. selection.js tourne la normale par le quaternion : fausse sous une
    #     échelle non uniforme
    ("frontend/lib3d/selection.js",
     "        .applyNormalMatrix(_matN.getNormalMatrix(h.object.matrixWorld)).normalize()",
     "        .applyQuaternion(h.object.getWorldQuaternion(new THREE.Quaternion())).normalize()",
     CANEVAS, ["NORMALE_MONDE"]),
    # ── etabli.js : le couteau ──────────────────────────────────────────────
    # 25. la coupe part sur une file pleine
    (JS, "  if (S.enAttente.length) {\n    direRefus(`${S.enAttente.length} modification(s) en attente — écris d'abord `",
     "  if (false) {\n    direRefus(`${S.enAttente.length} modification(s) en attente — écris d'abord `",
     CANEVAS, ["REFUSE_sans_piece"]),
    # 26. le couteau s'arme sans rien de retenu
    (JS, "  if (!noeuds.length) {\n    direRefus(\"aucune pièce retenue — cochez dans Parties ce que le couteau \"",
     "  if (false) {\n    direRefus(\"aucune pièce retenue — cochez dans Parties ce que le couteau \"",
     CANEVAS, ["apercu_du_couteau"]),
    # 27. les deux plans de découpe regardent du même côté
    (JS, "  COUTEAU.planB.setFromNormalAndCoplanarPoint(n.clone().negate(),\n"
         "                                              p.clone().addScaledVector(n, -demi));",
     "  COUTEAU.planB.setFromNormalAndCoplanarPoint(n,\n"
         "                                              p.clone().addScaledVector(n, -demi));",
     CANEVAS, ["apercu_du_couteau"]),
    # 28. les clones ne sont pas posés au monde
    (JS, "      c.matrix.copy(m.matrixWorld);\n", "", CANEVAS, ["apercu_du_couteau"]),
    # 29. les originaux restent visibles sous l'aperçu
    (JS, "    COUTEAU.originaux.push({ objet: m, visible: m.visible });\n    m.visible = false;",
     "    COUTEAU.originaux.push({ objet: m, visible: m.visible });",
     CANEVAS, ["apercu_du_couteau"]),
    # 30. les originaux ne retrouvent pas leur visibilité au rangement
    (JS, "  for (const { objet, visible } of COUTEAU.originaux) objet.visible = visible;\n", "",
     CANEVAS, ["apercu_du_couteau"]),
    # ── la page : boutons et clavier ────────────────────────────────────────
    # 31. la barre du couteau naît visible
    ("frontend/etabli/index.html",
     "<span class=\"outil-couteau hidden\" id=\"couteauBarre\">",
     "<span class=\"outil-couteau\" id=\"couteauBarre\">",
     CANEVAS, ["outils_vivent"]),
    # 32. Ctrl+F arme l'assise au lieu de laisser la recherche du navigateur
    (JS, "  if (ev.ctrlKey || ev.metaKey || ev.altKey) return false;\n  const t = ev.target;\n"
         "  if (t && (t.isContentEditable\n            || /^(INPUT|TEXTAREA|SELECT)$/i.test(t.tagName || \"\"))) return false;\n"
         "  const k = String(ev.key || \"\");",
     "  const t = ev.target;\n"
         "  if (t && (t.isContentEditable\n            || /^(INPUT|TEXTAREA|SELECT)$/i.test(t.tagName || \"\"))) return false;\n"
         "  const k = String(ev.key || \"\");",
     CANEVAS, ["outils_vivent"]),
    # 33. la coupe refusée par le serveur reste dans la file
    (JS, "    if (i >= 0) S.enAttente.splice(i, 1);\n", "", CANEVAS, ["REFUSE_sans_piece"]),
    # ── revue du lot B ─────────────────────────────────────────────────────
    # 34. une boucle non triangulable est SAUTÉE : pose reste vrai, triangles
    #     manquants en silence (la mutation verte du relecteur)
    (ME, '        t = _trianguler(b2)\n        if t is None:',
     '        t = _trianguler(b2)\n        if t is None:\n            continue\n        if False:',
     SOCLE, ["boucles_imbriquees"]),
    # 35. l'aperçu visite deux fois les maillages d'un retenu contenu dans un
    #     autre : six clones, et l'original reste caché
    (JS, [('  const maillages = new Set();', '  const maillages = [];'),
          ('maillages.add(m)', 'maillages.push(m)')],
     None, CANEVAS, ["apercu_du_couteau"]),
    # 36. « annuler » reste actif pendant l'écriture
    (JS, '    <button id="btnAnnuler"${_ecritEnCours ? " disabled" : ""}>annuler</button>`;',
     '    <button id="btnAnnuler">annuler</button>`;',
     CANEVAS, ["REFUSE_sans_piece"]),
    # 37. les triangles plats du capuchon ne sont plus dits
    (ME, '                           "degeneres": degeneres}',
     '                           "degeneres": 0}',
     SOCLE, ["boucles_imbriquees"]),
]


def rouges(banc, k):
    """Les tests rouges du banc ciblé — et si RIEN n'a tourné, on le dit
    (troisième état, voir mutations_plaque_slicer.rouges)."""
    r = subprocess.run([PY, "-m", "pytest", banc, "-q", "--no-header",
                        "-p", "no:warnings", "-k", k],
                       capture_output=True, cwd=R / "backend", timeout=900)
    txt = r.stdout.decode("utf-8", "replace")
    erreur = (r.returncode not in (0, 1)
              or bool(re.search(r"^ERROR ", txt, re.M)))
    return set(re.findall(r"^FAILED [^:]+::(\w+)", txt, re.M)), txt, erreur


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (rel, old, new, banc, attendus) in enumerate(M):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        src = p.read_bytes()
        brut = src.decode("utf-8")
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        paires = old if isinstance(old, list) else [(old, new)]
        for o, n_ in paires:
            assert txt.count(o) == 1, (i, rel, txt.count(o), o[:60])
            txt = txt.replace(o, n_)
        sha_avant = hashlib.sha256(src).hexdigest()
        p.write_bytes(txt.replace("\n", eol).encode("utf-8"))
        try:
            rg, sortie, erreur = rouges(banc, " or ".join(attendus))
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        manquants = [a for a in attendus if not any(a in n for n in rg)]
        if erreur:
            verdict = "ERREUR(collecte)"
            print(sortie[-1200:], file=sys.stderr)
        else:
            verdict = "ROUGE" if not manquants else ("VERTE" if not rg else "ROUGE(autres)")
        bilan.append((i, rel, verdict, sorted(rg), manquants))
        apercu = paires[0][0].strip()[:50]
        print(f"[{i:2d}] {verdict:16s} {rel:34s} {apercu!r} -> {sorted(rg)}"
              f"  sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
    print(json.dumps([b[:3] for b in bilan], ensure_ascii=False))


if __name__ == "__main__":
    main()
