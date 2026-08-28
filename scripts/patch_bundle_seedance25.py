# -*- coding: utf-8 -*-
# scripts/patch_bundle_seedance25.py
"""Assert-guarded patcher : Seedance 2.5 dans l'estimateur de coût du Studio.

BASELINE : bundle POST-patch dznodecat (queue de chaîne du 28/08).
Backup dédié : .js.bak_seedance25 (état juste avant CE patch).

Les SÉLECTEURS de modèle vidéo sont dynamiques (DzVideoModelSel lit
/api/video-models : l'ajout au registre backend les sert tous — nœud
Seedance du Studio et écran Quick). La SEULE table en dur du bundle est
`dzVmRates` — l'estimé « ≈ $ » affiché par nœud : {id: [$ par seconde à
la résolution maximale du registre, plafond de durée natif]}.

  S1  "seedance-2.5": [.473, 30] — 0,4730 $/s en 720p (la résolution max
      du registre : fal ne publie pas de $/s 1080p, facturation aux
      tokens — même relevé 28/08 que pricing.py), plafond natif 30 s ;
  S2  le libellé de prix du sélecteur (`lbl`) lisait uniquement la
      colonne 1080p (ou « * ») de usd_per_s — un modèle sans 1080p
      s'affichait SANS prix : repli sur la colonne la plus chère
      disponible (le pire cas, la philosophie de dzVmRates).

Run : python scripts/patch_bundle_seedance25.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_seedance25")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def main():
    raw = BUNDLE.read_bytes()
    crlf = raw.count(b"\r\n")
    lf_seul = raw.count(b"\n") - crlf
    cr_seul = raw.count(b"\r") - crlf
    if lf_seul or cr_seul:
        raise SystemExit(
            f"[seedance25] fins de ligne non homogenes AVANT patch "
            f"(CRLF={crlf} LF-isole={lf_seul} CR-isole={cr_seul}). Aborting.")
    s = raw.decode("utf-8")
    if "seedance-2.5" in s:
        raise SystemExit("Bundle déjà patché (seedance-2.5 présent). Aborting.")
    if not BAK.exists():
        shutil.copyfile(BUNDLE, BAK)
        print("backup ->", BAK.name)

    s = apply(
        s,
        'var dzVmRates={"seedance-v1-pro":[.124,10],"seedance-2":[.682,15],'
        '"seedance-2-fast":[.2419,15],',
        'var dzVmRates={"seedance-v1-pro":[.124,10],"seedance-2":[.682,15],'
        '"seedance-2-fast":[.2419,15],"seedance-2.5":[.473,30],',
        "S1-rates")

    s = apply(
        s,
        'var rr=m2.usd_per_s||{},v2=rr["1080p"]!=null?rr["1080p"]:rr["*"],px=v2!=null?',
        'var rr=m2.usd_per_s||{},v2=rr["1080p"]!=null?rr["1080p"]:rr["*"];'
        'if(v2==null)for(var k9 in rr){var n9=Number(rr[k9]);'
        'if(isFinite(n9)&&(v2==null||n9>v2))v2=n9}var px=v2!=null?',
        "S2-libelle")

    BUNDLE.write_text(s, encoding="utf-8", newline="")
    fin = BUNDLE.read_bytes()
    if fin.count(b"\n") != fin.count(b"\r\n"):
        raise SystemExit("[seedance25] le patch a traduit des fins de ligne. Aborting.")
    print("bundle écrit :", len(s), "o — Seedance 2.5 dans l'estimateur de coût")


if __name__ == "__main__":
    main()
