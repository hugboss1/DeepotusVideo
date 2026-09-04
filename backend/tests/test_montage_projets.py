# -*- coding: utf-8 -*-
"""P5 — PROJETS NOMMES : plusieurs montages coexistent sur le disque, et le
COURANT (montage_saved.json) sait de qui il est le brouillon. Banc par la
ROUTE, avec fastapi.testclient (aucun port ouvert) : c'est le cablage complet
— routes, disque, GET /project — qui est mesure, jamais une fonction prise
isolement. En-tete recopie de test_montage_texte.py (env, check), moins node,
ffmpeg et PIL : rien ici ne se rend ni ne s'execute en JS, et faire dependre
le banc d'un binaire dont il n'a pas besoin le ferait SAUTER sur une machine
ou tout est pourtant mesurable.
Run : & $PY tests/test_montage_projets.py   (depuis backend/)

TOUTE reponse passe par `J()` et tout acces est un `.get`. Ce n'est pas de la
coquetterie : ecrit avec `r.json()` nu, ce banc est MORT au premier appel de
sa premiere section (le SPA rend l'index.html sur une route absente, donc
JSONDecodeError) au lieu de rougir — l'exacte faute qu'une revue de ce
chantier a deja relevee ailleurs. Un banc qui meurt ne dit pas QUELLES
assertions manquent.

PROTOCOLE DE TOUT CE QUI EST AFFIRME ICI. Un dossier de donnees NEUF par
execution (tempfile.mkdtemp) ; IMAGES_FOLDER=<TMP>/images, donc le courant
est <TMP>/montage_saved.json et les projets <TMP>/montage_projects/*.json.
Le banc regarde CE DOSSIER LUI-MEME (pathlib), il ne demande pas au code ou
il ecrit : une implementation qui rangerait les projets ailleurs doit rougir.
`wipe()` vide le dossier entre les sections, pour qu'aucune ne herite de la
precedente. La source des clips est un fichier ORDINAIRE de <TMP> (un octet) :
`_resolve_src` n'accepte un `file_path` que s'il EXISTE, et GET /project
ELAGUE les clips dont la source a disparu — sans ce fichier, la sauvegarde
serait jugee inexploitable et `saved` retomberait a false, ce qui ferait
rougir la moitie de ce banc pour une raison qui n'a rien a voir.

CE QUI EST FERME ICI
  [1] les sept routes : `GET /projects` (metadonnees, tri par `updated_at`),
      `POST /projects` (le courant devient un projet nomme), `GET/PATCH/
      DELETE /projects/{pid}`, `POST /projects/{pid}/duplicate` et
      `POST /projects/{pid}/open`.
  [2] le COURANT porte `project_id` : POST /save le retient, GET /project le
      resert, et l'autosave MIROITE le courant dans le fichier du projet —
      c'est ce qui fait qu'un projet nomme suit les editions sans un geste.
  [3] NON-REGRESSION, la garde de ce lot : un POST /save SANS `project_id`
      n'ecrit RIEN dans montage_projects/. Les bancs P0/P1 passent par cette
      route ; si elle se mettait a semer des fichiers, ils ne le verraient
      pas et le dossier de l'utilisateur se remplirait tout seul.
  [4] les entrees MOLLES, que le plan ne couvrait pas : identifiant inconnu
      (404 sur les cinq routes qui en prennent un), identifiant HOSTILE
      (`../x`, `..%2F..%2Fx`, antislash, `.`, `..`), nom vide / de 200
      caracteres / non-chaine / avec un separateur, `project_id` non-chaine,
      fichier de projet corrompu, dossier sans aucun projet.
  [5] l'ecriture est ATOMIQUE : apres toutes les routes qui ecrivent, il ne
      reste pas un seul `.tmp` dans le dossier.
  [6] les DEUX gestes destructifs, cote serveur :
      * `open` REMPLACE le courant — l'ancien contenu n'est pas sauvegarde
        ailleurs et rien ne le rend ;
      * `DELETE` retire le fichier du projet — irrecuperable — et, si c'est
        le projet OUVERT, il retire aussi `project_id` du courant, faute de
        quoi le prochain autosave le RESSUSCITERAIT. Deuxieme verrou pour la
        meme panne, mesure ici : l'autosave ne MIROITE que dans un fichier
        de projet qui EXISTE DEJA ; il n'en cree jamais.
  [7] la duplication est INDEPENDANTE : editer la copie ne touche pas
      l'original (ce serait le cas si les deux partageaient un fichier).

CE QUE CE BANC N'AFFIRME PAS, et qui est un RESTE ASSUME.
  * L'ECRAN. Le popover « Projets » (M14), sa liste, son champ de renommage
    en ligne et sa confirmation `data-arm` ne sont mesures QUE par les
    comptes de test_montage_bundle.py : leur comportement reel demande
    l'application demarree, ce que ce banc ne fait jamais.
  * La COURSE entre un autosave en vol et un `open`/`DELETE` venu d'une AUTRE
    fenetre. Dans la fenetre qui agit, le bundle annule la requete en vol
    avant d'ecrire (meme geste que `svmLibReset`, garde par
    test_montage_bundle.py) ; entre deux fenetres, rien ne l'empeche. Le
    verrou [6] la borne : au pire le courant repart d'une edition perimee,
    jamais un projet supprime ne revient.
  * Le VERROU de concurrence sur un meme fichier de projet. Deux ecritures
    simultanees se terminent l'une apres l'autre (remplacement atomique) :
    la derniere gagne en entier, aucune ne laisse un fichier a moitie ecrit.
    Le banc mesure l'atomicite par l'absence de `.tmp`, pas par un tir
    concurrent — un tel tir ne serait pas deterministe.
  * La TAILLE. `POST /save` refuse au-dela de 2 Mo ou 400 clips ; les routes
    de projet copient ce que le courant portait deja et n'ajoutent aucune
    borne propre. Un dossier de mille projets n'est pas mesure."""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp5_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from fastapi.testclient import TestClient                # noqa: E402
from app.main import app                                 # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

ROOT = pathlib.Path(TMP)
PDIR = ROOT / "montage_projects"          # mesure DIRECTE, pas via le code
SAVED = ROOT / "montage_saved.json"
V1 = str(ROOT / "v1.mp4")
pathlib.Path(V1).write_bytes(b"x")


def J(resp):
    """Corps JSON, ou {} — voir l'en-tete : ce banc doit ROUGIR, pas mourir."""
    try:
        v = resp.json()
    except Exception:
        return {}
    return v if isinstance(v, dict) else {"_liste": v}


def names():
    return sorted(p.name for p in PDIR.glob("*")) if PDIR.is_dir() else []


def wipe():
    if PDIR.is_dir():
        for p in PDIR.iterdir():
            try:
                p.unlink()
            except OSError:
                pass


def TL(name="abysse", n=1):
    return {"name": name, "ratio": "9:16", "duration": 4, "mix": {},
            "clips": [{"tr": "v1", "id": "v%d" % i, "start": 0, "end": 4,
                       "src": {"file_path": V1}} for i in range(n)]}


def cur():
    return J(c.get("/api/montage/project"))


def fiche(pid):
    return J(c.get("/api/montage/projects/%s" % pid))


def nclips(pid):
    return len(fiche(pid).get("clips") or [])


# `raise_server_exceptions=False` : sans lui, une exception NON RATTRAPEE dans
# une route remonte jusqu'ici et TUE le banc au lieu de le faire rougir — un
# banc mort ne dit pas quelles assertions manquent. MESURE : trois des quinze
# mutations jouees le 04/09/2026 (`project_id` accepte sans fichier existant,
# miroir sans `project_id`, projet corrompu non rattrape) mouraient ainsi,
# donc les lignes censees les attraper ne prouvaient rien. Avec ce drapeau,
# le 500 est une REPONSE, `J()` en fait {} et les assertions decident.
c = TestClient(app, raise_server_exceptions=False)
c.__enter__()

print("\n[0] dossier vide — rien a lister, et rien a nommer sans courant")
r = c.get("/api/montage/projects")
check("liste_vide_repond_200",
      r.status_code == 200 and J(r).get("ok") is True
      and J(r).get("projects") == [], f"{r.status_code} {r.text[:120]}")
r = c.post("/api/montage/projects", json={"name": "sans courant"})
check("creer_sans_courant_400", r.status_code == 400, f"{r.status_code} {r.text[:120]}")
check("creer_sans_courant_n_ecrit_rien", names() == [], str(names()))

print("\n[1] le scenario du plan, par la route")
wipe()
tl = TL()
check("save_courant", c.post("/api/montage/save", json=tl).status_code == 200)
r = c.post("/api/montage/projects", json={"name": "Abysse v1"})
pid = J(r).get("id")
check("creer_depuis_courant",
      r.status_code == 200 and bool(pid) and J(r).get("clips") == 1,
      f"{r.status_code} {r.text[:140]}")
check("creer_ecrit_un_fichier", names() == ["%s.json" % pid], str(names()))
lst = J(c.get("/api/montage/projects"))
check("liste", [p.get("id") for p in (lst.get("projects") or [])] == [pid],
      str(lst)[:200])
p0 = ((lst.get("projects") or []) + [{}])[0]
check("liste_ne_rend_que_des_metadonnees",
      p0.get("clips") == 1 and p0.get("name") == "Abysse v1"
      and p0.get("ratio") == "9:16" and p0.get("duration") == 4.0
      and isinstance(p0.get("updated_at"), str) and "src" not in json.dumps(p0),
      str(p0))
# `bool(pid) and …` : sans ce premier terme, l'assertion comparait None a None
# et passait AU VERT sur un backend qui n'a pas une seule de ces routes —
# constate au tir rouge du 04/09/2026.
check("courant_porte_project_id",
      bool(pid) and cur().get("project_id") == pid,
      str(cur().get("project_id")))
tl2 = dict(tl, project_id=pid, clips=TL(n=2)["clips"])
check("save_avec_project_id", c.post("/api/montage/save", json=tl2).status_code == 200)
d = fiche(pid)
check("autosave_miroir", len(d.get("clips") or []) == 2, str(d.get("clips"))[:120])
check("fiche_projet_rend_les_clips_en_liste",
      isinstance(d.get("clips"), list) and d.get("id") == pid
      and d.get("project_id") == pid, str(d)[:200])
# Le NOM appartient au PROJET, pas au payload d'autosave : `tl2` porte encore
# « abysse » (le nom de la timeline avant qu'on la nomme), et le projet doit
# rester « Abysse v1 ». Sans cette regle, renommer dans le popover puis
# laisser passer un autosave rendait au projet son ancien nom, sans un mot —
# c'est ce qui faisait sortir « abysse (copie) » a la duplication.
check("autosave_ne_renomme_pas_le_projet", d.get("name") == "Abysse v1",
      str(d.get("name")))
check("autosave_a_bien_envoye_un_autre_nom", tl2.get("name") == "abysse",
      str(tl2.get("name")))
r = c.post("/api/montage/projects/%s/duplicate" % pid)
did = J(r).get("id")
check("dupliquer",
      r.status_code == 200 and bool(did) and did != pid
      and fiche(did).get("name") == "Abysse v1 (copie)",
      f"{r.status_code} {r.text[:140]}")
check("dupliquer_copie_les_clips", nclips(did) == 2, str(nclips(did)))
r = c.patch("/api/montage/projects/%s" % did, json={"name": "Abysse v2"})
check("renommer", r.status_code == 200 and J(r).get("name") == "Abysse v2",
      f"{r.status_code} {r.text[:140]}")
check("renommer_persiste", fiche(did).get("name") == "Abysse v2",
      str(fiche(did).get("name")))
r = c.post("/api/montage/projects/%s/open" % did)
pr = cur()
check("ouvrir_change_le_courant",
      r.status_code == 200 and pr.get("project_id") == did,
      f"{r.status_code} {r.text[:140]}")
check("ouvrir_rend_le_nom_du_projet", pr.get("name") == "Abysse v2",
      str(pr.get("name")))
r = c.delete("/api/montage/projects/%s" % pid)
rest = J(c.get("/api/montage/projects")).get("projects") or []
check("supprimer",
      r.status_code == 200 and J(r).get("deleted") is True
      and len(rest) == 1 and rest[0].get("id") == did,
      f"{r.status_code} {r.text[:120]} {rest}")
check("supprimer_retire_le_fichier", names() == ["%s.json" % did], str(names()))
r = c.post("/api/montage/projects", json={"name": "../x"})
check("nom_hostile_reduit", J(r).get("name") == "x", r.text[:140])
check("nom_hostile_ne_sort_pas_du_dossier",
      not (ROOT / "x.json").exists() and len(names()) == 2, str(names()))

print("\n[2] identifiant INCONNU — 404 sur les cinq routes qui en prennent un")
wipe()
c.post("/api/montage/save", json=TL())
codes = {
    "get": c.get("/api/montage/projects/m_inconnu").status_code,
    "patch": c.patch("/api/montage/projects/m_inconnu", json={"name": "x"}).status_code,
    "duplicate": c.post("/api/montage/projects/m_inconnu/duplicate").status_code,
    "open": c.post("/api/montage/projects/m_inconnu/open").status_code,
    "delete": c.delete("/api/montage/projects/m_inconnu").status_code,
}
for _k in ("get", "patch", "duplicate", "open", "delete"):
    check("inconnu_404_" + _k, codes[_k] == 404, str(codes[_k]))
check("inconnu_n_a_rien_ecrit", names() == [], str(names()))
check("inconnu_n_a_pas_touche_au_courant", cur().get("project_id") is None,
      str(cur().get("project_id")))

print("\n[3] identifiant HOSTILE — jamais de fichier hors du dossier")
wipe()
temoin = ROOT / "temoin.json"
temoin.write_text(json.dumps({"id": "temoin", "name": "TEMOIN", "clips": []}),
                  encoding="utf-8")
hostiles = ["..%2F..%2Ftemoin", "..%5Ctemoin", "%2E%2E%5Ctemoin", "%2E%2E",
            "%2E", "..%2Ftemoin", "m_%2E%2E%2Ftemoin", "%2E%2E%2F%2E%2E%2Ft.db"]
# LE STATUT NE DECIDE RIEN, et c'est mesure : un GET qui ne matche AUCUNE
# route retombe sur le SPA (index.html, 200) tandis que le DELETE de la meme
# adresse rend 405 — l'app se comporte ainsi bien avant P5, pour toute route
# absente. Un banc qui exigeait « jamais 200 » rougissait donc sur les trois
# vecteurs porteurs de `%2F` (que Starlette refuse d'injecter dans un
# parametre de chemin : ils n'atteignent meme pas le gestionnaire) et
# n'aurait rien dit du seul qui l'atteint. C'est le CONTENU qui decide : le
# temoin ne doit jamais etre LU, ni declare supprime. Le vecteur qui atteint
# vraiment le gestionnaire est `..%5Ctemoin` (antislash, aucun `/` a decoder)
# — MUTATION VERIFIEE : en retirant `Path(...).name` de `_pid`, lui seul fait
# rougir cette ligne.
bad = []
for h in hostiles:
    g = c.get("/api/montage/projects/" + h)
    dl = c.delete("/api/montage/projects/" + h)
    if "TEMOIN" in g.text or J(g).get("name") == "TEMOIN" or J(dl).get("deleted"):
        bad.append((h, g.status_code, dl.status_code, g.text[:60]))
check("hostile_ne_lit_ni_ne_supprime_hors_du_dossier", bad == [], str(bad))
_t = {}
try:
    _t = json.loads(temoin.read_text(encoding="utf-8"))
except (OSError, ValueError):
    _t = {}
check("hostile_temoin_intact", _t.get("name") == "TEMOIN", str(_t)[:120])
check("hostile_n_a_rien_cree_dans_le_dossier", names() == [], str(names()))
# tolerant : sous la mutation « _pid ne sanitise plus », le DELETE hostile
# EMPORTE reellement le temoin, et un `unlink()` nu tuait le banc juste apres
# que la ligne ci-dessus l'ait pourtant vu.
try:
    temoin.unlink()
except OSError:
    pass

print("\n[4] un fichier de projet CORROMPU est ignore, il ne fait pas tomber la liste")
wipe()
c.post("/api/montage/save", json=TL("bon"))
good = J(c.post("/api/montage/projects", json={"name": "bon"})).get("id")
PDIR.mkdir(parents=True, exist_ok=True)
(PDIR / "casse.json").write_text("{ceci n est pas du json", encoding="utf-8")
(PDIR / "liste.json").write_text("[1,2,3]", encoding="utf-8")
r = c.get("/api/montage/projects")
ids = [p.get("id") for p in (J(r).get("projects") or [])]
check("liste_survit_au_corrompu",
      r.status_code == 200 and bool(good) and good in ids,
      f"{r.status_code} {r.text[:140]}")
check("liste_ne_montre_pas_le_corrompu",
      "casse" not in json.dumps(ids) and len(ids) == 1, str(ids))
# `== 404`, et non « != 200 » : la version lache SURVIVAIT a deux mutations
# jouees le 04/09/2026 — `_load_project` ne rattrapant plus ValueError (donc
# 500 sur un JSON casse) et `_load_project` rendant un non-objet tel quel.
# Un 500 n'est pas un contrat, c'est une panne : un projet illisible est un
# projet INTROUVABLE, et c'est ce que la ligne exige maintenant.
r = c.get("/api/montage/projects/casse")
check("fiche_corrompue_est_un_404_pas_un_500", r.status_code == 404,
      str(r.status_code))
r = c.get("/api/montage/projects/liste")
check("fiche_non_objet_est_un_404", r.status_code == 404, str(r.status_code))
r = c.post("/api/montage/projects/casse/duplicate")
check("dupliquer_un_projet_corrompu_404", r.status_code == 404,
      str(r.status_code))
check("dupliquer_un_projet_corrompu_n_ecrit_rien",
      names() == sorted(["%s.json" % good, "casse.json", "liste.json"]),
      str(names()))
(PDIR / "casse.json").unlink()
(PDIR / "liste.json").unlink()

print("\n[5] les NOMS : vide, 200 caracteres, non-chaine, separateurs")
wipe()
c.post("/api/montage/save", json=TL("courant-a-moi"))
cas = [
    ("vide", {"name": ""}, "courant-a-moi"),
    ("espaces", {"name": "   "}, "courant-a-moi"),
    ("absent", {}, "courant-a-moi"),
    ("non_chaine", {"name": 42}, "courant-a-moi"),
    ("point_point", {"name": ".."}, "courant-a-moi"),
    ("separateur", {"name": "dossier/nom"}, "nom"),
    ("antislash", {"name": "dossier\\nom2"}, "nom2"),
]
for lbl, body, want in cas:
    r = c.post("/api/montage/projects", json=body)
    check("nom_" + lbl, r.status_code == 200 and J(r).get("name") == want,
          f"{r.status_code} {r.text[:120]}")
r = c.post("/api/montage/projects", json={"name": "z" * 200})
long_id = J(r).get("id")
check("nom_200_caracteres_borne_a_80", len(J(r).get("name") or "") == 80,
      str(len(J(r).get("name") or "")))
r = c.patch("/api/montage/projects/%s" % long_id, json={"name": ""})
check("renommer_avec_un_nom_vide_garde_l_ancien",
      r.status_code == 200 and len(J(r).get("name") or "") == 80,
      f"{r.status_code} {r.text[:120]}")
r = c.patch("/api/montage/projects/%s" % long_id, json={"name": "../evade"})
check("renommer_hostile_reduit", J(r).get("name") == "evade", r.text[:120])
check("renommer_ne_deplace_pas_le_fichier",
      ("%s.json" % long_id) in names() and "evade.json" not in names(),
      str(names()))

print("\n[6] `project_id` MOU dans POST /save — jamais de fichier fantaisiste")
wipe()
c.post("/api/montage/save", json=TL())
vrai = J(c.post("/api/montage/projects", json={"name": "vrai"})).get("id")
avant = names()
for lbl, val in (("dict", {"a": 1}), ("liste", [1]), ("nombre", 7),
                 ("bool", True), ("vide", ""), ("hostile", "../evade"),
                 ("inconnu", "m_jamaisvu")):
    r = c.post("/api/montage/save", json=dict(TL(), project_id=val))
    check("save_project_id_" + lbl + "_accepte", r.status_code == 200,
          f"{r.status_code} {r.text[:120]}")
check("save_project_id_mou_n_ecrit_aucun_fichier",
      names() == avant == ["%s.json" % vrai], f"{names()} / {avant}")
check("save_project_id_mou_n_est_pas_resservi", cur().get("project_id") is None,
      str(cur().get("project_id")))
check("save_project_id_hostile_n_evade_rien", not (ROOT / "evade.json").exists())
r = c.post("/api/montage/save", json=dict(TL(n=3), project_id=vrai))
check("save_project_id_valide_miroite",
      r.status_code == 200 and nclips(vrai) == 3,
      f"{r.status_code} {nclips(vrai)}")

print("\n[7] la liste est triee par `updated_at`, la plus recente en tete")
wipe()
PDIR.mkdir(parents=True, exist_ok=True)
for _pid, _at in (("m_vieux", "2020-01-01T00:00:00Z"),
                  ("m_recent", "2026-01-01T00:00:00Z"),
                  ("m_sansdate", None)):
    rec = {"id": _pid, "name": _pid, "clips": [], "ratio": "9:16", "duration": 1}
    if _at:
        rec["saved_at"] = _at
    (PDIR / (_pid + ".json")).write_text(json.dumps(rec), encoding="utf-8")
got = [p.get("id") for p in (J(c.get("/api/montage/projects")).get("projects") or [])]
check("tri_par_updated_at", got == ["m_recent", "m_vieux", "m_sansdate"], str(got))

print("\n[8] ECRITURE ATOMIQUE — pas un seul .tmp apres toutes les routes")
wipe()
c.post("/api/montage/save", json=TL())
a = J(c.post("/api/montage/projects", json={"name": "atom"})).get("id")
c.post("/api/montage/save", json=dict(TL(n=2), project_id=a))
b = J(c.post("/api/montage/projects/%s/duplicate" % a)).get("id")
c.patch("/api/montage/projects/%s" % b, json={"name": "atom2"})
c.post("/api/montage/projects/%s/open" % b)
tmps = [p.name for p in PDIR.glob("*") if not p.name.endswith(".json")] \
    if PDIR.is_dir() else []
check("aucun_tmp_residuel", tmps == [], str(tmps))
check("un_fichier_json_par_projet",
      names() == sorted(["%s.json" % a, "%s.json" % b]), str(names()))

print("\n[9] NON-REGRESSION — un POST /save SANS project_id n'ecrit rien ici")
wipe()
for i in range(3):
    r = c.post("/api/montage/save", json=TL("nu", n=i + 1))
    check("save_nu_%d_ok" % i, r.status_code == 200, r.text[:120])
check("save_nu_n_ecrit_rien_dans_montage_projects", names() == [], str(names()))
_sv = {}
try:
    _sv = json.loads(SAVED.read_text(encoding="utf-8"))
except (OSError, ValueError):
    _sv = {"project_id": "ILLISIBLE"}
check("save_nu_ne_pose_pas_project_id", "project_id" not in _sv,
      str(_sv.get("project_id")))
check("save_nu_reste_lisible_par_GET_project", cur().get("saved") is True,
      str(cur().get("saved")))

print("\n[10] SUPPRIMER le projet OUVERT : le courant se delie, rien ne ressuscite")
wipe()
c.post("/api/montage/save", json=TL("ouvert"))
opid = J(c.post("/api/montage/projects", json={"name": "ouvert"})).get("id")
check("supprime_avant_le_courant_est_lie", bool(opid)
      and cur().get("project_id") == opid, str(cur().get("project_id")))
c.delete("/api/montage/projects/%s" % opid)
check("supprime_le_courant_se_delie", cur().get("project_id") is None,
      str(cur().get("project_id")))
r = c.post("/api/montage/save", json=dict(TL("ouvert"), project_id=opid))
check("supprime_l_autosave_ne_ressuscite_pas",
      r.status_code == 200 and names() == [], str(names()))
check("supprime_la_timeline_courante_survit",
      cur().get("saved") is True and len(cur().get("clips") or []) == 1,
      str(cur().get("saved")))

print("\n[11] la DUPLICATION est independante — editer la copie ne touche pas l'original")
wipe()
c.post("/api/montage/save", json=TL("orig"))
o = J(c.post("/api/montage/projects", json={"name": "orig"})).get("id")
k = J(c.post("/api/montage/projects/%s/duplicate" % o)).get("id")
c.post("/api/montage/save", json=dict(TL("copie", n=5), project_id=k))
check("copie_editee_a_5_clips", nclips(k) == 5, str(nclips(k)))
check("original_intact_a_1_clip", nclips(o) == 1, str(nclips(o)))
check("copie_et_original_ont_des_fichiers_distincts",
      names() == sorted(["%s.json" % o, "%s.json" % k]), str(names()))

print("\n[12] OUVRIR remplace le courant EN ENTIER (geste destructif, cote serveur)")
wipe()
c.post("/api/montage/save", json=TL("premier", n=1))
p1 = J(c.post("/api/montage/projects", json={"name": "premier"})).get("id")
c.post("/api/montage/save", json=TL("second", n=4))
p2 = J(c.post("/api/montage/projects", json={"name": "second"})).get("id")
c.post("/api/montage/projects/%s/open" % p1)
cr = cur()
check("ouvrir_rend_les_clips_du_projet", len(cr.get("clips") or []) == 1,
      str(len(cr.get("clips") or [])))
check("ouvrir_relie_au_projet_ouvert",
      bool(p1) and cr.get("project_id") == p1, str(cr)[:160])
check("ouvrir_n_a_pas_modifie_le_projet_quitte", nclips(p2) == 4, str(nclips(p2)))
check("ouvrir_laisse_les_deux_fichiers", len(names()) == 2, str(names()))

print("\n[13] un projet INOUVRABLE (plus une source vivante) est REFUSE, 409")
# LE SEUL GESTE DU LOT QUI POUVAIT DETRUIRE UN MONTAGE SANS QU'ON DEMANDE
# RIEN DE DESTRUCTIF. Sans ce refus : `open` remplacait le courant par un
# projet dont GET /project elague ensuite TOUS les clips (source disparue),
# retombait sur la Bibliotheque, et la timeline affichee — si elle n'avait pas
# de nom — n'existait plus nulle part. La regle est celle de GET /project au
# mot pres : un clip V1 SANS `src` compte comme vivant, un clip dont la source
# a disparu ne compte pas.
wipe()
V2 = str(ROOT / "v2.mp4")
pathlib.Path(V2).write_bytes(b"y")
frag = dict(TL("fragile"), clips=[{"tr": "v1", "id": "f0", "start": 0, "end": 4,
                                   "src": {"file_path": V2}}])
c.post("/api/montage/save", json=frag)
fid = J(c.post("/api/montage/projects", json={"name": "fragile"})).get("id")
c.post("/api/montage/save", json=TL("sain"))
sid = J(c.post("/api/montage/projects", json={"name": "sain"})).get("id")
check("inouvrable_avant_le_projet_s_ouvre",
      c.post("/api/montage/projects/%s/open" % fid).status_code == 200
      and len(cur().get("clips") or []) == 1, str(cur().get("clips"))[:120])
c.post("/api/montage/projects/%s/open" % sid)          # on revient au sain
pathlib.Path(V2).unlink()
r = c.post("/api/montage/projects/%s/open" % fid)
check("inouvrable_409", r.status_code == 409, f"{r.status_code} {r.text[:140]}")
cr = cur()
check("inouvrable_n_a_pas_touche_le_courant",
      bool(sid) and cr.get("project_id") == sid
      and len(cr.get("clips") or []) == 1 and cr.get("name") == "sain",
      str(cr)[:200])
check("inouvrable_reste_listable_et_supprimable",
      fid in [p.get("id") for p in (J(c.get("/api/montage/projects"))
                                    .get("projects") or [])]
      and J(c.delete("/api/montage/projects/%s" % fid)).get("deleted") is True)
# un clip V1 SANS `src` (un plan de demo) compte comme vivant : c'est ce que
# GET /project fait, et deux regles differentes pour la meme question se
# contrediraient au premier projet mixte.
wipe()
c.post("/api/montage/save", json=dict(TL("nu"), clips=[
    {"tr": "v1", "id": "d0", "start": 0, "end": 4}]))
nid = J(c.post("/api/montage/projects", json={"name": "sans source"})).get("id")
check("projet_sans_src_du_tout_reste_ouvrable",
      c.post("/api/montage/projects/%s/open" % nid).status_code == 200,
      str(c.post("/api/montage/projects/%s/open" % nid).status_code))

c.__exit__(None, None, None)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
