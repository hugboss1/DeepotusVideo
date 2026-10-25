# -*- coding: utf-8 -*-
"""Banc de mutations du paquet agent du telephone (L4.1 T1) : casser -> rouge -> remettre.

PAS UN TEST : son nom ne commence pas par `test_`. Il se lance A LA MAIN, depuis le depot :

    python backend/tests/mutations_paquet_telephone.py            # toutes
    python backend/tests/mutations_paquet_telephone.py 2 3        # celles-la

Meme mecanique que mutations_appairage.py : chaque source est copiee AVANT, mutee, le banc lu (etiquettes FAIL), puis
remise A L'OCTET PRES (assertion sha256, meme en cas d'exception). Une VERTE est une assertion qui manque.
"""
import hashlib, os, pathlib, re, subprocess, sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
AIDE = "backend/app/services/agent_aide.py"
ROUTES = "backend/app/api/agent_campagnes_routes.py"
B = "test_agent_paquet_telephone.py"

# (fichier, ancre = UNE ligne exacte, remplacement, etiquettes attendues rouges, intention)
M = [
    (AIDE, "                if x.get(\"etat\") != \"retire\":", "                if True:",
     ["p2h"], "le catalogue garde les fiches retirees"),
    (ROUTES, "        return Response(status_code=304, headers={\"ETag\": p[\"version\"]})",
     "        return JSONResponse(p, headers={\"ETag\": p[\"version\"]})",
     ["p5b", "p5c"], "If-None-Match egal rend 200 au lieu de 304"),
    (ROUTES, "_CHAMPS_FICHE = (\"ecran\", \"type\", \"libelle\", \"infobulle\", \"role\", \"synonymes\", \"guide\")",
     "_CHAMPS_FICHE = (\"ecran\", \"type\", \"libelle\", \"infobulle\", \"role\", \"synonymes\", \"guide\", \"localisateur\")",
     ["p2c", "p2d"], "la fiche garde le localisateur"),
    (ROUTES, "OUTILS_TELEPHONE = (\"chercher_app\", \"lire_espace\", \"lire_document\", \"proposer_porte\", \"deviser_generation\")",
     "OUTILS_TELEPHONE = (\"chercher_app\", \"lire_espace\", \"lire_document\", \"proposer_porte\", \"deviser_generation\", \"ecrire_dossier\")",
     ["p4a"], "un outil d'ecriture de plus dans le paquet"),
    (ROUTES, "        systeme={r: AC.systeme_pour(r, espace_id, langue) for r in ROLES_TELEPHONE},",
     "        systeme={r: AC.systeme_pour(r, None, langue) for r in ROLES_TELEPHONE},",
     ["p3b", "p3c"], "le systeme du paquet ignore l'espace"),
    (ROUTES, "    p.pop(\"version\")", "    p.pop(\"version\")\n    p.pop(\"systeme\")",
     ["p3a"], "le systeme sort de la version (et du paquet)"),
    (ROUTES, "    if not espace_id:   # le téléphone ne connaît pas l'espace actif : le paquet porte celui du PC (spec §6.1)",
     "    if False:", ["p8a", "p8b", "p8c"], "sans espace_id, le paquet n'a pas l'espace actif"),
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
