# -*- coding: utf-8 -*-
"""t515 (RV5, 26/11/2026) — gabarit « REEL EN TABLEAUX » piloté par un fichier de repères, puis brouillon au Planificateur.

Spec docs/superpowers/specs/2026-11-13-reel-reference-design.md, § 3.4 points 3-4, § 9.2, R7, R8, R12.
Prototype : le Reel fait à la main (t519, film-promo/reel-recette) ; rien n'en est repris que la FORME des repères.

1. `fabriquer_reperes` (pur, gratuit) : un script VALIDÉ (porte 1 de RV4) + la recette + les temps des mots s'ils
   existent (transcription de la voix, `temps`), sinon des temps ESTIMÉS à 2,5 mots/s -> un fichier de REPÈRES : un
   tableau par brique (rôle, visuel de la recette, mot déclencheur et son temps, objet animé, valeur), les sous-titres
   groupés au format de la recette (mot en pastille, badge), la frise de progression, la provenance `inspire_de`.
   R8 : un chiffre absent des chiffres publiables de la fiche d'offre, ou des barres sans chiffre sourcé, sont marqués
   « valeur d'illustration » À L'IMAGE.
2. `page` (pure) : la page motion code du gabarit, écrite par nous (jamais par un modèle : aucun coût), aux couleurs de
   la CHARTE de l'espace (kit de marque, typographie d'identité : `motion_choregraphe.marque`), jamais à la palette de
   la source ; données en base64 comme la page de repli de t238 (le contrôle du bac à sable ne lit pas les mots du
   script comme du code). Sous-titres en pastille + badge DESSINÉS dans la page (R7).
3. `rendre` : la page rendue par le moteur motion code existant (`motion_code.rendre_page`, local, GRATUIT), puis le
   commentaire du MP4 posé sans réencodage (R12 b : « Structure inspirée de <lien>. Texte, images et voix
   originaux. ») et la RECETTE DE FABRICATION écrite à côté du rendu et dans `_recipes/<job>.fabrication.json`
   (lue par `recette_rendu`), avec `inspire_de` (R12 a).
4. `brouillon` : `routes.create_scheduled_post`, statut brouillon, mode TOUJOURS « assisted » (R8 : jamais « auto »,
   quoi que demande le corps), le job du rendu lié, `brief.inspire_de` (interne) et `brief.instagram.forme = reel`.
   R12 c : la ligne publique « Format inspiré d'un Reel de @compte. » est PROPOSÉE, décochée par défaut ; elle n'entre
   dans la légende que si l'utilisateur coche la case. La légende libre passe les gardes de `inspiration` (copie,
   mots interdits, source citée).
"""
from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

from loguru import logger

from app.services import inspiration as I
from app.services import script_court as SC

DEBIT = 2.5                    # mots par seconde quand aucun temps réel n'existe (spec : « 2,5 mots/s »)
DEPART_S = 0.3                 # silence avant le premier mot
PAUSE_S = 0.25                 # respiration entre deux briques (estimation)
QUEUE_S = 0.8                  # le dernier tableau tient encore un instant
DUREE_MAX = 90.0               # un Reel sur recette : au-delà, refus (le rendu image par image deviendrait trop long)
FPS_DEFAUT = 30
W, H = 1080, 1920
OBJETS = ("texte", "barres", "compteur", "carte", "liste")
_OBJET_DE_VISUEL = {"barres": "barres", "compteur": "compteur", "carte": "carte", "capture": "carte", "produit": "carte",
                    "personne": "carte", "liste": "liste", "schema": "liste", "texte": "texte", "autre": "texte"}
LIBELLES = {"fr": {"illustration": "valeur d'illustration"}, "en": {"illustration": "illustrative value"}}
COMMENTAIRE = {"fr": "Structure inspirée de {lien}. Texte, images et voix originaux.",
               "en": "Structure inspired by {lien}. Original text, images and voice."}
MENTION = {"fr": {"instagram": "Format inspiré d'un Reel de {qui}.", "tiktok": "Format inspiré d'un TikTok de {qui}.",
                  "youtube": "Format inspiré d'un Short de {qui}.", "": "Format inspiré d'une vidéo de {qui}."},
           "en": {"instagram": "Format inspired by a Reel from {qui}.", "tiktok": "Format inspired by a TikTok from {qui}.",
                  "youtube": "Format inspired by a Short from {qui}.", "": "Format inspired by a video from {qui}."}}


# ---- repères (purs) ---------------------------------------------------------------------------------------------------

def _norme(m: str) -> str:
    m = unicodedata.normalize("NFKD", str(m or "").casefold())
    return "".join(c for c in m if c.isalnum())


def _mots_temps(temps) -> list[dict]:
    """Les temps fournis ({text|mot, start|debut, end|fin}) -> [{t, s, e}] ; les entrées illisibles sont écartées."""
    out = []
    for x in temps if isinstance(temps, list) else []:
        if not isinstance(x, dict):
            continue
        t = str(x.get("text") if x.get("text") is not None else x.get("mot") or "").strip()
        try:
            s = float(x.get("start") if x.get("start") is not None else x.get("debut"))
            e = float(x.get("end") if x.get("end") is not None else x.get("fin") if x.get("fin") is not None else s)
        except (TypeError, ValueError):
            continue
        if t and s >= 0:
            out.append({"t": t, "s": round(s, 3), "e": round(max(s, e), 3)})
    return out


def _estimer(briques: list) -> list[list[dict]]:
    """Les temps ESTIMÉS : 2,5 mots par seconde, une respiration entre deux briques."""
    t, out, pas = DEPART_S, [], 1.0 / DEBIT
    for i, b in enumerate(briques):
        ligne = []
        for m in str(b.get("texte") or "").split():
            ligne.append({"t": m, "s": round(t, 3), "e": round(t + pas * 0.9, 3)})
            t += pas
        out.append(ligne)
        if i < len(briques) - 1:
            t += PAUSE_S
    return out


def _aligner(briques: list, temps) -> list[list[dict]] | None:
    """Les vrais temps répartis brique par brique, dans l'ordre ; None si leur nombre ne colle pas au script."""
    tt = _mots_temps(temps)
    n = [len(str(b.get("texte") or "").split()) for b in briques]
    if not tt or len(tt) != sum(n):
        return None
    out, k = [], 0
    for b, c in zip(briques, n):
        mots = str(b.get("texte") or "").split()
        out.append([{"t": mots[j], "s": tt[k + j]["s"], "e": tt[k + j]["e"]} for j in range(c)])
        k += c
    return out


def _connus(chiffres: list) -> set:
    return {SC._nombre(v) for x in chiffres or [] for v in SC.chiffres(str((x or {}).get("valeur") or ""))}


def _premier_chiffre(texte: str) -> str:
    """Le premier chiffre TEL QU'ÉCRIT (« 99 $ ») : c'est lui qu'on affiche ; la comparaison passe par SC._nombre."""
    for m in SC._CHIFFRE.finditer(str(texte or "")):
        if re.search(r"\d", m.group(0)):
            return " ".join(m.group(0).split())
    return ""


def _declencheur(mots: list[dict], ecran: str, valeur_chiffree: str) -> dict:
    """Le mot qui déclenche l'animation : le premier mot DIT qui est aussi à l'écran, sinon celui du chiffre, sinon le
    premier mot de la brique."""
    ecr = {_norme(w) for w in str(ecran or "").split()} - {""}
    nombre = _norme(valeur_chiffree.split()[0]) if valeur_chiffree else ""
    for w in mots:
        if nombre and _norme(w["t"]) == nombre:
            return {"mot": w["t"].strip(".,;:!?…"), "t": w["s"], "i": mots.index(w)}
    for w in mots:
        if _norme(w["t"]) in ecr:
            return {"mot": w["t"].strip(".,;:!?…"), "t": w["s"], "i": mots.index(w)}
    w = mots[0] if mots else {"t": "", "s": 0.0}
    return {"mot": w["t"].strip(".,;:!?…"), "t": w["s"], "i": 0}


def _entier(v, lo: int, hi: int, defaut: int) -> int:
    try:
        x = int(v)
    except (TypeError, ValueError):
        return defaut
    return max(lo, min(hi, x)) if x else defaut


def reperes(rec: dict, fiche: dict | None = None, temps=None) -> dict:
    """Le fichier de repères (PUR) d'une inspiration dont le script est validé. `fiche` = la fiche d'offre (chiffres
    publiables) ; `temps` = les temps des mots de la voix, s'ils existent."""
    s = rec.get("script") or {}
    if s.get("statut") != "valide" or not s.get("briques"):
        raise I.RefusInspiration("Le script n'est pas validé : valide-le d'abord (porte 1).", "script_non_valide")
    rc = rec.get("recette") or {}
    briques = s["briques"]
    structure = rc.get("structure") or []
    vrais = _aligner(briques, temps)
    mots = vrais or _estimer(briques)
    connus = _connus((fiche or {}).get("chiffres") or [])
    st = rc.get("soustitres") or {}
    mpl, nl = _entier(st.get("mots_par_ligne"), 1, 6, 3), _entier(st.get("lignes"), 1, 3, 2)
    pastille = st.get("mot_en_pastille") is not False
    badge = st.get("badge") is not False
    tableaux, soustitres = [], []
    debut = 0.0
    for i, b in enumerate(briques):
        ms = mots[i]
        suivant = mots[i + 1][0]["s"] if i + 1 < len(mots) and mots[i + 1] else None
        fin = round(suivant if suivant is not None else ((ms[-1]["e"] if ms else debut) + QUEUE_S), 3)
        sb = structure[i] if i < len(structure) and isinstance(structure[i], dict) else {}
        visuel = str(sb.get("visuel") or "texte")
        texte, ecran = str(b.get("texte") or ""), str(b.get("ecran") or "")
        chiffre = _premier_chiffre(texte + " " + ecran)
        objet = _OBJET_DE_VISUEL.get(visuel, "texte")
        if objet in ("texte",) and chiffre:
            objet = "compteur"
        if objet == "compteur" and not chiffre:
            objet = "texte"
        source_ok = bool(chiffre) and SC._nombre(chiffre) in connus
        illustration = (bool(chiffre) and not source_ok) or (objet == "barres" and not source_ok)
        dec = _declencheur(ms, ecran, chiffre)
        tableaux.append({"n": i + 1, "role": str(b.get("role") or sb.get("role") or ""), "visuel": visuel,
                         "debut": round(debut, 3), "fin": fin, "texte": texte, "ecran": ecran,
                         "declencheur": {"mot": dec["mot"], "t": dec["t"]}, "objet": objet,
                         "valeur": chiffre or ecran or dec["mot"], "illustration": bool(illustration)})
        ecr = {_norme(w) for w in ecran.split()} - {""}
        groupe = mpl * nl
        for g0 in range(0, len(ms), groupe):
            g = ms[g0:g0 + groupe]
            fin_g = ms[g0 + groupe]["s"] if g0 + groupe < len(ms) else fin
            lignes = []
            for l0 in range(0, len(g), mpl):
                lignes.append([{"t": w["t"], "s": w["s"],
                                "p": bool(pastille and _norme(w["t"]) in ecr),
                                "g": chiffre if (badge and chiffre and g0 + l0 + j == dec["i"]) else ""}
                               for j, w in enumerate(g[l0:l0 + mpl])])
            soustitres.append({"a": g[0]["s"], "b": round(fin_g, 3), "l": lignes})
        debut = fin
    duree = round(tableaux[-1]["fin"] if tableaux else 0.0, 3)
    if duree > DUREE_MAX:
        raise I.RefusInspiration("Le script dure plus de 90 secondes : raccourcis-le pour un Reel.", "trop_long")
    src = rc.get("inspire_de") or {}
    return {"version": 1, "genre": "reel_tableaux", "langue": s.get("langue") if s.get("langue") in ("fr", "en") else "fr",
            "temps": "mots" if vrais else "estimes", "debit_mots_s": DEBIT, "duree_s": duree, "W": W, "H": H,
            "tableaux": tableaux, "soustitres": soustitres, "frise": {"n": len(tableaux)},
            "mention_illustration": any(t["illustration"] for t in tableaux),
            "inspire_de": {k: src.get(k) or "" for k in ("plateforme", "lien", "libelle", "capture_le")},
            "fait_le": I._maintenant()}


def fabriquer_reperes(iid: str, temps=None) -> dict:
    """Les repères calculés et RANGÉS dans l'inspiration (gratuit)."""
    from app.services import offre as OF
    rec = I.lire(iid)
    try:
        fiche = OF.lire(rec["espace_id"])
    except KeyError:
        fiche = {}
    r = reperes(rec, fiche, temps)
    rec = I.lire(iid)
    reel = rec.get("reel") or {}
    reel.update({"reperes": r})
    reel.pop("rendu", None)                 # des repères neufs : le rendu précédent ne leur correspond plus
    rec["reel"] = reel
    I._ecrire(rec)
    logger.info(f"inspiration {iid[:8]} : repères, {len(r['tableaux'])} tableau(x), {r['duree_s']} s, temps {r['temps']}")
    return r


# ---- la charte et la page ---------------------------------------------------------------------------------------------

def _assombrir(c: str, k: float = 0.16) -> str:
    try:
        r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    except (TypeError, ValueError):
        return "#0a0d12"
    return "#%02x%02x%02x" % tuple(int(v * k) for v in (r, g, b))


def charte(eid: str) -> dict:
    """{accent, marque, fond, texte, police} : le kit de marque et la typographie d'identité de L'ESPACE."""
    from app.services import espaces
    from app.services import motion_choregraphe as CH
    with espaces.sous_espace(eid):
        m = CH.marque()
    return {"accent": m["couleur"], "marque": m["marque"], "fond": _assombrir(m["marque"]), "texte": "#ffffff",
            "police": m["police"]}


_JS = r"""var D=JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(document.getElementById("dz-donnees").textContent.trim()),
function(c){return c.charCodeAt(0)}))),C=D.charte;
function q(i){return document.getElementById(i)}
function mk(t,css,txt){var n=document.createElement(t);n.style.cssText=css||"";if(txt!=null)n.textContent=txt;return n}
function ez(t){t=Math.min(1,Math.max(0,t));return 1-Math.pow(1-t,3)}
var F=q("dz-frise"),S=q("dz-scene"),B=q("dz-sous"),cases=[];
for(var i=0;i<D.frise.n;i++){var c=mk("div","flex:1;height:14px;background:rgba(255,255,255,.18);position:relative;overflow:hidden");
var r=mk("div","position:absolute;left:0;bottom:0;height:100%;width:0;background:"+C.accent);c.appendChild(r);F.appendChild(c);cases.push(r)}
var TB=D.tableaux.map(function(t){var n=mk("div","position:absolute;left:8%;right:8%;bottom:42%;display:flex;flex-direction:column;align-items:center;gap:28px;opacity:0");
var o=mk("div","");n.appendChild(o);var nb=null;
if(t.objet==="barres"){o.style.cssText="display:flex;align-items:flex-end;gap:60px;height:620px";
var b1=mk("div","width:220px;height:0;background:rgba(255,255,255,.35)"),b2=mk("div","width:220px;height:0;background:"+C.accent);o.appendChild(b1);o.appendChild(b2);nb=[b1,b2];
var lb=mk("div","font:800 84px "+C.police+";color:"+C.texte,t.valeur);n.appendChild(lb)}
else if(t.objet==="compteur"){o.style.cssText="font:900 230px "+C.police+";color:"+C.accent+";line-height:1"}
else if(t.objet==="carte"){o.style.cssText="background:"+C.marque+";color:"+C.texte+";padding:70px 80px;font:800 96px "+C.police+";text-align:center;max-width:100%";o.textContent=t.ecran||t.valeur}
else if(t.objet==="liste"){o.style.cssText="display:flex;flex-direction:column;gap:24px;font:800 88px "+C.police+";color:"+C.texte;
nb=String(t.ecran||t.valeur).split(/[,·;]/).map(function(x){var it=mk("div","opacity:0","■ "+x.trim());o.appendChild(it);return it})}
else{o.style.cssText="font:900 150px "+C.police+";color:"+C.texte+";text-align:center;line-height:1.05";o.textContent=t.ecran||t.valeur}
if(t.illustration){n.appendChild(mk("div","font:600 40px "+C.police+";color:rgba(255,255,255,.7);border:2px solid rgba(255,255,255,.5);padding:6px 18px",D.libelles.illustration))}
S.appendChild(n);return{t:t,n:n,o:o,nb:nb}});
function nombre(v){var m=String(v).match(/-?\d+(?:[.,]\d+)?/);return m?{x:parseFloat(m[0].replace(",",".")),a:String(v).slice(0,m.index),b:String(v).slice(m.index+m[0].length),d:(m[0].split(/[.,]/)[1]||"").length}:null}
var GR=D.soustitres.map(function(g){var n=mk("div","position:absolute;left:6%;right:6%;bottom:16%;display:flex;flex-direction:column;align-items:center;gap:44px;opacity:0");
var mots=[];g.l.forEach(function(l){var li=mk("div","display:flex;flex-wrap:wrap;justify-content:center;gap:20px");
l.forEach(function(w){var s=mk("span","position:relative;font:900 76px "+C.police+";color:"+C.texte+";padding:4px 16px;opacity:.25",w.t);
if(w.p){s.style.background=C.accent;s.style.color=C.fond}
if(w.g){var bd=mk("span","position:absolute;right:-22px;bottom:96%;font:800 32px "+C.police+";background:"+C.marque+";color:"+C.texte+";padding:2px 12px;transform:rotate(-6deg)",w.g);s.appendChild(bd)}
li.appendChild(s);mots.push({w:w,s:s})});n.appendChild(li)});B.appendChild(n);return{g:g,n:n,mots:mots}});
window.dzFrame=function(t){var cur=-1;TB.forEach(function(o,i){var a=o.t.debut,b=o.t.fin;if(t>=a&&t<b)cur=i});
if(cur<0&&t>=D.duree_s-0.001)cur=TB.length-1;
cases.forEach(function(r,i){var o=TB[i].t,u=i<cur?1:(i===cur?Math.min(1,(t-o.debut)/Math.max(0.01,o.fin-o.debut)):0);r.style.width=(u*100)+"%"});
TB.forEach(function(o,i){if(i!==cur){o.n.style.opacity=0;return}var d=o.t.declencheur.t,u=ez((t-d)/0.45),e=ez((t-o.t.debut)/0.3);
o.n.style.opacity=e;o.o.style.transform="translateY("+((1-u)*60)+"px) scale("+(0.85+0.15*u)+")";
if(o.t.objet==="barres"&&o.nb){o.nb[0].style.height=(220*u)+"px";o.nb[1].style.height=(600*u)+"px"}
else if(o.t.objet==="compteur"){var v=nombre(o.t.valeur);o.o.textContent=v?(v.a+(v.x*u).toFixed(v.d)+v.b):o.t.valeur}
else if(o.t.objet==="liste"&&o.nb){o.nb.forEach(function(it,k){it.style.opacity=ez((t-d-k*0.25)/0.3)})}
else{o.o.style.opacity=0.35+0.65*u}});
GR.forEach(function(G){var on=t>=G.g.a&&t<G.g.b;G.n.style.opacity=on?1:0;if(!on)return;
G.mots.forEach(function(x){x.s.style.opacity=t>=x.w.s?1:0.25;x.s.style.transform=(t>=x.w.s&&t<x.w.s+0.12)?"scale(1.08)":"scale(1)"})})};"""


def page(rep: dict, ch: dict) -> str:
    """La page motion code du gabarit (PURE, déterministe). Tout ce qui vient du script est en base64."""
    lg = rep.get("langue") if rep.get("langue") in LIBELLES else "fr"
    donnees = {"tableaux": rep.get("tableaux") or [], "soustitres": rep.get("soustitres") or [],
               "frise": rep.get("frise") or {"n": len(rep.get("tableaux") or [])}, "duree_s": rep.get("duree_s") or 0,
               "libelles": LIBELLES[lg],
               "charte": {k: ch.get(k) for k in ("accent", "marque", "fond", "texte")}}
    donnees["charte"]["police"] = "'%s', Impact, 'Arial Black', 'Segoe UI', sans-serif" % str(ch.get("police") or "Anton").replace("'", "")
    b64 = base64.b64encode(json.dumps(donnees, ensure_ascii=True).encode("utf-8")).decode("ascii")
    return ('<!doctype html><html><head><style>body{background:%s}#dz-fond{position:absolute;inset:0;background:'
            'radial-gradient(circle at 50%% 30%%,%s 0,%s 75%%)}#dz-frise{position:absolute;left:6%%;right:6%%;top:7%%;'
            'display:flex;gap:10px}#dz-scene,#dz-sous{position:absolute;inset:0;overflow:hidden}</style></head><body>'
            '<div id="dz-fond"></div><div id="dz-frise"></div><div id="dz-scene"></div><div id="dz-sous"></div>'
            '<script type="application/octet-stream" id="dz-donnees">%s</script><script>%s</script></body></html>'
            % (ch.get("fond"), ch.get("marque"), ch.get("fond"), b64, _JS))


# ---- commentaire du MP4, recette de fabrication -----------------------------------------------------------------------

def commentaire(inspire_de: dict, langue: str = "fr") -> str:
    """R12 b : la balise de commentaire du MP4 (les réseaux l'effacent au réencodage ; aucune portée publique)."""
    lien = str((inspire_de or {}).get("lien") or (inspire_de or {}).get("libelle") or "").strip()
    return COMMENTAIRE["en" if langue == "en" else "fr"].format(lien=lien or "—")


def poser_commentaire(entree, sortie, texte: str) -> None:
    """Le commentaire posé par ffmpeg SANS réencodage (copie des flux). RuntimeError si ffmpeg échoue."""
    ff = shutil.which("ffmpeg") or "ffmpeg"
    r = subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(entree), "-map", "0", "-c", "copy",
                        "-metadata", f"comment={texte}", "-movflags", "+faststart", str(sortie)],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode != 0 or not Path(sortie).is_file():
        raise RuntimeError("L'encodage vidéo a échoué (ffmpeg).")


def chemin_fabrication(job_id: str) -> Path:
    from app.config import settings
    nom = Path(str(job_id or "")).name
    d = settings.outputs_path / "_recipes"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{nom}.fabrication.json"


def rendre(iid: str, sortie, *, job_id: str = "", fps: int = FPS_DEFAUT, langue: str = "fr") -> dict:
    """La page du gabarit rendue en MP4 (local, gratuit), commentée, avec sa recette de fabrication. Bloquant."""
    from app.services import motion_code as MC
    rec = I.lire(iid)
    rep = (rec.get("reel") or {}).get("reperes")
    if not rep or not rep.get("tableaux"):
        raise I.RefusInspiration("Prépare d'abord les repères du Reel.", "sans_reperes")
    ch = charte(rec["espace_id"])
    html = page(rep, ch)
    f = int(min(MC.FPS[1], max(MC.FPS[0], int(fps or FPS_DEFAUT))))
    duree = max(1.0, float(rep["duree_s"]))
    sortie = Path(sortie)
    brut = sortie.with_name(sortie.stem + ".brut.mp4")
    try:
        r = MC.rendre_page(html, brut, W=W, H=H, fps=f, duree_s=duree, delai=MC.delai_rendu(f, duree), langue=langue)
        texte = commentaire(rep.get("inspire_de") or {}, rep.get("langue") or "fr")
        poser_commentaire(brut, sortie, texte)
    finally:
        brut.unlink(missing_ok=True)
    fab = {"genre": "reel_tableaux", "tache": "t515", "inspiration_id": iid, "espace_id": rec["espace_id"],
           "inspire_de": rep.get("inspire_de") or {}, "commentaire_mp4": texte, "page_id": MC.enregistrer(html),
           "temps": rep.get("temps"), "tableaux": len(rep["tableaux"]), "duree_s": rep["duree_s"], "fps": f,
           "aspect_ratio": "9:16", "charte": ch, "mention_illustration": bool(rep.get("mention_illustration")),
           "script_valide_le": (rec.get("script") or {}).get("valide_le"), "rendu_le": I._maintenant()}
    corps = json.dumps(fab, ensure_ascii=False, indent=1)
    sortie.with_name(sortie.stem + ".recette.json").write_text(corps, encoding="utf-8")
    if job_id:
        chemin_fabrication(job_id).write_text(corps, encoding="utf-8")
    rec = I.lire(iid)
    reel = rec.get("reel") or {}
    reel["rendu"] = {"job_id": job_id, "video": str(sortie), "page_id": fab["page_id"], "le": fab["rendu_le"],
                     "duree_s": r.get("duree_s"), "fps": f}
    rec["reel"] = reel
    I._ecrire(rec)
    logger.info(f"inspiration {iid[:8]} : Reel en tableaux rendu, {fab['tableaux']} tableau(x), {r.get('duree_s')} s")
    return {**r, "video": str(sortie), "page_id": fab["page_id"]}


# ---- brouillon --------------------------------------------------------------------------------------------------------

def _qui(inspire_de: dict) -> str:
    lib = str(inspire_de.get("libelle") or "")
    m = re.search(r"@[\w.]+", lib)
    return m.group(0) if m else (lib.strip() or str(inspire_de.get("lien") or "").strip())


def mention_publique(inspire_de: dict, langue: str = "fr") -> str:
    """R12 c : la ligne publique PROPOSÉE (jamais posée d'office)."""
    d = MENTION["en" if langue == "en" else "fr"]
    qui = _qui(inspire_de or {})
    return d.get(str((inspire_de or {}).get("plateforme") or ""), d[""]).format(qui=qui) if qui else ""


def proposition(rec: dict) -> dict:
    """{titre, legende, mention_publique: {texte, coche: False}} : ce que l'écran pré-remplit."""
    s = rec.get("script") or {}
    rep = (rec.get("reel") or {}).get("reperes") or {}
    br = s.get("briques") or []
    lg = rep.get("langue") or s.get("langue") or "fr"
    return {"titre": str((br[0] if br else {}).get("ecran") or (br[0] if br else {}).get("texte") or "")[:200],
            "legende": " ".join(str(b.get("texte") or "") for b in br)[:2200],
            "mention_publique": {"texte": mention_publique(rep.get("inspire_de") or {}, lg), "coche": False}}


async def brouillon(iid: str, *, titre: str = "", legende=None, mention: bool = False) -> dict:
    """Le brouillon du Reel rendu, mode ASSISTÉ (R8), provenance interne (R12 a), mention publique si cochée (R12 c)."""
    from app.services import espaces
    rec = I.lire(iid)
    reel = rec.get("reel") or {}
    rendu = reel.get("rendu") or {}
    if not rendu.get("job_id"):
        raise I.RefusInspiration("Rends d'abord le Reel : le brouillon a besoin de sa vidéo.", "sans_rendu")
    p = proposition(rec)
    titre = I._texte(titre, 200) or p["titre"] or "Reel"
    legende = (str(legende).strip() if isinstance(legende, str) and legende.strip() else p["legende"])[:2200]
    interdits = await I._interdits(rec["espace_id"])
    j = I.juger_texte(rec, titre, "", legende, interdits)
    if not j["garde"]["ok"]:
        raise I.RefusInspiration("Trop proche de la capture : une suite de 12 mots ou plus la reprend. Réécris ce passage.", "copie", j)
    if j["interdits"]:
        raise I.RefusInspiration("Mots interdits de l'espace : réécris sans eux.", "interdits", j)
    if I._source_citee(rec, "\n".join((titre, legende))):
        raise I.RefusInspiration("La source de l'inspiration (lien ou compte) ne se publie pas : retire-la du texte.", "source", j)
    e = espaces.lire()["espaces"].get(rec["espace_id"])
    if not e or e.get("archive"):
        raise I.RefusInspiration("L'espace de cette inspiration est inconnu ou archivé.", "espace")
    ligne = p["mention_publique"]["texte"] if mention is True else ""
    caption = legende + ("\n\n" + ligne if ligne else "")
    inspire_de = (reel.get("reperes") or {}).get("inspire_de") or (rec.get("recette") or {}).get("inspire_de") or {}
    from app.api import routes as R
    post = await R.create_scheduled_post({
        "title": titre, "caption": caption, "status": "draft", "mode": "assisted", "run_at": I._demain(),
        "espace_id": rec["espace_id"], "job_id": rendu["job_id"], "format": "reel",
        "hook": str(((rec.get("script") or {}).get("briques") or [{}])[0].get("texte") or "")[:300] or None,
        "brief": {"instagram": {"forme": "reel"}, "inspire_de": inspire_de, "inspiration_id": iid,
                  "mention_publique": bool(ligne), "recette_reel": {"genre": "reel_tableaux", "tache": "t515"}}})
    rec = I.lire(iid)
    rec.setdefault("brouillons", []).append({"post_id": post.get("id"), "statut": post.get("status"), "cree": I._maintenant(),
                                            "reel": True, "job_id": rendu["job_id"], "mention_publique": bool(ligne),
                                            "proximite": j["garde"]["proximite"]})
    I._ecrire(rec)
    logger.info(f"inspiration {iid[:8]} : brouillon du Reel {str(post.get('id'))[:8]} ({post.get('status')}, "
                f"{post.get('mode')}), mention publique {'oui' if ligne else 'non'}")
    return {"post": post, **j}
