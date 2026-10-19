"""Fournit le navigateur du rendu motion code : chrome-headless-shell 155.0.8059.84 (Chrome for Testing), ÉPINGLÉ
(19/10/2026, relevé docs/superpowers/specs/2026-10-19-motion-code-moteur-embarque.md).

Lit vendor/chrome-headless-shell.json, télécharge l'archive win64 OFFICIELLE (storage.googleapis.com,
chrome-for-testing-public), vérifie taille et sha256 AVANT d'extraire, n'extrait que les langues du manifeste
(fr, en-US : 8 fichiers de langue sur 220, −41 Mio), revérifie chaque fichier extrait contre le manifeste, puis pose
vendor/chrome-headless-shell-<version>/ (jamais versionné). Une empreinte fausse arrête tout : rien n'est extrait. Une
entrée d'archive qui sortirait du dossier (../, chemin absolu) est refusée. L'APPLICATION ne télécharge jamais rien :
seuls ce script et le build de l'installeur (étape 4d) le font.

Usage : python scripts/vendor_chrome_headless_shell.py [--archive <zip déjà téléchargé>]
        python scripts/vendor_chrome_headless_shell.py --verifier [<dossier>]   arbre conforme ? (build, étape 4d)
        python scripts/vendor_chrome_headless_shell.py --ecrire [<dossier>]     (dev) réécrit `fichiers` — seulement
                                                                                 juste après une extraction vérifiée
        python scripts/vendor_chrome_headless_shell.py --derniere               la Stable du jour vs la version épinglée
"""
import hashlib, json, pathlib, re, shutil, struct, sys, tempfile, zipfile

RACINE = pathlib.Path(__file__).resolve().parent.parent
MANIFESTE = RACINE / "vendor" / "chrome-headless-shell.json"
CFT_JSON = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
sys.path.insert(0, str(RACINE / "scripts"))
from verifier_vendor import comparer, crt, empreintes, imports_pe   # noqa: E402


class EmpreinteFausse(RuntimeError):
    pass


def verifier(archive, sha256: str, taille: int) -> None:
    archive = pathlib.Path(archive)
    n = archive.stat().st_size
    if n != taille:
        raise EmpreinteFausse(f"{archive.name} : {n} octets, {taille} attendus — rien n'est extrait")
    h = hashlib.sha256()
    with open(archive, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    if h.hexdigest() != sha256:
        raise EmpreinteFausse(f"{archive.name} : sha256 {h.hexdigest()}, {sha256} attendu — rien n'est extrait")


def garder(nom: str, langues) -> bool:
    """Une entrée de l'archive est gardée, sauf un fichier de langue hors de `langues` (fr → fr.pak, fr_FEMININE.pak…)."""
    parties = nom.replace("\\", "/").split("/")
    if "locales" not in parties[:-1]:
        return True
    return any(re.fullmatch(re.escape(lg) + r"(_[A-Z]+)?\.pak", parties[-1]) for lg in langues)


def extraire(archive, cible, langues) -> pathlib.Path:
    """Extrait l'archive sous `cible` (arbre gardé, langues filtrées) et rend le chemin de chrome-headless-shell.exe."""
    cible = pathlib.Path(cible).resolve()
    with zipfile.ZipFile(archive) as z:
        noms = z.namelist()
        for nom in noms:                                  # tout est contrôlé AVANT d'écrire quoi que ce soit
            dest = (cible / nom).resolve()
            if dest != cible and cible not in dest.parents:
                raise EmpreinteFausse(f"entrée hors du dossier refusée : {nom}")
        cible.mkdir(parents=True, exist_ok=True)
        for nom in noms:
            if garder(nom, langues):
                z.extract(nom, cible)
    trouves = sorted(cible.rglob("chrome-headless-shell.exe"))
    if not trouves:
        raise EmpreinteFausse("chrome-headless-shell.exe absent de l'archive")
    return trouves[0]


def telecharger(url: str, dest: pathlib.Path) -> pathlib.Path:
    import urllib.request
    try:
        import truststore
        truststore.inject_into_ssl()
    except ImportError:
        pass
    with urllib.request.urlopen(url, timeout=900) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)
    return dest


def controler(m: dict, dossier: pathlib.Path) -> list:
    """Écarts de l'arbre `dossier` au manifeste (fichier altéré, manquant, en trop) + dépendance au runtime Visual C++."""
    ecarts = comparer(m.get("fichiers") or {}, dossier)
    if not m.get("fichiers"):
        ecarts.insert(0, "manifeste sans `fichiers` : rien à comparer")
    for f in dossier.rglob(m["binaire"]["exe"].split("/")[-1]):
        try:
            dep = crt(imports_pe(f))
        except (struct.error, ValueError, IndexError):
            ecarts.append(f"{f.name} : pas un exécutable Windows lisible")
            continue
        if dep:
            ecarts.append(f"{f.name} : dépend du runtime Visual C++ ({', '.join(dep)}) — l'installeur ne le pose pas")
    return ecarts


def main(args) -> int:
    m = json.loads(MANIFESTE.read_text("utf-8"))
    b = m["binaire"]
    pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--archive")]
    cible = RACINE / b["dossier"]
    if "--derniere" in args:
        import urllib.request
        with urllib.request.urlopen(CFT_JSON, timeout=60) as r:
            st = json.load(r)["channels"]["Stable"]["version"]
        print(f"épinglée {m['version']} · Stable du jour {st}" + ("" if st == m["version"] else " — à monter"))
        return 0
    if "--verifier" in args or "--ecrire" in args:
        dossier = pathlib.Path(pos[0]) if pos else cible
        if not dossier.is_dir():
            print(f"moteur absent : {dossier}", file=sys.stderr)
            return 1
        if "--ecrire" in args:
            m["fichiers"] = empreintes(dossier)
            MANIFESTE.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"manifeste réécrit : {len(m['fichiers'])} fichiers")
            return 0
        ecarts = controler(m, dossier)
        for e in ecarts:
            print("ÉCART", e, file=sys.stderr)
        if ecarts:
            return 1
        print(f"chrome-headless-shell {m['version']} conforme : {len(m['fichiers'])} fichiers, "
              "aucun runtime Visual C++ requis")
        return 0
    try:
        with tempfile.TemporaryDirectory() as t:
            if "--archive" in args:
                archive = pathlib.Path(args[args.index("--archive") + 1])
            else:
                print(f"téléchargement : {b['url']}")
                archive = telecharger(b["url"], pathlib.Path(t) / b["archive"])
            verifier(archive, b["sha256"], b["taille"])
            # Jamais d'effacement avant que la nouvelle installation soit complète : on extrait à côté, puis on échange.
            tmp = cible.with_name(cible.name + ".tmp")
            if tmp.exists():
                shutil.rmtree(tmp)
            try:
                extraire(archive, tmp, m["langues"])
                ecarts = controler(m, tmp)
                if ecarts:
                    raise EmpreinteFausse("extraction non conforme au manifeste : " + " ; ".join(ecarts[:10]))
            except BaseException:
                shutil.rmtree(tmp, ignore_errors=True)
                raise
            if cible.exists():
                shutil.rmtree(cible)
            tmp.rename(cible)
    except EmpreinteFausse as e:
        print(f"ARRÊT : {e}", file=sys.stderr)
        return 1
    print(f"chrome-headless-shell {m['version']} vérifié (sha256 {b['sha256'][:12]}…) -> "
          f"{(cible / b['exe']).relative_to(RACINE)}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
