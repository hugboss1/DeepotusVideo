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

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
