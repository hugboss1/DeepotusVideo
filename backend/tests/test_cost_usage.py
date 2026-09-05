"""GET /api/cost/usage — ce que `_job_to_cost` facture, provider par provider.

CE QUE CE BANC FERME (P7, tache 8b). `_job_to_cost` nommait `heygen`,
`episode` et `sprite2d`, puis retombait sur une branche « campaign » PAR
DEFAUT qui facturait `duration_s or 10` secondes de Seedance PLUS une image
FLUX — 0,403 USD par job aux tarifs par defaut de `pricing.load()` — pour
TOUT provider qu'elle ne nommait pas. Le cas `montage_proxy` avait ete ferme
par un `where` (65afc16) ; la branche, elle, restait ouverte.

LE PROTOCOLE DE MESURE, ET IL A DU ETRE REFAIT. La base tourne en mode WAL :
au 05/09/2026 `deepotus.db` pesait 4,60 Mo et son `-wal` 4,54 Mo. Une COPIE
D'OCTETS du seul `.db` perd tout ce que le WAL porte — elle rendait 105 jobs
`done` la ou la base en compte 116, et 43,41 USD la ou l'application en
affichait 51,90. Les chiffres ci-dessous sont pris sur un instantane COHERENT
(`sqlite3.Connection.backup()`, qui fusionne le WAL), jamais sur la base
vivante. Tarifs effectifs = defauts : le seul `pricing.json` de la machine ne
surcharge que `seedance_usd_per_s`, a sa propre valeur.

L'ANCIENNE BRANCHE EST REJOUEE, SA TRANSCRIPTION VERIFIEE : le total qu'elle
rend sur cet instantane reproduit au cent pres le `total_usd` que l'API du
backend INSTALLE (encore a 65afc16) rend sur la vraie base — 51,90. Sans cette
egalite, la colonne « avant » ne vaudrait rien.

LA MESURE QUI A TRANCHE (116 jobs `done` ; `scratchpad/mesure_avant.py` et
`mesure_defaut.py`) — 98,9 % du total affiche passait par la branche par
defaut :

  provider       n      avant     apres   ce que le job depense VRAIMENT
  seedance      35     18,885    18,885   1 image + N s de video : JUSTE
  template      33     13,299     0,000   RIEN — job PARENT, les sous-jobs
                                          (composition_id=parent) portent
                                          deja leur propre depense
  montage        4      6,332     0,000   RIEN — assemblage ffmpeg local
  <NULL>        13      5,239     5,239   seedance d'avant la colonne
                                          `provider` (13/13 portent un png
                                          ET une video) : JUSTE
  ugc            9      4,307     0,000   RIEN — fichier TELEVERSE par
                                          l'utilisateur (`await
                                          file.read()`, aucune API)
  asset3d        7      2,821     2,480   un maillage, desormais au tarif du
                                          maillage (rodin/hunyuan/tripo/
                                          tripo-h3.1) et non d'une video
  news           1      0,403     0,000   RIEN — reel ffmpeg local
  animation      1      0,323     0,000   RIEN — ffmpeg + PIL locaux
  heygen         5      0,240     0,240   branche nommee, juste
  sprite2d       8      0,048     0,048   branche nommee, juste
  TOTAL        116     51,900    26,890

  DEPENSE FABRIQUEE (template + montage + ugc + news + animation) :
  24,664 USD sur 51,900 AFFICHES, soit 47,5 % du chiffre montre a
  l'utilisateur. Les deux providers que la base ne porte pas encore tombaient
  dans la meme branche : `composition` (job parent, comme `template`) et
  `card3d` (« RIEN N'EST CONSTRUIT ICI : publier n'est pas fabriquer »,
  forge3d l. 3898).

LA DECISION — une LISTE BLANCHE explicite, et un ZERO QUI SE NOMME pour tout
le reste. Voir la docstring de `_job_to_cost` pour le raisonnement complet.
Ce banc en tient les trois moities :
  [1] les providers qui ne depensent rien rendent 0 et une ligne `local` ;
  [2] ceux qui depensent continuent de payer (garde contre le zero general) ;
  [3] un provider INCONNU rend 0 et SE NOMME dans `by_provider`
      (`non-tarifé:<provider>`), au lieu d'une facture inventee.

CE QUE CE BANC N'AFFIRME PAS
  * Que la facture soit JUSTE au centime. Elle reste DIRECTIONNELLE par
    construction (chaque fournisseur facture l'utilisateur en direct) et
    reglable dans `pricing.json`. Les lignes non nulles comparent au
    resultat de `pricing.estimate` du MEME devis, jamais a un litteral : ce
    qui est mesure est le ROUTAGE, pas le prix.
  * Que l'image FLUX d'une campagne ait toujours ete facturee. Un job
    Seedance parti d'une image FOURNIE par l'utilisateur n'a rien paye a
    FLUX ; la ligne reste chargee (0,003 USD, soit 0,3 % du total mesure) et
    rien dans la ligne de base ne permet de trancher.
  * Que le tarif Meshy d'un texturage soit exact : `cost_meta` du chemin
    `texturier=meshy` n'enregistre PAS la resolution, donc le devis prend le
    defaut de `credits_retexture` (2k = 10 credits). C'est une depense REELLE
    a un tarif directionnel, pas une depense inventee.
  * Que `by_provider` atteigne le PIXEL. Ce banc s'arrete a l'API. Au moment
    ou il a ete ecrit, la chaine `by_provider` n'apparaissait NULLE PART dans
    `frontend/dist/assets/index-BEOJX8L5.js` : la pastille n'affichait que
    `total_usd`. C'est la tache 8c qui l'a portee a l'ecran
    (`scripts/patch_bundle_dzcout.py`), et c'est `tests/test_cout_pastille.py`
    qui le mesure — pas une ligne d'ici.
  * Aucun rendu, aucun appel reseau, aucun ffmpeg. Ce banc pose des lignes en
    base et lit UNE route.

LA FAUTE N°6 DU CHANTIER (« un banc qui MEURT au lieu de rougir ») est tenue
ici par `_cout`, qui garde la pose, l'appel ET la depose, et par la ligne
`aucun_appel_n_a_plante` en queue. Un devis illisible rend un TEMOIN
DISTINGUABLE (`{"_temoin": "…·ECHEC#n"}`), jamais `{}` ni `None` : sans quoi
« ce provider ne coute rien » serait VRAI de tout job jamais pose.

Run: & $PY tests/test_cost_usage.py   (un processus, depuis backend/)
"""
import asyncio
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzcout_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from httpx import AsyncClient, ASGITransport                # noqa: E402
from app.main import app                                    # noqa: E402
from app.services import pricing as P                       # noqa: E402
from app.services.storage import (JobRecord,                # noqa: E402
                                  async_session_factory, init_db)

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


asyncio.run(init_db())
TARIFS = P.load()


def _devis(op):
    """Le devis de reference, garde. Rend un flottant NEGATIF en cas d'echec —
    aucune facture ne peut l'atteindre, donc aucune egalite ne verdit a vide,
    et le `> 0` en tete de chaque ligne le refuse explicitement."""
    try:
        return P.estimate(op, TARIFS)["total_usd"]
    except Exception as e:
        temoin(e)
        return -1.0


_n_pose = 0


def _cout(prov, **champs):
    """Pose UN job `done`, lit `GET /api/cost/usage`, depose le job.

    Rend `{"total_usd": …, "by_provider": {…}}`, ou un dict-TEMOIN dont
    aucune cle attendue n'existe : `.get("total_usd") == 0.0` est alors FAUX
    et `by_provider == {"local": 0.0}` aussi. Un banc qui ne peut pas poser
    son job ROUGIT, il ne verdit pas.

    La depose est dans un `finally` : la route lit TOUS les jobs `done`, donc
    un job oublie ferait mentir toutes les mesures SUIVANTES."""
    global _n_pose
    _n_pose += 1
    jid = "cafe0000-0000-0000-0000-%012d" % (_n_pose,)

    async def go():
        async with async_session_factory() as s:
            s.add(JobRecord(id=jid, status="done", progress=100,
                            image_filename="temoin_cout.png",
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
                j = await s.get(JobRecord, jid)
                if j is not None:
                    await s.delete(j)
                    await s.commit()

    try:
        return asyncio.run(go())
    except Exception as e:
        t = temoin(e)
        print(f"  ----  cout({prov!r}) a leve : {t}")
        return {"_temoin": t}


# ── [0] la base du banc est bien VIDE ────────────────────────────────────────
print("\n[0] la base du banc est vide — sans quoi tout total mesure autre chose.")
_vide = _cout("montage_proxy")   # ecarte par le `where` de la route (65afc16)
check("base_du_banc_vide_hors_le_job_pose",
      isinstance(_vide, dict) and "_temoin" not in _vide
      and _vide.get("total_usd") == 0.0
      and (_vide.get("by_provider") or {}) == {},
      repr(_vide))


# ── [1] les providers qui NE DEPENSENT RIEN ─────────────────────────────────
print("\n[1] les providers qui ne depensent rien — 0, et une ligne qui le dit.")
# `duration_s` est pose EXPRES et GRAND la ou la base reelle en porte un
# (montage 8..72 s, ugc 10..21 s, animation 8 s) : c'est LUI que la branche
# « campaign » convertissait en secondes de Seedance. Une ligne posee SANS
# duree verdirait aussi sur un code qui facture `duration_s or 10`.
SANS_DEPENSE = [
    ("montage",     {"duration_s": 72}, "assemblage ffmpeg local"),
    ("animation",   {"duration_s": 8},  "ffmpeg + PIL locaux"),
    ("ugc",         {"duration_s": 21}, "fichier televerse par l'utilisateur"),
    ("news",        {},                 "reel ffmpeg local"),
    ("template",    {},                 "job parent : les sous-jobs paient"),
    ("composition", {},                 "job parent : les sous-jobs paient"),
    ("card3d",      {},                 "publication : rien n'est fabrique"),
]
for _prov, _champs, _pourquoi in SANS_DEPENSE:
    _d = _cout(_prov, **_champs)
    # EGALITE EXACTE sur la carte, jamais « pas de fal dedans » : une carte
    # VIDE (job jamais pose) rendrait une inegalite VRAIE sans rien mesurer.
    check(f"cout_{_prov}_ne_coute_rien",
          _d.get("total_usd") == 0.0
          and (_d.get("by_provider") or {}) == {"local": 0.0},
          f"{_d} — {_pourquoi}")


# ── [2] ce qui DEPENSE continue de payer ────────────────────────────────────
print("\n[2] la garde contre le zero general — ce qui depense paie encore.")
_camp = _devis({"kind": "campaign", "ops": [{"kind": "image"},
                                            {"kind": "seedance",
                                             "duration_s": 10, "model": ""}]})
_d = _cout("seedance", duration_s=10)
check("cout_seedance_facture_son_image_et_sa_video",
      _camp > 0 and _d.get("total_usd") == round(_camp, 2)
      and (_d.get("by_provider") or {}) == {"fal": round(_camp, 4)},
      f"{_d} vs devis campagne {_camp}")
# Les 13 jobs `done` de la base reelle a `provider IS NULL` sont des rendus
# Seedance d'avant la colonne : 13/13 portent une image ET une video.
_d = _cout(None, duration_s=10)
check("cout_provider_nul_reste_une_campagne_seedance",
      _camp > 0 and _d.get("total_usd") == round(_camp, 2)
      and (_d.get("by_provider") or {}) == {"fal": round(_camp, 4)},
      f"{_d} vs devis campagne {_camp}")
_hg = _devis({"kind": "heygen", "minutes": max(0.2, 30 / 60.0)})
_d = _cout("heygen", duration_s=30)
check("cout_heygen_reste_sur_sa_branche_nommee",
      _hg > 0 and (_d.get("by_provider") or {}) == {"heygen": round(_hg, 4)},
      f"{_d} vs devis heygen {_hg}")


# ── [3] asset3d : au tarif du MAILLAGE, pas a celui d'une video ─────────────
print("\n[3] asset3d — le tarif de son moteur, lu dans `cost_meta`.")
# La base reelle porte trois asset3d `done` : deux `rodin`, un `hunyuan`.
for _moteur in ("rodin", "hunyuan"):
    _a3 = _devis({"kind": "asset3d", "engine": _moteur})
    _d = _cout("asset3d",
               cost_meta='{"engine": "%s", "job": "abcd1234"}' % _moteur)
    check(f"cout_asset3d_{_moteur}_est_facture_au_tarif_de_son_moteur",
          _a3 > 0 and _d.get("total_usd") == round(_a3, 2)
          and (_d.get("by_provider") or {}) == {"fal": round(_a3, 4)},
          f"{_d} vs devis asset3d {_moteur} {_a3}")
# Le texturage Meshy est facture en CREDITS MESHY : ni `fal`, ni une video.
_tx = _devis({"kind": "asset3d_texture"})
_d = _cout("asset3d", cost_meta='{"job": "abcd1234", "texturier": "meshy",'
                                ' "meshy_task": "t1", "version": 2}')
check("cout_asset3d_texturage_est_facture_en_credits_meshy",
      _tx > 0 and _d.get("total_usd") == round(_tx, 2)
      and (_d.get("by_provider") or {}) == {"meshy": round(_tx, 4)},
      f"{_d} vs devis retexture {_tx}")


# ── [4] l'INCONNU : zero, et il se nomme ────────────────────────────────────
print("\n[4] un provider inconnu — 0, et son nom dans la carte.")
_d = _cout("provider_de_demain", duration_s=45)
check("cout_provider_inconnu_ne_fabrique_aucune_depense",
      _d.get("total_usd") == 0.0, repr(_d))
# LE POINT DE TOUT LE LOT : un chiffre INVENTE est pire qu'un blanc AVOUE.
check("cout_provider_inconnu_se_nomme_dans_by_provider",
      (_d.get("by_provider") or {}) == {"non-tarifé:provider_de_demain": 0.0},
      repr(_d.get("by_provider")))


# ── [5] rougir plutot que mourir ────────────────────────────────────────────
check("aucun_appel_n_a_plante", _plantages == 0,
      f"{_plantages} appel(s) ont leve — voir les lignes « ---- » ci-dessus")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
