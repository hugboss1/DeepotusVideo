# -*- coding: utf-8 -*-
"""Avatar live G0 (t161, 10/10/2026) — le socle du Direct : Personnages (images de référence + voix + consentement)
et sessions Decart Lucy 2.5 bornées. Spec : docs/superpowers/specs/2026-10-10-higgsfield-genjutsu-inventaire.md.

Relevé le 10/10 dans @decartai/sdk 0.2.8 et la doc Decart :
  - le flux vidéo va du navigateur (ou du téléphone) à Decart EN DIRECT, par WebRTC : le backend ne voit jamais une
    image ; il ne fait que frapper un jeton client (POST /v1/client/tokens, en-tête X-API-KEY) ;
  - un jeton expiré n'arrête PAS une session déjà ouverte — seul `constraints.realtime.maxSessionDuration` la borne.
    C'est donc lui qui porte le plafond : la garde réserve le devis de la durée ENTIÈRE, Decart coupe à la borne ;
  - Lucy 2.5 : 0,02 $/s, 0,04 $/s en mode rapide, à la seconde de génération active. La fin de session note le réel
    (secondes rapportées, bornées) à la place du devis.

Les Personnages vivent dans DATA_ROOT/personnages/<id>/ : fiche.json + ref_<n>.png (ré-encodés par Pillow : aucun
octet reçu n'est écrit tel quel). Les sessions vivent EN MÉMOIRE (une session dure au plus 30 minutes ; un
redémarrage les oublie et laisse le devis, sens sûr pour un plafond)."""
import base64
import io
import json
import re
import secrets as _secrets
import shutil
import time
from datetime import datetime

import httpx
from loguru import logger

from app.config import DATA_ROOT, SSL_VERIFY, settings

BASE_URL = "https://api.decart.ai"
MODELE = "lucy-2.5"
DUREE_MIN_S = 10            # minimum de maxSessionDuration chez Decart
DUREE_MAX_S = 1800          # 30 minutes : au-delà, on rouvre une session (et la garde repasse)
DUREE_DEFAUT_S = 300
TTL_JETON_S = 60            # le temps de se connecter ; n'arrête pas la session
IMAGES_MAX = 8
COTE_MIN_PX = 256           # Decart recommande 512 ; sous 256 le visage est illisible
COTE_MAX_PX = 2048          # ré-échantillonné au-delà
TEXTE_CONSENTEMENT = ("J'ai le droit d'utiliser ce visage et cette voix : ce sont les miens, ou la personne m'a donné "
                      "son accord pour les cloner.")

_RACINE = DATA_ROOT / "personnages"
_ID = re.compile(r"^[a-f0-9]{16}$")

#: session_id -> {personnage_id, duree_s, prix_usd_s, ref, appareil (id ou None pour le PC), ouverte}
_SESSIONS: dict[str, dict] = {}
#: t168f : les sessions fal closes (15 min) — la page et le relais peuvent clore dans n'importe quel ordre
_CLOSES: dict[str, dict] = {}


class Refus(Exception):
    """Refus métier : (statut HTTP, message)."""

    def __init__(self, statut: int, message: str):
        super().__init__(message)
        self.statut = statut
        self.message = message


def prix_usd_s(rapide: bool = False, fournisseur: str = "decart") -> float:
    from app.services import pricing as _pricing
    p = _pricing.load()
    if fournisseur == "fal":       # t168f : pas de mode rapide chez fal
        return float(p.get("fal_lucy_realtime_usd_per_s", 0.02))
    base = float(p.get("decart_realtime_usd_per_s", 0.02))
    return base * (2 if rapide else 1)


def borner_duree(v) -> int:
    """Durée demandée -> secondes entières dans [10, 1800] ; illisible -> 300."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return DUREE_DEFAUT_S
    if f != f or f in (float("inf"), float("-inf")):
        return DUREE_DEFAUT_S
    return int(max(DUREE_MIN_S, min(DUREE_MAX_S, round(f))))


def cle_presente() -> bool:
    return bool((getattr(settings, "DECART_API_KEY", "") or "").strip())


def cle_fal_presente() -> bool:
    return bool((getattr(settings, "FAL_KEY", "") or "").strip())


def fournisseurs() -> dict:
    """t168f : qui peut porter le Direct. Decart d'abord quand sa clé est là (mode rapide, borne chez Decart),
    fal sinon (la clé fal seule suffit)."""
    d, f = cle_presente(), cle_fal_presente()
    return {"decart": d, "fal": f, "defaut": "decart" if d else ("fal" if f else None)}


def choisir_fournisseur(demande) -> str:
    fo = fournisseurs()
    if demande in (None, ""):
        if fo["defaut"] is None:
            raise Refus(409, "Aucune clé pour le Direct : posez une clé fal (FAL_KEY, fal.ai) ou une clé Decart "
                             "(DECART_API_KEY, platform.decart.ai) — rien n'a été lancé.")
        return fo["defaut"]
    if demande not in ("decart", "fal"):
        raise Refus(400, "Fournisseur du Direct : « decart » ou « fal ».")
    if not fo[demande]:
        raise Refus(409, ("Clé Decart absente (DECART_API_KEY) : l'écran Direct la demande à sa première ouverture "
                          "(console : platform.decart.ai)" if demande == "decart" else
                          "Clé fal absente (FAL_KEY, Réglages → clés API)") + " — rien n'a été lancé.")
    return demande


# ── Personnages ─────────────────────────────────────────────────────────────────────────────────────────────────────

def _dossier(pid: str):
    if not isinstance(pid, str) or not _ID.match(pid):
        return None
    d = _RACINE / pid
    return d if (d / "fiche.json").is_file() else None


def _image_png(b64: str) -> bytes:
    from PIL import Image, UnidentifiedImageError
    try:
        brut = base64.b64decode(b64 or "", validate=False)
    except (ValueError, TypeError):
        raise Refus(415, "Image illisible (base64 invalide).")
    try:
        im = Image.open(io.BytesIO(brut))
        im.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise Refus(415, "Ces octets ne sont pas une image (PNG, JPEG ou WebP).")
    w, h = im.size
    if min(w, h) < COTE_MIN_PX:
        raise Refus(400, f"Image trop petite ({w}×{h}) : {COTE_MIN_PX} px au moins sur le petit côté (512 conseillés).")
    im = im.convert("RGB")
    if max(w, h) > COTE_MAX_PX:
        im.thumbnail((COTE_MAX_PX, COTE_MAX_PX))
    out = io.BytesIO()
    im.save(out, "PNG")
    return out.getvalue()


def _publique(f: dict) -> dict:
    return {"id": f["id"], "nom": f["nom"], "images": f["images"], "voix": f.get("voix") or {},
            "consentement": f["consentement"], "cree": f["cree"]}


def creer_personnage(corps: dict, origine: str = "pc") -> dict:
    corps = corps if isinstance(corps, dict) else {}
    if corps.get("consentement") is not True:
        raise Refus(400, "Consentement requis : cochez « " + TEXTE_CONSENTEMENT + " »")
    nom = re.sub(r"\s+", " ", str(corps.get("nom") or "")).strip()[:60] or "Personnage"
    images = corps.get("images")
    if not isinstance(images, list) or not images:
        raise Refus(400, "Au moins une image de référence (visage de face, bien éclairé).")
    if len(images) > IMAGES_MAX:
        raise Refus(400, f"{IMAGES_MAX} images au plus.")
    pngs = [_image_png(b) for b in images]          # tout est vérifié AVANT d'écrire quoi que ce soit
    voix = corps.get("voix") if isinstance(corps.get("voix"), dict) else {}
    voix = {k: str(voix.get(k))[:80] for k in ("fournisseur", "voice_id") if voix.get(k)}
    pid = _secrets.token_hex(8)
    d = _RACINE / pid
    d.mkdir(parents=True, exist_ok=False)
    for i, b in enumerate(pngs):
        (d / f"ref_{i}.png").write_bytes(b)
    fiche = {"id": pid, "nom": nom, "images": len(pngs), "voix": voix, "cree": datetime.now().isoformat(timespec="seconds"),
             "consentement": {"texte": TEXTE_CONSENTEMENT, "le": datetime.now().isoformat(timespec="seconds"),
                              "origine": origine}}
    (d / "fiche.json").write_text(json.dumps(fiche, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"avatar_live: Personnage {pid} « {nom} » ({len(pngs)} images, consentement {origine})")
    return _publique(fiche)


def lire_personnage(pid: str) -> dict | None:
    d = _dossier(pid)
    if d is None:
        return None
    try:
        return _publique(json.loads((d / "fiche.json").read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError):
        return None


def lister_personnages() -> list[dict]:
    if not _RACINE.is_dir():
        return []
    out = [lire_personnage(p.name) for p in _RACINE.iterdir() if p.is_dir()]
    return sorted([f for f in out if f], key=lambda f: f["cree"])


def chemin_image(pid: str, n) -> str | None:
    f = lire_personnage(pid)
    try:
        n = int(n)
    except (TypeError, ValueError):
        return None
    if f is None or not 0 <= n < f["images"]:
        return None
    p = _RACINE / pid / f"ref_{n}.png"
    return str(p) if p.is_file() else None


def poser_voix(pid: str, voix: dict) -> dict:
    """G2 (t163) : rattache une voix (clonée ou choisie) au Personnage, en réécrivant fiche.json."""
    d = _dossier(pid)
    if d is None:
        raise Refus(404, "Personnage inconnu.")
    f = json.loads((d / "fiche.json").read_text(encoding="utf-8"))
    f["voix"] = {k: v for k, v in (voix or {}).items() if k in ("fournisseur", "voice_id", "clonee", "le", "verification")}
    tmp = d / "fiche.json.tmp"
    tmp.write_text(json.dumps(f, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(d / "fiche.json")
    return _publique(f)


def supprimer_personnage(pid: str) -> bool:
    d = _dossier(pid)
    if d is None:
        return False
    shutil.rmtree(d)
    return True


# ── Sessions ────────────────────────────────────────────────────────────────────────────────────────────────────────

async def _poster(url: str, entetes: dict, corps: dict) -> tuple[int, dict]:
    """Le SEUL appel réseau du module (remplacé par les bancs)."""
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=20) as c:
        r = await c.post(url, headers=entetes, json=corps)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {"detail": r.text[:200]}


_MODELE_RVC = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def preparer_voix(voix, personnage: dict | None) -> dict | None:
    """G5 (t166) : la voix en direct demandée à l'ouverture. None = la voix du micro telle quelle."""
    if not isinstance(voix, dict) or not voix.get("moteur"):
        return None
    if voix["moteur"] == "cloud":
        if not (getattr(settings, "ELEVENLABS_API_KEY", "") or "").strip():
            raise Refus(409, "Clé ElevenLabs absente (Réglages → clés API) : la voix en direct par le cloud est indisponible.")
        vid = str(voix.get("voice_id") or ((personnage or {}).get("voix") or {}).get("voice_id") or "").strip()[:80]
        if not vid:
            raise Refus(400, "Voix en direct : ce Personnage n'a pas de voix (clonez-la dans l'onglet Personnages).")
        return {"moteur": "cloud", "voice_id": vid}
    if voix["moteur"] == "local":
        m = str(voix.get("modele") or "")
        if not _MODELE_RVC.match(m):
            raise Refus(400, "Voix locale : choisissez une voix RVC entraînée (Voixbox).")
        try:
            tr = max(-12, min(12, int(voix.get("transpose") or 0)))
        except (TypeError, ValueError):
            tr = 0
        return {"moteur": "local", "modele": m, "transpose": tr}
    raise Refus(400, "Voix en direct : moteur « cloud » ou « local ».")


def preparer_session(personnage_id: str, duree_s, rapide: bool = False, voix=None, fournisseur=None) -> dict:
    """Vérifie tout ce qui ne coûte rien (clé, Personnage) et rend l'op d'estimation : la route passe la garde du
    plafond ENTRE ce contrôle et `ouvrir_session_direct`."""
    fo = choisir_fournisseur(fournisseur)
    if fo == "fal" and rapide:
        raise Refus(400, "Le mode rapide n'existe que chez Decart : décochez-le pour un Direct par fal.")
    f = lire_personnage(personnage_id)
    if f is None:
        raise Refus(404, "Personnage inconnu.")
    duree = borner_duree(duree_s)
    v = preparer_voix(voix, f)
    op = {"kind": "direct", "seconds": duree, "rapide": bool(rapide), "fournisseur": fo}
    if v and v["moteur"] == "cloud":
        # UNE garde pour l'image et la voix (un seul dialogue de plafond) ; les lignes sont rattachées séparément
        op = {"kind": "campaign", "ops": [op, {"kind": "voix_sts", "duration_s": float(duree)}]}
    sid = _secrets.token_hex(12)
    return {"personnage": f, "duree_s": duree, "rapide": bool(rapide), "voix": v, "op": op, "fournisseur": fo,
            "session_id": sid, "ref": (f"fal-direct:{sid}" if fo == "fal" else f"decart:{sid}")}


async def ouvrir_session_direct(prep: dict, lignes: list, appareil: str | None) -> dict:
    """Frappe le jeton client chez Decart, borné à la durée réservée. Un refus de Decart remet la réservation à
    0 $ réel (rien n'a été consommé) et lève 502."""
    from app.services import plafonds as _plaf
    if prep.get("fournisseur") == "fal":
        return await _ouvrir_session_fal(prep, lignes, appareil)
    sid = prep["session_id"]
    ref = f"decart:{sid}"
    voix = prep.get("voix")
    # l'ordre des lignes est celui du devis : decart d'abord, la voix ensuite (lignes à 0 $ non écrites)
    await _plaf.rattacher(lignes[:1], ref)
    if voix and voix["moteur"] == "cloud" and len(lignes) > 1:
        await _plaf.rattacher(lignes[1:2], f"voixlive:{sid}")
    corps = {"expiresIn": TTL_JETON_S, "allowedModels": [MODELE],
             "constraints": {"realtime": {"maxSessionDuration": prep["duree_s"]}}}
    try:
        statut, rep = await _poster(f"{BASE_URL}/v1/client/tokens",
                                    {"X-API-KEY": settings.DECART_API_KEY.strip(), "content-type": "application/json"},
                                    corps)
    except httpx.HTTPError as e:
        statut, rep = 0, {"detail": type(e).__name__}
    jeton = rep.get("apiKey") if isinstance(rep, dict) else None
    if statut != 200 or not isinstance(jeton, str) or not jeton:
        await _plaf.noter_reel(ref, 0.0, 0.0)
        if voix and voix["moteur"] == "cloud":
            await _plaf.noter_reel(f"voixlive:{sid}", 0.0, 0.0)
        # relevé le 10/10 sur le vrai Decart : une clé refusée rend 401 {"error": "Invalid or expired API key"}
        detail = ((rep.get("detail") or rep.get("error")) if isinstance(rep, dict) else "") or ""
        raise Refus(502, f"Decart a refusé le jeton (HTTP {statut}) : {str(detail)[:120]} — rien n'a été facturé.")
    prix = prix_usd_s(prep["rapide"])
    _SESSIONS[sid] = {"personnage_id": prep["personnage"]["id"], "duree_s": prep["duree_s"], "prix_usd_s": prix,
                      "ref": ref, "appareil": appareil, "ouverte": time.time(), "voix": voix, "voix_s": 0.0}
    pid = prep["personnage"]["id"]
    return {"session_id": sid, "jeton": jeton, "expire": rep.get("expiresAt"), "modele": MODELE,
            "duree_max_s": prep["duree_s"], "prix_usd_s": prix, "devis_usd": round(prix * prep["duree_s"], 6),
            "rapide": prep["rapide"], "personnage": prep["personnage"], "voix": voix,
            "image_url": f"/api/avatar-live/personnages/{pid}/image/0"}


async def terminer_session(session_id: str, secondes, appareil: str | None) -> dict:
    """Le réel d'une session : secondes rapportées, bornées à [0, durée réservée]. Le PC clôt toute session ; un
    téléphone ne clôt que les siennes. Une session close disparaît (pas de double compte)."""
    from app.services import plafonds as _plaf
    sid0 = session_id if isinstance(session_id, str) else ""
    s = _SESSIONS.get(sid0)
    if s is None:
        c = _CLOSES.get(sid0)
        if c is not None and (appareil is None or c["appareil"] == appareil):
            return dict(c["facture"], deja_close=True)      # t168f : le relais a pu clore avant la page
        raise Refus(404, "Session inconnue ou déjà close.")
    if appareil is not None and s["appareil"] != appareil:
        raise Refus(404, "Session inconnue ou déjà close.")
    if s.get("fournisseur") == "fal":
        sec = _secondes_relais(s)           # t168f : la durée MESURÉE par le serveur, jamais celle de la page
    else:
        try:
            sec = float(secondes)
            if sec != sec:
                raise ValueError
        except (TypeError, ValueError):
            sec = float(s["duree_s"])           # illisible : la durée entière (sens sûr)
    sec = max(0.0, min(float(s["duree_s"]), sec))
    reel = round(sec * s["prix_usd_s"], 6)
    out = {"session_id": session_id, "secondes": sec, "reel_usd": reel}
    voix_cloud = bool(s.get("voix") and s["voix"]["moteur"] == "cloud")
    if voix_cloud:
        from app.services import pricing as _pricing
        vs = round(s["voix_s"], 3)
        vu = round(_pricing.estimate({"kind": "voix_sts", "duration_s": vs})["total_usd"], 6)
        out.update(voix_s=vs, voix_usd=vu)
    # t168f : tout est décidé AVANT le premier await — retirer la session et ranger sa facture d'un seul tenant, pour
    # qu'une fin concurrente (la page pendant que le relais clôt) trouve l'une ou l'autre, jamais aucune (404 vu en
    # preuve le 11/10)
    _SESSIONS.pop(session_id, None)
    if s.get("fournisseur") == "fal":
        out["mesure"] = "serveur"
        _CLOSES[session_id] = {"appareil": s["appareil"], "facture": out, "le": time.time()}
        for k in [k for k, v in _CLOSES.items() if time.time() - v["le"] > 900]:
            _CLOSES.pop(k, None)
        if s["relais"]["arret"] is not None:     # APRÈS la facture rangée : le relais la relit pour la page
            s["relais"]["arret"].set()
    await _plaf.noter_reel(s["ref"], reel, sec)
    if voix_cloud:
        await _plaf.noter_reel(f"voixlive:{session_id}", out["voix_usd"], out["voix_s"] / 60.0 * 1000.0)
    return out


def imputer_voix(session_id: str, appareil: str | None, duree_s: float) -> dict:
    """G5 : un segment de voix s'impute sur la session (la réserve cloud = la durée de la session). Rend la voix."""
    s = _SESSIONS.get(session_id if isinstance(session_id, str) else "")
    if s is None or (appareil is not None and s["appareil"] != appareil):
        raise Refus(404, "Session inconnue ou déjà close.")
    if not s.get("voix"):
        raise Refus(409, "Cette session a été ouverte sans voix en direct.")
    if s["voix_s"] + duree_s > float(s["duree_s"]) + 0.5:
        raise Refus(409, "Réserve de voix épuisée pour cette session : rouvrez un direct.")
    s["voix_s"] += duree_s
    return s["voix"]


# ── t168f (11/10/2026) : le Direct par fal (decart/lucy-2-5/realtime), la clé fal seule ─────────────────────────────
# Relevé par l'essai réel du 11/10 (spec, section 10) : la signalisation passe par un WebSocket fal (msgpack) ; la
# vidéo va pair-à-pair navigateur ⇄ Decart. L'expiration d'un jeton n'arrête RIEN ; la fermeture du WebSocket arrête
# la génération. Donc le backend TIENT ce WebSocket (clé en en-tête, jamais montrée à la page) et relaie : il coupe à
# la durée réservée, coupe dès que la page s'en va, et mesure lui-même les secondes facturées (de l'ouverture du
# WebSocket fal à sa fermeture : un peu plus que la génération, sens sûr pour un plafond).

FAL_APP = "decart/lucy-2-5/realtime"
FAL_WS = "wss://fal.run/" + FAL_APP
FAL_REF_MIN_PX = 512        # reference_image_url : 512×512 au moins (doc fal)
TTL_RELAIS_S = 60           # le temps de brancher le relais après la réservation
_MSG_MAX = 200_000          # une offre SDP fait ~5 ko ; au-delà, ce n'est pas de la signalisation


async def _ouvrir_session_fal(prep: dict, lignes: list, appareil: str | None) -> dict:
    """Aucun appel réseau ici : la session est RÉSERVÉE (garde passée) et attend son relais. Un relais jamais
    branché ne coûte rien : la fin notera 0 s."""
    from app.services import plafonds as _plaf
    await purger_fal()
    sid = prep["session_id"]
    voix = prep.get("voix")
    await _plaf.rattacher(lignes[:1], prep["ref"])
    if voix and voix["moteur"] == "cloud" and len(lignes) > 1:
        await _plaf.rattacher(lignes[1:2], f"voixlive:{sid}")
    prix = prix_usd_s(False, "fal")
    jeton = _secrets.token_urlsafe(24)
    _SESSIONS[sid] = {"personnage_id": prep["personnage"]["id"], "duree_s": prep["duree_s"], "prix_usd_s": prix,
                      "ref": prep["ref"], "appareil": appareil, "ouverte": time.time(), "voix": voix, "voix_s": 0.0,
                      "fournisseur": "fal",
                      "relais": {"jeton": jeton, "expire": time.time() + TTL_RELAIS_S, "pris": False,
                                 "debut": None, "fin": None, "arret": None, "timings": 0, "repondu": False}}
    pid = prep["personnage"]["id"]
    return {"session_id": sid, "fournisseur": "fal", "relais": f"/api/avatar-live/fal/relais?jeton={jeton}",
            "modele": FAL_APP, "duree_max_s": prep["duree_s"], "prix_usd_s": prix,
            "devis_usd": round(prix * prep["duree_s"], 6), "rapide": False, "personnage": prep["personnage"],
            "voix": voix, "image_url": f"/api/avatar-live/personnages/{pid}/image/0"}


async def purger_fal() -> int:
    """Une réservation fal dont le relais n'a jamais été branché (page fermée entre-temps) n'a rien pu générer :
    passé le délai du relais, elle est close à 0 $ réel au lieu de rester au devis."""
    vieilles = [sid for sid, s in _SESSIONS.items() if s.get("fournisseur") == "fal" and not s["relais"]["pris"]
                and time.time() > s["relais"]["expire"]]
    for sid in vieilles:
        try:
            await terminer_session(sid, 0, _SESSIONS[sid]["appareil"])
        except Refus:
            pass
    return len(vieilles)


def _secondes_relais(s: dict) -> float:
    r = s["relais"]
    if r["debut"] is None or not r.get("repondu"):
        return 0.0              # sans réponse SDP, aucun flux n'a pu être généré (refus, offre jamais envoyée)
    return max(0.0, (r["fin"] if r["fin"] is not None else time.monotonic()) - r["debut"])


def session_relais(jeton) -> tuple[str, dict] | None:
    """Le jeton du relais : à usage UNIQUE, valable TTL_RELAIS_S après la réservation. C'est la seule garde du
    WebSocket — la dépense a été réservée (et gardée) par POST /sessions."""
    if not isinstance(jeton, str) or not jeton:
        return None
    for sid, s in _SESSIONS.items():
        r = s.get("relais")
        if r and not r["pris"] and time.time() <= r["expire"] and _secrets.compare_digest(r["jeton"], jeton):
            r["pris"] = True
            return sid, s
    return None


def reference_data_uri(pid) -> str | None:
    """La photo 0 du Personnage en data URI JPEG, agrandie à 512 px sur le petit côté si besoin (exigence fal)."""
    from PIL import Image
    p = chemin_image(pid, 0) if isinstance(pid, str) and _ID.match(pid) else None
    if not p:
        return None
    im = Image.open(p).convert("RGB")
    w, h = im.size
    if min(w, h) < FAL_REF_MIN_PX:
        k = FAL_REF_MIN_PX / min(w, h)
        im = im.resize((max(FAL_REF_MIN_PX, round(w * k)), max(FAL_REF_MIN_PX, round(h * k))), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, "JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode("ascii")


async def _ouvrir_fal():
    """Le SEUL appel réseau du Direct par fal (remplacé par les bancs) : un WebSocket fal, clé en en-tête."""
    import ssl
    import websockets
    kw = {}
    if not SSL_VERIFY:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kw["ssl"] = ctx
    return await websockets.connect(FAL_WS, additional_headers={"Authorization": "Key " + settings.FAL_KEY.strip()},
                                    open_timeout=15, max_size=2 ** 20, **kw)


def _entree_fal(m: dict, cache: dict) -> dict:
    """{type: "etat", prompt, personnage_id} de la page -> l'entrée fal : l'état COMPLET (fal le remplace)."""
    prompt = re.sub(r"\s+", " ", str(m.get("prompt") or "")).strip()[:600] or "Keep the person."
    pid = m.get("personnage_id")
    if pid and pid not in cache:
        cache[pid] = reference_data_uri(pid)
    return {"prompt": prompt, "reference_image_url": cache.get(pid) if pid else None, "enable_prompt_expansion": True}


async def relayer_fal(page, jeton) -> None:
    """Le relais de signalisation page ⇄ fal. `page` : un WebSocket Starlette déjà accepté.
    Page -> serveur (JSON) : {type: "etat", prompt, personnage_id} (en premier, puis à chaud), {type: "offer", sdp},
    {type: "icecandidate", candidate}. Serveur -> page (JSON) : ready, iceServers, answer, icecandidate, error (relus
    de fal), puis {type: "fin", raison, secondes, reel_usd}. Fin sur : borne, page partie, fal parti, /sessions/fin."""
    import asyncio
    import msgpack
    trouve = session_relais(jeton)
    if trouve is None:
        await page.send_json({"type": "error", "error": "Relais refusé : session inconnue, expirée ou déjà branchée."})
        await page.close(code=4403)
        return
    sid, s = trouve
    r = s["relais"]
    r["arret"] = asyncio.Event()
    cache: dict = {}
    try:
        premier = await asyncio.wait_for(page.receive_json(), timeout=15)
    except Exception:  # noqa: BLE001 — page muette ou partie : rien n'a été ouvert chez fal
        await page.close(code=4408)
        return
    try:
        fal = await _ouvrir_fal()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"avatar_live: fal injoignable pour {sid} ({type(e).__name__})")
        await page.send_json({"type": "error", "error": f"fal injoignable ({type(e).__name__}) — rien n'a été facturé."})
        await page.close(code=4502)
        return
    r["debut"] = time.monotonic()

    async def page_vers_fal():
        m = premier
        while True:
            if isinstance(m, dict):
                ty = m.get("type")
                if ty == "etat":
                    await fal.send(msgpack.packb(_entree_fal(m, cache)))
                elif ty == "offer" and isinstance(m.get("sdp"), str) and len(m["sdp"]) < _MSG_MAX:
                    await fal.send(msgpack.packb({"type": "offer", "sdp": m["sdp"]}))
                elif ty == "icecandidate" and isinstance(m.get("candidate"), dict):
                    c = m["candidate"]
                    await fal.send(msgpack.packb({"type": "icecandidate", "candidate": {
                        "candidate": str(c.get("candidate") or "")[:1000], "sdpMid": c.get("sdpMid"),
                        "sdpMLineIndex": c.get("sdpMLineIndex")}}))
            m = await page.receive_json()

    async def fal_vers_page():
        while True:
            brut = await fal.recv()
            if isinstance(brut, (bytes, bytearray)) and len(brut) > _MSG_MAX:
                continue
            try:
                m = msgpack.unpackb(brut) if isinstance(brut, (bytes, bytearray)) else json.loads(brut)
            except Exception:  # noqa: BLE001
                continue
            if not isinstance(m, dict):
                continue
            ty = str(m.get("type") or "")
            if ty == "x-fal-message":
                r["timings"] += 1
                continue
            if ty == "answer" and m.get("sdp"):
                r["repondu"] = True     # la génération peut commencer : on compte depuis l'ouverture (sens sûr)
            if ty.lower() in ("ready", "iceservers", "answer", "icecandidate", "error", "x-fal-error"):
                await page.send_json({k: m.get(k) for k in ("type", "sdp", "candidate", "iceServers", "error", "reason")
                                      if m.get(k) is not None})

    async def borne():
        await asyncio.sleep(float(s["duree_s"]))

    taches = {asyncio.ensure_future(page_vers_fal()): "page", asyncio.ensure_future(fal_vers_page()): "fal",
              asyncio.ensure_future(borne()): "borne", asyncio.ensure_future(r["arret"].wait()): "arret"}
    async def clore(raison):
        for t in taches:
            t.cancel()
        try:
            await fal.close()
        except Exception:  # noqa: BLE001
            pass
        r["fin"] = time.monotonic()
        if sid in _SESSIONS:            # la page n'a pas (encore) clos : le relais note le réel lui-même
            try:
                facture = await terminer_session(sid, None, s["appareil"])
            except Refus:
                facture = None
        else:
            facture = (_CLOSES.get(sid) or {}).get("facture")
        logger.info(f"avatar_live: Direct fal {sid} clos ({raison}), {round(_secondes_relais(s), 1)} s mesurées")
        if raison not in ("page", "annule"):
            try:
                await page.send_json({"type": "fin", "raison": raison,
                                      **({k: facture[k] for k in ("secondes", "reel_usd")} if facture else {})})
                await page.close(code=1000)
            except Exception:  # noqa: BLE001 — la page est déjà partie
                pass

    raison = "annule"               # le serveur s'arrête ou le gestionnaire est annulé : fal est coupé quand même
    try:
        faites, _ = await asyncio.wait(taches, return_when=asyncio.FIRST_COMPLETED)
        raison = taches[next(iter(faites))]
    finally:
        # la clôture (couper fal, noter le réel) survit à une annulation : une tâche à part, protégée
        await asyncio.shield(asyncio.ensure_future(clore(raison)))
