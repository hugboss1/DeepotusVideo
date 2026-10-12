# -*- coding: utf-8 -*-
# scripts/icones/g1_generer.py
"""Icônes « Deepotus Glyph », lot G1 (coque React) : réécrit les COUCHES et produit la table du maillon de queue.

Le bundle `frontend/dist/assets/index-BEOJX8L5.js` porte deux sortes de code :
  - les COUCHES rafraîchissables (montage, sonvfx, sfxstudio, vfxrack) : leur bloc /*__DZ_<TAG>_BEGIN__*/ … est, à
    l'octet, la source `frontend/patches/<x>.js` ; on les modifie dans la SOURCE, puis
    `python scripts/refresh_layer.py --layer <x> --force` les réinjecte (jamais en dur dans le bundle) ;
  - tout le reste (dont les blocs SUBS et DIALOGUE, dont la source ne reconstruit plus le bloc, et TRANSFERT, qu'aucun
    outil ne rafraîchit) : modifié par le maillon de queue `scripts/patch_bundle_dzglyph.py`, d'après la table
    `scripts/dzglyph_paires.json` écrite ici ; la source de TRANSFERT (marqueurs compris, test_transfert_bundle) reçoit
    le miroir exact du bloc livré.
  - la table garde aussi, couche par couche, les éditions faites dans les sources (positions de la source de BASE) :
    backend/tests/_i18n_l1_aide.py (avant_dzglyph, couche_avant_dzglyph) les défait pour les bancs d'avant G1, et
    appliquer_couche_g1 les rejoue pour les générateurs i18n (l1, l2, l4) qui réécrivent ces sources.
  Toute couche réécrite après la BASE (nouvelle traduction, retouche) : relancer ce générateur sur une BASE à jour.

SAISIE (positions toujours exprimées dans le bundle de la BASE, commit BASE ci-dessous = socle G0) :
  - `scripts/icones/g1_saisie_cles.json` : sites où une clé de la carte d'icônes `Sh` (« sparkle », « zap »…) est
    repointée vers la clé finale de la suite — produit une fois depuis docs/icones/suite-finale/implementation.json
    puis figé ;
  - `scripts/icones/g1_saisie.py` : le reste (glyphes, emojis, données, socle `__dzGlyphe`), écrit à la main.
Chaque entrée : ancre (unique dans le bundle de BASE), avant (unique dans l'ancre), après, ids de implementation.json.

    python scripts/icones/g1_generer.py           # écrit les couches et la table
    python scripts/icones/g1_generer.py --check   # code 1 si un des fichiers n'est pas à jour

Lecture et écriture en OCTETS (le mode texte aplatit les CRLF — mémoire du 07/09/2026).
"""
import importlib.util
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
BASE = "d4c6a2f4"                                   # socle G0 (PR #281) + traductions L3 (t143) et L5 (t145)
REL_BUNDLE = "frontend/dist/assets/index-BEOJX8L5.js"
TABLE = REPO / "scripts" / "dzglyph_paires.json"
SAISIE_CLES = REPO / "scripts" / "icones" / "g1_saisie_cles.json"
SAISIE = REPO / "scripts" / "icones" / "g1_saisie.py"
COUCHES = {"MONTAGE": "montage.js", "SONVFX": "son-vfx-montage.js", "SFXSTUDIO": "sfxstudio.js",
           "VFXRACK": "vfxrack.js",
           # t145 : TRANSFERT est devenu une couche rafraîchie (refresh_layer --layer transfert, traduction L5) ; sa
           # source porte ses propres lignes de marqueurs (le cœur est entre elles, voir coeur())
           "TRANSFERT": "transfert.js"}
NOMS = {"MONTAGE": "montage", "SONVFX": "sonvfx", "SFXSTUDIO": "sfxstudio", "VFXRACK": "vfxrack",
        "TRANSFERT": "transfert"}
MIROIRS = {}                                        # (TRANSFERT en était un avant t145)
# Retouches FONCTIONNELLES d'une couche posées APRÈS G1 par un générateur i18n (sa saisie les porte) : rejouées ici
# par texte exact sur la source de BASE, APRÈS les éditions G1 ; elles gardent la LONGUEUR de la couche (les positions
# de la table, que les générateurs i18n rejouent sur leur sortie, ne bougent donc pas). Toujours en LF ici.
RETOUCHES = {
    # t183 : le Duel nomme son challenger d'après `tous` (saisie scripts/i18n_l3/montage_i.py, longueur conservée)
    "MONTAGE": [('function dzDuelLabel(mm,id){var m=((mm&&mm.models)||[]).find(function(z){return z.id===id});return m?m.label:id}', 'function dzDuelLabel(mm,id){var m=((mm&&mm.tous)||[]).find(function(zz){return zz.id===id});return m?m.label:id}')],
    # t183 (G1 génération IA, 11/10/2026) : le rail Son & VFX sans prix écrit en dur, le SFX généré n'est plus
    # « gratuit » (saisie scripts/i18n_l4/son_a.py, commentaire réécrit à longueur compensée)
    "SONVFX": [("/* Le prix affiché est celui de CE QUE FAIT le bouton. « VFX particules » est\n   passé de « $0.06 » à « gratuit » parce que la génération est désormais une\n   simulation locale, et « SFX » à « gratuit » parce que 606 bruitages CC0 sont\n   livrés : la facturation ElevenLabs ne concerne plus que la génération sur\n   description. Un tarif qui survit au câblage est un mensonge d'interface. */", '/* t183 (11/10/2026) : AUCUN prix écrit en dur dans ce rail. Musique et voix off se\n   paient au modèle choisi (leurs cartes affichent le prix lu au serveur) ; le SFX\n   GÉNÉRÉ se paie en crédits ElevenLabs — seuls les 606 bruitages CC0 livrés sont\n   gratuits ; VFX particules et post-traitement sont locaux. Un tarif écrit ici\n   ment dès que le câblage change. */'), (' {id:"music",name:dzT("son.gen.musique"),desc:dzT("son.gen.musique_desc"),price:"~$0.10",c:"--c-audio"},\n {id:"sfx",name:"SFX",desc:dzT("son.gen.sfx_desc"),price:dzT("son.commun.gratuit"),c:"--c-audio"},\n {id:"voiceover",name:dzT("son.gen.voix_off"),desc:dzT("son.gen.voix_off_desc"),price:"$0.08",c:"--c-audio"},\n {id:"vfx",name:dzT("son.gen.vfx"),desc:dzT("son.gen.vfx_desc"),price:dzT("son.commun.gratuit"),c:"--c-3d"},\n {id:"post",name:dzT("son.gen.post"),desc:"Grain, glow, aberration, transitions",price:dzT("son.commun.gratuit"),c:"--c-3d"}];', ' {id:"music",name:dzT("son.gen.musique"),desc:dzT("son.gen.musique_desc"),price:dzT("son.gen.prix_modele"),c:"--c-audio"},\n {id:"sfx",name:"SFX",desc:dzT("son.gen.sfx_desc"),price:dzT("son.gen.prix_sfx"),c:"--c-audio"},\n {id:"voiceover",name:dzT("son.gen.voix_off"),desc:dzT("son.gen.voix_off_desc"),price:dzT("son.gen.prix_modele"),c:"--c-audio"},\n {id:"vfx",name:dzT("son.gen.vfx"),desc:dzT("son.gen.vfx_desc"),price:dzT("son.gen.local"),c:"--c-3d"},\n {id:"post",name:dzT("son.gen.post"),desc:"Grain, glow, aberration, transitions",price:dzT("son.gen.local"),c:"--c-3d"}];'), ('r.jsx("span",{className:"svm-genprice",\n          title:dzT("son.sfx.prix_aide"),children:"$0.03"})', 'r.jsx(svmSfx().Choix||"span",\n                                                    {dur:sfxDur,n:2})'), ('        return d2&&d2.Drawer?r.jsx(d2.Drawer,{open:sfxOn,\n          onClose:function(){setSfxOn(!1)},\n          onInsert:sfxInsert,playheadSec:ph,defaultTab:"sfx"}):null})(),', '        return d2&&d2.Drawer?r.jsx(d2.Drawer,{open:sfxOn,\n  onClose:function(){setSfxOn(!1)},\n         onInsert:sfxInsert,playheadSec:ph,clip:sel,defaultTab:"sfx"}):null})(),'), ('/* le prix affiché d\'un modèle de musique : par génération, ou à la seconde (ACE-Step) sur la durée choisie */\nfunction svmMusicPrice(v,dur){\n  return v.usd_unit==="s"?"~$"+(v.usd*dur).toFixed(3)+" · "+dur+" s":"~$"+v.usd.toFixed(2)}', '/* t187 : prix d\'un modèle, à 0 $ « à mesurer » */\nfunction svmMusicPrice(v,dur,ly){var u=ly&&v.usd_lyrics!=null&&ly.replace(/\\[[^\\[\\]\\n]{1,24}\\]/g,"").trim()?v.usd_lyrics:v.usd,c=v.usd_unit==="s"?u*dur:v.usd_unit==="min"?u*Math.ceil(dur/60):u;\n  return !(u>0)?dzT("ia.prix.a_mesurer"):"~$"+c.toFixed(v.usd_unit==="s"||Math.round(c*1000)%10?3:2)+(v.usd_unit==="s"||v.usd_unit==="min"?" · "+dur+" s":"")}'), ("/* T102 : les paroles se montrent quand le modèle les prend ET que la voix est\n     demandée — ou TOUJOURS si le modèle n'a pas d'interrupteur instrumental\n     (Music 2.0 : paroles obligatoires ; avant, l'état « instrumental » par\n     défaut les cachait à jamais) */", '/* T102 : paroles si le modèle les prend et voix demandée \n\n\n   */'), ('children:svmMusicPrice(v,v.duration?Math.min(v.duration[1],Math.max(v.duration[0],dur)):dur)})]}),', 'children:svmMusicPrice(v,v.duration?Math.min(v.duration[1],Math.max(v.duration[0],dur)):dur,model===v.id&&showLyr?lyrics:"")})]}),')],
    # t186 (G4 génération IA, 12/10/2026) : la rangée « Sujet » du rack choisit son modèle dans le registre du
    # détourage vidéo (saisie scripts/i18n_l4/vfx.py) — retouches de VfxStack à longueur égale (commentaire de tête
    # compensé), code neuf APRÈS la dernière édition G1 (avant vfxPatch1)
    "VFXRACK": [("/* ── T103 (D2b) : la rangée « Sujet » — détourer le plan (BiRefNet, fal) ──\n     PAYANT et au prix NON AFFICHÉ par fal : 1er clic = devis du backend (la\n     ligne dit « à mesurer »), 2e clic = tir. Le résultat part au Montage par\n     `dz-matte` {id, matte} : l'hôte le pose sur le plan, annulable. */", "/* ── T103 (D2b) + t186 (G4) : la rangée « Sujet » — détourer le plan ─────────────────────────────────────────────\n     PAYANT : 1er clic = devis, 2e clic = tir ; le modèle vient du registre\n     (vfxMatte*, fin de couche). Résultat au Montage par `dz-matte`. */"), ("body:JSON.stringify({kind:\"matte\",duration_s:vfxN(clip.end,0)-vfxN(clip.start,0)})", "body:JSON.stringify(vfxMatteDevis(vfxN(clip.end,0)-vfxN(clip.start,0)))"), ("if(VFX_MATTE.busy||!clip||!clip.src||!clip.src.job_id)return;", "if(VFX_MATTE.busy||!clip||!clip.src||!clip.src.job_id)return;if(vfxMatteSansSujet(fireNote))return;"), ("vfxPost(\"/api/matte\",{job_id:clip.src.job_id,model:VFX_MATTE.model})", "vfxPost(\"/api/matte\",vfxMatteCorps(clip.src.job_id))"), ("onChange:function(e){VFX_MATTE.model=e.target.value;VFX_MATTE.arm=null;", "onChange:function(e){vfxMatteChoix(e.target.value);VFX_MATTE.arm=null;"), ("children:mods.map(function(o){return r.jsx(\"option\",{value:o.id,children:o.label},o.id)})}):null,", "children:mods.map(function(o){return r.jsx(\"option\",{value:o.id,children:vfxMatteLbl(o)},o.id)})}):null,vfxMatteSujetRow(mtick),"), ("/* petit utilitaire : {clé: valeur} calculé", "/* ── t186 (G4) : le modèle du détourage d'un plan, pris dans le registre unique ──\n   GET /api/matte-models sert en tête les trois anciennes clés (BiRefNet v2 vidéo :\n   general, matting, portrait) puis les modèles vidéo du registre (Bria VRMBG 3.0, VEED\n   rapide, Pixelcut vidéo, SAM 3.1), chacun avec usd, unite, prompt, dispo, cle. Le\n   libellé porte le prix (règle unique prixUsd de DzModelesIA, sinon dzPrixUsd du maillon\n   encartsia) et, sans clé, la mention « clé X à ajouter dans Réglages » : l'option reste\n   CHOISISSABLE, POST /api/matte refuse en 503 avant toute dépense. SAM 3.1 exige le sujet\n   à garder (champ sous le sélecteur, refus avant l'envoi s'il est vide). Le choix est\n   mémorisé (localStorage dz_detour_vfx) ; défaut historique : general. Ces fonctions\n   vivent ICI, après la dernière édition G1 de la couche : la table dzglyph_paires.json\n   repère les éditions par position (les retouches plus haut sont à longueur égale). */\nvar VFX_DETOUR_LS=\"dz_detour_vfx\";\ntry{VFX_MATTE.model=localStorage.getItem(VFX_DETOUR_LS)||VFX_MATTE.model}catch(_e){}\nVFX_MATTE.sujet=\"\";\nfunction vfxMatteMod(id){var l=VFX_MATTE.models||[];for(var i=0;i<l.length;i++)if(l[i].id===id)return l[i];return null}\n/* un modèle mémorisé que le serveur ne sert plus retombe sur la première option (general) */\nfunction vfxMatteValide(){var l=VFX_MATTE.models||[];if(l.length&&!vfxMatteMod(VFX_MATTE.model))VFX_MATTE.model=l[0].id}\nfunction vfxMattePrixUsd(usd,unite){\n  var f=(window.DzModelesIA&&window.DzModelesIA.prixUsd)||(typeof dzPrixUsd===\"function\"?dzPrixUsd:null);\n  return f?f(usd,unite):\"\"}\nfunction vfxMatteNom(o){var k=\"detour.modele.\"+String(o.id||\"\").replace(/-/g,\"_\");\n  return window.DZ_I18N&&window.DZ_I18N[k]?dzT(k):o.label}\nfunction vfxMatteLbl(o){var p=vfxMattePrixUsd(o.usd,o.unite);\n  return vfxMatteNom(o)+\" · \"+(p||dzT(\"ia.prix.a_mesurer\"))+(o.dispo===!1&&o.cle?\" · \"+dzT(\"ia.cle.a_ajouter\",{cle:o.cle}):\"\")}\nfunction vfxMatteChoix(v){VFX_MATTE.model=v;try{localStorage.setItem(VFX_DETOUR_LS,v)}catch(_e){}}\nfunction vfxMatteSujetReq(){var m=vfxMatteMod(VFX_MATTE.model);return!!(m&&m.prompt)}\nfunction vfxMatteSansSujet(note){vfxMatteValide();\n  if(!vfxMatteSujetReq()||String(VFX_MATTE.sujet||\"\").trim())return!1;\n  note(dzT(\"detour.champ.sujet_requis\"));return!0}\n/* le devis : BiRefNet (anciennes clés, birefnet-v2-video) garde le kind « matte » d'avant ; les autres : « detourage »\n   — copie JS de la règle unique du serveur, matte_service.op_devis (/matte et décor Avatar) */\nfunction vfxMatteDevis(dur){var m=vfxMatteMod(VFX_MATTE.model),reg=(m&&m.registre)||VFX_MATTE.model;\n  return reg===\"birefnet-v2-video\"||reg===\"general\"||reg===\"matting\"||reg===\"portrait\"?{kind:\"matte\",duration_s:dur}:{kind:\"detourage\",modele:reg,secondes:dur}}\nfunction vfxMatteCorps(job){var c={job_id:job,model:VFX_MATTE.model};\n  if(vfxMatteSujetReq())c.sujet=String(VFX_MATTE.sujet||\"\").trim();return c}\nfunction vfxMatteSujetRow(tick){\n  vfxMatteValide();\n  if(!vfxMatteSujetReq())return null;\n  return r.jsx(\"input\",{className:\"vfx-sel vfx-msujet\",type:\"text\",value:VFX_MATTE.sujet||\"\",\"data-dzdetsujet\":\"1\",\n    placeholder:dzT(\"detour.champ.sujet\"),\"aria-label\":dzT(\"detour.champ.sujet\"),\n    onChange:function(e){VFX_MATTE.sujet=e.target.value;VFX_MATTE.arm=null;tick(function(n){return n+1})}})}\n\n/* petit utilitaire : {clé: valeur} calculé")],
    # t187 (G5 génération IA, 12/10/2026) : le modèle du bruitage et « Depuis la vidéo » (saisies
    # scripts/i18n_l4/*.py) — retouches à longueur égale avant la dernière édition G1, code neuf en fin de couche
    "SFXSTUDIO": [('cost==null?dzT("sfx.gen.cout_auto"):dzT("sfx.gen.cout",{n:cost})', 'cost==null?svxSfxCout(gDur,gVar,1):svxSfxCout(gDur,gVar,0)      '), ('/* ── POST /api/audio/sfx — génération ElevenLabs ─────────────────────────── */\nfunction svxGenSfx(o){\n  o=o||{};\n  var body={prompt:String(o.prompt||"").slice(0,450)};\n  if(o.duration_s!=null)body.duration_s=svxClamp(o.duration_s,0.5,22);\n  if(o.prompt_influence!=null)body.prompt_influence=svxClamp(o.prompt_influence,0,1);\n  body.variations=Math.round(svxClamp(o.variations!=null?o.variations:1,1,4));', '/* ── POST /api/audio/sfx — modèle choisi (t187) ──────── */\nfunction svxGenSfx(o){\n  o=o||{};\n  var body={prompt:String(o.prompt||"").slice(0,450)};\n  if(o.duration_s!=null)body.duration_s=svxClamp(o.duration_s,0.5,22);\n  if(o.prompt_influence!=null)body.prompt_influence=svxClamp(o.prompt_influence,0,1);\n  body.variations=Math.round(svxClamp(o.variations!=null?o.variations:1,1,4));svxSfxCorps(body,o);'), ('      r.jsx("div",{className:"svx-gex",children:SVX_EXAMPLES.map(function(ex){', '      svxSfxR(gAuto?0:gDur,gVar,props.clip,gPrompt,refresh,fireNote),r.jsx("div",{className:"svx-gex",children:SVX_EXAMPLES.map(function(ex){'), ('  /* T101 (plan-son-vfx T5) : `inline` = monté dans la page (Bibliothèque → Audio), toujours ouvert, sans « Fermer » */', '  /* T101 : `inline` = dans la page, sans « Fermer »  */'), ('/* ── export contrat ──────────────────────────────────────────────────────── */\nwindow.DzSfx={ready:!0,Drawer:SvxDrawer,Rack:SvxRack,Meter:SvxMeter,\n  genSfx:svxGenSfx,fxPresets:svxFxPresets};', '/* ── t187 (G5, génération IA enrichie) : le MODÈLE du bruitage, texte ET vidéo ──────────\n   Le registre des bruitages (backend sfx_service.SFX_MODELS) est servi par GET\n   /api/ia/catalogue (natures sfx_texte et sfx_video) : chaque option porte son prix (lu au\n   catalogue) et, sans clé, la mention « clé X à ajouter dans Réglages » — elle reste\n   CHOISISSABLE (jamais disabled) : la route refuse en 503 avant toute dépense. Le choix est\n   commun au tiroir Sons et à la carte SFX de Son & VFX (localStorage dz_sfx_modele et\n   dz_sfx_modele_video ; vide = le défaut du serveur : ElevenLabs direct, ou son jumeau via\n   fal sans clé ElevenLabs). Le PRIX annoncé est le devis du SERVEUR — POST /api/cost/estimate\n   (kind « sfx ») pour une description, POST /api/audio/sfx-video avec devis:true pour un\n   clip — le même chiffre que la garde des plafonds, avant ET après le clic. « Depuis la\n   vidéo » (clip vidéo sélectionné dans la timeline) : 1er clic = arme, 2e clic = tir.\n   Ces fonctions vivent APRÈS la dernière édition G1 de la couche (table dzglyph_paires.json :\n   éditions repérées par position) ; un useReducer (et non useState) rafraîchit l\'affichage. */\nvar SVX_SFXM={texte:"",video:"",voix:!1,cat:{},prix:{},subs:[],arm:null,busy:!1};\nvar SVX_SFXM_LS="dz_sfx_modele",SVX_SFXM_LSV="dz_sfx_modele_video";\ntry{SVX_SFXM.texte=localStorage.getItem(SVX_SFXM_LS)||"";SVX_SFXM.video=localStorage.getItem(SVX_SFXM_LSV)||""}catch(_e){}\n/* les libellés du catalogue arrivent en français : ceux qui portent un suffixe à traduire passent par dzT */\nvar SVX_SFXM_NOMS={"sonilo-video":dzT("son.sfx.libelle.sonilo_video"),\n  "mirelo-video":dzT("son.sfx.libelle.mirelo_video"),"kling-v2a":dzT("son.sfx.libelle.kling_v2a")};\nfunction svxSfxPing(){SVX_SFXM.subs.slice().forEach(function(f){try{f()}catch(_e){}})}\nfunction svxSfxAbonne(t){\n  x.useEffect(function(){SVX_SFXM.subs.push(t);\n    return function(){var i=SVX_SFXM.subs.indexOf(t);if(i>=0)SVX_SFXM.subs.splice(i,1)}},[])}\nfunction svxSfxCat(nat){\n  var c=SVX_SFXM.cat[nat];if(c)return c.l;\n  SVX_SFXM.cat[nat]={l:null};\n  fetch("/api/ia/catalogue?nature="+nat).then(function(res){return res.ok?res.json():null})\n    .then(function(d){SVX_SFXM.cat[nat]={l:(d&&d.modeles)||[]};svxSfxPing()})\n    .catch(function(){SVX_SFXM.cat[nat]={l:[]};svxSfxPing()});\n  return null}\nfunction svxSfxMod(nat,id){var l=svxSfxCat(nat)||[];\n  for(var i=0;i<l.length;i++)if(l[i].id===id)return l[i];return null}\n/* le modèle EFFECTIF : le choix mémorisé s\'il est encore servi, sinon le défaut du serveur */\nfunction svxSfxEff(nat){\n  var l=svxSfxCat(nat)||[],v=nat==="sfx_video"?SVX_SFXM.video:SVX_SFXM.texte;\n  if(v&&svxSfxMod(nat,v))return v;\n  if(nat==="sfx_video")return l.length?l[0].id:"";\n  var d=svxSfxMod(nat,"elevenlabs-direct"),f=svxSfxMod(nat,"elevenlabs-v2-fal");\n  return d&&d.dispo===!1&&f&&f.dispo!==!1?f.id:"elevenlabs-direct"}\nfunction svxSfxUsd(m){var v=Number(m&&m.usd);\n  if(!(v>0)||!isFinite(v))return dzT("ia.prix.a_mesurer");\n  return "$"+String(Math.round(v*10000)/10000)+(m.unite==="s"?"/s":m.unite==="video"?" / "+dzT("son.sfx.unite_video"):"")}\nfunction svxSfxTexte(m){\n  return (SVX_SFXM_NOMS[m.id]||m.label||m.id)+" · "+svxSfxUsd(m)\n    +(m.dispo===!1&&m.cle?" · "+dzT("ia.cle.a_ajouter",{cle:m.cle}):"")}\nfunction svxSfxChoisir(nat,v){\n  if(nat==="sfx_video")SVX_SFXM.video=v;else SVX_SFXM.texte=v;\n  SVX_SFXM.arm=null;\n  try{localStorage.setItem(nat==="sfx_video"?SVX_SFXM_LSV:SVX_SFXM_LS,v)}catch(_e){}\n  svxSfxPing()}\n/* le corps de POST /api/audio/sfx reçoit le modèle CHOISI (rien : le défaut du serveur) */\nfunction svxSfxCorps(body,o){\n  var m=o&&o.modele!=null?String(o.modele):SVX_SFXM.texte,c=SVX_SFXM.cat.sfx_texte;\n  if(m&&(!c||!c.l||svxSfxMod("sfx_texte",m)))body.modele=m}\n/* le devis du serveur, mis en cache par corps : undefined pendant la lecture, null si refusé */\nfunction svxSfxDevis(url,body){\n  var k=url+" "+JSON.stringify(body),e=SVX_SFXM.prix[k];\n  if(e)return e.usd;\n  SVX_SFXM.prix[k]={usd:void 0};\n  fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})\n    .then(function(res){return res.ok?res.json():null})\n    .then(function(d){var u=d&&(typeof d.total_usd==="number"?d.total_usd:typeof d.usd==="number"?d.usd:null);\n      SVX_SFXM.prix[k]={usd:u==null?null:u};svxSfxPing()})\n    .catch(function(){SVX_SFXM.prix[k]={usd:null};svxSfxPing()});\n  return void 0}\nfunction svxSfxPrixTxt(usd){\n  return usd===void 0?dzT("sfx.action.prix_attente"):usd==null?"—"\n    :usd>0?"~$"+usd.toFixed(usd<0.1?3:2):dzT("ia.prix.a_mesurer")}\n/* l\'ancienne estimation en crédits ne parle que pour ElevenLabs direct ; un modèle fal a son prix à côté du sélecteur */\nfunction svxSfxCout(dur,n,auto){\n  if(svxSfxEff("sfx_texte")!=="elevenlabs-direct")return "";\n  return auto?dzT("sfx.gen.cout_auto"):dzT("sfx.gen.cout",{n:Math.round(40*dur)*n})}\n/* le sélecteur sfx_texte + SON prix (devis du serveur pour cette durée et ces variations) */\nfunction SvxSfxChoix(props){\n  var t=x.useReducer(function(n){return n+1},0)[1];\n  svxSfxAbonne(t);\n  var l=svxSfxCat("sfx_texte"),v=svxSfxEff("sfx_texte"),d=Number(props.dur)>0?Number(props.dur):null;\n  var usd=l?svxSfxDevis("/api/cost/estimate",{kind:"sfx",modele:v,secondes:d,\n    echantillons:Math.max(1,Math.min(4,Math.round(Number(props.n)||1)))}):void 0;\n  return r.jsxs("span",{className:"svx-sfxm","data-dzsfxm":"texte",children:[\n    r.jsx("select",{className:"svx-select svx-sfxmsel",value:v,\n      "aria-label":dzT("son.sfx.modele"),title:dzT("son.sfx.modele"),\n      onChange:function(e){svxSfxChoisir("sfx_texte",e.target.value)},\n      children:(l||[]).map(function(m){return r.jsx("option",{value:m.id,children:svxSfxTexte(m)},m.id)})}),\n    r.jsx("span",{className:"svm-genprice svx-sfxmprix",title:dzT("son.sfx.prix_modele"),\n      children:svxSfxPrixTxt(usd)})]})}\n/* « Depuis la vidéo » : le clip VIDÉO sélectionné dans la timeline (job rendu) part à un modèle sfx_video */\nfunction svxSfxClipVideo(c){return !!(c&&c.src&&c.src.job_id&&!/^a/.test(String(c.tr||"")))}\nfunction SvxSfxVideo(props){\n  var t=x.useReducer(function(n){return n+1},0)[1];\n  svxSfxAbonne(t);\n  var c=props.clip,l=svxSfxCat("sfx_video"),v=svxSfxEff("sfx_video"),m=svxSfxMod("sfx_video",v);\n  var corps={clip_id:String(c.src.job_id),modele:v};\n  if(m&&m.voix)corps.garder_voix=!!SVX_SFXM.voix;\n  var usd=l&&v?svxSfxDevis("/api/audio/sfx-video",Object.assign({devis:!0},corps)):void 0;\n  var p=String(props.prompt||"").trim(),cle=JSON.stringify(corps)+"|"+p,armed=SVX_SFXM.arm===cle;\n  function go(){\n    if(SVX_SFXM.busy||!v)return;\n    if(m&&m.prompt&&!p){props.note(dzT("son.sfx.decrire_video"));return}\n    if(!armed){SVX_SFXM.arm=cle;t();return}\n    SVX_SFXM.arm=null;SVX_SFXM.busy=!0;t();\n    fetch("/api/audio/sfx-video",{method:"POST",headers:{"Content-Type":"application/json"},\n      body:JSON.stringify(Object.assign({prompt:p},corps))})\n      .then(function(res){return res.json().catch(function(){return {}})\n        .then(function(d){if(!res.ok)throw new Error(d.detail&&d.detail.message||d.detail||dzT("sfx.action.echec_code",{code:res.status}));return d})})\n      .then(function(d){SVX_SFXM.busy=!1;t();if(props.refresh)props.refresh();\n        var it=(d.items||[])[0];\n        props.note(dzT("son.sfx.video_fait",{nom:it?it.filename:"—",prix:svxSfxPrixTxt(typeof d.usd==="number"?d.usd:null)})\n          +((d.videos||[]).length?" "+dzT("son.sfx.video_sonorisee"):""))})\n      .catch(function(e){SVX_SFXM.busy=!1;t();props.note(String(e&&e.message||e))})}\n  return r.jsxs("div",{className:"svx-sfxv","data-dzsfxv":"1",children:[\n    r.jsx(SvmLabel,{children:dzT("son.sfx.depuis_video")}),\n    r.jsx("div",{className:"svx-note",children:dzT("son.sfx.video_aide",{clip:c.label||c.id||""})}),\n    r.jsxs("div",{className:"svx-grow",children:[\n      r.jsx("select",{className:"svx-select svx-sfxmsel",value:v,"data-dzsfxm":"video",\n        "aria-label":dzT("son.sfx.modele"),title:dzT("son.sfx.modele"),\n        onChange:function(e){svxSfxChoisir("sfx_video",e.target.value)},\n        children:(l||[]).map(function(o){return r.jsx("option",{value:o.id,children:svxSfxTexte(o)},o.id)})}),\n      m&&m.voix?r.jsxs("label",{className:"svx-sfxvoix",children:[\n        r.jsx("input",{type:"checkbox",checked:!!SVX_SFXM.voix,"data-dzsfxvoix":"1",\n          onChange:function(e){SVX_SFXM.voix=!!e.target.checked;SVX_SFXM.arm=null;t()}}),\n        dzT("son.sfx.garder_voix")]}):null]}),\n    r.jsx("button",{className:"svm-goldbtn svx-gold"+(armed?" svx-armed":""),"data-dzsfxvgo":"1",\n      "data-busy":SVX_SFXM.busy?"":void 0,disabled:!!SVX_SFXM.busy,\n      title:armed?dzT("sfx.action.armee",{prix:svxSfxPrixTxt(usd)}):dzT("son.sfx.prix_modele"),\n      onClick:go,children:SVX_SFXM.busy?dzT("sfx.gen.en_cours")\n        :armed?svxSfxPrixTxt(usd)+" — "+dzT("son.sfx.confirmer")\n        :dzT("son.sfx.depuis_video")+" · "+svxSfxPrixTxt(usd)})]})}\n/* la rangée « Modèle » de l\'onglet Générer du tiroir, puis le bruitage du clip vidéo sélectionné (Montage) ;\n   `clip` undefined = tiroir hors Montage (Bibliothèque) : rien ; null ou non vidéo : l\'indication */\nfunction svxSfxR(dur,n,clip,prompt,refresh,note){\n  return r.jsxs(r.Fragment,{children:[\n    r.jsxs("div",{className:"svx-grow svx-sfxmrow",children:[\n      r.jsx("span",{className:"svx-glabel",children:dzT("son.sfx.modele")}),\n      r.jsx(SvxSfxChoix,{dur:dur,n:n})]}),\n    clip===void 0?null:svxSfxClipVideo(clip)\n      ?r.jsx(SvxSfxVideo,{clip:clip,prompt:prompt,refresh:refresh,note:note})\n      :r.jsx("div",{className:"svx-note svx-sfxvnone",children:dzT("son.sfx.video_sans_clip")})]})}\n\n/* ── export contrat ──────────────────────────────────────────────────────── */\nwindow.DzSfx={ready:!0,Drawer:SvxDrawer,Rack:SvxRack,Meter:SvxMeter,\n  genSfx:svxGenSfx,fxPresets:svxFxPresets,Choix:SvxSfxChoix};')],
}


def coeur(src: str, tag: str) -> tuple:
    """(début, fin) du cœur du bloc `tag` dans sa source : entre ses lignes de marqueurs s'il en porte (transfert.js),
    sinon la source entière ; fins de ligne des bords exclues."""
    b, e = f"/*__DZ_{tag}_BEGIN__*/", f"/*__DZ_{tag}_END__*/"
    i, j = (src.index(b) + len(b), src.index(e)) if b in src else (0, len(src))
    while i < j and src[i] in "\r\n﻿":
        i += 1
    while j > i and src[j - 1] in "\r\n":
        j -= 1
    return i, j


def git_show(rel: str) -> bytes:
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{BASE}:{rel}"], capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"[g1] git show {BASE}:{rel} a échoué : {r.stderr.decode('utf-8', 'replace')}")
    # le dépôt garde des LF (core.autocrlf=true) ; sur disque, bundle et couches sont en CRLF : on travaille en CRLF
    return r.stdout.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


def saisie() -> list:
    cles = json.loads(SAISIE_CLES.read_bytes().decode("utf-8"))["sites"]
    spec = importlib.util.spec_from_file_location("g1_saisie", SAISIE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [dict(e, source="cles") for e in cles] + [dict(e, source="main") for e in mod.EDITIONS]


def resoudre(base: str, E: list) -> list:
    """Chaque édition -> position de `avant` dans le bundle de base ; refuse ancre non unique et chevauchements."""
    out, err = [], []
    for e in E:
        n = base.count(e["ancre"])
        if n != 1:
            err.append(f"ancre x{n} (attendu 1) {e['ids'][:2]} : {e['ancre'][:90]!r}")
            continue
        if e["ancre"].count(e["avant"]) != 1:
            err.append(f"« avant » x{e['ancre'].count(e['avant'])} dans l'ancre {e['ids'][:2]} : {e['avant']!r}")
            continue
        p = base.find(e["ancre"]) + e["ancre"].find(e["avant"])
        out.append(dict(e, pos=p))
    out.sort(key=lambda e: e["pos"])
    for a, b in zip(out, out[1:]):
        if a["pos"] + len(a["avant"]) > b["pos"]:
            err.append(f"éditions qui se chevauchent : {a['ids'][:1]} ({a['source']}) / {b['ids'][:1]} ({b['source']})")
    if err:
        raise SystemExit("[g1] saisie refusée :\n  " + "\n  ".join(err))
    return out


def blocs(base: str) -> dict:
    """TAG -> (début du contenu, fin) du bloc de chaque couche rafraîchissable, bords CRLF exclus."""
    d = {}
    for tag in COUCHES:
        b, e = f"/*__DZ_{tag}_BEGIN__*/", f"/*__DZ_{tag}_END__*/"
        i, j = base.index(b) + len(b), base.index(e)
        while base[i] in "\r\n":
            i += 1
        while base[j - 1] in "\r\n":
            j -= 1
        d[tag] = (i, j)
    return d


def appliquer_positions(texte: str, eds: list, decal: int = 0) -> str:
    for e in sorted(eds, key=lambda e: -e["pos"]):
        p = e["pos"] - decal
        if texte[p:p + len(e["avant"])] != e["avant"]:
            raise SystemExit(f"[g1] « avant » introuvable à sa position {e['ids'][:1]} : {e['avant']!r}")
        texte = texte[:p] + e["apres"] + texte[p + len(e["avant"]):]
    return texte


def generer() -> tuple:
    base_raw = git_show(REL_BUNDLE)
    base = base_raw.decode("utf-8")
    E = resoudre(base, saisie())
    B = blocs(base)
    sources, dans_couche = {}, set()
    for tag, (i, j) in B.items():
        eds = [e for e in E if i <= e["pos"] < j]
        for e in eds:
            if e["pos"] + len(e["avant"]) > j:
                raise SystemExit(f"[g1] édition à cheval sur le bord du bloc {tag} : {e['ids'][:1]}")
            dans_couche.add(id(e))
        src = git_show("frontend/patches/" + COUCHES[tag]).decode("utf-8")
        c0, c1 = coeur(src, tag)
        if src[c0:c1] != base[i:j]:
            raise SystemExit(f"[g1] la source de base de {tag} ne reconstruit pas son bloc : couche à adopter d'abord")
        sources[tag] = appliquer_positions(src, eds, decal=i - c0)
        for av, ap in RETOUCHES.get(tag, ()):
            t = sources[tag]
            nl = "\r\n" if "\r\n" in t else "\n"
            av, ap = av.replace("\n", nl), ap.replace("\n", nl)
            if t.count(av) != 1:
                raise SystemExit(f"[g1] retouche de {tag} introuvable (x{t.count(av)}) : {av[:60]!r}")
            sources[tag] = t.replace(av, ap)
    # le bundle intermédiaire = base + couches rafraîchies (même chemin que refresh_layer)
    inter = base
    for tag, (i, j) in sorted(B.items(), key=lambda kv: -kv[1][0]):
        inter = inter[:i] + _coeur_txt(sources[tag], tag) + inter[j:]
    # éditions hors couches, appliquées dans l'ordre sur le texte courant, ancre minimale unique
    reste = [e for e in E if id(e) not in dans_couche]
    t = inter

    # décalage des positions de base vers le bundle intermédiaire
    def vers_inter(p):
        d = 0
        for tag, (i, j) in B.items():
            if j <= p:
                d += len(_coeur_txt(sources[tag], tag)) - (j - i)
        return p + d
    paires = []
    decal = 0
    for e in reste:
        p = vers_inter(e["pos"]) + decal
        if t[p:p + len(e["avant"])] != e["avant"]:
            raise SystemExit(f"[g1] position perdue {e['ids'][:1]}")
        # ancre unique AVANT, remplacement unique APRÈS : la table se défait exactement, paire par paire à rebours
        g = d = 0
        while True:
            a, b = max(0, p - g), min(len(t), p + len(e["avant"]) + d)
            anc = t[a:b]
            rem = t[a:p] + e["apres"] + t[p + len(e["avant"]):b]
            t2 = t[:a] + rem + t[b:]
            if t.count(anc) == 1 and t2.count(rem) == 1:
                break
            g += 8
            d += 8
        t = t2
        decal += len(e["apres"]) - len(e["avant"])
        paires.append({"ancre": anc, "remplace": rem, "ids": e["ids"]})
    # les éditions des couches, positions dans la SOURCE de base (CRLF) : de quoi les défaire (bancs, avant_dzglyph)
    # « coeurs » : où commence le cœur du bloc dans la source (transfert.js porte ses lignes de marqueurs) — un banc
    # qui ne tient que le cœur (bloc du bundle) décale les positions d'autant
    couches, coeurs = {}, {}
    for tag, (i, j) in B.items():
        src = git_show("frontend/patches/" + COUCHES[tag]).decode("utf-8")
        c0 = coeur(src, tag)[0]
        coeurs[NOMS[tag]] = c0
        couches[NOMS[tag]] = [{"pos": e["pos"] - i + c0, "avant": e["avant"], "apres": e["apres"], "ids": e["ids"]}
                              for e in E if i <= e["pos"] < j]
    table = {"base": BASE, "n_editions": len(E), "n_couches": len(E) - len(reste), "paires": paires,
             "couches": couches, "coeurs": coeurs}
    # réversibilité exacte (bancs : avant_dzglyph) — défaire à rebours rend le bundle intermédiaire à l'octet
    r = t
    for pr in reversed(paires):
        if r.count(pr["remplace"]) != 1:
            raise SystemExit(f"[g1] table non réversible : {pr['ids'][:1]}")
        r = r.replace(pr["remplace"], pr["ancre"], 1)
    if r != inter:
        raise SystemExit("[g1] table non réversible : le bundle intermédiaire n'est pas retrouvé")
    return sources, table, t


def _coeur_txt(src: str, tag: str) -> str:
    i, j = coeur(src, tag)
    return src[i:j]


def appliquer_bloc_g1(texte: str) -> str:
    """t145 : la source transfert.js (marqueurs compris) d'avant G1 -> avec G1 (pour i18n_l5_generer)."""
    return appliquer_couche_g1(texte, "transfert")


def appliquer_couche_g1(texte: str, cible: str) -> str:
    """La couche `cible` (montage, sonvfx, sfxstudio, vfxrack — ou son nom de fichier) d'avant G1 -> avec les icônes
    G1, d'après la table consignée (sans relire la saisie). Pour les générateurs i18n (l1, l2, l4), qui réécrivent
    ces sources : leur sortie porte donc aussi G1. Mêmes fins de ligne en sortie qu'en entrée."""
    nom = {"montage.js": "montage", "son-vfx-montage.js": "sonvfx", "sfxstudio.js": "sfxstudio",
           "vfxrack.js": "vfxrack", "transfert.js": "transfert", "TRANSFERT": "transfert"}.get(cible, cible)
    if not TABLE.is_file():
        return texte
    subs = json.loads(TABLE.read_bytes().decode("utf-8")).get("couches", {}).get(nom, [])
    crlf = "\r\n" in texte
    s = texte if crlf else texte.replace("\n", "\r\n")
    for e in sorted(subs, key=lambda x: -x["pos"]):
        if s[e["pos"]:e["pos"] + len(e["avant"])] != e["avant"]:
            raise SystemExit(f"[g1] couche {nom} : « avant » absent de sa place {e['ids'][:1]} — régénérer G1 "
                             "(scripts/icones/g1_generer.py) sur la nouvelle base")
        s = s[:e["pos"]] + e["apres"] + s[e["pos"] + len(e["avant"]):]
    return s if crlf else s.replace("\r\n", "\n")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    check = "--check" in sys.argv
    sources, table, final = generer()
    ecarts = []
    # bloc TRANSFERT : sa source (marqueurs compris) EST le bloc du bundle (test_transfert_bundle) mais aucun outil ne
    # le rafraîchit — le maillon l'édite dans le bundle, et la source en reçoit le miroir exact
    for tag, nom in MIROIRS.items():
        b, e = f"/*__DZ_{tag}_BEGIN__*/", f"/*__DZ_{tag}_END__*/"
        i, j = final.index(b), final.index(e) + len(e)
        p = REPO / "frontend/patches" / nom
        neuf = (final[i:j] + "\r\n").encode("utf-8")
        if p.read_bytes().replace(b"\r\n", b"\n") != neuf.replace(b"\r\n", b"\n"):
            ecarts.append(str(p.relative_to(REPO)))
            if not check:
                p.write_bytes(neuf)
    for tag, src in sources.items():
        p = REPO / "frontend/patches" / COUCHES[tag]
        neuf = src.encode("utf-8")
        if p.read_bytes().replace(b"\r\n", b"\n") != neuf.replace(b"\r\n", b"\n"):
            ecarts.append(str(p.relative_to(REPO)))
            if not check:
                p.write_bytes(neuf)
    tb = (json.dumps(table, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    if not TABLE.exists() or TABLE.read_bytes().replace(b"\r\n", b"\n") != tb:
        ecarts.append(str(TABLE.relative_to(REPO)))
        if not check:
            TABLE.write_bytes(tb)
    if check:
        print(f"[g1] --check : {'à jour' if not ecarts else 'PAS à jour : ' + ', '.join(ecarts)}")
        return 1 if ecarts else 0
    print(f"[g1] {table['n_editions']} éditions : {table['n_couches']} dans les couches, "
          f"{len(table['paires'])} paires pour le maillon ; écrits : {', '.join(ecarts) or 'rien (à jour)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
