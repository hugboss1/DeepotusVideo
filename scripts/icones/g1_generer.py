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
    "SONVFX": [("/* Le prix affiché est celui de CE QUE FAIT le bouton. « VFX particules » est\n   passé de « $0.06 » à « gratuit » parce que la génération est désormais une\n   simulation locale, et « SFX » à « gratuit » parce que 606 bruitages CC0 sont\n   livrés : la facturation ElevenLabs ne concerne plus que la génération sur\n   description. Un tarif qui survit au câblage est un mensonge d'interface. */", '/* t183 (11/10/2026) : AUCUN prix écrit en dur dans ce rail. Musique et voix off se\n   paient au modèle choisi (leurs cartes affichent le prix lu au serveur) ; le SFX\n   GÉNÉRÉ se paie en crédits ElevenLabs — seuls les 606 bruitages CC0 livrés sont\n   gratuits ; VFX particules et post-traitement sont locaux. Un tarif écrit ici\n   ment dès que le câblage change. */'), (' {id:"music",name:dzT("son.gen.musique"),desc:dzT("son.gen.musique_desc"),price:"~$0.10",c:"--c-audio"},\n {id:"sfx",name:"SFX",desc:dzT("son.gen.sfx_desc"),price:dzT("son.commun.gratuit"),c:"--c-audio"},\n {id:"voiceover",name:dzT("son.gen.voix_off"),desc:dzT("son.gen.voix_off_desc"),price:"$0.08",c:"--c-audio"},\n {id:"vfx",name:dzT("son.gen.vfx"),desc:dzT("son.gen.vfx_desc"),price:dzT("son.commun.gratuit"),c:"--c-3d"},\n {id:"post",name:dzT("son.gen.post"),desc:"Grain, glow, aberration, transitions",price:dzT("son.commun.gratuit"),c:"--c-3d"}];', ' {id:"music",name:dzT("son.gen.musique"),desc:dzT("son.gen.musique_desc"),price:dzT("son.gen.prix_modele"),c:"--c-audio"},\n {id:"sfx",name:"SFX",desc:dzT("son.gen.sfx_desc"),price:dzT("son.gen.prix_sfx"),c:"--c-audio"},\n {id:"voiceover",name:dzT("son.gen.voix_off"),desc:dzT("son.gen.voix_off_desc"),price:dzT("son.gen.prix_modele"),c:"--c-audio"},\n {id:"vfx",name:dzT("son.gen.vfx"),desc:dzT("son.gen.vfx_desc"),price:dzT("son.gen.local"),c:"--c-3d"},\n {id:"post",name:dzT("son.gen.post"),desc:"Grain, glow, aberration, transitions",price:dzT("son.gen.local"),c:"--c-3d"}];')],
    # t186 (G4 génération IA, 12/10/2026) : la rangée « Sujet » du rack choisit son modèle dans le registre du
    # détourage vidéo (saisie scripts/i18n_l4/vfx.py) — retouches de VfxStack à longueur égale (commentaire de tête
    # compensé), code neuf APRÈS la dernière édition G1 (avant vfxPatch1)
    "VFXRACK": [("/* ── T103 (D2b) : la rangée « Sujet » — détourer le plan (BiRefNet, fal) ──\n     PAYANT et au prix NON AFFICHÉ par fal : 1er clic = devis du backend (la\n     ligne dit « à mesurer »), 2e clic = tir. Le résultat part au Montage par\n     `dz-matte` {id, matte} : l'hôte le pose sur le plan, annulable. */", "/* ── T103 (D2b) + t186 (G4) : la rangée « Sujet » — détourer le plan ─────────────────────────────────────────────\n     PAYANT : 1er clic = devis, 2e clic = tir ; le modèle vient du registre\n     (vfxMatte*, fin de couche). Résultat au Montage par `dz-matte`. */"), ("body:JSON.stringify({kind:\"matte\",duration_s:vfxN(clip.end,0)-vfxN(clip.start,0)})", "body:JSON.stringify(vfxMatteDevis(vfxN(clip.end,0)-vfxN(clip.start,0)))"), ("if(VFX_MATTE.busy||!clip||!clip.src||!clip.src.job_id)return;", "if(VFX_MATTE.busy||!clip||!clip.src||!clip.src.job_id)return;if(vfxMatteSansSujet(fireNote))return;"), ("vfxPost(\"/api/matte\",{job_id:clip.src.job_id,model:VFX_MATTE.model})", "vfxPost(\"/api/matte\",vfxMatteCorps(clip.src.job_id))"), ("onChange:function(e){VFX_MATTE.model=e.target.value;VFX_MATTE.arm=null;", "onChange:function(e){vfxMatteChoix(e.target.value);VFX_MATTE.arm=null;"), ("children:mods.map(function(o){return r.jsx(\"option\",{value:o.id,children:o.label},o.id)})}):null,", "children:mods.map(function(o){return r.jsx(\"option\",{value:o.id,children:vfxMatteLbl(o)},o.id)})}):null,vfxMatteSujetRow(mtick),"), ("/* petit utilitaire : {clé: valeur} calculé", "/* ── t186 (G4) : le modèle du détourage d'un plan, pris dans le registre unique ──\n   GET /api/matte-models sert en tête les trois anciennes clés (BiRefNet v2 vidéo :\n   general, matting, portrait) puis les modèles vidéo du registre (Bria VRMBG 3.0, VEED\n   rapide, Pixelcut vidéo, SAM 3.1), chacun avec usd, unite, prompt, dispo, cle. Le\n   libellé porte le prix (règle unique prixUsd de DzModelesIA, sinon dzPrixUsd du maillon\n   encartsia) et, sans clé, la mention « clé X à ajouter dans Réglages » : l'option reste\n   CHOISISSABLE, POST /api/matte refuse en 503 avant toute dépense. SAM 3.1 exige le sujet\n   à garder (champ sous le sélecteur, refus avant l'envoi s'il est vide). Le choix est\n   mémorisé (localStorage dz_detour_vfx) ; défaut historique : general. Ces fonctions\n   vivent ICI, après la dernière édition G1 de la couche : la table dzglyph_paires.json\n   repère les éditions par position (les retouches plus haut sont à longueur égale). */\nvar VFX_DETOUR_LS=\"dz_detour_vfx\";\ntry{VFX_MATTE.model=localStorage.getItem(VFX_DETOUR_LS)||VFX_MATTE.model}catch(_e){}\nVFX_MATTE.sujet=\"\";\nfunction vfxMatteMod(id){var l=VFX_MATTE.models||[];for(var i=0;i<l.length;i++)if(l[i].id===id)return l[i];return null}\n/* un modèle mémorisé que le serveur ne sert plus retombe sur la première option (general) */\nfunction vfxMatteValide(){var l=VFX_MATTE.models||[];if(l.length&&!vfxMatteMod(VFX_MATTE.model))VFX_MATTE.model=l[0].id}\nfunction vfxMattePrixUsd(usd,unite){\n  var f=(window.DzModelesIA&&window.DzModelesIA.prixUsd)||(typeof dzPrixUsd===\"function\"?dzPrixUsd:null);\n  return f?f(usd,unite):\"\"}\nfunction vfxMatteLbl(o){var p=vfxMattePrixUsd(o.usd,o.unite);\n  return o.label+\" · \"+(p||dzT(\"ia.prix.a_mesurer\"))+(o.dispo===!1&&o.cle?\" · \"+dzT(\"ia.cle.a_ajouter\",{cle:o.cle}):\"\")}\nfunction vfxMatteChoix(v){VFX_MATTE.model=v;try{localStorage.setItem(VFX_DETOUR_LS,v)}catch(_e){}}\nfunction vfxMatteSujetReq(){var m=vfxMatteMod(VFX_MATTE.model);return!!(m&&m.prompt)}\nfunction vfxMatteSansSujet(note){vfxMatteValide();\n  if(!vfxMatteSujetReq()||String(VFX_MATTE.sujet||\"\").trim())return!1;\n  note(dzT(\"detour.champ.sujet_requis\"));return!0}\n/* le devis : BiRefNet (anciennes clés, birefnet-v2-video) garde le kind « matte » d'avant ; les autres : « detourage » */\nfunction vfxMatteDevis(dur){var m=vfxMatteMod(VFX_MATTE.model),reg=(m&&m.registre)||VFX_MATTE.model;\n  return reg===\"birefnet-v2-video\"||reg===\"general\"||reg===\"matting\"||reg===\"portrait\"?{kind:\"matte\",duration_s:dur}:{kind:\"detourage\",modele:reg,secondes:dur}}\nfunction vfxMatteCorps(job){var c={job_id:job,model:VFX_MATTE.model};\n  if(vfxMatteSujetReq())c.sujet=String(VFX_MATTE.sujet||\"\").trim();return c}\nfunction vfxMatteSujetRow(tick){\n  vfxMatteValide();\n  if(!vfxMatteSujetReq())return null;\n  return r.jsx(\"input\",{className:\"vfx-sel vfx-msujet\",type:\"text\",value:VFX_MATTE.sujet||\"\",\"data-dzdetsujet\":\"1\",\n    placeholder:dzT(\"detour.champ.sujet\"),\"aria-label\":dzT(\"detour.champ.sujet\"),\n    onChange:function(e){VFX_MATTE.sujet=e.target.value;VFX_MATTE.arm=null;tick(function(n){return n+1})}})}\n\n/* petit utilitaire : {clé: valeur} calculé")],
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
