"""Transfert entre machines — exporter tout ce que l'application a créé, et
le reprendre sur une autre installation.

Demande de l'utilisateur (07/09/2026) : « un export de toute la bibliothèque
et de tous les agents packagés pour un export inter-machines […] le contenu
de la bibliothèque doit être à l'identique, la bible, les plans de
communication, bref tout ce qui est créé depuis une instance de
l'application sur un poste doit être reconduit sur une autre instance sur
une autre machine. […] Il ne faut pas exporter les clés, évidemment. »

CE QUI PART — la racine de données (`DATA_ROOT`) et elle seule : la base
SQLite (instantané COHÉRENT, jamais une copie d'octets — le journal WAL
peut peser autant que la base et une copie brute rendrait un état plus
ancien, mesuré le 05/09/2026), les assets, les modèles et séries Cardforge,
`pricing.json`. Le code de l'application ne part PAS : il vient de
l'installeur, et les deux postes doivent tourner la même version.

CE QUI NE PART JAMAIS — les secrets et le jetable :
  * `.env` et toute variante (`.env.bak…`) : les clés d'API vivent là, et
    l'utilisateur l'a dit explicitement. Aucune clé n'est stockée en base
    (vérifié : aucune colonne ne porte de secret) ;
  * les journaux (`logs/`), qui nomment des chemins de l'autre machine ;
  * les fichiers de travail de SQLite (`-wal`, `-shm`) — l'instantané les
    contient déjà — et les vieux `.db.bak` ;
  * ce que l'application sait reconstruire : caches, aperçus, temporaires.

LE PIÈGE QUI FAIT ÉCHOUER UN IMPORT NAÏF : `jobs.video_path`,
`final_video_path`, `audio_path`, `caption_path` et `bible_entities`
stockent des chemins **ABSOLUS** (`C:\\Users\\<nom>\\AppData\\Local\\…`,
mesuré). Sur l'autre poste, le nom d'utilisateur diffère : sans
ré-ancrage, la moitié de la bibliothèque pointerait dans le vide. L'import
remplace donc le préfixe de la machine d'origine (inscrit au manifeste) par
celui de la machine réceptrice — et ne touche à rien d'autre.

FUSION, PAS ÉCRASEMENT : à l'import, une ligne dont la clé primaire existe
déjà est LAISSÉE telle quelle, un fichier déjà présent au même octet près
est sauté. Deux postes peuvent donc s'échanger leur travail dans les deux
sens sans qu'aucun ne perde le sien.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from app.config import APP_VERSION, DATA_ROOT

MANIFESTE = "manifeste.json"
DOSSIER_BASE = "base"
DOSSIER_DONNEES = "donnees"
NOM_BASE = "deepotus.db"
FORMAT = 1                      # version du format de transfert

# ── ce qui ne part pas ────────────────────────────────────────────────
# Motif par motif, pour que la raison de chaque exclusion se lise.
SECRETS = ("*.env", ".env", ".env.*")          # les clés d'API
JETABLE = (
    "logs/*",                    # journaux : chemins de l'autre machine
    "*.db-wal", "*.db-shm",      # journal SQLite : l'instantané le contient
    "*.db.bak", "*.db",          # la base part par l'instantané, pas brute
    "rebut_*/*",                 # corbeilles datées
    "assets/outputs/_cache/*",   # cache d'aperçus du montage
    "assets/outputs/_tmp_*/*",   # rendus en cours
    "assets/outputs/fxpreview/*",  # vignettes d'effets, régénérées
    "assets/outputs/_graphs/*",  # instantanés de graphes de travail
    "**/__pycache__/*",
    "**/.DS_Store", "**/Thumbs.db",
)


def _motif(rel: str, motifs: tuple[str, ...]) -> bool:
    p = Path(rel.replace("\\", "/"))
    return any(p.match(m) or p.as_posix().startswith(m.rstrip("*"))
               for m in motifs)


def exclu(rel: str) -> tuple[bool, str]:
    """(exclu ?, motif lisible) — un seul endroit décide, l'écran l'affiche."""
    if _motif(rel, SECRETS):
        return True, "clé d'API"
    if _motif(rel, JETABLE):
        return True, "jetable"
    return False, ""


@dataclass
class Etat:
    """L'avancement, tel que l'écran le montre."""
    phase: str = "attente"
    fait: int = 0
    total: int = 0
    octets: int = 0
    octets_total: int = 0
    fichier: str = ""
    lignes: dict = field(default_factory=dict)
    detail: str = ""

    def dict(self) -> dict:
        pct = 0
        if self.octets_total:
            pct = min(99, round(self.octets * 100 / self.octets_total))
        elif self.total:
            pct = min(99, round(self.fait * 100 / self.total))
        return {"phase": self.phase, "pct": 100 if self.phase == "fini" else pct,
                "fait": self.fait, "total": self.total,
                "octets": self.octets, "octets_total": self.octets_total,
                "fichier": self.fichier, "lignes": self.lignes,
                "detail": self.detail}


def racine() -> Path:
    return Path(DATA_ROOT)


def inventaire(base: Path | None = None) -> tuple[list[tuple[str, int]], int]:
    """Les fichiers qui partent, en chemins RELATIFS à la racine, et le poids.

    Trié : l'export est alors reproductible, et deux inventaires se
    comparent ligne à ligne.
    """
    base = base or racine()
    out: list[tuple[str, int]] = []
    total = 0
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(base).as_posix()
        if exclu(rel)[0]:
            continue
        try:
            t = p.stat().st_size
        except OSError:
            continue
        out.append((rel, t))
        total += t
    out.sort()
    return out, total


def instantane_base(dst: Path) -> int:
    """La base, COHÉRENTE : `backup()` fusionne le journal WAL.

    Une copie d'octets du seul `.db` rend un état plus ancien — mesuré le
    05/09/2026 : 105 jobs au lieu de 116, sans la moindre erreur.
    """
    src = racine() / NOM_BASE
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    s = sqlite3.connect("file:" + src.as_posix() + "?mode=ro", uri=True)
    t = sqlite3.connect(str(dst))
    try:
        s.backup(t)
    finally:
        t.close()
        s.close()
    return dst.stat().st_size


def compte_lignes(db: Path) -> dict:
    c = sqlite3.connect("file:" + db.as_posix() + "?mode=ro", uri=True)
    try:
        tabs = [r[0] for r in c.execute(
            "select name from sqlite_master where type='table' "
            "and name not like 'sqlite_%'")]
        return {n: c.execute(f'select count(*) from "{n}"').fetchone()[0]
                for n in sorted(tabs)}
    finally:
        c.close()


def nom_paquet(quand: float | None = None) -> str:
    t = time.localtime(quand if quand is not None else time.time())
    return time.strftime("DeepotusVideoGen-Transfert-%Y-%m-%d-%H%M", t)


def exporter(destination: str | Path, etat: Etat | None = None,
             *, quand: float | None = None) -> dict:
    """Écrit le paquet de transfert dans `destination`. Rend le manifeste."""
    etat = etat or Etat()
    dest = Path(destination).expanduser()
    if not dest.is_dir():
        raise ValueError(f"Destination introuvable : {dest}")
    paquet = dest / nom_paquet(quand)
    if paquet.exists():
        raise ValueError(f"Un paquet du même nom existe déjà : {paquet.name}")

    etat.phase = "inventaire"
    fichiers, poids = inventaire()
    etat.total, etat.octets_total = len(fichiers), poids
    libre = shutil.disk_usage(dest).free
    if libre < poids * 1.05:
        raise ValueError(
            f"Place insuffisante : {poids / 1e9:.1f} Go à écrire, "
            f"{libre / 1e9:.1f} Go libres sur la destination.")

    paquet.mkdir(parents=True)
    etat.phase = "base"
    etat.detail = "instantané cohérent de la base"
    taille_db = instantane_base(paquet / DOSSIER_BASE / NOM_BASE)
    lignes = compte_lignes(paquet / DOSSIER_BASE / NOM_BASE)
    etat.lignes = lignes

    etat.phase = "fichiers"
    src = racine()
    for rel, taille in fichiers:
        cible = paquet / DOSSIER_DONNEES / rel
        cible.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, cible)
        etat.fait += 1
        etat.octets += taille
        etat.fichier = rel

    manifeste = {
        "format": FORMAT,
        "app_version": APP_VERSION,
        "cree_le": time.strftime("%Y-%m-%dT%H:%M:%S",
                                 time.localtime(quand or time.time())),
        "machine": os.environ.get("COMPUTERNAME") or os.uname().nodename
        if hasattr(os, "uname") else os.environ.get("COMPUTERNAME", "?"),
        # LA CLÉ DU RÉ-ANCRAGE : la racine d'origine, telle qu'elle est
        # écrite dans les chemins absolus de la base.
        "racine_origine": str(racine()),
        "fichiers": len(fichiers),
        "octets": poids,
        "base_octets": taille_db,
        "lignes": lignes,
        "exclus": {"secrets": list(SECRETS), "jetable": list(JETABLE)},
    }
    (paquet / MANIFESTE).write_text(
        json.dumps(manifeste, ensure_ascii=False, indent=1), encoding="utf-8")
    etat.phase = "fini"
    etat.detail = str(paquet)
    logger.info(f"transfert: export de {len(fichiers)} fichiers "
                f"({poids / 1e6:.0f} Mo) vers {paquet}")
    return {**manifeste, "dossier": str(paquet)}


def lire_manifeste(dossier: str | Path) -> dict:
    """Le manifeste d'un paquet, avec les refus PARLANTS."""
    d = Path(dossier).expanduser()
    if d.is_file() and d.name == MANIFESTE:
        d = d.parent
    m = d / MANIFESTE
    if not m.exists():
        raise ValueError(f"Ce dossier ne porte pas de {MANIFESTE} : {d}")
    data = json.loads(m.read_text(encoding="utf-8"))
    if int(data.get("format") or 0) != FORMAT:
        raise ValueError(f"Format de transfert {data.get('format')} inconnu "
                         f"(cette version lit le {FORMAT}).")
    if not (d / DOSSIER_BASE / NOM_BASE).exists():
        raise ValueError("Paquet incomplet : la base est absente.")
    return {**data, "dossier": str(d)}


# Les colonnes qui portent un chemin ABSOLU, mesurées le 07/09/2026 sur la
# base réelle. `image_filename`, `library_assets.filename` et
# `meshy_tasks.local_dir` sont RELATIFS : ils ne doivent pas être touchés.
COLONNES_CHEMIN = {
    "jobs": ("video_path", "audio_path", "final_video_path", "caption_path"),
    "bible_entities": ("model3d_file",),
    "scheduled_posts_legacy": ("render_path",),
    "meshy_tasks": ("local_files",),
}


def reancrer(valeur, origine: str, ici: str):
    """Remplace le préfixe de la machine d'origine. Rend la valeur telle
    quelle si elle ne commence pas par ce préfixe — un chemin relatif, une
    valeur nulle ou un chemin d'une TROISIÈME machine ne sont pas devinés."""
    if not isinstance(valeur, str) or not valeur or not origine:
        return valeur
    for o in (origine, origine.replace("\\", "/")):
        for v, sep in ((valeur, "\\"), (valeur.replace("/", "\\"), "\\")):
            if v.lower().startswith(o.replace("/", "\\").lower()):
                return ici + v[len(o):]
    return valeur


def importer(dossier: str | Path, etat: Etat | None = None) -> dict:
    """Reprend un paquet dans CETTE installation. Fusionne, n'écrase pas."""
    etat = etat or Etat()
    man = lire_manifeste(dossier)
    d = Path(man["dossier"])
    origine = str(man.get("racine_origine") or "")
    ici = str(racine())

    etat.phase = "inventaire"
    src = d / DOSSIER_DONNEES
    fichiers: list[tuple[str, int]] = []
    poids = 0
    if src.is_dir():
        for p in src.rglob("*"):
            if p.is_file():
                rel = p.relative_to(src).as_posix()
                if exclu(rel)[0]:          # ceinture : un paquet bricolé
                    continue               # ne réintroduit pas de `.env`
                t = p.stat().st_size
                fichiers.append((rel, t))
                poids += t
    fichiers.sort()
    etat.total, etat.octets_total = len(fichiers), poids

    etat.phase = "fichiers"
    ajoutes = sautes = 0
    for rel, taille in fichiers:
        cible = racine() / rel
        if cible.exists() and cible.stat().st_size == taille:
            sautes += 1                    # déjà là, au même octet près
        else:
            cible.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src / rel, cible)
            ajoutes += 1
        etat.fait += 1
        etat.octets += taille
        etat.fichier = rel

    etat.phase = "base"
    etat.detail = "fusion des enregistrements"
    res = fusionner_base(d / DOSSIER_BASE / NOM_BASE, origine, ici)
    etat.lignes = res["ajoutees"]
    etat.phase = "fini"
    etat.detail = (f"{ajoutes} fichiers repris, {sautes} déjà présents ; "
                   f"{sum(res['ajoutees'].values())} enregistrements ajoutés")
    logger.info(f"transfert: import — {etat.detail}")
    return {"fichiers_ajoutes": ajoutes, "fichiers_sautes": sautes,
            "octets": poids, **res, "manifeste": man}


def fusionner_base(paquet_db: Path, origine: str, ici: str) -> dict:
    """Ajoute les lignes ABSENTES, ré-ancre les chemins, ne touche à rien
    d'autre. Les tables inconnues de cette installation sont ignorées (et
    dites) : un paquet plus récent ne doit pas casser l'import."""
    cible_db = racine() / NOM_BASE
    src = sqlite3.connect("file:" + paquet_db.as_posix() + "?mode=ro", uri=True)
    dst = sqlite3.connect(str(cible_db))
    ajoutees: dict[str, int] = {}
    ignorees: list[str] = []
    try:
        tabs_src = [r[0] for r in src.execute(
            "select name from sqlite_master where type='table' "
            "and name not like 'sqlite_%'")]
        tabs_dst = {r[0] for r in dst.execute(
            "select name from sqlite_master where type='table'")}
        for t in sorted(tabs_src):
            if t not in tabs_dst:
                ignorees.append(t)
                continue
            cols_src = [r[1] for r in src.execute(f'pragma table_info("{t}")')]
            cols_dst = [r[1] for r in dst.execute(f'pragma table_info("{t}")')]
            cols = [c for c in cols_src if c in cols_dst]
            if not cols:
                ignorees.append(t)
                continue
            chemins = {c for c in COLONNES_CHEMIN.get(t, ()) if c in cols}
            lignes = src.execute(
                f'select {", ".join(chr(34) + c + chr(34) for c in cols)} '
                f'from "{t}"').fetchall()
            if not lignes:
                continue
            if chemins:
                idx = [i for i, c in enumerate(cols) if c in chemins]
                lignes = [tuple(reancrer(v, origine, ici) if i in idx else v
                                for i, v in enumerate(r)) for r in lignes]
            avant = dst.execute(f'select count(*) from "{t}"').fetchone()[0]
            dst.executemany(
                f'insert or ignore into "{t}" '
                f'({", ".join(chr(34) + c + chr(34) for c in cols)}) '
                f'values ({", ".join("?" * len(cols))})', lignes)
            apres = dst.execute(f'select count(*) from "{t}"').fetchone()[0]
            if apres != avant:
                ajoutees[t] = apres - avant
        dst.commit()
    finally:
        dst.close()
        src.close()
    return {"ajoutees": ajoutees, "tables_ignorees": ignorees}


def destinations() -> list[dict]:
    """Les volumes où écrire : la racine de chaque disque, plus le Bureau.

    Le navigateur ne sait pas ouvrir un sélecteur de dossier du système ;
    l'écran propose donc cette liste ET un champ libre.
    """
    out: list[dict] = []
    vus: set[str] = set()

    def ajoute(chemin: Path, nom: str) -> None:
        try:
            if not chemin.is_dir():
                return
            u = shutil.disk_usage(chemin)
        except OSError:
            return
        cle = str(chemin).lower()
        if cle in vus:
            return
        vus.add(cle)
        out.append({"chemin": str(chemin), "nom": nom,
                    "libre": u.free, "total": u.total})

    if os.name == "nt":
        for lettre in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            ajoute(Path(f"{lettre}:\\"), f"Disque {lettre}:")
        prof = Path.home()
        for nom, sous in (("Bureau", "Desktop"), ("Bureau", "Bureau"),
                          ("Documents", "Documents")):
            ajoute(prof / sous, nom)
    else:
        ajoute(Path.home(), "Dossier personnel")
        for m in ("/media", "/mnt", "/Volumes"):
            b = Path(m)
            if b.is_dir():
                for p in b.iterdir():
                    ajoute(p, p.name)
    return out
