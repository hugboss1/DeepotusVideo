"""Exporte le catalogue des menus de photocraft 0.3.0 (crates/ui-egui/src/menu_catalog.rs) et ses libellés français
(crates/ui-egui/src/i18n/fr.tsv) vers frontend/photolab/donnees/menus.json, pour l'écran du Photolab (P2).
Données de photocraft, MIT OU Apache-2.0 : la source et la licence sont écrites dans le JSON.
D8 : « Photoshop » n'apparaît dans aucun libellé montré ; chaque remplacement est consigné dans `remplacements`.

Usage : python scripts/photocraft_catalogue.py <dossier des sources photocraft v0.3.0 extraites>
"""
import hashlib, json, pathlib, re, sys

COMMIT_FR = "3d23a708c2"
BLOB_FR = "453fa2ad21254713c30f12d9a3ac017d1e3ded05"

RACINE = pathlib.Path(__file__).resolve().parent.parent
SORTIE = RACINE / "frontend" / "photolab" / "donnees" / "menus.json"
LIGNE = re.compile(r'^\s*\(&\[(?P<chemin>[^\]]*)\],\s*"(?P<libelle>(?:[^"\\]|\\.)*)",\s*'
                   r'(?:Some\("(?P<raccourci>[^"]*)"\)|None),\s*"(?P<id>[^"]*)"\),\s*$')
NEUTRE = {"Photoshop": "Photolab"}


def lire_fr(tsv: pathlib.Path):
    texte, par_id = {}, {}
    for l in tsv.read_text("utf-8").splitlines():
        if not l or l.startswith("#"):
            continue
        parts = l.split("\t")
        if len(parts) != 3:
            continue
        ctx, src, trad = parts
        if ctx == "":
            texte[src] = trad
        elif ctx == "@id":
            par_id[src] = trad
    return texte, par_id


def neutre(s: str, remplacements: list) -> str:
    for a, b in NEUTRE.items():
        if a in s:
            remplacements.append(s)
            s = s.replace(a, b)
    return s


def blob_git(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def main(args) -> int:
    global SORTIE
    args = list(args)
    opts = {}
    for cle in ("--fr-tsv", "--sortie"):
        if cle in args:
            i = args.index(cle)
            opts[cle] = args[i + 1]
            del args[i:i + 2]
    if len(args) != 1 or "--fr-tsv" not in opts:
        print("Usage : photocraft_catalogue.py <sources v0.3.0> --fr-tsv <fr.tsv> [--sortie <menus.json>]")
        return 2
    if "--sortie" in opts:
        SORTIE = pathlib.Path(opts["--sortie"]).resolve()
    src = pathlib.Path(args[0])
    tsv = pathlib.Path(opts["--fr-tsv"])
    # Le tag v0.3.0 n'a pas de français : le fr.tsv vient d'un commit postérieur, épinglé par son empreinte git.
    empreinte = blob_git(tsv.read_bytes())
    if empreinte != BLOB_FR:
        print(f"Refus : fr.tsv a l'empreinte git {empreinte}, attendue {BLOB_FR} (commit {COMMIT_FR}).")
        return 1
    cat = next(src.rglob("menu_catalog.rs"))
    texte, par_id = lire_fr(tsv)
    entrees, menus, remplacements = [], {}, []
    for l in cat.read_text("utf-8").splitlines():
        m = LIGNE.match(l)
        if not m:
            continue
        chemin = re.findall(r'"((?:[^"\\]|\\.)*)"', m["chemin"])
        for c in chemin:
            menus.setdefault(c, texte.get(c, c))
        if m["libelle"] == "---":
            entrees.append({"chemin": chemin, "separateur": True})
            continue
        en = m["libelle"]
        fr = par_id.get(m["id"]) or texte.get(en) or en
        entrees.append({"chemin": chemin, "id": m["id"], "libelle_en": neutre(en, remplacements),
                        "libelle_fr": neutre(fr, remplacements), "raccourci": m["raccourci"]})
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps({"source": "storytold/photocraft v0.3.0 crates/ui-egui/src/menu_catalog.rs",
                                  "source_fr": f"storytold/photocraft@{COMMIT_FR} crates/ui-egui/src/i18n/fr.tsv "
                                               f"(blob {BLOB_FR[:8]}, postérieur au tag v0.3.0 : le français est "
                                               f"arrivé après la release)",
                                  "licence": "MIT OR Apache-2.0", "menus_fr": menus, "remplacements": remplacements,
                                  "entrees": entrees}, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(f"{len(entrees)} lignes ({sum(1 for e in entrees if e.get('separateur'))} séparateurs), "
          f"{len(remplacements)} remplacements D8 -> {SORTIE.relative_to(RACINE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
