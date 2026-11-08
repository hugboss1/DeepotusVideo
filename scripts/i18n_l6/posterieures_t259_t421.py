"""Évolutions postérieures à L6 de deux modules de BASE, consignées ici en éditions S pour que la table reste
réversible (test_i18n_l6 [2]) et que --check reproduise exactement les sources actuelles :
- js/mod-didact.js (t259, a55a58f8) : didact_position — l'encart d'une option DANS un menu se pose à côté du menu ;
- js/mod-envoi.js (t421, #523) : un nom d'image refusé est dit (toast commun.envoi.refuse, clé du dictionnaire commun,
  pas de clé vectorlab neuve) et rien n'est ouvert."""
from outils import L, S, X, H  # noqa: F401

DIDACT = "js/mod-didact.js"
ENVOI = "js/mod-envoi.js"

ENTREES = [
    S(DIDACT, 53, "/* ── DOM ── */",
      "// t259 : la position de l'encart. Une option DANS un menu (flyout du Photolab) le reçoit à CÔTÉ du menu — "
      "dessous, il\r\n"
      "// couvrirait les lignes suivantes que l'utilisateur veut encore survoler ; ailleurs, la position de la bulle "
      "courte.\r\n"
      "export function didact_position(el, menu, taille, fenetre, marge = 8) {\r\n"
      "  if (!menu) return bulle_position(el, taille, fenetre, marge);\r\n"
      "  let x = menu.x + menu.w + marge;\r\n"
      "  if (x + taille.w > fenetre.w - marge) x = Math.max(marge, menu.x - marge - taille.w);\r\n"
      "  const y = Math.max(marge, Math.min(fenetre.h - marge - taille.h, el.y));\r\n"
      "  return { x, y, dessous: false };\r\n"
      "}\r\n"
      "\r\n"
      "/* ── DOM ── */", {}),
    S(DIDACT, 69,
      "const r = el.getBoundingClientRect();\r\n"
      "    const p = bulle_position({ x: r.left, y: r.top, w: r.width, h: r.height }, "
      "{ w: encart.offsetWidth, h: encart.offsetHeight },\r\n"
      "                             { w: window.innerWidth, h: window.innerHeight }, 8);",
      "const r = el.getBoundingClientRect(), m = el.closest('[role=\"menu\"]'), "
      "rm = m ? m.getBoundingClientRect() : null;\r\n"
      "    const p = didact_position({ x: r.left, y: r.top, w: r.width, h: r.height }, "
      "rm && { x: rm.left, y: rm.top, w: rm.width, h: rm.height },\r\n"
      "                              { w: encart.offsetWidth, h: encart.offsetHeight }, "
      "{ w: window.innerWidth, h: window.innerHeight }, 8);", {}),
    S(ENVOI, 47, "if (!r) return false;",
      "if (!r) return false;\r\n"
      "    if (r.refus) { VL.toast(T(\"commun.envoi.refuse\", { nom: r.refus }), true); return false; }     "
      "// t421 : dit, n'ouvre rien", {}),
    S(ENVOI, 67, "if (!r) return;",
      "if (!r) return;\r\n"
      "    if (r.refus) { VL.toast(T(\"commun.envoi.refuse\", { nom: r.refus }), true); return; }", {}),
]
