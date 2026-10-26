# -*- coding: utf-8 -*-
"""Banc de mutations de `GET /api/pair/moi` (L4.1 T2) : casser -> rouge -> remettre.

PAS UN TEST : son nom ne commence pas par `test_`. Il se lance A LA MAIN, depuis le depot :

    python backend/tests/mutations_pair_moi.py            # toutes
    python backend/tests/mutations_pair_moi.py 2 3        # celles-la

Meme mecanique que mutations_paquet_telephone.py : chaque source est copiee AVANT, mutee, le banc lu (etiquettes FAIL),
puis remise A L'OCTET PRES (assertion sha256, meme en cas d'exception). Une VERTE est une assertion qui manque.
"""
import hashlib, os, pathlib, re, subprocess, sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
ROUTES = "backend/app/api/routes.py"
MAIN = "backend/app/main.py"
B = "test_pair_moi.py"

# (fichier, ancre = UNE ligne exacte, remplacement, etiquettes attendues rouges, intention)
M = [
    (ROUTES, "    if not entete.strip():", "    if False:",
     ["m3"], "sans jeton, la boucle locale n'a plus son 404"),
    (ROUTES, '    return {"appareil": await _appareil_requis(request)}',
     '    return {"appareil": {**(await _appareil_requis(request)), "id": "autre"}}',
     ["m1", "m3b"], "l'id rendu n'est pas celui du jeton"),
    (MAIN, '                                            ("POST", "/api/agent/campagnes/importer"),',
     '                                            ("POST", "/api/pair/moi"), ("POST", "/api/agent/campagnes/importer"),',
     ["m4"], "la route rejoint les ecritures ouvertes"),
    (ROUTES, "    if not appareil:", "    if False:",
     ["m3c"], "un jeton invalide n'est plus refuse (boucle locale)"),
]

_FIN = re.compile(r"^\s*\d+ ok, \d+ fail\s*$", re.M)


def lire():
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    p = subprocess.run([PY, f"tests/{B}"], capture_output=True, cwd=R / "backend", timeout=900, env=env)
    txt = (p.stdout + p.stderr).decode("utf-8", "replace")
    echecs = set(re.findall(r"^\s*FAIL\s+(\S+)", txt, re.M))
    return echecs, txt, (not _FIN.search(txt) and not echecs)


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (rel, old, new, attendus, intention) in enumerate(M, 1):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        src = p.read_bytes()
        sha_avant = hashlib.sha256(src).hexdigest()
        brut = src.decode("utf-8")
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        assert "\n" not in old, (i, "ancre multi-ligne")
        assert txt.count(old) == 1, (i, rel, txt.count(old), old[:70])
        p.write_bytes(txt.replace(old, new).replace("\n", eol).encode("utf-8"))
        try:
            echecs, sortie, erreur = lire()
        finally:
            p.write_bytes(src)
            assert hashlib.sha256(p.read_bytes()).hexdigest() == sha_avant, (i, rel)
        verdict = "ERREUR" if erreur else ("ROUGE" if echecs else "VERTE")
        if erreur:
            print(sortie[-1500:], file=sys.stderr)
        manquants = [a for a in attendus if a not in echecs]
        note = f"  (rouge, mais pas sur {manquants})" if verdict == "ROUGE" and manquants else ""
        bilan.append(verdict)
        print(f"{verdict} {i} {rel} {intention} [{sorted(echecs)}]{note}")
        sys.stdout.flush()
    print(f"\n{len(bilan)} mutation(s) : {bilan.count('ROUGE')} ROUGE, {bilan.count('VERTE')} VERTE, {bilan.count('ERREUR')} ERREUR")
    return 0 if bilan and all(v == "ROUGE" for v in bilan) else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
