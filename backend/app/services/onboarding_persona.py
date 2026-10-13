# -*- coding: utf-8 -*-
"""t205 (Espaces de marque E5, 13/10/2026) — l'ONBOARDING d'un persona : définir avec l'utilisateur la nature précise
d'une marque (produit, audience, personnage, ton, univers visuel, références, interdits) puis en tirer le persona v2.

Huit étapes (spec D3) ; les réponses vivent dans un BROUILLON par espace (`DATA_ROOT/espaces/<id>/onboarding.json`),
validé champ par champ à l'écriture, reprenable à tout moment. Rien n'est écrit dans le persona avant que l'utilisateur
VALIDE la proposition (`valider`).
  - lire l'URL du produit : jamais une adresse privée ou locale (chaque redirection revérifiée), propose nom et pitch ;
  - planches d'ambiance : 4 DIRECTIONS tirées des réponses (déterministe, gratuit) ; leurs vignettes sont payantes,
    devisées d'abord, générées sur demande par la route (garde de dépense + plafond) ;
  - synthèse : MANUELLE (déterministe, toujours possible, sans clé) ou par LLM (sur demande, sous plafond) — la sortie
    du LLM est COMPLÉTÉE par la synthèse manuelle et passée à la même validation ; un LLM muet ou un JSON illisible
    retombe sur la manuelle, et c'est dit.
"""
from __future__ import annotations

import ipaddress
import json
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from loguru import logger

from app.services import espaces

ETAPES = ("produit", "audience", "personnage", "ton", "ambiance", "references", "interdits")
MAX_TEXTE = 600
MAX_LISTE = 30
MAX_ELEM = 120
PERSONNAGES = ("mascotte", "humain", "abstrait", "aucun")
CURSEURS = ("serieux_meme", "oracle_copain", "sobre_exuberant")
# champ -> genre : t texte court, l liste de textes, n curseur 0-100, c choix, d objet libre contrôlé ailleurs
SCHEMA = {
    "produit": {"nom": "t", "url": "t", "pitch": "t", "produits": "l"},
    "audience": {"qui": "t", "ou": "l", "aime": "l", "rejette": "l"},
    "personnage": {"type": "c", "description": "t", "nom": "t"},
    "ton": {"serieux_meme": "n", "oracle_copain": "n", "sobre_exuberant": "n", "garder": "l", "rejeter": "l",
            "langues": "l", "catchphrase": "t", "handle": "t"},
    "ambiance": {"choisies": "l", "rejetees": "l", "notes": "t"},
    "references": {"images": "l"},
    "interdits": {"sujets": "l", "mots": "l", "couleurs": "l", "concurrents": "l", "legal": "t"},
}


def _fichier(eid: str):
    f = espaces.chemin(eid, "persona.json")
    if f is None or eid not in espaces.lire()["espaces"]:
        raise KeyError(eid)
    return f.with_name("onboarding.json")


def brouillon(eid: str) -> dict:
    f = _fichier(eid)
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(d, dict) and isinstance(d.get("etapes"), dict):
            return d
    except (OSError, ValueError):
        pass
    return {"etapes": {}, "directions": [], "proposition": None, "maj": None}


def _ecrire(eid: str, d: dict) -> dict:
    d["maj"] = datetime.now().isoformat(timespec="seconds")
    f = _fichier(eid)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)
    return d


def _propre(etape: str, data) -> dict:
    if etape not in SCHEMA:
        raise ValueError(f"étape inconnue : {etape} — connues : {', '.join(SCHEMA)}")
    if not isinstance(data, dict):
        raise ValueError("une étape s'écrit en objet JSON")
    out = {}
    for k, v in data.items():
        g = SCHEMA[etape].get(k)
        if g is None:
            raise ValueError(f"{etape}.{k} : champ inconnu")
        if g == "t":
            if not isinstance(v, str):
                raise ValueError(f"{etape}.{k} doit être un texte")
            out[k] = v.strip()[:MAX_TEXTE]
        elif g == "l":
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                raise ValueError(f"{etape}.{k} doit être une liste de textes")
            out[k] = [x.strip()[:MAX_ELEM] for x in v if x.strip()][:MAX_LISTE]
        elif g == "n":
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 100:
                raise ValueError(f"{etape}.{k} doit être un nombre de 0 à 100")
            out[k] = int(v)
        elif g == "c":
            if v not in PERSONNAGES:
                raise ValueError(f"{etape}.{k} : choisir parmi {', '.join(PERSONNAGES)}")
            out[k] = v
    if etape == "produit" and out.get("url"):
        u = urlparse(out["url"])
        if u.scheme not in ("http", "https") or not u.netloc:
            raise ValueError("produit.url doit être une adresse http(s)")
    if etape == "references":
        for n in out.get("images", []):
            if "/" in n or "\\" in n or n in (".", ".."):
                raise ValueError(f"references.images : nom de fichier invalide ({n})")
    return out


def enregistrer_etape(eid: str, etape: str, data) -> dict:
    """Écrit (remplace) une étape du brouillon après validation ; une proposition déjà faite devient périmée."""
    d = brouillon(eid)
    d["etapes"][etape] = _propre(etape, data)
    d["proposition"] = None
    if etape in ("produit", "audience", "personnage", "ton", "interdits"):
        d["directions"] = directions(d)          # une vignette reste tant que le prompt de sa direction est le même
    return _ecrire(eid, d)


def effacer(eid: str) -> None:
    f = _fichier(eid)
    f.unlink(missing_ok=True)


# ---- l'URL du produit -------------------------------------------------------------------------------------------------

def hote_prive(h) -> bool:
    """Même règle que routes._is_private_host : jamais un hôte local, privé, lien-local ou réservé."""
    h = (h or "").lower().strip("[]")
    if h in ("localhost", "") or h.endswith(".local") or h.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(h)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        return False


def lire_url(url: str, client=None) -> dict:
    """{nom, pitch, texte} tirés de la page publique du produit. ValueError = adresse refusée ou illisible. Les
    redirections sont suivies À LA MAIN (5 au plus) et chaque hôte est revérifié."""
    import httpx
    from app.config import SSL_VERIFY
    u = urlparse(url or "")
    if u.scheme not in ("http", "https") or not u.netloc:
        raise ValueError("adresse http(s) attendue")
    propre = client is None
    c = client or httpx.Client(verify=SSL_VERIFY, timeout=20.0, follow_redirects=False,
                               headers={"User-Agent": "Mozilla/5.0 (compatible; DeepotusVideo onboarding)"})
    try:
        for _ in range(6):
            if hote_prive(urlparse(url).hostname):
                raise ValueError("adresse privée ou locale refusée")
            r = c.get(url)
            if r.is_redirect and r.headers.get("location"):
                url = urljoin(url, r.headers["location"])
                continue
            break
        else:
            raise ValueError("trop de redirections")
        if r.status_code != 200:
            raise ValueError(f"la page répond {r.status_code}")
        html = r.text[:2_000_000]
    finally:
        if propre:
            c.close()
    titre = ""
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if m:
        titre = re.sub(r"\s+", " ", m.group(1)).strip()
    desc = ""
    m = re.search(r'<meta[^>]+(?:name|property)=["\'](?:og:)?description["\'][^>]+content=["\']([^"\']+)', html, re.I)
    if m:
        desc = m.group(1).strip()
    texte = ""
    try:
        import trafilatura
        texte = (trafilatura.extract(html) or "").strip()
    except Exception:  # noqa: BLE001 — l'extraction est un bonus
        texte = ""
    if not texte:
        texte = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", " ", html))).strip()
    nom = re.split(r"\s[|\-–—:]\s", titre)[0].strip() if titre else ""
    pitch = desc or (texte.split(". ")[0] + "." if texte else "")
    return {"nom": nom[:MAX_ELEM], "pitch": pitch[:MAX_TEXTE], "texte": texte[:3000]}


# ---- les planches d'ambiance ------------------------------------------------------------------------------------------

_DIRECTIONS = (
    ("cinema", "Cinéma sombre", "cinematic, low-key lighting, deep shadows, anamorphic lens, film grain"),
    ("lumineux", "Clair et net", "bright clean studio light, soft shadows, minimal set, crisp product focus"),
    ("graphique", "Graphique et pop", "bold flat colors, graphic shapes, high contrast, poster-like composition"),
    ("organique", "Organique et doux", "natural textures, warm diffuse light, shallow depth of field, calm mood"),
)


def directions(d: dict) -> list:
    """4 directions comparatives tirées des réponses (déterministe, gratuit) : même sujet, quatre partis pris."""
    e = d.get("etapes", {})
    p, pers, interd = e.get("produit", {}), e.get("personnage", {}), e.get("interdits", {})
    sujet = (pers.get("description") if pers.get("type") in ("mascotte", "humain", "abstrait") else "") \
        or p.get("pitch") or p.get("nom") or "the brand"
    anciens = {x["id"]: x for x in d.get("directions", []) if isinstance(x, dict) and x.get("id")}
    neg = ", ".join(interd.get("couleurs", []) + interd.get("sujets", []))
    out = []
    for i, titre, style in _DIRECTIONS:
        prompt = f"{sujet}. {style}. Brand mood board frame, no text, no watermark."
        if neg:
            prompt += f" Avoid: {neg}."
        old = anciens.get(i, {})
        out.append({"id": i, "titre": titre, "style": style, "prompt": prompt[:900],
                    "image": old.get("image") if old.get("prompt") == prompt[:900] else None})
    return out


def poser_vignettes(eid: str, images: dict) -> dict:
    """images = {id_direction: nom de fichier} (après génération par la route)."""
    d = brouillon(eid)
    if not d.get("directions"):
        d["directions"] = directions(d)
    for x in d["directions"]:
        if x["id"] in images:
            x["image"] = images[x["id"]]
    return _ecrire(eid, d)


# ---- la synthèse ------------------------------------------------------------------------------------------------------

def _mode_voix(ton: dict) -> str:
    s, o = ton.get("serieux_meme", 50), ton.get("oracle_copain", 50)
    if s >= 65:
        return "custom"
    return "oracle" if o <= 35 else "prophet" if o <= 65 else "seer"


def synthese_manuelle(eid: str) -> dict:
    """La proposition de persona v2, tirée des réponses SANS LLM (toujours possible)."""
    d = brouillon(eid)
    e = d["etapes"]
    p, a, pers, ton = e.get("produit", {}), e.get("audience", {}), e.get("personnage", {}), e.get("ton", {})
    amb, ref, interd = e.get("ambiance", {}), e.get("references", {}), e.get("interdits", {})
    nom_esp = espaces.lire()["espaces"][eid].get("nom") or eid
    nom = p.get("nom") or nom_esp
    dirs = {x["id"]: x for x in (d.get("directions") or directions(d))}
    choisies = [dirs[i] for i in amb.get("choisies", []) if i in dirs]
    rejetees = [dirs[i] for i in amb.get("rejetees", []) if i in dirs]
    vibe = []
    for x in choisies:
        vibe += [s.strip() for s in x["style"].split(",")]
    vibe += a.get("aime", [])
    neg = ["no text", "no watermark"] + [s.strip() for x in rejetees for s in x["style"].split(",")[:2]] \
        + interd.get("couleurs", []) + interd.get("sujets", [])
    tags = ["#" + re.sub(r"[^0-9A-Za-z]", "", nom)] + ["#" + re.sub(r"[^0-9A-Za-z]", "", x) for x in p.get("produits", [])]
    s, ex = ton.get("serieux_meme", 50), ton.get("sobre_exuberant", 50)
    tons = (["solemn", "measured"] if s < 35 else ["playful", "meme-literate"] if s > 65 else ["confident", "clear"]) \
        + (["exuberant"] if ex > 65 else ["understated"] if ex < 35 else [])
    ecran = {"id": eid, "name": pers.get("nom") or nom, "handle": ton.get("handle") or "@",
             "role": (p.get("pitch") or f"La voix de {nom}.")[:200], "voiceMode": _mode_voix(ton), "tone": tons,
             "formality": max(0, min(100, 100 - s)), "emojiPolicy": "frequent" if ex > 65 else "none" if ex < 25 else "sparse",
             "catchphrase": ton.get("catchphrase", ""), "preferred": ton.get("garder", []),
             "banned": interd.get("mots", []) + ton.get("rejeter", []), "languages": [x.upper()[:2] for x in ton.get("langues", [])] or ["EN"]}
    return {
        "display_name": nom,
        "vibe_keywords": list(dict.fromkeys(x for x in vibe if x))[:20],
        "default_negative_prompt": ", ".join(dict.fromkeys(x for x in neg if x))[:800],
        "default_hashtags_pool": list(dict.fromkeys(t for t in tags if len(t) > 1))[:12],
        "identite": {"nom": nom, "url": p.get("url", ""), "mission": p.get("pitch", ""), "produits": p.get("produits", [])},
        "audience": {"qui": a.get("qui", ""), "ou": a.get("ou", []), "aime": a.get("aime", []), "rejette": a.get("rejette", [])},
        "ton": {k: ton[k] for k in CURSEURS if k in ton} | {"garder": ton.get("garder", []), "rejeter": ton.get("rejeter", []),
                                                            "langues": ton.get("langues", [])},
        "visuel": {"personnage": pers, "directions_choisies": [x["id"] for x in choisies],
                   "directions_rejetees": [x["id"] for x in rejetees],
                   "style_ecrit": "; ".join(x["style"] for x in choisies), "references": ref.get("images", []),
                   "interdits": {k: interd.get(k, []) for k in ("couleurs", "sujets", "concurrents")},
                   "legal": interd.get("legal", "")},
        "ecran": ecran,
        "source": "manuelle",
    }


SYSTEME_LLM = ("You are a brand strategist. From the onboarding answers, write the brand persona. Reply with JSON ONLY: "
               '{"display_name": str, "mission": str (one sentence), "vibe_keywords": [8-15 short visual keywords], '
               '"default_negative_prompt": str, "default_hashtags_pool": [6-12 hashtags], "style_ecrit": str '
               "(visual style described by descriptors only, NEVER an artist name), "
               '"ecran": {"role": str, "tone": [3-5 adjectives], "catchphrase": str, "preferred": [words], '
               '"banned": [words]}}. Respect every forbidden topic, word and legal constraint.')


def jetons_llm() -> tuple:
    return 1800, 1200


def _json_objet(txt: str):
    if not txt:
        return None
    t = re.sub(r"^```(?:json)?|```$", "", txt.strip(), flags=re.M)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        v = json.loads(t[i:j + 1])
        return v if isinstance(v, dict) else None
    except ValueError:
        return None


def _liste(v, n=20):
    return [str(x).strip()[:MAX_ELEM] for x in v if str(x).strip()][:n] if isinstance(v, list) else None


def synthese_llm(eid: str, dispatch=None) -> dict:
    """La proposition par LLM, COMPLÉTÉE par la manuelle (un champ absent ou mal formé garde la valeur manuelle).
    LLM muet ou JSON illisible : la manuelle, avec `note`."""
    base = synthese_manuelle(eid)
    if dispatch is None:
        from app.services import summarizer
        dispatch = summarizer._chat_dispatch
    d = brouillon(eid)
    prompt = "Onboarding answers (JSON):\n" + json.dumps(d["etapes"], ensure_ascii=False)[:6000]
    try:
        brut, fournisseur = dispatch(prompt, SYSTEME_LLM, jetons_llm()[1])
    except Exception as e:  # noqa: BLE001
        logger.warning(f"onboarding llm : {e}")
        brut, fournisseur = None, ""
    j = _json_objet(brut or "")
    if not j:
        return base | {"note": "le LLM n'a rien rendu de lisible : synthèse sans IA"}
    out = json.loads(json.dumps(base))
    if isinstance(j.get("display_name"), str) and j["display_name"].strip():
        out["display_name"] = j["display_name"].strip()[:120]
    if isinstance(j.get("mission"), str) and j["mission"].strip():
        out["identite"]["mission"] = j["mission"].strip()[:MAX_TEXTE]
    for k in ("vibe_keywords", "default_hashtags_pool"):
        v = _liste(j.get(k))
        if v:
            out[k] = v
    if isinstance(j.get("default_negative_prompt"), str) and j["default_negative_prompt"].strip():
        out["default_negative_prompt"] = j["default_negative_prompt"].strip()[:800]
    if isinstance(j.get("style_ecrit"), str) and j["style_ecrit"].strip():
        out["visuel"]["style_ecrit"] = j["style_ecrit"].strip()[:MAX_TEXTE]
    ec = j.get("ecran") if isinstance(j.get("ecran"), dict) else {}
    if isinstance(ec.get("role"), str) and ec["role"].strip():
        out["ecran"]["role"] = ec["role"].strip()[:200]
    if isinstance(ec.get("catchphrase"), str):
        out["ecran"]["catchphrase"] = ec["catchphrase"].strip()[:200]
    for k in ("tone", "preferred"):
        v = _liste(ec.get(k), 12)
        if v:
            out["ecran"][k] = v
    v = _liste(ec.get("banned"), 30)
    if v is not None:
        # les interdits saisis par l'utilisateur restent TOUJOURS bannis, quoi que propose le LLM
        out["ecran"]["banned"] = list(dict.fromkeys(base["ecran"]["banned"] + v))
    out["source"] = f"llm:{fournisseur}" if fournisseur else "llm"
    return out


def proposer(eid: str, proposition: dict) -> dict:
    d = brouillon(eid)
    d["proposition"] = proposition
    return _ecrire(eid, d)


_CHAMPS_PROPOSITION = ("display_name", "vibe_keywords", "default_negative_prompt", "default_hashtags_pool", "identite",
                       "audience", "ton", "visuel", "ecran")


def valider(eid: str, proposition: dict | None = None) -> dict:
    """Écrit la proposition (relue/corrigée par l'utilisateur, sinon celle du brouillon) dans le persona de l'espace,
    PAR-DESSUS l'existant (modèles, voix, modes gardés). ValueError = rien à valider ou persona refusé."""
    prop = proposition if isinstance(proposition, dict) else brouillon(eid).get("proposition")
    if not isinstance(prop, dict):
        raise ValueError("aucune proposition à valider : lancez d'abord la synthèse")
    if not isinstance(prop.get("ecran"), dict):
        raise ValueError("proposition incomplète : persona d'écran absent")
    actuel = espaces.persona(eid)
    nouveau = dict(actuel)
    for k in _CHAMPS_PROPOSITION:
        if k in prop:
            nouveau[k] = prop[k]
    nouveau["ecran"] = dict(prop["ecran"], id=eid)
    nouveau["onboarding"] = {"valide_le": datetime.now().isoformat(timespec="seconds"), "source": prop.get("source", "")}
    p = espaces.ecrire_persona(eid, nouveau)
    d = brouillon(eid)
    d["proposition"] = prop
    d["valide_le"] = nouveau["onboarding"]["valide_le"]
    _ecrire(eid, d)
    from app.services import contenus_espace          # t207 : un espace sans modèle reçoit ses contenus de départ
    contenus_espace.semer_si_vide(eid)
    return p
