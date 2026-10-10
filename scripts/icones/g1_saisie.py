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

# ═══ S13 — couche SONVFX (Son & VFX, Montage historique) ═══════════════════════════════════════════════════════
E("son-vfx.en-tete-de-l-ecran-dzsonvfx.theme",
  'children:props.theme==="dark"?dzT("son.theme.clair"):dzT("son.theme.sombre")})}',
  'children:props.theme==="dark"?dzT("son.theme.clair"):dzT("son.theme.sombre")}',
  'children:[__dzGl("dz-action-theme")," ",props.theme==="dark"?dzT("son.theme.clair"):dzT("son.theme.sombre")]}')
for _ids, _anc in (
        (("son-vfx.onglet-audio-navigateur-de-sfx-svmsfxbro.sfx-pause", "son-vfx.onglet-audio-navigateur-de-sfx-svmsfxbro.sfx-ecouter"),
         'onClick:function(){props.play(url)},children:on?"▮▮":"▶"}'),
        (("son-vfx.onglet-audio-musique.musique-pause", "son-vfx.onglet-audio-musique.musique-ecouter"),
         'onClick:function(){props.play(resUrl)},children:on?"▮▮":"▶"}'),
        (("son-vfx.onglet-audio-voix.voix-pause", "son-vfx.onglet-audio-voix.voix-ecouter"),
         'children:playingVoice===v.id?"▮▮":"▶"}'),
        (("son-vfx.onglet-audio-editeur-30-s.editeur-pause", "son-vfx.onglet-audio-editeur-30-s.editeur-lecture"),
         'dzT("son.commun.lecture"),children:playing?"▮▮":"▶"}'),
        (("son-vfx.onglet-audio-sfx-generes.sfxgen-pause", "son-vfx.onglet-audio-sfx-generes.sfxgen-ecouter"),
         'children:sfxPlay===it.url?"▮▮":"▶"}'),
        (("montage.panneau-narration-bloc.narr-pause", "montage.panneau-narration-bloc.narr-ecouter"),
         'children:narrPlayId===c.id?"▮▮":"▶"}'),
        (("montage.barre-de-transport.pause", "montage.barre-de-transport.lecture"),
         'setPlaying(!playing)},children:playing?"▮▮":"▶"}')):
    GL(_ids[0], _anc, '"▮▮"', "dz-media-pause")
    GL(_ids[1], _anc, '"▶"', "dz-media-lecture")
T("son-vfx.onglet-audio-navigateur-de-sfx-svmsfxbro.sfx-biblio", 'children:busy===it.id?"…":dzT("son.sfx.ajouter")}',
  'dzT("son.sfx.ajouter")', "dz-action-ajouter-bibliotheque", "+")
T("son-vfx.onglet-vfx-particules.vfx-biblio", 'children:dzT("son.vfx.ouvrir_biblio")}', 'dzT("son.vfx.ouvrir_biblio")',
  "dz-nav-bibliotheque", "→")
T("son-vfx.onglet-audio-musique.musique-montage", 'children:dzT("son.musique.ouvrir_montage")}',
  'dzT("son.musique.ouvrir_montage")', "dz-nav-montage", "→")
T("son-vfx.onglet-audio-editeur-30-s.editeur-montage", 'children:dzT("son.editeur.envoyer_montage")}',
  'dzT("son.editeur.envoyer_montage")', "dz-nav-montage", "→")
T("son-vfx.onglet-audio-sfx-generes.sfxgen-montage", 'children:dzT("son.sfx.ouvrir_montage")}',
  'dzT("son.sfx.ouvrir_montage")', "dz-nav-montage", "→")
GL("son-vfx.onglet-audio-editeur-de-paroles-svmlyric.paroles-retirer", 'return j!==i}))},children:"✕"})]},i)})]})}', '"✕"',
   "dz-action-supprimer")
GL("son-vfx.onglet-audio-sfx-lignes-cibles.sfx-cible", 'fireNote(dzT("son.sfx.sans_backend"))},children:"▶"}', '"▶"',
   "dz-media-lecture")
# menu Affichage : la case cochée « ✓ » reste une donnée ; le menu la rend en icône
E(["montage.menu-affichage.menu-coche-inspecteur", "montage.menu-affichage.menu-coche-medias",
   "montage.menu-affichage.menu-coche-durees-sur-les-clips", "montage.menu-affichage.menu-coche-ancrer-la-barre-d-outils",
   "montage.menu-contextuel-d-un-clip-vitesse.menu-vitesse"],
  'r.jsx("span",{className:"svm-menukey",children:it.combo||""})', 'children:it.combo||""}',
  'children:it.combo==="✓"?__dzGl("dz-etat-option-active"):it.combo||""}')
GL("montage.inspecteur-overlay-trajectoire.trajectoire-retirer", 'svmMpRemove(sel.id,pi)},\r\n              children:"🗑︎"}',
   '"🗑︎"', "dz-action-supprimer")
GL("montage.inspecteur-clip-audio-automation.automation-retirer", 'svmVpRemove(sel.id,pi)},children:"🗑︎"}', '"🗑︎"',
   "dz-action-supprimer")
GL("montage.panneau-narration-bloc.narr-supprimer", 'delClipById(c.id)},\r\n          children:"🗑︎"}', '"🗑︎"',
   "dz-action-supprimer")
GL("montage.inspecteur-de-clip.clip-supprimer", 'onClick:delClip,children:"🗑︎"}', '"🗑︎"', "dz-action-supprimer")
E("montage.inspecteur-jonction-a-b.ab-reculer", 'children:"◀ −1"}', '"◀ −1"', '__dzGlT("dz-media-image-precedente","◀ −1","◀")')
E("montage.inspecteur-jonction-a-b.ab-avancer", 'children:"+1 ▶"}', '"+1 ▶"', '__dzGlT("dz-media-image-suivante","+1 ▶","▶")')
E("montage.inspecteur-clip-audio.automation", 'children:"◇ automation"}', '"◇ automation"',
  '__dzGlT("dz-media-automation","◇ automation","◇")')
E("montage.inspecteur-clip-audio-vitesse.vitesse-reset", 'children:"×"+spdv.toFixed(2)}', '"×"+spdv.toFixed(2)',
  '[__dzGl("dz-action-reinitialiser")," ","×"+spdv.toFixed(2)]')
GL("montage.bandeau-du-haut.menu", 'y:b.bottom+4}))},children:"☰"}', '"☰"', "dz-action-menu")
T("montage.bandeau-du-haut.rendre", 'children:dzT("montage.titre.rendre")}', 'dzT("montage.titre.rendre")', "dz-media-rendre", "→")
E("montage.barre-de-transport.vitesse-jog", 'children:(spd<0?"◀ ×":"×")+Math.abs(spd)}', '(spd<0?"◀ ×":"×")+Math.abs(spd)',
  'spd<0?[__dzGl("dz-media-vitesse")," ×"+Math.abs(spd)]:"×"+Math.abs(spd)')
GL("montage.barre-de-transport.coupe-prec", 'onClick:function(){jump(-1)},children:"◀◀"}', '"◀◀"', "dz-media-precedent")
GL("montage.barre-de-transport.image-prec", 'children:"|◀"}', '"|◀"', "dz-media-image-precedente")
GL("montage.barre-de-transport.image-suiv", 'children:"▶|"}', '"▶|"', "dz-media-image-suivante")
GL("montage.barre-de-transport.coupe-suiv", 'onClick:function(){jump(1)},children:"▶▶"}', '"▶▶"', "dz-media-suivant")
GL("montage.barre-de-transport.annuler", 'onClick:undo,children:"↶"}', '"↶"', "dz-action-annuler")
GL("montage.barre-de-transport.retablir", 'onClick:redo,children:"↷"}', '"↷"', "dz-action-retablir")
W("montage.barre-d-outils-de-la-timeline.marqueurs", 'children:"◆ "+((proj.markers||[]).length)}',
  '"◆ "+((proj.markers||[]).length)', "dz-media-marqueur", "◆")
GL("montage.barre-d-outils-de-la-timeline.titre-ajouter", 'onClick:function(){dzTtAdd()},children:"T+"}', '"T+"', "dz-media-titre")
GL("montage.barre-d-outils-de-la-timeline.ajustement-ajouter", 'onClick:function(){dzAjAdd()},children:"J+"}', '"J+"',
   "dz-calque-reglage")
GL("montage.bandeau-de-rappels-sous-la-timeline.rappels-masquer",
   'try{localStorage.setItem("dz_hints_off","1")}catch(_e){}},\r\n            children:"×"}', '"×"', "dz-action-fermer")
GL("montage.barre-de-transport.raccourcis", 'onClick:function(){setKbOn(!kbOn)},children:"?"}', '"?"', "dz-action-raccourcis")
GL("montage.en-tete-de-piste.piste-ajouter", 'openPicker(tr.id)},children:"+"},"add")', '"+"', "dz-action-ajouter")
GL("montage.en-tete-de-piste.piste-muet", 'onClick:function(){svmTrackMute(tr.id)},children:"M"}', '"M"', "dz-media-muet")
GL("montage.en-tete-de-piste.piste-solo", 'svmTrackSolo(tr.id,e.shiftKey)},children:"S"}', '"S"', "dz-media-solo")
GL("montage.en-tete-de-piste.piste-verrou", 'onClick:function(){svmTrackLock(tr.id)},children:"🔒︎"}', '"🔒︎"',
   "dz-etat-verrouille")
T("montage.inspecteur-overlay-trajectoire.trajectoire-poser", 'onClick:svmMpHere,children:dzT("montage.trajectoire.poser")}',
  'dzT("montage.trajectoire.poser")', "dz-media-image-cle", "◇")

# ═══ S14 — couche SFXSTUDIO (tiroir Sons) ══════════════════════════════════════════════════════════════════════
GL("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-fav-on", 'favToggle(it.name)},\r\n      children:on?"★":"☆"})}', '"★"',
   "dz-action-favori")
GL("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-fav-off", 'favToggle(it.name)},\r\n      children:on?"★":"☆"})}', '"☆"',
   "dz-action-favori")
E("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-fantome",
  'g.textContent="♪ "+item.name+(item.dur?" · "+svmShort(item.dur):"");',
  'g.textContent="♪ "+item.name+(item.dur?" · "+svmShort(item.dur):"");',
  '__dzGlD(g,"dz-media-audio","♪ "+item.name+(item.dur?" · "+svmShort(item.dur):""),"♪",12);')
E("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-arme", 'children:armed?prix+" ✓":lbl}', 'prix+" ✓"',
  '[prix," ",__dzGl("dz-action-valider")]')
for _a, _sfx in (('prevToggle(it)},\r\n        children:playing?"▮▮":"▶"}),\r\n      r.jsxs("div",{className:"svx-ibody"', ""),
                 ('prevToggle(it)},\r\n          children:playing?"▮▮":"▶"}),\r\n        ren?', "liste-")):
    GL((_sfx and "son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-liste-arreter" or "son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-arreter"), _a, '"▮▮"', "dz-media-arret")
    GL((_sfx and "son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-liste-ecouter" or "son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-ecouter"), _a, '"▶"', "dz-media-lecture")
W("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-derive",
  'children:"← "+(it.parent.length>20?it.parent.slice(0,19)+"…":it.parent)}',
  '"← "+(it.parent.length>20?it.parent.slice(0,19)+"…":it.parent)', "dz-etat-derive", "←")
GL("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-inserer", 'doInsert(it,"playhead")},\r\n          children:"⤵"}', '"⤵"',
   "dz-media-inserer")
GL("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-supprimer", 'setConfirmDel(it.name)},\r\n          children:"✕"}', '"✕"',
   "dz-action-supprimer")
GL("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-rafraichir", 'onClick:refresh,children:"⟳"}', '"⟳"', "dz-action-actualiser")
GL("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-importer", '"aria-hidden":!0}):"⤒"}', '"⤒"', "dz-action-importer")
GL("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-fermer", 'if(props.onClose)props.onClose()},children:"✕"})]}),\r\n    r.jsxs("div",{className:"svx-tabs"',
   '"✕"', "dz-action-fermer")
GL("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-semantique", 'setNearOf(null)},children:"✧"}', '"✧"',
   "dz-action-recherche-semantique")
GL("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-survol", 'setHoverPrev(!hoverPrev)},children:"👂"}', '"👂"',
   "dz-media-preecoute")
GL("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-module-ouvert", 'className:"svx-mcaret","aria-hidden":!0,children:exp?"▾":"▸"}',
   '"▾"', "dz-action-deplier")
E("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-module-ferme", 'className:"svx-mcaret","aria-hidden":!0,children:exp?"▾":"▸"}',
  '"▸"', '__dzGl("dz-action-deplier","1em",{transform:"rotate(-90deg)"})')
GL("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-detail-fermer", 'onClick:function(){setPin(!1)},children:"✕"}', '"✕"',
   "dz-action-fermer")
T("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-aide-fav", 'children:dzT("sfx.vide.aucun_favori_aide")}',
  'dzT("sfx.vide.aucun_favori_aide")', "dz-action-favori", "★")
T("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-aide-indexer", 'fireNote(dzT("sfx.recherche.pas_indexe",{nom:it.name}))',
  'dzT("sfx.recherche.pas_indexe",{nom:it.name})', "dz-action-recherche-semantique", "✧")
GL("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-stems", 'actBtn(it,"stems","≡",', '"≡"', "dz-media-stems")
GL("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-isoler", 'actBtn(it,"isolate","◌",', '"◌"', "dz-media-isoler-voix")
GL("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-ameliorer", 'actBtn(it,"enhance","✦",', '"✦"', "dz-media-ameliorer")
T("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-detail-stop", ':playing?dzT("sfx.rack.stop"):dzT("sfx.rack.ecouter")}',
  'dzT("sfx.rack.stop")', "dz-media-arret", "▮▮")
T("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-detail-ecouter", ':playing?dzT("sfx.rack.stop"):dzT("sfx.rack.ecouter")}',
  'dzT("sfx.rack.ecouter")', "dz-media-lecture", "▶")
GL("son-vfx.tiroir-sons-dzsfx-drawer-montage-et-son-.sons-onglet-fav", 'var SVX_TABS=[["tous",dzT("sfx.onglet.tous")],["fav","★"]',
   '"★"', "dz-action-favori")

# ═══ S15 — couche VFXRACK (rack d'effets) ══════════════════════════════════════════════════════════════════════
GL("son-vfx.rack-vfx-vfxrack-panneau-d-effets-du-cli.vfx-onglet-fav",
   'cats:[["tous",dzT("vfx.commun.tous")],["fav","★"]].concat(cats)}}', '"★"', "dz-action-favori")
GL("son-vfx.rack-vfx-vfxrack-panneau-d-effets-du-cli.vfx-onglet-fav",
   'var tabs=(cat&&cat.cats)||[["tous",dzT("vfx.commun.tous")],["fav","★"]];', '"★"', "dz-action-favori")
E("son-vfx.rack-vfx-vfxrack-panneau-d-effets-du-cli.vfx-fantome", 'g.textContent="✦ "+e.label;', 'g.textContent="✦ "+e.label;',
  '__dzGlD(g,"dz-edit-effet","✦ "+e.label,"✦",12);')
GL("son-vfx.rack-vfx-vfxrack-panneau-d-effets-du-cli.vfx-fav-on", 'favToggle(e.type)},\r\n          children:on?"★":"☆"}', '"★"',
   "dz-action-favori")
GL("son-vfx.rack-vfx-vfxrack-panneau-d-effets-du-cli.vfx-fav-off", 'favToggle(e.type)},\r\n          children:on?"★":"☆"}', '"☆"',
   "dz-action-favori")
GL("son-vfx.rack-vfx-vfxrack-panneau-d-effets-du-cli.vfx-fermer", 'if(props.onClose)props.onClose()},children:"✕"})]}),\r\n    r.jsx(VfxAlert,{})',
   '"✕"', "dz-action-fermer")
GL("son-vfx.rack-vfx-vfxrack-panneau-d-effets-du-cli.vfx-module-ouvert", 'className:"vfx-mcaret","aria-hidden":!0,children:open?"▾":"▸"}',
   '"▾"', "dz-action-deplier")
E("son-vfx.rack-vfx-vfxrack-panneau-d-effets-du-cli.vfx-module-ferme", 'className:"vfx-mcaret","aria-hidden":!0,children:open?"▾":"▸"}',
  '"▸"', '__dzGl("dz-action-deplier","1em",{transform:"rotate(-90deg)"})')
GL("son-vfx.rack-vfx-vfxrack-panneau-d-effets-du-cli.vfx-monter", 'onClick:function(){moveAt(i,-1)},children:"▲"}', '"▲"', "dz-edit-monter")
GL("son-vfx.rack-vfx-vfxrack-panneau-d-effets-du-cli.vfx-descendre", 'onClick:function(){moveAt(i,1)},children:"▼"}', '"▼"',
   "dz-edit-descendre")
GL("son-vfx.rack-vfx-vfxrack-panneau-d-effets-du-cli.vfx-contourne", 'onClick:function(){bypassAt(i)},children:off?"◌":"◉"}', '"◌"',
   "dz-etat-contourne")
GL("son-vfx.rack-vfx-vfxrack-panneau-d-effets-du-cli.vfx-actif", 'onClick:function(){bypassAt(i)},children:off?"◌":"◉"}', '"◉"',
   "dz-etat-actif")
GL("son-vfx.rack-vfx-vfxrack-panneau-d-effets-du-cli.vfx-retirer", 'onClick:function(){removeAt(i)},children:"✕"}', '"✕"',
   "dz-action-retirer")
T("son-vfx.rack-vfx-vfxrack-panneau-d-effets-du-cli.vfx-aide-fav", 'children:dzT("vfx.panneau.favori_aide")}',
  'dzT("vfx.panneau.favori_aide")', "dz-action-favori", "★")
T("son-vfx.rack-vfx-vfxrack-panneau-d-effets-du-cli.vfx-ajouter", 'children:dzT("vfx.pile.ajouter")}', 'dzT("vfx.pile.ajouter")',
  "dz-action-ajouter", "+")

# ═══ S16 — couche MONTAGE (Montage, et composants Studio / Templates / Bibliothèque qui y vivent) ═══════════════
# t143 : textes passés par dzT (traduction L3, posée AVANT G1) ; l'anglais garde le glyphe
for _lit in ('dzT("montage.pistes.ajouter_video")', 'dzT("montage.pistes.ajouter_audio")'):
    T("montage.bandeau-du-haut.ajout-piste", 'children:' + _lit + '},', _lit, "dz-action-ajouter", "+")
GL("montage.en-tete-de-piste.piste-grip", 'className:"dzm-grip","aria-hidden":!0,children:"⋮"}', '"⋮"', "dz-action-poignee")
GL("montage.en-tete-de-piste.piste-monter", 'onClick:function(){mv(-1)},children:"▲"}', '"▲"', "dz-edit-monter")
GL("montage.en-tete-de-piste.piste-descendre", 'onClick:function(){mv(1)},children:"▼"}', '"▼"', "dz-edit-descendre")
GL("montage.en-tete-de-piste.piste-retirer", 'children:arm?String(n):"×"}', '"×"', "dz-action-supprimer")
GL("montage.liste-des-projets-popover-projets.projet-vide", 'title:dzT("montage.projets.montage_vide"),\r\n          children:"\\u2205"}', '"\\u2205"',
   "dz-etat-vide")
GL("montage.liste-des-projets-popover-projets.projet-comparer", 'props.onDiff(p)},children:"⇄"}', '"⇄"', "dz-action-comparer")
GL("montage.liste-des-projets-popover-projets.projet-supprimer", 'children:xArm?dzT("montage.projets.supprimer_arme"):"×"}', '"×"', "dz-action-supprimer")
GL("montage.barre-de-duree-de-timeline-dzmdurbtn.duree-moins", 'dzmDurBtn("dzm-durm","−",', '"−"', "dz-media-timeline-raccourcir")
GL("montage.barre-de-duree-de-timeline-dzmdurbtn.duree-plus", 'dzmDurBtn("dzm-durp","+",', '"+"', "dz-media-timeline-allonger")
T("montage.inspecteur-plan.extraire-son", 'children:tr?dzT("montage.extraire.bouton",{piste:TR}):',
  'dzT("montage.extraire.bouton",{piste:TR})', "dz-media-extraire-son", "→")
GL("montage.barre-d-outils-flottante-onglet-outils.tb-onglet-ouvert", 'className:"dzm-tbchev","aria-hidden":!0,\r\n        children:open?"▾":"▴"}',
   '"▾"', "dz-action-deplier")
E("montage.barre-d-outils-flottante-onglet-outils.tb-onglet-ferme", 'className:"dzm-tbchev","aria-hidden":!0,\r\n        children:open?"▾":"▴"}',
  '"▴"', '__dzGl("dz-action-deplier","1em",{transform:"rotate(180deg)"})')
GL("montage.barre-d-outils-flottante.tb-recentrer", 'o.onRecentrer()},\r\n      children:"⌖"}', '"⌖"', "dz-action-recentrer")
GL("montage.barre-d-outils-flottante.tb-replier", 'o.onClose()},\r\n      children:"×"},"cl")', '"×"', "dz-action-deplier")
GL("montage.index-des-marqueurs-dzmmarkerindex.marqueur-retirer", 'o.onRemove(m.id)},\r\n          children:"\\u2716"}', '"\\u2716"',
   "dz-action-supprimer")
T("montage.inspecteur-plan-rampe-de-vitesse.rampe-diviser", 'children:dzT("montage.proprietes.diviser")}',
  'dzT("montage.proprietes.diviser")', "dz-edit-couper", "→")
E("montage.tiroir-medias-dzmmediadrawer.medias-filtre-3", 'var DZM_NOTE_CHIPS=[[3,"★ 3+",', '"★ 3+"',
  '__dzGlT("dz-etat-note","★ 3+","★")')
E("montage.tiroir-medias-dzmmediadrawer.medias-filtre-5", '  [5,"★ 5","Ne montrer que les Good Take', '"★ 5"',
  '__dzGlT("dz-etat-note","★ 5","★")')
T("montage.tiroir-medias-dzmmediadrawer.medias-autoclips", 'children:dzT("montage.autoclips.bouton")}',
  'dzT("montage.autoclips.bouton")', "dz-media-extraits", "✂")
GL("montage.tiroir-medias-dzmmediadrawer.medias-noter", 'noter(j,i)},children:"★"}', '"★"', "dz-etat-note")
E("montage.barre-du-lecteur-prise-de-voix-dzmvoicer.voixoff-stop", 'children:st==="prise"?"■ "+el:', '"■ "+el',
  '__dzGlT("dz-media-arret","■ "+el,"■")')
T("montage.barre-du-lecteur-prise-de-voix-dzmvoicer.voixoff-rec",
  ':st==="envoi"?dzT("montage.prise.puce_envoi"):dzT("montage.prise.puce")}', 'dzT("montage.prise.puce")', "dz-media-rec", "●")
GL("montage.scopes-dzmscopes.scopes-fermer", '"aria-label":dzT("montage.scopes.fermer"),onClick:bascule,children:"×"}', '"×"', "dz-action-fermer")
# Studio (composants de la couche)
T("studio.inspecteur-epingle-du-noeud-dzpinpanel.pin-sans", 'children:dzT("studio.epingle.sans_epingle")}',
  'dzT("studio.epingle.sans_epingle")', "dz-etat-epingle", "📌")
T("studio.inspecteur-epingle-du-noeud-dzpinpanel.pin-pas-encore", 'children:dzT("studio.epingle.pas_encore")}',
  'dzT("studio.epingle.pas_encore")', "dz-etat-epingle", "📌")
T("studio.inspecteur-epingle-du-noeud-dzpinpanel.pin-epingle", 'children:dzT("studio.epingle.epingle")}',
  'dzT("studio.epingle.epingle")', "dz-etat-epingle", "📌")
T("studio.inspecteur-epingle-du-noeud-dzpinpanel.pin-regenerer", 'children:dzT("studio.epingle.regenerer")}',
  'dzT("studio.epingle.regenerer")', "dz-action-regenerer", "↻")
T("studio.panneau-duel-de-moteurs.duel-champion", 'children:dzT("studio.duel.champion",{nom:dzDuelLabel(mm,A)})}',
  'dzT("studio.duel.champion",{nom:dzDuelLabel(mm,A)})', "dz-etat-meilleur", "⚔")
GL("studio.tiroir-resultat-defileur-image-par-image.scrub-prec", 'onClick:function(){pas(-1)},children:"‹"}', '"‹"',
   "dz-media-image-precedente")
GL("studio.tiroir-resultat-defileur-image-par-image.scrub-suiv", 'onClick:function(){pas(1)},children:"›"}', '"›"',
   "dz-media-image-suivante")
# Templates
E("templates.fenetre-reagencer-dzreflowbar.avertissement", 'return r.jsx("div",{children:"⚠ "+w},"w"+i)', '"⚠ "+w',
  '__dzGlT("dz-etat-avertissement","⚠ "+w,"⚠")')
GL("templates.inspecteur-masque-de-case-dzmaskeditor.masque-retirer", 'cursor:"pointer"},children:"✕"})]},"t"+i)', '"✕"',
   "dz-action-retirer")
T("templates.inspecteur-texte-en-arche-dztexteeditor.arche-deborde", 'children:dzT("templates.texte.arc_deborde",{n:rayonMin})}',
  'dzT("templates.texte.arc_deborde",{n:rayonMin})', "dz-etat-avertissement", "⚠")
T("templates.inspecteur-animation-de-region-dzanimedi.anim-rejouer", 'children:dzT("templates.anim.rejouer")}',
  'dzT("templates.anim.rejouer")', "dz-media-lecture", "▶")
T("templates.editeur-de-composant-dzcomposanteditor.composant-retablir", 'children:dzT("templates.composant.retablir")}',
  'dzT("templates.composant.retablir")', "dz-action-reinitialiser", "↺")
T("templates.export-figma-dzexportfigma.export-svg", 'children:dzT("templates.export.svg")}', 'dzT("templates.export.svg")',
  "dz-action-exporter", "↓")
# Bibliothèque
W("bibliotheque.barre-de-filtres-dzmetachips.filtre-note", 'ch.push(puce("note",3,"★ 3+ ("+c.note3+")",f.note===3))',
  '"★ 3+ ("+c.note3+")"', "dz-etat-note", "★")
GL("bibliotheque.carte-d-element-grille.carte-fav-on", 'children:fav?"★":"☆"}', '"★"', "dz-action-favori")
GL("bibliotheque.carte-d-element-grille.carte-fav-off", 'children:fav?"★":"☆"}', '"☆"', "dz-action-favori")
E("bibliotheque.carte-d-element-grille.carte-note", 'children:"●".repeat(note)}', '"●".repeat(note)',
  'Array.apply(null,Array(note)).map(function(){return __dzGl("dz-etat-note")})')
GL("bibliotheque.fiche-editeur-de-meta-dzmetaeditor.meta-note-on", 'children:note>=n?"●":"○"}', '"●"', "dz-etat-note")
E("bibliotheque.fiche-editeur-de-meta-dzmetaeditor.meta-note-off", 'children:note>=n?"●":"○"}', '"○"',
  '__dzGl("dz-etat-note","1em",{opacity:.35})')
GL("bibliotheque.fiche-editeur-de-meta-dzmetaeditor.meta-tag-retirer",
   'color:"var(--ink-muted)",fontSize:11,padding:"0 2px"},children:"×"})]},"t"+g)', '"×"', "dz-action-retirer")
GL("bibliotheque.fiche-lignee-dzlignee.lignee-externe", 'placeItems:"center",fontSize:16},children:"🎬"})', '"🎬"', "dz-media-video")
T("bibliotheque.fiche-lignee-dzlignee.lignee-cycle", 'children:dzT("biblio.lignee.cycle")}', 'dzT("biblio.lignee.cycle")',
  "dz-etat-avertissement", "↺")
T("bibliotheque.fiche-licence-dzfiche.fiche-licence", 'children:dzT("biblio.fiche.licence_inconnue")}',
  'dzT("biblio.fiche.licence_inconnue")', "dz-etat-avertissement", "⚠")
E(["bibliotheque.corbeille-dzcorbeille.corbeille-image", "bibliotheque.corbeille-dzcorbeille.corbeille-son",
   "bibliotheque.corbeille-dzcorbeille.corbeille-rendu", "bibliotheque.corbeille-dzcorbeille.corbeille-illisible"],
  'var icone={image:"🖼",son:"🔊",rendu:"🎬",illisible:"⚠"};', 'var icone={image:"🖼",son:"🔊",rendu:"🎬",illisible:"⚠"};',
  'var icone={image:__dzGl("dz-media-image"),son:__dzGl("dz-media-audio"),rendu:__dzGl("dz-media-video"),'
  'illisible:__dzGl("dz-etat-avertissement")};')
for _id, _k, _c, _g in (("outil-corbeille", "biblio.outils.corbeille", "dz-nav-corbeille", "🗑"),
                        ("outil-nettoyage", "biblio.outils.nettoyage", "dz-action-nettoyer", "🧹"),
                        ("outil-recherche", "biblio.outils.recherche", "dz-action-chercher", "🔎"),
                        ("vue-grille", "biblio.outils.grille", "dz-action-vue-grille", "▦"),
                        ("vue-liste", "biblio.outils.liste", "dz-action-vue-liste", "☰")):
    T("bibliotheque.barre-d-outils-de-la-bibliotheque-dzouti." + _id, 'dzT("%s"),dzT("%s_aide")' % (_k, _k), 'dzT("%s")' % _k,
      _c, _g)
GL("bibliotheque.commentaires-dzcommentaires.commentaire-suppr",
   'onClick:function(){supprimer(c)},style:{background:"none",border:0,cursor:"pointer",color:"var(--ink-muted)"},children:"×"}',
   '"×"', "dz-action-supprimer")
E("bibliotheque.vue-liste-dzliste.liste-tri-desc", 'children:c[1]+(on?(tri.desc?" ▾":" ▴"):"")}', 'c[1]+(on?(tri.desc?" ▾":" ▴"):"")',
  'on?[c[1]," ",__dzGl("dz-action-trier","1em",tri.desc?void 0:{transform:"rotate(180deg)"})]:c[1]')
DEJA("bibliotheque.vue-liste-dzliste.liste-tri-asc", "même site que liste-tri-desc : dz-action-trier, retourné pour l'ordre croissant")
GL("bibliotheque.vue-liste-dzliste.liste-son", 'children:z.kind==="audio"?"🔊":z.kind==="render"?"🎬":"·"}', '"🔊"', "dz-media-audio")
GL("bibliotheque.vue-liste-dzliste.liste-rendu", 'children:z.kind==="audio"?"🔊":z.kind==="render"?"🎬":"·"}', '"🎬"', "dz-media-video")
E("bibliotheque.vue-liste-dzliste.liste-note", 'cell(z.note?"●".repeat(Math.min(5,z.note)):"","o")',
  '"●".repeat(Math.min(5,z.note))',
  'Array.apply(null,Array(Math.min(5,z.note))).map(function(){return __dzGl("dz-etat-note")})')
GL("bibliotheque.vue-liste-dzliste.liste-fav", 'cell(z.fav?"★":"","f")', '"★"', "dz-action-favori")
E(["bibliotheque.projets-etat-dzetatprojet.etat-rendu", "bibliotheque.projets-etat-dzetatprojet.etat-son"],
  'children:(z.kind==="render"?"🎬 ":z.kind==="audio"?"🔊 ":"")+z.ref}', '(z.kind==="render"?"🎬 ":z.kind==="audio"?"🔊 ":"")+z.ref',
  'z.kind==="render"?__dzGlT("dz-media-video","🎬 "+z.ref,"🎬"):z.kind==="audio"?__dzGlT("dz-media-audio","🔊 "+z.ref,"🔊"):z.ref')
T("bibliotheque.fiche-images-semblables-dzsemblables.semblables-sans-clip", 'setMsg(R.status===503?dzT("biblio.semblables.sans_clip"):',
  'dzT("biblio.semblables.sans_clip")', "dz-action-chercher", "🔎")
E(["bibliotheque.menu-ranger-dans-un-projet.projet-dedans", "bibliotheque.menu-ranger-dans-un-projet.projet-ranger"],
  'return{lbl:(on?"✓ ":"📁 ")+p.nom', 'return{lbl:', 'return{ic:on?"dz-etat-option-active":"dz-action-ranger",g:on?"✓":"📁",lbl:')
E("bibliotheque.menu-envoyer-vers-dzsendto.envoyer-studio-nouveau-graph", '{lbl:dzT("biblio.envoyer.studio_rendu"),fn:',
  '{lbl:', '{ic:"dz-nav-studio",g:"🎬",lbl:')
E("bibliotheque.menu-envoyer-vers-dzsendto.envoyer-lancer-une-recette-d", '{lbl:dzT("biblio.envoyer.recette"),fn:',
  '{lbl:', '{ic:"dz-action-lancer-recette",g:"🍳",lbl:')
E("bibliotheque.menu-envoyer-vers-lancer-une-recette-cho.recette-choix", 'return{lbl:"🍳 "+g.name+" — "+g.recette+" source(s)",v:g.id}',
  'return{lbl:', 'return{ic:"dz-action-lancer-recette",g:"🍳",lbl:')
E([], 'return{lbl:o.lbl,fn:function(){fini=!0;res(o.v)}}', 'return{lbl:o.lbl,', 'return{ic:o.ic,g:o.g,lbl:o.lbl,')
T("bibliotheque.barre-des-projets-dzprojetsbar.projets-auto-on", 'ch.push(bouton(ici?dzT("biblio.projets.auto_ici"):',
  'dzT("biblio.projets.auto_ici")', "dz-action-rangement-auto", "●")
T("bibliotheque.barre-des-projets-dzprojetsbar.projets-auto-off", 'ici?dzT("biblio.projets.auto_ici"):dzT("biblio.projets.auto_activer"),',
  'dzT("biblio.projets.auto_activer")', "dz-action-rangement-auto", "○")
T("bibliotheque.barre-des-projets-dzprojetsbar.projets-auto-actif", 'children:[dzT("biblio.projets.auto_actif",{nom:actif.nom}),',
  'dzT("biblio.projets.auto_actif",{nom:actif.nom})', "dz-action-rangement-auto", "●")
GL("bibliotheque.barre-des-projets-dzprojetsbar.projets-auto-stop", 'cursor:"pointer",color:"var(--ink-muted)",fontSize:11},children:"✕"})]}));',
   '"✕"', "dz-action-rangement-auto")
T("bibliotheque.barre-des-projets-dzprojetsbar.projets-epingle", 'ch.push(bouton(f.epingle?dzT("biblio.projets.epingle"):',
  'dzT("biblio.projets.epingle")', "dz-action-epingler-mobile", "📱")
T("bibliotheque.barre-des-projets-dzprojetsbar.projets-epingler", ':dzT("biblio.projets.epingler"),', 'dzT("biblio.projets.epingler")',
  "dz-action-epingler-mobile", "📱")
T("bibliotheque.barre-des-projets-dzprojetsbar.projets-renommer", 'ch.push(bouton(dzT("biblio.projets.renommer_bouton"),',
  'dzT("biblio.projets.renommer_bouton")', "dz-action-renommer", "✎")
T("bibliotheque.barre-des-projets-dzprojetsbar.projets-etat", 'ch.push(bouton(dzT("biblio.projets.etat_bouton"),',
  'dzT("biblio.projets.etat_bouton")', "dz-etat-information", "▦")
DEJA("bibliotheque.barre-des-projets-dzprojetsbar.projets-option-mobile",
     "NON POSÉ : le 📱 vit dans le texte d'une <option> NATIVE (r.jsx(\"option\")) — aucune icône possible ; texte gardé")
DEJA("bibliotheque.liste-tri-par-lignee.lignee-indent",
     "NON POSÉ : « ↳ » est préfixé au NOM de l'élément (donnée name, chaîne) pour la vue triée par lignée — pas un site d'icône")
# Réglages : choix de la langue (DzLangueUI)
E("reglages.fournisseurs-par-defaut-langue-dzlangueu.langue", 'children:dzT("reglages.langue.titre")}', 'dzT("reglages.langue.titre")',
  '[__dzGl("dz-action-langue")," ",dzT("reglages.langue.titre")]')
# barre d'outils flottante du Montage (DzmTbIcon) : les tracés maison cèdent la place à la suite
E(["montage.barre-outils.piste-video", "montage.barre-outils.piste-audio", "montage.barre-outils.bibliotheque",
   "montage.barre-outils.couleur", "montage.barre-outils.rebond", "montage.barre-outils.glow", "montage.barre-outils.emoji",
   "montage.barre-outils.texte", "montage.barre-outils.projets", "montage.barre-outils.poignee", "montage.barre-outils.piste-incrust",
   "montage.barre-d-outils-flottante-dzmtoolbar.tb-piste-video", "montage.barre-d-outils-flottante-dzmtoolbar.tb-piste-audio",
   "montage.barre-d-outils-flottante-dzmtoolbar.tb-bibliotheque", "montage.barre-d-outils-flottante-dzmtoolbar.tb-couleur",
   "montage.barre-d-outils-flottante-dzmtoolbar.tb-rebond", "montage.barre-d-outils-flottante-dzmtoolbar.tb-glow",
   "montage.barre-d-outils-flottante-dzmtoolbar.tb-emoji", "montage.barre-d-outils-flottante-dzmtoolbar.tb-texte",
   "montage.barre-d-outils-flottante-dzmtoolbar.tb-projets", "montage.barre-d-outils-flottante-dzmtoolbar.tb-poignee",
   "montage.barre-d-outils-flottante-dzmtoolbar.tb-piste-incrust"],
  'var px=Number(o.size);if(!isFinite(px)||px<=0)px=DZM_TB_PX;\r\n  return r.jsx("svg",{className:"dzm-tbi",',
  'var px=Number(o.size);if(!isFinite(px)||px<=0)px=DZM_TB_PX;\r\n',
  'var px=Number(o.size);if(!isFinite(px)||px<=0)px=DZM_TB_PX;\r\n'
  '  /* icônes G1 : la suite Deepotus Glyph d\'abord (window.DZ_ICONS), les tracés maison en repli */\r\n'
  '  var gk=DZM_TB_GLYPHE[o.name],gs=gk&&typeof window!=="undefined"&&window.DZ_ICONS&&window.DZ_ICONS[gk],'
  'gm=typeof gs==="string"&&/^<svg[^>]*>([\\s\\S]*)<\\/svg>$/.exec(gs);\r\n'
  '  if(gm)return r.jsx("svg",{className:"dzm-tbi",viewBox:"0 0 24 24",fill:"currentColor",width:px,height:px,"aria-hidden":!0,\r\n'
  '    focusable:"false","data-dzi":gk,dangerouslySetInnerHTML:{__html:gm[1]}},o.k||("tbi-"+o.name));\r\n')
E([], 'function DzmTbIcon(o){', 'function DzmTbIcon(o){',
  'var DZM_TB_GLYPHE={"piste-video":"dz-media-piste-video","piste-audio":"dz-media-piste-audio",'
  '"bibliotheque":"dz-action-choisir-bibliotheque","couleur":"dz-edit-anim-couleur","rebond":"dz-edit-anim-rebond",'
  '"glow":"dz-edit-anim-halo","emoji":"dz-media-emoji-auto","texte":"dz-media-sous-titres","projets":"dz-nav-projets",'
  '"poignee":"dz-action-poignee","piste-incrust":"dz-media-incrustation"};\r\nfunction DzmTbIcon(o){')

# ═══ S17 — bloc SUBS (tiroir sous-titres ; sa source ne reconstruit plus le bloc : édité par le maillon) ═══════
E("montage.tiroir-sous-titres-subs.subs-fam-fix", '  fix:{glyph:"✎",dit:', '"✎"', '__dzGl("dz-etat-grave")')
E("montage.tiroir-sous-titres-subs.subs-fam-ack", '  ack:{glyph:"✓",dit:', '"✓"', '__dzGl("dz-etat-acquitte")')
for _id, _v, _g, _k in (("subs-ancre-gauche", '["left","gauche","⭰"]', "⭰", "dz-edit-aligner-gauche"),
                        ("subs-ancre-centre", '["center","centré","≡"]', "≡", "dz-edit-aligner-centre-h"),
                        ("subs-ancre-droite", '["right","droite","⭲"]', "⭲", "dz-edit-aligner-droite"),
                        ("subs-ancre-haut", '["top","haut","⤒"]', "⤒", "dz-edit-aligner-haut"),
                        ("subs-ancre-milieu", '["middle","milieu","⇔"]', "⇔", "dz-edit-aligner-centre-v"),
                        ("subs-ancre-bas", '["bottom","bas","⤓"]', "⤓", "dz-edit-aligner-bas")):
    E("montage.tiroir-sous-titres-subs-onglet-style." + _id, _v, '"%s"' % _g, '__dzGl("%s")' % _k)
E("montage.tiroir-sous-titres-subs-onglet-style.subs-hors-zone", 'l\'ignore, l\'aperçu aussi.",\r\n      children:readout},"hud")',
  'children:readout}', 'children:__dzGlT("dz-etat-avertissement",readout,"⚠")}')
GL("montage.tiroir-sous-titres-subs.subs-module-ouvert", 'className:"sub-mcaret","aria-hidden":!0,children:open?"▾":"▸"}', '"▾"',
   "dz-action-deplier")
E("montage.tiroir-sous-titres-subs.subs-module-ferme", 'className:"sub-mcaret","aria-hidden":!0,children:open?"▾":"▸"}', '"▸"',
  '__dzGl("dz-action-deplier","1em",{transform:"rotate(-90deg)"})')
GL("montage.tiroir-sous-titres-subs.subs-caler", 'onClick:function(){setHere(s.id,which)},children:"⏱"}', '"⏱"',
   "dz-media-tete-lecture")
GL("montage.tiroir-sous-titres-subs.subs-replique-ouverte", 'toggleOpen(s.id)},\r\n        children:open?"▾":"▸"},"c")', '"▾"',
   "dz-action-deplier")
E("montage.tiroir-sous-titres-subs.subs-replique-fermee", 'toggleOpen(s.id)},\r\n        children:open?"▾":"▸"},"c")', '"▸"',
  '__dzGl("dz-action-deplier","1em",{transform:"rotate(-90deg)"})')
E("montage.tiroir-sous-titres-subs.subs-reafficher", 'children:s.hidden?"🚫":"👁"},"eye")', '"🚫"',
  '__dzGl("dz-etat-visible","1em",{opacity:.4})')
GL("montage.tiroir-sous-titres-subs.subs-masquer", 'children:s.hidden?"🚫":"👁"},"eye")', '"👁"', "dz-etat-visible")
GL("montage.tiroir-sous-titres-subs.subs-supprimer", 'onClick:function(){delAt(s.id)},children:"✕"},"del")', '"✕"',
   "dz-action-supprimer")
E("montage.tiroir-sous-titres-subs.subs-calc-ack", 'r.jsx("b",{children:"✓ "},"g1")', '"✓ "', '[__dzGl("dz-etat-acquitte")," "]')
E("montage.tiroir-sous-titres-subs.subs-calc-fix", 'r.jsx("b",{children:"✎ "},"g2")', '"✎ "', '[__dzGl("dz-etat-grave")," "]')
GL("montage.tiroir-sous-titres-subs.subs-legende-fix", 'children:"✎"},"g"),\r\n          "écrit dans le fichier livré"', '"✎"',
   "dz-etat-grave")
GL("montage.tiroir-sous-titres-subs.subs-legende-ack", 'children:"✓"},"g"),\r\n          "acquitte : n\'écrit rien', '"✓"',
   "dz-etat-acquitte")
GL("montage.tiroir-sous-titres-subs.subs-trace", 'children:"✓"},"g"),\r\n        r.jsxs("span",{className:"sub-covigntxt"', '"✓"',
   "dz-etat-acquitte")
E("montage.tiroir-sous-titres-subs.subs-gestes-replier", 'children:covOpen?"replier les gestes ▾"', '"replier les gestes ▾"',
  '__dzGlT("dz-action-deplier","replier les gestes ▾","▾")')
E("montage.tiroir-sous-titres-subs.subs-gestes-deplier", ':"traiter "+subsPl(covBad.length,"plan")+" ▸"}',
  '"traiter "+subsPl(covBad.length,"plan")+" ▸"',
  '["traiter "+subsPl(covBad.length,"plan")," ",__dzGl("dz-action-deplier","1em",{transform:"rotate(-90deg)"})]')
E(["montage.tiroir-sous-titres-subs.subs-seuils-replier", "montage.tiroir-sous-titres-subs.subs-seuils-regler"],
  'children:nrmOn?"replier ▾":"régler ▸"}', 'nrmOn?"replier ▾":"régler ▸"',
  'nrmOn?__dzGlT("dz-action-deplier","replier ▾","▾"):["régler ",__dzGl("dz-action-deplier","1em",{transform:"rotate(-90deg)"})]')
E("montage.tiroir-sous-titres-subs.subs-redecouper", 'children:"redécouper toute la piste "+(cpsOn?"▾":"▸")}',
  '"redécouper toute la piste "+(cpsOn?"▾":"▸")',
  '["redécouper toute la piste ",__dzGl("dz-action-deplier","1em",cpsOn?void 0:{transform:"rotate(-90deg)"})]')
GL("montage.tiroir-sous-titres-subs.subs-fermer", 'if(props.onClose)props.onClose()},children:"✕"})]}),\r\n    /* ── LA LIGNE DES COMPTES',
   '"✕"', "dz-action-fermer")

# ═══ S18 — bloc TRANSFERT (Réglages › Transfert entre machines) ════════════════════════════════════════════════
E(["reglages.transfert-entre-machines.modal-titre", "reglages.transfert.modale-titre"], 'children: dztIcone(modal, 18) }, "i")',
  'dztIcone(modal, 18)', '__dzGl("dz-nav-transfert", 18, { display: "block" })')
E(["reglages.transfert-entre-machines.exporter", "reglages.transfert.exporter"], 'children: [dztIcone("export", 16),',
  'dztIcone("export", 16)', '__dzGl("dz-action-exporter", 16, { display: "block" })')
E(["reglages.transfert-entre-machines.importer", "reglages.transfert.importer"], 'children: [dztIcone("import", 16),',
  'dztIcone("import", 16)', '__dzGl("dz-action-importer", 16, { display: "block" })')

# ═══ divers ═══════════════════════════════════════════════════════════════════════════════════════════════════
DEJA("coque.panneau-file-des-rendus-ligne-de-job.job-renommer", "littéral rename du bouton de la ligne -> dz-action-renommer (g1_saisie_cles)")
DEJA("coque.file.vide-run", "même site que coque.panneau-file-des-rendus.file-vide-run")
DEJA(["marque.favicon.dist", "marque.favicon.source", "marque.titre.emoji"],
     "frontend/dist/index.html et frontend/index.html : favicon = /api/branding/logo (dz-marque-icone-app est une IMAGE, "
     "décision utilisateur dd9e3307), titre sans 🐙 — édités directement (hors bundle)")

# ═══ S19 — orientation du chevron : dz-action-deplier pointe vers le BAS (l'ancien caretR vers la droite, caret vers
# la gauche) ; « chevron unique orienté par CSS » (lexique) — chaque rotation héritée est recalée
E([], 'size:12,style:{transform:i?"rotate(90deg)":"none",transition:"transform var(--dur-1) var(--ease)"}}),r.jsx("span",{className:"upper"',
  'transform:i?"rotate(90deg)":"none"', 'transform:i?"none":"rotate(-90deg)"')
E([], 'style:{color:"var(--ink-soft)",transform:c?"rotate(90deg)":"none",transition:"transform var(--dur-1) var(--ease)"}})]}),c&&r.jsxs(',
  'transform:c?"rotate(90deg)":"none"', 'transform:c?"none":"rotate(-90deg)"')
E([], 'iconSize:11,onClick:()=>o(!0),title:dzT("coque.rail.replier")})', 'iconSize:11,onClick:()=>o(!0),',
  'iconSize:11,style:{transform:"rotate(90deg)"},onClick:()=>o(!0),')
E([], 'title:dzT("coque.rail.deplier"),children:r.jsx(X,{name:"caretR",size:14})})', 'size:14})',
  'size:14,style:{transform:"rotate(-90deg)"}})')
