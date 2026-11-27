# -*- coding: utf-8 -*-
"""t513 (RV3, 26/11/2026) — référence donnée par un LIEN : plateforme, métadonnées publiques, sous-titres YouTube.

Spec docs/superpowers/specs/2026-11-13-reel-reference-design.md, § 4.2 (ce que chaque plateforme permet), R2, R11.

R2 : l'application NE TÉLÉCHARGE JAMAIS la vidéo d'autrui. Un lien donne :
- sa plateforme et son identifiant (`reconnaitre`, pur) ;
- ses métadonnées publiques par oEmbed quand la plateforme l'ouvre sans compte (YouTube, TikTok, X) : titre, auteur,
  vignette (adresse seulement, jamais téléchargée) ; Instagram et Facebook exigent un jeton d'application Meta
  (décision D7 en attente) : rien n'est lu, et l'écran le dit ;
- sur YouTube, les SOUS-TITRES publics (manuels, sinon automatiques) par yt-dlp `--dump-json` puis la piste de
  sous-titres seule : jamais l'image ni le son.
Le lien seul ne suffit pas à une recette (pas d'images ni de son) : l'inspiration créée (matière « lien ») porte le
message « fournissez un enregistrement d'écran, son activé » (`besoin_capture`). Les sous-titres lus deviennent le
texte capté (garde anti-copie des contenus refaits). Tout est gratuit.

« Mes recettes » : `recettes(espace)` liste les recettes rangées par RV2 dans `DATA_ROOT/espaces/<id>/recettes/`.

Coutures des bancs : `_GET_JSON` (url -> dict), `_GET_TEXTE` (url -> str), `_YTDLP_INFO` (url -> dict).
"""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from urllib.parse import parse_qs, quote, urlparse

from loguru import logger

from app.services import inspiration as I

MATIERE = "lien"
DELAI_S = 20.0
DELAI_YTDLP = 60.0
MAX_SOUSTITRES = I.MAX_TEXTE
MAX_RECETTES = 100

PLATEFORMES = ("instagram", "tiktok", "youtube", "x", "facebook", "linkedin")
OEMBED = {
    "youtube": "https://www.youtube.com/oembed?format=json&url=",
    "tiktok": "https://www.tiktok.com/oembed?url=",
    "x": "https://publish.twitter.com/oembed?omit_script=1&url=",
}
# ce que la plateforme rend au lien seul, sans compte (§ 4.2) ; « jeton » = oEmbed derrière une application Meta (D7)
OUVERT = {"youtube": "oembed", "tiktok": "oembed", "x": "oembed", "instagram": "jeton", "facebook": "jeton",
          "linkedin": "rien"}

_HOTES = {
    "instagram": ("instagram.com",), "tiktok": ("tiktok.com",), "youtube": ("youtube.com", "youtu.be"),
    "x": ("x.com", "twitter.com"), "facebook": ("facebook.com", "fb.watch"), "linkedin": ("linkedin.com",),
}


# ---- pur --------------------------------------------------------------------------------------------------------------

def reconnaitre(url: str) -> dict:
    """{plateforme, id, lien} ; plateforme « » si le lien n'est d'aucune plateforme connue. ValueError si ce n'est pas
    une adresse http(s)."""
    brut = str(url or "").strip()
    if len(brut) > I.MAX_SOURCE:
        raise I.RefusInspiration("Lien trop long : 300 caractères au plus.", "lien")
    u = urlparse(brut)
    if u.scheme not in ("http", "https") or not u.netloc:
        raise I.RefusInspiration("Lien attendu : une adresse qui commence par https://", "lien")
    hote = u.netloc.lower().split("@")[-1].split(":")[0]
    hote = hote[4:] if hote.startswith("www.") else hote
    hote = hote[2:] if hote.startswith("m.") else hote
    plateforme = next((p for p, hs in _HOTES.items() if any(hote == h or hote.endswith("." + h) for h in hs)), "")
    chemin = [x for x in u.path.split("/") if x]
    ident = ""
    if plateforme == "instagram" and len(chemin) >= 2 and chemin[0] in ("reel", "reels", "p", "tv"):
        ident = chemin[1]
    elif plateforme == "tiktok":
        ident = next((chemin[i + 1] for i, x in enumerate(chemin[:-1]) if x == "video"), "")
    elif plateforme == "youtube":
        if hote == "youtu.be" and chemin:
            ident = chemin[0]
        elif chemin[:1] in (["shorts"], ["live"], ["embed"]) and len(chemin) >= 2:
            ident = chemin[1]
        else:
            ident = (parse_qs(u.query).get("v") or [""])[0]
    elif plateforme == "x":
        ident = next((chemin[i + 1] for i, x in enumerate(chemin[:-1]) if x == "status"), "")
    ident = re.sub(r"[^A-Za-z0-9_-]", "", ident)[:64]
    propre = f"{u.scheme}://{u.netloc}{u.path}" + (f"?v={ident}" if plateforme == "youtube" and "v=" in u.query else "")
    return {"plateforme": plateforme, "id": ident, "lien": propre[:I.MAX_SOURCE]}


def lire_vtt(texte: str) -> list[dict]:
    """Une piste WebVTT -> [{debut, texte}] ; balises retirées, lignes répétées des sous-titres automatiques fusionnées."""
    out, vus = [], []
    debut = None
    for ligne in str(texte or "").splitlines():
        ligne = ligne.strip()
        m = re.match(r"^(\d{1,2}:)?(\d{2}):(\d{2})[.,](\d{3})\s+-->", ligne)
        if m:
            h = int((m.group(1) or "0:")[:-1])
            debut = h * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(4)) / 1000
            continue
        if not ligne or debut is None or ligne.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        t = re.sub(r"<[^>]+>", "", ligne).strip()
        t = re.sub(r"\s+", " ", t)
        if not t or (vus and t == vus[-1]):
            continue
        vus.append(t)
        out.append({"debut": round(debut, 2), "texte": t})
    return out


def texte_horodate(blocs: list[dict], tranche: float = 30.0) -> str:
    """Les sous-titres en lignes `[mm:ss] texte`, une par tranche."""
    lignes, cle, cour = [], None, []
    for b in blocs:
        k = int(b["debut"] // tranche)
        if cle is not None and k != cle:
            lignes.append((cle, cour)); cour = []
        cle = k
        cour.append(b["texte"])
    if cour:
        lignes.append((cle, cour))
    return "\n".join(f"[{int(k * tranche) // 60:02d}:{int(k * tranche) % 60:02d}] {' '.join(c)}" for k, c in lignes)


def choisir_piste(info: dict, langues: tuple) -> tuple[str, str, str] | None:
    """(url, langue, genre) de la meilleure piste VTT : manuelle avant automatique, dans l'ordre des langues."""
    for genre, cle in (("manuels", "subtitles"), ("automatiques", "automatic_captions")):
        pistes = info.get(cle) or {}
        if not isinstance(pistes, dict):
            continue
        ordre = [l for l in langues if l in pistes] + [l for l in pistes if l.split("-")[0] in langues and l not in langues]
        for l in ordre:
            for f in pistes.get(l) or []:
                if isinstance(f, dict) and f.get("ext") == "vtt" and str(f.get("url") or "").startswith("https://"):
                    return f["url"], l, genre
    return None


# ---- réseau (coutures) ------------------------------------------------------------------------------------------------

async def _get_json_defaut(url: str) -> dict:
    import httpx
    from app.config import SSL_VERIFY
    async with httpx.AsyncClient(timeout=DELAI_S, verify=SSL_VERIFY, follow_redirects=True) as c:
        r = await c.get(url, headers={"User-Agent": "DeepotusVideo"})
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")
    return r.json()


async def _get_texte_defaut(url: str) -> str:
    import httpx
    from app.config import SSL_VERIFY
    async with httpx.AsyncClient(timeout=DELAI_S, verify=SSL_VERIFY, follow_redirects=True) as c:
        r = await c.get(url, headers={"User-Agent": "DeepotusVideo"})
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")
    return r.text[:2_000_000]


async def _ytdlp_info_defaut(url: str) -> dict:
    """Les métadonnées yt-dlp (`--dump-json --skip-download`) : jamais l'image ni le son."""
    from app.services import veille_collecte as VC
    cmd = VC._ytdlp_commande()
    if not cmd:
        raise FileNotFoundError("yt-dlp")
    p = await asyncio.create_subprocess_exec(*cmd, "--dump-json", "--skip-download", "--no-playlist", "--", url,
                                             stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, _err = await asyncio.wait_for(p.communicate(), DELAI_YTDLP)
    except asyncio.TimeoutError:
        p.kill()
        raise RuntimeError("yt-dlp") from None
    if p.returncode != 0:
        raise RuntimeError("yt-dlp")
    return json.loads(out.decode("utf-8", "replace") or "{}")


_GET_JSON = _get_json_defaut
_GET_TEXTE = _get_texte_defaut
_YTDLP_INFO = _ytdlp_info_defaut


# ---- lecture d'un lien ------------------------------------------------------------------------------------------------

async def _oembed(plateforme: str, lien: str) -> dict:
    base = OEMBED.get(plateforme)
    if not base:
        return {}
    try:
        j = await _GET_JSON(base + quote(lien, safe=""))
    except Exception as e:  # noqa: BLE001 — une métadonnée absente n'empêche rien
        logger.info(f"inspiration : oEmbed {plateforme} indisponible ({type(e).__name__})")
        return {}
    if not isinstance(j, dict):
        return {}
    titre = I._texte(j.get("title"), 300)
    if not titre and plateforme == "x":
        titre = I._texte(re.sub(r"<[^>]+>", " ", str(j.get("html") or "")).split("&mdash;")[0], 300)
    vignette = str(j.get("thumbnail_url") or "")
    return {"titre": " ".join(titre.split()), "auteur": I._texte(j.get("author_name"), 120),
            "vignette": vignette if vignette.startswith("https://") else ""}


async def _soustitres_youtube(lien: str, langue: str) -> dict:
    langues = ("fr", "en") if langue != "en" else ("en", "fr")
    try:
        info = await _YTDLP_INFO(lien)
    except FileNotFoundError:
        return {"etat": "sans_outil"}
    except Exception as e:  # noqa: BLE001
        logger.info(f"inspiration : yt-dlp en échec ({type(e).__name__})")
        return {"etat": "echec"}
    piste = choisir_piste(info if isinstance(info, dict) else {}, langues)
    meta = {"duree_s": info.get("duration") if isinstance(info, dict) else None,
            "compteurs": {k: info.get(k) for k in ("view_count", "like_count", "comment_count")
                          if isinstance(info, dict) and isinstance(info.get(k), int)} or None}
    if not piste:
        return {"etat": "aucun", **meta}
    try:
        blocs = lire_vtt(await _GET_TEXTE(piste[0]))
    except Exception as e:  # noqa: BLE001
        logger.info(f"inspiration : piste de sous-titres illisible ({type(e).__name__})")
        return {"etat": "echec", **meta}
    texte = texte_horodate(blocs)[:MAX_SOUSTITRES]
    return {"etat": "lus" if texte else "aucun", "langue": piste[1], "genre": piste[2], "texte": texte,
            "blocs": len(blocs), **meta}


async def capter_lien(*, url: str, espace_id: str, source_libelle: str = "", langue: str = "fr") -> dict:
    """Crée l'inspiration « lien » : plateforme, métadonnées, sous-titres YouTube ; jamais la vidéo."""
    r = reconnaitre(url)
    pl = r["plateforme"]
    meta = await _oembed(pl, r["lien"]) if OUVERT.get(pl) == "oembed" else {}
    st = await _soustitres_youtube(r["lien"], langue) if pl == "youtube" else {"etat": "non_ouvert"}
    texte = st.get("texte") or ""
    iid = uuid.uuid4().hex
    maintenant = I._maintenant()
    rec = {"id": iid, "espace_id": espace_id, "cree": maintenant, "langue": langue if langue in ("fr", "en") else "fr",
           "matiere": MATIERE,
           "source": {"libelle": I._texte(source_libelle or meta.get("titre"), I.MAX_SOURCE), "lien": r["lien"],
                      "le": maintenant, "plateforme": pl, "ident": r["id"], "auteur": meta.get("auteur") or "",
                      "titre": meta.get("titre") or "", "vignette": meta.get("vignette") or "",
                      "compteurs": st.get("compteurs"), "compteurs_verifies": False},
           "texte_capte": texte, "texte_colle": False, "ocr": {"moteur": "", "mots": 0, "raison": ""}, "palette": [],
           "lien": {"acces": OUVERT.get(pl, "rien"), "soustitres": {k: v for k, v in st.items() if k != "texte"},
                    "besoin_capture": True},
           "analyse": None, "redaction": None, "brouillons": []}
    I._ecrire(rec)
    logger.info(f"inspiration {iid[:8]} : lien {pl or 'inconnu'}, métadonnées {'oui' if meta else 'non'}, "
                f"sous-titres {st.get('etat')}, {len(texte.split())} mot(s)")
    return rec


# ---- « mes recettes » -------------------------------------------------------------------------------------------------

def recettes(espace_id: str) -> list[dict]:
    """Les recettes de l'espace, les plus récentes d'abord, en vue courte (pour la liste et le compagnon)."""
    from app.services import espaces
    if not espaces.id_valide(espace_id):
        return []
    d = espaces.dossier() / espace_id / "recettes"
    if not d.is_dir():
        return []
    out = []
    for f in d.glob("*.json"):
        if not I._ID.match(f.stem):
            continue
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(r, dict):
            continue
        src = r.get("source") or {}
        out.append({"id": f.stem, "lu_le": r.get("lu_le") or "", "plateforme": src.get("plateforme") or "",
                    "libelle": src.get("libelle") or "", "duree_s": (r.get("format") or {}).get("duree_s"),
                    "tableaux": (r.get("rythme") or {}).get("tableaux"),
                    "mots_par_minute": (r.get("rythme") or {}).get("mots_par_minute"),
                    "briques": [b.get("role") for b in r.get("structure") or []],
                    "appel": (r.get("appel") or {}).get("type") or ""})
    out.sort(key=lambda x: x["lu_le"], reverse=True)
    return out[:MAX_RECETTES]
