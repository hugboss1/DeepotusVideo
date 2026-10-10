"""t146 — integration : les jonctions entre groupes, vues à l'assemblage.

- mod-pile : VERS_TRANSFORMER / VERS_TRAIT sont COMPARÉS au texte des libellés de rangées de mod-style, que le groupe
  apparence passe par T : les libellés traduits (mêmes clés) sont AJOUTÉS aux listes, les français restent (sous node
  et en français, T rend le même texte : la comparaison est inchangée).
- mod-barreoutils : la bulle d'un outil vient de index.html (traduite par la surcouche du runtime) et reçoit « (B) »
  au chargement — AVANT que la surcouche ne passe : le texte n'aurait plus été reconnu (correspondance exacte). La
  base est donc traduite d'abord par le runtime (window.__dzI18n.traduire, null en français ou hors dictionnaire).
"""
from outils import S

ENTREES = [
    S("js/mod-pile.js", 15, '"Puissance"];',
      '"Puissance",\r\n  T("vectorlab.style.l_h"), T("vectorlab.style.incliner"), T("vectorlab.style.puissance")];', {}),
    S("js/mod-pile.js", 16, '"Joint", "Décaler"];',
      '"Joint", "Décaler",\r\n  T("vectorlab.style.contour"), T("vectorlab.style.trait"), T("vectorlab.style.pointilles"), T("vectorlab.style.decaler")];', {}),
    S("js/mod-barreoutils.js", 32, 'b.title = `${b.title} (${t})`',
      'b.title = `${(window.__dzI18n && window.__dzI18n.traduire(b.title)) || b.title} (${t})`', {}),
    # les <option> statiques de index.html (rôles du document) : la surcouche n'entre jamais dans un <select> — traduites
    # une fois au démarrage par le dictionnaire du runtime (entrées H de coque ; null en français)
    S("js/core.js", 785, 'initCalques(VL);',
      '// t146 : les <option> statiques de index.html (rôles…) — la surcouche n\'entre pas dans un <select>\r\n'
      'for (const o of document.querySelectorAll("select option")) { const t = window.__dzI18n && window.__dzI18n.traduire(o.textContent); if (t) o.textContent = t; }\r\n'
      'initCalques(VL);', {}),
    # le rôle du document (valeur stockée : libre, decor, lumiere, personnage) est AFFICHÉ — traduit à l'affichage
    S("js/core.js", 597, '`${etat.meta.role} · v${etat.meta.version}`',
      '`${({ libre: T("vectorlab.page.role_libre"), decor: T("vectorlab.page.role_decor"), lumiere: T("vectorlab.page.role_lumiere"), personnage: T("vectorlab.page.role_personnage") })[etat.meta.role] || etat.meta.role} · v${etat.meta.version}`', {}),
    S("js/mod-biblio.js", 77, '${esc(d.role)} · v${esc(d.version)}',
      '${esc(({ libre: T("vectorlab.page.role_libre"), decor: T("vectorlab.page.role_decor"), lumiere: T("vectorlab.page.role_lumiere"), personnage: T("vectorlab.page.role_personnage") })[d.role] || d.role)} · v${esc(d.version)}', {}),
]
