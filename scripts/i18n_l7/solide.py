"""t147 — solide : js/mod-solid.js (pièce Volume) et js/mod-capture.js (pièce Import), entiers.

Traduit : gabarit HTML des deux panneaux, libellés des tableaux (épaisseurs, vues, lumières, tranches, reliefs,
poses, côtés), étiquettes d'annulation (montrées dans le toast « annulé : … »), HUD et paragraphe des cartes de
matière du Volume (phrases recomposées en clés à variables), bordereau du tourne-disque, relevé, détourage IA,
parcours « Et maintenant », toasts, messages d'erreur montrés (panne, refus, motifs).
GARDÉ : le JSON écrit dans le GLB (generator, notes, noms de nœud/matériau : contenu de fichier exporté), les gardes
de chargement et console.*, les noms de fichiers (source_recto.png, …_tourne-disque.), les ids/sélecteurs, le
message interne « route absente » (jamais affiché : panne() dit « backend absent »), les locales toLocaleString,
les unités seules (Kio, o, px).
Le libellé du détourage est comparé à lui-même avant/après relecture des tarifs (même langue des deux côtés) ;
le remplacement « Détourer » → « Redétourer » passe par deux clés (contexte) pour marcher en anglais.
"""
from outils import L, S, X, H

N = "\r\n"
F = "js/mod-solid.js"
C = "js/mod-capture.js"


def T(fichier, ligne, avant, cle, fr, en, contexte=False):
    """texte HTML dans une chaîne '…' de gabarit : `avant` (sans guillemets) devient ' + dzT(cle) + '."""
    d = (fr, en, "contexte") if contexte else (fr, en)
    return S(fichier, ligne, avant, avant.replace(fr, "' + dzT(\"%s\") + '" % cle, 1), {cle: d})


def P(pre, e):
    """préfixe l'ancre par le début du littéral (guillemet compris) : le contrôle des restes veut l'ouverture couverte."""
    e["avant"] = pre + e["avant"]
    e["apres"] = pre + e["apres"]
    return e


ENTREES = [
    # ── mod-solid.js : gardes ────────────────────────────────────────────────────────────────────────────────
    X(F, 59, '"mod-solid: js/core.js doit etre charge avant ce fichier"', "garde de chargement"),
    X(F, 259, '"cardforge: solid — valeurs PBR divergentes entre l\'ecran et le backend"', "console.warn"),

    # ── tableaux de libellés ─────────────────────────────────────────────────────────────────────────────────
    L(F, 77, '"Fine"', "cartes.solid.ep_fine", "Fine", "Thin", contexte=True),
    L(F, 77, '"carte promotionnelle"', "cartes.solid.ep_fine_h", "carte promotionnelle", "promo card"),
    L(F, 78, '"Carte à jouer"', "cartes.solid.ep_jouer", "Carte à jouer", "Playing card"),
    L(F, 78, '"standard, cœur bleu 310 g"', "cartes.solid.ep_jouer_h", "standard, cœur bleu 310 g",
      "standard, 310 gsm blue core"),
    L(F, 79, '"Lin renforcé"', "cartes.solid.ep_lin", "Lin renforcé", "Reinforced linen"),
    L(F, 79, '"jeu de société"', "cartes.solid.ep_lin_h", "jeu de société", "board game"),
    L(F, 80, '"Carton épais"', "cartes.solid.ep_carton", "Carton épais", "Thick stock"),
    L(F, 80, '"carte de collection premium"', "cartes.solid.ep_carton_h", "carte de collection premium",
      "premium collectible card"),
    L(F, 81, '"Plaque"', "cartes.solid.ep_plaque", "Plaque", "Plate"),
    L(F, 81, '"carte métal / plastique"', "cartes.solid.ep_plaque_h", "carte métal / plastique",
      "metal / plastic card"),
    L(F, 84, '"Matière"', "cartes.solid.vue_matiere", "Matière", "Material"),
    L(F, 84, '"Rendu éclairé, comme un tirage réel"', "cartes.solid.vue_matiere_t",
      "Rendu éclairé, comme un tirage réel", "Lit render, like a real print"),
    L(F, 85, '"Encre"', "cartes.solid.vue_encre", "Encre", "Ink"),
    L(F, 85, '"Sans éclairage : l\'impression telle quelle"', "cartes.solid.vue_encre_t",
      "Sans éclairage : l'impression telle quelle", "Unlit: the print as is"),
    L(F, 86, '"Normales"', "cartes.solid.vue_normales", "Normales", "Normals"),
    L(F, 86, '"Orientation des faces (couleur = normale)"', "cartes.solid.vue_normales_t",
      "Orientation des faces (couleur = normale)", "Face orientation (color = normal)"),
    L(F, 87, '"Îlots UV"', "cartes.solid.ilots", "Îlots UV", "UV islands"),
    L(F, 87, '"Recto / verso / tranche : les 3 régions de l\'atlas, dont le HUD mesure le recouvrement"',
      "cartes.solid.vue_ilots_t",
      "Recto / verso / tranche : les 3 régions de l'atlas, dont le HUD mesure le recouvrement",
      "Front / back / edge: the 3 atlas regions, whose overlap the HUD measures"),
    L(F, 90, '"Vitrine"', "cartes.solid.env_vitrine", "Vitrine", "Showcase"),
    L(F, 91, '"Chaud"', "cartes.solid.env_chaud", "Chaud", "Warm"),
    L(F, 91, '"Froid"', "cartes.solid.env_froid", "Froid", "Cool"),
    L(F, 92, '"Neutre"', "cartes.solid.env_neutre", "Neutre", "Neutral"),
    L(F, 95, '"Unie"', "cartes.solid.tr_unie", "Unie", "Plain"),
    L(F, 95, '"Métal"', "cartes.solid.tr_metal", "Métal", "Metal"),
    L(F, 95, '"Sombre"', "cartes.solid.tr_sombre", "Sombre", "Dark"),
    L(F, 104, '"Aucun"', "cartes.solid.rel_aucun", "Aucun", "None"),
    L(F, 104, '"Pas de carte de normales dans le fichier"', "cartes.solid.rel_aucun_t",
      "Pas de carte de normales dans le fichier", "No normal map in the file"),
    L(F, 105, '"Léger"', "cartes.solid.rel_leger", "Léger", "Light"),
    L(F, 105, '"Quart de l\'atlas : le relief d\'encre pour un quart des texels"', "cartes.solid.rel_leger_t",
      "Quart de l'atlas : le relief d'encre pour un quart des texels",
      "Quarter of the atlas: ink relief for a quarter of the texels"),
    L(F, 106, '"Détaillé"', "cartes.solid.rel_detaille", "Détaillé", "Detailed"),
    L(F, 106, '"Moitié de l\'atlas : le plus fin que la source permette"', "cartes.solid.rel_detaille_t",
      "Moitié de l'atlas : le plus fin que la source permette", "Half of the atlas: the finest the source allows"),
    L(F, 112, '"Recto"', "cartes.solid.recto", "Recto", "Front"),
    L(F, 112, '"La face avant, de face"', "cartes.solid.pose_recto_t", "La face avant, de face",
      "The front face, head-on"),
    L(F, 113, '"Verso"', "cartes.solid.verso", "Verso", "Back"),
    L(F, 113, '"La face arrière, de face — sans miroir"', "cartes.solid.pose_verso_t",
      "La face arrière, de face — sans miroir", "The back face, head-on — not mirrored"),
    L(F, 119, '"Tranche"', "cartes.solid.tranche", "Tranche", "Edge", contexte=True),
    L(F, 120, '"Macro sur le coin : rayon, chanfrein et épaisseur à l\'échelle du millimètre"',
      "cartes.solid.pose_tranche_t",
      "Macro sur le coin : rayon, chanfrein et épaisseur à l'échelle du millimètre",
      "Corner macro: radius, chamfer and thickness at millimeter scale"),

    # ── init ─────────────────────────────────────────────────────────────────────────────────────────────────
    L(F, 247, '"Tourne-disque indisponible — ffmpeg absent"', "cartes.solid.tt_indispo",
      "Tourne-disque indisponible — ffmpeg absent", "Turntable unavailable — ffmpeg missing"),
    S(F, 264, "'Maillage <b>card</b> enregistré côté serveur : '" + N
      + "            + r.triangles + ' faces / ' + r.vertices + ' sommets — la sphère de repli en compte '" + N
      + "            + s.triangles + '. L\\'export 3D ne peut donc pas livrer une boule à la place de la carte.'",
      'dzT("cartes.solid.reg", { tri: r.triangles, som: r.vertices, sph: s.triangles })',
      {"cartes.solid.reg": (
          "Maillage <b>card</b> enregistré côté serveur : {tri} faces / {som} sommets — la sphère de repli en "
          "compte {sph}. L'export 3D ne peut donc pas livrer une boule à la place de la carte.",
          "Mesh <b>card</b> registered on the server: {tri} faces / {som} vertices — the fallback sphere has "
          "{sph}. The 3D export therefore cannot ship a ball instead of the card.")}),

    # ── gabarit ──────────────────────────────────────────────────────────────────────────────────────────────
    S(F, 282, 'title="Filaire (W)">\' + ICO("dz-lab3d-filaire", 16, "cf-ic") + \'Filaire</button>\'',
      'title="\' + dzT("cartes.solid.filaire_w") + \'">\' + ICO("dz-lab3d-filaire", 16, "cf-ic") + '
      'dzT("cartes.solid.filaire_btn") + \'</button>\'',
      {"cartes.solid.filaire_w": ("Filaire (W)", "Wireframe (W)"),
       "cartes.solid.filaire_btn": ("Filaire", "Wireframe")}),
    T(F, 283, 'title="Tourne-disque (R)">', "cartes.solid.tt_r", "Tourne-disque (R)", "Turntable (R)"),
    P('\'        <button type="button" class="btn sm cf-solid-z" data-z="-1" ', S(F, 296, 'title="Zoom arrière (molette)" aria-label="Zoom arrière">',
      'title="\' + dzT("cartes.solid.zoom_arr_t") + \'" aria-label="\' + dzT("cartes.solid.zoom_arr") + \'">',
      {"cartes.solid.zoom_arr_t": ("Zoom arrière (molette)", "Zoom out (wheel)"),
       "cartes.solid.zoom_arr": ("Zoom arrière", "Zoom out")})),
    S(F, 298, 'title="Zoom avant (molette)" aria-label="Zoom avant">',
      'title="\' + dzT("cartes.solid.zoom_av_t") + \'" aria-label="\' + dzT("cartes.solid.zoom_av") + \'">',
      {"cartes.solid.zoom_av_t": ("Zoom avant (molette)", "Zoom in (wheel)"),
       "cartes.solid.zoom_av": ("Zoom avant", "Zoom in")}),
    T(F, 299, '<i class="cf-solid-zh">glisser = tourner · clic droit = déplacer</i>', "cartes.solid.souris",
      "glisser = tourner · clic droit = déplacer", "drag = rotate · right-click = pan"),
    T(F, 301, '<span class="lbl">Lumière</span>', "cartes.solid.lumiere", "Lumière", "Light"),
    P('\'      <label class="btn sm cf-solid-hdrib" ', T(F, 306, 'title="Importer un environnement : .hdr, .exr ou une image">', "cartes.solid.hdri_t",
      "Importer un environnement : .hdr, .exr ou une image", "Import an environment: .hdr, .exr or an image")),
    P('\'      <button type="button" class="btn sm cf-solid-fit" ', S(F, 308, 'title="Recadrer la caméra (F)">\' + ICO("dz-action-ajuster-vue", 16, "cf-ic") + \'Recadrer</button>\'',
      'title="\' + dzT("cartes.solid.recadrer_t") + \'">\' + ICO("dz-action-ajuster-vue", 16, "cf-ic") + '
      'dzT("cartes.solid.recadrer") + \'</button>\'',
      {"cartes.solid.recadrer_t": ("Recadrer la caméra (F)", "Reframe the camera (F)"),
       "cartes.solid.recadrer": ("Recadrer", "Reframe", "contexte")})),
    P('\'        min-field-of-view="8deg" max-field-of-view="55deg" ', T(F, 314, 'alt="Aperçu en volume de la carte">', "cartes.solid.mv_alt", "Aperçu en volume de la carte",
      "3D preview of the card")),
    T(F, 318, 'cf-solid-abort">annuler</button>', "cartes.solid.annuler", "annuler", "undo"),
    T(F, 329, '<b>Épaisseur</b>', "cartes.solid.epaisseur", "Épaisseur", "Thickness"),
    T(F, 341, '<b>Coins et tranche</b>', "cartes.solid.coins", "Coins et tranche", "Corners and edge"),
    T(F, 342, '> suivre le format</label>', "cartes.solid.suivre_format", "suivre le format", "match the format"),
    T(F, 344, 'cf-solid-lb">Rayon</span>', "cartes.solid.rayon", "Rayon", "Radius"),
    T(F, 349, 'cf-solid-lb">Finesse</span>', "cartes.solid.finesse", "Finesse", "Smoothness"),
    S(F, 354, 'title="Retrait du chanfrein : la même jambe en Z et en XY, donc une arête à 45°">Retrait</span>',
      'title="\' + dzT("cartes.solid.retrait_t") + \'">\' + dzT("cartes.solid.retrait") + \'</span>',
      {"cartes.solid.retrait_t": ("Retrait du chanfrein : la même jambe en Z et en XY, donc une arête à 45°",
                                  "Chamfer inset: the same leg in Z and in XY, hence a 45° edge"),
       "cartes.solid.retrait": ("Retrait", "Inset", "contexte")}),
    S(F, 360, 'cf-solid-lb">Tranche</span>', 'cf-solid-lb">\' + dzT("cartes.solid.tranche") + \'</span>', {}),
    P('\'        <span class="lbl cf-solid-lb" ', S(F, 368, 'title="Carte de normales : le grain d\\\'encre. Son poids est mesuré ci-dessous.">',
      'title="\' + dzT("cartes.solid.relief_t") + \'">',
      {"cartes.solid.relief_t": ("Carte de normales : le grain d'encre. Son poids est mesuré ci-dessous.",
                                 "Normal map: the ink grain. Its weight is measured below.")})),
    T(F, 375, '<b>Tourne-disque</b>', "cartes.solid.tt", "Tourne-disque", "Turntable"),
    T(F, 377, '<span class="lbl">Images</span>', "cartes.solid.images", "Images", "Frames", contexte=True),
    T(F, 378, '<span class="lbl">Images / s</span>', "cartes.solid.images_s", "Images / s", "Frames / s"),
    T(F, 381, '<span class="lbl">Définition</span>', "cartes.solid.definition", "Définition", "Resolution",
      contexte=True),
    T(F, 385, 'cf-solid-lb">Élévation</span>', "cartes.solid.elevation", "Élévation", "Elevation"),
    T(F, 390, 'cf-solid-go">Rendre le tourne-disque &mdash; local, gratuit</button>', "cartes.solid.tt_go",
      "Rendre le tourne-disque &mdash; local, gratuit", "Render the turntable &mdash; local, free"),
    T(F, 395, '<summary>Rendu et raccourcis</summary>', "cartes.solid.rendu", "Rendu et raccourcis",
      "Rendering and shortcuts"),
    T(F, 397, 'cf-solid-lb">Exposition</span>', "cartes.solid.exposition", "Exposition", "Exposure"),
    T(F, 400, 'cf-solid-lb">Ombre</span>', "cartes.solid.ombre", "Ombre", "Shadow"),
    S(F, 404, '<span class="lbl">Plafond de l\\\'atlas</span>',
      '<span class="lbl">\' + dzT("cartes.solid.plafond") + \'</span>',
      {"cartes.solid.plafond": ("Plafond de l'atlas", "Atlas cap")}),
    T(F, 411, '<span class="lbl">Image de base</span>', "cartes.solid.image_base", "Image de base", "Base image"),
    T(F, 413, '>JPEG — léger (4:2:0)</option>', "cartes.solid.fmt_jpeg", "JPEG — léger (4:2:0)",
      "JPEG — light (4:2:0)"),
    T(F, 414, '>JPEG — chroma pleine (4:4:4)</option>', "cartes.solid.fmt_jpeg444", "JPEG — chroma pleine (4:4:4)",
      "JPEG — full chroma (4:4:4)"),
    T(F, 415, '>PNG — sans perte</option>', "cartes.solid.fmt_png", "PNG — sans perte", "PNG — lossless"),
    P("'          <dt>+ &nbsp;&minus;</dt>", T(F, 419, '<dd>épaisseur &plusmn; 0,01 mm</dd>', "cartes.solid.k_ep", "épaisseur &plusmn; 0,01 mm",
      "thickness &plusmn; 0.01 mm")),
    T(F, 420, '<dd>rayon de coin &plusmn; 0,5 mm</dd>', "cartes.solid.k_rayon", "rayon de coin &plusmn; 0,5 mm",
      "corner radius &plusmn; 0.5 mm"),
    P("'          <dt>1 &hellip; 4</dt>", T(F, 421, '<dd>vue (matière, encre, normales, îlots)</dd>', "cartes.solid.k_vue",
      "vue (matière, encre, normales, îlots)", "view (material, ink, normals, islands)")),
    T(F, 422, '<dd>filaire</dd>', "cartes.solid.filaire", "filaire", "wireframe"),
    S(F, 423, '<dd>recadrer</dd><dt>T</dt><dd>tourne-disque</dd>',
      '<dd>\' + dzT("cartes.solid.k_recadrer") + \'</dd><dt>T</dt><dd>\' + dzT("cartes.solid.k_tt") + \'</dd>',
      {"cartes.solid.k_recadrer": ("recadrer", "reframe"),
       "cartes.solid.k_tt": ("tourne-disque", "turntable")}),
    P("'          <dt>Ctrl+Z</dt>", T(F, 424, '<dd>annuler le dernier réglage</dd>', "cartes.solid.k_undo", "annuler le dernier réglage",
      "undo the last setting")),
    P("'        ", T(F, 426, '<p class="hint">Les champs numériques se règlent aussi à la <b>molette</b> et au <b>glissé horizontal</b>.</p>',
      "cartes.solid.k_hint",
      "Les champs numériques se règlent aussi à la <b>molette</b> et au <b>glissé horizontal</b>.",
      "Number fields can also be set with the <b>mouse wheel</b> or by <b>dragging horizontally</b>.")),
    # ── annulation ───────────────────────────────────────────────────────────────────────────────────────────
    L(F, 490, '"rien à annuler"', "cartes.solid.rien_annuler", "rien à annuler", "nothing to undo"),
    S(F, 492, '"annulé : " + u.label', 'dzT("cartes.solid.annule", { label: u.label })',
      {"cartes.solid.annule": ("annulé : {label}", "undone: {label}")}),
    S(F, 517, "t + ' px maxi</option>'", 'dzT("cartes.solid.px_maxi", { t: t }) + \'</option>\'',
      {"cartes.solid.px_maxi": ("{t} px maxi", "{t} px max")}),
    L(F, 530, '"vue"', "cartes.solid.u_vue", "vue", "view"),
    L(F, 532, '"filaire"', "cartes.solid.filaire", "filaire", "wireframe"),
    L(F, 534, '"style de tranche"', "cartes.solid.u_style", "style de tranche", "edge style"),
    L(F, 536, '"relief d\'encre"', "cartes.solid.u_relief", "relief d'encre", "ink relief"),
    L(F, 538, '"épaisseur"', "cartes.solid.u_ep", "épaisseur", "thickness"),
    L(F, 694, '"suivre le format"', "cartes.solid.suivre_format", "suivre le format", "match the format"),
    L(F, 696, '"couleur de tranche"', "cartes.solid.u_couleur", "couleur de tranche", "edge color"),
    L(F, 697, '"lumière"', "cartes.solid.u_lumiere", "lumière", "light"),
    S(F, 713, '"HDRI : " + f.name.slice(0, 22)', 'dzT("cartes.solid.hdri_nom", { nom: f.name.slice(0, 22) })',
      {"cartes.solid.hdri_nom": ("HDRI : {nom}", "HDRI: {nom}")}),
    L(F, 717, '"HDRI importé"', "cartes.solid.u_hdri", "HDRI importé", "HDRI imported"),
    S(F, 718, '"environnement importé : " + f.name + " (" + fr(f.size / 1024, 0) + " Kio)"',
      'dzT("cartes.solid.env_importe", { nom: f.name, kio: fr(f.size / 1024, 0) })',
      {"cartes.solid.env_importe": ("environnement importé : {nom} ({kio} Kio)",
                                    "environment imported: {nom} ({kio} KiB)")}),
    L(F, 723, '"image de base"', "cartes.solid.u_image", "image de base", "base image"),
    L(F, 725, '"définition"', "cartes.solid.u_definition", "définition", "resolution"),
    L(F, 726, '"format vidéo"', "cartes.solid.u_fmt_video", "format vidéo", "video format"),
    L(F, 772, '"épaisseur"', "cartes.solid.u_ep", "épaisseur", "thickness"),
    L(F, 773, '"épaisseur"', "cartes.solid.u_ep", "épaisseur", "thickness"),
    L(F, 774, '"rayon"', "cartes.solid.u_rayon", "rayon", "radius"),
    L(F, 775, '"rayon"', "cartes.solid.u_rayon", "rayon", "radius"),
    L(F, 776, '"filaire"', "cartes.solid.filaire", "filaire", "wireframe"),
    L(F, 780, '"vue"', "cartes.solid.u_vue", "vue", "view"),

    # ── synchronisation ──────────────────────────────────────────────────────────────────────────────────────
    S(F, 816, "f + ' images @ ' + fps + ' i/s'", 'dzT("cartes.solid.images_fps", { n: f, fps: fps })',
      {"cartes.solid.images_fps": ("{n} images @ {fps} i/s", "{n} frames @ {fps} fps")}),
    S(F, 818, "'<b>' + up + '&deg;</b> au-dessus de l\\'horizon &mdash; angle polaire '" + N
      + "      + fr(90 - up, 0) + '&deg; posé sur la visionneuse, et relu sur elle après le rendu.'",
      'dzT("cartes.solid.elev_hint", { up: up, polaire: fr(90 - up, 0) })',
      {"cartes.solid.elev_hint": (
          "<b>{up}&deg;</b> au-dessus de l'horizon &mdash; angle polaire {polaire}&deg; posé sur la visionneuse, "
          "et relu sur elle après le rendu.",
          "<b>{up}&deg;</b> above the horizon &mdash; polar angle {polaire}&deg; set on the viewer, and read back "
          "from it after rendering.")}),
    S(F, 822, "'<i style=\"background:#29b89e\"></i>recto<i style=\"background:#8c6bdc\"></i>verso"
      "<i style=\"background:#f2b53d\"></i>tranche'",
      "'<i style=\"background:#29b89e\"></i>' + dzT(\"cartes.solid.l_recto\") + '<i style=\"background:#8c6bdc\">"
      "</i>' + dzT(\"cartes.solid.l_verso\") + '<i style=\"background:#f2b53d\"></i>' + dzT(\"cartes.solid.l_tranche\")",
      {"cartes.solid.l_recto": ("recto", "front"), "cartes.solid.l_verso": ("verso", "back"),
       "cartes.solid.l_tranche": ("tranche", "edge", "contexte")}),
    S(F, 914, '"coupe · 1 mm = " + K + " px, cote " + fr(h, 1) + " px · retrait "' + N
      + '      + fr(bv, 3) + " mm"',
      'dzT("cartes.solid.coupe", { k: K, cote: fr(h, 1), retrait: fr(bv, 3) })',
      {"cartes.solid.coupe": ("coupe · 1 mm = {k} px, cote {cote} px · retrait {retrait} mm",
                              "section · 1 mm = {k} px, dimension {cote} px · inset {retrait} mm")}),
    S(F, 929, "'Aucun chanfrein : l\\'arête entre la face et la tranche est vive.'",
      'dzT("cartes.solid.chanfrein_aucun")',
      {"cartes.solid.chanfrein_aucun": ("Aucun chanfrein : l'arête entre la face et la tranche est vive.",
                                        "No chamfer: the corner between the face and the edge is sharp.")}),
    S(F, 932, "'Chanfrein à <b>45°</b> : retrait <b>' + fr(bv, 3)" + N
      + "      + ' mm</b> en Z <i>et</i> en XY, méplat ' + fr(bv * Math.SQRT2, 3) + ' mm.'" + N
      + "      + ((dem - bv) > 5e-4" + N
      + "        ? ' Demande ' + fr(dem, 2) + ' mm <b>bornée</b> par l\\'épaisseur (0,225 × '" + N
      + "        + fr(th, 2) + ' mm) : le fichier porte ' + fr(bv, 3) + ', pas ' + fr(dem, 2) + '.'",
      'dzT("cartes.solid.chanfrein", { r: fr(bv, 3), m: fr(bv * Math.SQRT2, 3) })' + N
      + "      + ((dem - bv) > 5e-4" + N
      + '        ? dzT("cartes.solid.chanfrein_borne", { dem: fr(dem, 2), th: fr(th, 2), r: fr(bv, 3) })',
      {"cartes.solid.chanfrein": ("Chanfrein à <b>45°</b> : retrait <b>{r} mm</b> en Z <i>et</i> en XY, méplat {m} mm.",
                                  "<b>45°</b> chamfer: inset <b>{r} mm</b> in Z <i>and</i> in XY, flat {m} mm."),
       "cartes.solid.chanfrein_borne": (
           " Demande {dem} mm <b>bornée</b> par l'épaisseur (0,225 × {th} mm) : le fichier porte {r}, pas {dem}.",
           " Requested {dem} mm <b>capped</b> by the thickness (0.225 × {th} mm): the file carries {r}, not {dem}.")}),

    # ── HUD : types relus ────────────────────────────────────────────────────────────────────────────────────
    L(F, 1535, '"gris"', "cartes.solid.png_gris", "gris", "gray"),
    L(F, 1535, '"gris+A"', "cartes.solid.png_gris_a", "gris+A", "gray+A"),
    L(F, 1804, '"N&B"', "cartes.solid.nb", "N&B", "B&W"),
    S(F, 2410, '("PNG " + pngType(img.bytes) + " sans perte")',
      'dzT("cartes.solid.png_sans_perte", { type: pngType(img.bytes) })',
      {"cartes.solid.png_sans_perte": ("PNG {type} sans perte", "PNG {type} lossless")}),

    # ── GLB : contenu du fichier exporté ─────────────────────────────────────────────────────────────────────
    X(F, 2250, '"Card Forge P5 — apercu"', "generator du GLB exporté"),
    X(F, 2251, '"node.scale met le maillage en metres (glTF 2.0)"', "note écrite dans le GLB exporté"),
    X(F, 2262, '"retrait = jambe du chanfrein a 45 deg, en Z et en XY"', "extras écrits dans le GLB exporté"),

    # ── HUD ──────────────────────────────────────────────────────────────────────────────────────────────────
    S(F, 2484, "(J && J.images ? J.images.length : 0) + ' images : base'",
      'dzT("cartes.solid.n_images_base", { n: J && J.images ? J.images.length : 0 })',
      {"cartes.solid.n_images_base": ("{n} images : base", "{n} images: base")}),
    L(F, 2485, "'+normales'", "cartes.solid.plus_normales", "+normales", "+normals"),
    L(F, 2487, "'base seule · non éclairé'", "cartes.solid.base_seule", "base seule · non éclairé", "base only · unlit"),
    L(F, 2487, "'sommets colorés'", "cartes.solid.sommets_colores", "sommets colorés", "colored vertices"),
    S(F, 2494, "'4:2:0 — chroma ½ (' + Math.round(dpiMin / 2) + ' DPI de couleur au pire axe)'",
      'dzT("cartes.solid.chroma420", { dpi: Math.round(dpiMin / 2) })',
      {"cartes.solid.chroma420": ("4:2:0 — chroma ½ ({dpi} DPI de couleur au pire axe)",
                                  "4:2:0 — ½ chroma ({dpi} color DPI on the worse axis)")}),
    S(F, 2496, "'4:4:4 — chroma pleine (' + Math.round(dpiMin) + ' DPI de couleur)'",
      'dzT("cartes.solid.chroma444", { dpi: Math.round(dpiMin) })',
      {"cartes.solid.chroma444": ("4:4:4 — chroma pleine ({dpi} DPI de couleur)",
                                  "4:4:4 — full chroma ({dpi} color DPI)")}),
    S(F, 2506, "pct(P.ratio_source) + ' en hauteur'", 'dzT("cartes.solid.en_hauteur", { pct: pct(P.ratio_source) })',
      {"cartes.solid.en_hauteur": ("{pct} en hauteur", "{pct} in height")}),
    S(F, 2507, "pct(P.ratio_source_w) + ' en largeur'",
      'dzT("cartes.solid.en_largeur", { pct: pct(P.ratio_source_w) })',
      {"cartes.solid.en_largeur": ("{pct} en largeur", "{pct} in width")}),
    L(F, 2508, "' · échelle 1:1'", "cartes.solid.echelle_11", " · échelle 1:1", " · 1:1 scale"),
    T(F, 2526, '<span>Carte</span>', "cartes.solid.hud_carte", "Carte", "Card", contexte=True),
    T(F, 2531, '<span>Échelle</span>', "cartes.solid.hud_echelle", "Échelle", "Scale"),
    L(F, 2532, "'ABSENTE'", "cartes.solid.absente", "ABSENTE", "MISSING"),
    S(F, 2533, "'node.scale mesuré sur les sommets — 1 unité glTF = 1 m : le fichier s\\'ouvre'" + N
      + "        + ' à la taille ci-dessus, pas à ' + fr(d[1] / (sc * 1000), 2) + ' m'" + N
      + "        : 'le fichier ne porte pas sa taille réelle'",
      'dzT("cartes.solid.hud_echelle_ok", { m: fr(d[1] / (sc * 1000), 2) })' + N
      + '        : dzT("cartes.solid.hud_echelle_ko")',
      {"cartes.solid.hud_echelle_ok": (
          "node.scale mesuré sur les sommets — 1 unité glTF = 1 m : le fichier s'ouvre à la taille ci-dessus, "
          "pas à {m} m",
          "node.scale measured on the vertices — 1 glTF unit = 1 m: the file opens at the size above, not at {m} m"),
       "cartes.solid.hud_echelle_ko": ("le fichier ne porte pas sa taille réelle",
                                       "the file does not carry its real size")}),
    S(F, 2542, '<span>Verso</span>', '<span>\' + dzT("cartes.solid.verso") + \'</span>', {}),
    S(F, 2543, "'à l\\'endroit'", 'dzT("cartes.solid.endroit")',
      {"cartes.solid.endroit": ("à l'endroit", "right way round")}),
    L(F, 2543, "'MIROIR — À CORRIGER'", "cartes.solid.miroir_corriger", "MIROIR — À CORRIGER", "MIRRORED — FIX IT"),
    S(F, 2544, "O.verso.endroit + '/' + O.verso.tri + ' triangles orientés comme le recto'" + N
      + "      + ' vu de son côté · îlot u[' + fr(O.u[0], 2) + ' ; ' + fr(O.u[1], 2) + ']'",
      'dzT("cartes.solid.hud_verso", { ok: O.verso.endroit, tri: O.verso.tri, u0: fr(O.u[0], 2), u1: fr(O.u[1], 2) })',
      {"cartes.solid.hud_verso": (
          "{ok}/{tri} triangles orientés comme le recto vu de son côté · îlot u[{u0} ; {u1}]",
          "{ok}/{tri} triangles oriented like the front seen from its side · island u[{u0} ; {u1}]")}),
    S(F, 2547, "'</b><i>sommets ' + vtx", '\'</b><i>\' + dzT("cartes.solid.hud_sommets", { n: vtx })',
      {"cartes.solid.hud_sommets": ("sommets {n}", "vertices {n}")}),
    L(F, 2548, "' · maillage local'", "cartes.solid.maillage_local", " · maillage local", " · local mesh"),
    S(F, 2552, "'<div class=\"cf-solid-hl\"><span>Îlots UV</span><b>' + I.regions + '&nbsp;régions</b><i>'",
      "'<div class=\"cf-solid-hl\"><span>' + dzT(\"cartes.solid.ilots\") + '</span><b>' + "
      "dzT(\"cartes.solid.hud_regions\", { n: I.regions }) + '</b><i>'",
      {"cartes.solid.hud_regions": ("{n}&nbsp;régions", "{n}&nbsp;regions")}),
    S(F, 2553, "I.chevauche + ' recouvrement sur ' + I.paires + ' paires · '",
      'dzT("cartes.solid.hud_recouv", { n: I.chevauche, p: I.paires })',
      {"cartes.solid.hud_recouv": ("{n} recouvrement sur {p} paires · ", "{n} overlaps out of {p} pairs · ")}),
    S(F, 2554, "tri + '/' + tri + ' dét. < 0 · pire ' + det.toExponential(1).replace(\".\", \",\")",
      'dzT("cartes.solid.hud_det", { tri: tri, pire: det.toExponential(1).replace(".", ",") })',
      {"cartes.solid.hud_det": ("{tri}/{tri} dét. < 0 · pire {pire}", "{tri}/{tri} det. < 0 · worst {pire}")}),
    L(F, 2555, "'MIROIR DÉTECTÉ'", "cartes.solid.miroir_detecte", "MIROIR DÉTECTÉ", "MIRROR DETECTED"),
    S(F, 2556, "I.composantes + ' composantes en comptant les sommets dupliqués à la couture'",
      'dzT("cartes.solid.hud_comp", { n: I.composantes })',
      {"cartes.solid.hud_comp": ("{n} composantes en comptant les sommets dupliqués à la couture",
                                 "{n} components counting the vertices duplicated at the seam")}),
    S(F, 2562, '<span>Recto</span>', '<span>\' + dzT("cartes.solid.recto") + \'</span>', {}),
    L(F, 2564, "' DPI (largeur × hauteur)'", "cartes.solid.dpi_lh", " DPI (largeur × hauteur)", " DPI (width × height)"),
    S(F, 2571, '<span>Tranche</span>', '<span>\' + dzT("cartes.solid.tranche") + \'</span>', {}),
    S(F, 2572, "' DPI</b><i>le long du périmètre (' + fr(peri, 1) + ' mm)'",
      '\' DPI</b><i>\' + dzT("cartes.solid.hud_perimetre", { mm: fr(peri, 1) })',
      {"cartes.solid.hud_perimetre": ("le long du périmètre ({mm} mm)", "along the perimeter ({mm} mm)")}),
    S(F, 2573, "fr(edgeCross, 0) + ' DPI en travers (' + fr(d[2], 2)" + N + "          + ' mm)'",
      'dzT("cartes.solid.hud_travers", { dpi: fr(edgeCross, 0), mm: fr(d[2], 2) })',
      {"cartes.solid.hud_travers": ("{dpi} DPI en travers ({mm} mm)", "{dpi} DPI across ({mm} mm)")}),
    S(F, 2575, "' · bande ' + (P.edge_px_exact || P.edge_px)[0] + ' × '" + N
      + "        + fr((P.edge_px_exact || P.edge_px)[1], 1) + ' px · îlots UV figés par le'" + N
      + "        + ' contrat, le chiffre annoncé est le pire des deux axes'",
      '\' · \' + dzT("cartes.solid.hud_bande", { w: (P.edge_px_exact || P.edge_px)[0], '
      'h: fr((P.edge_px_exact || P.edge_px)[1], 1) })',
      {"cartes.solid.hud_bande": (
          "bande {w} × {h} px · îlots UV figés par le contrat, le chiffre annoncé est le pire des deux axes",
          "strip {w} × {h} px · UV islands frozen by the contract, the figure shown is the worse of the two axes")}),
    L(F, 2581, "'de quoi porter du texte'", "cartes.solid.texte_ok", "de quoi porter du texte", "enough to carry text"),
    L(F, 2582, "'motif oui, texte non'", "cartes.solid.motif_oui", "motif oui, texte non", "pattern yes, text no"),
    L(F, 2582, "'aplat ou dégradé, pas de motif fin'", "cartes.solid.aplat", "aplat ou dégradé, pas de motif fin",
      "flat color or gradient, no fine pattern"),
    S(F, 2583, "' · levier : la définition du document (atlas ' + P.h + ' px pour un plafond de '" + N
      + "        + P.cap + ')</i></div>'",
      '\' · \' + dzT("cartes.solid.hud_levier", { h: P.h, cap: P.cap }) + \'</i></div>\'',
      {"cartes.solid.hud_levier": ("levier : la définition du document (atlas {h} px pour un plafond de {cap})",
                                   "lever: the document resolution (atlas {h} px for a cap of {cap})")}),
    T(F, 2585, '<span>Modèle</span>', "cartes.solid.hud_modele", "Modèle", "Model"),

    # ── paragraphe des cartes de matière ─────────────────────────────────────────────────────────────────────
    S(F, 2598, "'Vue non éclairée : le fichier ne porte que l\\'image de base '" + N
      + "        + '(les cartes de matière n\\'y serviraient à rien).'",
      'dzT("cartes.solid.mt_non_eclaire")',
      {"cartes.solid.mt_non_eclaire": (
          "Vue non éclairée : le fichier ne porte que l'image de base (les cartes de matière n'y serviraient à rien).",
          "Unlit view: the file only carries the base image (material maps would be useless there).")}),
    S(F, 2607, "fr(b / Math.max(1, LAST.bytes) * 100, 1) + ' % du fichier'",
      'dzT("cartes.solid.pct_fichier", { p: fr(b / Math.max(1, LAST.bytes) * 100, 1) })',
      {"cartes.solid.pct_fichier": ("{p} % du fichier", "{p}% of the file")}),
    L(F, 2622, '"zéro"', "cartes.solid.mot_0", "zéro", "zero"),
    L(F, 2622, '"une"', "cartes.solid.mot_1", "une", "one"),
    L(F, 2622, '"deux"', "cartes.solid.mot_2", "deux", "two"),
    L(F, 2622, '"trois"', "cartes.solid.mot_3", "trois", "three"),
    L(F, 2622, '"quatre"', "cartes.solid.mot_4", "quatre", "four"),
    L(F, 2622, '"cinq"', "cartes.solid.mot_5", "cinq", "five"),
    L(F, 2622, '"six"', "cartes.solid.mot_6", "six", "six"),
    S(F, 2623, "'<b>' + (MOTS[nImg] || nImg) + ' image' + (nImg > 1 ? 's' : '') + '</b> pour '" + N
      + "      + (MOTS[nSlot] || nSlot) + ' emplacement' + (nSlot > 1 ? 's' : '')" + N
      + "      + ' de matière — comptées dans le JSON du GLB, pas annoncées : base '",
      'dzT(nImg > 1 ? "cartes.solid.mt_images_plusieurs" : "cartes.solid.mt_images_un", { n: MOTS[nImg] || nImg })' + N
      + '      + dzT(nSlot > 1 ? "cartes.solid.mt_slots_plusieurs" : "cartes.solid.mt_slots_un", { n: MOTS[nSlot] || nSlot })' + N
      + '      + dzT("cartes.solid.mt_base")',
      {"cartes.solid.mt_images_un": ("<b>{n} image</b> pour ", "<b>{n} image</b> for "),
       "cartes.solid.mt_images_plusieurs": ("<b>{n} images</b> pour ", "<b>{n} images</b> for "),
       "cartes.solid.mt_slots_un": ("{n} emplacement de matière", "{n} material slot"),
       "cartes.solid.mt_slots_plusieurs": ("{n} emplacements de matière", "{n} material slots"),
       "cartes.solid.mt_base": (" — comptées dans le JSON du GLB, pas annoncées : base ",
                                " — counted in the GLB JSON, not announced: base ")}),
    S(F, 2627, "', chrominance à demi-définition — c\\'est une perte, pas'" + N
      + "        + ' une option, et elle porte sur le dessin : <b>Rendu et raccourcis → Image de base'" + N
      + "        + ' → chroma pleine</b> la supprime pour environ le double de poids'",
      'dzT("cartes.solid.mt_chroma420")',
      {"cartes.solid.mt_chroma420": (
          ", chrominance à demi-définition — c'est une perte, pas une option, et elle porte sur le dessin : "
          "<b>Rendu et raccourcis → Image de base → chroma pleine</b> la supprime pour environ le double de poids",
          ", half-resolution chroma — this is a loss, not an option, and it affects the artwork: "
          "<b>Rendering and shortcuts → Base image → full chroma</b> removes it for about twice the weight")}),
    S(F, 2631, "', normales ' + ko(nb) + ' en ' + LAST.pbr.normal_px.join('×')",
      'dzT("cartes.solid.mt_normales", { ko: ko(nb), px: LAST.pbr.normal_px.join(\'×\') })',
      {"cartes.solid.mt_normales": (", normales {ko} en {px}", ", normals {ko} at {px}")}),
    S(F, 2632, "', ORM ' + ko(LAST.pbr.orm.bytes.byteLength) + ' en '" + N
      + "      + LAST.pbr.orm_px.join('×') + ' — <b>lue deux fois</b> : rugosité (vert) + métal (bleu) et'" + N
      + "      + ' occlusion (rouge).'",
      'dzT("cartes.solid.mt_orm", { ko: ko(LAST.pbr.orm.bytes.byteLength), px: LAST.pbr.orm_px.join(\'×\') })',
      {"cartes.solid.mt_orm": (
          ", ORM {ko} en {px} — <b>lue deux fois</b> : rugosité (vert) + métal (bleu) et occlusion (rouge).",
          ", ORM {ko} at {px} — <b>read twice</b>: roughness (green) + metal (blue) and occlusion (red).")}),
    S(F, 2635, "' Plus l\\'attribut TANGENT.'", 'dzT("cartes.solid.mt_tangent")',
      {"cartes.solid.mt_tangent": (" Plus l'attribut TANGENT.", " Plus the TANGENT attribute.")}),
    S(F, 2636, "' <b>Relief d\\'encre : Aucun</b> — pas de carte de normales, donc pas'" + N
      + "        + ' d\\'attribut TANGENT non plus : il n\\'aurait rien à orienter.'",
      'dzT("cartes.solid.mt_sans_relief")',
      {"cartes.solid.mt_sans_relief": (
          " <b>Relief d'encre : Aucun</b> — pas de carte de normales, donc pas d'attribut TANGENT non plus : "
          "il n'aurait rien à orienter.",
          " <b>Ink relief: None</b> — no normal map, so no TANGENT attribute either: it would have nothing to orient.")}),
    S(F, 2642, "'<br>Relief d\\'encre <b>' + esc(LAST.pbr.relief_l) + '</b> — ce que les'" + N
      + "        + ' normales achètent, mesuré sur les octets écrits : <b>'" + N
      + "        + fr(R2.max_deg, 2) + '°</b> d\\'inclinaison au maximum, ' + fr(R2.rms_deg, 2)" + N
      + "        + '° en moyenne quadratique, ' + fr(R2.sous1_pct, 1) + ' % des texels sous 1°.'",
      'dzT("cartes.solid.mt_relief", { l: esc(LAST.pbr.relief_l), max: fr(R2.max_deg, 2), '
      'rms: fr(R2.rms_deg, 2), pct: fr(R2.sous1_pct, 1) })',
      {"cartes.solid.mt_relief": (
          "<br>Relief d'encre <b>{l}</b> — ce que les normales achètent, mesuré sur les octets écrits : "
          "<b>{max}°</b> d'inclinaison au maximum, {rms}° en moyenne quadratique, {pct} % des texels sous 1°.",
          "<br>Ink relief <b>{l}</b> — what the normals buy, measured on the written bytes: "
          "<b>{max}°</b> maximum tilt, {rms}° RMS, {pct}% of texels under 1°.")}),
    S(F, 2649, "' La marche d\\'encre s\\'en déduit : pente maximale sur un axe '" + N
      + "        + fr(R2.pente_max * 100, 2) + ' % × pas de texel ' + fr(R2.pas_mm, 4)" + N
      + "        + ' mm = <b>' + fr(R2.relief_mesure_mm * 1000, 1) + ' µm</b> — la consigne partagée'" + N
      + "        + ' avec le backend en demandait ' + fr(R2.relief_demande_mm * 1000, 0)" + N
      + "        + '. C\\'est une épaisseur d\\'encre offset, pas une gravure — et elle coûte '" + N
      + "        + part(nb) + '.'",
      'dzT("cartes.solid.mt_marche", { pente: fr(R2.pente_max * 100, 2), pas: fr(R2.pas_mm, 4), '
      'um: fr(R2.relief_mesure_mm * 1000, 1), dem: fr(R2.relief_demande_mm * 1000, 0), cout: part(nb) })',
      {"cartes.solid.mt_marche": (
          " La marche d'encre s'en déduit : pente maximale sur un axe {pente} % × pas de texel {pas} mm = "
          "<b>{um} µm</b> — la consigne partagée avec le backend en demandait {dem}. C'est une épaisseur d'encre "
          "offset, pas une gravure — et elle coûte {cout}.",
          " The ink step follows: maximum slope on one axis {pente}% × texel pitch {pas} mm = <b>{um} µm</b> — "
          "the target shared with the backend asked for {dem}. It is an offset ink thickness, not an engraving — "
          "and it costs {cout}.")}),
    L(F, 2658, "' écrit ici (filtre choisi ligne par ligne) : pas de canal alpha constant à payer.'",
      "cartes.solid.mt_ecrit_ici", " écrit ici (filtre choisi ligne par ligne) : pas de canal alpha constant à payer.",
      " written here (filter chosen row by row): no constant alpha channel to pay for."),
    L(F, 2659, "' par la toile du navigateur.'", "cartes.solid.mt_toile", " par la toile du navigateur.",
      " by the browser canvas."),
    S(F, 2665, "' <b>' + NM.couleurs + ' couleurs distinctes</b> comptées sur les'" + N
      + "          + ' texels : ' + ko(nb) + ' en palette contre ' + ko(NM.rgb_octets)" + N
      + "          + ' en RGB pour les <b>mêmes</b> texels (empreinte FNV de la source et de la'" + N
      + "          + ' reconstruction comparées avant l\\'écriture), soit '" + N
      + "          + fr((1 - nb / NM.rgb_octets) * 100, 0) + ' % de moins.'",
      'dzT("cartes.solid.mt_palette", { n: NM.couleurs, pal: ko(nb), rgb: ko(NM.rgb_octets), '
      'gain: fr((1 - nb / NM.rgb_octets) * 100, 0) })',
      {"cartes.solid.mt_palette": (
          " <b>{n} couleurs distinctes</b> comptées sur les texels : {pal} en palette contre {rgb} en RGB pour les "
          "<b>mêmes</b> texels (empreinte FNV de la source et de la reconstruction comparées avant l'écriture), "
          "soit {gain} % de moins.",
          " <b>{n} distinct colors</b> counted on the texels: {pal} as palette versus {rgb} as RGB for the "
          "<b>same</b> texels (FNV fingerprints of the source and the reconstruction compared before writing), "
          "i.e. {gain}% less.")}),
    S(F, 2672, "' Profondeur <b>utile</b> comptée sur les texels écrits : '" + N
      + "          + R2.distinctes[0] + ' / ' + R2.distinctes[1] + ' / ' + R2.distinctes[2]" + N
      + "          + ' valeurs distinctes sur 256 (X / Y / Z), soit ' + fr(R2.bits_utiles, 1)" + N
      + "          + ' bits utiles sous un en-tête 8 bits — un en-tête n\\'est pas une mesure.'",
      'dzT("cartes.solid.mt_profondeur", { x: R2.distinctes[0], y: R2.distinctes[1], z: R2.distinctes[2], '
      'bits: fr(R2.bits_utiles, 1) })',
      {"cartes.solid.mt_profondeur": (
          " Profondeur <b>utile</b> comptée sur les texels écrits : {x} / {y} / {z} valeurs distinctes sur 256 "
          "(X / Y / Z), soit {bits} bits utiles sous un en-tête 8 bits — un en-tête n'est pas une mesure.",
          " <b>Useful</b> depth counted on the written texels: {x} / {y} / {z} distinct values out of 256 "
          "(X / Y / Z), i.e. {bits} useful bits under an 8-bit header — a header is not a measurement.")}),
    S(F, 2677, "'<br>Relu dans l\\'ORM écrit : papier rugosité ' + pc(M.face_rough.moy)" + N
      + "      + ' au recto et ' + pc(M.back_rough.moy) + ' au verso (' + pc(M.face_rough.min)" + N
      + "      + ' sous l\\'encre → ' + pc(M.face_rough.max)" + N
      + "      + ' sur le papier nu), métal ' + pc(M.face_metal.max) + '. Tranche « ' + esc(st)" + N
      + "      + ' » : rugosité ' + pc(M.edge_rough.moy) + ', métal ' + pc(M.edge_metal.max)" + N
      + "      + ' (canal bleu : ' + LAST.pbr.metal_vals + ' valeur'" + N
      + "      + (LAST.pbr.metal_vals > 1 ? 's' : '') + ' distincte'" + N
      + "      + (LAST.pbr.metal_vals > 1 ? 's' : '') + ' sur 256).'",
      'dzT("cartes.solid.mt_orm_relu", { r: pc(M.face_rough.moy), rv: pc(M.back_rough.moy), '
      'rmin: pc(M.face_rough.min), rmax: pc(M.face_rough.max), m: pc(M.face_metal.max), st: esc(st), '
      'er: pc(M.edge_rough.moy), em: pc(M.edge_metal.max) })' + N
      + '      + dzT(LAST.pbr.metal_vals > 1 ? "cartes.solid.mt_bleu_plusieurs" : "cartes.solid.mt_bleu_un", '
      '{ n: LAST.pbr.metal_vals })',
      {"cartes.solid.mt_orm_relu": (
          "<br>Relu dans l'ORM écrit : papier rugosité {r} au recto et {rv} au verso ({rmin} sous l'encre → "
          "{rmax} sur le papier nu), métal {m}. Tranche « {st} » : rugosité {er}, métal {em}",
          "<br>Read back from the written ORM: paper roughness {r} on the front and {rv} on the back ({rmin} under "
          "ink → {rmax} on bare paper), metal {m}. Edge “{st}”: roughness {er}, metal {em}"),
       "cartes.solid.mt_bleu_un": (" (canal bleu : {n} valeur distincte sur 256).",
                                   " (blue channel: {n} distinct value out of 256)."),
       "cartes.solid.mt_bleu_plusieurs": (" (canal bleu : {n} valeurs distinctes sur 256).",
                                          " (blue channel: {n} distinct values out of 256).")}),
    S(F, 2688, "' Occlusion (rouge) ' + pc(M.face_ao.min) + ' → ' + pc(M.face_ao.max)" + N
      + "        + ' sur le recto (moyenne ' + pc(M.face_ao.moy) + '), ' + pc(M.edge_ao.min)" + N
      + "        + ' → ' + pc(M.edge_ao.max) + ' sur la tranche : <b>'" + N
      + "        + fr((M.face_ao.max - M.face_ao.min) * 100, 1) + ' %</b> de sa dynamique,'" + N
      + "        + ' un contact d\\'encre et un pincement de tranche — pas une cavité.'",
      'dzT("cartes.solid.mt_occlusion", { a: pc(M.face_ao.min), b: pc(M.face_ao.max), moy: pc(M.face_ao.moy), '
      'c: pc(M.edge_ao.min), d: pc(M.edge_ao.max), p: fr((M.face_ao.max - M.face_ao.min) * 100, 1) })',
      {"cartes.solid.mt_occlusion": (
          " Occlusion (rouge) {a} → {b} sur le recto (moyenne {moy}), {c} → {d} sur la tranche : <b>{p} %</b> de "
          "sa dynamique, un contact d'encre et un pincement de tranche — pas une cavité.",
          " Occlusion (red) {a} → {b} on the front (mean {moy}), {c} → {d} on the edge: <b>{p}%</b> of its range, "
          "an ink contact and an edge pinch — not a cavity.")}),
    S(F, 2693, "'<br><b>metallicFactor ' + pc(LAST.pbr.metal_max) + '</b> : une visionneuse qui perd la'" + N
      + "      + ' texture retombe sur '",
      'dzT("cartes.solid.mt_metal", { m: pc(LAST.pbr.metal_max) })',
      {"cartes.solid.mt_metal": ("<br><b>metallicFactor {m}</b> : une visionneuse qui perd la texture retombe sur ",
                                 "<br><b>metallicFactor {m}</b>: a viewer that loses the texture falls back to ")}),
    L(F, 2695, "'du papier mat, pas sur un lingot de chrome.'", "cartes.solid.mt_mat",
      "du papier mat, pas sur un lingot de chrome.", "matte paper, not a chrome ingot."),
    L(F, 2696, "'la métallicité de la tranche, jamais au-dessus.'", "cartes.solid.mt_metal_tranche",
      "la métallicité de la tranche, jamais au-dessus.", "the edge metalness, never above it."),
    S(F, 2697, "' Le jeu <b>complet</b> du cahier des charges — huit PNG, hauteur et émission'" + N
      + "      + ' comprises — est le livrable de l\\'<b>Export 3D</b> ; ici c\\'est l\\'aperçu.'",
      'dzT("cartes.solid.mt_complet")',
      {"cartes.solid.mt_complet": (
          " Le jeu <b>complet</b> du cahier des charges — huit PNG, hauteur et émission comprises — est le "
          "livrable de l'<b>Export 3D</b> ; ici c'est l'aperçu.",
          " The <b>full</b> set from the spec — eight PNGs, height and emission included — is delivered by "
          "<b>3D Export</b>; this is the preview.")}),
    S(F, 2707, "' Bords des trois îlots <b>dilatés de ' + PAD_EFF.u + ' px</b> en largeur et <b>'" + N
      + "      + PAD_EFF.v + ' px</b> en hauteur, soit la moitié de chaque gouttière arrondie'" + N
      + "      + ' au pixel supérieur (' + fr(gutU, 1) + ' px recto|verso → ' + fr(gutU / 2, 1)" + N
      + "      + ', ' + fr(gutV, 1) + ' px faces|tranche → ' + fr(gutV / 2, 1) + ').'",
      'dzT("cartes.solid.mt_dilat", { u: PAD_EFF.u, v: PAD_EFF.v, gu: fr(gutU, 1), gu2: fr(gutU / 2, 1), '
      'gv: fr(gutV, 1), gv2: fr(gutV / 2, 1) })',
      {"cartes.solid.mt_dilat": (
          " Bords des trois îlots <b>dilatés de {u} px</b> en largeur et <b>{v} px</b> en hauteur, soit la moitié "
          "de chaque gouttière arrondie au pixel supérieur ({gu} px recto|verso → {gu2}, {gv} px faces|tranche → "
          "{gv2}).",
          " Edges of the three islands <b>dilated by {u} px</b> in width and <b>{v} px</b> in height, i.e. half "
          "of each gutter rounded up to the next pixel ({gu} px front|back → {gu2}, {gv} px faces|edge → {gv2}).")}),
    S(F, 2711, "' Reste-t-il du fond entre deux îlots ? <b>' + PAD_EFF.reste.blanc" + N
      + "      + '</b> texel(s) encore au blanc pur sur ' + PAD_EFF.reste.total + ' — compté'" + N
      + "      + ' sur la toile qui est encodée dans le fichier, pas promis'",
      'dzT("cartes.solid.mt_reste", { n: PAD_EFF.reste.blanc, t: PAD_EFF.reste.total })',
      {"cartes.solid.mt_reste": (
          " Reste-t-il du fond entre deux îlots ? <b>{n}</b> texel(s) encore au blanc pur sur {t} — compté sur la "
          "toile qui est encodée dans le fichier, pas promis",
          " Is there background left between two islands? <b>{n}</b> texel(s) still pure white out of {t} — "
          "counted on the canvas encoded in the file, not promised")}),
    L(F, 2715, "' : rien à baver dans le bord de la carte, à aucun niveau de mip.'", "cartes.solid.mt_rien_baver",
      " : rien à baver dans le bord de la carte, à aucun niveau de mip.",
      ": nothing to bleed into the card edge, at any mip level."),
    S(F, 2716, "' : le filtrage d\\'un moteur peut encore les mêler au bord.'", 'dzT("cartes.solid.mt_baver")',
      {"cartes.solid.mt_baver": (" : le filtrage d'un moteur peut encore les mêler au bord.",
                                 ": an engine's filtering may still blend them into the edge.")}),
    L(F, 2717, "' (non puissance de deux) → filtre '", "cartes.solid.mt_npot", " (non puissance de deux) → filtre ",
      " (not a power of two) → filter "),
    L(F, 2719, "', aucun mipmap demandé : aucun avertissement de validateur.'", "cartes.solid.mt_sans_mip",
      ", aucun mipmap demandé : aucun avertissement de validateur.",
      ", no mipmap requested: no validator warning."),

    # ── tourne-disque ────────────────────────────────────────────────────────────────────────────────────────
    L(F, 2861, '"un rendu est déjà en cours"', "cartes.solid.tt_en_cours", "un rendu est déjà en cours",
      "a render is already in progress"),
    L(F, 2868, '"aperçu pas encore prêt"', "cartes.solid.tt_pas_pret", "aperçu pas encore prêt",
      "preview not ready yet"),
    L(F, 2912, '"rendu annulé"', "cartes.solid.tt_annule", "rendu annulé", "render canceled"),
    S(F, 2931, '"image " + (i + 1) + " refusée (" + r.status + ")"',
      'dzT("cartes.solid.tt_refusee", { i: i + 1, status: r.status })',
      {"cartes.solid.tt_refusee": ("image {i} refusée ({status})", "frame {i} rejected ({status})")}),
    S(F, 2933, '"image " + (i + 1) + " / " + n', 'dzT("cartes.solid.tt_prog", { i: i + 1, n: n })',
      {"cartes.solid.tt_prog": ("image {i} / {n}", "frame {i} / {n}")}),
    L(F, 2935, '"encodage ffmpeg…"', "cartes.solid.tt_encodage", "encodage ffmpeg…", "ffmpeg encoding…"),
    S(F, 2945, "rep.frames + ' images @ '" + N
      + "        + rep.fps + ' i/s, ' + fr(rep.seconds, 2) + ' s, ' + size + '×' + size + ', '" + N
      + "        + fr(mo, 2) + ' Mo '",
      'dzT("cartes.solid.tt_out", { n: rep.frames, fps: rep.fps, s: fr(rep.seconds, 2), size: size, mo: fr(mo, 2) })',
      {"cartes.solid.tt_out": ("{n} images @ {fps} i/s, {s} s, {size}×{size}, {mo} Mo ",
                               "{n} frames @ {fps} fps, {s} s, {size}×{size}, {mo} MB ")}),
    L(F, 2947, "'(seuil 8 Mo tenu)'", "cartes.solid.tt_seuil_ok", "(seuil 8 Mo tenu)", "(8 MB limit met)"),
    L(F, 2947, "'(au-dessus de 8 Mo)'", "cartes.solid.tt_seuil_ko", "(au-dessus de 8 Mo)", "(over 8 MB)"),
    S(F, 2948, "' · élévation relue dans la visionneuse : ' + fr(upLu, 1) + '&deg; au-dessus de l\\'horizon'" + N
      + "        + ' (angle polaire ' + fr(90 - upLu, 1) + '&deg;)'",
      'dzT("cartes.solid.tt_elev", { up: fr(upLu, 1), pol: fr(90 - upLu, 1) })',
      {"cartes.solid.tt_elev": (
          " · élévation relue dans la visionneuse : {up}&deg; au-dessus de l'horizon (angle polaire {pol}&deg;)",
          " · elevation read back from the viewer: {up}&deg; above the horizon (polar angle {pol}&deg;)")}),
    S(F, 2950, "' · luminance moyenne de la <b>carte</b> dans les images'" + N
      + "          + ' <b>livrées</b> : ' + fr(lum, 1)" + N
      + "          + '/255 pour un albédo de recto de ' + fr(alb, 1) + '/255, soit '" + N
      + "          + fr(lum / alb * 100, 0) + ' % (' + lumN + ' images échantillonnées ; la carte'" + N
      + "          + ' = les pixels de l\\'image composée plus clairs que le fond peint de plus de '" + N
      + "          + LUM_SEUIL + '/255 — l\\'ombre portée, plus sombre que le fond, en est exclue.'" + N
      + "          + ' Sur la vidéo seule, le fond se retrouve par la médiane temporelle des '" + N
      + "          + rep.frames + ' images)'",
      'dzT("cartes.solid.tt_lum", { lum: fr(lum, 1), alb: fr(alb, 1), pct: fr(lum / alb * 100, 0), n: lumN, '
      'seuil: LUM_SEUIL, total: rep.frames })',
      {"cartes.solid.tt_lum": (
          " · luminance moyenne de la <b>carte</b> dans les images <b>livrées</b> : {lum}/255 pour un albédo de "
          "recto de {alb}/255, soit {pct} % ({n} images échantillonnées ; la carte = les pixels de l'image "
          "composée plus clairs que le fond peint de plus de {seuil}/255 — l'ombre portée, plus sombre que le "
          "fond, en est exclue. Sur la vidéo seule, le fond se retrouve par la médiane temporelle des {total} images)",
          " · mean luminance of the <b>card</b> in the <b>delivered</b> frames: {lum}/255 for a front albedo of "
          "{alb}/255, i.e. {pct}% ({n} frames sampled; the card = the pixels of the composited frame brighter than "
          "the painted background by more than {seuil}/255 — the cast shadow, darker than the background, is "
          "excluded. From the video alone, the background is recovered by the temporal median of the {total} "
          "frames)")}),
    S(F, 2965, "'aucune empreinte d\\'outil ni de machine'", 'dzT("cartes.solid.tt_emp_aucune")',
      {"cartes.solid.tt_emp_aucune": ("aucune empreinte d'outil ni de machine", "no tool or machine fingerprint")}),
    S(F, 2966, "rep.empreintes.total + ' empreinte(s) restantes'",
      'dzT("cartes.solid.tt_emp_n", { n: rep.empreintes.total })',
      {"cartes.solid.tt_emp_n": ("{n} empreinte(s) restantes", "{n} fingerprint(s) remaining")}),
    S(F, 2967, "rep.empreintes.versions + ' version d\\'outil, '" + N
      + "          + rep.empreintes.machine + ' « threads= » (le processeur de la machine), '" + N
      + "          + rep.empreintes.outil + ' nom d\\'encodeur — comptés dans les '" + N
      + "          + rep.empreintes.octets + ' octets du fichier livré'",
      'dzT("cartes.solid.tt_emp_detail", { v: rep.empreintes.versions, m: rep.empreintes.machine, '
      'o: rep.empreintes.outil, b: rep.empreintes.octets })',
      {"cartes.solid.tt_emp_detail": (
          "{v} version d'outil, {m} « threads= » (le processeur de la machine), {o} nom d'encodeur — comptés "
          "dans les {b} octets du fichier livré",
          "{v} tool version, {m} “threads=” (the machine's processor), {o} encoder name — counted in the {b} "
          "bytes of the delivered file")}),
    S(F, 2972, "'. Le conteneur ' + (rep.format === \"webm\" ? 'Matroska' : 'MP4')" + N
      + "            + ' impose un champ d\\'application de multiplexage : il porte « Lavf »,'" + N
      + "            + ' sans version ni machine — c\\'est le seul reste, et il est nommé.'",
      'dzT("cartes.solid.tt_muxeur", { c: rep.format === "webm" ? \'Matroska\' : \'MP4\' })',
      {"cartes.solid.tt_muxeur": (
          ". Le conteneur {c} impose un champ d'application de multiplexage : il porte « Lavf », sans version ni "
          "machine — c'est le seul reste, et il est nommé.",
          ". The {c} container requires a muxing application field: it carries “Lavf”, with no version or "
          "machine — that is the only remnant, and it is named.")}),
    S(F, 2976, '"tourne-disque : " + rep.frames + " images, " + fr(mo, 2) + " Mo"',
      'dzT("cartes.solid.tt_toast", { n: rep.frames, mo: fr(mo, 2) })',
      {"cartes.solid.tt_toast": ("tourne-disque : {n} images, {mo} Mo", "turntable: {n} frames, {mo} MB")}),

    # ═════ mod-capture.js ════════════════════════════════════════════════════════════════════════════════════
    X(C, 43, '"mod-capture: js/core.js doit etre charge avant ce fichier"', "garde de chargement"),
    L(C, 55, '"Recto"', "cartes.capture.recto", "Recto", "Front"),
    L(C, 56, '"Verso"', "cartes.capture.verso", "Verso", "Back"),
    S(C, 233, '"confiance " + num(v, 2) : "confiance inconnue"',
      'dzT("cartes.capture.confiance", { v: num(v, 2) }) : dzT("cartes.capture.confiance_inconnue")',
      {"cartes.capture.confiance": ("confiance {v}", "confidence {v}"),
       "cartes.capture.confiance_inconnue": ("confiance inconnue", "confidence unknown")}),
    L(C, 315, '"Détourer le sujet"', "cartes.capture.detourer", "Détourer le sujet", "Cut out subject"),
    L(C, 317, '"les voies de détourage n\'ont pas encore été lues sur ce poste"', "cartes.capture.voies_pas_lues",
      "les voies de détourage n'ont pas encore été lues sur ce poste",
      "this computer's cutout options have not been read yet"),
    L(C, 322, '"aucune voie de détourage n\'est disponible sur ce poste"', "cartes.capture.aucune_voie",
      "aucune voie de détourage n'est disponible sur ce poste", "no cutout option is available on this computer"),
    L(C, 326, '"déposez d\'abord un recto : le sujet s\'isole sur lui"', "cartes.capture.recto_d_abord_sujet",
      "déposez d'abord un recto : le sujet s'isole sur lui", "drop a front first: the subject is isolated from it"),
    S(C, 337, '"le tarif du détourage n\'est pas dans la table de "' + N
      + '        + "l\'application (Réglages → Tarifs et budget) : le prix se dit AVANT "' + N
      + '        + "l\'appel, donc l\'option payante n\'est pas proposée"',
      'dzT("cartes.capture.sans_tarif")',
      {"cartes.capture.sans_tarif": (
          "le tarif du détourage n'est pas dans la table de l'application (Réglages → Tarifs et budget) : le prix "
          "se dit AVANT l'appel, donc l'option payante n'est pas proposée",
          "the cutout price is not in the app's price table (Settings → Pricing and budget): the price is stated "
          "BEFORE the call, so the paid option is not offered")}),
    L(C, 344, '"Détourer le sujet — gratuit (local)"', "cartes.capture.detourer_local",
      "Détourer le sujet — gratuit (local)", "Cut out subject — free (local)"),
    S(C, 345, '"Détourer le sujet (fal, ~" + num(s.prix_usd, 3) + " $)"',
      'dzT("cartes.capture.detourer_fal", { prix: num(s.prix_usd, 3) })',
      {"cartes.capture.detourer_fal": ("Détourer le sujet (fal, ~{prix} $)", "Cut out subject (fal, ~${prix})")}),
    L(C, 356, '"non mesuré"', "cartes.capture.non_mesure", "non mesuré", "not measured"),
    S(C, 358, '"pourtour " + String(g.color || "?")', 'dzT("cartes.capture.pourtour", { c: String(g.color || "?") })',
      {"cartes.capture.pourtour": ("pourtour {c}", "surround {c}")}),
    S(C, 360, '"le détourage garderait " + num(g.couverture * 100, 1)' + N + '            + " % de l\'image"',
      'dzT("cartes.capture.garderait", { p: num(g.couverture * 100, 1) })',
      {"cartes.capture.garderait": ("le détourage garderait {p} % de l'image", "the cutout would keep {p}% of the image")}),
    L(C, 363, '"mesure hors bornes"', "cartes.capture.hors_bornes", "mesure hors bornes", "measurement out of bounds"),
    S(C, 365, '"détourage local refusé — " + motif', 'dzT("cartes.capture.refuse", { motif: motif })',
      {"cartes.capture.refuse": ("détourage local refusé — {motif}", "local cutout refused — {motif}")}),
    S(C, 366, '"uniformité du pourtour " + num(g.uniformite, 2)' + N + '      + " pour un plancher de " + num(g.seuil, 2)',
      'dzT("cartes.capture.uniformite", { u: num(g.uniformite, 2), s: num(g.seuil, 2) })',
      {"cartes.capture.uniformite": ("uniformité du pourtour {u} pour un plancher de {s}",
                                     "surround uniformity {u} for a floor of {s}")}),
    S(C, 369, '"couverture retirée " + num(g.couverture * 100, 1) + " %"',
      'dzT("cartes.capture.couverture", { p: num(g.couverture * 100, 1) })',
      {"cartes.capture.couverture": ("couverture retirée {p} %", "coverage removed {p}%")}),
    S(C, 371, '" — attendue entre " + num(bornes[0] * 100, 0) + " % et "' + N + '            + num(bornes[1] * 100, 0) + " %"',
      'dzT("cartes.capture.attendue", { a: num(bornes[0] * 100, 0), b: num(bornes[1] * 100, 0) })',
      {"cartes.capture.attendue": (" — attendue entre {a} % et {b} %", " — expected between {a}% and {b}%")}),
    S(C, 384, '"Le bloc « Détourage IA », plus bas, dit ce que ce poste sait faire "' + N + '        + "et à quel prix."',
      'dzT("cartes.capture.bloc_ia")',
      {"cartes.capture.bloc_ia": ("Le bloc « Détourage IA », plus bas, dit ce que ce poste sait faire et à quel prix.",
                                  "The “AI cutout” block below says what this computer can do and at what price.")}),
    L(C, 424, '"Importer l\'illustration"', "cartes.capture.et_illus", "Importer l'illustration", "Import the illustration"),
    S(C, 425, '"la pile d\'images de la pièce Illustration — ou, d\'un clic, "' + N
      + '          + "« adopter » ce qui vient d\'être repris ici"',
      'dzT("cartes.capture.et_illus_q")',
      {"cartes.capture.et_illus_q": (
          "la pile d'images de la pièce Illustration — ou, d'un clic, « adopter » ce qui vient d'être repris ici",
          "the image stack of the Illustration piece — or, in one click, “adopt” what was just captured here")}),
    L(C, 430, '"Choisir ou importer la bordure"', "cartes.capture.et_bord", "Choisir ou importer la bordure",
      "Choose or import the border"),
    S(C, 431, '"le catalogue de familles, et « adopter la bordure » qui pose "' + N
      + '          + "les mesures relevées sur la carte reprise"',
      'dzT("cartes.capture.et_bord_q")',
      {"cartes.capture.et_bord_q": (
          "le catalogue de familles, et « adopter la bordure » qui pose les mesures relevées sur la carte reprise",
          "the family catalog, and “adopt the border”, which applies the measurements taken on the captured card")}),
    L(C, 436, '"Régler le Sceau prismatique"', "cartes.capture.et_sceau", "Régler le Sceau prismatique",
      "Adjust the Prismatic Seal"),
    S(C, 437, '"métal, largeur de bande, et les trois portées — écran, "' + N
      + '          + "impression, 3D — réglables séparément"',
      'dzT("cartes.capture.et_sceau_q")',
      {"cartes.capture.et_sceau_q": (
          "métal, largeur de bande, et les trois portées — écran, impression, 3D — réglables séparément",
          "metal, band width, and the three scopes — screen, print, 3D — adjustable separately")}),
    L(C, 442, '"Éditer le verso"', "cartes.capture.et_verso", "Éditer le verso", "Edit the back"),
    S(C, 443, '"le dos de carte : motif du catalogue, image importée et "' + N + '          + "calques de texture"',
      'dzT("cartes.capture.et_verso_q")',
      {"cartes.capture.et_verso_q": ("le dos de carte : motif du catalogue, image importée et calques de texture",
                                     "the card back: catalog pattern, imported image and texture layers")}),
    S(C, 461, '"déposez d\'abord un recto : c\'est lui que la Forge 3D "' + N + '        + "recevra en couche."',
      'dzT("cartes.capture.pub_sans_recto")',
      {"cartes.capture.pub_sans_recto": ("déposez d'abord un recto : c'est lui que la Forge 3D recevra en couche.",
                                         "drop a front first: it is what Forge 3D will receive as a layer.")}),
    S(C, 466, '"analysez le recto d\'abord : le manifeste porte le format "' + N
      + '        + "et les millimètres de la mesure."',
      'dzT("cartes.capture.pub_sans_mesure")',
      {"cartes.capture.pub_sans_mesure": (
          "analysez le recto d'abord : le manifeste porte le format et les millimètres de la mesure.",
          "analyze the front first: the manifest carries the format and the millimeters of the measurement.")}),
    S(C, 483, '"publication terminée, mais le serveur n\'a pas rendu de "' + N
      + '        + "bordereau : ouvrez la pièce Forge 3D pour voir ce qui a été écrit."',
      'dzT("cartes.capture.pub_sans_bordereau")',
      {"cartes.capture.pub_sans_bordereau": (
          "publication terminée, mais le serveur n'a pas rendu de bordereau : ouvrez la pièce Forge 3D pour voir "
          "ce qui a été écrit.",
          "publishing done, but the server returned no report: open the Forge 3D piece to see what was written.")}),
    S(C, 490, '"aucune couche publiée : le manifeste est vide (redéposez le "' + N + '        + "recto, puis relancez)."',
      'dzT("cartes.capture.pub_vide")',
      {"cartes.capture.pub_vide": ("aucune couche publiée : le manifeste est vide (redéposez le recto, puis relancez).",
                                   "no layer published: the manifest is empty (drop the front again, then retry).")}),
    S(C, 494, 'n + (n > 1 ? " couches publiées" : " couche publiée")' + N + '      + " vers la Forge 3D"',
      'dzT(n > 1 ? "cartes.capture.publiees_plusieurs" : "cartes.capture.publiees_un", { n: n })',
      {"cartes.capture.publiees_un": ("{n} couche publiée vers la Forge 3D", "{n} layer published to Forge 3D"),
       "cartes.capture.publiees_plusieurs": ("{n} couches publiées vers la Forge 3D",
                                             "{n} layers published to Forge 3D")}),
    L(C, 497, '"manifeste sans nom"', "cartes.capture.manifeste_sans_nom", "manifeste sans nom", "unnamed manifest"),
    S(C, 500, '", toile " + toile[0] + " × " + toile[1] + " px"',
      'dzT("cartes.capture.toile", { w: toile[0], h: toile[1] })',
      {"cartes.capture.toile": (", toile {w} × {h} px", ", canvas {w} × {h} px")}),

    # ── gabarit ──────────────────────────────────────────────────────────────────────────────────────────────
    T(C, 568, '<b>Reprendre une carte</b>', "cartes.capture.titre", "Reprendre une carte", "Import an existing card"),
    T(C, 569, 'cf-capture-sub">un fichier par côté — le second dépôt remplace le premier</span>',
      "cartes.capture.sous_titre", "un fichier par côté — le second dépôt remplace le premier",
      "one file per side — a second drop replaces the first"),
    S(C, 586, 'id="cf-capture-empty">Déposez ici l\\\'image de la carte, ou choisissez un fichier.</p>',
      'id="cf-capture-empty">\' + dzT("cartes.capture.vide_accueil") + \'</p>',
      {"cartes.capture.vide_accueil": ("Déposez ici l'image de la carte, ou choisissez un fichier.",
                                       "Drop the card image here, or choose a file.")}),
    P('\'<button class="btn strong sm" id="cf-capture-pick" type="button" ', S(C, 593, 'title="PNG, JPEG ou WebP — le serveur réduit l\\\'image au-delà du plafond d\\\'import">\' + '
      'ICO("dz-action-importer", 16, "cf-ic") + \'Choisir un fichier…</button>\'',
      'title="\' + dzT("cartes.capture.pick_t") + \'">\' + ICO("dz-action-importer", 16, "cf-ic") + '
      'dzT("cartes.capture.pick") + \'</button>\'',
      {"cartes.capture.pick_t": ("PNG, JPEG ou WebP — le serveur réduit l'image au-delà du plafond d'import",
                                 "PNG, JPEG or WebP — the server downsizes the image beyond the import cap"),
       "cartes.capture.pick": ("Choisir un fichier…", "Choose a file…")})),
    S(C, 594, 'title="Déposer une autre image à la place de celle-ci">Remplacer</button>',
      'title="\' + dzT("cartes.capture.remplacer_t") + \'">\' + dzT("cartes.capture.remplacer") + \'</button>',
      {"cartes.capture.remplacer_t": ("Déposer une autre image à la place de celle-ci",
                                      "Drop another image in place of this one"),
       "cartes.capture.remplacer": ("Remplacer", "Replace")}),
    P('\'<button class="btn sm hidden" id="cf-capture-analyse" type="button" ', S(C, 596, 'title="Mesurer le recto déposé : bordure, zones, fond, palette. Gratuit, local, sans aucun appel payant '
      '— et rejouable autant de fois qu\\\'on veut.">\' + ICO("dz-action-mesurer", 16, "cf-ic") + \'Analyser</button>\'',
      'title="\' + dzT("cartes.capture.analyser_t") + \'">\' + ICO("dz-action-mesurer", 16, "cf-ic") + '
      'dzT("cartes.capture.analyser") + \'</button>\'',
      {"cartes.capture.analyser_t": (
          "Mesurer le recto déposé : bordure, zones, fond, palette. Gratuit, local, sans aucun appel payant — et "
          "rejouable autant de fois qu'on veut.",
          "Measure the dropped front: border, zones, background, palette. Free, local, no paid call — and "
          "repeatable as often as you like."),
       "cartes.capture.analyser": ("Analyser", "Analyze")})),
    S(C, 597, 'title="Afficher ou masquer les zones candidates par-dessus l\\\'aperçu">Masquer les zones</button>',
      'title="\' + dzT("cartes.capture.boxtog_t") + \'">\' + dzT("cartes.capture.masquer_zones") + \'</button>',
      {"cartes.capture.boxtog_t": ("Afficher ou masquer les zones candidates par-dessus l'aperçu",
                                   "Show or hide the candidate zones over the preview"),
       "cartes.capture.masquer_zones": ("Masquer les zones", "Hide zones")}),
    T(C, 602, 'id="cf-capture-state">pas de capture</span>', "cartes.capture.pas_capture", "pas de capture", "no capture"),
    P("'", T(C, 604, '<dt>Côté</dt>', "cartes.capture.r_cote", "Côté", "Side")),
    T(C, 605, '<dt>Trame</dt>', "cartes.capture.r_trame", "Trame", "Raster"),
    P("'", T(C, 606, '<dt>Fichier</dt>', "cartes.capture.r_fichier", "Fichier", "File")),
    T(C, 607, '<dt>Analyse</dt>', "cartes.capture.r_analyse", "Analyse", "Analysis"),
    T(C, 619, '<b>Mesures du recto</b>', "cartes.capture.mesures_titre", "Mesures du recto", "Front measurements"),
    T(C, 620, 'cf-capture-sub">chaque détection porte sa confiance chiffrée — analyse locale, gratuite, rejouable</span>',
      "cartes.capture.mesures_sous", "chaque détection porte sa confiance chiffrée — analyse locale, gratuite, rejouable",
      "each detection carries its confidence figure — local, free, repeatable analysis"),
    T(C, 644, '<b>Détourage IA</b>', "cartes.capture.ia_titre", "Détourage IA", "AI cutout"),
    T(C, 645, 'cf-capture-sub">isoler le sujet du recto — une option, jamais une étape obligée</span>',
      "cartes.capture.ia_sous", "isoler le sujet du recto — une option, jamais une étape obligée",
      "isolate the subject of the front — an option, never a required step"),
    S(C, 655, 'id="cf-capture-ia-vide">Le sujet détouré s\\\'affichera ici.</p>',
      'id="cf-capture-ia-vide">\' + dzT("cartes.capture.ia_vide") + \'</p>',
      {"cartes.capture.ia_vide": ("Le sujet détouré s'affichera ici.", "The cut-out subject will appear here.")}),
    S(C, 658, "'Détourer le sujet</button>'", 'dzT("cartes.capture.detourer") + \'</button>\'', {}),
    T(C, 675, '<b>Et maintenant</b>', "cartes.capture.suite_titre", "Et maintenant", "What next"),
    T(C, 676, 'cf-capture-sub">quatre gestes, chacun chez la pièce qui le sait faire</span>', "cartes.capture.suite_sous",
      "quatre gestes, chacun chez la pièce qui le sait faire", "four actions, each in the piece that knows how"),
    P('\'<button class="btn strong sm hidden" id="cf-capture-publier" type="button" ', S(C, 680, 'title="Écrit les couches importées dans le manifeste que la pièce Forge 3D sait lire — local, gratuit, '
      'rejouable">\' + ICO("dz-nav-cf-forge-3d", 16, "cf-ic") + \'Publier vers la 3D</button>\'',
      'title="\' + dzT("cartes.capture.publier_t") + \'">\' + ICO("dz-nav-cf-forge-3d", 16, "cf-ic") + '
      'dzT("cartes.capture.publier") + \'</button>\'',
      {"cartes.capture.publier_t": (
          "Écrit les couches importées dans le manifeste que la pièce Forge 3D sait lire — local, gratuit, rejouable",
          "Writes the imported layers into the manifest the Forge 3D piece can read — local, free, repeatable"),
       "cartes.capture.publier": ("Publier vers la 3D", "Publish to 3D")})),
    # ── peinture ─────────────────────────────────────────────────────────────────────────────────────────────
    S(C, 697, 's.label + " : une capture est déposée"', 'dzT("cartes.capture.seg_depose", { cote: s.label })',
      {"cartes.capture.seg_depose": ("{cote} : une capture est déposée", "{cote}: a capture is dropped")}),
    S(C, 698, 's.label + " : rien encore"', 'dzT("cartes.capture.seg_rien", { cote: s.label })',
      {"cartes.capture.seg_rien": ("{cote} : rien encore", "{cote}: nothing yet")}),
    S(C, 732, '"L\'image de cette capture ne se charge plus "' + N
      + '              + "(fichier absent côté serveur). Déposez-la à nouveau."',
      'dzT("cartes.capture.img_ko")',
      {"cartes.capture.img_ko": (
          "L'image de cette capture ne se charge plus (fichier absent côté serveur). Déposez-la à nouveau.",
          "This capture's image no longer loads (file missing on the server). Drop it again.")}),
    L(C, 736, '"capture illisible"', "cartes.capture.illisible", "capture illisible", "unreadable capture"),
    S(C, 740, '"capture " + d.label', 'dzT("cartes.capture.alt", { cote: d.label })',
      {"cartes.capture.alt": ("capture {cote}", "{cote} capture")}),
    L(C, 752, '"Déposez ici l\'image de la carte, ou choisissez un fichier."', "cartes.capture.vide_accueil",
      "Déposez ici l'image de la carte, ou choisissez un fichier.", "Drop the card image here, or choose a file."),
    L(C, 763, '"pas de capture"', "cartes.capture.pas_capture", "pas de capture", "no capture"),
    L(C, 764, '"analysée"', "cartes.capture.analysee", "analysée", "analyzed"),
    L(C, 764, '"capture déposée"', "cartes.capture.deposee", "capture déposée", "capture dropped"),
    S(C, 771, '(Number(i.bytes) || 0).toLocaleString("fr-FR") + " octets"',
      'dzT("cartes.capture.octets", { n: (Number(i.bytes) || 0).toLocaleString("fr-FR") })',
      {"cartes.capture.octets": ("{n} octets", "{n} bytes")}),
    L(C, 772, '"propriété du recto"', "cartes.capture.prop_recto", "propriété du recto", "applies to the front"),
    L(C, 773, '"pas encore"', "cartes.capture.pas_encore", "pas encore", "not yet"),
    S(C, 775, '"PNG, JPEG ou WebP. Au-delà de " + MAX_IMPORT_PX + " px de côté, le "' + N
      + '        + "serveur réduit l\'image et répond ses dimensions réelles."',
      'dzT("cartes.capture.note_vide", { px: MAX_IMPORT_PX })',
      {"cartes.capture.note_vide": (
          "PNG, JPEG ou WebP. Au-delà de {px} px de côté, le serveur réduit l'image et répond ses dimensions réelles.",
          "PNG, JPEG or WebP. Beyond {px} px per side, the server downsizes the image and returns its actual "
          "dimensions.")}),
    S(C, 778, '"« Analyser » mesure ce recto sur le serveur : bordure, zones, fond, "' + N
      + '          + "palette. C\'est local et gratuit — aucun appel payant — et ça se "' + N
      + '          + "rejoue autant de fois qu\'on veut."',
      'dzT("cartes.capture.note_recto")',
      {"cartes.capture.note_recto": (
          "« Analyser » mesure ce recto sur le serveur : bordure, zones, fond, palette. C'est local et gratuit — "
          "aucun appel payant — et ça se rejoue autant de fois qu'on veut.",
          "“Analyze” measures this front on the server: border, zones, background, palette. It is local and free "
          "— no paid call — and can be rerun as often as you like.")}),
    S(C, 781, '"L\'analyse porte sur le RECTO — bordure, zones et fond s\'y mesurent. "' + N
      + '          + "Déposer un verso ne l\'efface pas : il sert au dos de carte et à "' + N
      + '          + "l\'objet 3D."',
      'dzT("cartes.capture.note_verso")',
      {"cartes.capture.note_verso": (
          "L'analyse porte sur le RECTO — bordure, zones et fond s'y mesurent. Déposer un verso ne l'efface pas : "
          "il sert au dos de carte et à l'objet 3D.",
          "The analysis applies to the FRONT — border, zones and background are measured there. Dropping a back "
          "does not erase it: the back is used for the card back and the 3D object.")}),
    L(C, 791, '"Remesurer"', "cartes.capture.remesurer", "Remesurer", "Re-measure"),
    L(C, 791, '"Analyser"', "cartes.capture.analyser", "Analyser", "Analyze"),
    L(C, 799, '"Masquer les zones"', "cartes.capture.masquer_zones", "Masquer les zones", "Hide zones"),
    L(C, 799, '"Montrer les zones"', "cartes.capture.montrer_zones", "Montrer les zones", "Show zones"),
    S(C, 831, '"Ouvre la pièce « " + String(e.piece) + " » et amène la "' + N + '          + "section sous les yeux"',
      'dzT("cartes.capture.go_t", { piece: String(e.piece) })',
      {"cartes.capture.go_t": ("Ouvre la pièce « {piece} » et amène la section sous les yeux",
                               "Opens the “{piece}” piece and brings the section into view")}),
    S(C, 849, '"Écrit le manifeste des couches importées dans le dossier de la "' + N
      + '        + "pièce Forge 3D : la face reprise (et le sujet détouré s\'il "' + N
      + '        + "existe) deviennent des sources de nœuds. Local, gratuit, "' + N
      + '        + "rejouable — un nouveau format se republie."',
      'dzT("cartes.capture.pub_note")',
      {"cartes.capture.pub_note": (
          "Écrit le manifeste des couches importées dans le dossier de la pièce Forge 3D : la face reprise (et le "
          "sujet détouré s'il existe) deviennent des sources de nœuds. Local, gratuit, rejouable — un nouveau "
          "format se republie.",
          "Writes the manifest of imported layers into the Forge 3D piece's folder: the captured face (and the "
          "cut-out subject, if any) become node sources. Local, free, repeatable — a new format can be "
          "republished.")}),
    S(C, 868, '"la pièce « " + String(e.piece) + " » n\'existe pas sur cette "' + N
      + '        + "version : " + String((x && x.message) || x)',
      'dzT("cartes.capture.piece_absente", { piece: String(e.piece), err: String((x && x.message) || x) })',
      {"cartes.capture.piece_absente": ("la pièce « {piece} » n'existe pas sur cette version : {err}",
                                        "the “{piece}” piece does not exist in this version: {err}")}),
    S(C, 882, '"la pièce est ouverte, mais la section « " + String(e.titre)' + N
      + '        + " » n\'a pas été trouvée dans cette version de l\'écran."',
      'dzT("cartes.capture.section_absente", { titre: String(e.titre) })',
      {"cartes.capture.section_absente": (
          "la pièce est ouverte, mais la section « {titre} » n'a pas été trouvée dans cette version de l'écran.",
          "the piece is open, but the “{titre}” section was not found in this version of the screen.")}),

    # ── bloc IA ──────────────────────────────────────────────────────────────────────────────────────────────
    S(C, 941, 'off.libelle.replace("Détourer", "Redétourer")',
      'off.libelle.replace(dzT("cartes.capture.mot_detourer"), dzT("cartes.capture.mot_redetourer"))',
      {"cartes.capture.mot_detourer": ("Détourer", "Cut out", "contexte"),
       "cartes.capture.mot_redetourer": ("Redétourer", "Re-cut", "contexte")}),
    L(C, 944, '"rembg tourne sur cette machine : aucun appel, aucune dépense"', "cartes.capture.rembg_t",
      "rembg tourne sur cette machine : aucun appel, aucune dépense", "rembg runs on this machine: no call, no spending"),
    S(C, 945, '"l\'image part chez le fournisseur, qui facture directement — le "' + N
      + '          + "tarif affiché vient de Réglages → Tarifs et budget"',
      'dzT("cartes.capture.fal_t")',
      {"cartes.capture.fal_t": (
          "l'image part chez le fournisseur, qui facture directement — le tarif affiché vient de Réglages → "
          "Tarifs et budget",
          "the image goes to the provider, who bills directly — the price shown comes from Settings → Pricing and "
          "budget")}),
    L(C, 951, '"sujet isolé"', "cartes.capture.sujet_isole", "sujet isolé", "subject isolated"),
    L(C, 951, '"disponible"', "cartes.capture.disponible", "disponible", "available"),
    L(C, 951, '"indisponible"', "cartes.capture.indisponible", "indisponible", "unavailable"),
    S(C, 968, '"La couche détourée ne se charge plus (fichier "' + N
      + '              + "absent côté serveur). Relancez le détourage."',
      'dzT("cartes.capture.sujet_ko")',
      {"cartes.capture.sujet_ko": ("La couche détourée ne se charge plus (fichier absent côté serveur). "
                                   "Relancez le détourage.",
                                   "The cut-out layer no longer loads (file missing on the server). "
                                   "Run the cutout again.")}),
    L(C, 977, '"sujet détouré"', "cartes.capture.sujet_alt", "sujet détouré", "cut-out subject"),
    S(C, 992, '"Le détourage tourne ICI : rien ne sort de la machine, rien n\'est "' + N + '            + "facturé."',
      'dzT("cartes.capture.ia_local")',
      {"cartes.capture.ia_local": ("Le détourage tourne ICI : rien ne sort de la machine, rien n'est facturé.",
                                   "The cutout runs HERE: nothing leaves the machine, nothing is billed.")}),
    S(C, 994, '"L\'image part chez fal.ai, qui facture directement. Le montant "' + N
      + '            + "affiché vient de la table de tarifs de l\'application."',
      'dzT("cartes.capture.ia_fal")',
      {"cartes.capture.ia_fal": (
          "L'image part chez fal.ai, qui facture directement. Le montant affiché vient de la table de tarifs de "
          "l'application.",
          "The image goes to fal.ai, which bills directly. The amount shown comes from the app's price table.")}),
    S(C, 998, '"Couche « sujet » : " + suj.w + " × " + suj.h + " px, "' + N + '          + weight(suj.bytes)',
      'dzT("cartes.capture.couche_sujet", { w: suj.w, h: suj.h, poids: weight(suj.bytes) })',
      {"cartes.capture.couche_sujet": ("Couche « sujet » : {w} × {h} px, {poids}",
                                       "“Subject” layer: {w} × {h} px, {poids}")}),
    S(C, 1001, '" — elle garde " + num(suj.couverture * 100, 1) + " % de l\'image"',
      'dzT("cartes.capture.garde", { p: num(suj.couverture * 100, 1) })',
      {"cartes.capture.garde": (" — elle garde {p} % de l'image", " — it keeps {p}% of the image")}),
    S(C, 1003, '" (voie " + String(suj.voie) + ")"', 'dzT("cartes.capture.voie", { v: String(suj.voie) })',
      {"cartes.capture.voie": (" (voie {v})", " (via {v})")}),
    S(C, 1004, '". La pièce Illustration peut l\'adopter."', 'dzT("cartes.capture.adopter")',
      {"cartes.capture.adopter": (". La pièce Illustration peut l'adopter.", ". The Illustration piece can adopt it.")}),

    # ── relevé ───────────────────────────────────────────────────────────────────────────────────────────────
    S(C, 1026, '"mesuré le " + quand(s.analyzed)', 'dzT("cartes.capture.mesure_le", { date: quand(s.analyzed) })',
      {"cartes.capture.mesure_le": ("mesuré le {date}", "measured on {date}")}),
    S(C, 1033, '"Le format du jeu a changé depuis cette mesure : "' + N
      + '          + div.avant + " → " + div.apres + ". Les millimètres ci-dessous "' + N
      + '          + "décrivent la carte d\'avant — relancez « Remesurer »."',
      'dzT("cartes.capture.diverge", { avant: div.avant, apres: div.apres })',
      {"cartes.capture.diverge": (
          "Le format du jeu a changé depuis cette mesure : {avant} → {apres}. Les millimètres ci-dessous décrivent "
          "la carte d'avant — relancez « Remesurer ».",
          "The deck format changed since this measurement: {avant} → {apres}. The millimeters below describe the "
          "previous card — run “Re-measure” again.")}),
    L(C, 1043, '"Échelle"', "cartes.capture.echelle", "Échelle", "Scale"),
    S(C, 1048, 'num(e.mm_par_px * 1000, 3) + " µm par pixel"',
      'dzT("cartes.capture.um_px", { v: num(e.mm_par_px * 1000, 3) })',
      {"cartes.capture.um_px": ("{v} µm par pixel", "{v} µm per pixel")}),
    S(C, 1052, '"ratio image " + num(e.ratio_image, 4) + " contre "' + N
      + '          + num(e.ratio_format, 4) + " au format — écart "' + N
      + '          + (ec >= 0 ? "+" : "−") + num(Math.abs(ec) * 100, 1) + " %"',
      'dzT("cartes.capture.ratio", { ri: num(e.ratio_image, 4), rf: num(e.ratio_format, 4), '
      'signe: ec >= 0 ? "+" : "−", p: num(Math.abs(ec) * 100, 1) })',
      {"cartes.capture.ratio": ("ratio image {ri} contre {rf} au format — écart {signe}{p} %",
                                "image ratio {ri} vs {rf} for the format — deviation {signe}{p}%")}),
    L(C, 1059, '"Bordure"', "cartes.capture.bordure", "Bordure", "Border"),
    S(C, 1060, '"bande de " + num(b.mm, 2) + " mm — " + String(b.color || "?")',
      'dzT("cartes.capture.bande", { mm: num(b.mm, 2), c: String(b.color || "?") })',
      {"cartes.capture.bande": ("bande de {mm} mm — {c}", "{mm} mm band — {c}")}),
    S(C, 1062, '"rayon de coin estimé " + num(b.radius_mm, 2) + " mm"',
      'dzT("cartes.capture.rayon", { mm: num(b.radius_mm, 2) })',
      {"cartes.capture.rayon": ("rayon de coin estimé {mm} mm", "estimated corner radius {mm} mm")}),
    L(C, 1063, '"rayon de coin : non mesuré"', "cartes.capture.rayon_nm", "rayon de coin : non mesuré",
      "corner radius: not measured"),
    S(C, 1070, '"les " + Object.keys(b.epaisseurs_mm).length + " bords vus : "',
      'dzT("cartes.capture.bords_vus", { n: Object.keys(b.epaisseurs_mm).length })',
      {"cartes.capture.bords_vus": ("les {n} bords vus : ", "the {n} edges seen: ")}),
    S(C, 1074, '"régularité " + num(b.regularite, 2) + " · netteté " + num(b.nettete, 2)',
      'dzT("cartes.capture.regularite", { r: num(b.regularite, 2), n: num(b.nettete, 2) })',
      {"cartes.capture.regularite": ("régularité {r} · netteté {n}", "regularity {r} · sharpness {n}")}),
    L(C, 1075, '"aucune bordure mesurable sur cette carte"', "cartes.capture.sans_bordure",
      "aucune bordure mesurable sur cette carte", "no measurable border on this card"),
    L(C, 1082, '"Zones occupées"', "cartes.capture.zones", "Zones occupées", "Occupied zones"),
    S(C, 1084, 'bx.length + (bx.length > 1 ? " zones candidates" : " zone candidate")',
      'dzT(bx.length > 1 ? "cartes.capture.zones_plusieurs" : "cartes.capture.zones_un", { n: bx.length })',
      {"cartes.capture.zones_un": ("{n} zone candidate", "{n} candidate zone"),
       "cartes.capture.zones_plusieurs": ("{n} zones candidates", "{n} candidate zones")}),
    S(C, 1086, '(k + 1) + " · " + num(z.w, 1) + " × " + num(z.h, 1) + " mm"' + N
      + '              + " en (" + num(z.x, 1) + " ; " + num(z.y, 1) + ") — densité "' + N
      + '              + num(z.densite, 2) + " · netteté " + num(z.nettete, 2)',
      'dzT("cartes.capture.zone_ligne", { k: k + 1, w: num(z.w, 1), h: num(z.h, 1), x: num(z.x, 1), '
      'y: num(z.y, 1), d: num(z.densite, 2), n: num(z.nettete, 2) })',
      {"cartes.capture.zone_ligne": ("{k} · {w} × {h} mm en ({x} ; {y}) — densité {d} · netteté {n}",
                                     "{k} · {w} × {h} mm at ({x} ; {y}) — density {d} · sharpness {n}")}),
    L(C, 1089, '" — TRONQUÉE par la bande exclue"', "cartes.capture.tronquee", " — TRONQUÉE par la bande exclue",
      " — TRUNCATED by the excluded band"),
    L(C, 1091, '"aucune zone candidate"', "cartes.capture.aucune_zone", "aucune zone candidate", "no candidate zone"),
    S(C, 1093, '"bande exclue le long des bords : " + num(s.zones_bande_mm, 2)' + N
      + '             + " mm (bordure + portée du filtre)"',
      'dzT("cartes.capture.bande_exclue", { mm: num(s.zones_bande_mm, 2) })',
      {"cartes.capture.bande_exclue": ("bande exclue le long des bords : {mm} mm (bordure + portée du filtre)",
                                       "band excluded along the edges: {mm} mm (border + filter reach)")}),
    L(C, 1098, '"Fond"', "cartes.capture.fond", "Fond", "Background", contexte=True),
    S(C, 1104, 'pal.length + " teintes dominantes"', 'dzT("cartes.capture.teintes", { n: pal.length })',
      {"cartes.capture.teintes": ("{n} teintes dominantes", "{n} dominant hues")}),
    L(C, 1104, '"non mesurée"', "cartes.capture.non_mesuree", "non mesurée", "not measured"),
    S(C, 1165, '"zone " + (k + 1) + " — " + num(b.w, 1) + " × " + num(b.h, 1)' + N
      + '        + " mm, densité " + num(b.densite, 2)',
      'dzT("cartes.capture.zone_t", { k: k + 1, w: num(b.w, 1), h: num(b.h, 1), d: num(b.densite, 2) })',
      {"cartes.capture.zone_t": ("zone {k} — {w} × {h} mm, densité {d}", "zone {k} — {w} × {h} mm, density {d}")}),
    S(C, 1167, '" — tronquée par la bande exclue : cette taille est un "' + N + '          + "minimum"',
      'dzT("cartes.capture.tronquee_t")',
      {"cartes.capture.tronquee_t": (" — tronquée par la bande exclue : cette taille est un minimum",
                                     " — truncated by the excluded band: this size is a minimum")}),

    # ── réseau, gestes ───────────────────────────────────────────────────────────────────────────────────────
    X(C, 1279, '"route absente"', "message interne jamais affiché : panne() lit x.missing et dit « backend absent »"),
    S(C, 1296, '"backend absent : " + quoi + " exige /api/cards"', 'dzT("cartes.capture.backend_absent", { quoi: quoi })',
      {"cartes.capture.backend_absent": ("backend absent : {quoi} exige /api/cards",
                                         "backend missing: {quoi} requires /api/cards")}),
    S(C, 1302, '"backend injoignable (" + m + ") — " + quoi' + N + '        + " a besoin du service local"',
      'dzT("cartes.capture.backend_injoignable", { err: m, quoi: quoi })',
      {"cartes.capture.backend_injoignable": ("backend injoignable ({err}) — {quoi} a besoin du service local",
                                              "backend unreachable ({err}) — {quoi} needs the local service")}),
    L(C, 1309, '"un import est déjà en cours"', "cartes.capture.import_en_cours", "un import est déjà en cours",
      "an import is already in progress"),
    S(C, 1315, '"ce fichier n\'est pas une image (" + (f.type || "type inconnu") + ")"',
      'dzT("cartes.capture.pas_image", { type: f.type || dzT("cartes.capture.type_inconnu") })',
      {"cartes.capture.pas_image": ("ce fichier n'est pas une image ({type})", "this file is not an image ({type})"),
       "cartes.capture.type_inconnu": ("type inconnu", "unknown type")}),
    L(C, 1320, '"import de la carte…"', "cartes.capture.import_busy", "import de la carte…", "importing the card…"),
    S(C, 1328, '"carte importée — " + d.w + " × " + d.h + " px, " + weight(d.bytes)',
      'dzT("cartes.capture.importee", { w: d.w, h: d.h, poids: weight(d.bytes) })',
      {"cartes.capture.importee": ("carte importée — {w} × {h} px, {poids}", "card imported — {w} × {h} px, {poids}")}),
    L(C, 1330, '"l\'import"', "cartes.capture.q_import", "l'import", "the import"),
    L(C, 1350, '"un traitement est déjà en cours"', "cartes.capture.traitement_en_cours",
      "un traitement est déjà en cours", "a task is already running"),
    L(C, 1352, '"déposez d\'abord un recto : l\'analyse porte sur lui"', "cartes.capture.recto_d_abord_analyse",
      "déposez d'abord un recto : l'analyse porte sur lui", "drop a front first: the analysis applies to it"),
    L(C, 1357, '"analyse du recto…"', "cartes.capture.analyse_busy", "analyse du recto…", "analyzing the front…"),
    S(C, 1362, '"recto analysé — "' + N
      + '        + (b ? "bordure " + num(b.mm, 2) + " mm (" + conf(b.confidence) + ")"' + N
      + '             : "aucune bordure mesurable")' + N
      + '        + ", " + r.boxes.length + " zone" + (r.boxes.length > 1 ? "s" : "")' + N
      + '        + ", " + r.palette.length + " teintes"',
      'dzT("cartes.capture.analyse_ok", {' + N
      + '        bord: b ? dzT("cartes.capture.analyse_bord", { mm: num(b.mm, 2), conf: conf(b.confidence) })' + N
      + '             : dzT("cartes.capture.analyse_sans_bord"),' + N
      + '        zones: dzT(r.boxes.length > 1 ? "cartes.capture.analyse_zones_plusieurs" : '
      '"cartes.capture.analyse_zones_un", { n: r.boxes.length }),' + N
      + '        teintes: r.palette.length })',
      {"cartes.capture.analyse_ok": ("recto analysé — {bord}, {zones}, {teintes} teintes",
                                     "front analyzed — {bord}, {zones}, {teintes} hues"),
       "cartes.capture.analyse_bord": ("bordure {mm} mm ({conf})", "border {mm} mm ({conf})"),
       "cartes.capture.analyse_sans_bord": ("aucune bordure mesurable", "no measurable border"),
       "cartes.capture.analyse_zones_un": ("{n} zone", "{n} zone"),
       "cartes.capture.analyse_zones_plusieurs": ("{n} zones", "{n} zones")}),
    L(C, 1368, '"l\'analyse"', "cartes.capture.q_analyse", "l'analyse", "the analysis"),
    L(C, 1393, '"les options de détourage"', "cartes.capture.q_options", "les options de détourage", "the cutout options"),
    L(C, 1407, '"un traitement est déjà en cours"', "cartes.capture.traitement_en_cours",
      "un traitement est déjà en cours", "a task is already running"),
    L(C, 1409, '"détourage indisponible"', "cartes.capture.detour_indispo", "détourage indisponible", "cutout unavailable"),
    L(C, 1421, '"détourage indisponible"', "cartes.capture.detour_indispo", "détourage indisponible", "cutout unavailable"),
    S(C, 1423, '"le tarif a changé depuis l\'affichage : « " + avant.libelle' + N
      + '        + " » → « " + off.libelle + " ». Rien n\'a été envoyé — relancez si "' + N
      + '        + "vous êtes d\'accord."',
      'dzT("cartes.capture.tarif_change", { avant: avant.libelle, apres: off.libelle })',
      {"cartes.capture.tarif_change": (
          "le tarif a changé depuis l'affichage : « {avant} » → « {apres} ». Rien n'a été envoyé — relancez si vous "
          "êtes d'accord.",
          "the price changed since it was shown: “{avant}” → “{apres}”. Nothing was sent — retry if you agree.")}),
    L(C, 1430, '"détourage local…"', "cartes.capture.detour_local_busy", "détourage local…", "local cutout…"),
    L(C, 1430, '"détourage par fal.ai…"', "cartes.capture.detour_fal_busy", "détourage par fal.ai…", "cutout via fal.ai…"),
    S(C, 1451, '"sujet isolé — " + d.w + " × " + d.h + " px, " + weight(d.bytes)',
      'dzT("cartes.capture.sujet_ok", { w: d.w, h: d.h, poids: weight(d.bytes) })',
      {"cartes.capture.sujet_ok": ("sujet isolé — {w} × {h} px, {poids}", "subject isolated — {w} × {h} px, {poids}")}),
    L(C, 1452, '" (local, gratuit)"', "cartes.capture.local_gratuit", " (local, gratuit)", " (local, free)"),
    S(C, 1453, '" (fal, ~" + num(d.prix_usd, 3) + " $)"', 'dzT("cartes.capture.fal_prix", { prix: num(d.prix_usd, 3) })',
      {"cartes.capture.fal_prix": (" (fal, ~{prix} $)", " (fal, ~${prix})")}),
    L(C, 1456, '"le détourage"', "cartes.capture.q_detourage", "le détourage", "the cutout"),
    L(C, 1483, '"un traitement est déjà en cours"', "cartes.capture.traitement_en_cours",
      "un traitement est déjà en cours", "a task is already running"),
    L(C, 1485, '"rien à publier"', "cartes.capture.rien_publier", "rien à publier", "nothing to publish"),
    L(C, 1488, '"publication des couches vers la Forge 3D…"', "cartes.capture.pub_busy",
      "publication des couches vers la Forge 3D…", "publishing layers to Forge 3D…"),
    L(C, 1496, '"la publication vers la 3D"', "cartes.capture.q_publication", "la publication vers la 3D",
      "publishing to 3D"),

    # ── valeurs techniques d'allure française (MIME, ids, attributs, police) ─────────────────────────────────
    X(F, 104, '"aucun"', "id de relief comparé et stocké"),
    X(F, 307, "'        <input type=\"file\" id=\"cf-solid-hdri\" accept=\".hdr,.exr,image/*\" hidden></label>'",
      "attributs techniques (filtre accept)"),
    X(F, 312, "'        shadow-intensity=\"0.55\" shadow-softness=\"0.9\" exposure=\"1\" environment-image=\"neutral\"'",
      "attributs de <model-viewer>"),
    X(F, 903, '"9.5px sans-serif"', "police"),
    X(F, 1546, '"image/png"', "type MIME"),
    X(F, 1549, '"image/png"', "type MIME"),
    X(F, 1552, '"image/png"', "type MIME"),
    X(F, 2408, '"image/png"', "type MIME"),
    X(F, 2409, '"image/jpeg"', "type MIME"),
    X(F, 2754, '"image/png"', "type MIME"),
    X(F, 2929, '"image/jpeg"', "type MIME"),
    X(F, 2995, '"image/png"', "type MIME"),
    X(C, 592, "'<input type=\"file\" accept=\"image/png,image/jpeg,image/webp\" class=\"cf-capture-file\" id=\"cf-capture-file\">'",
      "attributs techniques (filtre accept)"),
]
