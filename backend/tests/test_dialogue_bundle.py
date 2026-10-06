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
    # tache #81 PR C (03/10/2026) : le maillon montage (en aval) reecrit trois de ces dialogues : jeter range a la
    # CORBEILLE. La derive est datee ici ; le reste du remplacement du maillon dialogue est inchange.
    DERIVES_AVAL = {'confirmer("Delete this render and its files?")': 'confirmer("Mettre ce rendu à la corbeille ? (restaurable depuis la Corbeille de la Bibliothèque)")',
                    'confirmer("Delete ce son ?")': 'confirmer("Mettre ce son à la corbeille ? (restaurable depuis la Corbeille de la Bibliothèque)")',
                    'confirmer("Delete cette image ?")': 'confirmer("Mettre cette image à la corbeille ? (restaurable depuis la Corbeille de la Bibliothèque)")'}
    for tag, a, r, n in P.PATCHES:
        for _v, _n in DERIVES_AVAL.items():
            r = r.replace(_v, _n)
        check(f"{tag} : ancre consommée", s.count(a) == 0, str(s.count(a)))
        check(f"{tag} : remplacement présent ×{n}", s.count(r) == n, str(s.count(r)))
    check(f"{len(P.PATCHES)} sections = 11 sites confirm + 2 sites prompt du relevé", len(P.PATCHES) == 13)
    hors = s[:i] + s[j:]
    check("plus aucun confirm( ni prompt( natif hors couche",
          re.search(r"(?<![\w.])(?:confirm|prompt)\(", hors) is None and "window.confirm(" not in hors)
    # 27/09/2026 : + 1, le bouton Save du Studio (section R8sv1 de patch_bundle_montage, maillon AVAL) -- ce releve
    # ne voyait que les `prompt(` NUS ; les `window.prompt(` (dix restants) lui avaient echappe.
    # + les dix window.prompt( restants (R8pr1..R8pr7 + deux replis du maillon montage) : 11 avec await, et les deux
    # copies de chemin enchainees par .then(done) (13 appels en tout) ; plus AUCUN window.prompt(.
    # tache #53 (01/10/2026) : + 1 saisir enchaine par .then, le nom d'un preset Quick (P5st1, maillon montage) : 13 -> 14.
    # tache #71 PR A (03/10/2026) : + 1 saisir avec await, le nom d'une recette du Studio (DzRecetteBtn, maillon montage).
    # tache #71 PR C (03/10/2026) : + 1 saisir avec await, garder ou changer un texte d'une recette (dzRecLancerAvec).
    # tache #72 PR B (03/10/2026) : + 2 saisir avec await, le nom d'un nouveau kit et le renommage (DzKits).
    # tache #78 PR B (03/10/2026) : + 3 saisir enchaines par .then (couche montage, projets de la Bibliotheque) : le nom
    # d'un nouveau projet (barre et menu « Envoyer vers ») et le renommage d'un projet : 18 -> 21, await inchange.
    # tache #76 PR H (03/10/2026) : + 1 saisir avec await, le lien d'un cadre Figma a importer (DzFigmaImport, maillon montage).
    # tache T102 (06/10/2026) : + 1 saisir avec await, le theme du squelette de paroles (SvmLyricsEditor, couche sonvfx).
    check("await __dzDialogue.saisir ×17 hors couche (2 de ce maillon + 15 du maillon montage), saisir ×23, window.prompt( ×0",
          hors.count("await window.__dzDialogue.saisir(") == 17 and hors.count("window.__dzDialogue.saisir(") == 23
          and "window.prompt(" not in hors, str((hors.count("await window.__dzDialogue.saisir("), hors.count("window.prompt("))))
    SRC = RACINE / "frontend" / "shared" / "dialogue.js"
    check("la couche du patcher = frontend/shared/dialogue.js octet pour octet (source unique)",
          SRC.exists() and COUCHE.read_bytes() == SRC.read_bytes())
    # t132 (28/09/2026) : + 2, la barre des episodes du maillon montage (P1es1 : modifications perdues, suppression).
    # tache #69 (02/10/2026) : + 1, « Remplacer » le graphe ouvert par un graphe importe (DzImportGraph, maillon montage).
    # tache #71 PR B (03/10/2026) : + 1, le devis du duel de moteurs (DzDuelPanel, maillon montage).
    # tache #71 PR C (03/10/2026) : + 1, le devis d'une recette lancee depuis la Bibliotheque (dzRecLancerAvec).
    # tache #72 PR B (03/10/2026) : + 1, supprimer un kit de marque (DzKits).
    # tache #80 PR B (03/10/2026) : + 1, le prix de « Rejouer la recette » dans la fiche d'une image (DzFiche).
    # tache #81 PR C (03/10/2026) : + 2, vider la corbeille (DzCorbeille) et mettre des doublons a la corbeille (DzNettoyage).
    # tache #82 PR A (04/10/2026) : + 1, supprimer un commentaire de revue (DzCommentaires).
    # tache #82 PR C (04/10/2026) : + 1, le prix des legendes (DzRecherche).
    # tache #82 PR D (04/10/2026) : + 1, la taille de l'installation de CLIP (DzClipBloc).
    check("await __dzDialogue.confirmer ×23 hors couche (11 + 2 de P1es1 + 1 import du Studio + 1 duel + 1 recette + 1 kit + 1 rejouer + 2 corbeille/nettoyage + 1 commentaire + 1 legendes + 1 CLIP ; la couche le cite en commentaire)",
          hors.count("await window.__dzDialogue.confirmer(") == 23,
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
