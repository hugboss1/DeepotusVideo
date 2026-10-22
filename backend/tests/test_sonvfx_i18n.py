# -*- coding: utf-8 -*-
"""Son & VFX : traduction FR/EN de tout ce que le lot t268-t278 a livré (t279, 22/10/2026).

Sections :
  [I] chaque clé dzT littérale des pages du lot (sources sonvfx-*.js, maillon dzsonvfx, scripts des illustrations)
      existe au dictionnaire, avec un français et un anglais non vides et les mêmes variables {x} ;
  [G] les noms des générateurs IA du Post-traitement : le serveur sert le libellé de registre (en français) ;
      la page le traduit par une table de clés LITTÉRALES (dzSvoNomGen), sauf les noms propres. Le français de chaque
      clé reste celui du registre, et chaque réglage d'un générateur a son libellé (dzSvoOptLbl) ;
  [S] la page affiche ces noms par la table, jamais g.label brut ; le livré porte la source à l'octet.
Run (depuis backend/) : & $PY tests/test_sonvfx_i18n.py"""
import json, pathlib, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(RACINE / "scripts"))
sys.path.insert(0, str(RACINE / "backend"))

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label}  {str(detail)[:300]}")


DICO = {}
for _p in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
    DICO.update(json.loads(_p.read_text(encoding="utf-8")))
PATCHES = RACINE / "frontend" / "patches"
SOURCES = {p.name: p.read_bytes().decode("utf-8") for p in sorted(PATCHES.glob("sonvfx-*.js"))}
SOURCES["patch_bundle_dzsonvfx.py"] = (RACINE / "scripts" / "patch_bundle_dzsonvfx.py").read_text(encoding="utf-8")
for _n in ("dz-vfx-illus.js", "dz-post-illus.js"):
    SOURCES[_n] = (RACINE / "frontend" / "shared" / _n).read_text(encoding="utf-8")


def _vars(s):
    return sorted(set(re.findall(r"\{(\w+)\}", s or "")))


# ── [I] clés littérales ───────────────────────────────────────────────────────────────────────────────────────────
print("[I] clés des pages du lot")
CLES = {}
for _n, _s in SOURCES.items():
    for _k in re.findall(r'dzT\(\s*"([A-Za-z0-9_.]+)"', _s):
        CLES.setdefault(_k, _n)
check("I0 les pages du lot passent par dzT (plus de 300 clés)", len(CLES) > 300, len(CLES))
_abs = sorted(k for k in CLES if k not in DICO)
check("I1 chaque clé existe au dictionnaire", not _abs, _abs[:10])
_vide = sorted(k for k in CLES if k in DICO and not (DICO[k].get("fr") and DICO[k].get("en")))
check("I2 chaque clé a un français ET un anglais", not _vide, _vide[:10])
_var = sorted(k for k in CLES if k in DICO and _vars(DICO[k].get("fr")) != _vars(DICO[k].get("en")))
check("I3 mêmes variables {x} des deux côtés", not _var, _var[:10])
_hub = json.loads((RACINE / "frontend" / "shared" / "i18n" / "sonvfx_hub.json").read_text(encoding="utf-8"))
_ailleurs = sorted(k for k in _hub if not k.startswith(("sonvfx.", "dzsv")))
check("I4 sonvfx_hub.json ne porte que des clés du lot (sonvfx.*)", not _ailleurs, _ailleurs[:10])

# ── [G] noms des générateurs ──────────────────────────────────────────────────────────────────────────────────────
print("[G] générateurs du Post-traitement")
from app.services import post_ia as PI  # noqa: E402

GENS = PI.generateurs()
SRC = SOURCES["sonvfx-post.js"]


def _table(nom):
    m = re.search(r"function " + nom + r"\([a-z]\)\{return \(\{(.*?)\}\)\[", SRC, re.S)
    return dict(re.findall(r'"?([A-Za-z0-9_:.-]+)"?:dzT\("([A-Za-z0-9_.]+)"\)', m.group(1))) if m else {}


NOMS = _table("dzSvoNomGen")
OPTS = _table("dzSvoOptLbl")
# un nom propre (marque, modèle) ne se traduit pas : le libellé servi reste affiché
PROPRES = {"sfx_video:hunyuan-foley", "sfx_video:thinksound", "video_post:restyle-decart", "sfx:elevenlabs-direct",
           "sfx:elevenlabs-v2-fal"}
_manq = [g["id"] for g in GENS if g["id"] not in NOMS and g["id"] not in PROPRES]
check("G1 chaque générateur qui n'est pas un nom propre a son nom traduit", NOMS and not _manq, _manq)
_ecart = [(g["id"], g["label"], DICO.get(NOMS[g["id"]], {}).get("fr")) for g in GENS
          if g["id"] in NOMS and not g["label"].startswith(DICO.get(NOMS[g["id"]], {}).get("fr") or "§")]
check("G2 le français de chaque clé est le libellé du registre ou son début (titre de carte des VFX IA, sans la "
      "précision finale) : la table reste fidèle", not _ecart, _ecart)
check("G3 la table ne nomme aucun générateur inconnu", set(NOMS) <= {g["id"] for g in GENS},
      sorted(set(NOMS) - {g["id"] for g in GENS}))
_ok = [k for k in NOMS if DICO.get(NOMS[k], {}).get("en") and DICO[NOMS[k]]["en"] != DICO[NOMS[k]]["fr"]]
check("G4 chaque nom traduit a un anglais distinct du français", len(_ok) == len(NOMS),
      sorted(set(NOMS) - set(_ok)))
_okeys = sorted({k for g in GENS for k in (g.get("options") or {})})
check("G5 chaque réglage d'un générateur a son libellé", _okeys and set(_okeys) <= set(OPTS),
      sorted(set(_okeys) - set(OPTS)))
check("G6 les clés des réglages existent au dictionnaire", all(v in DICO for v in OPTS.values()),
      [v for v in OPTS.values() if v not in DICO])

# ── [S] la page ───────────────────────────────────────────────────────────────────────────────────────────────────
print("[S] la page")
BUNDLE = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
_i, _j = BUNDLE.find("/*__dzsvparticules*/"), BUNDLE.find("/*__dzsvpost*/")
PAGE = BUNDLE[_i + len("/*__dzsvparticules*/"):_j] if 0 <= _i < _j else ""
import patch_bundle_dzsonvfx as PSV  # noqa: E402

check("S1 le livré porte la source aplatie, à l'octet", PAGE and PAGE == PSV.aplatir(SRC))
check("S2 aucun nom de générateur affiché brut (children / title / aria-label sur g.label)",
      PAGE and not re.search(r"(children|title):[^,{}]*g\.label|nom:g\.label", PAGE))
check("S3 les réglages IA passent par dzSvoOptLbl (plus de nom d'API brut)",
      "children:dzSvoOptLbl(k)" in PAGE and 'children:k.replace(' not in PAGE)
check("S4 le nom traduit sert au bouton, à son aria-label et à la tête du maillon",
      PAGE.count("dzSvoNomGen(g)") >= 3)
_dico = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_bytes()
check("S5 dictionnaire assemblé à jour (clés neuves, source = copie de dist)",
      all(k.encode() in _dico for k in list(NOMS.values()) + list(OPTS.values()))
      and _dico == (RACINE / "frontend" / "dist" / "shared" / "dz-i18n-dico.js").read_bytes())

print(f"\n{ok} PASS / {fail} FAIL")


def test_sonvfx_i18n():
    assert fail == 0


if __name__ == "__main__":
    sys.exit(1 if fail else 0)
