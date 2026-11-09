"""t484 (09/11/2026, demande de l'utilisateur) — changement FONCTIONNEL de lib3d/viewer.js posé APRÈS L9 :
le sol du repère (trame, axes, marques) se pose sous le BAS du modèle (api.sol, relevé par cadrer) et non plus à
y = 0, où un GLB centré sur son origine avait la moitié basse sous la grille. Le modèle n'est pas déplacé : les
outils (Affiner, Rig, Établi) prennent les points de la scène pour des coordonnées du fichier.
La table réversible L9 exige : source du poste == base 7f99c72c + éditions ; d'où cette saisie (comme trame.py).
Banc : backend/tests/test_sol_3d.py. Aucun texte affiché."""
from outils import S

V = "lib3d/viewer.js"

ENTREES = [
    S(V, 149, '  api.scene.remove(api.racine);\r\n  api.racine = null;',
      "  api.scene.remove(api.racine);\r\n  api.racine = null;\r\n  api.sol = 0;            /* t484 : plus de modèle, le sol revient à l'origine (voir cadrer) */", {}),
    S(V, 1120, '  const centre = boite.getCenter(new THREE.Vector3());',
      "  const centre = boite.getCenter(new THREE.Vector3());\r\n  /* t484 — LE SOL EST SOUS LE MODÈLE, PAS À SON CENTRE. Un GLB dont l'origine est au milieu (cas courant des\r\n     moteurs de génération et des imports) avait la moitié basse sous la grille. On ne DÉPLACE PAS le modèle :\r\n     le pinceau d'Affiner, les jointures du Rig, les mesures et coupes de l'Établi prennent les points de la\r\n     scène pour des coordonnées du fichier, et un décalage les fausserait tous. C'est la grille et les axes\r\n     (majRepere) qui se posent à la hauteur du bas du modèle ; les coordonnées restent celles du fichier. */\r\n  api.sol = Number.isFinite(boite.min.y) ? boite.min.y : 0;", {}),
    S(V, 687, '  if (e.pas === pas && e.cases === cases && e.plan === plan) return e;',
      '  /* t484 : la trame et les axes se posent sur le SOL du modèle (api.sol, relevé par cadrer). Repositionnés à\r\n     CHAQUE appel, avant le mémo : un nouveau modèle de même échelle garde (pas, cases, plan) mais pas sa hauteur. */\r\n  const sol = Number.isFinite(api.sol) ? api.sol : 0;\r\n  e.sol = sol;\r\n  if (e.trame) e.trame.position.y = sol;\r\n  if (e.axes) e.axes.position.y = sol;\r\n  if (e.pas === pas && e.cases === cases && e.plan === plan) return e;', {}),
    S(V, 707, '  e.axes = construireAxes(cases * pas);',
      '  e.axes = construireAxes(cases * pas);\r\n  e.trame.position.y = sol;\r\n  e.axes.position.y = sol;', {}),
    S(V, 756, '  const normale = e.plan;',
      "  const normale = e.plan;\r\n  /* t484 : l'origine du repère est posée sur le sol du modèle (voir cadrer et majRepere) */\r\n  const zero = { x: 0, y: Number.isFinite(e.sol) ? e.sol : 0, z: 0 };", {}),
    S(V, 762, '    pied[normale] = 0;',
      '    pied[normale] = zero[normale];', {}),
    S(V, 764, '    jambe[a1] = 0;',
      '    jambe[a1] = zero[a1];', {}),
    S(V, 767, '    pousser(jambe, { x: 0, y: 0, z: 0 }, COULEUR_AXE[a2]);',
      '    pousser(jambe, zero, COULEUR_AXE[a2]);', {}),
]
