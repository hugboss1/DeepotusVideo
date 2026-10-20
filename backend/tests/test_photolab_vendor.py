# -*- coding: utf-8 -*-
"""t136 (Photolab P1) — le moteur photocraft est ÉPINGLÉ : manifeste versionné, empreinte vérifiée AVANT d'extraire,
binaires jamais versionnés.
Run : & $PY tests/test_photolab_vendor.py   (depuis backend/)"""
import hashlib, io, json, pathlib, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8")
RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RACINE / "scripts"))
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


M = json.loads((RACINE / "vendor" / "photocraft.json").read_text("utf-8"))
b = M.get("binaire", {})
check("1 manifeste : version 0.3.0, tag v0.3.0, licence MIT OR Apache-2.0",
      M.get("version") == "0.3.0" and M.get("tag") == "v0.3.0" and M.get("licence") == "MIT OR Apache-2.0", M)
check("2 archive Windows épinglée (nom, taille, sha256 de la release)",
      b.get("archive") == "photocraft-0.3.0-windows-x64-portable.zip" and b.get("taille") == 65251740
      and b.get("sha256") == "9997f7df3a6f0717b46bb0f503b3d920c3beedeb9e9c4e1ff2ef3b8671acd47e", b)

import vendor_photocraft as V                                  # noqa: E402

with tempfile.TemporaryDirectory() as t:
    t = pathlib.Path(t)
    z = io.BytesIO()
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("photocraft-0.3.0/photocraft-cli.exe", b"MZ faux")
        f.writestr("photocraft-0.3.0/portable.txt", b"")
    octets = z.getvalue()
    arch = t / "a.zip"
    arch.write_bytes(octets)
    bon = hashlib.sha256(octets).hexdigest()
    try:
        V.verifier(arch, "0" * 64, len(octets))
        refuse = False
    except V.EmpreinteFausse:
        refuse = True
    check("3 une empreinte fausse est REFUSÉE avant toute extraction", refuse and not (t / "x").exists())
    try:
        V.verifier(arch, bon, len(octets) + 1)
        refuse_taille = False
    except V.EmpreinteFausse:
        refuse_taille = True
    check("4 une taille fausse est refusée aussi", refuse_taille)
    V.verifier(arch, bon, len(octets))
    cible = t / "x"
    cli = V.extraire(arch, cible)
    check("5 extraction : l'arbre de l'archive est gardé, le CLI est trouvé où qu'il soit",
          cli == cible / "photocraft-0.3.0" / "photocraft-cli.exe" and cli.read_bytes() == b"MZ faux", cli)
    z2 = io.BytesIO()
    with zipfile.ZipFile(z2, "w") as f:
        f.writestr("../evade.exe", b"x")
    (t / "b.zip").write_bytes(z2.getvalue())
    try:
        V.extraire(t / "b.zip", t / "y")
        evade = True
    except V.EmpreinteFausse:
        evade = False
    check("6 une entrée qui sortirait du dossier (../) est refusée", not evade and not (t / "evade.exe").exists())

# De bout en bout : main() ne détruit JAMAIS une installation valide avant que la nouvelle soit complète.
# MANIFESTE pointe sur un manifeste temporaire dont binaire.dossier est ABSOLU (RACINE / absolu = absolu en pathlib).
with tempfile.TemporaryDirectory() as t:
    t = pathlib.Path(t)

    def archive(nom, avec_cli):
        z = io.BytesIO()
        with zipfile.ZipFile(z, "w") as f:
            if avec_cli:
                f.writestr("pc/photocraft-cli.exe", b"MZ neuf")
            f.writestr("pc/portable.txt", b"")
        p = t / nom
        p.write_bytes(z.getvalue())
        return p, hashlib.sha256(z.getvalue()).hexdigest(), len(z.getvalue())

    dossier = t / "vendor" / "photocraft-9.9.9"

    def installer_ancienne():
        shutil_rm = __import__("shutil").rmtree
        if dossier.exists():
            shutil_rm(dossier)
        dossier.mkdir(parents=True)
        (dossier / "marqueur.txt").write_text("ancienne")

    def manifeste(sha, taille):
        mf = t / "m.json"
        mf.write_text(json.dumps({"binaire": {"sha256": sha, "taille": taille, "dossier": str(dossier)},
                                  "version": "9.9.9", "tag": "v9", "depot": "x/y"}), "utf-8")
        V.MANIFESTE = mf

    tmp = dossier.with_name(dossier.name + ".tmp")
    a_bon, sha_bon, n_bon = archive("bon.zip", True)
    a_sans, sha_sans, n_sans = archive("sans.zip", False)
    # (a) empreinte fausse
    installer_ancienne(); manifeste("0" * 64, n_bon)
    try:
        V.main(["--archive", str(a_bon)]); leve = False
    except V.EmpreinteFausse:
        leve = True
    check("3a empreinte fausse : refus ET l'ancienne installation est intacte",
          leve and (dossier / "marqueur.txt").exists() and not tmp.exists())
    # (b) extraction qui échoue (pas de CLI)
    installer_ancienne(); manifeste(sha_sans, n_sans)
    try:
        V.main(["--archive", str(a_sans)]); leve = False
    except V.EmpreinteFausse:
        leve = True
    check("3b extraction ratée : refus, ancienne installation intacte, aucun .tmp qui traîne",
          leve and (dossier / "marqueur.txt").exists() and not tmp.exists())
    # (c) archive correcte
    installer_ancienne(); manifeste(sha_bon, n_bon)
    V.main(["--archive", str(a_bon)])
    check("3c archive correcte : l'ancienne est remplacée, le CLI est dans le dossier, aucun .tmp",
          not (dossier / "marqueur.txt").exists() and (dossier / "pc" / "photocraft-cli.exe").read_bytes() == b"MZ neuf"
          and not tmp.exists())
V.MANIFESTE = RACINE / "vendor" / "photocraft.json"

gi = (RACINE / ".gitignore").read_text("utf-8")
check("7 les binaires ne sont jamais versionnés (.gitignore vendor/photocraft-*/)", "vendor/photocraft-*/" in gi)

# ── t250 (Photolab M1) : la version CANDIDATE 0.10.0 cohabite avec l'épinglée ; une seule source de version ──
C = json.loads((RACINE / "vendor" / "photocraft-0.10.0.json").read_text("utf-8"))
cb = C.get("binaire", {})
check("8 manifeste candidat : 0.10.0, tag v0.10.0, archive officielle (taille, sha256 recoupés le 20/10)",
      C.get("version") == "0.10.0" and C.get("tag") == "v0.10.0" and C.get("licence") == "MIT OR Apache-2.0"
      and cb.get("archive") == "photocraft-0.10.0-windows-x64-portable.zip" and cb.get("taille") == 84828713
      and cb.get("sha256") == "66b7e47d66589eb6947c8d7417c80fa44621cf83823ffdc47f42024eb03bd5d2"
      and cb.get("url") == "https://github.com/storytold/photocraft/releases/download/v0.10.0/" + cb.get("archive", "")
      and cb.get("dossier") == "vendor/photocraft-0.10.0", cb)
cf = C.get("fichiers") or {}
check("9 manifeste candidat : les 9 fichiers de l'archive, chacun avec taille et sha256",
      len(cf) == 9 and all(k.startswith("photocraft-0.10.0-windows-x64-portable/") for k in cf)
      and all(len(v.get("sha256", "")) == 64 and v.get("taille", 0) > 0 for v in cf.values())
      and {"photocraft-cli.exe", "photocraft.exe", "portable.txt"} <= {k.rsplit("/", 1)[1] for k in cf}, sorted(cf))
check("10 --manifeste choisit le manifeste candidat, sans option c'est l'épinglé",
      V.manifeste(["--manifeste", "x.json"]) == pathlib.Path("x.json") and V.manifeste([]) == V.MANIFESTE)

sys.path.insert(0, str(RACINE / "backend"))
from app.services import photolab_moteur as PM                 # noqa: E402
check("11 le pont lit SA version dans vendor/photocraft.json (une seule source)", PM.VERSION == M.get("version"),
      (PM.VERSION, M.get("version")))
with tempfile.TemporaryDirectory() as t:
    t = pathlib.Path(t)
    (t / "vendor").mkdir()
    (t / "vendor" / "photocraft.json").write_text(json.dumps({"version": "9.9.9"}), "utf-8")
    lue = PM._version_epinglee(t)
    (t / "vendor" / "photocraft.json").write_text("{pas du json", "utf-8")
    illisible = PM._version_epinglee(t)
check("12 version lue du manifeste ; manifeste illisible : la dernière épinglée connue (le backend démarre)",
      lue == "9.9.9" and illisible == "0.3.0", (lue, illisible))

# verifier_vendor --manifeste --ecrire réécrit le manifeste CANDIDAT, jamais l'épinglé (défaut vu en t250).
import verifier_vendor as VV                                    # noqa: E402
epingle_avant = (RACINE / "vendor" / "photocraft.json").read_bytes()
with tempfile.TemporaryDirectory() as t:
    t = pathlib.Path(t)
    (t / "moteur" / "pc").mkdir(parents=True)
    (t / "moteur" / "pc" / "portable.txt").write_bytes(b"x")
    mf = t / "cand.json"
    mf.write_text(json.dumps({"version": "9.9.9", "binaire": {"dossier": str(t / "moteur"), "cli": "c.exe", "app": "a.exe"}}), "utf-8")
    VV.main([str(t / "moteur"), "--manifeste", str(mf), "--ecrire"])
    ecrit = json.loads(mf.read_text("utf-8")).get("fichiers") or {}
check("10b --manifeste --ecrire : le candidat reçoit ses fichiers, vendor/photocraft.json reste à l'octet",
      list(ecrit) == ["pc/portable.txt"] and (RACINE / "vendor" / "photocraft.json").read_bytes() == epingle_avant, ecrit)

R10 = json.loads((RACINE / "backend" / "tests" / "photocraft_commandes_0.10.0.json").read_text("utf-8"))
R03 = json.loads((RACINE / "backend" / "tests" / "photocraft_commandes_0.3.0.json").read_text("utf-8"))
ids10 = [c["id"] for c in R10]
check("13 registre 0.10.0 capturé du vrai binaire : 918 commandes, ids uniques, toutes celles de 0.3.0 présentes",
      len(R10) == 918 and len(set(ids10)) == 918 and {c["id"] for c in R03} <= set(ids10), len(R10))
# keywords n'est servi que là où l'amont en déclare (1 commande sur 918 au 20/10) : il est gardé, pas exigé.
check("14 registre 0.10.0 : champs nouveaux du moteur gardés tels quels (disabledReason, needsDocument partout)",
      all({"id", "label", "menu", "params", "shortcut", "enabled", "needsDocument", "disabledReason"} <= set(c) for c in R10)
      and any("keywords" in c for c in R10))

# Le script de capture s'éprouve sur le VRAI moteur 0.3.0 : il doit redonner à l'octet (fins de ligne mises à part) le
# registre capturé à la main en t138. Binaire : PHOTOCRAFT_CLI, sinon vendor/, sinon l'installation.
import os, glob                                                 # noqa: E402
import photocraft_commandes as PCAP                             # noqa: E402
cands = [os.environ.get("PHOTOCRAFT_CLI", "")] + sorted(glob.glob(str(RACINE / "vendor" / "photocraft-0.3.0" / "*" / "photocraft-cli.exe"))) \
    + sorted(glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "DeepotusVideoGen", "vendor", "photocraft-0.3.0", "*", "photocraft-cli.exe")))
cli03 = next((pathlib.Path(c) for c in cands if c and pathlib.Path(c).is_file() and "0.3.0" in PCAP.version_cli(pathlib.Path(c)).split()), None)
if cli03 is None:
    check("15 photocraft-cli 0.3.0 trouvé pour éprouver la capture (sinon cette section est rouge)", False)
else:
    with tempfile.TemporaryDirectory() as t:
        sortie = pathlib.Path(t) / "c.json"
        code = PCAP.main(["--cli", str(cli03), "--sortie", str(sortie)])
        attendu = (RACINE / "backend" / "tests" / "photocraft_commandes_0.3.0.json").read_bytes().replace(b"\r\n", b"\n")
        check("15 la capture rejouée sur le vrai 0.3.0 redonne le registre de t138 à l'octet",
              code == 0 and sortie.read_bytes() == attendu)
    with tempfile.TemporaryDirectory() as t:
        mf = pathlib.Path(t) / "m.json"
        mf.write_text(json.dumps({"version": "0.10.0", "binaire": {"dossier": "x", "cli": "photocraft-cli.exe"}}), "utf-8")
        refus = PCAP.main(["--manifeste", str(mf), "--cli", str(cli03), "--sortie", str(pathlib.Path(t) / "c.json")])
        check("16 un binaire d'une autre version que le manifeste : rien n'est écrit",
              refus == 1 and not (pathlib.Path(t) / "c.json").exists())

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
