# -*- coding: utf-8 -*-
# scripts/icones/g1_saisie.py
"""Saisie du lot G1 (coque React) — glyphes, emojis, données et socle ; lue par scripts/icones/g1_generer.py.

Chaque édition : ids (docs/icones/suite-finale/implementation.json), ancre (UNIQUE dans le bundle de la BASE G0),
avant (unique dans l'ancre), après. Le générateur décide seul si le site vit dans une couche (source réécrite) ou
hors couche (paire du maillon patch_bundle_dzglyph.py).

Outils posés par le socle (S0 ci-dessous), visibles de tout le module, couches comprises :
  __dzGl(clé[, taille[, style]])      élément React d'une icône de la suite (taille par défaut : 1em) ;
  __dzGlT(clé, texte, glyphe[, t])    texte (souvent traduit) qui PORTAIT un glyphe : le glyphe devient l'icône,
                                      à sa place (devant ou derrière) ; glyphe absent (ou texte non chaîne) :
                                      le texte est rendu tel quel ;
  __dzGlS(texte, glyphe)              le texte sans le glyphe (pour un attribut, une option native) ;
  __dzGlH(clé[, taille])              balisage HTML de l'icône (code qui écrit du HTML / du DOM) ;
  __dzGlD(élément, clé, texte, glyphe[, t])  pose texte + icône dans un élément DOM (textContent sûr).
Les dictionnaires (frontend/shared/i18n/*.json) sont produits par les générateurs i18n : leurs textes gardent le
glyphe, retiré à l'affichage par __dzGlT / __dzGlS (jamais réécrits ici).
"""

EDITIONS = []
SATISFAITS = {}      # id -> pourquoi aucun site propre (servi par une autre édition, ou laissé tel quel)


def DEJA(ids, note):
    for i in (ids if isinstance(ids, list) else [ids]):
        SATISFAITS[i] = note


def E(ids, ancre, avant, apres):
    EDITIONS.append({"ids": ids if isinstance(ids, list) else [ids], "ancre": ancre, "avant": avant, "apres": apres})


def GL(ids, ancre, avant, cle, taille=None):
    """Un littéral glyphe (« avant », guillemets compris) devient l'icône."""
    t = "" if taille is None else f",{taille}"
    E(ids, ancre, avant, f'__dzGl("{cle}"{t})')


def KI(ids, ancre, avant, cle):
    """Un bouton K sans icône reçoit icon:"clé" (« avant » = le début de ses props, réécrit à l'identique)."""
    E(ids, ancre, avant, avant.replace("r.jsx(K,{", f'r.jsx(K,{{icon:"{cle}",', 1))


def T(ids, ancre, avant, cle, glyphe, taille=None):
    """Un texte traduit dzT(...) qui portait un glyphe : __dzGlT(clé, dzT(...), glyphe)."""
    t = "" if taille is None else f",{taille}"
    E(ids, ancre, avant, f'__dzGlT("{cle}",{avant},"{glyphe}"{t})')


# ═══ S0 — socle : la carte Sh apprend les clés de la suite ═════════════════════════════════════════════════════
SOCLE = (
    r'function __dzGlyphe(e){if(typeof e!=="string"||e.slice(0,3)!=="dz-"||typeof window==="undefined")return null;'
    r'var u=window.DZ_ICONS_IMAGES&&window.DZ_ICONS_IMAGES[e];if(u)return Sh[e]=r.jsx("image",{href:u,width:24,'
    r'height:24,preserveAspectRatio:"xMidYMid slice"});var s=window.DZ_ICONS&&window.DZ_ICONS[e],'
    r'm=typeof s==="string"&&/^<svg([^>]*)>([\s\S]*)<\/svg>$/.exec(s);if(!m)return null;'
    r'var p={dangerouslySetInnerHTML:{__html:m[2]}};m[1].replace(/([a-z][a-z-]*)="([^"]*)"/g,function(_,k,v){'
    r'if(k!=="xmlns"&&k!=="viewBox")p[k.replace(/-([a-z])/g,function(_,c){return c.toUpperCase()})]=v});'
    r'return Sh[e]=r.jsx("g",p)}'
    r'function __dzGl(e,t,n){return r.jsx(X,{name:e,size:t==null?"1em":t,style:n})}'
    r'function __dzGlT(e,s,g,t){var i=__dzGl(e,t);if(typeof s!=="string")return s;'
    r'var k=g?s.indexOf(g):-1;if(k<0)return s;var a=s.slice(0,k).replace(/\s+$/,""),'
    r'b=s.slice(k+g.length).replace(/^\s+/,"");return a&&b?[a," ",i," ",b]:a?[a," ",i]:b?[i," ",b]:i}'
    r'function __dzGlS(s,g){if(typeof s!=="string"||!g)return s;var k=s.indexOf(g);return k<0?s:'
    r'(s.slice(0,k)+s.slice(k+g.length)).replace(/^\s+|\s+$/g,"").replace(/\s{2,}/g," ")}'
    r'function __dzGlH(e,t){return typeof window!=="undefined"&&window.dzIcone?window.dzIcone(e,{taille:t||14}):""}'
    r'function __dzGlD(el,e,s,g,t){var k=typeof s==="string"&&g?s.indexOf(g):0,f=k>0&&k>=s.length-g.length;'
    r'el.textContent=__dzGlS(s,g)||"";var h=__dzGlH(e,t);if(h)el.insertAdjacentHTML(f?"beforeend":"afterbegin",'
    r'f?" "+h:h+" ");return el}'
)
E([], 'function X({name:e,size:t=16,style:n}){const o=Sh[e];',
  'function X({name:e,size:t=16,style:n}){const o=Sh[e];',
  SOCLE + 'function X({name:e,size:t=16,style:n}){const o=Sh[e]||__dzGlyphe(e);')


def W(ids, ancre, avant, cle, glyphe, taille=None):
    """Une expression texte (« avant ») qui peut porter le glyphe : __dzGlT(clé, (avant), glyphe)."""
    t = "" if taille is None else f",{taille}"
    E(ids, ancre, avant, f'__dzGlT("{cle}",({avant}),"{glyphe}"{t})')


# ═══ S1 — Coque ═════════════════════════════════════════════════════════════════════════════════════════════════
T("coque.accueil-premier-lancement.accueil-retour", 'children:dzT("coque.accueil.retour")}', 'dzT("coque.accueil.retour")',
  "dz-action-retour", "←")
GL("coque.panneau-file-des-rendus.file-vide", ',children:"🐙"}),dzT("coque.file.vide")', '"🐙"', "dz-etat-vide")
E("coque.panneau-file-des-rendus.file-vide-run", 'children:"▶ Run"}),dzT("coque.file.vide_ou")', '"▶ Run"',
  '__dzGlT("dz-action-lancer","▶ Run","▶")')
# sélecteur d'image de la Bibliothèque (HTML en chaîne)
E("coque.selecteur-d-image-de-la-bibliotheque-dzl.libpicker-fermer",
  '<button class="dzlp-x" title="Fermer (Échap)">✕</button>', '✕',
  '\'+__dzGlH("dz-action-fermer",14)+\'')
E("coque.selecteur-d-image-de-la-bibliotheque-dzl.libpicker-importer",
  'data-dzlp="fichier">⬆ Importer un fichier…</button>', '⬆ ', '\'+__dzGlH("dz-action-importer",14)+\' ')
E("coque.selecteur-d-image-de-la-bibliotheque-dzl.libpicker-figma",
  'FIGMA_TOKEN requis dans le .env">◇ Depuis Figma…</button>', '◇ ', '\'+__dzGlH("dz-reseau-figma",14)+\' ')
# accueil : clé masquée (•••) -> l'icône « caché »
E("coque.accueil-etape-fournisseurs.accueil-cle-masquee", 'children:o.set?"••••••••••••":dzT("coque.accueil.absente_env")',
  '"••••••••••••"', '__dzGl("dz-etat-cache",14)')
# accueil : pastille d'état de chaque clé (check|warn) — le cas « posée » reçoit dz-etat-succes
DEJA("coque.accueil-etape-fournisseurs.accueil-cle-etat", "littéral check -> dz-etat-succes posé par g1_saisie_cles")

# ═══ S2 — Quick ═════════════════════════════════════════════════════════════════════════════════════════════════
T("quick.barre-des-presets-haut-de-quick.preset-enregistrer", 'children:dzT("quick.preset.enregistrer")}',
  'dzT("quick.preset.enregistrer")', "dz-action-enregistrer", "💾")
GL("quick.barre-des-presets-haut-de-quick.preset-supprimer", 'onClick:dzQpDel,children:"🗑"}', '"🗑"', "dz-action-supprimer")
E("quick.galerie-de-mouvements-fenetre.galerie-fermer", 'x2.textContent="✕";', 'x2.textContent="✕";',
  'x2.innerHTML=__dzGlH("dz-action-fermer",14);x2.setAttribute("aria-label",dzT("quick.galerie.fermer"));')
E("quick.galerie-de-mouvements-fenetre.galerie-rerendre", 'rb.textContent=dzT("quick.galerie.rerendre",{img:img});',
  'rb.textContent=dzT("quick.galerie.rerendre",{img:img});',
  '__dzGlD(rb,"dz-action-recalculer",dzT("quick.galerie.rerendre",{img:img}),"↻",13);')
T("quick.panneau-seedance-image-de-depart.parcourir-depart", 'children:dzT("quick.source.parcourir")},"dzlps")',
  'dzT("quick.source.parcourir")', "dz-action-choisir-bibliotheque", "📚")
T("quick.panneau-seedance-image-de-fin.parcourir-fin", 'children:dzT("quick.source.parcourir")},"dzlpe")',
  'dzT("quick.source.parcourir")', "dz-action-choisir-bibliotheque", "📚")
T("quick.reglages-de-voix-dzvotuning.defauts", 'children:dzT("quick.reglage.defauts")}', 'dzT("quick.reglage.defauts")',
  "dz-action-reinitialiser", "↺")

# ═══ S3 — Studio (hors couches) ═════════════════════════════════════════════════════════════════════════════════
GL("studio.carte-de-noeud-apercu.apercu-du-noeud-animation-au-dessus-du-n",
   'style:{fontSize:22,lineHeight:1},children:"✦"}),r.jsx("div",{style:{fontSize:11,opacity:.8}', '"✦"', "dz-cat-animation")
E("studio.toast-d-erreur-fournisseur-dzprovider.toast-erreur", 'color:#fff">⚠️ \'+dzEsc(title)+\'</div>',
  '⚠️ \'+dzEsc(title)', '\'+__dzGlH("dz-etat-erreur",14)+\' \'+dzEsc(title)')
E("studio.toast-d-erreur-fournisseur-dzprovider.toast-lien", "+dzEsc(prov.name)+' account →</a>'",
  "' account →</a>'", "' account '+__dzGlH(\"dz-action-ouvrir-externe\",12)+'</a>'")
W("studio.inspecteur-noeud-news-pick.news-titre-image",
  'label:((it.image?"📷 ":"")+(it.title||"untitled").slice(0,48))+(it.source_name?" · "+it.source_name:"")}',
  '((it.image?"📷 ":"")+(it.title||"untitled").slice(0,48))+(it.source_name?" · "+it.source_name:"")',
  "dz-media-image", "📷")
E(["studio.inspecteur-noeud-animation.anim-type-texte"], 'children:el.type==="text"?"T":el.type==="sticker"?"★":"▦"}',
  '"T":', '__dzGl("dz-media-texte"):')
E(["studio.inspecteur-noeud-animation.anim-type-sticker"], 'children:el.type==="text"?"T":el.type==="sticker"?"★":"▦"}',
  '"★"', '__dzGl("dz-media-sticker")')
E(["studio.inspecteur-noeud-animation.anim-type-image"], 'children:el.type==="text"?"T":el.type==="sticker"?"★":"▦"}',
  '"▦"', '__dzGl("dz-media-image")')
GL("studio.inspecteur-noeud-animation.anim-el-monter",
   'cursor:"pointer"},children:"↑"}),r.jsx("button",{onClick:function(ev){ev.stopPropagation();moveEl(i,1)}', '"↑"', "dz-edit-monter")
GL("studio.inspecteur-noeud-animation.anim-el-descendre",
   'cursor:"pointer"},children:"↓"}),r.jsx("button",{onClick:function(ev){ev.stopPropagation();delEl(i)}', '"↓"', "dz-edit-descendre")
GL("studio.inspecteur-noeud-animation.anim-el-suppr", 'cursor:"pointer"},children:"×"})]},el.id||i)});', '"×"', "dz-action-supprimer")
GL("studio.inspecteur-noeud-animation-police.police-prec",
   'lineHeight:1},children:"▲"}),r.jsx("button",{onClick:function(){fontStep(1)}', '"▲"', "dz-action-element-precedent")
GL("studio.inspecteur-noeud-animation-police.police-suiv",
   'lineHeight:1},children:"▼"})]}),r.jsxs("div",{style:{flex:1,minWidth:0,overflow:"hidden"}', '"▼"', "dz-action-element-suivant")
E("studio.inspecteur-noeud-animation-favoris.fav-typo", 'children:"★ Typo"}', '"★ Typo"', '__dzGlT("dz-action-favori","★ Typo","★")')
E("studio.inspecteur-noeud-animation-favoris.fav-anim", 'children:"★ Anim"}', '"★ Anim"', '__dzGlT("dz-action-favori","★ Anim","★")')
T("studio.inspecteur-noeud-animation-favoris.fav-element", 'children:dzT("studio.animation.fav_element")}',
  'dzT("studio.animation.fav_element")', "dz-action-favori", "★")
T("studio.inspecteur-noeud-animation-favoris.favoris-titre", 'r.jsxs(ie,{label:dzT("studio.animation.favoris"),',
  'dzT("studio.animation.favoris")', "dz-action-favori", "★")
GL("studio.inspecteur-noeud-animation-favoris.fav-retirer", 'cursor:"pointer"},children:"×"})]},key)}', '"×"', "dz-action-favori")
T("studio.inspecteur-noeud-animation.anim-kf-prec", 'children:dzT("studio.animation.kf_prec")}', 'dzT("studio.animation.kf_prec")',
  "dz-media-precedent", "◀")
T("studio.inspecteur-noeud-animation.anim-kf-retirer", 'children:dzT("studio.animation.kf_retirer")}',
  'dzT("studio.animation.kf_retirer")', "dz-media-image-cle-retirer", "−")
T("studio.inspecteur-noeud-animation.anim-kf-suiv", 'children:dzT("studio.animation.kf_suiv")}', 'dzT("studio.animation.kf_suiv")',
  "dz-media-suivant", "▶")
T("studio.inspecteur-noeud-animation.anim-lire", 'children:dzT("studio.animation.lire")}', 'dzT("studio.animation.lire")',
  "dz-media-lecture", "▶")
T("studio.champ-texte-selecteur-d-emojis-dzemojipi.emoji-fermer",
  'children:open?dzT("studio.emoji.fermer"):dzT("studio.emoji.inserer")}', 'dzT("studio.emoji.fermer")', "dz-action-fermer", "✕")
T("studio.champ-texte-selecteur-d-emojis-dzemojipi.emoji-ouvrir",
  'children:open?dzT("studio.emoji.fermer"):dzT("studio.emoji.inserer")}', 'dzT("studio.emoji.inserer")', "dz-media-emoji", "😊")
GL("studio.champ-texte-selecteur-d-emojis-dzemojipi.emoji-perso-suppr", 'zIndex:2},children:"×"})]},it.name))}', '"×"',
   "dz-action-supprimer")
T("studio.inspecteur-champ-prompt-ia-dzpromptai.promptia-ok", 'setMsg(d.ai?dzT("studio.promptia.affine_via",{p:d.provider}):',
  'dzT("studio.promptia.affine_via",{p:d.provider})', "dz-etat-succes", "✓")
T("studio.inspecteur-champ-texte-ia-dztextai.texteia-ok", 'setMsg(d.ai?dzT("studio.texteia.affine_via",{p:d.provider}):',
  'dzT("studio.texteia.affine_via",{p:d.provider})', "dz-etat-succes", "✓")
T("studio.inspecteur-noeud-image.image-parcourir", 'children:dzT("studio.source.parcourir")},"dzlp")',
  'dzT("studio.source.parcourir")', "dz-action-choisir-bibliotheque", "📚")
T("studio.inspecteur-noeud-news-pick.news-a-image", 'children:dzT("studio.noeuds.news.a_image")}',
  'dzT("studio.noeuds.news.a_image")', "dz-etat-succes", "✓")
T("studio.inspecteur-noeud-upload.duree-maitresse", 'label:dzT("studio.source.duree_maitre")}',
  'dzT("studio.source.duree_maitre")', "dz-media-duree", "⏱")
W("studio.carte-de-noeud-pied.carte-maitre", '`${t.durationS}s${t.master?dzT("studio.carte.maitre"):""}`',
  '`${t.durationS}s${t.master?dzT("studio.carte.maitre"):""}`', "dz-media-duree", "⏱")
T("studio.editeur-de-sticker-dzstickereditor.sticker-ia", 'children:busy?"…":dzT("studio.sticker.ia")}',
  'dzT("studio.sticker.ia")', "dz-media-generer-image", "✨")
T("studio.editeur-de-sticker-dzstickereditor.sticker-importer", 'children:busy?"…":dzT("studio.sticker.importer_image")}',
  'dzT("studio.sticker.importer_image")', "dz-action-importer", "⬆")
GL("studio.apercu-de-composition-spatiale.compose-avatar", 'style:{fontSize:"7cqw"},children:"🗣"},"i")', '"🗣"', "dz-media-avatar")
DEJA("studio.bandeau-d-etat-du-canevas.etat-execution", "littéraux sparkle/check/warn du bandeau posés par g1_saisie_cles")
# aperçu Voiceover/MusicTrack/AudioMix/Loudness : la forme d'onde tirée au hasard devient l'icône « forme d'onde »
E("studio.carte-de-noeud-apercu.zone-d-apercu-des-noeuds-voiceover-music",
  '["Voiceover","MusicTrack","AudioMix","Loudness"].includes(n)?r.jsx("svg",{viewBox:"0 0 200 90",style:{width:"100%",height:"100%",background:"linear-gradient(135deg, #063020 0%, #02060d 100%)"},children:r.jsx("path",{stroke:"var(--green)",strokeWidth:"1.5",fill:"none",d:Ph()})})',
  'r.jsx("svg",{viewBox:"0 0 200 90",style:{width:"100%",height:"100%",background:"linear-gradient(135deg, #063020 0%, #02060d 100%)"},children:r.jsx("path",{stroke:"var(--green)",strokeWidth:"1.5",fill:"none",d:Ph()})})',
  'r.jsx("div",{style:{width:"100%",height:"100%",background:"linear-gradient(135deg, #063020 0%, #02060d 100%)",display:"flex",alignItems:"center",justifyContent:"center",color:"var(--green)"},children:__dzGl("dz-media-forme-onde",40)})')
# vignette d'un fichier audio (composant rr) : le tracé d'onde devient l'icône
E("coque.vignette-de-media-composant-rr.onde-audio",
  'e==="audio"&&r.jsx("svg",{viewBox:"0 0 60 30",style:{position:"absolute",inset:"20% 10%",color:s.audio},children:r.jsx("path",{stroke:"currentColor",strokeWidth:"1.5",fill:"none",d:"M0 15 Q5 5 10 15 T20 15 T30 15 T40 15 T50 15 T60 15"})})',
  'r.jsx("svg",{viewBox:"0 0 60 30",style:{position:"absolute",inset:"20% 10%",color:s.audio},children:r.jsx("path",{stroke:"currentColor",strokeWidth:"1.5",fill:"none",d:"M0 15 Q5 5 10 15 T20 15 T30 15 T40 15 T50 15 T60 15"})})',
  'r.jsx("div",{style:{position:"absolute",inset:"20% 10%",color:s.audio,display:"flex",alignItems:"center",justifyContent:"center"},children:__dzGl("dz-media-forme-onde",28)})')
DEJA("coque.ecran-de-demarrage-hm.anneaux-splash",
     "NON POSÉ : anneaux décoratifs animés du splash React autour du logo (composition du splash ; logo et splash gardés en image, choix utilisateur)")

# ═══ S4 — Quick (suite), Avatar, Voix ═══════════════════════════════════════════════════════════════════════════
# onglets de mode : la donnée porte la clé (rendue par r.jsx(X,{name:fe,size:12}))
E("quick.onglets-de-mode-en-tete-quick.onglet-seedance", '[["seedance","Seedance","sparkle",Za]', '"sparkle"',
  '"dz-media-generer-video"')
E("quick.onglets-de-mode-en-tete-quick.onglet-heygen", '["heygen","HeyGen","mic",_n]', '"mic"', '"dz-media-avatar"')
E("quick.onglets-de-mode-en-tete-quick.onglet-composition", '["comp","Composition","layers",Za||_n]', '"layers"',
  '"dz-cat-composition"')
E("quick.onglets-de-mode-en-tete-quick.onglet-voix-off", '["voice",dzT("quick.onglet.voix_off"),"wave",!1]', '"wave"',
  '"dz-media-voix"')
DEJA("quick.pied-de-quick.generer", "littéral play du gros bouton -> dz-action-generer (g1_saisie_cles)")
E(["quick.mode-avatar-castings-enregistres.save-enregistrer-le-casting",
   "avatar-heygen.quick-panneau-heygen-castings.casting-enregistrer"],
  'icon:"save",title:dzT("quick.casting.enregistrer")', '"save"', '"dz-action-enregistrer"')
DEJA("voix-voicebox.quick-onglet-voix-off.generer-voix", "littéral wave -> dz-media-generer-voix (g1_saisie_cles)")
DEJA("voix-voicebox.studio-noeud-voix-off-dzvoicenodepanel.noeud-generer-voix",
     "littéral wave -> dz-media-generer-voix (g1_saisie_cles)")
W("avatar-heygen.quick-panneau-heygen.avatar-photo",
  'label:`${B._kind==="talking_photo"?"📷 ":""}${B.name||B.avatar_id} ${B.gender?`· ${B.gender}`:""}`}',
  '`${B._kind==="talking_photo"?"📷 ":""}${B.name||B.avatar_id} ${B.gender?`· ${B.gender}`:""}`', "dz-media-image", "📷")
W("avatar-heygen.quick-panneau-heygen.voix-courante",
  'label:"✓ "+((sv.name||sv.voice_id)+"").trim()+(sv.language?" · "+sv.language:"")}',
  '"✓ "+((sv.name||sv.voice_id)+"").trim()+(sv.language?" · "+sv.language:"")', "dz-etat-option-active", "✓")
# messages de casting / avatar : un seul emplacement d'affichage (ce), testé par startsWith -> converti au RENDU
E(["avatar-heygen.quick-panneau-heygen-castings.casting-charge", "avatar-heygen.quick-panneau-heygen-photo-avatar.avatar-cree"],
  ':"var(--green)"},children:ce})', 'children:ce}', 'children:__dzGlT("dz-etat-succes",ce,"✓")}')
T("avatar-heygen.quick-panneau-heygen-castings.casting-sauve", 'Ee(d?(dzT("quick.casting.sauvegarde",{nom:nm,voix:((_v.name||"?")+"").trim()})):',
  'dzT("quick.casting.sauvegarde",{nom:nm,voix:((_v.name||"?")+"").trim()})', "dz-etat-enregistre", "✓")
E([], 'color:ce.startsWith(', 'ce.startsWith(', 'String(ce).startsWith(')
W("avatar-heygen.inspecteur-selecteur-d-avatar-dzavatarpi.avatar-fav-liste", 'label:(isFav(a)?"★ ":"")+a.avatar_name}',
  '(isFav(a)?"★ ":"")+a.avatar_name', "dz-action-favori", "★")
GL("avatar-heygen.inspecteur-selecteur-d-avatar-dzavatarpi.avatar-prec", 'cursor:"pointer"},children:"▲"}),img?', '"▲"',
   "dz-action-element-precedent")
GL("avatar-heygen.inspecteur-selecteur-d-avatar-dzavatarpi.avatar-fav-on", 'children:cur&&isFav(cur)?"★":"☆"}', '"★"', "dz-action-favori")
GL("avatar-heygen.inspecteur-selecteur-d-avatar-dzavatarpi.avatar-fav-off", 'children:cur&&isFav(cur)?"★":"☆"}', '"☆"', "dz-action-favori")
GL("avatar-heygen.inspecteur-selecteur-d-avatar-dzavatarpi.avatar-suiv", 'cursor:"pointer"},children:"▼"})]}),r.jsx(O,{label:"Avatar"',
   '"▼"', "dz-action-element-suivant")
GL("voix-voicebox.quick-onglet-voix-off-dzvoicepicker.voix-stop", 'children:vpl===vk?"■":"▶"}', '"■"', "dz-media-arret")
GL("voix-voicebox.quick-onglet-voix-off-dzvoicepicker.voix-ecouter", 'children:vpl===vk?"■":"▶"}', '"▶"', "dz-media-lecture")
GL("voix-voicebox.quick-onglet-voix-off-dzvoicepicker.voix-recharger", 'lineHeight:"1"},children:"↻"})]}),r.jsxs("div",{className:"scroll","data-dzvoicelist"',
   '"↻"', "dz-action-actualiser")
GL("voix-voicebox.quick-onglet-voix-off-castings.casting-voix-suppr", '"data-dzcastdel":"1",onClick:delCast,children:"✕"}', '"✕"',
   "dz-action-supprimer")
GL("voix-voicebox.studio-noeud-voix-off-dzvoicenodepanel.noeud-casting-suppr", '"data-dzvncastdel":"1",onClick:delCast,children:"✕"}',
   '"✕"', "dz-action-supprimer")
T("voix-voicebox.quick-onglet-voix-off-castings.casting-voix-sauver", 'children:dzT("quick.voix.casting_sauver")}',
  'dzT("quick.voix.casting_sauver")', "dz-action-enregistrer", "★")
T("voix-voicebox.studio-noeud-voix-off-dzvoicenodepanel.noeud-casting-sauver", 'children:dzT("studio.voix.sauver")}',
  'dzT("studio.voix.sauver")', "dz-action-enregistrer", "★")

# ═══ S5 — Templates ═════════════════════════════════════════════════════════════════════════════════════════════
GL("templates.liste-des-templates-gauche.integre", 'children:"🔒"}),f.name]}', '"🔒"', "dz-etat-verrouille")
GL("templates.editeur-spatial-toile.region-image", 'style:{fontSize:"11cqw"},children:"🖼"},"g")', '"🖼"', "dz-media-image")
GL("templates.editeur-spatial-toile.region-audio", 'style:{fontSize:"11cqw"},children:"🎵"},"g")', '"🎵"', "dz-media-audio")
GL("templates.editeur-spatial-toile.region-sticker", 'style:{fontSize:"14cqw"},children:"🐙"},"g")', '"🐙"', "dz-media-sticker")
GL("templates.editeur-spatial-toile.region-video", 'opacity:.85},children:"🎬"},"g")', '"🎬"', "dz-media-video")
# barre « Ajouter » : la donnée porte [type, libellé, clé, glyphe] ; le rendu pose l'icône
E("templates.editeur-spatial-barre-ajouter.ajout-live", '["live","● LIVE"]', '["live","● LIVE"]',
  '["live","● LIVE","dz-media-badge-direct","●"]')
E("templates.editeur-spatial-barre-ajouter.ajout-prix", '["price",dzT("templates.region.prix")]',
  '["price",dzT("templates.region.prix")]', '["price",dzT("templates.region.prix"),"dz-media-badge-prix","$"]')
E("templates.editeur-spatial-barre-ajouter.ajout-sticker", '["sticker","🐙 Sticker"]', '["sticker","🐙 Sticker"]',
  '["sticker","🐙 Sticker","dz-media-sticker","🐙"]')
E([], 'cursor:"pointer"},children:"+ "+z[1]},z[0])', 'children:"+ "+z[1]}',
  'children:z[2]?["+ "].concat(__dzGlT(z[2],z[1],z[3])):"+ "+z[1]}')
T("templates.inspecteur-de-region.region-supprimer", 'children:dzT("templates.inspecteur.supprimer")}',
  'dzT("templates.inspecteur.supprimer")', "dz-action-supprimer", "🗑")
T("templates.menu-d-un-template.menu-supprimer", 'children:dzT("templates.menu.supprimer")}', 'dzT("templates.menu.supprimer")',
  "dz-action-supprimer", "🗑")
T("templates.menu-d-un-template.menu-verrouille", 'children:dzT("templates.menu.verrouille")}', 'dzT("templates.menu.verrouille")',
  "dz-etat-verrouille", "🔒")
E("templates.pied-de-l-editeur.enregistre", ':"var(--green)"},children:y})', 'children:y}',
  'children:__dzGlT("dz-etat-enregistre",y,"✓")}')

# ═══ S6 — News ══════════════════════════════════════════════════════════════════════════════════════════════════
W("news.liste-des-articles.article-en-tete", 'children:(i.en_tete?"★ ":"")+i.score+"/100"}', '(i.en_tete?"★ ":"")+i.score+"/100"',
  "dz-etat-meilleur", "★")
E("news.fenetre-chaine-du-jour.chaine-en-tete",
  r'pa.textContent=dzT("news.chaine.articles_liste")+(j.articles||[]).map(function(a){return(a.en_tete?"★ ":"")+',
  r'pa.textContent=dzT("news.chaine.articles_liste")+(j.articles||[]).map(function(a){return(a.en_tete?"★ ":"")+',
  r'pa.textContent=dzT("news.chaine.articles_liste");(j.articles||[]).forEach(function(a,i){if(i)pa.appendChild(document.createTextNode("\n"));if(a.en_tete)pa.insertAdjacentHTML("beforeend",__dzGlH("dz-etat-meilleur",12)+" ");pa.appendChild(document.createTextNode(""+')
E([], r'dzT("news.chaine.deja_couvert"):"")}).join("\n");zone.appendChild(pa);', r':"")}).join("\n");zone.appendChild(pa);',
  r':"")))});zone.appendChild(pa);')

# ═══ S7 — Scheduler ═════════════════════════════════════════════════════════════════════════════════════════════
# flèches Précédent / Suivant : la clé finale porte son sens, la rotation du caret disparaît
E([], 'name:"caret",iconSize:12,style:{transform:"rotate(90deg)"},title:dzT("scheduler.calendrier.precedent")',
  ',style:{transform:"rotate(90deg)"}', '')
E([], 'name:"caret",iconSize:12,style:{transform:"rotate(-90deg)"},title:dzT("scheduler.calendrier.suivant")',
  ',style:{transform:"rotate(-90deg)"}', '')
E(["scheduler.inspecteur-de-post-pied.post-reprendre",
   "scheduler.editeur-de-post-pied-post-confie-a-un-telephone.undo-post-repris"],
  'icon:"undo",className:"dz-sched-reprendre"', '"undo"', '"dz-action-transferer-pc"')
W("scheduler.inspecteur-de-post-source.source-rendu",
  'label:`▶ ${j.title||j.provider||"render"} · ${(j.job_id||"").slice(0,6)}`}',
  '`▶ ${j.title||j.provider||"render"} · ${(j.job_id||"").slice(0,6)}`', "dz-media-video", "▶")
W("scheduler.inspecteur-de-post-source.source-image", 'label:"🖼 "+z}', '"🖼 "+z', "dz-media-image", "🖼")
W("scheduler.inspecteur-de-post-plan.plan-news", 'label:"📰 "+(v.title||"news").slice(0,28)}',
  '"📰 "+(v.title||"news").slice(0,28)', "dz-media-article", "📰")
T("scheduler.inspecteur-de-post-plan.plan-generer-image", '{value:"__gen__",label:dzT("scheduler.plan.generer_image")}',
  'dzT("scheduler.plan.generer_image")', "dz-media-generer-image", "✨")
# menus construits par __dzSendMenu : l'entrée porte ic (clé) et g (glyphe retiré du libellé)
E([], 'items.forEach(function(it){var b=document.createElement("button");b.textContent=it.lbl;',
  'b.textContent=it.lbl;', 'if(it.ic)__dzGlD(b,it.ic,it.lbl,it.g,14);else b.textContent=it.lbl;')
E("scheduler.menu-campagne.campagne-brief", '{lbl:dzT("scheduler.campagne.brief"),fn:__dzSchedBrief}',
  '{lbl:dzT("scheduler.campagne.brief")', '{ic:"dz-action-modifier",g:"✎",lbl:dzT("scheduler.campagne.brief")')
E("scheduler.menu-campagne.campagne-series", '{lbl:dzT("scheduler.campagne.series"),fn:__dzSchedSeries}',
  '{lbl:dzT("scheduler.campagne.series")', '{ic:"dz-action-recurrence",g:"↻",lbl:dzT("scheduler.campagne.series")')
E("scheduler.menu-campagne.campagne-recyclage", '{lbl:dzT("scheduler.campagne.recyclage"),fn:__dzSchedRecycler}',
  '{lbl:dzT("scheduler.campagne.recyclage")', '{ic:"dz-action-recycler",g:"♻",lbl:dzT("scheduler.campagne.recyclage")')

# ═══ S8 — Épisodes ══════════════════════════════════════════════════════════════════════════════════════════════
GL("episodes.carte-d-episode-bloc-brief-dzbrief.brief-deplie", 'children:["Brief ",o?"▾":"▸"]}', '"▾"', "dz-action-deplier")
E("episodes.carte-d-episode-bloc-brief-dzbrief.brief-replie", 'children:["Brief ",o?"▾":"▸"]}', '"▸"',
  '__dzGl("dz-action-deplier","1em",{transform:"rotate(-90deg)"})')
GL("episodes.etape-scenes-carte-de-scene.scene-monter", 'sbtn("↑",function(){moveScene(i,-1)}', '"↑"', "dz-edit-monter")
GL("episodes.etape-scenes-carte-de-scene.scene-descendre", 'sbtn("↓",function(){moveScene(i,1)}', '"↓"', "dz-edit-descendre")
GL("episodes.etape-scenes-carte-de-scene.scene-supprimer", 'sbtn("✕",function(){rmScene(i)}', '"✕"', "dz-action-supprimer")
W("episodes.barre-des-episodes-dzepbar.barre-modifie", 'children:(dirty&&has?"● ":"")+dzT("episodes.barre.enregistrer")}',
  '(dirty&&has?"● ":"")+dzT("episodes.barre.enregistrer")', "dz-etat-modifie", "●")
T("episodes.barre-des-episodes-dzepbar.barre-ouvrir", 'children:dzT("episodes.barre.ouvrir")}', 'dzT("episodes.barre.ouvrir")',
  "dz-action-deplier", "▾")
GL("episodes.barre-des-episodes-liste-deroulante.liste-supprimer", 'supprimer(e.id,e.title)},children:"✕"})', '"✕"',
   "dz-action-supprimer")
T("episodes.chapitres-choix-du-mode-2-cartes.mode-atelier", 'dzT("episodes.chapitres.atelier_entrer"))',
  'dzT("episodes.chapitres.atelier_entrer")', "dz-nav-atelier", "→")
T("episodes.chapitres-choix-du-mode-2-cartes.mode-origine", 'dzT("episodes.chapitres.origine_ouvrir"))',
  'dzT("episodes.chapitres.origine_ouvrir")', "dz-nav-episodes", "→")
T("episodes.chapitres-en-tete-d-un-mode.changer-mode", 'children:dzT("episodes.chapitres.retour")}',
  'dzT("episodes.chapitres.retour")', "dz-action-retour", "←")
T("episodes.etape-narration.narration-ok", 'children:[dzT("episodes.narration.enregistree",{kb:res.kb})]',
  'dzT("episodes.narration.enregistree",{kb:res.kb})', "dz-etat-enregistre", "✓")

# ═══ S9 — Game Assets (studio 3D, hub) ══════════════════════════════════════════════════════════════════════════
E(["game-assets.assets-2d.boutons-sans-icone", "game-assets.hub-game-assets-dzgameassetshub.hub-guide"],
  ',children:"Guide ↗"})},"g")', '"Guide ↗"', '__dzGlT("dz-nav-guide","Guide ↗","↗")')
E("game-assets.hub-game-assets-dzgameassetshub.hub-guide-off", ',children:"Guide ↗"},"g")]', '"Guide ↗"',
  '__dzGlT("dz-nav-guide","Guide ↗","↗")')
E("game-assets.3d-studio-panneau-lod-dzlod.lod", 'children:busy?"Chaîne…":"⛰ LOD"}', '"⛰ LOD"', '__dzGlT("dz-lab3d-lod","⛰ LOD","⛰")')
E("game-assets.3d-studio-panneau-lod-dzlod.lod-dl", 'children:"↓ Archive LOD"}', '"↓ Archive LOD"',
  '__dzGlT("dz-action-telecharger","↓ Archive LOD","↓")')
E("game-assets.3d-studio-panneau-optimiser-dzoptimize.optimiser", 'children:busy?"Optimisation…":"⚙ Optimiser"}', '"⚙ Optimiser"',
  '__dzGlT("dz-lab3d-optimiser","⚙ Optimiser","⚙")')
E("game-assets.3d-studio-panneau-optimiser-dzoptimize.opt-simple", 'children:cmp?"▣ Simple":"⇆ Comparer"}', '"▣ Simple"',
  '__dzGlT("dz-action-comparer","▣ Simple","▣")')
E("game-assets.3d-studio-panneau-optimiser-dzoptimize.opt-comparer", 'children:cmp?"▣ Simple":"⇆ Comparer"}', '"⇆ Comparer"',
  '__dzGlT("dz-action-comparer","⇆ Comparer","⇆")')
E("game-assets.3d-studio-panneau-optimiser-dzoptimize.opt-dl", 'children:"↓ GLB optimisé"}', '"↓ GLB optimisé"',
  '__dzGlT("dz-action-telecharger","↓ GLB optimisé","↓")')
E("game-assets.3d-studio-panneau-textures-dztex.tex-export", 'children:busy?"Export…":"↓ Textures"}', '"↓ Textures"',
  '__dzGlT("dz-action-exporter","↓ Textures","↓")')
GL("game-assets.3d-studio-carte-d-un-rendu-3d.renommer",
   'children:"✎"}),r.jsx("button",{onClick:async function(){if(await window.__dzDialogue.confirmer("Supp', '"✎"', "dz-action-renommer")
GL("game-assets.3d-studio-carte-d-un-rendu-3d.supprimer", 'color:"var(--red)"},children:"🗑"})]}),', '"🗑"', "dz-action-supprimer")
E("game-assets.3d-studio-carte-d-un-rendu-3d.poster", 'children:rot[sh]?"▣ Poster":"▶ Rotate"}', '"▣ Poster"',
  '__dzGlT("dz-media-image","▣ Poster","▣")')
E("game-assets.3d-studio-carte-d-un-rendu-3d.rotate", 'children:rot[sh]?"▣ Poster":"▶ Rotate"}', '"▶ Rotate"',
  '__dzGlT("dz-lab3d-rotation","▶ Rotate","▶")')
E("game-assets.3d-studio-carte-d-un-rendu-3d.vers-impression", 'children:"→ Impression 3D"}', '"→ Impression 3D"',
  '__dzGlT("dz-lab3d-impression-3d","→ Impression 3D","→")')
E("game-assets.3d-studio-carte-d-un-rendu-3d.dl-format", 'children:"↓ "+fm.toUpperCase()}', '"↓ "+fm.toUpperCase()',
  '__dzGlT("dz-action-exporter","↓ "+fm.toUpperCase(),"↓")')
GL("game-assets.3d-studio-vues-generees-planches.dl-shot", 'textDecoration:"none",color:"var(--cyan)"},children:"↓"})', '"↓"',
   "dz-action-telecharger")
GL("game-assets.3d-studio-vues-generees-planches.shot-biblio", 'children:"★"})]})]},i)})})]}):null', '"★"',
   "dz-action-ajouter-bibliotheque")
E(["game-assets.3d-studio-graphe-de-progression-pipeline.pipeline-encours",
   "game-assets.3d-studio-graphe-de-progression-pipeline.pipeline-fait"],
  'children:n.st==="run"?"⏳ "+n.label:n.st==="done"?"✓ "+n.label:n.label}',
  'n.st==="run"?"⏳ "+n.label:n.st==="done"?"✓ "+n.label:n.label',
  'n.st==="run"?__dzGlT("dz-etat-attente","⏳ "+n.label,"⏳"):n.st==="done"?__dzGlT("dz-etat-succes","✓ "+n.label,"✓"):n.label')
GL("game-assets.3d-studio-graphe-de-progression-pipeline.pipeline-dl", 'color:"var(--cyan)",textDecoration:"none"},children:"↓"})',
   '"↓"', "dz-action-telecharger")
GL("game-assets.3d-studio-graphe-de-progression-pipeline.pipeline-biblio", 'children:"★"})]});', '"★"',
   "dz-action-ajouter-bibliotheque")
GL("game-assets.3d-studio-graphe-de-progression-pipeline.pipeline-poster", 'children:rot[sh]?"▣":"▶"}', '"▣"', "dz-media-image")
GL("game-assets.3d-studio-graphe-de-progression-pipeline.pipeline-rotate", 'children:rot[sh]?"▣":"▶"}', '"▶"', "dz-lab3d-rotation")
E("game-assets.3d-studio-vue-de-suivi-d-un-asset-dzgame.3d-retour", 'children:"← New asset"}', '"← New asset"',
  '__dzGlT("dz-action-retour","← New asset","←")')

# ═══ S10 — Bibliothèque (hors couches) ══════════════════════════════════════════════════════════════════════════
DEJA("bibliotheque.fiche-detail-d-un-element-modale.fiche-type", "littéraux film/image de l'en-tête de fiche (g1_saisie_cles)")
T("bibliotheque.fiche-detail-actions.fiche-favori-on", 'children:__dzFavHas(m.jobId)?dzT("biblio.detail.favori_oui"):dzT("biblio.detail.favori_non")}',
  'dzT("biblio.detail.favori_oui")', "dz-action-favori", "★")
T("bibliotheque.fiche-detail-actions.fiche-favori-off", 'children:__dzFavHas(m.jobId)?dzT("biblio.detail.favori_oui"):dzT("biblio.detail.favori_non")}',
  'dzT("biblio.detail.favori_non")', "dz-action-favori", "☆")
for _a in ('objectFit:"cover",display:"block"}}),r.jsx("div",{style:{position:"absolute",bottom:4,right:4,padding:"2px 5px",fontSize:9,fontWeight:600,fontFamily:"var(--f-mono)",color:"var(--cyan)",background:"#02060daa",borderRadius:3},children:dzT("biblio.vue.survol")}',
           'objectFit:"contain",display:"block"}}),r.jsx("div",{style:{position:"absolute",bottom:4,right:4,padding:"2px 5px",fontSize:9,fontWeight:600,fontFamily:"var(--f-mono)",color:"var(--cyan)",background:"#02060daa",borderRadius:3},children:dzT("biblio.vue.survol")}'):
    T("bibliotheque.grille-des-rendus-vignette.vignette-survol", _a, 'dzT("biblio.vue.survol")', "dz-media-lecture", "▶")
KI("bibliotheque.fiche-detail-actions.fiche-envoyer", 'r.jsx(K,{variant:"ghost",size:"sm",onClick:()=>__dzSendTo(m,function(){y(null)})',
   'r.jsx(K,{variant:"ghost",size:"sm",onClick:()=>__dzSendTo(', "dz-action-envoyer-vers")
KI("bibliotheque.fiche-detail-actions.fiche-renommer",
   'r.jsx(K,{variant:"ghost",size:"sm",onClick:async()=>{var nn=await window.__dzDialogue.saisir(dzT("biblio.detail.renommer_image")',
   'r.jsx(K,{variant:"ghost",size:"sm",onClick:async()=>{var nn=await window.__dzDialogue.saisir(dzT("biblio.detail.renommer_image")',
   "dz-action-renommer")
KI("bibliotheque.fiche-detail-actions.fiche-renommer",
   'r.jsx(K,{variant:"ghost",size:"sm",onClick:async()=>{var nn=await window.__dzDialogue.saisir(dzT("biblio.detail.renommer_asset")',
   'r.jsx(K,{variant:"ghost",size:"sm",onClick:async()=>{var nn=await window.__dzDialogue.saisir(dzT("biblio.detail.renommer_asset")',
   "dz-action-renommer")
E("bibliotheque.fiche-detail-actions.fiche-spritelab-rendu", ',children:"→ Sprite Lab"}),m.kind==="image"', '"→ Sprite Lab"',
  '__dzGlT("dz-cat-sprites","→ Sprite Lab","→")')
E("bibliotheque.fiche-detail-actions.fiche-spritelab-image", ',children:"→ Sprite Lab"}),m.jobId', '"→ Sprite Lab"',
  '__dzGlT("dz-cat-sprites","→ Sprite Lab","→")')
for _id, _k, _c, _g in [
        ("envoyer-cardforge-copier-img", 'biblio.envoyer.cible.cardforge', "dz-cat-cartes", "🃏"),
        ("envoyer-chapitre-atelier-i", 'biblio.envoyer.cible.bible', "dz-nav-atelier", "📖"),
        ("envoyer-copier-la-sheet-dans-l", 'biblio.envoyer.cible.sheet_images', "dz-action-envoyer-vers", "🖼"),
        ("envoyer-impression-3d-export", 'biblio.envoyer.cible.impression3d', "dz-lab3d-impression-3d", "🖨"),
        ("envoyer-montage-clip-video", 'biblio.envoyer.cible.montage_clip', "dz-nav-montage", "🎞"),
        ("envoyer-montage-overlay-a-la", 'biblio.envoyer.cible.montage_overlay', "dz-nav-montage", "🎞"),
        ("envoyer-photolab-retoucher-l", 'photolab.cible.photolab', "dz-nav-photolab", "📷"),
        ("envoyer-projet-de-la-bibliothe", 'biblio.envoyer.cible.projet', "dz-action-ranger", "📁"),
        ("envoyer-prolonger-le-clip-7", 'biblio.envoyer.cible.prolonger', "dz-media-generer-video", "⚡"),
        ("envoyer-quick-image-de-depar", 'biblio.envoyer.cible.quick_image', "dz-nav-quick", "⚡"),
        ("envoyer-scheduler-brouillon", 'biblio.envoyer.cible.scheduler', "dz-nav-scheduler", "📅"),
        ("envoyer-sprite-lab-source", 'biblio.envoyer.cible.spritelab', "dz-cat-sprites", "🎮"),
        ("envoyer-studio-noeud-image", 'biblio.envoyer.cible.studio_image', "dz-nav-studio", "🎬"),
        ("envoyer-template-studio-fo", 'biblio.envoyer.cible.template', "dz-nav-templates", "🧩"),
        ("envoyer-tile-lab-source-de-l", 'photolab.cible.tilelab', "dz-cat-tuiles", "🧱"),
        ("envoyer-vectorlab-nouveau-do", 'photolab.cible.vectorlab', "dz-nav-vectorlab", "✒")]:
    _pref = {"biblio.envoyer.cible.scheduler": ['__dzSendNav("assets3d",{subtab:"tiles"})}});items.push(',
                                                'label:nom})}});items.push('],
             "biblio.envoyer.cible.spritelab": ['.then(done)}}});items.push(', '__dzSendNav("montage")}});items.push(']}
    for _p in _pref.get(_k, [""]):
        E("bibliotheque.menu-envoyer-vers-dzsendto." + _id, _p + '{lbl:dzT("%s"),fn:' % _k, '{lbl:dzT("%s")' % _k,
          '{ic:"%s",g:"%s",lbl:dzT("%s")' % (_c, _g, _k))

# ═══ S11 — Réglages, dépenses, mise à jour ══════════════════════════════════════════════════════════════════════
DEJA("reglages.apparence.apparence-halo", "l'emoji 🐙 du texte d'aide est retiré du dictionnaire (saisie i18n L1 + "
     "réassemblage) : rien à poser dans le bundle")
T("reglages.assistant-persona-fenetre.persona-retour", 'children:dzT("reglages.personas.retour")}',
  'dzT("reglages.personas.retour")', "dz-action-retour", "←")
E("reglages.pack-de-sous-titres.pack-enregistre", 'children:[" · ",i]}', 'children:[" · ",i]}',
  'children:[" · ",__dzGlT("dz-etat-enregistre",i,"✓")]}')
T("reglages.tarifs-et-budget.tarifs-enregistre", 'children:dzT("reglages.tarifs.enregistre")}', 'dzT("reglages.tarifs.enregistre")',
  "dz-etat-enregistre", "✓")
E("reglages.tarifs-et-budget.tarifs-enregistrer",
  'children:saving?dzT("reglages.tarifs.enregistrement"):dzT("reglages.tarifs.enregistrer")}', ':dzT("reglages.tarifs.enregistrer")}',
  ':[__dzGl("dz-action-enregistrer")," ",dzT("reglages.tarifs.enregistrer")]}')
KI("reglages.cles-d-api-test-dztestcle.cle-tester", "r.jsx(K,{variant:'ghost',size:'sm',title:dzT(\"reglages.cles.tester_titre\")",
   "r.jsx(K,{variant:'ghost',size:'sm',title:dzT(\"reglages.cles.tester_titre\")", "dz-action-tester")
KI("mise-a-jour.reglages-diagnostic-dzmaj.maj-verifier", "r.jsx(K,{variant:'ghost',size:'sm',onClick:revoir",
   "r.jsx(K,{variant:'ghost',size:'sm',onClick:revoir", "dz-action-actualiser")
E("depenses-plafonds.reglages-tarifs-et-budget-plafonds-dzpla.plafond-atteint",
  'children:dzT("reglages.plafonds.seuil_atteint")}', 'dzT("reglages.plafonds.seuil_atteint")',
  '[__dzGl("dz-etat-plafond")," ",dzT("reglages.plafonds.seuil_atteint")]')
DEJA("reglages.coffre-dzcoffre.coffre", "littéraux check des boutons Poser / Ouvrir le coffre -> dz-media-coffre (g1_saisie_cles)")
DEJA("reglages.appareils-dzappair.appareils", "littéral plus du bouton Appairer -> dz-action-appairer (g1_saisie_cles)")
DEJA("depenses-plafonds.infobulle-du-compteur-de-depenses-en-tet.minorant",
     "NON POSÉ : le ⚠ vit dans le texte d'une infobulle native (attribut title) — aucune icône possible ; texte gardé")

# ═══ S12 — Game Assets (catégories), marque, données ═══════════════════════════════════════════════════════════
E(["game-assets.assets-2d.cards", "game-assets.assets-2d.pixel", "game-assets.assets-2d.sprites", "game-assets.assets-2d.tiles",
   "game-assets.barre-categories.3d", "game-assets.barre-categories.a2d", "game-assets.barre-categories.cards",
   "game-assets.barre-categories.materials", "game-assets.barre-categories.sprites", "game-assets.barre-categories.studio3d",
   "game-assets.barre-categories.tiles"],
  'var __dzCatSVG={"a2d":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="3" y="3" width="8" height="8" rx="1.4"/><rect x="13" y="3" width="8" height="8" rx="1.4" opacity=".45"/><rect x="3" y="13" width="8" height="8" rx="1.4" opacity=".45"/><rect x="13" y="13" width="8" height="8" rx="1.4"/></svg>\',"pixel":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="3" y="15" width="6" height="6"/><rect x="9" y="9" width="6" height="6"/><rect x="15" y="3" width="6" height="6"/><rect x="9" y="15" width="6" height="6" opacity=".35"/><rect x="15" y="9" width="6" height="6" opacity=".35"/></svg>\',"3d":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2.8 20.6 7.4v9.2L12 21.2 3.4 16.6V7.4z" opacity=".34"/><path d="M12 2.8 20.6 7.4 12 11.9 3.4 7.4z"/></svg>\',"studio3d":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="2.6" y="4" width="18.8" height="16" opacity=".3"/><path d="M12 7.4 16.2 9.8v4.8L12 17l-4.2-2.4V9.8z"/></svg>\',"sprites":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="3" y="5" width="18" height="14" opacity=".3"/><rect x="5.4" y="7.4" width="5.4" height="4.6"/><rect x="13.2" y="12" width="5.4" height="4.6"/></svg>\',"tiles":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="3" y="4.8" width="8.4" height="6.6"/><rect x="12.6" y="4.8" width="8.4" height="6.6" opacity=".34"/><rect x="3" y="12.6" width="8.4" height="6.6" opacity=".34"/><rect x="12.6" y="12.6" width="8.4" height="6.6"/></svg>\',"materials":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="12" r="8.6" opacity=".34"/><path d="M12 3.4a8.6 8.6 0 0 1 0 17.2z"/></svg>\',"cards":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="4.6" y="6.4" width="10.4" height="13.8" opacity=".34" transform="rotate(-10 9.8 13.3)"/><rect x="10.2" y="4.6" width="9.6" height="15"/></svg>\'};',
  'var __dzCatSVG={"a2d":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="3" y="3" width="8" height="8" rx="1.4"/><rect x="13" y="3" width="8" height="8" rx="1.4" opacity=".45"/><rect x="3" y="13" width="8" height="8" rx="1.4" opacity=".45"/><rect x="13" y="13" width="8" height="8" rx="1.4"/></svg>\',"pixel":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="3" y="15" width="6" height="6"/><rect x="9" y="9" width="6" height="6"/><rect x="15" y="3" width="6" height="6"/><rect x="9" y="15" width="6" height="6" opacity=".35"/><rect x="15" y="9" width="6" height="6" opacity=".35"/></svg>\',"3d":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2.8 20.6 7.4v9.2L12 21.2 3.4 16.6V7.4z" opacity=".34"/><path d="M12 2.8 20.6 7.4 12 11.9 3.4 7.4z"/></svg>\',"studio3d":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="2.6" y="4" width="18.8" height="16" opacity=".3"/><path d="M12 7.4 16.2 9.8v4.8L12 17l-4.2-2.4V9.8z"/></svg>\',"sprites":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="3" y="5" width="18" height="14" opacity=".3"/><rect x="5.4" y="7.4" width="5.4" height="4.6"/><rect x="13.2" y="12" width="5.4" height="4.6"/></svg>\',"tiles":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="3" y="4.8" width="8.4" height="6.6"/><rect x="12.6" y="4.8" width="8.4" height="6.6" opacity=".34"/><rect x="3" y="12.6" width="8.4" height="6.6" opacity=".34"/><rect x="12.6" y="12.6" width="8.4" height="6.6"/></svg>\',"materials":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="12" r="8.6" opacity=".34"/><path d="M12 3.4a8.6 8.6 0 0 1 0 17.2z"/></svg>\',"cards":\'<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="4.6" y="6.4" width="10.4" height="13.8" opacity=".34" transform="rotate(-10 9.8 13.3)"/><rect x="10.2" y="4.6" width="9.6" height="15"/></svg>\'};',
  'var __dzCatSVG={"a2d":__dzGlH("dz-cat-assets-2d","100%"),"pixel":__dzGlH("dz-nav-espace-pixel","100%"),'
  '"3d":__dzGlH("dz-cat-3d","100%"),"studio3d":__dzGlH("dz-cat-studio-3d","100%"),"sprites":__dzGlH("dz-cat-sprites","100%"),'
  '"tiles":__dzGlH("dz-cat-tuiles","100%"),"materials":__dzGlH("dz-cat-matieres","100%"),"cards":__dzGlH("dz-cat-cartes","100%")};')
DEJA(["marque.logo.coque-rail-de-navigation-marque-ch", "marque.logo.coque-ecran-de-demarrage-splash",
      "marque.logo.accueil-onboarding-en-tete", "marque.logo.reglages-identite-marque", "marque.logo.reglages-identite-marque-2",
      "marque.navrail.logo", "marque.splash.logo", "marque.splash.image"],
     "dz-marque-poulpe / dz-marque-splash sont des IMAGES (choix utilisateur) : le site affiche déjà /api/branding/logo ou /assets/dz-splash.jpg")
# sites qui lisent un nom d'icône dans une DONNÉE (rail, catégories Qr, canaux, palette ⌘K, accordéon ie…) : la donnée est repointée
# par g1_saisie_cles ; le site d'appel n'a rien à changer
DEJA([
    'coque.accueil-premier-lancement-etape-canaux.canal-instagram-776560',
    'coque.accueil-premier-lancement-etape-canaux.canal-telegram-776560',
    'coque.accueil-premier-lancement-etape-canaux.canal-tiktok-776560',
    'coque.accueil-premier-lancement-etape-canaux.canal-x-776560',
    'coque.accueil-premier-lancement-etape-canaux.canal-youtube-776560',
    'coque.accueil-etape-bienvenue.accueil-carte-planificateur',
    'coque.accueil-etape-bienvenue.accueil-carte-publication-auto',
    'coque.accueil-etape-bienvenue.accueil-carte-studio',
    'coque.palette-de-commandes-k.cmd-aller-a-quick',
    'coque.palette-de-commandes-k.cmd-aller-au-planificateur',
    'coque.palette-de-commandes-k.cmd-aller-au-studio',
    'coque.palette-de-commandes-k.cmd-aller-aux-news',
    'coque.palette-de-commandes-k.cmd-nouveau-graphe-de-post-avatar',
    'coque.palette-de-commandes-k.cmd-nouveau-graphe-de-reel-news',
    'coque.palette-de-commandes-k.cmd-ouvrir-le-dernier-rendu',
    'coque.palette-de-commandes-k.cmd-programmer-un-post-pour-demain',
    'coque.palette-de-commandes-k.cmd-reglages-cles-d-api',
    'coque.palette-de-commandes-k.cmd-reglages-comptes-connectes',
    'coque.palette-de-commandes-k.cmd-revoir-l-accueil',
    'quick.accordeon.camera-curseurs',
    'quick.accordeon.disposition-de-la-composition',
    'quick.accordeon.gabarits-de-prompt',
    'quick.accordeon.gabarits-seedance-n',
    'quick.accordeon.parametres',
    'quick.accordeon.presets',
    'quick.accordeon.prompt',
    'quick.accordeon.script-n-4900-car',
    'quick.accordeon.source-seedance',
    'quick.accordeon.avatar-u-length',
    'quick.onglets-de-mode-en-tete-quick.onglet-composition',
    'quick.onglets-de-mode-en-tete-quick.onglet-heygen',
    'quick.onglets-de-mode-en-tete-quick.onglet-seedance',
    'quick.onglets-de-mode-en-tete-quick.onglet-voix-off',
    'quick.accordeon.script',
    'quick.accordeon.voix',
    'studio.canevas-bord-droit.insp-rouvrir',
    'studio.canevas-bord-gauche.dock-rouvrir',
    'studio.carte-de-noeud-canevas.noeud-cat-audio',
    'studio.carte-de-noeud-canevas.noeud-cat-compose',
    'studio.carte-de-noeud-canevas.noeud-cat-edit',
    'studio.carte-de-noeud-canevas.noeud-cat-gen',
    'studio.carte-de-noeud-canevas.noeud-cat-master',
    'studio.carte-de-noeud-canevas.noeud-cat-motion',
    'studio.carte-de-noeud-canevas.noeud-cat-output',
    'studio.carte-de-noeud-canevas.noeud-cat-source',
    'studio.inspecteur-de-noeud.insp-cat-audio',
    'studio.inspecteur-de-noeud.insp-cat-compose',
    'studio.inspecteur-de-noeud.insp-cat-edit',
    'studio.inspecteur-de-noeud.insp-cat-gen',
    'studio.inspecteur-de-noeud.insp-cat-master',
    'studio.inspecteur-de-noeud.insp-cat-motion',
    'studio.inspecteur-de-noeud.insp-cat-output',
    'studio.inspecteur-de-noeud.insp-cat-source',
    'studio.accordeon.audio',
    'studio.accordeon.connexions',
    'studio.accordeon.estimation',
    'studio.accordeon.execution',
    'studio.accordeon.nom-du-graphe',
    'studio.accordeon.sortie',
    'studio.accordeon.affinage-ia-diction-de-l-avatar',
    'studio.accordeon.animation',
    'studio.accordeon.article-news',
    'studio.accordeon.avatar',
    'studio.accordeon.decoupe',
    'studio.accordeon.effets-masque',
    'studio.accordeon.enchainement',
    'studio.accordeon.favoris',
    'studio.accordeon.format',
    'studio.accordeon.generateur',
    'studio.accordeon.generateur-de-prompt-ia',
    'studio.accordeon.generation-d-images',
    'studio.accordeon.layout',
    'studio.accordeon.master',
    'studio.accordeon.piste-musicale',
    'studio.accordeon.prompt',
    'studio.accordeon.proprietes',
    'studio.accordeon.apercu-du-rendu',
    'studio.accordeon.apercu-du-rendu-2',
    'studio.accordeon.apercu-du-rendu-en-direct',
    'studio.accordeon.render',
    'studio.accordeon.rendu-existant',
    'studio.accordeon.separateur',
    'studio.accordeon.texte',
    'studio.accordeon.texte-en-surimpression',
    'studio.accordeon.ticker',
    'studio.accordeon.titles-kind-kind',
    'studio.accordeon.video-ugc',
    'studio.accordeon.voix-off',
    'studio.accordeon.illustration-news',
    'studio.accordeon.image',
    'studio.accordeon.script-news',
    'studio.palette-de-noeuds-colonne-nodes.palette-cat-audio',
    'studio.palette-de-noeuds-colonne-nodes.palette-cat-compose',
    'studio.palette-de-noeuds-colonne-nodes.palette-cat-edit',
    'studio.palette-de-noeuds-colonne-nodes.palette-cat-gen',
    'studio.palette-de-noeuds-colonne-nodes.palette-cat-master',
    'studio.palette-de-noeuds-colonne-nodes.palette-cat-motion',
    'studio.palette-de-noeuds-colonne-nodes.palette-cat-output',
    'studio.palette-de-noeuds-colonne-nodes.palette-cat-source',
    'templates.accordeon.c-dzt-templates-inspecteur-region',
    'news.accordeon.classement-du-jour',
    'news.accordeon.filtre-gratuit',
    'news.accordeon.script',
    'news.accordeon.script-genere',
    'scheduler.calendrier-carte-de-post.canal-instagram-720009',
    'scheduler.calendrier-carte-de-post.canal-telegram-720009',
    'scheduler.calendrier-carte-de-post.canal-tiktok-720009',
    'scheduler.calendrier-carte-de-post.canal-x-720009',
    'scheduler.calendrier-carte-de-post.canal-youtube-720009',
    'scheduler.generateur-de-plan-fenetre.canal-instagram-754830',
    'scheduler.generateur-de-plan-fenetre.canal-telegram-754830',
    'scheduler.generateur-de-plan-fenetre.canal-tiktok-754830',
    'scheduler.generateur-de-plan-fenetre.canal-x-754830',
    'scheduler.generateur-de-plan-fenetre.canal-youtube-754830',
    'scheduler.inspecteur-de-post-canaux.canal-instagram-741544',
    'scheduler.inspecteur-de-post-canaux.canal-telegram-741544',
    'scheduler.inspecteur-de-post-canaux.canal-tiktok-741544',
    'scheduler.inspecteur-de-post-canaux.canal-x-741544',
    'scheduler.inspecteur-de-post-canaux.canal-youtube-741544',
    'scheduler.vue-routage-graphe-du-post.canal-instagram-727532',
    'scheduler.vue-routage-graphe-du-post.canal-telegram-727532',
    'scheduler.vue-routage-graphe-du-post.canal-tiktok-727532',
    'scheduler.vue-routage-graphe-du-post.canal-x-727532',
    'scheduler.vue-routage-graphe-du-post.canal-youtube-727532',
    'scheduler.accordeon.canaux',
    'scheduler.accordeon.legende',
    'scheduler.accordeon.programmation',
    'scheduler.accordeon.rendu',
    'scheduler.accordeon.reprogrammer-n-importe-quelle-date',
    'chapitres-episodes.accordeon.assemblage-export',
    'chapitres-episodes.accordeon.illustrations-animation',
    'chapitres-episodes.accordeon.script-voix',
    'chapitres-episodes.accordeon.storyboard-decoupage-en-scenes',
    'reglages.comptes-connectes.canal-instagram-701063',
    'reglages.comptes-connectes.canal-telegram-701063',
    'reglages.comptes-connectes.canal-tiktok-701063',
    'reglages.comptes-connectes.canal-x-701063',
    'reglages.comptes-connectes.canal-youtube-701063',
], "donnée repointée (g1_saisie_cles) : le site lit son nom d'icône dans la donnée")
