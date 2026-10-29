"""t376 (lot « Game Assets : finitions », 29/10/2026) — 3D : T-pose ou A-pose, règle D6 dans le 3D Studio.

La liste `pose_mode` de Meshy (a-pose / t-pose / libre) existait déjà ; elle reçoit la règle D6 du plan : grisée et
mise à « libre » quand le sujet n'est pas un personnage (prompt tapé ou classification vision de l'image, une fois),
raison affichée, avertissement en cas de doute. Le travail vit dans /shared/dz-pose3d.js (dictionnaire pose3d.json) ;
studio3d.js (GÉNÉRÉ par L9) ne reçoit qu'UN crochet, sans texte affiché : après le rendu de la modale « preview »,
window.__dzPose3d.monterSelect sur #f-pose, avec le prompt quand la source est le texte et l'image choisie.
"""
from outils import S

SJ = "studio3d/studio3d.js"

ENTREES = [
    S(SJ, 878, "  body.innerHTML = html;\r\n",
      "  body.innerHTML = html;\r\n"
      "  /* t376 : règle D6 (personnage ou non) sur la pose Meshy — /shared/dz-pose3d.js */\r\n"
      "  if (id === \"preview\" && window.__dzPose3d) window.__dzPose3d.monterSelect(body.querySelector(\"#f-pose\"), "
      "{ engine: \"meshy\", multiview: true, subject: c.source === \"text\" ? c.prompt : \"\", image: c.imageName || \"\" });\r\n",
      {}),
]
