"""Routeur des réglages (plan Settings, tâche #15 du suivi, 29/09/2026).

Ce que l'écran Settings gagne vit ICI et pas dans les 10 000 lignes de `routes.py` : d'abord le diagnostic (T1-T3),
plus tard plafonds, guides fournisseurs, mise à jour, export, coffre. Monté par `main.py` sous `/api/reglages`,
comme les routeurs montage et cards.

Toute route qui lit ou teste des clés passe par `_local()` — la garde de boucle locale des Réglages
(`routes._require_localhost`, un seul propriétaire de la règle), GET compris : les aperçus de clés sont des Réglages.
"""
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.config import APP_VERSION

router = APIRouter()


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


async def _soldes() -> dict:
    """Les soldes en direct : un seul producteur (`/cost/balances`), deux lecteurs (la pastille du bandeau et le
    diagnostic). Remplacé au banc."""
    from app.api.routes import cost_balances
    return await cost_balances()


@router.get("/diagnostic")
async def diagnostic_complet(request: Request):
    """L'écran unique : version, poids disque, journal, clés (masquées), soldes."""
    _local(request)
    from app.api.routes import _ALLOWED_ENV_KEYS, _mask, _read_env_file
    from app.services import coffre as C, diagnostic as D
    env = _read_env_file()
    cles = []
    for k in sorted(_ALLOWED_ENV_KEYS):
        # tâche #20 : une clé absorbée par le coffre n'est pas « absente » ; coffre fermé -> « verrouillé » (None)
        v, source = env.get(k, ""), "env"
        if not v and C.ouvert() and C.lire_cle(k):
            v, source = C.lire_cle(k), "coffre"
        if not v and C.verrouille() and k in C.SECRETES:
            cles.append({"cle": k, "definie": None, "apercu": "", "source": "coffre-verrouille", "testable": D.testable(k)})
            continue
        cles.append({"cle": k, "definie": bool(v), "apercu": _mask(v), "source": source, "testable": D.testable(k)})
    try:
        soldes = await _soldes()
    except Exception as e:  # noqa: BLE001 — un solde muet ne masque pas le reste
        soldes = {"erreur": str(e)[:160]}
    return {"version": APP_VERSION, "disque": D.poids_disque(), "journal": D.journal_erreurs(),
            "cles": cles, "soldes": soldes}


@router.post("/diagnostic/cle")
async def diagnostic_cle(body: dict, request: Request):
    """Teste UNE clé. Sans `valeur`, la clé enregistrée est relue du `.env` : l'écran n'a jamais à renvoyer un secret
    au serveur pour le faire tester."""
    _local(request)
    from app.api.routes import _ALLOWED_ENV_KEYS, _read_env_file
    from app.services import diagnostic as D
    nom = str((body or {}).get("nom") or "").strip()
    if nom not in _ALLOWED_ENV_KEYS:
        raise HTTPException(400, f"clé inconnue ou non modifiable : {nom}")
    from app.services import coffre as C
    env = _read_env_file()
    if C.ouvert():          # tâche #20 : les clés du coffre ouvert se testent comme celles du .env
        env = {**{k: C.lire_cle(k) for k in C.cles_posees()}, **{k: v for k, v in env.items() if v}}
    if nom.startswith("X_"):
        return await D.tester_x(env)
    valeur = str((body or {}).get("valeur") or "") or env.get(nom, "")
    if not valeur and C.verrouille() and nom in C.SECRETES:
        raise HTTPException(409, "Coffre verrouillé : ouvrez-le pour tester cette clé.")
    return await D.tester_cle(nom, valeur)


@router.get("/guides")
async def lire_guides(request: Request):
    """Tâche #17 : où créer chaque clé, comment on est facturé, à quoi elle sert ici (FR/EN, liens datés)."""
    _local(request)
    from app.services import guides_fournisseurs as G
    return {"guides": G.tous()}


# ── mise à jour (plan Settings T10, tâche #18) ────────────────────────────────────────────────────────────────────

_MAJ_TACHES: set = set()


@router.get("/maj")
async def lire_maj(request: Request):
    """L'état connu : le cache (une vérification par jour au plus), jamais bloquant."""
    _local(request)
    from app.services import mise_a_jour as M
    return await M.verifier()


@router.post("/maj/verifier")
async def forcer_maj(request: Request):
    _local(request)
    from app.services import mise_a_jour as M
    return await M.verifier(force=True)


@router.post("/maj/telecharger")
async def telecharger_maj(request: Request):
    """Lance EN FOND le téléchargement de l'installeur de la dernière Release dans DATA_ROOT/telechargements (130 Mo :
    la route rend la main, l'écran suit /maj/telechargement). Ne le lance jamais : c'est l'utilisateur."""
    import asyncio
    _local(request)
    from app.services import mise_a_jour as M
    etat = await M.verifier()
    a = etat.get("asset") or {}
    if not etat.get("disponible") or not a.get("url"):
        raise HTTPException(404, "aucune mise à jour à télécharger")
    if M.etat_telechargement().get("en_cours"):
        raise HTTPException(409, "un téléchargement est déjà en cours")
    t = asyncio.create_task(M.telecharger(a["url"], a["nom"], a.get("octets") or 0))
    _MAJ_TACHES.add(t)
    t.add_done_callback(_MAJ_TACHES.discard)
    return {"ok": True, "lance": True, "nom": a["nom"], "octets": a.get("octets") or 0}


@router.get("/maj/telechargement")
async def suivre_telechargement(request: Request):
    _local(request)
    from app.services import mise_a_jour as M
    return M.etat_telechargement()


# ── le coffre (plan Settings T16, tâche #20) ─────────────────────────────────────────────────────────────────────


def _crypto_ou_503() -> None:
    """Tâche #20 : sans la roue `cryptography`, un 503 qui le dit, jamais un 500 muet au premier chiffrement."""
    from app.services import coffre as C
    try:
        C._aesgcm()
    except C.CoffreIndisponible as e:
        raise HTTPException(503, str(e))


def _mdp(body, cle="mot_de_passe") -> str:
    return str((body or {}).get(cle) or "")


@router.get("/coffre/etat")
async def coffre_etat(request: Request):
    _local(request)
    from app.services import coffre as C
    return {"pose": C.est_pose(), "ouvert": C.ouvert(), "retenu": C.retenu(),
            "cles": sorted(C.cles_posees()) if C.ouvert() else []}


@router.post("/coffre/poser")
async def coffre_poser(body: dict, request: Request):
    """Pose le coffre, l'ouvre, et y DÉPLACE les secrets du .env (ils quittent le fichier en clair)."""
    _local(request)
    _crypto_ou_503()
    from app.services import coffre as C
    mdp = _mdp(body)
    if len(mdp) < C.MDP_MIN:
        raise HTTPException(400, f"mot de passe trop court ({C.MDP_MIN} caractères au moins)")
    if C.est_pose():
        raise HTTPException(409, "un coffre existe déjà : ouvrez-le, ou changez son mot de passe — le reposer "
                                 "écraserait son contenu")
    C.poser(mdp, {})
    C.ouvrir(mdp)
    return {"ok": True, "absorbees": C.absorber_env()}


@router.post("/coffre/ouvrir")
async def coffre_ouvrir(body: dict, request: Request):
    _local(request)
    _crypto_ou_503()
    from app.services import coffre as C
    try:
        cles = C.ouvrir(_mdp(body))
    except C.MotDePasseInvalide as e:
        raise HTTPException(401, str(e))
    return {"ok": True, "cles": len(cles)}


@router.post("/coffre/fermer")
async def coffre_fermer(request: Request):
    _local(request)
    from app.services import coffre as C
    C.fermer()
    return {"ok": True}


@router.post("/coffre/mot-de-passe")
async def coffre_mot_de_passe(body: dict, request: Request):
    _local(request)
    _crypto_ou_503()
    from app.services import coffre as C
    try:
        C.changer_mot_de_passe(_mdp(body, "ancien"), _mdp(body, "nouveau"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except C.MotDePasseInvalide as e:
        raise HTTPException(401, str(e))
    return {"ok": True, "message": "Mot de passe changé ; l'ouverture automatique a été désarmée."}


@router.post("/coffre/retenir")
async def coffre_retenir(request: Request):
    _local(request)
    from app.services import coffre as C
    try:
        C.retenir()
    except C.CoffreVerrouille as e:
        raise HTTPException(409, str(e))
    return {"ok": True}


@router.post("/coffre/oublier")
async def coffre_oublier(request: Request):
    _local(request)
    from app.services import coffre as C
    C.oublier()
    return {"ok": True}


@router.post("/coffre/archive")
async def coffre_archive(body: dict, request: Request):
    """L'archive chiffrée portable (format DZKV1), rendue telle quelle ; son mot de passe est à part de celui du coffre."""
    import time as _t
    from fastapi.responses import Response
    _local(request)
    _crypto_ou_503()
    from app.services import coffre as C
    try:
        blob = C.archiver(_mdp(body))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except C.CoffreVerrouille as e:
        raise HTTPException(409, str(e))
    nom = f"DeepotusVideoGen-{_t.strftime('%Y-%m-%d')}.dzk"
    return Response(content=blob, media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{nom}"', "Cache-Control": "no-store"})


@router.post("/coffre/archive/importer")
async def coffre_archive_importer(request: Request, fichier: UploadFile = File(...), mot_de_passe: str = Form("")):
    _local(request)
    _crypto_ou_503()
    from app.services import coffre as C
    blob = await fichier.read(4_000_001)
    if len(blob) > 4_000_000:
        raise HTTPException(413, "archive trop lourde (4 Mo au plus)")
    try:
        return C.restaurer(blob, mot_de_passe)
    except C.MotDePasseInvalide as e:
        raise HTTPException(401, str(e))
    except C.CoffreVerrouille as e:
        raise HTTPException(409, str(e))


# ── plafonds de dépense mensuels (plan Settings T4-T6, tâche #16) ─────────────────────────────────────────────────


@router.get("/plafonds")
async def plafonds_lire(request: Request):
    """{global_usd (= « Monthly budget cap » de la grille), par_moteur, alerte_pct}."""
    _local(request)
    from app.services import plafonds as P
    return P.charger()


@router.post("/plafonds")
async def plafonds_ecrire(body: dict, request: Request):
    """Enregistre les plafonds ; les valeurs invalides sont écartées (rendu = ce qui est RÉELLEMENT enregistré)."""
    _local(request)
    from app.services import plafonds as P
    if not isinstance(body, dict):
        raise HTTPException(400, "corps illisible : un objet {global_usd, par_moteur, alerte_pct} est attendu")
    return P.enregistrer(body)


@router.get("/depenses")
async def depenses(request: Request, mois: str | None = None):
    """Tâche #21 : le tableau réel contre estimé du mois (ou `mois=AAAA-MM`). Le registre commence le jour où la
    garde des plafonds a été installée : `depuis` le dit, plutôt que de laisser croire à un historique qui n'existe pas."""
    _local(request)
    from app.services import plafonds as P
    if mois is not None and not (len(mois) == 7 and mois[4] == "-" and mois[:4].isdigit() and mois[5:].isdigit()):
        raise HTTPException(400, "mois illisible : AAAA-MM attendu")
    return await P.tableau(mois)


@router.get("/plafonds/etat")
async def plafonds_etat(request: Request, mois: str | None = None):
    """Le mois en cours (ou `mois=AAAA-MM`) : estimé, réel, effectif, pourcentages et alertes, global et par moteur."""
    _local(request)
    from app.services import plafonds as P
    if mois is not None and not (len(mois) == 7 and mois[4] == "-" and mois[:4].isdigit() and mois[5:].isdigit()):
        raise HTTPException(400, "mois illisible : AAAA-MM attendu")
    return await P.etat(mois)


# Tâche #22 (29/09/2026, plan Settings T19) : ce que le champ de recherche des Réglages sait trouver. `section` est la
# clé de la barre latérale de `xm` (celle que son setter ouvre), `rubrique` son libellé TEL QU'AFFICHÉ — le banc relit
# les deux dans le bundle livré. Écart au plan du 03/09 : une clé n'est indexée que LÀ où un écran l'affiche (9 lignes +
# Ollama sous « API keys », les réseaux sous « Connected accounts ») ; les clés autorisées qu'aucun écran ne montre
# (ANTHROPIC_MODEL, ELEVENLABS_VOICE_ID_*, …) n'y sont pas — la recherche mènerait dans le vide.
_RUBRIQUES = {
    "diag": "Diagnostic", "coffre": "Coffre", "keys": "API keys", "accounts": "Connected accounts",
    "personas": "Personas", "branding": "Branding", "pack": "Caption pack", "defaults": "Provider defaults",
    "paths": "Paths", "news": "News", "appearance": "Appearance", "pricing": "Pricing & budget",
    "transfert": "Transfert entre machines",
}
_INDEX_FIXE = [
    ("diag", "Diagnostic", "diagnostic santé état disque poids journal erreurs version soldes crédits test des clés"),
    ("diag", "Mise à jour", "mise à jour nouvelle version release télécharger installer github"),
    ("coffre", "Coffre à clés", "coffre mot de passe maître chiffrement verrouiller déverrouiller sécurité dpapi"),
    ("coffre", "Archive chiffrée des clés", "archive exporter importer clés second poste autre machine dzk mot de passe"),
    ("keys", "Clés API", "clé api jeton token fournisseur guide tester enregistrer"),
    ("accounts", "Comptes connectés", "comptes réseaux sociaux publication x twitter telegram youtube instagram tester"),
    ("personas", "Personas", "persona ton voix audience personnage profil"),
    ("branding", "Kit de marque", "marque logo nom de l'application couleur identité branding"),
    ("pack", "Pack de légendes", "légendes étiquettes tags emoji icône caption"),
    ("defaults", "Fournisseurs par défaut", "défaut fournisseur génération d'image flux gpt image voix résumeur "
                                            "planificateur modèle provider"),
    ("paths", "Dossiers et versions", "chemins dossier images sorties python ffmpeg version backend api"),
    ("news", "Flux d'actualités", "news actualités rss flux article ajouter rafraîchir"),
    ("appearance", "Apparence", "apparence animations mouvement réduit halo effets"),
    ("pricing", "Grille de prix", "prix tarif coût dollar grille estimation"),
    ("pricing", "Plafonds de dépense", "plafond budget limite mensuel alerte dépassement confirmation dépense"),
    ("pricing", "Dépenses du mois", "dépenses réel estimé facturé moteur écran tableau rapproché"),
    ("transfert", "Transfert entre machines", "transfert exporter importer sauvegarde copie autre machine empreintes "
                                              "intégrité sha256 lots"),
]
_CLES_ECRAN = {
    "keys": ("FAL_KEY", "HEYGEN_API_KEY", "ELEVENLABS_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
             "GEMINI_API_KEY", "GEMINI_MODEL", "MESHY_API_KEY", "FIGMA_TOKEN", "OLLAMA_URL", "OLLAMA_MODEL"),
    "accounts": ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "TELEGRAM_BOT_TOKEN",
                 "TELEGRAM_CHAT_ID", "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN",
                 "YOUTUBE_CHANNEL_ID", "IG_ACCESS_TOKEN", "IG_BUSINESS_ID",
                 # tâche #31 (30/09) : Connected accounts affiche TikTok
                 "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN", "TIKTOK_AUDITED"),
}


@router.get("/index")
async def index_reglages(request: Request):
    """Tout ce que la recherche des Réglages peut trouver, avec la section à ouvrir. Des NOMS et des MOTS seulement :
    aucune valeur ni aperçu de clé n'est lu ici."""
    _local(request)
    from app.api.routes import _ALLOWED_ENV_KEYS
    from app.services import guides_fournisseurs as G
    entrees = [{"section": s, "rubrique": _RUBRIQUES[s], "libelle": l, "cle": "", "mots": m} for s, l, m in _INDEX_FIXE]
    for s, cles in _CLES_ECRAN.items():
        for k in cles:
            if k not in _ALLOWED_ENV_KEYS:
                continue
            g = G.guide(k) or {}
            mots = " ".join(filter(None, ["clé", k.replace("_", " ").lower(), g.get("nom", ""), g.get("fr", "")[:220]]))
            entrees.append({"section": s, "rubrique": _RUBRIQUES[s], "libelle": g.get("nom") or k, "cle": k,
                            "mots": mots})
    return {"entrees": entrees}
