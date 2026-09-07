"""Transfert entre machines — l'aller-retour COMPLET, sur deux racines.

Demande du 07/09/2026 : exporter tout ce que l'application a créé, le
reprendre sur une autre machine, sans les clés, à l'identique.

Ce banc simule DEUX postes : une racine `poste_a` qui exporte, une racine
`poste_b` qui importe — avec un nom d'utilisateur DIFFÉRENT dans les
chemins, puisque c'est là que tombent les imports naïfs. Il vérifie que la
bibliothèque, la bible, les plans de communication et les rendus arrivent,
que les chemins absolus sont ré-ancrés, que la clé d'API ne part JAMAIS, et
qu'un second import ne détruit rien.

Style autonome (`check`) : un processus, une sortie `=== N passed ===`.
Run: python tests/test_transfert.py
"""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import traceback
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
_tmp = tempfile.mkdtemp(prefix="dztr_")
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{Path(_tmp, 't.db').as_posix()}"
os.environ["DEEPOTUS_DATA_DIR"] = str(Path(_tmp, "poste_a"))
os.environ.setdefault("FAL_KEY", "test-key")
Path(_tmp, "poste_a").mkdir(parents=True, exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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
    """Témoin NUMÉROTÉ : deux gardes qui sautent ne se valent jamais."""
    global _plantages
    _plantages += 1
    return f"{type(e).__name__}: {e} ·ECHEC#{_plantages}"


def G(quoi, thunk):
    """Garde à témoin : une levée devient une valeur distinguable, jamais
    une mort silencieuse du banc (faute n°6 du chantier)."""
    try:
        return thunk()
    except BaseException as e:                          # noqa: BLE001
        t = temoin(e)
        print(f"  ----  {quoi} a levé : {t}")
        traceback.print_exc(limit=2)
        return t


def refus(quoi, thunk):
    """Un refus ATTENDU rend son message — et ne compte PAS comme un
    plantage. `aucun_appel_n_a_plante` reste ainsi le temoin des levees
    IMPREVUES ; sans cette distinction il rougirait a chaque refus
    correctement mesure."""
    try:
        thunk()
        return f"AUCUN REFUS ({quoi})"
    except ValueError as e:
        return str(e)


from app.services import transfert as TR                # noqa: E402

A = Path(_tmp, "poste_a")            # la machine qui exporte
B = Path(_tmp, "poste_b")            # celle qui importe
DEST = Path(_tmp, "cle_usb")
B.mkdir(parents=True, exist_ok=True)
DEST.mkdir(parents=True, exist_ok=True)

# ── un poste A crédible : des assets, une base, et une clé d'API ──
SCHEMA = """
create table jobs (id text primary key, title text, provider text,
                   video_path text, final_video_path text,
                   image_filename text, audio_path text);
create table library_assets (filename text primary key, source text,
                             origin text);
create table bible_entities (id text primary key, name text,
                             model3d_file text);
create table scheduled_posts (id text primary key, texte text);
create table graphs (id text primary key, nom text);
"""


def semer_base(racine, prefixe, jid="j1", eid="e1", pid="p1",
               asset="logo.png", garder_ouverte=False):
    """Seme une base credible. `prefixe` est la racine du POSTE : c'est ce
    que l'application ecrit vraiment dans les colonnes de chemin absolu.

    `garder_ouverte` laisse la connexion vivante en mode WAL, avec des
    lignes NON fusionnees — l'etat d'une application qui tourne, et le seul
    ou une copie d'octets du `.db` ment (mesure du 05/09/2026)."""
    db = racine / "deepotus.db"
    c = sqlite3.connect(str(db))
    c.execute("pragma journal_mode=WAL")
    c.executescript(SCHEMA)
    c.execute("insert into jobs values (?,?,?,?,?,?,?)",
              (jid, "Memecoin", "seedance",
               prefixe + r"\assets\outputs\videos" + "\\" + jid + ".mp4",
               prefixe + r"\assets\outputs\final" + "\\" + jid + ".mp4",
               "vignette.png", None))
    c.execute("insert into library_assets values (?,?,?)",
              (asset, "studio", "depot"))
    c.execute("insert into bible_entities values (?,?,?)",
              (eid, "Deepotus",
               prefixe + r"\assets\outputs\assets3d" + "\\" + eid + ".glb"))
    c.execute("insert into scheduled_posts values (?,?)",
              (pid, "plan de communication du lundi"))
    c.commit()
    if garder_ouverte:
        return c              # le journal WAL reste NON fusionne
    c.close()
    return None


def ecrire(p: Path, texte: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texte, encoding="utf-8")


# La racine du poste A EST le prefixe de ses chemins absolus : c'est ce
# que l'application ecrit. Un prefixe litteral different n'aurait exerce
# aucun re-ancrage (trou trouve par mutation le 07/09/2026).
PREFIXE_A = str(A)
_conn_a = semer_base(A, PREFIXE_A, garder_ouverte=True)
ecrire(A / ".env", "ANTHROPIC_API_KEY=sk-ant-SECRET-A-NE-PAS-EXPORTER\n")
ecrire(A / ".env.bak.corrupted", "OPENAI_API_KEY=sk-AUSSI-SECRET\n")
ecrire(A / "pricing.json", '{"stt_usd_per_min": {"elevenlabs": 0.0067}}')
ecrire(A / "logs" / "deepotus-2026-09-07.log", "journal de la machine A")
ecrire(A / "assets" / "images" / "logo.png", "PNG-logo")
ecrire(A / "assets" / "montage_saved.json", '{"clips": [], "duration": 55}')
ecrire(A / "assets" / "outputs" / "final" / "j1.mp4", "MP4-final")
ecrire(A / "assets" / "outputs" / "videos" / "j1.mp4", "MP4-brut")
ecrire(A / "assets" / "outputs" / "assets3d" / "e1.glb", "GLB")
ecrire(A / "assets" / "outputs" / "_cache" / "proxy.json", "cache jetable")
ecrire(A / "assets" / "outputs" / "fxpreview" / "fx.png", "apercu jetable")
ecrire(A / "assets" / "vector" / "doc1.json", '{"v":"1"}')
ecrire(A / "cardforge_series" / "serie1.json", '{"nom":"serie 1"}')
# la base de A porte maintenant un VRAI journal WAL, non fusionne :
# `instantane_base` doit le lire, une copie d'octets le manquerait
check("la_base_du_poste_A_a_bien_un_journal_WAL_en_attente",
      (A / "deepotus.db-wal").exists()
      and (A / "deepotus.db-wal").stat().st_size > 0,
      str(sorted(p.name for p in A.glob("deepotus.db*"))))

# ── inventaire : ce qui part, ce qui ne part pas ──
fichiers, poids = TR.inventaire(A)
rels = [r for r, _ in fichiers]
check("l_inventaire_prend_la_bibliotheque_et_les_plans",
      "assets/images/logo.png" in rels
      and "assets/montage_saved.json" in rels
      and "assets/outputs/final/j1.mp4" in rels
      and "assets/vector/doc1.json" in rels
      and "cardforge_series/serie1.json" in rels
      and "pricing.json" in rels, str(rels))
check("l_inventaire_ecarte_LA_CLE_d_api",
      not any(r.startswith(".env") for r in rels), str(rels))
check("l_inventaire_ecarte_les_journaux_et_le_jetable",
      not any(r.startswith("logs/") for r in rels)
      and "assets/outputs/_cache/proxy.json" not in rels
      and "assets/outputs/fxpreview/fx.png" not in rels
      and "deepotus.db-wal" not in rels
      and "deepotus.db" not in rels, str(rels))
check("l_inventaire_est_trie_et_compte_ses_octets",
      rels == sorted(rels) and poids == sum(t for _, t in fichiers)
      and poids > 0, f"{poids}")

# ── l'export écrit un paquet complet ──
res = G("exporter", lambda: TR.exporter(DEST, TR.Etat(), quand=0))
paquet = Path(res["dossier"]) if isinstance(res, dict) else None
check("l_export_rend_un_paquet_date_et_nomme",
      paquet is not None and paquet.exists()
      and paquet.name.startswith("DeepotusVideoGen-Transfert-"),
      str(res)[:120])
if paquet:
    check("le_paquet_porte_son_manifeste_et_la_base",
          (paquet / TR.MANIFESTE).exists()
          and (paquet / TR.DOSSIER_BASE / TR.NOM_BASE).exists())
    man = json.loads((paquet / TR.MANIFESTE).read_text(encoding="utf-8"))
    check("le_manifeste_inscrit_la_racine_d_ORIGINE",
          man.get("racine_origine") == str(A), str(man.get("racine_origine")))
    # LE POINT DE L'INSTANTANE : ces lignes ne vivent que dans le journal
    # WAL de A (sa connexion est encore ouverte). Une copie d'octets du
    # seul `.db` les manquerait — la base du paquet serait VIDE.
    # `.get` et non `[...]` : sous une base de paquet vide (copie d'octets
    # au lieu d'instantane) l'indexation TUAIT le banc au lieu de le faire
    # rougir — la ligne doit porter le defaut, pas l'emporter.
    _lg = man.get("lignes") or {}
    check("le_manifeste_compte_les_lignes_par_table",
          _lg.get("jobs") == 1 and _lg.get("scheduled_posts") == 1,
          str(_lg))
    def _compter_jobs():
        c = sqlite3.connect(
            "file:" + (paquet / TR.DOSSIER_BASE / TR.NOM_BASE).as_posix()
            + "?mode=ro", uri=True)
        try:
            return c.execute("select count(*) from jobs").fetchone()[0]
        finally:
            c.close()

    # une base de paquet SANS TABLE leve « no such table » : la garde en
    # fait un temoin distinguable, et la ligne rougit avec sa cause
    _n = G("compter les jobs de la base du paquet", _compter_jobs)
    check("LA_BASE_DU_PAQUET_PORTE_LES_LIGNES_DU_JOURNAL_WAL",
          _n == 1, f"{_n} job(s) — une copie d'octets en aurait rendu 0")
    # LE POINT DE LA DEMANDE : aucune clé dans le paquet, nulle part
    dedans = [p for p in paquet.rglob("*") if p.is_file()]
    fuite = [p for p in dedans
             if "SECRET" in G("lire " + p.name,
                              lambda p=p: p.read_text(encoding="utf-8",
                                                      errors="ignore"))]
    check("AUCUNE_cle_dans_le_paquet", not fuite, str(fuite))
    check("le_paquet_porte_les_fichiers_de_la_bibliotheque",
          (paquet / TR.DOSSIER_DONNEES / "assets/images/logo.png").exists()
          and (paquet / TR.DOSSIER_DONNEES
               / "assets/outputs/final/j1.mp4").exists())

# ── refus parlants de l'export ──
mauvais = refus("export vers un dossier absent",
                lambda: TR.exporter(Path(_tmp, "nulle_part"), TR.Etat()))
check("export_vers_une_destination_absente_refuse_en_disant_pourquoi",
      isinstance(mauvais, str) and "introuvable" in mauvais.lower(),
      str(mauvais)[:120])
deux = refus("deux exports à la même minute",
             lambda: TR.exporter(DEST, TR.Etat(), quand=0))
check("un_paquet_du_meme_nom_n_est_jamais_ecrase",
      isinstance(deux, str) and "existe" in deux.lower(), str(deux)[:120])

# ── l'import sur le poste B, dont le nom d'utilisateur DIFFÈRE ──
PREFIXE_B = str(B)
os.environ["DEEPOTUS_DATA_DIR"] = PREFIXE_B
# B a SON travail, sous d'AUTRES identifiants : sans cela `insert or ignore`
# ecarterait les lignes de A et le re-ancrage ne serait jamais exerce.
semer_base(B, PREFIXE_B, jid="jB", eid="eB", pid="pB", asset="logoB.png")
ecrire(B / ".env", "ANTHROPIC_API_KEY=sk-ant-CLE-DU-POSTE-B\n")

# la racine du service suit la variable d'environnement : on la repointe
TR.racine = lambda: B                                    # noqa: E731
etat = TR.Etat()
imp = G("importer", lambda: TR.importer(paquet, etat)) if paquet else "pas de paquet"
check("l_import_rend_son_compte_rendu",
      isinstance(imp, dict) and imp["fichiers_ajoutes"] > 0, str(imp)[:160])
if isinstance(imp, dict):
    check("les_fichiers_de_A_sont_arrives_sur_B",
          (B / "assets/images/logo.png").exists()
          and (B / "assets/outputs/final/j1.mp4").read_text(
              encoding="utf-8") == "MP4-final")
    check("la_cle_du_poste_B_n_a_pas_ete_ecrasee",
          (B / ".env").read_text(encoding="utf-8").strip()
          == "ANTHROPIC_API_KEY=sk-ant-CLE-DU-POSTE-B")
    cb = sqlite3.connect(str(B / "deepotus.db"))
    lignes = dict(cb.execute(
        "select id, video_path from jobs").fetchall())
    check("le_travail_du_poste_B_est_intact",
          "jB" in lignes and lignes["jB"] is not None
          and lignes["jB"].lower().startswith(str(B).lower()), str(lignes))
    check("le_job_de_A_est_arrive", "j1" in lignes, str(lignes))
    # LE PIÈGE : le chemin absolu doit pointer chez B, pas chez olivi
    # Chercher le mot du nom d'utilisateur ne prouverait RIEN : le
    # dossier temporaire du banc vit lui-même sous ce profil. La
    # vraie propriete est que le prefixe d'ORIGINE a disparu.
    check("LE_CHEMIN_ABSOLU_EST_REANCRE_SUR_LA_RACINE_DE_B",
          "j1" in lignes and lignes["j1"] is not None
          and lignes["j1"].lower().startswith(str(B).lower())
          and not lignes["j1"].lower().startswith(PREFIXE_A.lower()),
          str(lignes.get("j1")))
    check("et_le_fichier_ainsi_designe_existe_VRAIMENT",
          "j1" in lignes and lignes["j1"] is not None
          and Path(lignes["j1"]).exists(), str(lignes.get("j1")))
    autres = dict(cb.execute(
        "select id, model3d_file from bible_entities").fetchall())
    check("la_bible_arrive_et_son_chemin_est_reancre_aussi",
          "e1" in autres and "eB" in autres and autres["e1"] is not None
          and autres["e1"].lower().startswith(str(B).lower())
          and not autres["e1"].lower().startswith(PREFIXE_A.lower()),
          str(autres))
    plans = [r[0] for r in cb.execute("select id from scheduled_posts")]
    check("les_plans_de_communication_arrivent_ET_ceux_de_B_restent",
          sorted(plans) == ["p1", "pB"], str(plans))
    biblio = sorted(r[0] for r in
                    cb.execute("select filename from library_assets"))
    check("la_bibliotheque_arrive_a_l_identique_SANS_effacer_celle_de_B",
          biblio == ["logo.png", "logoB.png"], str(biblio))
    cb.close()

    # ── un SECOND import ne détruit rien et n'ajoute rien ──
    etat2 = TR.Etat()
    imp2 = G("second import", lambda: TR.importer(paquet, etat2))
    check("un_second_import_ne_recopie_rien",
          isinstance(imp2, dict) and imp2["fichiers_ajoutes"] == 0
          and imp2["fichiers_sautes"] == imp["fichiers_ajoutes"],
          str(imp2)[:160])
    check("et_n_ajoute_aucune_ligne_en_double",
          isinstance(imp2, dict) and not imp2["ajoutees"],
          str(imp2.get("ajoutees") if isinstance(imp2, dict) else imp2))

# ── ré-ancrage : la fonction pure, et ce qu'elle NE fait PAS ──
check("reancrer_remplace_le_prefixe_d_origine",
      TR.reancrer(PREFIXE_A + r"\assets\x.png", PREFIXE_A, r"D:\Data")
      == r"D:\Data\assets\x.png")
check("reancrer_laisse_un_chemin_RELATIF_tranquille",
      TR.reancrer("vignette.png", PREFIXE_A, r"D:\Data") == "vignette.png")
check("reancrer_ne_devine_pas_le_chemin_d_une_TROISIEME_machine",
      TR.reancrer(r"E:\ailleurs\x.png", PREFIXE_A, r"D:\Data")
      == r"E:\ailleurs\x.png")
check("reancrer_laisse_les_valeurs_nulles_et_vides",
      TR.reancrer(None, PREFIXE_A, "D:") is None
      and TR.reancrer("", PREFIXE_A, "D:") == "")
check("reancrer_ne_fait_rien_sans_origine_connue",
      TR.reancrer(PREFIXE_A + r"\a.png", "", r"D:\Data")
      == PREFIXE_A + r"\a.png")

# ── manifeste : les refus parlants ──
vide = Path(_tmp, "dossier_vide")
vide.mkdir(exist_ok=True)
m1 = refus("manifeste absent", lambda: TR.lire_manifeste(vide))
check("un_dossier_sans_manifeste_refuse_en_le_disant",
      isinstance(m1, str) and TR.MANIFESTE in m1, str(m1)[:120])
faux = Path(_tmp, "faux_paquet")
(faux / TR.DOSSIER_BASE).mkdir(parents=True, exist_ok=True)
(faux / TR.MANIFESTE).write_text('{"format": 99}', encoding="utf-8")
m2 = refus("format inconnu", lambda: TR.lire_manifeste(faux))
check("un_format_inconnu_refuse_en_le_disant",
      isinstance(m2, str) and "99" in m2, str(m2)[:120])
(faux / TR.MANIFESTE).write_text(
    json.dumps({"format": TR.FORMAT}), encoding="utf-8")
m3 = refus("base absente", lambda: TR.lire_manifeste(faux))
check("un_paquet_sans_base_refuse_en_le_disant",
      isinstance(m3, str) and "base" in m3.lower(), str(m3)[:120])

check("aucun_appel_n_a_plante", _plantages == 0, f"{_plantages} plantage(s)")
if _conn_a is not None:
    _conn_a.close()
shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
