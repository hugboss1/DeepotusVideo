# -*- coding: utf-8 -*-
"""t208 (Espaces de marque E8, 13/10/2026) — les textes de marque qui étaient codés en dur lisent l'espace.
Ce que ce banc garde :
  - DEEPOTUS À L'OCTET : 161 sorties (légendes, voix off, scripts d'avatar et News par mode, langue et budget, voix du
    polissage, légende HeyGen, prompt et brief du classement News, storyboard, paroles, titre d'un lot) sont
    exactement celles de la base aa61fa8f (figées : tests/textes_espace_deepotus.json) ;
  - un autre espace n'hérite RIEN de Deepotus (ni « deep », ni « 🐙 », ni abysse) et lit SON persona : nom, mission
    et audience dans le prompt de classement, nom dans le storyboard, phrase fétiche en signature ;
  - un espace sans persona ne casse rien (son nom suffit) ;
  - les mots « deepotus » / « from the deep » ne sont plus dans le code de prompt_engine, news_rank, news_chain,
    music_service, pipeline, ni dans _ai_scenes ; le User-Agent des News est neutre ;
  - `remplir` ne touche qu'aux clés données (les accolades d'un exemple JSON restent).
Data-dir isolé, aucune clé, rien de payé. Témoin : la base (aa61fa8f) n'a pas le module.
Run (depuis backend/) : & $PY tests/test_espaces_textes.py"""
import ast, inspect, json, pathlib, re, subprocess, sys
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


r0 = subprocess.run(["git", "show", "aa61fa8f:backend/app/services/textes_espace.py"], capture_output=True, cwd=str(RACINE))
check("T1 témoin : la base n'a pas le module", r0.returncode != 0)

from app.services import espaces as ES, textes_espace as TX          # noqa: E402
ES.lire()

print("[A] Deepotus à l'octet")
GOLD = json.loads((_ICI / "textes_espace_deepotus.json").read_text(encoding="utf-8"))
vu = CAP.capturer("deepotus")
ecarts = sorted(k for k in set(GOLD) | set(vu) if GOLD.get(k) != vu.get(k))
check(f"A1 les {len(GOLD)} sorties figées sont identiques", not ecarts and len(GOLD) >= 160, str(ecarts[:5]))
check("A2 la graine porte les signatures d'avant", TX.textes("deepotus")["signature"]["EN"] == "From the deep. 🐙")

print("[B] un autre espace : son persona, rien de Deepotus")
rip = ES.creer({"nom": "Rippled"})["id"]
ES.ecrire_persona(rip, {"display_name": "Rippled — the network",
                        "identite": {"nom": "Rippled", "mission": "Instant settlement for everyone."},
                        "audience": {"qui": "Builders and small merchants"},
                        "ecran": {"catchphrase": "Ripple on."},
                        "default_hashtags_pool": ["#Rippled", "#Payments"]})
r = CAP.capturer(rip)
FUITE = re.compile(r"deep|🐙|abyss|biolumin|octopus|profondeurs\.", re.I)
texte = json.dumps(r, ensure_ascii=False)
# les intentions d'entrée (« Les profondeurs s'ouvrent… ») ne sont pas des fuites : on ne cherche que les signatures
fuites = sorted({m.group(0) for m in FUITE.finditer(texte.replace("Les profondeurs s'ouvrent", ""))})
check("B1 aucune trace de Deepotus dans 161 sorties", not fuites, str(fuites))
check("B2 légende générique = phrase fétiche + hashtags", r["generic_EN"] == "Ripple on.\n\n#Rippled #Payments", repr(r["generic_EN"]))
s0 = r["rank_system"][0]
check("B3 classement : nom, mission, audience", "Rippled" in s0 and "Instant settlement for everyone" in s0
      and "Builders and small merchants" in s0 and '{"id": str' in s0, s0)
check("B4 brief par défaut = mission + audience ; un brief donné passe tel quel",
      r["rank_prompt"][0].startswith("Brand brief: Instant settlement for everyone, Builders and small merchants\n")
      and r["rank_prompt"][1].startswith("Brand brief: solana\n"), str(r["rank_prompt"]))
check("B5 storyboard : le nom de l'espace ; le mode sujet seul inchangé",
      "storyboard director for a brand called Rippled" in r["story_system"][0]
      and r["story_system"][1] == GOLD["story_system"][1], str(r["story_system"]))
n = r["news_EN_None_None_90"]
check("B6 script News signé par l'espace, ton par défaut dit", n["script"].endswith("Stay sharp, stay skeptical. Rippled.")
      and "commentator" in n["rationale"][0], json.dumps(n)[:300])
check("B7 script News FR", r["news_FR_oracle_rates matter_90"]["script"].startswith(
    "Voici ce qui a bouge aujourd'hui. Lecture Rippled: rates matter."),   # le filtre colle « : » (comme avant)
      r["news_FR_oracle_rates matter_90"]["script"][:120])
check("B8 voix off et légende d'intention", r["vo_EN_x"] == "x. That's why Rippled."
      and r["cap_FR_x"] == "x.\n\nRipple on.\n\n#Rippled #Payments", repr((r["vo_EN_x"], r["cap_FR_x"])))
check("B9 voix du polissage neutre", r["polish_desc_EN_None"] == ["cynical, dry-witty commentator"], str(r["polish_desc_EN_None"]))
check("B10 paroles : la mission pour thème", "Rippled — Instant settlement for everyone." in r["lyrics"], r["lyrics"][:80])
check("B11 légende HeyGen", r["heygen_cap_None"] == "Hello there.\n\nRipple on.\n\n#Rippled #Payments", repr(r["heygen_cap_None"]))
check("B12 script d'avatar, rationale au nom de l'espace", "Rippled persona injected (brand cues + sign-off)"
      in r["script_EN_x_None_60"]["rationale"] and r["news_vide_EN"]["suggested_caption"].startswith("Rippled.\n\n"),
      str(r["script_EN_x_None_60"]["rationale"]))
check("B13 titre d'un lot", TX.textes(rip)["news_titre"] == "News Rippled")

print("[C] un espace sans persona")
nu = ES.creer({"nom": "Client Nu"})["id"]
t = TX.textes(nu)
r2 = CAP.capturer(nu)
check("C1 nom = celui de l'espace, signature « Client Nu. »", t["nom"] == "Client Nu" and t["signature"]["FR"] == "Client Nu.")
check("C2 aucune trace de Deepotus", not FUITE.search(json.dumps(r2, ensure_ascii=False).replace("Les profondeurs s'ouvrent", "")))
check("C3 brief et thème de repli", r2["rank_prompt"][0].startswith("Brand brief: Client Nu\n") and "the story so far" in r2["lyrics"])

print("[D] plus rien en dur")
APP = _ICI.parent / "app"


def chaines(src: str) -> list:
    """Les chaînes du code, docstrings exclues (elles citent la graine par son nom : ce n'est pas une sortie)."""
    arbre = ast.parse(src)
    docs = {id(n.value) for n in ast.walk(arbre) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}
    return [n.value for n in ast.walk(arbre)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]


INTERDIT = re.compile(r"deepotus|from the deep|des profondeurs|deep-sea", re.I)
for f in ("services/prompt_engine.py", "services/news_rank.py", "services/news_chain.py", "services/music_service.py",
          "services/pipeline.py", "services/news_service.py"):
    reste = [c[:60] for c in chaines((APP / f).read_text(encoding="utf-8")) if INTERDIT.search(c)]
    check(f"D {f} : aucune chaîne Deepotus", not reste, str(reste[:3]))
from app.api import routes as RT                                    # noqa: E402
reste = [c for c in chaines(inspect.getsource(RT._ai_scenes)) if INTERDIT.search(c)]
check("D routes._ai_scenes : aucune chaîne Deepotus", not reste, str(reste))
from app.services import news_service as NS                         # noqa: E402
check("D User-Agent des News neutre", "deepotus" not in NS._UA.lower() and NS._UA.startswith("Mozilla/5.0"), NS._UA)

print("[F] écran : l'exemple des notes de Quick")
BUNDLE = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_text(encoding="utf-8")
check("F1 plus de « $DEEPOTUS Pyth-feed », un exemple neutre (anglais, décision L2)",
      "Pyth-feed" not in BUNDLE and BUNDLE.count('placeholder:"e.g. fits the next launch announcement"') == 1)
sys.path.insert(0, str(RACINE / "scripts"))
import patch_bundle_dzespace as DZE                                   # noqa: E402
avant = DZE.defaire(BUNDLE)
check("F2 l'inverse du maillon rend l'exemple d'avant", 'placeholder:"e.g. fits the $DEEPOTUS Pyth-feed announcement"'
      in avant and DZE.appliquer(avant) == BUNDLE)

print("[E] remplir")
check("E1 seules les clés données", TX.remplir('{"id": str} {nom} {s}', nom="R") == '{"id": str} R {s}')
check("E2 listes et dicts", TX.remplir({"a": ["{x}", 3]}, x="y") == {"a": ["y", 3]})

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
