# -*- coding: utf-8 -*-
"""t208-bis (Espaces de marque E8, 13/10/2026) — les textes Deepotus qui restaient en dur dans le Studio, les News et
l'avatar photo HeyGen lisent l'espace actif.
Ce que ce banc garde :
  - un seul aide `dzMq(clé)` (maillon dzespace) : l'espace `deepotus` (ou rien de chargé) rend MOT POUR MOT les
    textes d'avant ; un autre espace rend un texte NEUTRE à son nom, sans « deep », « 🐙 » ni « deepotus » ;
  - les sites du bundle le lisent : nœud Texte (valeur par défaut = script HeyGen par défaut, compilateur, devis
    dzPinReemploi), légende « planifier ce rendu » et celle du shell, vignette, bandeau de marque, élément texte de
    l'animation, prompt d'illustration News, nom par défaut de createPhotoAvatar ;
  - aucun x.useState ajouté (731), l'inverse du maillon rend le bundle d'avant ;
  - serveur : le nom par défaut de l'avatar photo et le prompt système du polissage des scripts viennent de l'espace
    (Deepotus : la graine, identique à l'octet ; un autre : son nom).
Data-dir isolé, aucune clé, rien de payé. Témoin : la base (cab8f445) n'a pas dzMq.
Run (depuis backend/) : & $PY tests/test_espaces_studio.py"""
import asyncio, inspect, io, json, pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI))
import _textes_espace_capture as CAP                                 # noqa: E402
CAP.preparer()
sys.path.insert(0, str(_ICI.parent))
RACINE = _ICI.parent.parent
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "cab8f445"
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("T1 témoin : la base n'a pas dzMq", r0.returncode == 0 and b"function dzMq(" not in r0.stdout)

BUNDLE = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_text(encoding="utf-8")
DEEP = {"texte": "From the deep, the prophecy ascends.", "legende": "Drop from the deep. 🐙",
        "legende_shell": "New drop from the deep. 🐙", "vignette": "🐙 DEEPOTUS · from the deep",
        "bandeau_mark": "🐙", "bandeau_texte": "DEEPOTUS", "anim_texte": "DEEPOTUS",
        "news_illus": "deepotus news illustration, cinematic deep-sea", "avatar": "Custom deepotus avatar"}

print("[A] le bundle : un aide, les sites le lisent")
check("A1 dzMq posé une fois, aucun useState ajouté",
      BUNDLE.count("function dzMq(") == 1 and BUNDLE.count("x.useState(") == 731)
for lit in ("From the deep, the prophecy ascends.", "Drop from the deep. 🐙", "New drop from the deep. 🐙",
            "🐙 DEEPOTUS · from the deep", "deepotus news illustration, cinematic deep-sea", "Custom deepotus avatar"):
    check(f"A2 « {lit} » ne reste que dans dzMq", BUNDLE.count(f'"{lit}"') == 1, str(BUNDLE.count(f'"{lit}"')))
SITES = {
    "nœud Texte (catalogue)": 'outPorts:[{id:"out",type:"text"}],props:{get value(){return dzMq("texte")}}}',
    "script HeyGen du compositeur": 'script=(scr&&scr.props&&scr.props.value)||dzMq("texte"),',
    "script HeyGen du compilateur": 'b=((p=h==null?void 0:h.props)==null?void 0:p.value)||dzMq("texte");',
    "devis (dzPinReemploi)": 'String(sc&&sc.props&&sc.props.value||dzMq("texte")).trim()',
    "légende « planifier ce rendu »": 'caption:dzMq("legende")})',
    "légende du shell": 'caption:F.caption||dzMq("legende_shell"),',
    "vignette": ':dzMq("vignette")})]})',
    "bandeau de marque": 'props:{get mark(){return dzMq("bandeau_mark")},get text(){return dzMq("bandeau_texte")}}}',
    "élément texte de l'animation": 'if(t==="text")b.text=dzMq("anim_texte");',
    "aperçu de l'élément texte": 'children:cur.text||dzMq("anim_texte")}',
    "prompt d'illustration News": 'x.useState(newsTitle||dzMq("news_illus"))',
    "nom de l'avatar photo": 'createPhotoAvatar:async(e,t=dzMq("avatar"))=>',
}
for nom, motif in SITES.items():
    check(f"A3 {nom}", BUNDLE.count(motif) == 1)

sys.path.insert(0, str(RACINE / "scripts"))
import patch_bundle_dzespace as DZE                                   # noqa: E402
try:
    avant = DZE.defaire(BUNDLE)
except AssertionError as e:
    avant = str(e)
check("A4 l'inverse du maillon rend les littéraux d'avant, et l'aller-retour est exact",
      "function dzMq(" not in avant and avant.count('"From the deep, the prophecy ascends."') == 4
      and 'props:{mark:"🐙",text:"DEEPOTUS"}' in avant and DZE.appliquer(avant) == BUNDLE, avant[:120])

print("[B] dzMq sous node")
i = BUNDLE.index("function dzMq(")
fn = BUNDLE[i:BUNDLE.index("function tg(", i)]
cles = json.dumps(list(DEEP))
js = (fn + ";var K=" + cles + ",R={};function tout(){var o={};K.forEach(function(k){o[k]=dzMq(k)});return o}"
      "R.rien=tout();var dzEspCache=null;R.nul=tout();"
      "dzEspCache={actif:'deepotus',espaces:[{id:'deepotus',nom:'Deepotus'}]};R.deep=tout();"
      "dzEspCache={actif:'esp_1',espaces:[{id:'deepotus',nom:'Deepotus'},{id:'esp_1',nom:'Rippled'}]};R.rip=tout();"
      "dzEspCache={actif:'esp_9',espaces:[]};R.inconnu=tout();"
      "process.stdout.write(JSON.stringify(R))")
rn = subprocess.run(["node", "-e", js], capture_output=True, text=True, encoding="utf-8")
try:
    R = json.loads(rn.stdout)
except ValueError:
    R = {}
check("B1 rien de chargé (et dzEspCache non déclaré) : les textes d'avant", R.get("rien") == DEEP and R.get("nul") == DEEP,
      rn.stdout[:200] + rn.stderr[:300])
check("B2 Deepotus : les textes d'avant, mot pour mot", R.get("deep") == DEEP, str(R.get("deep")))
rip = R.get("rip") or {}
FUITE = re.compile(r"deep|🐙|abyss|octopus|prophe", re.I)
check("B3 un autre espace : rien de Deepotus", rip and not [v for v in rip.values() if FUITE.search(v)], str(rip))
check("B4 un autre espace : son nom", rip.get("texte") == "Meet Rippled." and rip.get("legende") == "New from Rippled."
      and rip.get("legende_shell") == "New from Rippled." and rip.get("vignette") == "RIPPLED"
      and rip.get("bandeau_texte") == "RIPPLED" and rip.get("anim_texte") == "RIPPLED" and rip.get("bandeau_mark") == ""
      and rip.get("news_illus") == "Rippled news illustration, cinematic" and rip.get("avatar") == "Custom Rippled avatar", str(rip))
check("B5 un espace absent de la liste : son id", (R.get("inconnu") or {}).get("texte") == "Meet esp_9.", str(R.get("inconnu")))

print("[C] serveur : avatar photo et polissage")
from app.services import espaces as ES, textes_espace as TX, summarizer as SUM   # noqa: E402
ES.lire()
POLIR_AVANT = ("You are a scriptwriter for DEEPOTUS, a deep-sea themed crypto brand "
               "whose mascot is an octopus from the deep. You rewrite short scripts "
               "for an AI avatar to read aloud. Keep the brand name 'Deepotus' and "
               "its sign-off. Make it punchy, natural and varied. No hashtags, no "
               "stage directions, no quotation marks, no preamble. Return ONLY the "
               "script text.")
td = TX.textes("deepotus")
check("C1 Deepotus : nom d'avatar et prompt du polissage d'avant", td.get("avatar_nom") == "Custom deepotus avatar"
      and td.get("polir_systeme") == POLIR_AVANT, str((td.get("avatar_nom"), td.get("polir_systeme"))))
rid = ES.creer({"nom": "Rippled"})["id"]
tr = TX.textes(rid)
check("C2 un autre espace : son nom, rien de Deepotus", tr.get("avatar_nom") == "Custom Rippled avatar"
      and "Rippled" in tr.get("polir_systeme", "") and not FUITE.search(tr.get("polir_systeme", "") + tr["avatar_nom"]),
      str((tr.get("avatar_nom"), tr.get("polir_systeme"))))

vus = []
SUM._chat_dispatch = lambda prompt, system, max_tokens: (vus.append(system) or None, "")
SUM.available = lambda: True
for eid in ("deepotus", rid):
    with ES.sous_espace(eid):
        SUM.rewrite_script("Hello there.")
check("C3 rewrite_script envoie le prompt de l'espace", vus[:1] == [POLIR_AVANT] and len(vus) == 2
      and "Rippled" in vus[1] and not FUITE.search(vus[1]), str(vus))

from app.api import routes as RT                                    # noqa: E402
src = inspect.getsource(RT.create_photo_avatar_endpoint)
check("C4 l'endpoint de l'avatar photo n'a plus « deepotus » en dur", "deepotus" not in src.lower(), src[:300])
reçus = []


class _Faux:
    async def create_photo_avatar(self, file_path, avatar_name, group_name, do_train):
        reçus.append(avatar_name)
        return {"photo_avatar_id": "x", "group_id": "g", "status": "ok", "avatar_name": avatar_name}


type(RT.settings).has_heygen = property(lambda self: True)


async def _rien(*a, **k):
    return None
RT.HeyGenClient = _Faux
RT._plafond = _rien
RT.invalidate_list_cache = lambda: None
from fastapi import UploadFile                                      # noqa: E402
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00"
       b"\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")
for eid in ("deepotus", rid):
    with ES.sous_espace(eid):
        for nom in ("", "Mon avatar"):
            try:
                asyncio.run(RT.create_photo_avatar_endpoint(file=UploadFile(io.BytesIO(PNG), filename="a.png"),
                                                            avatar_name=nom, group_name="", do_train=False))
            except Exception as e:  # noqa: BLE001
                reçus.append(f"ERREUR {e!r}")
check("C5 avatar sans nom : celui de l'espace ; un nom donné passe tel quel",
      reçus == ["Custom deepotus avatar", "Mon avatar", "Custom Rippled avatar", "Mon avatar"], str(reçus))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
