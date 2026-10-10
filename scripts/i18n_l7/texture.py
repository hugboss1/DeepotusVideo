"""t147 — texture : js/mod-texture.js entier (pièce 06 · Matières : catalogue des 30 matières, finitions, table
lumineuse, banc d'essai, raccord de tuile, 8 maps PBR). Traduits : libellés du catalogue et des effets, curseurs de
dérivation, titres, boutons, infobulles, toasts, notes d'aide (concaténations → une clé à variables), unités Mo/Ko/Go.
GARDÉS : les catégories `cat` (valeurs comparées par le filtre, affichées par catLbl), les messages d'erreur internes
non affichés (« route absente »), la garde de chargement. Les textes renvoyés par le serveur (m.note, m.hint,
m.mesure_sur, m.note16) ne sont pas dans ce fichier."""
from outils import L, S, X, H

F = "js/mod-texture.js"
K = "cartes.texture."


def C(s):
    """Les sources sont en CRLF : un saut de ligne réel d'un bloc multi-ligne devient \\r\\n."""
    return s.replace("\r\n", "\n").replace("\n", "\r\n")


def LL(ligne, fr, cle, en, guill='"', n=1, contexte=False):
    """L sur un littéral sans échappement : le littéral est fr entre guillemets."""
    return L(F, ligne, guill + fr + guill, K + cle, fr, en, n=n, contexte=contexte)


def SS(ligne, avant, apres, dico, n=1):
    return S(F, ligne, C(avant), C(apres), {K + k: v for k, v in dico.items()}, n=n)


ENTREES = [
    X(F, 37, '"mod-texture: js/core.js doit etre charge avant ce fichier"', "garde de chargement (développeur)"),

    # ── 1. le catalogue : libellés affichés (les ids, gen, cat restent) ──
    LL(61, "Vélin ivoire", "mat_velin", "Ivory vellum"),
    LL(62, "Offset blanc", "mat_offset", "White offset"),
    LL(63, "Bristol lisse", "mat_bristol", "Smooth bristol"),
    LL(64, "Vergé crème", "mat_verge", "Cream laid"),
    LL(65, "Kraft brun", "mat_kraft", "Brown kraft"),
    LL(66, "Recyclé gris", "mat_recycle", "Grey recycled"),
    LL(67, "Papier aquarelle", "mat_aquarelle", "Watercolor paper"),
    LL(68, "Parchemin", "mat_parchemin", "Parchment"),
    LL(69, "Papier journal", "mat_journal", "Newsprint"),
    LL(70, "Carton noir mat", "mat_carton_noir", "Matte black board"),
    LL(71, "Lin naturel", "mat_lin", "Natural linen"),
    LL(72, "Toile de coton", "mat_toile", "Cotton canvas"),
    LL(73, "Canvas peintre", "mat_canvas", "Painter's canvas"),
    LL(74, "Toile de jute", "mat_jute", "Burlap"),
    LL(75, "Soie sauvage", "mat_soie", "Wild silk"),
    LL(77, "Feutrine", "mat_feutre", "Felt"),
    LL(78, "Ardoise", "mat_ardoise", "Slate"),
    LL(79, "Marbre blanc", "mat_marbre", "White marble"),
    LL(82, "Marbre noir", "mat_marbre_noir", "Black marble"),
    LL(83, "Béton ciré", "mat_beton", "Polished concrete"),
    LL(84, "Granit moucheté", "mat_granit", "Speckled granite"),
    LL(85, "Or brossé", "mat_or_brosse", "Brushed gold"),
    LL(86, "Argent brossé", "mat_argent_brosse", "Brushed silver"),
    LL(87, "Cuivre patiné", "mat_cuivre", "Patinated copper"),
    LL(88, "Acier peigné", "mat_acier", "Combed steel"),
    LL(89, "Fibre de carbone", "mat_carbone", "Carbon fiber"),
    LL(90, "Cuir grainé", "mat_cuir", "Grained leather"),
    LL(91, "Bois clair", "mat_bois", "Light wood"),
    LL(92, "Ébène", "mat_ebene", "Ebony"),
] + [X(F, ln, '"minéral"', "catégorie : valeur comparée par le filtre, affichée par catLbl") for ln in (78, 79, 82, 83, 84)] \
  + [X(F, ln, '"métal"', "catégorie : valeur comparée par le filtre, affichée par catLbl") for ln in (85, 86, 87, 88, 89)] + [

    # ── effets de dessus ──
    LL(98, "Aucun", "aucun", "None"),
    LL(99, "Grain de la matière", "over_grain", "Material grain"),
    LL(100, "Trame toile", "over_toile", "Canvas weave"),
    LL(101, "Foil or", "over_foil_or", "Gold foil"),
    LL(102, "Foil argent", "over_foil_argent", "Silver foil"),
    LL(103, "Holographique", "over_holo", "Holographic"),
    LL(104, "Irisé", "over_irise", "Iridescent"),
    LL(105, "Givre", "over_givre", "Frost"),
    LL(106, "Poussière & rayures", "over_poussiere", "Dust & scratches"),
    LL(107, "Vignettage", "over_vignette", "Vignette"),

    # ── curseurs de dérivation ──
    LL(120, "Force de la normale", "d_normal_strength", "Normal strength"),
    LL(121, "Inverser Y (DirectX)", "d_normal_invert_y", "Invert Y (DirectX)"),
    LL(122, "Détail de la hauteur", "d_height_detail", "Height detail"),
    LL(123, "Source de rugosité", "d_roughness_source", "Roughness source"),
    LL(124, "Biais de rugosité", "d_roughness_bias", "Roughness bias"),
    LL(125, "Contraste de rugosité", "d_roughness_contrast", "Roughness contrast"),
    LL(126, "Inverser la rugosité", "d_roughness_invert", "Invert roughness"),
    LL(127, "Force de l'occlusion", "d_ao_strength", "Occlusion strength"),
    LL(128, "Rayon d'occlusion", "d_ao_radius", "Occlusion radius"),
    LL(129, "Mode métallique", "d_metallic_mode", "Metallic mode"),
    LL(130, "Seuil métallique", "d_metallic_threshold", "Metallic threshold"),
    LL(131, "Seuil d'émission", "d_emissive_threshold", "Emission threshold"),

    # ── noms des maps ──
    LL(136, "Normale", "normale", "Normal"),
    LL(136, "Rugosité", "rugosite", "Roughness"),
    LL(137, "Métallique", "metallique", "Metallic"),
    LL(137, "Hauteur", "hauteur", "Height"),
    LL(138, "Émission", "emission", "Emission"),
    LL(138, "ORM (packée)", "orm_packee", "ORM (packed)"),

    # catégories affichées : un libellé par valeur comparée
    SS(140, "  const RES_CHOICES = [1024, 2048, 4096];",
       "  const RES_CHOICES = [1024, 2048, 4096];\n"
       "  /* t147 : la catégorie `cat` reste la valeur comparée par le filtre ; seul son libellé se traduit. */\n"
       "  const catLbl = (c) => ({\n"
       "    papier: dzT(\"cartes.texture.cat_papier\"), textile: dzT(\"cartes.texture.cat_textile\"),\n"
       "    \"minéral\": dzT(\"cartes.texture.cat_mineral\"), \"métal\": dzT(\"cartes.texture.cat_metal\"),\n"
       "    organique: dzT(\"cartes.texture.cat_organique\"),\n"
       "  }[c] || c);",
       {"cat_papier": ("papier", "paper"), "cat_textile": ("textile", "textile"),
        "cat_mineral": ("minéral", "mineral"), "cat_metal": ("métal", "metal"),
        "cat_organique": ("organique", "organic")}),

    # ── environnements et surfaces de la table lumineuse ──
    LL(912, "Rasant", "env_rasant", "Grazing"),
    LL(914, "Chaleureux", "env_chaud", "Warm"),
    LL(915, "Nuit", "env_nuit", "Night"),
    LL(923, "Plat", "forme_plat", "Flat"),
    LL(924, "Sphère", "forme_sphere", "Sphere"),
    LL(925, "Tuilé 2×2", "forme_tuile", "Tiled 2×2"),

    SS(1143, """'azimut <b>' + Math.round(LIT.az) + '°</b> · élévation <b>'
        + Math.round(LIT.el) + '°</b> · ' + esc(env.label)
        + ' · <span class="mono">' + W + '×' + H + ' px en ' + LIT.ms + ' ms</span>'""",
       """dzT("cartes.texture.lit_info", { az: Math.round(LIT.az), el: Math.round(LIT.el),
          env: esc(env.label), w: W, h: H, ms: LIT.ms })""",
       {"lit_info": ('azimut <b>{az}°</b> · élévation <b>{el}°</b> · {env} · <span class="mono">{w}×{h} px en {ms} ms</span>',
                     'azimuth <b>{az}°</b> · elevation <b>{el}°</b> · {env} · <span class="mono">{w}×{h} px in {ms} ms</span>')}),
    LL(1146, ' · <b class="cf-tx-flat">normale coupée</b>', "lit_n_coupee", ' · <b class="cf-tx-flat">normal off</b>', guill="'"),
    LL(1147, ' · <b class="cf-tx-flat">rugosité coupée</b>', "lit_r_coupee", ' · <b class="cf-tx-flat">roughness off</b>', guill="'"),
    LL(1148, ' · <b class="cf-tx-flat">métal coupé</b>', "lit_m_coupe", ' · <b class="cf-tx-flat">metal off</b>', guill="'"),
    LL(1149, ' · <b class="cf-tx-flat">occlusion coupée</b>', "lit_ao_coupee", ' · <b class="cf-tx-flat">occlusion off</b>', guill="'"),

    LL(1268, " Mo", "u_mo", " MB", contexte=True),
    LL(1269, " Ko", "u_ko", " KB", contexte=True),
    LL(1276, " Mo", "u_mo", " MB", contexte=True),
    LL(1276, " Ko", "u_ko", " KB", contexte=True),

    LL(1357, "Matières", "titre", "Materials"),

    # ── historique ──
    SS(1381, 'M.toast("rien à " + (from === UNDO ? "annuler" : "rétablir"));',
       'M.toast(from === UNDO ? dzT("cartes.texture.rien_annuler") : dzT("cartes.texture.rien_retablir"));',
       {"rien_annuler": ("rien à annuler", "nothing to undo"),
        "rien_retablir": ("rien à rétablir", "nothing to redo")}),
    LL(1387, "annulé", "annule", "undone", contexte=True),
    LL(1387, "rétabli", "retabli", "redone"),
    LL(1433, "matière : aucune", "toast_aucune", "material: none"),
    LL(1439, "réglages de matière remis aux défauts", "toast_defauts", "material settings reset to defaults"),

    # ── en-tête ──
    LL(1453, "Matière importée", "matiere_importee", "Imported material"),
    LL(1453, "Aucune matière", "aucune_matiere", "No material"),
    LL(1457, "Annuler", "annuler", "Undo", contexte=True),
    LL(1460, "Rétablir", "retablir", "Redo"),
    LL(1463, "Défauts", "defauts", "Defaults"),

    # ── D. table lumineuse ──
    LL(1493, "Table lumineuse", "lit_titre", "Light table"),
    LL(1493, "vos 8 PNG rallumés — glissez dans l'image pour orienter la lampe", "lit_sous",
       "your 8 PNGs relit — drag in the image to aim the lamp"),
    LL(1494, "microfacettes GGX", "lit_badge", "GGX microfacets"),
    SS(1497, """"Dérivez les maps : cet écran les rallume ensuite — <b>basecolor × normale × rugosité × métal × occlusion</b>, "
        + "sur un plan, une sphère ou une tuile 2×2, lumière déplaçable à la souris, "
        + "chaque map coupable pour voir ce qu'elle apporte.\"""",
       'dzT("cartes.texture.lit_vide")',
       {"lit_vide": ("Dérivez les maps : cet écran les rallume ensuite — <b>basecolor × normale × rugosité × métal × "
                     "occlusion</b>, sur un plan, une sphère ou une tuile 2×2, lumière déplaçable à la souris, chaque map "
                     "coupable pour voir ce qu'elle apporte.",
                     "Derive the maps: this screen then relights them — <b>basecolor × normal × roughness × metal × "
                     "occlusion</b>, on a plane, a sphere or a 2×2 tile, with a light you move with the mouse, and each map "
                     "can be switched off to see what it adds.")}),
    LL(1506, "Glisser : déplacer la lumière", "lit_glisser", "Drag: move the light"),
    LL(1558, "Azimut", "azimut", "Azimuth"),
    LL(1560, "Élévation", "elevation", "Elevation"),
    LL(1563, "Normale", "normale", "Normal"),
    LL(1563, "Rugosité", "rugosite", "Roughness"),
    LL(1563, "Métal", "metal", "Metal"),
    LL(1568, "Balayer la lumière", "balayer", "Sweep the light"),
    LL(1581, "Banc d'essai", "banc", "Test bench"),
    LL(1583, "Rend la même scène avec un seul réglage changé et mesure l'écart sur les pixels rendus", "banc_tip",
       "Renders the same scene with a single setting changed and measures the difference on the rendered pixels"),
    SS(1588, r"""'<p class="cf-tx-note"><b>Banc d\'essai — '
        + r.px.toLocaleString("fr-FR") + ' pixels rendus à l\'instant, '
        + 'un seul réglage changé à chaque fois.</b></p>'
        + '<p class="cf-tx-note"><b>Réponse métallique</b> — même scène, lumière '
        + 'à 35°, surface très rugueuse (spéculaire étalé) : luminance moyenne '
        + '<span class="mono">' + fx(r.metal0, 4) + '</span> à métal 0 contre '
        + '<span class="mono">' + fx(r.metal1, 4) + '</span> à métal 1, soit <b>−'
        + fx(r.chute, 1) + ' %</b>. C\'est le diffus qui part — '
        + '<span class="mono">kd = (1−F)(1−métal)</span> s\'annule ; ce qui reste '
        + 'est le spéculaire et le reflet d\'environnement, teintés par l\'albédo.</p>'
        + '<p class="cf-tx-note"><b>Fresnel</b> — sphère noire (albédo 0,02), '
        + 'soleil éteint, normale coupée : il ne reste que le reflet de '
        + 'l\'environnement. Luminance <span class="mono">' + fx(r.fIn, 4)
        + '</span> au centre (incidence normale, F₀ = 0,04) contre '
        + '<span class="mono">' + fx(r.fOut, 4) + '</span> sur la couronne du bord '
        + '(incidence rasante), soit <b>×' + fx(r.fOut / (r.fIn || 1e-9), 1)
        + '</b>. C\'est le terme de Schlick <span class="mono">F₀ + (1−F₀)(1−v·h)⁵</span> : '
        + 'toute surface devient un miroir au ras.</p>'
        + '<p class="cf-tx-note"><b>Rugosité</b> — largeur du lobe spéculaire, '
        + 'part de la sphère au-dessus de la moitié du maximum : <b>'
        + fx(r.lobe10, 1) + ' %</b> à rugosité 0,10 contre <b>' + fx(r.lobe60, 1)
        + ' %</b> à 0,60. Le lobe s\'élargit, il ne change pas seulement '
        + 'd\'intensité.</p>'""",
       """dzT("cartes.texture.banc_tete", { px: r.px.toLocaleString("fr-FR") })
        + dzT("cartes.texture.banc_metal", { m0: fx(r.metal0, 4), m1: fx(r.metal1, 4), chute: fx(r.chute, 1) })
        + dzT("cartes.texture.banc_fresnel", { fin: fx(r.fIn, 4), fout: fx(r.fOut, 4),
          k: fx(r.fOut / (r.fIn || 1e-9), 1) })
        + dzT("cartes.texture.banc_rugosite", { l10: fx(r.lobe10, 1), l60: fx(r.lobe60, 1) })""",
       {"banc_tete": ('<p class="cf-tx-note"><b>Banc d\'essai — {px} pixels rendus à l\'instant, un seul réglage changé '
                      'à chaque fois.</b></p>',
                      '<p class="cf-tx-note"><b>Test bench — {px} pixels rendered just now, one setting changed each '
                      'time.</b></p>'),
        "banc_metal": ('<p class="cf-tx-note"><b>Réponse métallique</b> — même scène, lumière à 35°, surface très rugueuse '
                       '(spéculaire étalé) : luminance moyenne <span class="mono">{m0}</span> à métal 0 contre '
                       '<span class="mono">{m1}</span> à métal 1, soit <b>−{chute} %</b>. C\'est le diffus qui part — '
                       '<span class="mono">kd = (1−F)(1−métal)</span> s\'annule ; ce qui reste est le spéculaire et le '
                       'reflet d\'environnement, teintés par l\'albédo.</p>',
                       '<p class="cf-tx-note"><b>Metallic response</b> — same scene, light at 35°, very rough surface '
                       '(spread specular): mean luminance <span class="mono">{m0}</span> at metal 0 versus '
                       '<span class="mono">{m1}</span> at metal 1, i.e. <b>−{chute} %</b>. It is the diffuse that goes — '
                       '<span class="mono">kd = (1−F)(1−metal)</span> drops to zero; what remains is the specular and the '
                       'environment reflection, tinted by the albedo.</p>'),
        "banc_fresnel": ('<p class="cf-tx-note"><b>Fresnel</b> — sphère noire (albédo 0,02), soleil éteint, normale '
                         'coupée : il ne reste que le reflet de l\'environnement. Luminance <span class="mono">{fin}</span> '
                         'au centre (incidence normale, F₀ = 0,04) contre <span class="mono">{fout}</span> sur la couronne '
                         'du bord (incidence rasante), soit <b>×{k}</b>. C\'est le terme de Schlick <span class="mono">F₀ + '
                         '(1−F₀)(1−v·h)⁵</span> : toute surface devient un miroir au ras.</p>',
                         '<p class="cf-tx-note"><b>Fresnel</b> — black sphere (albedo 0.02), sun off, normal off: only the '
                         'environment reflection remains. Luminance <span class="mono">{fin}</span> at the center (normal '
                         'incidence, F₀ = 0.04) versus <span class="mono">{fout}</span> on the edge ring (grazing '
                         'incidence), i.e. <b>×{k}</b>. This is the Schlick term <span class="mono">F₀ + '
                         '(1−F₀)(1−v·h)⁵</span>: every surface becomes a mirror at grazing angles.</p>'),
        "banc_rugosite": ('<p class="cf-tx-note"><b>Rugosité</b> — largeur du lobe spéculaire, part de la sphère au-dessus '
                          'de la moitié du maximum : <b>{l10} %</b> à rugosité 0,10 contre <b>{l60} %</b> à 0,60. Le lobe '
                          's\'élargit, il ne change pas seulement d\'intensité.</p>',
                          '<p class="cf-tx-note"><b>Roughness</b> — width of the specular lobe, share of the sphere above '
                          'half the maximum: <b>{l10} %</b> at roughness 0.10 versus <b>{l60} %</b> at 0.60. The lobe '
                          'widens; it does not merely change intensity.</p>')}),
    SS(1619, r""""<b>Microfacettes GGX</b> (Trowbridge-Reitz) + <b>Smith</b> corrélé en hauteur + "
      + "<b>Fresnel de Schlick</b>, en <b>espace linéaire</b> (la base color est décodée "
      + "du sRGB avant d'entrer et ré-encodée en sortie), avec réponse métallique "
      + "<span class=\"mono\">F0 = mélange(0,04 ; albédo ; métal)</span> et un environnement "
      + "hémisphérique ciel/sol. Sans ombres portées, ni carte d'environnement réelle, "
      + "ni réfraction. Calculé sur les <b>PNG écrits</b>, ramenés à " + LIT_PX
      + " px au plus (jamais agrandis) — la taille rendue est comptée sous la toile.""" + '"',
       'dzT("cartes.texture.lit_modele", { px: LIT_PX })',
       {"lit_modele": ('<b>Microfacettes GGX</b> (Trowbridge-Reitz) + <b>Smith</b> corrélé en hauteur + <b>Fresnel de '
                       'Schlick</b>, en <b>espace linéaire</b> (la base color est décodée du sRGB avant d\'entrer et '
                       'ré-encodée en sortie), avec réponse métallique <span class="mono">F0 = mélange(0,04 ; albédo ; '
                       'métal)</span> et un environnement hémisphérique ciel/sol. Sans ombres portées, ni carte '
                       'd\'environnement réelle, ni réfraction. Calculé sur les <b>PNG écrits</b>, ramenés à {px} px au '
                       'plus (jamais agrandis) — la taille rendue est comptée sous la toile.',
                       '<b>GGX microfacets</b> (Trowbridge-Reitz) + height-correlated <b>Smith</b> + <b>Schlick '
                       'Fresnel</b>, in <b>linear space</b> (the base color is decoded from sRGB on the way in and '
                       're-encoded on the way out), with a metallic response <span class="mono">F0 = mix(0.04; albedo; '
                       'metal)</span> and a sky/ground hemispherical environment. No cast shadows, no real environment '
                       'map, no refraction. Computed on the <b>written PNGs</b>, scaled to {px} px at most (never '
                       'enlarged) — the rendered size is counted under the canvas.')}),

    # ── A. matière du support ──
    LL(1637, "La matière de la carte", "papier_titre", "Card material"),
    LL(1637, "calque z = 10 · peint en premier", "papier_sous", "layer z = 10 · painted first"),
    SS(1638, 'MATS.length + " matières procédurales"',
       'dzT("cartes.texture.n_matieres", { n: MATS.length })',
       {"n_matieres": ("{n} matières procédurales", "{n} procedural materials")}),
    SS(1643, 'esc(c || "tout")', 'esc(c ? catLbl(c) : dzT("cartes.texture.cat_tout"))',
       {"cat_tout": ("tout", "all")}),
    LL(1649, "chercher…", "chercher", "search…"),
    LL(1665, '<b>Glisser une image ici</b><span>ou cliquer — elle devient la matière de la carte (JPEG/PNG/WebP)</span>',
       "drop", '<b>Drop an image here</b><span>or click — it becomes the card material (JPEG/PNG/WebP)</span>', guill="'"),
    X(F, 1668, '"image/*"', "filtre MIME du sélecteur de fichier"),
    LL(1688, "Opacité", "opacite", "Opacity"),
    LL(1690, "Fusion", "fusion", "Blend"),
    LL(1691, "Échelle", "echelle", "Scale"),
    LL(1696, "Teinte", "teinte", "Tint", contexte=True),
    LL(1707, "Regénère le hasard du motif", "grain_tip", "Reseeds the pattern's randomness"),

    # ── raccord de tuile ──
    SS(1737, r"""'<b>non défini</b><i class="cf-tx-def">marche médiane nulle : '
        + 'plus d\'une colonne sur deux est identique à sa voisine</i>'""",
       'dzT("cartes.texture.ratmed_nul")',
       {"ratmed_nul": ('<b>non défini</b><i class="cf-tx-def">marche médiane nulle : plus d\'une colonne sur deux est '
                       'identique à sa voisine</i>',
                       '<b>undefined</b><i class="cf-tx-def">zero median step: more than one column in two is identical '
                       'to its neighbor</i>')}),
    SS(1749, """'<b>Répétition de la tuile</b>'
        + '<span class="mono">jonction ÷ marche médiane ' + ratMed(r)
        + ' · ÷ plus forte marche <b>' + fx(r.exces, 2) + '×</b>'
        + '<i class="cf-tx-def">tuile ' + TILE + ' px</i></span>'
        + '<span class="mono">H ' + fx(r.x.edge, 2) + ' / méd. ' + fx(r.x.med, 2)
        + ' / max ' + fx(r.x.max, 2)
        + ' · V ' + fx(r.y.edge, 2) + ' / méd. ' + fx(r.y.med, 2)
        + ' / max ' + fx(r.y.max, 2)
        + '<i class="cf-tx-def">marche de jonction / médiane / plus forte, par axe</i></span>'""",
       """dzT("cartes.texture.seam_ligne", { med: ratMed(r), ex: fx(r.exces, 2), tile: TILE,
          he: fx(r.x.edge, 2), hm: fx(r.x.med, 2), hx: fx(r.x.max, 2),
          ve: fx(r.y.edge, 2), vm: fx(r.y.med, 2), vx: fx(r.y.max, 2) })""",
       {"seam_ligne": ('<b>Répétition de la tuile</b><span class="mono">jonction ÷ marche médiane {med} · ÷ plus forte '
                       'marche <b>{ex}×</b><i class="cf-tx-def">tuile {tile} px</i></span><span class="mono">H {he} / méd. '
                       '{hm} / max {hx} · V {ve} / méd. {vm} / max {vx}<i class="cf-tx-def">marche de jonction / médiane / '
                       'plus forte, par axe</i></span>',
                       '<b>Tile repeat</b><span class="mono">seam ÷ median step {med} · ÷ largest step <b>{ex}×</b><i '
                       'class="cf-tx-def">tile {tile} px</i></span><span class="mono">H {he} / med. {hm} / max {hx} · V '
                       '{ve} / med. {vm} / max {vx}<i class="cf-tx-def">seam step / median / largest, per axis</i></span>')}),
    SS(1762, '"Mesurer les " + MATS.length + " tuiles"',
       'dzT("cartes.texture.mesurer_n", { n: MATS.length })',
       {"mesurer_n": ("Mesurer les {n} tuiles", "Measure the {n} tiles")}),
    SS(1764, """"Mesure les " + (2 * (TILE - 1)) + " paires de colonnes et de lignes de chaque tuile "
      + "et publie les deux rapports (marche médiane, plus forte marche)\"""",
       'dzT("cartes.texture.mesurer_tip", { n: 2 * (TILE - 1) })',
       {"mesurer_tip": ("Mesure les {n} paires de colonnes et de lignes de chaque tuile et publie les deux rapports "
                        "(marche médiane, plus forte marche)",
                        "Measures the {n} column and row pairs of each tile and publishes both ratios (median step, "
                        "largest step)")}),
    LL(1774, "Exporter la tuile (PNG mesuré)", "tuile_export", "Export the tile (measured PNG)"),
    LL(1776, "Envoie la tuile 512 px au backend, qui la re-mesure sur les octets reçus et inscrit le résultat dans le fichier",
       "tuile_export_tip",
       "Sends the 512 px tile to the backend, which re-measures it on the received bytes and writes the result into the file"),
    SS(1792, '"mesure des " + MATS.length + " tuiles…"',
       'dzT("cartes.texture.mesure_n", { n: MATS.length })',
       {"mesure_n": ("mesure des {n} tuiles…", "measuring {n} tiles…")}),
    SS(1804, r"""'<p class="cf-tx-note"><b>' + n + ' / ' + MATS.length
      + '</b> tuiles dont la jonction reste sous la <b>plus forte</b> marche que la '
      + 'matière porte déjà à l\'intérieur (≤ 1,00×) · plus haut rapport <b>'
      + esc(pireId) + ' ' + fx(pire, 2) + '×</b>.</p>'
      + '<p class="cf-tx-note"><b>Le calcul, en entier.</b> On fait la moyenne des écarts '
      + 'entre la dernière colonne et la première (idem pour les lignes) : c\'est la '
      + '<b>marche de jonction</b>. On la divise ensuite par deux repères pris à '
      + 'l\'intérieur de la <i>même</i> tuile, sur ses <b>' + (TILE - 1) + '</b> paires de '
      + 'colonnes voisines et ses <b>' + (TILE - 1) + '</b> paires de lignes voisines : la '
      + 'marche <b>médiane</b>, et la <b>plus forte</b>. Les deux rapports sont publiés '
      + 'ensemble parce qu\'ils ne répondent pas à la même question — la médiane dit '
      + 'l\'ordinaire de la matière, la plus forte dit son pire — et un rapport divisé '
      + 'par le pire ne peut presque pas dépasser 1. Luminance '
      + '<span class="mono">0,299 R + 0,587 V + 0,114 B</span>, sans arrondi, tuile de '
      + TILE + ' px. La colonne ci-dessous donne le rapport à la plus forte marche.</p>'""",
       """dzT("cartes.texture.seamall_compte", { n: n, total: MATS.length, pire: esc(pireId), ex: fx(pire, 2) })
      + dzT("cartes.texture.seamall_calcul", { i: TILE - 1, tile: TILE })""",
       {"seamall_compte": ('<p class="cf-tx-note"><b>{n} / {total}</b> tuiles dont la jonction reste sous la <b>plus '
                           'forte</b> marche que la matière porte déjà à l\'intérieur (≤ 1,00×) · plus haut rapport '
                           '<b>{pire} {ex}×</b>.</p>',
                           '<p class="cf-tx-note"><b>{n} / {total}</b> tiles whose seam stays below the <b>largest</b> '
                           'step the material already carries inside (≤ 1.00×) · highest ratio <b>{pire} {ex}×</b>.</p>'),
        "seamall_calcul": ('<p class="cf-tx-note"><b>Le calcul, en entier.</b> On fait la moyenne des écarts entre la '
                           'dernière colonne et la première (idem pour les lignes) : c\'est la <b>marche de jonction</b>. '
                           'On la divise ensuite par deux repères pris à l\'intérieur de la <i>même</i> tuile, sur ses '
                           '<b>{i}</b> paires de colonnes voisines et ses <b>{i}</b> paires de lignes voisines : la marche '
                           '<b>médiane</b>, et la <b>plus forte</b>. Les deux rapports sont publiés ensemble parce '
                           'qu\'ils ne répondent pas à la même question — la médiane dit l\'ordinaire de la matière, la '
                           'plus forte dit son pire — et un rapport divisé par le pire ne peut presque pas dépasser 1. '
                           'Luminance <span class="mono">0,299 R + 0,587 V + 0,114 B</span>, sans arrondi, tuile de '
                           '{tile} px. La colonne ci-dessous donne le rapport à la plus forte marche.</p>',
                           '<p class="cf-tx-note"><b>The full calculation.</b> We average the differences between the '
                           'last column and the first (same for rows): that is the <b>seam step</b>. We then divide it by '
                           'two references taken inside the <i>same</i> tile, over its <b>{i}</b> pairs of neighboring '
                           'columns and its <b>{i}</b> pairs of neighboring rows: the <b>median</b> step and the '
                           '<b>largest</b> one. Both ratios are published together because they do not answer the same '
                           'question — the median tells the material\'s ordinary, the largest tells its worst — and a '
                           'ratio divided by the worst can hardly exceed 1. Luminance <span class="mono">0.299 R + 0.587 G '
                           '+ 0.114 B</span>, unrounded, {tile} px tile. The column below gives the ratio to the largest '
                           'step.</p>')}),
    SS(1823, 'n + "/" + MATS.length + " tuiles sous 1,00× — plus haut : " + pireId + " " + fx(pire, 2) + "×"',
       'dzT("cartes.texture.seamall_toast", { n: n, total: MATS.length, pire: pireId, ex: fx(pire, 2) })',
       {"seamall_toast": ("{n}/{total} tuiles sous 1,00× — plus haut : {pire} {ex}×",
                          "{n}/{total} tiles under 1.00× — highest: {pire} {ex}×")}),
    LL(1833, "choisir une matière du catalogue avant d'exporter sa tuile", "tuile_choisir",
       "pick a catalog material before exporting its tile"),
    SS(1835, '"export de la tuile " + m.label + "…"',
       'dzT("cartes.texture.tuile_busy", { mat: m.label })',
       {"tuile_busy": ("export de la tuile {mat}…", "exporting the {mat} tile…")}),
    X(F, 1837, '"image/png"', "type MIME du blob"),
    LL(1838, "le navigateur n'a pas produit de PNG", "pas_de_png", "the browser did not produce a PNG"),
    X(F, 1842, '"route absente"', "message interne : x.missing décide du toast affiché, ce texte n'est jamais montré"),
    SS(1854, r"""'<b>' + esc(m.label) + ' — recalculé sur le fichier reçu.</b> '
          + 'Rapport à la plus forte marche : à l\'écran <span class="mono">'
          + fx(ecran.exces_brut, 4) + '×</span> · dans le PNG <span class="mono">'
          + fx(t.seam.exces_brut, 4) + '×</span> · écart '
          + '<span class="mono">' + fx(ecart, 4) + '</span>'
          + ' · rapport à la marche médiane <span class="mono">'
          + ratMed(t.seam, true) + '</span>'
          + '. H ' + fx(t.seam.x.edge, 2) + ' / méd. ' + fx(t.seam.x.med, 2)
          + ' / max ' + fx(t.seam.x.max, 2)
          + ' · V ' + fx(t.seam.y.edge, 2) + ' / méd. ' + fx(t.seam.y.med, 2)
          + ' / max ' + fx(t.seam.y.max, 2)
          + '. Fichier <span class="mono">' + t.w + ' × ' + t.h + ' px, '
          + Math.round(t.bytes / 1024) + ' Ko</span>, chunks '
          + '<span class="mono">' + esc((t.chunks || []).filter((c, i, a) => a.indexOf(c) === i).join(" ")) + '</span>'
          + (t.dpi && t.dpi[0] ? ' · ' + dpiTxt(t.dpi) : '')
          + '. Les mesures sont écrites dans ses chunks <span class="mono">tEXt</span>, '
          + 'avec la formule qui les produit.</p>'""",
       """dzT("cartes.texture.tuile_chk", { mat: esc(m.label), ecran: fx(ecran.exces_brut, 4),
            png: fx(t.seam.exces_brut, 4), ecart: fx(ecart, 4), med: ratMed(t.seam, true),
            he: fx(t.seam.x.edge, 2), hm: fx(t.seam.x.med, 2), hx: fx(t.seam.x.max, 2),
            ve: fx(t.seam.y.edge, 2), vm: fx(t.seam.y.med, 2), vx: fx(t.seam.y.max, 2),
            w: t.w, h: t.h, ko: Math.round(t.bytes / 1024),
            chunks: esc((t.chunks || []).filter((c, i, a) => a.indexOf(c) === i).join(" ")),
            dpi: (t.dpi && t.dpi[0] ? ' · ' + dpiTxt(t.dpi) : '') })""",
       {"tuile_chk": ('<b>{mat} — recalculé sur le fichier reçu.</b> Rapport à la plus forte marche : à l\'écran '
                      '<span class="mono">{ecran}×</span> · dans le PNG <span class="mono">{png}×</span> · écart '
                      '<span class="mono">{ecart}</span> · rapport à la marche médiane <span class="mono">{med}</span>. '
                      'H {he} / méd. {hm} / max {hx} · V {ve} / méd. {vm} / max {vx}. Fichier <span class="mono">{w} × '
                      '{h} px, {ko} Ko</span>, chunks <span class="mono">{chunks}</span>{dpi}. Les mesures sont écrites '
                      'dans ses chunks <span class="mono">tEXt</span>, avec la formule qui les produit.</p>',
                      '<b>{mat} — recomputed on the received file.</b> Ratio to the largest step: on screen '
                      '<span class="mono">{ecran}×</span> · in the PNG <span class="mono">{png}×</span> · difference '
                      '<span class="mono">{ecart}</span> · ratio to the median step <span class="mono">{med}</span>. '
                      'H {he} / med. {hm} / max {hx} · V {ve} / med. {vm} / max {vx}. File <span class="mono">{w} × '
                      '{h} px, {ko} KB</span>, chunks <span class="mono">{chunks}</span>{dpi}. The measurements are '
                      'written into its <span class="mono">tEXt</span> chunks, along with the formula that produces '
                      'them.</p>')}),
    SS(1872, """"tuile exportée et recalculée sur le fichier : "
        + fx(t && t.seam ? t.seam.exces_brut : 0, 4) + "× la plus forte marche\"""",
       'dzT("cartes.texture.tuile_toast", { v: fx(t && t.seam ? t.seam.exces_brut : 0, 4) })',
       {"tuile_toast": ("tuile exportée et recalculée sur le fichier : {v}× la plus forte marche",
                        "tile exported and recomputed on the file: {v}× the largest step")}),
    LL(1876, "backend absent : l'export de tuile exige /api/cards", "tuile_sans_backend",
       "backend missing: tile export requires /api/cards"),

    # ── la grille ──
    LL(1883, "Aucune", "aucune", "None"),
    SS(1887, '(m.label + " " + m.cat)', '(m.label + " " + catLbl(m.cat))', {}),
    LL(1891, "Importée", "importee", "Imported"),
    SS(1897, '" · " + m.cat', '" · " + catLbl(m.cat)', {}),
    SS(1929, """" · jonction ÷ marche médiane "
        + (r.ratio_median === null ? "non défini (médiane nulle)" : fx(r.ratio_median, 2) + "×")
        + ", ÷ plus forte marche " + fx(r.exces, 2)
        + "× — H " + fx(r.x.edge, 2) + " / méd. " + fx(r.x.med, 2) + " / max " + fx(r.x.max, 2)
        + ", V " + fx(r.y.edge, 2) + " / méd. " + fx(r.y.med, 2) + " / max " + fx(r.y.max, 2)""",
       """dzT("cartes.texture.mat_tip", {
          med: (r.ratio_median === null ? dzT("cartes.texture.non_defini") : fx(r.ratio_median, 2) + "×"),
          ex: fx(r.exces, 2), he: fx(r.x.edge, 2), hm: fx(r.x.med, 2), hx: fx(r.x.max, 2),
          ve: fx(r.y.edge, 2), vm: fx(r.y.med, 2), vx: fx(r.y.max, 2) })""",
       {"mat_tip": (" · jonction ÷ marche médiane {med}, ÷ plus forte marche {ex}× — H {he} / méd. {hm} / max {hx}, "
                    "V {ve} / méd. {vm} / max {vx}",
                    " · seam ÷ median step {med}, ÷ largest step {ex}× — H {he} / med. {hm} / max {hx}, "
                    "V {ve} / med. {vm} / max {vx}"),
        "non_defini": ("non défini (médiane nulle)", "undefined (zero median)")}),
    LL(1936, "la jonction de cette tuile dépasse la plus forte marche qu'elle contient", "mat_alerte",
       "this tile's seam exceeds the largest step it contains"),
    SS(1963, """m.label + " — niveaux alignés : métal " + fx(m.mtl, 2)
        + ", rugosité " + fx(m.rgh, 2)""",
       'dzT("cartes.texture.aligne_toast", { mat: m.label, m: fx(m.mtl, 2), r: fx(m.rgh, 2) })',
       {"aligne_toast": ("{mat} — niveaux alignés : métal {m}, rugosité {r}",
                         "{mat} — levels aligned: metal {m}, roughness {r}")}),
    LL(1969, "ce fichier n'est pas une image", "pas_image", "this file is not an image"),
    LL(1971, "import de la matière…", "import_busy", "importing the material…"),
    X(F, 1973, '"route absente"', "message interne : x.missing décide du toast affiché, ce texte n'est jamais montré"),
    SS(1985, '"matière importée — " + ((d && d.paper) ? d.paper.w + " x " + d.paper.h + " px" : "OK")',
       'dzT("cartes.texture.import_toast", { info: ((d && d.paper) ? d.paper.w + " x " + d.paper.h + " px" : "OK") })',
       {"import_toast": ("matière importée — {info}", "material imported — {info}")}),
    LL(1987, "backend absent : l'import exige /api/cards", "import_sans_backend",
       "backend missing: import requires /api/cards"),

    # ── B. finition ──
    LL(1996, "La finition", "over_titre", "Finish"),
    LL(1996, "calque z = 30 · peint en dernier", "over_sous", "layer z = 30 · painted last"),
    SS(1997, '(OVERS.length - 1) + " effets"', 'dzT("cartes.texture.n_effets", { n: OVERS.length - 1 })',
       {"n_effets": ("{n} effets", "{n} effects")}),
    LL(2010, "Opacité", "opacite", "Opacity"),
    LL(2012, "Fusion", "fusion", "Blend"),
    LL(2013, "Échelle", "echelle", "Scale"),
    LL(2016, "Frottement", "frottement", "Edge wear"),
    LL(2017, "Éclat localisé", "eclat", "Spot gloss"),
    SS(2020, """"Le frottement assombrit, l'éclat éclaircit : ils sont peints séparément, "
      + "sinon l'éclat virerait au gris.\"""",
       'dzT("cartes.texture.over_note")',
       {"over_note": ("Le frottement assombrit, l'éclat éclaircit : ils sont peints séparément, sinon l'éclat virerait au "
                      "gris.",
                      "Edge wear darkens, gloss brightens: they are painted separately, otherwise the gloss would turn "
                      "grey.")}),

    # ── C. les 8 maps ──
    LL(2031, "Les 8 maps PBR", "pbr_titre", "The 8 PBR maps"),
    LL(2031, "dérivées de la carte rendue à l'échelle 1", "pbr_sous", "derived from the card rendered at scale 1"),
    LL(2039, "Dériver les 8 maps", "deriver_8", "Derive the 8 maps"),
    LL(2060, "16 bits (hauteur + normale) — maps de cet écran", "bits16", "16-bit (height + normal) — this screen's maps"),
    LL(2062, "carré (atlas)", "carre", "square (atlas)"),
    SS(2068, r""""Source : la carte " + (CF.current() + 1) + " rendue par le moteur unique, "
      + "<b>" + g.canvas_px.join(" x ") + " px</b> à " + g.dpi + " DPI. Sortie "
      + "<b>" + dim.join(" x ") + " px</b>"
      + (s.pbr.square ? " (atlas carré)" : " (format de la carte)")
      + ", soit <b>" + dpiTxt(dpi) + "</b> "
      + "inscrits dans le chunk <span class=\"mono\">pHYs</span> de chaque PNG — "
      + "fond perdu compris""" + '"',
       """dzT("cartes.texture.source", { n: CF.current() + 1, px: g.canvas_px.join(" x "), dpi: g.dpi,
        out: dim.join(" x "),
        fmt: (s.pbr.square ? dzT("cartes.texture.fmt_atlas") : dzT("cartes.texture.fmt_carte")),
        dens: dpiTxt(dpi) })""",
       {"source": ('Source : la carte {n} rendue par le moteur unique, <b>{px} px</b> à {dpi} DPI. Sortie <b>{out} '
                   'px</b>{fmt}, soit <b>{dens}</b> inscrits dans le chunk <span class="mono">pHYs</span> de chaque PNG — '
                   'fond perdu compris',
                   'Source: card {n} rendered by the single engine, <b>{px} px</b> at {dpi} DPI. Output <b>{out} '
                   'px</b>{fmt}, i.e. <b>{dens}</b> written into the <span class="mono">pHYs</span> chunk of each PNG — '
                   'bleed included'),
        "fmt_atlas": (" (atlas carré)", " (square atlas)"),
        "fmt_carte": (" (format de la carte)", " (card format)")}),
    SS(2079, """" (l'atlas carré rend les pixels rectangulaires : la densité n'est "
          + "pas la même en largeur et en hauteur)\"""",
       'dzT("cartes.texture.atlas_rect")',
       {"atlas_rect": (" (l'atlas carré rend les pixels rectangulaires : la densité n'est pas la même en largeur et en "
                       "hauteur)",
                       " (the square atlas makes pixels rectangular: density differs between width and height)")}),
    SS(2112, """"Coût : le dernier lot a pesé <b>" + mo(REPORT.bytes_total) + "</b> en <b>"
        + fx((REPORT.ms || 0) / 1000, 1) + " s</b> pour " + fx(REPORT.out_mpx, 2)
        + " Mpx (" + esc(REPORT.out_px || "") + "). Cette sélection en fait <b>"
        + fx(k, 2) + " ×</b> — soit ≈ <b>" + mo(REPORT.bytes_total * k)
        + "</b> et ≈ <b>" + dur((REPORT.ms || 0) * k) + "</b> par carte"
        + (n > 1
          ? ", et pour les <b>" + n + " cartes distinctes</b> de ce jeu ≈ <b>"
          : ", et pour la <b>seule carte</b> de ce jeu ≈ <b>")
        + (jeu >= 1073741824 ? fx(jeu / 1073741824, 2) + " Go" : mo(jeu))
        + "</b> et ≈ <b>" + dur((REPORT.ms || 0) * k * n)
        + "</b>. Les « ≈ » sont une règle de trois à coût par pixel constant, "
        + "à partir du poids et du temps du dernier lot.\"""",
       """dzT("cartes.texture.cout", { poids: mo(REPORT.bytes_total), s: fx((REPORT.ms || 0) / 1000, 1),
          mpx: fx(REPORT.out_mpx, 2), outpx: esc(REPORT.out_px || ""), k: fx(k, 2),
          pk: mo(REPORT.bytes_total * k), dk: dur((REPORT.ms || 0) * k) })
        + dzT(n > 1 ? "cartes.texture.cout_jeu" : "cartes.texture.cout_seule", { n: n,
          jeu: (jeu >= 1073741824 ? fx(jeu / 1073741824, 2) + dzT("cartes.texture.u_go") : mo(jeu)),
          dj: dur((REPORT.ms || 0) * k * n) })
        + dzT("cartes.texture.cout_regle")""",
       {"cout": ("Coût : le dernier lot a pesé <b>{poids}</b> en <b>{s} s</b> pour {mpx} Mpx ({outpx}). Cette sélection "
                 "en fait <b>{k} ×</b> — soit ≈ <b>{pk}</b> et ≈ <b>{dk}</b> par carte",
                 "Cost: the last batch weighed <b>{poids}</b> in <b>{s} s</b> for {mpx} Mpx ({outpx}). This selection is "
                 "<b>{k} ×</b> that — about <b>{pk}</b> and about <b>{dk}</b> per card"),
        "cout_jeu": (", et pour les <b>{n} cartes distinctes</b> de ce jeu ≈ <b>{jeu}</b> et ≈ <b>{dj}</b>",
                     ", and for the <b>{n} distinct cards</b> of this deck about <b>{jeu}</b> and about <b>{dj}</b>"),
        "cout_seule": (", et pour la <b>seule carte</b> de ce jeu ≈ <b>{jeu}</b> et ≈ <b>{dj}</b>",
                       ", and for the <b>only card</b> of this deck about <b>{jeu}</b> and about <b>{dj}</b>"),
        "u_go": (" Go", " GB", "contexte"),
        "cout_regle": (". Les « ≈ » sont une règle de trois à coût par pixel constant, à partir du poids et du temps du "
                       "dernier lot.",
                       ". The “about” figures are a rule of three at constant cost per pixel, based on the weight and "
                       "time of the last batch.")}),
    LL(2131, "largeur", "largeur", "width"),
    LL(2131, "hauteur", "hauteur_min", "height"),
    LL(2142, " carré", "res_carre", " square"),
    LL(2142, " au format de la carte", "res_format", " at card format"),
    SS(2148, """"<b>" + bas + " DPI en " + axe + "</b> : sous les 300 DPI d'une impression "
        + "pour une carte de " + fx(g.trim_mm[0] + 2 * g.bleed_mm, 1) + " × "
        + fx(g.trim_mm[1] + 2 * g.bleed_mm, 1) + " mm fond perdu compris. \"""",
       """dzT("cartes.texture.sous300_note", { dpi: bas, axe: axe, w: fx(g.trim_mm[0] + 2 * g.bleed_mm, 1),
          h: fx(g.trim_mm[1] + 2 * g.bleed_mm, 1) })""",
       {"sous300_note": ("<b>{dpi} DPI en {axe}</b> : sous les 300 DPI d'une impression pour une carte de {w} × {h} mm "
                         "fond perdu compris. ",
                         "<b>{dpi} DPI along the {axe}</b>: below the 300 DPI of a print for a {w} × {h} mm card, bleed "
                         "included. ")}),
    SS(2152, '"Passent les 300 DPI sur les deux axes : <b>" + bons.slice(0, 3).join("</b>, <b>") + "</b>."',
       'dzT("cartes.texture.sous300_bons", { liste: bons.slice(0, 3).join("</b>, <b>") })',
       {"sous300_bons": ("Passent les 300 DPI sur les deux axes : <b>{liste}</b>.",
                         "Reach 300 DPI on both axes: <b>{liste}</b>.")}),
    LL(2153, "Aucune définition proposée n'atteint 300 DPI sur ce format.", "sous300_aucun",
       "No offered resolution reaches 300 DPI on this format."),
    SS(2176, """"<b>Seuil d'émission " + fx(seuilEm, 2) + " &gt; " + fx(sl.max, 2)
        + "</b> — la luminance de l'image dérivée ne dépasse jamais "
        + fx(sl.max, 2) + " (sur " + (sl.px || 0).toLocaleString("fr-FR")
        + " pixels au dernier calcul) : l'émission sortira <b>noire</b>. \"""",
       """dzT("cartes.texture.emission_noire", { seuil: fx(seuilEm, 2), max: fx(sl.max, 2),
          px: (sl.px || 0).toLocaleString("fr-FR") })""",
       {"emission_noire": ("<b>Seuil d'émission {seuil} &gt; {max}</b> — la luminance de l'image dérivée ne dépasse "
                           "jamais {max} (sur {px} pixels au dernier calcul) : l'émission sortira <b>noire</b>. ",
                           "<b>Emission threshold {seuil} &gt; {max}</b> — the luminance of the derived image never "
                           "exceeds {max} (over {px} pixels in the last run): the emission will come out <b>black</b>. ")}),
    SS(2182, '"Régler le seuil sur " + fx(cible, 2) + " (p80 mesuré)"',
       'dzT("cartes.texture.seuil_fix", { v: fx(cible, 2) })',
       {"seuil_fix": ("Régler le seuil sur {v} (p80 mesuré)", "Set the threshold to {v} (measured p80)")}),
    SS(2184, """"Le centile 80 de la luminance de l'image dérivée : un "
          + "pixel sur cinq passe alors le seuil. Ce que la map porte "
          + "ensuite est mesuré sous sa vignette, comme le reste.\"""",
       'dzT("cartes.texture.seuil_fix_tip")',
       {"seuil_fix_tip": ("Le centile 80 de la luminance de l'image dérivée : un pixel sur cinq passe alors le seuil. Ce "
                          "que la map porte ensuite est mesuré sous sa vignette, comme le reste.",
                          "The 80th percentile of the derived image's luminance: one pixel in five then passes the "
                          "threshold. What the map then carries is measured under its thumbnail, like the rest.")}),
    SS(2206, """"<b>" + esc(mm.label) + "</b> : " + (mm.mtl >= 0.5 ? "métal" : "diélectrique")
        + " " + fx(mm.mtl, 2) + " / rugosité " + fx(mm.rgh, 2)
        + " — niveaux cuits actuels métal " + fx(s.pbr.levels.metallic, 2)
        + ", rugosité " + fx(s.pbr.levels.roughness, 2)""",
       """dzT("cartes.texture.aligne_note", { mat: esc(mm.label),
          type: (mm.mtl >= 0.5 ? dzT("cartes.texture.metal_min") : dzT("cartes.texture.dielectrique")),
          m: fx(mm.mtl, 2), r: fx(mm.rgh, 2),
          cm: fx(s.pbr.levels.metallic, 2), cr: fx(s.pbr.levels.roughness, 2) })""",
       {"aligne_note": ("<b>{mat}</b> : {type} {m} / rugosité {r} — niveaux cuits actuels métal {cm}, rugosité {cr}",
                        "<b>{mat}</b>: {type} {m} / roughness {r} — current baked levels metal {cm}, roughness {cr}"),
        "metal_min": ("métal", "metal"),
        "dielectrique": ("diélectrique", "dielectric")}),
    LL(2211, ". Exporté tel quel, il sortira en <b>plastique doré</b>.", "plastique",
       ". Exported as is, it will come out as <b>gold-colored plastic</b>."),
    LL(2212, "Aligner sur la matière", "aligner", "Match the material"),
    SS(2228, """"Réglages de dérivation (" + DERIVE_UI.length
      + ") et niveaux cuits (2)\"""",
       'dzT("cartes.texture.reglages_sum", { n: DERIVE_UI.length })',
       {"reglages_sum": ("Réglages de dérivation ({n}) et niveaux cuits (2)",
                         "Derivation settings ({n}) and baked levels (2)")}),
    LL(2242, "Niveau métallique (cuit)", "niveau_metal", "Metallic level (baked)"),
    LL(2244, "Niveau de rugosité (cuit)", "niveau_rugosite", "Roughness level (baked)"),
    SS(2256, """"Le niveau vit dans la MAP, pas dans un facteur : <b>moyenne mesurée = niveau réglé</b>, "
      + "relue sur le PNG écrit (glTF : rugosité = facteur × canal V). "
      + "<b>Portée :</b> ces deux niveaux sont cuits dans les maps de <i>cet</i> écran — "
      + "celles que téléchargent « PNG », « Planche » et le manifeste. L'écran <b>Export 3D</b> "
      + "cuit les siens depuis sa propre <b>finition</b> : il ne relit pas ces deux nombres. "
      + "Les douze réglages de dérivation ci-dessus, eux, sont bien repris par lui.\"""",
       'dzT("cartes.texture.niveaux_note")',
       {"niveaux_note": ("Le niveau vit dans la MAP, pas dans un facteur : <b>moyenne mesurée = niveau réglé</b>, relue "
                         "sur le PNG écrit (glTF : rugosité = facteur × canal V). <b>Portée :</b> ces deux niveaux sont "
                         "cuits dans les maps de <i>cet</i> écran — celles que téléchargent « PNG », « Planche » et le "
                         "manifeste. L'écran <b>Export 3D</b> cuit les siens depuis sa propre <b>finition</b> : il ne "
                         "relit pas ces deux nombres. Les douze réglages de dérivation ci-dessus, eux, sont bien repris "
                         "par lui.",
                         "The level lives in the MAP, not in a factor: <b>measured mean = set level</b>, read back from "
                         "the written PNG (glTF: roughness = factor × G channel). <b>Scope:</b> these two levels are "
                         "baked into <i>this</i> screen's maps — the ones downloaded by “PNG”, “Sheet” and the manifest. "
                         "The <b>3D Export</b> screen bakes its own from its own <b>finish</b>: it does not read these "
                         "two numbers. The twelve derivation settings above, however, are picked up by it.")}),
    SS(2310, """"<b>Aucune map dérivée pour l'instant.</b>"
        + "<span>La carte affichée porte déjà sa matière : un clic la transforme en 8 maps PBR "
        + "mesurées — relief, rugosité, occlusion, hauteur.</span>\"""",
       'dzT("cartes.texture.maps_vide")',
       {"maps_vide": ("<b>Aucune map dérivée pour l'instant.</b><span>La carte affichée porte déjà sa matière : un clic la "
                      "transforme en 8 maps PBR mesurées — relief, rugosité, occlusion, hauteur.</span>",
                      "<b>No derived maps yet.</b><span>The displayed card already carries its material: one click turns "
                      "it into 8 measured PBR maps — relief, roughness, occlusion, height.</span>")}),
    LL(2313, "Dériver maintenant", "deriver_maint", "Derive now"),
    SS(2329, """'<span class="cf-tx-flat">' + plates + ' constante'
        + (plates > 1 ? 's' : '') + '</span>'""",
       """'<span class="cf-tx-flat">'
        + dzT(plates > 1 ? "cartes.texture.constantes.plusieurs" : "cartes.texture.constantes.un", { n: plates }) + '</span>'""",
       {"constantes.un": ("{n} constante", "{n} constant map"),
        "constantes.plusieurs": ("{n} constantes", "{n} constant maps")}),
    SS(2331, """'<span class="mono">rugosité effective ' + fx(eff.roughness === undefined ? 0 : eff.roughness, 3)
      + ' · métal ' + fx(eff.metallic === undefined ? 0 : eff.metallic, 3) + '</span>'""",
       """'<span class="mono">' + dzT("cartes.texture.effectifs", {
        r: fx(eff.roughness === undefined ? 0 : eff.roughness, 3),
        m: fx(eff.metallic === undefined ? 0 : eff.metallic, 3) }) + '</span>'""",
       {"effectifs": ("rugosité effective {r} · métal {m}", "effective roughness {r} · metal {m}")}),
    LL(2333, " · dérivé à ", "derive_a", " · derived at ", guill="'"),
    SS(2335, """' DPI · carte '
        + ph.mm[0] + '×' + ph.mm[1] + ' mm (fond perdu ' + ph.bleed_mm
        + ', zone sûre ' + ph.safe_mm + ')</span>'""",
       """' DPI · ' + dzT("cartes.texture.phys_carte", { w: ph.mm[0], h: ph.mm[1], bleed: ph.bleed_mm,
          safe: ph.safe_mm }) + '</span>'""",
       {"phys_carte": ("carte {w}×{h} mm (fond perdu {bleed}, zone sûre {safe})",
                       "card {w}×{h} mm (bleed {bleed}, safe zone {safe})")}),
    SS(2343, """'<span class="cf-tx-flat">sous 300 DPI : '
            + Math.min(ph.dpi[0], ph.dpi[1]) + " DPI en "
            + (ph.dpi[0] <= ph.dpi[1] ? "largeur" : "hauteur") + '</span>'""",
       """'<span class="cf-tx-flat">' + dzT("cartes.texture.sous300", { dpi: Math.min(ph.dpi[0], ph.dpi[1]),
            axe: (ph.dpi[0] <= ph.dpi[1] ? dzT("cartes.texture.largeur") : dzT("cartes.texture.hauteur_min")) })
            + '</span>'""",
       {"sous300": ("sous 300 DPI : {dpi} DPI en {axe}", "below 300 DPI: {dpi} DPI along the {axe}")}),
    LL(2346, "Planche PNG", "planche", "PNG sheet"),
    LL(2348, "Les 8 maps sur une seule image, avec les mesures écrites dessous", "planche_tip",
       "The 8 maps on a single image, with the measurements written below"),
    LL(2351, "Manifeste JSON", "manifeste", "JSON manifest"),
    LL(2353, "Espaces colorimétriques, densité physique, conventions, SHA-256 de chaque fichier", "manifeste_tip",
       "Color spaces, physical density, conventions, SHA-256 of each file"),
    LL(2372, "Comment lire ces chiffres — les définitions exactes, arrondis compris", "defs_sum",
       "How to read these figures — the exact definitions, rounding included"),
    SS(2375, """"Les chiffres de cet écran sont <b>lus sur les octets des PNG écrits</b>, la profondeur "
      + "comprise. <b>niveaux</b> = combien de valeurs différentes le canal mesuré contient "
      + "réellement, sur ce que sa profondeur autorise (256 en 8 bits, 65 536 en 16) : c'est "
      + "ce compte, et pas l'étiquette du fichier, qui décide si un dégradé sortira lisse ou "
      + "en marches. Sur une map 16 bits, deux chiffres disent ce que le second octet "
      + "apporte : la part des points <b>trop fins pour un octet</b>, et l'<b>information "
      + "qu'il porte</b>, sur 8. Quand ces deux-là tombent à zéro, la map est écrite en "
      + "8 bits, elle pèse moins, et l'étiquette le dit.\"""",
       'dzT("cartes.texture.defs_octets")',
       {"defs_octets": ("Les chiffres de cet écran sont <b>lus sur les octets des PNG écrits</b>, la profondeur comprise. "
                        "<b>niveaux</b> = combien de valeurs différentes le canal mesuré contient réellement, sur ce que "
                        "sa profondeur autorise (256 en 8 bits, 65 536 en 16) : c'est ce compte, et pas l'étiquette du "
                        "fichier, qui décide si un dégradé sortira lisse ou en marches. Sur une map 16 bits, deux "
                        "chiffres disent ce que le second octet apporte : la part des points <b>trop fins pour un "
                        "octet</b>, et l'<b>information qu'il porte</b>, sur 8. Quand ces deux-là tombent à zéro, la map "
                        "est écrite en 8 bits, elle pèse moins, et l'étiquette le dit.",
                        "The figures on this screen are <b>read from the bytes of the written PNGs</b>, bit depth "
                        "included. <b>levels</b> = how many distinct values the measured channel actually contains, out "
                        "of what its depth allows (256 at 8 bits, 65,536 at 16): it is this count, not the file's label, "
                        "that decides whether a gradient comes out smooth or banded. On a 16-bit map, two figures tell "
                        "what the second byte adds: the share of points <b>too fine for one byte</b>, and the "
                        "<b>information it carries</b>, out of 8. When both drop to zero, the map is written at 8 bits, "
                        "it weighs less, and the label says so.")}),
    SS(2394, r""""<b>Ce que « moy », « ampl. » et « é.-t. » veulent dire</b> — et ce n'est pas la même "
      + "chose d'une map à l'autre, d'où l'étiquette sous chaque chiffre. <b>moy</b> = moyenne "
      + "du canal nommé ; sur la base color et l'émission c'est la <b>luminance Rec.601</b>, "
      + "<span class=\"mono\">(R×19595 + V×38470 + B×7471 + 32768) &gt;&gt; 16</span>, "
      + "<b>arrondie</b>. Sur une map 16 bits elle se lit sur seize bits, puis se ramène "
      + "sur l'échelle 0-255. "
      + "<b>ampl.</b> = <b>p95 − p5</b> du même canal, sur 255 — pas max moins min ; "
      + "sur une map 16 bits, les centiles sont pris sur les <b>65 536 classes réelles</b> "
      + "et ramenés sur l'échelle 0-255, et c'est un décimal. "
      + "<b>é.-t.</b> = écart-type du même canal, sur la même échelle : c'est lui qui sépare "
      + "une map qui varie partout d'une map constante sur 90 % de sa surface. "
      + "Le manifeste porte ces définitions par ligne (<span class=\"mono\">canal_mesure</span>, "
      + "<span class=\"mono\">amplitude_mesure</span>).""" + '"',
       'dzT("cartes.texture.defs_moy")',
       {"defs_moy": ("<b>Ce que « moy », « ampl. » et « é.-t. » veulent dire</b> — et ce n'est pas la même chose d'une map "
                     "à l'autre, d'où l'étiquette sous chaque chiffre. <b>moy</b> = moyenne du canal nommé ; sur la base "
                     "color et l'émission c'est la <b>luminance Rec.601</b>, <span class=\"mono\">(R×19595 + V×38470 + "
                     "B×7471 + 32768) &gt;&gt; 16</span>, <b>arrondie</b>. Sur une map 16 bits elle se lit sur seize "
                     "bits, puis se ramène sur l'échelle 0-255. <b>ampl.</b> = <b>p95 − p5</b> du même canal, sur 255 — "
                     "pas max moins min ; sur une map 16 bits, les centiles sont pris sur les <b>65 536 classes "
                     "réelles</b> et ramenés sur l'échelle 0-255, et c'est un décimal. <b>é.-t.</b> = écart-type du même "
                     "canal, sur la même échelle : c'est lui qui sépare une map qui varie partout d'une map constante sur "
                     "90 % de sa surface. Le manifeste porte ces définitions par ligne (<span "
                     "class=\"mono\">canal_mesure</span>, <span class=\"mono\">amplitude_mesure</span>).",
                     "<b>What “mean”, “range” and “s.d.” mean</b> — and it is not the same from one map to another, hence "
                     "the label under each figure. <b>mean</b> = mean of the named channel; on the base color and the "
                     "emission it is the <b>Rec.601 luminance</b>, <span class=\"mono\">(R×19595 + G×38470 + B×7471 + "
                     "32768) &gt;&gt; 16</span>, <b>rounded</b>. On a 16-bit map it is read on sixteen bits, then brought "
                     "back to the 0-255 scale. <b>range</b> = <b>p95 − p5</b> of the same channel, out of 255 — not max "
                     "minus min; on a 16-bit map, the percentiles are taken over the <b>65,536 real classes</b> and "
                     "brought back to the 0-255 scale, so it is a decimal. <b>s.d.</b> = standard deviation of the same "
                     "channel, on the same scale: it is what separates a map that varies everywhere from a map that is "
                     "constant over 90 % of its surface. The manifest carries these definitions per row (<span "
                     "class=\"mono\">canal_mesure</span>, <span class=\"mono\">amplitude_mesure</span>).")}),
    LL(2435, " (16 demandés)", "b16_demandes", " (16 requested)", guill="'"),
    LL(2470, '<span class="mono">moy <b>', "v_moy", '<span class="mono">mean <b>', guill="'"),
    LL(2472, '<span class="mono">ampl. ', "v_ampl", '<span class="mono">range ', guill="'"),
    LL(2474, '<span class="mono">é.-t. ', "v_et", '<span class="mono">s.d. ', guill="'"),
    LL(2475, '<i class="cf-tx-def">écart-type du même canal</i></span>', "v_et_def",
       '<i class="cf-tx-def">standard deviation of the same channel</i></span>', guill="'"),
    LL(2476, '<span class="mono">niveaux ', "v_niveaux", '<span class="mono">levels ', guill="'"),
    LL(2478, '<i class="cf-tx-def">valeurs distinctes du même canal</i></span>', "v_niveaux_def",
       '<i class="cf-tx-def">distinct values of the same channel</i></span>', guill="'"),
    LL(2480, '<span class="mono">hors 8 bits ', "v_hors8", '<span class="mono">beyond 8 bits ', guill="'"),
    LL(2481, '<i class="cf-tx-def">points trop fins pour un octet', "v_hors8_def",
       '<i class="cf-tx-def">points too fine for one byte', guill="'"),
    LL(2482, ", sur ", "v_sur", ", out of ", guill="'"),
    LL(2483, '<span class="mono">second octet ', "v_octet2", '<span class="mono">second byte ', guill="'"),
    L(F, 2485, "'<i class=\"cf-tx-def\">information qu\\'il porte</i></span>'", K + "v_octet2_def",
      '<i class="cf-tx-def">information qu\'il porte</i></span>',
      '<i class="cf-tx-def">information it carries</i></span>'),
    LL(2487, '<span class="cf-tx-flat">constante</span>', "v_constante", '<span class="cf-tx-flat">constant</span>',
       guill="'"),
    LL(2504, " (blocs 192²) · ", "corr_blocs", " (192² blocks) · "),
    LL(2506, " (pleine résolution) avec la luminance de la base color", "corr_pleine",
       " (full resolution) against the base color luminance"),
    SS(2511, """"normale unitaire " + fx(u.unit_pct, 1) + " % · |n| moy " + fx(u.mean, 5)
        + " (" + fx(u.min, 4) + " – " + fx(u.max, 4) + ") · " + u.zneg + " pixel(s) à z<0"
        + " · décodé sur " + (u.bits || 8) + " bits\"""",
       """dzT("cartes.texture.normale_unit", { pct: fx(u.unit_pct, 1), moy: fx(u.mean, 5), min: fx(u.min, 4),
          max: fx(u.max, 4), z: u.zneg, bits: u.bits || 8 })""",
       {"normale_unit": ("normale unitaire {pct} % · |n| moy {moy} ({min} – {max}) · {z} pixel(s) à z<0 · décodé sur "
                         "{bits} bits",
                         "unit normal {pct} % · |n| mean {moy} ({min} – {max}) · {z} pixel(s) at z<0 · decoded on "
                         "{bits} bits")}),
    LL(2523, "rugosité", "rugosite_min", "roughness"),
    LL(2523, "métal", "metal_min", "metal"),
    LL(2526, "non mesurable", "non_mesurable", "not measurable"),
    SS(2532, """"écart maximum avec les trois maps séparées, sur "
        + p.px.toLocaleString("fr-FR") + " pixels relus : " + trois.join(" · ")
        + (p.octets ? " · " + Math.round(p.octets / 1024) + " Ko" : "")""",
       """dzT("cartes.texture.orm_ecart", { px: p.px.toLocaleString("fr-FR"), liste: trois.join(" · ") })
        + (p.octets ? " · " + Math.round(p.octets / 1024) + dzT("cartes.texture.u_ko") : "")""",
       {"orm_ecart": ("écart maximum avec les trois maps séparées, sur {px} pixels relus : {liste}",
                      "maximum difference with the three separate maps, over {px} pixels read back: {liste}")}),
    SS(2550, """"livrer l'ORM <b>à la place</b> des trois séparées : "
          + deux[0] + " contre " + deux[1]
          + " — " + (d > 0
            ? "le lot <b>grossirait</b> de " + mo(d)
              + " (la déflate compresse trois plans corrélés côte à côte moins "
              + "bien que trois gris séparés)"
            : d < 0
              ? "le lot maigrirait de " + mo(-d)
              : "même poids") + ", mesuré sur les fichiers écrits\"""",
       """dzT("cartes.texture.orm_livrer", { a: deux[0], b: deux[1],
            bilan: (d > 0
              ? dzT("cartes.texture.orm_grossit", { p: mo(d) })
              : d < 0
                ? dzT("cartes.texture.orm_maigrit", { p: mo(-d) })
                : dzT("cartes.texture.orm_meme")) })""",
       {"orm_livrer": ("livrer l'ORM <b>à la place</b> des trois séparées : {a} contre {b} — {bilan}, mesuré sur les "
                       "fichiers écrits",
                       "shipping the ORM <b>instead of</b> the three separate maps: {a} versus {b} — {bilan}, measured "
                       "on the written files"),
        "orm_grossit": ("le lot <b>grossirait</b> de {p} (la déflate compresse trois plans corrélés côte à côte moins bien "
                        "que trois gris séparés)",
                        "the batch would <b>grow</b> by {p} (deflate compresses three correlated planes side by side less "
                        "well than three separate grays)"),
        "orm_maigrit": ("le lot maigrirait de {p}", "the batch would shrink by {p}"),
        "orm_meme": ("même poids", "same weight")}),
    LL(2571, " Ko", "u_ko", " KB", contexte=True),

    # ── écritures et réseau ──
    LL(2653, "Backend /api/cards/…/texture absent : les deux couches 2D fonctionnent, la dérivation PBR non.",
       "backend_absent", "Backend /api/cards/…/texture missing: both 2D layers work, PBR derivation does not."),
    LL(2654, "Backend : ", "backend_err", "Backend: "),
    LL(2688, "rendu de la carte à l'échelle 1…", "busy_rendu", "rendering the card at 1:1…"),
    SS(2690, '"envoi de la source (" + Math.round(blob.size / 1024) + " Ko)…"',
       'dzT("cartes.texture.busy_envoi", { ko: Math.round(blob.size / 1024) })',
       {"busy_envoi": ("envoi de la source ({ko} Ko)…", "uploading the source ({ko} KB)…")}),
    SS(2692, '"dérivation des 8 maps " + (s.pbr.square ? s.pbr.res + " x " + s.pbr.res : "à " + s.pbr.res + " px") + "…"',
       'dzT("cartes.texture.busy_derive", { taille: (s.pbr.square ? s.pbr.res + " x " + s.pbr.res'
       ' : dzT("cartes.texture.a_px", { n: s.pbr.res })) })',
       {"busy_derive": ("dérivation des 8 maps {taille}…", "deriving the 8 maps {taille}…"),
        "a_px": ("à {n} px", "at {n} px")}),
    SS(2709, """(REPORT ? REPORT.maps.length : 0) + " maps dérivées en "
        + ((Date.now() - t0) / 1000).toFixed(1) + " s"
        + (plates > 0 ? " — " + plates + " constante" + (plates > 1 ? "s" : "") : "")""",
       """dzT("cartes.texture.derivees", { n: REPORT ? REPORT.maps.length : 0,
          s: ((Date.now() - t0) / 1000).toFixed(1) })
        + (plates > 0 ? " — " + dzT(plates > 1 ? "cartes.texture.constantes.plusieurs"
          : "cartes.texture.constantes.un", { n: plates }) : "")""",
       {"derivees": ("{n} maps dérivées en {s} s", "{n} maps derived in {s} s")}),
    LL(2715, "Backend /api/cards/…/texture absent : les deux couches 2D fonctionnent, la dérivation PBR non.",
       "backend_absent", "Backend /api/cards/…/texture missing: both 2D layers work, PBR derivation does not."),
    LL(2716, "Dérivation : ", "derivation_err", "Derivation: "),
    SS(2728, '"téléchargement de " + kind + "…"', 'dzT("cartes.texture.busy_dl", { kind: kind })',
       {"busy_dl": ("téléchargement de {kind}…", "downloading {kind}…")}),
    LL(2736, "planche des 8 maps…", "busy_planche", "8-map sheet…"),
    LL(2745, "manifeste du lot…", "busy_manifeste", "batch manifest…"),
    LL(2748, "manifeste : espaces colorimétriques, densité physique, conventions, SHA-256", "manifeste_toast",
       "manifest: color spaces, physical density, conventions, SHA-256"),
]
