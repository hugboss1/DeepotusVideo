"""t344 (lot Scenario, B9, 29/10/2026) — « Comparer les moteurs » : un lien de plus dans le rail du 3D Studio.

La page du banc (comparer.html, comparer.js, comparer_calc.js) est à part et se traduit par son propre dictionnaire
(frontend/shared/i18n/comparatif3d.json, dzT). index.html n'est jamais réécrit par L9 : le texte et l'infobulle du
lien sont traduits par la surcouche (entrées H).
Demande de l'utilisateur (même lot) : vignettes des nœuds du graphe Meshy et aperçu agrandi — le travail vit dans un
module à part (graphe_vues.js, dictionnaire studio3dvues.json) ; studio3d.js ne reçoit que TROIS crochets, sans texte
affiché : l'état exposé (window.__dzStudio3d = { S, NODES }), l'évènement « studio3d:peint » au début de
renderPreview, et le modèle du nœud cliqué (window.__dzApercuNoeud) préféré au dernier modèle dans l'aperçu.
"""
from outils import H, S

SJ = "studio3d/studio3d.js"

ENTREES = [
    S(SJ, 122, "  libImages: null, pickedImage: null,\r\n};",
      "  libImages: null, pickedImage: null,\r\n};\r\n"
      "/* t344 : l'état, lu par graphe_vues.js (vignettes des nœuds, aperçu agrandi) — lecture seule */\r\n"
      "window.__dzStudio3d = { S, NODES };", {}),
    S(SJ, 668, "function renderPreview() {\r\n",
      "function renderPreview() {\r\n"
      "  document.dispatchEvent(new CustomEvent(\"studio3d:peint\"));   // t344 : les vignettes suivent chaque rendu\r\n",
      {}),
    S(SJ, 673, "  let glb = S.run?.outputs?.modelUrls?.glb;",
      "  /* t344 : le modèle du nœud cliqué (graphe_vues.js), sinon le dernier, comme avant */\r\n"
      "  let glb = (typeof window.__dzApercuNoeud === \"function\" && window.__dzApercuNoeud()) "
      "|| S.run?.outputs?.modelUrls?.glb;", {}),
    H("studio3d.t344_h.comparer", "Comparer les moteurs", "Compare engines"),
    H("studio3d.t344_h.comparer_aide",
      "Une image, plusieurs moteurs, le même éclairage : triangles, arêtes ouvertes, temps et coût côte à côte",
      "One image, several engines, the same lighting: triangles, open edges, time and cost side by side"),
]
