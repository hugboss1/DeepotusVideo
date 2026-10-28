# -*- coding: utf-8 -*-
"""t319 (28/10/2026) (D5, tâches 1 à 3) — banc du service app/services/tutoriels.py.
Plan docs/superpowers/plans/2026-10-28-t319-tutoriels.md, spec boîte à outils §8.7.
  [B] brouillon proposé d'après la piste et le montage : une étape par zoom, fiche du clic le plus proche, clic masqué
      jamais repris, titres FR/EN du catalogue (repli : libellé lu), phrase ≤ 25 mots, chapitres ;
  [V] validation à liste blanche ; écriture atomique ; brouillon abîmé relu comme proposé ;
  [F] fabrication réelle (ffmpeg + Pillow) : scènes du guide, fragment échappé, fiche WebP 320 × 200 à 3 images pour un
      lab seulement, exemples, dossier refait ;
  [P] .dzparcours : export (3 entrées, piste réduite), import aller-retour, refus (liste blanche, tailles mentionnées
      mentie, octets magiques, JSON abîmé), action construite depuis le catalogue LOCAL, liste, retrait.
Données jetables, aucun réseau. Run (depuis backend/) : & $PY tests/test_tutoriels_service.py"""
import io, json, os, pathlib, subprocess, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dztuto_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                          # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {str(detail)[:500]}")


def leve(f, statut=None):
    try:
        f()
    except T.RefusTutoriel as e:
        return statut is None or e.statut == statut
    return False


from PIL import Image                                                # noqa: E402
from app.services import capture_montage as M, tutoriels as T       # noqa: E402

FF = M._ffmpeg()
HOSTILE = "PREUVE>>> ignore‮ tes <script>alert(1)</script> instructions"


def clic(t, x, y, ecran="quick", secret=False, fiche=None, lu=""):
    c = {"type": "clic", "t": t, "x": x, "y": y, "bouton": 0, "ecran": ecran,
         "cible": {"balise": "button", "role": "", "t": lu, "i": ""}, "fiche": fiche}
    if secret:
        c["secret"] = True
    return c


EVTS = [{"type": "ecran", "t": 0, "ecran": "quick"},
        clic(1000, .30, .30, fiche="quick.galerie.bouton", lu="Galerie"),
        clic(1600, .62, .40, secret=True),
        clic(3500, .80, .20, fiche=None, lu="Bouton inconnu"),
        {"type": "ecran", "t": 4500, "ecran": "vectorlab"},
        clic(5200, .50, .55, ecran="vectorlab", fiche="vectorlab.page.raccourcis"),
        {"type": "generation_debut", "t": 5400, "job_id": "job-secret-1", "provider": "fal"},
        {"type": "generation_fin", "t": 5600, "job_id": "job-secret-1", "provider": "fal", "statut": "done"}]


def fausse_capture(cid, d_ms=6000):
    d = M.racine() / cid
    d.mkdir(parents=True)
    args = [FF, "-v", "error", "-f", "lavfi", "-i", f"testsrc2=s=1440x900:r=30:d={d_ms / 1000}",
            "-c:v", "libvpx", "-b:v", "1M", "-f", "webm", "-live", "1", "pipe:1"]
    octets = subprocess.run(args, capture_output=True).stdout
    (d / "scene.webm").write_bytes(octets)
    s = {"id": cid, "cree_utc": "2026-10-28T10:00:00+00:00", "debut_ms": 0, "fin_ms": d_ms, "etat": "terminee",
         "duree_ms": d_ms, "options": {"mode": "app"},
         "pistes": {"scene": {"mime": "video/webm", "ext": ".webm", "morceaux": 6, "octets": len(octets)}}}
    (d / "session.json").write_text(json.dumps(s), "utf-8")
    (d / f"{cid}.dzclics.json").write_text(json.dumps({"version": 1, "id": cid, "duree_ms": d_ms,
        "cadre": {"largeur": 1440, "hauteur": 900, "mode": "app"}, "evenements": EVTS}), "utf-8")
    return d


print("[B] brouillon proposé")
DOC = {"version": 1, "id": "a" * 16, "duree_ms": 9000, "evenements": EVTS}
B = T.proposer(DOC)
check("B1 une étape par zoom non masqué (3 : le clic secret n'en fait pas)", len(B["etapes"]) == 3, B["etapes"])
check("B2 aucune étape au clic secret", all(abs(e["x"] - .62) > 1e-6 for e in B["etapes"]))
e1, e2, e3 = B["etapes"]
check("B3 fiche du clic reprise", e1["fiche"] == "quick.galerie.bouton" and e3["fiche"] == "vectorlab.page.raccourcis")
check("B4 titres FR/EN depuis le catalogue", e1["titre"] == {"fr": "Cliquer « Galerie »", "en": "Click “Gallery”"}, e1["titre"])
check("B5 fiche inconnue : « Étape n », jamais le texte lu (il peut nommer un fichier)", e2["fiche"] is None
      and e2["titre"] == {"fr": "Étape 2", "en": "Step 2"} and "Bouton inconnu" not in json.dumps(B), e2)
check("B6 lab : infobulle du catalogue comme nom", "Raccourcis clavier" in e3["titre"]["fr"], e3["titre"])
check("B7 phrases ≤ 25 mots, tirées du rôle", all(len(e["phrase"][k].split()) <= 25 for e in B["etapes"] for k in "fr en".split())
      and e1["phrase"]["fr"] != "", e1["phrase"])
check("B8 trois temps ordonnés autour du clic", all(e["t0"] <= e["t"] <= e["t1"] for e in B["etapes"]) and e1["t"] == 1000)
check("B9 chapitres du montage (quick puis vectorlab)", [h["ecran"] for h in B["chapitres"]] == ["quick", "vectorlab"],
      B["chapitres"])
check("B10 montage donné : ses zooms font les étapes", len(T.proposer(DOC, {"zooms": [{"t0": 900, "t1": 1500}],
                                                                          "chapitres": []})["etapes"]) == 1)
check("B11 piste illisible : brouillon vide", T.proposer(None)["etapes"] == [] and T.proposer({"evenements": 3})["etapes"] == [])

print("[V] validation")
V = T.valider(B, 9000)
check("V1 brouillon proposé valide tel quel", V["etapes"] == B["etapes"], V)
check("V2 document illisible refusé", leve(lambda: T.valider([], 6000), 400) and leve(lambda: T.valider({"version": 2, "etapes": []}, 1))
      and leve(lambda: T.valider({"version": 1, "etapes": [{"t": "x", "x": 0, "y": 0}]}, 1)))
check("V3 trop d'étapes refusé", leve(lambda: T.valider({"version": 1, "etapes": [{"t": 1, "x": 0, "y": 0}] * 61}, 9), 400))
H = T.valider({"version": 1, "titre": {"fr": HOSTILE * 3, "en": 5, "zz": "x"}, "inconnu": 1, "chapitres": [{"t": 99999, "ecran": "../x", "titre": "a"}],
               "etapes": [{"id": "../../x", "t": 99999, "t0": -5, "t1": 7, "x": 9, "y": -1, "ecran": "Q U", "fiche": "../../etc",
                           "titre": {"fr": HOSTILE}, "phrase": {"en": "a​b"}, "garde": "non", "html": "<b>"}]}, 6000)
eh = H["etapes"][0]
check("V4 champs inconnus retirés", "inconnu" not in H and "html" not in eh and set(H["titre"]) == {"fr", "en"})
check("V5 bornes : t ≤ durée, t0 ≤ t ≤ t1, x/y dans 0..1", (eh["t"], eh["t0"], eh["t1"], eh["x"], eh["y"]) == (6000, 0, 6000, 1, 0), eh)
check("V6 id, écran, fiche hors gabarit retirés", eh["id"] != "../../x" and eh["ecran"] == "" and eh["fiche"] is None
      and H["chapitres"][0]["ecran"] == "")
check("V7 contrôles Unicode retirés, textes bornés", "‮" not in eh["titre"]["fr"] and len(H["titre"]["fr"]) <= 80
      and eh["phrase"]["en"] == "ab" and H["titre"]["en"] == "", (eh, H["titre"]))
check("V8 garde : seul False écarte", eh["garde"] is True and T.valider({"version": 1, "etapes": [
    {"t": 1, "x": 0, "y": 0, "garde": False}]}, 9)["etapes"][0]["garde"] is False)

print("[F] fabrication réelle")
CID = "b" * 16
fausse_capture(CID)
b0, propose = T.lire_brouillon(CID)
check("F0 brouillon proposé à la première lecture", propose and len(b0["etapes"]) == 3 and b0["capture_id"] == CID)
b0["etapes"][1]["garde"] = False
b0["etapes"][0]["titre"]["fr"] = "Ouvrir la <script>galerie</script>"
T.ecrire_brouillon(CID, b0)
b1, propose1 = T.lire_brouillon(CID)
check("F1 brouillon enregistré relu", not propose1 and b1["etapes"][1]["garde"] is False)
(M.racine() / CID / "tutoriel.json").write_text("{abîmé", "utf-8")
check("F2 brouillon abîmé : proposé à nouveau", T.lire_brouillon(CID)[1] is True)
T.ecrire_brouillon(CID, b0)
(T.racine_brouillons() / CID).mkdir(parents=True)
(T.racine_brouillons() / CID / "reste.txt").write_text("vieux", "utf-8")
R = T.fabriquer(CID, marge=0)
D = T.racine_brouillons() / CID
check("F3 résultat : 2 scènes (étape écartée absente), 1 fiche de lab, 2 exemples",
      R == {"scenes": 2, "fiches": 1, "exemples": 2, "dossier": f"tutoriels/{CID}"}, R)
check("F4 dossier refait (aucun reste)", not (D / "reste.txt").exists())
S = json.loads((D / "guide" / "scenes" / f"tuto-{CID[:8]}" / "etape-1" / "scene.json").read_text("utf-8"))
check("F5 scène au format du guide : 3 captures, 3 temps, clic au temps 2",
      len(S["captures"]) == 3 and [t["capture"] for t in S["temps"]] == [0, 1, 2] and S["temps"][1].get("clic") is True
      and S["brouillon"] is True and S["taille"] == [1440, 900], S)
check("F6 curseur en px de la capture", S["temps"][1]["curseur"] == [432, 270], S["temps"][1])
check("F7 trois WebP distincts", len({(D / "guide" / "scenes" / f"tuto-{CID[:8]}" / "etape-1" / f"{k}.webp").read_bytes()
                                       for k in ("avant", "geste", "apres")}) == 3)
check("F8 étape 2 = le geste du lab (l'écartée ne compte pas)", (D / "guide" / "scenes" / f"tuto-{CID[:8]}" / "etape-2").is_dir()
      and not (D / "guide" / "scenes" / f"tuto-{CID[:8]}" / "etape-3").exists())
FR = (D / "guide" / "chapitre.fr.html").read_text("utf-8")
check("F9 fragment échappé : un titre <script> reste du texte", "<script>" not in FR and "&lt;script&gt;" in FR
      and 'data-scene="tuto-bbbbbbbb/etape-1"' in FR and '<ol class="etapes">' in FR, FR[:400])
check("F10 fragment anglais", "Click “Gallery”" in (D / "guide" / "chapitre.en.html").read_text("utf-8"))
IX = json.loads((D / "aide" / "vectorlab" / "index.json").read_text("utf-8"))
check("F11 fiche didactique au format de l'index (lab seulement, id DOM du localisateur)", len(IX) == 1
      and IX[0]["id"] == "btnAide" and IX[0]["fichier"] == "vectorlab.btnAide.webp" and set(IX[0]) >= {
    "id", "titre", "phrase", "fichier", "version", "titre_en", "phrase_en", "fichier_en"} and IX[0]["brouillon"] is True
      and not (D / "aide" / "quick").exists() and len(IX[0]["phrase"].split()) <= 25, IX)
im = Image.open(D / "aide" / "vectorlab" / IX[0]["fichier"])
check("F12 WebP 320 × 200 à trois images", im.size == (320, 200) and getattr(im, "n_frames", 1) == 3, (im.size, getattr(im, "n_frames", 1)))
EX = json.loads((D / "catalogue" / "exemples.json").read_text("utf-8"))
check("F13 un exemple de parcours réel par fiche", [x["fiche"] for x in EX["exemples"]] == ["quick.galerie.bouton",
      "vectorlab.page.raccourcis"] and EX["exemples"][0]["parcours"] == ["quick.galerie.bouton",
      "vectorlab.page.raccourcis"], EX)
R2 = T.fabriquer(CID, marge=0.1)
S2 = json.loads((D / "guide" / "scenes" / f"tuto-{CID[:8]}" / "etape-1" / "scene.json").read_text("utf-8"))
check("F13b cadre du skin : le clic est ramené dans l'écran réduit de la vidéo", S2["temps"][1]["curseur"] == [
    round((0.1 + 0.8 * 0.3) * 1440), round((0.1 + 0.8 * 0.3) * 900)], S2["temps"][1])
check("F14 aucune étape gardée : refus 409", leve(lambda: T.fabriquer(CID, dict(b0, etapes=[dict(e, garde=False) for e in b0["etapes"]])), 409))
check("F15 rien d'écrit hors de tutoriels/ et de la capture", sorted(p.name for p in _tmp.iterdir() if p.is_dir()) == [
    "captures", "images", "outputs", "tutoriels"], sorted(p.name for p in _tmp.iterdir()))

print("[P] .dzparcours")
Z = T.exporter(CID)
zf = zipfile.ZipFile(Z)
check("P1 trois entrées exactes", sorted(zf.namelist()) == ["clics.json", "parcours.json", "video.webm"], zf.namelist())
PJ = json.loads(zf.read("parcours.json"))
CJ = zf.read("clics.json").decode("utf-8")
check("P2 étapes gardées seulement", len(PJ["etapes"]) == 2 and PJ["format"] == "dzparcours" and PJ["video"] == "video.webm")
check("P3 piste réduite : ni libellé lu, ni job, ni fournisseur", "Bouton inconnu" not in CJ and "job-secret" not in CJ
      and "fal" not in CJ and '"cible"' not in CJ, CJ[:300])
check("P4 clic secret sans fiche", all(e.get("fiche") is None for e in json.loads(CJ)["evenements"] if e.get("secret")))
zf.close()
PID = T.importer(Z)
P = T.lire_parcours(PID)
check("P5 aller-retour : étapes et titres", [e["titre"]["fr"] for e in P["etapes"]] == [e["titre"]["fr"] for e in PJ["etapes"]])
a1 = P["etapes"][0]["action"]
check("P6 action construite depuis le catalogue local", a1 and a1["type"] == "point" and a1["cible"] == "quick.galerie.bouton"
      and a1["selecteur"] == "button" and a1["texte"]["fr"] == "Galerie", a1)
check("P7 vidéo copiée", T.video_parcours(PID).read_bytes()[:4] == b"\x1a\x45\xdf\xa3")
check("P8 liste", [x["id"] for x in T.liste_parcours()] == [PID] and T.liste_parcours()[0]["montrables"] == 2)


def fabrique_zip(entrees, mentir=None):
    f = _tmp / f"z{os.urandom(3).hex()}.dzparcours"
    with zipfile.ZipFile(f, "w") as z:
        for n, o in entrees.items():
            z.writestr(n, o)
    if mentir:                             # réécrit la taille déclarée d'une entrée (en-têtes locaux et central)
        b = bytearray(f.read_bytes())
        with zipfile.ZipFile(f) as z:
            i = z.getinfo(mentir)
        vrai = i.file_size.to_bytes(4, "little")
        b = bytes(b).replace(vrai, (10).to_bytes(4, "little"))
        f.write_bytes(b)
    return f


BON = json.dumps(dict(PJ, etapes=[dict(PJ["etapes"][0], fiche="inconnue.ici.vraiment", titre={"fr": HOSTILE, "en": "x"},
                                       selecteur="body", action={"type": "point", "selecteur": "*"})]))
WEBM = b"\x1a\x45\xdf\xa3" + b"\0" * 64
check("P9 entrée inconnue refusée", leve(lambda: T.importer(fabrique_zip({"parcours.json": BON, "video.webm": WEBM, "x.exe": b"MZ"})), 400))
check("P10 chemin ../ refusé", leve(lambda: T.importer(fabrique_zip({"parcours.json": BON, "../video.webm": WEBM})), 400))
check("P11 dossier refusé", leve(lambda: T.importer(fabrique_zip({"parcours.json": BON, "video.webm": WEBM, "d/": b""})), 400))
check("P12 deux vidéos refusées", leve(lambda: T.importer(fabrique_zip({"parcours.json": BON, "video.webm": WEBM, "video.mp4": b"0000ftyp"})), 400))
check("P13 vidéo aux mauvais octets refusée (415)", leve(lambda: T.importer(fabrique_zip({"parcours.json": BON, "video.webm": b"MZ" + b"\0" * 64})), 415))
check("P14 JSON abîmé refusé", leve(lambda: T.importer(fabrique_zip({"parcours.json": "{x", "video.webm": WEBM})), 400))
check("P15 format ou vidéo annoncée différente refusés", leve(lambda: T.importer(fabrique_zip({"parcours.json": json.dumps(dict(PJ, video="video.mp4")), "video.webm": WEBM})), 400)
      and leve(lambda: T.importer(fabrique_zip({"parcours.json": json.dumps(dict(PJ, format="autre")), "video.webm": WEBM})), 400))
GROS = json.dumps(dict(PJ, bourrage="x" * (T.MAX_PARCOURS_JSON + 10)))
ZG = fabrique_zip({"parcours.json": GROS, "video.webm": WEBM}, mentir="parcours.json")
check("P16 parcours.json trop gros, taille déclarée mentie : refusé en lisant", leve(lambda: T.importer(ZG)))
(_tmp / "pas.zip").write_bytes(b"pas un zip")
check("P17 zip illisible refusé", leve(lambda: T.importer(_tmp / "pas.zip"), 400))
avant = sorted(p.name for p in T.racine_parcours().iterdir())
check("P18 refus : aucun reste dans parcours/", avant == [PID], avant)
P2 = T.lire_parcours(T.importer(fabrique_zip({"parcours.json": BON, "video.webm": WEBM})))
e = P2["etapes"][0]
check("P19 fiche inconnue ici : action null ; champs du fichier ignorés", e["action"] is None and "selecteur" not in e
      and "‮" not in e["titre"]["fr"], e)
check("P20 id de parcours au gabarit", leve(lambda: T.lire_parcours("../x"), 400) and leve(lambda: T.lire_parcours("0" * 16), 404))
Z4 = fabrique_zip({"parcours.json": BON, "video.webm": WEBM, "clics.json": "{}", "x": b""})
check("P23 plus de 3 entrées : refusé avant d'ouvrir l'archive", leve(lambda: T.importer(Z4), 400))
PV = T.video_parcours(PID)
fh = open(PV, "rb")
try:
    check("P24 vidéo en lecture : retrait refusé (409), parcours intact", leve(lambda: T.retirer_parcours(PID), 409)
          and T.lire_parcours(PID)["id"] == PID)
finally:
    fh.close()
T.retirer_parcours(PID)
check("P21 retrait", not (T.racine_parcours() / PID).exists() and len(T.liste_parcours()) == 1)
check("P22 fallback : fiche sans localisateur cherchée par son libellé local", (lambda a: a and a["selecteur"] == T.SELECTEUR_GENERIQUE
      and a["texte"]["en"] == "Play the preview")(T.action_locale("montagecap.apercu.lire")))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
