"""Fournit le moteur du Photolab : photocraft-cli 0.3.0, ÉPINGLÉ (t136, Photolab P1, 07/10/2026).

Lit vendor/photocraft.json, télécharge l'archive Windows de la release officielle (gh si présent, sinon urllib),
vérifie taille et sha256 AVANT d'extraire, extrait dans vendor/photocraft-0.3.0/ (jamais versionné). Une empreinte
fausse arrête tout : rien n'est extrait. Une entrée d'archive qui sortirait du dossier (../, chemin absolu) est refusée.

Usage : python scripts/vendor_photocraft.py [--archive <zip déjà téléchargé>]
"""
import hashlib, json, pathlib, shutil, subprocess, sys, tempfile, zipfile

RACINE = pathlib.Path(__file__).resolve().parent.parent
MANIFESTE = RACINE / "vendor" / "photocraft.json"


class EmpreinteFausse(RuntimeError):
    pass


def verifier(archive: pathlib.Path, sha256: str, taille: int) -> None:
    octets = archive.read_bytes()
    if len(octets) != taille:
        raise EmpreinteFausse(f"{archive.name} : {len(octets)} octets, {taille} attendus — rien n'est extrait")
    vu = hashlib.sha256(octets).hexdigest()
    if vu != sha256:
        raise EmpreinteFausse(f"{archive.name} : sha256 {vu}, {sha256} attendu — rien n'est extrait")


def extraire(archive: pathlib.Path, cible: pathlib.Path) -> pathlib.Path:
    """Extrait l'archive sous `cible` (arbre gardé) et rend le chemin de photocraft-cli.exe."""
    cible = cible.resolve()
    with zipfile.ZipFile(archive) as z:
        for nom in z.namelist():
            dest = (cible / nom).resolve()
            if dest != cible and cible not in dest.parents:
                raise EmpreinteFausse(f"entrée hors du dossier refusée : {nom}")
        cible.mkdir(parents=True, exist_ok=True)
        z.extractall(cible)
    trouves = sorted(cible.rglob("photocraft-cli.exe"))
    if not trouves:
        raise EmpreinteFausse("photocraft-cli.exe absent de l'archive")
    return trouves[0]


def telecharger(m: dict, dossier: pathlib.Path) -> pathlib.Path:
    b = m["binaire"]
    dest = dossier / b["archive"]
    if shutil.which("gh"):
        try:
            subprocess.run(["gh", "release", "download", m["tag"], "-R", m["depot"], "-p", b["archive"], "-D",
                            str(dossier), "--clobber"], check=True)
            return dest
        except subprocess.CalledProcessError:
            pass  # gh présent mais non connecté : on retombe sur urllib (le sha256 garde les deux chemins)
    import urllib.request
    try:
        import truststore
        truststore.inject_into_ssl()
    except ImportError:
        pass
    with urllib.request.urlopen(b["url"], timeout=600) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)
    return dest


def main(args) -> int:
    m = json.loads(MANIFESTE.read_text("utf-8"))
    b = m["binaire"]
    cible = RACINE / b["dossier"]
    with tempfile.TemporaryDirectory() as t:
        archive = pathlib.Path(args[args.index("--archive") + 1]) if "--archive" in args else telecharger(m, pathlib.Path(t))
        verifier(archive, b["sha256"], b["taille"])
        # Jamais d'effacement avant que la nouvelle installation soit complète : on extrait à côté, puis on échange.
        tmp = cible.with_name(cible.name + ".tmp")
        if tmp.exists():
            shutil.rmtree(tmp)
        try:
            extraire(archive, tmp)
        except BaseException:
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        if cible.exists():
            shutil.rmtree(cible)
        tmp.rename(cible)
        cli = sorted(cible.rglob("photocraft-cli.exe"))[0]
    try:
        montre = cli.relative_to(RACINE)
    except ValueError:
        montre = cli
    print(f"photocraft {m['version']} vérifié (sha256 {b['sha256'][:12]}…) -> {montre}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
