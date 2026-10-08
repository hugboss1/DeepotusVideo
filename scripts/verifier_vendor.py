"""Vérifie le moteur du Photolab fichier par fichier contre vendor/photocraft.json (t140, Photolab P5, 08/10/2026).

Le manifeste porte, pour chaque fichier livré par l'archive officielle, sa taille et son sha256 (`fichiers`). Un
fichier altéré, manquant ou EN TROP (une DLL glissée à côté du moteur) est un écart : code 1, écarts listés. Le dossier
`PhotoCraftData` (préférences de l'app native en mode portable) n'est pas un écart.

Le build de l'installeur l'appelle sur l'arbre PRÉPARÉ (scripts/build-installer.ps1, étape 4c) ; vendor_photocraft.py
l'utilise après chaque extraction. Il refuse aussi un moteur qui importerait le runtime C de Visual C++ (vcruntime,
msvcp, UCRT) : la 0.3.0 n'en dépend pas, l'installeur ne pose donc aucun redistribuable — une version qui en
dépendrait doit d'abord le faire poser.

Usage : python scripts/verifier_vendor.py [<dossier du moteur>] [--ecrire]
  --ecrire : (développement) réécrit `fichiers` d'après le dossier — seulement juste après une extraction vérifiée.
"""
import hashlib, json, pathlib, struct, sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
MANIFESTE = RACINE / "vendor" / "photocraft.json"
IGNORES = ("PhotoCraftData",)                    # préférences de l'app native (portable.txt)
_CRT = ("vcruntime", "msvcp", "ucrtbase", "api-ms-win-crt-", "concrt", "vccorlib")


def _ignore(rel: pathlib.PurePosixPath) -> bool:
    # le mode portable écrit PhotoCraftData À CÔTÉ de photocraft.exe, donc sous le dossier de l'archive (relevé t140)
    return any(p in IGNORES for p in rel.parts[:-1])


def empreintes(dossier) -> dict:
    """{chemin relatif en / : {taille, sha256}} de chaque fichier du dossier (hors IGNORES)."""
    dossier = pathlib.Path(dossier)
    out = {}
    for f in sorted(dossier.rglob("*")):
        if not f.is_file():
            continue
        rel = pathlib.PurePosixPath(f.relative_to(dossier).as_posix())
        if _ignore(rel):
            continue
        h = hashlib.sha256()
        with open(f, "rb") as fh:
            for bloc in iter(lambda: fh.read(1 << 20), b""):
                h.update(bloc)
        out[str(rel)] = {"taille": f.stat().st_size, "sha256": h.hexdigest()}
    return out


def comparer(attendus: dict, dossier) -> list:
    """Écarts entre le manifeste et le dossier, une phrase par fichier ; [] = conforme."""
    vus = empreintes(dossier)
    ecarts = []
    for rel, a in sorted(attendus.items()):
        v = vus.get(rel)
        if v is None:
            ecarts.append(f"{rel} : manquant")
        elif v["taille"] != a["taille"]:
            ecarts.append(f"{rel} : {v['taille']} octets, {a['taille']} attendus")
        elif v["sha256"] != a["sha256"]:
            ecarts.append(f"{rel} : sha256 {v['sha256'][:12]}…, {a['sha256'][:12]}… attendu")
    for rel in sorted(set(vus) - set(attendus)):
        ecarts.append(f"{rel} : en trop (absent de l'archive officielle)")
    return ecarts


def imports_pe(chemin) -> list:
    """DLL importées par un exécutable PE (imports + imports différés), lues sans dépendance."""
    b = pathlib.Path(chemin).read_bytes()
    pe = struct.unpack_from("<I", b, 0x3C)[0]
    nsec = struct.unpack_from("<H", b, pe + 6)[0]
    taille_opt = struct.unpack_from("<H", b, pe + 20)[0]
    opt = pe + 24
    dd = opt + (112 if struct.unpack_from("<H", b, opt)[0] == 0x20B else 96)
    sections = []
    for k in range(nsec):
        o = opt + taille_opt + 40 * k
        vs, va, rs, raw = struct.unpack_from("<IIII", b, o + 8)
        sections.append((va, max(vs, rs), raw))

    def off(rva):
        for va, n, raw in sections:
            if va <= rva < va + n:
                return rva - va + raw
        return None

    noms = []
    for idx, pas, champ in ((1, 20, 3), (13, 32, 1)):
        rva = struct.unpack_from("<I", b, dd + 8 * idx)[0]
        o = off(rva) if rva else None
        while o is not None:
            entree = struct.unpack_from("<5I", b, o)
            if not any(entree):
                break
            on = off(entree[champ])
            if on is None:
                break
            noms.append(b[on:b.index(b"\0", on)].decode("ascii", "replace"))
            o += pas
    return list(dict.fromkeys(noms))


def crt(imports) -> list:
    """Les imports qui exigeraient le redistribuable Visual C++."""
    return [n for n in imports if n.lower().startswith(_CRT)]


def main(args) -> int:
    m = json.loads(MANIFESTE.read_text("utf-8"))
    pos = [a for a in args if not a.startswith("--")]
    dossier = pathlib.Path(pos[0]) if pos else RACINE / m["binaire"]["dossier"]
    if not dossier.is_dir():
        print(f"moteur absent : {dossier}", file=sys.stderr)
        return 1
    if "--ecrire" in args:
        m["fichiers"] = empreintes(dossier)
        MANIFESTE.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"manifeste réécrit : {len(m['fichiers'])} fichiers")
        return 0
    ecarts = comparer(m.get("fichiers") or {}, dossier)
    if not m.get("fichiers"):
        ecarts.insert(0, "manifeste sans `fichiers` : rien à comparer")
    for exe in (m["binaire"]["cli"], m["binaire"]["app"]):
        for f in dossier.rglob(exe):
            dep = crt(imports_pe(f))
            if dep:
                ecarts.append(f"{f.name} : dépend du runtime Visual C++ ({', '.join(dep)}) — l'installeur ne le pose pas")
    for e in ecarts:
        print("ÉCART", e, file=sys.stderr)
    if ecarts:
        return 1
    print(f"photocraft {m['version']} conforme : {len(m['fichiers'])} fichiers, aucun runtime Visual C++ requis")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
