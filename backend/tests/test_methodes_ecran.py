# -*- coding: utf-8 -*-
"""t433 (lot M0 « Méthodes », 08/11/2026) — l'écran « Méthodes » dans la barre des applications.

[1] le maillon      scripts/patch_bundle_dzmethodes.py : marqueur x1, aucun .bak_* laissé, octets, --check « déjà
                    appliqué », sondes (dzcreer3d, whatsapppage, épingles), 3 paires (ancre x1 avant, remplacement x1
                    livré), hors couche, épingles intouchées, CRLF, node --check ;
[2] réversible      avant_dzmethodes == defaire, appelé EN TÊTE de avant_dzcreer3d ;
[3] les paires      rail juste après la Bibliothèque (icône existante), iframe /methodes/ (clé pmethodes), liste blanche ;
[4] la page         index.html charge dico puis runtime AVANT methodes.js ; node --check ; aucune chaîne française
                    en dur hors commentaires (tout par dzT) ; chaque clé methodes.* utilisée existe en FR et EN ;
                    l'assemblé est à jour ; aucun confirm/alert natif ; données par textContent (aucun innerHTML hors icônes).
Run : & $PY tests/test_methodes_ecran.py   (depuis backend/)
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND / "tests"))
sys.path.insert(0, str(REPO / "scripts"))
import _i18n_l1_aide as AIDE  # noqa: E402

NODE = shutil.which("node")
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


ASSETS = REPO / "frontend" / "dist" / "assets"
BUNDLE = ASSETS / "index-BEOJX8L5.js"
RAW = BUNDLE.read_bytes()
B = RAW.decode("utf-8")
MARKER = "/*dzmethodes*/"
CONFIRMER = "await window.__dzDialogue.confirmer("
PAGE = REPO / "frontend" / "methodes"


def main():
    print("[1] le maillon")
    import patch_bundle_dzmethodes as PM
    src = (REPO / "scripts" / "patch_bundle_dzmethodes.py").read_text("utf-8")
    check("1.1 le marqueur une fois", B.count(MARKER) == 1, B.count(MARKER))
    check("1.2 aucun .bak_* laissé", not list(ASSETS.glob("*.bak_*")), list(ASSETS.glob("*.bak_*")))
    check("1.3 lecture et écriture en OCTETS", "read_text(" not in src and "write_text(" not in src
          and "read_bytes(" in src and "write_bytes(" in src)
    r = subprocess.run([sys.executable, "-X", "utf8", str(REPO / "scripts" / "patch_bundle_dzmethodes.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO))
    check("1.4 --check : « déjà appliqué », bundle inchangé", r.returncode == 0 and "déjà appliqué" in r.stdout
          and BUNDLE.read_bytes() == RAW, r.stdout + r.stderr)
    check("1.5 sondes : dzcreer3d, whatsapppage et épingles",
          ("dzcreer3d", "/*dzcreer3d*/", 1) in PM.SONDE_AMONT and ("whatsapppage", "/*whatsapppage*/", 1) in PM.SONDE_AMONT
          and ("useState", "x.useState(", 731) in PM.SONDE_AMONT and ("montage", "DzTracks", 181) in PM.SONDE_AMONT
          and ("dialogue", CONFIRMER, 30) in PM.SONDE_AMONT and ("version", "v2.8.0", 4) in PM.SONDE_AMONT)
    avant = PM.defaire(B)
    check("1.6 trois paires ; ancre x1 avant, remplacement x1 livré",
          len(PM.PAIRES) == 3 and all(avant.count(a) == 1 and B.count(z) == 1 for a, z in PM.PAIRES))
    check("1.7 paires sans fin de ligne, sans x.useState( ni confirmation",
          all("\n" not in a + z and "x.useState(" not in z and CONFIRMER not in z for a, z in PM.PAIRES))
    check("1.8 remplacements hors des blocs de couche", all(PM.hors_couche(B, z) for _a, z in PM.PAIRES))
    check("1.9 aller-retour exact", PM.appliquer(avant) == B)
    check("1.10 épingles intouchées et CRLF", B.count("x.useState(") == 731 and B.count("DzTracks") == 181
          and B.count("v2.8.0") == 4 and B.count(CONFIRMER) == 30
          and RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
    if NODE:
        r = subprocess.run([NODE, "--check", str(BUNDLE)], capture_output=True, text=True)
        check("1.11 node --check du bundle", r.returncode == 0, r.stderr[-300:])

    print("\n[2] réversible")
    # t494 (09/11) : dzigformat est posé APRÈS dzmethodes ; l'inverse le défait d'abord
    sans_aval = PM.defaire(AIDE.avant_dzigformat(B))
    check("2.1 avant_dzmethodes == defaire (maillon aval dzigformat défait d'abord)", AIDE.avant_dzmethodes(B) == sans_aval)
    aide = (BACKEND / "tests" / "_i18n_l1_aide.py").read_text("utf-8")
    i = aide.index("def avant_dzcreer3d(")
    corps = aide[i:aide.index("\ndef ", i + 10)]
    check("2.2 appelé EN TÊTE de avant_dzcreer3d", "bundle = avant_dzmethodes(bundle)" in corps
          and corps.index("avant_dzmethodes(") < corps.index("if _m.MARKER not in bundle"))
    check("2.3 sans marqueur : rendu tel quel", AIDE.avant_dzmethodes(sans_aval) == sans_aval)

    print("\n[3] les paires")
    i_bib = B.index('{id:"library",')
    i_me = B.index('{id:"methodes",')
    i_a3 = B.index('{id:"assets3d",')
    check("3.1 le rail : Méthodes entre la Bibliothèque et Game Assets, libellé dzT, icône existante",
          i_bib < i_me < i_a3 and 'label:dzT("methodes.rail.titre"),icon:"dz-action-lancer-recette"' in B[i_me:i_a3])
    svg = (REPO / "frontend" / "shared" / "icons" / "dz-icons.svg").read_text("utf-8")
    check("3.2 l'icône existe dans la planche Deepotus Glyph", 'id="dz-action-lancer-recette"' in svg)
    check("3.3 la vue : iframe /methodes/, clé pmethodes",
          's==="methodes"&&r.jsx("iframe",{src:"/methodes/",title:dzT("methodes.page.titre"),' in B and '"pmethodes")' in B)
    check("3.4 liste blanche des vues : « methodes » poussé dans Yu avant sa première lecture, la liste amont intacte",
          'sg=Yu.includes((Yu.push("methodes"),oa.get("view")))?oa.get("view"):null' in B
          and '"avatarlive","whatsapp"],sg=Yu.includes(' in B)

    print("\n[4] la page")
    html = (PAGE / "index.html").read_text("utf-8")
    ordre = [html.index(s) for s in ('/shared/dz-i18n-dico.js', '/shared/dz-i18n.js', 'methodes.js"')]
    check("4.1 dictionnaire puis runtime AVANT methodes.js", ordre == sorted(ordre))
    js = (PAGE / "methodes.js").read_text("utf-8")
    if NODE:
        r = subprocess.run([NODE, "--check", str(PAGE / "methodes.js")], capture_output=True, text=True)
        check("4.2 node --check methodes.js", r.returncode == 0, r.stderr[-300:])
    code = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    code = re.sub(r"(?m)^\s*//.*$", "", code)
    code = re.sub(r"//[^\n\"']*$", "", code, flags=re.M)
    litteraux = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', code)
    francais = [s for s in litteraux if re.search(r"[éèêàùçôî]", s) or re.search(r"\b(le|la|les|une|des)\b ", s)]
    check("4.3 aucun texte français en dur dans le code (tout passe par dzT)", not francais, francais[:5])
    cles = {k for k in re.findall(r'T\("(methodes\.[a-z_.A-Z]+)"', js) if not k.endswith(".")}
    cles |= {"methodes.effort." + e for e in "sml"} | {"methodes.filtre." + k for k in ("famille", "agent", "ecran")}
    dico = json.loads((REPO / "frontend" / "shared" / "i18n" / "methodes.json").read_text("utf-8"))
    check("4.4 chaque clé utilisée existe en FR et EN", all(k in dico and dico[k]["fr"] and dico[k]["en"] for k in cles),
          sorted(k for k in cles if k not in dico))
    check("4.5 les clés du rail existent", "methodes.rail.titre" in dico and "methodes.rail.desc" in dico
          and "methodes.page.titre" in dico)
    r = subprocess.run([sys.executable, "-X", "utf8", str(REPO / "scripts" / "i18n_assembler.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO))
    check("4.6 dictionnaire assemblé à jour", r.returncode == 0, r.stdout + r.stderr)
    check("4.7 aucun confirm/alert/prompt natif", not re.search(r"\b(confirm|alert|prompt)\(", code))
    check("4.8 innerHTML réservé aux icônes", code.count("innerHTML") == 1 and "dzIcone" in code)

    print(f"\n{ok} PASS, {fail} FAIL")
    return fail


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
