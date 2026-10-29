# -*- coding: utf-8 -*-
"""t345 (29/10/2026) — banc de MUTATIONS du serveur MCP : casser → rouge → remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`). Il se lance À LA MAIN, depuis backend/ :
    & $PY tests/mutations_mcp.py          # toutes
    & $PY tests/mutations_mcp.py 0 3      # celles-là
Chaque mutation modifie UN fichier source, lance tests/test_mcp_serveur.py dans un processus neuf, vérifie que les
lignes déclarées rougissent, puis remet le fichier À L'OCTET (copie faite AVANT, comparaison APRÈS).
"""
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
BANC = "tests/test_mcp_serveur.py"
PONT = "backend/app/services/mcp_pont.py"
ROUTES = "backend/app/api/mcp_routes.py"
STDIO = "backend/app/mcp_stdio.py"
BOITES = "backend/app/services/agent_boites.py"

# (fichier, ancien, nouveau, lignes attendues rouges (préfixes))
M = [
    # 0 — le filtre de l'agent mcp tombe : écritures et cartes de conversation deviennent visibles
    (BOITES, 'FILTRES = {"mcp": _permis_mcp}', 'FILTRES = {}', ["2.8", "6.3"]),
    # 1 — plus de masquage : la clé du coffre et le chemin local sortent
    (PONT, "    return recette_export.nettoyer(v)", "    return v", ["4.1", "4.2", "4.3", "4.4", "4.5"]),
    # 2 — « lancer » dépense : il saute l'attente et passe directement « lancee »
    (PONT, '        d = _transition(jeton, ("devis",), "en_attente",', '        d = _transition(jeton, ("devis",), "lancee",',
     ["3.5", "3.9"]),
    # 3 — le client MCP peut faire avancer la demande : la garde d'Origin des gestes de l'écran disparaît
    (ROUTES, '    if not h or h not in (_HOTES_ECRAN | {APP_HOSTNAME}):', '    if False:', ["2.4", "3.11", "3.12"]),
    # 4 — serveur actif par défaut
    (PONT, '    return bool(_lire_json(dossier() / "reglages.json", {}).get("actif") is True)',
     '    return bool(_lire_json(dossier() / "reglages.json", {"actif": True}).get("actif", True))', ["2.1", "2.2", "2.3"]),
    # 5 — le client stdio n'a plus de liste blanche de chemins
    (STDIO, '    if chemin not in CHEMINS:', '    if False:', ["1.23"]),
    # 6 — le client stdio écrit un journal sur stdout
    (STDIO, '        sys.stderr.write(f"[deepotus-mcp] {texte}\\n")', '        sys.stdout.write(f"[deepotus-mcp] {texte}\\n")',
     ["1.2", "1.15"]),
    # 7 — le journal garde les valeurs des arguments
    (PONT, '"arguments": sorted(str(k)[:40] for k in args)[:20]', '"arguments": args', ["4.6"]),
]


def rouges(sortie: str) -> set:
    return {m.group(1) for m in re.finditer(r"FAIL\s+([0-9]+\.[0-9]+[a-z]?)", sortie)}


def jouer(i: int) -> bool:
    f, ancien, nouveau, attendues = M[i]
    p = R / f
    avant = p.read_bytes()
    texte = avant.decode("utf-8")
    nl = "\r\n" if "\r\n" in texte else "\n"
    a, n = ancien.replace("\n", nl), nouveau.replace("\n", nl)
    if texte.count(a) != 1:
        print(f"[{i}] ANCRE x{texte.count(a)} dans {f}")
        return False
    try:
        p.write_bytes(texte.replace(a, n, 1).encode("utf-8"))
        r = subprocess.run([sys.executable, BANC], cwd=R / "backend", capture_output=True, timeout=900,
                           env={**__import__("os").environ, "PYTHONUTF8": "1"})
        sortie = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
    finally:
        p.write_bytes(avant)
    assert p.read_bytes() == avant, f"{f} pas remis à l'octet"
    vus = rouges(sortie)
    manque = [x for x in attendues if x not in vus]
    plante = r.returncode != 0 and not vus
    bon = r.returncode != 0 and (not manque or plante)
    print(f"[{i}] {'ROUGE' if bon else 'VERT (mutation survivante)'} — attendues {attendues}, rouges {sorted(vus)[:12]}"
          + (" (le banc s'arrête sur une exception)" if plante else ""))
    return bon


if __name__ == "__main__":
    choix = [int(a) for a in sys.argv[1:]] or list(range(len(M)))
    res = [jouer(i) for i in choix]
    print(f"\n{sum(res)}/{len(res)} mutations tuées")
    sys.exit(0 if all(res) else 1)
