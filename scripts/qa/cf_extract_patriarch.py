"""Extrait « Le Patriarche des Vieilles Maisons » du dossier fabricant.

    python scripts/qa/cf_extract_patriarch.py [--pdf CHEMIN] [--out CHEMIN]

POURQUOI UN SCRIPT ONE-SHOT ET PAS UN TEST (plan D9, fait F1)
─────────────────────────────────────────────────────────────
Le dossier fabricant ne contient PAS les 92 faces : il contient DIX images,
dont une seule au gabarit d'une carte (1060 x 1484 px, 5:7 exact, page 5 —
le gabarit illustré 4.1). C'est la SEULE face du jeu réel qui existe
aujourd'hui, et c'est sur elle que roule la preuve §7.2.

Ce fichier n'est donc pas un test : c'est l'outil qui pose la pièce à
conviction HORS DÉPÔT, une fois, à la main. Le gardien permanent est le test
synthétique de `test_cards_capture.py` (une carte à vérité connue AU MÊME
FORMAT) ; le vrai fichier, lui, ne monte jamais en CI — il n'est pas à nous.

TROIS RÈGLES, ET AUCUNE N'EST DÉCORATIVE
────────────────────────────────────────
1. L'IGNORE SE VÉRIFIE AVANT D'ÉCRIRE. `.superpowers/` est ignoré par le
   dépôt ; si un jour il ne l'était plus, ce script REFUSE d'écrire plutôt
   que de semer un actif tiers dans l'index. L'incident du gauntlet précédent
   (le vrai nom de l'utilisateur parti dans 58 binaires) a coûté assez cher
   pour que la vérification passe AVANT le premier octet.
2. LES MÉTADONNÉES SONT PURGÉES. Un PNG écrit par PIL depuis une image dont
   le `.info` vient d'un décodeur porte volontiers des chunks tEXt : nom de
   l'outil, chemin d'origine, horodatage. On repart donc des PIXELS SEULS
   (`frombytes` sur `tobytes`), et on RELIT le fichier écrit pour prouver
   qu'aucun chunk de texte n'y est, et qu'aucun mot interdit (chemins,
   « pypdf », le nom du dossier source) ne traîne dans les octets.
3. LE PDF MANQUANT EST UNE ERREUR LITTÉRALE, avec le chemin attendu. Un
   « FileNotFoundError » nu enverrait chercher un fichier dont personne ne
   sait plus le nom.

Sortie : le chemin écrit, ses dimensions, son poids, et la liste des chunks
PNG effectivement présents.
"""
from __future__ import annotations

import argparse
import struct
import subprocess
import sys
from pathlib import Path

# La racine du dépôt : ce fichier est dans scripts/qa/.
REPO = Path(__file__).resolve().parents[2]

PDF_DEFAUT = Path.home() / "Downloads" / "DOSSIER_FABRICANT_DEEPOTUS_FRAGMENTS.pdf"
OUT_DEFAUT = REPO / ".superpowers" / "samples" / "patriarch.png"

# La page (index 0) et les dimensions qui identifient l'objet. La spec donne
# les deux ; les dimensions suffisent à trancher (une seule image du dossier
# les porte), la page évite de balayer les seize.
PAGE_INDEX = 4
TAILLE = (1060, 1484)

# Les chunks qu'un PNG d'image pure a le droit de porter. Tout le reste — et
# en particulier tEXt/iTXt/zTXt/tIME — est du métadonnée, donc du texte qui
# peut nommer une machine, un chemin ou une personne.
CHUNKS_PERMIS = {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"sRGB", b"gAMA", b"cHRM"}


def _echoue(message: str) -> None:
    print("ECHEC : " + message, file=sys.stderr)
    raise SystemExit(2)


def ignore_verifie(cible: Path) -> str:
    """`.superpowers/` est-il ignoré ? Rend la ligne de .gitignore qui l'ignore.

    Le contrôle passe par git lui-même (`git check-ignore -v`) : réimplémenter
    la sémantique des motifs .gitignore pour se rassurer serait exactement le
    genre de garde qui se trompe en silence."""
    r = subprocess.run(
        ["git", "check-ignore", "-v", str(cible)],
        cwd=str(REPO), capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    return ""


def ajoute_ignore() -> str:
    gi = REPO / ".gitignore"
    texte = gi.read_text(encoding="utf-8") if gi.is_file() else ""
    if not texte.endswith("\n"):
        texte += "\n"
    texte += ".superpowers/\n"
    gi.write_text(texte, encoding="utf-8")
    return str(gi)


def chunks_png(octets: bytes) -> list:
    """Les types de chunks du fichier, dans l'ordre. Lecture à la main : on
    veut voir ce qui EST écrit, pas ce qu'une bibliothèque veut bien rendre."""
    if octets[:8] != b"\x89PNG\r\n\x1a\n":
        _echoue("le fichier écrit n'est pas un PNG")
    out = []
    i = 8
    while i + 8 <= len(octets):
        (n,) = struct.unpack(">I", octets[i:i + 4])
        typ = octets[i + 4:i + 8]
        out.append(typ)
        i += 12 + n
        if typ == b"IEND":
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", default=str(PDF_DEFAUT))
    ap.add_argument("--out", default=str(OUT_DEFAUT))
    a = ap.parse_args()

    pdf = Path(a.pdf)
    out = Path(a.out)

    if not pdf.is_file():
        _echoue(
            "le dossier fabricant est introuvable.\n"
            "        chemin attendu : " + str(pdf) + "\n"
            "        (le dossier n'est pas dans le depot : il appartient a "
            "l'utilisateur. Deposez-le a ce chemin, ou passez --pdf.)")

    # ── 1. L'IGNORE, AVANT LE PREMIER OCTET ──────────────────────────────
    ligne = ignore_verifie(out)
    if not ligne:
        gi = ajoute_ignore()
        ligne = ignore_verifie(out)
        if not ligne:
            _echoue(
                "« .superpowers/ » n'est toujours pas ignore apres ecriture "
                "dans " + gi + " : refus d'ecrire un actif tiers dans un "
                "arbre suivi.")
        print("IGNORE AJOUTE : « .superpowers/ » a ete ecrit dans " + gi)
    print("ignore : " + ligne)

    try:
        import pypdf
    except ImportError as e:
        _echoue("pypdf est absent de cet interpreteur (" + str(e) + "). Il "
                "est pourtant dans requirements : lancez ce script avec le "
                "python du backend.")

    lecteur = pypdf.PdfReader(str(pdf))
    if len(lecteur.pages) <= PAGE_INDEX:
        _echoue("le PDF n'a que " + str(len(lecteur.pages)) + " pages : la "
                "page " + str(PAGE_INDEX + 1) + " n'existe pas.")
    page = lecteur.pages[PAGE_INDEX]

    trouve = None
    vues = []
    for im in page.images:
        taille = tuple(im.image.size)
        vues.append(str(taille[0]) + "x" + str(taille[1]))
        if taille == TAILLE:
            trouve = im
            break
    if trouve is None:
        _echoue(
            "aucune image " + str(TAILLE[0]) + "x" + str(TAILLE[1]) + " sur "
            "la page " + str(PAGE_INDEX + 1) + ". Vues : " + ", ".join(vues))

    src = trouve.image
    # ── 2. LES PIXELS SEULS ──────────────────────────────────────────────
    # `frombytes` reconstruit une image dont `.info` est VIDE : rien du
    # decodeur, rien du PDF, rien du chemin ne peut suivre jusqu'au fichier.
    from PIL import Image
    mode = src.mode if src.mode in ("RGB", "L", "RGBA") else "RGB"
    if src.mode != mode:
        src = src.convert(mode)
    propre = Image.frombytes(mode, src.size, src.tobytes())

    out.parent.mkdir(parents=True, exist_ok=True)
    propre.save(str(out), format="PNG", optimize=True)

    # ── 3. LA PREUVE, SUR LES OCTETS ECRITS ──────────────────────────────
    octets = out.read_bytes()
    types = chunks_png(octets)
    interdits = [t for t in types if t not in CHUNKS_PERMIS]
    if interdits:
        out.unlink(missing_ok=True)
        _echoue("le PNG porte des chunks de metadonnees : "
                + ", ".join(t.decode("ascii", "replace") for t in interdits))
    bas = octets.lower()
    for mot in (b"pypdf", b"deepotus_fragments", b"dossier_fabricant",
                b"c:\\", b"/users/", b"\\users\\", b"downloads"):
        if mot in bas:
            out.unlink(missing_ok=True)
            _echoue("le PNG contient « " + mot.decode("ascii", "replace")
                    + " » : metadonnee non purgee.")

    with Image.open(str(out)) as relu:
        relu.load()
        dims = relu.size
        m = relu.mode
    if tuple(dims) != TAILLE:
        _echoue("le fichier relu fait " + str(dims) + ", pas " + str(TAILLE))

    print("ecrit   : " + str(out))
    print("taille  : " + str(dims[0]) + " x " + str(dims[1]) + " px, mode "
          + m + ", ratio " + format(dims[1] / dims[0], ".6f")
          + " (5:7 = " + format(7 / 5, ".6f") + ")")
    print("poids   : " + format(len(octets), ",d").replace(",", " ") + " octets")
    print("chunks  : " + " ".join(t.decode("ascii", "replace") for t in types))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
