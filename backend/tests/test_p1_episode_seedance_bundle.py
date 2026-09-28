# -*- coding: utf-8 -*-
"""P1 #6 lot A (28/09/2026) — L'ECRAN CHAPITRES PROPOSE ET PAIE SEEDANCE.

Temoin (.bak_montage) : l'etape 4 disait « Seedance est rendu en Ken Burns
dans cette version », la requete de rendu n'emportait que {text,
image_filename, motion} et aucun max_usd. Groupe P1 du maillon montage :
  P1ep1  dzEpScenesPayload / dzEpMaxUsd / DzEpSeedance / DzEpDevis, poses
         avant DzEpisodes ;
  P1ep2  par scene Seedance : modele (DzVideoModelSel) + resolution ;
  P1ep3  etape 4 : le devis remplace la phrase Ken Burns ;
  P1ep4  la requete emporte modele/resolution/prompt ET max_usd = le devis
         AFFICHE (refus si le devis ne correspond plus aux scenes) ;
  P1ep5  fin de rendu : les replis Ken Burns s'affichent ;
  P1ep6  le pied de page ne promet plus « une prochaine iteration ».
Les fonctions pures sont EXECUTEES sous node. Faute n6 : details par _d().
Run : & $PY tests/test_p1_episode_seedance_bundle.py   (depuis backend/)
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(ROOT / "scripts"))
import patch_bundle_montage as P                           # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:400]
    except Exception as e:                                   # pragma: no cover
        return f"(detail illisible : {e})"


BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.with_name(BUNDLE.name + ".bak_montage")
s = BUNDLE.read_bytes().decode("utf-8")
bak = BAK.read_bytes().decode("utf-8") if BAK.is_file() else ""
NODE = shutil.which("node")
PHRASE_KB = "Seedance est rendu en Ken Burns dans cette version."
PROCHAINE = "L'animation Seedance par scène arrivera dans une prochaine itération."
REQ_OLD = 'scenes:scenes.map(function(s){return{text:s.text||"",image_filename:s.image_filename||null,motion:s.motion||"kenburns"}})})'

print("\n[0] temoins (.bak_montage)")
check("0.1 .bak present, node present", bool(bak) and bool(NODE), "")
check("0.2 temoin : la phrase Ken Burns, la promesse et l'ancienne requete x1 dans le .bak",
      bak.count(PHRASE_KB) == 1 and bak.count(PROCHAINE) == 1 and bak.count(REQ_OLD) == 1, "")

print("\n[1] bundle : textes et requete")
check("1.1 la phrase « rendu en Ken Burns dans cette version » a disparu", s.count(PHRASE_KB) == 0, "")
check("1.2 la promesse « prochaine iteration » a disparu", s.count(PROCHAINE) == 0, "")
check("1.3 l'ancienne requete a disparu ; la nouvelle emporte payload + max_usd",
      s.count(REQ_OLD) == 0 and s.count("scenes:dzEpScenesPayload(scenes),max_usd:dzMx") == 1, "")
check("1.3b assembleEpisode REFUSE avant tout appel quand le devis n'est pas pret ou perime",
      s.count('async function assembleEpisode(){var dzMx=dzEpMaxUsd(scenes);if(dzMx===!1){setEpErr("Devis Seedance pas encore prêt') == 1, "")
check("1.4 le devis est rendu a l'etape 4, le selecteur par scene seedance, le repli en fin de rendu",
      s.count("r.jsx(DzEpDevis,{scenes:scenes})") == 1 and s.count('sc.motion==="seedance"?r.jsx(DzEpSeedance,') == 1
      and s.count('"data-dzeprepli":"1"') == 1, "")


def _fn(nom, txt=s):
    i = txt.find("function " + nom + "(")
    if i < 0:
        return ""
    # jusqu'a la prochaine declaration de fonction de premier niveau connue
    j = min([k for k in (txt.find("function " + x + "(", i + 10) for x in
            ("dzEpScenesPayload", "dzEpSig", "dzEpMaxUsd", "DzEpSeedance", "DzEpDevis", "DzEpisodes", "dzVideoModels")) if k > i] or [len(txt)])
    return txt[i:j]


JS = _fn("dzEpScenesPayload") + "\n" + _fn("dzEpSig") + "\n" + _fn("dzEpMaxUsd")
SC = [{"text": "a", "image_filename": "i.png", "motion": "seedance", "video_model": "seedance-v1-pro",
       "resolution": "720p", "illustration_prompt": "tide", "image_url": "/x"},
      {"text": "b", "image_filename": None, "motion": "kenburns"}]
prog = JS + r"""
var SC=%s;var out={};
out.payload=dzEpScenesPayload(SC);
window={};out.sans=dzEpMaxUsd([SC[1]]);
out.pasPret=dzEpMaxUsd(SC);
window.__dzEpDevis={sig:dzEpSig(dzEpScenesPayload(SC)),total:0.16};out.pret=dzEpMaxUsd(SC);
var SC2=JSON.parse(JSON.stringify(SC));SC2[0].resolution="1080p";out.perime=dzEpMaxUsd(SC2);
process.stdout.write(JSON.stringify(out));
""" % json.dumps(SC)
prog = prog.replace("window={};", "global.window={};")
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
    f.write(prog)
r = subprocess.run([NODE, f.name], capture_output=True, text=True, encoding="utf-8") if NODE else None
os.unlink(f.name)
try:
    O = json.loads(r.stdout) if r and r.returncode == 0 else {}
except Exception:
    O = {}

print("\n[2] fonctions pures executees")
check("2.1 s'executent", bool(O), _d(r.stderr[-300:] if r else "node absent"))
check("2.2 la requete emporte modele, resolution, prompt d'illustration (et pas image_url)",
      (O.get("payload") or [{}])[0] == {"text": "a", "image_filename": "i.png", "motion": "seedance",
                                        "video_model": "seedance-v1-pro", "resolution": "720p", "illustration_prompt": "tide"},
      _d(O.get("payload")))
check("2.3 sans scene seedance illustree : pas de max_usd (undefined), rien a payer", bool(O) and "sans" not in O, _d(O))
check("2.4 devis pas encore pret : lancement REFUSE (false)", O.get("pasPret") is False, _d(O.get("pasPret")))
check("2.5 devis pret et conforme aux scenes : max_usd = le total affiche", O.get("pret") == 0.16, _d(O.get("pret")))
check("2.6 scenes modifiees depuis le devis (1080p) : refuse (false)", O.get("perime") is False, _d(O.get("perime")))

print("\n[3] groupe P1 et syntaxe")
_P1 = [t for t, _a, _r in getattr(P, "P1", [])]
check("3.1 P1ep1..P1ep6 dans le groupe P1 (apres P1rg2), groupe en QUEUE de PATCHES",
      [t.split("-")[0] for t in _P1[11:17]] == ["P1ep1", "P1ep2", "P1ep3", "P1ep4", "P1ep5", "P1ep6"]
      and [t for t, _a, _r in P.PATCHES[-len(_P1):]] == _P1, _d(_P1[-6:]))
_nc = subprocess.run([NODE, "--check", str(BUNDLE)], capture_output=True, text=True) if NODE else None
check("3.2 le bundle ENTIER passe node --check", _nc is not None and _nc.returncode == 0, _d(_nc.stderr[-300:] if _nc else ""))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
