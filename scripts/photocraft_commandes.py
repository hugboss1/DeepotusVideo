"""Capture le registre des commandes du VRAI moteur photocraft (t250, Photolab M1, 20/10/2026).

Lance `photocraft-cli serve` (stdio, racines d'automatisation dans un dossier temporaire vide), demande
`engine.commands` sans document ouvert, et écrit la réponse telle quelle — clés triées, indentation 2, UTF-8 — dans
backend/tests/photocraft_commandes_<version>.json. Rejoué sur le moteur 0.3.0, il redonne À L'OCTET (fins de ligne
mises à part) le fichier capturé à la main en t138 : c'est le contrôle du script.

Usage : python scripts/photocraft_commandes.py [--manifeste <vendor/photocraft-X.json>] [--cli <photocraft-cli.exe>]
                                               [--sortie <fichier.json>]
  --cli : un binaire ailleurs que vendor/ (ex. l'installation) ; sa version doit être celle du manifeste.
"""
import json, pathlib, subprocess, sys, tempfile

RACINE = pathlib.Path(__file__).resolve().parent.parent
MANIFESTE = RACINE / "vendor" / "photocraft.json"


def _arg(args, nom, defaut=None):
    return args[args.index(nom) + 1] if nom in args else defaut


def capturer(cli: pathlib.Path, delai: float = 120) -> list:
    with tempfile.TemporaryDirectory() as d:
        p = subprocess.Popen([str(cli), "serve", "--automation-read-root", d, "--automation-write-root", d],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            p.stdin.write((json.dumps({"id": 1, "method": "engine.commands", "params": {}}) + "\n").encode("utf-8"))
            p.stdin.flush()
            ligne = p.stdout.readline()
        finally:
            p.stdin.close()
            try:
                p.wait(timeout=delai)
            except subprocess.TimeoutExpired:
                p.kill()
    rep = json.loads(ligne)
    if not rep.get("ok"):
        raise RuntimeError(f"engine.commands refusé : {rep.get('error')}")
    res = rep["result"]
    return res if isinstance(res, list) else res["commands"]


def version_cli(cli: pathlib.Path) -> str:
    r = subprocess.run([str(cli), "--version"], capture_output=True, text=True, encoding="utf-8", timeout=60)
    return (r.stdout or r.stderr).strip()


def main(args) -> int:
    m = json.loads(pathlib.Path(_arg(args, "--manifeste", MANIFESTE)).read_text("utf-8"))
    if "--cli" in args:
        cli = pathlib.Path(_arg(args, "--cli"))
    else:
        trouves = sorted((RACINE / m["binaire"]["dossier"]).rglob(m["binaire"]["cli"]))
        if not trouves:
            print(f"moteur {m['version']} absent : python scripts/vendor_photocraft.py", file=sys.stderr)
            return 1
        cli = trouves[0]
    v = version_cli(cli)
    if m["version"] not in v.split():
        print(f"{cli} annonce « {v} », le manifeste dit {m['version']} : rien n'est écrit", file=sys.stderr)
        return 1
    liste = capturer(cli)
    sortie = pathlib.Path(_arg(args, "--sortie", RACINE / "backend" / "tests" / f"photocraft_commandes_{m['version']}.json"))
    sortie.write_text(json.dumps(liste, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(liste)} commandes ({v}) -> {sortie}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
