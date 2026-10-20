# -*- coding: utf-8 -*-
"""Constats relevés en rédigeant le catalogue de l'assistant (t248, 20/10/2026), corrigés ensemble.
Sections :
  [P] plafonds des images : une `source` inconnue (« generation » de Rejouer la recette) n'est plus une catégorie
      fantôme ; les routes d'images passent toutes par `_categorie_image` ;
  [C] maillon dzconstats : la musique payante et le test Telegram se confirment, les images du Studio, des Chapitres
      et du Planificateur portent leur `source` ; [D] sa chaîne ; [K] ses textes FR/EN ;
  [V] infobulles du Vectorlab qui promettaient plus que le bouton (Calque de réglage, Masque de luminance, Épaissir).
Run (depuis backend/) : & $PY tests/test_constats_catalogue.py"""
import pathlib, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if callable(cond):
        try:
            cond = cond()
        except Exception as e:  # noqa: BLE001
            cond, detail = False, f"{type(e).__name__}: {e}"
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label}  {detail}")


# ---------------------------------------------------------------- [P] plafonds des images
print("[P] plafonds des images")
ROUTES = (RACINE / "backend" / "app" / "api" / "routes.py").read_text(encoding="utf-8")
check("P1 plus aucune source brute prise pour catégorie",
      'str(body.get("source") or "bibliotheque")' not in ROUTES)
check("P2 les huit gardes d'images passent par _categorie_image", ROUTES.count("_categorie_image(body)") == 8,
      ROUTES.count("_categorie_image(body)"))


def _cat():
    from app.api import routes as R
    from app.services import plafonds as PL
    c = R._categorie_image
    assert c({}) == "bibliotheque"
    assert c({"source": "generation"}) == "bibliotheque"          # Rejouer la recette
    assert c({"source": "chapitres"}) == "chapitres"
    assert c({"source": "studio"}) == "studio"
    assert c({"source": " Scheduler "}) == "scheduler"
    assert c({"source": "x" * 40}) == "bibliotheque"
    assert c({"source": None}) == "bibliotheque"
    assert all(c({"source": k}) == k for k in PL.CATEGORIES)
    return True


check("P3 _categorie_image : catégorie connue gardée, sinon « bibliotheque »", _cat)

# ---------------------------------------------------------------- [C] câblage du maillon dzconstats dans le livré
print("[C] câblage dans le livré")
sys.path.insert(0, str(RACINE / "scripts"))
sys.path.insert(0, str(_ICI))
import patch_bundle_dzconstats as PC  # noqa: E402
RAW = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes()
B = RAW.decode("utf-8")
CONF = "await window.__dzDialogue.confirmer("


def _avant(texte, ancre, cible):
    """`ancre` précède `cible` dans la même fonction (moins de 600 caractères entre les deux)."""
    j = B.index(cible)
    i = B.rfind(ancre, 0, j)
    return i >= 0 and j - i < 600


PLAF = RACINE / "frontend" / "shared" / "dz-plafonds.js"
check("C1 musique : dz-plafonds.js confirme POST /api/audio/music AVANT l'envoi ; copie dist identique",
      lambda: 'p === "/api/audio/music" && m === "POST" && !(await musiqueConfirmee(o))' in PLAF.read_text(encoding="utf-8")
      and PLAF.read_bytes() == (RACINE / "frontend" / "dist" / "shared" / "dz-plafonds.js").read_bytes())


def _musique_sous_node():
    """La VRAIE couche sous node, faux fetch et faux dialogue : Annuler n'envoie rien (409 lisible), Générer envoie
    une fois en nommant le modèle, et un autre POST n'est pas retenu."""
    import subprocess, tempfile
    js = r"""
globalThis.window = globalThis; globalThis.location = { href: "http://x/" };
globalThis.sessionStorage = { getItem() { return null; }, setItem() {} };
const T0 = setTimeout; globalThis.setTimeout = () => 0;
let envois = [], reponse = false, questions = [];
globalThis.fetch = async (u, o) => { envois.push(String(u)); return new Response("{}", { status: 200 }); };
window.__dzDialogue = { confirmer: async (q, opt) => { questions.push(q); return reponse; } };
require(process.argv[2]);
(async () => {
  const corps = JSON.stringify({ model: "lyria-3", prompt: "x" });
  const r1 = await window.fetch("/api/audio/music", { method: "POST", body: corps });
  const d1 = await r1.json();
  reponse = true;
  const r2 = await window.fetch("/api/audio/music", { method: "POST", body: corps });
  const r3 = await window.fetch("/api/audio/voiceover", { method: "POST", body: "{}" });
  console.log(JSON.stringify({ s1: r1.status, d1: d1.detail, s2: r2.status, s3: r3.status, envois, questions }));
})();
"""
    with tempfile.TemporaryDirectory() as t:
        f = pathlib.Path(t) / "h.js"
        f.write_text(js, encoding="utf-8")
        p = subprocess.run(["node", str(f), str(PLAF)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    import json as _j
    r = _j.loads(p.stdout.strip().splitlines()[-1])
    assert r["s1"] == 409 and "rien" in r["d1"], r
    assert r["envois"] == ["/api/audio/music", "/api/audio/voiceover"], r
    assert len(r["questions"]) == 2 and all("lyria-3" in q for q in r["questions"]), r
    assert r["s2"] == 200 and r["s3"] == 200, r
    return True


check("C1b musique sous node : Annuler n'envoie rien, Générer envoie une fois, les autres POST passent", _musique_sous_node)
check("C2 Réglages › Comptes : Telegram seul confirmé avant le test",
      'async function w(k){if(k==="telegram"){if(!' + CONF + 'dzT("reglages.comptes.telegram_q")' in B)
check("C2b Espaces : Telegram seul confirmé avant le test",
      'async function tester(c){if(c.plateforme==="telegram"){if(!' + CONF + 'dzT("reglages.comptes.telegram_q")' in B)
check("C3 l'API envoie la source (absente = défaut serveur)", 'source:o/*__dzconstats*/})' in B)
check("C3b Studio : 3 générations (Image gen, sticker, illustration News) + les variantes en « studio »",
      B.count(',"studio")') == 3 and 'body.source=body.source||"studio";D.postJson("/images/process",body)' in B, B.count(',"studio")'))
check("C3c Chapitres : 2 illustrations en « chapitres »", B.count(',"chapitres")') == 2)
check("C3d Planificateur : 3 images en « scheduler »", B.count('void 0,"scheduler")') == 3)
check("C3e Bibliothèque « Créer l'image » inchangée (défaut serveur)", 'D.generateImage(C,1,"portrait_16_9")' in B)

# ---------------------------------------------------------------- [D] chaîne
print("[D] chaîne")
check("D1 marqueur ×1", B.count(PC.MARKER) == 1)
check("D2 aller-retour exact", lambda: PC.appliquer(PC.defaire(B)) == B)
check("D3 avant_dzschedconf défait dzconstats d'abord",
      lambda: PC.MARKER not in __import__("_i18n_l1_aide").avant_dzschedconf(B))
check("D4 comptes figés : x.useState( 731, DzTracks 181, v2.8.0 ×4, confirmer ×30",
      B.count("x.useState(") == 731 and B.count("DzTracks") == 181 and B.count("v2.8.0") == 4 and B.count(CONF) == 30)
check("D5 octets : CRLF partout", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
check("D6 aucun .bak_dzconstats laissé", not list((RACINE / "frontend" / "dist" / "assets").glob("*.bak_dzconstats")))
def _hors_blocs():
    """Aucune paire dans un bloc de couche (MONTAGE, SONVFX) : chacun doit rester sa couche source (L3/L4 2c)."""
    d = PC.defaire(B)
    for nom in ("MONTAGE", "SONVFX"):
        b0, b1 = d.index(f"/*__DZ_{nom}_BEGIN__*/"), d.index(f"/*__DZ_{nom}_END__*/")
        assert not any(b0 < d.index(a) < b1 for a, _ in PC.PAIRES), nom
    return True


check("D8 aucune paire dans les blocs de couche MONTAGE et SONVFX", _hors_blocs)
check("D7 aucune paire ne contient de fin de ligne : un bundle relu en mode texte (CRLF → LF) se défait aussi",
      lambda: not any("\n" in a or "\r" in a or "\n" in r or "\r" in r for a, r in PC.PAIRES)
      and PC.MARKER not in __import__("_i18n_l1_aide").avant_dzconstats(B.replace("\r\n", "\n")))

# ---------------------------------------------------------------- [K] textes
print("[K] textes")
import json, re  # noqa: E402
DICO = json.loads((RACINE / "frontend" / "shared" / "i18n" / "constats_confirmer.json").read_text(encoding="utf-8"))
UTILISEES = set(re.findall(r'dzT\("(reglages\.comptes\.telegram_[a-z_]+)"', "".join(a for _, a in PC.PAIRES)))
UTILISEES |= set(re.findall(r'texte\("(son\.musique\.[a-z_]+)"', PLAF.read_text(encoding="utf-8")))
check("K1 toutes les clés du maillon et de dz-plafonds ont FR et EN non vides",
      len(UTILISEES) == 7 and UTILISEES <= set(DICO) and all(DICO[k]["fr"] and DICO[k]["en"] for k in UTILISEES), sorted(UTILISEES - set(DICO)))
check("K2 mêmes variables en FR et en EN",
      all(set(re.findall(r"\{\w+\}", v["fr"])) == set(re.findall(r"\{\w+\}", v["en"])) for v in DICO.values()))
ASSEMBLE = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_text(encoding="utf-8")
check("K3 le dictionnaire assemblé les contient", all(f'"{k}"' in ASSEMBLE for k in DICO))

# ---------------------------------------------------------------- [V] infobulles du Vectorlab
print("[V] infobulles du Vectorlab")
VL = json.loads((RACINE / "frontend" / "shared" / "i18n" / "vectorlab.json").read_text(encoding="utf-8"))
check("V1 « Calque de réglage » dit qu'il ouvre l'onglet Pixel",
      VL["vectorlab.calques.reglage_titre"]["fr"].startswith("Ouvre l'onglet Pixel")
      and VL["vectorlab.calques.reglage_titre"]["en"].startswith("Opens the Pixel tab"))
check("V2 « Masque de luminance » dit qu'il ouvre l'onglet Apparence",
      VL["vectorlab.calques.masque_lum_titre"]["fr"].startswith("Ouvre l'onglet Apparence")
      and VL["vectorlab.calques.masque_lum_titre"]["en"].startswith("Opens the Appearance tab"))
check("V3 « Épaissir » dit qu'il crée une copie (l'original reste)",
      "copie" in VL["vectorlab.typo.epaissir_titre"]["fr"] and "copy" in VL["vectorlab.typo.epaissir_titre"]["en"])
_VLJS = RACINE / "frontend" / "vectorlab" / "js"
check("V4 le module passe toujours par ces clés (source du Vectorlab inchangée)",
      lambda: 'T("vectorlab.calques.reglage_titre")' in (_VLJS / "mod-layers.js").read_text(encoding="utf-8")
      and 'T("vectorlab.calques.masque_lum_titre")' in (_VLJS / "mod-layers.js").read_text(encoding="utf-8")
      and 'T("vectorlab.typo.epaissir_titre")' in (_VLJS / "mod-typo.js").read_text(encoding="utf-8"))

# ---------------------------------------------------------------- [Q] vocabulaire des catégories (t265)
print("[Q] vocabulaire des catégories de dépense")
_MOTIFS_CAT = [r'\bcategorie\s*(?::\s*str\s*)?=\s*"([a-z0-9_]+)"',               # mot-clé ou défaut (tirer_garde, Depense)
               r'\b_plafond\(.*,\s*"([a-z0-9_]+)"\s*(?:,\s*[^")]*)?\)',          # _plafond(op, "x"[, ref])
               r'\bverifier\(\s*op\w*\s*,\s*"([a-z0-9_]+)"']                     # plafonds.verifier(op, "x")


def _categories_ecrites():
    vus = {}
    for f in (RACINE / "backend" / "app").rglob("*.py"):
        for i, ligne in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for m in _MOTIFS_CAT:
                for c in re.findall(m, ligne):
                    vus.setdefault(c, []).append(f"{f.name}:{i}")
    return vus


def _q1():
    from app.services import plafonds as PL
    vus = _categories_ecrites()
    assert {"motion", "aide", "chapitres", "studio"} <= set(vus), sorted(vus)     # le relevé voit bien le code
    hors = {c: v[:2] for c, v in vus.items() if c not in PL.CATEGORIES}
    assert not hors, hors
    return True


check("Q1 toute catégorie écrite par le code (motion, aide, mobile…) est au vocabulaire plafonds.CATEGORIES", _q1)


def _q2():
    from app.api import routes as R
    assert R._categorie_image({"source": "motion"}) == "motion"
    assert R._categorie_image({"source": "generation"}) == "bibliotheque"
    return True


check("Q2 _categorie_image garde « motion », écarte toujours une source inconnue", _q2)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
