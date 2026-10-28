# -*- coding: utf-8 -*-
"""t364 (28/10/2026) — socle Apify : l'application lance un Actor de sa LISTE BLANCHE, au devis connu d'avance, sous un
PLAFOND DUR posé chez Apify (`maxTotalChargeUsd`), relève le coût réel et rend les résultats.

Aucun outil de l'agent ne s'en sert encore : t365 (leads Google Maps) et t366 (veille enrichie) s'y branchent, par la
carte « collecte » (agent_campagnes_routes). API REST (jamais la CLI : elle n'a pas de plafond de coût).
Jeton : `APIFY_TOKEN` (Réglages › Clés d'API, coffre, ou variable d'environnement), dans l'en-tête `Authorization`,
jamais dans une URL ni un message. Identifiants, builds et prix relevés le 28/10/2026 (skill veille-concurrents, t363).
Coutures de banc : _GET, _POST, _HORLOGE.
"""
from __future__ import annotations

import json
import time

from app.config import DATA_ROOT, settings

API = "https://api.apify.com/v2"
PLAFONDS = {"veille": 2.0, "leads": 1.0}       # $ par run, décision du 28/10 (§6.4)
DUREE_MAX = 600                                 # s : `timeout` du run ; au-delà de l'attente, abort
FORFAIT_CALCUL_USD = 0.05                       # un Actor gratuit consomme quand même du calcul
CACHE_S = 24 * 3600
MAX_RESULTATS = 500
MAX_TEXTE = 300
MAX_LISTE = 20
PANNES_MAX = 3
DEMARRAGE = ("start", "apify-actor-start", "actor-start-gb", "actor-start")
_SANS_PROXY_RESIDENTIEL = {"useApifyProxy": True}
_SANS_RESEAUX = {"facebooks": False, "instagrams": False, "youtubes": False, "tiktoks": False, "twitters": False}

# clé -> acteur (owner~nom), build épinglé, usage (plafond), champs autorisés, champ du nombre, entrée imposée, et
# `evenements` : les seuls événements payants que l'entrée imposée laisse partir (le devis ignore les autres).
ACTEURS = {
    "google_maps": {"acteur": "compass~crawler-google-places", "build": "0.14.777", "usage": "leads",
                    "max": "maxCrawledPlacesPerSearch",
                    "champs": {"searchStringsArray", "locationQuery", "language", "skipClosedPlaces"},
                    "impose": {"scrapePlaceDetailPage": False, "scrapeContacts": False, "scrapeDirectories": False,
                               "includeWebResults": False, "scrapeTableReservationProvider": False,
                               "scrapeOrderOnline": False, "maxQuestions": 0, "maxReviews": 0, "maxImages": 0,
                               "scrapeReviewsPersonalData": False, "scrapeImageAuthors": False,
                               "scrapeSocialMediaProfiles": _SANS_RESEAUX, "maximumLeadsEnrichmentRecords": 0,
                               "verifyLeadsEnrichmentEmails": False, "enableCompetitorAnalysis": False,
                               "website": "allPlaces", "searchMatching": "all"},
                    "evenements": {"apify-actor-start", "place-scraped"}},
    "contacts_site": {"acteur": "vdrmota~contact-info-scraper", "build": "0.2.246", "usage": "leads",
                      "max": "maxRequests", "champs": {"startUrls", "maxRequestsPerStartUrl", "maxDepth"},
                      "impose": {"sameDomain": True, "mergeContacts": True, "useBrowser": False,
                                 "waitUntil": "domcontentloaded", "proxyConfig": _SANS_PROXY_RESIDENTIEL,
                                 "scrapeSocialMediaProfiles": _SANS_RESEAUX, "maximumLeadsEnrichmentRecords": 0,
                                 "verifyLeadsEnrichmentEmails": False},
                      "evenements": {"actor-start-gb", "pages-scraped"}},
    "reddit": {"acteur": "trudax~reddit-scraper-lite", "build": "5.8.7", "usage": "veille", "max": "maxItems",
               "champs": {"searches", "searchCommunityName", "sort", "time"},
               "impose": {"skipUserPosts": True, "includeNSFW": False, "searchUsers": False, "searchCommunities": False}},
    "x": {"acteur": "apidojo~tweet-scraper", "build": "0.0.1567", "usage": "veille", "max": "maxItems",
          "champs": {"searchTerms", "sort", "tweetLanguage"}, "impose": {}},
    "instagram": {"acteur": "apify~instagram-comment-scraper", "build": "0.0.647", "usage": "veille",
                  "max": "resultsLimit", "champs": {"directUrls"}, "impose": {"includeNestedComments": False}},
    "avis_google_maps": {"acteur": "compass~Google-Maps-Reviews-Scraper", "build": "0.0.541", "usage": "veille",
                         "max": "maxReviews", "champs": {"startUrls", "placeIds", "reviewsSort", "language"},
                         "impose": {"personalData": False}},
    "google_play": {"acteur": "thewolves~google-play-reviews-scraper", "build": "0.0.988", "usage": "veille",
                    "max": "maxItems", "champs": {"appIds", "country", "language", "sort"}, "impose": {}},
    "trustpilot": {"acteur": "automation-lab~trustpilot", "build": "0.1.55", "usage": "veille",
                   "max": "maxReviewsPerCompany", "champs": {"companyUrls", "sort", "languages"},
                   "impose": {"includeCompanyInfo": False}},
    "g2": {"acteur": "automation-lab~g2-scraper", "build": "0.1.43", "usage": "veille", "max": "maxReviews",
           "champs": {"productUrls", "sortReviews"}, "impose": {"mode": "reviews"}},
    "tiktok": {"acteur": "clockworks~tiktok-scraper", "build": "0.0.625", "usage": "veille", "max": "resultsPerPage",
               "champs": {"searchQueries", "hashtags", "profiles", "videoSearchSorting", "videoSearchDateFilter",
                          "oldestPostDateUnified"},
               "impose": {"shouldDownloadVideos": False, "shouldDownloadCovers": False,
                          "shouldDownloadSlideshowImages": False, "shouldDownloadAvatars": False,
                          "shouldDownloadMusicCovers": False, "aiVideoDescription": False, "aiVideoSummary": False,
                          "downloadSubtitlesOptions": "NEVER_DOWNLOAD_SUBTITLES", "scrapeRelatedVideos": False,
                          "scrapeRelatedSearchWords": False, "scrapeAdditionalAuthorMeta": False,
                          "proxyCountryCode": "None"},
               "evenements": {"result", "actor-start"}},
    "tiktok_commentaires": {"acteur": "clockworks~tiktok-comments-scraper", "build": "0.0.481", "usage": "veille",
                            "max": "commentsPerPost", "champs": {"postURLs"}, "impose": {"maxRepliesPerComment": 0},
                            "evenements": {"result"}},
    "instagram_posts": {"acteur": "apify~instagram-scraper", "build": "0.0.831", "usage": "veille",
                        "max": "resultsLimit", "champs": {"directUrls", "onlyPostsNewerThan"},
                        "impose": {"resultsType": "posts", "addParentData": False}, "evenements": {"result"}},
}


class SansCle(RuntimeError):
    """Aucun jeton Apify : rien n'est appelé."""


class ApifyRefus(RuntimeError):
    """Refus AVANT tout run facturé (liste blanche, entrée, devis au-delà du plafond, compte Apify). `code` : le statut
    HTTP que la route rendra (422, 402, 502)."""
    def __init__(self, message: str, code: int = 422):
        super().__init__(message)
        self.code = code


class ApifyEchec(RuntimeError):
    """Le run est parti puis a échoué ; `cout_usd` : ce qu'Apify a facturé quand même."""
    def __init__(self, message: str, cout_usd: float = 0.0):
        super().__init__(message)
        self.cout_usd = float(cout_usd or 0.0)


def _jeton() -> str:
    return str(getattr(settings, "APIFY_TOKEN", "") or "").strip()


def configure() -> bool:
    return bool(_jeton())


def etat() -> dict:
    """Ce que l'écran peut savoir : prêt ou non, les plafonds. Jamais le jeton."""
    return {"configure": configure(), "plafonds_usd": dict(PLAFONDS)}


def _en_tetes(jeton: str | None) -> dict:
    return {"Content-Type": "application/json", **({"Authorization": f"Bearer {jeton}"} if jeton else {})}


async def _get(url: str, jeton: str | None = None) -> tuple[int, object]:
    import httpx
    async with httpx.AsyncClient(timeout=90.0) as c:
        r = await c.get(url, headers=_en_tetes(jeton))
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, None


async def _post(url: str, corps, jeton: str | None = None) -> tuple[int, object]:
    import httpx
    async with httpx.AsyncClient(timeout=90.0) as c:
        r = await c.post(url, headers=_en_tetes(jeton), content=json.dumps(corps if corps is not None else {}))
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, None


_GET, _POST, _HORLOGE = _get, _post, time.monotonic       # coutures du banc


def _acteur(cle: str) -> dict:
    if cle not in ACTEURS:
        raise ApifyRefus(f"Actor hors liste blanche : {str(cle)[:40]}", 422)
    return ACTEURS[cle]


def _propre(message, jeton: str) -> str:
    m = str(message or "")[:200]
    return m.replace(jeton, "***") if jeton else m


def _cache(cle: str):
    return DATA_ROOT / "cache" / "apify" / f"{cle}.json"


def vider_cache() -> None:
    d = DATA_ROOT / "cache" / "apify"
    for f in d.glob("*.json") if d.exists() else []:
        f.unlink(missing_ok=True)


async def _tarif(cle: str) -> dict:
    """L'enregistrement de prix en vigueur (le dernier de `pricingInfos`), gardé 24 h."""
    a = _acteur(cle)
    f = _cache(cle)
    try:
        c = json.loads(f.read_text(encoding="utf-8"))
        if time.time() - float(c["t"]) < CACHE_S:
            return c["pi"]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        statut, j = await _GET(f"{API}/acts/{a['acteur']}")
    except Exception as e:  # noqa: BLE001 — réseau : dit, sans rien d'autre
        raise ApifyRefus(f"prix d'Apify illisibles ({type(e).__name__})", 502) from None
    infos = (((j or {}).get("data") or {}).get("pricingInfos") if isinstance(j, dict) else None) or []
    if statut != 200 or not infos:
        raise ApifyRefus(f"prix d'Apify illisibles pour {a['acteur']} (HTTP {statut})", 502)
    pi = infos[-1]
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"t": time.time(), "pi": pi}), encoding="utf-8")
    return pi


def _borne(n) -> int:
    return max(1, min(int(n or 1), MAX_RESULTATS))


async def devis(cle: str, n: int) -> float:
    """Estimation haute en $ de N résultats (palier le plus cher ; seuls les événements permis)."""
    a = _acteur(cle)
    n = _borne(n)
    pi = await _tarif(cle)
    modele = pi.get("pricingModel")
    if modele == "FLAT_PRICE_PER_MONTH":
        raise ApifyRefus("Actor au forfait mensuel : refusé", 422)
    if modele == "PRICE_PER_DATASET_ITEM":
        return round(float(pi.get("pricePerUnitUsd") or 0) * n, 6)
    if modele == "FREE":
        return FORFAIT_CALCUL_USD
    total, permis = 0.0, a.get("evenements")
    for nom, ev in ((pi.get("pricingPerEvent") or {}).get("actorChargeEvents") or {}).items():
        if permis is not None and nom not in permis:
            continue
        prix = ev.get("eventPriceUsd")
        if prix is None:
            prix = max((t.get("tieredEventPriceUsd", 0) for t in (ev.get("eventTieredPricingUsd") or {}).values()),
                       default=0)
        total += float(prix) * (1 if nom in DEMARRAGE else n)
    return round(total, 6)


async def op(cle: str, n: int) -> dict:
    """L'op chiffrée par pricing (plafonds) : le devis tel quel."""
    return {"kind": "apify", "acteur": _acteur(cle)["acteur"], "usd": await devis(cle, n)}


def _valeur_sure(v) -> bool:
    if isinstance(v, bool) or isinstance(v, int):
        return True
    if isinstance(v, str):
        return len(v) <= MAX_TEXTE
    if isinstance(v, list):
        return len(v) <= MAX_LISTE and all(_valeur_sure(x) for x in v)
    if isinstance(v, dict):                         # startUrls : [{"url": ...}]
        return set(v) <= {"url"} and _valeur_sure(v.get("url", ""))
    return False


def filtrer(cle: str, entree: dict, n: int) -> dict:
    """L'entrée envoyée : seuls les champs autorisés (un autre champ = refus nommé), bornés, puis l'imposé et N."""
    a = _acteur(cle)
    entree = entree if isinstance(entree, dict) else {}
    hors = sorted(k for k in entree if k not in a["champs"])
    if hors:
        raise ApifyRefus(f"champ(s) d'entrée non autorisé(s) pour {cle} : {', '.join(hors)[:120]}", 422)
    for k, v in entree.items():
        if not _valeur_sure(v):
            raise ApifyRefus(f"valeur illisible ou trop longue pour {k}", 422)
    propre = dict(entree)
    propre.update(a["impose"])
    propre[a["max"]] = _borne(n)
    return propre


async def lancer(cle: str, entree: dict, n: int, plafond: float | None = None) -> dict:
    """UN run borné : {items, cout_usd, statut, partiel, run_id, devis_usd}. SansCle, ApifyRefus, ApifyEchec.
    Une panne après le lancement relit le run par son id ; il n'est JAMAIS relancé (pas de double facturation)."""
    a = _acteur(cle)
    n = _borne(n)
    corps = filtrer(cle, entree, n)
    plafond_usage = PLAFONDS[a["usage"]]
    plafond = min(float(plafond), plafond_usage) if plafond else plafond_usage
    d = await devis(cle, n)
    if d > plafond:
        raise ApifyRefus(f"devis {d:.2f} $ au-delà du plafond {plafond:.2f} $ : réduire le nombre de résultats", 402)
    jeton = _jeton()
    if not jeton:
        raise SansCle("aucune clé Apify : posez-la dans Réglages › Clés d'API")
    q = f"build={a['build']}&maxTotalChargeUsd={plafond}&maxItems={n}&timeout={DUREE_MAX}&waitForFinish=60"
    try:
        statut, j = await _POST(f"{API}/acts/{a['acteur']}/runs?{q}", corps, jeton)
    except Exception as e:  # noqa: BLE001
        raise ApifyRefus(f"Apify injoignable ({type(e).__name__})", 502) from None
    run = ((j or {}).get("data") if isinstance(j, dict) else None) or None
    if statut not in (200, 201) or not run:
        err = ((j or {}).get("error") or {}) if isinstance(j, dict) else {}
        if statut == 402:
            raise ApifyRefus(f"compte Apify : crédit insuffisant ({_propre(err.get('type'), jeton)})", 402)
        raise ApifyRefus(f"run refusé par Apify (HTTP {statut}) : {_propre(err.get('message'), jeton)}", 502)
    rid, fin, partiel, pannes = run.get("id"), _HORLOGE() + DUREE_MAX + 60, False, 0
    while run.get("status") in ("READY", "RUNNING"):
        if _HORLOGE() > fin or pannes >= PANNES_MAX:
            try:
                await _POST(f"{API}/actor-runs/{rid}/abort", None, jeton)
            except Exception:  # noqa: BLE001 — l'abort est un effort ; timeout=600 l'arrête de toute façon
                pass
            partiel = True
            break
        try:
            statut, j = await _GET(f"{API}/actor-runs/{rid}?waitForFinish=60", jeton)
            run = ((j or {}).get("data") if isinstance(j, dict) else None) or run
        except Exception:  # noqa: BLE001 — relu au tour suivant, jamais relancé
            pannes += 1
    items = []
    try:
        _s, li = await _GET(f"{API}/datasets/{run.get('defaultDatasetId')}/items?clean=true&format=json&limit={n}", jeton)
        items = [x for x in li if isinstance(x, dict)][:n] if isinstance(li, list) else []
    except Exception:  # noqa: BLE001
        partiel = True
    try:
        _s, j = await _GET(f"{API}/actor-runs/{rid}", jeton)
        run = ((j or {}).get("data") if isinstance(j, dict) else None) or run
    except Exception:  # noqa: BLE001
        pass
    cout = run.get("usageTotalUsd")
    cout = float(cout) if isinstance(cout, (int, float)) else d
    if run.get("status") == "FAILED" and not items:
        raise ApifyEchec(f"le run Apify a échoué ({a['acteur']})", cout)
    return {"items": items, "cout_usd": round(cout, 6), "statut": run.get("status"), "run_id": rid, "devis_usd": d,
            "partiel": partiel or run.get("status") != "SUCCEEDED"}
