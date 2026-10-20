"""Exporte le catalogue des menus de photocraft 0.3.0 (crates/ui-egui/src/menu_catalog.rs) et ses libellés français
(crates/ui-egui/src/i18n/fr.tsv) vers frontend/photolab/donnees/menus.json, pour l'écran du Photolab (P2).
Données de photocraft, MIT OR Apache-2.0 : la source et la licence sont écrites dans le JSON.
D8 : « Photoshop » n'apparaît dans aucun libellé montré ; chaque remplacement est consigné dans `remplacements`.

t258 (M9, 20/10/2026) : le français vient du fr.tsv LIVRÉ dans v0.10.0 (plus du commit 3d23a708c2, postérieur à
v0.3.0) et n'est qu'un REPLI :
- l'arbre des menus reste celui de v0.3.0 (l'écran y insère lui-même les entrées de 0.10 : INSERTIONS_M7/M8) ;
- un libellé français déjà présent dans le menus.json en place est GARDÉ, même si l'amont dit autre chose
  (l'écart est consigné dans `ecarts_amont`) : rien de ce que l'écran affiche ne change en douce ;
- `repli` : les commandes du moteur épinglé absentes de l'arbre (registre capturé du vrai binaire,
  backend/tests/photocraft_commandes_<version>.json), avec le libellé anglais du moteur et, quand le fr.tsv l'a,
  sa traduction. L'écran ne s'en sert qu'après ses propres libellés (mod-libelles.js).

Usage : python scripts/photocraft_catalogue.py <sources v0.3.0> --fr-tsv <fr.tsv de v0.10.0>
                                               [--commandes <registre .json>] [--sortie <menus.json>]
"""
import hashlib, json, pathlib, re, sys

TAG_FR = "v0.10.0"
COMMIT_FR = "8407d9ccb1"                                   # commit du tag v0.10.0
BLOB_FR = "4a819b0e1b15b2ed7f6fc2625895be1d02e46cf4"

RACINE = pathlib.Path(__file__).resolve().parent.parent
SORTIE = RACINE / "frontend" / "photolab" / "donnees" / "menus.json"
MANIFESTE = RACINE / "vendor" / "photocraft.json"
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


def garder(entrees: list, menus: dict, ancien: dict):
    """Nos libellés d'abord : le français du menus.json en place l'emporte sur l'amont (entrée par id, menu par nom).
    Rend la liste des écarts {id|menu, garde, amont}."""
    ecarts = []
    vieux = {e["id"]: e for e in (ancien or {}).get("entrees", []) if e.get("id")}
    for e in entrees:
        v = vieux.get(e.get("id"))
        if v and v.get("libelle_fr") and v["libelle_fr"] != e["libelle_fr"]:
            ecarts.append({"id": e["id"], "garde": v["libelle_fr"], "amont": e["libelle_fr"]})
            e["libelle_fr"] = v["libelle_fr"]
    for nom, fr in ((ancien or {}).get("menus_fr") or {}).items():
        if nom in menus and fr and fr != menus[nom]:
            ecarts.append({"menu": nom, "garde": fr, "amont": menus[nom]})
            menus[nom] = fr
    return ecarts


def repli(commandes: list, ids_arbre: set, texte: dict, par_id: dict) -> dict:
    """Commandes du moteur hors de l'arbre : libellé anglais du moteur, français du fr.tsv s'il existe. Un libellé qui
    nomme Photoshop (« Photoshop Step ») est écarté : l'écran a le sien (D8)."""
    r = {}
    for c in commandes:
        cid, en = c.get("id"), str(c.get("label") or "").strip()
        if not cid or cid in ids_arbre or cid in r or not en or "Photoshop" in en:
            continue
        fr = par_id.get(cid) or texte.get(en)
        r[cid] = {"libelle_en": en, **({"libelle_fr": fr} if fr and "Photoshop" not in fr else {})}
    return dict(sorted(r.items()))


def main(args) -> int:
    global SORTIE
    args = list(args)
    opts = {}
    for cle in ("--fr-tsv", "--sortie", "--commandes"):
        if cle in args:
            i = args.index(cle)
            opts[cle] = args[i + 1]
            del args[i:i + 2]
    if len(args) != 1 or "--fr-tsv" not in opts:
        print("Usage : photocraft_catalogue.py <sources v0.3.0> --fr-tsv <fr.tsv de v0.10.0> [--commandes <registre>] "
              "[--sortie <menus.json>]")
        return 2
    if "--sortie" in opts:
        SORTIE = pathlib.Path(opts["--sortie"]).resolve()
    src = pathlib.Path(args[0])
    tsv = pathlib.Path(opts["--fr-tsv"])
    # Le français est épinglé par son empreinte git : celui du tag v0.10.0, jamais « celui qui traîne ». Calculée sur
    # les fins de ligne LF, comme git (une extraction Windows peut l'avoir passé en CRLF).
    empreinte = blob_git(tsv.read_bytes().replace(b"\r\n", b"\n"))
    if empreinte != BLOB_FR:
        print(f"Refus : fr.tsv a l'empreinte git {empreinte}, attendue {BLOB_FR} ({TAG_FR}, commit {COMMIT_FR}).")
        return 1
    version = json.loads(MANIFESTE.read_text("utf-8"))["version"]
    reg = pathlib.Path(opts.get("--commandes") or RACINE / "backend" / "tests" / f"photocraft_commandes_{version}.json")
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
    ancien = json.loads(SORTIE.read_text("utf-8")) if SORTIE.is_file() else {}
    ecarts = garder(entrees, menus, ancien)
    rep = repli(json.loads(reg.read_text("utf-8")), {e["id"] for e in entrees if e.get("id")}, texte, par_id)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps({"source": "storytold/photocraft v0.3.0 crates/ui-egui/src/menu_catalog.rs",
                                  "source_fr": f"storytold/photocraft {TAG_FR} (commit {COMMIT_FR}) "
                                               f"crates/ui-egui/src/i18n/fr.tsv (blob {BLOB_FR[:8]}), traduction "
                                               f"française de l'amont, MIT OR Apache-2.0 : repli seulement, les "
                                               f"libellés déjà en place restent prioritaires",
                                  "source_repli": f"commandes du moteur photocraft {version} (engine.commands, "
                                                  f"{reg.name}) absentes de l'arbre ; libelle_fr = fr.tsv {TAG_FR}",
                                  "licence": "MIT OR Apache-2.0", "menus_fr": menus, "remplacements": remplacements,
                                  "ecarts_amont": ecarts, "entrees": entrees, "repli": rep},
                                 ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(f"{len(entrees)} lignes ({sum(1 for e in entrees if e.get('separateur'))} séparateurs), "
          f"{len(remplacements)} remplacements D8, {len(ecarts)} écarts amont gardés, {len(rep)} commandes en repli "
          f"({sum(1 for v in rep.values() if 'libelle_fr' in v)} traduites) -> {SORTIE}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
