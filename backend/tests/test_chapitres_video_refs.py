# -*- coding: utf-8 -*-
"""Plan chapitres T9 (tache #62 du suivi, 02/10/2026) — le constructeur video MULTI-REFERENCES (Veo 3.1
reference-to-video, elements de Kling v3), PUR.
DECISION DE L'UTILISATEUR (02/10) : « constructeur, registre a part » — hors de VIDEO_MODELS (aucun selecteur ne le
montre), aucun client reseau importe, aucune route ne l'appelle.
Champs relus sur fal.ai le 02/10 : le plan en avait DEUX faux (`reference_image_urls` pour Veo, `{image_url}` pour les
elements de Kling) ; ce banc les asserte faux.
Temoin positif : la base (b8dd9cab) n'a ni le module ni aucun `elements` dans fal_service.
Run (depuis backend/) : & $PY tests/test_chapitres_video_refs.py"""
import ast, os, pathlib, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("FAL_KEY", "cle-de-banc")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def leve(f):
    try:
        f()
    except ValueError as e:
        return str(e)
    return None


BASE = "b8dd9cab"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/video_refs.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/fal_service.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a pas le module, et fal_service ne connait aucun `elements`",
      r0.returncode != 0 and r1.returncode == 0 and b"elements" not in r1.stdout)

try:
    from app.services import video_refs as VR                       # noqa: E402
except ImportError as e:
    VR = None
    check("T2 le module existe", False, str(e))

if VR:
    from app.services import fal_service as FS                      # noqa: E402
    print("[G] registre a part, rien d'expose, rien d'appele")
    check("G1 le registre est A PART : aucune de ses entrees dans VIDEO_MODELS", set(VR.REGISTRE_REFS).isdisjoint(FS.VIDEO_MODELS)
          and not any("reference-to-video" in m.get("endpoint", "") for m in FS.VIDEO_MODELS.values()))
    arbre = ast.parse((_ICI.parent / "app" / "services" / "video_refs.py").read_text(encoding="utf-8"))
    imports = [n.module if isinstance(n, ast.ImportFrom) else a.name for n in ast.walk(arbre)
               if isinstance(n, (ast.Import, ast.ImportFrom)) for a in (n.names if isinstance(n, ast.Import) else [None])]
    check("G2 aucun client reseau importe (fal_client, httpx, requests, urllib…)",
          not any(i and i.split(".")[0] in ("fal_client", "httpx", "requests", "urllib", "aiohttp") for i in imports), str(imports))
    hors = [p for p in (_ICI.parent / "app").rglob("*.py") if p.name != "video_refs.py" and "video_refs" in p.read_text(encoding="utf-8", errors="replace")]
    check("G3 aucun code de l'application ne l'appelle (pas de route, pas de selecteur)", hors == [], str(hors))
    check("G4 la date de verification est ecrite", VR.VERIFIE_LE == "2026-10-02")

    print("\n[V] Veo 3.1 reference-to-video")
    V = VR.REGISTRE_REFS["veo-3.1-ref"]
    check("V1 endpoint et champ RELUS : fal-ai/veo3.1/reference-to-video, `image_urls` (pas `reference_image_urls`)",
          V["endpoint"] == "fal-ai/veo3.1/reference-to-video" and V["champ"] == "image_urls")
    ents = [{"nom": "A", "face": "a0", "vues": ["a1", "a2"]}, {"nom": "B", "face": "b0", "vues": ["b1"]}]
    ep, args, notes = VR.construire("veo-3.1-ref", "un plan", ents, duree=8, aspect_ratio="9:16", resolution="1080p")
    check("V2 liste PLATE, faces de chacune d'abord (entrelacees), plafond 3, troncature DITE",
          ep == V["endpoint"] and args.get("image_urls") == ["a0", "b0", "a1"] and "reference_image_urls" not in args
          and any("5 références -> 3" in n for n in notes), f"{args} {notes}")
    check("V3 duree \"8s\", cadre et resolution passes, audio COUPE (moitie du prix), pas de seed",
          args.get("duration") == "8s" and args.get("aspect_ratio") == "9:16" and args.get("resolution") == "1080p"
          and args.get("generate_audio") is False and "seed" not in args, str(args))
    _, a2, n2 = VR.construire("veo-3.1-ref", "p", ents[:1], duree=5, aspect_ratio="4:3", resolution="8k")
    check("V4 une duree non publiee est RAMENEE a 8 s et dite ; cadre et resolution inconnus ne sont pas envoyes",
          a2.get("duration") == "8s" and any("5s -> 8s" in n for n in n2) and "aspect_ratio" not in a2 and "resolution" not in a2, f"{a2} {n2}")
    check("V5 zero reference : refus explicite", "au moins 1" in (leve(lambda: VR.construire("veo-3.1-ref", "p", [])) or ""))
    check("V6 une meme vue ne part pas deux fois", VR.construire("veo-3.1-ref", "p", [{"face": "x"}, {"face": "x", "vues": ["y"]}])[1]["image_urls"] == ["x", "y"])
    check("V7 le cout annonce : 8 s x 0,20 $ = 1,60 $ sans audio, 3,20 $ avec",
          VR.cout_estime("veo-3.1-ref", 8) == 1.6 and VR.cout_estime("veo-3.1-ref", 8, audio=True) == 3.2)

    print("\n[K] Kling v3 Pro, elements")
    K = VR.REGISTRE_REFS["kling-v3-pro-elements"]
    check("K1 endpoint : celui du registre video existant (meme modele), champ `elements`",
          K["endpoint"] == FS.VIDEO_MODELS["kling-v3-pro"]["endpoint"] and K["champ"] == "elements")
    ents = [{"nom": "Elias", "face": "e0", "vues": ["e1", "e2", "e3", "e4"]}, {"nom": "Mira", "face": "m0", "vues": ["m1"]}]
    ep, args, notes = VR.construire("kling-v3-pro-elements", "@Element1 regarde @Element2", ents, start_image_url="debut.png", duree=5)
    check("K2 la forme RELUE : {frontal_image_url, reference_image_urls (1 a 3)}, pas {image_url}",
          args.get("elements") == [{"frontal_image_url": "e0", "reference_image_urls": ["e1", "e2", "e3"]},
                                   {"frontal_image_url": "m0", "reference_image_urls": ["m1"]}]
          and "image_url" not in str(args.get("elements")).replace("_image_url", ""), str(args.get("elements")))
    check("K3 la vue en trop est DITE ; start_image_url passe ; duree entiere ; pas de seed ; audio coupe",
          any("Elias : 4 vues -> 3" in n for n in notes) and args.get("start_image_url") == "debut.png"
          and args.get("duration") == 5 and "seed" not in args and args.get("generate_audio") is False, f"{args} {notes}")
    check("K4 sans image de depart : refus (fal l'exige)", "start_image_url" in (leve(lambda: VR.construire("kling-v3-pro-elements", "p", ents)) or ""))
    _, a3, n3 = VR.construire("kling-v3-pro-elements", "@Element1 marche", [{"nom": "Seul", "face": "s0", "vues": []}] + ents[:1], start_image_url="d")
    check("K5 une entite sans seconde vue est ECARTEE (fal en exige une) et c'est dit",
          len(a3["elements"]) == 1 and a3["elements"][0]["frontal_image_url"] == "e0" and any("Seul écartée" in n for n in n3), f"{a3} {n3}")
    _, a4, n4 = VR.construire("kling-v3-pro-elements", "personne", ents, start_image_url="d")
    check("K6 un prompt qui ne nomme pas les @ElementN : prevenu", any("@Element1, @Element2" in n for n in n4), str(n4))
    cinq = [{"nom": f"P{i}", "face": f"f{i}", "vues": [f"v{i}"]} for i in range(5)]
    _, a5, n5 = VR.construire("kling-v3-pro-elements", "@Element1", cinq, start_image_url="d", duree=20)
    check("K7 cinq entites -> 4 elements (plafond), 20 s -> 15 s, tout est DIT",
          len(a5["elements"]) == 4 and a5["duration"] == 15 and any("5 éléments -> 4" in n for n in n5) and any("20s -> 15s" in n for n in n5), f"{n5}")
    check("K8 aucune entite complete : refus", "au moins 1" in (leve(lambda: VR.construire("kling-v3-pro-elements", "p", [{"face": "x"}], start_image_url="d")) or ""))
    check("K9 prix Kling non publie : le cout est INCONNU (None), jamais invente", VR.cout_estime("kling-v3-pro-elements", 5) is None)
    check("K10 un modele hors registre : refus", "registre" in (leve(lambda: VR.construire("seedance-v1-pro", "p", ents)) or ""))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
