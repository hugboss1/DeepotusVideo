# -*- coding: utf-8 -*-
# scripts/restaurer_bak_montage.py
"""Reconstitue frontend/dist/assets/index-BEOJX8L5.js.bak_montage depuis l'histoire git.

POURQUOI. Le .bak_montage (« état juste avant le maillon montage ») est gitignoré (.gitignore l. 58) : il ne vivait
que dans les copies où patch_bundle_montage.py avait tourné, et il n'existe plus NULLE PART (constaté le 06/10/2026,
copie principale, dossiers de travail et installation fouillés). Or une quinzaine de bancs lisent ses témoins
(test_montage_bundle, test_montage_edition, test_studio_r8, test_p1_*, test_p2_*, test_retours_bundle_r7…) : ils
rougissaient tous, partout, pour cette seule raison — et un rouge permanent ne détecte plus rien.

COMMENT. Le maillon montage est DÉTERMINISTE : bundle = M1 (bloc injecté après ANCHOR_INJECT) puis PATCHES dans
l'ordre, sur le .bak. Il s'inverse donc exactement : chaque remplacement (occurrence unique exigée) redevient son
ancre, en ordre inverse, puis le bloc est retiré. On l'inverse sur le bundle d'un commit SOURCE avec le patcher DE CE
COMMIT, puis on prouve l'aller : rejouer montage sur le résultat doit redonner le bundle du commit octet pour octet.

LE COMMIT SOURCE est bcb9ecfe (04/10/2026, #164), le dernier état où le .bak vivait : depuis le 06/10 (T099),
refresh_layer réécrit les blocs SONVFX/SFXSTUDIO DANS LE BUNDLE sans passer par le .bak — inverser un bundle plus
récent y laisserait T101-T103 (514 useState au lieu de 483, la garde du payload déjà posée). Les témoins relevés par
les bancs sur le vrai .bak sont contrôlés avant d'écrire : 482 useState + l'état `lots` de #19, le corps du payload
sans `c.src&&c.src.job_id`, aucun bloc montage ; et le patcher montage ACTUEL doit y trouver chaque ancre une fois.

CE QUE LE FICHIER N'EST PAS : une base de rejeu. Relancer patch_bundle_montage.py sur ce .bak restaurerait l'état du
04/10 et effacerait sans un mot tout ce que refresh_layer et les maillons aval ont écrit depuis. La reconstruction
est déterministe : patch_bundle_montage.py la reconnaît à son empreinte (BAK_RECONSTRUIT_SHA256) et refuse alors
d'appliquer et de retirer (`--check`, en lecture seule, reste permis). Pas de fichier marqueur : tout nom en `.bak_*`
serait pris pour un maillon par guard_downstream et repatch_all. Le fichier sert de TÉMOIN aux bancs, rien d'autre.

La date de modification est celle du commit source : la garde de chaîne des patchers ordonne les .bak par mtime.

Usage :
  python scripts/restaurer_bak_montage.py                       # racine = le dépôt courant
  python scripts/restaurer_bak_montage.py --root <copie> [--repo <dépôt git>] [--commit <sha>]
Un .bak_montage existant qui n'est PAS la reconstruction (autre empreinte) n'est jamais écrasé.
"""
import hashlib
import importlib.util
import io
import os
import pathlib
import subprocess
import sys
import tarfile
import tempfile

COMMIT = "bcb9ecfe"
REL = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
LOTS = "x.useState({ journaux: false, rebuts: false })"
USESTATE_BAK = 482          # mesuré par test_montage_bundle (L7d0), + 1 pour `lots`
PAYLOAD_B = "clips.filter(function(c){return c.src})"


def _arg(args, nom, defaut):
    return pathlib.Path(args[args.index(nom) + 1]).resolve() if nom in args else defaut


def _charger(chemin, nom):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _extraire(repo, commit, dest):
    data = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", commit, "scripts/patch_bundle_montage.py",
                           "frontend/patches", str(REL).replace("\\", "/")],
                          capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as t:
        t.extractall(dest, filter="data") if sys.version_info >= (3, 12) else t.extractall(dest)


def inverser(pm, s):
    """bundle -> .bak : PATCHES en ordre inverse (remplacement -> ancre, x1 exigé), puis retrait du bloc M1."""
    crlf = "\r\n" in s
    for tag, anchor, repl in reversed(pm.PATCHES):
        r = pm.nl(repl, crlf)
        if s.count(r) != 1:
            raise SystemExit(f"[inverse] {tag} : remplacement x{s.count(r)} (want 1) — inversion impossible.")
        s = s.replace(r, pm.nl(anchor, crlf))
    component = pm.PATCH_SRC.read_bytes().decode("utf-8-sig")
    block = pm.nl("\n" + pm.BEGIN + "\n" + component + "\n" + pm.END, crlf)
    if s.count(pm.ANCHOR_INJECT + block) != 1:
        raise SystemExit("[inverse] M1 : bloc montage introuvable tel que sa source le dit.")
    return s.replace(pm.ANCHOR_INJECT + block, pm.ANCHOR_INJECT)


def aller(pm, s):
    crlf = "\r\n" in s
    component = pm.PATCH_SRC.read_bytes().decode("utf-8-sig")
    block = pm.nl("\n" + pm.BEGIN + "\n" + component + "\n" + pm.END, crlf)
    if s.count(pm.ANCHOR_INJECT) != 1:
        return None
    s = s.replace(pm.ANCHOR_INJECT, pm.ANCHOR_INJECT + block)
    for _tag, anchor, repl in pm.PATCHES:
        a = pm.nl(anchor, crlf)
        if s.count(a) != 1:
            return None
        s = s.replace(a, pm.nl(repl, crlf))
    return s


def temoins(s):
    """Les faits relevés par les bancs sur le VRAI .bak_montage ; liste vide = conforme."""
    ecarts = []
    if s.count(LOTS) != 1:
        ecarts.append(f"etat lots x{s.count(LOTS)} (want 1)")
    if s.count("x.useState(") != USESTATE_BAK + 1:
        ecarts.append(f"useState {s.count('x.useState(')} (want {USESTATE_BAK + 1})")
    if "/*__DZ_MONTAGE_BEGIN__*/" in s:
        ecarts.append("bloc montage present")
    i = s.find(PAYLOAD_B)
    j = s.find("return o})", i) if i >= 0 else -1
    corps = s[i:j] if 0 <= i < j else ""
    if len(corps) <= 1500 or corps.count("c.src.job_id") != 1 or corps.count("c.src&&c.src.job_id") != 0:
        ecarts.append(f"corps du payload : {len(corps)} o, nu {corps.count('c.src.job_id')}, "
                      f"garde {corps.count('c.src&&c.src.job_id')} (want >1500, 1, 0)")
    return ecarts


def main():
    args = sys.argv[1:]
    racine = _arg(args, "--root", pathlib.Path(".").resolve())
    repo = _arg(args, "--repo", racine)
    commit = args[args.index("--commit") + 1] if "--commit" in args else COMMIT
    bundle = racine / REL
    bak = bundle.with_name(bundle.name + ".bak_montage")
    if not bundle.is_file():
        raise SystemExit(f"bundle introuvable : {bundle}")
    actuel = _charger(pathlib.Path(__file__).resolve().parent / "patch_bundle_montage.py", "pm_actuel")
    if bak.exists() and hashlib.sha256(bak.read_bytes()).hexdigest() != actuel.BAK_RECONSTRUIT_SHA256:
        raise SystemExit(f"{bak.name} existe et n'est pas la reconstruction (autre empreinte) : "
                         "refus de l'écraser — c'est peut-être le vrai.")

    with tempfile.TemporaryDirectory(prefix="dzbakm_src_") as tmp:
        tmp = pathlib.Path(tmp)
        _extraire(repo, commit, tmp)
        pm = _charger(tmp / "scripts" / "patch_bundle_montage.py", "pm_source")
        raw = (tmp / REL).read_bytes()
        bom = raw.startswith(b"\xef\xbb\xbf")
        source = raw.decode("utf-8-sig")
        s = inverser(pm, source)
        ok_aller = aller(pm, s) == source
    print(f"commit source : {commit}")
    print(f"aller == bundle du commit : {ok_aller}")
    if not ok_aller:
        raise SystemExit("rejouer montage sur la reconstruction ne redonne pas le bundle du commit — rien n'est écrit.")
    ecarts = temoins(s)
    if ecarts:
        raise SystemExit("témoins du vrai .bak non conformes : " + " ; ".join(ecarts) + " — rien n'est écrit.")
    crlf = "\r\n" in s
    hors = [t for t, a, _r in actuel.PATCHES if s.count(actuel.nl(a, crlf)) != 1]
    if s.count(actuel.ANCHOR_INJECT) != 1 or hors:
        raise SystemExit(f"le patcher montage actuel n'y trouve pas toutes ses ancres x1 : {hors[:10]} — rien n'est écrit.")

    data = (b"\xef\xbb\xbf" if bom else b"") + s.encode("utf-8")
    if hashlib.sha256(data).hexdigest() != actuel.BAK_RECONSTRUIT_SHA256:
        raise SystemExit("la reconstruction n'a pas l'empreinte déclarée par patch_bundle_montage.py "
                         "(BAK_RECONSTRUIT_SHA256) — rien n'est écrit.")
    bak.write_bytes(data)
    ts = int(subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%ct", commit],
                            capture_output=True, text=True, check=True).stdout.strip())
    os.utime(bak, (ts, ts))
    print(f"écrit : {bak} ({bak.stat().st_size} o, {s.count('x.useState(')} useState, {len(actuel.PATCHES)} ancres x1)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
