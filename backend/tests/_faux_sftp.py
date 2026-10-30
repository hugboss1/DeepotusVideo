# -*- coding: utf-8 -*-
"""Faux client `sftp.exe` des bancs t378/t379 (aucun réseau). Appelé par un .cmd posé par le banc
(DZ_SFTP_EXE). Il rejoue le lot `-b` sur un dossier local qui joue le serveur (FAUX_SFTP_RACINE) et note ce qu'il a
reçu dans FAUX_SFTP_JOURNAL (une ligne JSON par appel : arguments, commandes, variables d'environnement vues).

Comme OpenSSH : si FAUX_SFTP_MDP est posé, le serveur EXIGE ce mot de passe, lu par le programme SSH_ASKPASS (forcé
par SSH_ASKPASS_REQUIRE=force) — et `BatchMode=no` doit précéder `-b`, sinon aucune invite n'est permise. L'hôte
« injoignable.test » ne se résout pas. `-df .` rend une ligne de df (Kio).
"""
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

args = sys.argv[1:]
env = dict(os.environ)
racine = Path(env["FAUX_SFTP_RACINE"])
journal = {"args": args, "env": sorted(env), "commandes": []}


def finir(code, texte=""):
    with open(env["FAUX_SFTP_JOURNAL"], "a", encoding="utf-8") as f:
        f.write(json.dumps(journal, ensure_ascii=False) + "\n")
    if texte:
        sys.stderr.write(texte + "\n")
    sys.exit(code)


lot = Path(args[args.index("-b") + 1])
journal["commandes"] = lot.read_text(encoding="utf-8").splitlines()
cible = args[args.index("--") + 1]
if cible.endswith("@injoignable.test"):
    finir(255, "ssh: Could not resolve hostname injoignable.test: Name or service not known")
attendu = env.get("FAUX_SFTP_MDP")
if attendu:
    av = [i for i, a in enumerate(args) if a == "BatchMode=no"]
    if not av or av[0] > args.index("-b") or env.get("SSH_ASKPASS_REQUIRE") != "force" or not env.get("SSH_ASKPASS"):
        finir(255, "user@host: Permission denied (publickey,password).")
    lu = subprocess.run([env["SSH_ASKPASS"], "Password:"], capture_output=True, text=True, shell=False).stdout
    journal["askpass_lu_ok"] = lu.rstrip("\r\n") == attendu
    if lu.rstrip("\r\n") != attendu:
        finir(255, "user@host: Permission denied (publickey,password).")
    if env.get("FAUX_SFTP_BAVARD"):                     # un serveur bavard qui recopie ce qu'il a reçu
        finir(1, "debug: secret recu " + lu.rstrip("\r\n"))
ici = racine


def distant(p):
    """Un chemin distant : absolu (/…) depuis la racine du faux serveur, sinon depuis le dossier courant."""
    return racine / p.lstrip("/") if p.startswith("/") else ici / p


for ligne in journal["commandes"]:
    tolere = ligne.startswith("-")
    mots = shlex.split(ligne.lstrip("-"), posix=True)
    cmd, a = mots[0], mots[1:]
    try:
        if cmd == "cd":
            d = distant(a[0])
            if not d.is_dir():
                raise OSError(f'Can\'t change directory: "{a[0]}"')
            ici = d
        elif cmd == "put":
            if not distant(a[1]).parent.is_dir():
                raise OSError(f'dest open "{a[1]}": No such file or directory')
            shutil.copyfile(a[0], distant(a[1]))
        elif cmd == "get":
            shutil.copyfile(distant(a[0]), a[1])
        elif cmd == "rm":
            distant(a[0]).unlink()
        elif cmd == "mkdir":
            distant(a[0]).mkdir()
        elif cmd == "ls":
            options = [x for x in a if x.startswith("-")]
            cible = distant(next((x for x in a if not x.startswith("-")), "."))
            if not cible.is_dir():
                raise OSError(f'Can\'t ls: "{cible.name}" not found')
            for p in sorted(cible.iterdir()):
                if "-ln" in options or "-l" in options:      # comme OpenSSH : type, liens, uid, gid, taille, date, nom
                    print(f"{'d' if p.is_dir() else '-'}rw-r--r--    1 1000     1000     {p.stat().st_size:>9} "
                          f"Oct 30 03:17 {p.name}")
                else:
                    print(p.name)
        elif cmd == "df":
            print("        Size         Used        Avail       (root)    %Capacity")
            print("     1000000       400000       600000       600000          40%")
        else:
            raise OSError(f"Invalid command {cmd}")
    except OSError as ex:
        if not tolere:
            finir(1, str(ex))
finir(0)
