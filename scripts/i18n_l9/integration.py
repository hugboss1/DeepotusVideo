"""t149 — integration : ce que la surcouche ne voit pas, dans les quatre labs à page (Spritelab, Tile Lab, Studio3D,
Plateau).

- Les <option> fixes des pages : la surcouche n'entre pas dans <select> (dz-i18n.js, TEXTE_EXCLU), ni dans les attributs
  alt (ATTRS = title, placeholder, aria-label) → une passe unique au chargement, comme en L8
  (window.__dzI18n.traduire ne rend rien en français).
- Les textes de page saisis en « contexte » par les groupes H (sph, tlh, s3b_page, plh) : leur français a ailleurs un
  autre sens (« Feuille » = Leaf au Photolab, « Pièce » = Patch, « Fondu » = Dissolve, « Plateau » = Board au
  Vectorlab, « tiers » = l'anglais d'une clé du Vectorlab…) ; la surcouche les ignore → la même passe pose, pour les
  seules clés « contexte » de CETTE page, le texte exact d'un nœud ou d'un title/placeholder par dzT(clé).
La passe ne fait rien en français, ni sous node (bancs : ni document ni dzLang).
"""
from outils import S

_ANCRE = "const $ = (s) => document.querySelector(s);"


def _passe(prefixe):
    return (_ANCRE + "\r\n"
            "/* t149 (traduction L9) : passe unique au chargement, en anglais seulement — (1) les <option> fixes de la page\r\n"
            "   (la surcouche n'entre pas dans <select>) ; (2) les textes de la page saisis en « contexte » (sens propre au\r\n"
            "   lab, la surcouche les ignore) : texte exact d'un nœud ou d'un title/placeholder -> dzT(clé), clés de cette\r\n"
            "   page seulement. */\r\n"
            "(function () {\r\n"
            "  if (typeof document === \"undefined\" || typeof dzLang !== \"function\" || dzLang() !== \"en\") return;\r\n"
            "  const tr = window.__dzI18n && window.__dzI18n.traduire;\r\n"
            "  if (tr) for (const o of document.querySelectorAll(\"select option\")) { const t = tr(o.textContent); if (t) o.textContent = t; }\r\n"
            "  if (tr) for (const im of document.querySelectorAll(\"img[alt]\")) { const t = tr(im.alt); if (t) im.alt = t; }   // alt : hors surcouche\r\n"
            "  const D = window.DZ_I18N || {}, idx = {}, nrm = (s) => String(s).replace(/\\s+/g, \" \").trim();\r\n"
            f"  for (const k in D) if (k.startsWith(\"{prefixe}\") && D[k] && D[k].contexte) idx[nrm(D[k].fr)] = k;\r\n"
            "  // la surcouche a pu passer AVANT : le texte qu'elle a posé (« Plateau » -> Board du Vectorlab) est reconnu aussi\r\n"
            "  if (tr) for (const f of Object.keys(idx)) { const e = tr(f); if (e && !idx[nrm(e)]) idx[nrm(e)] = idx[f]; }\r\n"
            "  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);\r\n"
            "  for (let x = w.nextNode(); x; x = w.nextNode()) {\r\n"
            "    const k = idx[nrm(x.nodeValue)];\r\n"
            "    if (k) x.nodeValue = x.nodeValue.match(/^\\s*/)[0] + dzT(k) + x.nodeValue.match(/\\s*$/)[0];\r\n"
            "  }\r\n"
            "  for (const el of document.querySelectorAll(\"[title],[placeholder]\")) for (const a of [\"title\", \"placeholder\"]) {\r\n"
            "    const v = el.getAttribute(a), k = v && idx[nrm(v)];\r\n"
            "    if (k) el.setAttribute(a, dzT(k));\r\n"
            "  }\r\n"
            "})();")


ENTREES = [
    S("spritelab/spritelab.js", 8, _ANCRE, _passe("sprites.sph_"), {}),
    S("tilelab/tilelab.js", 8, _ANCRE, _passe("tuiles.tlh_"), {}),
    S("studio3d/studio3d.js", 15, _ANCRE, _passe("studio3d.s3b_page."), {}),
    S("plateau/plateau.js", 18, _ANCRE, _passe("plateau.plh_"), {}),
]
