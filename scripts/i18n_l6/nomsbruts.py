"""noms-bruts (12/10, postérieur à L6) — un nom donné par l'utilisateur n'est jamais traduit par la surcouche.

Défaut vu aux captures du guide (t193, preuve 8809, dz_lang = "en") : un calque nommé « Fond » s'affichait « Fill ».
La surcouche de /shared/dz-i18n.js traduit tout nœud texte dont le texte est EXACTEMENT le français d'une entrée du
dictionnaire ; « Fond » en est une (vectorlab, Remplissage/Fond → Fill). Elle respecte déjà [data-dz-brut] (le
Photolab marque ainsi ses noms de calques : mod-calques, mod-cycle.brut, mod-iacalque). Le Vectorlab marque
désormais data-dz-brut="1" sur chaque libellé qui n'affiche QUE le nom saisi :
- panneau Calques : nom d'un calque, nom d'un objet (rangées de l'arbre) — js/mod-layers.js ;
- panneau Planches : nom d'une planche (texte et title) — js/mod-planches.js ;
- la page : étiquettes des planches et du document au-dessus de la page — js/core.js ;
- Apparence : noms des couleurs globales et des styles — js/mod-apparence2.js ;
- documents du lab (Bibliothèque du Vectorlab) : nom du document — js/mod-biblio.js ;
- persona Export : étiquettes des tranches — js/mod-exportplus.js ; Historique : noms des instantanés — js/mod-outils2.js ;
- menu Symboles : nom d'un symbole (drapeau `brut` d'une entrée de menu, rendu sur .fo-lib) — js/mod-flyout.js.
Pas marqués, et pourquoi : l'onglet du document (« nom @ 100% » n'est jamais un texte exact du dictionnaire) ; les
<option> (noms de calques de l'image IA par calque, terrains du menu contextuel) : la surcouche ne touche jamais une
OPTION ; les terrains (panneau Plateau, menu des terrains) : leurs noms par défaut viennent de T() à la création et
restent traduits à l'affichage ; les phrases qui CITENT un nom (« Supprimer le calque « {nom} » ? ») ne sont jamais
un texte exact. Aucun texte affiché neuf : pas de clé. Édition consignée en S sur la source de BASE (test_i18n_l6 [2])."""
from outils import L, S, X, H  # noqa: F401

BRUT = ' data-dz-brut="1"'

ENTREES = [
    # ── js/mod-layers.js : l'arbre des calques ──
    S("js/mod-layers.js", 126, '<span class="nom">${esc(r.nom)}</span>',
      '<span class="nom"' + BRUT + '>${esc(r.nom)}</span>', {}),
    S("js/mod-layers.js", 134, '<span class="nom">${esc(r.nom)}</span>',
      '<span class="nom"' + BRUT + '>${esc(r.nom)}</span>', {}),
    # ── js/mod-planches.js ──
    S("js/mod-planches.js", 17, '<span class="nom" title="${esc(p.nom)}">',
      '<span class="nom"' + BRUT + ' title="${esc(p.nom)}">', {}),
    # ── js/core.js : étiquettes posées sur la page ──
    S("js/core.js", 409, 'class: "planche-nom", "data-planche": p.id,',
      'class: "planche-nom", "data-planche": p.id, "data-dz-brut": "1",', {}),
    S("js/core.js", 416, 'class: "page-nom", "pointer-events": "none" }',
      'class: "page-nom", "data-dz-brut": "1", "pointer-events": "none" }', {}),
    # ── js/mod-apparence2.js : couleurs globales, styles ──
    S("js/mod-apparence2.js", 167, '<b style="flex:1">${esc(n)}</b>', '<b style="flex:1"' + BRUT + '>${esc(n)}</b>', {}),
    S("js/mod-apparence2.js", 174, '<b style="flex:1">${esc(n)}</b>', '<b style="flex:1"' + BRUT + '>${esc(n)}</b>', {}),
    # ── js/mod-biblio.js : nom d'un document ──
    S("js/mod-biblio.js", 76, '<div class="bib-nom" title="${esc(d.name)}">',
      '<div class="bib-nom"' + BRUT + ' title="${esc(d.name)}">', {}),
    # ── js/mod-exportplus.js : étiquette d'une tranche ──
    S("js/mod-exportplus.js", 186, 'l.textContent = t.nom;',
      'l.setAttribute("data-dz-brut", "1"); l.textContent = t.nom;', {}),
    # ── js/mod-outils2.js : nom d'un instantané ──
    S("js/mod-outils2.js", 333, '<span class="nom" title="${n}">',
      '<span class="nom"' + BRUT + ' title="${n}">', {}),
    # ── js/mod-flyout.js : un symbole est nommé par l'utilisateur ; le menu rend le drapeau `brut` ──
    S("js/mod-flyout.js", 22, 'libelle: s.nom || id,', 'libelle: s.nom || id, brut: true,', {}),
    S("js/mod-flyout.js", 226, '<span class="fo-lib">', '<span class="fo-lib"${e.brut ? \' data-dz-brut="1"\' : ""}>', {}),
]
