# -*- coding: utf-8 -*-
"""Lot L7-B — D-34 (24/09/2026) : NOTE ETOILE DES RENDUS, EN BASE.

Plan `docs/superpowers/plans/2026-09-24-plan-montage-resolve-L7B.md`,
decision n°5 et Tache 7. Une note 0..5 par RENDU (job) : colonne
`jobs.rating INTEGER` posee par la migration EXISTANTE (liste de paires
`V1_2_NEW_COLUMNS` + boucle `_auto_migrate`), `PUT /api/jobs/{id}/rating
{rating:0..5}` (0 = sans note), `_job_to_dict` rend `rating` (0 si NULL),
`Pipeline.list_jobs(..., min_rating=0)` filtre AVANT le `limit` et
`GET /api/jobs?min_rating=` le passe.

Ecart au plan (24/09/2026, decide par le controleur) : ce banc est un
fichier NEUF et non la section [5] de `test_montage_l7b.py` (edite en
parallele par un autre agent).

ETAT VIDE CONSTRUIT : la base TMP est creee AVANT le lifespan avec la forme
d'une base ANCIENNE — la table `jobs` telle qu'elle etait avant ce lot (les
colonnes de base + `V1_2_NEW_COLUMNS` lues au module, SANS `rating`) — et des
lignes. Le lifespan (`init_db`) doit alors AJOUTER la colonne sans perdre une
ligne. Le filtre de note est juge sur un jeu ou les rendus notes sont les
PLUS ANCIENS : un filtre applique APRES le `limit` rendrait une page 1 vide
(temoin : la meme page sans filtre ne contient AUCUN rendu note).

Transfert entre machines (`transfert.fusionner_base`, mesure l.336-383) :
les colonnes fusionnees sont l'INTERSECTION source/cible — un paquet d'une
machine sans `rating` entre (note NULL -> 0), et un paquet AVEC `rating` vers
une base sans la colonne entre aussi (colonne ignoree). Les deux sens sont
bances.

En-tete recopie de test_montage_eb.py (env AVANT `import app`, `check`,
`J`/`L`). Run : & $PY tests/test_montage_l7b_notes.py   (depuis backend/)

PROTOCOLE : toute reponse passe par `J()`/`L()` (jamais `.json()` nu), tout
acces est un `.get`. Une negation ne vaut que si son operande a vecu.
"""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzl7bn_")
DB = TMP + "/deepotus.db"          # = transfert.racine() / NOM_BASE
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + DB.replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import sqlite3, datetime as _dt                          # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def J(resp):
    """Corps JSON dict, ou {} — ce banc doit ROUGIR, pas mourir."""
    try:
        v = resp.json()
    except Exception:
        return {}
    return v if isinstance(v, dict) else {}


def L(resp):
    """Corps JSON liste de dicts, ou None (une liste vide reste une liste)."""
    try:
        v = resp.json()
    except Exception:
        return None
    return [j for j in v if isinstance(j, dict)] if isinstance(v, list) else None


def sql1(db, q):
    """Premiere ligne d'une requete, ou None — une colonne absente (etat
    rouge) fait rougir le check, pas mourir le banc."""
    try:
        with sqlite3.connect(db) as cx:
            return cx.execute(q).fetchone()
    except sqlite3.Error:
        return None


def cols_de(db, table="jobs"):
    with sqlite3.connect(db) as cx:
        return [r[1] for r in cx.execute(f'pragma table_info("{table}")')]


# ---- [0] base ANCIENNE construite avant le lifespan ----
from app.services import storage as _st                  # noqa: E402  (pas de connexion)
_BASE_COLS = [("id", "VARCHAR(36) NOT NULL PRIMARY KEY"), ("status", "VARCHAR(40)"),
              ("progress", "INTEGER"), ("image_filename", "VARCHAR(255)"),
              ("final_prompt", "TEXT"), ("negative_prompt", "TEXT"),
              ("video_path", "VARCHAR(500)"), ("audio_path", "VARCHAR(500)"),
              ("final_video_path", "VARCHAR(500)"), ("caption_text", "TEXT"),
              ("caption_path", "VARCHAR(500)"), ("error", "TEXT"),
              ("created_at", "DATETIME"), ("completed_at", "DATETIME")]
_ANCIENNES = _BASE_COLS + [(n, t) for (n, t) in _st.V1_2_NEW_COLUMNS if n != "rating"]
_T0 = _dt.datetime(2026, 9, 24, 12, 0, 0)
N_JOBS = 30
# les 6 plus ANCIENS sont notes (k=0..5) ; tout le reste est sans note
NOTES = {f"j{k:02d}": (k % 6) for k in range(6)}        # j00:0 j01:1 ... j05:5
with sqlite3.connect(DB) as _cx:
    _cx.execute("CREATE TABLE jobs (" + ", ".join(f"{n} {t}" for n, t in _ANCIENNES) + ")")
    for k in range(N_JOBS):
        jid = f"j{k:02d}"
        _cx.execute("INSERT INTO jobs (id, status, progress, title, image_filename, provider, "
                    "video_path, created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (jid, "done", 100, f"Rendu {k}", "x.png", "seedance", f"/out/{jid}.mp4",
                     (_T0 + _dt.timedelta(seconds=k)).isoformat(sep=" ")))
    _cx.commit()
AVANT = cols_de(DB)
with sqlite3.connect(DB) as _cx:
    LIGNES_AVANT = _cx.execute("select id, title, video_path, created_at from jobs order by id").fetchall()
print("\n[0] etat vide : la base ancienne n'a pas la colonne")
check("n0_base_ancienne_sans_rating_mais_avec_ses_colonnes",
      "rating" not in AVANT and "video_model" in AVANT and "title" in AVANT, AVANT)
check("n0_base_ancienne_porte_les_30_lignes", len(LIGNES_AVANT) == N_JOBS, len(LIGNES_AVANT))

from fastapi.testclient import TestClient                # noqa: E402
from app.main import app                                 # noqa: E402
c = TestClient(app, raise_server_exceptions=False)
c.__enter__()

print("\n[1] migration : colonne ajoutee, lignes intactes")
APRES = cols_de(DB)
check("n1_migration_ajoute_rating_par_la_liste_existante",
      "rating" in APRES and "rating" not in AVANT
      and ("rating", "INTEGER") in list(_st.V1_2_NEW_COLUMNS), (AVANT[-3:], APRES[-3:]))
with sqlite3.connect(DB) as _cx:
    LIGNES_APRES = _cx.execute("select id, title, video_path, created_at from jobs order by id").fetchall()
NULS = (sql1(DB, "select count(*) from jobs where rating is null") or (-1,))[0]
check("n1_lignes_intactes_apres_migration",
      len(LIGNES_AVANT) == N_JOBS and LIGNES_APRES == LIGNES_AVANT, (len(LIGNES_APRES),))
check("n1_lignes_anciennes_sans_note_null", NULS == N_JOBS, NULS)
check("n1_le_modele_porte_rating", "rating" in _st.JobRecord.__table__.columns,
      list(_st.JobRecord.__table__.columns.keys())[-3:])

print("\n[2] _job_to_dict rend rating (0 si NULL)")
r = c.get("/api/jobs/j10"); d = J(r)
check("n2_get_job_rend_rating_0_si_null",
      r.status_code == 200 and d.get("job_id") == "j10" and "rating" in d and d.get("rating") == 0
      and d.get("rating") is not None, (r.status_code, d.get("rating", "ABSENT")))
from app.api import routes as _routes                    # noqa: E402
_jr = _st.JobRecord(id="zz", status="done", image_filename="x.png")
_d_nul = _routes._job_to_dict(_jr)
_jr.rating = 4
_d_4 = _routes._job_to_dict(_jr)
check("n2_job_to_dict_direct_nul_0_et_4_4",
      _d_nul.get("job_id") == "zz" and _d_nul.get("rating", "ABSENT") == 0
      and _d_4.get("rating", "ABSENT") == 4, (_d_nul.get("rating", "ABSENT"), _d_4.get("rating", "ABSENT")))
check("n2_rating_est_un_int_pas_un_bool",
      type(_d_4.get("rating")) is int and type(_d_nul.get("rating")) is int,
      (type(_d_4.get("rating")), type(_d_nul.get("rating"))))

print("\n[3] PUT /api/jobs/{id}/rating : bornes, types, 404")
for jid, n in NOTES.items():
    rp = c.put(f"/api/jobs/{jid}/rating", json={"rating": n}); dp = J(rp)
    check(f"n3_put_{jid}_note_{n}_rend_200_et_la_note",
          rp.status_code == 200 and dp.get("job_id") == jid and dp.get("rating") == n,
          (rp.status_code, dp.get("rating", "ABSENT"), dp.get("detail")))
rg = c.get("/api/jobs/j05"); dg = J(rg)
check("n3_note_persistee_lue_par_get", rg.status_code == 200 and dg.get("rating") == 5,
      (rg.status_code, dg.get("rating", "ABSENT")))
_v = sql1(DB, "select rating from jobs where id='j05'")
check("n3_note_ecrite_en_base", _v is not None and _v[0] == 5, _v)
MAUVAIS = [({"rating": 6}, "6"), ({"rating": -1}, "moins_1"), ({"rating": "3"}, "chaine_3"),
           ({"rating": 3.5}, "3_5"), ({"rating": 3.0}, "flottant_3_0"), ({"rating": True}, "bool_true"),
           ({"rating": False}, "bool_false"), ({"rating": None}, "null"), ({}, "absent"),
           ([3], "liste")]
for body, nom in MAUVAIS:
    rb = c.put("/api/jobs/j04/rating", json=body)
    check(f"n3_put_{nom}_rend_400", rb.status_code == 400, (rb.status_code, J(rb).get("detail")))
rb = c.put("/api/jobs/j04/rating", content=b"pas du json", headers={"content-type": "application/json"})
check("n3_put_corps_non_json_rend_400", rb.status_code == 400, rb.status_code)
rg4 = c.get("/api/jobs/j04"); dg4 = J(rg4)
check("n3_les_refus_ne_touchent_pas_la_note_4",
      rg4.status_code == 200 and dg4.get("rating") == 4, dg4.get("rating", "ABSENT"))
r404 = c.put("/api/jobs/inconnu/rating", json={"rating": 3})
check("n3_put_job_inconnu_rend_404_alors_que_3_est_valide",
      r404.status_code == 404 and c.put("/api/jobs/j03/rating", json={"rating": 3}).status_code == 200,
      r404.status_code)
# 0 = sans note : remise a zero d'un rendu note
c.put("/api/jobs/j29/rating", json={"rating": 2})
_avant0 = J(c.get("/api/jobs/j29")).get("rating")
r0 = c.put("/api/jobs/j29/rating", json={"rating": 0}); d0 = J(r0)
check("n3_put_0_remet_sans_note",
      _avant0 == 2 and r0.status_code == 200 and d0.get("rating") == 0, (_avant0, r0.status_code, d0.get("rating", "ABSENT")))

print("\n[4] GET /api/jobs?min_rating= : filtre AVANT le limit")
# notes posees : j01:1 j02:2 j03:3 j04:4 j05:5 (j00:0, j29 remis a 0)
ATT3 = ["j05", "j04", "j03"]          # created_at desc
r_sans = c.get("/api/jobs", params={"limit": 5}); l_sans = L(r_sans) or []
ids_sans = [j.get("job_id") for j in l_sans]
check("n4_temoin_page1_sans_filtre_ne_contient_aucun_note",
      r_sans.status_code == 200 and len(ids_sans) == 5 and not (set(ids_sans) & set(ATT3))
      and ids_sans[0] == "j29", ids_sans)
r3 = c.get("/api/jobs", params={"limit": 2, "min_rating": 3}); l3 = L(r3)
r3b = c.get("/api/jobs", params={"limit": 2, "offset": 2, "min_rating": 3}); l3b = L(r3b)
r3c = c.get("/api/jobs", params={"limit": 2, "offset": 4, "min_rating": 3}); l3c = L(r3c)
ids3 = [j.get("job_id") for j in (l3 or [])] + [j.get("job_id") for j in (l3b or [])]
check("n4_min_rating_3_pagine_juste_sur_deux_pages",
      r3.status_code == 200 and r3b.status_code == 200 and l3 is not None and l3b is not None
      and ids3 == ATT3, ids3)
check("n4_min_rating_3_page_au_dela_vide",
      r3c.status_code == 200 and l3c == [], (r3c.status_code, l3c))
check("n4_min_rating_3_ne_rend_que_des_notes_3_et_plus",
      l3 is not None and len(l3) == 2 and all((j.get("rating") or 0) >= 3 for j in (l3 or []) + (l3b or [])),
      [(j.get("job_id"), j.get("rating")) for j in (l3 or [])])
r5 = c.get("/api/jobs", params={"limit": 24, "min_rating": 5}); l5 = L(r5)
check("n4_min_rating_5_good_take_seul_j05",
      r5.status_code == 200 and [j.get("job_id") for j in (l5 or [])] == ["j05"], l5 and [j.get("job_id") for j in l5])
r_0 = c.get("/api/jobs", params={"limit": 50, "min_rating": 0}); l_0 = L(r_0)
check("n4_min_rating_0_rend_tout", r_0.status_code == 200 and l_0 is not None and len(l_0) == N_JOBS,
      l_0 and len(l_0))
r_9 = c.get("/api/jobs", params={"limit": 50, "min_rating": 9}); l_9 = L(r_9)
check("n4_min_rating_hors_bornes_ramene_a_5",
      r_9.status_code == 200 and [j.get("job_id") for j in (l_9 or [])] == ["j05"], l_9 and [j.get("job_id") for j in l_9])
r_m = c.get("/api/jobs", params={"limit": 50, "min_rating": -3}); l_m = L(r_m)
check("n4_min_rating_negatif_ramene_a_0", r_m.status_code == 200 and l_m is not None and len(l_m) == N_JOBS,
      l_m and len(l_m))
# « rendu 2 » vise Rendu 2 et Rendu 20..29 (11 lignes) ; seule j02 porte >= 2
r_q = c.get("/api/jobs", params={"limit": 50, "min_rating": 2, "q": "rendu 2"}); l_q = L(r_q)
r_q0 = c.get("/api/jobs", params={"limit": 50, "q": "rendu 2"}); l_q0 = L(r_q0)
check("n4_min_rating_se_compose_avec_q",
      r_q.status_code == 200 and [j.get("job_id") for j in (l_q or [])] == ["j02"]
      and len(l_q0 or []) == 11, (l_q and [j.get("job_id") for j in l_q], len(l_q0 or [])))
import asyncio                                           # noqa: E402
from app.services.pipeline import Pipeline               # noqa: E402
try:
    _pl = [j.id for j in asyncio.run(Pipeline.list_jobs(limit=1, min_rating=4))]
except Exception as e:                                   # etat rouge : argument inconnu
    _pl = repr(e)
check("n4_pipeline_list_jobs_min_rating_direct", _pl == ["j05"], _pl)

print("\n[5] transfert entre machines : colonne toleree dans les deux sens")
from app.services import transfert as _tr               # noqa: E402
# (a) paquet d'une machine SANS rating -> cette base (avec rating)
PAQ_A = TMP + "/paquet_a.db"
with sqlite3.connect(PAQ_A) as _cx:
    _cx.execute("CREATE TABLE jobs (" + ", ".join(f"{n} {t}" for n, t in _ANCIENNES) + ")")
    _cx.execute("INSERT INTO jobs (id, status, progress, title, image_filename, provider, video_path, created_at) "
                "VALUES ('ta1','done',100,'Transfert A','x.png','seedance','/out/ta1.mp4','2026-09-01 10:00:00')")
    _cx.commit()
from pathlib import Path                                 # noqa: E402
ra = _tr.fusionner_base(Path(PAQ_A), "", "")
ga = c.get("/api/jobs/ta1"); dga = J(ga)
check("n5_paquet_sans_rating_entre_et_se_lit_0",
      (ra.get("ajoutees") or {}).get("jobs") == 1 and ga.status_code == 200 and dga.get("rating") == 0,
      (ra, ga.status_code, dga.get("rating", "ABSENT")))
# (b) paquet AVEC rating -> une base SANS la colonne (autre racine)
RAC_B = Path(TMP) / "machine_b"; RAC_B.mkdir()
with sqlite3.connect(str(RAC_B / _tr.NOM_BASE)) as _cx:
    _cx.execute("CREATE TABLE jobs (" + ", ".join(f"{n} {t}" for n, t in _ANCIENNES) + ")")
    _cx.commit()
PAQ_B = TMP + "/paquet_b.db"
with sqlite3.connect(DB) as _src, sqlite3.connect(PAQ_B) as _dst:
    _src.backup(_dst)
_racine_orig = _tr.racine
_tr.racine = lambda: RAC_B
try:
    rb_ = _tr.fusionner_base(Path(PAQ_B), "", "")
finally:
    _tr.racine = _racine_orig
with sqlite3.connect(str(RAC_B / _tr.NOM_BASE)) as _cx:
    nb_b = _cx.execute("select count(*) from jobs").fetchone()[0]
cols_b = cols_de(str(RAC_B / _tr.NOM_BASE))
check("n5_paquet_avec_rating_entre_dans_une_base_sans_la_colonne",
      (rb_.get("ajoutees") or {}).get("jobs") == N_JOBS + 1 and nb_b == N_JOBS + 1
      and "rating" not in cols_b and "rating" in cols_de(PAQ_B), (rb_, nb_b))
# (c) meme base des deux cotes : la note voyage
RAC_C = Path(TMP) / "machine_c"; RAC_C.mkdir()
with sqlite3.connect(PAQ_B) as _src, sqlite3.connect(str(RAC_C / _tr.NOM_BASE)) as _dst:
    _dst.execute("CREATE TABLE jobs (" + ", ".join(f"{n} {t}" for n, t in _ANCIENNES) + ", rating INTEGER)")
    _dst.commit()
_tr.racine = lambda: RAC_C
try:
    rc_ = _tr.fusionner_base(Path(PAQ_B), "", "")
finally:
    _tr.racine = _racine_orig
_n5 = sql1(str(RAC_C / _tr.NOM_BASE), "select rating from jobs where id='j05'")
check("n5_la_note_voyage_quand_les_deux_bases_ont_la_colonne",
      (rc_.get("ajoutees") or {}).get("jobs") == N_JOBS + 1 and _n5 is not None and _n5[0] == 5, (rc_, _n5))

c.__exit__(None, None, None)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
