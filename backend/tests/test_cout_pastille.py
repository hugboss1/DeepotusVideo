"""La pastille de cout DIT le blanc — du backend jusqu'au pixel.

CE QUE CE BANC FERME. La tache 8b a fait rendre 0 a tout provider non tarife,
sous la cle `non-tarifé:<provider>` de `by_provider`, « pour que le blanc porte
un nom ». MESURE alors : la chaine `by_provider` n'apparaissait NULLE PART dans
`frontend/dist/assets/index-BEOJX8L5.js` — la pastille n'affichait que
`total_usd`. Le blanc se nommait dans l'API et mourait avant l'ecran ; un total
INCOMPLET s'y presentait comme un total.

CE QUE LA PASTILLE DIT DESORMAIS (patch `scripts/patch_bundle_dzcout.py`) :
  * son infobulle liste `by_provider` ligne a ligne, montant compris ;
  * une ligne non tarifee y est NOMMEE comme telle (« coût inconnu, absent de
    ce total ») et le provider y apparait SANS son prefixe technique ;
  * des qu'il en existe une, le total passe de « $x » a « ≥ $x » et une pastille
    ambre « · N non tarifé(s) » s'ajoute. Un MINORANT annonce vaut mieux qu'un
    total qui se tait.

LA SEULE LIGNE QUI VAILLE VRAIMENT, ET C'EST LA RAISON D'ETRE DE CE BANC :
`prefixe_du_bundle_est_celui_du_backend`. Le decoupage `x.slice(P.length)` du
bundle et la cle `f"non-tarifé:{prov}"` de `_job_to_cost` sont DEUX litteraux
dans DEUX langages, dans DEUX fichiers. Rien d'autre ne les tient ensemble :
renommer l'un laisse l'autre vert, et l'ecran afficherait alors le prefixe brut
comme s'il etait un nom de fournisseur. Ce banc les fait donc mesurer L'UN PAR
L'AUTRE — la charge utile vient de `GET /api/cost/usage` (l'app ASGI, aucun
serveur lance) et le prefixe est EXTRAIT du bundle, jamais recopie ici.

LE CŒUR EST EXTRAIT DU BUNDLE LIVRE, PAS DU PATCHER. On lit le fichier que
l'application charge vraiment : c'est la seule facon de voir qu'un maillon
amont relance seul a efface la section — le mode de panne qui a deja coute
vingt-deux correctifs a ce depot. Meme lecon que `test_montage_bundle.py`.

CE QUE CE BANC N'AFFIRME PAS
  * Que ce soit BEAU, ni meme visible : aucune capture, aucun navigateur. Il
    dit que le texte existe, qu'il est juste, et que la fonction qui le
    fabrique s'execute. Le rendu se regarde a l'ecran, par l'utilisateur.
  * Que la pastille se rafraichisse : elle lit `cost/usage` au montage du
    Shell, et ce lot n'y touche pas.
  * Que `by_provider` porte un COMPTE de jobs. La carte ne dit pas COMBIEN de
    jobs sont non tarifes, seulement QUELS providers le sont ; l'infobulle ne
    promet donc pas de nombre de jobs.
  * Aucun rendu, aucun appel reseau, aucun backend demarre.

Run: & $PY tests/test_cout_pastille.py   (un processus, depuis backend/)
"""
import asyncio
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzpast_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from httpx import AsyncClient, ASGITransport                # noqa: E402
from app.main import app                                    # noqa: E402
from app.services.storage import (JobRecord,                # noqa: E402
                                  async_session_factory, init_db)

ROOT = pathlib.Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
PATCHER = ROOT / "scripts" / "patch_bundle_dzcout.py"

ok = fail = 0
_plantages = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def temoin(e):
    """TEMOIN d'un appel qui a LEVE — NUMEROTE et DISTINGUABLE."""
    global _plantages
    _plantages += 1
    return "%s: %s ·ECHEC#%d" % (type(e).__name__, e, _plantages)


def LIT(p):
    """Le texte d'un fichier, ou un temoin. Un fichier absent doit ROUGIR."""
    try:
        return p.read_text(encoding="utf-8", newline="")
    except Exception as e:
        t = temoin(e)
        print(f"  ----  lecture de {p.name} : {t}")
        return t


# ── [0] les deux fichiers du lot ────────────────────────────────────────────
print("\n[0] le patcher et le bundle livre.")
check("patcher_present", PATCHER.is_file(), str(PATCHER))
check("bundle_present", BUNDLE.is_file(), str(BUNDLE))
S = LIT(BUNDLE) if BUNDLE.is_file() else "·ECHEC#0 bundle absent"


def charge_patcher():
    """Le patcher IMPORTE (aucune recopie de ses ancres ici), ou un temoin."""
    try:
        spec = importlib.util.spec_from_file_location("dzcout_patcher", PATCHER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:
        t = temoin(e)
        print(f"  ----  import du patcher : {t}")
        return None


P = charge_patcher()


# ── [1] MIROIR DU BUNDLE LIVRE ──────────────────────────────────────────────
print("\n[1] chaque couple ancre -> remplacement du patcher, dans le bundle.")
_paires = getattr(P, "PATCHES", None) if P is not None else None
check("patcher_expose_sa_table_de_patches",
      isinstance(_paires, list) and len(_paires) >= 3,
      repr(type(_paires)) + " " + str(len(_paires or [])))
for _tag, _anc, _rep in (_paires or []):
    check(f"bundle_porte_{_tag}", S.count(_rep) == 1,
          f"remplacement x{S.count(_rep)} (want 1)")
    # Quand le remplacement ne REPREND pas l'ancre, elle doit avoir DISPARU :
    # sinon le patch a ete applique deux fois, ou pas au bon endroit.
    if _anc not in _rep:
        check(f"ancre_consommee_{_tag}", S.count(_anc) == 0,
              f"ancre x{S.count(_anc)} (want 0)")

# Le marqueur, compte EXACT : une definition, un export, une infobulle, et
# quatre lectures dans la pastille. Un compte libre laisserait passer une
# double application.
check("marqueur_compte_exact", S.count("__dzCoutBlanc") == 7,
      f"x{S.count('__dzCoutBlanc')} (want 7)")


# ── [2] la syntaxe du bundle n'a pas bouge ──────────────────────────────────
print("\n[2] node --check sur le bundle entier — SCRIPT puis MODULE.")


def node(args, **kw):
    try:
        return subprocess.run(["node"] + args, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=300,
                              **kw)
    except Exception as e:
        t = temoin(e)
        print(f"  ----  node {args[:2]} : {t}")

        class _Echec:
            returncode = -1
            stdout = t
            stderr = t
        return _Echec()


_r = node(["--check", str(BUNDLE)])
check("node_check_script", _r.returncode == 0, (_r.stderr or "")[-300:])
# index.html charge le bundle en <script type="module">, ou deux declarations
# du meme nom au premier niveau sont une SyntaxError que le check SCRIPT ne
# voit pas. La preambule ajoute UNE declaration de plus : c'est exactement la
# classe d'erreur qu'il faut mesurer ici.
if BUNDLE.is_file():
    with BUNDLE.open("rb") as _fh:
        _r = node(["--input-type=module", "--check"], stdin=_fh)
    check("node_check_module", _r.returncode == 0, (_r.stderr or "")[-300:])
else:
    check("node_check_module", False, "bundle absent")


# ── [3] le CŒUR, EXTRAIT DU BUNDLE ET EXECUTE ───────────────────────────────
print("\n[3] `__dzCoutBlanc` extrait du bundle livre, execute sous node,")
print("    sur des cartes rendues par GET /api/cost/usage.")
_DEB = "function __dzCoutBlanc(u){"
_FIN = "window.__dzCoutBlanc=__dzCoutBlanc;"
_i = S.find(_DEB)
_k = S.find(_FIN, _i) if _i >= 0 else -1
CŒUR = S[_i:_k + len(_FIN)] if _i >= 0 and _k > _i else ""
check("cœur_extrait_du_bundle", len(CŒUR) > 200,
      f"debut={_i} fin={_k} longueur={len(CŒUR)}")
if not CŒUR:
    # un cœur VIDE ferait passer toutes les lignes suivantes par le temoin ;
    # on pose une definition qui NE PEUT PAS repondre juste, plutot que rien.
    CŒUR = ("function __dzCoutBlanc(u){return {n:-1,noms:['·ECHEC'],"
            "titre:'·ECHEC extraction'}}var window={};"
            "window.__dzCoutBlanc=__dzCoutBlanc;")

# LE PREFIXE, LU DANS LE BUNDLE — jamais recopie. C'est lui que la ligne
# `prefixe_du_bundle_est_celui_du_backend` confronte a la cle du backend.
_j = CŒUR.find('P="')
PREFIXE_BUNDLE = CŒUR[_j + 3:CŒUR.find('"', _j + 3)] if _j >= 0 else "·ECHEC"
check("prefixe_lisible_dans_le_cœur", _j >= 0 and 3 < len(PREFIXE_BUNDLE) < 40,
      repr(PREFIXE_BUNDLE))

asyncio.run(init_db())
_n_pose = 0


def carte(*jobs):
    """La carte que la pastille recevra VRAIMENT : on pose les jobs, on lit
    `GET /api/cost/usage` par l'app ASGI, on depose. Rend un dict-TEMOIN dont
    `by_provider` n'existe pas — aucune assertion ne peut alors verdir."""
    global _n_pose
    ids = []
    for prov, champs in jobs:
        _n_pose += 1
        ids.append(("beef0000-0000-0000-0000-%012d" % _n_pose, prov, champs))

    async def go():
        async with async_session_factory() as s:
            for jid, prov, champs in ids:
                s.add(JobRecord(id=jid, status="done", progress=100,
                                image_filename="temoin_pastille.png",
                                provider=prov, **champs))
            await s.commit()
        try:
            async with AsyncClient(transport=ASGITransport(app=app),
                                   base_url="http://t", timeout=120.0) as c:
                r = await c.get("/api/cost/usage")
            d = r.json()
            return d if isinstance(d, dict) else {"_temoin": repr(d)}
        finally:
            async with async_session_factory() as s:
                for jid, _p, _c in ids:
                    j = await s.get(JobRecord, jid)
                    if j is not None:
                        await s.delete(j)
                await s.commit()

    try:
        return asyncio.run(go())
    except Exception as e:
        t = temoin(e)
        print(f"  ----  carte({[j[0] for j in jobs]}) : {t}")
        return {"_temoin": t}


CAS = [
    ("vide", carte()),
    ("tarife", carte(("seedance", {"duration_s": 10}),
                     ("montage", {"duration_s": 72}))),
    ("un_blanc", carte(("seedance", {"duration_s": 10}),
                       ("provider_de_demain", {"duration_s": 45}))),
    ("deux_blancs", carte(("provider_de_demain", {}),
                          ("autre_provider", {}))),
]
# La cle que le BACKEND a ecrite, relevee sur la carte reelle (pas construite
# ici) : c'est elle que le bundle doit savoir decouper.
_bp = (CAS[2][1].get("by_provider") or {})
CLES_BLANCHES = sorted(k for k in _bp if not k.startswith("fal"))
check("le_backend_a_bien_pose_une_cle_blanche", len(CLES_BLANCHES) == 1,
      f"{_bp}")
CLE_BLANCHE = CLES_BLANCHES[0] if CLES_BLANCHES else "·ECHEC_aucune_cle"

# LA LIGNE DU LOT : deux litteraux, deux langages, deux fichiers.
check("prefixe_du_bundle_est_celui_du_backend",
      len(CLES_BLANCHES) == 1 and CLE_BLANCHE.startswith(PREFIXE_BUNDLE)
      and CLE_BLANCHE[len(PREFIXE_BUNDLE):] == "provider_de_demain",
      f"cle backend={CLE_BLANCHE!r} prefixe bundle={PREFIXE_BUNDLE!r}")

_dir = pathlib.Path(TMP)
(_dir / "cas.json").write_text(
    json.dumps([c for _n, c in CAS], ensure_ascii=False), encoding="utf-8")
(_dir / "shim.js").write_text(
    "var window={};\n" + CŒUR + "\n"
    "var cas=JSON.parse(require('fs').readFileSync("
    + json.dumps(str(_dir / "cas.json")) + ",'utf8'));\n"
    "console.log(JSON.stringify(cas.map(function(c){"
    "return window.__dzCoutBlanc(c)})));\n",
    encoding="utf-8")
_r = node([str(_dir / "shim.js")])
check("cœur_s_execute_sous_node", _r.returncode == 0, (_r.stderr or "")[-400:])
try:
    RES = json.loads(_r.stdout or "[]")
except Exception as e:
    RES = [{"n": -1, "noms": [temoin(e)], "titre": temoin(e)}] * len(CAS)
R = dict(zip([n for n, _c in CAS], RES)) if len(RES) == len(CAS) else {}
check("une_reponse_par_cas", len(RES) == len(CAS),
      f"{len(RES)} reponse(s) pour {len(CAS)} cas — {_r.stdout[:200]!r}")


def _r_de(nom):
    """La reponse du cas `nom`, ou un TEMOIN dont `n` est NEGATIF et le titre
    une chaine marquee : `n == 0` est alors faux, et `"MINORANT" in titre`
    aussi. Un cas manquant ne peut pas verdir une ligne."""
    return R.get(nom) or {"n": -1, "noms": ["·ECHEC"], "titre": "·ECHEC absent"}

_v = _r_de("vide")
check("carte_vide_ne_nomme_aucun_blanc", _v.get("n") == 0, repr(_v))
check("carte_vide_le_dit_au_lieu_de_mentir",
      "Aucune" in str(_v.get("titre")), repr(_v.get("titre"))[:200])

_t = _r_de("tarife")
# On exige D'ABORD que l'infobulle porte le fournisseur ET son montant : sans
# cela, « elle ne dit pas MINORANT » serait vrai d'une chaine vide.
check("carte_tarifee_liste_le_fournisseur_et_son_montant",
      "fal" in str(_t.get("titre")) and "0.403" in str(_t.get("titre")),
      repr(_t.get("titre"))[:250])
check("carte_tarifee_n_annonce_aucun_minorant",
      "fal" in str(_t.get("titre")) and _t.get("n") == 0
      and "MINORANT" not in str(_t.get("titre")), repr(_t)[:250])
# Un « local — $0 » nu se lit comme une panne. La ligne DIT pourquoi elle est
# a zero : un rendu local ne depense rien, et ce n'est pas la meme chose
# qu'un cout inconnu. Le job `montage` du cas fabrique cette ligne-la.
check("carte_tarifee_explique_le_zero_local",
      "local" in str(_t.get("titre"))
      and "opérations locales" in str(_t.get("titre")),
      repr(_t.get("titre"))[:300])

_u = _r_de("un_blanc")
check("un_blanc_est_compte", _u.get("n") == 1, repr(_u)[:250])
check("un_blanc_est_nomme_dans_l_infobulle",
      "provider_de_demain" in str(_u.get("titre")), repr(_u.get("titre"))[:250])
# ... et NOMME, pas exhibe : le prefixe technique ne doit pas passer a l'ecran.
# La premiere moitie interdit la version vacante (un titre vide passerait).
# ELLE COMPARE A LA CLE DU BACKEND, PAS AU PREFIXE DU BUNDLE, et c'est la
# table de mutations qui l'a impose : ecrite avec `PREFIXE_BUNDLE`, elle etait
# CIRCULAIRE — renommer le prefixe d'UN SEUL cote (mutations 0 et 1) laissait
# l'ecran afficher « non-tarifé:provider_de_demain » en entier et la ligne
# restait VERTE, puisqu'elle cherchait le prefixe MUTE, absent par
# construction. MESURE le 05/09/2026 : trois lignes verdissaient ainsi.
check("un_blanc_sans_son_prefixe_technique",
      "provider_de_demain" in str(_u.get("titre"))
      and CLE_BLANCHE not in str(_u.get("titre")),
      repr(_u.get("titre"))[:250])
check("un_blanc_annonce_un_minorant",
      "MINORANT" in str(_u.get("titre")), repr(_u.get("titre"))[:250])
# le total tarife du MEME cas reste dit : le blanc s'ajoute, il n'efface pas.
check("un_blanc_n_efface_pas_la_depense_reelle",
      "fal" in str(_u.get("titre")) and "0.403" in str(_u.get("titre")),
      repr(_u.get("titre"))[:250])

_d = _r_de("deux_blancs")
check("deux_blancs_sont_comptes", _d.get("n") == 2, repr(_d)[:250])
check("deux_blancs_nomment_les_deux",
      "provider_de_demain" in str(_d.get("titre"))
      and "autre_provider" in str(_d.get("titre")),
      repr(_d.get("titre"))[:300])
check("deux_blancs_accordent_le_pluriel",
      "fournisseurs" in str(_d.get("titre")), repr(_d.get("titre"))[:300])


# ── [4] rougir plutot que mourir ────────────────────────────────────────────
check("aucun_appel_n_a_plante", _plantages == 0,
      f"{_plantages} appel(s) ont leve — voir les lignes « ---- » ci-dessus")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
