"""Miroir de la couche « dialogues maison » du bundle (finitions UI, 20/09/2026).

Même discipline que `test_transfert_bundle.py` : le patcher est CHARGÉ comme
un module (ses ancres sont des données), le bloc injecté doit ÊTRE la couche
octet pour octet, chaque section est vérifiée des DEUX côtés, le bundle reste
en CRLF (compté en octets), et il ne reste AUCUN `confirm(` natif.

Run: python tests/test_dialogue_bundle.py
"""
import importlib.util
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
COUCHE = RACINE / "frontend" / "patches" / "dialogue.js"
PATCHER = RACINE / "scripts" / "patch_bundle_dialogue.py"

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def load(nom, chemin):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    P = load("patch_bundle_dialogue", PATCHER)
    raw = BUNDLE.read_bytes()
    s = raw.decode("utf-8-sig")
    couche = COUCHE.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
    src_patcher = PATCHER.read_text(encoding="utf-8")

    check("patcher : lit et écrit en octets (pas de read_text/write_text)",
          "read_text(" not in src_patcher and "write_text(" not in src_patcher)
    check("bundle : CRLF conservés, comptés en octets",
          raw.count(b"\r\n") > 15000 and raw.count(b"\n") == raw.count(b"\r\n"),
          f"crlf={raw.count(b'\r\n')} lf={raw.count(b'\n')}")
    i, j = s.find(P.BEGIN), s.find(P.END)
    check("bloc injecté présent une fois, BEGIN avant END",
          s.count(P.BEGIN) == 1 and s.count(P.END) == 1 and 0 <= i < j)
    bloc = s[i:j + len(P.END)].replace("\r\n", "\n") if i >= 0 else ""
    check("bloc = la couche octet pour octet", bloc == couche.strip())
    check("injection juste après l'ancre transfert",
          s.find(P.ANCHOR_INJECT) >= 0 and s.find(P.ANCHOR_INJECT) < i)
    for tag, a, r, n in P.PATCHES:
        check(f"{tag} : ancre consommée", s.count(a) == 0, str(s.count(a)))
        check(f"{tag} : remplacement présent ×{n}", s.count(r) == n, str(s.count(r)))
    check(f"{len(P.PATCHES)} sections = 11 sites confirm + 2 sites prompt du relevé", len(P.PATCHES) == 13)
    hors = s[:i] + s[j:]
    check("plus aucun confirm( ni prompt( natif hors couche",
          re.search(r"(?<![\w.])(?:confirm|prompt)\(", hors) is None and "window.confirm(" not in hors)
    check("await __dzDialogue.saisir ×2 hors couche",
          hors.count("await window.__dzDialogue.saisir(") == 2, str(hors.count("await window.__dzDialogue.saisir(")))
    SRC = RACINE / "frontend" / "shared" / "dialogue.js"
    check("la couche du patcher = frontend/shared/dialogue.js octet pour octet (source unique)",
          SRC.exists() and COUCHE.read_bytes() == SRC.read_bytes())
    check("await __dzDialogue.confirmer ×11 hors couche (la couche le cite en commentaire)",
          hors.count("await window.__dzDialogue.confirmer(") == 11,
          str(hors.count("await window.__dzDialogue.confirmer(")))
    check("la couche remplace window.alert et pose __dzDialogue",
          "window.alert = function" in couche and "window.__dzDialogue = {" in couche)
    check("la couche ne cite aucune ancre du patcher",
          all(a not in couche for _, a, _, _ in P.PATCHES) and P.ANCHOR_INJECT not in couche)
    check("charte : mono 9,5 px + letter-spacing .12em + surfaces --srf-*",
          "9.5px 'IBM Plex Mono'" in couche and "letter-spacing:.12em" in couche
          and "--srf-panel" in couche and "--brd-hard" in couche)
    check("charte : aucun arrondi de châssis", "border-radius" not in couche)
    for tag, jeton, n in P.SONDE_AMONT:
        check(f"sonde amont {tag} : {jeton} ×{n}", s.count(jeton) == n, str(s.count(jeton)))
    print(f"\n{ok} PASS, {fail} FAIL")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())


def test_dialogue_bundle():
    assert main() == 0
