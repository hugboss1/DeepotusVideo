# -*- coding: utf-8 -*-
"""Socle Son & VFX (T099, plan 2026-09-03-plan-son-vfx T1) : helper de ducking octet pour octet, kinds de prix,
source `sonvfx` de la Bibliothèque, refresh_layer — à sec ET pour de vrai sur une COPIE du bundle.

Écarts au plan, relevés sur le terrain le 06/10/2026 :
- le Montage portait DÉJÀ le ducking paramétré (via sfx_service.fnum) : le helper le rend octet pour octet, et
  le Montage l'appelle ;
- pricing a DÉJÀ une branche `music` (registre MUSIC_MODELS, tâche #16) : seules stems / isolate / matte sont
  ajoutées ; ACE-Step et MiniMax 2.0 entreront au registre avec leur tâche (T6 du plan) ;
- la chaîne compte 11 .bak (le plan en comptait 4, sans .bak_subs ni .bak_vfxrack) : refresh_layer n'en ouvre
  toujours AUCUN, et le banc le vérifie sur une copie qui en porte.

Run: python tests/test_son_vfx_socle.py (depuis backend/)
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

os.environ.setdefault("DEEPOTUS_DATA_DIR", tempfile.mkdtemp(prefix="dzsvx_"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
OUTIL = RACINE / "scripts" / "refresh_layer.py"
BUNDLE_REL = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def main():
    from app.services import sfx_service as S, pricing as P, library_index as LI

    # ── 1 · le helper de ducking, octet pour octet avec la ligne historique ──
    check("ducking bool = ligne historique",
          S.ducking_filter(True) == "sidechaincompress=threshold=0.05:ratio=6:attack=50:release=400")
    d = S.parse_ducking({"ratio": 8, "attack_ms": 20, "release_ms": 300, "threshold": 0.1})
    check("ducking dict = mêmes champs, même ordre",
          S.ducking_filter(d) == "sidechaincompress=threshold=0.1:ratio=8:attack=20:release=300",
          S.ducking_filter(d))
    # le Montage rend EXACTEMENT ce qu'il rendait (l'ancienne écriture, recopiée ici en littéral)
    ancien = (f"sidechaincompress=threshold={S.fnum(d['threshold'])}:ratio={S.fnum(d['ratio'])}:"
              f"attack={S.fnum(d['attack'])}:release={S.fnum(d['release'])}")
    check("ducking dict = l'écriture historique du Montage", S.ducking_filter(d) == ancien)
    src_m = (RACINE / "backend/app/services/montage_service.py").read_text(encoding="utf-8")
    check("le Montage appelle LE helper (plus de chaîne recopiée)",
          "sfx_service.ducking_filter(ducking)" in src_m and "threshold=0.05:ratio=6:attack=50:release=400" not in src_m)

    # ── 2 · les kinds de prix ───────────────────────────────────────────────
    p = P.load()
    for k, v in (("demucs_usd_per_s", 0.0007), ("birefnet_video_usd_per_s", 0.0),
                 ("elevenlabs_isolation_chars_per_min", 1000.0)):
        check(f"clé de prix {k}", p.get(k) == v, str(p.get(k)))
    e = P.estimate({"kind": "stems", "duration_s": 100})
    check("estimation stems = 100 s × 0,0007", abs(e["total_usd"] - 0.07) < 1e-6, str(e))
    e = P.estimate({"kind": "isolate", "duration_s": 90})
    check("estimation isolation = 1,5 min × 1000 car. × tarif",
          abs(e["total_usd"] - 1500 * P.elevenlabs_rate(None, p)) < 1e-9, str(e))
    e = P.estimate({"kind": "matte", "duration_s": 10})
    check("estimation matte = 0 $ MAIS ligne présente et libellée « à mesurer »",
          e["total_usd"] == 0.0 and "mesurer" in e["breakdown"][0]["label"], str(e))
    m = P.estimate({"kind": "music", "model": "", "n": 1})
    check("la branche `music` existante est intacte (registre)", m["total_usd"] > 0, str(m))

    # ── 3 · la source de la Bibliothèque ────────────────────────────────────
    check("source sonvfx connue de la Bibliothèque", LI.SOURCES.get("sonvfx") == "Son & VFX")

    # ── 4 · refresh_layer à sec, sur le dépôt ───────────────────────────────
    for couche in ("sfxstudio", "vfxrack", "sonvfx", "montage"):
        r = subprocess.run([sys.executable, str(OUTIL), "--layer", couche, "--check"],
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        check(f"refresh_layer --check {couche} : 1 bloc, rien d'écrit",
              r.returncode == 0 and "bloc: 1" in r.stdout and "rien écrit" in r.stdout,
              r.stdout[-300:] + r.stderr[-300:])

    # ── 5 · refresh_layer POUR DE VRAI, sur une COPIE qui porte des .bak ────
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzrefresh_"))
    try:
        b = tmp / BUNDLE_REL
        b.parent.mkdir(parents=True)
        shutil.copyfile(RACINE / BUNDLE_REL, b)
        for tag in ("subs", "vfxrack", "version"):
            (b.parent / f"{b.name}.bak_{tag}").write_bytes(b"ne pas toucher " + tag.encode())
        empreinte = {q.name: q.read_bytes() for q in b.parent.glob(b.name + ".bak_*")}
        (tmp / "frontend/patches").mkdir(parents=True)
        source = (RACINE / "frontend/patches/sfxstudio.js").read_bytes().decode("utf-8-sig")
        marque = "/* refresh_layer : marque du banc T099 */"
        (tmp / "frontend/patches/sfxstudio.js").write_bytes((marque + "\n" + source).encode("utf-8"))
        avant = (RACINE / BUNDLE_REL).read_bytes()
        r = subprocess.run([sys.executable, str(OUTIL), "--layer", "sfxstudio", "--root", str(tmp)],
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        apres = b.read_bytes()
        texte = apres.decode("utf-8-sig")
        bloc = texte.split("/*__DZ_SFXSTUDIO_BEGIN__*/", 1)[1].split("/*__DZ_SFXSTUDIO_END__*/", 1)[0]
        hors = texte.replace(bloc, "")
        hors_avant = avant.decode("utf-8-sig")
        bloc_avant = hors_avant.split("/*__DZ_SFXSTUDIO_BEGIN__*/", 1)[1].split("/*__DZ_SFXSTUDIO_END__*/", 1)[0]
        check("refresh réel : code 0", r.returncode == 0, r.stdout[-300:] + r.stderr[-300:])
        check("le bloc porte la source neuve", marque in bloc)
        check("hors du bloc, PAS UN OCTET n'a bougé", hors == hors_avant.replace(bloc_avant, ""))
        check("les .bak de la copie sont intacts, octet pour octet",
              {q.name: q.read_bytes() for q in b.parent.glob(b.name + ".bak_*")} == empreinte)
        crlf_avant, crlf_apres = avant.count(b"\r\n"), apres.count(b"\r\n")
        check("fins de ligne alignées sur le bundle (CRLF partout ou nulle part)",
              (crlf_avant == 0) == (crlf_apres == 0) and apres.count(b"\n") - crlf_apres <= avant.count(b"\n") - crlf_avant,
              f"{crlf_avant} -> {crlf_apres}")
        check("le dépôt lui-même n'a pas été touché", (RACINE / BUNDLE_REL).read_bytes() == avant)
        # un bundle aux marqueurs doublés : refus, rien écrit
        b.write_bytes(apres + b"/*__DZ_SFXSTUDIO_BEGIN__*/")
        r2 = subprocess.run([sys.executable, str(OUTIL), "--layer", "sfxstudio", "--root", str(tmp)],
                            capture_output=True, text=True, encoding="utf-8", timeout=60)
        check("marqueurs doublés : refus et rien écrit",
              r2.returncode != 0 and b.read_bytes() == apres + b"/*__DZ_SFXSTUDIO_BEGIN__*/", r2.stdout + r2.stderr)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── 6 · les trois SOURCES reproduisent leur bloc : rafraîchir sans changement = 0 octet de différence ──
    # (adoption du 06/10 : sfxstudio.js manquait les 36 lignes L6 et son-vfx-montage.js les 1 462 du Montage L1→L7)
    for couche in ("sfxstudio", "vfxrack", "sonvfx", "montage"):
        t = pathlib.Path(tempfile.mkdtemp(prefix="dzrefresh_"))
        try:
            (t / BUNDLE_REL).parent.mkdir(parents=True)
            shutil.copyfile(RACINE / BUNDLE_REL, t / BUNDLE_REL)
            shutil.copytree(RACINE / "frontend/patches", t / "frontend/patches")
            r = subprocess.run([sys.executable, str(OUTIL), "--layer", couche, "--root", str(t)],
                               capture_output=True, text=True, encoding="utf-8", timeout=120)
            check(f"rafraîchir {couche} depuis sa source : bundle identique à l'octet",
                  r.returncode == 0 and (t / BUNDLE_REL).read_bytes() == (RACINE / BUNDLE_REL).read_bytes(),
                  r.stdout[-200:] + r.stderr[-200:])
        finally:
            shutil.rmtree(t, ignore_errors=True)

    # ── 7 · la GARDE DE DÉRIVE, dans une copie VERSIONNÉE : un patcher a écrit dans le bloc -> refus, puis adoption ──
    t = pathlib.Path(tempfile.mkdtemp(prefix="dzderive_"))
    try:
        (t / BUNDLE_REL).parent.mkdir(parents=True)
        shutil.copyfile(RACINE / BUNDLE_REL, t / BUNDLE_REL)
        shutil.copytree(RACINE / "frontend/patches", t / "frontend/patches")
        g = ["git", "-C", str(t), "-c", "user.name=banc", "-c", "user.email=banc@local"]
        subprocess.run(g[:3] + ["init", "-q"], check=True)
        subprocess.run(g + ["add", "frontend/patches"], check=True)
        subprocess.run(g + ["commit", "-q", "-m", "sources"], check=True)
        raw = (t / BUNDLE_REL).read_bytes()
        intrus = b"/* injecte DANS le bloc par un autre patcher (banc T099) */"
        fin = b"/*__DZ_VFXRACK_END__*/"
        (t / BUNDLE_REL).write_bytes(raw.replace(fin, intrus + b"\r\n" + fin, 1))
        apres_intrus = (t / BUNDLE_REL).read_bytes()
        r = subprocess.run([sys.executable, str(OUTIL), "--layer", "vfxrack", "--root", str(t)],
                           capture_output=True, text=True, encoding="utf-8", timeout=120)
        check("dérive : refus (rc 5), la ligne intruse est NOMMÉE, rien écrit",
              r.returncode == 5 and "injecte DANS le bloc" in r.stdout
              and (t / BUNDLE_REL).read_bytes() == apres_intrus, r.stdout[-300:])
        r = subprocess.run([sys.executable, str(OUTIL), "--layer", "vfxrack", "--root", str(t), "--check"],
                           capture_output=True, text=True, encoding="utf-8", timeout=120)
        check("--check dit la dérive (l'intruse et la ligne de bord qu'elle déplace)",
              "dérive : " in r.stdout and "dérive : 0" not in r.stdout, r.stdout)
        r = subprocess.run([sys.executable, str(OUTIL), "--layer", "vfxrack", "--root", str(t), "--adopter"],
                           capture_output=True, text=True, encoding="utf-8", timeout=120)
        src = (t / "frontend/patches/vfxrack.js").read_bytes()
        check("--adopter : la source reprend la ligne intruse, bundle inchangé",
              r.returncode == 0 and intrus in src and (t / BUNDLE_REL).read_bytes() == apres_intrus, r.stdout)
    finally:
        shutil.rmtree(t, ignore_errors=True)

    print(f"\n=== {ok} passed, {fail} failed ===")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
