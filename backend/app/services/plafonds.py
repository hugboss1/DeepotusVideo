"""Plafonds de dépense mensuels (plan Settings T4-T6 — tâche #16 du suivi, 29/09/2026).

MESURE D'ABORD (29/09) : environ 48 routes non-GET dépensent chez un fournisseur (vidéo, images, voix, musique, SFX,
3D, LLM, transcription…) et n'ont AUCUN point d'entrée commun ; seules quelques-unes chiffrent un devis (garde par
requête `max_usd`, retours-IA F3 / P1 #9). La garde MENSUELLE est donc UNE fonction, `verifier()`, appelée juste
AVANT la dépense dans chacune d'elles — un recensement AST (banc test_plafonds_garde) refuse qu'une route payante
l'oublie.

Décisions de l'utilisateur (29/09) : le plafond GLOBAL est le champ existant « Monthly budget cap »
(`pricing.json` → `monthly_budget_usd`, 0 = aucun) ; les plafonds PAR MOTEUR et le seuil d'alerte vivent dans
`DATA_ROOT/plafonds.json`. `verifier()` VÉRIFIE ET ENREGISTRE l'estimation en un appel : un tir qui échoue ensuite
chez le fournisseur laisse une ligne un peu trop chère — c'est le sens SÛR pour un plafond (on sur-compte, jamais
l'inverse) ; la colonne « réel » corrige là où le fournisseur donne un chiffre (T6 : crédits Meshy, delta HeyGen).

La confirmation d'un dépassement voyage par une ContextVar posée par le middleware de `main.py` AVANT `call_next`
(l'en-tête `X-DZ-Plafond: confirme`) ; l'alerte à 80 % est TIRÉE par l'écran (`/api/reglages/plafonds/etat`).
"""
import json
import time
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select

from app.config import DATA_ROOT

_FICHIER = DATA_ROOT / "plafonds.json"
DEFAUTS = {"global_usd": 0.0, "par_moteur": {}, "alerte_pct": 80}

# Les écrans qui peuvent dépenser — le vocabulaire des catégories.
CATEGORIES = ("quick", "studio", "chapitres", "son", "montage", "news", "scheduler", "bibliotheque", "sprites",
              "tuiles", "matieres", "cartes", "moteurs3d", "marketing", "atelier", "vectorlab", "reglages",
              "dictee")

CONFIRME: ContextVar[bool] = ContextVar("dz_plafond_confirme", default=False)


def _global_usd() -> float:
    """Le plafond global = `monthly_budget_usd` de la grille (lu comme la garde par requête lit ses réglages :
    illisible, négatif ou non fini -> 0, jamais une ouverture)."""
    from app.services import pricing as _pricing
    try:
        return float(_pricing._reglage_fini(_pricing.load(), "monthly_budget_usd"))
    except Exception:  # noqa: BLE001
        return 0.0


def _moteurs_valides(pm) -> dict:
    out = {}
    for k, v in (pm or {}).items() if isinstance(pm, dict) else []:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        if v > 0 and v == v and v != float("inf"):
            out[str(k)[:24]] = float(v)
    return out


def charger() -> dict:
    d = {"global_usd": _global_usd(), "par_moteur": {}, "alerte_pct": 80}
    try:
        if _FICHIER.is_file():
            brut = json.loads(_FICHIER.read_text(encoding="utf-8"))
            if isinstance(brut, dict):
                d["par_moteur"] = _moteurs_valides(brut.get("par_moteur"))
                a = brut.get("alerte_pct")
                if isinstance(a, (int, float)) and not isinstance(a, bool):
                    d["alerte_pct"] = max(1, min(100, int(a)))
    except (OSError, ValueError, TypeError):
        pass
    return d


def enregistrer(d: dict) -> dict:
    """Écrit le global dans la GRILLE (monthly_budget_usd, fusion — P1 #9) et le reste dans plafonds.json. FUSION :
    une clé absente garde sa valeur (un écran qui n'envoie que les moteurs n'efface pas le global)."""
    from app.services import pricing as _pricing
    d = d or {}
    cur = charger()
    g = d.get("global_usd", cur["global_usd"])
    try:
        g = float(g) if not isinstance(g, bool) and g is not None else 0.0
    except (TypeError, ValueError):
        g = 0.0
    g = g if (g >= 0 and g == g and g != float("inf")) else 0.0
    _pricing.save({"monthly_budget_usd": g})
    a = d.get("alerte_pct", cur["alerte_pct"])
    try:
        a = max(1, min(100, int(a))) if a is not None and not isinstance(a, bool) else 80
    except (TypeError, ValueError):
        a = 80
    propre = {"par_moteur": _moteurs_valides(d.get("par_moteur", cur["par_moteur"])), "alerte_pct": a}
    _FICHIER.parent.mkdir(parents=True, exist_ok=True)
    tmp = _FICHIER.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(propre, indent=2), encoding="utf-8")
    tmp.replace(_FICHIER)
    return charger()


@asynccontextmanager
async def _registre():
    """Une session dont la table `depenses` EXISTE : créée à la volée (`checkfirst`) sur une base qui ne l'a pas —
    mesuré le 29/09 : les bancs Cardforge ouvrent une base sans `init_db`, et la garde y cassait la route en 500.
    Dans la transaction de la session : une lecture sans commit ne laisse rien derrière elle."""
    from app.services.storage import Depense, async_session_factory
    async with async_session_factory() as s:
        conn = await s.connection()
        await conn.run_sync(lambda sc: Depense.__table__.create(sc, checkfirst=True))
        yield s


def mois_courant() -> str:
    """Heure LOCALE : « mon mois » est celui du calendrier de l'utilisateur, pas celui d'UTC."""
    return time.strftime("%Y-%m")


async def _cumul(mois: str) -> dict:
    """Somme du mois, relue en base, par moteur : estimé, réel (quand connu), EFFECTIF = réel là où il existe,
    estimé ailleurs."""
    from app.services.storage import Depense
    par: dict[str, dict] = {}
    depuis = ""
    async with _registre() as s:
        lignes = (await s.execute(select(Depense).where(Depense.mois == mois))).scalars().all()
        prem = (await s.execute(select(Depense).order_by(Depense.quand))).scalars().first()
        if prem is not None:
            depuis = prem.quand.strftime("%Y-%m-%d")
    for l in lignes:
        d = par.setdefault(l.moteur, {"estime_usd": 0.0, "reel_usd": 0.0, "effectif_usd": 0.0, "lignes": 0})
        d["estime_usd"] = round(d["estime_usd"] + (l.estime_usd or 0.0), 6)
        if l.reel_usd is not None:
            d["reel_usd"] = round(d["reel_usd"] + l.reel_usd, 6)
            d["effectif_usd"] = round(d["effectif_usd"] + l.reel_usd, 6)
        else:
            d["effectif_usd"] = round(d["effectif_usd"] + (l.estime_usd or 0.0), 6)
        d["lignes"] += 1
    return {"par_moteur": par, "depuis": depuis, "mois": mois}


async def etat(mois: str | None = None) -> dict:
    """L'état du mois pour l'écran : totaux, pourcentages, alertes au seuil."""
    mois = mois or mois_courant()
    p = charger()
    c = await _cumul(mois)
    par = c["par_moteur"]
    tot = {k: round(sum(v[k] for v in par.values()), 6) for k in ("estime_usd", "reel_usd", "effectif_usd")}
    seuil = p["alerte_pct"]
    alerte = []
    gp = p["global_usd"]
    tot["pct"] = round(100.0 * tot["effectif_usd"] / gp, 1) if gp > 0 else 0.0
    tot["plafond_usd"] = gp
    if gp > 0 and tot["pct"] >= seuil:
        alerte.append("global")
    for m, v in par.items():
        pm = float(p["par_moteur"].get(m) or 0.0)
        v["plafond_usd"] = pm
        v["pct"] = round(100.0 * v["effectif_usd"] / pm, 1) if pm > 0 else 0.0
        if pm > 0 and v["pct"] >= seuil:
            alerte.append(m)
    return {"mois": mois, "global": tot, "par_moteur": par, "plafonds": p, "alerte": alerte, "depuis": c["depuis"]}


# Tâche #21 (plan Settings T18, 29/09/2026) — le tableau réel contre estimé.
# Les moteurs qui savent dire ce qu'ils ont VRAIMENT facturé (Meshy : crédits consommés ; HeyGen : delta du solde d'un
# rendu seul en vol). Pour les autres (fal, ElevenLabs, les LLM), « estimé » n'est pas un défaut : c'est tout ce qui existe.
RAPPROCHABLES = {"meshy", "heygen"}


async def tableau(mois: str | None = None) -> dict:
    """Une ligne par (moteur, catégorie), avec l'ÉTAT de son chiffre — jamais mélangés :
      reel                   tous les tirs du groupe ont un réel fournisseur ;
      reel-partiel           une partie seulement : l'effectif mêle réel et estimé, et le nombre est dit ;
      estime                 ce moteur ne facture pas à l'appel : l'estimé est la seule vérité disponible ;
      estime-non-rapproche   un moteur rapprochable dont AUCUN tir n'a pu être rattaché — le taire le ferait
                             passer pour un estimé ordinaire.
    L'effectif se calcule LIGNE par LIGNE (réel là où il existe, estimé ailleurs), comme `_cumul` des plafonds ;
    l'écart (réel − estimé) ne porte que sur les tirs rapprochés, jamais sur un réel absent."""
    from app.services.storage import Depense
    mois = mois or mois_courant()
    groupes: dict = {}
    depuis = ""
    async with _registre() as s:
        lignes = (await s.execute(select(Depense).where(Depense.mois == mois))).scalars().all()
        prem = (await s.execute(select(Depense).order_by(Depense.quand))).scalars().first()
        if prem is not None:
            depuis = prem.quand.strftime("%Y-%m-%d")
    for l in lignes:
        g = groupes.setdefault((l.moteur, l.categorie or ""), {
            "moteur": l.moteur, "categorie": l.categorie or "", "tirs": 0, "rapproches": 0,
            "estime_usd": 0.0, "reel_usd": None, "reel_unites": None, "effectif_usd": 0.0, "ecart_usd": None})
        g["tirs"] += 1
        est = float(l.estime_usd or 0.0)
        g["estime_usd"] = round(g["estime_usd"] + est, 6)
        if l.reel_usd is not None:
            g["rapproches"] += 1
            g["reel_usd"] = round((g["reel_usd"] or 0.0) + l.reel_usd, 6)
            g["ecart_usd"] = round((g["ecart_usd"] or 0.0) + (l.reel_usd - est), 6)
            g["effectif_usd"] = round(g["effectif_usd"] + l.reel_usd, 6)
        else:
            g["effectif_usd"] = round(g["effectif_usd"] + est, 6)
        if l.reel_unites is not None:
            g["reel_unites"] = round((g["reel_unites"] or 0.0) + l.reel_unites, 4)
    out = []
    for g in groupes.values():
        if g["rapproches"] and g["rapproches"] == g["tirs"]:
            g["etat"] = "reel"
        elif g["rapproches"]:
            g["etat"] = "reel-partiel"
        elif g["moteur"] in RAPPROCHABLES:
            g["etat"] = "estime-non-rapproche"
        else:
            g["etat"] = "estime"
        out.append(g)
    out.sort(key=lambda g: (-g["effectif_usd"], g["moteur"], g["categorie"]))
    te = round(sum(g["estime_usd"] for g in out), 6)
    tr = round(sum(g["reel_usd"] or 0.0 for g in out), 6)
    tf = round(sum(g["effectif_usd"] for g in out), 6)
    return {"mois": mois, "depuis": depuis, "lignes": out,
            "total": {"estime_usd": te, "reel_usd": tr, "effectif_usd": tf,
                      "couverture_pct": round(100.0 * tr / tf, 1) if tf else 0.0}}


def _fr(v: float) -> str:
    """Deux décimales ; sous 0,10 $ jusqu'à quatre (mesuré en preuve le 29/09 : « 0,01 $ au-dessus de 0,00 $ » pour
    un devis de 0,006 $ contre un plafond de 0,001 $ — un refus qui se contredit)."""
    v = float(v) + 0.0
    if v == 0 or abs(v) >= 0.1:
        return f"{v:.2f}".replace(".", ",")
    s = f"{v:.4f}".rstrip("0")
    return (s + "0" if len(s.split(".")[1]) < 2 else s).replace(".", ",")


def _refus(motif, moteur, deja, devis, plafond, categorie) -> HTTPException:
    ou = f" (écran « {categorie} »)" if categorie else ""
    qui = "toutes dépenses confondues" if motif == "global" else f"le moteur « {moteur} »"
    msg = (f"Plafond mensuel atteint : {qui} a déjà coûté {_fr(deja)} $ ce mois-ci ; ce tir{ou} ajouterait "
           f"{_fr(devis)} $ et passerait au-dessus de {_fr(plafond)} $. Confirmez pour tirer quand même, ou relevez "
           f"le plafond dans Réglages → Pricing & budget.")
    return HTTPException(402, {"dz_plafond": {
        "motif": motif, "moteur": moteur, "categorie": categorie, "deja_usd": round(deja, 4),
        "devis_usd": round(devis, 4), "plafond_usd": round(plafond, 4), "message": msg}})


async def verifier(op: dict, categorie: str = "", ref: str | None = None, confirme: bool | None = None) -> dict:
    """LA garde, à appeler juste AVANT la dépense. Rend {devis, lignes (ids écrits), etat}. Lève 402 (detail
    `dz_plafond`) quand le devis ferait passer le mois au-dessus d'un plafond et que l'utilisateur n'a pas confirmé.
    Un refus n'écrit rien ; un devis nul (local, gratuit) n'encombre pas le registre."""
    from app.services import pricing as _pricing
    from app.services.storage import Depense

    devis = _pricing.estimate(op or {})
    p = charger()
    mois = mois_courant()
    ok = CONFIRME.get() if confirme is None else bool(confirme)
    if not ok and (p["global_usd"] > 0 or p["par_moteur"]):
        par = (await _cumul(mois))["par_moteur"]
        deja_g = sum(v["effectif_usd"] for v in par.values())
        gp = p["global_usd"]
        if gp > 0 and devis["total_usd"] > 0 and deja_g + devis["total_usd"] > gp + 1e-9:
            raise _refus("global", "", deja_g, devis["total_usd"], gp, categorie)
        for m in sorted({l["provider"] for l in devis["breakdown"]}):
            pm = float(p["par_moteur"].get(m) or 0.0)
            if pm <= 0:
                continue
            deja = par.get(m, {}).get("effectif_usd", 0.0)
            somme = sum(x["usd"] for x in devis["breakdown"] if x["provider"] == m)
            if somme > 0 and deja + somme > pm + 1e-9:
                raise _refus("moteur", m, deja, somme, pm, categorie)

    kind = str((op or {}).get("kind") or "")[:32]
    neuves = []
    async with _registre() as s:
        for ligne in devis["breakdown"]:
            if not ligne["usd"] or ligne["usd"] <= 0:
                continue          # gratuit (local, cache) : il n'encombre pas le registre
            d = Depense(quand=datetime.utcnow(), mois=mois, moteur=str(ligne["provider"])[:24],
                        categorie=str(categorie or "")[:24], op=kind, estime_usd=float(ligne["usd"]),
                        ref=(ref[:64] if ref else None))
            s.add(d)
            neuves.append(d)
        await s.commit()
        ids = [d.id for d in neuves]
    return {"devis": devis, "lignes": ids, "etat": {"mois": mois}}


async def rattacher(ids: list[int], ref: str) -> int:
    """Colle une référence aux lignes qu'un `verifier()` vient d'écrire : l'id d'une tâche Meshy ou d'un job HeyGen
    n'existe QU'APRÈS la réservation ; sans ce rattachement le coût réel ne serait jamais rapproché (ou deviné)."""
    from app.services.storage import Depense
    if not ids or not ref:
        return 0
    n = 0
    async with _registre() as s:
        for i in ids:
            d = await s.get(Depense, i)
            if d is not None:
                d.ref = ref[:64]
                n += 1
        await s.commit()
    return n


async def noter_reel(ref: str, usd: float | None, unites: float | None) -> int:
    """Le fournisseur a facturé : on écrit le réel sur CETTE référence. Rend le nombre de lignes touchées (0 =
    référence inconnue, dit dans le journal plutôt que d'inventer une ligne)."""
    from app.services.storage import Depense
    if not ref:
        return 0
    n = 0
    async with _registre() as s:
        lignes = (await s.execute(select(Depense).where(Depense.ref == ref))).scalars().all()
        for l in lignes:
            if usd is not None:
                l.reel_usd = float(usd)
            if unites is not None:
                l.reel_unites = float(unites)
            n += 1
        await s.commit()
    if not n:
        logger.info(f"plafonds.noter_reel: référence inconnue {ref!r} — ignorée")
    return n


_HEYGEN_EN_VOL = 0
_HEYGEN_DEBUTS = 0   # compteur de départs : un rendu démarré ET fini pendant le nôtre se voit ici


@asynccontextmanager
async def suivi_heygen(ref: str, lire_quota=None):
    """Encadre UN rendu HeyGen pour en tirer le coût réel. HeyGen ne facture pas par vidéo : la seule vérité est le
    solde du compte (`HeyGenClient.remaining_quota()`). Le delta avant/après n'est attribuable qu'à un seul rendu en
    vol : à deux rendus concurrents, « réel » reste vide et le journal le dit, plutôt que d'inventer un chiffre."""
    global _HEYGEN_EN_VOL, _HEYGEN_DEBUTS

    async def _defaut():
        from app.services.heygen_service import HeyGenClient
        q = await HeyGenClient().remaining_quota()
        v = q.get("remaining_quota") if isinstance(q, dict) else None
        return float(v) if v is not None else None

    lire = lire_quota or _defaut
    deja_en_vol = _HEYGEN_EN_VOL
    _HEYGEN_EN_VOL += 1
    _HEYGEN_DEBUTS += 1
    depart = _HEYGEN_DEBUTS
    try:
        avant = await lire()
    except Exception:  # noqa: BLE001 — un solde muet ne casse pas un rendu
        avant = None
    try:
        yield
    finally:
        seul = (deja_en_vol == 0 and _HEYGEN_DEBUTS == depart)   # personne avant nous, personne pendant
        _HEYGEN_EN_VOL -= 1
        try:
            apres = await lire() if (avant is not None and seul) else None
        except Exception:  # noqa: BLE001
            apres = None
        if avant is not None and apres is not None and apres <= avant:
            from app.services import pricing as _pricing
            credits = float(avant - apres)
            await noter_reel(ref, credits * float(_pricing.load()["heygen_credit_usd"]), credits)
        else:
            logger.info(f"plafonds.suivi_heygen({ref}) : coût réel non attribuable "
                        f"(rendus concurrents ou quota illisible) — estimé conservé")


async def rattacher_meshy(ids: list[int], task_id) -> int:
    """Rattache les lignes d'une garde à la tâche Meshy `meshy:<id>` ; si la tâche est DÉJÀ terminale dans le
    journal (`meshy_tasks`, la passe de texture attend la fin avant de rendre la main), son `consumed_credits` —
    seule vérité comptable de Meshy — devient aussitôt le réel. Sinon c'est `meshy_service.record_state` qui le
    notera à l'arrivée de l'état terminal."""
    tid = str(task_id or "").strip()
    if not tid:
        return 0
    n = await rattacher(ids, f"meshy:{tid}")
    from app.services.storage import MeshyTaskRecord, async_session_factory
    async with async_session_factory() as s:
        row = await s.get(MeshyTaskRecord, tid)
        fini = row is not None and row.status in ("SUCCEEDED", "FAILED", "CANCELED")
        cc = int(row.consumed_credits or 0) if row is not None else 0
    if fini:
        await noter_meshy(tid, cc)
    return n


async def noter_meshy(task_id: str, credits: int) -> int:
    """Le réel d'une tâche Meshy terminée : crédits consommés x `meshy_credit_usd` de la grille."""
    from app.services import pricing as _pricing
    c = float(credits or 0)
    return await noter_reel(f"meshy:{task_id}", c * float(_pricing.load()["meshy_credit_usd"]), c)


def op_llm(in_tok: float = 2000, out_tok: float = 800, fournisseur: str | None = None) -> dict:
    """L'op d'estimation d'UN appel LLM, au fournisseur que `_chat_dispatch` essaiera d'abord
    (`summarizer.active_provider()` ; aucun -> local, gratuit). Écart daté : `_chat_dispatch` bascule vers un autre
    fournisseur en cas d'échec — le fournisseur réellement facturé peut différer."""
    prov = (fournisseur or "").strip().lower()
    if not prov:
        try:
            from app.services.summarizer import active_provider
            prov = (active_provider() or "").strip().lower()
        except Exception:  # noqa: BLE001
            prov = ""
    return {"kind": "llm", "provider": prov or "local", "in_tok": int(max(0, in_tok)), "out_tok": int(max(0, out_tok))}
