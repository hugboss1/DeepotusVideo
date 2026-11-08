# -*- coding: utf-8 -*-
"""t435b (lot M2 « Méthodes », 08/11/2026) — B4 la chaîne d'éditions vidéo, la carte du Monteur, le bouton « Méthodes »
des écrans. Médias synthétiques, dossier de données temporaire ; le tir fal et le modèle sont SIMULÉS (aucun réseau).

[P] pur            l'invite d'une étape : la seule chose à changer + la garde de tout le reste ; consigne vide refusée ;
[C] chaîne         créer (copie de la source), lire, lister, parent = source ; devis = video_refs.cout_estime (entrée +
                   sortie, résolution), conform du clip court au plancher de 4 s, références par défaut ; refus :
                   pas une vidéo, résolution inconnue, chaîne inconnue ;
[R] routes         503 sans clé fal (aucune réserve, aucune dépense) ; 409 sans confirmation (devis joint) ; 409 coût
                   hors accord ; tir confirmé : 200, étape « en_cours » puis « fait » (tâche de fond), sortie rangée,
                   recalée au nombre d'images du parent, mesurée (dérive 0), ligne de dépense « montage », registre ;
                   la seconde étape édite la PREMIÈRE sortie ; tir en échec -> étape « echec », jamais « en_cours » ;
[A] agent          deviser_etape_chaine : carte « devis » valide (agent_format), chaîne ouverte sur `source` ; refus
                   propre ; chaines_lire ; boîte du Monteur ; la boucle remonte la carte et s'arrête (« carte ») ;
[N] pont           dz-methodes-pont.js sous node : pastille visible sur Montage, cachée ailleurs ; le clic navigue vers
                   « methodes » puis filtre l'iframe sur ?ecran=montage ; chargé par dist/index.html ; shared == dist.
Run : & $PY tests/test_chaine_video.py   (depuis backend/)
"""
import asyncio
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzchaine435b_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir()
pathlib.Path(_tmp, "outputs").mkdir()
for _k in ("ELEVENLABS_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "HEYGEN_API_KEY", "MESHY_API_KEY",
           "OPENAI_API_KEY", "OLLAMA_URL", "OPENROUTER_API_KEY", "FAL_KEY"):
    os.environ[_k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
REPO = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True, capture_output=True, timeout=120)


def refus(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError:
        return True
    return False


def main():
    if not shutil.which("ffmpeg"):
        print("SKIP: ffmpeg introuvable")
        return 0
    R = pathlib.Path(_tmp)
    M = R / "medias"
    M.mkdir()
    ff("-f", "lavfi", "-i", "testsrc2=size=640x360:rate=24:duration=5", "-c:v", "libx264", "-pix_fmt", "yuv420p",
       str(M / "prise.mp4"))
    ff("-f", "lavfi", "-i", "testsrc2=size=640x360:rate=24:duration=2.5", "-c:v", "libx264", "-pix_fmt", "yuv420p",
       str(M / "courte.mp4"))
    from PIL import Image
    Image.new("RGB", (64, 64), (200, 30, 30)).save(M / "ref.png")

    from app.services import chaine_video as CV
    from app.services import video_refs as VR

    print("[P] pur")
    p = CV.prompt_etape("  la robe devient   rouge ")
    check("P1 invite : « Change only this: … » puis la garde (caméra, timing, tout le reste)",
          p.startswith("Change only this: la robe devient rouge.") and "camera move" in p and "timing" in p)
    check("P2 consigne vide : refus", refus(CV.prompt_etape, "  "))

    print("\n[C] chaîne")
    ch = CV.creer("medias/prise.mp4", "Essai")
    check("C1 créer : id, copie de la source dans briques/chaines/<id>/, nom", ch["id"].startswith("ch_")
          and ch["source"] == f"briques/chaines/{ch['id']}/00_source.mp4" and (R / ch["source"]).is_file()
          and ch["nom"] == "Essai" and ch["origine"] == "medias/prise.mp4")
    check("C2 lire, lister, parent = la source", CV.lire(ch["id"])["id"] == ch["id"]
          and [x["id"] for x in CV.lister()] == [ch["id"]] and CV.parent(ch) == ch["source"])
    d = CV.devis_etape(ch["id"], "le ciel devient orange", resolution="480p")
    attendu = VR.cout_estime(CV.MODELE, int(d["secondes_sortie"]), entree_s=d["secondes_entree"], resolution="480p")
    check("C3 devis : prix = video_refs.cout_estime, 5 s, référence par défaut, pas de refus",
          d["usd"] == round(attendu, 4) and d["secondes_sortie"] == 5 and d["refus"] is None and d["n"] == 1
          and d["references"] == ["(image du milieu du parent)"] and d["op"]["kind"] == "video_refs", d)
    ch2 = CV.creer("medias/courte.mp4")
    d2 = CV.devis_etape(ch2["id"], "x")
    check("C4 clip de 2,5 s : conform prévu au plancher de 4 s", d2["conform"] and d2["secondes_sortie"] == 4
          and d2["refus"] is None, (d2.get("conform"), d2["secondes_sortie"], d2["refus"]))
    check("C5 refus : pas une vidéo, résolution inconnue, chaîne inconnue",
          refus(CV.creer, "medias/ref.png") and refus(CV.devis_etape, ch["id"], "x", None, "1080p")
          and refus(CV.devis_etape, "ch_000000000000", "x") and CV.lire("../x") is None)

    print("\n[R] routes")
    from fastapi.testclient import TestClient
    from app.config import settings
    from app.main import app
    from app.services import previs_plan as PV
    TIRS = []

    async def _tirer(modele, *, clip, frames, prompt, tache, resolution, duree, dossier=None):
        TIRS.append({"modele": modele, "clip": pathlib.Path(clip), "frames": [pathlib.Path(f) for f in frames],
                     "prompt": prompt, "tache": tache, "resolution": resolution, "duree": duree})
        if os.environ.get("DZ_BANC_ECHEC"):
            raise RuntimeError("fal.ai : panne simulée")
        dest = pathlib.Path(dossier) / f"previs_{len(TIRS)}.mp4"
        ff("-i", str(clip), "-vf", "hue=h=60", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(dest))
        return {"video": dest, "seed": 7, "endpoint": "bytedance/seedance-2.5/reference-to-video", "arguments": {},
                "notes": []}

    PV.tirer_previs = _tirer
    cl = TestClient(app)
    base = f"/api/briques/chaines/{ch['id']}"
    corps = {"consigne": "le ciel devient orange", "resolution": "480p"}
    r = cl.post(base + "/etapes", json=corps | {"confirme_cout": True, "max_usd": 5})
    check("R1 sans clé fal : 503, aucune étape réservée, aucun tir", r.status_code == 503 and not TIRS
          and CV.lire(ch["id"])["etapes"] == [], r.text[:200])
    settings.FAL_KEY = "fal-cle-de-banc"
    r = cl.post(base + "/etapes", json=corps)
    check("R2 sans confirmation : 409, devis joint", r.status_code == 409
          and (r.json().get("detail") or {}).get("usd") == d["usd"] and not TIRS, r.text[:200])
    r = cl.post(base + "/etapes", json=corps | {"confirme_cout": True, "max_usd": d["usd"] / 2})
    check("R3 coût hors accord : 409, rien réservé", r.status_code == 409 and CV.lire(ch["id"])["etapes"] == [], r.text[:200])
    r = cl.post(base + "/etapes", json=corps | {"confirme_cout": True, "max_usd": d["usd"]})
    e1 = (CV.lire(ch["id"])["etapes"] or [{}])[0]
    check("R4 tir confirmé : 200, l'étape 1 FAITE (tâche de fond), Seedance « editing », référence = image du parent",
          r.status_code == 200 and r.json()["n"] == 1 and e1.get("statut") == "fait" and len(TIRS) == 1
          and TIRS[0]["tache"] == "editing" and TIRS[0]["modele"] == "seedance-2.5-v2v"
          and TIRS[0]["prompt"].startswith("Change only this: le ciel devient orange") and len(TIRS[0]["frames"]) == 1,
          (r.text[:200], e1))
    s1 = R / e1.get("sortie", "x")
    i1 = PV.infos_clip(s1)
    check("R5 sortie rangée dans la chaîne, recalée sur le parent (120 images), mesurée : dérive 0, fiable",
          s1.is_file() and e1["sortie"].startswith(f"briques/chaines/{ch['id']}/01_etape") and i1["images"] == 120
          and e1["mesure"]["derive_images"] == 0 and e1["recalage"] and "erreur" not in e1["recalage"], (i1, e1))
    check("R6 la référence temporaire a été retirée", not list((R / "briques" / "chaines" / ch["id"]).glob("ref_*.png")))
    db = sqlite3.connect(str(R / "t.db"))
    dep = db.execute("SELECT categorie, ref, estime_usd FROM depenses").fetchall()
    check("R7 une ligne de dépense « montage », rattachée à l'étape", len(dep) == 1 and dep[0][0] == "montage"
          and dep[0][1] == f"{ch['id']}:1", dep)
    reg = cl.get("/api/briques/registre", params={"tache": ch["id"]}).json()
    check("R8 registre : « étape 1 » faite, estimée au devis", reg["etapes"][0]["etape"] == "étape 1"
          and reg["etapes"][0]["statut"] == "fait" and reg["etapes"][0]["estime_usd"] == d["usd"], reg)
    d2 = cl.post(base + "/devis", json={"consigne": "un oiseau traverse", "resolution": "480p"}).json()
    r = cl.post(base + "/etapes", json={"consigne": "un oiseau traverse", "resolution": "480p", "confirme_cout": True,
                                        "max_usd": d2["usd"]})
    check("R9 la seconde étape édite la PREMIÈRE sortie (devis et tir)", r.status_code == 200
          and d2["parent"] == e1["sortie"] and len(TIRS) == 2
          and TIRS[1]["clip"].resolve() == (R / e1["sortie"]).resolve(),
          (d2.get("parent"), str(TIRS[1]["clip"]) if len(TIRS) > 1 else None))
    os.environ["DZ_BANC_ECHEC"] = "1"
    d3 = cl.post(base + "/devis", json={"consigne": "la nuit tombe", "resolution": "480p"}).json()
    cl.post(base + "/etapes", json={"consigne": "la nuit tombe", "resolution": "480p", "confirme_cout": True,
                                    "max_usd": d3["usd"]})
    e3 = CV.lire(ch["id"])["etapes"][-1]
    check("R10 tir en échec : l'étape passe « echec » avec la raison, jamais « en_cours »", e3["statut"] == "echec"
          and "panne simulée" in e3.get("erreur", ""), e3)
    os.environ.pop("DZ_BANC_ECHEC")
    check("R11 GET liste et chaîne ; 404 inconnue", cl.get("/api/briques/chaines").json()["chaines"]
          and cl.get(base).json()["id"] == ch["id"] and cl.get("/api/briques/chaines/ch_000000000000").status_code == 404)

    print("\n[A] agent")
    from app.services import agent_boites as B
    from app.services import agent_format as fmt
    from app.services import agent_outils as ao
    loop = asyncio.new_event_loop()
    run = loop.run_until_complete
    ctx = ao.Ctx(cid="am_000000000001", agent="monteur")
    r = run(ao.executer("deviser_etape_chaine", {"consigne": "le sac devient bleu", "source": "medias/prise.mp4",
                                                 "resolution": "480p"}, ctx))
    c = r.get("carte") or {}
    check("A1 deviser_etape_chaine : carte « devis » valide, action chaine_etape, chaîne neuve ouverte sur la source",
          r["ok"] and c.get("genre") == "devis" and c.get("action") == "chaine_etape" and c["devis"] > 0
          and not fmt.valider(fmt.nouveau_message("agent", [c])) and CV.lire(c["arguments"]["chaine"]) is not None, r)
    r = run(ao.executer("deviser_etape_chaine", {"consigne": "x"}, ctx))
    check("A2 ni chaîne ni source : refus propre", r["ok"] is False and r.get("carte") is None)
    r = run(ao.executer("chaines_lire", {"chaine": ch["id"]}, ctx))
    check("A3 chaines_lire : la chaîne et ses étapes", r["ok"] and len(r["donnees"]["etapes"]) == 3)
    check("A4 boîte du Monteur : + chaines_lire, deviser_etape_chaine ; mcp ne voit pas la carte ; registre sain",
          {"chaines_lire", "deviser_etape_chaine"} <= set(B.outils_pour("monteur"))
          and "deviser_etape_chaine" not in B.outils_pour("mcp") and B.verifier() == [], B.verifier())
    from app.services import agent_metier as AM
    from app.services import moteurs_texte as MT
    settings.ANTHROPIC_API_KEY = "sk-ant-cle-de-banc"
    SCRIPT = [{"blocs": [{"type": "tool_use", "id": "t1", "name": "deviser_etape_chaine",
                          "input": {"consigne": "la robe devient rouge", "chaine": ch["id"], "resolution": "480p"}}],
               "arret": "tool_use", "in_tok": 100, "out_tok": 50},
              {"blocs": [{"type": "text", "text": "jamais lu"}], "arret": "end_turn", "in_tok": 1, "out_tok": 1}]
    MT.converser = lambda *a, **k: SCRIPT.pop(0)
    conv = AM.creer("monteur")
    r = run(AM.message("monteur", conv["id"], "Rends la robe rouge", max_usd=1))
    check("A5 la boucle remonte la carte et s'arrête (« carte »), un seul appel du modèle",
          r["arret"] == "carte" and len(r["cartes"]) == 1 and r["cartes"][0]["action"] == "chaine_etape"
          and len(SCRIPT) == 1 and AM.lire("monteur", conv["id"])["messages"][1]["cartes"], r)
    loop.close()

    print("\n[N] pont")
    sh = REPO / "frontend" / "shared" / "dz-methodes-pont.js"
    check("N1 shared == dist ; chargé par dist/index.html", sh.read_bytes() == (REPO / "frontend" / "dist" / "shared" /
          "dz-methodes-pont.js").read_bytes() and '<script src="/shared/dz-methodes-pont.js"></script>' in
          (REPO / "frontend" / "dist" / "index.html").read_text("utf-8"))
    node = shutil.which("node")
    if node:
        harnais = r"""
        var ev = [], noeuds = [], vue = "montage", remplace = [];
        function noeud(tag){ var n = {tag: tag, style: {}, attrs: {}, enfants: [], ecoute: {}, textContent: "",
          setAttribute: function(k, v){ this.attrs[k] = v; }, appendChild: function(c){ this.enfants.push(c); return c; },
          addEventListener: function(k, f){ this.ecoute[k] = f; } };
          Object.defineProperty(n, "lastChild", {get: function(){ return this.enfants[this.enfants.length - 1]; }});
          noeuds.push(n); return n; }
        var iframe = {contentWindow: {location: {replace: function(u){ remplace.push(u); }}}};
        global.window = {localStorage: {getItem: function(){ return vue; }}, dzT: function(k){ return k; },
          dispatchEvent: function(e){ ev.push(e); }};
        global.CustomEvent = function(t, o){ this.type = t; this.detail = o.detail; };
        global.document = {body: noeud("body"), createElement: noeud,
          querySelector: function(s){ return s.indexOf("/methodes/") > 0 ? iframe : null; }};
        global.setInterval = function(){}; var minuteurs = [];
        global.setTimeout = function(f){ minuteurs.push(f); };
        require(process.argv[2]);
        var b = document.body.enfants[0];
        var r = {visible_montage: b.style.display};
        vue = "settings"; window.__dzMethodesPont.tic(); r.visible_reglages = b.style.display;
        vue = "montage"; window.__dzMethodesPont.tic(); r.texte = b.lastChild.textContent;
        b.ecoute.click(); while (minuteurs.length) minuteurs.shift()();
        r.nav = ev.map(function(e){ return e.type + ":" + e.detail.view; }); r.remplace = remplace;
        console.log(JSON.stringify(r));
        """
        f = R / "h.js"
        f.write_text(harnais, "utf-8")
        p = subprocess.run([node, str(f), str(sh)], capture_output=True, text=True, timeout=60)
        try:
            j = json.loads(p.stdout)
        except ValueError:
            j = {"erreur": (p.stdout + p.stderr)[-400:]}
        check("N2 pastille visible sur Montage, cachée sur Réglages, libellé dzT", j.get("visible_montage") == "inline-flex"
              and j.get("visible_reglages") == "none" and j.get("texte") == "methodes.pont.bouton", j)
        check("N3 clic : navigation vers « methodes » puis l'iframe filtrée sur ?ecran=montage",
              j.get("nav") == ["deepotus:navigate:methodes"] and j.get("remplace") == ["/methodes/?ecran=montage"], j)
    dico = json.loads((REPO / "frontend" / "shared" / "i18n" / "methodes.json").read_text("utf-8"))
    check("N4 clés FR/EN du pont et des cartes", all(k in dico for k in ("methodes.pont.bouton", "methodes.pont.titre",
          "methodes.agent.lancer", "methodes.agent.etape_faite", "methodes.agent.arret.carte")))

    print(f"\n{ok} PASS, {fail} FAIL")
    return fail


if __name__ == "__main__":
    code = main()
    shutil.rmtree(_tmp, ignore_errors=True)
    sys.exit(1 if code else 0)
