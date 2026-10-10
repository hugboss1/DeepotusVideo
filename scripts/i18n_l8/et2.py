"""t148 — et2 : etabli/etabli.js lignes 2401-4548 (le couteau et son connecteur, le point de vue, le panneau Parties
et la plaque, la porte d'écriture — file d'attente, bilans de réparation / creusage / perçage / décimation, booléens,
vignette —, le panneau Fiche, le repère, l'amorçage) et la page etabli/index.html (entrées H : jamais modifiée).

GARDÉ : les valeurs envoyées au serveur ou comparées (« couper », « deux », « teton », types MIME « image/png »),
l'unité « u. glTF » (unité seule, épinglée dans uniteCourante), les noms d'opération internes listés dans
« écrit : … / abandonné : … », et tout ce que le serveur rend (src.couture, src.matieres, capuchon.raison,
src.avertissement, src.limite, e.message) : traduit côté backend (L10). Les valeurs internes AFFICHÉES (type de
connecteur, rôle mâle/femelle, opération booléenne, côté gardé) passent par une table dzT au point d'affichage.
"""
from outils import L, S, X, H

F = "etabli/etabli.js"
PLAGES = {F: (2401, 4548)}

# tables d'affichage des valeurs internes (insérées telles quelles dans les « après »)
TYPES = ('({ teton: dzT("etabli.et2_connecteur.teton"), cheville: dzT("etabli.et2_connecteur.cheville"), '
         'aronde: dzT("etabli.et2_connecteur.aronde") }[{v}] || {v})')
OPS = ('({ union: dzT("etabli.et2_bool.op_union"), difference: dzT("etabli.et2_bool.op_difference"), '
       'intersection: dzT("etabli.et2_bool.op_intersection") }[{v}] || {v})')


def types(v):
    return TYPES.replace("{v}", v)


def ops(v):
    return OPS.replace("{v}", v)


AUCUN = "etabli.et2_commun.aucun_modele"
D_AUCUN = {AUCUN: ("aucun modèle chargé", "no model loaded")}
D_TYPES = {"etabli.et2_connecteur.teton": ("téton", "plug"),
           "etabli.et2_connecteur.cheville": ("cheville", "dowel"),
           "etabli.et2_connecteur.aronde": ("queue d'aronde", "dovetail")}
D_OPS = {"etabli.et2_bool.op_union": ("union", "union"),
         "etabli.et2_bool.op_difference": ("différence", "difference"),
         "etabli.et2_bool.op_intersection": ("intersection", "intersection")}

ENTREES = [
    # ── le couteau ──────────────────────────────────────────────────────────────────────────────────────────
    L(F, 2540, '"aucun modèle chargé — rien à couper"', "etabli.et2_couteau.rien_a_couper",
      "aucun modèle chargé — rien à couper", "no model loaded — nothing to cut"),
    L(F, 2544, '"la plaque est une VUE : revenez à « Assemblé » pour couper"', "etabli.et2_couteau.plaque_vue",
      "la plaque est une VUE : revenez à « Assemblé » pour couper",
      "the plate is a VIEW: go back to “Assembled” to cut"),
    S(F, 2549, '"aucune pièce retenue — cochez dans Parties ce que le couteau "\r\n      + "doit couper : il ne tranche '
      'jamais tout le modèle par défaut"', 'dzT("etabli.et2_couteau.aucune_piece_cochez")',
      {"etabli.et2_couteau.aucune_piece_cochez": (
          "aucune pièce retenue — cochez dans Parties ce que le couteau doit couper : il ne tranche jamais tout le "
          "modèle par défaut",
          "no part selected — tick in Parts what the knife should cut: it never slices the whole model by default")}),
    S(F, 2567, '"couteau rangé : plus aucune pièce retenue, il n\'y a plus rien à "\r\n      + "couper"',
      'dzT("etabli.et2_couteau.range")',
      {"etabli.et2_couteau.range": ("couteau rangé : plus aucune pièce retenue, il n'y a plus rien à couper",
                                    "knife put away: no part selected any more, nothing left to cut")}),
    L(F, 2590, '"le couteau n\'est pas armé — « Couteau » pose d\'abord le plan de coupe"',
      "etabli.et2_couteau.pas_arme", "le couteau n'est pas armé — « Couteau » pose d'abord le plan de coupe",
      "the knife is not armed — “Knife” places the cutting plane first"),
    L(F, 2593, '"aucun modèle chargé — rien à couper"', "etabli.et2_couteau.rien_a_couper",
      "aucun modèle chargé — rien à couper", "no model loaded — nothing to cut"),
    L(F, 2595, '"une écriture est en cours — attends la fin de la série avant de couper"',
      "etabli.et2_couteau.ecriture_en_cours", "une écriture est en cours — attends la fin de la série avant de couper",
      "a write is in progress — wait for the batch to finish before cutting"),
    S(F, 2599, '`${S.enAttente.length} modification(s) en attente — écris d\'abord `\r\n'
      '      + "les modifications en attente (« écrire la version ») : la coupe "\r\n'
      '      + "renumérote les nœuds et ne se met pas en file derrière elles"',
      'dzT("etabli.et2_couteau.attente_ecris", { n: S.enAttente.length })',
      {"etabli.et2_couteau.attente_ecris": (
          "{n} modification(s) en attente — écris d'abord les modifications en attente (« écrire la version ») : "
          "la coupe renumérote les nœuds et ne se met pas en file derrière elles",
          "{n} pending change(s) — write the pending changes first (“write the version”): the cut renumbers the "
          "nodes and does not queue behind them")}),
    S(F, 2608, '"aucune pièce retenue — le couteau ne tranche jamais tout le "\r\n      + "modèle par défaut"',
      'dzT("etabli.et2_couteau.aucune_piece")',
      {"etabli.et2_couteau.aucune_piece": ("aucune pièce retenue — le couteau ne tranche jamais tout le modèle par "
                                           "défaut",
                                           "no part selected — the knife never slices the whole model by default")}),
    S(F, 2699, 'direAvis(`coupe écrite (version ${fiche.version}) — capuchon non posé : `\r\n    + manques.join(" · "));',
      'direAvis(dzT("etabli.et2_couteau.capuchon_non_pose", { version: fiche.version, manques: manques.join(" · ") }));',
      {"etabli.et2_couteau.capuchon_non_pose": ("coupe écrite (version {version}) — capuchon non posé : {manques}",
                                                "cut written (version {version}) — cap not placed: {manques}")}),

    # ── le connecteur ───────────────────────────────────────────────────────────────────────────────────────
    L(F, 2663, '"connecteur non posé : pose une taille cible — un connecteur se donne en millimètres"',
      "etabli.et2_connecteur.sans_cible",
      "connecteur non posé : pose une taille cible — un connecteur se donne en millimètres",
      "connector not placed: set a target size — a connector is sized in millimeters"),
    L(F, 2668, '"connecteur non posé : la coupe n\'a gardé qu\'un côté — il faut les deux moitiés à relier"',
      "etabli.et2_connecteur.un_cote",
      "connecteur non posé : la coupe n'a gardé qu'un côté — il faut les deux moitiés à relier",
      "connector not placed: the cut kept only one side — both halves are needed to join"),
    L(F, 2673, '"connecteur non posé : la coupe a traversé plusieurs pièces — coupe-en une seule à la fois"',
      "etabli.et2_connecteur.plusieurs",
      "connecteur non posé : la coupe a traversé plusieurs pièces — coupe-en une seule à la fois",
      "connector not placed: the cut went through several parts — cut one at a time"),
    S(F, 2679, '`${p.role === "male" ? "mâle" : p.role} « ${p.nom} »`',
      'dzT("etabli.et2_connecteur.role_nom", { role: p.role === "male" ? dzT("etabli.et2_connecteur.male") '
      ': p.role === "femelle" ? dzT("etabli.et2_connecteur.femelle") : p.role, nom: p.nom })',
      {"etabli.et2_connecteur.role_nom": ("{role} « {nom} »", "{role} “{nom}”"),
       "etabli.et2_connecteur.male": ("mâle", "male", "contexte"),
       "etabli.et2_connecteur.femelle": ("femelle", "female", "contexte")}),
    S(F, 2680, 'direAvis(`${type} posé (version ${bilan.derniere.version}) : ${roles.join(", ")} — jeu '
      '${JEU_CONNECTEUR.toLocaleString("fr-FR")} millimètre(s) `\r\n'
      '    + "porté par la femelle ; passe « Réparer en un clic » pour souder la couture");',
      'direAvis(dzT("etabli.et2_connecteur.pose", { type: ' + types("type") + ', version: bilan.derniere.version, '
      'roles: roles.join(", "), jeu: JEU_CONNECTEUR.toLocaleString("fr-FR") }));',
      {"etabli.et2_connecteur.pose": (
          "{type} posé (version {version}) : {roles} — jeu {jeu} millimètre(s) porté par la femelle ; passe "
          "« Réparer en un clic » pour souder la couture",
          "{type} placed (version {version}): {roles} — {jeu} millimeter(s) of clearance on the female part; run "
          "“Repair in one click” to weld the seam"),
       **D_TYPES}),

    # ── le point de vue ─────────────────────────────────────────────────────────────────────────────────────
    L(F, 2816, '"Depuis +Z, en orthographique — un axe du modèle, pas de la plaque"', "etabli.et2_vue.titre_face",
      "Depuis +Z, en orthographique — un axe du modèle, pas de la plaque",
      "From +Z, orthographic — a model axis, not a plate axis"),
    L(F, 2817, '"Depuis +Y, en orthographique — un axe du modèle, pas de la plaque"', "etabli.et2_vue.titre_dessus",
      "Depuis +Y, en orthographique — un axe du modèle, pas de la plaque",
      "From +Y, orthographic — a model axis, not a plate axis"),
    L(F, 2818, '"Depuis +X, en orthographique — un axe du modèle, pas de la plaque"', "etabli.et2_vue.titre_profil",
      "Depuis +X, en orthographique — un axe du modèle, pas de la plaque",
      "From +X, orthographic — a model axis, not a plate axis"),
    L(F, 2834, '"Perspective"', "etabli.et2_vue.perspective", "Perspective", "Perspective"),
    L(F, 2834, '"Isométrique"', "etabli.et2_vue.isometrique", "Isométrique", "Isometric"),
    L(F, 2836, '"Revenir à la caméra à fuite, sur la direction d\'origine"', "etabli.et2_vue.titre_perspective",
      "Revenir à la caméra à fuite, sur la direction d'origine",
      "Back to the perspective camera, in the original direction"),
    S(F, 2837, '"Caméra orthographique sur (1, 1, 1) : les fuyantes disparaissent, "\r\n'
      '      + "deux longueurs égales se lisent égales où qu\'elles soient"',
      'dzT("etabli.et2_vue.titre_iso")',
      {"etabli.et2_vue.titre_iso": (
          "Caméra orthographique sur (1, 1, 1) : les fuyantes disparaissent, deux longueurs égales se lisent égales "
          "où qu'elles soient",
          "Orthographic camera on (1, 1, 1): vanishing lines disappear, two equal lengths read equal wherever they "
          "are")}),
    L(F, 2851, '" · c\'est cette vue qui regarde la plaque en face"', "etabli.et2_vue.face_plaque",
      " · c'est cette vue qui regarde la plaque en face", " · this is the view that faces the plate"),
    L(F, 2894, '"aucun modèle chargé — il n\'y a pas encore de caméra à orienter"', "etabli.et2_vue.rien_a_orienter",
      "aucun modèle chargé — il n'y a pas encore de caméra à orienter",
      "no model loaded — there is no camera to orient yet"),
    S(F, 2905, '`vue inconnue « ${nom} » — aucune projection ne lui est associée`',
      'dzT("etabli.et2_vue.inconnue", { nom })',
      {"etabli.et2_vue.inconnue": ("vue inconnue « {nom} » — aucune projection ne lui est associée",
                                   "unknown view “{nom}” — no projection is associated with it")}),
    L(F, 2947, '"aucun modèle chargé — il n\'y a pas encore de caméra à basculer"', "etabli.et2_vue.rien_a_basculer",
      "aucun modèle chargé — il n'y a pas encore de caméra à basculer",
      "no model loaded — there is no camera to switch yet"),

    # ── le panneau Parties et la plaque ─────────────────────────────────────────────────────────────────────
    S(F, 3001, '`<span>${x.tris.toLocaleString("fr-FR")} tri</span>`',
      '`<span>${dzT("etabli.et2_parties.tris", { n: x.tris.toLocaleString("fr-FR") })}</span>`',
      {"etabli.et2_parties.tris": ("{n} tri", "{n} tris")}),
    S(F, 3031, '? "montrer" : "masquer")',
      '? dzT("etabli.et2_plaque.montrer_piece") : dzT("etabli.et2_plaque.masquer_piece"))',
      {"etabli.et2_plaque.montrer_piece": ("montrer cette pièce", "show this part"),
       "etabli.et2_plaque.masquer_piece": ("masquer cette pièce", "hide this part")}),
    S(F, 3036, '\r\n    <div class="plaque-tete">Sur la plaque · ${PLQ.pieces.length} pièce(s)',
      '\r\n    <div class="plaque-tete">${dzT("etabli.et2_plaque.tete", { n: PLQ.pieces.length })}',
      {"etabli.et2_plaque.tete": ("Sur la plaque · {n} pièce(s)", "On the plate · {n} part(s)")}),
    S(F, 3045, 'title="${oeil(x.cle)} cette pièce"', 'title="${oeil(x.cle)}"', {}),
    S(F, 3046, 'aria-label="${oeil(x.cle)} cette pièce"', 'aria-label="${oeil(x.cle)}"', {}),
    S(F, 3050, '<label>rotation de <b>', '<label>${dzT("etabli.et2_plaque.rotation_de")} <b>',
      {"etabli.et2_plaque.rotation_de": ("rotation de", "rotation of")}),
    S(F, 3052, '"> °</label>\r\n         <span>glisser déplace (aimanté au pas du plateau, Maj libère) ·\r\n'
      '           flèches = un pas, Alt fin, Ctrl ×10 · l\'anneau tourne\r\n'
      '           (Maj = ${PAS_ROTATION}°)</span>',
      '"> °</label>\r\n         <span>${dzT("etabli.et2_plaque.aide_courante", { pas: PAS_ROTATION })}</span>',
      {"etabli.et2_plaque.aide_courante": (
          "glisser déplace (aimanté au pas du plateau, Maj libère) · flèches = un pas, Alt fin, Ctrl ×10 · l'anneau "
          "tourne (Maj = {pas}°)",
          "drag moves (snapped to the bed step, Shift frees) · arrows = one step, Alt fine, Ctrl ×10 · the ring "
          "rotates (Shift = {pas}°)")}),
    S(F, 3056, '<span>cliquez une pièce : la glisser la déplace (aimantée au pas du\r\n'
      '           plateau, Maj libère), l\'anneau la tourne (Maj = ${PAS_ROTATION}°),\r\n'
      '           les flèches la poussent d\'un pas (Alt fin, Ctrl ×10)</span>',
      '<span>${dzT("etabli.et2_plaque.aide_aucune", { pas: PAS_ROTATION })}</span>',
      {"etabli.et2_plaque.aide_aucune": (
          "cliquez une pièce : la glisser la déplace (aimantée au pas du plateau, Maj libère), l'anneau la tourne "
          "(Maj = {pas}°), les flèches la poussent d'un pas (Alt fin, Ctrl ×10)",
          "click a part: dragging moves it (snapped to the bed step, Shift frees), the ring rotates it "
          "(Shift = {pas}°), the arrows nudge it one step (Alt fine, Ctrl ×10)")}),
    S(F, 3058, '</div>\r\n    <p class="plaque-note">Vue seulement : le maillage assemblé reste la\r\n'
      '      vérité — déplacer ici n\'écrit jamais dans le modèle, seulement dans le\r\n'
      '      plan de plaque. <span',
      '</div>\r\n    <p class="plaque-note">${dzT("etabli.et2_plaque.note")} <span',
      {"etabli.et2_plaque.note": (
          "Vue seulement : le maillage assemblé reste la vérité — déplacer ici n'écrit jamais dans le modèle, "
          "seulement dans le plan de plaque.",
          "View only: the assembled mesh remains the truth — moving here never writes to the model, only to the "
          "plate layout.")}),
    S(F, 3062, '` ${PLQ.vides} nœud(s) sans géométrie ne sont pas étalés : un\r\n'
      '      contenant n\'a rien à montrer, et son œil ne commanderait rien.`',
      '` ${dzT("etabli.et2_plaque.vides", { n: PLQ.vides })}`',
      {"etabli.et2_plaque.vides": (
          "{n} nœud(s) sans géométrie ne sont pas étalés : un contenant n'a rien à montrer, et son œil ne "
          "commanderait rien.",
          "{n} node(s) without geometry are not laid out: a container has nothing to show, and its eye would "
          "control nothing.")}),
    S(F, 3064, '` ${PLQ.partages} matériau(x) partagé(s) entre pièces — leur teinte\r\n'
      '      sur le modèle n\'est pas fidèle (le dernier parcouru gagne) ; la\r\n'
      '      pastille, elle, l\'est.`',
      '` ${dzT("etabli.et2_plaque.partages", { n: PLQ.partages })}`',
      {"etabli.et2_plaque.partages": (
          "{n} matériau(x) partagé(s) entre pièces — leur teinte sur le modèle n'est pas fidèle (le dernier "
          "parcouru gagne) ; la pastille, elle, l'est.",
          "{n} material(s) shared between parts — their tint on the model is not faithful (the last one visited "
          "wins); the swatch is.")}),
    L(F, 3078, '"aucune partie à cette granularité"', "etabli.et2_parties.aucune_partie",
      "aucune partie à cette granularité", "no part at this granularity"),
    L(F, 3078, '"aucun modèle chargé"', AUCUN, *D_AUCUN[AUCUN]),
    S(F, 3078, '</div>\r\n    <div class="parties-actions">\r\n      <button id="btnIsoler">Isoler la sélection<',
      '</div>\r\n    <div class="parties-actions">\r\n      <button id="btnIsoler">${dzT("etabli.et2_parties.isoler")}<',
      {"etabli.et2_parties.isoler": ("Isoler la sélection", "Isolate selection")}),
    S(F, 3081, '>Tout revoir<', '>${dzT("etabli.et2_parties.tout_revoir")}<',
      {"etabli.et2_parties.tout_revoir": ("Tout revoir", "Show all")}),
    S(F, 3082, '>Séparer la sélection en une version<', '>${dzT("etabli.et2_parties.separer")}<',
      {"etabli.et2_parties.separer": ("Séparer la sélection en une version", "Split the selection into a version")}),
    S(F, 3083, 'title="Une version PAR élément coché, toutes nées de la version courante (des sœurs, pas une chaîne)"',
      'title="${dzT("etabli.et2_parties.titre_separement")}"',
      {"etabli.et2_parties.titre_separement": (
          "Une version PAR élément coché, toutes nées de la version courante (des sœurs, pas une chaîne)",
          "One version PER ticked item, all born from the current version (siblings, not a chain)")}),
    S(F, 3084, '> une par une</label>', '> ${dzT("etabli.et2_parties.une_par_une")}</label>',
      {"etabli.et2_parties.une_par_une": ("une par une", "one by one")}),
    S(F, 3086, 'title="Pose une matière du Material Forge sur les pièces cochées — écrit une version"',
      'title="${dzT("etabli.et2_parties.titre_habiller")}"',
      {"etabli.et2_parties.titre_habiller": (
          "Pose une matière du Material Forge sur les pièces cochées — écrit une version",
          "Applies a Material Forge material to the ticked parts — writes a version")}),
    S(F, 3087, '>— matière —<', '>${dzT("etabli.et2_parties.matiere_vide")}<',
      {"etabli.et2_parties.matiere_vide": ("— matière —", "— material —")}),
    S(F, 3088, '>Habiller<', '>${dzT("etabli.et2_parties.habiller")}<',
      {"etabli.et2_parties.habiller": ("Habiller", "Skin")}),
    S(F, 3089, 'title="Cavités (rouge) et arêtes (vert) calculées depuis la géométrie, en vue B — rien n\'est écrit"',
      'title="${dzT("etabli.et2_parties.titre_masques")}"',
      {"etabli.et2_parties.titre_masques": (
          "Cavités (rouge) et arêtes (vert) calculées depuis la géométrie, en vue B — rien n'est écrit",
          "Cavities (red) and edges (green) computed from the geometry, in view B — nothing is written")}),
    S(F, 3089, '>Masques<', '>${dzT("etabli.et2_parties.masques")}<',
      {"etabli.et2_parties.masques": ("Masques", "Masks")}),
    S(F, 3091, 'title="Union, différence ou intersection de deux groupes de pièces — écrit une version"',
      'title="${dzT("etabli.et2_bool.titre")}"',
      {"etabli.et2_bool.titre": ("Union, différence ou intersection de deux groupes de pièces — écrit une version",
                                 "Union, difference or intersection of two groups of parts — writes a version")}),
    S(F, 3094, '>différence (A − B)<', '>${dzT("etabli.et2_bool.option_difference")}<',
      {"etabli.et2_bool.option_difference": ("différence (A − B)", "difference (A − B)")}),
    S(F, 3097, '>A = sélection<', '>${dzT("etabli.et2_bool.a_selection")}<',
      {"etabli.et2_bool.a_selection": ("A = sélection", "A = selection")}),
    S(F, 3098, '>B = sélection<', '>${dzT("etabli.et2_bool.b_selection")}<',
      {"etabli.et2_bool.b_selection": ("B = sélection", "B = selection")}),
    S(F, 3099, '>Appliquer<', '>${dzT("etabli.et2_bool.appliquer")}<',
      {"etabli.et2_bool.appliquer": ("Appliquer", "Apply")}),

    # ── le gizmo, la file d'attente ─────────────────────────────────────────────────────────────────────────
    S(F, 3221, '"la plaque est une VUE : revenez à « Assemblé » pour "\r\n      + "déplacer une pièce"',
      'dzT("etabli.et2_gizmo.plaque_vue")',
      {"etabli.et2_gizmo.plaque_vue": ("la plaque est une VUE : revenez à « Assemblé » pour déplacer une pièce",
                                       "the plate is a VIEW: go back to “Assembled” to move a part")}),
    S(F, 3242, '"ce maillage n\'est rattaché à aucun nœud glTF — "\r\n'
      '      + "rien à envoyer au serveur, donc rien à déplacer"',
      'dzT("etabli.et2_gizmo.sans_noeud")',
      {"etabli.et2_gizmo.sans_noeud": (
          "ce maillage n'est rattaché à aucun nœud glTF — rien à envoyer au serveur, donc rien à déplacer",
          "this mesh is not attached to any glTF node — nothing to send to the server, so nothing to move")}),
    S(F, 3361, '"« recentrer » défait « posé sur une face » : décoche « recentrer »"\r\n'
      '    + " ou annule l\'assise — le recentrage est écrit APRÈS l\'assise."',
      'dzT("etabli.et2_attente.contradiction")',
      {"etabli.et2_attente.contradiction": (
          "« recentrer » défait « posé sur une face » : décoche « recentrer » ou annule l'assise — le recentrage "
          "est écrit APRÈS l'assise.",
          "“recenter” undoes “laid on a face”: untick “recenter” or cancel the lay-flat — recentering is written "
          "AFTER the lay-flat.")}),
    S(F, 3370, '`${Object.keys(t.charge).length} nœud(s) déplacé(s)`',
      'dzT("etabli.et2_attente.deplaces", { n: Object.keys(t.charge).length })',
      {"etabli.et2_attente.deplaces": ("{n} nœud(s) déplacé(s)", "{n} node(s) moved")}),
    S(F, 3371, '`${t.charge.noeuds.length} nœud(s) à séparer`',
      'dzT("etabli.et2_attente.a_separer", { n: t.charge.noeuds.length })',
      {"etabli.et2_attente.a_separer": ("{n} nœud(s) à séparer", "{n} node(s) to split")}),
    L(F, 3372, '" — un fichier par élément"', "etabli.et2_attente.un_fichier", " — un fichier par élément",
      " — one file per item"),
    S(F, 3373, '`réparer l\'assise : axe ${t.charge.axe_haut}, échelle ${t.charge.echelle}`',
      'dzT("etabli.et2_attente.reparer", { axe: t.charge.axe_haut, echelle: t.charge.echelle })',
      {"etabli.et2_attente.reparer": ("réparer l'assise : axe {axe}, échelle {echelle}",
                                      "fix placement: axis {axe}, scale {echelle}")}),
    L(F, 3374, '", recentré"', "etabli.et2_attente.recentre", ", recentré", ", recentered"),
    S(F, 3375, '`posé sur une face (normale ${t.charge.normale.map(fmtCoord).join(", ")})`',
      'dzT("etabli.et2_attente.assise", { normale: t.charge.normale.map(fmtCoord).join(", ") })',
      {"etabli.et2_attente.assise": ("posé sur une face (normale {normale})", "laid on a face (normal {normale})")}),
    S(F, 3376, '`coupe de ${t.charge.noeuds.length} pièce(s) — garder ${t.charge.garder}`',
      'dzT("etabli.et2_attente.coupe", { n: t.charge.noeuds.length, garder: t.charge.garder === "deux" '
      '? dzT("etabli.et2_attente.les_deux") : t.charge.garder })',
      {"etabli.et2_attente.coupe": ("coupe de {n} pièce(s) — garder {garder}", "cut of {n} part(s) — keep {garder}"),
       "etabli.et2_attente.les_deux": ("les deux", "both", "contexte")}),
    S(F, 3377, '`réparer le maillage : ${t.charge.actions.map((a) => LIBELLE_ACTION[a] || a).join(", ")}`',
      'dzT("etabli.et2_attente.reparer_maillage", { actions: t.charge.actions.map((a) => LIBELLE_ACTION[a] || a)'
      '.join(", ") })',
      {"etabli.et2_attente.reparer_maillage": ("réparer le maillage : {actions}", "repair the mesh: {actions}")}),
    S(F, 3378, '`décimer vers ${t.charge.preset || t.charge.target_tris} triangles`',
      'dzT("etabli.et2_attente.decimer", { cible: t.charge.preset || t.charge.target_tris })',
      {"etabli.et2_attente.decimer": ("décimer vers {cible} triangles", "decimate to {cible} triangles")}),
    S(F, 3379, '`creuser : paroi ${fmtMesure(t.charge.paroi)} ${uniteCourante()}`',
      'dzT("etabli.et2_attente.creuser", { paroi: fmtMesure(t.charge.paroi), unite: uniteCourante() })',
      {"etabli.et2_attente.creuser": ("creuser : paroi {paroi} {unite}", "hollow: wall {paroi} {unite}")}),
    S(F, 3380, '`percer : ⌀ ${fmtMesure(2 * t.charge.rayon)} ${uniteCourante()}`',
      'dzT("etabli.et2_attente.percer", { d: fmtMesure(2 * t.charge.rayon), unite: uniteCourante() })',
      {"etabli.et2_attente.percer": ("percer : ⌀ {d} {unite}", "drill: ⌀ {d} {unite}")}),
    S(F, 3381, '`${t.charge.operation} de ${t.charge.a.length} et ${t.charge.b.length} pièce(s)`',
      'dzT("etabli.et2_attente.booleen", { op: ' + ops("t.charge.operation") + ', a: t.charge.a.length, '
      'b: t.charge.b.length })',
      {"etabli.et2_attente.booleen": ("{op} de {a} et {b} pièce(s)", "{op} of {a} and {b} part(s)"), **D_OPS}),
    S(F, 3382, '`connecteur ${t.charge.type} : rayon ${fmtMesure(t.charge.rayon)} ${uniteCourante()}`',
      'dzT("etabli.et2_attente.connecteur", { type: ' + types("t.charge.type") + ', rayon: fmtMesure(t.charge.rayon), '
      'unite: uniteCourante() })',
      {"etabli.et2_attente.connecteur": ("connecteur {type} : rayon {rayon} {unite}",
                                         "connector {type}: radius {rayon} {unite}"), **D_TYPES}),
    S(F, 3383, '`matériau ${t.charge.materiau} : ${Object.keys(t.charge).filter((k) => k !== "materiau").join(", ")}`',
      'dzT("etabli.et2_attente.materiau", { nom: t.charge.materiau, champs: Object.keys(t.charge)'
      '.filter((k) => k !== "materiau").join(", ") })',
      {"etabli.et2_attente.materiau": ("matériau {nom} : {champs}", "material {nom}: {champs}")}),
    S(F, 3384, '`habiller ${t.charge.lots.length} partie(s)`',
      'dzT("etabli.et2_attente.habiller", { n: t.charge.lots.length })',
      {"etabli.et2_attente.habiller": ("habiller {n} partie(s)", "skin {n} part(s)")}),

    # ── les opérations qui écrivent seules : libellés ──────────────────────────────────────────────────────
    L(F, 3391, '"réparer le maillage"', "etabli.et2_op.reparer_maillage", "réparer le maillage", "repair the mesh"),
    L(F, 3391, '"décimer"', "etabli.et2_op.decimer", "décimer", "decimate"),
    L(F, 3391, '"creuser"', "etabli.et2_op.creuser", "creuser", "hollow"),
    L(F, 3391, '"percer"', "etabli.et2_op.percer", "percer", "drill"),
    L(F, 3392, '"le booléen"', "etabli.et2_op.booleen", "le booléen", "the boolean"),
    L(F, 3392, '"le connecteur"', "etabli.et2_op.connecteur", "le connecteur", "the connector"),
    L(F, 3393, '"le matériau"', "etabli.et2_op.materiau", "le matériau", "the material"),
    L(F, 3393, '"l\'habillage"', "etabli.et2_op.habillage", "l'habillage", "the skinning"),
    L(F, 3394, '"sommets confondus"', "etabli.et2_action.souder", "sommets confondus", "coincident vertices"),
    L(F, 3394, '"faces dupliquées"', "etabli.et2_action.doublons", "faces dupliquées", "duplicate faces"),
    L(F, 3394, '"triangles plats"', "etabli.et2_action.degeneres", "triangles plats", "flat triangles"),
    L(F, 3395, '"normales unifiées"', "etabli.et2_action.normales", "normales unifiées", "unified normals"),
    L(F, 3395, '"trous bouchés"', "etabli.et2_action.trous", "trous bouchés", "filled holes"),
    L(F, 3400, '"aucun modèle chargé"', AUCUN, *D_AUCUN[AUCUN]),
    L(F, 3401, '"une écriture est en cours — attends la fin de la série"', "etabli.et2_ecrire.en_cours",
      "une écriture est en cours — attends la fin de la série", "a write is in progress — wait for the batch to finish"),
    S(F, 3403, '`${S.enAttente.length} modification(s) en attente — écris-les d\'abord : « ${LIBELLE_OP[operation] '
      '|| operation} » `\r\n      + "renumérote les nœuds et ne se met pas en file derrière elles"',
      'dzT("etabli.et2_ecrire.attente_op", { n: S.enAttente.length, op: LIBELLE_OP[operation] || operation })',
      {"etabli.et2_ecrire.attente_op": (
          "{n} modification(s) en attente — écris-les d'abord : « {op} » renumérote les nœuds et ne se met pas en "
          "file derrière elles",
          "{n} pending change(s) — write them first: “{op}” renumbers the nodes and does not queue behind them")}),

    # ── les bilans ─────────────────────────────────────────────────────────────────────────────────────────
    S(F, 3428, '`, ${p.bouches} trou(s) bouché(s)${p.non ? `, ${p.non} NON bouché(s) (raisons dans la fiche)` : ""}`',
      '`, ${dzT("etabli.et2_bilan.trous_bouches", { n: p.bouches })}${p.non ? `, '
      '${dzT("etabli.et2_bilan.trous_non", { n: p.non })}` : ""}`',
      {"etabli.et2_bilan.trous_bouches": ("{n} trou(s) bouché(s)", "{n} hole(s) filled"),
       "etabli.et2_bilan.trous_non": ("{n} NON bouché(s) (raisons dans la fiche)",
                                      "{n} NOT filled (reasons in the version sheet)")}),
    S(F, 3429, 'direAvis(`maillage réparé (version ${fiche.version}) : ${p.soudes} sommet(s) soudé(s), '
      '${p.doublons} doublon(s), `\r\n'
      '    + `${p.degeneres} triangle(s) plat(s), ${p.retournes} retourné(s)${trous} — `\r\n'
      '    + (src.ferme_apres ? "fermé" : (src.ferme_avant ? "fermé avant, OUVERT après" : "encore ouvert")));',
      'direAvis(dzT("etabli.et2_bilan.repare", { version: fiche.version, soudes: p.soudes, doublons: p.doublons, '
      'plats: p.degeneres, retournes: p.retournes, trous, etat: src.ferme_apres ? dzT("etabli.et2_bilan.ferme") '
      ': (src.ferme_avant ? dzT("etabli.et2_bilan.ferme_avant") : dzT("etabli.et2_bilan.ouvert")) }));',
      {"etabli.et2_bilan.repare": (
          "maillage réparé (version {version}) : {soudes} sommet(s) soudé(s), {doublons} doublon(s), {plats} "
          "triangle(s) plat(s), {retournes} retourné(s){trous} — {etat}",
          "mesh repaired (version {version}): {soudes} vertex(es) welded, {doublons} duplicate(s), {plats} flat "
          "triangle(s), {retournes} flipped{trous} — {etat}"),
       "etabli.et2_bilan.ferme": ("fermé", "closed", "contexte"),
       "etabli.et2_bilan.ferme_avant": ("fermé avant, OUVERT après", "closed before, OPEN after"),
       "etabli.et2_bilan.ouvert": ("encore ouvert", "still open")}),
    S(F, 3439, 'direAvis(`creusé (version ${fiche.version}) : paroi ${fmtMesure(src.paroi)} ${uniteCourante()} sur '
      '${src.pieces.length} pièce(s)`\r\n'
      '    + (src.avertissement ? ` — paroi qui tient : ${fmtMesure(src.paroi_max)} ${uniteCourante()} — '
      '${src.avertissement}` : "")\r\n'
      '    + (src.limite ? ` — limite : ${src.limite}` : ""));',
      'direAvis(dzT("etabli.et2_bilan.creuse", { version: fiche.version, paroi: fmtMesure(src.paroi), '
      'unite: uniteCourante(), n: src.pieces.length })\r\n'
      '    + (src.avertissement ? dzT("etabli.et2_bilan.paroi_tient", { paroi: fmtMesure(src.paroi_max), '
      'unite: uniteCourante(), avert: src.avertissement }) : "")\r\n'
      '    + (src.limite ? dzT("etabli.et2_bilan.limite", { limite: src.limite }) : ""));',
      {"etabli.et2_bilan.creuse": ("creusé (version {version}) : paroi {paroi} {unite} sur {n} pièce(s)",
                                   "hollowed (version {version}): wall {paroi} {unite} on {n} part(s)"),
       "etabli.et2_bilan.paroi_tient": (" — paroi qui tient : {paroi} {unite} — {avert}",
                                        " — wall that holds: {paroi} {unite} — {avert}"),
       "etabli.et2_bilan.limite": (" — limite : {limite}", " — limit: {limite}")}),
    S(F, 3449, 'direAvis(`percé (version ${fiche.version}) : ⌀ ${fmtMesure(2 * src.rayon)} ${uniteCourante()}, '
      'paroi traversée `\r\n'
      '    + `${fmtMesure(q.paroi_traversee)} ${uniteCourante()} — ${q.retires_dehors} + ${q.retires_dedans} '
      'triangle(s) `\r\n'
      '    + `retirés (dehors + dedans), tube de ${q.tube} triangle(s)`\r\n'
      '    + (src.pieces.length > 1 ? ` — ${src.pieces.length} pièces percées` : ""));',
      'direAvis(dzT("etabli.et2_bilan.perce", { version: fiche.version, d: fmtMesure(2 * src.rayon), '
      'unite: uniteCourante(), paroi: fmtMesure(q.paroi_traversee), dehors: q.retires_dehors, '
      'dedans: q.retires_dedans, tube: q.tube })\r\n'
      '    + (src.pieces.length > 1 ? dzT("etabli.et2_bilan.pieces_percees", { n: src.pieces.length }) : ""));',
      {"etabli.et2_bilan.perce": (
          "percé (version {version}) : ⌀ {d} {unite}, paroi traversée {paroi} {unite} — {dehors} + {dedans} "
          "triangle(s) retirés (dehors + dedans), tube de {tube} triangle(s)",
          "drilled (version {version}): ⌀ {d} {unite}, wall crossed {paroi} {unite} — {dehors} + {dedans} "
          "triangle(s) removed (outside + inside), tube of {tube} triangle(s)"),
       "etabli.et2_bilan.pieces_percees": (" — {n} pièces percées", " — {n} parts drilled")}),
    L(F, 3462, '"perçage : clique sur la peau de la pièce à percer"', "etabli.et2_foret.clique_peau",
      "perçage : clique sur la peau de la pièce à percer", "drilling: click the skin of the part to drill"),
    L(F, 3466, '"perçage : un diamètre en millimètres > 0"', "etabli.et2_foret.diametre",
      "perçage : un diamètre en millimètres > 0", "drilling: a diameter in millimeters > 0"),
    L(F, 3469, '"pose une taille cible : un trou de drainage en millimètres n\'a de sens qu\'avec une échelle"',
      "etabli.et2_foret.sans_cible",
      "pose une taille cible : un trou de drainage en millimètres n'a de sens qu'avec une échelle",
      "set a target size: a drain hole in millimeters only makes sense with a scale"),
    S(F, 3481, 'direAvis(`décimé (version ${fiche.version}) : ${src.before.tris} → ${src.after.tris} triangles `\r\n'
      '    + `(−${src.reduction_pct} %)${src.aggressive ? ", passe agressive" : ""}`\r\n'
      '    + (src.cible_atteinte === false ? ` — cible de ${src.target_tris} NON atteinte, le maillage ne se simplifie '
      'pas plus` : ""));',
      'direAvis(dzT("etabli.et2_bilan.decime", { version: fiche.version, avant: src.before.tris, '
      'apres: src.after.tris, pct: src.reduction_pct })\r\n'
      '    + (src.aggressive ? dzT("etabli.et2_bilan.agressive") : "")\r\n'
      '    + (src.cible_atteinte === false ? dzT("etabli.et2_bilan.cible_non", { cible: src.target_tris }) : ""));',
      {"etabli.et2_bilan.decime": ("décimé (version {version}) : {avant} → {apres} triangles (−{pct} %)",
                                   "decimated (version {version}): {avant} → {apres} triangles (−{pct}%)"),
       "etabli.et2_bilan.agressive": (", passe agressive", ", aggressive pass"),
       "etabli.et2_bilan.cible_non": (" — cible de {cible} NON atteinte, le maillage ne se simplifie pas plus",
                                      " — target of {cible} NOT reached, the mesh will not simplify any further")}),

    # ── la barre d'attente, l'écriture ─────────────────────────────────────────────────────────────────────
    S(F, 3496, '>index de nœud déduits d\'un NOM — repli heuristique, à vérifier<',
      '>${dzT("etabli.et2_attente.doute")}<',
      {"etabli.et2_attente.doute": ("index de nœud déduits d'un NOM — repli heuristique, à vérifier",
                                    "node indices inferred from a NAME — heuristic fallback, to be checked")}),
    L(F, 3516, '"en cours d\'écriture"', "etabli.et2_attente.en_cours", "en cours d'écriture", "being written"),
    L(F, 3516, '"en attente"', "etabli.et2_attente.en_attente", "en attente", "pending"),
    S(F, 3517, '`<b>${S.enAttente.length} modification(s) ${etat}</b>',
      '`<b>${dzT("etabli.et2_attente.n_modifs", { n: S.enAttente.length, etat })}</b>',
      {"etabli.et2_attente.n_modifs": ("{n} modification(s) {etat}", "{n} change(s) {etat}")}),
    S(F, 3518, 'title="ordre d\'écriture imposé : déplacer, puis poser sur une face, puis réparer, puis séparer — le '
      'déplacement rend au fichier le monde affiché, l\'assise y est mesurée, l\'extraction renumérote les nœuds"',
      'title="${dzT("etabli.et2_attente.ordre")}"',
      {"etabli.et2_attente.ordre": (
          "ordre d'écriture imposé : déplacer, puis poser sur une face, puis réparer, puis séparer — le déplacement "
          "rend au fichier le monde affiché, l'assise y est mesurée, l'extraction renumérote les nœuds",
          "enforced write order: move, then lay on a face, then repair, then split — moving gives the file the "
          "displayed world, the lay-flat is measured in it, extraction renumbers the nodes")}),
    S(F, 3519, '>écrire la version<', '>${dzT("etabli.et2_attente.ecrire")}<',
      {"etabli.et2_attente.ecrire": ("écrire la version", "write the version")}),
    S(F, 3520, '>annuler<', '>${dzT("etabli.et2_attente.annuler")}<',
      {"etabli.et2_attente.annuler": ("annuler", "cancel", "contexte")}),
    L(F, 3538, '"aucun modèle chargé — rien à écrire"', "etabli.et2_ecrire.rien_a_ecrire",
      "aucun modèle chargé — rien à écrire", "no model loaded — nothing to write"),
    S(F, 3587, '"l\'étape « décimée » n\'est pas une version numérotée : "\r\n'
      '          + "chargez une version pour la corriger"',
      'dzT("etabli.et2_ecrire.etape_decimee")',
      {"etabli.et2_ecrire.etape_decimee": (
          "l'étape « décimée » n'est pas une version numérotée : chargez une version pour la corriger",
          "the “decimated” stage is not a numbered version: load a version to fix it")}),
    S(F, 3665, 'direRefus(`écrit : ${ecrites.join(", ") || "rien"}`\r\n'
      '        + (adopte ? ` · adoption faite (job ${S.a.job})` : "")\r\n'
      '        + ` · abandonné : ${restantes.join(", ") || "rien"}`',
      'direRefus(dzT("etabli.et2_ecrire.ecrit", { ops: ecrites.join(", ") || dzT("etabli.et2_ecrire.rien") })\r\n'
      '        + (adopte ? dzT("etabli.et2_ecrire.adoption", { job: S.a.job }) : "")\r\n'
      '        + dzT("etabli.et2_ecrire.abandonne", { ops: restantes.join(", ") || dzT("etabli.et2_ecrire.rien") })',
      {"etabli.et2_ecrire.ecrit": ("écrit : {ops}", "written: {ops}"),
       "etabli.et2_ecrire.rien": ("rien", "nothing", "contexte"),
       "etabli.et2_ecrire.adoption": (" · adoption faite (job {job})", " · adopted (job {job})"),
       "etabli.et2_ecrire.abandonne": (" · abandonné : {ops}", " · dropped: {ops}")}),

    # ── la vignette ────────────────────────────────────────────────────────────────────────────────────────
    S(F, 3804, '`vignette non fabriquée (${e.message}) — la version `\r\n      + `${version} est écrite`',
      'dzT("etabli.et2_vignette.non_fabriquee", { msg: e.message, version })',
      {"etabli.et2_vignette.non_fabriquee": ("vignette non fabriquée ({msg}) — la version {version} est écrite",
                                             "thumbnail not created ({msg}) — version {version} is written")}),
    L(F, 3813, '"toBlob n\'a rien rendu"', "etabli.et2_vignette.toblob_vide", "toBlob n'a rien rendu",
      "toBlob returned nothing"),
    X(F, 3814, '"image/png"', "type MIME"),
    X(F, 3820, '"image/png"', "type MIME (en-tête de requête)"),
    S(F, 3823, '`vignette non envoyée (${e.message}) — la version `\r\n      + `${version} est écrite`',
      'dzT("etabli.et2_vignette.non_envoyee", { msg: e.message, version })',
      {"etabli.et2_vignette.non_envoyee": ("vignette non envoyée ({msg}) — la version {version} est écrite",
                                           "thumbnail not sent ({msg}) — version {version} is written")}),

    # ── séparer, booléens ──────────────────────────────────────────────────────────────────────────────────
    S(F, 3863, '"aucun nœud glTF dans la sélection — un matériau, ou une "\r\n'
      '      + "primitive de maillage, n\'a pas d\'index à envoyer"',
      'dzT("etabli.et2_parties.sans_noeud")',
      {"etabli.et2_parties.sans_noeud": (
          "aucun nœud glTF dans la sélection — un matériau, ou une primitive de maillage, n'a pas d'index à envoyer",
          "no glTF node in the selection — a material, or a mesh primitive, has no index to send")}),
    S(F, 3886, '`${cote.toUpperCase()} : coche d\'abord des pièces dans la liste — A et B sont des groupes de nœuds`',
      'dzT("etabli.et2_bool.coche_dabord", { cote: cote.toUpperCase() })',
      {"etabli.et2_bool.coche_dabord": (
          "{cote} : coche d'abord des pièces dans la liste — A et B sont des groupes de nœuds",
          "{cote}: tick parts in the list first — A and B are groups of nodes")}),
    L(F, 3891, '"un même nœud ne peut pas être à la fois dans A et dans B"', "etabli.et2_bool.meme_noeud",
      "un même nœud ne peut pas être à la fois dans A et dans B", "the same node cannot be in both A and B"),
    L(F, 3901, '"choisis A puis B (« A = sélection », « B = sélection ») : un booléen a deux opérandes"',
      "etabli.et2_bool.choisis", "choisis A puis B (« A = sélection », « B = sélection ») : un booléen a deux opérandes",
      "choose A then B (“A = selection”, “B = selection”): a boolean has two operands"),
    S(F, 3910, 'direAvis(`${src.booleen} écrite (version ${bilan.derniere.version}) : ${src.triangles_a} + '
      '${src.triangles_b} → `\r\n    + `${src.triangles} triangles — ${src.couture} ; ${src.matieres}`);',
      'direAvis(dzT("etabli.et2_bool.ecrite", { op: ' + ops("src.booleen") + ', version: bilan.derniere.version, '
      'a: src.triangles_a, b: src.triangles_b, n: src.triangles, couture: src.couture, matieres: src.matieres }));',
      {"etabli.et2_bool.ecrite": ("{op} écrite (version {version}) : {a} + {b} → {n} triangles — {couture} ; "
                                  "{matieres}",
                                  "{op} written (version {version}): {a} + {b} → {n} triangles — {couture}; "
                                  "{matieres}"), **D_OPS}),

    # ── le panneau Fiche ───────────────────────────────────────────────────────────────────────────────────
    S(F, 3919, '\r\n    <div class="dt-label">Réparer l\'assise<', '\r\n    <div class="dt-label">${dzT("etabli.et2_fiche.reparer_assise")}<',
      {"etabli.et2_fiche.reparer_assise": ("Réparer l'assise", "Fix placement")}),
    S(F, 3921, '<label>axe haut', '<label>${dzT("etabli.et2_fiche.axe_haut")}',
      {"etabli.et2_fiche.axe_haut": ("axe haut", "up axis")}),
    S(F, 3924, '<label>échelle <input', '<label>${dzT("etabli.et2_fiche.echelle")} <input',
      {"etabli.et2_fiche.echelle": ("échelle", "scale")}),
    S(F, 3925, '> recentrer sur l\'origine</label>', '> ${dzT("etabli.et2_fiche.recentrer")}</label>',
      {"etabli.et2_fiche.recentrer": ("recentrer sur l'origine", "recenter on the origin")}),
    S(F, 3926, '>Mettre en attente<', '>${dzT("etabli.et2_fiche.mettre_en_attente")}<',
      {"etabli.et2_fiche.mettre_en_attente": ("Mettre en attente", "Queue")}),
    S(F, 3927, '<p class="note">Le recentrage a besoin de la géométrie : sur un GLB\r\n'
      '      compressé il refuse, en le disant. L\'axe et l\'échelle passent quand\r\n'
      '      même.</p>',
      '<p class="note">${dzT("etabli.et2_fiche.note_recentrage")}</p>',
      {"etabli.et2_fiche.note_recentrage": (
          "Le recentrage a besoin de la géométrie : sur un GLB compressé il refuse, en le disant. L'axe et "
          "l'échelle passent quand même.",
          "Recentering needs the geometry: on a compressed GLB it refuses, and says so. The axis and the scale "
          "still go through.")}),
    S(F, 3930, '>Réparer le maillage<', '>${dzT("etabli.et2_fiche.reparer_maillage")}<',
      {"etabli.et2_fiche.reparer_maillage": ("Réparer le maillage", "Repair the mesh")}),
    S(F, 3932, '</div>\r\n    <button id="fReparerMaillage" title="Écrit aussitôt une version de plus : sommets confondus, doublons, triangles plats, normales — '
      'et les trous si la case est cochée"',
      '</div>\r\n    <button id="fReparerMaillage" title="${dzT("etabli.et2_fiche.titre_reparer")}"',
      {"etabli.et2_fiche.titre_reparer": (
          "Écrit aussitôt une version de plus : sommets confondus, doublons, triangles plats, normales — et les trous "
          "si la case est cochée",
          "Immediately writes one more version: coincident vertices, duplicates, flat triangles, normals — and holes "
          "if the box is ticked")}),
    S(F, 3933, '>Réparer en un clic<', '>${dzT("etabli.et2_fiche.reparer_un_clic")}<',
      {"etabli.et2_fiche.reparer_un_clic": ("Réparer en un clic", "Repair in one click")}),
    S(F, 3934, '<p class="note">Écrit AUSSITÔT une version de plus (les nœuds sont renumérotés) ; le\r\n'
      '      détail de ce qui a été fait s\'affiche dans la barre du bas, et la version d\'avant\r\n'
      '      reste sur le disque. « Trous bouchés » ajoute de la matière : décoché d\'office.</p>',
      '<p class="note">${dzT("etabli.et2_fiche.note_reparer")}</p>',
      {"etabli.et2_fiche.note_reparer": (
          "Écrit AUSSITÔT une version de plus (les nœuds sont renumérotés) ; le détail de ce qui a été fait "
          "s'affiche dans la barre du bas, et la version d'avant reste sur le disque. « Trous bouchés » ajoute de "
          "la matière : décoché d'office.",
          "Writes one more version RIGHT AWAY (the nodes are renumbered); the details of what was done show in the "
          "bottom bar, and the previous version stays on disk. “Filled holes” adds material: unticked by "
          "default.")}),
    S(F, 3937, '>Creuser<', '>${dzT("etabli.et2_fiche.creuser")}<',
      {"etabli.et2_fiche.creuser": ("Creuser", "Hollow")}),
    S(F, 3938, '<label>paroi (millimètres) <input', '<label>${dzT("etabli.et2_fiche.paroi")} <input',
      {"etabli.et2_fiche.paroi": ("paroi (millimètres)", "wall (millimeters)")}),
    S(F, 3939, 'title="L\'épaisseur de la paroi, en millimètres réels — exige une taille cible"',
      'title="${dzT("etabli.et2_fiche.titre_paroi")}"',
      {"etabli.et2_fiche.titre_paroi": ("L'épaisseur de la paroi, en millimètres réels — exige une taille cible",
                                        "The wall thickness, in real millimeters — requires a target size")}),
    S(F, 3940, 'title="Écrit aussitôt une version creusée : la peau doublée vers l\'intérieur, sur la sélection ou '
      'tout le modèle"',
      'title="${dzT("etabli.et2_fiche.titre_creuser")}"',
      {"etabli.et2_fiche.titre_creuser": (
          "Écrit aussitôt une version creusée : la peau doublée vers l'intérieur, sur la sélection ou tout le modèle",
          "Immediately writes a hollowed version: the skin doubled inward, on the selection or the whole model")}),
    S(F, 3940, '>Creuser<', '>${dzT("etabli.et2_fiche.creuser")}<', {}),
    S(F, 3941, '<p class="note">Double la peau vers l\'intérieur, à épaisseur constante. Exige une taille cible\r\n'
      '      (une paroi est une cote physique) et un maillage FERMÉ — sinon « Réparer le maillage », trous\r\n'
      '      cochés. Ce que la paroi ne peut pas tenir est compté et dit, avec l\'épaisseur qui tient.</p>',
      '<p class="note">${dzT("etabli.et2_fiche.note_creuser")}</p>',
      {"etabli.et2_fiche.note_creuser": (
          "Double la peau vers l'intérieur, à épaisseur constante. Exige une taille cible (une paroi est une cote "
          "physique) et un maillage FERMÉ — sinon « Réparer le maillage », trous cochés. Ce que la paroi ne peut pas "
          "tenir est compté et dit, avec l'épaisseur qui tient.",
          "Doubles the skin inward, at constant thickness. Requires a target size (a wall is a physical dimension) "
          "and a CLOSED mesh — otherwise “Repair the mesh”, holes ticked. What the wall cannot hold is counted and "
          "reported, with the thickness that holds.")}),
    S(F, 3944, '>Percer (drainage)<', '>${dzT("etabli.et2_fiche.percer")}<',
      {"etabli.et2_fiche.percer": ("Percer (drainage)", "Drill (drain hole)")}),
    S(F, 3945, '<label>trou ⌀ (millimètres) <input', '<label>${dzT("etabli.et2_fiche.trou")} <input',
      {"etabli.et2_fiche.trou": ("trou ⌀ (millimètres)", "hole ⌀ (millimeters)")}),
    S(F, 3946, 'title="Le diamètre du trou de drainage, en millimètres réels — exige une taille cible"',
      'title="${dzT("etabli.et2_fiche.titre_trou")}"',
      {"etabli.et2_fiche.titre_trou": ("Le diamètre du trou de drainage, en millimètres réels — exige une taille cible",
                                       "The drain hole diameter, in real millimeters — requires a target size")}),
    S(F, 3947, 'title="Arme le foret : clique ensuite la face à percer, le trou suit sa normale (Échap renonce)"',
      'title="${dzT("etabli.et2_fiche.titre_foret")}"',
      {"etabli.et2_fiche.titre_foret": (
          "Arme le foret : clique ensuite la face à percer, le trou suit sa normale (Échap renonce)",
          "Arms the drill: then click the face to drill, the hole follows its normal (Esc cancels)")}),
    S(F, 3947, '>Percer (clic sur la pièce)<', '>${dzT("etabli.et2_fiche.foret")}<',
      {"etabli.et2_fiche.foret": ("Percer (clic sur la pièce)", "Drill (click the part)")}),
    S(F, 3948, '<p class="note">Sur une pièce CREUSÉE : le foret traverse la paroi sous le clic (dehors puis dedans) et '
      'recoud le\r\n'
      '      tube entre les deux peaux — la paroi opposée n\'est pas touchée. Écrit aussitôt une version de plus. Une '
      'pièce\r\n'
      '      pleine, un rayon plus fin qu\'une facette ou un bord qui rase une arête sont refusés, en le disant.</p>',
      '<p class="note">${dzT("etabli.et2_fiche.note_foret")}</p>',
      {"etabli.et2_fiche.note_foret": (
          "Sur une pièce CREUSÉE : le foret traverse la paroi sous le clic (dehors puis dedans) et recoud le tube "
          "entre les deux peaux — la paroi opposée n'est pas touchée. Écrit aussitôt une version de plus. Une pièce "
          "pleine, un rayon plus fin qu'une facette ou un bord qui rase une arête sont refusés, en le disant.",
          "On a HOLLOWED part: the drill goes through the wall under the click (outside then inside) and stitches "
          "the tube between the two skins — the opposite wall is not touched. Immediately writes one more version. "
          "A solid part, a radius finer than a facet or a rim grazing an edge are refused, with the reason.")}),
    S(F, 3951, '>Décimer<', '>${dzT("etabli.et2_fiche.decimer")}<',
      {"etabli.et2_fiche.decimer": ("Décimer", "Decimate")}),
    S(F, 3952, '<label>cible <select', '<label>${dzT("etabli.et2_fiche.cible")} <select',
      {"etabli.et2_fiche.cible": ("cible", "target", "contexte")}),
    S(F, 3952, 'title="Le nombre de triangles visé ; les noms de pièces sont gardés"',
      'title="${dzT("etabli.et2_fiche.titre_decimer")}"',
      {"etabli.et2_fiche.titre_decimer": ("Le nombre de triangles visé ; les noms de pièces sont gardés",
                                          "The target triangle count; part names are kept")}),
    S(F, 3953, '>ultra — 100 000 triangles<', '>${dzT("etabli.et2_fiche.preset_ultra")}<',
      {"etabli.et2_fiche.preset_ultra": ("ultra — 100 000 triangles", "ultra — 100,000 triangles")}),
    S(F, 3954, '>élevé — 50 000<', '>${dzT("etabli.et2_fiche.preset_high")}<',
      {"etabli.et2_fiche.preset_high": ("élevé — 50 000", "high — 50,000")}),
    S(F, 3955, '>jeu — 10 000<', '>${dzT("etabli.et2_fiche.preset_game")}<',
      {"etabli.et2_fiche.preset_game": ("jeu — 10 000", "game — 10,000")}),
    S(F, 3956, '>détaillé — 5 000<', '>${dzT("etabli.et2_fiche.preset_detailed")}<',
      {"etabli.et2_fiche.preset_detailed": ("détaillé — 5 000", "detailed — 5,000")}),
    S(F, 3957, 'title="Écrit aussitôt une version décimée — elle entre dans la lignée, la version d\'avant reste sur le '
      'disque"',
      'title="${dzT("etabli.et2_fiche.titre_decimer_btn")}"',
      {"etabli.et2_fiche.titre_decimer_btn": (
          "Écrit aussitôt une version décimée — elle entre dans la lignée, la version d'avant reste sur le disque",
          "Immediately writes a decimated version — it joins the lineage, the previous version stays on disk")}),
    S(F, 3957, '>Décimer<', '>${dzT("etabli.et2_fiche.decimer")}<', {}),
    S(F, 3958, '<p class="note">La décimation écrit une VERSION de plus, au lieu du fichier « décimé » à\r\n'
      '      part que l\'Établi ne sait pas charger. Un modèle déjà sous la cible est refusé.</p>',
      '<p class="note">${dzT("etabli.et2_fiche.note_decimer")}</p>',
      {"etabli.et2_fiche.note_decimer": (
          "La décimation écrit une VERSION de plus, au lieu du fichier « décimé » à part que l'Établi ne sait pas "
          "charger. Un modèle déjà sous la cible est refusé.",
          "Decimation writes one more VERSION, instead of the separate “decimated” file the Workbench cannot load. "
          "A model already under the target is refused.")}),
    L(F, 3962, '"aucun modèle chargé — rien à réparer"', "etabli.et2_fiche.rien_a_reparer",
      "aucun modèle chargé — rien à réparer", "no model loaded — nothing to repair"),
    L(F, 3975, '"cochez au moins une action de réparation"', "etabli.et2_fiche.une_action",
      "cochez au moins une action de réparation", "tick at least one repair action"),
    L(F, 3981, '"paroi : un nombre de millimètres > 0"', "etabli.et2_fiche.paroi_invalide",
      "paroi : un nombre de millimètres > 0", "wall: a number of millimeters > 0"),
    L(F, 3985, '"pose une taille cible : une paroi en millimètres n\'a de sens qu\'avec une échelle"',
      "etabli.et2_fiche.paroi_sans_cible",
      "pose une taille cible : une paroi en millimètres n'a de sens qu'avec une échelle",
      "set a target size: a wall in millimeters only makes sense with a scale"),
    L(F, 3995, '"foret rangé"', "etabli.et2_foret.range", "foret rangé", "drill put away"),
    L(F, 3996, '"aucun modèle chargé — rien à percer"', "etabli.et2_foret.rien_a_percer",
      "aucun modèle chargé — rien à percer", "no model loaded — nothing to drill"),
    L(F, 3998, '"pose une taille cible : un trou de drainage en millimètres n\'a de sens qu\'avec une échelle"',
      "etabli.et2_foret.sans_cible",
      "pose une taille cible : un trou de drainage en millimètres n'a de sens qu'avec une échelle",
      "set a target size: a drain hole in millimeters only makes sense with a scale"),
    L(F, 4001, '"la plaque est une VUE : revenez à « Assemblé » pour percer"', "etabli.et2_foret.plaque_vue",
      "la plaque est une VUE : revenez à « Assemblé » pour percer",
      "the plate is a VIEW: go back to “Assembled” to drill"),
    L(F, 4004, '"foret armé : clique la face à percer — le trou suit sa normale (Échap renonce)"',
      "etabli.et2_foret.arme", "foret armé : clique la face à percer — le trou suit sa normale (Échap renonce)",
      "drill armed: click the face to drill — the hole follows its normal (Esc cancels)"),

    # ── le repère ──────────────────────────────────────────────────────────────────────────────────────────
    X(F, 4063, '"u. glTF"', "unité seule (uniteCourante, la seule source de l'unité)"),
    S(F, 4154, '`nœud ${o.userData.indexGltf}`', 'dzT("etabli.et2_repere.noeud_n", { n: o.userData.indexGltf })',
      {"etabli.et2_repere.noeud_n": ("nœud {n}", "node {n}")}),
    L(F, 4154, '"sans nom"', "etabli.et2_repere.sans_nom", "sans nom", "untitled"),
    S(F, 4167, '\r\n    <div class="dt-label">Repère · origine<', '\r\n    <div class="dt-label">${dzT("etabli.et2_repere.titre")}<',
      {"etabli.et2_repere.titre": ("Repère · origine", "Axes · origin")}),
    S(F, 4170, '<label>taille cible', '<label>${dzT("etabli.et2_repere.taille_cible")}',
      {"etabli.et2_repere.taille_cible": ("taille cible", "target size")}),
    S(F, 4175, '<p class="repere-note">Tout se lit en unités glTF tant qu\'aucune taille\r\n'
      '      cible n\'est posée : un GLB n\'en porte AUCUNE, et c\'est le serveur qui en\r\n'
      '      fabrique une pour écrire un STL — la plus grande dimension du modèle\r\n'
      '      devient la cible. Ce champ applique CETTE règle et rien d\'autre ; vide,\r\n'
      '      aucun chiffre en millimètres n\'est affiché.</p>',
      '<p class="repere-note">${dzT("etabli.et2_repere.note_unites")}</p>',
      {"etabli.et2_repere.note_unites": (
          "Tout se lit en unités glTF tant qu'aucune taille cible n'est posée : un GLB n'en porte AUCUNE, et c'est "
          "le serveur qui en fabrique une pour écrire un STL — la plus grande dimension du modèle devient la cible. "
          "Ce champ applique CETTE règle et rien d'autre ; vide, aucun chiffre en millimètres n'est affiché.",
          "Everything reads in glTF units until a target size is set: a GLB carries NONE, and the server makes one "
          "to write an STL — the model's largest dimension becomes the target. This field applies THAT rule and "
          "nothing else; empty, no millimeter figure is shown.")}),
    S(F, 4180, '<p class="repere-note">Ce sont des cotes, PAS des coordonnées de plateau :\r\n'
      '      l\'export STL recentre en X/Y et pose Z au sol, si bien qu\'une pièce lue\r\n'
      '      ici à −31,50 n\'arrivera pas à −31,50 dans le slicer. La cible, elle,\r\n'
      '      SURVIT au changement de modèle — c\'est ce qu\'on veut imprimer, pas une\r\n'
      '      propriété du maillage — et l\'échelle est refaite sur le maillage\r\n'
      '      affiché.</p>',
      '<p class="repere-note">${dzT("etabli.et2_repere.note_cotes")}</p>',
      {"etabli.et2_repere.note_cotes": (
          "Ce sont des cotes, PAS des coordonnées de plateau : l'export STL recentre en X/Y et pose Z au sol, si bien "
          "qu'une pièce lue ici à −31,50 n'arrivera pas à −31,50 dans le slicer. La cible, elle, SURVIT au "
          "changement de modèle — c'est ce qu'on veut imprimer, pas une propriété du maillage — et l'échelle est "
          "refaite sur le maillage affiché.",
          "These are dimensions, NOT bed coordinates: the STL export recenters in X/Y and puts Z on the floor, so a "
          "part read here at −31.50 will not land at −31.50 in the slicer. The target, however, SURVIVES a model "
          "change — it is what you want to print, not a property of the mesh — and the scale is redone on the "
          "displayed mesh.")}),
    S(F, 4224, '"taille cible invalide — un nombre de millimètres > 0, ou le "\r\n'
      '      + "champ vide pour rester en unités glTF"',
      'dzT("etabli.et2_repere.cible_invalide")',
      {"etabli.et2_repere.cible_invalide": (
          "taille cible invalide — un nombre de millimètres > 0, ou le champ vide pour rester en unités glTF",
          "invalid target size — a number of millimeters > 0, or an empty field to stay in glTF units")}),
    S(F, 4232, '"aucun modèle mesuré — une taille cible se pose sur la plus "\r\n'
      '      + "grande dimension d\'un maillage, il en faut un à l\'écran"',
      'dzT("etabli.et2_repere.aucun_mesure")',
      {"etabli.et2_repere.aucun_mesure": (
          "aucun modèle mesuré — une taille cible se pose sur la plus grande dimension d'un maillage, il en faut un "
          "à l'écran",
          "no measured model — a target size is set on a mesh's largest dimension, one must be on screen")}),
    S(F, 4313, '`pas ${PLQ.active ? "du plateau" : "de la grille"} <b>${esc(pas)}</b>`\r\n'
      '    + (enMillimetres()\r\n'
      '      ? ` · cible ${esc(REP.cibleMm)} ${esc(u)} sur la plus grande dimension`\r\n'
      '      : " · aucune taille cible, donc aucun millimètre déduit");',
      '(PLQ.active ? dzT("etabli.et2_repere.pas_plateau", { pas: `<b>${esc(pas)}</b>` }) '
      ': dzT("etabli.et2_repere.pas_grille", { pas: `<b>${esc(pas)}</b>` }))\r\n'
      '    + (enMillimetres()\r\n'
      '      ? dzT("etabli.et2_repere.cible_sur", { cible: esc(REP.cibleMm), unite: esc(u) })\r\n'
      '      : dzT("etabli.et2_repere.aucune_cible"));',
      {"etabli.et2_repere.pas_plateau": ("pas du plateau {pas}", "bed step {pas}"),
       "etabli.et2_repere.pas_grille": ("pas de la grille {pas}", "grid step {pas}"),
       "etabli.et2_repere.cible_sur": (" · cible {cible} {unite} sur la plus grande dimension",
                                       " · target {cible} {unite} on the largest dimension"),
       "etabli.et2_repere.aucune_cible": (" · aucune taille cible, donc aucun millimètre déduit",
                                          " · no target size, so no millimeters inferred")}),
    S(F, 4334, '>x · y · z depuis l\'origine, en ${esc(u)}<',
      '>${dzT("etabli.et2_repere.tete", { unite: esc(u) })}<',
      {"etabli.et2_repere.tete": ("x · y · z depuis l'origine, en {unite}", "x · y · z from the origin, in {unite}")}),
    S(F, 4342, '<div class="repere-vide">aucune sélection — le repère montre\r\n        l\'origine, ses trois axes et son pas<',
      '<div class="repere-vide">${dzT("etabli.et2_repere.vide")}<',
      {"etabli.et2_repere.vide": ("aucune sélection — le repère montre l'origine, ses trois axes et son pas",
                                  "no selection — the axes show the origin, its three axes and its step")}),
    S(F, 4346, '<div class="repere-plus">… et ${reste} autre(s) sélection(s)<', '<div class="repere-plus">${dzT("etabli.et2_repere.autres", { n: reste })}<',
      {"etabli.et2_repere.autres": ("… et {n} autre(s) sélection(s)", "… and {n} other selection(s)")}),
    S(F, 4348, '>${m.sansPosition} sélection(s) sans\r\n'
      '        position — un matériau n\'est pas un volume, un nœud sans géométrie\r\n'
      '        n\'a pas de boîte<',
      '>${dzT("etabli.et2_repere.sans_position", { n: m.sansPosition })}<',
      {"etabli.et2_repere.sans_position": (
          "{n} sélection(s) sans position — un matériau n'est pas un volume, un nœud sans géométrie n'a pas de boîte",
          "{n} selection(s) without a position — a material is not a volume, a node without geometry has no box")}),
    S(F, 4352, '>${tronquees} croix non tracée(s) — au-delà,\r\n'
      '        le repère 3D cesse d\'être lisible ; les chiffres, eux, restent<',
      '>${dzT("etabli.et2_repere.tronquees", { n: tronquees })}<',
      {"etabli.et2_repere.tronquees": (
          "{n} croix non tracée(s) — au-delà, le repère 3D cesse d'être lisible ; les chiffres, eux, restent",
          "{n} cross(es) not drawn — beyond that, the 3D axes stop being readable; the figures remain")}),
    S(F, 4356, '<div class="repere-plus">la plaque est une VUE : les chiffres sont\r\n'
      '        ceux du MODÈLE, étalement et rotation défaits, et le repère 3D ne\r\n'
      '        marque rien — sa croix tomberait à côté des pièces étalées.',
      '<div class="repere-plus">${dzT("etabli.et2_repere.plaque_vue")}',
      {"etabli.et2_repere.plaque_vue": (
          "la plaque est une VUE : les chiffres sont ceux du MODÈLE, étalement et rotation défaits, et le repère 3D "
          "ne marque rien — sa croix tomberait à côté des pièces étalées.",
          "the plate is a VIEW: the figures are those of the MODEL, layout and rotation undone, and the 3D axes mark "
          "nothing — their cross would land beside the laid-out parts.")}),
    L(F, 4359, '" † cette lecture-là n\'a pas pu être corrigée."', "etabli.et2_repere.non_corrigee",
      " † cette lecture-là n'a pas pu être corrigée.", " † this reading could not be corrected."),

    # ── l'amorçage ─────────────────────────────────────────────────────────────────────────────────────────
    S(F, 4543, '`chronologie illisible — ${e.message}`', 'dzT("etabli.et2_chrono.illisible", { msg: e.message })',
      {"etabli.et2_chrono.illisible": ("chronologie illisible — {msg}", "unreadable timeline — {msg}")}),

    # ── la page etabli/index.html (surcouche ; jamais modifiée) ───────────────────────────────────────────
    H("etabli.et2_page.titre", "Deepotus — Établi", "Deepotus — Workbench"),
    H("etabli.et2_page.vie", "La vie du modèle", "Model history"),
    H("etabli.et2_page.chargement", "chargement…", "loading…"),
    H("etabli.et2_page.clic_charger", "clic : charger ·", "click: load ·"),
    H("etabli.et2_page.alt_clic", "alt-clic", "alt-click"),
    H("etabli.et2_page.comparer", ": comparer", ": compare"),
    H("etabli.et2_page.titre_retour", "Revenir au graphe du 3D Studio", "Back to the 3D Studio graph"),
    H("etabli.et2_page.etabli", "Établi", "Workbench"),
    H("etabli.et2_page.titre_aide", "Le pas à pas et le lexique, sans quitter l'écran — et le chapitre 21 du guide",
      "The walkthrough and the glossary, without leaving the screen — and chapter 21 of the guide"),
    H("etabli.et2_page.aide", "Aide", "Help"),
    H("etabli.et2_page.titre_compare", "Fermer la comparaison", "Close the comparison"),
    H("etabli.et2_page.face", "Face", "Front"),
    H("etabli.et2_page.dessus", "Dessus", "Top"),
    H("etabli.et2_page.profil", "Profil", "Profile"),
    H("etabli.et2_page.titre_garder", "le côté a est celui que montre la flèche du plan",
      "side a is the one the plane's arrow points to"),
    H("etabli.et2_page.garder_deux", "garder les deux côtés", "keep both sides"),
    H("etabli.et2_page.garder_a", "garder le côté a (flèche)", "keep side a (arrow)"),
    H("etabli.et2_page.garder_b", "garder le côté b", "keep side b"),
    H("etabli.et2_page.titre_connecteur",
      "posé APRÈS la coupe, sur les deux moitiés que le couteau vient d'écrire (une version de plus)",
      "placed AFTER the cut, on the two halves the knife just wrote (one more version)"),
    H("etabli.et2_page.sans_connecteur", "sans connecteur", "no connector"),
    H("etabli.et2_connecteur.teton", "téton", "plug"),
    H("etabli.et2_connecteur.cheville", "cheville", "dowel"),
    H("etabli.et2_connecteur.aronde", "queue d'aronde", "dovetail"),
    H("etabli.et2_page.titre_couper", "Python coupe et écrit une version de plus — refusé tant que des modifications "
      "attendent", "Python cuts and writes one more version — refused while changes are pending"),
    H("etabli.et2_page.couper", "Couper", "Cut"),
    H(AUCUN, *D_AUCUN[AUCUN]),
    H("etabli.et2_page.parties", "Parties", "Parts"),
    H("etabli.et2_page.fiche", "Fiche", "Report"),
    H("etabli.et2_page.impression", "Impression 3D", "3D printing"),
    H("etabli.et2_page.titre_imprimer", "Exporte la version AFFICHÉE en STL + 3MF aux millimètres de la taille cible "
      "(dossier sous assets/print3d)",
      "Exports the DISPLAYED version as STL + 3MF at the target size in millimeters (folder under assets/print3d)"),
    H("etabli.et2_page.titre_slicer", "Ouvre le .3mf du dernier export dans le slicer (ElegooSlicer ou OrcaSlicer)",
      "Opens the .3mf of the latest export in the slicer (ElegooSlicer or OrcaSlicer)"),
    H("etabli.et2_page.slicer", "Ouvrir dans le slicer", "Open in the slicer"),
    H("etabli.et2_page.retour_blender", "Retour de Blender", "Back from Blender"),
    H("etabli.et2_page.titre_retour_blender",
      "Importe un GLB corrigé (dans Blender ou ailleurs) comme une version de PLUS du job affiché : rien n'est "
      "écrasé, et ce qui s'est perdu en route (squelette, clips, matériaux) est dit",
      "Imports a corrected GLB (from Blender or elsewhere) as one MORE version of the displayed job: nothing is "
      "overwritten, and what was lost on the way (skeleton, clips, materials) is reported"),
    H("etabli.et2_page.importer_version", "Importer une version corrigée…", "Import a corrected version…"),
]
