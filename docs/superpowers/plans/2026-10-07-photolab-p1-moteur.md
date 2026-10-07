# Photolab P1 — moteur photocraft épinglé et pont backend — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** faire tourner le moteur de photocraft 0.3.0 (`photocraft-cli serve`) derrière le backend de Deepotus, avec des routes `/api/photolab/*` qui ouvrent, créent, modifient, rendent et enregistrent un document, et PROUVER que le résultat est identique à celui de photocraft lui-même — c'est la décision D1, validée par l'utilisateur le 07/10/2026.

**Architecture :** un processus `photocraft-cli serve` (JSON lignes sur stdio) par backend, démarré à la première demande, piloté par `backend/app/services/photolab_moteur.py` (une session, un verrou, un délai par requête, redémarrage s'il meurt). Le moteur ne voit qu'UN dossier, `<données>/photolab/` (racine de lecture ET d'écriture, chemins relatifs seulement — règle du moteur lui-même). Les routes (`backend/app/api/photolab_routes.py`) copient l'entrée depuis la Bibliothèque vers ce dossier et servent rendus et exports depuis lui. Aucune interface en P1 : l'écran est P2 (t137).

**Tech stack :** Python 3.13 embarqué (FastAPI, subprocess, threading), photocraft-cli 0.3.0 (Rust, binaire de release officiel, MIT OU Apache-2.0), Pillow pour comparer les pixels dans les bancs.

**Spec :** `docs/superpowers/specs/2026-10-07-photolab-design.md` (D1, D5, D8, lot P1) et l'inventaire `docs/superpowers/specs/2026-10-07-photocraft-inventaire.md` (partie B §9 registre, §6 formats). Skill de mise en œuvre : `lab-externe-deepotus` (références `moteur.md`, `licences.md`).

---

## Faits établis (lus dans les sources v0.3.0, 07/10/2026)

- Release Windows : `photocraft-0.3.0-windows-x64-portable.zip`, 65 251 740 o, sha256 `9997f7df3a6f0717b46bb0f503b3d920c3beedeb9e9c4e1ff2ef3b8671acd47e` (liste de la release `gh release view v0.3.0 -R storytold/photocraft`). Contenu annoncé : `photocraft.exe`, `photocraft-cli.exe`, `portable.txt` ; redistribuable Visual C++ requis.
- `photocraft-cli serve [--automation-read-root <dir>] [--automation-write-root <dir>]` sans `--port` : une session sans interface, requêtes `{"id","method","params"}` une par ligne sur stdin, réponses une par ligne sur stdout : `{"id":…,"ok":true,"result":…}` ou `{"id":…,"ok":false,"error":"…"}` ; une ligne illisible reçoit `{"id":null,"ok":false,…}` (`crates/automation/src/rpc.rs:300-330`). Fin de stdin = fin du serveur.
- Méthodes (`rpc.rs:34-46, 64-134`) : `engine.execute {command, params, wait=true}`, `engine.commands {filter?}` → `[{id,label,menu,shortcut,params,enabled}]`, `doc.open {path}`, `doc.new {width,height,background,…}` (= commande `file.new`), `doc.save {path?, format?, quality?}`, `doc.inspect`, `doc.render {maxSide=1024, path?}` (PNG en base64, ou écrit à `path` → `{path, bytes}`), `doc.select {index}`, `doc.close`, `session.list`, `batch {steps, stopOnError}`, `methods`.
- Chemins : relatifs, en barres obliques, résolus SOUS la racine ; absolus, `..`, préfixes Windows et composants vides refusés ; une racine absente = refus (`crates/automation/src/workspace.rs:21-60`).
- Commandes et paramètres vus dans les tests du moteur : `filter.blur.gaussianBlur {"radius":3}`, `image.adjustments.invert {}`, `image.adjustments.levels {"lightness":{"outBlack":60}}`, `image.adjustments.equalize {}`, `filter.blur.average {}`, `layer.new.layer {"name":…}`, `edit.fill {"color":"#000000"}`, `file.new {"width","height","background"}`.
- Catalogue des menus : `crates/ui-egui/src/menu_catalog.rs`, 765 lignes `(&[chemin], "libellé" | "---", Some("raccourci") | None, "id" | "---")` ; traductions `crates/ui-egui/src/i18n/fr.tsv` (`contexte<TAB>source<TAB>traduction`, contexte vide = texte anglais, `@id` = id de commande, `@plural`), licence des traductions MIT OU Apache-2.0 (`i18n/LICENSE-translations.txt`).

## Deux téléchargements à faire autoriser par l'utilisateur (règle de la session)

1. L'archive Windows ci-dessus (65 Mo) — tâche 2.
2. L'archive des sources du tag v0.3.0 (`https://github.com/storytold/photocraft/archive/refs/tags/v0.3.0.tar.gz`, ≈ 16 Mo) — tâche 9, pour le catalogue des menus et les libellés français.

Demander chacun au moment de sa tâche, avec nom, source et taille ; ne rien télécharger avant le « oui ».

## Conventions du dépôt à respecter

- Bancs : scripts `backend/tests/test_*.py` à lanceur `__main__` (pas pytest), `check(label, cond, detail)`, sortie `=== N passed, M failed ===`, code 1 s'il y a un échec. Lancer avec le Python embarqué :
  `"$LOCALAPPDATA/DeepotusVideoGen/runtime/python/python.exe" -X utf8 tests/<banc>.py` depuis `backend/`.
- Un banc qui a besoin du serveur : dossier de données jetable (`DEEPOTUS_DATA_DIR`, `DATABASE_URL`, `IMAGES_FOLDER`, `OUTPUTS_FOLDER` posés AVANT d'importer `app`), client `httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)))`.
- Commentaires en français qui disent la RAISON mesurée ; sujets de commit sans accents ; pied `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Écrire tout script contenant `\n` ou `\` avec l'outil Write (un heredoc bash les désescape).
- Ne jamais lancer `tests/mutations_*.py` dans un balayage.

## Fichiers

| Fichier | Rôle |
|---|---|
| `vendor/photocraft.json` (créé, versionné) | le manifeste épinglé : version, archives, tailles, empreintes, licence |
| `scripts/vendor_photocraft.py` (créé) | télécharge l'archive Windows, vérifie l'empreinte AVANT d'extraire, extrait dans `vendor/photocraft-0.3.0/` |
| `.gitignore` (modifié) | `vendor/photocraft-*/` (binaires jamais versionnés) |
| `backend/app/services/photolab_moteur.py` (créé) | chemin du binaire, dossier de travail, chemins relatifs sûrs, `SessionMoteur`, liste des commandes refusées, session unique |
| `backend/tests/faux_photocraft.py` (créé) | faux moteur qui parle le protocole (bancs sans binaire) |
| `backend/tests/test_photolab_moteur.py` (créé) | bancs purs : chemins, session (faux moteur), refus |
| `backend/app/api/photolab_routes.py` (créé) | routes `/api/photolab/*` |
| `backend/app/main.py` (modifié) | montage du routeur ; arrêt du moteur au `lifespan` |
| `backend/tests/test_photolab_routes.py` (créé) | bancs des routes avec le faux moteur |
| `backend/tests/test_photolab_fidelite.py` (créé) | VRAI binaire : notre pont = photocraft-cli lui-même, pixel pour pixel |
| `scripts/photolab_mesure.py` (créé) | mesure de latence (spike D1) |
| `scripts/photocraft_catalogue.py` (créé) | catalogue des menus + libellés FR depuis les sources du tag |
| `frontend/photolab/donnees/menus.json` (créé, généré, versionné) | le catalogue exporté pour P2 |
| `backend/tests/test_photolab_catalogue.py` (créé) | forme et comptes du catalogue |
| `docs/superpowers/specs/2026-10-07-photolab-design.md` (modifié) | résultat du spike consigné sous D1 |

---

### Task 0 : préparer

- [ ] **Step 1 : branche et suivi**

```bash
git fetch -q origin && git checkout -b chantier/photolab-p1 origin/main
```
Suivi (artifact, collection `taches`) : t136 → `en_cours`, note « branche chantier/photolab-p1 ». Si la branche `chantier/photolab-p0` (inventaire + conception, t135) n'est pas encore fusionnée, la fusionner d'abord dans `main` par sa propre PR : ce plan cite ses fichiers.

---

### Task 1 : le manifeste épinglé et le script de fournisseur

**Files :**
- Create : `vendor/photocraft.json`
- Create : `scripts/vendor_photocraft.py`
- Test : `backend/tests/test_photolab_vendor.py`

- [ ] **Step 1 : écrire le banc (rouge)**

`backend/tests/test_photolab_vendor.py` :

```python
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

gi = (RACINE / ".gitignore").read_text("utf-8")
check("7 les binaires ne sont jamais versionnés (.gitignore vendor/photocraft-*/)", "vendor/photocraft-*/" in gi)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```

- [ ] **Step 2 : le lancer, il doit être rouge**

Run : `"$LOCALAPPDATA/DeepotusVideoGen/runtime/python/python.exe" -X utf8 tests/test_photolab_vendor.py` (depuis `backend/`)
Attendu : `FileNotFoundError` sur `vendor/photocraft.json` (le manifeste n'existe pas).

- [ ] **Step 3 : le manifeste**

`vendor/photocraft.json` :

```json
{
  "nom": "photocraft",
  "version": "0.3.0",
  "depot": "storytold/photocraft",
  "tag": "v0.3.0",
  "licence": "MIT OR Apache-2.0",
  "binaire": {
    "archive": "photocraft-0.3.0-windows-x64-portable.zip",
    "url": "https://github.com/storytold/photocraft/releases/download/v0.3.0/photocraft-0.3.0-windows-x64-portable.zip",
    "taille": 65251740,
    "sha256": "9997f7df3a6f0717b46bb0f503b3d920c3beedeb9e9c4e1ff2ef3b8671acd47e",
    "cli": "photocraft-cli.exe",
    "app": "photocraft.exe",
    "dossier": "vendor/photocraft-0.3.0"
  },
  "sources": {
    "archive": "photocraft-0.3.0-sources.tar.gz",
    "url": "https://github.com/storytold/photocraft/archive/refs/tags/v0.3.0.tar.gz"
  }
}
```

- [ ] **Step 4 : le script**

`scripts/vendor_photocraft.py` (écrit avec l'outil Write) :

```python
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
        subprocess.run(["gh", "release", "download", m["tag"], "-R", m["depot"], "-p", b["archive"], "-D", str(dossier),
                        "--clobber"], check=True)
    else:
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
        if cible.exists():
            shutil.rmtree(cible)
        cli = extraire(archive, cible)
    print(f"photocraft {m['version']} vérifié (sha256 {b['sha256'][:12]}…) -> {cli.relative_to(RACINE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 5 : `.gitignore`**

Ajouter à la fin de `.gitignore` :

```
# t136 : moteur du Photolab, fourni par scripts/vendor_photocraft.py (épinglé dans vendor/photocraft.json)
vendor/photocraft-*/
```

- [ ] **Step 6 : relancer le banc, il doit être vert**

Run : même commande qu'au Step 2. Attendu : `=== 7 passed, 0 failed ===`.

- [ ] **Step 7 : commit**

```bash
git add vendor/photocraft.json scripts/vendor_photocraft.py .gitignore backend/tests/test_photolab_vendor.py
git commit -m "photolab : moteur photocraft 0.3.0 epingle (manifeste, verification avant extraction) (t136)"
```

---

### Task 2 : fournir le vrai binaire (téléchargement à autoriser)

- [ ] **Step 1 : demander l'accord** — « Je télécharge photocraft-0.3.0-windows-x64-portable.zip (65 Mo, release officielle GitHub storytold/photocraft v0.3.0) et je l'extrais dans vendor/photocraft-0.3.0/ (non versionné) ? » Attendre le oui.

- [ ] **Step 2 : lancer le script**

Run (racine du dépôt) : `python scripts/vendor_photocraft.py`
Attendu : `photocraft 0.3.0 vérifié (sha256 9997f7df3a6f…) -> vendor\photocraft-0.3.0\…\photocraft-cli.exe`.

- [ ] **Step 3 : vérifier que le binaire répond**

Run : `vendor/photocraft-0.3.0/**/photocraft-cli.exe commands --filter gaussian` (chemin exact donné au Step 2).
Attendu : une ligne `filter.blur.gaussianBlur`. Si Windows refuse de lancer (VC++ absent) : le dire à l'utilisateur et s'arrêter (P5 traitera le redistribuable).

- [ ] **Step 4 : `git status` ne montre aucun fichier sous `vendor/photocraft-0.3.0/`.**

---

### Task 3 : chemins — binaire, dossier de travail, chemins relatifs sûrs

**Files :**
- Create : `backend/app/services/photolab_moteur.py`
- Test : `backend/tests/test_photolab_moteur.py`

- [ ] **Step 1 : écrire le banc [1] (rouge)**

`backend/tests/test_photolab_moteur.py` (les sections [2] et [3] s'ajoutent aux tâches 4 et 5) :

```python
# -*- coding: utf-8 -*-
"""t136 (Photolab P1) — le pont vers photocraft-cli, sans le vrai binaire.
  [1] chemins : binaire épinglé, dossier de travail unique, chemins relatifs sûrs (même règle que le moteur).
  [2] la session : protocole JSON lignes avec un FAUX moteur (tests/faux_photocraft.py).
  [3] les commandes refusées : rien qui écrive ou lise hors du dossier de travail.
Run : & $PY tests/test_photolab_moteur.py   (depuis backend/)"""
import os, pathlib, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt136_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ.pop("PHOTOCRAFT_CLI", None)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_moteur as PM                # noqa: E402
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


print("\n[1] chemins")
d = PM.dossier_travail()
check("1a dossier de travail = <données>/photolab, sous-dossiers entrees, rendus, exports",
      d == _tmp / "photolab" and all((d / s).is_dir() for s in ("entrees", "rendus", "exports")), d)
for bon in ("entrees/a.png", "rendus/apercu.png", "exports/Mon-fichier_2.psd"):
    check(f"1b relatif accepte {bon}", PM.relatif(bon) == bon)
for mauvais in ("../x.png", "entrees/../../x", "C:/x.png", "/etc/x", "entrees\\a.png", "", "entrees//a.png", "./a.png",
                "a b.png", None):
    try:
        PM.relatif(mauvais)
        passe = True
    except ValueError:
        passe = False
    check(f"1c relatif refuse {mauvais!r}", not passe)
faux = _tmp / "outil" / "photocraft-cli.exe"
faux.parent.mkdir()
faux.write_bytes(b"MZ")
os.environ["PHOTOCRAFT_CLI"] = str(faux)
check("1d PHOTOCRAFT_CLI désigne le binaire (bancs, installations particulières)", PM.chemin_cli() == faux, PM.chemin_cli())
os.environ["PHOTOCRAFT_CLI"] = str(_tmp / "absent.exe")
racine_vide = _tmp / "racine_vide"
racine_vide.mkdir()
PM.RACINE_APP = racine_vide
try:
    PM.chemin_cli()
    absent_dit = False
except PM.MoteurAbsent as e:
    absent_dit = "vendor_photocraft.py" in str(e)
check("1e binaire introuvable : MoteurAbsent qui dit comment le fournir", absent_dit)
os.environ.pop("PHOTOCRAFT_CLI")
vend = racine_vide / "vendor" / "photocraft-0.3.0" / "photocraft-0.3.0-windows-x64"
vend.mkdir(parents=True)
(vend / "photocraft-cli.exe").write_bytes(b"MZ")
check("1f sinon : vendor/photocraft-0.3.0/** sous la racine de l'application", PM.chemin_cli() == vend / "photocraft-cli.exe",
      PM.chemin_cli())

if __name__ == "__main__":
    print(f"\n=== {ok} passed, {fail} failed ===")
    sys.exit(1 if fail else 0)
```

- [ ] **Step 2 : le lancer, rouge** — Attendu : `ImportError` (`photolab_moteur` absent).

- [ ] **Step 3 : implémenter les chemins**

`backend/app/services/photolab_moteur.py` (première partie ; la session s'ajoute à la tâche 4) :

```python
"""Le moteur du Photolab : photocraft-cli 0.3.0 piloté en JSON lignes (t136, Photolab P1, 07/10/2026).

Décision D1 (validée par l'utilisateur le 07/10) : le CALCUL est celui de photocraft, pour que le Photolab produise
exactement ce que photocraft produit ; notre écran (P2) ne fait que le piloter. Un processus `photocraft-cli serve`
par backend, démarré à la première demande, arrêté avec le backend (fin de stdin = fin du serveur).

Le moteur ne voit qu'un dossier : <données>/photolab/, sa racine de lecture ET d'écriture. Il refuse lui-même les
chemins absolus, `..` et les préfixes Windows (crates/automation/src/workspace.rs) ; `relatif` applique la même règle
AVANT l'envoi, pour qu'un refus soit dit ici, en français, et jamais tenté.
"""
import os
import re
from pathlib import Path

VERSION = "0.3.0"
RACINE_APP = Path(__file__).resolve().parents[3]          # le dépôt, ou %LOCALAPPDATA%\DeepotusVideoGen installé
SOUS_DOSSIERS = ("entrees", "rendus", "exports")
_REL = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9._-]*(/[A-Za-z0-9_-][A-Za-z0-9._-]*)*")


class MoteurAbsent(RuntimeError):
    """Le binaire photocraft-cli n'est pas là (pas encore fourni, ou installation incomplète)."""


class MoteurErreur(RuntimeError):
    """Le moteur a répondu ok:false (le message est le sien) ou s'est arrêté."""


class MoteurDelai(RuntimeError):
    """Pas de réponse dans le délai : le moteur a été arrêté et sera relancé à la demande suivante."""


def chemin_cli() -> Path:
    env = os.environ.get("PHOTOCRAFT_CLI")
    if env and Path(env).is_file():
        return Path(env)
    base = RACINE_APP / "vendor" / f"photocraft-{VERSION}"
    if base.is_dir():
        for c in sorted(base.rglob("photocraft-cli.exe")):
            return c
    raise MoteurAbsent(f"Moteur du Photolab absent : photocraft-cli {VERSION} introuvable sous {base} — "
                       "lance `python scripts/vendor_photocraft.py`.")


def dossier_travail() -> Path:
    from app.config import DATA_ROOT
    d = Path(DATA_ROOT) / "photolab"
    for s in SOUS_DOSSIERS:
        (d / s).mkdir(parents=True, exist_ok=True)
    return d


def relatif(p) -> str:
    """Un chemin relatif sûr (barres obliques, ni `..`, ni `.`, ni absolu, ni espace) — sinon ValueError."""
    if not isinstance(p, str) or not _REL.fullmatch(p) or any(s in (".", "..") for s in p.split("/")):
        raise ValueError(f"chemin refusé : {p!r}")
    return p
```

- [ ] **Step 4 : relancer, vert** — Attendu : `=== 17 passed, 0 failed ===` (1a, 3 × 1b, 10 × 1c, 1d, 1e, 1f).

- [ ] **Step 5 : commit**

```bash
git add backend/app/services/photolab_moteur.py backend/tests/test_photolab_moteur.py
git commit -m "photolab : chemins du moteur (binaire epingle, dossier de travail, chemins relatifs surs) (t136)"
```

---

### Task 4 : la session — protocole JSON lignes, délai, redémarrage

**Files :**
- Create : `backend/tests/faux_photocraft.py`
- Modify : `backend/app/services/photolab_moteur.py` (ajout de `SessionMoteur`, `session`, `fermer`)
- Modify : `backend/tests/test_photolab_moteur.py` (section [2])

- [ ] **Step 1 : le faux moteur**

`backend/tests/faux_photocraft.py` (outil Write) — parle le même protocole, avec des commandes de banc qui provoquent les cas difficiles :

```python
"""FAUX photocraft-cli serve pour les bancs du Photolab (t136) : même protocole JSON lignes, aucun calcul.
Commandes de banc : dz.dormir (ne répond pas), dz.mourir (quitte), dz.erreur (ok:false), dz.bruit (ligne non JSON
avant la réponse), dz.desordre (une réponse à un AUTRE id avant la bonne). doc.render/doc.save écrivent un petit
fichier sous la racine d'écriture. Le pid est rendu par `dz.pid` (pour voir un redémarrage)."""
import json, os, sys, time

args = sys.argv[1:]
ecriture = args[args.index("--automation-write-root") + 1] if "--automation-write-root" in args else "."
docs = []


def repondre(i, ok, val):
    cle = "result" if ok else "error"
    sys.stdout.write(json.dumps({"id": i, "ok": ok, cle: val}) + "\n")
    sys.stdout.flush()


for ligne in sys.stdin:
    ligne = ligne.strip()
    if not ligne:
        continue
    try:
        req = json.loads(ligne)
    except ValueError:
        repondre(None, False, "bad JSON")
        continue
    i, m, p = req.get("id"), req.get("method"), req.get("params") or {}
    if m == "engine.execute":
        c = p.get("command")
        if c == "dz.dormir":
            time.sleep(30)
        elif c == "dz.mourir":
            sys.exit(3)
        elif c == "dz.erreur":
            repondre(i, False, "no active layer")
        elif c == "dz.bruit":
            sys.stdout.write("pas du JSON\n")
            repondre(i, True, {"ok": True})
        elif c == "dz.desordre":
            repondre(i + 1000, True, {"autre": True})
            repondre(i, True, {"bon": True})
        elif c == "dz.pid":
            repondre(i, True, {"pid": os.getpid()})
        else:
            repondre(i, True, {"command": c, "params": p.get("params")})
    elif m == "doc.new":
        docs.append(p)
        repondre(i, True, {"document": len(docs) - 1})
    elif m == "doc.open":
        docs.append({"path": p.get("path")})
        repondre(i, True, {"document": len(docs) - 1, "path": p.get("path")})
    elif m == "doc.inspect":
        repondre(i, True, {"documents": docs})
    elif m in ("doc.render", "doc.save"):
        chemin = p.get("path") or "rendus/sans_nom.png"
        os.makedirs(os.path.dirname(os.path.join(ecriture, chemin)), exist_ok=True)
        with open(os.path.join(ecriture, chemin), "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\nFAUX")
        repondre(i, True, {"path": chemin, "bytes": 12})
    elif m == "engine.commands":
        repondre(i, True, [{"id": "filter.blur.gaussianBlur", "label": "Gaussian Blur…", "menu": ["Filter", "Blur"],
                            "shortcut": None, "params": "{radius}", "enabled": bool(docs)}])
    else:
        repondre(i, False, f"unknown method `{m}` (try `methods`)")
```

- [ ] **Step 2 : la section [2] du banc (rouge)**

Ajouter à `backend/tests/test_photolab_moteur.py`, AVANT le bloc `if __name__ == "__main__":` :

```python
print("\n[2] la session (faux moteur)")
import json as _json, time as _time                        # noqa: E402
FAUX = [sys.executable, str(BACKEND / "tests" / "faux_photocraft.py"), "serve",
        "--automation-read-root", str(d), "--automation-write-root", str(d)]
s = PM.SessionMoteur(FAUX, delai_s=2.0)
r = s.appeler("doc.new", {"width": 64, "height": 32})
check("2a démarrage à la première demande, réponse rendue", r == {"document": 0} and s.vivant(), r)
check("2b generation = 1 après le premier démarrage", s.generation == 1, s.generation)
check("2c une ligne non JSON est ignorée", s.appeler("engine.execute", {"command": "dz.bruit"}) == {"ok": True})
check("2d une réponse à un autre id est ignorée, la bonne est rendue",
      s.appeler("engine.execute", {"command": "dz.desordre"}) == {"bon": True})
try:
    s.appeler("engine.execute", {"command": "dz.erreur"})
    err = None
except PM.MoteurErreur as e:
    err = str(e)
check("2e ok:false -> MoteurErreur avec le message du moteur, la session reste vivante",
      err == "no active layer" and s.vivant(), err)
pid1 = s.appeler("engine.execute", {"command": "dz.pid"})["pid"]
t0 = _time.monotonic()
try:
    s.appeler("engine.execute", {"command": "dz.dormir"}, delai_s=0.5)
    delai = False
except PM.MoteurDelai:
    delai = True
check("2f pas de réponse dans le délai -> MoteurDelai, moteur arrêté, sans attendre ses 30 s",
      delai and not s.vivant() and _time.monotonic() - t0 < 5, _time.monotonic() - t0)
pid2 = s.appeler("engine.execute", {"command": "dz.pid"})["pid"]
check("2g la demande suivante relance un NOUVEAU moteur (generation 2)", pid2 != pid1 and s.generation == 2, (pid1, pid2))
try:
    s.appeler("engine.execute", {"command": "dz.mourir"})
    mort = False
except PM.MoteurErreur:
    mort = True
check("2h moteur qui meurt pendant une demande -> MoteurErreur, relancé ensuite",
      mort and s.appeler("doc.inspect") == {"documents": []} and s.generation == 3, s.generation)
s.fermer()
check("2i fermer() arrête le moteur", not s.vivant())
PM.FABRIQUE = lambda: PM.SessionMoteur(FAUX, delai_s=2.0)
PM._SESSION = None
check("2j session() rend UNE session (la même à chaque appel)", PM.session() is PM.session())
PM.fermer()
check("2k fermer() du module arrête et oublie la session", PM._SESSION is None)
```

Lancer : rouge attendu (`AttributeError: SessionMoteur`).

- [ ] **Step 3 : implémenter la session**

Ajouter à la fin de `backend/app/services/photolab_moteur.py` :

```python
import itertools
import json
import queue
import subprocess
import sys
import threading
import time

_SANS_FENETRE = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


class SessionMoteur:
    """Une session `photocraft-cli serve` : une requête à la fois (verrou), réponse appariée par id, délai par
    requête. Un délai dépassé ou un moteur mort arrêtent le processus ; la demande suivante en relance un neuf
    (`generation` +1) — ses documents ouverts sont alors PERDUS, l'écran (P2) relit `generation` pour le dire."""

    def __init__(self, commande: list, delai_s: float = 60.0):
        self.commande = list(commande)
        self.delai_s = delai_s
        self.generation = 0
        self._proc = None
        self._lignes = None
        self._ids = itertools.count(1)
        self._verrou = threading.Lock()

    def vivant(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def _demarrer(self):
        self._proc = subprocess.Popen(self.commande, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.DEVNULL, creationflags=_SANS_FENETRE)
        self._lignes = queue.Queue()
        threading.Thread(target=self._lire, args=(self._proc, self._lignes), daemon=True).start()
        self.generation += 1

    @staticmethod
    def _lire(proc, q):
        for brut in proc.stdout:
            q.put(brut)
        q.put(None)                                       # fin de flux : le moteur s'est arrêté

    def fermer(self):
        p, self._proc = self._proc, None
        if p is None:
            return
        if p.poll() is None:
            try:
                p.stdin.close()                           # fin de stdin = fin propre du serveur
                p.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                p.kill()
                p.wait()

    def appeler(self, methode: str, params: dict | None = None, delai_s: float | None = None):
        delai = delai_s or self.delai_s
        with self._verrou:
            if not self.vivant():
                self._demarrer()
            rid = next(self._ids)
            try:
                self._proc.stdin.write((json.dumps({"id": rid, "method": methode, "params": params or {}}) + "\n")
                                       .encode("utf-8"))
                self._proc.stdin.flush()
            except OSError:
                self.fermer()
                raise MoteurErreur(f"{methode} : le moteur s'est arrêté")
            fin = time.monotonic() + delai
            while True:
                reste = fin - time.monotonic()
                if reste <= 0:
                    self.fermer()
                    raise MoteurDelai(f"{methode} : pas de réponse en {delai:g} s — moteur arrêté, relancé à la "
                                      "demande suivante")
                try:
                    brut = self._lignes.get(timeout=reste)
                except queue.Empty:
                    continue
                if brut is None:
                    self.fermer()
                    raise MoteurErreur(f"{methode} : le moteur s'est arrêté")
                try:
                    rep = json.loads(brut.decode("utf-8"))
                except ValueError:
                    continue                              # une ligne qui n'est pas une réponse (journal, bruit)
                if not isinstance(rep, dict) or rep.get("id") != rid:
                    continue
                if rep.get("ok"):
                    return rep.get("result")
                raise MoteurErreur(str(rep.get("error") or "erreur du moteur"))


FABRIQUE = None                                           # bancs : une fabrique de fausse session
_SESSION = None
_VERROU_SESSION = threading.Lock()


def session() -> SessionMoteur:
    global _SESSION
    with _VERROU_SESSION:
        if _SESSION is None:
            if FABRIQUE is not None:
                _SESSION = FABRIQUE()
            else:
                d = dossier_travail()
                _SESSION = SessionMoteur([str(chemin_cli()), "serve", "--automation-read-root", str(d),
                                          "--automation-write-root", str(d)])
        return _SESSION


def fermer():
    global _SESSION
    with _VERROU_SESSION:
        if _SESSION is not None:
            _SESSION.fermer()
        _SESSION = None
```

- [ ] **Step 4 : relancer, vert** — Attendu : `=== 28 passed, 0 failed ===` (17 + 11).

- [ ] **Step 5 : commit**

```bash
git add backend/app/services/photolab_moteur.py backend/tests/faux_photocraft.py backend/tests/test_photolab_moteur.py
git commit -m "photolab : session photocraft-cli serve (JSON lignes, delai, relance) (t136)"
```

---

### Task 5 : les commandes refusées

Le moteur a des commandes qui lisent ou écrivent des fichiers par leurs paramètres (`file.saveAs {path}`, `file.place…`, scripts, droplets, greffons). Le pont n'en laisse passer AUCUNE : les fichiers passent par les routes, qui utilisent `relatif`.

**Files :** Modify `backend/app/services/photolab_moteur.py`, `backend/tests/test_photolab_moteur.py` (section [3]).

- [ ] **Step 1 : section [3] (rouge)** — avant `if __name__ == "__main__":` :

```python
print("\n[3] les commandes refusées")
for bon in ("filter.blur.gaussianBlur", "image.adjustments.levels", "layer.new.layer", "edit.fill", "select.all"):
    check(f"3a commande acceptée {bon}", PM.commande_autorisee(bon, {"radius": 3}) == bon)
for mauvais, params in (("file.saveAs", {}), ("file.open", {}), ("file.place.embedded", {}), ("file.scripts.browse", {}),
                        ("automate.droplet", {}), ("plugin.install", {}), ("app.quit", {}), ("FILTER.blur", {}),
                        ("filter..blur", {}), ("filter.blur.gaussianBlur", {"path": "C:/x.png"}),
                        ("image.adjustments.colorLookup", {"lut": {"file": "../x.cube"}}),
                        ("layer.new.layer", {"steps": [{"folder": "x"}]})):
    try:
        PM.commande_autorisee(mauvais, params)
        passe = True
    except ValueError:
        passe = False
    check(f"3b refusée {mauvais} {params}", not passe)
```

- [ ] **Step 2 : implémenter**

Ajouter à `backend/app/services/photolab_moteur.py` (après `relatif`) :

```python
_ID_COMMANDE = re.compile(r"[a-z][A-Za-z0-9]*(\.[a-z][A-Za-z0-9]*)+")
PREFIXES_REFUSES = ("file.", "app.", "automate.", "plugin.", "script", "window.", "help.", "edit.preferences",
                    "edit.presets", "edit.keyboardShortcuts", "edit.menus")
CLES_FICHIER = {"path", "paths", "file", "files", "filename", "fileName", "folder", "dir", "directory", "source", "out",
                "output", "url"}


def _cles(v):
    if isinstance(v, dict):
        for k, w in v.items():
            yield k
            yield from _cles(w)
    elif isinstance(v, list):
        for w in v:
            yield from _cles(w)


def commande_autorisee(cid, params) -> str:
    """L'id d'une commande moteur que l'écran peut lancer — sinon ValueError. Refusées : tout ce qui touche des
    fichiers, l'application ou du code (préfixes ci-dessus), et toute commande dont les paramètres nomment un fichier :
    les fichiers passent par les routes du Photolab, jamais par une commande."""
    if not isinstance(cid, str) or not _ID_COMMANDE.fullmatch(cid):
        raise ValueError(f"commande illisible : {cid!r}")
    if cid.startswith(PREFIXES_REFUSES):
        raise ValueError(f"commande réservée aux routes du Photolab : {cid}")
    if any(k in CLES_FICHIER for k in _cles(params)):
        raise ValueError(f"{cid} : un paramètre nomme un fichier — passe par les routes du Photolab")
    return cid
```

Note : `source` est dans `CLES_FICHIER` parce que `image.adjustments.matchColor {"source": 1}` désigne un document par index ; il passera par une route dédiée en P3 si besoin (le refus est sûr par défaut).

- [ ] **Step 3 : vert** — Attendu : `=== 45 passed, 0 failed ===` (28 + 5 + 12).

- [ ] **Step 4 : commit**

```bash
git add backend/app/services/photolab_moteur.py backend/tests/test_photolab_moteur.py
git commit -m "photolab : commandes moteur refusees (fichiers, application, code) (t136)"
```

---

### Task 6 : les routes `/api/photolab`

**Files :**
- Create : `backend/app/api/photolab_routes.py`
- Modify : `backend/app/main.py` (montage après le bloc `__DZ_DICTATION_ROUTER_END__` ; arrêt dans le `finally` du `lifespan`)
- Test : `backend/tests/test_photolab_routes.py`

- [ ] **Step 1 : le banc (rouge)**

`backend/tests/test_photolab_routes.py` :

```python
# -*- coding: utf-8 -*-
"""t136 (Photolab P1) — les routes /api/photolab avec le FAUX moteur (tests/faux_photocraft.py).
Run : & $PY tests/test_photolab_routes.py   (depuis backend/)"""
import asyncio, os, pathlib, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt136r_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_moteur as PM                # noqa: E402
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:300]}")


D = PM.dossier_travail()
FAUX = [sys.executable, str(BACKEND / "tests" / "faux_photocraft.py"), "serve",
        "--automation-read-root", str(D), "--automation-write-root", str(D)]
PM.FABRIQUE = lambda: PM.SessionMoteur(FAUX, delai_s=3.0)
from PIL import Image                                          # noqa: E402
Image.new("RGB", (8, 8), (200, 30, 30)).save(_tmp / "images" / "rouge.png")


async def scenario():
    import httpx
    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t") as c:
        e = (await c.get("/api/photolab/etat")).json()
        check("1 /etat : version 0.3.0, generation 0 avant la première demande", e.get("version") == "0.3.0"
              and e.get("generation") == 0, e)
        r = await c.post("/api/photolab/nouveau", json={"width": 64, "height": 32, "background": "white"})
        check("2 /nouveau crée un document", r.status_code == 200 and r.json().get("document") == 0, r.text)
        r = await c.post("/api/photolab/nouveau", json={"width": 0, "height": 32})
        check("3 /nouveau borné (1..30000)", r.status_code == 400, r.status_code)
        r = await c.post("/api/photolab/ouvrir", json={"filename": "rouge.png"})
        check("4 /ouvrir copie l'image de la Bibliothèque dans entrees/ et l'ouvre par chemin RELATIF",
              r.status_code == 200 and r.json().get("path") == "entrees/rouge.png" and (D / "entrees" / "rouge.png").is_file(),
              r.text)
        for mauvais in ("../t.db", "absent.png", "a/b.png"):
            r = await c.post("/api/photolab/ouvrir", json={"filename": mauvais})
            check(f"5 /ouvrir refuse {mauvais}", r.status_code in (400, 404), (r.status_code, r.text))
        r = await c.post("/api/photolab/executer", json={"command": "filter.blur.gaussianBlur", "params": {"radius": 3}})
        check("6 /executer passe la commande et ses paramètres", r.status_code == 200
              and r.json() == {"command": "filter.blur.gaussianBlur", "params": {"radius": 3}}, r.text)
        r = await c.post("/api/photolab/executer", json={"command": "file.saveAs", "params": {"path": "C:/x.psd"}})
        check("7 /executer refuse une commande de fichier (400)", r.status_code == 400, r.status_code)
        r = await c.post("/api/photolab/executer", json={"command": "dz.erreur"})
        check("8 erreur du moteur -> 422 avec son message", r.status_code == 422 and "no active layer" in r.text, r.text)
        r = await c.post("/api/photolab/rendu", json={"maxSide": 512})
        j = r.json()
        check("9 /rendu écrit rendus/apercu.png et rend une URL qui le sert",
              r.status_code == 200 and j.get("url", "").startswith("/api/photolab/rendus/apercu.png?v=") and "ms" in j, j)
        f = await c.get(j["url"])
        check("10 l'aperçu est servi en image/png", f.status_code == 200 and f.headers["content-type"] == "image/png"
              and f.content.startswith(b"\x89PNG"), f.status_code)
        r = await c.post("/api/photolab/rendu", json={"maxSide": 99999})
        check("11 /rendu borné (64..8192)", r.status_code == 400, r.status_code)
        r = await c.post("/api/photolab/enregistrer", json={"format": "psd", "nom": "Mon essai"})
        j = r.json()
        check("12 /enregistrer écrit dans exports/ sous un nom sûr et le sert",
              r.status_code == 200 and j.get("fichier") == "Mon-essai.psd" and (D / "exports" / "Mon-essai.psd").is_file(), j)
        r = await c.post("/api/photolab/enregistrer", json={"format": "exe"})
        check("13 /enregistrer : format hors liste refusé", r.status_code == 400, r.status_code)
        for chemin in ("/api/photolab/rendus/..%2Ft.db", "/api/photolab/exports/..%5Ct.db", "/api/photolab/rendus/absent.png"):
            r = await c.get(chemin)
            check(f"14 {chemin} ne sert rien hors du dossier", r.status_code in (400, 404), r.status_code)
        r = await c.get("/api/photolab/commandes")
        check("15 /commandes rend le registre du moteur", r.status_code == 200
              and r.json()[0]["id"] == "filter.blur.gaussianBlur", r.text)
        r = await c.post("/api/photolab/executer", json={"command": "dz.mourir"})
        e = (await c.get("/api/photolab/etat")).json()
        r2 = await c.post("/api/photolab/executer", json={"command": "dz.pid"})
        e2 = (await c.get("/api/photolab/etat")).json()
        check("16 moteur mort : 422 dit, puis relancé ; /etat montre la nouvelle generation",
              r.status_code == 422 and r2.status_code == 200 and e2["generation"] == e["generation"] + 1, (r.text, e, e2))
    PM.fermer()
    PM.FABRIQUE = None
    os.environ["PHOTOCRAFT_CLI"] = str(_tmp / "absent.exe")
    PM.RACINE_APP = _tmp
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t") as c:
        r = await c.post("/api/photolab/nouveau", json={"width": 8, "height": 8})
        e = (await c.get("/api/photolab/etat")).json()
        check("17 moteur absent : 503 qui dit comment le fournir ; /etat present:false",
              r.status_code == 503 and "vendor_photocraft.py" in r.text and e.get("present") is False, (r.text, e))

asyncio.run(scenario())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```

Lancer : rouge attendu (404 sur `/api/photolab/etat`).

- [ ] **Step 2 : les routes**

`backend/app/api/photolab_routes.py` :

```python
"""Routes du Photolab (t136, P1, 07/10/2026) : /api/photolab — le pont HTTP vers le moteur photocraft.

L'écran (P2) ne parle qu'à ces routes. Les fichiers n'entrent et ne sortent que par elles : une image de la
Bibliothèque est COPIÉE dans <données>/photolab/entrees/ avant d'être ouverte (le moteur ne lit que son dossier),
les rendus et exports sont servis depuis rendus/ et exports/. Rien de payant : le moteur est local.
"""
import asyncio
import re
import shutil
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services import photolab_moteur as PM

router = APIRouter()
_NOM_IMAGE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._ -]{0,180}")
_NOM_SERVI = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]{0,180}")
FORMATS = ("pcraft", "psd", "psb", "png", "jpg", "webp", "tif", "tga")
_rendus = {"n": 0}


async def _appeler(methode, params=None, delai_s=None):
    try:
        s = PM.session()
        return await asyncio.to_thread(s.appeler, methode, params or {}, delai_s)
    except PM.MoteurAbsent as e:
        raise HTTPException(503, str(e))
    except PM.MoteurDelai as e:
        raise HTTPException(504, str(e))
    except PM.MoteurErreur as e:
        raise HTTPException(422, f"photocraft : {e}")
    except ValueError as e:
        raise HTTPException(400, str(e))


def _entier(v, bas, haut, nom):
    if not isinstance(v, int) or isinstance(v, bool) or not bas <= v <= haut:
        raise HTTPException(400, f"{nom} : entier de {bas} à {haut} attendu")
    return v


@router.get("/etat")
async def etat():
    try:
        chemin = str(PM.chemin_cli()) if PM.FABRIQUE is None else "(banc)"
        present = True
    except PM.MoteurAbsent:
        chemin, present = None, False
    s = PM._SESSION
    return {"version": PM.VERSION, "present": present, "chemin": chemin, "generation": s.generation if s else 0,
            "vivant": bool(s and s.vivant())}


@router.get("/commandes")
async def commandes():
    return await _appeler("engine.commands")


@router.post("/nouveau")
async def nouveau(body: dict):
    p = {"width": _entier(body.get("width"), 1, 30000, "width"), "height": _entier(body.get("height"), 1, 30000, "height")}
    for k in ("background", "resolution", "mode", "depth", "name"):
        if k in body:
            p[k] = body[k]
    return await _appeler("doc.new", p)


@router.post("/ouvrir")
async def ouvrir(body: dict):
    from app.config import settings
    nom = (body or {}).get("filename")
    if not isinstance(nom, str) or not _NOM_IMAGE.fullmatch(nom):
        raise HTTPException(400, f"nom d'image refusé : {nom!r}")
    src = settings.images_path / nom
    if not src.is_file():
        raise HTTPException(404, f"image introuvable dans la Bibliothèque : {nom}")
    sur = re.sub(r"[^A-Za-z0-9._-]", "-", nom)
    dest = PM.dossier_travail() / "entrees" / sur
    await asyncio.to_thread(shutil.copyfile, src, dest)
    return await _appeler("doc.open", {"path": PM.relatif(f"entrees/{sur}")})


@router.post("/executer")
async def executer(body: dict):
    cid, params = (body or {}).get("command"), (body or {}).get("params") or {}
    try:
        PM.commande_autorisee(cid, params)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return await _appeler("engine.execute", {"command": cid, "params": params})


@router.get("/inspecter")
async def inspecter():
    return await _appeler("doc.inspect")


@router.post("/rendu")
async def rendu(body: dict | None = None):
    m = _entier((body or {}).get("maxSide", 1024), 64, 8192, "maxSide")
    t0 = time.perf_counter()
    await _appeler("doc.render", {"path": "rendus/apercu.png", "maxSide": m})
    _rendus["n"] += 1
    return {"url": f"/api/photolab/rendus/apercu.png?v={_rendus['n']}", "ms": round((time.perf_counter() - t0) * 1000)}


@router.post("/enregistrer")
async def enregistrer(body: dict):
    fmt = (body or {}).get("format")
    if fmt not in FORMATS:
        raise HTTPException(400, f"format hors liste : {fmt!r} ({', '.join(FORMATS)})")
    base = re.sub(r"[^A-Za-z0-9_-]+", "-", str((body or {}).get("nom") or "photolab")).strip("-") or "photolab"
    fichier = f"{base[:80]}.{fmt}"
    p = {"path": PM.relatif(f"exports/{fichier}"), "format": fmt}
    if "quality" in (body or {}):
        p["quality"] = _entier(body["quality"], 1, 100, "quality")
    await _appeler("doc.save", p)
    return {"fichier": fichier, "url": f"/api/photolab/exports/{fichier}"}


def _servir(sous, nom):
    if not _NOM_SERVI.fullmatch(nom or ""):
        raise HTTPException(400, "nom refusé")
    f = PM.dossier_travail() / sous / nom
    if not f.is_file():
        raise HTTPException(404, "introuvable")
    return FileResponse(f, media_type="image/png" if nom.endswith(".png") else None)


@router.get("/rendus/{nom}")
async def servir_rendu(nom: str):
    return _servir("rendus", nom)


@router.get("/exports/{nom}")
async def servir_export(nom: str):
    return _servir("exports", nom)
```

- [ ] **Step 3 : monter le routeur et arrêter le moteur avec le backend**

Dans `backend/app/main.py`, juste après la ligne `# __DZ_DICTATION_ROUTER_END__` :

```python
# __DZ_PHOTOLAB_ROUTER_BEGIN__
# Photolab (t136, 07/10/2026) : /api/photolab — pont vers le moteur photocraft-cli 0.3.0 (décision D1)
from app.api.photolab_routes import router as photolab_router
app.include_router(photolab_router, prefix="/api/photolab")
# __DZ_PHOTOLAB_ROUTER_END__
```

Dans `lifespan`, bloc `finally:`, juste avant `logger.info("Shutting down")` :

```python
        # t136 : le moteur du Photolab s'arrête avec le backend (fin de stdin = fin propre de photocraft-cli serve)
        try:
            from app.services import photolab_moteur
            photolab_moteur.fermer()
        except Exception as e:
            logger.warning(f"Photolab : arrêt du moteur ignoré ({e!r})")
```

- [ ] **Step 4 : vert** — Attendu : `=== 21 passed, 0 failed ===` (17 numéros, dont 3 pour le 5 et 3 pour le 14).

- [ ] **Step 5 : commit**

```bash
git add backend/app/api/photolab_routes.py backend/app/main.py backend/tests/test_photolab_routes.py
git commit -m "photolab : routes /api/photolab (etat, nouveau, ouvrir, executer, rendu, enregistrer) (t136)"
```

---

### Task 7 : la fidélité — notre pont = photocraft lui-même

Le cœur de D1 : la même commande sur la même entrée donne les mêmes pixels par notre pont que par `photocraft-cli run`.

**Files :** Create `backend/tests/test_photolab_fidelite.py`.

- [ ] **Step 1 : le banc**

```python
# -*- coding: utf-8 -*-
"""t136 (Photolab P1) — FIDÉLITÉ (décision D1) avec le VRAI moteur : pour chaque commande, notre pont
(/api/photolab : ouvrir -> executer -> enregistrer png) et `photocraft-cli run <entrée> --cmd … --out` donnent les
MÊMES pixels. Rouge si le binaire manque (lancer `python scripts/vendor_photocraft.py`) : jamais un faux vert.
Run : & $PY tests/test_photolab_fidelite.py   (depuis backend/)"""
import asyncio, json, os, pathlib, subprocess, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt136f_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from PIL import Image, ImageDraw                              # noqa: E402
from app.services import photolab_moteur as PM                # noqa: E402
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:300]}")


try:
    CLI = PM.chemin_cli()
except PM.MoteurAbsent as e:
    check("0 le vrai moteur est fourni", False, e)
    print(f"\n=== {ok} passed, {fail} failed ===")
    sys.exit(1)

# une entrée déterministe : dégradé, formes, couleurs saturées (un flou ou des niveaux y changent des pixels)
im = Image.new("RGB", (96, 64))
px = im.load()
for y in range(64):
    for x in range(96):
        px[x, y] = (x * 255 // 95, y * 255 // 63, (x * y) % 256)
dr = ImageDraw.Draw(im)
dr.rectangle((10, 10, 40, 30), fill=(250, 20, 20))
dr.ellipse((50, 20, 90, 60), fill=(20, 200, 60))
im.save(_tmp / "images" / "entree.png")

CAS = [("filter.blur.gaussianBlur", {"radius": 3}), ("image.adjustments.invert", {}),
       ("image.adjustments.levels", {"lightness": {"outBlack": 60}}), ("image.adjustments.equalize", {}),
       ("filter.blur.average", {})]


def reference(cid, params, sortie):
    r = subprocess.run([str(CLI), "run", str(_tmp / "images" / "entree.png"), "--cmd", cid, "--params", json.dumps(params),
                        "--out", str(sortie)], capture_output=True, text=True, timeout=120)
    return r.returncode == 0 and sortie.is_file(), r.stderr[-300:]


def pixels(p):
    return list(Image.open(p).convert("RGBA").getdata())


async def scenario():
    import httpx
    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t",
                                 timeout=120) as c:
        for cid, params in CAS:
            ref = _tmp / f"ref-{cid}.png"
            fait, err = reference(cid, params, ref)
            if not fait:
                check(f"{cid} : référence photocraft-cli run", False, err)
                continue
            r1 = await c.post("/api/photolab/ouvrir", json={"filename": "entree.png"})
            r2 = await c.post("/api/photolab/executer", json={"command": cid, "params": params})
            r3 = await c.post("/api/photolab/enregistrer", json={"format": "png", "nom": f"pont-{cid.replace('.', '-')}"})
            if not (r1.status_code == r2.status_code == r3.status_code == 200):
                check(f"{cid} : le pont répond", False, (r1.text, r2.text, r3.text))
                continue
            pont = PM.dossier_travail() / "exports" / r3.json()["fichier"]
            a, b = pixels(ref), pixels(pont)
            check(f"{cid} {params} : mêmes pixels que photocraft-cli", a == b and pixels(_tmp / "images" / "entree.png") != a,
                  f"{sum(x != y for x, y in zip(a, b))} pixels différents")
            PM.fermer()                                   # un moteur neuf par cas : aucun document d'un cas ne reste
    PM.fermer()

asyncio.run(scenario())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```

- [ ] **Step 2 : le lancer** — Attendu : `=== 5 passed, 0 failed ===`. Un écart de pixels est un FAIT à comprendre avant de continuer (ex. `run` écrit un PNG 16 bits, ou applique la commande au calque et non au document) : lire `apps/photocraft-cli/src/lib.rs` (`run_cmds`, `files::save`) et corriger le PONT, pas le banc. Si une commande de `CAS` n'existe pas sous ce nom, `engine.commands` donne le bon id : remplacer l'id dans `CAS`, pas l'assertion.

- [ ] **Step 3 : commit**

```bash
git add backend/tests/test_photolab_fidelite.py
git commit -m "photolab : banc de fidelite, le pont rend les memes pixels que photocraft-cli (t136)"
```

---

### Task 8 : le spike de latence (D1)

**Files :** Create `scripts/photolab_mesure.py` ; Modify `docs/superpowers/specs/2026-10-07-photolab-design.md`.

- [ ] **Step 1 : le script**

`scripts/photolab_mesure.py` (outil Write) :

```python
"""Spike de latence du Photolab (t136, décision D1) : combien coûte un aller-retour moteur sur une image 1920 × 1080 ?
Ouvre une image synthétique dans photocraft-cli serve, puis mesure (médiane de 5) : doc.render maxSide 1024 et 1920,
filtre flou gaussien r=3, niveaux, nouveau calque + remplissage, et l'aller-retour complet « commande + rendu 1920 ».
Usage : python scripts/photolab_mesure.py     (le binaire doit être fourni : scripts/vendor_photocraft.py)
"""
import os, pathlib, statistics, sys, tempfile, time

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "backend"))
d = pathlib.Path(tempfile.mkdtemp(prefix="dzmesure_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(d)
from PIL import Image                                          # noqa: E402
from app.services import photolab_moteur as PM                # noqa: E402

w = PM.dossier_travail()
img = Image.effect_mandelbrot((1920, 1080), (-2.2, -1.2, 1.0, 1.2), 100).convert("RGB")
img.save(w / "entrees" / "m.png")
s = PM.SessionMoteur([str(PM.chemin_cli()), "serve", "--automation-read-root", str(w), "--automation-write-root", str(w)],
                     delai_s=120)
s.appeler("doc.open", {"path": "entrees/m.png"})


def mesure(nom, f, n=5):
    t = []
    for _ in range(n):
        t0 = time.perf_counter()
        f()
        t.append((time.perf_counter() - t0) * 1000)
    print(f"| {nom} | {statistics.median(t):.0f} ms | {min(t):.0f}–{max(t):.0f} ms |")


print("| Mesure (1920 × 1080, médiane de 5) | Médiane | Écart |\n|---|---|---|")
mesure("doc.render maxSide 1024", lambda: s.appeler("doc.render", {"path": "rendus/a.png", "maxSide": 1024}))
mesure("doc.render maxSide 1920", lambda: s.appeler("doc.render", {"path": "rendus/a.png", "maxSide": 1920}))
mesure("flou gaussien r=3", lambda: s.appeler("engine.execute", {"command": "filter.blur.gaussianBlur", "params": {"radius": 3}}))
mesure("niveaux", lambda: s.appeler("engine.execute", {"command": "image.adjustments.levels",
                                                       "params": {"lightness": {"outBlack": 20}}}))
mesure("nouveau calque + remplissage", lambda: (s.appeler("engine.execute", {"command": "layer.new.layer", "params": {}}),
                                               s.appeler("engine.execute", {"command": "edit.fill", "params": {"color": "#336699"}})))
mesure("aller-retour flou + rendu 1920", lambda: (s.appeler("engine.execute", {"command": "filter.blur.gaussianBlur",
                                                                                  "params": {"radius": 1}}),
                                                 s.appeler("doc.render", {"path": "rendus/a.png", "maxSide": 1920})))
s.fermer()
```

- [ ] **Step 2 : le lancer** — Run : `"$LOCALAPPDATA/DeepotusVideoGen/runtime/python/python.exe" -X utf8 scripts/photolab_mesure.py`. Attendu : un tableau de 6 lignes.

- [ ] **Step 3 : consigner le résultat sous D1** dans `docs/superpowers/specs/2026-10-07-photolab-design.md` : coller le tableau, la machine (CPU, RAM) et la décision qui en découle, selon cette règle écrite AVANT de mesurer :
  - aller-retour « commande + rendu 1920 » ≤ 300 ms → D1 tel quel (rendu complet à chaque geste validé) ;
  - 300 ms à 1,5 s → P2 rend à la taille de la VUE (`maxSide` = plus grand côté du canevas affiché) et garde un aperçu JS pendant les gestes continus ;
  - > 1,5 s → le dire à l'utilisateur avant P2 : rendu par région (à demander en amont ou à faire dans un fork) ou repli D10 (app native).

- [ ] **Step 4 : commit**

```bash
git add scripts/photolab_mesure.py docs/superpowers/specs/2026-10-07-photolab-design.md
git commit -m "photolab : spike de latence du moteur et decision consignee sous D1 (t136)"
```

---

### Task 9 : le catalogue des menus pour P2 (téléchargement des sources à autoriser)

**Files :**
- Create : `scripts/photocraft_catalogue.py`, `frontend/photolab/donnees/menus.json` (généré), `backend/tests/test_photolab_catalogue.py`

- [ ] **Step 1 : demander l'accord** — « Je télécharge l'archive des sources de photocraft v0.3.0 (github.com/storytold/photocraft/archive/refs/tags/v0.3.0.tar.gz, ≈ 16 Mo) dans le dossier temporaire, pour en extraire le catalogue des menus et les libellés français (MIT OU Apache-2.0) ? » Attendre le oui.

- [ ] **Step 2 : le banc (rouge)**

`backend/tests/test_photolab_catalogue.py` :

```python
# -*- coding: utf-8 -*-
"""t136 (Photolab P1) — le catalogue des menus de photocraft 0.3.0 exporté pour l'écran (P2) : forme, comptes du relevé
(inventaire B §1), libellés FR, attribution.
Run : & $PY tests/test_photolab_catalogue.py   (depuis backend/)"""
import json, pathlib, re, sys
sys.stdout.reconfigure(encoding="utf-8")
RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:300]}")


C = json.loads((RACINE / "frontend" / "photolab" / "donnees" / "menus.json").read_text("utf-8"))
E = C.get("entrees", [])
check("1 attribution : source, version, licence", C.get("source") == "storytold/photocraft v0.3.0 crates/ui-egui/src/menu_catalog.rs"
      and C.get("licence") == "MIT OR Apache-2.0", {k: C.get(k) for k in ("source", "licence")})
check("2 les 765 lignes du catalogue, dans l'ordre", len(E) == 765, len(E))
check("3 10 menus de premier niveau dans l'ordre de photocraft",
      list(dict.fromkeys(e["chemin"][0] for e in E)) == ["File", "Edit", "Image", "Layer", "Type", "Select", "Filter",
                                                          "View", "Window", "Help"],
      list(dict.fromkeys(e["chemin"][0] for e in E)))
sep = [e for e in E if e.get("separateur")]
ent = [e for e in E if not e.get("separateur")]
check("4 séparateurs sans id ni libellé", sep and all(set(e) == {"chemin", "separateur"} for e in sep))
check("5 chaque entrée : id, libelle_en, libelle_fr non vides, raccourci ou null",
      all(re.fullmatch(r"[a-z][A-Za-z0-9]*(\.[A-Za-z0-9]+)+", e["id"]) and e["libelle_en"] and e["libelle_fr"]
          and (e["raccourci"] is None or isinstance(e["raccourci"], str)) for e in ent),
      [e for e in ent if not e.get("libelle_fr")][:3])
nouv = next((e for e in ent if e["id"] == "file.new"), None)
check("6 File › New… = Nouveau…, Cmd+N", nouv == {"chemin": ["File"], "id": "file.new", "libelle_en": "New…",
                                                  "libelle_fr": "Nouveau…", "raccourci": "Cmd+N"}, nouv)
check("7 les noms des menus et sous-menus ont leur traduction", C.get("menus_fr", {}).get("File") == "Fichier"
      and C.get("menus_fr", {}).get("Blur") == "Flou", {k: C.get("menus_fr", {}).get(k) for k in ("File", "Blur")})
check("8 aucun « Photoshop » dans les libellés montrés (D8)",
      not [e for e in ent if "Photoshop" in e["libelle_fr"] or "Photoshop" in e["libelle_en"]],
      [e["libelle_en"] for e in ent if "Photoshop" in e["libelle_en"]][:5])
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
```

Le test 8 est intentionnellement exigeant : s'il rougit, le script remplace « Photoshop » par un libellé neutre dans les deux langues (règle D8) et le dit dans `remplacements` du JSON — voir Step 3.

Lancer : rouge (fichier absent).

- [ ] **Step 3 : le script**

`scripts/photocraft_catalogue.py` (outil Write) :

```python
"""Exporte le catalogue des menus de photocraft 0.3.0 (crates/ui-egui/src/menu_catalog.rs) et ses libellés français
(crates/ui-egui/src/i18n/fr.tsv) vers frontend/photolab/donnees/menus.json, pour l'écran du Photolab (P2).
Données de photocraft, MIT OU Apache-2.0 : la source et la licence sont écrites dans le JSON.
D8 : « Photoshop » n'apparaît dans aucun libellé montré ; chaque remplacement est consigné dans `remplacements`.

Usage : python scripts/photocraft_catalogue.py <dossier des sources photocraft v0.3.0 extraites>
"""
import json, pathlib, re, sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
SORTIE = RACINE / "frontend" / "photolab" / "donnees" / "menus.json"
LIGNE = re.compile(r'^\s*\(&\[(?P<chemin>[^\]]*)\],\s*"(?P<libelle>(?:[^"\\]|\\.)*)",\s*'
                   r'(?:Some\("(?P<raccourci>[^"]*)"\)|None),\s*"(?P<id>[^"]*)"\),\s*$')
NEUTRE = {"Photoshop": "Photolab"}


def lire_fr(tsv: pathlib.Path):
    texte, par_id = {}, {}
    for l in tsv.read_text("utf-8").splitlines():
        if not l or l.startswith("#"):
            continue
        parts = l.split("\t")
        if len(parts) != 3:
            continue
        ctx, src, trad = parts
        if ctx == "":
            texte[src] = trad
        elif ctx == "@id":
            par_id[src] = trad
    return texte, par_id


def neutre(s: str, remplacements: list) -> str:
    for a, b in NEUTRE.items():
        if a in s:
            remplacements.append(s)
            s = s.replace(a, b)
    return s


def main(args) -> int:
    src = pathlib.Path(args[0])
    cat = next(src.rglob("menu_catalog.rs"))
    tsv = next(src.rglob("i18n/fr.tsv"))
    texte, par_id = lire_fr(tsv)
    entrees, menus, remplacements = [], {}, []
    for l in cat.read_text("utf-8").splitlines():
        m = LIGNE.match(l)
        if not m:
            continue
        chemin = re.findall(r'"((?:[^"\\]|\\.)*)"', m["chemin"])
        for c in chemin:
            menus.setdefault(c, texte.get(c, c))
        if m["libelle"] == "---":
            entrees.append({"chemin": chemin, "separateur": True})
            continue
        en = m["libelle"]
        fr = par_id.get(m["id"]) or texte.get(en) or en
        entrees.append({"chemin": chemin, "id": m["id"], "libelle_en": neutre(en, remplacements),
                        "libelle_fr": neutre(fr, remplacements), "raccourci": m["raccourci"]})
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps({"source": "storytold/photocraft v0.3.0 crates/ui-egui/src/menu_catalog.rs",
                                  "licence": "MIT OR Apache-2.0", "menus_fr": menus, "remplacements": remplacements,
                                  "entrees": entrees}, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(f"{len(entrees)} lignes ({sum(1 for e in entrees if e.get('separateur'))} séparateurs), "
          f"{len(remplacements)} remplacements D8 -> {SORTIE.relative_to(RACINE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4 : télécharger, extraire, générer**

```bash
gh api repos/storytold/photocraft/tarball/v0.3.0 > "$TMP/photocraft-src.tar.gz"
mkdir -p "$TMP/photocraft-src" && tar -xzf "$TMP/photocraft-src.tar.gz" -C "$TMP/photocraft-src"
python scripts/photocraft_catalogue.py "$TMP/photocraft-src"
```
(`$TMP` = le dossier de travail temporaire de la session.) Attendu : `765 lignes (… séparateurs), N remplacements D8 -> frontend\photolab\donnees\menus.json`.

- [ ] **Step 5 : le banc, vert** — Attendu : `=== 8 passed, 0 failed ===`. Si le 2 ne donne pas 765 : la regex `LIGNE` rate une forme de ligne — afficher les lignes de `menu_catalog.rs` qui commencent par `    (&[` sans correspondre, élargir la regex, regénérer.

- [ ] **Step 6 : commit**

```bash
git add scripts/photocraft_catalogue.py frontend/photolab/donnees/menus.json backend/tests/test_photolab_catalogue.py
git commit -m "photolab : catalogue des menus de photocraft 0.3.0 exporte avec libelles FR (t136)"
```

---

### Task 10 : mutations, balayage, preuve, compte rendu

- [ ] **Step 1 : mutations** (sources copiées AVANT, comparées APRÈS ; script dans le scratchpad, comme pour t131/t134). Chaque mutation doit rendre ROUGE son banc :

| Mutation | Fichier | Banc |
|---|---|---|
| `relatif` accepte `..` (retirer le test `s in (".", "..")`) | photolab_moteur.py | test_photolab_moteur 1c |
| la réponse n'est plus appariée par id (`rep.get("id") != rid` → `False`) | photolab_moteur.py | test_photolab_moteur 2d |
| le délai n'arrête plus le moteur (retirer `self.fermer()` avant `raise MoteurDelai`) | photolab_moteur.py | 2f |
| `PREFIXES_REFUSES` sans `"file."` | photolab_moteur.py | 3b, routes 7 |
| `CLES_FICHIER` sans `"path"` | photolab_moteur.py | 3b |
| `/ouvrir` ouvre `src` directement (chemin absolu) au lieu de la copie | photolab_routes.py | routes 4 |
| `_servir` sans la regex de nom | photolab_routes.py | routes 14 |
| `verifier` ne compare plus le sha256 | vendor_photocraft.py | vendor 3 |
| le pont enregistre en jpg quand on demande png | photolab_routes.py | fidélité (pixels différents) |

- [ ] **Step 2 : balayage** — `python scripts/restaurer_bak_montage.py`, puis tous les bancs qui lisent `main.py`, les routes ou le bundle :
`grep -ln "app.main\|index-.*\.js\|BUN\b\|_bundle()\|montage.js" tests/test_*.py` (depuis `backend/`, JAMAIS `tests/mutations_*.py`). Un rouge qui l'est aussi sur `main` se dit et se traite à part.

- [ ] **Step 3 : preuve sur 8799** (serveur `preuve-t115` : code du worktree, données jetables, aucune clé) dans le navigateur intégré, par `fetch` :
  `/api/photolab/etat` (present:true, version 0.3.0) → téléverser une image (`/api/images/upload`) → `/api/photolab/ouvrir` → `/executer` flou gaussien r=3 → `/rendu {maxSide:1024}` → afficher l'URL rendue dans un `<img>` et faire une capture → `/enregistrer {format:"psd"}` → `/api/photolab/exports/<fichier>` répond. Relever les `ms` de `/rendu`.

- [ ] **Step 4 : suivi, mémoire, compte rendu** — note de t136 (bancs, spike, décision de latence), un fichier mémoire `photolab-moteur-136.md` (pièges rencontrés), puis le compte rendu à l'utilisateur et attendre « commit et ouvre la PR ». Installation : le backend change (routes, service, main.py) → relance ; le binaire va dans `%LOCALAPPDATA%\DeepotusVideoGen\vendor\photocraft-0.3.0\` (copier le dossier vérifié, puis vérifier `photocraft-cli.exe` par son sha256 contre celui de l'extraction).

---

## Auto-revue (faite à l'écriture du plan)

- **Couverture du lot P1 de la spec** : manifeste et empreinte (T1, T2), session serve / verrou / délai / redémarrage / racines (T3, T4), refus (T5), routes (T6), bancs de fidélité (T7), spike de latence (T8), catalogue des menus en JSON (T9). Rien de P2 (écran) ni de P4 (Bibliothèque en écriture) : `/ouvrir` LIT une image de la Bibliothèque, l'enregistrement dans la Bibliothèque est P4.
- **Aucun espace réservé** : les seules inconnues (structure interne du zip, forme exacte de `run`) sont traitées par du code qui s'adapte (`rglob`) ou par une consigne de diagnostic précise (T7 Step 2).
- **Noms cohérents** : `chemin_cli`, `dossier_travail`, `relatif`, `commande_autorisee`, `SessionMoteur.appeler/fermer/vivant/generation`, `session()`, `fermer()`, `FABRIQUE`, `_SESSION`, `RACINE_APP`, `MoteurAbsent/MoteurErreur/MoteurDelai` — mêmes noms dans le service, les routes et les trois bancs.
