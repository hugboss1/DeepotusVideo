# -*- coding: utf-8 -*-
"""t210 (Espaces de marque E10, 15/10/2026) — EXPORT et IMPORT d'un espace de marque, SANS SECRETS (spec D9).

Un paquet = un .zip que l'on remet à un client ou que l'on recharge sur une autre installation. Il porte :
  - `espace.json`   : le format, la date, le nom, la couleur et le plafond propre de l'espace ;
  - `persona.json`, `contenus.json`, `onboarding.json` (le brouillon de l'assistant, s'il existe) ;
  - `identite/identite.json` et ses images (logo, mascotte, produits) — la planche se recompose (gratuit) ;
  - `kit/kit.json` et `kit/logo.png` quand l'espace a choisi un kit pour ses contenus ;
  - `comptes.json` : plateforme, libellé, handle et champs PUBLICS de chaque compte ; les champs secrets n'y sont que
    NOMMÉS (`a_ressaisir`) : un secret ne quitte jamais le coffre ni le .env.
Rien d'autre : ni la Bibliothèque, ni les posts, ni les dépenses (ce sont des données de travail, pas la marque).

L'import crée TOUJOURS un espace neuf (jamais un remplacement), non actif. Tout est VALIDÉ avant la première écriture
(mêmes juges que les écrans : persona, contenus, identité, onboarding, kit, Pillow pour les images) ; un échec
pendant l'écriture défait ce qui a été écrit (espace, comptes, kit). Liste blanche des noms d'entrées (jamais de ../),
bornes de taille (zip et décompressé), nombre d'entrées borné : une entrée inconnue est ignorée et dite.
"""
from __future__ import annotations

import io
import json
import re
import shutil
import unicodedata
import zipfile
from datetime import datetime

from app.services import brand_kits, comptes, contenus_espace, espaces, fiche_client, identite, onboarding_persona

FORMAT = "deepotus-espace"
VERSION = 1
MAX_ZIP = 40 * 1024 * 1024
MAX_DECOMPRESSE = 120 * 1024 * 1024
MAX_ENTREES = 60
_JSONS = ("espace.json", "persona.json", "contenus.json", "onboarding.json", "comptes.json",
          "identite/identite.json", "kit/kit.json", "client.json")
_IMAGE = re.compile(r"^identite/((?:logo|mascotte|produits)-[0-9a-f]{8}\.png)$")


def _slug(nom: str) -> str:
    s = unicodedata.normalize("NFKD", nom or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()[:40] or "espace"


def _json(doc) -> bytes:
    return json.dumps(doc, indent=2, ensure_ascii=False).encode("utf-8")


def _comptes_publics(eid: str) -> list:
    """Les comptes de l'espace, champs publics seulement ; les secrets NOMMÉS, jamais lus."""
    out = []
    for v in comptes.lister(eid):
        if comptes.champs_poses_par_serveur(v["plateforme"]):
            continue    # t310 (27/10/2026) : un compte relié par le serveur (whatsapp) ne voyage pas : il se relie dans chaque espace
        publics, secrets_ = {}, []
        for ch in v["champs"]:
            if ch["secret"]:
                secrets_.append(ch["nom"])
            elif ch.get("valeur") not in (None, "", False):
                publics[ch["nom"]] = ch["valeur"]
        out.append({"plateforme": v["plateforme"], "libelle": v["libelle"], "handle": v.get("handle") or "",
                    "publics": publics, "a_ressaisir": secrets_})
    return out


def exporter(eid: str) -> tuple:
    """(octets du zip, nom de fichier). KeyError = espace inconnu."""
    doc = espaces.lire()
    if not espaces.id_valide(eid) or eid not in doc["espaces"]:
        raise KeyError(eid)
    e = doc["espaces"][eid]
    tete = {"format": FORMAT, "version": VERSION, "exporte_le": datetime.now().isoformat(timespec="seconds"),
            "source": eid, "espace": {"nom": e.get("nom") or eid, "couleur": e.get("couleur") or "#ef4444",
                                      "plafond_usd": espaces.plafond_valide(e.get("plafond_usd")),
                                      # t306 (25/10/2026) : le type et le parent voyagent (le parent n'est repris que s'il existe)
                                      "type": e.get("type") if e.get("type") in espaces.TYPES else "marque",
                                      "parent": e.get("parent") or None}}
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("espace.json", _json(tete))
        persona = espaces.persona(eid)
        z.writestr("persona.json", _json(persona))
        z.writestr("contenus.json", _json(espaces.contenus(eid)))
        f_onb = espaces.chemin(eid, "persona.json").with_name("onboarding.json")
        if f_onb.is_file():
            z.writestr("onboarding.json", _json({"etapes": onboarding_persona.brouillon(eid).get("etapes") or {}}))
        idv = identite.lire(eid)
        z.writestr("identite/identite.json", _json({k: idv[k] for k in ("palette", "typographies", "style_ecrit", "adn",
                                                                          "logo", "mascotte", "produits")}))
        for nom in ([idv["logo"]] if idv.get("logo") else []) + list(idv.get("mascotte") or []) + list(idv.get("produits") or []):
            p = identite.dossier(eid) / nom
            if _IMAGE.match("identite/" + nom) and p.is_file():
                z.write(p, "identite/" + nom)
        kid = e.get("kit_id")
        kits = brand_kits.lire()["kits"]
        if kid and kid in kits:
            z.writestr("kit/kit.json", _json({"id": kid, **{k: kits[kid].get(k) for k in brand_kits.CHAMPS
                                                            if isinstance(kits[kid].get(k), str)}}))
            logo = brand_kits.logo_path(kid)
            if logo:
                z.write(logo, "kit/logo.png")
        z.writestr("comptes.json", _json(_comptes_publics(eid)))
        if tete["espace"]["type"] == "client":   # t306 : la fiche validée (contact, mode, consentements datés, journal)
            z.writestr("client.json", _json(fiche_client.valider(fiche_client.lire(eid))))
    return b.getvalue(), f"espace-{_slug(tete['espace']['nom'])}-{datetime.now():%Y%m%d}.zip"


# ---- l'import ----------------------------------------------------------------------------------------------------------

def _lire_zip(data: bytes) -> tuple:
    """{nom: octets} des entrées connues, [noms ignorés]. ValueError = paquet refusé."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise ValueError("paquet d'espace vide")
    if len(data) > MAX_ZIP:
        raise ValueError("paquet d'espace trop lourd (40 Mo au plus)")
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        infos = z.infolist()
    except (zipfile.BadZipFile, OSError, ValueError):
        raise ValueError("ce n'est pas un paquet d'espace (.zip illisible)")
    if len(infos) > MAX_ENTREES:
        raise ValueError(f"paquet d'espace : {MAX_ENTREES} entrées au plus")
    if sum(i.file_size for i in infos) > MAX_DECOMPRESSE:
        raise ValueError("paquet d'espace trop lourd une fois décompressé")
    pris, ignores = {}, []
    for i in infos:
        n = i.filename
        if i.is_dir():
            continue
        if n in _JSONS or _IMAGE.match(n) or n == "kit/logo.png":
            try:
                pris[n] = z.read(i)
            except Exception:  # noqa: BLE001 — zlib, CRC : le paquet est abîmé
                raise ValueError("paquet d'espace abîmé (entrée illisible)")
        else:
            ignores.append(n[:120])
    return pris, ignores


def _charger(pris: dict, nom: str, defaut=None):
    if nom not in pris:
        return defaut
    try:
        return json.loads(pris[nom].decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError):
        raise ValueError(f"paquet d'espace : {nom} illisible")


def _nom_libre(nom: str) -> str:
    pris = {(v.get("nom") or "").strip().lower() for v in espaces.lire()["espaces"].values()}
    if nom.lower() not in pris:
        return nom
    n = 2
    while f"{nom} ({n})".lower() in pris:
        n += 1
    return f"{nom} ({n})"[:espaces.MAX]


def _ignore(gabarit: str, **valeurs) -> str:
    """t308 (26/10/2026) : une raison d'`ignores`, écrite comme un GABARIT `{variable}` que le générateur L10
    (scripts/i18n_l10_erreurs.py) relève par AST, au même titre qu'un `raise ValueError(...)`. Rend le texte français
    rempli ; la route d'import le traduit selon la langue de la requête, par app.i18n.erreurs (un seul dictionnaire)."""
    return gabarit.format(**valeurs)


def _ecarts_fiche(brut, ignores: list) -> None:
    """t306 : dit, une ligne française par cas, ce que `fiche_client.valider` écarte ou réécrit dans la fiche du paquet."""
    d = brut if isinstance(brut, dict) else {}
    mode = d.get("mode_publication")
    if mode is not None and mode not in fiche_client.MODES:
        ignores.append(_ignore("client.json : mode de publication inconnu ({mode}), remplacé par valide_par_client", mode=str(mode)[:40]))
    for i, x in enumerate(d.get("consentements") if isinstance(d.get("consentements"), list) else [], 1):
        v = fiche_client.valider({"consentements": [x]})["consentements"]
        if not v:
            ignores.append(_ignore("client.json : consentement n°{i} écarté (canal, permissions ou date invalides)", i=i))
        elif x.get("moyen") not in fiche_client.MOYENS:
            ignores.append(_ignore("client.json : consentement n°{i} : moyen inconnu, remplacé par « ecrit »", i=i))
    # t306 : plusieurs consentements en cours sur un même canal : le plus récent est gardé, les autres sont clos (dit).
    actifs = {}
    for i, x in enumerate(d.get("consentements") if isinstance(d.get("consentements"), list) else [], 1):
        v = fiche_client.valider({"consentements": [x]})["consentements"]
        if v and v[0]["revoque_le"] is None:
            actifs.setdefault(v[0]["canal_id"], []).append((v[0]["date"], i))
    for canal, lst in actifs.items():
        gardee = max(lst)[1]
        for _date, i in lst:
            if i != gardee:
                ignores.append(_ignore("client.json : consentement n°{i} : un autre, plus récent (n°{gardee}), court déjà pour le "
                                       "canal {canal}, celui-ci est clos", i=i, gardee=gardee, canal=canal))
    for i, x in enumerate(d.get("journal") if isinstance(d.get("journal"), list) else [], 1):
        v = fiche_client.valider({"journal": [x]})["journal"]
        if not v:
            ignores.append(_ignore("client.json : ligne de journal n°{i} écartée (événement ou date invalides)", i=i))
            continue
        if x.get("canal_id") not in (None, "") and x.get("canal_id") != v[0]["canal_id"]:
            ignores.append(_ignore("client.json : ligne de journal n°{i} : canal invalide, retiré", i=i))
        if x.get("qui") not in fiche_client.QUI:
            ignores.append(_ignore("client.json : ligne de journal n°{i} : auteur inconnu, remplacé par « utilisateur »", i=i))
    if len(d.get("journal") if isinstance(d.get("journal"), list) else []) > fiche_client.MAX_JOURNAL:
        ignores.append(_ignore("client.json : journal tronqué aux {max} lignes les plus récentes", max=fiche_client.MAX_JOURNAL))


def _preparer(pris: dict, ignores: list) -> dict:
    """Valide TOUT le paquet sans rien écrire. Rend ce qu'il faut écrire."""
    tete = _charger(pris, "espace.json")
    if not isinstance(tete, dict) or tete.get("format") != FORMAT:
        raise ValueError("ce n'est pas un paquet d'espace (espace.json absent ou d'un autre format)")
    if not isinstance(tete.get("version"), int) or tete["version"] > VERSION:
        raise ValueError("paquet d'espace d'une version plus récente : mettez l'application à jour")
    e = tete.get("espace") if isinstance(tete.get("espace"), dict) else {}
    nom = espaces._nom(e.get("nom"))
    couleur = espaces._couleur(e.get("couleur"), "#ef4444")
    plan = {"nom": nom, "couleur": couleur, "plafond_usd": espaces.plafond_valide(e.get("plafond_usd"))}
    # t306 : type et parent. Type inconnu = marque ; parent absent de CETTE instance (ou refusé par les règles) = retiré, dit.
    type_ = e.get("type") if e.get("type") in espaces.TYPES else "marque"
    if e.get("type") is not None and e.get("type") not in espaces.TYPES:
        ignores.append(_ignore("type d'espace inconnu ({type}) : repris comme marque", type=str(e.get("type"))[:30]))
    parent = None
    if e.get("parent"):
        try:
            parent = espaces._parent_valide(espaces.lire(), type_, e.get("parent"))
        except ValueError:
            ignores.append(_ignore("parent {parent} absent de cette installation ou refusé : retiré", parent=str(e.get("parent"))[:40]))
    plan["type"], plan["parent"] = type_, parent
    fiche = _charger(pris, "client.json")
    plan["fiche"] = None
    if type_ == "client":
        if fiche is not None and not isinstance(fiche, dict):
            raise ValueError("paquet d'espace : client.json illisible")
        _ecarts_fiche(fiche, ignores)
        plan["fiche"] = fiche_client.valider(fiche)
        # relecture finale t310 (Minor 8) : le compte whatsapp ne voyage pas, son consentement `whatsapp:<numéro>` non plus
        # (il porterait sur un canal que l'espace neuf n'a pas) ; dit dans `ignores`, comme pour le compte
        garder = []
        for x in plan["fiche"]["consentements"]:
            if str(x.get("canal_id") or "").startswith("whatsapp:"):
                ignores.append(_ignore("client.json : consentement {canal} écarté : un numéro WhatsApp se relie dans chaque "
                                       "espace, il ne s'importe pas", canal=str(x["canal_id"])[:60]))
            else:
                garder.append(x)
        plan["fiche"]["consentements"] = garder
    elif fiche is not None:
        ignores.append(_ignore("client.json : ignoré (l'espace n'est pas un client)"))
    persona = _charger(pris, "persona.json")
    if persona is None:
        raise ValueError("paquet d'espace : persona.json manquant")
    plan["persona"] = espaces._valider_persona(persona)
    plan["contenus"] = contenus_espace.valider(_charger(pris, "contenus.json", espaces.CONTENUS_VIDES))
    onb = _charger(pris, "onboarding.json")
    plan["onboarding"] = {}
    if onb is not None:
        etapes = onb.get("etapes") if isinstance(onb, dict) else None
        if not isinstance(etapes, dict):
            raise ValueError("paquet d'espace : onboarding.json illisible")
        plan["onboarding"] = {k: onboarding_persona._propre(k, v) for k, v in etapes.items()}
    idv = _charger(pris, "identite/identite.json", {})
    if not isinstance(idv, dict):
        raise ValueError("paquet d'espace : identite/identite.json illisible")
    plan["identite"] = {}
    if "palette" in idv:
        plan["identite"]["palette"] = identite._palette(idv["palette"])
    if "typographies" in idv:
        plan["identite"]["typographies"] = identite._typos(idv["typographies"])
    if "style_ecrit" in idv:
        plan["identite"]["style_ecrit"] = identite._sans_artiste(
            identite._texte(idv["style_ecrit"], "style_ecrit", identite.MAX_STYLE), "style écrit")
    if "adn" in idv:
        plan["identite"]["adn"] = identite._adn(idv["adn"])
    images = []
    for genre in ("logo", "mascotte", "produits"):
        noms = [idv.get("logo")] if genre == "logo" else (idv.get(genre) if isinstance(idv.get(genre), list) else [])
        for n in [x for x in noms if isinstance(x, str)][:identite.GENRES[genre]]:
            cle = "identite/" + n
            if _IMAGE.match(cle) and cle in pris:
                images.append((genre, identite._png(pris[cle])))
    plan["images"] = images
    kit = _charger(pris, "kit/kit.json")
    plan["kit"] = None
    if kit is not None:
        if not isinstance(kit, dict):
            raise ValueError("paquet d'espace : kit/kit.json illisible")
        champs = brand_kits._propre({k: v for k, v in kit.items() if k in brand_kits.CHAMPS},
                                    dict(brand_kits.DEFAUTS, name=nom))
        logo = identite._png(pris["kit/logo.png"]) if "kit/logo.png" in pris else None
        plan["kit"] = {"champs": champs, "logo": logo, "idv": str(kit.get("id") or "").startswith("idv_")}
    cpts = _charger(pris, "comptes.json", [])
    if not isinstance(cpts, list) or len(cpts) > comptes.MAX_COMPTES:
        raise ValueError("paquet d'espace : comptes.json illisible")
    plan["comptes"] = []
    for i, c in enumerate(cpts):
        if not isinstance(c, dict) or c.get("plateforme") not in comptes.PLATEFORMES:
            raise ValueError(f"paquet d'espace : compte n°{i + 1} illisible")
        p = c["plateforme"]
        if comptes.champs_poses_par_serveur(p):
            # t310 (27/10/2026) : jamais deux espaces sur un même numéro WhatsApp — le compte se relie, il ne s'importe pas
            ignores.append(_ignore("comptes.json : compte n°{i} ({plateforme}) ignoré : il se relie dans chaque espace, "
                                   "il ne s'importe pas", i=i + 1, plateforme=comptes.PLATEFORMES[p][0]))
            continue
        champs_p = dict(comptes.PLATEFORMES[p][1])
        pub = c.get("publics") if isinstance(c.get("publics"), dict) else {}
        # un champ SECRET glissé dans le paquet n'est jamais écrit : on le fait ressaisir, comme les autres
        publics = {k: v for k, v in pub.items() if k in champs_p and not champs_p[k]
                   and isinstance(v, (str, bool, int, float)) and not isinstance(v, dict)}
        plan["comptes"].append({"plateforme": p, "libelle": comptes._texte(c.get("libelle")),
                                "handle": comptes._texte(c.get("handle")), "publics": publics,
                                "a_ressaisir": [k for k, s in comptes.PLATEFORMES[p][1] if s]})
    return plan


def _retirer_espace(eid: str) -> None:
    from pathlib import Path
    from app.config import settings
    doc = espaces.lire()
    if doc["espaces"].pop(eid, None) is not None:
        espaces._ecrire(doc)
    shutil.rmtree(espaces.dossier() / eid, ignore_errors=True)
    for p in Path(settings.images_path).glob(identite.nom_bibliotheque(eid, "*")):   # les copies de Bibliothèque
        p.unlink(missing_ok=True)


def importer(data: bytes) -> dict:
    """Crée un espace NEUF depuis un paquet. ValueError = paquet refusé, rien d'écrit (ou tout défait)."""
    pris, ignores = _lire_zip(data)
    plan = _preparer(pris, ignores)
    if len(espaces.lire()["espaces"]) >= espaces.MAX_ESPACES:
        raise ValueError(f"{espaces.MAX_ESPACES} espaces au plus : archivez-en ou supprimez-en un d'abord")
    vue = espaces.creer({"nom": _nom_libre(plan["nom"]), "couleur": plan["couleur"], "type": plan["type"],
                         "parent": plan["parent"]})
    eid, crees, kid = vue["id"], [], None
    try:
        if plan["plafond_usd"]:
            espaces.modifier(eid, {"plafond_usd": plan["plafond_usd"]})
        persona = dict(plan["persona"])
        espaces.ecrire_persona(eid, persona)
        contenus_espace.ecrire(eid, plan["contenus"])
        for etape, v in plan["onboarding"].items():
            onboarding_persona.enregistrer_etape(eid, etape, v)
        if plan["identite"]:
            identite.ecrire(eid, plan["identite"])
        for genre, png in plan["images"]:
            identite.ajouter_image(eid, genre, png)
        if plan["kit"]:
            k = plan["kit"]
            kid = brand_kits.enregistrer(dict(k["champs"], **({"id": identite.kit_id(eid)} if k["idv"] else {})))
            if k["logo"]:
                (brand_kits.dossier() / "logos").mkdir(parents=True, exist_ok=True)
                (brand_kits.dossier() / "logos" / f"{kid}.png").write_bytes(k["logo"])
            espaces.modifier(eid, {"kit_id": kid})
        if plan["fiche"] is not None:    # t306 : la fiche, puis une ligne `import` au journal
            fiche_client._poser(eid, plan["fiche"])
            fiche_client.noter(eid, "import", "", "utilisateur")
        ressaisir = []
        for c in plan["comptes"]:
            v = comptes.creer({"espace_id": eid, "plateforme": c["plateforme"], "libelle": c["libelle"],
                               "handle": c["handle"]})
            crees.append(v["id"])
            if c["publics"]:
                comptes.poser(v["id"], c["publics"])
            ressaisir.append({"compte": v["id"], "plateforme": c["plateforme"], "libelle": v["libelle"],
                              "champs": c["a_ressaisir"]})
    except Exception:
        for cid in crees:
            try:
                comptes.supprimer(cid)
            except Exception:  # noqa: BLE001 — défaire au mieux, puis dire l'erreur d'origine
                pass
        if kid:
            try:
                brand_kits.supprimer(kid)
            except Exception:  # noqa: BLE001
                pass
        _retirer_espace(eid)
        raise
    return {"espace": [v for v in espaces.lister(archives=True) if v["id"] == eid][0], "a_ressaisir": ressaisir,
            "ignores": ignores}
