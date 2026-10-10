"""t147 — integration : les jonctions vues à l'assemblage.

- index.html porte deux textes dont le même français a AILLEURS une autre traduction : le titre de la pièce 11
  « Édition » (ici Publishing, « Edit » au Montage) et le libellé « Carte » du bouton de repli de la scène (ici Card,
  « Map » au Vectorlab). La surcouche, qui traduit à l'aveugle par le texte exact, prendrait le mauvais sens : boot()
  les pose par dzT (clés « contexte », que la surcouche ignore) avant la première peinture.
- mod-face : les noms du catalogue (sujets, compositions, palettes, séries) vivent dans des tables FIGÉES par
  test_cards_face (comparées au backend cards/face.py) : traduits À L'AFFICHAGE seulement (vignettes, puces, liste des
  sujets, bulles) par libF (la surcouche du runtime : entrées H ci-dessous) ; le libellé stocké reste celui de la table.
"""
from outils import S, H

ENTREES = [
    S("js/core.js", 2389, "    BOOTED = true;\r\n",
      "    BOOTED = true;\r\n"
      "    /* t147 : « Édition » et « Carte » de index.html ont ailleurs un autre sens (Edit, Map) : posés par dzT */\r\n"
      "    { const h = el(\"#cf-panel-edition .panel-head h2\"); if (h) h.textContent = dzT(\"cartes.edition.titre\");\r\n"
      "      const c = el(\"#stageFoldBtn .sf-t\"); if (c) c.textContent = dzT(\"cartes.solid.hud_carte\"); }\r\n",
      {"cartes.edition.titre": ("Édition", "Publishing", "contexte"), "cartes.solid.hud_carte": ("Carte", "Card", "contexte")}),
]

FACE = "js/mod-face.js"
ENTREES += [
    S(FACE, 192, "  const PAL_BY = {}, SUB_BY = {}, COM_BY = {};\r\n",
      "  const PAL_BY = {}, SUB_BY = {}, COM_BY = {};\r\n"
      "  /* t147 : les noms du catalogue traduits À L'AFFICHAGE seulement (tables figées par les bancs miroir) — en\r\n"
      "     français, hors navigateur ou inconnus : tels quels ; une tuile se relit par ses ids */\r\n"
      "  const libF = (s) => (typeof window !== \"undefined\" && window.__dzI18n && window.__dzI18n.traduire(s)) || s;\r\n"
      "  const tuileLib = (c) => (c && SUB_BY[c.subject] && COM_BY[c.compo])\r\n"
      "    ? libF(SUB_BY[c.subject].label) + \" — \" + libF(COM_BY[c.compo].label) : libF(c && c.label);\r\n", {}),
    S(FACE, 3127, "s.textContent = c.label;", "s.textContent = tuileLib(c);", {}),
    S(FACE, 3397, "'\">' + esc(s.label)", "'\">' + esc(libF(s.label))", {}),
    S(FACE, 3405, "'>' + esc(s.label) + '</option>'", "'>' + esc(libF(s.label)) + '</option>'", {}),
    S(FACE, 3412, "'\">' + esc(c.label) + '</button>'", "'\">' + esc(libF(c.label)) + '</button>'", {}),
    S(FACE, 3620, "esc(p.label) + '</button>'", "esc(libF(p.label)) + '</button>'", {}),
    H("cartes.face.cat_braise", 'Braise', 'Ember'),
    H("cartes.face.cat_givre", 'Givre', 'Frost'),
    H("cartes.face.cat_sylve", 'Sylve', 'Sylvan'),
    H("cartes.face.cat_crepuscule", 'Crépuscule', 'Dusk'),
    H("cartes.face.cat_abysse", 'Abysse', 'Abyss'),
    H("cartes.face.cat_or", 'Or', 'Gold'),
    H("cartes.face.cat_cendre", 'Cendre', 'Ash'),
    H("cartes.face.cat_orage", 'Orage', 'Storm'),
    H("cartes.face.cat_floraison", 'Floraison', 'Bloom'),
    H("cartes.face.cat_neant", 'Néant', 'Void'),
    H("cartes.face.cat_sable", 'Sable', 'Sand'),
    H("cartes.face.cat_tour", 'Tour de guet', 'Watchtower'),
    H("cartes.face.cat_pins", 'Forêt de pins', 'Pine forest'),
    H("cartes.face.cat_monolithe", 'Portail de pierre', 'Stone gate'),
    H("cartes.face.cat_sphinx", 'Sphinx de garde', 'Guardian sphinx'),
    H("cartes.face.cat_portail", 'Portail arcanique', 'Arcane portal'),
    H("cartes.face.cat_cristaux", 'Cristaux', 'Crystals'),
    H("cartes.face.cat_navire", 'Navire', 'Ship'),
    H("cartes.face.cat_loup", 'Loup', 'Wolf'),
    H("cartes.face.cat_chevalier", 'Chevalier', 'Knight'),
    H("cartes.face.cat_citadelle", 'Citadelle', 'Citadel'),
    H("cartes.face.cat_baleine", 'Baleine céleste', 'Sky whale'),
    H("cartes.face.cat_phenix", 'Phénix', 'Phoenix'),
    H("cartes.face.cat_serpent", 'Serpent des mers', 'Sea serpent'),
    H("cartes.face.cat_golem", 'Golem de pierre', 'Stone golem'),
    H("cartes.face.cat_archere", 'Archère', 'Archer'),
    H("cartes.face.cat_brasier", 'Brasier', 'Beacon'),
    H("cartes.face.cat_medaillon", 'Médaillon', 'Medallion'),
    H("cartes.face.cat_blason", 'Blason', 'Heraldry'),
    H("cartes.face.cat_profondeurs", 'Profondeurs', 'Depths'),
    H("cartes.face.cat_contre_jour", 'Contre-jour', 'Backlight'),
    H("cartes.face.cat_vitrail", 'Vitrail', 'Stained Glass'),
    H("cartes.face.cat_vectoriel", 'Vectoriel', 'Vector'),
    H("cartes.face.cat_affiche", 'Affiche polonaise', 'Polish poster'),
]
