# -*- coding: utf-8 -*-
"""t380 (30/10/2026) — FILS SOCIAUX SUIVIS : une autre sorte de source News (plan du 29/10, Lot B, décision D4).

Un FIL = un compte ou une communauté d'une plateforme (X, Instagram, TikTok, YouTube, Reddit ; LinkedIn exclu), lu à
la FRÉQUENCE choisie pour lui, dont les publications rejoignent le cache de News et donc le classement existant
(filtre, mémoire, tendances, score, chaîne) avec leur `plateforme`.
  - YouTube et Reddit : flux GRATUITS (Atom d'une chaîne UC…, .rss d'une communauté ou d'un compte) ;
  - X, Instagram, TikTok : Apify (services/apify.py, liste blanche) derrière un ACCORD : le devis est montré, l'utilisateur
    pose un plafond PAR RELEVÉ (au plus celui de l'usage « veille ») avec `confirme_cout` ; sans accord, aucun run ni
    devis à la boucle ; un devis du jour au-delà du plafond du fil = refus (`devis_depasse`) ; puis la garde des
    plafonds mensuels (`plafonds.verifier`, catégorie « news », réf. = l'id du fil) avant le run, et le coût réel noté.
Les agents ne font que SUGGÉRER (`proposer_fil`, boîte « fils ») : la suggestion attend dans « Suggérés par les agents »
avec son origine, l'utilisateur l'accepte (le fil naît) ou l'écarte (jamais reproposée).
Auteurs tiers non gardés (règle de la veille) : un élément ne porte ni pseudo ni « submitted by /u/… », un lien X ou
TikTok est refait sans le pseudo. Stockage dans le dossier de News : fils.json, fils_suggestions.json, fils_items.json.
Couture de banc : `_RSS(src)` (lecture d'un flux, news_service._fetch_rss par défaut)."""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import threading
from datetime import datetime, timedelta, timezone

from loguru import logger

from app.services.news_service import MAX_ITEMS, _clean, _hid, news_service

PLATEFORMES = {
    "x": {"libelle": "X", "lecture": "apify", "acteur": "x"},
    "instagram": {"libelle": "Instagram", "lecture": "apify", "acteur": "instagram_posts"},
    "tiktok": {"libelle": "TikTok", "lecture": "apify", "acteur": "tiktok"},
    "youtube": {"libelle": "YouTube", "lecture": "rss"},
    "reddit": {"libelle": "Reddit", "lecture": "rss"},
}
FREQUENCES_H = (1, 3, 6, 12, 24, 72, 168)
FREQUENCE_DEFAUT_H = 24
MAX_DEFAUT, MAX_BORNE = 20, 100           # publications demandées par relevé Apify
PAR_FIL = 25                              # éléments gardés par fil
MAX_FILS, MAX_SUGGESTIONS = 50, 50
CADRES = ("campagne", "veille", "prospects")
TIC_S = 600

_VERROU = threading.Lock()


class RefusFil(ValueError):
    """Un refus dit à l'écran ou à l'agent : `code` (devis_a_accepter, devis_depasse, deja_suivi…), `statut` HTTP."""

    def __init__(self, message: str, code: str = "", statut: int = 400, **extra):
        super().__init__(message)
        self.code, self.statut, self.extra = code, statut, extra


def _RSS(src: dict) -> list[dict]:
    return news_service._fetch_rss(src)


def _FILS_PATH():
    return news_service.dir / "fils.json"


def _SUG_PATH():
    return news_service.dir / "fils_suggestions.json"


def _ITEMS_PATH():
    return news_service.dir / "fils_items.json"


def _lire(chemin, defaut):
    try:
        return json.loads(chemin().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defaut


def _ecrire(chemin, valeur) -> None:
    p = chemin()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(valeur, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def _maintenant() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d: datetime | None = None) -> str:
    return (d or _maintenant()).isoformat(timespec="seconds")


# ---- identifiants ------------------------------------------------------------------------------------------------------

_YT = re.compile(r"(?<![A-Za-z0-9_-])(UC[A-Za-z0-9_-]{22})(?![A-Za-z0-9_-])")
_RD_URL = re.compile(r"^(?:https?://)?(?:(?:www|old|new|np)\.)?reddit\.com/(r|u|user)/([A-Za-z0-9_-]+)", re.I)
_RD_COURT = re.compile(r"^/?(r|u)/([A-Za-z0-9_-]+)/?$", re.I)
_X_URL = re.compile(r"^(?:https?://)?(?:www\.|mobile\.)?(?:x|twitter)\.com/([A-Za-z0-9_]+)(?:[/?#]|$)", re.I)
_IG_URL = re.compile(r"^(?:https?://)?(?:www\.)?instagram\.com/([A-Za-z0-9._]+)(?:[/?#]|$)", re.I)
_TT_URL = re.compile(r"^(?:https?://)?(?:www\.|m\.)?tiktok\.com/@([A-Za-z0-9._]+)(?:[/?#]|$)", re.I)
_PSEUDO = {"x": re.compile(r"^[A-Za-z0-9_]{1,15}$"), "instagram": re.compile(r"^[A-Za-z0-9._]{1,30}$"),
           "tiktok": re.compile(r"^[A-Za-z0-9._]{2,24}$")}
_RESERVES = {"x": {"i", "home", "search", "explore", "hashtag", "intent", "share"},
             "instagram": {"p", "reel", "reels", "explore", "stories", "tv"}, "tiktok": set()}


def normaliser(plateforme: str, brut: str) -> dict:
    """{plateforme, identifiant, lecture, url_flux, lien} ; ValueError qui dit quoi coller."""
    p = str(plateforme or "").strip().lower()
    if p not in PLATEFORMES:
        raise RefusFil("plateforme non suivie : X, Instagram, TikTok, YouTube ou Reddit", "plateforme")
    s = str(brut or "").strip()[:300]
    if p == "youtube":
        m = _YT.search(s)
        if not m or not (s == m.group(1) or "youtube.com" in s.lower()):
            raise RefusFil("chaîne YouTube : collez l'identifiant UC… ou l'adresse /channel/UC… (un @pseudo n'a pas de "
                           "flux)", "identifiant")
        ident = m.group(1)
        flux, lien = (f"https://www.youtube.com/feeds/videos.xml?channel_id={ident}",
                      f"https://www.youtube.com/channel/{ident}")
    elif p == "reddit":
        m = _RD_URL.match(s) or _RD_COURT.match(s)
        sorte, nom = ((m.group(1).lower(), m.group(2)) if m else ("r", s))
        sorte = "u" if sorte in ("u", "user") else "r"
        if not re.match(r"^[A-Za-z0-9_]{3,21}$" if sorte == "r" else r"^[A-Za-z0-9_-]{3,20}$", nom):
            raise RefusFil("Reddit : collez r/communauté, u/compte ou leur adresse", "identifiant")
        ident = f"{sorte}/{nom}"
        chemin = f"r/{nom}" if sorte == "r" else f"user/{nom}"
        flux, lien = f"https://www.reddit.com/{chemin}/.rss", f"https://www.reddit.com/{chemin}/"
    else:
        m = {"x": _X_URL, "instagram": _IG_URL, "tiktok": _TT_URL}[p].match(s)
        ident = m.group(1) if m else s.lstrip("@")
        if not _PSEUDO[p].match(ident) or ident.lower() in _RESERVES[p]:
            raise RefusFil(f"{PLATEFORMES[p]['libelle']} : collez le @pseudo du compte ou l'adresse de son profil",
                           "identifiant")
        flux = None
        lien = {"x": f"https://x.com/{ident}", "instagram": f"https://www.instagram.com/{ident}/",
                "tiktok": f"https://www.tiktok.com/@{ident}"}[p]
    return {"plateforme": p, "identifiant": ident, "lecture": PLATEFORMES[p]["lecture"], "url_flux": flux, "lien": lien}


def _id(prefixe: str, plateforme: str, identifiant: str) -> str:
    return prefixe + hashlib.sha1(f"{plateforme}|{identifiant.lower()}".encode("utf-8")).hexdigest()[:10]


def _nom_defaut(n: dict) -> str:
    return n["identifiant"] if n["plateforme"] in ("youtube", "reddit") else "@" + n["identifiant"]


def _frequence(v, defaut=FREQUENCE_DEFAUT_H) -> int:
    if v is None:
        return defaut
    if isinstance(v, bool) or not isinstance(v, int) or v not in FREQUENCES_H:
        raise RefusFil(f"fréquence hors liste (heures) : {', '.join(str(x) for x in FREQUENCES_H)}", "frequence")
    return v


def _max(v) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= MAX_BORNE:
        raise RefusFil(f"nombre de publications par relevé : de 1 à {MAX_BORNE}", "max")
    return v


# ---- fils ----------------------------------------------------------------------------------------------------------------

def _fils() -> list[dict]:
    v = _lire(_FILS_PATH, [])
    return v if isinstance(v, list) else []


def vue(f: dict) -> dict:
    """Ce que l'écran lit d'un fil : la description, sa lecture, son lien public et sa prochaine lecture."""
    n = normaliser(f["plateforme"], f["identifiant"])
    prochaine = None
    if not f.get("pause") and (n["lecture"] == "rss" or f.get("accord")):
        t = f.get("derniere_tentative")
        prochaine = _iso(datetime.fromisoformat(t) + timedelta(hours=f["frequence_h"])) if t else _iso()
    return dict(f, lecture=n["lecture"], lien=n["lien"], prochaine=prochaine)


def lire_fil(fid: str) -> dict | None:
    for f in _fils():
        if f.get("id") == fid:
            return vue(f)
    return None


def _modifier(fid: str, **champs) -> dict | None:
    with _VERROU:
        fils = _fils()
        for f in fils:
            if f.get("id") == fid:
                f.update(champs)
                _ecrire(_FILS_PATH, fils)
                return vue(f)
    return None


def ajouter(plateforme: str, identifiant: str, nom: str | None = None, frequence_h=None,
            origine: dict | None = None) -> dict:
    n = normaliser(plateforme, identifiant)
    freq = _frequence(frequence_h)
    fid = _id("fil_", n["plateforme"], n["identifiant"])
    with _VERROU:
        fils = _fils()
        if any(f.get("id") == fid for f in fils):
            raise RefusFil("ce fil est déjà suivi", "deja_suivi", 409, fil_id=fid)
        if len(fils) >= MAX_FILS:
            raise RefusFil(f"{MAX_FILS} fils au plus : retirez-en un d'abord", "trop", 409)
        apify = n["lecture"] == "apify"
        f = {"id": fid, "plateforme": n["plateforme"], "identifiant": n["identifiant"],
             "nom": _clean(nom, 80) or _nom_defaut(n), "frequence_h": freq, "max": MAX_DEFAUT,
             "origine": origine or {"type": "main"}, "cree": _iso(), "pause": False, "accord": None,
             "derniere_lecture": None, "derniere_tentative": None, "dernier_nombre": 0, "dernier_cout_usd": 0.0,
             "cout_cumule_usd": 0.0, "etat": "devis_a_accepter" if apify else "jamais_lu", "erreur": None}
        fils.append(f)
        _ecrire(_FILS_PATH, fils)
    return vue(f)


def modifier(fid: str, corps: dict) -> dict | None:
    champs = {}
    if "pause" in corps:
        champs["pause"] = bool(corps["pause"])
    if "frequence_h" in corps:
        champs["frequence_h"] = _frequence(corps["frequence_h"])
    if "max" in corps:
        champs["max"] = _max(corps["max"])
    if "nom" in corps:
        champs["nom"] = _clean(corps["nom"], 80)
    if lire_fil(fid) is None:
        return None
    if "nom" in champs and not champs["nom"]:
        f = lire_fil(fid)
        champs["nom"] = _nom_defaut(normaliser(f["plateforme"], f["identifiant"]))
    return _modifier(fid, **champs)


def retirer(fid: str) -> bool:
    with _VERROU:
        fils = _fils()
        reste = [f for f in fils if f.get("id") != fid]
        if len(reste) == len(fils):
            return False
        _ecrire(_FILS_PATH, reste)
        items = _lire(_ITEMS_PATH, {})
        if isinstance(items, dict) and items.pop(fid, None) is not None:
            _ecrire(_ITEMS_PATH, items)
    _fusionner_cache(fid, [])
    return True


# ---- éléments --------------------------------------------------------------------------------------------------------------

_REDDIT_AUTEUR = re.compile(r"\s*submitted by\s+/?u/[\w-]+.*$", re.I | re.S)
_REDDIT_RESTES = re.compile(r"\[(?:link|comments)\]|/?\bu/[\w-]{3,20}", re.I)


def _sans_auteur(plateforme: str, texte: str) -> str:
    if plateforme == "reddit":
        texte = _REDDIT_RESTES.sub("", _REDDIT_AUTEUR.sub("", texte or ""))
    return re.sub(r"\s+", " ", texte or "").strip()


def _date_iso(v) -> str:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        try:
            return _iso(datetime.fromtimestamp(v / 1000 if v > 1e12 else v, timezone.utc))
        except (OverflowError, OSError, ValueError):
            return ""
    s = str(v or "").strip()
    for essai in (lambda: datetime.fromisoformat(s.replace("Z", "+00:00")),
                  lambda: datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y")):     # X : « Wed Oct 30 10:00:00 +0000 2026 »
        try:
            d = essai()
            return _iso((d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc))
        except ValueError:
            continue
    return ""


def _source_nom(f: dict) -> str:
    return f"{PLATEFORMES[f['plateforme']]['libelle']} · {f['nom']}"


def _items_apify(f: dict, cle: str, bruts: list) -> list[dict]:
    from app.services import apify_suite as SU
    champs = SU.CHAMPS[cle]
    images = {"instagram_posts": ["displayUrl"], "tiktok": ["videoMeta.coverUrl", "covers.default"], "x": []}[cle]
    out = []
    for it in bruts if isinstance(bruts, list) else []:
        if not isinstance(it, dict):
            continue
        texte = SU._champ(it, champs["texte"])
        if not isinstance(texte, str) or not texte.strip():
            continue
        lien = SU._lien_sans_pseudo(str(SU._champ(it, champs["url"]) or ""))[:500]
        premiere = next((l.strip() for l in texte.splitlines() if l.strip()), "")
        titre = _clean(premiere, 140) + ("…" if len(_clean(premiere, 400)) > 140 else "")
        image = SU._champ(it, images) if images else None
        out.append({"id": _hid(f["id"], lien or texte[:200]), "source_id": f["id"], "source_name": _source_nom(f),
                    "title": titre, "summary": _clean(texte), "link": lien,
                    "published": _date_iso(SU._champ(it, champs["date"])),
                    "image": image if isinstance(image, str) and image.startswith("https://") else None,
                    "plateforme": f["plateforme"]})
    return out


def _items_rss(f: dict, url: str) -> list[dict]:
    src = {"id": f["id"], "name": _source_nom(f), "url": url}
    out = []
    for it in _RSS(src):
        it = dict(it, title=_sans_auteur(f["plateforme"], it.get("title", "")),
                  summary=_sans_auteur(f["plateforme"], it.get("summary", "")), plateforme=f["plateforme"])
        out.append(it)
    return out


def _garder_items(fid: str, nouveaux: list[dict]) -> None:
    with _VERROU:
        tous = _lire(_ITEMS_PATH, {})
        tous = tous if isinstance(tous, dict) else {}
        par_id = {i["id"]: i for i in tous.get(fid, []) if isinstance(i, dict) and i.get("id")}
        par_id.update({i["id"]: i for i in nouveaux})
        tous[fid] = sorted(par_id.values(), key=lambda x: x.get("published") or "", reverse=True)[:PAR_FIL]
        _ecrire(_ITEMS_PATH, tous)


def items_actifs() -> list[dict]:
    """Les éléments des fils suivis et non en pause (news_service._refresh_blocking les ajoute à ses sources)."""
    tous = _lire(_ITEMS_PATH, {})
    actifs = {f["id"] for f in _fils() if not f.get("pause")}
    return [i for fid, l in (tous.items() if isinstance(tous, dict) else []) if fid in actifs for i in l]


def _fusionner_cache(fid: str, items: list[dict]) -> None:
    """Les éléments d'un fil remplacent les siens dans le cache de News (sans toucher fetched_at)."""
    with _VERROU:
        c = news_service._read_cache() or {}
        garde = [i for i in (c.get("items") or []) if i.get("source_id") != fid]
        tout = sorted(garde + list(items), key=lambda x: x.get("published") or "", reverse=True)[:MAX_ITEMS]
        c["items"] = tout
        news_service.cache_path.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")


# ---- relevé ----------------------------------------------------------------------------------------------------------------

def entree_apify(f: dict) -> tuple[str, dict]:
    """(clé de la liste blanche, entrée) : les publications du compte, les plus récentes."""
    h = f["identifiant"]
    if f["plateforme"] == "x":
        return "x", {"searchTerms": [f"from:{h}"], "sort": "Latest"}
    if f["plateforme"] == "instagram":
        return "instagram_posts", {"directUrls": [f"https://www.instagram.com/{h}/"]}
    return "tiktok", {"profiles": [h]}


async def devis(fid: str) -> dict | None:
    from app.services import apify as AP
    f = lire_fil(fid)
    if f is None:
        return None
    if f["lecture"] == "rss":
        return {"gratuit": True, "devis_usd": 0.0}
    cle, entree = entree_apify(f)
    try:
        d = await AP.devis(cle, f["max"], entree)
    except AP.ApifyRefus as e:
        raise RefusFil(str(e), "devis", e.code) from None
    return {"gratuit": False, "devis_usd": d, "max": f["max"], "plafond_usd": (f.get("accord") or {}).get("plafond_usd"),
            "plafond_max_usd": AP.PLAFONDS[AP.ACTEURS[cle]["usage"]], "configure": AP.configure()}


async def poser_accord(fid: str, plafond_usd, confirme_cout: bool) -> dict | None:
    """L'accord d'un fil payant : 400 (pas Apify, plafond hors bornes), 503 sans clé, 409 sans confirme_cout (le devis
    est rendu), 400 si le devis du jour dépasse le plafond choisi. Rien n'est lancé, rien n'est dépensé."""
    from app.services import apify as AP
    f = lire_fil(fid)
    if f is None:
        return None
    if f["lecture"] != "apify":
        raise RefusFil("ce fil est gratuit : aucun accord à donner", "gratuit")
    cle, _e = entree_apify(f)
    maxi = AP.PLAFONDS[AP.ACTEURS[cle]["usage"]]
    if isinstance(plafond_usd, bool) or not isinstance(plafond_usd, (int, float)) or not 0 < plafond_usd <= maxi:
        raise RefusFil(f"plafond par relevé : plus de 0 $ et au plus {maxi:.2f} $", "plafond")
    if not AP.configure():
        raise RefusFil("aucune clé Apify : posez-la dans Réglages › Clés d'API", "sans_cle", 503)
    d = (await devis(fid))["devis_usd"]
    if confirme_cout is not True:
        raise RefusFil("accord requis : le devis de chaque relevé est montré avant tout run", "confirme_cout", 409,
                       devis_usd=d, max=f["max"], plafond_max_usd=maxi)
    if d > float(plafond_usd):
        raise RefusFil(f"le devis du relevé ({d:.2f} $) dépasse le plafond choisi ({float(plafond_usd):.2f} $)",
                       "devis_depasse")
    etat = "ok" if f.get("derniere_lecture") else "jamais_lu"
    return _modifier(fid, accord={"plafond_usd": round(float(plafond_usd), 4), "devis_usd": d, "le": _iso()},
                     etat=etat, erreur=None)


def retirer_accord(fid: str) -> dict | None:
    f = lire_fil(fid)
    if f is None:
        return None
    return _modifier(fid, accord=None, etat="devis_a_accepter" if f["lecture"] == "apify" else f["etat"])


async def relever(fid: str) -> dict | None:
    """UN relevé du fil : gratuit (flux), ou payant (accord → clé → devis sous le plafond du fil → plafonds mensuels
    « news » → run borné → réel noté). Lève RefusFil, apify.SansCle / ApifyRefus / ApifyEchec, HTTPException 402."""
    from app.services import apify as AP, plafonds
    f = lire_fil(fid)
    if f is None:
        return None
    _modifier(fid, derniere_tentative=_iso())
    cout = 0.0
    if f["lecture"] == "rss":
        try:
            items = await asyncio.to_thread(_items_rss, f, normaliser(f["plateforme"], f["identifiant"])["url_flux"])
        except Exception as e:  # noqa: BLE001 — un flux illisible : dit sur le fil, jamais une trace
            _modifier(fid, etat="erreur", erreur=f"flux illisible ({type(e).__name__})")
            raise RefusFil("flux illisible : réessayez plus tard", "flux", 502) from None
    else:
        accord = f.get("accord")
        if not accord:
            _modifier(fid, etat="devis_a_accepter")
            raise RefusFil("relevé payant : acceptez d'abord le devis du fil", "devis_a_accepter", 409)
        if not AP.configure():
            _modifier(fid, etat="sans_cle")
            raise AP.SansCle("aucune clé Apify : posez-la dans Réglages › Clés d'API")
        cle, entree = entree_apify(f)
        try:
            d = await AP.devis(cle, f["max"], entree)
        except AP.ApifyRefus as e:
            _modifier(fid, etat="erreur", erreur=str(e)[:200])
            raise
        if d > accord["plafond_usd"]:
            _modifier(fid, etat="devis_depasse", erreur=None)
            raise RefusFil(f"le devis du relevé ({d:.2f} $) dépasse le plafond du fil ({accord['plafond_usd']:.2f} $)",
                           "devis_depasse", 409, devis_usd=d, plafond_usd=accord["plafond_usd"])
        try:
            garde = await plafonds.verifier({"kind": "apify", "acteur": AP.ACTEURS[cle]["acteur"], "usd": d}, "news",
                                            ref=fid)
        except Exception:
            _modifier(fid, etat="plafond_mensuel")
            raise
        lignes = (garde or {}).get("lignes") or []
        try:
            r = await AP.lancer(cle, entree, f["max"], plafond=accord["plafond_usd"])
        except Exception as e:
            perdu = float(getattr(e, "cout_usd", 0.0) or 0.0)
            await plafonds.noter_reel_lignes(lignes, perdu)
            _modifier(fid, etat="erreur", erreur=str(e)[:200] if isinstance(e, (AP.ApifyRefus, AP.ApifyEchec, AP.SansCle))
                      else f"relevé en échec ({type(e).__name__})", dernier_cout_usd=round(perdu, 6),
                      cout_cumule_usd=round(float(f.get("cout_cumule_usd") or 0) + perdu, 6))
            raise
        cout = float(r.get("cout_usd") or 0.0)
        await plafonds.noter_reel_lignes(lignes, cout)
        items = _items_apify(f, cle, r.get("items") or [])
    _garder_items(fid, items)
    _fusionner_cache(fid, items)
    fil = _modifier(fid, derniere_lecture=_iso(), dernier_nombre=len(items), dernier_cout_usd=round(cout, 6),
                    cout_cumule_usd=round(float(f.get("cout_cumule_usd") or 0) + cout, 6), etat="ok", erreur=None)
    return {"lus": len(items), "cout_usd": round(cout, 6), "fil": fil}


def _du(f: dict, maintenant: datetime) -> bool:
    t = f.get("derniere_tentative")
    if not t:
        return True
    try:
        return maintenant - datetime.fromisoformat(t) >= timedelta(hours=f["frequence_h"])
    except (TypeError, ValueError):
        return True


async def tic() -> dict:
    """Un passage de la boucle : chaque fil dû et non en pause est lu ; un fil payant sans accord n'est jamais lu (ni
    devis demandé). Rend {lus, sans_accord, refus: {id: code}}."""
    from fastapi import HTTPException
    from app.services import apify as AP
    rep = {"lus": [], "sans_accord": [], "refus": {}}
    maintenant = _maintenant()
    for f in [vue(x) for x in _fils()]:
        if f.get("pause"):
            continue
        if f["lecture"] == "apify" and not f.get("accord"):
            rep["sans_accord"].append(f["id"])
            continue
        if not _du(f, maintenant):
            continue
        try:
            await relever(f["id"])
            rep["lus"].append(f["id"])
        except RefusFil as e:
            rep["refus"][f["id"]] = e.code
        except AP.SansCle:
            rep["refus"][f["id"]] = "sans_cle"
        except HTTPException as e:
            rep["refus"][f["id"]] = "plafond_mensuel" if e.status_code == 402 else f"http_{e.status_code}"
        except Exception as e:  # noqa: BLE001 — un fil en panne n'arrête pas les autres
            rep["refus"][f["id"]] = "erreur"
            logger.warning(f"fil {f['id']} : relevé ignoré : {type(e).__name__}")
    return rep


async def boucle(premier: float = 90, intervalle: float = TIC_S) -> None:
    await asyncio.sleep(premier)
    while True:
        try:
            if _FILS_PATH().exists():
                await tic()
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 — une panne d'un passage n'arrête pas la boucle
            logger.warning(f"fils : passage ignoré : {type(e).__name__} : {e}")
        await asyncio.sleep(intervalle)


# ---- suggestions des agents -----------------------------------------------------------------------------------------------

def _suggestions() -> list[dict]:
    v = _lire(_SUG_PATH, [])
    return v if isinstance(v, list) else []


def proposer(plateforme: str, identifiant: str, raison: str, origine: dict, nom: str = "") -> dict:
    """Une SUGGESTION, jamais un abonnement. {statut: proposee | deja_proposee | deja_suivi, suggestion | fil}."""
    n = normaliser(plateforme, identifiant)
    fid = _id("fil_", n["plateforme"], n["identifiant"])
    if lire_fil(fid) is not None:
        return {"statut": "deja_suivi", "fil": lire_fil(fid)}
    sid = _id("sug_", n["plateforme"], n["identifiant"])
    with _VERROU:
        sg = _suggestions()
        for s in sg:
            if s.get("id") == sid:
                if s.get("etat") == "ecartee":
                    raise RefusFil("déjà écarté par l'utilisateur : ne pas le reproposer", "ecartee")
                if s.get("etat") == "proposee":
                    return {"statut": "deja_proposee", "suggestion": s}
                sg.remove(s)                      # acceptée puis fil retiré : proposée de nouveau
                break
        if sum(1 for s in sg if s.get("etat") == "proposee") >= MAX_SUGGESTIONS:
            raise RefusFil(f"{MAX_SUGGESTIONS} suggestions attendent déjà l'utilisateur", "trop", 409)
        s = {"id": sid, "plateforme": n["plateforme"], "identifiant": n["identifiant"],
             "nom": _clean(nom, 80) or _nom_defaut(n), "raison": _clean(raison, 300), "origine": origine,
             "cree": _iso(), "etat": "proposee", "fil_id": None}
        sg.append(s)
        _ecrire(_SUG_PATH, sg)
    return {"statut": "proposee", "suggestion": s}


def _decider(sid: str, **champs) -> dict | None:
    with _VERROU:
        sg = _suggestions()
        for s in sg:
            if s.get("id") == sid:
                s.update(champs, decide=_iso())
                _ecrire(_SUG_PATH, sg)
                return s
    return None


def accepter(sid: str, frequence_h=None) -> dict | None:
    s = next((x for x in _suggestions() if x.get("id") == sid), None)
    if s is None:
        return None
    if s.get("etat") != "proposee":
        raise RefusFil("suggestion déjà décidée", "decidee", 409)
    try:
        f = ajouter(s["plateforme"], s["identifiant"], s.get("nom"), frequence_h, origine=s.get("origine"))
    except RefusFil as e:
        if e.code != "deja_suivi":
            raise
        f = lire_fil(e.extra["fil_id"])
    _decider(sid, etat="acceptee", fil_id=f["id"])
    return f


def ecarter(sid: str) -> dict | None:
    s = next((x for x in _suggestions() if x.get("id") == sid), None)
    if s is None:
        return None
    if s.get("etat") != "proposee":
        raise RefusFil("suggestion déjà décidée", "decidee", 409)
    return _decider(sid, etat="ecartee")


def lister() -> dict:
    sg = sorted(_suggestions(), key=lambda s: (s.get("etat") != "proposee", s.get("cree") or ""), reverse=False)
    en_attente = [s for s in sg if s.get("etat") == "proposee"][::-1]
    decidees = sorted([s for s in sg if s.get("etat") != "proposee"], key=lambda s: s.get("decide") or "", reverse=True)
    return {"fils": [vue(f) for f in _fils()], "suggestions": en_attente + decidees[:20]}
